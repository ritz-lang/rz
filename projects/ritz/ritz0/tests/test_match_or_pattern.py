"""AGAST #4450: or-patterns (`A | B =>`) in `match` (LANGUAGE_SPEC §8.2).

What runs is ritz0/test/test_diff_match_or_pattern.ritz, through the
regression matrix on all three compilers.  This file holds the refusals, one
table per compiler (test_table_rows.py; docs/TESTING.md), each said at the
alternative that is wrong:

- an alternative binds nothing, so a name that is no variant or const of the
  scrutinee (it would bind) is refused, on an enum and on an integer;
- `_` takes every value, so it is an arm of its own, never an alternative;
- a variant with a payload list is refused, binding or not.

A repeated variant or value is the unreachable arm of §8.1, whether the arm
that has it already is an earlier one or this one, and coverage counts every
alternative: a gap is named, and a `_` after alternatives that cover every
variant is unreachable.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals

BINDS = ("an or-pattern can't bind a name: each alternative is a literal, "
         "a const or a variant")
WILDCARD = ("`_` can't be an alternative of an or-pattern: it matches "
            "everything; give it an arm of its own")
PAYLOAD = ("an or-pattern alternative can't have a payload list: give that "
           "variant an arm of its own")

COLOR = "enum Color\n    Red\n    Green\n    Blue\n\n"
SHAPE = "enum Shape\n    Circle(i64)\n    Empty\n    Dot\n\n"
MAIN = "\nfn main() -> i32\n    0\n"


def _color(arms):
    return f"{COLOR}fn f(c: Color) -> i32\n    match c\n{arms}{MAIN}"


ROWS = {  # name: (program with `^` at the spot, message)
    "binding_on_enum": (_color("        Red | ^x => 1\n        _ => 2\n"), BINDS),
    "binding_first": (_color("        ^x | Red => 1\n        _ => 2\n"), BINDS),
    "binding_on_integer": (
        "fn f(n: i64) -> i64\n    match n\n        0 | ^k => 1\n        _ => 2\n" + MAIN,
        BINDS),
    "wildcard": (_color("        Red | ^_ => 1\n"), WILDCARD),
    "payload_binds": (
        f"{SHAPE}fn f(s: Shape) -> i64\n    match s\n"
        "        Empty | ^Circle(r) => 1\n        Dot => 2\n" + MAIN, PAYLOAD),
    "payload_wildcard": (
        f"{SHAPE}fn f(s: Shape) -> i64\n    match s\n"
        "        ^Circle(_) | Empty => 1\n        Dot => 2\n" + MAIN, PAYLOAD),
    # A repeat is §8.1's unreachable arm, naming the arm that has it first.
    "repeat_in_one_pattern": (
        _color("        Red | Green | ^Red => 1\n        Blue => 2\n"),
        "unreachable match arm: the arm at line 8 covers it"),
    "repeat_of_an_earlier_arm": (
        _color("        Red => 1\n        Green | ^Red => 2\n        Blue => 3\n"),
        "unreachable match arm: the arm at line 8 covers it"),
    "repeat_of_an_integer": (
        "fn f(n: i64) -> i64\n    match n\n        1 | 2 => 1\n        3 | ^2 => 2\n"
        "        _ => 3\n" + MAIN,
        "unreachable match arm: the arm at line 3 covers it"),
    # Coverage counts every alternative.
    "gap": (f"{COLOR}fn f(c: Color) -> i32\n    ^match c\n        Red | Green => 1\n{MAIN}",
            "non-exhaustive match: missing Blue"),
    "covered_then_wildcard": (
        _color("        Red | Blue => 1\n        Green => 2\n        ^_ => 3\n"),
        "unreachable match arm: the arm at line 9 covers it"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_or_pattern_refusals(compiler, tmp_path):
    assert_refusals(compiler, tmp_path, ROWS)
