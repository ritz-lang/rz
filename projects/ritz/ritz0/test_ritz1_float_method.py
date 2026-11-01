"""AGAST #1370: ritz1 lowers float methods (ceil/floor/round/abs) on f32/f64.

THE DEFECT

emit_expr_method (ritz1/src/emitter_expr_call.ritz) resolved a receiver type
only for struct-typed receivers (and, since #1506, integer BitOps). `x.ceil()`
on an `f32` left type_name null and failed with "cannot determine receiver
type for method call". Before #1369 that same branch silently produced 0.

ritz0 (_try_emit_float_intrinsic) lowers the set inline, never as a libcall
(ritz links no libc, AGAST #1321):

    abs   -> llvm.fabs.{f32,f64}
    floor -> t = sitofp(fptosi(x)); t > x ? t - 1 : t
    ceil  -> t = sitofp(fptosi(x)); t < x ? t + 1 : t
    round -> trunc(x < 0 ? x - 0.5 : x + 0.5)     (half away from zero)

The result has the receiver's width, so get_expr_type must report it too:
`let y = (x + 0.25).ceil()` infers f32, and `x.floor() + 0.5` is f32 math.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# The ticket's repro: an identifier receiver.
REPRO = """\
fn main() -> i32
    let x: f32 = 1.25
    let y: f32 = x.ceil()
    return y as i32
"""

# test_issue_float_coercion's third [[test]]: an expression receiver whose
# result type is INFERRED from the method call.
EXPR_RECEIVER = """\
fn id_f32(v: f32) -> f32
    v

fn main() -> i32
    let x = id_f32(1)
    let y = (x + (0.25 as f32)).ceil()
    let yi = y as i32
    if yi != 2
        return 1
    return 42
"""

# Every method on both widths, positive and negative, including the
# boundaries where trunc and floor/ceil disagree and round's tie rule.
ALL_METHODS = """\
pub fn main() -> i32
    let a: f64 = 0.0 - 2.5
    let b: f64 = 2.5
    let c: f32 = 0.0 - 1.75
    let d: f32 = 3.0
    if (a.floor() as i32) != (0 - 3)
        return 1
    if (a.ceil() as i32) != (0 - 2)
        return 2
    if (a.round() as i32) != (0 - 3)
        return 3
    if (b.round() as i32) != 3
        return 4
    if (b.floor() as i32) != 2
        return 5
    if (b.ceil() as i32) != 3
        return 6
    if (c.floor() as i32) != (0 - 2)
        return 7
    if (c.ceil() as i32) != (0 - 1)
        return 8
    if (c.round() as i32) != (0 - 2)
        return 9
    if (d.ceil() as i32) != 3
        return 10
    if (d.floor() as i32) != 3
        return 11
    if (a.abs() * 2.0) as i32 != 5
        return 12
    if (c.abs() * 4.0) as i32 != 7
        return 13
    return 42
"""

# The result keeps the receiver's width through binops, params, returns and
# chained methods; a struct-field receiver.
RESULT_TYPE = """\
struct P
    x: f32
    y: f64

fn half_f32(v: f32) -> f32
    v * 0.5

fn fl(v: f64) -> f64
    return v.floor()

pub fn main() -> i32
    let x: f32 = 2.25
    # Annotated: an untyped let from a float BINARY is #2047, not this.
    let s: f32 = x.floor() + 0.5
    if (s * 2.0) as i32 != 5
        return 1
    if (half_f32(x.ceil()) * 2.0) as i32 != 3
        return 2
    if fl(7.9) as i32 != 7
        return 3
    let n: f32 = 0.0 - 1.5
    if (n.abs().ceil()) as i32 != 2
        return 4
    # A struct literal: `p.x = 4.5` field stores are #2048, not this.
    let p = P { x: 4.5, y: 0.0 - 4.5 }
    if p.x.round() as i32 != 5
        return 5
    if p.y.round() as i32 != (0 - 5)
        return 6
    let z = n.round()
    let zi = z as i32
    if zi != (0 - 2)
        return 7
    return 42
"""

CASES = {
    "repro": (REPRO, 2),
    "expr_receiver": (EXPR_RECEIVER, 42),
    "all_methods": (ALL_METHODS, 42),
    "result_type": (RESULT_TYPE, 42),
}

# A call receiver must be evaluated exactly once. Hand-derived expectation:
# ritz0 may evaluate a call receiver twice (cf. #1563 for BitOps), so it is
# not used as the oracle here.
CALL_RECEIVER = """\
var g_calls: i32 = 0

fn mk() -> f64
    g_calls = g_calls + 1
    0.0 - 3.25

pub fn main() -> i32
    let r: f64 = mk().floor()
    if r as i32 != (0 - 4)
        return 1
    if g_calls != 1
        return 2
    return 42
"""

RITZ1_ONLY = {
    "call_receiver": (CALL_RECEIVER, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_float_method(ritz1_bin, tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_ONLY))
def test_ritz1_float_method_ritz1_only(ritz1_bin, tmp_path, name):
    program, want = RITZ1_ONLY[name]
    assert _run("ritz1", tmp_path, name, program) == want


# IR shape: floor/ceil/round are inline (no libm call: ritz links no libc,
# #1321); abs is llvm.fabs at the receiver's width, declared once each.
IR_SHAPE = """\
pub fn main() -> i32
    let a: f32 = 1.5
    let b: f64 = 2.5
    let c: f32 = a.abs() + a.abs()
    let d: f64 = b.abs()
    let e: f64 = b.floor() + b.ceil() + b.round()
    return (c as i32) + (d as i32) + (e as i32)
"""


@pytest.mark.integration
def test_ritz1_float_method_ir_shape(ritz1_bin, tmp_path):
    import os
    import subprocess

    from test_ritz1_builtin_struct_shadow import RITZ1_BIN, RITZ_ROOT

    src = tmp_path / "ir_shape.ritz"
    src.write_text(IR_SHAPE)
    ll = tmp_path / "ir_shape.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0, comp.stderr
    ir = ll.read_text()
    assert ir.count("declare float @llvm.fabs.f32(float)") == 1
    assert ir.count("declare double @llvm.fabs.f64(double)") == 1
    assert "call float @llvm.fabs.f32(float " in ir
    assert "call double @llvm.fabs.f64(double " in ir
    for libcall in ("floor", "ceil", "round", "llvm.trunc"):
        assert f"@{libcall}" not in ir
        assert f"@llvm.{libcall}" not in ir
    assert "fptosi double" in ir and "sitofp i64" in ir
    assert _run("ritz1", tmp_path, "ir_shape_run", IR_SHAPE) == 3 + 2 + 8
