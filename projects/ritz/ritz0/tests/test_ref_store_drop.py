"""A store through a reference drops the old value; through `*T` it doesn't
(LARB R58, AGAST #3474 ritz0 / #3475 ritz1).

LANGUAGE_SPEC §13.6: a store through an `@&T`, a `:&` parameter, or a place
reached through one, drops the old value, in the same order as a store to an
owned binding: after the value, before the store.  A mutable borrow always
refers to a live owned value.  A store through a `*T` is a raw write and drops
nothing: a raw pointer may point at uninitialised memory (`box_new`).

`S`'s drop appends its `x` to `D` as a decimal digit; `mk` appends 8 before
it builds its value, so `D` spells out what dropped and in what order.  Each
program exits 42 when `D` is what the spec says, otherwise `D % 200`.

Runs on ritz0, ritz1 and ritz1_selfhosted; ritz0 is the oracle.
"""

import pytest
from test_ref_into_value import COMPILERS, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

PRELUDE = """\
var D: i64 = 0

struct S
    x: i64

impl Drop for S
    fn drop(self:& S)
        D = D * 10 + self.x

struct Holder
    t: S

struct Outer
    h: Holder

struct Arr
    a: [2]S

fn mk(x: i64) -> S
    D = D * 10 + 8
    return S { x: x }

fn verdict(want: i64) -> i32
    if D == want
        return 42
    let r = (D % 200) as i32
    if r == 42
        return 43
    return r

"""

# v (8), then the old value (1) drops, then the store; the caller's binding
# drops the new value (5) at its scope end.
DROPS = 815
# Through a `*T` the old value (1) is never dropped.
RAW = 85

RUNS = {
    "field_through_mut_ref": ("""\
fn put(p: @&Holder)
    p.t = mk(5)

fn f()
    var h = Holder { t: S { x: 1 } }
    put(@&h)
""", DROPS),
    "field_through_borrow_param": ("""\
fn put(h:& Holder)
    h.t = mk(5)

fn f()
    var h = Holder { t: S { x: 1 } }
    put(h)
""", DROPS),
    "field_through_local_mut_ref": ("""\
fn f()
    var h = Holder { t: S { x: 1 } }
    let r = @&h
    r.t = mk(5)
""", DROPS),
    # A place reached through a reference: a field of a field.
    "nested_field_through_mut_ref": ("""\
fn put(p: @&Outer)
    p.h.t = mk(5)

fn f()
    var o = Outer { h: Holder { t: S { x: 1 } } }
    put(@&o)
""", DROPS),
    "deref_through_mut_ref": ("""\
fn put(p: @&S)
    *p = mk(5)

fn f()
    var s = S { x: 1 }
    put(@&s)
""", DROPS),
    # `*h = v` on a `h:& S` borrow stores to the caller's S (#2972).
    "deref_through_borrow_param": ("""\
fn put(h:& S)
    *h = mk(5)

fn f()
    var s = S { x: 1 }
    put(s)
""", DROPS),
    # `h = v` on a `h:& S` borrow is a store to the caller's S, too.
    "whole_through_borrow_param": ("""\
fn put(h:& S)
    h = mk(5)

fn f()
    var s = S { x: 1 }
    put(s)
""", DROPS),
    # In a generic body the drop is decided at the instance's `T`: the
    # typing pass types the monomorphised module the emitter emits.
    "deref_through_mut_ref_generic": ("""\
fn put<T>(p: @&T, v: T)
    *p = v

fn f()
    var s = S { x: 1 }
    put(@&s, mk(5))
""", DROPS),
    # An element of an array reached through a reference (R58 with R39):
    # v (8), the old a[0] (1); at the caller's scope end a[0] (5), a[1] (2).
    "element_through_mut_ref": ("""\
fn put(p: @&Arr)
    p.a[0] = mk(5)

fn f()
    var r = Arr { a: [S { x: 1 }, S { x: 2 }] }
    put(@&r)
""", 8152),
    # An element of an array behind a `:& [2]S` borrow (the array-local
    # element store, STMT_INDEX_ASSIGN): v (8), the old a[1] (2); at the
    # caller's scope end a[0] (1), a[1] (5).
    "element_through_array_borrow": ("""\
fn put(a:& [2]S)
    a[1] = mk(5)

fn f()
    var a: [2]S = [S { x: 1 }, S { x: 2 }]
    put(@&a)
""", 8215),
    # As an assignment expression (a match arm), `*p = v` and `p.t = v`
    # through a reference drop the old value too (AGAST #3583).
    "match_arm_deref_through_mut_ref": ("""\
fn put(p: @&S, o: Option<i64>)
    match o
        Some(k) => *p = mk(k)
        None => D = 0

fn f()
    var s = S { x: 1 }
    put(@&s, Some(5))
""", DROPS),
    "match_arm_field_through_mut_ref": ("""\
fn put(p: @&Holder, o: Option<i64>)
    match o
        Some(k) => p.t = mk(k)
        None => D = 0

fn f()
    var h = Holder { t: S { x: 1 } }
    put(@&h, Some(5))
""", DROPS),
    # Through a `*T` in a match arm: a raw write, nothing drops.
    "match_arm_deref_through_pointer": ("""\
fn put(p: *S, o: Option<i64>)
    match o
        Some(k) => *p = mk(k)
        None => D = 0

fn f()
    var s = S { x: 1 }
    put(@&s, Some(5))
""", RAW),
    "deref_through_pointer": ("""\
fn put(p: *S)
    *p = mk(5)

fn f()
    var s = S { x: 1 }
    put(@&s)
""", RAW),
    "field_through_pointer": ("""\
fn put(p: *Holder)
    p.t = mk(5)

fn f()
    var h = Holder { t: S { x: 1 } }
    put(@&h)
""", RAW),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_store_through_reference_drops(compiler, tmp_path, name):
    body, want = RUNS[name]
    src = (PRELUDE + body + "\npub fn main() -> i32\n    f()"
           + f"\n    return verdict({want})\n")
    rc = _run(compiler, tmp_path, name, src)
    assert rc == 42, f"{compiler} {name}: D % 200 == {rc}, spec says D == {want}"
