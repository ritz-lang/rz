"""AGAST #2027 (+ #2067): a float-annotated let whose match / if arms mix types.

`let a: f64 = match o / None => 0 / Some(v) => v` crashed ritz0 with a raw
`AttributeError: '_Undefined' object has no attribute 'type'`. The match
emitters saw an integer arm next to a float arm, called the arms
irreconcilable, and returned `ir.Undefined`, which LetStmt then read `.type`
off. The if-expression form was worse: it merged at whichever arm was
"larger" by bit width, so `if c then 0 else 1.5` merged at i64 and truncated
1.5 to 1, with no error.

The rule is the one ritz0 already applies to the plain form. `let a: f64 = 0`
and `let a: f64 = <int expr>` convert the initialiser (sitofp), and
`let a: f32 = <f64>` converts it (fptrunc). A match or if that IS the
initialiser (directly, or as the tail of an arm / block) gets the same
conversion on each arm, so the arms merge at the annotation's float type.
This is what ritz1 does since #1946.

Arm shapes outside that rule are a located diagnostic, not a traceback:

* a pointer arm. ritz1 rejects it too ("match arm yields a non-numeric
  value"). The plain form `let a: f64 = <ptr>` is wrong in both compilers
  and is ticketed separately.
* a bool arm. The plain form converts in both compilers but disagrees on
  the value: ritz0 sitofp's i1 true to -1.0, ritz1 gives 1.0. Merging it
  would copy that bug into the match form, so it stays rejected until the
  plain-form rule is settled (separate ticket).

Every runnable program is run under ritz0 AND ritz1 and both must give the
same exit code.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

# --- the two ticket repros, verbatim -----------------------------------------

REPRO_2027 = """\
import ritzlib.option
fn f(o: Option<f64>) -> f64
    let a: f64 = match o
        None => 0
        Some(v) => v
    return a

fn main() -> i32
    return f(None) as i32
"""

REPRO_2067 = """\
import ritzlib.option

fn opt(o: Option<f64>) -> i32
    let b: f64 = match o
        None => 1
        Some(v) => v
    return b as i32

pub fn main() -> i32
    return opt(None) + 2
"""

# --- wider coverage; each returns 42 on success, a distinct code per check ---

# Both arm orders, and both arms taken: the integer arm must arrive as a
# float, and the float arm must not be truncated.
F64_BOTH_ARMS = """\
import ritzlib.option

fn f(o: Option<f64>) -> f64
    let a: f64 = match o
        None => 3
        Some(v) => v
    return a

fn g(o: Option<f64>) -> f64
    let a: f64 = match o
        Some(v) => v
        None => 5
    return a

fn main() -> i32
    if f(None) != 3.0
        return 1
    if f(Some(2.5)) != 2.5
        return 2
    if g(None) != 5.0
        return 3
    if g(Some(0.25)) != 0.25
        return 4
    return 42
"""

F32_ANNOTATION = """\
import ritzlib.option

fn f(o: Option<f32>) -> f32
    let a: f32 = match o
        None => 6
        Some(v) => v
    return a

fn main() -> i32
    let half: f32 = 0.5
    if f(None) != 6.0
        return 1
    if f(Some(half)) != 0.5
        return 2
    return 42
"""

# The #1357 note in test/test_diff_float_neg_payload.ritz: an f32 payload arm
# next to a `0.0` (f64) literal arm. Under an annotation the arms merge at it.
F32_ARM_NEXT_TO_FLOAT_LITERAL = """\
import ritzlib.option

fn as32(o: Option<f32>) -> f32
    let a: f32 = match o
        Some(v) => v
        None => 0.0
    return a

fn as64(o: Option<f32>) -> f64
    let a: f64 = match o
        Some(v) => v
        None => 0.0
    return a

fn main() -> i32
    let q: f32 = 1.25
    if as32(Some(q)) != 1.25
        return 1
    if as32(None) != 0.0
        return 2
    if as64(Some(q)) != 1.25
        return 3
    if as64(None) != 0.0
        return 4
    return 42
