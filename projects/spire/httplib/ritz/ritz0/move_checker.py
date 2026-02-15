"""
Move and Borrow Checker for ritz0

Phase 9: Ownership & Borrowing

Implements Rust-like ownership semantics:
- Values move by default (use-after-move = error)
- Borrows: &T (shared), &mut T (exclusive)
- Aliased mutable borrows are disallowed

This runs after parsing/name resolution, before code generation.
"""

from typing import Dict, Set, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import ritz_ast as rast


class OwnershipError(Exception):
    """Error for ownership/borrowing violations."""
    def __init__(self, message: str, span = None):
        self.span = span
        if span:
            super().__init__(f"{span.file}:{span.line}:{span.column}: {message}")
        else:
            super().__init__(message)


class VarState(Enum):
    """State of a variable in the ownership system."""
    OWNED = auto()       # Variable owns its value
    MOVED = auto()       # Value has been moved out
    BORROWED = auto()    # Shared borrow active (&T)
    MUT_BORROWED = auto() # Mutable borrow active (&mut T)


@dataclass
class VarInfo:
    """Information about a variable's ownership state."""
    name: str
    ritz_type: rast.Type
    state: VarState = VarState.OWNED
    # Where the variable was defined
    def_span: Optional[rast.Span] = None
    # Where the variable was moved (if moved)
    move_span: Optional[rast.Span] = None
    # Active borrows (borrow location -> is_mutable)
    borrows: List[Tuple[rast.Span, bool]] = field(default_factory=list)


@dataclass
class Scope:
    """A lexical scope for tracking variable ownership."""
    parent: Optional['Scope'] = None
    vars: Dict[str, VarInfo] = field(default_factory=dict)

    def lookup(self, name: str) -> Optional[VarInfo]:
        """Look up a variable in this scope or parents."""
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def define(self, name: str, ritz_type: rast.Type, span: Optional[rast.Span] = None):
        """Define a new variable in this scope."""
        self.vars[name] = VarInfo(name, ritz_type, VarState.OWNED, span)

    def save_states(self) -> Dict[str, Tuple[VarState, Optional[rast.Span]]]:
        """Save variable states (for control flow analysis)."""
        states = {}
        for name, info in self.vars.items():
            states[name] = (info.state, info.move_span)
        if self.parent:
            states.update(self.parent.save_states())
        return states

    def restore_states(self, states: Dict[str, Tuple[VarState, Optional[rast.Span]]]):
        """Restore variable states."""
        for name, (state, move_span) in states.items():
            info = self.lookup(name)
            if info:
                info.state = state
                info.move_span = move_span


