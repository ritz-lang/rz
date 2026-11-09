"""AGAST #2021: ritz1 widens a signed i8 local / param with sext.

THE DEFECT

emit_expr_ident's local arm (emitter_expr_access.ritz) grouped TYPE_I8 with
TYPE_U8 and reloaded both with `zext i8 ... to i64`, while every i8 element
load (`p[i]` on a `*i8`, `a[i]` on a `[N]i8`) and an i8 global reload used
`sext`.  So `let x: i8 = -3` widened to 0xFD and `p[2] != x` was true: the
ticket repro returned 1 instead of 42.  Params are spilled to an alloca and
reloaded through the same arm, so they were wrong too.  `*q` on a `*i8`
(emit_expr_unary's OP_DEREF arm) had the same i8/u8 grouping and is fixed
alongside.

Each program is checked against a fixed exit code under ritz0 (the oracle)
and ritz1: a mismatch exits with the number of the first failing check.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# The ticket repro, verbatim.
REPRO = """\
pub fn main() -> i32
    var a: [5]i8 = [1, 2, -3, 4, 5]
    let p: *i8 = @a as *i8
    let x0: i8 = -3
    if p[2] != x0
        return 1
    return 42
"""

# An i8 local, param and global, each holding a negative value, compared
# with `*i8` and `[N]i8` elements both ways round, against a negative
# literal, ordered against zero, and cast to i64.
MATRIX = """\
var g: i8 = 0
var ga: [3]i8

fn param_vs_ptr(p: *i8, x: i8) -> i32
    if p[2] != x
        return 1
    if x != p[2]
        return 2
    if x >= 0
        return 3
    if x as i64 != -3
        return 4
    return 0

fn param_vs_ptr_neg128(p: *i8, x: i8) -> i32
    if p[0] != x
        return 1
    return 0

pub fn main() -> i32
    var a: [5]i8 = [1, 2, -3, 4, -128]
    let p: *i8 = @a as *i8
    let x: i8 = -3
    var y: i8 = 0
    y = -128

    # local vs *i8 and [N]i8 elements
    if p[2] != x
        return 10
    if x != p[2]
        return 11
    if a[2] != x
        return 12
    if x != a[2]
        return 13
    if p[4] != y
        return 14
    if a[4] != y
        return 15
    # local vs literal / ordering / cast
    if x != -3
        return 16
    if x >= 0
        return 17
    if not (x < 0)
        return 18
    if x as i64 != -3
        return 19
    if y as i64 != -128
        return 20
    if x + 1 != -2
        return 21

    # param
    if param_vs_ptr(p, x) != 0
        return 30
    if param_vs_ptr(@a[0] as *i8, -3) != 0
        return 31
    if param_vs_ptr_neg128(p + 4, y) != 0
        return 32

    # global scalar and global [N]i8
    g = -3
    ga[1] = -3
    if p[2] != g
        return 40
    if g != a[2]
        return 41
    if ga[1] != x
        return 42
    if x != ga[1]
        return 43
    if g as i64 != -3
        return 44

    # unsigned control: u8 must keep zero-extending
    let u: u8 = 253
    if u as i64 != 253
        return 50
    if u < 128
        return 51
    return 42
"""

# `*q` on a `*i8` (local, param, global pointer) widened with zext too
# (emit_expr_unary's OP_DEREF arm, emitter_expr_arith.ritz).  The literal
# right-hand side keeps this independent of the local-reload fix.
DEREF = """\
var g: *i8 = null

fn first(q: *i8) -> i8
    *q

pub fn main() -> i32
    var a: [5]i8 = [1, 2, -3, 4, -128]
    let p: *i8 = @a as *i8
    if *(p + 2) != -3
        return 1
    if *(p + 4) as i64 != -128
        return 2
    if *(p + 2) >= 0
        return 3
    if first(p + 2) != -3
        return 4
    g = p
    if *(g + 2) != -3
        return 5
    # unsigned control: *u8 keeps zero-extending
    var b: [1]u8 = [253]
    let bp: *u8 = @b as *u8
    if *bp as i64 != 253
        return 7
    return 42
"""

COMPILERS = ["ritz0", "ritz1"]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_i8_ptr_deref(compiler, tmp_path):
    assert _run(compiler, tmp_path, "i8_deref", DEREF) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_i8_local_repro(compiler, tmp_path):
    assert _run(compiler, tmp_path, "i8_repro", REPRO) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_i8_local_param_global_matrix(compiler, tmp_path):
    assert _run(compiler, tmp_path, "i8_matrix", MATRIX) == 42
