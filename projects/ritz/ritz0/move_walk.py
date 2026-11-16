"""
The move checker's walk over statements and expressions (LANGUAGE_SPEC §13).

MoveWalk is MoveChecker's walk, one method per AST node kind, reached through
two dispatch tables keyed on the node's class: STMT_CHECKS and EXPR_CHECKS
(LARB review/5 ritz0 N2, AGAST #3449; they were one if/elif chain each,
`_check_one_stmt` and a 220-line `_check_expr`).  A kind with no entry has no
ownership effect: literals, `sizeof`'s operand, a lambda's body.  Every listed
kind is a direct subclass of rast.Expr or rast.Stmt, so `type(node)` finds
exactly the entry the isinstance chain used to (test_pass_structure.py).

The state it walks over (scopes, loans, the types) and the questions it asks
(`_check_borrow`, `_through_reference`, ...) are MoveChecker's, in
move_checker.py.  Blocks, `defer`s and loops are here too: they are the walk.
"""

from typing import Dict, List, Optional, Set, Tuple

import array_rules
import deref_rules
import ritz_ast as rast
from move_state import OwnershipError, Scope, VarInfo, VarState, _is_lending_param

# One binding's state in a snapshot: (binding, state, move span, moved fields).
Snapshot = Dict[int, Tuple[VarInfo, VarState, Optional[rast.Span], Dict[str, rast.Span]]]


