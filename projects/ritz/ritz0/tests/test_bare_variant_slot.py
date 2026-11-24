"""A bare variant in an enum slot is the slot's enum's variant (AGAST #3602).

`variant_to_enum` is a flat name -> enum map, so the last enum to declare a
name owns it.  tempest/lib/iris_bridge.ritz declares `enum Display` with a
`None` variant, and the checker then read every bare `None` as `Display.None`,
even in a `-> Option<T>` return:

    enum Display
        None
        Block

    fn f() -> Option<i32>
        return None        # return type Display doesn't match expected Option<i32>

The emitter builds the slot's variant (`_emit_enum_variant_with_type`).  The
checker now does the same: a bare `V` or `V(..)` landing in a slot whose enum
declares `V` has the slot's type.  Option and Result are the emitter's own,
so an `Option<T>` slot declares `Some`/`None` whether or not ritzlib's
`enum Option<T>` is in scope.

Where no slot decides, a name two concrete user enums declare is #2039's
ambiguity.  The emitter already refuses it in every value position; the
checker reports it too, with the same text, instead of guessing the last
declarer.  A generic enum (ritzlib's Option) never makes a name ambiguous
(LANGUAGE_SPEC §10 "Bare variants"), and a match arm resolves against the
scrutinee, so neither is reported.

These run the checker alone: the emitter already compiles each program.
The last two tables (AGAST #4656) run all three compilers.
"""

import pytest

from parser import parse
from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals, assert_runs
from type_checker import TypeChecker

OPTION = "enum Option<T>\n    Some(T)\n    None\n\n"
DISPLAY = "enum Display\n    None\n    Block\n\n"
# A user enum declaring the Option ctor's name, for the call form.
WRAP = "enum Wrap\n    Some(i32)\n    Bare\n\n"


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


# Every slot the ticket's `None` can land in: a return, a tail, a typed
# `let`, an argument and an assignment.
SLOTS = (
    "fn f() -> Option<i32>\n"
    "    return None\n\n"
    "fn g() -> Option<i32>\n"
    "    None\n\n"
    "fn h() -> Option<i32>\n"
    "    let x: Option<i32> = None\n"
    "    x\n\n"
    "fn k(o: Option<i32>) -> i32\n"
    "    0\n\n"
    "fn m() -> i32\n"
    "    var y: Option<i32> = Some(1)\n"
    "    y = None\n"
    "    k(None)\n")


@pytest.mark.unit
@pytest.mark.parametrize("decls", [
    pytest.param(DISPLAY, id="no-ritzlib-option"),
    pytest.param(OPTION + DISPLAY, id="option-first"),
    pytest.param(DISPLAY + OPTION, id="display-first"),
])
def test_none_in_an_option_slot_is_options(decls):
    assert types(decls + SLOTS) == []


@pytest.mark.unit
def test_none_in_the_other_enums_slot_is_still_its_own():
    # Control: the slot names Display, so `None` is Display's.
    src = OPTION + DISPLAY + (
        "fn f() -> Display\n"
        "    return None\n\n"
        "fn g() -> Display\n"
        "    let d: Display = None\n"
        "    d\n")
    assert types(src) == []


@pytest.mark.unit
def test_a_slot_that_doesnt_declare_the_name_still_mismatches():
    # Control: the slot doesn't decide, so `Block` stays Display's and the
    # mismatch is still reported.
    src = OPTION + DISPLAY + "fn f() -> Option<i32>\n    return Block\n"
    assert types(src) == [
        "<stdin>:10:5: return type Display doesn't match expected Option<i32>"]


@pytest.mark.unit
@pytest.mark.parametrize("decls", [
    pytest.param(OPTION + WRAP, id="option-first"),
    pytest.param(WRAP + OPTION, id="wrap-first"),
])
def test_a_variant_call_in_an_option_slot_is_options(decls):
    src = decls + (
        "fn f() -> Option<i32>\n"
        "    return Some(1)\n\n"
        "fn g() -> Wrap\n"
        "    return Some(1)\n")
    assert types(src) == []


