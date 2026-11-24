"""AGAST #1357: a match with no value, used as one, is a located error at the match.

A match whose live arms yield values of irreconcilable types (a struct next
to an integer), or whose arm is a block ending in a statement, has no value
(#1321).  As a statement that is fine.  Where a value is wanted, ritz0 died
with a raw `'_Undefined' object has no attribute 'type'` traceback that named
no source position.  The emitters now return a sentinel carrying the match's
span, and reading it as a value reports there, at the `match`.

One row per consumer kind (test_table_rows.py, docs/TESTING.md).  A call
argument has no row: a match cannot open inside `(` (the parser refuses it
first).  ritz1 says the same, at the same place, from Sema (AGAST #4656,
if_arm_value.ritz): an arm that ends in a statement, or arms whose values are
a struct and an integer, two structs, or `()` and an integer.
"""

import pytest

from test_ref_into_value import COMPILERS
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
    # AGAST #4656: the ticket's shape, an int match whose arm is one
    # assignment (test_checker_corpus_gaps.py's TestUnitIsOneType too).
    "int_match_assignment_arm": _fn(
        "    var w: i64 = 0\n"
        "    let v = ^match 3\n"
        "        1 =>\n            w = 1\n"
        "        _ => 7\n"
    ),
    "unit_arm_next_to_an_integer": (
        "fn f(k: i32) -> i32\n    ^match k\n        1 => 3\n        _ => ()\n\n"
        "fn main() -> i32\n    f(1)\n"),
    # Two structs, and test_match_mixed_type_arms.py's value match.
    "two_structs": _fn("    let q: Shape = mk()\n    let v = ^match s\n"
                       "        A(n) => p\n        B(n) => q\n"),
    "typed_let_in_main": (
        HEAD + "fn main() -> i32\n    let p: P = P { x: 99 }\n    let s: Shape = A(5)\n"
        "    ^let v: i64 = match s" + ARMS + "    return v as i32\n",
        "`v` is declared `i64` but its initialiser has no single value "
        "type: its match / if arms yield values that cannot be merged at "
        "that type"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_match_with_no_value_used_as_one_is_refused_at_the_match(tmp_path, compiler):
    rows = {n: row if isinstance(row, tuple) else (row, MESSAGE) for n, row in ROWS.items()}
    assert_refusals(compiler, tmp_path, rows)


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
    "                A(r) => w = p.x\n"
    "                B(r) => w = 7\n"
    "        B(q) => w = q\n"
    "    w\n\n"
    "fn main() -> i32\n    g(Shape.B(3), Shape.A(1)) as i32\n"
)


# Controls for ritz1's check (AGAST #4656): arms that do yield one value
# type, a `pass` or a diverging arm beside them, still run.
ONE_TYPE = (
    "struct P\n    x: i64\n\n"
    "fn pick(k: i64, p: P, q: P) -> i64\n"
    "    let a = match k\n        1 => p\n        _ => q\n"
    "    let b: i64 = match k\n        1 => 4 as i32\n        2 =>\n            return 9\n        _ => k\n"
    "    let c = match k\n        1 => true\n        _ => false\n"
    "    var w: i64 = 0\n"
    "    match k\n        1 =>\n            w = 1\n        _ => pass\n"
    "    a.x + b + w\n\n"
    "fn main() -> i32\n    pick(1, P { x: 1 }, P { x: 2 }) as i32\n"
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_match_with_no_value_as_a_statement_still_runs(tmp_path, compiler):
    assert_runs(compiler, tmp_path, {"nested_statement_match": (STATEMENT, 3),
                                     "one_value_type": (ONE_TYPE, 6)})
