"""What monomorph.py and its mixins share: the inference errors, the type
substitution and type-param unification, the AST child map, and name
mangling (with the module's type aliases it reads while a pass runs).
Split out of monomorph.py (AGAST #3522); monomorph re-exports every name
here, so `from monomorph import ...` is unchanged."""

import contextlib
import copy
import dataclasses
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

import ritz_ast as rast


class GenericInferError(Exception):
    """A generic call whose type args its arguments don't determine (AGAST
    #1982).  The message carries `file:line:column`, as ritz1's does."""

    def __init__(self, message: str, span=None):
        self.span = span
        self.reason = message
        if span is not None:
            message = f"{span.file}:{span.line}:{span.column}: {message}"
        super().__init__(message)


class InstantiationRecursionError(GenericInferError):
    """Instantiation that never reaches a fixpoint (AGAST #3330).

    `impl<T> Cell<T>  fn wrap(..) -> Cell<Cell<T>>`: every method of a
    generic impl is specialised for each instance, so each instance names a
    deeper one.  Located at the generic impl, as ritz1's is."""


# How many generations of instances one instantiation may discover before it
# is refused as recursive (AGAST #3330).  An instance named in the program is
# generation 0; one first named while specialising a generation-g instance is
# g + 1.  ritz1 uses the same cap (monomorph.ritz, MAX_INSTANCE_DEPTH).
MAX_INSTANCE_DEPTH = 64


def map_child_nodes(node, on_expr, on_stmt, on_type):
    """Rebuild `node` with on_expr / on_stmt / on_type applied to its children.

    The fallback for every AST kind the monomorph walks have no dedicated case
    for.  Each dataclass field is mapped by kind: an Expr (Block included) goes
    through on_expr, a Stmt through on_stmt, a Type through on_type; lists and
    tuples are mapped element-wise; any other dataclass (MatchArm, Pattern,
    Param, AsmOperand) is walked recursively.  Spans and plain
    values are kept.

    Returns `node` itself when nothing beneath it changed, otherwise a shallow
    copy with the changed fields replaced — never mutates `node`, which is the
    generic template shared by every instantiation.

    Before AGAST #1937 the fallback was `return node`, so sizeof(T), casts and
    generic calls inside Match, Grouped, TupleLit, InterpString, ...
    kept the template's T.
    """
    def map_value(value):
        if isinstance(value, rast.Expr):
            return on_expr(value)
        if isinstance(value, rast.Stmt):
            return on_stmt(value)
        if isinstance(value, rast.Type):
            return on_type(value)
        if isinstance(value, list):
            new = [map_value(v) for v in value]
            return value if all(a is b for a, b in zip(new, value)) else new
        if isinstance(value, tuple):
            new = tuple(map_value(v) for v in value)
            return value if all(a is b for a, b in zip(new, value)) else new
        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return map_child_nodes(value, on_expr, on_stmt, on_type)
        return value

    changes = {}
    for f in dataclasses.fields(node):
        if f.name == "span":
            continue
        old = getattr(node, f.name)
        new = map_value(old)
        if new is not old:
            changes[f.name] = new
    if not changes:
        return node
    new_node = copy.copy(node)
    for name, value in changes.items():
        setattr(new_node, name, value)
    return new_node


