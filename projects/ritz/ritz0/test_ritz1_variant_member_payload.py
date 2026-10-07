"""Regression tests for AGAST #1664: `Some(s.value)` / `Ok(s.value)` where
`value` is a struct-typed field (StrView) under ritz1.

ritzlib/argspec.ritz:427 (77_args):

    fn value_at(p: @ArgParser, idx: i32) -> Option<StrView>
        let s = slot_at(p, idx)
        if s.present
            return Some(s.value)        # value: StrView

ritz1 loaded the field as `%StrView` and then stored it into the Option
payload with `store i64 %<%StrView>` — emit_variant_struct only recognised an
ident, a string literal or a call as an aggregate payload.  A member chain
whose innermost field is a struct is an aggregate too.

Each program returns 42 when correct and a distinct small code naming the
check that failed otherwise.  ritz0 is the oracle; everything runs at RUNTIME
and reads the payload back (len and bytes), so a zeroed or truncated payload
cannot pass.

String literals reach StrView fields through a typed `let svN: StrView`
local: a bare "..." initialiser in a struct literal is the separate #1669.
"""

import pytest

from test_ritz1_bool_fields import EXPECTED, _run, ritz1_bin  # noqa: F401, F811

PROGRAMS = {
    # The ticket repro, through an @ref param, with the payload read back.
    "ticket_repro_ref": """\
import ritzlib.option
import ritzlib.strview

struct Slot
    present: bool
    value: StrView

fn get(s: @Slot) -> Option<StrView>
    if s.present
        return Some(s.value)
    None

fn olen(o: Option<StrView>) -> i64
    match o
        Some(v) => v.len
        None => -1

fn obyte(o: Option<StrView>, i: i64) -> i64
    match o
        Some(v) => *(v.ptr + i) as i64
        None => -1

pub fn main() -> i32
    let sv1: StrView = "hey"
    let s = Slot { present: true, value: sv1 }
    if olen(get(@s)) != 3
        return 1
    if obyte(get(@s), 2) != 121
        return 2
    let sv2: StrView = "x"
    let n = Slot { present: false, value: sv2 }
    if olen(get(@n)) != -1
        return 3
    return 42
""",
    # By-value struct (param and local) and a tail-expression Some(field);
    # the field is named `default` as in argspec's ArgSpec.
    "by_value_and_default": """\
import ritzlib.option
import ritzlib.strview

struct Spec
    id: i64
    default: StrView

fn dflt(f: Spec) -> Option<StrView>
    Some(f.default)

fn local_some() -> Option<StrView>
    let sv3: StrView = "abcd"
    let f = Spec { id: 1, default: sv3 }
    return Some(f.default)

fn olen(o: Option<StrView>) -> i64
    match o
        Some(v) => v.len
        None => -1

fn obyte(o: Option<StrView>, i: i64) -> i64
    match o
        Some(v) => *(v.ptr + i) as i64
        None => -1

pub fn main() -> i32
    let sv4: StrView = "hello"
    let f1 = Spec { id: 7, default: sv4 }
    if olen(dflt(f1)) != 5
        return 1
    let sv5: StrView = "hello"
    let f2 = Spec { id: 8, default: sv5 }
    if obyte(dflt(f2), 4) != 111
        return 2
    if olen(local_some()) != 4
        return 3
    if obyte(local_some(), 0) != 97
        return 4
    return 42
""",
    # Nested member chain and a raw pointer, plus Ok(field) for Result.
    "nested_ptr_and_ok": """\
import ritzlib.option
import ritzlib.result
import ritzlib.strview

struct Inner
    tag: i32
    name: StrView

struct Outer
    k: i64
    inner: Inner

fn nested(o: @Outer) -> Option<StrView>
    Some(o.inner.name)

fn via_ptr(p: *Inner) -> Option<StrView>
    Some(p.name)

fn as_ok(i: @Inner) -> Result<StrView, i32>
    if i.tag < 0
        return Err(i.tag)
    Ok(i.name)

fn olen(o: Option<StrView>) -> i64
    match o
        Some(v) => v.len
        None => -1

fn obyte(o: Option<StrView>, i: i64) -> i64
    match o
        Some(v) => *(v.ptr + i) as i64
        None => -1
\nfn rlen(r: Result<StrView, i32>) -> i64
    match r
        Ok(v) => v.len
        Err(e) => e as i64 - 100

fn rbyte(r: Result<StrView, i32>, i: i64) -> i64
    match r
        Ok(v) => *(v.ptr + i) as i64
        Err(e) => -1

pub fn main() -> i32
    let sv6: StrView = "xyz"
    let i0 = Inner { tag: 5, name: sv6 }
    let o = Outer { k: 9, inner: i0 }
    if olen(nested(@o)) != 3
        return 1
    if obyte(nested(@o), 1) != 121
        return 2
    let sv7: StrView = "uvwz"
    let i = Inner { tag: 5, name: sv7 }
    if olen(via_ptr(@i)) != 4
        return 3
    if obyte(via_ptr(@i), 3) != 122
        return 4
    if rlen(as_ok(@i)) != 4
        return 5
    if rbyte(as_ok(@i), 0) != 117
        return 6
    let sv8: StrView = "q"
    let bad = Inner { tag: -4, name: sv8 }
    if rlen(as_ok(@bad)) != -104
        return 7
    return 42
""",
    # A pointer-to-struct field carries a type name too but loads as a
    # pointer, not an aggregate: Some(h.target) must stay a scalar store.
    "ptr_field_stays_scalar": """\
import ritzlib.option
import ritzlib.strview

struct Inner
    tag: i32
    name: StrView

struct Holder
    k: i64
    target: *Inner

fn pick(h: @Holder) -> Option<*Inner>
    Some(h.target)

fn read_tag(p: *Inner) -> i64
    p.tag as i64

fn tag_of(o: Option<*Inner>) -> i64
    match o
        Some(p) => read_tag(p)
        None => -1

pub fn main() -> i32
    let sv: StrView = "ab"
    var i = Inner { tag: 11, name: sv }
    let h = Holder { k: 3, target: @i }
    if tag_of(pick(@h)) != 11
        return 1
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
def test_ritz1_variant_member_payload(ritz1_bin, tmp_path, name):  # noqa: F811
    """ritz1 stored a struct-typed field payload as i64 (#1664)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
