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
import array_rules
import ref_rules
import ritz_ast as rast
from ufcs import UFCS_NON_GENERIC_PREFIXES


class OwnershipError(Exception):
    """Error for ownership/borrowing violations. `after_move` marks a use or
    a borrow of a value that already moved: at a move-only `T` a generic
    instance can do that where its generic body doesn't (AGAST #2921)."""
    def __init__(self, message: str, span = None, after_move: bool = False):
        self.span = span
        self.reason = message
        self.after_move = after_move
        if span:
            super().__init__(f"{span.file}:{span.line}:{span.column}: {message}")
        else:
            super().__init__(message)


class VarState(Enum):
    """State of a variable in the ownership system. Whether it's borrowed is
    in VarInfo.borrows."""
    OWNED = auto()       # Variable owns its value
    MOVED = auto()       # Value has been moved out


@dataclass(eq=False)
class Loan:
    """An `@` or `@&` of a place, on the place's root (AGAST #2438). One made
    inside a statement ends with it; `holder` is the binding a declaration gave
    it to, and it ends with that binding's block (_pop_scope)."""
    span: Optional[rast.Span]
    mutable: bool
    holder: Optional['VarInfo'] = field(default=None, repr=False)
    # The place's steps below the root: a field's name, or '[]' for an index
    # (R11a: any two indexes count as equal). `@c.x` is ('x',).
    path: Tuple[str, ...] = ()


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
    # The loans of this binding, or of a place in it, still active.
    borrows: List[Loan] = field(default_factory=list)
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



def _element_of(ty: Optional[rast.Type]) -> Optional[rast.Type]:
    """What `[]` reads from a Vec<T> or Span<T> (T) or a String (u8), else
    None. The emitter's twin is Emitter._buffer_field_path."""
    if not isinstance(ty, rast.NamedType):
        return None
    if ty.name in ('Vec', 'Span') and len(ty.args) == 1:
        return ty.args[0]
    if ty.name == 'String' and not ty.args:
        return rast.NamedType(ty.span, 'u8', [])
    return None


