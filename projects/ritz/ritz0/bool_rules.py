"""What `bool` may not do, and the words for it (LARB R4, AGAST #2342).

bool is its own type. The emitter and the type checker both report through these
words, and ritz1's bool_check.ritz prints the same ones.
"""

INTEGER = 'an integer'
POINTER = 'a pointer'
FLOAT = 'a float'
OTHER = 'a struct or enum'

COMPARISONS = ('==', '!=', '<', '<=', '>', '>=')
LOGICAL = ('&&', '||', 'and', 'or')
BITWISE = ('&', '|', '^', '<<', '>>')
ARITHMETIC = ('+', '-', '*', '/', '%')

# `&&`, `||` and `!` are the same operators; ritz1's AST keeps only the operator.
SPELLING = {'&&': 'and', '||': 'or', '!': 'not'}

_WRITE = {INTEGER: ': write `x != 0`', POINTER: ': write `p != null`'}
PRECEDENCE_HINT = ': `x & 1 == 1` is `x & (1 == 1)`: parenthesise `(x & 1) == 1`'
AS_BOOL_REMOVED = '`as bool` is removed: write `x != 0`'


def must_be_bool(what: str, kind: str) -> str:
    """`what` is `if condition`, or `operand of `and``."""
    return f"{what} must be bool, got {kind}{_WRITE.get(kind, '')}"


def operand_is_bool(op: str, wanted: str, comparison: bool = False) -> str:
    """A bool operand of a bitwise (`wanted` an integer) or arithmetic operator."""
    hint = PRECEDENCE_HINT if comparison else ''
    return f"operand of `{op}` must be {wanted}, got bool{hint}"


def cannot_compare(kind: str) -> str:
    return f"cannot compare bool with {kind}"


def value_into_bool(kind: str) -> str:
    return f"cannot use {kind} as bool{_WRITE.get(kind, '')}"


def bool_into_slot(kind: str) -> str:
    hint = ': write `b as i32`' if kind == INTEGER else ''
    return f"cannot use bool as {kind}{hint}"


def cannot_cast(kind: str) -> str:
    return f"cannot cast bool to {kind}"
