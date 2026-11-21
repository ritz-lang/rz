"""AGAST #3931: an untyped `let` initialised by a comparison of floats is a
bool, on every compiler.

THE DEFECT

ritz1's get_expr_type (ritz1/src/emitter_core.ritz) answered every binary
that is not arithmetic with its LEFT operand's type, so `a == b` on two f32s
was "an f32".  emit_var_decl's #2047 inference then gave `let x = a == b` a
`float` slot and clang refused `store float %.11` (`%.11` the comparison's
i64 bool).  LANGUAGE_SPEC.md's float-comparison example tripped it
(check-doc-examples under ritz1, #3928).  Sema's typer (sema_expr_ty) already
said TYPE_BOOL; the emitter's did not.

THE FIX

get_expr_type answers a comparison (`== != < <= > >=`) with the emitter's
bool slot, TYPE_I64 (#1646), whatever its operands, as ritz0 types it bool.

Every row runs on ritz0, ritz1 and ritz1_selfhosted.  Each program reads the
inferred bool both ways (a true and a false comparison), so a slot that
merely links but holds the wrong value still fails.
"""

import subprocess

import pytest

from test_ref_into_value import COMPILERS, _ids, _run
from test_ritz1_builtin_struct_shadow import RITZ1_BIN

# The ticket's three repros, each alone enough to make ritz1 emit invalid IR.
REPROS = {
    "mixed_cast_to_f32": """\
pub fn main() -> i32
    let a: f32 = 0.1
    let b: f64 = 0.1
    let in_f32 = a == b as f32
    if in_f32
        return 42
    return 1
""",
    "mixed_cast_to_f64": """\
pub fn main() -> i32
    let a: f32 = 0.5
    let b: f64 = 0.5
    let in_f64 = a as f64 == b
    if in_f64
        return 42
    return 1
""",
    "f32_vs_literal": """\
pub fn main() -> i32
    let y: f32 = 0.5
    let lit = y == 0.5
    if lit
        return 42
    return 1
""",
}

# `op`: (operands that make it true, operands that make it false).
OPS = {
    "eq": ("==", ("1.5", "1.5"), ("1.5", "2.5")),
    "ne": ("!=", ("1.5", "2.5"), ("1.5", "1.5")),
    "lt": ("<", ("1.5", "2.5"), ("2.5", "1.5")),
    "le": ("<=", ("1.5", "1.5"), ("2.5", "1.5")),
    "gt": (">", ("2.5", "1.5"), ("1.5", "2.5")),
    "ge": (">=", ("1.5", "1.5"), ("1.5", "2.5")),
}

FLOATS = ["f32", "f64"]


def _op_program(op, ty):
    sym, (ta, tb), (fa, fb) = OPS[op]
    return f"""\
pub fn main() -> i32
    let a: {ty} = {ta}
    let b: {ty} = {tb}
    let c: {ty} = {fa}
    let d: {ty} = {fb}
    let yes = a {sym} b
    let no = c {sym} d
    if not yes
        return 1
    if no
        return 2
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", _ids(REPROS))
def test_ticket_repro_let_is_bool(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, REPROS[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", FLOATS)
@pytest.mark.parametrize("op", _ids(OPS))
def test_every_comparison_let_is_bool(tmp_path, compiler, op, ty):
    assert _run(compiler, tmp_path, f"{op}_{ty}", _op_program(op, ty)) == 42


@pytest.mark.integration
@pytest.mark.parametrize("ty", FLOATS)
@pytest.mark.parametrize("op", _ids(OPS))
def test_ritz1_comparison_let_slot_is_the_bool_slot(ritz1_bin, tmp_path, op, ty):
    """The inferred slot is ritz1's bool slot (i64, #1646), never the
    operands' float / double."""
    src = tmp_path / f"{op}_{ty}.ritz"
    src.write_text(_op_program(op, ty))
    ll = tmp_path / f"{op}_{ty}.ll"
    proc = subprocess.run([str(RITZ1_BIN), str(src), "-o", str(ll)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]
    body = ll.read_text().split("@main(", 1)[1].split("\n}", 1)[0]
    allocas = [ln.split("= alloca ", 1)[1].strip() for ln in body.splitlines() if "= alloca " in ln]
    # Four annotated float operands, then `yes` and `no`.
    assert len(allocas) == 6, body
    assert allocas[-2:] == ["i64", "i64"], body