@dataclass
class TypeSubstitution:
    """A mapping from type parameter names to concrete types."""
    mapping: Dict[str, rast.Type]
    # Optional: generic struct names -> mangled names after substitution
    struct_manglings: Dict[str, Dict[Tuple[str, ...], str]] = None

    def bare(self, ty: rast.Type) -> rast.Type:
        """`ty` with the type parameters substituted, and no instance renamed.

        This is the type an instance is keyed by: Box<Box<i32>> is keyed
        `Box_i32`, as _type_args_to_key spells it, not by its renamed
        argument `Box$i32` (AGAST #3080, #3342).
        """
        return TypeSubstitution(self.mapping).apply(ty)

    def apply(self, ty: rast.Type) -> rast.Type:
        """Apply substitution to a type, returning a new type."""
        if isinstance(ty, rast.NamedType):
            # Check if this is a type parameter
            if ty.name in self.mapping and not ty.args:
                concrete = copy.deepcopy(self.mapping[ty.name])
                # A parameter bound to an instance (T = Cell<Cell<i32>>) is
                # renamed to it like a spelled-out one, or the generic type
                # reaches the emitter, which finds no struct for it and lowers
                # the field as i8 (AGAST #3342).
                if self.struct_manglings:
                    return TypeSubstitution({}, self.struct_manglings).apply(concrete)
                return concrete
            # Otherwise, apply to any type arguments
            new_args = [self.apply(arg) for arg in ty.args]

            # If this is a generic struct with type args, mangle the name
            if new_args and self.struct_manglings and ty.name in self.struct_manglings:
                args_key = tuple(mangle_type_name(self.bare(arg)) for arg in ty.args)
                mangled = self.struct_manglings[ty.name].get(args_key)
                if mangled:
                    return rast.NamedType(ty.span, mangled, [])

            return rast.NamedType(ty.span, ty.name, new_args)
        elif isinstance(ty, rast.PtrType):
            return rast.PtrType(ty.span, self.apply(ty.inner), ty.mutable)
        elif isinstance(ty, rast.RefType):
            return rast.RefType(ty.span, self.apply(ty.inner), ty.mutable)
        elif isinstance(ty, rast.ArrayType):
            return rast.ArrayType(ty.span, ty.size, self.apply(ty.inner))
        elif isinstance(ty, rast.FnType):
            new_params = [self.apply(p) for p in ty.params]
            new_ret = self.apply(ty.ret) if ty.ret else None
            return rast.FnType(ty.span, new_params, new_ret, ty.callconv)
        # A type parameter inside a tuple or SIMD vector was left
        # unsubstituted until AGAST #2741 and lowered as i8.
        elif isinstance(ty, rast.TupleType):
            return rast.TupleType(ty.span, [self.apply(e) for e in ty.elements])
        elif isinstance(ty, rast.VectorType):
            return rast.VectorType(ty.span, ty.count, self.apply(ty.inner))
        else:
            return ty


# Type aliases of the module being monomorphized: name -> target type.  Set by
# monomorphize() for the duration of one pass.  Aliases are transparent, so
# mangle_type_name spells an alias as its target (`Vec<Id>` with `type Id = u32`
# is Vec$u32, the same instantiation as `Vec<u32>`), matching ritz1 (AGAST #2049).
_TYPE_ALIASES: Dict[str, rast.Type] = {}


def resolve_alias(ty: rast.Type) -> rast.Type:
    """Follow a bare alias name (and alias-of-alias chains) to its target."""
    return resolve_alias_in(ty, _TYPE_ALIASES)


def resolve_alias_in(ty: rast.Type, aliases: Dict[str, rast.Type]) -> rast.Type:
    """Follow a bare alias name through `aliases` (chains included)."""
    seen = set()
    while (isinstance(ty, rast.NamedType) and not ty.args
           and ty.name in aliases and ty.name not in seen):
        seen.add(ty.name)
        ty = aliases[ty.name]
    return ty


def is_int_literal(expr) -> bool:
    """`3` or `-3`: an argument that binds a bare `T` only when nothing else
    does (LANGUAGE_SPEC §4.4)."""
    return (isinstance(expr, rast.IntLit)
            or (isinstance(expr, rast.UnaryOp) and expr.op == '-'
                and isinstance(expr.operand, rast.IntLit)))


