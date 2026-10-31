"""AGAST #1966: ritz1 lays out a LOCAL `[N]f32` / `[N]f64` array as
`[N x float]` / `[N x double]`.

THE DEFECT

emit_var_decl allocated `let loc: [3]f32 = [1.0, 2.0, 3.5]` as
`alloca [3 x i64]` and the literal / fill writers stored each element as
`store i64 %double` -- invalid IR.  Struct-field float arrays already used
`float` / `double` elements (#1935); locals kept an i64 slot per element.

The runtime behaviour (literal, fill, `loc[i]` loads and stores, for-in) is
checked against ritz0 in ritz0/test/test_issue_local_float_array.ritz.  This
file pins what that matrix test cannot see:

  * the alloca itself.  With opaque pointers, `float` GEPs over a larger
    `[N x i64]` alloca still run correctly, so only the IR text shows that
    the alloca and every GEP over it agree on the element type;
  * `@loc[i]` into a float array.  ritz0 rejects it ("Cannot index type:
    [3 x float]", #1972), so ritz1 is checked against a fixed exit code;
  * `loc[a..b]`, likewise ritz1-only.

Callees read and write through `*u32` / `*u64`: indexing a `*f32` / `*f64`
pointer is broken in ritz1 (#1973).
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run

# The callee only receives the pointer: indexing through a `*f32` / `*f64`
# is #1973.
SHAPE = """\
fn take(p: *{elem}) -> void
    return

pub fn main() -> i32
    var a: [4]{elem} = [1.0, -2.0, 3.0, 4.0]
    var b: [4]{elem} = [0.5; 4]
    let one: {elem} = 1.0
    a[3] = 2.5
    b[0] = a[1]
    take(@a[1])
    if a[1] != one
        return 1
    return 0
"""


@pytest.mark.integration
@pytest.mark.parametrize("elem,llvm", [("f32", "float"), ("f64", "double")])
def test_local_float_array_ir_uses_float_elements(ritz1_bin, tmp_path, elem, llvm):
    """The alloca, the literal / fill / index stores and every GEP over the
    local use `float` / `double`; no element is stored as i64."""
    src = tmp_path / f"arr_{elem}.ritz"
    src.write_text(SHAPE.format(elem=elem))
    ll = tmp_path / f"arr_{elem}.ll"
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    main_ir = ll.read_text().split("define i32 @main", 1)[1]
    assert main_ir.count(f"alloca [4 x {llvm}]") == 2, main_ir
    assert "alloca [4 x i64]" not in main_ir
    geps = [ln for ln in main_ir.splitlines() if "getelementptr [4 x" in ln]
    # 4 literal stores + 4 fill stores + a[3] = + b[0] = + a[1] (load)
    # + @a[1] + a[1] (load).
    assert len(geps) == 13, geps
    for g in geps:
        assert f"getelementptr [4 x {llvm}]" in g, g
    assert f"store {llvm} " in main_ir
    assert "store i64" not in main_ir
    if elem == "f32":
        # f64 literals are narrowed for an f32 element.
        assert "fptrunc double" in main_ir
    proc = subprocess.run(["clang", "-c", str(ll), "-o", str(tmp_path / "o.o")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]


# `@loc[i]` is the address of element i: a callee writing IEEE bits at
# offset 1 from `@a[1]` lands on a[2] and leaves a[1] alone.  The callees
# write through `*u32` / `*u64` because indexing a `*f32` / `*f64` is #1973.
ADDR_OF = """\
fn put32(p: *u32, i: i64, v: u32) -> void
    p[i] = v

fn put64(p: *u64, i: i64, v: u64) -> void
    p[i] = v

pub fn main() -> i32
    var a: [4]f32 = [1.0, 2.0, 3.0, 4.0]
    var d: [3]f64 = [1.0, 2.0, 3.0]
    let nine: f32 = 9.0
    let two: f32 = 2.0
    put32(@a[1] as *u32, 1, 0x41100000)
    if a[2] != nine
        return 1
    if a[1] != two
        return 2
    put64(@d[1] as *u64, 1, 0xBFE0000000000000)
    if d[2] != -0.5
        return 3
    if d[1] != 2.0
        return 4
    return 42
"""


@pytest.mark.integration
def test_local_float_array_addr_of_element(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "addr_of", ADDR_OF) == 42


# `loc[a..b]` is a pointer to element a (AGAST #110), GEP'd at the alloca's
# element type: with an i64 stride `a[2..4]` would point at a[4], past the
# end.  Also pins that get_expr_type does not call a range index an f32
# (the `as *u32` cast would then be an fptosi of a pointer).
SLICE = """\
pub fn main() -> i32
    var a: [4]f32 = [1.0, 2.0, 3.0, 4.0]
    var d: [3]f64 = [1.0, 2.0, -0.5]
    let q: *u32 = a[2..4] as *u32
    if q[0] != 0x40400000
        return 1
    if q[1] != 0x40800000
        return 2
    let r: *u64 = d[2..3] as *u64
    if r[0] != 0xBFE0000000000000
        return 3
    return 42
"""


@pytest.mark.integration
def test_local_float_array_range_slice(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "slice", SLICE) == 42
