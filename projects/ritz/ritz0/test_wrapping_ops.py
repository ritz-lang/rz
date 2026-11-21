"""Wrapping arithmetic: `+%`, `-%`, `*%` and their `op=` forms (LARB R63, AGAST #3485).

    let h = h *% 16777619       # FNV: wraps at h's type, by request

R63 makes `+`, `-` and `*` stop the program on overflow (#3488, later); the
`%` forms are how code that means to wrap (hashes, crypto rounds, PRNGs) says
so.  The operators themselves, on ritz0 (#3485) and ritz1 (#3486):

- they lex as one token each and parse at the precedence of `+`, `-`, `*`;
- they type as R21 types `+`: operands and result at the operand type, a
  literal taking the other operand's type;
- they lower to plain `add`, `sub`, `mul` at that type.  A wider slot doesn't
  widen them (#3225 does for `+`): the writer asked for the wrap, so a
  `let w: u16 = a +% b` with `a, b: u8` wraps at 8 bits, as a cast would stop
  the walk;
- they are integer operators: on a float or a pointer they are refused,
  located, on every compile.

The parser keeps them as `BinOp('+', wrapping=True)` (ritz1: `Expr.wrapping`),
so every rule for `+` applies unchanged and only the two differences above look
at the flag.  Each runtime row's `main` returns 3 when it holds, on all three
compilers; the lexing and parsing rows are ritz0's front end.
"""

import pytest
import ritz_ast as rast
from lexer import tokenize
from parser import parse
from test_ref_into_value import _assert_refused, _run
from tokens import TokenType

U64_MAX = "18446744073709551615"

# Every compiler, as test_ref_into_value runs a row: the rule is the language's,
# not ritz0's, and ritz1_selfhosted must accept what ritz1 does.
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


# --- lexing and parsing -------------------------------------------------------

@pytest.mark.unit
def test_each_wrapping_operator_is_one_token():
    got = [(t.type, t.value) for t in tokenize("+% -% *% +%= -%= *%=")][:-1]
    assert got == [
        (TokenType.PLUSPCT, "+%"), (TokenType.MINUSPCT, "-%"), (TokenType.STARPCT, "*%"),
        (TokenType.PLUSPCTEQ, "+%="), (TokenType.MINUSPCTEQ, "-%="), (TokenType.STARPCTEQ, "*%="),
    ]


def _tail(src):
    return parse(f"fn main()\n  {src}").items[0].body.expr


def _shape(e):
    """`e` as nested tuples: (op, wrapping, left, right), or a leaf's name."""
    if isinstance(e, rast.BinOp):
        return (e.op, e.wrapping, _shape(e.left), _shape(e.right))
    return e.name


@pytest.mark.unit
@pytest.mark.parametrize("src, want", [
    # `*%` binds tighter than `+%`, as `*` does than `+`.
    ("a +% b *% c", ("+", True, "a", ("*", True, "b", "c"))),
    ("a *% b + c", ("+", False, ("*", True, "a", "b"), "c")),
    # `+%` and `-%` are `+`'s level, left-associative with it.
    ("a - b +% c", ("+", True, ("-", False, "a", "b"), "c")),
    ("a -% b - c", ("-", False, ("-", True, "a", "b"), "c")),
    # Below `<<`'s level, as `+` is: `a << b +% c` is `a << (b +% c)`.
    ("a << b +% c", ("<<", False, "a", ("+", True, "b", "c"))),
], ids=["mul_over_add", "mul_then_plain_add", "plain_then_wrap", "wrap_then_plain", "under_shift"])
def test_wrapping_operators_take_their_plain_operators_precedence(src, want):
    assert _shape(_tail(src)) == want


@pytest.mark.unit
@pytest.mark.parametrize("op", ["+", "-", "*"])
def test_compound_wrapping_assignment_desugars_to_the_wrapping_operator(op):
    stmt = parse(f"fn main()\n  x {op}%= y").items[0].body.stmts[0]
    assert isinstance(stmt, rast.AssignStmt) and stmt.op == op
    assert _shape(stmt.value) == (op, True, "x", "y")


# --- running: each wraps at its operand type -------------------------------------

