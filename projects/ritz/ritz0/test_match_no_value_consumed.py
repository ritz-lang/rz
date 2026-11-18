"""AGAST #1357: a match with no value, used as one, is a located error at the match.

A match whose live arms yield values of irreconcilable types (a struct next
to an integer), or whose arm is a block ending in a statement, has no value
(#1321).  As a statement that is fine.  Where a value is wanted, ritz0 died
with a raw `'_Undefined' object has no attribute 'type'` traceback that named
no source position.  The emitters now return a sentinel carrying the match's
span, and reading it as a value reports there, at the `match`.

One row per consumer kind (test_table_rows.py, docs/TESTING.md).  ritz0 only:
this is ritz0's emitter-as-type-checker error surface.  A call argument has
no row: a match cannot open inside `(` (the parser refuses it first).
"""

import pytest

from test_table_rows import assert_refusals, assert_runs

MESSAGE = (
    "this match has no value: its arms don't yield one value type, "
    "so it can't be used where a value is wanted"
)

HEAD = (
    "struct P\n    x: i64\n\n"
    "enum Shape\n    A(i64)\n    B(i64)\n\n"
    "fn mk() -> Shape\n    A(5)\n\n"
)
# Arms of irreconcilable types: a struct and an integer.
ARMS = "\n        A(q) => p\n        B(q) => 7\n"


def _fn(body, ret="i64", tail="    return 0\n"):
    """`f(s: Shape) -> ret` whose body is `body`; main calls it."""
    return (
        f"{HEAD}fn f(s: Shape) -> {ret}\n"
        "    let p: P = P { x: 99 }\n"
        f"{body}{tail}\n"
        "fn main() -> i32\n    f(mk())\n    0\n"
    )


ROWS = {
    "let": _fn("    let v = ^match s" + ARMS),
    # A typed `let` keeps its own message, at the `let`, naming the
    # annotation (#2027, test_let_float_match_int_arm.py).
    "typed_let": (_fn("    ^let v: i64 = match s" + ARMS),
                  "`v` is declared `i64` but its initialiser has no single value "
                  "type: its match / if arms yield values that cannot be merged at "
                  "that type"),
    "assign": _fn("    var v: i64 = 0\n    v = ^match s" + ARMS),
    "return": _fn("    return ^match s" + ARMS, tail=""),
    "operand": _fn("    let v: i64 = 1 + ^match s" + ARMS),
    "fn_tail": _fn("    ^match s" + ARMS, tail=""),
    # An arm that is a block ending in a statement, not a value. The enum
    # match read it as a silent 0 (its `i32 0` dummy); the integer one crashed.
    "enum_match_statement_arm": _fn(
        "    var w: i64 = 0\n"
        "    let v = ^match s\n"
        "        A(q) =>\n            w = q\n            var t: i64 = 2\n"
        "        B(q) => 7\n"
    ),
    "int_match_statement_arm": _fn(
        "    var w: i64 = 0\n"
        "    let v = ^match 3\n"
        "        1 =>\n            w = 1\n            var t: i64 = 2\n"
        "        _ => 7\n"
    ),
}


@pytest.mark.integration
def test_match_with_no_value_used_as_one_is_refused_at_the_match(tmp_path):
    rows = {n: row if isinstance(row, tuple) else (row, MESSAGE) for n, row in ROWS.items()}
    assert_refusals("ritz0", tmp_path, rows)


# As a statement a match with no value still compiles, nested in another
# match's arm too: the outer match's `hasattr(v, 'type')` probe of the inner
# NoValue must answer "no value", not raise (#1321's font.ritz shape).
STATEMENT = (
    "struct P\n    x: i64\n\n"
    "enum Shape\n    A(i64)\n    B(i64)\n\n"
    "fn g(s: Shape, t: Shape) -> i64\n"
    "    var w: i64 = 0\n"
    "    let p: P = P { x: 99 }\n"
    "    match s\n"
    "        A(q) =>\n"
    "            match t\n"
    "                A(r) => p\n"
    "                B(r) => 7\n"
    "        B(q) => w = q\n"
    "    w\n\n"
    "fn main() -> i32\n    g(Shape.B(3), Shape.A(1)) as i32\n"
)


@pytest.mark.integration
def test_match_with_no_value_as_a_statement_still_runs(tmp_path):
    assert_runs("ritz0", tmp_path, {"nested_statement_match": (STATEMENT, 3)})