class MoveWalk:
    """The per-node-kind half of MoveChecker (see the module docstring)."""

    # ---- blocks and `defer` --------------------------------------------------

    def _check_block(self, block: rast.Block, value_used: bool = True) -> bool:
        """Check a block expression.

        `value_used` is False when nothing receives the block's value (a
        procedure body, an `if` arm in statement position): its tail is then
        a temporary, or a binding that stays owned, not a move (AGAST #2253).

        Returns True if block definitely returns (via ReturnStmt).
        """
        self._defers.append([])
        try:
            for stmt in block.stmts:
                returned = self._check_stmt(stmt)
                if returned:
                    # Rest of block is dead code - skip checking it
                    # This prevents false positives like "use after move" when the
                    # move is in a return and the "use" is after the return
                    return True
            if block.expr:
                # A block's value is a statement of its own for loans: an arm's
                # `@&c` doesn't meet the next arm's.
                mark = len(self._arg_loans)
                # A bare `t:& T` tail still reads the referent by value, used
                # or not, as on ritz1 (AGAST #2949).
                lent = (isinstance(block.expr, rast.Ident)
                        and self._lent_param(block.expr) is not None)
                self._check_expr(block.expr, is_move_context=value_used or lent)
                self._release_arg_loans(mark)
            # Falling off the end, after the tail value.
            self._run_defers(len(self._defers) - 1)
            return False
        finally:
            self._defers.pop()

    def _run_defers(self, depth: int) -> None:
        """Check the deferred statements of the blocks from `depth` up, innermost
        first and LIFO, as if written here (an exit of those blocks). Each is
        checked in the scope it was written in. A name it uses that is moved
        here is an error at the `defer`; otherwise its own moves count, so a
        deferred move is the binding's last use (LANGUAGE_SPEC §13.7)."""
        for frame in reversed(self._defers[depth:]):
            for stmt, scope in reversed(frame):
                self._run_defer(stmt, scope)

    def _run_defer(self, stmt: rast.DeferStmt, scope: Scope) -> None:
        """One deferred statement, for _run_defers."""
        moved = self._moved_in_defer(stmt, scope)
        if moved is not None:
            if id(stmt) not in self._refused_defers:
                self._refused_defers.add(id(stmt))
                self.errors.append(OwnershipError(
                    f"`{moved}` may be moved before the deferred statement runs",
                    stmt.span))
            return
        saved = self.scope
        self.scope = scope
        try:
            self._push_scope()
            self._check_block(stmt.body)
            self._pop_scope()
        finally:
            self.scope = saved

    def _moved_in_defer(self, stmt: rast.DeferStmt, scope: Scope) -> Optional[str]:
        """The first name the deferred statement uses that is moved (or has a
        field moved out) now, or None."""
        found: List[str] = []

        def walk(node):
            if found:
                return
            if isinstance(node, rast.Ident):
                info = scope.lookup(node.name)
                if info is not None and (info.state == VarState.MOVED or info.moved_fields):
                    found.append(node.name)
                return
            if isinstance(node, (rast.Lambda, rast.Closure)):
                return
            if isinstance(node, list):
                for child in node:
                    walk(child)
            elif isinstance(node, rast.Node):
                for f in node.__dataclass_fields__:
                    child = getattr(node, f)
                    if isinstance(child, (list, rast.Node)):
                        walk(child)
        walk(stmt.body)
        return found[0] if found else None

    # ---- statements ----------------------------------------------------------

    def _check_stmt(self, stmt: rast.Stmt) -> bool:
        """Check a statement for ownership violations. The loans it makes
        that no binding holds end with it (AGAST #2438).

        Returns True if statement definitely returns (terminates control flow).
        """
        mark = len(self._arg_loans)
        try:
            return self._check_one_stmt(stmt)
        finally:
            self._release_arg_loans(mark)

    def _check_one_stmt(self, stmt: rast.Stmt) -> bool:
        """Dispatch on the statement's kind (STMT_CHECKS); True if it ends
        this control flow path."""
        check = self.STMT_CHECKS.get(type(stmt))
        return check(self, stmt) if check is not None else False

    def _binding_type(self, stmt) -> rast.Type:
        """What a `var` or `let` declares: its explicit type if present,
        otherwise inferred from its initializer."""
        if stmt.type:
            return stmt.type
        elif stmt.value:
            return self._infer_expr_type(stmt.value)
        return rast.NamedType(stmt.span, 'unknown', [])

    def _stmt_var(self, stmt: rast.VarStmt) -> bool:
        if stmt.value:
            self._check_expr(stmt.value, is_move_context=True)
        elif (isinstance(self.types.resolve(stmt.type), rast.ArrayType)
                and self.types.is_move_only(stmt.type)):
            # §3.3 (LARB R39): storing an element drops the old one, so
            # every element of a Drop array must hold a value.
            self.errors.append(OwnershipError(
                array_rules.uninitialised_drop_array(stmt.name),
                stmt.name_span or stmt.span))
        self.scope.define(stmt.name, self._binding_type(stmt), stmt.span)
        self._hold_loans(self.scope.vars[stmt.name], stmt.value, stmt.type)
        return False

    def _stmt_let(self, stmt: rast.LetStmt) -> bool:
        if stmt.value:
            self._check_expr(stmt.value, is_move_context=True)
        self.scope.define(stmt.name, self._binding_type(stmt), stmt.span)
        self._hold_loans(self.scope.vars[stmt.name], stmt.value, stmt.type)
        return False

    def _stmt_let_tuple(self, stmt: rast.LetTupleStmt) -> bool:
        # `let (a, b) = v` (§13.6, AGAST #2282): v moves, as into a
        # `let`, and each name owns its element (a struct's field, by
        # declaration order), so the emitter drops the names, not v.
        self._check_expr(stmt.value, is_move_context=True)
        elems = self._destructured_types(stmt.value, len(stmt.names))
        for i, name in enumerate(stmt.names):
            span = stmt.name_spans[i] if i < len(stmt.name_spans) else stmt.span
            self.scope.define(name, elems[i], span)
        return False

    def _stmt_expr(self, stmt: rast.ExprStmt) -> bool:
        self._check_expr(stmt.expr, is_move_context=False)
        return False

    def _stmt_assert(self, stmt: rast.AssertStmt) -> bool:
        # Its condition is checked like any expression, as on ritz1: a
        # call's `@&s, @s` is the same conflict there (AGAST #2438).
        self._check_expr(stmt.condition, is_move_context=False)
        return False

    def _stmt_return(self, stmt: rast.ReturnStmt) -> bool:
        if stmt.value:
            self._check_expr(stmt.value, is_move_context=True)
        self._run_defers(0)
        # Return terminates this control flow path
        return True

    def _stmt_defer(self, stmt: rast.DeferStmt) -> bool:
        # Nothing runs here: it's checked at each exit (_run_defers).
        if self._defers:
            self._defers[-1].append((stmt, self.scope))
        return False

    def _stmt_assign(self, stmt: rast.AssignStmt) -> bool:
        # Check the value first - this is a move. `t = f(t)` reads the
        # old t before the assignment makes t an owner again.
        self._check_expr(stmt.value, is_move_context=True)
        # The target (lvalue) is not a move, and assigning to a bare
        # moved-from binding is not a use of it (§13.6). Nor is assigning
        # to a field moved out of a binding: that field is owned again.
        if self._reown_field(stmt.target):
            # The emitter sets the field's drop flags again.
            stmt.target.reowns_field = True
        elif not isinstance(stmt.target, rast.Ident):
            self._check_expr(stmt.target, is_move_context=False)
        # A write inside a borrowed place (AGAST #2438, R11a).
        self._check_mut_use(self._loan_place(stmt.target), stmt.target.span, "assign")
        # After assignment, the target variable becomes owned again
        if isinstance(stmt.target, rast.Ident):
            var_info = self.scope.lookup(stmt.target.name)
            if var_info:
                var_info.state = VarState.OWNED
                var_info.move_span = None
                var_info.moved_fields = {}
        return False

    def _stmt_asm(self, stmt: rast.AsmStmt) -> bool:
        # §18.6: an `out` or `inout` operand is an assignment of its
        # place for the borrow rules (§13.5); ritz1: ref_check_asm.
        for o in stmt.operands:
            if o.direction in ('out', 'inout'):
                target = rast.Ident(o.span, o.name)
                self._check_mut_use(self._loan_place(target), o.span, "assign")
        return False

    def _stmt_while(self, stmt: rast.WhileStmt) -> bool:
        def iteration():
            # The condition runs at the loop head, on every iteration.
            self._check_expr(stmt.cond, is_move_context=False)
            self._push_scope()
            done = self._check_block(stmt.body)
            self._pop_scope()
            return done
        self._check_loop(iteration)
        return False

    def _stmt_for(self, stmt: rast.ForStmt) -> bool:
        # The iterator is moved into the loop, once. What a reference
        # reaches stays its owner's, so the loop only reads it.  A call's
        # `[N]T` result, or an array literal, is a temporary, dropped per
        # element after the loop however it's left: `x` is a copy of its
        # element, as over a local, and drops nothing (AGAST #3284, #3297).
        # A global, or a field of one, is walked in place (§6.3): it is
        # never dropped, so nothing moves out of it (LARB R34, #3366).
        in_place = (self._through_reference(stmt.iter)
                    or self._array_temporary(stmt.iter)
                    or self._global_place(stmt.iter))
        self._check_expr(stmt.iter, is_move_context=not in_place)
        held = self._for_loan(stmt.iter)
        if held is not None:
            held[0].borrows.append(held[1])

        def iteration():
            self._push_scope()
            # Loop variable is defined fresh each iteration
            # For range-based for loops, the variable is i64 (Copy type)
            self.scope.define(stmt.var, rast.NamedType(stmt.span, 'i64', []), stmt.span)
            done = self._check_block(stmt.body)
            self._pop_scope()
            return done
        self._check_loop(iteration)
        if held is not None:
            held[0].borrows = [b for b in held[0].borrows if b is not held[1]]
        return False

    def _stmt_break(self, stmt: rast.BreakStmt) -> bool:
        self._run_loop_defers()
        self._note_loop_exit('breaks')
        return True

    def _stmt_continue(self, stmt: rast.ContinueStmt) -> bool:
        self._run_loop_defers()
        self._note_loop_exit('continues')
        return True

    # ---- loops (AGAST #2161) ------------------------------------------------
    #
    # A loop body runs again with whatever the previous iteration left, so a
    # binding declared outside the loop and moved inside it is moved at the
    # loop head unless every path back there assigned it again. The body is
    # checked once with the entry state and, while that grows the set of
    # moved bindings at the head, again with the merged head state. Paths
    # that `break` don't reach the head; they join the state after the loop.

    def _snapshot(self) -> Snapshot:
        """Every visible binding's state (and its moved-out fields), keyed by
        binding (not name, so a shadowing binding in an inner scope can't
        stand in for an outer one)."""
        out: Snapshot = {}
        scope = self.scope
        while scope:
            for info in scope.vars.values():
                out.setdefault(
                    id(info), (info, info.state, info.move_span, dict(info.moved_fields)))
            scope = scope.parent
        return out

    def _restore(self, snap) -> None:
        for info, state, span, fields in snap.values():
            info.state = state
            info.move_span = span
            info.moved_fields = dict(fields)

    @staticmethod
    def _join(paths) -> Snapshot:
        """Where `paths` meet: each binding of the first path, moved if it is
        moved on any of them, else in the first path's state; a field is
        moved out if it is on any of them."""
        out = dict(paths[0])
        for key, (info, state, span, fields) in paths[0].items():
            merged = dict(fields)
            for p in paths:
                got = p.get(key)
                if got is None:
                    continue
                for fname, fspan in got[3].items():
                    merged.setdefault(fname, fspan)
            for p in paths:
                got = p.get(key)
                if got is not None and got[1] == VarState.MOVED:
                    state, span = VarState.MOVED, got[2]
                    break
            out[key] = (info, state, span, merged)
        return out

    @staticmethod
    def _moved_keys(snap) -> Set:
        out: Set = {k for k, (_i, st, _s, _f) in snap.items() if st == VarState.MOVED}
        out |= {(k, f) for k, (_i, _st, _s, fields) in snap.items() for f in fields}
        return out

    def _run_loop_defers(self) -> None:
        """break / continue: the defers of the blocks inside the loop."""
        if self._loop_defer_depth:
            self._run_defers(self._loop_defer_depth[-1])

    def _note_loop_exit(self, kind: str) -> None:
        if self._loops:
            self._loops[-1][kind].append(self._snapshot())

    def _check_loop(self, iteration) -> None:
        """Check a loop whose one iteration `iteration()` checks (returning
        True if the body never falls through to the loop head)."""
        head = self._snapshot()
        for _ in range(8):           # moves only grow; 8 passes is plenty
            self._restore(head)
            frame = {'breaks': [], 'continues': []}
            self._loops.append(frame)
            self._loop_defer_depth.append(len(self._defers))
            try:
                done = iteration()
            finally:
                self._loop_defer_depth.pop()
            self._loops.pop()
            back = list(frame['continues'])
            if not done:
                back.append(self._snapshot())
            new_head = self._join([head] + back)
            if self._moved_keys(new_head) == self._moved_keys(head):
                break
            head = new_head
        # Leaving: the condition failed at the head, or a `break`.
        self._restore(self._join([head] + frame['breaks']))

    # ---- expressions ---------------------------------------------------------

    def _check_expr(self, expr: rast.Expr, is_move_context: bool = False):
        """Check an expression for ownership violations, by its kind
        (EXPR_CHECKS).

        Args:
            expr: The expression to check
            is_move_context: True if this expression's value will be moved
        """
        check = self.EXPR_CHECKS.get(type(expr))
        if check is not None:
            check(self, expr, is_move_context)

    def _expr_ident(self, expr: rast.Ident, is_move_context: bool) -> None:
        var_info = self.scope.lookup(expr.name)
        if not var_info:
            if is_move_context:
                self._check_global_move_out(expr)
            return
        # Check if variable has been moved
        if var_info.state == VarState.MOVED:
            self.errors.append(OwnershipError(
                f"use of moved value: `{expr.name}` (moved at {var_info.move_span})",
                expr.span, after_move=True
            ))
            return
        # Used whole after a field was moved out (AGAST #2171).
        if var_info.moved_fields:
            fname, fspan = next(iter(var_info.moved_fields.items()))
            self.errors.append(OwnershipError(
                f"use of moved value: `{expr.name}.{fname}` (moved at {fspan})",
                expr.span, after_move=True
            ))
            return

        # If this is a move context and type is not Copy, mark as moved.
        # A by-value `name: T` parameter (Borrow.CONST) owns its value
        # (§13.2) and moves like any binding (AGAST #2157). A `name:& T`
        # parameter's value stays the caller's, so it can't move
        # (AGAST #2231).
        if is_move_context and not self._is_copy_type(var_info.ritz_type):
            if var_info.borrow == rast.Borrow.MUTABLE:
                self._reject_move_out(expr.span)
                return
            var_info.state = VarState.MOVED
            var_info.move_span = expr.span
            # The emitter clears the binding's drop flag here.
            expr.moves_binding = True

    def _expr_binop(self, expr: rast.BinOp, is_move_context: bool) -> None:
        # Binary ops don't move their operands (they borrow or copy)
        self._check_expr(expr.left, is_move_context=False)
        self._check_expr(expr.right, is_move_context=False)

    def _expr_unary(self, expr: rast.UnaryOp, is_move_context: bool) -> None:
        if expr.op in ('&', '@'):
            # Shared borrow - check the operand exists and isn't moved
            # Both legacy & and RERITZ @ are immutable borrows
            self._check_borrow(expr.operand, mutable=False, span=expr.span)
        elif expr.op in ('&mut', '@&'):
            # Mutable borrow - check no other borrows exist
            # Both legacy &mut and RERITZ @& are mutable borrows
            self._check_borrow(expr.operand, mutable=True, span=expr.span)
        elif expr.op == '*':
            # Dereference - check the pointer expression
            self._check_expr(expr.operand, is_move_context=False)
            if is_move_context and self._through_reference(expr) \
                    and self.types.is_move_only(self._place_type(expr)):
                self._reject_move_out(expr.span)
        else:
            self._check_expr(expr.operand, is_move_context=False)

    def _expr_call(self, expr: rast.Call, is_move_context: bool) -> None:
        if isinstance(expr.func, rast.Ident) and expr.func.name == 'sizeof':
            # sizeof's operand is never evaluated: it neither moves nor
            # uses its operand (AGAST #2124; `sizeof(key)` used to move key).
            return
        # Function arguments are moved (unless Copy)
        # Borrows created for arguments are released after the call completes
        # (unless the reference escapes, which we don't track yet)
        self._check_expr(expr.func, is_move_context=False)

        # Save borrow states before processing arguments
        borrow_states_before = self._save_borrow_states()

        params = (self.fn_params.get(expr.func.name)
                  if isinstance(expr.func, rast.Ident) else None)
        self._in_args += 1
        for i, arg in enumerate(expr.args):
            param = params[i] if params and i < len(params) else None
            self._check_expr(arg, is_move_context=not _is_lending_param(param))
            self._check_place_borrow(arg, param)
        self._in_args -= 1

        # Release borrows that were created for this call
        # (borrows don't outlive the call unless stored somewhere)
        self._restore_borrow_states(borrow_states_before)
        self._mark_temporary(expr, is_move_context)

    def _expr_method_call(self, expr: rast.MethodCall, is_move_context: bool) -> None:
        # The receiver is borrowed (auto-ref) unless the method takes it
        # by value (AGAST #2239). An argument moves when every method of
        # that name takes it by value.
        by_value = self._method_takes_self(expr) or self._takes_place_behind(expr)
        self._check_expr(expr.expr, is_move_context=by_value)
        self._check_ref_receiver(expr)
        # A receiver taken `self: @&T` or `self:& T` is a mutable borrow of
        # its place.
        if self._lends_self_mut(expr) and self._holds_by_value(expr.expr):
            self._check_mut_use(self._loan_place(expr.expr), expr.expr.span, "borrow")
        if not self._method_lends_self(expr):
            # A temporary receiver taken by value is moved, not dropped.
            self._unmark_temporary(expr.expr)
        borrow_states_before = self._save_borrow_states()
        # `E.V(args)` builds a variant, which owns its payload.
        is_variant = self.types.variant_value_type(
            expr, lambda n: self.scope.lookup(n) is not None) is not None
        self._in_args += 1
        for i, arg in enumerate(expr.args):
            self._check_expr(arg, is_move_context=is_variant or self._method_arg_moves(expr, i))
            self._check_place_borrow(arg, self._method_param(expr, i))
        self._in_args -= 1
        self._restore_borrow_states(borrow_states_before)
        self._mark_temporary(expr, is_move_context)

    def _expr_grouped(self, expr: rast.Grouped, is_move_context: bool) -> None:
        self._check_expr(expr.expr, is_move_context=is_move_context)

    def _expr_field(self, expr: rast.Field, is_move_context: bool) -> None:
        if is_move_context and self._through_deref(expr) \
                and self.types.is_move_only(self._part_type(
                    self.types.resolve(self._loan_type(expr.expr)), expr.field)):
            # `deref` lends the T: its move-only field can't be taken (§7.7).
            self._check_expr(expr.expr, is_move_context=False)
            self._reject_move_out(expr.span)
        elif self._numbered_struct_field(expr) is not None:
            # `h.0` of a struct: no such field, in any position (AGAST #3233).
            # The one error: it's no use of `h`, so what moved out of `h`
            # doesn't add a second.
            self.errors.append(OwnershipError(
                deref_rules.no_field(self._numbered_struct_field(expr), expr.field),
                expr.name_span or expr.span))
        elif self._field_owner(expr) is not None:
            self._check_owned_field(expr, self._field_owner(expr), is_move_context)
        else:
            self._check_unowned_field(expr, is_move_context)

    def _check_unowned_field(self, expr: rast.Field, is_move_context: bool) -> None:
        """A field of something no binding owns here: a reference's referent,
        an element, a global or a temporary."""
        # Field access doesn't move the struct (unless the result is moved)
        self._check_expr(expr.expr, is_move_context=False)
        if not is_move_context:
            return
        if self._through_reference(expr):
            # `p[i].f`: _field_path_type doesn't type an element (#2444).
            if self.types.is_move_only(self._field_path_type(expr) or self._place_type(expr)):
                self._reject_move_out(expr.span)
        elif self._moves_out_of_element(expr):
            self.errors.append(OwnershipError(array_rules.MOVE_OUT_OF_ELEMENT, expr.span))
        elif self._check_global_move_out(expr):
            pass
        elif self.types.is_move_only(self._field_path_type(expr)):
            # Moving a move-only field out of a temporary: the rest of
            # the temporary isn't dropped either (no partial drops).
            while isinstance(expr, rast.Field):
                expr = expr.expr
            self._unmark_temporary(expr)

    def _expr_index(self, expr: rast.Index, is_move_context: bool) -> None:
        self._check_expr(expr.expr, is_move_context=False)
        self._check_expr(expr.index, is_move_context=False)
        if is_move_context and self._through_reference(expr) \
                and self.types.is_move_only(self._place_type(expr)):
            self._reject_move_out(expr.span)
        elif is_move_context and self._moves_out_of_element(expr):
            self.errors.append(OwnershipError(array_rules.MOVE_OUT_OF_ELEMENT, expr.span))

    def _expr_struct_lit(self, expr: rast.StructLit, is_move_context: bool) -> None:
        for _, value in expr.fields:
            self._check_expr(value, is_move_context=True)
        self._mark_temporary(expr, is_move_context)

    def _expr_elements(self, expr, is_move_context: bool) -> None:
        """An array or tuple literal owns its elements, wherever the literal
        itself goes (AGAST #2238)."""
        for element in expr.elements:
            self._check_expr(element, is_move_context=True)
        self._mark_temporary(expr, is_move_context)

    def _expr_array_fill(self, expr: rast.ArrayFill, is_move_context: bool) -> None:
        # `[v; n]` owns its value like a literal owns its elements, so
        # `[t; 2]` with `t:& Res` moves out of the reference (AGAST #2948).
        self._check_expr(expr.value, is_move_context=True)
        # It copies that one value into each element: n > 1 of a
        # move-only one would drop it n times (AGAST #2963).
        if expr.count > 1 and self.types.is_move_only(self._fill_value_type(expr.value)):
            self.errors.append(OwnershipError(array_rules.FILL_MOVE_ONLY, expr.span))

    def _expr_match(self, expr: rast.Match, is_move_context: bool) -> None:
        # What a reference reaches stays its owner's, and an element its
        # array's (#2268): matching it only reads.
        reads = (self._through_reference(expr.expr)
                 or self._element_root(expr.expr) is not None)
        self._check_expr(expr.expr, is_move_context=not reads)
        # The match owns a scrutinee it moved (AGAST #2177, ritz1 #2174).
        owned = self._owned_scrutinee_type(expr.expr)
        expr.owns_scrutinee = owned
        lent = None if owned is not None else self._lent_scrutinee_type(expr.expr)
        # Each arm starts from the state before the match. After it, a
        # binding is moved if an arm that falls through moved it; an arm
        # that leaves (`break`, `return`, ...) took its moves with it.
        before = self._snapshot()
        outs = []
        mark = len(self._arg_loans)
        for arm in expr.arms:
            self._restore(before)
            self._release_arg_loans(mark)
            if not self._check_arm(expr, arm, owned, lent, is_move_context):
                outs.append(self._snapshot())
        if outs:
            self._restore(self._join(outs))

    def _check_arm(self, match: rast.Match, arm: rast.MatchArm, owned, lent,
                   is_move_context: bool) -> bool:
        """One arm of `match`, in a scope of its own; True if it leaves."""
        self._push_scope()
        # Pattern bindings
        self._check_pattern(arm.pattern)
        if owned is not None:
            self._own_payload(arm, owned)
        elif lent is not None:
            self._lend_payload(arm, lent)
        if isinstance(arm.body, rast.Block):
            left = self._check_block(arm.body, value_used=is_move_context)
        else:
            self._check_expr(arm.body, is_move_context=is_move_context)
            left = isinstance(arm.body, (rast.BreakExpr, rast.ContinueExpr, rast.ReturnExpr))
        self._note_arm_type(match, arm)
        self._pop_scope()
        return left

    def _expr_break(self, expr: rast.BreakExpr, is_move_context: bool) -> None:
        self._run_loop_defers()
        self._note_loop_exit('breaks')

    def _expr_continue(self, expr: rast.ContinueExpr, is_move_context: bool) -> None:
        self._run_loop_defers()
        self._note_loop_exit('continues')

    def _expr_return(self, expr: rast.ReturnExpr, is_move_context: bool) -> None:
        if expr.value is not None:
            self._check_expr(expr.value, is_move_context=True)
        self._run_defers(0)

    def _expr_try(self, expr: rast.TryOp, is_move_context: bool) -> None:
        self._check_expr(expr.expr, is_move_context=is_move_context)
        # The Err path returns through every block's defers; the Ok path
        # goes on, so their moves don't carry past the `?`.
        if self._defers and any(self._defers):
            snap = self._snapshot()
            self._run_defers(0)
            self._restore(snap)

    def _expr_cast(self, expr: rast.Cast, is_move_context: bool) -> None:
        # `v as T` hands its operand's value on: it moves wherever the
        # cast does (AGAST #2948; `t as Res` with `t:& Res` copied out).
        self._check_ref_cast(expr)
        self._check_expr(expr.expr, is_move_context=is_move_context)

    def _expr_if(self, expr: rast.If, is_move_context: bool) -> None:
        # If expression with proper control flow handling:
        # - Save state before branches
        # - If a branch returns, its moves don't affect code after the if
        # - If both branches return, code after if is dead
        # - For if/else where neither returns, each branch checks independently
        self._check_expr(expr.cond, is_move_context=False)

        # Save state before entering branches
        saved_states = self.scope.save_states()

        # Check then branch
        self._push_scope()
        then_returns = self._check_block(expr.then_block, value_used=is_move_context)
        self._pop_scope()

        # Save state after then branch (captures moves in then)
        states_after_then = self.scope.save_states()

        if not expr.else_block:
            # No else branch - if then returns, restore pre-if state
            # (the non-return path is when condition is false)
            if then_returns:
                self.scope.restore_states(saved_states)
            # If then doesn't return, merge: either then path moved or condition was false
            # Conservative: if moved in then, mark as potentially moved
            return

        # Always restore to pre-if state for else branch
        # (else branch doesn't see moves from then branch)
        self.scope.restore_states(saved_states)

        self._push_scope()
        else_returns = self._check_block(expr.else_block, value_used=is_move_context)
        self._pop_scope()

        # After if/else, merge states:
        # - If both return, code after is dead, state doesn't matter
        # - If only then returns, keep state from else (the current one)
        # - If only else returns, keep state from then (restore after_then)
        # - If neither returns, conservatively mark moved in EITHER branch as moved
        if then_returns:
            pass
        elif else_returns:
            self.scope.restore_states(states_after_then)
        else:
            self._merge_branches(states_after_then)

    def _merge_branches(self, states_after_then) -> None:
        """Neither branch of an if/else returned: a binding moved in either
        is moved after it, and so is a field moved out in either (AGAST
        #2171).  The current state is the else branch's."""
        states_after_else = self.scope.save_states()
        for name, (then_state, then_move_span, then_fields) in states_after_then.items():
            else_info = states_after_else.get(name)
            if not else_info:
                continue
            else_state, else_move_span, else_fields = else_info
            var_info = self.scope.lookup(name)
            if not var_info:
                continue
            # If moved in either branch, mark as moved
            if then_state == VarState.MOVED or else_state == VarState.MOVED:
                var_info.state = VarState.MOVED
                var_info.move_span = then_move_span or else_move_span
            merged = dict(then_fields)
            for fname, fspan in else_fields.items():
                merged.setdefault(fname, fspan)
            var_info.moved_fields = merged

    def _expr_block(self, expr: rast.Block, is_move_context: bool) -> None:
        self._push_scope()
        self._check_block(expr)
        self._pop_scope()

    STMT_CHECKS = {
        rast.VarStmt: _stmt_var,
        rast.LetStmt: _stmt_let,
        rast.LetTupleStmt: _stmt_let_tuple,
        rast.ExprStmt: _stmt_expr,
        rast.AssertStmt: _stmt_assert,
        rast.ReturnStmt: _stmt_return,
        rast.DeferStmt: _stmt_defer,
        rast.AssignStmt: _stmt_assign,
        rast.AsmStmt: _stmt_asm,
        rast.WhileStmt: _stmt_while,
        rast.ForStmt: _stmt_for,
        rast.BreakStmt: _stmt_break,
        rast.ContinueStmt: _stmt_continue,
    }

    EXPR_CHECKS = {
        rast.Ident: _expr_ident,
        rast.BinOp: _expr_binop,
        rast.UnaryOp: _expr_unary,
        rast.Call: _expr_call,
        rast.MethodCall: _expr_method_call,
        rast.Grouped: _expr_grouped,
        rast.Field: _expr_field,
        rast.Index: _expr_index,
        rast.StructLit: _expr_struct_lit,
        rast.ArrayLit: _expr_elements,
        rast.TupleLit: _expr_elements,
        rast.ArrayFill: _expr_array_fill,
        rast.Match: _expr_match,
        rast.BreakExpr: _expr_break,
        rast.ContinueExpr: _expr_continue,
        rast.ReturnExpr: _expr_return,
        rast.TryOp: _expr_try,
        rast.Cast: _expr_cast,
        rast.If: _expr_if,
        rast.Block: _expr_block,
    }