def unify_type_params(param: rast.Type, arg: rast.Type, params: List[str],
                      bound: Dict[str, rast.Type], conflict: Set[str],
                      resolve=None) -> None:
    """Match a param type against an argument type, binding `params` in
    `bound`; a param bound to two different types goes in `conflict`.
    Matched structurally: `T`, `@T`, `*T`, `Vec<T>`, `[N]T`, tuples."""
    resolve = resolve or resolve_alias
    param = resolve(param)
    arg = resolve(arg)
    if isinstance(param, rast.NamedType) and param.name in params and not param.args:
        prev = bound.get(param.name)
        if prev is None:
            bound[param.name] = arg
        elif mangle_type_name(resolve(prev)) != mangle_type_name(arg):
            conflict.add(param.name)
        return
    ptrs = (rast.PtrType, rast.RefType)
    if isinstance(param, ptrs) and isinstance(arg, ptrs):
        unify_type_params(param.inner, arg.inner, params, bound, conflict, resolve)
    elif isinstance(param, rast.NamedType) and isinstance(arg, rast.NamedType):
        if param.name == arg.name and len(param.args) == len(arg.args):
            for p, a in zip(param.args, arg.args):
                unify_type_params(p, a, params, bound, conflict, resolve)
    elif isinstance(param, rast.ArrayType) and isinstance(arg, rast.ArrayType):
        unify_type_params(param.inner, arg.inner, params, bound, conflict, resolve)
    elif isinstance(param, rast.TupleType) and isinstance(arg, rast.TupleType):
        if len(param.elements) == len(arg.elements):
            for p, a in zip(param.elements, arg.elements):
                unify_type_params(p, a, params, bound, conflict, resolve)


def bind_type_params(params: List[str], pairs, resolve=None):
    """(bound, conflict): the type params `params` that the arguments bind.

    `pairs` is (param type, argument, argument's type or None) per argument,
    by section 4.4's rule for a generic call: each argument binds each T its
    parameter's type mentions, and an integer literal binds a bare `T` only
    when no other argument binds T (`vec_push(@&v, 3)` on a Vec<i32> is
    vec_push<i32>)."""
    resolve = resolve or resolve_alias
    bound: Dict[str, rast.Type] = {}
    conflict: Set[str] = set()
    literal: Dict[str, rast.Type] = {}
    for param_type, arg, arg_type in pairs:
        if param_type is None:
            continue
        if is_int_literal(arg):
            p = resolve(param_type)
            if (isinstance(p, rast.NamedType) and p.name in params and not p.args
                    and arg_type is not None):
                literal.setdefault(p.name, arg_type)
            continue
        if arg_type is not None:
            unify_type_params(param_type, arg_type, params, bound, conflict, resolve)
    for name, ty in literal.items():
        bound.setdefault(name, ty)
    return bound, conflict


def mangle_type_name(ty: rast.Type) -> str:
    """Generate a mangled name component for a type.

    A type alias mangles as its target (AGAST #2049).

    Examples:
        i32 -> "i32"
        *u8 -> "ptr_u8"
        *mut i32 -> "ptr_i32" (LARB R74: `*mut T` is a spelling of `*T`)
        Vec<i32> -> "Vec_i32"
    """
    ty = resolve_alias(ty)
    if isinstance(ty, rast.NamedType):
        if ty.args:
            arg_names = "_".join(mangle_type_name(arg) for arg in ty.args)
            return f"{ty.name}_{arg_names}"
        return ty.name
    elif isinstance(ty, rast.PtrType):
        # `*mut T` is another spelling of `*T` (LARB R74, AGAST #3959): one
        # type, so one mangled name and one instance.
        return f"ptr_{mangle_type_name(ty.inner)}"
    elif isinstance(ty, rast.RefType):
        if ty.mutable:
            return f"refmut_{mangle_type_name(ty.inner)}"
        return f"ref_{mangle_type_name(ty.inner)}"
    elif isinstance(ty, rast.ArrayType):
        return f"arr{_folded_array_size(ty)}_{mangle_type_name(ty.inner)}"
    # Every type below fell through to "unknown" until AGAST #2270, so e.g.
    # `wrap<Result<(), E>>` and `wrap<Result<(i64, i64), E>>` were one
    # instantiation and a valid program was rejected.
    elif isinstance(ty, rast.TupleType):
        # Spelled as the emitter's `_type_to_name_suffix` spells it, so a tuple
        # has one name whether or not the monomorphizer routes it.
        if not ty.elements:
            return "unit"
        return "tuple_" + "_".join(mangle_type_name(e) for e in ty.elements)
    elif isinstance(ty, rast.FnType):
        # The arity and `ret` marker keep params and return type apart:
        # fn(i32) -> i64 is fn1_i32_ret_i64, fn(i64) -> i32 is fn1_i64_ret_i32.
        params = "".join(f"_{mangle_type_name(p)}" for p in ty.params)
        ret = mangle_type_name(ty.ret) if ty.ret is not None else "unit"
        return f"fn{len(ty.params)}{params}_ret_{ret}"
    elif isinstance(ty, rast.VectorType):
        return f"vec{ty.count}_{mangle_type_name(ty.inner)}"
    # A shared fallback name is what made distinct types collide: a new Type
    # node must be given a spelling here.
    raise TypeError(f"mangle_type_name: no spelling for {type(ty).__name__}")


