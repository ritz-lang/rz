"""`E.from(v)` call sites (LANGUAGE_SPEC §10.4, AGAST #1880).

The parser generates `fn E__from(v: T) -> Option<E>` for every enum with a
representation type in a module that imports ritzlib.option (parser.py,
_enum_from_fns).  This pass, run on the merged module after import
resolution, rewrites each `E.from(args)` -- a MethodCall on the bare name of
an enum -- into the plain call `E__from(args)`, so name resolution, type
inference and emission all see an ordinary fn call.  ritz1 does the same
rewrite in its monomorph walk.

`X.from(...)` where X is an enum without a generated `from` is an error,
located at the call.
"""

from typing import List

import ritz_ast as rast
from parser import enum_from_name


def _no_from(enum_name: str) -> str:
    return (f"enum '{enum_name}' has no 'from': that needs a representation "
            f"type ('enum {enum_name}: <integer type>') and its module must "
            f"import ritzlib.option")


def rewrite_enum_from(module: rast.Module) -> List[str]:
    """Rewrite `E.from(...)` in place; return located errors."""
    enums = {it.name for it in module.items if isinstance(it, rast.EnumDef)}
    fns = {it.name for it in module.items if isinstance(it, rast.FnDef)}
    errors: List[str] = []

    def rewrite(node):
        if (isinstance(node, rast.MethodCall) and node.method == "from"
                and isinstance(node.expr, rast.Ident) and node.expr.name in enums):
            target = enum_from_name(node.expr.name)
            if target not in fns:
                errors.append(f"{node.span}: {_no_from(node.expr.name)}")
                return node
            return rast.Call(node.span, rast.Ident(node.expr.span, target),
                             node.args)
        return node

    # A plain __dict__ walk: dataclasses.fields() per node made this pass a
    # quarter of a large file's parse time.  Types hold no calls (and a
    # Span is no Node).
    skip = rast.Type

    def visit(x):
        if isinstance(x, rast.Node) and not isinstance(x, skip):
            walk(x)
            return rewrite(x)
        if isinstance(x, list):
            for i, y in enumerate(x):
                x[i] = visit(y)
        elif isinstance(x, tuple):
            return tuple(visit(y) for y in x)
        return x

    def walk(node):
        d = node.__dict__
        for k, v in d.items():
            if isinstance(v, (rast.Node, list, tuple)):
                d[k] = visit(v)

    if not enums:
        return errors
    for item in module.items:
        walk(item)
    return errors
