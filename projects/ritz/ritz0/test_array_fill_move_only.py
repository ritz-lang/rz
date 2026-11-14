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

Each row runs on ritz0, ritz1 and ritz1_selfhosted, and each that compiles
must return ritz0's result on all three (#2976).
"""

import pytest

from array_rules import FILL_MOVE_ONLY
from test_ref_into_value import COMPILERS, _assert_refused, _run

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

# Element size 16, not 8: a fill stored as i64 slots would misplace `y`.
struct D
    c: C
    y: i64

fn make() -> Res
    return Res { h: 1 }

fn make_c() -> C
    return C { x: 6 }

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
    # `[r; 1]` moves `r` into the element: one drop, of `a[0]`, not of `r` too.
    "one_element": (DEFS + """
fn f() -> i32
    var r: Res = make()
    r.h = 3
    let a: [1]Res = [r; 1]
    return a[0].h

pub fn main() -> i32
    let h = f()
    return h * 10 + DROPS
""", 31),
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
    "struct_literal": (DEFS + """
pub fn main() -> i32
    let a: [3]C = [C { x: 4 }; 3]
    return a[2].x
""", 4),
    "nested_struct_param": (DEFS + """
fn h(d: D) -> i32
    let a: [3]D = [d; 3]
    return a[2].c.x + a[1].y as i32 + a[0].c.x

pub fn main() -> i32
    return h(D { c: C { x: 2 }, y: 5 })
""", 9),
    # An unannotated fill of a struct is `[3]C`, as `let a = [c, c, c]` is.
    "untyped_let": (DEFS + """
pub fn main() -> i32
    let c: C = C { x: 2 }
    let a = [c; 3]
    return a[2].x + a[0].x
""", 4),
    "assign_temporary": (DEFS + """
pub fn main() -> i32
    var a: [2]C = [C { x: 0 }; 2]
    a = [make_c(); 2]
    return a[0].x + a[1].x
""", 12),
    "generic_struct_instance": (DEFS + """
fn g<T>(t: T) -> T
    let a: [2]T = [t; 2]
    return a[1]

pub fn main() -> i32
    let c: C = g<C>(C { x: 5 })
    return c.x
""", 5),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(REFUSED))
def test_move_only_fill_of_more_than_one_is_refused(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, DEFS + REFUSED[site] + ENTRY, FILL_MOVE_ONLY)


# AGAST #2976: ritz1 stored a struct fill's value as an i64 into `[N x i64]`
# slots (clang refused the IR), and `[r; 1]` left `r` live to drop twice. Each
# element is now the value's `%T` aggregate, and the fill moves its value. A
# row that runs to ritz0's result also compiled: no separate "not refused" row.
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(ACCEPTED))
def test_fill_that_cannot_duplicate_compiles(tmp_path, compiler, site):
    src, want = ACCEPTED[site]
    assert _run(compiler, tmp_path, site, src) == want

