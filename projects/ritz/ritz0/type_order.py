"""Order a module's named struct definitions so clang accepts them (AGAST #3653).

llvmlite prints a context's identified types in the order they were created.
LLVM's text parser accepts a named struct that is used before its `= type`
line almost everywhere: as a by-value struct field, as a pointee, as a function
result.  The one place it refuses is a function type's parameter:

    %"Info" = type {%"StrView" (%"StrView")*, i64}
    %"StrView" = type {i8*, i64}
    ; error: invalid type for function argument

because a forward-referenced type is still an opaque placeholder there.  ritz0
creates the builtin `StrView` lazily, the first time some type names it, and a
user struct can be declared after the struct whose fn field takes it, so the
creation order alone can't be relied on.

`order_identified_types` reorders the context's types, stably, so every struct
that a function-type parameter takes by value is defined before the struct
holding that function type.  Only those edges count: they're the only ones the
parser needs, and pointers never add one, so ordinary self-referential and
mutually-referential structs (through `*T`) still order freely.  A genuine
by-value cycle through fn parameters can't be ordered at all; the walk still
terminates, and clang reports it.
"""

from llvmlite import ir


def _param_structs(ty: ir.Type, out: list, in_param: bool) -> None:
    """Append to `out` each identified struct that `ty` holds by value in a fn-type parameter."""
    if isinstance(ty, ir.IdentifiedStructType):
        # Its own body is its own node in the ordering; don't descend.
        if in_param:
            out.append(ty)
    elif isinstance(ty, ir.FunctionType):
        for arg in ty.args:
            _param_structs(arg, out, True)
        # A forward-referenced result is accepted, so the result adds no edge,
        # but a fn type inside it (a returned fn pointer) still may.
        _param_structs(ty.return_type, out, False)
    elif isinstance(ty, ir.PointerType):
        # `%S*` is fine forward-referenced; `%S (%S)*`'s pointee is the fn type.
        _param_structs(ty.pointee, out, False)
    elif isinstance(ty, (ir.ArrayType, ir.VectorType)):
        _param_structs(ty.element, out, in_param)
    elif isinstance(ty, ir.LiteralStructType):
        for elem in ty.elements:
            _param_structs(elem, out, in_param)


def _dependencies(ty: ir.IdentifiedStructType) -> list:
    """The identified structs that must be defined before `ty`'s `= type` line."""
    deps: list = []
    if not ty.is_opaque:
        for elem in ty.elements:
            _param_structs(elem, deps, False)
    return deps


def order_identified_types(context: ir.Context) -> None:
    """Reorder `context.identified_types` in place (see the module docstring)."""
    types = context.identified_types
    ordered: dict = {}
    visiting: set = set()

    def visit(name: str, ty: ir.IdentifiedStructType) -> None:
        if name in ordered or name in visiting:
            return  # done, or a by-value cycle: leave it where it falls
        visiting.add(name)
        for dep in _dependencies(ty):
            visit(dep.name, dep)
        visiting.discard(name)
        ordered[name] = ty

    for name, ty in list(types.items()):
        visit(name, ty)
    types.clear()
    types.update(ordered)
