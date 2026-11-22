"""The built-in `Future` type (LARB R79, AGAST #4006).

`Future` means "some async fn's future".  Every generated future starts with
the same header (async_transform_v2.FUTURE_HEADER: its poll fn first), so a
reference to any of them is a reference to a `Future`, and
`future_poll(f: @&Future) -> bool` polls one through its header.  Its size is
the async fn's, which `Future` doesn't say: only a reference to one is a value.

The rule here is the typing pass's (type_checker.TypeChecker.check): `Future`
by value, in a `let`/`var`, a field, a param, an array element or a return, is
refused at the `Future`.

That a generated future fits an `@&Future` slot is not judged here: ritz0
transforms async after typing and its generated names are unspellable
(`NAME$Future`, AGAST #3606), so the checker never meets one.  ritz1 lowers
before its checks and mirrors the fit in sema_type.sema_future_ref_fits
(#4007).
"""

from dataclasses import fields, is_dataclass
from typing import Iterator, List, Optional, Tuple

import ritz_ast as rast

FUTURE = 'Future'
POLL = 'future_poll'

# future_poll's one param, `f: @&Future`.
POLL_PARAM = rast.RefType(span=None, inner=rast.NamedType(span=None, name=FUTURE), mutable=True)

NO_SIZE = "`Future` has no size; take it by reference, `@&Future`"


def is_future(ty: Optional[rast.Type]) -> bool:
    """`ty` is the built-in `Future`."""
    return isinstance(ty, rast.NamedType) and ty.name == FUTURE and not ty.args


def _by_value(ty: Optional[rast.Type]) -> Iterator[rast.NamedType]:
    """Each `Future` in `ty` held by value: not behind a `*`, `@` or `@&`."""
    if ty is None or isinstance(ty, (rast.PtrType, rast.RefType)):
        return
    if is_future(ty):
        yield ty
    elif isinstance(ty, rast.ArrayType):
        yield from _by_value(ty.inner)
    elif isinstance(ty, rast.TupleType):
        for part in ty.elements:
            yield from _by_value(part)
    elif isinstance(ty, rast.NamedType):
        for arg in ty.args or ():
            yield from _by_value(arg)


def _bindings(node) -> Iterator[rast.Type]:
    """The written type of every `let`/`var` under `node`."""
    if isinstance(node, (rast.LetStmt, rast.VarStmt)) and node.type is not None:
        yield node.type
    if isinstance(node, list):
        for child in node:
            yield from _bindings(child)
    elif is_dataclass(node) and not isinstance(node, rast.Type):
        for f in fields(node):
            child = getattr(node, f.name)
            if isinstance(child, (list, rast.Node)):
                yield from _bindings(child)


def _fn_slots(fn) -> Iterator[rast.Type]:
    for param in fn.params:
        yield param.type
    yield fn.ret_type
    if getattr(fn, 'body', None) is not None:
        yield from _bindings(fn.body)


def by_value_errors(module: rast.Module, wanted) -> List[Tuple[str, rast.Span]]:
    """NO_SIZE at each `Future` written by value in `module`'s structs, and
    in the signatures and bodies of the fns `wanted` picks."""
    slots: List[Optional[rast.Type]] = []
    for item in module.items:
        if isinstance(item, rast.StructDef):
            slots += [ty for _, ty in item.fields]
        elif isinstance(item, rast.FnDef) and wanted(item):
            slots += _fn_slots(item)
        elif isinstance(item, rast.ImplBlock):
            for method in item.methods:
                if wanted(method):
                    slots += _fn_slots(method)
    return [(NO_SIZE, ty.span) for slot in slots for ty in _by_value(slot)]