def _f(ty, body, call, want):
    """`fn f(a: ty, b: ty)` returning 3 when `body`'s `r` is `want`."""
    return (f"fn f(a: {ty}, b: {ty}) -> i32\n{body}    if r == {want}\n        return 3\n    return 4\n"
            f"\npub fn main() -> i32\n    f({call})\n")


RUNS = {
    # The edges of each type, both ways, for each operator.
    "u8_add": _f("u8", "    let r = a +% b\n", "255, 1", 0),
    "u8_sub": _f("u8", "    let r = a -% b\n", "0, 1", 255),
    "u8_mul": _f("u8", "    let r = a *% b\n", "200, 2", 144),
    "i32_add": _f("i32", "    let r = a +% b\n", "2147483647, 1", -2147483648),
    "i32_sub": _f("i32", "    let r = a -% b\n", "-2147483648, 1", 2147483647),
    "i32_mul": _f("i32", "    let r = a *% b\n", "2147483647, 2", -2),
    "u64_add": _f("u64", "    let r = a +% b\n", f"{U64_MAX}, 1", 0),
    "u64_sub": _f("u64", "    let r = a -% b\n", "0, 1", U64_MAX),
    "u64_mul": _f("u64", "    let r = a *% b\n", "4294967296, 4294967296", 0),
    # A literal operand takes the other operand's type (R21), so this is a u8 add.
    "u8_literal": _f("u8", "    let r = a +% 1\n", "255, 0", 0),
    # The `op=` forms.
    "u8_add_eq": _f("u8", "    var r = a\n    r +%= b\n", "255, 1", 0),
    "i32_sub_eq": _f("i32", "    var r = a\n    r -%= b\n", "-2147483648, 1", 2147483647),
    "u64_mul_eq": _f("u64", "    var r = a\n    r *%= b\n", "4294967296, 4294967296", 0),
    # A wider slot doesn't widen a wrapping operation (#3225 widens `+`): it
    # wraps at u8, 300 - 256.
    "wider_slot": _f("u8", "    let r: u16 = a +% b\n", "200, 100", 44),
    "wider_slot_assign": _f("u8", "    var r: u16 = 0\n    r = a *% b\n", "200, 200", 64),
    # ... but the plain `*` above it still runs in the slot: (200 +% 100) * 10.
    "wider_slot_outer_plain": _f("u8", "    let r: u16 = (a +% b) * 10\n", "200, 100", 440),
    # The walk stops at the wrapping node too: the `/` below it stays a u8
    # divide, so `b * c` wraps to 144 before it (14, not 400 / 10 = 40).
    "wider_slot_stops_below": (
        "fn f(a: u8, b: u8, c: u8) -> i32\n"
        "    let r: u16 = a +% ((b * c) / 10)\n"
        "    if r == 15\n        return 3\n    return 4\n"
        "\npub fn main() -> i32\n    f(1, 200, 2)\n"),
    # A generic's instance is rebuilt by monomorph, and keeps the wrap.
    "generic_instance": ("fn g<T>(t: T, a: u8, b: u8) -> i32\n    let r: u16 = a +% b\n"
                         "    if r == 44\n        return 3\n    return 4\n"
                         "\npub fn main() -> i32\n    g(0, 200, 100)\n"),
}


@pytest.mark.integration
@pytest.mark.batched
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_wrapping_operator_wraps_at_its_operand_type(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, RUNS[name]) == 3


# --- refused: they are integer operators ---------------------------------------------

REFUSED = {
    "float": ("fn f(x: f64) -> f64\n    ^x +% 1.0\n", "`+%` wraps an integer, and `f64` isn't one"),
    "pointer": ("fn f(p: *i32) -> *i32\n    ^p +% 1\n", "`+%` wraps an integer, and `*i32` isn't one"),
    "float_mul_eq": ("fn f(x: f64) -> f64\n    var y = x\n    ^y *%= 2.0\n    y\n",
                     "`*%` wraps an integer, and `f64` isn't one"),
}


@pytest.mark.integration
@pytest.mark.batched
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_wrapping_operator_on_a_non_integer_is_refused(tmp_path, compiler, name):
    body, message = REFUSED[name]
    _assert_refused(compiler, tmp_path, name, body + "\npub fn main() -> i32\n    0\n", message)