AMBIGUOUS = "enum S\n    A\n    B\n\nenum T\n    B\n    C\n\nenum E\n    Holds(i32)\n\nenum F\n    Holds(i32)\n\n"
MESSAGE = ("ambiguous enum variant '{n}': declared by enum '{a}' and enum '{b}'; "
           "qualify it, e.g. '{a}.{n}'")


@pytest.mark.unit
def test_an_ambiguous_bare_variant_is_reported():
    src = AMBIGUOUS + (
        "fn f() -> i32\n"
        "    let x = B\n"
        "    let y = Holds(1)\n"
        "    0\n")
    assert types(src) == [
        "<stdin>:16:13: " + MESSAGE.format(n="B", a="S", b="T"),
        "<stdin>:17:13: " + MESSAGE.format(n="Holds", a="E", b="F"),
    ]


@pytest.mark.unit
def test_unambiguous_neighbours_and_match_arms_are_not_reported():
    # Control: `A` has one declarer, Option's generic `None` doesn't clash
    # with Display's, and a bare arm resolves against the scrutinee.
    src = AMBIGUOUS + OPTION + DISPLAY + (
        "fn f(s: S) -> i32\n"
        "    let a = A\n"
        "    let d = None\n"
        "    match s\n"
        "        A => 0\n"
        "        B => 1\n")
    assert types(src) == []


# --- A bare variant the slot's enum doesn't declare (AGAST #4656) --------------
#
# `return Block` in a `-> Option<i32>` fn, `Block` a variant of Display only.
# ritz1 built Display's `Block` into the Option slot and exited 0; ritz0
# refused it at the statement, as `Unknown variant Block in enum Option$i32`.
# Both now say it at `Block`, naming the enum as declared (as
# test_match_foreign_variant.py's pattern does), in every slot.

FOREIGN = "Unknown variant Block in enum Option"


def _program(body, ret="i32"):
    return OPTION + DISPLAY + f"fn f() -> {ret}\n{body}\n" + (
        "fn k(o: Option<i32>) -> i32\n    0\n\n"
        "fn main() -> i32\n    f()\n    0\n")


FOREIGN_ROWS = {
    "return": (_program("    return ^Block\n", "Option<i32>"), FOREIGN),
    "fn_tail": (_program("    ^Block\n", "Option<i32>"), FOREIGN),
    "typed_let": (_program("    let x: Option<i32> = ^Block\n    0\n"), FOREIGN),
    "assign": (_program("    var y: Option<i32> = None\n    y = ^Block\n    0\n"), FOREIGN),
    "argument": (_program("    k(^Block)\n"), FOREIGN),
    # No ritzlib Option in scope: the built-in one declares Some / None only.
    "builtin_option": (DISPLAY + "fn f() -> Option<i32>\n    return ^Block\n\n"
                       "fn main() -> i32\n    f()\n    0\n", FOREIGN),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_another_enums_bare_variant_in_an_enum_slot_is_refused(compiler, tmp_path):
    assert_refusals(compiler, tmp_path, FOREIGN_ROWS)


# Control: the slot's own variant still lands in it: `None` in an Option slot
# whichever enum declares `None` last, `Block` in a Display one.
OWN_ROWS = {
    "none_in_option": (OPTION + DISPLAY + (
        "fn f() -> Option<i32>\n    return None\n\n"
        "fn k(o: Option<i32>) -> i32\n"
        "    match o\n        Some(v) => v\n        None => 3\n\n"
        "fn main() -> i32\n"
        "    let x: Option<i32> = None\n"
        "    k(f()) + k(x) + k(None)\n"), 9),
    "block_in_display": (OPTION + DISPLAY + (
        "fn f() -> Display\n    return Block\n\n"
        "fn k(d: Display) -> i32\n"
        "    match d\n        None => 1\n        Block => 4\n\n"
        "fn main() -> i32\n"
        "    let d: Display = Block\n"
        "    k(f()) + k(d) + k(Block)\n"), 12),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_slots_own_bare_variant_still_runs(compiler, tmp_path):
    assert_runs(compiler, tmp_path, OWN_ROWS)
