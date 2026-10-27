"""Regression tests for AGAST #1673: `*(a.b.c.ptr + i)` through a 2+-level
member chain under ritz1.

ritz1 resolved the pointee type of `*(ptr + i)` for a one-level chain
(`s.value.ptr`) but not for deeper ones (`o.inner.name.ptr`): it emitted
`load i64` (an 8-byte read of a u8), so the compare failed at runtime.

Each program returns 42 when correct and a distinct small code naming the
check that failed otherwise. ritz0 is the oracle; everything is checked at
RUNTIME, because the bad load compiles cleanly and only gives a wrong answer.
"""

import pytest

from test_ritz1_bool_fields import EXPECTED, _run

PROGRAMS = {
    # The ticket repro: a 2-level chain to a StrView's *u8.
    "two_level_u8": """\
import ritzlib.strview

struct Inner
    tag: i32
    name: StrView

struct Outer
    k: i64
    inner: Inner

pub fn main() -> i32
    let i0 = Inner { tag: 5, name: "xyz" }
    let o = Outer { k: 9, inner: i0 }
    if *(o.inner.name.ptr + 1) != 121
        return 2
    if *(o.inner.name.ptr + 2) != 122
        return 3
    return 42
""",
    # Three levels to a *u8; the neighbouring bytes differ, so an 8-byte
    # read cannot compare equal.
    "three_level_u8": """\
import ritzlib.strview

struct C
    tag: i32
    name: StrView

struct B
    x: i64
    c: C

struct A
    y: i32
    b: B

pub fn main() -> i32
    let a = A { y: 1, b: B { x: 2, c: C { tag: 3, name: "abc" } } }
    if *(a.b.c.name.ptr + 0) != 97
        return 2
    if *(a.b.c.name.ptr + 1) != 98
        return 3
    return 42
""",
    # 2- and 3-level chains to a raw *i32 field (not a StrView).
    "i32_pointee": """\
struct Buf
    n: i64
    p: *i32

struct Mid
    t: i32
    buf: Buf

struct Top
    z: i64
    mid: Mid

pub fn main() -> i32
    var arr: [4]i32 = [10, 20, 30, 40]
    let m = Mid { t: 1, buf: Buf { n: 4, p: @arr[0] } }
    if *(m.buf.p + 1) != 20
        return 2
    let t = Top { z: 7, mid: m }
    if *(t.mid.buf.p + 2) != 30
        return 3
    if *(t.mid.buf.p + 3) + 2 != 42
        return 4
    return 42
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_deref_member_chain(ritz1_bin, tmp_path, name):
    """ritz1 loaded i64 for `*(a.b.c.ptr + i)` past one member level (#1673)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
