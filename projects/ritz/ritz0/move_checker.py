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
from dataclasses import dataclass, field
from enum import Enum, auto
import ref_rules
import ritz_ast as rast
from tail_value import slot_tails


class OwnershipError(Exception):
    """Error for ownership/borrowing violations."""
    def __init__(self, message: str, span = None):
        self.span = span
        self.reason = message
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
    # Borrow semantics for parameters (CONST/MUTABLE/MOVE)
    # If set, this parameter is a borrow and is effectively Copy
    borrow: Optional[rast.Borrow] = None
    # Move-only fields moved out of the binding (a partial move, §13.6,
    # AGAST #2171, #2232): dotted path below the binding (`f`, `f.g`) ->
    # where. The binding stays usable through its other fields; using it
    # whole, the moved field, a parent of it or a part of it is an error.
    moved_fields: Dict[str, rast.Span] = field(default_factory=dict)


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

    def define(self, name: str, ritz_type: rast.Type, span: Optional[rast.Span] = None, borrow: Optional[rast.Borrow] = None):
        """Define a new variable in this scope."""
        self.vars[name] = VarInfo(name, ritz_type, VarState.OWNED, span, borrow=borrow)

    def save_states(self) -> Dict[str, Tuple[VarState, Optional[rast.Span], Dict[str, rast.Span]]]:
        """Save variable states (for control flow analysis)."""
        states = {}
        for name, info in self.vars.items():
            states[name] = (info.state, info.move_span, dict(info.moved_fields))
        if self.parent:
            states.update(self.parent.save_states())
        return states

    def restore_states(self, states: Dict[str, Tuple[VarState, Optional[rast.Span], Dict[str, rast.Span]]]):
        """Restore variable states."""
        for name, (state, move_span, fields) in states.items():
            info = self.lookup(name)
            if info:
                info.state = state
                info.move_span = move_span
                info.moved_fields = dict(fields)


def field_path(expr: rast.Expr) -> Optional[Tuple[str, str]]:
    """`b.f.g` as the binding name and the dotted path below it, ("b", "f.g").
    None for anything else. Move tracking and drop flags are keyed on these
    paths, so the checker and the emitter share this."""
    parts: List[str] = []
    while isinstance(expr, rast.Field):
        parts.append(expr.field)
        expr = expr.expr
    if not parts or not isinstance(expr, rast.Ident):
        return None
    return expr.name, '.'.join(reversed(parts))


def path_within(path: str, parent: str) -> bool:
    """Is the dotted field path `path` the field `parent` or a part of it?"""
    return path == parent or path.startswith(parent + '.')


def _is_lending_param(param: Optional[rast.Param]) -> bool:
    """A parameter that borrows its argument rather than taking ownership:
    `@T`, `@&T`, `*T` (auto-borrow, AGAST #1290) or `name:& T`."""
    if param is None:
        return False
    if getattr(param, 'borrow', None) == rast.Borrow.MUTABLE:
        return True
    return isinstance(param.type, (rast.RefType, rast.PtrType))


