"""AGAST #2047: an untyped `let` with a float-valued initializer gets a
float / double slot in ritz1.

THE DEFECT

emit_var_decl's untyped-init inference (ritz1/src/emitter_stmt.ritz) narrowed
the parser-default TYPE_I64 slot only for calls, methods, `match` and `if`.
`let s = x + 0.5` with `x: f32` allocated `alloca i64` and emitted
`store i64 %.8, ptr %.4` with `%.8` a float, which clang rejects.

THE FIX

When get_expr_type(init) is TYPE_F32 / TYPE_F64 and no earlier arm typed the
slot, the slot takes that type.

One program per initializer shape, so a regression names the shape that
broke.  ritz0 is the oracle; ritz0/test/test_issue_untyped_float_let.ritz
runs the same shapes through the regression matrix.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

CASES = {
    # The ticket's repro: exit 5 under ritz0.
    "binary_f32": (
        """\
pub fn main() -> i32
    let x: f32 = 2.25
    let s = x + 0.5
    return (s * 2.0) as i32
""",
        5,
    ),
    "binary_f64": (
        """\
pub fn main() -> i32
    let x: f64 = 2.5
    let s = x * 4.0 - 1.0
    return s as i32
""",
        9,
    ),
    "cast_f32": (
        """\
pub fn main() -> i32
    let n: i32 = 7
    let f = n as f32
    return (f * 1.5) as i32
""",
        10,
    ),
    "cast_f64": (
        """\
pub fn main() -> i32
    let n: i64 = 6
    let f = n as f64
    return (f * 1.5) as i32
""",
        9,
    ),
    "field_f32": (
        """\
struct P
    a: f32
    b: f64

pub fn main() -> i32
    let p = P { a: 2.75, b: 0.0 }
    let a = p.a
    return (a * 4.0) as i32
""",
        11,
    ),
    "field_f64": (
        """\
struct P
    a: f32
    b: f64

pub fn main() -> i32
    let p = P { a: 0.0, b: 3.25 }
    let b = p.b
    return (b * 4.0) as i32
""",
        13,
    ),
    "neg_f32": (
        """\
pub fn main() -> i32
    let x: f32 = 1.5
    let n = -x
    return (n * -2.0) as i32
""",
        3,
    ),
    "neg_f64": (
        """\
pub fn main() -> i32
    let x: f64 = 2.25
    let n = -x
    return (n * -2.0) as i32
""",
        4,
    ),
    # #1370's float methods in arithmetic.
    "floor_plus_f32": (
        """\
pub fn main() -> i32
    let x: f32 = 3.75
    let r = x.floor() + 0.5
    return (r * 2.0) as i32
""",
        7,
    ),
    "floor_plus_f64": (
        """\
pub fn main() -> i32
    let x: f64 = 4.25
    let r = x.floor() + 0.5
    return (r * 2.0) as i32
""",
        9,
    ),
}

# Integer initializers stay i64 slots: the inference must not widen them.
INT_UNCHANGED = """\
pub fn main() -> i32
    let x: i32 = 40
    let s = x + 2
    let c = 3.9 as i32
    return (s as i32) + c - 3
"""


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_untyped_float_let(ritz1_bin, tmp_path, name):
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_untyped_int_let_unchanged(ritz1_bin, tmp_path, compiler):
    assert _run(compiler, tmp_path, "int_unchanged", INT_UNCHANGED) == 42


@pytest.mark.integration
@pytest.mark.parametrize(
    "name,llvm",
    [("binary_f32", "float"), ("binary_f64", "double"), ("cast_f32", "float"), ("neg_f64", "double")],
)
def test_ritz1_untyped_float_let_slot_type(ritz1_bin, tmp_path, name, llvm):
    import subprocess

    src = tmp_path / f"{name}.ritz"
    src.write_text(CASES[name][0])
    ll = tmp_path / f"{name}.ll"
    proc = subprocess.run([str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]
    body = ll.read_text().split("@main(", 1)[1].split("\n}", 1)[0]
    # Two slots: the annotated source and the untyped `let`.  The `let`'s
    # (the last) is at the float width -- never the i64 default.
    allocas = [ln.split("= alloca ", 1)[1].strip() for ln in body.splitlines() if "= alloca " in ln]
    assert len(allocas) == 2 and allocas[-1] == llvm, body
    assert "i64" not in allocas, body
