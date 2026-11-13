"""Can a function body reach its end without producing a value? (AGAST #1429)

A pure walk over the AST. `value_gap(body)` returns the node where control
can complete without a value, or None when every path either yields a value
or never arrives at the end at all (a `return`, a `while true` with no
`break`).

It is called for functions that declare a return type, which is what keeps
procedures out of it: a procedure's tail runs for effect, and ending in a
guard or an if/else of assignments is ordinary code.
"""

from dataclasses import fields, is_dataclass
from typing import Optional

import ritz_ast as rast


def _has_own_break(node) -> bool:
    """A `break` under `node` that leaves the loop `node` is the body of.

    An inner loop owns its own breaks, and a lambda or closure body is a
    different function.
    """
    if isinstance(node, (rast.BreakStmt, rast.BreakExpr)):
        return True
    if isinstance(node, (rast.WhileStmt, rast.ForStmt,
                         rast.Lambda, rast.Closure)):
        return False
    if isinstance(node, (list, tuple)):
        return any(_has_own_break(item) for item in node)
    if isinstance(node, rast.Node) and is_dataclass(node):
        return any(_has_own_break(getattr(node, f.name))
                   for f in fields(node) if f.name != 'span')
    return False


def _stmt_diverges(stmt) -> bool:
    """Whether control never gets past `stmt`.

    `break` and `continue` are not here because `value_gap` never walks a loop
    body: a loop is judged whole, through `_has_own_break`.
    """
    if isinstance(stmt, rast.ReturnStmt):
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
    if isinstance(expr, rast.ReturnExpr):
        return True
    if isinstance(expr, rast.If):
        return (expr.else_block is not None
                and _block_diverges(expr.then_block)
                and _block_diverges(expr.else_block))
    if isinstance(expr, rast.Block):
        return _block_diverges(expr)
    if isinstance(expr, rast.Match):
        return bool(expr.arms) and all(_expr_diverges(a.body) for a in expr.arms)
    return False


def arm_diverges(node) -> bool:
    """Whether the if/match arm `node` leaves without ever yielding a value.

    Unlike `_expr_diverges`, a `break` or `continue` counts: the arm is not a
    loop body, so either one leaves the expression the arm belongs to (#1752).
    """
    loop_exit = (rast.BreakStmt, rast.ContinueStmt, rast.BreakExpr, rast.ContinueExpr)
    if isinstance(node, loop_exit):
        return True
    if isinstance(node, rast.Block):
        if any(isinstance(s, loop_exit)
               or (isinstance(s, rast.ExprStmt) and arm_diverges(s.expr))
               for s in node.stmts):
            return True
        if node.expr is not None and arm_diverges(node.expr):
            return True
    return _expr_diverges(node)


def value_gap(node, yields_nothing=lambda expr: False) -> Optional[rast.Node]:
    """The node where `node`, in value position, completes with no value.

    `yields_nothing` lets the caller name expressions only it can judge, such
    as a call to a fn that declares no return type.
    """
    if isinstance(node, rast.Block):
        if any(_stmt_diverges(s) for s in node.stmts):
            return None
        if node.expr is None:
            return node.stmts[-1] if node.stmts else node
        return value_gap(node.expr, yields_nothing)
    if _expr_diverges(node):
        return None
    if isinstance(node, rast.If):
        if node.else_block is None:
            return node
        return (value_gap(node.then_block, yields_nothing)
                or value_gap(node.else_block, yields_nothing))
    if isinstance(node, rast.Match):
        for arm in node.arms:
            gap = value_gap(arm.body, yields_nothing)
            if gap is not None:
                return gap
        return None
    if isinstance(node, rast.AssignExpr):
        return node
    if isinstance(node, rast.Ident) and node.name == 'pass':
        return node
    return node if yields_nothing(node) else None


def value_tails(node):
    """The expressions `node`'s value comes from.

    The node itself, or (recursively) an if branch's or block's trailing
    expression, or a match arm's body. Parentheses leave no node to see through.
    """
    if isinstance(node, rast.Block):
        if node.expr is not None:
            yield from value_tails(node.expr)
    elif isinstance(node, rast.If):
        yield from value_tails(node.then_block)
        if node.else_block is not None:
            yield from value_tails(node.else_block)
    elif isinstance(node, rast.Match):
        for arm in node.arms:
            yield from value_tails(arm.body)
    elif node is not None:
        yield node


def slot_tails(slot, node, resolve=lambda ty: ty):
    """(expression, the type of the slot it lands in) for each of `node`'s
    value tails, when `node` lands in a `slot`-typed place: an array or tuple
    literal's elements land in that type's elements. `resolve` sees through
    the caller's type aliases.

    Only a literal takes its type from its slot (LARB R3), so this is for them.
    Nothing else reads by destination: a `name:& T` param stopped at #2337.
    """
    slot = resolve(slot)
    for tail in value_tails(node):
        if isinstance(tail, rast.ArrayLit) and isinstance(slot, rast.ArrayType):
            for element in tail.elements:
                yield from slot_tails(slot.inner, element, resolve)
        elif isinstance(tail, rast.ArrayFill) and isinstance(slot, rast.ArrayType):
            yield from slot_tails(slot.inner, tail.value, resolve)
        elif (isinstance(tail, rast.TupleLit) and isinstance(slot, rast.TupleType)
                and len(tail.elements) == len(slot.elements)):
            for element, element_slot in zip(tail.elements, slot.elements):
                yield from slot_tails(element_slot, element, resolve)
        else:
            yield tail, slot