"""

# A non-literal integer arm: a local and a call result, of differing widths.
NON_LITERAL_INT_ARM = """\
import ritzlib.option

fn seven() -> i64
    return 7

fn f(o: Option<f64>, k: i32) -> f64
    let a: f64 = match o
        None => k
        Some(v) => v
    return a

fn g(o: Option<f64>) -> f64
    let a: f64 = match o
        Some(v) => v
        None => seven()
    return a

fn main() -> i32
    if f(None, -4) != -4.0
        return 1
    if f(Some(1.5), 9) != 1.5
        return 2
    if g(None) != 7.0
        return 3
    return 42
"""

# An integer scrutinee (the integer-match emitter, not the enum one).
INT_SCRUTINEE = """\
fn pick(k: i64) -> f64
    let a: f64 = match k
        1 => 1.5
        2 => 2
        _ => 4
    return a

fn main() -> i32
    if pick(1) != 1.5
        return 1
    if pick(2) != 2.0
        return 2
    if pick(9) != 4.0
        return 3
    return 42
"""

# The if-expression form, both arm orders, f64 and f32. `if c then 0 else 1.5`
# used to merge at i64 and silently truncate 1.5 to 1.
IF_EXPRESSION = """\
fn a64(n: i32) -> f64
    let a: f64 = if n > 2 then 0 else 1.5
    return a

fn b64(n: i32) -> f64
    let a: f64 = if n > 2 then 2.5 else n
    return a

fn a32(n: i32) -> f32
    let a: f32 = if n > 2 then 8 else 0.5
    return a

fn main() -> i32
    if a64(1) != 1.5
        return 1
    if a64(5) != 0.0
        return 2
    if b64(5) != 2.5
        return 3
    if b64(-3) != -3.0
        return 4
    if a32(1) != 0.5
        return 5
    if a32(3) != 8.0
        return 6
    return 42
"""

# `var` takes the same initialiser rule as `let`.
VAR_FORM = """\
import ritzlib.option

fn v(o: Option<f64>) -> f64
    var a: f64 = match o
        None => 4
        Some(x) => x
    return a

fn main() -> i32
    if v(None) != 4.0
        return 1
    if v(Some(0.5)) != 0.5
        return 2
    return 42
"""

# An if whose then-arm is a block ending in an integer local. ritz0 merged
# at i64 and truncated the 0.5 arm to 0.
IF_BLOCK_TAIL = """\
fn f(n: i32) -> f64
    let a: f64 = if n > 2
        let m = n * 2
        m
    else
        0.5
    return a

fn main() -> i32
    if f(3) != 6.0
        return 1
    if f(0) != 0.5
        return 2
    return 42
"""

# Nested value tails: an else-if chain and a match inside a match arm. The
# annotation reaches every tail of the initialiser in ritz0. ritz1 only
# annotates the outermost match/if and rejects these cleanly (#2092).
ELSE_IF_CHAIN = """\
fn f(n: i32) -> f64
    let a: f64 = if n > 5 then 1.5 else if n > 2 then 2 else 0.25
    return a

fn main() -> i32
    if f(9) != 1.5
        return 1
    if f(3) != 2.0
        return 2
    if f(0) != 0.25
        return 3
    return 42
"""

NESTED_MATCH = """\
import ritzlib.option

fn nested(o: Option<f64>, p: Option<f64>) -> f64
    let a: f64 = match o
        None => 1
        Some(x) => match p
            None => 2
            Some(y) => x + y
    return a

fn main() -> i32
    if nested(None, None) != 1.0
        return 3
    if nested(Some(1.0), None) != 2.0
        return 4
    if nested(Some(1.0), Some(0.5)) != 1.5
        return 5
    return 42
