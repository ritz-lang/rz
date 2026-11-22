"""Definitions shared by emitter_llvmlite and the split emitter modules.

`emitter_llvmlite` imports `emitter.exprs` (and, later, the other split
modules), so those modules cannot import `emitter_llvmlite` back.  The
exception classes and small pure helpers both sides need live here instead,
which keeps the import graph acyclic.

`emitter_llvmlite` re-exports these names, so `from emitter_llvmlite import
EmitError` and friends keep working (AGAST #1826).
"""

from typing import Optional

from llvmlite import ir

import ritz_ast as rast


class EmitError(Exception):
    """A user-facing error detected during emission, with a source location.

    Some source errors are only reachable from the emitter. Matching on a
    variant an enum does not declare is one: `type_checker._check_pattern`
    silently ignores it, so emission is the first and only pass that
    notices. Those are still *user* errors and
    must read like one, so this mirrors the `file:line:column: message` format
    used by `TypeError`, `OwnershipError`, `NameError` and friends rather than
    escaping as a bare `ValueError` with a Python traceback attached.
    """

    def __init__(self, message: str, span: Optional[rast.Span] = None):
        self.span = span
        self.message = message
        if span:
            super().__init__(f"{span.file}:{span.line}:{span.column}: {message}")
        else:
            super().__init__(message)


class UnknownFunction(EmitError, ValueError):
    """A call to a name nothing declares (AGAST #3243: that includes `write`,
    `read`, `open`, `close` and `nanosleep`, no longer builtins). Located like
    any EmitError; still a ValueError, so a route that only tries a call for
    an address falls back as it did before the location was added."""


class InternalError(ValueError):
    """An emitter invariant broke: a layout not computed, an operator the
    parser cannot produce. A compiler bug, never the user's, so it is *not*
    an EmitError: it still surfaces as a traceback (AGAST #1390). A
    ValueError for the same fallback reason as SourceError."""


class SourceError(EmitError, ValueError):
    """A source error found by an emitter helper (AGAST #1390): an unknown
    struct, field, variant or variable, a builtin's arity, `?` on a non-Result.

    These were 129 bare ValueError raises that reached the user as a
    Python traceback naming no file. Raised through `Emitter._err`, which
    locates them at the innermost expression being emitted. Still a
    ValueError, so a route that only *tries* (an lvalue address before
    spilling an rvalue, a type lookup that says nothing on failure) falls
    back exactly as it did before the location was added."""


MATCH_HAS_NO_VALUE = (
    "this match has no value: its arms don't yield one value type, "
    "so it can't be used where a value is wanted")


class MatchHasNoValue(EmitError, AttributeError):
    """A `NoValue` read as a value (AGAST #1357), located at its match.

    Also an AttributeError, so `hasattr(v, 'type')` / `getattr(v, 'type',
    None)` probes still answer "no value" as they did for ir.Undefined; only
    a consumer that really reads the value's type gets the located error."""

    def __init__(self, span: Optional[rast.Span]):
        super().__init__(MATCH_HAS_NO_VALUE, span)


class NoValue:
    """What a match with no value yields: its live arms' types can't merge, or
    an arm ends in a statement (#1321).  Fine as a statement.  It was the bare
    ir.Undefined, so a consumer in value position (a `let`, an assignment, a
    `return`, an operand...) died with a raw `'_Undefined' object has no
    attribute 'type'`.  This carries the match's span, and any attribute read
    (`.type`, `.get_reference()`...) raises MatchHasNoValue there (#1357)."""

    __slots__ = ("span",)

    def __init__(self, span: Optional[rast.Span]):
        self.span = span

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        raise MatchHasNoValue(self.span)

    def __repr__(self):
        return "NoValue"


# A `pass` arm's place in a match's arm values (_fill_pass_arms).
_PASS_ARM = object()


def has_no_value(val) -> bool:
    """Whether `val` is an expression's "no value": ir.Undefined (a block
    ending in a statement, a diverging `break` / `return`) or a NoValue."""
    return val is ir.Undefined or isinstance(val, NoValue)


# Volatile / atomic memory builtins (AGAST #1879): name -> (arity, rmw op).
MEM_BUILTINS = {
    'volatile_load': (1, None),
    'volatile_store': (2, None),
    'atomic_load': (1, None),
    'atomic_store': (2, None),
    'atomic_xchg': (2, 'xchg'),
    'atomic_cmpxchg': (3, None),
    'atomic_fetch_add': (2, 'add'),
    'atomic_fetch_sub': (2, 'sub'),
    'atomic_fetch_and': (2, 'and'),
    'atomic_fetch_or': (2, 'or'),
    'atomic_fetch_xor': (2, 'xor'),
    'fence': (0, None),
}


def _llvm_callconv(callconv: Optional[str]) -> Optional[str]:
    """LLVM's name for a `[[callconv]]` value (LANGUAGE_SPEC §17.7), None for C."""
    if callconv is None or callconv == 'c':
        return None
    if callconv == 'win64':
        return 'win64cc'
    raise InternalError(f"unknown calling convention '{callconv}'")


def qualified_access_removed(expr: rast.QualifiedIdent) -> str:
    """The diagnostic for an `a::b` nothing lowered (AGAST #2591)."""
    q, n = expr.qualifier, expr.name
    return (f"`{q}::{n}`: `::` was removed in RERITZ (LANGUAGE_SPEC §15.3). "
            f"Imported names share one namespace, so write `{n}`; "
            f"an enum variant is `{q}.{n}`")


def _is_float_lit_operand(expr) -> bool:
    """AGAST #1969: is `expr` a float literal or a negated one (`-0.1`,
    `-(-0.1)`)?  Both emit a `double` whose value is exact in the source, so
    a binop against an f32 narrows them to f32 rather than widening the f32
    side.  Mirrors ritz1's `is_float_lit_operand` (emitter_core.ritz): the
    two compilers must agree on exactly these shapes.
    """
    while isinstance(expr, rast.UnaryOp) and expr.op == '-':
        expr = expr.operand
    # AGAST #3607: literals only, `0.0 - 7.0`, is a literal too (the
    # checker's FloatLitType): it takes the other side's width.
    if isinstance(expr, rast.BinOp) and expr.op in ('+', '-', '*', '/'):
        return _is_float_lit_operand(expr.left) and _is_float_lit_operand(expr.right)
    return isinstance(expr, rast.FloatLit)
