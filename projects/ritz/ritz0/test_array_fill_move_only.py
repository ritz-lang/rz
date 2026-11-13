#!/usr/bin/env python3
"""`[v; n]` copies one value into n elements, so a move-only `v` fills at most
one (LANGUAGE_SPEC §13.1, AGAST #2963).

Before, `[r; 2]` with `r: Res` and `impl Drop for Res` compiled on both
compilers, and both elements dropped the same resource. A fill of a move-only
value with a count above 1 is now a located error at the `[`, worded the same by
ritz0 (move_checker.py) and ritz1 (ref_check.ritz), whether the value is a
binding, a field or a temporary (`[make(); 2]`), and in a generic instance at a
move-only `T`. `[r; 1]` moves `r` into the one element, and a copy type fills
any count.

Each row runs on ritz0, ritz1 and ritz1_selfhosted. ritz1 can't yet lower a
fill of a struct value at all (#2976), so the rows that should compile are held
to ritz0 there by strict xfails.
"""

import pytest

from array_rules import FILL_MOVE_ONLY
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _run

pytestmark = pytest.mark.integration

DEFS = """\
var DROPS: i32 = 0

struct Res
    h: i32

impl Drop for Res
    fn drop(self: @&Res)
        DROPS = DROPS + 1

struct Holder
    r: Res

struct C
    x: i32

fn make() -> Res
    return Res { h: 1 }

"""

ENTRY = """
pub fn main() -> i32
    return 0
"""

# `^` is where each compiler must report the error: the fill's `[`.
REFUSED = {
    "owned_param": """\
fn f(r: Res)
    let a: [2]Res = ^[r; 2]
""",
    "local": """\
fn f()
    var r: Res = make()
    let a: [3]Res = ^[r; 3]
""",
    "untyped_let": """\
fn f(r: Res)
    let a = ^[r; 2]
""",
    "temporary_call": """\
fn f()
    let a: [2]Res = ^[make(); 2]
""",
    "temporary_literal": """\
fn f()
    let a: [2]Res = ^[Res { h: 1 }; 2]
""",
    # Move-only through a field: Holder drops its Res.
    "move_only_field": """\
fn f(h: Holder)
    let a: [2]Holder = ^[h; 2]
""",
    "element": """\
fn f(a: [2]Res)
    let b: [2]Res = ^[a[0]; 2]
""",
    "assign": """\
fn f(r: Res)
    var a: [2]Res
    a = ^[r; 2]
""",
    "argument": """\
fn g(a: [2]Res)
    pass

fn f(r: Res)
    g(^[r; 2])
""",
    # Checked per instance: `T` is `Res` here.
    "generic_instance": """\
fn g<T>(t: T)
    let a: [2]T = ^[t; 2]

fn f(r: Res)
    g<Res>(r)
""",
}

# What still compiles: one element owns the value, and a copy type fills any count.
ACCEPTED = {
    "one_element": (DEFS + """
pub fn main() -> i32
    var r: Res = make()
    r.h = 3
    let a: [1]Res = [r; 1]
    return a[0].h
""", 3),
    "temporary_one_element": (DEFS + """
pub fn main() -> i32
    let a: [1]Res = [make(); 1]
    return a[0].h + 2
""", 3),
    "copy_type": (DEFS + """
pub fn main() -> i32
    let c: C = C { x: 1 }
    let a: [3]C = [c; 3]
    return a[0].x + a[1].x + a[2].x
""", 3),
    "copy_generic_instance": (DEFS + """
fn g<T>(t: T) -> T
    let a: [2]T = [t; 2]
    return a[1]

pub fn main() -> i32
    return g<i32>(3)
""", 3),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(REFUSED))
def test_move_only_fill_of_more_than_one_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, DEFS + REFUSED[site] + ENTRY, FILL_MOVE_ONLY)


# ritz1 lowers a fill of a struct value, or of a generic `T`, into `[N x i64]`
# slots: clang refuses the IR. Only a `c:& C` source is copied right (#2288).
LOWERING_GAP = "AGAST #2976: ritz1 stores a struct fill's value as an i64"


def _accepted_params():
    for site in sorted(ACCEPTED):
        for compiler in COMPILERS:
            marks = [pytest.mark.xfail(strict=True, reason=LOWERING_GAP)] if compiler != "ritz0" else []
            yield pytest.param(site, compiler, marks=marks)


@pytest.mark.parametrize("site,compiler", list(_accepted_params()))
def test_fill_that_cannot_duplicate_compiles(tmp_path, compiler, site):
    src, want = ACCEPTED[site]
    assert _run(compiler, tmp_path, site, src) == want


# The rule's own half of the above, which ritz1 meets already: these compile.
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(ACCEPTED))
def test_fill_that_cannot_duplicate_is_not_refused(tmp_path, compiler, site):
    comp, ll, _ = _compile(compiler, tmp_path, site, ACCEPTED[site][0])
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
