"""Regression tests for AGAST #1669: a bare "..." initialiser for a StrView
field in a struct literal under ritz1.

    struct Slot
        present: bool
        value: StrView
    let s = Slot { present: true, value: "hey" }

A bare "..." lowers to `%Span$u8` (AGAST #98); emit_struct_lit_field_store
stored that register with `store %StrView`, which clang rejects ("defined with
type '%"Span$u8"' but expected '%StrView'"). The two are the layout-equivalent
{ ptr, i64 } pair, so the field store must rebuild the value as the field's
type, as the struct `ret` paths already do (coerce_struct_ret_value).

Each program returns 42 when correct and a distinct small code naming the
check that failed otherwise. ritz0 is the oracle; everything runs at RUNTIME
and reads the field back (len and bytes), so a zeroed or swapped field cannot
pass.
"""

import pytest

from test_ritz1_bool_fields import EXPECTED, _run, ritz1_bin  # noqa: F401, F811

PROGRAMS = {
    # The ticket repro, with the bytes read back too.
    "ticket_repro": """\
import ritzlib.strview

struct Slot
    present: bool
    value: StrView

pub fn main() -> i32
    let s = Slot { present: true, value: "hey" }
    if s.value.len != 3
        return 1
    if *(s.value.ptr + 2) != 121
        return 2
    if not s.present
        return 3
    return 42
""",
    # By value: literal in a `var`, a tail-expression literal, a `return`
    # literal and a reassignment, each read back through a by-value param.
    "by_value": """\
import ritzlib.strview

struct Spec
    id: i64
    name: StrView
    tag: i32

# Consumes `sp` (by-value structs move), so each value is checked once.
# Returns 0 when len, the last byte and tag all match, else 1/2/3.
fn check(sp: Spec, n: i64, last: i64, tag: i32) -> i32
    if sp.name.len != n
        return 1
    if *(sp.name.ptr + n - 1) as i64 != last
        return 2
    if sp.tag != tag
        return 3
    0

fn tail_lit() -> Spec
    Spec { id: 2, name: "abcd", tag: 7 }

fn ret_lit() -> Spec
    return Spec { id: 3, name: "hello", tag: 8 }

pub fn main() -> i32
    var a = Spec { id: 1, name: "xy", tag: 6 }
    if a.id != 1
        return 1
    if check(a, 2, 121, 6) != 0
        return 2
    if check(tail_lit(), 4, 100, 7) != 0
        return 3
    if check(ret_lit(), 5, 111, 8) != 0
        return 4
    var b = Spec { id: 4, name: "zz", tag: 0 }
    b = Spec { id: 9, name: "q", tag: 10 }
    if check(b, 1, 113, 10) != 0
        return 5
    return 42
""",
    # Nested: the literal sits in an inner struct literal, written in place.
    "nested": """\
import ritzlib.strview

struct Inner
    tag: i32
    name: StrView

struct Outer
    k: i64
    inner: Inner
    label: StrView

pub fn main() -> i32
    let o = Outer { k: 9, inner: Inner { tag: 5, name: "xyz" }, label: "lbl!" }
    if o.inner.name.len != 3
        return 1
    # Read the bytes through a one-level chain: `*(o.inner.name.ptr + 1)`
    # loads i64 under ritz1, a separate deref-width bug (filed from #1669).
    let nm: StrView = o.inner.name
    if *(nm.ptr + 1) != 121
        return 2
    if o.label.len != 4 or *(o.label.ptr + 3) != 33
        return 3
    if o.k != 9 or o.inner.tag != 5
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
def test_ritz1_struct_lit_strview_field(ritz1_bin, tmp_path, name):  # noqa: F811
    """ritz1 stored a "..." %Span$u8 into a %StrView field (#1669)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
