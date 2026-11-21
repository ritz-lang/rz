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
"""

import pytest

from parser import parse
from type_checker import TypeChecker

pytestmark = pytest.mark.unit

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


@pytest.mark.parametrize("decls", [
    pytest.param(DISPLAY, id="no-ritzlib-option"),
    pytest.param(OPTION + DISPLAY, id="option-first"),
    pytest.param(DISPLAY + OPTION, id="display-first"),
])
def test_none_in_an_option_slot_is_options(decls):
    assert types(decls + SLOTS) == []


def test_none_in_the_other_enums_slot_is_still_its_own():
    # Control: the slot names Display, so `None` is Display's.
    src = OPTION + DISPLAY + (
        "fn f() -> Display\n"
        "    return None\n\n"
        "fn g() -> Display\n"
        "    let d: Display = None\n"
        "    d\n")
    assert types(src) == []


def test_a_slot_that_doesnt_declare_the_name_still_mismatches():
    # Control: the slot doesn't decide, so `Block` stays Display's and the
    # mismatch is still reported.
    src = OPTION + DISPLAY + "fn f() -> Option<i32>\n    return Block\n"
    assert types(src) == [
        "<stdin>:10:5: return type Display doesn't match expected Option<i32>"]


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
