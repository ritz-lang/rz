"""AGAST #1512: ritz1 dispatches a method call whose receiver is a struct field.

THE DEFECT

emit_expr_method (ritz1/src/emitter_expr_call.ritz) resolved the receiver
type for identifier, call, method and struct-literal receivers only. A
field receiver -- `r.raw.push(9)`, `q.a.get()` -- left type_name null and
the call failed with "cannot determine receiver type for method call".
monomorph.ritz likewise only instantiated generic methods (`vec_push$u8`)
from an identifier receiver, so a `Vec<u8>` field's method had no body.

Covered: a generic `Vec<u8>` field (method via the UFCS `vec_` fallback,
both by-mut-ref `push` and by-ref `len()`), a user impl method on a field
(by value `self` and by `@&` mutating `self`), and a nested field
receiver `o.q.a.get()`.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg, ritz1_bin  # noqa: F401

# The ticket's repro: `push` mutates the field in place, so len must be 1.
VEC_FIELD = """\
import ritzlib.memory
import ritzlib.gvec

struct R
    raw: Vec<u8>

pub fn main() -> i32
    var r: R = R { raw: vec_new<u8>() }
    r.raw.push(9)
    r.raw.push(33)
    let n: i64 = r.raw.len()
    let b: u8 = r.raw.get(1)
    return (n + b as i64) as i32
"""

# A user impl method on a field, plus a mutating one that must write through
# to the field (not to a copy).
USER_FIELD = """\
struct A
    v: i64

impl A
    fn get(self) -> i64
        self.v
    fn bump(self: @&A, by: i64)
        self.v = self.v + by

struct Q
    x: i64
    a: A

struct O
    pad: i64
    q: Q

pub fn main() -> i32
    var q: Q
    q.x = 5
    q.a.v = 10
    q.a.bump(30)
    var o: O
    o.pad = 1
    o.q.x = 7
    o.q.a.v = 2
    return (q.a.get() + o.q.a.get()) as i32
"""

# Roots other than an annotated local: a `@&R` param and an un-annotated
# `var r = R { ... }`.
VEC_FIELD_ROOTS = """\
import ritzlib.memory
import ritzlib.gvec

struct R
    raw: Vec<u8>

fn fill(r: @&R) -> i64
    r.raw.push(4)
    r.raw.push(5)
    r.raw.len() * 10 + r.raw.get(1) as i64

pub fn main() -> i32
    var r = R { raw: vec_new<u8>() }
    let n: i64 = fill(@&r)
    r.raw.push(7)
    return (n + r.raw.len()) as i32
"""

# ritz1-only cases, hand-derived expectations.  ritz0 is not a usable
# oracle for either (AGAST #1559):
#   - it never instantiates `vec_get$u8` for a field of an UN-annotated
#     `var r = R { ... }` ("No method 'get' found for type 'Vec$u8'");
#   - it loses a push through a `*Vec<u8>` field (len stays 3, `get(3)`
#     reads garbage).
# A `*Vec<u8>` field dispatches through the pointer the field holds, so the
# push lands in `r.raw`: len 4 (4, 5, 7, 20) * 10 + element 3 (20) = 60.
VEC_PTR_FIELD = """\
import ritzlib.memory
import ritzlib.gvec

struct R
    raw: Vec<u8>

struct P
    vp: *Vec<u8>

pub fn main() -> i32
    var r: R = R { raw: vec_new<u8>() }
    r.raw.push(4)
    r.raw.push(5)
    r.raw.push(7)
    var p: P
    p.vp = @r.raw
    p.vp.push(20)
    return (r.raw.len() * 10 + p.vp.get(3) as i64) as i32
"""

# `vec_get$u8` is reached ONLY through a field of an un-annotated root.
# len 2 * 10 + element 1 (22) = 42.
VEC_INFERRED_ROOT = """\
import ritzlib.memory
import ritzlib.gvec

struct R
    raw: Vec<u8>

pub fn main() -> i32
    var r = R { raw: vec_new<u8>() }
    r.raw.push(11)
    r.raw.push(22)
    return (r.raw.len() * 10 + r.raw.get(1) as i64) as i32
"""

RITZ1_ONLY = {
    "vec_ptr_field": (VEC_PTR_FIELD, 60),
    "vec_inferred_root": (VEC_INFERRED_ROOT, 42),
}

CASES = {
    "vec_u8_field": (VEC_FIELD, 35),
    "vec_u8_field_roots": (VEC_FIELD_ROOTS, 20 + 5 + 3),
    "user_impl_field": (USER_FIELD, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_field_receiver(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY))
def test_ritz1_only_field_receiver(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = RITZ1_ONLY[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want