class MoveTypes:
    """Which types are move-only (LANGUAGE_SPEC §13.1, AGAST #1854/#2157).

    A type is move-only iff it implements `Drop`, or it has a field, an
    enum-variant payload or a generic argument that is move-only, checked
    transitively. Every other type copies. A name this module doesn't
    define (a type parameter, a type inference couldn't name) is a copy
    type: a wrong "copy" only skips a use-after-move error, while a wrong
    "move" rejects valid programs, which is what #1489 and #1548 were.
    Shared by the move checker and the emitter's drop glue.
    """

    def __init__(self, module: rast.Module):
        self.drop_types: Set[str] = set()
        self.structs: Dict[str, rast.StructDef] = {}
        self.enums: Dict[str, rast.EnumDef] = {}
        self.aliases: Dict[str, rast.Type] = {}
        for item in module.items:
            if isinstance(item, rast.ImplBlock) and item.trait_name == 'Drop':
                self.drop_types.add(item.type_name)
            elif isinstance(item, rast.StructDef):
                self.structs[item.name] = item
            elif isinstance(item, rast.EnumDef):
                self.enums[item.name] = item
            elif isinstance(item, rast.TypeAlias):
                self.aliases[item.name] = item.target
        self._cache: Dict[str, bool] = {}

    def has_own_drop(self, ty: rast.Type) -> bool:
        return isinstance(ty, rast.NamedType) and ty.name in self.drop_types

    def resolve(self, ty: Optional[rast.Type]) -> Optional[rast.Type]:
        """`ty` with type aliases followed."""
        seen: Set[str] = set()
        while (isinstance(ty, rast.NamedType) and not ty.args
               and ty.name in self.aliases and ty.name not in seen):
            seen.add(ty.name)
            ty = self.aliases[ty.name]
        return ty

    def is_move_only(self, ty: Optional[rast.Type]) -> bool:
        if ty is None:
            return False
        key = _type_key(ty)
        if key not in self._cache:
            self._cache[key] = False      # cycle guard: a recursive type
            self._cache[key] = self._compute(ty)
        return self._cache[key]

    def _compute(self, ty: rast.Type) -> bool:
        if isinstance(ty, rast.NamedType):
            if ty.name in self.drop_types:
                return True
            if any(self.is_move_only(a) for a in ty.args):
                return True
            if ty.name in self.aliases and not ty.args:
                return self.is_move_only(self.aliases[ty.name])
            if ty.name in self.structs:
                return any(self.is_move_only(t) for _n, t in self.struct_fields(ty))
            if ty.name in self.enums:
                return any(self.is_move_only(t)
                           for v in self.enums[ty.name].variants for t in v.fields)
            return False
        if isinstance(ty, rast.ArrayType):
            return self.is_move_only(ty.inner)
        if isinstance(ty, rast.TupleType):
            return any(self.is_move_only(t) for t in ty.elements)
        if isinstance(ty, rast.UnionType):
            return any(self.is_move_only(t) for t in ty.variants)
        # Pointers, references, fn types, SIMD vectors: copies.
        return False

    def variant_value_type(self, expr: rast.Expr, is_binding) -> Optional[rast.Type]:
        """The enum type of a qualified variant value, `E.V` or `E.V(...)`,
        when `E` is a non-generic enum declaring `V` and not a binding
        (`is_binding(name)`). None for anything else."""
        if isinstance(expr, rast.Field):
            base, name = expr.expr, expr.field
        elif isinstance(expr, rast.MethodCall):
            base, name = expr.expr, expr.method
        else:
            return None
        if not isinstance(base, rast.Ident) or is_binding(base.name):
            return None
        ed = self.enums.get(base.name)
        if ed is None or ed.type_params or not any(v.name == name for v in ed.variants):
            return None
        return rast.NamedType(expr.span, ed.name, [])

    def struct_fields(self, ty: rast.NamedType) -> List[Tuple[str, rast.Type]]:
        """The struct's fields with its type parameters replaced by `ty`'s args."""
        sd = self.structs.get(ty.name)
        if sd is None:
            return []
        subst = dict(zip(sd.type_params or [], ty.args))
        return [(n, _subst(t, subst)) for n, t in sd.fields]


def _type_key(ty: rast.Type) -> str:
    if isinstance(ty, rast.NamedType):
        if ty.args:
            return f"{ty.name}<{','.join(_type_key(a) for a in ty.args)}>"
        return ty.name
    if isinstance(ty, rast.ArrayType):
        return f"[{ty.size}]{_type_key(ty.inner)}"
    if isinstance(ty, rast.TupleType):
        return f"({','.join(_type_key(t) for t in ty.elements)})"
    if isinstance(ty, rast.UnionType):
        return '|'.join(_type_key(t) for t in ty.variants)
    if isinstance(ty, (rast.PtrType, rast.RefType)):
        return f"*{_type_key(ty.inner)}"
    return type(ty).__name__


