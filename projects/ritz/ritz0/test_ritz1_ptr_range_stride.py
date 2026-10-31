"""AGAST #1974: ritz1's range index `p[a..b]` on a bare `*T` pointer GEPs
by the pointee's element type, not by `i8`.

THE DEFECT

emit_expr_index's #110 range lowering left `rng_elem_ty` at its `i8`
default for a bare pointer base, so `p[2..4]` on a `*u32` was
`getelementptr i8, ptr %p, i64 2`: a pointer to byte 2, not element 2.

ritz0 rejects slicing a bare pointer, so these programs are checked
against a fixed exit code (as test_ritz1_ptr_float_index.py does), and
the IR is checked for the element-typed GEP.
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run

# Each case: element type, LLVM spelling, array literal, expected p[2..4][0]
# and p[2..4][1] (read back through the slice, then compared).
CASES = [
    ("u8", "i8", "[1, 2, 3, 4, 5]", "3", "4"),
    ("i8", "i8", "[1, 2, 3, 4, 5]", "3", "4"),
    ("u16", "i16", "[1, 2, 300, 400, 5]", "300", "400"),
    ("i16", "i16", "[1, 2, -300, 400, 5]", "-300", "400"),
    ("u32", "i32", "[1, 2, 70000, 80000, 5]", "70000", "80000"),
    ("i32", "i32", "[1, 2, -70000, 80000, 5]", "-70000", "80000"),
    ("u64", "i64", "[1, 2, 0x100000000, 0x200000000, 5]", "0x100000000", "0x200000000"),
    ("i64", "i64", "[1, 2, -5000000000, 6000000000, 5]", "-5000000000", "6000000000"),
    ("f32", "float", "[1.0, 2.0, 3.5, -4.25, 5.0]", "3.5", "-4.25"),
    ("f64", "double", "[1.0, 2.0, 3.5, -4.25, 5.0]", "3.5", "-4.25"),
]

# A local `*T`, a `*T` parameter and a global `*T`, each sliced at lo=2.
PROG = """\
var g: *{elem} = null

fn second(p: *{elem}) -> {elem}
    let s: *{elem} = p[2..4]
    s[1]

pub fn main() -> i32
    var a: [5]{elem} = {lit}
    let p: *{elem} = @a as *{elem}
    let s: *{elem} = p[2..4]
    let x0: {elem} = {v0}
    let x1: {elem} = {v1}
    if s[0] != x0
        return 1
    if s[1] != x1
        return 2
    if second(p) != x1
        return 3
    g = p
    let t: *{elem} = g[2..4]
    if t[0] != x0
        return 4
    if t[1] != x1
        return 5
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("elem,llvm,lit,v0,v1", CASES, ids=[c[0] for c in CASES])
def test_ptr_range_strides_by_element(ritz1_bin, tmp_path, elem, llvm, lit, v0, v1):
    src = PROG.format(elem=elem, lit=lit, v0=v0, v1=v1)
    assert _run("ritz1", tmp_path, f"prs_{elem}", src) == 42


@pytest.mark.integration
@pytest.mark.parametrize("elem,llvm,lit,v0,v1", CASES, ids=[c[0] for c in CASES])
def test_ptr_range_ir_geps_element_type(ritz1_bin, tmp_path, elem, llvm, lit, v0, v1):
    src = tmp_path / f"prs_ir_{elem}.ritz"
    src.write_text(
        f"fn sl(p: *{elem}) -> *{elem}\n    p[2..4]\n\n"
        "pub fn main() -> i32\n    return 0\n"
    )
    ll = tmp_path / f"prs_ir_{elem}.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    body = ll.read_text().split(" @sl(", 1)[1].split("\n}", 1)[0]
    assert f"getelementptr {llvm}, ptr" in body, body
    if llvm != "i8":
        assert "getelementptr i8" not in body, body


# The ticket's repro: `p[2..4]` on a `*u32` points at element 2.
REPRO = """\
pub fn main() -> i32
    var a: [4]u32 = [10, 20, 30, 40]
    let p: *u32 = @a as *u32
    let s: *u32 = p[2..4]
    if s[0] != 30
        return 1
    if s[1] != 40
        return 2
    return 42
"""


@pytest.mark.integration
def test_ptr_range_ticket_repro(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "repro", REPRO) == 42


# A `**T` strides by pointer size: `pp[1..3][0]` is pp[1].
PTR_PTR = """\
fn tail(pp: **u8) -> **u8
    pp[1..3]

pub fn main() -> i32
    var a: [3]u8 = [7, 8, 9]
    var ptrs: [3]*u8 = [@a[0], @a[1], @a[2]]
    let pp: **u8 = @ptrs as **u8
    let s: **u8 = pp[1..3]
    let e0: *u8 = s[0]
    if *e0 != 8
        return 1
    let e1: *u8 = s[1]
    if *e1 != 9
        return 2
    let t: **u8 = tail(pp)
    let e2: *u8 = t[1]
    if *e2 != 9
        return 3
    return 42
"""


@pytest.mark.integration
def test_ptr_ptr_range_strides_by_pointer(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "ptr_ptr", PTR_PTR) == 42
