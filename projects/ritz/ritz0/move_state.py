"""
The move checker's state: ownership errors, binding states, loans, scopes,
and which types are move-only (MoveTypes, LANGUAGE_SPEC §13.1).

Split out of move_checker.py (LARB review/5 ritz0 N2, AGAST #3449) so the
checker (move_checker.py) and its per-node-kind walk (move_walk.py) can both
import it.  move_checker re-exports every name here.
"""

from typing import Dict, Set, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum, auto
import ritz_ast as rast


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
    # A `for`'s loan on the place its iterable indexes into (AGAST #2439): only
    # a use of that place, or of one holding it, can move the buffer, so only
    # those conflict. `vs[0].a[2] = 50` is inside `vs` and stays legal.
    outer: bool = False


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
    # `var x: T` with no initialiser, T with drop glue (§13.6, AGAST #4033):
    # the declaration's span, which also stands as the "moved at" of each
    # part not written yet (uninit_rules.py), so `is` tells one from a move.
    uninit_span: Optional[rast.Span] = None

    def unwritten(self, span: Optional[rast.Span]) -> bool:
        """Is `span`, a moved_fields or move_span entry, "not written yet"?"""
        return span is not None and span is self.uninit_span


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
        self.index_muts: Dict[str, rast.ImplBlock] = {}   # `impl IndexMut for S` (§7.8)
        for item in module.items:
            if isinstance(item, rast.ImplBlock) and item.trait_name == 'Deref':
                self.derefs[item.type_name] = item
            if isinstance(item, rast.ImplBlock) and item.trait_name == 'IndexMut':
                self.index_muts[item.type_name] = item
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
        # Pointers, references, fn types, SIMD vectors: copies.
        return False

    def holds_reference(self, ty: Optional[rast.Type], seen: Optional[Set[str]] = None) -> bool:
        """`ty` is a pointer or reference, or a struct, enum, tuple or array
        holding one (AGAST #3215). A type parameter holds none."""
        ty = self.resolve(ty)
        if isinstance(ty, (rast.PtrType, rast.RefType)):
            return True
        if isinstance(ty, rast.ArrayType):
            return self.holds_reference(ty.inner, seen)
        if isinstance(ty, rast.TupleType):
            return any(self.holds_reference(t, seen) for t in ty.elements)
        if not isinstance(ty, rast.NamedType) or self._is_param(ty):
            return False
        seen = set() if seen is None else seen
        key = _type_key(ty)
        if key in seen:
            return False      # a recursive type: its other fields decide
        seen.add(key)
        if ty.name in self.structs:
            return any(self.holds_reference(t, seen) for _n, t in self.struct_fields(ty))
        ed = self.enums.get(ty.name)
        if ed is not None:
            subst = dict(zip(ed.type_params or [], ty.args))
            return any(self.holds_reference(_subst(t, subst), seen)
                       for v in ed.variants for t in v.fields)
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
        return self._lent_target(self.derefs.get(ty.name), 'deref', ty)

    def index_mut_target(self, ty: rast.NamedType) -> Optional[rast.Type]:
        """The element T `impl IndexMut for S` lends (its `index_mut`'s
        `@&T`), at `ty`'s type arguments; None without `IndexMut` (§7.8)."""
        return self._lent_target(self.index_muts.get(ty.name), 'index_mut', ty)

    @staticmethod
    def _lent_target(impl: Optional[rast.ImplBlock], method: str,
                     ty: rast.NamedType) -> Optional[rast.Type]:
        if impl is None:
            return None
        for m in impl.methods:
            if m.name == method and isinstance(m.ret_type, (rast.RefType, rast.PtrType)):
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