def _subst(ty: rast.Type, subst: Dict[str, rast.Type]) -> rast.Type:
    if not subst:
        return ty
    if isinstance(ty, rast.NamedType):
        if not ty.args and ty.name in subst:
            return subst[ty.name]
        if ty.args:
            return rast.NamedType(ty.span, ty.name, [_subst(a, subst) for a in ty.args])
        return ty
    if isinstance(ty, rast.ArrayType):
        return rast.ArrayType(ty.span, ty.size, _subst(ty.inner, subst))
    if isinstance(ty, rast.TupleType):
        return rast.TupleType(ty.span, [_subst(t, subst) for t in ty.elements])
    return ty


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

    # Primitive scalar names. Only `_infer_expr_type`'s `read_*` heuristic
    # still needs them: move-vs-copy is decided by MoveTypes (LANGUAGE_SPEC
    # §13.1), not by a list (AGAST #2157; the list was #1489 and #1548).
    PRIMITIVES = {
        'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64', 'bool', 'f32', 'f64',
        'usize', 'isize',
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
        # Per enclosing loop: the binding states at each `break` and
        # `continue` (AGAST #2161, _check_loop).
        self._loops: List[Dict[str, list]] = []
        # (binding name, field path) pairs the current function moves out of
        # a binding (AGAST #2171, #2232); the emitter gives those drop flags.
        self._field_moves: Set[Tuple[str, str]] = set()
        # id(Ident) of each value that lands in a reference (_note_ref_slot).
        self._ref_tails: Set[int] = set()
        self.current_ret_type: Optional[rast.Type] = None

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
        """Moves out of a reference in a monomorphised module's generic
        instances. `check` saw those bodies with `T` a copy type (AGAST #2263),
        so an instance at a move-only `T` is where `*p` turns into a move. Each
        is checked on a copy: the emitter reads the marks `check` leaves, and
        giving an instance its own is #2263's change, not this one."""
        self.errors = []
        self._collect(module)
        fns = [item for item in module.items if isinstance(item, rast.FnDef)]
        for item in module.items:
            if isinstance(item, rast.ImplBlock):
                fns.extend(item.methods)
        for fn in fns:
            if any(self.types.is_move_only(a) for a in getattr(fn, 'instance_args', ())):
                self._check_fn(copy.deepcopy(fn))
        self.errors = [e for e in self.errors if e.reason == ref_rules.MOVE_OUT_OF_REF]
        self._drop_repeats()
        return self.errors

    def _collect(self, module: rast.Module) -> None:
        """Type aliases and function signatures."""
        self.types = MoveTypes(module)
        for item in module.items:
            if isinstance(item, rast.TypeAlias):
                self.type_aliases[item.name] = item.target
            elif isinstance(item, (rast.FnDef, rast.ExternFn)):
                # Collect function return type for call inference
                if item.ret_type:
                    self.fn_return_types[item.name] = item.ret_type
                self.fn_params[item.name] = list(item.params)
            elif isinstance(item, rast.ImplBlock):
                for m in item.methods:
                    self.methods.setdefault(m.name, []).append(m)
                    self.type_methods.setdefault((item.type_name, m.name), []).append(m)
                    self.method_impl[id(m)] = item

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
            # Bare string literals produce StrView (AGAST #98).
            # StrView is Copy (ptr + len view, no ownership).
            return rast.NamedType(expr.span, 'StrView', [])
        elif isinstance(expr, rast.CStringLit):
            # C-string literals: c"hello" -> *u8 (Copy)
            return rast.PtrType(expr.span, rast.NamedType(expr.span, 'u8', []), mutable=False)
        # Note: SpanStringLit (s"...") was removed in AGAST #98 — bare
        # StringLit now produces StrView of the same { ptr, len } shape.
        elif isinstance(expr, rast.NullLit):
            # Null is a special pointer type (Copy)
            return rast.PtrType(expr.span, rast.NamedType(expr.span, 'void', []), mutable=False)
        elif isinstance(expr, rast.Ident):
            info = self.scope.lookup(expr.name)
            if info:
                return info.ritz_type
            return rast.NamedType(expr.span, 'unknown', [])
        elif isinstance(expr, rast.UnaryOp):
            if expr.op in ('&', '@'):
                inner = self._infer_expr_type(expr.operand)
                return rast.PtrType(expr.span, inner, mutable=False)
            elif expr.op in ('&mut', '@&'):
                inner = self._infer_expr_type(expr.operand)
                return rast.PtrType(expr.span, inner, mutable=True)
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
        elif self.types.variant_value_type(
                expr, lambda n: self.scope.lookup(n) is not None) is not None:
            return self.types.variant_value_type(
                expr, lambda n: self.scope.lookup(n) is not None)
        elif isinstance(expr, rast.TupleLit):
            return rast.TupleType(expr.span, [self._infer_expr_type(e) for e in expr.elements])
        elif isinstance(expr, rast.Field):
            # What the field declares (AGAST #2243): the emitter types the
            # binding from that too. A qualified variant is handled above.
            return (self._field_path_type(expr)
                    or rast.NamedType(expr.span, 'unknown', []))
        elif isinstance(expr, rast.Call):
            # Look up function return type
            if isinstance(expr.func, rast.Ident):
                fn_name = expr.func.name
                if fn_name in self.fn_return_types:
                    return self.fn_return_types[fn_name]
            # Unknown function or no return type
            return rast.NamedType(expr.span, 'unknown', [])
        elif isinstance(expr, rast.TryOp):
            # TryOp (?) unwraps Result<T, E> to T or Option<T> to T
            # Infer the inner type from the expression's Result/Option
            inner = self._infer_expr_type(expr.expr)
            if isinstance(inner, rast.NamedType) and inner.name in ('Result', 'Option'):
                # The ok/some type is the first type argument
                if inner.args:
                    return inner.args[0]
            # Fallback: return unknown (could be any type)
            return rast.NamedType(expr.span, 'unknown', [])
        elif isinstance(expr, rast.MethodCall):
            # What the method declares, on the receiver's own type (AGAST
            # #2257): the emitter types the binding from that too.
            declared = self._method_return_type(expr)
            if declared is not None:
                return declared
            # Otherwise (a builtin, a UFCS fallback), go by the method's name.
            method = expr.method
            # Common methods that return Copy types
            if method in ('len', 'cap', 'count', 'size', 'is_empty', 'is_some', 'is_none',
                          'is_ok', 'is_err', 'contains', 'unwrap_or'):
                # These typically return usize, i64, or bool - all Copy
                return rast.NamedType(expr.span, 'i64', [])
            # read_* methods return Result<primitive>
            if method.startswith('read_'):
                type_suffix = method[5:]  # e.g., "u16", "u32", "i8", etc.
                if type_suffix in self.PRIMITIVES:
                    return rast.NamedType(expr.span, 'Result', [
                        rast.NamedType(expr.span, type_suffix, [])
                    ])
            # Fallback to unknown
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

    def _save_borrow_states(self) -> Dict[str, Tuple[VarState, List]]:
        """Save borrow states for all variables in scope.

        Returns a dict mapping var name to (state, borrows list copy).
        Only saves borrow-related state, not move state.
        """
        states = {}
        scope = self.scope
        while scope:
            for name, info in scope.vars.items():
                if name not in states:  # Don't override inner scope with outer
                    states[name] = (info.state, list(info.borrows))
            scope = scope.parent
        return states

    def _restore_borrow_states(self, saved: Dict[str, Tuple[VarState, List]]):
        """Restore borrow states, preserving move states.

        This releases borrows that were created after the save point,
        but does NOT restore moved values (moves are permanent until reassigned).
        """
        for name, (saved_state, saved_borrows) in saved.items():
            info = self.scope.lookup(name)
            if info:
                # Don't restore if the variable was moved - moves are permanent
                if info.state == VarState.MOVED:
                    continue
                # Restore borrow state (releases borrows created after save)
                info.state = saved_state
                info.borrows = saved_borrows

    def _check_fn(self, fn: rast.FnDef):
        """Check a function definition."""
        self.current_fn_name = fn.name
        self._field_moves = set()
        self._ref_tails = set()
        self._push_scope()

        # Parameters are owned at function start
        # For borrow semantics tracking, we need to store the borrow kind
        # along with the type so _is_copy_type can know if it's a reference
        for param in fn.params:
            self.scope.define(param.name, param.type, param.span, borrow=param.borrow)

        # Check function body (which is a Block)
        self.current_ret_type = fn.ret_type
        self._note_ref_slot(fn.ret_type, fn.body)
        self._check_block(fn.body)

        self._pop_scope()
        fn.field_moves = self._field_moves
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
                self._note_ref_slot(stmt.type, stmt.value)
                self._check_expr(stmt.value, is_move_context=True)
                self._hold_reborrows(stmt.type, stmt.value)
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
            # Let binding. `let p: @T = t` of a `name:& T` parameter takes
            # the parameter's address (AGAST #2231): a read, not a move.
            if stmt.value:
                reborrows = (isinstance(self.types.resolve(stmt.type),
                                        (rast.RefType, rast.PtrType))
                             and self._lent_param(stmt.value) is not None)
                self._note_ref_slot(stmt.type, stmt.value)
                self._check_expr(stmt.value, is_move_context=not reborrows)
                self._hold_reborrows(stmt.type, stmt.value)
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
                self._note_ref_slot(self.current_ret_type, stmt.value)
                self._check_expr(stmt.value, is_move_context=True)
            # Return terminates this control flow path
            return True

        elif isinstance(stmt, rast.AssignStmt):
            # Check the value first - this is a move. `t = f(t)` reads the
            # old t before the assignment makes t an owner again. A reference
            # takes a `name:& T` parameter's address (AGAST #1302, #2249).
            self._note_ref_slot(self._assign_slot_type(stmt.target), stmt.value)
            self._check_expr(stmt.value, is_move_context=True)
            # The target (lvalue) is not a move, and assigning to a bare
            # moved-from binding is not a use of it (§13.6). Nor is assigning
            # to a field moved out of a binding: that field is owned again.
            if self._reown_field(stmt.target):
                # The emitter sets the field's drop flags again.
                stmt.target.reowns_field = True
            elif not isinstance(stmt.target, rast.Ident):
                self._check_expr(stmt.target, is_move_context=False)
            # After assignment, the target variable becomes owned again
            if isinstance(stmt.target, rast.Ident):
                var_info = self.scope.lookup(stmt.target.name)
                if var_info:
                    var_info.state = VarState.OWNED
                    var_info.move_span = None
                    var_info.moved_fields = {}
            return False

        elif isinstance(stmt, rast.WhileStmt):
            def iteration():
                # The condition runs at the loop head, on every iteration.
                self._check_expr(stmt.cond, is_move_context=False)
                self._push_scope()
                done = self._check_block(stmt.body)
                self._pop_scope()
                return done
            self._check_loop(iteration)
            return False

        elif isinstance(stmt, rast.ForStmt):
            # The iterator is moved into the loop, once. What a reference
            # reaches stays its owner's, so the loop only reads it.
            self._check_expr(stmt.iter,
                             is_move_context=not self._through_reference(stmt.iter))

            def iteration():
                self._push_scope()
                # Loop variable is defined fresh each iteration
                # For range-based for loops, the variable is i64 (Copy type)
                self.scope.define(stmt.var, rast.NamedType(stmt.span, 'i64', []), stmt.span)
                done = self._check_block(stmt.body)
                self._pop_scope()
                return done
            self._check_loop(iteration)
            return False

        elif isinstance(stmt, rast.BreakStmt):
            self._note_loop_exit('breaks')
            return True

        elif isinstance(stmt, rast.ContinueStmt):
            self._note_loop_exit('continues')
            return True

        return False

    # ---- loops (AGAST #2161) ------------------------------------------------
    #
    # A loop body runs again with whatever the previous iteration left, so a
    # binding declared outside the loop and moved inside it is moved at the
    # loop head unless every path back there assigned it again. The body is
    # checked once with the entry state and, while that grows the set of
    # moved bindings at the head, again with the merged head state. Paths
    # that `break` don't reach the head; they join the state after the loop.

    def _snapshot(self) -> Dict[int, Tuple[VarInfo, VarState, Optional[rast.Span], Dict[str, rast.Span]]]:
        """Every visible binding's state (and its moved-out fields), keyed by
        binding (not name, so a shadowing binding in an inner scope can't
        stand in for an outer one)."""
        out: Dict[int, Tuple[VarInfo, VarState, Optional[rast.Span], Dict[str, rast.Span]]] = {}
        scope = self.scope
        while scope:
            for info in scope.vars.values():
                out.setdefault(id(info), (info, info.state, info.move_span,
                                          dict(info.moved_fields)))
            scope = scope.parent
        return out

    def _restore(self, snap) -> None:
        for info, state, span, fields in snap.values():
            info.state = state
            info.move_span = span
            info.moved_fields = dict(fields)

    @staticmethod
    def _join(paths) -> Dict[int, Tuple[VarInfo, VarState, Optional[rast.Span], Dict[str, rast.Span]]]:
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
            done = iteration()
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

    def _check_expr(self, expr: rast.Expr, is_move_context: bool = False):
        """Check an expression for ownership violations.

        Args:
            expr: The expression to check
            is_move_context: True if this expression's value will be moved
        """
        if isinstance(expr, rast.Ident):
            var_info = self.scope.lookup(expr.name)
            if id(expr) in self._ref_tails and self._lent_param(expr) is not None:
                is_move_context = False
            if var_info:
                # Check if variable has been moved
                if var_info.state == VarState.MOVED:
                    self.errors.append(OwnershipError(
                        f"use of moved value: `{expr.name}` (moved at {var_info.move_span})",
                        expr.span
                    ))
                    return
                # Used whole after a field was moved out (AGAST #2171).
                if var_info.moved_fields:
                    fname, fspan = next(iter(var_info.moved_fields.items()))
                    self.errors.append(OwnershipError(
                        f"use of moved value: `{expr.name}.{fname}` (moved at {fspan})",
                        expr.span
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

        elif isinstance(expr, rast.BinOp):
            # Binary ops don't move their operands (they borrow or copy)
            self._check_expr(expr.left, is_move_context=False)
            self._check_expr(expr.right, is_move_context=False)

        elif isinstance(expr, rast.UnaryOp):
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

        elif (isinstance(expr, rast.Call) and isinstance(expr.func, rast.Ident)
                and expr.func.name == 'sizeof'):
            # sizeof's operand is never evaluated: it neither moves nor
            # uses its operand (AGAST #2124; `sizeof(key)` used to move key).
            pass

        elif isinstance(expr, rast.Call):
            # Function arguments are moved (unless Copy)
            # Borrows created for arguments are released after the call completes
            # (unless the reference escapes, which we don't track yet)
            self._check_expr(expr.func, is_move_context=False)

            # Save borrow states before processing arguments
            borrow_states_before = self._save_borrow_states()

            params = (self.fn_params.get(expr.func.name)
                      if isinstance(expr.func, rast.Ident) else None)
            for i, arg in enumerate(expr.args):
                param = params[i] if params and i < len(params) else None
                self._check_expr(arg, is_move_context=not _is_lending_param(param))
                self._check_place_borrow(arg, param)

            # Release borrows that were created for this call
            # (borrows don't outlive the call unless stored somewhere)
            self._restore_borrow_states(borrow_states_before)
            self._mark_temporary(expr, is_move_context)

        elif isinstance(expr, rast.MethodCall):
            # The receiver is borrowed (auto-ref) unless the method takes it
            # by value (AGAST #2239). An argument moves when every method of
            # that name takes it by value.
            self._check_expr(expr.expr, is_move_context=self._method_takes_self(expr))
            self._check_ref_receiver(expr)
            if not self._method_lends_self(expr):
                # A temporary receiver taken by value is moved, not dropped.
                self._unmark_temporary(expr.expr)
            borrow_states_before = self._save_borrow_states()
            # `E.V(args)` builds a variant, which owns its payload.
            is_variant = self.types.variant_value_type(
                expr, lambda n: self.scope.lookup(n) is not None) is not None
            for i, arg in enumerate(expr.args):
                self._check_expr(arg, is_move_context=is_variant or self._method_arg_moves(expr, i))
                self._check_place_borrow(arg, self._method_param(expr, i))
            self._restore_borrow_states(borrow_states_before)
            self._mark_temporary(expr, is_move_context)

        elif isinstance(expr, rast.Grouped):
            self._check_expr(expr.expr, is_move_context=is_move_context)

        elif isinstance(expr, rast.Field) and self._field_owner(expr) is not None:
            self._check_owned_field(expr, self._field_owner(expr), is_move_context)

        elif isinstance(expr, rast.Field):
            # Field access doesn't move the struct (unless the result is moved)
            self._check_expr(expr.expr, is_move_context=False)
            if is_move_context and self._through_reference(expr):
                if self.types.is_move_only(self._field_path_type(expr)):
                    self._reject_move_out(expr.span)
            elif is_move_context and self.types.is_move_only(self._field_path_type(expr)):
                # Moving a move-only field out of a temporary: the rest of
                # the temporary isn't dropped either (no partial drops).
                while isinstance(expr, rast.Field):
                    expr = expr.expr
                self._unmark_temporary(expr)

        elif isinstance(expr, rast.Index):
            self._check_expr(expr.expr, is_move_context=False)
            self._check_expr(expr.index, is_move_context=False)
            if is_move_context and self._through_reference(expr) \
                    and self.types.is_move_only(self._place_type(expr)):
                self._reject_move_out(expr.span)

        elif isinstance(expr, rast.StructLit):
            field_types = dict(self.types.struct_fields(
                rast.NamedType(expr.span, expr.name, expr.type_args)))
            for name, value in expr.fields:
                self._note_ref_slot(field_types.get(name), value)
                self._check_expr(value, is_move_context=True)
            self._mark_temporary(expr, is_move_context)

        elif isinstance(expr, (rast.ArrayLit, rast.TupleLit)):
            # The literal owns its elements, wherever the literal itself
            # goes (AGAST #2238).
            for element in expr.elements:
                self._check_expr(element, is_move_context=True)
            self._mark_temporary(expr, is_move_context)

        elif isinstance(expr, rast.Match):
            # What a reference reaches stays its owner's: matching it only reads.
            self._check_expr(expr.expr,
                             is_move_context=not self._through_reference(expr.expr))
            # The match owns a scrutinee it moved (AGAST #2177, ritz1 #2174).
            owned = self._owned_scrutinee_type(expr.expr)
            expr.owns_scrutinee = owned
            # Each arm starts from the state before the match. After it, a
            # binding is moved if an arm that falls through moved it; an arm
            # that leaves (`break`, `return`, ...) took its moves with it.
            before = self._snapshot()
            outs = []
            for arm in expr.arms:
                self._restore(before)
                self._push_scope()
                # Pattern bindings
                self._check_pattern(arm.pattern)
                if owned is not None:
                    self._own_payload(arm, owned)
                if isinstance(arm.body, rast.Block):
                    left = self._check_block(arm.body)
                else:
                    self._check_expr(arm.body, is_move_context=is_move_context)
                    left = isinstance(arm.body, (rast.BreakExpr, rast.ContinueExpr,
                                                 rast.ReturnExpr))
                self._pop_scope()
                if not left:
                    outs.append(self._snapshot())
            if outs:
                self._restore(self._join(outs))

        elif isinstance(expr, rast.BreakExpr):
            self._note_loop_exit('breaks')

        elif isinstance(expr, rast.ContinueExpr):
            self._note_loop_exit('continues')

        elif isinstance(expr, rast.ReturnExpr):
            if expr.value is not None:
                self._note_ref_slot(self.current_ret_type, expr.value)
                self._check_expr(expr.value, is_move_context=True)

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
                    for name, (then_state, then_move_span, then_fields) in states_after_then.items():
                        else_info = states_after_else.get(name)
                        if else_info:
                            else_state, else_move_span, else_fields = else_info
                            var_info = self.scope.lookup(name)
                            # If moved in either branch, mark as moved
                            if then_state == VarState.MOVED or else_state == VarState.MOVED:
                                if var_info:
                                    var_info.state = VarState.MOVED
                                    var_info.move_span = then_move_span or else_move_span
                            # Likewise a field moved out in either (AGAST #2171).
                            if var_info:
                                merged = dict(then_fields)
                                for fname, fspan in else_fields.items():
                                    merged.setdefault(fname, fspan)
                                var_info.moved_fields = merged
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
                               rast.CStringLit, rast.BoolLit, rast.CharLit)):
            pass

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
        bindings, and `var x = a[0]` staying unknown there is #2268."""
        if isinstance(expr, rast.Grouped):
            return self._place_type(expr.expr)
        if isinstance(expr, rast.UnaryOp) and expr.op == '*':
            held = self.types.resolve(self._place_type(expr.operand))
            # `*t` of a `t:& T` is t's value, and t's type is already T.
            return held.inner if isinstance(held, (rast.PtrType, rast.RefType)) else held
        if isinstance(expr, rast.Index):
            held = self.types.resolve(self._place_type(expr.expr))
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

    def _through_reference(self, expr: rast.Expr) -> bool:
        """Does the place `expr` lie behind an `@T`, `@&T`, `*T` or `:&`? Its
        value then has an owner elsewhere, so it can't be moved out."""
        while True:
            if isinstance(expr, rast.Grouped):
                expr = expr.expr
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

    def _note_ref_slot(self, slot: Optional[rast.Type],
                       value: Optional[rast.Expr]) -> None:
        """`value` lands in a `slot`-typed place. A `name:& T` parameter that
        reaches a reference there lends itself on rather than moves out (AGAST
        #1302, #2249). Whether a tail still names the parameter is up to
        _check_expr: only there is an arm's own binding in scope."""
        for tail, tail_slot in slot_tails(slot, value, self.types.resolve):
            if (isinstance(tail, rast.Ident)
                    and isinstance(tail_slot, (rast.RefType, rast.PtrType))):
                self._ref_tails.add(id(tail))

    def _hold_reborrows(self, slot: Optional[rast.Type], value: rast.Expr) -> None:
        """A `name:& T` parameter bound to a reference is borrowed from here
        on, exactly as `@name` / `@&name` would be (§13.5's first rule). A raw
        pointer isn't tracked, whichever way it's spelled."""
        held = {}
        for tail, tail_slot in slot_tails(slot, value, self.types.resolve):
            if (isinstance(tail, rast.Ident) and isinstance(tail_slot, rast.RefType)
                    and self._lent_param(tail) is not None):
                held[(tail.name, tail_slot.mutable)] = tail
        for (_, mutable), tail in held.items():
            self._check_borrow(tail, mutable=mutable, span=tail.span)

    def _assign_slot_type(self, target: rast.Expr) -> Optional[rast.Type]:
        """The type of the slot `target = ...` writes, element or otherwise."""
        if not isinstance(target, rast.Index):
            return self._field_path_type(target)
        base = self.types.resolve(self._assign_slot_type(target.expr))
        return base.inner if isinstance(base, (rast.ArrayType, rast.PtrType)) else None

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
            return next((t for n, t in self.types.struct_fields(owner) if n == part), None)
        return None

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

    def _field_owner(self, expr: rast.Field) -> Optional[VarInfo]:
        """The binding `expr` (`b.f`, `b.f.g`) is a field of, when the binding
        holds that field by value (_path_owners). None otherwise, as for
        `h.0` of a struct: a positional read, so a use of all of `h`."""
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
            self.errors.append(OwnershipError(
                f"use of moved value: `{name}` (moved at {info.move_span})",
                expr.span))
            return
        for moved, moved_at in info.moved_fields.items():
            if path_within(path, moved) or path_within(moved, path):
                self.errors.append(OwnershipError(
                    f"use of moved value: `{name}.{moved}` (moved at {moved_at})",
                    expr.span))
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

    def _receiver_type(self, expr: rast.Expr) -> Optional[rast.Type]:
        """The type of a method receiver, looking through `*r`."""
        if isinstance(expr, rast.UnaryOp) and expr.op == '*':
            # `*t` of a `t:& T` is t's value, and t's type is already T.
            return self._receiver_type(expr.operand)
        return self.types.resolve(self._field_path_type(expr))

    def _method_return_type(self, call: rast.MethodCall) -> Optional[rast.Type]:
        """The type `call` returns, for `Type.method()` or `value.method()`,
        looked up on the receiver's own type with the impl's type parameters
        replaced by the receiver's arguments. None when the type doesn't
        declare the method or its impls disagree on the return type."""
        recv = call.expr
        if isinstance(recv, rast.Ident) and self.scope.lookup(recv.name) is None:
            ty = rast.NamedType(recv.span, recv.name, [])
        else:
            ty = self._receiver_type(recv)
        while isinstance(ty, (rast.PtrType, rast.RefType)):
            ty = self.types.resolve(ty.inner)
        if not isinstance(ty, rast.NamedType):
            return None
        rets: Dict[str, rast.Type] = {}
        for m in self.type_methods.get((ty.name, call.method), []):
            subst = dict(zip(self.method_impl[id(m)].type_params, ty.args))
            subst['Self'] = ty
            ret = _subst(m.ret_type, subst)
            rets[_type_key(ret)] = ret
        return next(iter(rets.values())) if len(rets) == 1 else None

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
        """Does argument `i` of `call` move? Only if every same-named method
        takes it by value; unknown methods lend (no move, no drop-flag clear)."""
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
        if not isinstance(arg, rast.Ident):
            return
        info = self.scope.lookup(arg.name)
        if info is None or info.state == VarState.MOVED:
            return    # already reported by _check_expr
        held = self.types.resolve(info.ritz_type)
        wanted = self.types.resolve(param.type)
        if (isinstance(held, (rast.RefType, rast.PtrType))
                and not isinstance(wanted, (rast.RefType, rast.PtrType))):
            return
        self._check_borrow(arg, mutable=True, span=arg.span)

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
                if var_info.moved_fields:
                    fname = next(iter(var_info.moved_fields))
                    self.errors.append(OwnershipError(
                        f"cannot borrow `{expr.name}` - `{expr.name}.{fname}` has been moved",
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
            return None
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