def _lends_mut(param: rast.Param) -> bool:
    """`name:& T` or `name: @&T`: a mutable borrow of the argument's place.
    Not `*T` (#2371) or `@T`."""
    if getattr(param, 'borrow', None) == rast.Borrow.MUTABLE:
        return True
    return isinstance(param.type, rast.RefType) and param.type.mutable

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
        self.derefs: Dict[str, rast.ImplBlock] = {}   # `impl Deref for S` (§7.7)
        for item in module.items:
            if isinstance(item, rast.ImplBlock) and item.trait_name == 'Deref':
                self.derefs[item.type_name] = item
            if isinstance(item, rast.ImplBlock) and item.trait_name == 'Drop':
                self.drop_types.add(item.type_name)
            elif isinstance(item, rast.StructDef):
                self.structs[item.name] = item
            elif isinstance(item, rast.EnumDef):
                self.enums[item.name] = item
            elif isinstance(item, rast.TypeAlias):
                self.aliases[item.name] = item.target
        # The type parameters of the generic fn or impl being checked. They
        # shadow any type of the same name (AGAST #2966): in `fn take<T>` the
        # `T` is the parameter, a copy type here, not a `struct T`.
        self.params: frozenset = frozenset()
        self._caches: dict[frozenset, dict[str, bool]] = {}
        self._cache: dict[str, bool] = self._caches.setdefault(self.params, {})

    def set_params(self, names) -> None:
        """Check under the type parameters `names` (empty outside a generic).
        Each set keeps its own cache: `Wrap<T>` differs with `T` shadowed."""
        self.params = frozenset(names)
        self._cache = self._caches.setdefault(self.params, {})

    def _is_param(self, ty: rast.Type | None) -> bool:
        return isinstance(ty, rast.NamedType) and not ty.args and ty.name in self.params

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
            if self._is_param(ty):
                return False
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

    def deref_target(self, ty: rast.NamedType) -> Optional[rast.Type]:
        """The T `impl Deref for S` reaches (its `deref`'s `@T`), at `ty`'s
        type arguments; None when S doesn't implement `Deref` (§7.7)."""
        impl = self.derefs.get(ty.name)
        if impl is None:
            return None
        for m in impl.methods:
            if m.name == 'deref' and isinstance(m.ret_type, (rast.RefType, rast.PtrType)):
                params = [a.name for a in impl.impl_type.args
                          if isinstance(a, rast.NamedType)] if impl.impl_type else []
                return _subst(m.ret_type.inner, dict(zip(params, ty.args)))
        return None

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
        Each is checked on a copy: the emitter reads the marks `check` leaves,
        and giving an instance its own is #2263's change, not this one."""
        self.errors = []
        self._collect(module)
        fns = [item for item in module.items if isinstance(item, rast.FnDef)]
        for item in module.items:
            if isinstance(item, rast.ImplBlock):
                fns.extend(item.methods)
        for fn in fns:
            if any(self.types.is_move_only(a) for a in getattr(fn, 'instance_args', ())):
                self._check_fn(copy.deepcopy(fn))
        self.errors = [e for e in self.errors
                       if e.reason in (ref_rules.MOVE_OUT_OF_REF, array_rules.FILL_MOVE_ONLY)
                       or e.after_move]
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
                    if item.trait_name == 'Drop' and m.name == 'drop' and m.params \
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
        """Exit current scope. The loans its bindings hold end here: a loan
        lasts to the end of its holder's block (AGAST #2438)."""
        gone = {id(info) for info in self.scope.vars.values()}
        scope = self.scope.parent
        while scope:
            for info in scope.vars.values():
                info.borrows = [b for b in info.borrows
                                if b.holder is None or id(b.holder) not in gone]
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
        return name + ''.join('[_]' if s == '[]' else '' if s == '*' else f'.{s}'
                              for s in path)

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
        near = [b for b in info.borrows if self._overlap(b.path, path)]
        for b in near:
            if b.mutable:
                return b
        return near[0] if mutable and near else None

    def _report(self, name: str, path: Tuple[str, ...], loan: Loan,
                what: str, span) -> None:
        """`what` is "assign", "mutable" or "immutable"."""
        here = self._place_str(name, path)
        held = self._place_str(name, loan.path)
        kind = "mutable" if loan.mutable else "immutable"
        if what == "assign":
            head = f"cannot assign to `{here}`"
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

    def _held_borrows(self, value: Optional[rast.Expr]) -> List[rast.UnaryOp]:
        """The `@place` and `@&place` a declaration's binding holds: its value,
        or an arm's tail of an `if` or `match` value."""
        out: List[rast.UnaryOp] = []

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
                out.append(e)
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
        for e in self._held_borrows(value):
            place = self._loan_place(e.operand)
            info = self.scope.lookup(place[0]) if place is not None else None
            if info is not None and info is not holder:
                info.borrows.append(Loan(e.span, e.op in ('&mut', '@&'), holder, place[1]))

    def _release_arg_loans(self, mark: int) -> None:
        """End the argument loans made since `mark`."""
        for info, loan in self._arg_loans[mark:]:
            info.borrows = [b for b in info.borrows if b is not loan]
        del self._arg_loans[mark:]

    def _check_fn(self, fn: rast.FnDef):
        """Check a function definition."""
        impl = self.method_impl.get(id(fn))
        self.types.set_params(list(fn.type_params or [])
                              + list((impl.type_params or []) if impl else []))
        try:
            self._check_fn_body(fn)
        finally:
            self.types.set_params(())

    def _check_fn_body(self, fn: rast.FnDef):
        self.current_fn_name = fn.name
        self._field_moves = set()
        self._push_scope()

        # Parameters are owned at function start
        # For borrow semantics tracking, we need to store the borrow kind
        # along with the type so _is_copy_type can know if it's a reference
        for param in fn.params:
            self.scope.define(param.name, param.type, param.span, borrow=param.borrow)

        # Check function body (which is a Block)
        self.current_ret_type = fn.ret_type
        self._check_block(fn.body)

        self._pop_scope()
        fn.field_moves = self._field_moves
        self.current_fn_name = None

    def _check_block(self, block: rast.Block) -> bool:
        """Check a block expression.

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
                self._check_expr(block.expr, is_move_context=True)
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
                moved = self._moved_in_defer(stmt, scope)
                if moved is not None:
                    if id(stmt) not in self._refused_defers:
                        self._refused_defers.add(id(stmt))
                        self.errors.append(OwnershipError(
                            f"`{moved}` may be moved before the deferred statement runs",
                            stmt.span))
                    continue
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
            self._hold_loans(self.scope.vars[stmt.name], stmt.value, stmt.type)
            return False

        elif isinstance(stmt, rast.LetStmt):
            # Let binding.
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
            self._hold_loans(self.scope.vars[stmt.name], stmt.value, stmt.type)
            return False

        elif isinstance(stmt, rast.ExprStmt):
            self._check_expr(stmt.expr, is_move_context=False)
            return False

        elif isinstance(stmt, rast.AssertStmt):
            # Its condition is checked like any expression, as on ritz1: a
            # call's `@&s, @s` is the same conflict there (AGAST #2438).
            self._check_expr(stmt.condition, is_move_context=False)
            return False

        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                self._check_expr(stmt.value, is_move_context=True)
            self._run_defers(0)
            # Return terminates this control flow path
            return True

        elif isinstance(stmt, rast.DeferStmt):
            # Nothing runs here: it's checked at each exit (_run_defers).
            if self._defers:
                self._defers[-1].append((stmt, self.scope))
            return False

        elif isinstance(stmt, rast.AssignStmt):
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
            self._run_loop_defers()
            self._note_loop_exit('breaks')
            return True

        elif isinstance(stmt, rast.ContinueStmt):
            self._run_loop_defers()
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

        elif isinstance(expr, rast.MethodCall):
            # The receiver is borrowed (auto-ref) unless the method takes it
            # by value (AGAST #2239). An argument moves when every method of
            # that name takes it by value.
            self._check_expr(expr.expr, is_move_context=self._method_takes_self(expr)
                             or self._takes_place_behind(expr))
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

        elif isinstance(expr, rast.Grouped):
            self._check_expr(expr.expr, is_move_context=is_move_context)

        elif isinstance(expr, rast.Field) and is_move_context and self._through_deref(expr) \
                and self.types.is_move_only(self._part_type(
                    self.types.resolve(self._loan_type(expr.expr)), expr.field)):
            # `deref` lends the T: its move-only field can't be taken (§7.7).
            self._check_expr(expr.expr, is_move_context=False)
            self._reject_move_out(expr.span)

        elif isinstance(expr, rast.Field) and self._field_owner(expr) is not None:
            self._check_owned_field(expr, self._field_owner(expr), is_move_context)

        elif isinstance(expr, rast.Field):
            # Field access doesn't move the struct (unless the result is moved)
            self._check_expr(expr.expr, is_move_context=False)
            if is_move_context and self._through_reference(expr):
                # `p[i].f`: _field_path_type doesn't type an element (#2444).
                if self.types.is_move_only(self._field_path_type(expr) or self._place_type(expr)):
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
            for _, value in expr.fields:
                self._check_expr(value, is_move_context=True)
            self._mark_temporary(expr, is_move_context)

        elif isinstance(expr, (rast.ArrayLit, rast.TupleLit)):
            # The literal owns its elements, wherever the literal itself
            # goes (AGAST #2238).
            for element in expr.elements:
                self._check_expr(element, is_move_context=True)
            self._mark_temporary(expr, is_move_context)

        elif isinstance(expr, rast.ArrayFill):
            # `[v; n]` owns its value like a literal owns its elements, so
            # `[t; 2]` with `t:& Res` moves out of the reference (AGAST #2948).
            self._check_expr(expr.value, is_move_context=True)
            # It copies that one value into each element: n > 1 of a
            # move-only one would drop it n times (AGAST #2963).
            if expr.count > 1 and self.types.is_move_only(self._fill_value_type(expr.value)):
                self.errors.append(OwnershipError(array_rules.FILL_MOVE_ONLY, expr.span))

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
            mark = len(self._arg_loans)
            for arm in expr.arms:
                self._restore(before)
                self._release_arg_loans(mark)
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
            self._run_loop_defers()
            self._note_loop_exit('breaks')

        elif isinstance(expr, rast.ContinueExpr):
            self._run_loop_defers()
            self._note_loop_exit('continues')

        elif isinstance(expr, rast.ReturnExpr):
            if expr.value is not None:
                self._check_expr(expr.value, is_move_context=True)
            self._run_defers(0)

        elif isinstance(expr, rast.TryOp):
            self._check_expr(expr.expr, is_move_context=is_move_context)
            # The Err path returns through every block's defers; the Ok path
            # goes on, so their moves don't carry past the `?`.
            if self._defers and any(self._defers):
                snap = self._snapshot()
                self._run_defers(0)
                self._restore(snap)

        elif isinstance(expr, rast.Cast):
            # `v as T` hands its operand's value on: it moves wherever the
            # cast does (AGAST #2948; `t as Res` with `t:& Res` copied out).
            self._check_ref_cast(expr)
            self._check_expr(expr.expr, is_move_context=is_move_context)

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

    def _fill_value_type(self, value: rast.Expr) -> Optional[rast.Type]:
        """The type of a fill's value: a binding, call or literal as
        `_infer_expr_type` has it, else a place (`*p`, `p[i]`)."""
        ty = self._infer_expr_type(value)
        if isinstance(ty, rast.NamedType) and ty.name == 'unknown':
            return self._place_type(value)
        return ty

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
        return self._takes_self_by_value(self.types.resolve(self._place_type(call.expr)),
                                         call.method)

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
                expr.span, after_move=True))
            return
        for moved, moved_at in info.moved_fields.items():
            if path_within(path, moved) or path_within(moved, path):
                self.errors.append(OwnershipError(
                    f"use of moved value: `{name}.{moved}` (moved at {moved_at})",
                    expr.span, after_move=True))
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

    # The free function `v.m()` means on a type with no `m` of its own: Vec's
    # `vec_m`, String's `string_m` (ufcs.py has the emitter's table).
    UFCS_PREFIXES = {'Vec': 'vec_', 'Span': 'span_', 'Option': 'option_',
                     'Result': 'result_', 'Box': 'box_', **UFCS_NON_GENERIC_PREFIXES}

    def _lends_self_mut(self, call: rast.MethodCall) -> bool:
        """Does `call` take its receiver `self: @&T`, `self:& T`, or as a UFCS
        function's first param of either kind? A mutable borrow of the
        receiver's place (AGAST #2438). False where the callee is unknown."""
        ty = self._receiver_type(call.expr)
        if not isinstance(ty, rast.NamedType):
            return False
        cands = [list(m.params) for m in self.type_methods.get((ty.name, call.method)) or []]
        if cands:
            cands = [ps for ps in cands if ps and ps[0].name == 'self']
        else:
            prefix = self.UFCS_PREFIXES.get(ty.name)
            params = self.fn_params.get(f"{prefix}{call.method}") if prefix else None
            cands = [params] if params else []
        return bool(cands) and all(ps and _lends_mut(ps[0]) for ps in cands)

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
                    self.errors.append(OwnershipError(
                        f"cannot borrow `{expr.name}` - value has been moved",
                        span, after_move=True
                    ))
                    return
                if var_info.moved_fields:
                    fname = next(iter(var_info.moved_fields))
                    self.errors.append(OwnershipError(
                        f"cannot borrow `{expr.name}` - `{expr.name}.{fname}` has been moved",
                        span, after_move=True
                    ))
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
