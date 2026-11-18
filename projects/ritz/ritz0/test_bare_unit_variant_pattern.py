"""A bare unit-variant pattern binds nothing (AGAST #3605).

The parser reads a bare `None` arm as `IdentPattern("None")`, and the type
checker bound it like any name: a local `None` with the scrutinee's type.  The
arm's body `None` then resolved to that local, not the variant:

    fn f(self: @F) -> Option<i32>
        match @self.loca
            Some(l) => Some(l.n)
            None => None        # match arms have different types: Option and @Option<L>

A by-value scrutinee hid it, because the local's type was the enum anyway.

The emitter has the rule already: a bare name is a variant case when the
scrutinee's enum declares it, and otherwise a catch-all binding.  The checker
now agrees, so a name of *another* enum's variant still binds.

These run the checker alone: the bug is the checker's, and the emitter already
compiles each program.
"""

import pytest

from parser import parse
from type_checker import TypeChecker

pytestmark = pytest.mark.unit

# Option as ritzlib.option declares it: without it `Some(..)` is `unknown`,
# which fits anything and hides the mismatch.
OPTION = "enum Option<T>\n    Some(T)\n    None\n\n"
OPT = "enum Opt\n    Has(i32)\n    Empty\n\n"


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


def test_none_through_a_reference_is_the_variant():
    # The ticket's repro: angelo/src/font.ritz:93.
    src = OPTION + (
        "struct L\n    n: i32\n\n"
        "struct F\n    loca: Option<L>\n\n"
        "fn f(self: @F) -> Option<i32>\n"
        "    match @self.loca\n"
        "        Some(l) => Some(l.n)\n"
        "        None => None\n")
    assert types(src) == []


def test_user_unit_variant_through_a_reference_is_the_variant():
    src = OPT + (
        "fn f(o: @Opt) -> Opt\n"
        "    match o\n"
        "        Has(v) => Has(v)\n"
        "        Empty => Empty\n")
    assert types(src) == []


def test_another_enums_variant_name_still_binds():
    # `Empty` isn't a variant of i32: the emitter takes it as a catch-all
    # binding, so its body `Empty` is the i32, not an `Opt`.
    src = OPT + (
        "fn f(n: i32) -> i32\n"
        "    match n\n"
        "        1 => 2\n"
        "        Empty => Empty\n")
    assert types(src) == []
