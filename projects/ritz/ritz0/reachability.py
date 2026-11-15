"""Code that can never run is refused: "unreachable code" (AGAST #2520).

LARB ruling (Aaron, 2026-11-15), extending R13 from match arms to statements.
A statement can never run when it follows, in the same block, one that never
lets control past it:

* a `return`, `break` or `continue`;
* an `if`/`else` (else-if chains and nested ifs too) whose every arm diverges;
* a `match` whose every arm diverges;
* a `loop`, or a `while` on the literal `true`, with no `break` that leaves it.

The first such statement of a block is a located error. ritz0 parses `loop` as
`while true`, so the two are one case; any other condition, a const equal to
true included, is not judged infinite (LANGUAGE_SPEC §6.1).

Unlike tail_value's `_stmt_diverges`, a `break` or `continue` counts here: this
judges what follows a statement in its own block, and both leave that block.
Whether a loop is infinite uses tail_value's `_has_own_break`, so the two rules
agree on which loops end.

ritz1's twin is ritz1/src/reachability.ritz; test_dead_tail_after_diverging_if.py
holds all three compilers to one table, positions included.
"""

from dataclasses import fields, is_dataclass
from typing import List, Optional

import ritz_ast as rast
from binder_names import _judged_fns
from tail_value import _has_own_break

MESSAGE = "unreachable code"

_LEAVES = (rast.ReturnStmt, rast.BreakStmt, rast.ContinueStmt)
_LEAVES_EXPR = (rast.ReturnExpr, rast.BreakExpr, rast.ContinueExpr)


def _stmt_diverges(stmt) -> bool:
    """Whether control never reaches the statement after `stmt`."""
    if isinstance(stmt, _LEAVES):
        return True
    if isinstance(stmt, rast.ExprStmt):
        return _expr_diverges(stmt.expr)
    if isinstance(stmt, rast.WhileStmt):
        return (isinstance(stmt.cond, rast.BoolLit) and stmt.cond.value is True
                and not _has_own_break(stmt.body))
    if isinstance(stmt, rast.UnsafeBlock):
        return _block_diverges(stmt.body)
    return False


def _block_diverges(block) -> bool:
    return (any(_stmt_diverges(s) for s in block.stmts)
            or (block.expr is not None and _expr_diverges(block.expr)))


def _expr_diverges(expr) -> bool:
    if isinstance(expr, _LEAVES_EXPR):
        return True
    if isinstance(expr, rast.Grouped):
        return _expr_diverges(expr.expr)
    if isinstance(expr, rast.Block):
        return _block_diverges(expr)
    if isinstance(expr, rast.If):
        return (expr.else_block is not None
                and _block_diverges(expr.then_block)
                and _expr_diverges(expr.else_block))
    if isinstance(expr, rast.Match):
        return bool(expr.arms) and all(_expr_diverges(a.body) for a in expr.arms)
    return False


def _first_dead(block) -> Optional[rast.Node]:
    """The first statement (or tail expression) of `block` that never runs."""
    for i, stmt in enumerate(block.stmts):
        if _stmt_diverges(stmt):
            if i + 1 < len(block.stmts):
                return block.stmts[i + 1]
            return block.expr
    return None


def _children(node):
    for f in fields(node):
        if f.name == 'span':
            continue
        value = getattr(node, f.name, None)
        for item in (value if isinstance(value, (list, tuple)) else (value,)):
            if isinstance(item, rast.Node) and is_dataclass(item):
                yield item


def _walk(node, errors: List[str]) -> None:
    """Every block under `node`, in source order."""
    if isinstance(node, rast.Block):
        dead = _first_dead(node)
        if dead is not None and dead.span is not None:
            sp = dead.span
            errors.append(f"{sp.file}:{sp.line}:{sp.column}: error: {MESSAGE}")
    for child in _children(node):
        _walk(child, errors)


def check_reachable(module: rast.Module, source_path: Optional[str] = None) -> List[str]:
    """`file:line:col: error: unreachable code` for the first dead statement of
    each block in the fns this compile emits (binder_names._judged_fns)."""
    errors: List[str] = []
    for fn in _judged_fns(module, source_path):
        _walk(fn.body, errors)
    return errors
