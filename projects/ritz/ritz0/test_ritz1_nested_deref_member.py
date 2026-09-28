"""AGAST #1510: ritz1 reads/writes a field through a nested deref.

THE DEFECT

emit_member_ptr / emit_expr_member (ritz1) resolved the struct type of a
deref base `(*X).f` only when X was a bare identifier. A deref of a field
(`(*(*b).ops).n`, `(*b.ops).n`) or of a deref (`(**pp).n`) left the
struct type unresolved and the member failed "unhandled EXPR_MEMBER".

The fix resolves the deref operand's static pointee type recursively
(deref of member of deref ...) and GEPs on it.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg, ritz1_bin  # noqa: F401

_STRUCTS = """\
struct Ops
    pad: i32
    n: i32

struct B
    tag: i32
    ops: *Ops

struct C
    b: B
    bp: *B

"""

# The ticket's repro: deref of a field of a deref.
DEREF_MEMBER_DEREF = (
    _STRUCTS
    + """\
fn g(b: *B) -> i32
    return (*(*b).ops).n

pub fn main() -> i32
    var o: Ops = Ops { pad: 1, n: 4 }
    var b: B = B { tag: 9, ops: @o }
    return g(@b)
"""
)

# Deref of a field accessed with auto-deref (`b.ops` through a *B).
DEREF_AUTO_MEMBER = (
    _STRUCTS
    + """\
fn g(b: *B) -> i32
    return (*b.ops).n

pub fn main() -> i32
    var o: Ops = Ops { pad: 1, n: 5 }
    var b: B = B { tag: 9, ops: @o }
    return g(@b)
"""
)

# Double deref of a pointer-to-pointer param.
DOUBLE_DEREF = (
    _STRUCTS
    + """\
fn g(pp: **Ops) -> i32
    return (**pp).n

pub fn main() -> i32
    var o: Ops = Ops { pad: 1, n: 6 }
    var p: *Ops = @o
    return g(@p)
"""
)

# Deeper chain through an embedded struct and a second pointer hop, both
# read and store forms.  (*(*(*c).bp).ops).n = 30; then read 30 + 7.
DEEP_CHAIN_STORE = (
    _STRUCTS
    + """\
fn g(c: *C) -> i32
    (*(*(*c).bp).ops).n = 30
    (*(*c).b.ops).pad = 7
    return (*(*(*c).bp).ops).n + (*c.b.ops).pad

pub fn main() -> i32
    var o: Ops = Ops { pad: 1, n: 2 }
    var o2: Ops = Ops { pad: 3, n: 4 }
    var b: B = B { tag: 9, ops: @o }
    var c: C
    c.b.tag = 1
    c.b.ops = @o2
    c.bp = @b
    let r: i32 = g(@c)
    return r + o.n - 30 + o2.pad - 7
"""
)

# Store through a double deref.
DOUBLE_DEREF_STORE = (
    _STRUCTS
    + """\
fn g(pp: **Ops)
    (**pp).n = 11

pub fn main() -> i32
    var o: Ops = Ops { pad: 1, n: 6 }
    var p: *Ops = @o
    g(@p)
    return o.n
"""
)

# Compound assignment desugars to the same `(*X).f = (*X).f op v` store.
# n: 6 += 5 -> 11; ops.pad through a field-of-deref: 1 *= 3 -> 3.
COMPOUND_STORE = (
    _STRUCTS
    + """\
fn g(pp: **Ops, b: *B)
    (**pp).n += 5
    (*(*b).ops).pad *= 3

pub fn main() -> i32
    var o: Ops = Ops { pad: 1, n: 6 }
    var p: *Ops = @o
    var b: B = B { tag: 9, ops: @o }
    g(@p, @b)
    return o.n * 10 + o.pad
"""
)

CASES = {
    "compound_store": (COMPOUND_STORE, 113),
    "deref_member_deref": (DEREF_MEMBER_DEREF, 4),
    "deref_auto_member": (DEREF_AUTO_MEMBER, 5),
    "double_deref": (DOUBLE_DEREF, 6),
    "deep_chain_store": (DEEP_CHAIN_STORE, 37),
    "double_deref_store": (DOUBLE_DEREF_STORE, 11),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_nested_deref_member(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want