class MoveChecker:
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

    # Types that are Copy (don't move, they copy)
    COPY_TYPES = {
        'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'bool', 'f32', 'f64',
        # SIMD vector types are trivially copyable (SSE2 128-bit = 16 bytes)
        'v2i64', 'v4i32', 'v8i16', 'v16i8',
        # AVX2 256-bit vectors (32 bytes, still trivially copyable)
        'v4i64', 'v8i32', 'v16i16', 'v32i8',
    }

    def __init__(self):
        self.scope: Scope = Scope()
        self.errors: List[OwnershipError] = []
        # Track function parameters (they're owned at function start)
        self.current_fn_name: Optional[str] = None
        # Type aliases: name -> underlying type
        self.type_aliases: Dict[str, rast.Type] = {}
        # Function return types: name -> return type
        self.fn_return_types: Dict[str, rast.Type] = {}

    def check(self, module: rast.Module) -> List[OwnershipError]:
        """Check ownership rules for a module.

        Returns a list of errors (empty if all rules satisfied).
        """
        self.errors = []

        # First pass: collect type aliases and function signatures
        for item in module.items:
            if isinstance(item, rast.TypeAlias):
                self.type_aliases[item.name] = item.target
            elif isinstance(item, rast.FnDef):
                # Collect function return type for call inference
                if item.ret_type:
                    self.fn_return_types[item.name] = item.ret_type
            elif isinstance(item, rast.ExternFn):
                # Extern functions also have return types for inference
                if item.ret_type:
                    self.fn_return_types[item.name] = item.ret_type

        # Second pass: check functions
        for item in module.items:
            if isinstance(item, rast.FnDef):
                self._check_fn(item)

        return self.errors

    def _is_copy_type(self, ty: rast.Type) -> bool:
        """Check if a type is Copy (trivially copyable)."""
        if isinstance(ty, rast.NamedType):
            # Primitives are Copy
            if ty.name in self.COPY_TYPES:
                return True
            # Check if it's a type alias to a Copy type
            if ty.name in self.type_aliases:
                return self._is_copy_type(self.type_aliases[ty.name])
            # TODO: Check for Copy trait implementation
            return False
        elif isinstance(ty, rast.PtrType) or isinstance(ty, rast.RefType):
            # Raw pointers and references are Copy
            return True
        elif isinstance(ty, rast.UnionType):
            # Union types are Copy if all variants are Copy
            return all(self._is_copy_type(v) for v in ty.variants)
        else:
            return False

    def _infer_expr_type(self, expr: rast.Expr) -> rast.Type:
        """Infer the type of an expression for ownership checking.

        Returns a basic type so we can determine if it's Copy.
        This doesn't need to be as complete as the type checker - just enough
        to identify Copy types like pointers and primitives.
        """
        if isinstance(expr, rast.IntLit):
            return rast.NamedType(expr.span, 'i64', [])
        elif isinstance(expr, rast.FloatLit):
            return rast.NamedType(expr.span, 'f64', [])
        elif isinstance(expr, rast.BoolLit):
            return rast.NamedType(expr.span, 'bool', [])
        elif isinstance(expr, rast.CharLit):
            return rast.NamedType(expr.span, 'u8', [])
        elif isinstance(expr, rast.StringLit):
            # String literals produce String type (Issue #89 Phase 3)
            # String is NOT Copy - needs ownership tracking
            return rast.NamedType(expr.span, 'String', [])
        elif isinstance(expr, rast.CStringLit):
            # C-string literals: c"hello" -> *u8 (Copy)
            return rast.PtrType(expr.span, rast.NamedType(expr.span, 'u8', []), mutable=False)
        elif isinstance(expr, rast.SpanStringLit):
            # Span string literals: s"hello" -> Span<u8> (Copy - it's just ptr + len)
            return rast.NamedType(expr.span, 'Span', [rast.NamedType(expr.span, 'u8', [])])
        elif isinstance(expr, rast.NullLit):
            # Null is a special pointer type (Copy)
            return rast.PtrType(expr.span, rast.NamedType(expr.span, 'void', []), mutable=False)
        elif isinstance(expr, rast.Ident):
            info = self.scope.lookup(expr.name)
            if info:
                return info.ritz_type
            return rast.NamedType(expr.span, 'unknown', [])
        elif isinstance(expr, rast.UnaryOp):
            if expr.op == '&':
                inner = self._infer_expr_type(expr.operand)
                return rast.PtrType(expr.span, inner, mutable=False)
            elif expr.op == '*':
                inner = self._infer_expr_type(expr.operand)
                if isinstance(inner, rast.PtrType):
                    return inner.inner
                return rast.NamedType(expr.span, 'unknown', [])
            return self._infer_expr_type(expr.operand)
        elif isinstance(expr, rast.BinOp):
            return self._infer_expr_type(expr.left)
        elif isinstance(expr, rast.Cast):
            return expr.target
        elif isinstance(expr, rast.StructLit):
            return rast.NamedType(expr.span, expr.name, [])
        elif isinstance(expr, rast.ArrayLit):
            if expr.elements:
                inner = self._infer_expr_type(expr.elements[0])
                return rast.ArrayType(expr.span, len(expr.elements), inner)
            return rast.NamedType(expr.span, 'unknown', [])
        elif isinstance(expr, rast.Call):
            # Look up function return type
            if isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
                if fn_name in self.fn_return_types:
                    return self.fn_return_types[fn_name]
            # Unknown function or no return type
            return rast.NamedType(expr.span, 'unknown', [])
        # Default to unknown
        return rast.NamedType(expr.span, 'unknown', [])

    def _push_scope(self):
        """Enter a new scope."""
        self.scope = Scope(parent=self.scope)

    def _pop_scope(self):
        """Exit current scope."""
        if self.scope.parent:
            self.scope = self.scope.parent

    def _check_fn(self, fn: rast.FnDef):
        """Check a function definition."""
        self.current_fn_name = fn.name
        self._push_scope()

        # Parameters are owned at function start
        for param in fn.params:
            self.scope.define(param.name, param.type, param.span)

        # Check function body (which is a Block)
        self._check_block(fn.body)

        self._pop_scope()
        self.current_fn_name = None

    def _check_block(self, block: rast.Block) -> bool:
        """Check a block expression.

        Returns True if block definitely returns (via ReturnStmt).
        """
        for stmt in block.stmts:
            returned = self._check_stmt(stmt)
            if returned:
                # Rest of block is dead code - skip checking it
                # This prevents false positives like "use after move" when the
                # move is in a return and the "use" is after the return
                return True
        if block.expr:
            self._check_expr(block.expr, is_move_context=True)
        return False

    def _check_stmt(self, stmt: rast.Stmt) -> bool:
        """Check a statement for ownership violations.

        Returns True if statement definitely returns (terminates control flow).
        """
        if isinstance(stmt, rast.VarStmt):
            # Variable declaration
            if stmt.value:
                self._check_expr(stmt.value, is_move_context=True)
            # Use explicit type if present, otherwise infer from initializer
            if stmt.type:
                var_type = stmt.type
            elif stmt.value:
                var_type = self._infer_expr_type(stmt.value)
            else:
                var_type = rast.NamedType(stmt.span, 'unknown', [])
            self.scope.define(stmt.name, var_type, stmt.span)
            return False

        elif isinstance(stmt, rast.LetStmt):
            # Let binding
            if stmt.value:
                self._check_expr(stmt.value, is_move_context=True)
            # Use explicit type if present, otherwise infer from initializer
            if stmt.type:
                var_type = stmt.type
            elif stmt.value:
                var_type = self._infer_expr_type(stmt.value)
            else:
                var_type = rast.NamedType(stmt.span, 'unknown', [])
            self.scope.define(stmt.name, var_type, stmt.span)
            return False

        elif isinstance(stmt, rast.ExprStmt):
            self._check_expr(stmt.expr, is_move_context=False)
            return False

        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                self._check_expr(stmt.value, is_move_context=True)
            # Return terminates this control flow path
            return True

        elif isinstance(stmt, rast.AssignStmt):
            # Check the target (lvalue) - not a move
            self._check_expr(stmt.target, is_move_context=False)
            # Check the value - this is a move
            self._check_expr(stmt.value, is_move_context=True)
            # After assignment, the target variable becomes owned again
            if isinstance(stmt.target, rast.Ident):
                var_info = self.scope.lookup(stmt.target.name)
                if var_info:
                    var_info.state = VarState.OWNED
                    var_info.move_span = None
            return False

        elif isinstance(stmt, rast.WhileStmt):
            self._check_expr(stmt.cond, is_move_context=False)
            self._push_scope()
            self._check_block(stmt.body)
            self._pop_scope()
            return False

        elif isinstance(stmt, rast.ForStmt):
            self._push_scope()
            # The iterator is moved into the loop
            self._check_expr(stmt.iter, is_move_context=True)
            # Loop variable is defined fresh each iteration
            # For range-based for loops, the variable is i64 (Copy type)
            self.scope.define(stmt.var, rast.NamedType(stmt.span, 'i64', []), stmt.span)
            self._check_block(stmt.body)
            self._pop_scope()
            return False

        return False

    def _check_expr(self, expr: rast.Expr, is_move_context: bool = False):
        """Check an expression for ownership violations.

        Args:
            expr: The expression to check
            is_move_context: True if this expression's value will be moved
        """
        if isinstance(expr, rast.Ident):
            var_info = self.scope.lookup(expr.name)
            if var_info:
                # Check if variable has been moved
                if var_info.state == VarState.MOVED:
                    self.errors.append(OwnershipError(
                        f"use of moved value: `{expr.name}` (moved at {var_info.move_span})",
                        expr.span
                    ))
                    return

                # If this is a move context and type is not Copy, mark as moved
                if is_move_context and not self._is_copy_type(var_info.ritz_type):
                    var_info.state = VarState.MOVED
                    var_info.move_span = expr.span

        elif isinstance(expr, rast.BinOp):
            # Binary ops don't move their operands (they borrow or copy)
            self._check_expr(expr.left, is_move_context=False)
            self._check_expr(expr.right, is_move_context=False)

        elif isinstance(expr, rast.UnaryOp):
            if expr.op == '&':
                # Shared borrow - check the operand exists and isn't moved
                self._check_borrow(expr.operand, mutable=False, span=expr.span)
            elif expr.op == '&mut':
                # Mutable borrow - check no other borrows exist
                self._check_borrow(expr.operand, mutable=True, span=expr.span)
            elif expr.op == '*':
                # Dereference - check the pointer expression
                self._check_expr(expr.operand, is_move_context=False)
            else:
                self._check_expr(expr.operand, is_move_context=False)

        elif isinstance(expr, rast.Call):
            # Function arguments are moved (unless Copy)
            self._check_expr(expr.func, is_move_context=False)
            for arg in expr.args:
                self._check_expr(arg, is_move_context=True)

        elif isinstance(expr, rast.Field):
            # Field access doesn't move the struct (unless the result is moved)
            self._check_expr(expr.expr, is_move_context=False)

        elif isinstance(expr, rast.Index):
            self._check_expr(expr.expr, is_move_context=False)
            self._check_expr(expr.index, is_move_context=False)

        elif isinstance(expr, rast.StructLit):
            for _name, value in expr.fields:
                self._check_expr(value, is_move_context=True)

        elif isinstance(expr, rast.Match):
            self._check_expr(expr.expr, is_move_context=True)
            for arm in expr.arms:
                self._push_scope()
                # Pattern bindings
                self._check_pattern(arm.pattern)
                self._check_expr(arm.body, is_move_context=is_move_context)
                self._pop_scope()

        elif isinstance(expr, rast.TryOp):
            self._check_expr(expr.expr, is_move_context=is_move_context)

        elif isinstance(expr, rast.Cast):
            self._check_expr(expr.expr, is_move_context=False)

        elif isinstance(expr, rast.If):
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
            then_returns = self._check_block(expr.then_block)
            self._pop_scope()

            # Save state after then branch (captures moves in then)
            states_after_then = self.scope.save_states()

            if expr.else_block:
                # Always restore to pre-if state for else branch
                # (else branch doesn't see moves from then branch)
                self.scope.restore_states(saved_states)

                self._push_scope()
                else_returns = self._check_block(expr.else_block)
                self._pop_scope()

                # After if/else, merge states:
                # - If both return, code after is dead
                # - If only then returns, keep state from else
                # - If only else returns, keep state from then (restore after_then)
                # - If neither returns, conservatively mark moved in EITHER branch as moved
                if then_returns and else_returns:
                    # Both return - subsequent code is dead, state doesn't matter
                    pass
                elif then_returns:
                    # Then returned, else didn't - keep current state (from else)
                    pass
                elif else_returns:
                    # Else returned, then didn't - restore state from after then
                    self.scope.restore_states(states_after_then)
                else:
                    # Neither returned - merge: if moved in either branch, mark as moved
                    states_after_else = self.scope.save_states()
                    for name, (then_state, then_move_span) in states_after_then.items():
                        else_info = states_after_else.get(name)
                        if else_info:
                            else_state, else_move_span = else_info
                            # If moved in either branch, mark as moved
                            if then_state == VarState.MOVED or else_state == VarState.MOVED:
                                var_info = self.scope.lookup(name)
                                if var_info:
                                    var_info.state = VarState.MOVED
                                    var_info.move_span = then_move_span or else_move_span
            else:
                # No else branch - if then returns, restore pre-if state
                # (the non-return path is when condition is false)
                if then_returns:
                    self.scope.restore_states(saved_states)
                # If then doesn't return, merge: either then path moved or condition was false
                # Conservative: if moved in then, mark as potentially moved

        elif isinstance(expr, rast.Block):
            self._push_scope()
            self._check_block(expr)
            self._pop_scope()

        # Literals don't have ownership concerns
        elif isinstance(expr, (rast.IntLit, rast.FloatLit, rast.StringLit,
                               rast.CStringLit, rast.SpanStringLit, rast.BoolLit, rast.CharLit)):
            pass

    def _check_borrow(self, expr: rast.Expr, mutable: bool, span: rast.Span):
        """Check a borrow expression for validity."""
        if isinstance(expr, rast.Ident):
            var_info = self.scope.lookup(expr.name)
            if var_info:
                # Can't borrow a moved value
                if var_info.state == VarState.MOVED:
                    self.errors.append(OwnershipError(
                        f"cannot borrow `{expr.name}` - value has been moved",
                        span
                    ))
                    return

                # Check for conflicting borrows
                if mutable:
                    # Mutable borrow conflicts with any existing borrow
                    if var_info.state == VarState.BORROWED:
                        self.errors.append(OwnershipError(
                            f"cannot borrow `{expr.name}` as mutable - already borrowed as immutable",
                            span
                        ))
                    elif var_info.state == VarState.MUT_BORROWED:
                        self.errors.append(OwnershipError(
                            f"cannot borrow `{expr.name}` as mutable - already borrowed as mutable",
                            span
                        ))
                    else:
                        var_info.state = VarState.MUT_BORROWED
                        var_info.borrows.append((span, True))
                else:
                    # Shared borrow conflicts with mutable borrow
                    if var_info.state == VarState.MUT_BORROWED:
                        self.errors.append(OwnershipError(
                            f"cannot borrow `{expr.name}` as immutable - already borrowed as mutable",
                            span
                        ))
                    else:
                        var_info.state = VarState.BORROWED
                        var_info.borrows.append((span, False))
        else:
            # For non-identifier borrows, just check the expression
            self._check_expr(expr, is_move_context=False)

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
