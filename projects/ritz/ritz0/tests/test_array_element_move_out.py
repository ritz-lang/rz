#!/usr/bin/env python3
"""A move-only value can't be moved out of an array element (LANGUAGE_SPEC
§13.2, AGAST #2268).

The array still owns, and drops, each of its elements: it has no flag for one
of them having moved. Before, `var x = a[0]; consume(x)` with a Drop element
compiled on ritz0 and dropped the one value three times (`consume`, `x` and
`a`), and ritz1 failed at clang. A by-value read of a move-only element, or of
a move-only field of one, is now a located error at the place, worded the same
by ritz0 (move_checker.py) and ritz1 (ownership.ritz), as Rust's E0508 is. A
copy element, a copy field of a move-only one, a borrow of one, a method that
lends it and a match on one still read it, and compile.

Each row runs on ritz0, ritz1 and ritz1_selfhosted.
"""

import re

import pytest

from array_rules import MOVE_OUT_OF_ELEMENT
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _located, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

DEFS = """\
var DROPS: i32 = 0

struct Res
    h: i32

impl Drop for Res
    fn drop(self: @&Res)
        DROPS = DROPS + 1

impl Res
    fn burn(self: Res) -> i32
        return self.h

    fn peek(self: @Res) -> i32
        return self.h

struct Holder
    r: Res
    n: i32

struct Rack
    rs: [2]Res

struct C
    x: i32

enum Slot
    Full(Res)
    Empty

fn make(h: i32) -> Res
    return Res { h: h }

fn eat(r: Res) -> i32
    return r.h

fn look(r: @Res) -> i32
    return r.h

fn mka() -> [2]Res
    return [make(1), make(2)]

"""

ENTRY = """
pub fn main() -> i32
    return 0
"""

# `^` is where each compiler must report the error: the start of the place.
REFUSED = {
    # The ticket's program: the binding, then the call, would each drop it.
    "binding": """\
fn f()
    var a: [1]Res = [make(1)]
    var x = ^a[0]
    eat(x)
""",
    "argument": """\
fn f()
    var a: [2]Res = [make(1), make(2)]
    eat(^a[1])
""",
    # A by-value array parameter owns its elements as a local does.
    "return_from_param": """\
fn f(a: [2]Res) -> Res
    return ^a[1]
""",
    "assign": """\
fn f()
    var a: [1]Res = [make(1)]
    var x: Res = make(2)
    x = ^a[0]
""",
    "into_array_literal": """\
fn f()
    var a: [1]Res = [make(1)]
    let b: [1]Res = [^a[0]]
""",
    # Move-only through a field: Holder drops its Res.
    "whole_struct_element": """\
fn f()
    var hs: [1]Holder = [Holder { r: make(1), n: 0 }]
    let h = ^hs[0]
""",
    # A move-only field of an element is the element's to drop.
    "field_of_element": """\
fn f()
    var hs: [1]Holder = [Holder { r: make(1), n: 0 }]
    eat(^hs[0].r)
""",
    "element_of_array_field": """\
fn f(k: Rack) -> i32
    return eat(^k.rs[0])
""",
    "row_of_nested_array": """\
fn f()
    let row: [2]Res = [make(1), make(2)]
    var a: [1][2]Res = [row]
    eat(^a[0][1])
""",
    # A by-value `self` takes the receiver.
    "by_value_receiver": """\
fn f() -> i32
    var a: [1]Res = [make(1)]
    return ^a[0].burn()
""",
    # A call's array result drops every element too.
    "temporary_array": """\
fn f() -> i32
    return eat(^mka()[1])
""",
}

# What still compiles. Each returns its result * 10 + DROPS: every element is
# dropped once, by its array.
ACCEPTED = {
    "copy_element": (DEFS + """
fn f() -> i32
    var a: [2]C = [C { x: 3 }, C { x: 4 }]
    let c = a[1]
    return c.x + a[1].x

pub fn main() -> i32
    return f() * 10 + DROPS
""", 80),
    "copy_field_of_move_only_element": (DEFS + """
fn f() -> i32
    var a: [2]Res = [make(3), make(4)]
    let h = a[1].h
    return h

pub fn main() -> i32
    let r = f()
    return r * 10 + DROPS
""", 42),
    "borrowed_element": (DEFS + """
fn f() -> i32
    var a: [2]Res = [make(3), make(4)]
    return look(@a[1]) + a[0].peek()

pub fn main() -> i32
    let r = f()
    return r * 10 + DROPS
""", 72),
    "match_on_element": (DEFS + """
fn f() -> i32
    var a: [1]Slot = [Slot.Full(make(5))]
    match a[0]
        Slot.Empty => return 0
        _ => return 5

pub fn main() -> i32
    let r = f()
    return r * 10 + DROPS
""", 51),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(REFUSED))
def test_move_out_of_an_element_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, DEFS + REFUSED[site] + ENTRY, MOVE_OUT_OF_ELEMENT)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(ACCEPTED))
def test_a_read_that_moves_nothing_out_compiles(tmp_path, compiler, site):
    src, want = ACCEPTED[site]
    assert _run(compiler, tmp_path, site, src) == want


# A Vec doesn't drop its elements (gvec.ritz has no `impl Drop`), so `v[i]`
# leaves it nothing to drop twice: only an array is refused. A Vec of a Drop type
# is refused elsewhere, in gvec.ritz's generic bodies (test_move_out_through_index
# .py), so this asserts only that the marked line has no element error.
VEC_ELEMENT = "import ritzlib.gvec\n\n" + DEFS + """\
fn f(v: Vec<Res>) -> i32
    return eat(^v[0])
""" + ENTRY


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_vec_element_is_not_an_array_element(tmp_path, compiler):
    src, where = _located(VEC_ELEMENT)
    comp, _, _ = _compile(compiler, tmp_path, "vec_element", src)
    out = comp.stdout + comp.stderr
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    line = where.split(":")[0]
    assert not [f for f in found if f[0].split(":")[0] == line and f[1] == MOVE_OUT_OF_ELEMENT], \
        f"{compiler}: reported an element move out at line {line}:\n{out[-2000:]}"
