"""
Move and Borrow Checker for ritz0

Phase 9: Ownership & Borrowing

Implements the ownership model of LANGUAGE_SPEC §13:
- Move-only types (Drop, or containing a Drop) move; every other type
  copies (use-after-move = error)
- Borrows: &T (shared), &mut T (exclusive)
- Aliased mutable borrows are disallowed

This runs after parsing/name resolution, before code generation.
"""

import copy
from typing import Dict, Set, List, Optional, Tuple
import array_rules
import ref_rules
from metadata import type_to_string
import ritz_ast as rast
import typed
# The state lives in move_state.py, the per-node-kind walk in move_walk.py
# (AGAST #3449); every name move_state defines is still importable from here.
from move_state import (  # noqa: F401 (re-exported)
    OwnershipError, VarState, Loan, VarInfo, Scope, field_path, path_within,
    _is_lending_param, _element_of, _lends_mut, MoveTypes, _type_key, _subst,
)
from move_walk import MoveWalk


class MoveChecker(MoveWalk):
    """
    Checks ownership and borrowing rules.

    Rules enforced:
    1. Use-after-move: Cannot use a variable after moving it
    2. Aliased mutable borrow: Cannot have multiple &mut or &mut with &
    3. Borrow checker: Borrows must not outlive the borrowed value

    For now, we implement a simplified version:
    - Track move state per variable
    - Detect use-after-move
    - Detect multiple mutable borrows (within same scope)
    """

    def __init__(self):
        self.scope: Scope = Scope()
        self.errors: List[OwnershipError] = []
        # Track function parameters (they're owned at function start)
        self.current_fn_name: Optional[str] = None
        # Type aliases: name -> underlying type
        self.type_aliases: Dict[str, rast.Type] = {}
        # Each expression's type, from the typing pass (typed.py): the
        # kinds in typed.MOVE_CHECKER_READS come from here.
        self.typed: Optional[typed.Typed] = None
        # The fn being checked: the table is read in it (typed.Typed).
        self._body: Optional[rast.FnDef] = None
        # Function parameters: name -> params, so an argument lent to an
        # `@T` / `*T` / `:&` parameter (auto-borrow) isn't counted as a move.
        self.fn_params: Dict[str, List[rast.Param]] = {}
        # Method name -> every impl's FnDef of that name.
        self.methods: Dict[str, List[rast.FnDef]] = {}
        # (type name, method name) -> that type's FnDefs of that name.
        self.type_methods: Dict[Tuple[str, str], List[rast.FnDef]] = {}
        # id(method FnDef) -> its impl block, for the impl's type parameters.
        self.method_impl: Dict[int, rast.ImplBlock] = {}
        self.types: Optional[MoveTypes] = None
        # Module-level `var` name -> its declared type (AGAST #2269). Scope
        # sees only locals and parameters; a local of the same name shadows.
        self.globals: Dict[str, rast.Type] = {}
        # Per enclosing loop: the binding states at each `break` and
        # `continue` (AGAST #2161, _check_loop).
        self._loops: List[Dict[str, list]] = []
        # (binding name, field path) pairs the current function moves out of
        # a binding (AGAST #2171, #2232); the emitter gives those drop flags.
        self._field_moves: Set[Tuple[str, str]] = set()
        self.current_ret_type: Optional[rast.Type] = None
        # The loans call arguments are making, which no binding holds: each
        # ends with its call (_restore_borrow_states), or sooner with the
        # statement or arm it's in (AGAST #2438). Outside a call's arguments a
        # borrow nothing holds lends nothing, as on ritz1.
        self._arg_loans: List[Tuple[VarInfo, Loan]] = []
        self._in_args = 0
        # `defer` (LANGUAGE_SPEC §13.7): per open block, its (DeferStmt, the
        # Scope at the defer) in source order; per open loop, how many block
        # frames were open at it. A deferred statement is checked as if it
        # were written at each exit it runs on (_run_defers).
        self._defers: List[List[Tuple[rast.DeferStmt, Scope]]] = []
        self._loop_defer_depth: List[int] = []
        # Per open loop: the scope outside its body, where a `break` or
        # `continue` stops dropping (AGAST #4096).
        self._loop_scopes: List[Scope] = []
        # Defers already refused, so one reached by several exits is one error.
        self._refused_defers: Set[int] = set()

    def check(self, module: rast.Module) -> List[OwnershipError]:
        """Check ownership rules for a module.

        Returns a list of errors (empty if all rules satisfied). As a side
        effect, every Ident that moves a move-only binding gets
        `moves_binding = True`; the emitter clears that binding's drop flag
        there, so a moved-from binding is never dropped (§13.6). Likewise a
        Field that moves a move-only field out of a binding gets
        `moves_field = True`, an assignment target that gives it back
        `reowns_field = True`, and each FnDef `field_moves`, the (binding,
        field path) pairs it moves out (AGAST #2171, #2232): the emitter
        keeps a drop flag per such path, so the binding's drop skips it.
        """
        self.errors = []
        self._collect(module)
        self.typed = typed.typed_of(module)
        module.moves_annotated = True

        # Second pass: check functions and impl methods
        for item in module.items:
            if isinstance(item, rast.FnDef):
                self._check_fn(item)
            elif isinstance(item, rast.ImplBlock):
                for m in item.methods:
                    self._check_fn(m)

        self._drop_repeats()
        return self.errors

    def check_instances(self, module: rast.Module) -> List[OwnershipError]:
        """Moves out of a reference, and uses or borrows of a moved value, in
        a monomorphised module's generic instances. `check` saw those bodies
        with `T` a copy type (AGAST #2263), so an instance at a move-only `T`
        is where `*p` turns into a move and where `let b: T = x` after
        `let a: T = x` uses a moved `x` (AGAST #2921, as ritz1 refuses it).
        Each is checked on a copy, for its errors only. The marks the emitter
        reads come from its own `check` of the monomorphised module (that
        module is new, so not yet `moves_annotated`), which sees each
        instance at its concrete `T` (AGAST #2263)."""
        self.errors = []
        self._collect(module)
        fns = [item for item in module.items if isinstance(item, rast.FnDef)]
        for item in module.items:
            if isinstance(item, rast.ImplBlock):
                fns.extend(item.methods)
        impls = {id(m): item for item in module.items
                 if isinstance(item, rast.ImplBlock) for m in item.methods}
        for fn in fns:
            if any(self.types.is_move_only(a) for a in getattr(fn, 'instance_args', ())):
                body = copy.deepcopy(fn)
                # The copy's own types: the table holds the original's nodes.
                self.typed = typed.type_bodies(module, [(body, impls.get(id(fn)))])
                self._check_fn(body)
        kept = (ref_rules.MOVE_OUT_OF_REF, array_rules.FILL_MOVE_ONLY,
                array_rules.MOVE_OUT_OF_ELEMENT)
        self.errors = [e for e in self.errors if e.reason in kept or e.after_move]
        self._drop_repeats()
        return self.errors

    def _collect(self, module: rast.Module) -> None:
        """Type aliases and function signatures."""
        self.types = MoveTypes(module)
        for item in module.items:
            if isinstance(item, rast.TypeAlias):
                self.type_aliases[item.name] = item.target
            elif isinstance(item, rast.VarDef) and item.type is not None:
                self.globals[item.name] = item.type
            elif isinstance(item, (rast.FnDef, rast.ExternFn)):
                self.fn_params[item.name] = list(item.params)
            elif isinstance(item, rast.ImplBlock):
                for m in item.methods:
                    self._collect_method(item, m)

    def _collect_method(self, impl: rast.ImplBlock, m: rast.FnDef) -> None:
        """An impl's method, for _collect; `Drop.drop` must lend `self`."""
        self.methods.setdefault(m.name, []).append(m)
        self.type_methods.setdefault((impl.type_name, m.name), []).append(m)
        self.method_impl[id(m)] = impl
        if impl.trait_name == 'Drop' and m.name == 'drop' and m.params \
                and m.params[0].name == 'self' and not _is_lending_param(m.params[0]):
            self.errors.append(OwnershipError(ref_rules.DROP_BY_VALUE, m.params[0].span))

    def _drop_repeats(self) -> None:
        """A loop body checked twice (_check_loop) reports its errors twice,
        and so do two instances of one generic body."""
        seen = set()
        unique = []
        for err in self.errors:
            if str(err) not in seen:
                seen.add(str(err))
                unique.append(err)
        self.errors = unique

    def _is_copy_type(self, ty: rast.Type) -> bool:
        """A type is Copy unless it is move-only (LANGUAGE_SPEC §13.1)."""
        return not self.types.is_move_only(ty)

    def _infer_expr_type(self, expr: rast.Expr) -> rast.Type:
        """`expr`'s type for ownership checking: the typing pass's, for the
        kinds it answers (EXPR_TYPES); `unknown` for any other kind.

        Only move-vs-copy (LANGUAGE_SPEC §13.1) and a few shapes (an array, a
        tuple, a struct to destructure) are read from it."""
        infer = self.EXPR_TYPES.get(type(expr))
        if infer is None:
            return rast.NamedType(expr.span, 'unknown', [])
        return infer(self, expr)

    def _type_from_table(self, expr: rast.Expr) -> rast.Type:
        """The typing pass's type for `expr` (typed.MOVE_CHECKER_READS), in
        the body being checked (typed.Typed); `unknown` where the pass
        didn't type it there (a body it skipped)."""
        ty = (self.typed.type_of(expr, within=self._body)
              if self.typed is not None else None)
        return ty if ty is not None else rast.NamedType(expr.span, 'unknown', [])

    # Every kind _infer_expr_type types, by class (see move_walk.py's
    # EXPR_CHECKS on why `type(expr)` is enough): all from the typing pass
    # (AGAST #3448, #3553, #4065).  Index is deliberately absent: `a[i]`
    # stays unknown (#2268).
    EXPR_TYPES = dict.fromkeys(typed.MOVE_CHECKER_READS, _type_from_table)

    def _destructured_types(self, value: rast.Expr, n: int) -> List[rast.Type]:
        """The types `let (x1, ..., xn) = value` gives its n names: the
        tuple's elements, or a struct's fields in declaration order (as
        the emitter destructures it). `unknown` where neither fits."""
        ty = self.types.resolve(self._infer_expr_type(value))
        if isinstance(ty, rast.TupleType) and len(ty.elements) == n:
            return list(ty.elements)
        if isinstance(ty, rast.NamedType):
            fields = self.types.struct_fields(ty)
            if len(fields) == n:
                return [t for _name, t in fields]
        return [rast.NamedType(value.span, 'unknown', []) for _ in range(n)]

    def _push_scope(self):
        """Enter a new scope."""
        self.scope = Scope(parent=self.scope)

    def _pop_scope(self):
        """Exit current scope. The loans its bindings hold end here: a loan
        lasts to the end of its holder's block (AGAST #2438)."""
        gone = {id(info) for info in self.scope.vars.values()}
        scope = self.scope.parent
        while scope:
            for info in scope.vars.values():
                info.borrows = [
                    b for b in info.borrows if b.holder is None or id(b.holder) not in gone]
            scope = scope.parent
        if self.scope.parent:
            self.scope = self.scope.parent

    def _save_borrow_states(self) -> Dict[int, Tuple[VarInfo, List[Loan]]]:
        """Every visible binding's loans, keyed by binding."""
        states = {}
        scope = self.scope
        while scope:
            for info in scope.vars.values():
                states.setdefault(id(info), (info, list(info.borrows)))
            scope = scope.parent
        return states

    def _restore_borrow_states(self, saved: Dict[int, Tuple[VarInfo, List[Loan]]]):
        """End the loans made since `saved`: a call's arguments' (the loans
        don't outlive the call). Moves stay."""
        for info, borrows in saved.values():
            info.borrows = list(borrows)

    # ---- loans (LANGUAGE_SPEC §13.5, LARB rulings R11 and R11a, AGAST #2438) -
    #
    # A borrow is of a place: a root binding and its field and index steps.
    # Two places overlap when one's path is a prefix of the other's (field
    # names must match; any two indexes are equal). While a binding holds an
    # `@T` of a place, or within one call's arguments, a mutable borrow of an
    # overlapping place is an error; while it holds an `@&T`, any borrow is.
    # The mutable borrows are `@&p`, `p` into a `:&` param, a receiver taken
    # `self: @&T` or `self:& T`, and a write into p's own storage. ritz1's twin
    # is the loan half of ref_check.ritz, and
    # test_borrow_conflict_all_compilers.py holds the three compilers to one
    # table.

    Place = Tuple[str, Tuple[str, ...]]

    def _steps(self, place: rast.Expr):
        """`place`'s root expression and its steps, root first. A field reached
        through `Deref` takes a `*` step first (§7.7, R17 rule 6)."""
        steps: List[str] = []
        while True:
            if isinstance(place, rast.Grouped):
                place = place.expr
            elif isinstance(place, rast.Field):
                steps.append(place.field)
                if self._through_deref(place):
                    steps.append('*')
                place = place.expr
            elif isinstance(place, rast.Index):
                steps.append('[]')
                place = place.expr
            else:
                return place, tuple(reversed(steps))

    def _loan_root(self, place: rast.Expr) -> Optional[str]:
        """The binding `@place` borrows (see _loan_place)."""
        found = self._loan_place(place)
        return found[0] if found else None

    def _loan_place(self, place: rast.Expr) -> Optional['MoveChecker.Place']:
        """The place `@place` borrows: a binding and the steps `place` takes
        from it by fields and indexes with no pointer or reference on the way,
        so `@c.x` and `@vs[0]` borrow `c.x` and `vs[]`. None if there's none,
        or the type on the way is unknown."""
        top = place
        while True:
            if isinstance(place, rast.Grouped):
                place = place.expr
            elif isinstance(place, rast.Ident):
                if self.scope.lookup(place.name) is None:
                    return None
                return place.name, self._steps(top)[1]
            elif isinstance(place, (rast.Field, rast.Index)):
                if isinstance(place, rast.Index) and isinstance(place.index, rast.Range):
                    return None
                if not self._holds_by_value(place.expr):
                    return None
                place = place.expr
            else:
                return None

    def _write_place(self, target: rast.Expr) -> Optional['MoveChecker.Place']:
        """The place a store to `target` writes: _loan_place's, or `m[k].f…`
        when `m` is a struct indexed through `IndexMut` (§7.8, R11a, AGAST
        #4160), so `g[2].v = 5` writes `g[_].v` as `a[2].v = 5` does `a[_].v`.
        Each field's owner must be a struct held by value: a store through a
        pointer field writes outside `m`. ritz1's twin is ref_loan.ritz
        rl_index_step for SI_USE_FIELD_STORE."""
        found = self._loan_place(target)
        if found is not None:
            return found
        fields: List[str] = []
        e = target
        while isinstance(e, (rast.Grouped, rast.Field)):
            if isinstance(e, rast.Field):
                fields.append(e.field)
            e = e.expr
        if not fields or not isinstance(e, rast.Index) or isinstance(e.index, rast.Range):
            return None
        owner = self.types.resolve(self._loan_type(e.expr))
        if not isinstance(owner, rast.NamedType):
            return None
        held = self.types.index_mut_target(owner)
        base = self._loan_place(e) if held is not None else None
        if base is None:
            return None
        for name in reversed(fields):
            held = self.types.resolve(held)
            if not (isinstance(held, rast.NamedType) and held.name in self.types.structs
                    and any(n == name for n, _ in self.types.struct_fields(held))):
                return None
            held = self._part_type(held, name)
        return base[0], base[1] + tuple(reversed(fields))

    def _loan_type(self, expr: rast.Expr) -> Optional[rast.Type]:
        """_place_type, also through a Vec's element (`vs[1].a`), for the steps
        of a place. Only the loan check reads it. ritz1's is ref_loan_ty."""
        if isinstance(expr, rast.Grouped):
            return self._loan_type(expr.expr)
        if isinstance(expr, rast.Index):
            held = self.types.resolve(self._loan_type(expr.expr))
            if (isinstance(held, rast.NamedType) and held.name == 'Vec'
                    and len(held.args) == 1):
                return held.args[0]
        elif isinstance(expr, rast.Field):
            base = self.types.resolve(self._loan_type(expr.expr))
            if isinstance(base, rast.TupleType) or (
                    isinstance(base, rast.NamedType) and base.name != 'unknown'):
                return self._part_type(base, expr.field)
        return self._place_type(expr)

    def _holds_by_value(self, base: rast.Expr) -> bool:
        """Is `base` a value, not a pointer or reference to one?"""
        held = self.types.resolve(self._loan_type(base))
        if held is None or isinstance(held, (rast.PtrType, rast.RefType)):
            return False
        return not (isinstance(held, rast.NamedType) and held.name == 'unknown')

    @staticmethod
    def _overlap(a: Tuple[str, ...], b: Tuple[str, ...]) -> bool:
        """Is one path a prefix of the other? Two `*` steps (through `Deref`)
        are equal; a `*` step overlaps any own field, which may re-aim it."""
        for x, y in zip(a, b):
            if x != y:
                return '*' in (x, y)
        return True

    @staticmethod
    def _place_str(name: str, path: Tuple[str, ...]) -> str:
        return name + ''.join(
            '[_]' if s == '[]' else '' if s == '*' else f'.{s}' for s in path)

    def _through_deref(self, place: rast.Field) -> bool:
        """Is `place` a field its struct reaches through `Deref` (§7.7)?"""
        owner = self.types.resolve(self._loan_type(place.expr))
        if not isinstance(owner, rast.NamedType) or owner.name not in self.types.structs:
            return False
        if any(n == place.field for n, _ in self.types.struct_fields(owner)):
            return False
        return self.types.deref_target(owner) is not None

    def _conflict(self, info: VarInfo, path: Tuple[str, ...],
                  mutable: bool) -> Optional[Loan]:
        """The loan on `info` a new borrow of `path` (`mutable` or not)
        conflicts with: an overlapping mutable loan first, else, for a mutable
        borrow, an overlapping shared one."""
        near = [b for b in info.borrows if self._overlap(b.path, path)
                and (not b.outer or len(path) <= len(b.path))]
        for b in near:
            if b.mutable:
                return b
        return near[0] if mutable and near else None

    def _report(self, name: str, path: Tuple[str, ...], loan: Loan,
                what: str, span) -> None:
        """`what` is "assign", "move", "mutable" or "immutable"."""
        here = self._place_str(name, path)
        held = self._place_str(name, loan.path)
        kind = "mutable" if loan.mutable else "immutable"
        if what == "assign":
            head = f"cannot assign to `{here}`"
        elif what == "move":
            head = f"cannot move out of `{here}`"
        else:
            head = f"cannot borrow `{here}` as {what}"
        self.errors.append(OwnershipError(
            f"{head} - `{held}` is already borrowed as {kind}", span))

    def _check_mut_use(self, place: Optional['MoveChecker.Place'], span, verb: str) -> None:
        """A mutable borrow of `place` that ends with the statement: a receiver
        (verb "borrow") or a write (verb "assign")."""
        info = self.scope.lookup(place[0]) if place is not None else None
        if info is None:
            return
        loan = self._conflict(info, place[1], mutable=True)
        if loan is not None:
            self._report(place[0], place[1], loan,
                         "assign" if verb == "assign" else "mutable", span)

    def _check_move_borrowed(self, name: str, info: VarInfo, path: Tuple[str, ...], span):
        """A move of `name`'s `path` conflicts with any live loan of an
        overlapping place, as a mutable borrow would (LARB R57, R11a). True if
        it was reported."""
        loan = self._conflict(info, path, mutable=True)
        if loan is None:
            return False
        self._report(name, path, loan, "move", span)
        return True

    def _span_view_base(self, value: rast.Expr) -> Optional[rast.Expr]:
        """`v` of `v[a..b]` when `v` is a Vec or String held by value: in a Span
        slot the slice is a view of v's storage, not a copy (§7.8), so it lends
        v (LARB R57). A Span's slice views what the Span does, not the Span."""
        if not (isinstance(value, rast.Index) and isinstance(value.index, rast.Range)):
            return None
        held = self.types.resolve(self._loan_type(value.expr))
        if isinstance(held, rast.NamedType) and (
                held.name in ('Vec', 'String') or held.name.startswith('Vec$')):
            return value.expr
        return None

    def _is_span_slot(self, declared: Optional[rast.Type]) -> bool:
        held = self.types.resolve(declared) if declared is not None else None
        return isinstance(held, rast.NamedType) and (
            held.name == 'Span' or held.name.startswith('Span$'))

    def _held_borrows(self, value: Optional[rast.Expr],
                      span_slot: bool = False) -> List[Tuple[rast.Expr, rast.Expr, bool]]:
        """What a declaration's binding borrows, as (expression, place,
        mutable): an `@place` or `@&place` its value is, or an arm's tail of an
        `if` or `match` value is; in a Span slot (`span_slot`) a view
        `v[a..b]` of a Vec or String too, an `@v` (R57)."""
        out: List[Tuple[rast.Expr, rast.Expr, bool]] = []

        def tail(block):
            if isinstance(block, rast.Block):
                if block.expr is not None:
                    walk(block.expr)
                elif block.stmts and isinstance(block.stmts[-1], rast.ExprStmt):
                    walk(block.stmts[-1].expr)
            elif block is not None:
                walk(block)

        def walk(e):
            if isinstance(e, rast.Grouped):
                walk(e.expr)
            elif isinstance(e, rast.UnaryOp) and e.op in ('&', '@', '&mut', '@&'):
                out.append((e, e.operand, e.op in ('&mut', '@&')))
            elif span_slot and self._span_view_base(e) is not None:
                out.append((e, self._span_view_base(e), False))
            elif isinstance(e, rast.If):
                tail(e.then_block)
                tail(e.else_block)
            elif isinstance(e, rast.Match):
                for arm in e.arms:
                    tail(arm.body)
        walk(value)
        return out

    def _hold_loans(self, holder: VarInfo, value: Optional[rast.Expr],
                    declared: Optional[rast.Type]) -> None:
        """The loans `holder`, just declared with `value`, holds to the end of
        its block. `@x` held in a `*T` isn't a borrow (#2371)."""
        held = self.types.resolve(declared) if declared is not None else None
        if isinstance(held, rast.PtrType) and not held.shared:
            return
        for e, operand, mutable in self._held_borrows(value, self._is_span_slot(declared)):
            place = self._loan_place(operand)
            info = self.scope.lookup(place[0]) if place is not None else None
            if info is not None and info is not holder:
                info.borrows.append(Loan(e.span, mutable, holder, place[1]))

    def _for_loan(self, it: rast.Expr) -> Optional[Tuple[VarInfo, Loan]]:
        """The loan a `for` over `it` holds for its body (LARB R11, AGAST
        #2439): a `for` walks a place in place (§6.3), so when the place's path
        crosses an index into anything but an array (a Vec, a Span, a pointer),
        a push may move the storage it walks. The loan is an `@` of the base of
        the last such index, `vs` in `vs[0].a`, `s.vs` in `s.vs[0].a`."""
        while isinstance(it, rast.Grouped) or (
                isinstance(it, rast.UnaryOp) and it.op in ('&', '@')):
            it = it.expr if isinstance(it, rast.Grouped) else it.operand
        e, base = it, None
        while isinstance(e, (rast.Grouped, rast.Field, rast.Index)):
            inner = e.expr
            if isinstance(e, rast.Index) and base is None:
                held = self.types.resolve(self._loan_type(inner))
                if held is not None and not isinstance(held, rast.ArrayType) and not (
                        isinstance(held, rast.NamedType) and held.name == 'unknown'):
                    base = inner
            e = inner
        place = self._loan_place(base) if base is not None else None
        info = self.scope.lookup(place[0]) if place is not None else None
        if info is None:
            return None
        return info, Loan(base.span, False, None, place[1], outer=True)

    def _release_arg_loans(self, mark: int) -> None:
        """End the argument loans made since `mark`."""
        for info, loan in self._arg_loans[mark:]:
            info.borrows = [b for b in info.borrows if b is not loan]
        del self._arg_loans[mark:]

    def _check_fn(self, fn: rast.FnDef):
        """Check a function definition."""
        impl = self.method_impl.get(id(fn))
        self.types.set_params(
            list(fn.type_params or []) + list((impl.type_params or []) if impl else []))
        try:
            self._check_fn_body(fn)
        finally:
            self.types.set_params(())

    def _check_fn_body(self, fn: rast.FnDef):
        self.current_fn_name = fn.name
        self._body = fn
        self._field_moves = set()
        # Bindings whose unwritten part was reported (uninit_rules.py).
        self._unwritten_reported = set()
        self._push_scope()

        # Parameters are owned at function start
        # For borrow semantics tracking, we need to store the borrow kind
        # along with the type so _is_copy_type can know if it's a reference
        for param in fn.params:
            self.scope.define(param.name, param.type, param.span, borrow=param.borrow)

        # Check function body (which is a Block)
        self.current_ret_type = fn.ret_type
        # A procedure's tail value goes nowhere (AGAST #2253).
        self._check_block(fn.body, value_used=fn.ret_type is not None)

        self._pop_scope()
        fn.field_moves = self._field_moves
        self.current_fn_name = None
        self._body = None

    # ---- temporaries (AGAST #2161) -------------------------------------------

    def _mark_temporary(self, expr: rast.Expr, is_move_context: bool) -> None:
        """A move-only value built by a call or literal that nothing takes
        ownership of is a temporary: `expr.drop_temp` (its type) tells the
        emitter to drop it at the end of its statement (§13.6)."""
        if is_move_context:
            return
        ty = self._infer_expr_type(expr)
        if self.types.is_move_only(ty):
            expr.drop_temp = ty

    def _fill_value_type(self, value: rast.Expr) -> Optional[rast.Type]:
        """The type of a fill's value: a binding, call or literal as
        `_infer_expr_type` has it, else a place (`*p`, `p[i]`)."""
        ty = self._infer_expr_type(value)
        if isinstance(ty, rast.NamedType) and ty.name == 'unknown':
            return self._place_type(value)
        return ty

    def _array_temporary(self, expr: rast.Expr) -> bool:
        """Is `expr` an array literal, or a call whose by-value `[N]T` result,
        a `for` walks? Nothing else can reach it, so nothing takes it (AGAST
        #3284, #3297)."""
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        if isinstance(expr, rast.ArrayLit):
            return True
        return (isinstance(expr, (rast.Call, rast.MethodCall))
                and isinstance(
                    self.types.resolve(self._infer_expr_type(expr)), rast.ArrayType))

    @staticmethod
    def _unmark_temporary(expr: rast.Expr) -> None:
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        if getattr(expr, 'drop_temp', None) is not None:
            expr.drop_temp = None

    # ---- moves out of a `name:& T` parameter (AGAST #2231) --------------------

    def _lent_param(self, expr: rast.Expr) -> Optional[str]:
        """The `name:& T` parameter `expr` reads, if any: `t`, `t.f`, `t.f.g`
        or `*t`. Its value belongs to the caller."""
        while True:
            if isinstance(expr, rast.Field):
                expr = expr.expr
            elif isinstance(expr, rast.UnaryOp) and expr.op == '*':
                expr = expr.operand
            else:
                break
        if isinstance(expr, rast.Ident):
            info = self.scope.lookup(expr.name)
            if info is not None and info.borrow == rast.Borrow.MUTABLE:
                return expr.name
        return None

    def _place_type(self, expr: rast.Expr) -> Optional[rast.Type]:
        """The type of a place: a binding, `*p`, `p.f`, `p[i]` or a pointer
        expression. Only the checks below read it: `_infer_expr_type` types
        bindings. `var x = a[0]` stays unknown there: a move-only element
        can't be moved out (#2268), and a copy one copies either way."""
        if isinstance(expr, rast.Grouped):
            return self._place_type(expr.expr)
        if isinstance(expr, rast.UnaryOp) and expr.op == '*':
            held = self.types.resolve(self._place_type(expr.operand))
            # `*t` of a `t:& T` is t's value, and t's type is already T.
            return held.inner if isinstance(held, (rast.PtrType, rast.RefType)) else held
        if isinstance(expr, rast.Index):
            held = self.types.resolve(self._place_type(expr.expr))
            # R9: `p[i]` and `(*p)[i]` are an element of the Vec, Span or String
            # `p` sees through to, and `v[i]` of one held by value (#2444). A
            # slice isn't an element.
            if isinstance(held, (rast.PtrType, rast.RefType)) \
                    and _element_of(self.types.resolve(held.inner)) is not None:
                held = self.types.resolve(held.inner)
            if _element_of(held) is not None:
                return None if isinstance(expr.index, rast.Range) else _element_of(held)
            while isinstance(held, (rast.PtrType, rast.RefType, rast.ArrayType)):
                inner = self.types.resolve(held.inner)
                if isinstance(held, rast.ArrayType) or not isinstance(inner, rast.ArrayType):
                    return inner
                held = inner
            return None
        if isinstance(expr, rast.BinOp):
            return self._place_type(expr.left)
        if isinstance(expr, rast.Field):
            base = self.types.resolve(self._place_type(expr.expr))
            while isinstance(base, (rast.PtrType, rast.RefType)):
                base = self.types.resolve(base.inner)
            return self._part_type(base, expr.field)
        return self._infer_expr_type(expr)

    def _element_root(self, expr: rast.Expr) -> Optional[rast.Index]:
        """The `a[i]` that the place `expr` (`a[i]`, `a[i].f.g`) is, or is a
        field of, when `a` is an array held by value: a local, a by-value
        parameter, a field of one or a call's result. None otherwise; `p[i]`
        through a reference has its own error, and `a[i..j]` is a slice."""
        while isinstance(expr, (rast.Field, rast.Grouped)):
            expr = expr.expr
        if not isinstance(expr, rast.Index) or isinstance(expr.index, rast.Range):
            return None
        held = self.types.resolve(self._place_type(expr.expr))
        return expr if isinstance(held, rast.ArrayType) else None

    def _moves_out_of_element(self, expr: rast.Expr) -> bool:
        """Does a by-value read of `expr` move a move-only value out of an
        array element (AGAST #2268)? The array has no flag for one moved
        element: it drops all of them, so the value would have two owners."""
        return (self._element_root(expr) is not None
                and self.types.is_move_only(self._place_type(expr)))

    def _through_reference(self, expr: rast.Expr) -> bool:
        """Does the place `expr` lie behind an `@T`, `@&T`, `*T` or `:&`? Its
        value then has an owner elsewhere, so it can't be moved out."""
        while True:
            if isinstance(expr, rast.Grouped):
                expr = expr.expr
            elif isinstance(expr, rast.Field) and self._through_deref(expr):
                return True     # `deref` lends it (§7.7)
            elif isinstance(expr, (rast.Field, rast.Index)):
                expr = expr.expr
            elif isinstance(expr, rast.UnaryOp) and expr.op == '*':
                expr = expr.operand
            else:
                return self._lent_param(expr) is not None
            if isinstance(self.types.resolve(self._place_type(expr)),
                          (rast.PtrType, rast.RefType)):
                return True

    def _check_ref_receiver(self, call: rast.MethodCall) -> None:
        """A by-value `self` method called on a reference to a move-only
        value would take the value out from behind it."""
        held = self.types.resolve(self._place_type(call.expr))
        if not isinstance(held, (rast.PtrType, rast.RefType)):
            return
        while isinstance(held, (rast.PtrType, rast.RefType)):
            held = self.types.resolve(held.inner)
        if self.types.is_move_only(held) and self._takes_self_by_value(held, call.method):
            self._reject_move_out(call.span)

    def _takes_place_behind(self, call: rast.MethodCall) -> bool:
        """A by-value `self` on an element or a deref: `p[i].m()`, `(*p)[i].m()`,
        `(*p).m()` (#2444, R9). _receiver_type doesn't type an element or see
        through a deref, so this asks the place's own type. The place then reads
        as a move: behind a reference that's the "cannot move out" error, and an
        owned element or deref has nothing else a move would change."""
        return self._takes_self_by_value(
            self.types.resolve(self._place_type(call.expr)), call.method)

    def _field_path_type(self, expr: rast.Expr) -> Optional[rast.Type]:
        """The type of a field path `b.f.g`, at any depth, or None."""
        if not isinstance(expr, rast.Field):
            return self._infer_expr_type(expr)
        base = self.types.resolve(self._field_path_type(expr.expr))
        while isinstance(base, (rast.PtrType, rast.RefType)):
            base = self.types.resolve(base.inner)
        return self._part_type(base, expr.field)

    def _part_type(self, owner: Optional[rast.Type], part: str) -> Optional[rast.Type]:
        """The type of `part` of a value of type `owner`: a struct's field by
        name or a tuple's element by index (AGAST #2244). None if it has none."""
        if isinstance(owner, rast.TupleType):
            index = int(part) if part.isdigit() else len(owner.elements)
            return owner.elements[index] if index < len(owner.elements) else None
        if isinstance(owner, rast.NamedType):
            own = next((t for n, t in self.types.struct_fields(owner) if n == part), None)
            if own is not None or owner.name not in self.types.structs:
                return own
            # Not S's own: T's, through `Deref` (§7.7).
            target = self.types.resolve(self.types.deref_target(owner))
            if isinstance(target, rast.NamedType):
                return next((t for n, t in self.types.struct_fields(target) if n == part), None)
        return None

    def _check_ref_cast(self, cast: rast.Cast) -> None:
        """`r as T` with `r: @T`, `@&T` or `*T` and T move-only (AGAST #2985):
        the plain slot's error, at `r`. Without it the cast copies the value
        out from behind the reference, and both owners drop it. A copy T reads
        through, and a cast to a pointer type stays a reference."""
        target = self.types.resolve(cast.target)
        if not self.types.is_move_only(target):
            return
        held = self.types.resolve(self._infer_expr_type(cast.expr))
        if not isinstance(held, (rast.PtrType, rast.RefType)):
            return
        if _type_key(self.types.resolve(held.inner)) == _type_key(target):
            self.errors.append(OwnershipError(ref_rules.REF_INTO_VALUE, cast.expr.span))

    def _check_global_move_out(self, expr: rast.Expr) -> bool:
        """`G` or `G.f.g` read by value, with `G` a module-level `var` and the
        value move-only (LARB R34, AGAST #3366, §13.2): refused at the path. A
        global is never dropped and any function may read it, so nothing could
        track the move. True if it refused. A path through a pointer field is
        "cannot move out of a reference" first (_through_reference)."""
        place = self._global_place(expr)
        if place is None or not self.types.is_move_only(self._field_path_type(expr)):
            return False
        self.errors.append(OwnershipError(ref_rules.move_out_of_global(*place), expr.span))
        return True

    def _global_place(self, expr: rast.Expr) -> Optional[Tuple[str, str]]:
        """`G` or `G.f.g`, with `G` a module-level `var` no local shadows: the
        global's name and the path as written. None for anything else."""
        if isinstance(expr, rast.Ident):
            root, path = expr.name, expr.name
        else:
            parts = field_path(expr)
            if parts is None:
                return None
            root, path = parts[0], f"{parts[0]}.{parts[1]}"
        if self.scope.lookup(root) is not None or root not in self.globals:
            return None
        return root, path

    def _reject_move_out(self, span: Optional[rast.Span]) -> None:
        self.errors.append(OwnershipError(ref_rules.MOVE_OUT_OF_REF, span))

    # ---- moves out of a field (AGAST #2171) ----------------------------------

    def _path_owners(self, expr: rast.Field) -> Optional[List[rast.Type]]:
        """The values `expr` (`b.f.g`, `b.f.0`) is held in by value, outermost
        first (`b`, then `b.f`), when `b` owns a struct or tuple value: a local
        or by-value parameter of a named or tuple type, not a pointer, a
        reference or a `name:& T` parameter. None if the path isn't held that
        way all along: it leaves through a pointer or an enum."""
        base = expr.expr
        if isinstance(base, rast.Ident):
            info = self.scope.lookup(base.name)
            if info is None or info.borrow == rast.Borrow.MUTABLE:
                return None
            ty = self.types.resolve(info.ritz_type)
            return [ty] if isinstance(ty, (rast.NamedType, rast.TupleType)) else None
        if not isinstance(base, rast.Field):
            return None
        owners = self._path_owners(base)
        if owners is None:
            return None
        ty = self.types.resolve(self._part_type(owners[-1], base.field))
        if isinstance(ty, rast.TupleType) or (
                isinstance(ty, rast.NamedType) and ty.name in self.types.structs):
            return owners + [ty]
        return None

    def _numbered_struct_field(self, expr: rast.Field) -> Optional[str]:
        """The struct `S`, as the source spells it, when `expr` is `s.N` and
        s is an S, or a pointer or reference to one. `.N` is a tuple's
        accessor only: a struct has no field `0`, and reading it by position
        would renumber when a field is inserted above it (AGAST #3233)."""
        if not expr.field.isdigit():
            return None
        owner = self.types.resolve(self._loan_type(expr.expr))
        while isinstance(owner, (rast.PtrType, rast.RefType)):
            owner = self.types.resolve(owner.inner)
        if not isinstance(owner, rast.NamedType) or owner.name not in self.types.structs:
            return None
        return type_to_string(owner)

    def _field_owner(self, expr: rast.Field) -> Optional[VarInfo]:
        """The binding `expr` (`b.f`, `b.f.g`) is a field of, when the binding
        holds that field by value (_path_owners). None otherwise; `h.0` of a
        struct is refused before it gets here (_numbered_struct_field)."""
        owners = self._path_owners(expr)
        if owners is None or expr.field.isdigit() != isinstance(owners[-1], rast.TupleType):
            return None
        path = field_path(expr)
        return self.scope.lookup(path[0]) if path is not None else None

    def _reown_field(self, target: rast.Expr) -> bool:
        """`b.f = v` gives back whatever moved out of `b.f`, `f` itself or
        parts of it, unless `b` or a parent of `f` is gone too. True if it
        gave anything back."""
        if not isinstance(target, rast.Field):
            return False
        info = self._field_owner(target)
        if info is None or info.state == VarState.MOVED:
            return False
        path = field_path(target)[1]
        if any(path_within(path, m) and m != path for m in info.moved_fields):
            return False
        back = [m for m in info.moved_fields if path_within(m, path)]
        for m in back:
            del info.moved_fields[m]
        return bool(back)

    def _check_owned_field(self, expr: rast.Field, info: VarInfo,
                           is_move_context: bool) -> None:
        """`b.f.g` for a binding `b` that holds it by value: a use of that
        field only, so what moved out of its siblings doesn't matter. A moved
        field overlaps it if it is the field, a parent (`b.f` moved) or a
        part of it (`b.f.g.h` moved). In a move context a move-only field
        moves out of `b` (a partial move, §13.6)."""
        name, path = field_path(expr)
        if info.state == VarState.MOVED:
            self.errors.append(self._moved_error(
                name, info, "", info.move_span, expr.span))
            return
        for moved, moved_at in info.moved_fields.items():
            if path_within(path, moved) or path_within(moved, path):
                self.errors.append(self._moved_error(
                    name, info, moved, moved_at, expr.span))
                return
        if not is_move_context or not self.types.is_move_only(self._field_path_type(expr)):
            return
        for owner in self._path_owners(expr):
            if self.types.has_own_drop(owner):
                # Its drop would see a half-moved value (Rust's E0509).
                self.errors.append(OwnershipError(
                    f"cannot move out of `{name}.{path}`: "
                    f"`{owner.name}` implements Drop",
                    expr.span))
                return
        # Not while a loan of an overlapping place is live (LARB R57, R11a).
        if self._check_move_borrowed(name, info, tuple(path.split('.')), expr.span):
            return
        info.moved_fields[path] = expr.span
        self._field_moves.add((name, path))
        # The emitter clears the field's drop flag here.
        expr.moves_field = True

    def _method_lends_self(self, call: rast.MethodCall) -> bool:
        """Does every method named like `call` borrow its receiver?"""
        cands = self.methods.get(call.method)
        if not cands:
            return False
        for m in cands:
            params = list(m.params)
            if not params or params[0].name != 'self' or not _is_lending_param(params[0]):
                return False
        return True

    def _lends_self_mut(self, call: rast.MethodCall) -> bool:
        """Does `call` take its receiver `self: @&T` or `self:& T`? A mutable
        borrow of the receiver's place (AGAST #2438). Only impl methods: the
        UFCS table that also named free fns went with R66 (#3496). False
        where the callee is unknown."""
        ty = self._receiver_type(call.expr)
        if not isinstance(ty, rast.NamedType):
            return False
        cands = [list(m.params) for m in self.type_methods.get((ty.name, call.method)) or []]
        cands = [ps for ps in cands if ps and ps[0].name == 'self']
        return bool(cands) and all(ps and _lends_mut(ps[0]) for ps in cands)

    def _receiver_type(self, expr: rast.Expr) -> Optional[rast.Type]:
        """The type of a method receiver, looking through `*r`."""
        if isinstance(expr, rast.UnaryOp) and expr.op == '*':
            # `*t` of a `t:& T` is t's value, and t's type is already T.
            return self._receiver_type(expr.operand)
        return self.types.resolve(self._field_path_type(expr))

    def _method_takes_self(self, call: rast.MethodCall) -> bool:
        """Does `call` take its receiver by value? `self:= T`, `self: T` and
        bare `self` do. The method is looked up on the receiver's own type,
        not by name across impls: moving a receiver wrongly rejects a valid
        program, and another type's method says nothing about this call. A
        method the receiver's type doesn't declare (a UFCS fallback) lends."""
        return self._takes_self_by_value(self._receiver_type(call.expr), call.method)

    def _takes_self_by_value(self, ty: Optional[rast.Type], method: str) -> bool:
        if not isinstance(ty, rast.NamedType):
            return False
        cands = self.type_methods.get((ty.name, method))
        if not cands:
            return False
        for m in cands:
            params = list(m.params)
            if not params or params[0].name != 'self' or _is_lending_param(params[0]):
                return False
        return True

    def _method_arg_params(self, call: rast.MethodCall, i: int) -> list:
        """Param `i` of each same-named method; None where one has no such param."""
        static = (isinstance(call.expr, rast.Ident)
                  and self.scope.lookup(call.expr.name) is None)
        found = []
        for m in self.methods.get(call.method) or []:
            params = list(m.params)
            if not static and params and params[0].name == 'self':
                params = params[1:]
            found.append(params[i] if i < len(params) else None)
        return found

    def _method_arg_moves(self, call: rast.MethodCall, i: int) -> bool:
        """Does argument `i` of `call` move? A receiver type the method is
        known on answers from that type's own param (see below); otherwise
        every same-named method must take it by value, and an unknown method
        lends (no move, no drop-flag clear).

        The receiver's type matters: the name-wide table mixes unrelated
        methods. `Vec<u8>.push(item: u8)` and `Vec<*u8>.push(item: *u8)` share
        the name, and a `*T` param reads as lending, so a `v.push(x)` argument
        was taken as lent and `x` was dropped after being copied into the Vec
        (AGAST #4537). Auto-deref means the receiver may be a pointer."""
        ty = self._receiver_type(call.expr)
        while isinstance(ty, (rast.PtrType, rast.RefType)):
            ty = self.types.resolve(ty.inner)
        if isinstance(ty, rast.NamedType):
            cands = self.type_methods.get((ty.name, call.method))
            if cands:
                found = []
                for m in cands:
                    params = list(m.params)
                    if params and params[0].name == 'self':
                        params = params[1:]
                    found.append(params[i] if i < len(params) else None)
                return bool(found) and all(
                    p is not None and not _is_lending_param(p) for p in found)
        params = self._method_arg_params(call, i)
        return bool(params) and all(p is not None and not _is_lending_param(p) for p in params)

    def _method_param(self, call: rast.MethodCall, i: int) -> Optional[rast.Param]:
        """Param `i` of the method `call` can only mean, or None."""
        params = self._method_arg_params(call, i)
        return params[0] if len(params) == 1 else None

    def _check_place_borrow(self, arg: rast.Expr, param: Optional[rast.Param]) -> None:
        """AGAST #2335: a place into a `name:& T` parameter is an `@&` of it
        for §13.5. A reference or pointer into a `:& U` isn't a place of `U`: it
        passes what it points at, so the binding itself isn't borrowed."""
        if param is None or getattr(param, 'borrow', None) != rast.Borrow.MUTABLE:
            return
        if isinstance(arg, rast.Ident):
            info = self.scope.lookup(arg.name)
            if info is None or info.state == VarState.MOVED:
                return    # already reported by _check_expr
            held = self.types.resolve(info.ritz_type)
        elif isinstance(arg, (rast.Field, rast.Index)):
            # A field or element is a place too (R11a): `f(r.a)` lends `r.a`.
            held = self.types.resolve(self._place_type(arg))
        else:
            return
        wanted = self.types.resolve(param.type)
        if (isinstance(held, (rast.RefType, rast.PtrType))
                and not isinstance(wanted, (rast.RefType, rast.PtrType))):
            return
        self._check_borrow(arg, mutable=True, span=arg.span)

    def _check_borrow(self, expr: rast.Expr, mutable: bool, span: rast.Span):
        """`@expr` or `@&expr` (`mutable`): a borrow of expr's root. A call's
        argument lends it until the call returns; a declaration holds it to
        the end of its block (_hold_loans)."""
        if isinstance(expr, rast.Ident):
            var_info = self.scope.lookup(expr.name)
            if var_info:
                # Can't borrow a moved value
                if var_info.state == VarState.MOVED:
                    self.errors.append(self._moved_error(
                        expr.name, var_info, "", var_info.move_span, span, borrow=True))
                    return
                if var_info.moved_fields:
                    fname, fspan = next(iter(var_info.moved_fields.items()))
                    self.errors.append(self._moved_error(
                        expr.name, var_info, fname, fspan, span, borrow=True))
                    return
        else:
            # For non-identifier borrows, check the expression
            self._check_expr(expr, is_move_context=False)
        place = self._loan_place(expr)
        info = self.scope.lookup(place[0]) if place is not None else None
        if info is None:
            return
        loan = self._conflict(info, place[1], mutable)
        if loan is not None:
            self._report(place[0], place[1], loan,
                         'mutable' if mutable else 'immutable', span)
            return
        if self._in_args:
            loan = Loan(span, mutable, None, place[1])
            info.borrows.append(loan)
            self._arg_loans.append((info, loan))

    # ---- match scrutinees and payload bindings (AGAST #2177) -----------------
    #
    # ritz1's rule (#2174, ownership.ritz own_match_begin / own_match_payload):
    # a match moves its scrutinee, so the match owns that value. An arm whose
    # pattern binds a move-only payload (`Full(t)`) hands it to the binding,
    # which is owned and dropped at the arm's end unless moved; any other arm
    # (`_`, `Empty`, `Full(_)`) leaves it to the scrutinee, which drops after
    # the arms meet. A borrowed scrutinee (`match @s`), or one read through a
    # pointer, moves nothing and owns nothing.

    def _owned_scrutinee_type(self, scrut: rast.Expr) -> Optional[rast.Type]:
        """The type of a match scrutinee the match owns, or None: a
        move-only binding it just moved, a move-only field it just moved
        out of a binding, or a by-value call's move-only result."""
        while isinstance(scrut, rast.Grouped):
            scrut = scrut.expr
        # A constructor (`Some(make(1))`, `@Full(make(1))`) builds a value
        # only the match holds, borrowed or not (#2433, ritz1 #2419).
        built = scrut
        if isinstance(built, rast.UnaryOp) and built.op in ('@', '&', '@&', '&mut'):
            built = built.operand
        ctor = self._ctor_type(built)
        if ctor is not None:
            return ctor if self.types.is_move_only(ctor) else None
        if isinstance(scrut, rast.Ident):
            moved = getattr(scrut, 'moves_binding', False)
        elif isinstance(scrut, rast.Field):
            moved = getattr(scrut, 'moves_field', False)
        else:
            moved = isinstance(scrut, rast.Call)
        if not moved:
            return None
        ty = self._field_path_type(scrut)
        return ty if self.types.is_move_only(ty) else None

    # The builtin constructors: (generic enum, the type argument the payload
    # gives, or None for a unit variant). The emitter's _BUILTIN_CTORS.
    _BUILTIN_CTORS = {'Some': ('Option', 0), 'None': ('Option', None),
                      'Ok': ('Result', 0), 'Err': ('Result', 1)}

    def _ctor_type(self, expr: rast.Expr) -> Optional[rast.NamedType]:
        """The enum a bare constructor builds, or None (#2433): a user enum's
        variant is that enum, and `Some(x)` is `Option<x's type>`, a type
        argument nothing gives being i64 (ritz1 #2419). Only whether it's
        move-only matters here; the emitter names the specialization."""
        while isinstance(expr, rast.Grouped):
            expr = expr.expr
        qualified = self.types.variant_value_type(
            expr, lambda n: self.scope.lookup(n) is not None)
        if qualified is not None:
            return qualified
        if isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident):
            name, args = expr.func.name, expr.args
        elif isinstance(expr, rast.Ident):
            name, args = expr.name, None
        else:
            return None
        if self.scope.lookup(name) is not None:
            return None
        users = [ed for ed in self.types.enums.values()
                 if not ed.type_params and any(v.name == name for v in ed.variants)]
        if users:
            return rast.NamedType(expr.span, users[0].name, [])
        if name not in self._BUILTIN_CTORS:
            return None
        base, slot = self._BUILTIN_CTORS[name]
        if (slot is None) != (args is None) or (args is not None and len(args) != 1):
            return None
        type_args = [rast.NamedType(expr.span, 'i64', [])
                     for _ in range(2 if base == 'Result' else 1)]
        if slot is not None:
            type_args[slot] = self._ctor_type(args[0]) or self._infer_expr_type(args[0])
        return rast.NamedType(expr.span, base, type_args)

    def _variant_fields(self, ty: rast.Type, variant: str) -> Optional[List[rast.Type]]:
        """The payload types of `variant` of the enum `ty`, with the enum's
        type parameters replaced by `ty`'s args. None if not an enum's."""
        while (isinstance(ty, rast.NamedType) and not ty.args
               and ty.name in self.types.aliases):
            ty = self.types.aliases[ty.name]
        if not isinstance(ty, rast.NamedType):
            return None
        ed = self.types.enums.get(ty.name)
        if ed is None:
            # Option and Result are the compiler's when no `ritzlib.option`
            # declares them: `Some(v) => eat(v)` takes the payload.
            fields = {('Option', 'Some'): [0], ('Option', 'None'): [],
                      ('Result', 'Ok'): [0], ('Result', 'Err'): [1]}.get((ty.name, variant))
            if fields is None or len(ty.args) != (2 if ty.name == 'Result' else 1):
                return None
            return [ty.args[i] for i in fields]
        subst = dict(zip(ed.type_params or [], ty.args))
        for v in ed.variants:
            if v.name == variant:
                return [_subst(t, subst) for t in v.fields]
        return None

    def _own_payload(self, arm: rast.MatchArm, scrut_ty: rast.Type) -> None:
        """An arm of a match that owns its scrutinee: give each payload
        binding its payload's type, so a move-only one is move-checked and
        the emitter drops it. `arm.takes_payload` (the arm binds a move-only
        payload) tells the emitter the arm, not the scrutinee, owns it."""
        arm.takes_payload = False
        pattern = arm.pattern
        if not isinstance(pattern, rast.VariantPattern):
            return
        fields = self._variant_fields(scrut_ty, pattern.name)
        if fields is None:
            return
        for sub, fty in zip(pattern.fields, fields):
            if isinstance(sub, rast.IdentPattern) and self.types.is_move_only(fty):
                info = self.scope.vars.get(sub.name)
                if info is not None:
                    info.ritz_type = fty
                    arm.takes_payload = True

    def _lent_scrutinee_type(self, scrut: rast.Expr) -> Optional[rast.Type]:
        """The type of a match scrutinee that something else owns, or None:
        `@s` / `@&s`, a place behind a reference or pointer (`*p`, `p.f`), a
        `name:& T` parameter or an array element (AGAST #2178)."""
        while isinstance(scrut, rast.Grouped):
            scrut = scrut.expr
        if isinstance(scrut, rast.UnaryOp) and scrut.op in ('@', '&', '@&', '&mut'):
            place = scrut.operand
        elif self._through_reference(scrut) or self._element_root(scrut) is not None:
            place = scrut
        else:
            return None
        ty = self.types.resolve(self._place_type(place))
        while isinstance(ty, (rast.PtrType, rast.RefType)):
            ty = self.types.resolve(ty.inner)
        return ty if self.types.is_move_only(ty) else None

    def _lend_payload(self, arm: rast.MatchArm, scrut_ty: rast.Type) -> None:
        """An arm of a match that owns nothing: its payload bindings are
        copies of a value the scrutinee's owner still drops, so a move-only
        one is lent like a `name:& T` parameter: it reads, and a by-value
        move out of it is refused (AGAST #2178, Rust's E0507)."""
        pattern = arm.pattern
        if not isinstance(pattern, rast.VariantPattern):
            return
        fields = self._variant_fields(scrut_ty, pattern.name)
        if fields is None:
            return
        for sub, fty in zip(pattern.fields, fields):
            if isinstance(sub, rast.IdentPattern) and self.types.is_move_only(fty):
                info = self.scope.vars.get(sub.name)
                if info is not None:
                    info.ritz_type = fty
                    info.borrow = rast.Borrow.MUTABLE

    def _check_pattern(self, pattern: rast.Pattern):
        """Check a pattern and register any bindings."""
        if isinstance(pattern, rast.IdentPattern):
            # Pattern binding creates a new variable
            # The type would be inferred from the matched value
            # For now, use a placeholder
            self.scope.define(pattern.name, rast.NamedType(pattern.span, 'unknown', []), pattern.span)
        elif isinstance(pattern, rast.VariantPattern):
            # Check sub-patterns
            for sub in pattern.fields:
                self._check_pattern(sub)
        elif isinstance(pattern, rast.StructPattern):
            for _name, sub in pattern.fields:
                self._check_pattern(sub)