def _folded_array_size(ty: rast.ArrayType) -> int:
    """The integer size of `[N]T`, as a mangled name spells it (AGAST #2843).

    Const eval folds every size to an int (AGAST #2857 made it reach a call's
    type argument, `first<*[2]i8>`).  Printing an unfolded node put
    `IntLit(span=/path/main.ritz:10:27, value=2)` in the symbol, so the IR
    named the build path; an unfolded size is a const-eval bug, so it raises.
    """
    size = ty.size
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError(
            f"mangle_type_name: array size {type(size).__name__} is not folded")
    return size


def mangle_generic_name(base_name: str, type_args: List[rast.Type]) -> str:
    """Generate a mangled name for a generic instantiation.

    Uses '$' separator between function name and type args to avoid collisions.
    For example, vec_get<*u8> becomes vec_get$ptr_u8, not vec_get_ptr_u8
    (which would collide with vec_get_ptr<u8>).

    Examples:
        Pair<i32> -> "Pair$i32"
        Vec<*u8> -> "Vec$ptr_u8"
        Map<i32, *u8> -> "Map$i32_ptr_u8"
    """
    if not type_args:
        return base_name
    arg_names = "_".join(mangle_type_name(arg) for arg in type_args)
    return f"{base_name}${arg_names}"


@contextlib.contextmanager
def type_aliases(module: rast.Module):
    """Make `module`'s type aliases the ones resolve_alias / mangle_type_name
    follow, for the duration of one pass, restoring the previous set after."""
    global _TYPE_ALIASES
    saved = _TYPE_ALIASES
    _TYPE_ALIASES = {item.name: item.target for item in module.items
                     if isinstance(item, rast.TypeAlias)}
    try:
        yield
    finally:
        _TYPE_ALIASES = saved


def _names_type_param(ty, params) -> bool:
    """Whether type `ty` names any of `params` anywhere inside it: a field or
    parameter type that names none is fully known, a slot even while the
    params are being inferred (LARB R51a).  `Pair<u8, A>` names A: partly
    known counts as not known.  An alias is resolved first."""
    if not params or ty is None:
        return False
    if isinstance(ty, (list, tuple)):
        return any(_names_type_param(t, params) for t in ty)
    if not dataclasses.is_dataclass(ty) or isinstance(ty, type):
        return False
    if isinstance(ty, rast.NamedType):
        if ty.name in params and not ty.args:
            return True
        resolved = resolve_alias(ty)
        if resolved is not ty:
            return _names_type_param(resolved, params)
    return any(_names_type_param(getattr(ty, f.name), params)
               for f in dataclasses.fields(ty) if f.name != 'span')