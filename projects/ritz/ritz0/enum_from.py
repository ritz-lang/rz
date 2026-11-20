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

A local or param that shadows the enum's name (AGAST #4414) makes `E.from` a
method call on that binding, not the enum's conversion, so the rewrite walks
each fn body with its lexical scopes and refuses there -- as ritz1's
`rewrite_enum_from_call` does.  binder_check (binder_names.py) does not
reserve enum *type* names, so the shadow is legal and must compile.
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

    # Lexical frames, innermost last. A binding is added when its `let`/`var`
    # is reached (after its initialiser, as it reads) and vanishes with its
    # block, so a name free again after its scope ends is rewritten again.
    scopes: list[set] = []

    def bind(name: str) -> None:
        if name != "_" and scopes:
            scopes[-1].add(name)

    def bind_pattern(pattern) -> None:
        if isinstance(pattern, rast.IdentPattern):
            bind(pattern.name)
        elif isinstance(pattern, rast.VariantPattern):
            for field_pattern in pattern.fields:
                bind_pattern(field_pattern)
        elif isinstance(pattern, rast.StructPattern):
            for _, field_pattern in pattern.fields:
                bind_pattern(field_pattern)

    def shadowed(name: str) -> bool:
        return any(name in frame for frame in reversed(scopes))

    def visit(x):
        """Rewrite `E.from` in `x` (post-order) and return the node."""
        if x is None or isinstance(x, rast.Type):
            return x
        if isinstance(x, list):
            for i, y in enumerate(x):
                x[i] = visit(y)
            return x
        if isinstance(x, tuple):
            return tuple(visit(y) for y in x)
        if not isinstance(x, rast.Node):
            return x

        # The cases that own a scope or bind names are walked structurally;
        # everything else falls through to its fields.
        if isinstance(x, rast.FnDef):
            scopes.append({param.name for param in x.params})
            x.body = visit(x.body)
            scopes.pop()
            return x
        if isinstance(x, rast.Block):
            scopes.append(set())
            for i, stmt in enumerate(x.stmts):
                x.stmts[i] = visit(stmt)
            x.expr = visit(x.expr)
            scopes.pop()
            return x
        if isinstance(x, (rast.LetStmt, rast.VarStmt)):
            x.value = visit(x.value)
            bind(x.name)
            return x
        if isinstance(x, rast.LetTupleStmt):
            x.value = visit(x.value)
            for name in x.names:
                bind(name)
            return x
        if isinstance(x, rast.ForStmt):
            x.iter = visit(x.iter)
            scopes.append({x.var})
            x.body = visit(x.body)
            scopes.pop()
            return x
        if isinstance(x, rast.MatchArm):
            scopes.append(set())
            bind_pattern(x.pattern)
            x.guard = visit(x.guard)
            x.body = visit(x.body)
            scopes.pop()
            return x
        if isinstance(x, rast.MethodCall):
            x.expr = visit(x.expr)
            for i, arg in enumerate(x.args):
                x.args[i] = visit(arg)
            if (x.method == "from" and isinstance(x.expr, rast.Ident)
                    and x.expr.name in enums
                    and not shadowed(x.expr.name)):
                target = enum_from_name(x.expr.name)
                if target not in fns:
                    errors.append(f"{x.span}: {_no_from(x.expr.name)}")
                    return x
                return rast.Call(x.span, rast.Ident(x.expr.span, target),
                                 x.args)
            return x

        # A plain __dict__ walk: dataclasses.fields() per node made this pass
        # a quarter of a large file's parse time. Types hold no calls (and a
        # Span is no Node).
        for key, value in x.__dict__.items():
            if key == "span":
                continue
            new = visit(value)
            if new is not value:
                setattr(x, key, new)
        return x

    if not enums:
        return errors
    for i, item in enumerate(module.items):
        module.items[i] = visit(item)
    return errors
