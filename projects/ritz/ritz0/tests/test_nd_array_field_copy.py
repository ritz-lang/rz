"""AGAST #3299: `let g = h.m` of a multi-dimensional array field
(`m: [2][3]i32`) copies the `[2][3]i32`, and `g[i][j]` indexes the copy.

THE DEFECT

ritz0: a `let` binds the copy as an SSA `[2 x [3 x i32]]` value.  `g[1][2]`
takes the address of the row `g[1]` (_emit_lvalue_addr's Index branch), which
only knew alloca'd and global arrays, so it raised "Cannot index type:
[2 x [3 x i32]]".  The annotated `let g: [2][3]i32 = h.m` crashed the same way.

ritz1: emit_var_decl_at refused every initialiser on an N-d slot (#1509),
so `let g = h.m` (typed N-d by #3017's slot inference), the annotated form and
#2169's `var b = a` of an N-d local all failed closed with "an initializer
on a multi-dimensional array is not supported in ritz1".

THE FIX

ritz0 spills a let-bound array value to a slot before indexing a row of it,
as _emit_index_core already does for a 1-D read.  ritz1 copies a whole N-d
array place (a field, a local, `*p`) into the slot; a literal or fill
initialiser on an N-d slot still fails closed.

Each case is a copy, never a view: the source is written after the binding
and the binding must not see it.  ritz0 is the oracle.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

H = """\
struct H
    k: i64
    m: [2][3]i32

fn fill(h: *H)
    h.k = 9
    h.m[0][1] = 3
    h.m[1][2] = 7

"""

CASES = {
    # The ticket's repro, then a write to the field the copy must not see.
    "untyped_let": (H + """\
pub fn main() -> i32
    var h: H
    fill(@h)
    let g = h.m
    h.m[1][2] = 1
    return g[1][2] * 10 + g[0][1]
""", 73),
    # The annotated form the untyped one should match.
    "annotated_let": (H + """\
pub fn main() -> i32
    var h: H
    fill(@h)
    let g: [2][3]i32 = h.m
    h.m[0][1] = 1
    return g[1][2] * 10 + g[0][1]
""", 73),
    # A `var` copy: writing it leaves the field alone, and the other way round.
    "var_copy_both_ways": (H + """\
pub fn main() -> i32
    var h: H
    fill(@h)
    var g = h.m
    g[1][2] = 5
    h.m[0][1] = 1
    return g[1][2] * 10 + g[0][1] + h.m[1][2] * 20
""", 193),
    # Through a pointer root (`p.m`, `p: *H`).
    "pointer_root": (H + """\
fn get(p: *H) -> i32
    let g = p.m
    p.m[1][2] = 1
    return g[1][2] * 10 + g[0][1]

pub fn main() -> i32
    var h: H
    fill(@h)
    return get(@h)
""", 73),
    # Three dimensions, a dynamic index on every axis.
    "three_d": ("""\
struct T
    m: [2][3][4]i32

pub fn main() -> i32
    var t: T
    t.m[1][2][3] = 6
    t.m[0][1][2] = 4
    let g = t.m
    t.m[1][2][3] = 1
    var i = 1
    var j = 2
    var k = 3
    return g[i][j][k] * 10 + g[i - 1][j - 1][k - 1]
""", 64),
    # AGAST #2169: `var b = a` of an N-d local.
    "local_var_copy": ("""\
pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 7
    a[0][1] = 3
    var b = a
    a[1][2] = 1
    return b[1][2] * 10 + b[0][1]
""", 73),
    # An annotated N-D local from a local (was test_ritz1_whole_array.py's
    # strict-xfail `aoa_whole`, #2099).
    "annotated_local_copy": ("""\
pub fn main() -> i32
    var m: [2][4]i32
    m[1][3] = 3
    var n: [2][4]i32 = m
    m[1][3] = 1
    return n[1][3]
""", 3),
    # A lent `a:& [2][3]i32` param: the copy reads through the borrow.
    "lent_param_copy": ("""\
fn f(a:& [2][3]i32) -> i32
    var b = a
    return b[1][2] - 2

pub fn main() -> i32
    var a: [2][3]i32
    a[1][2] = 5
    return f(@&a)
""", 3),
    # A global N-D source, as `var b = G`.
    "global_var_copy": ("""\
var G: [2][3]i32

pub fn main() -> i32
    G[1][2] = 7
    G[0][1] = 3
    var b = G
    G[1][2] = 1
    return b[1][2] * 10 + b[0][1]
""", 73),
    # 1 KB: past SRET_MIN_BYTES, so ritz1 copies it pointer-to-pointer.
    "large_field": ("""\
struct Big
    m: [16][16]i32

pub fn main() -> i32
    var h: Big
    h.m[15][14] = 7
    h.m[3][1] = 3
    let g = h.m
    h.m[15][14] = 1
    return g[15][14] * 10 + g[3][1]
""", 73),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_nd_array_field_copy(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_nd_array_field_copy(ritz1_bin, tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_nd_array_shape_mismatch_rejected(ritz1_bin, tmp_path, compiler):
    """A `[2][3]i32` field never initialises a `[3][2]i32` slot."""
    program = H + """\
pub fn main() -> i32
    var h: H
    let g: [3][2]i32 = h.m
    return g[1][1]
"""
    with pytest.raises(AssertionError, match="failed to compile"):
        _run(compiler, tmp_path, "shape_mismatch", program)
