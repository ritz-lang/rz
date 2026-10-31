"""AGAST #1973: ritz1 indexes through a `*f32` / `*f64` pointer at the
element's real width.

THE DEFECT

`p[i]` on a `*f32` / `*f64` fell to emit_expr_index's byte path
(`getelementptr i8` + `load i8` -- a silently wrong value) and `p[i] = v`
fell to emit_index_assign_ptr_store's i64 path (`getelementptr i64` +
`store i64 %float` -- clang rejects it).

The runtime behaviour is checked against ritz0 in
ritz0/test/test_issue_ptr_float_index.ritz.  This file pins what that
matrix test cannot see:

  * the IR itself: every GEP, load and store through the pointer is
    `float` / `double`, and an f64 value into an f32 slot is fptrunc'd;
  * a callee writing through `@loc[i]` of a local float array.  ritz0
    rejects `@loc[i]` on a float array ("Cannot index type: [3 x float]",
    #1972), so ritz1 is checked against a fixed exit code.
"""

import re
import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run

SHAPE = """\
fn st(p: *{elem}, v: {elem}) -> void
    p[1] = v

fn ld(p: *{elem}) -> {elem}
    p[1]

fn lit(p: *{elem}) -> void
    p[0] = 2.5

pub fn main() -> i32
    return 0
"""


def _fn_ir(ll_text, name):
    body = ll_text.split(f" @{name}(", 1)[1]
    return body.split("\n}", 1)[0]


@pytest.mark.integration
@pytest.mark.parametrize("elem,llvm", [("f32", "float"), ("f64", "double")])
def test_ptr_float_index_ir_uses_float_elements(ritz1_bin, tmp_path, elem, llvm):
    src = tmp_path / f"pfi_{elem}.ritz"
    src.write_text(SHAPE.format(elem=elem))
    ll = tmp_path / f"pfi_{elem}.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    text = ll.read_text()
    st, ld, lit = (_fn_ir(text, n) for n in ("st", "ld", "lit"))
    for body in (st, ld, lit):
        assert f"getelementptr {llvm}, ptr" in body, body
        assert "getelementptr i8" not in body and "getelementptr i64" not in body, body
    # The value stored into the GEP'd element is a float / double.
    for body in (st, lit):
        gep = re.search(r"(%\.\d+) = getelementptr", body).group(1)
        stores = [ln for ln in body.splitlines() if ln.endswith(f"ptr {gep}")]
        assert len(stores) == 1 and stores[0].lstrip().startswith(f"store {llvm} "), (
            body
        )
    assert f"load {llvm}, ptr" in ld and "load i8" not in ld, ld
    assert f"ret {llvm} " in ld, ld
    assert f"store {llvm} " in lit, lit
    if elem == "f32":
        # The f64 literal is narrowed for an f32 slot.
        assert "fptrunc double" in lit, lit
    proc = subprocess.run(
        ["clang", "-c", str(ll), "-o", str(tmp_path / "o.o")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]


# A callee writing / reading through `@loc[i]`: element 1 of `@a[1]` is
# a[2], and a[1] is left alone.
ADDR_OF = """\
fn put32(p: *f32, i: i64, v: f32) -> void
    p[i] = v

fn get32(p: *f32, i: i64) -> f32
    p[i]

fn put64(p: *f64, i: i64, v: f64) -> void
    p[i] = v

fn get64(p: *f64, i: i64) -> f64
    p[i]

pub fn main() -> i32
    var a: [4]f32 = [1.0, 2.0, 3.0, 4.0]
    var d: [3]f64 = [1.0, 2.0, 3.0]
    let nine: f32 = 9.0
    let two: f32 = 2.0
    let four: f32 = 4.0
    put32(@a[1], 1, nine)
    if a[2] != nine
        return 1
    if a[1] != two
        return 2
    if get32(@a[1], 2) != four
        return 3
    put64(@d[1], 1, -0.5)
    if d[2] != -0.5
        return 4
    if d[1] != 2.0
        return 5
    if get64(@d[0], 1) != 2.0
        return 6
    return 42
"""


@pytest.mark.integration
def test_ptr_float_index_through_addr_of_element(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "addr_of", ADDR_OF) == 42


# A range `p[a..b]` over a `*f32` / `*f64` is an element pointer, not a
# float: get_expr_type must not call it F32 / F64, or the `as *u32` cast
# lowers as a float->int conversion of a pointer.  `lo` is 0 because a bare
# pointer's range GEP strides by i8 whatever the pointee (AGAST #1974).
RANGE = """\
pub fn main() -> i32
    var a: [4]f32 = [1.0, 2.0, 3.0, 4.0]
    var d: [2]f64 = [1.0, -0.5]
    let p: *f32 = @a as *f32
    let q: *u32 = p[0..2] as *u32
    if q[1] != 0x40000000
        return 1
    let pd: *f64 = @d as *f64
    let r: *u64 = pd[0..2] as *u64
    if r[1] != 0xBFE0000000000000
        return 2
    return 42
"""


@pytest.mark.integration
def test_ptr_float_range_is_a_pointer(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "range", RANGE) == 42