"""

NESTED_CASES = [
    pytest.param(ELSE_IF_CHAIN, 42, id="else-if-chain"),
    pytest.param(NESTED_MATCH, 42, id="nested-match"),
]

RUN_CASES = [
    pytest.param(REPRO_2027, 0, id="repro-2027"),
    pytest.param(REPRO_2067, 3, id="repro-2067"),
    pytest.param(F64_BOTH_ARMS, 42, id="f64-both-arms"),
    pytest.param(F32_ANNOTATION, 42, id="f32-annotation"),
    pytest.param(F32_ARM_NEXT_TO_FLOAT_LITERAL, 42, id="f32-arm-next-to-0.0"),
    pytest.param(NON_LITERAL_INT_ARM, 42, id="non-literal-int-arm"),
    pytest.param(INT_SCRUTINEE, 42, id="int-scrutinee"),
    pytest.param(IF_EXPRESSION, 42, id="if-expression"),
    pytest.param(VAR_FORM, 42, id="var-form"),
    pytest.param(IF_BLOCK_TAIL, 42, id="if-block-tail"),
]

# --- located diagnostics -----------------------------------------------------

POINTER_ARM = """\
import ritzlib.option

fn f(o: Option<f64>) -> i32
    let p: *u8 = c"x"
    let a: f64 = match o
        Some(v) => v
        None => p
    return 0

fn main() -> i32
    return f(None)
"""

BOOL_ARM = """\
import ritzlib.option

fn f(o: Option<f64>) -> i32
    let t: bool = true
    let a: f64 = match o
        None => t
        Some(v) => v
    return 0

fn main() -> i32
    return f(None)
"""


def _ritz1_run(ritz1_bin: Path, tmp_path: Path, program: str):
    """Compile with ritz1, link, run. Returns (rc or None, diagnostics)."""
    src = tmp_path / "prog.ritz"
    src.write_text(program)
    ll = tmp_path / "prog.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    comp = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    if comp.returncode != 0 or not ll.exists():
        return None, comp.stdout + comp.stderr
    exe = tmp_path / "prog"
    link = subprocess.run(
        ["clang", str(RITZ_START), str(ll), "-o", str(exe), "-nostdlib"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    if link.returncode != 0:
        return None, link.stdout + link.stderr
    return subprocess.run([str(exe)], timeout=60).returncode, ""


@pytest.mark.integration
@pytest.mark.parametrize("program,want", RUN_CASES + NESTED_CASES)
def test_ritz0_merges_arms_at_annotation_float(ritz0_oracle, program, want):
    res = ritz0_oracle(program)
    assert res.ir_ok, res.diagnostics[-3000:]
    assert res.rc == want


@pytest.mark.integration
@pytest.mark.parametrize("program,want", RUN_CASES)
def test_ritz1_agrees(ritz1_bin, tmp_path, program, want):
    rc, diag = _ritz1_run(ritz1_bin, tmp_path, program)
    assert rc is not None, diag[-3000:]
    assert rc == want


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="#2092: ritz1 annotates only the outermost match/if")
@pytest.mark.parametrize("program,want", NESTED_CASES)
def test_ritz1_agrees_nested_tails(ritz1_bin, tmp_path, program, want):
    rc, diag = _ritz1_run(ritz1_bin, tmp_path, program)
    assert rc is not None, diag[-3000:]
    assert rc == want


def _ritz0_compile(run_ritz0, tmp_path: Path, program: str):
    src = tmp_path / "bad.ritz"
    src.write_text(program)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return run_ritz0([str(src), "-o", str(tmp_path / "bad.ll")],
                     cwd=tmp_path, env=env, timeout=300)


@pytest.mark.integration
@pytest.mark.parametrize("program", [
    pytest.param(POINTER_ARM, id="pointer-arm"),
    pytest.param(BOOL_ARM, id="bool-arm"),
])
def test_ritz0_rejects_non_numeric_arm_with_location(run_ritz0, tmp_path, program):
    comp = _ritz0_compile(run_ritz0, tmp_path, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "Traceback" not in out and "AttributeError" not in out, out
    # Located at the `let` (line 5), naming the variable and its annotation.
    assert "bad.ritz:5:" in out, out
    assert "`a` is declared `f64`" in out, out


@pytest.mark.integration
def test_ritz1_rejects_pointer_arm(ritz1_bin, tmp_path):
    rc, diag = _ritz1_run(ritz1_bin, tmp_path, POINTER_ARM)
    assert rc is None
    assert "match arm yields a non-numeric value" in diag
