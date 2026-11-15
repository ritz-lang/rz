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

import fast_link
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

fn seven() -> i32
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
        let m = n + n
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
# annotation reaches every tail of the initialiser, recursively, in both
# compilers (ritz1 since #2092).
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

# A nested tail reached through a block: an else-if branch that is a
# multi-line block ending in an integer, and a block-bodied match arm whose
# tail is an if.
NESTED_BLOCK_TAIL = """\
import ritzlib.option

fn f(n: i32) -> f64
    let a: f64 = if n > 5
        0.5
    else if n > 2
        let m = n + n
        m
    else
        0.25
    return a

fn g(o: Option<i32>) -> f64
    let a: f64 = match o
        None => 0.5
        Some(k) =>
            let d: i32 = k + 1
            if d > 3 then d else 0.5
    return a

fn main() -> i32
    if f(9) != 0.5
        return 1
    if f(3) != 6.0
        return 2
    if f(0) != 0.25
        return 3
    if g(None) != 0.5
        return 4
    if g(Some(5)) != 6.0
        return 5
    if g(Some(1)) != 0.5
        return 6
    return 42
"""

# Three levels, at f32: match -> if -> else-if chain, every tail an integer
# except one f32 leaf.
THREE_LEVELS_F32 = """\
import ritzlib.option

fn f(o: Option<i32>) -> f32
    let a: f32 = match o
        None => 7
        Some(k) => if k > 10 then 1 else if k > 5 then 2 else if k > 0 then 0.5 else 3
    return a

fn main() -> i32
    if f(None) != 7.0
        return 1
    if f(Some(11)) != 1.0
        return 2
    if f(Some(6)) != 2.0
        return 3
    if f(Some(1)) != 0.5
        return 4
    if f(Some(0)) != 3.0
        return 5
    return 42
"""

# Only tails take the annotation: a match / if in a nested match's scrutinee
# or a nested if's condition yields an integer there, not an f64.
NESTED_NON_TAIL = """\
import ritzlib.option

fn big(v: i32) -> bool
    return v > 2

fn f(n: i32) -> f64
    let a: f64 = if n > 5 then 0.5 else if big(if n > 0 then n else 0) then 2 else 0.25
    return a

fn g(o: Option<i32>, n: i32) -> f64
    let a: f64 = match o
        None => 0.5
        Some(k) => match (if n > 0 then k else 0)
            0 => 1
            _ => 0.25
    return a

fn main() -> i32
    if f(9) != 0.5
        return 1
    if f(3) != 2.0
        return 2
    if f(1) != 0.25
        return 3
    if g(None, 1) != 0.5
        return 4
    if g(Some(0), 1) != 1.0
        return 5
    if g(Some(3), 1) != 0.25
        return 6
    if g(Some(3), -1) != 1.0
        return 7
    return 42
"""

# AGAST #3313: every arm an integer, of differing types. ritz0 merged
# `k` (i32) and `1` (i64) at i64, and the annotation then refused i64 -> f64
# as lossy. Under the annotation each arm converts on its own (ritz1's rule),
# so `k` converts as the exact i32 it is and the literal is exempt.
ALL_INT_ARMS_IF = """\
fn h(k: i32) -> f64
    let a: f64 = if k > 3 then k else 1
    return a

fn g(k: i32) -> f64
    let a: f64 = if k > 3 then 2 else k
    return a

fn s(k: i16) -> f32
    let a: f32 = if k > 3 then k else 1
    return a

fn u(x: u32) -> f64
    let a: f64 = if x > 3 then x else 1
    return a

fn ub(x: u32) -> f64
    let a: f64 = if x > 3
        let y: u32 = x
        y
    else
        1
    return a

fn main() -> i32
    if h(5) != 5.0
        return 1
    if h(0) != 1.0
        return 2
    if g(5) != 2.0
        return 3
    if g(-7) != -7.0
        return 4
    if s(9) != 9.0
        return 5
    if s(-2) != 1.0
        return 6
    if u(4000000000) != 4000000000.0
        return 7
    if ub(4000000000) != 4000000000.0
        return 8
    if ub(2) != 1.0
        return 9
    return 42
"""

# The ticket's nested form: an all-int if as a match arm's tail.
ALL_INT_ARMS_NESTED = """\
import ritzlib.option

fn f(o: Option<i32>) -> f64
    let a: f64 = match o
        None => 2
        Some(k) => if k > 3 then k else 1
    return a

fn main() -> i32
    if f(None) != 2.0
        return 1
    if f(Some(5)) != 5.0
        return 2
    if f(Some(0)) != 1.0
        return 3
    return 42
"""

# The match form, all integer arms of differing types. Each arm converts by
# its own type: merged first, u32 and i16 widened to an i32 phi and 4e9 came
# out negative. A u32 *payload* binding `x` converted signed in ritz0 too: the
# merge converts after the arm's scope closed, so x's type was gone (#3332).
ALL_INT_ARMS_MATCH = """\
import ritzlib.option

fn f(o: Option<i16>) -> f64
    let a: f64 = match o
        None => 1
        Some(x) => x
    return a

fn p(o: Option<u32>) -> f64
    let a: f64 = match o
        None => 1
        Some(x) => x
    return a

fn g(k: i64, x: u32, w: i16) -> f64
    let a: f64 = match k
        0 => x
        1 => w
        _ => 3
    return a

fn main() -> i32
    let m: i16 = -9
    if f(Some(m)) != -9.0
        return 1
    if f(None) != 1.0
        return 2
    if g(0, 4000000000, 5) != 4000000000.0
        return 3
    if g(1, 1, -5) != -5.0
        return 4
    if g(2, 1, 1) != 3.0
        return 5
    let big: u32 = 4000000000
    if p(Some(big)) != 4000000000.0
        return 6
    if p(None) != 1.0
        return 7
    return 42
"""

ALL_INT_CASES = [
    pytest.param(ALL_INT_ARMS_IF, 42, id="all-int-arms-if"),
    pytest.param(ALL_INT_ARMS_NESTED, 42, id="all-int-arms-nested-match"),
    pytest.param(ALL_INT_ARMS_MATCH, 42, id="all-int-arms-match"),
]

NESTED_CASES = [
    pytest.param(ELSE_IF_CHAIN, 42, id="else-if-chain"),
    pytest.param(NESTED_MATCH, 42, id="nested-match"),
    pytest.param(NESTED_BLOCK_TAIL, 42, id="nested-block-tail"),
    pytest.param(THREE_LEVELS_F32, 42, id="three-levels-f32"),
    pytest.param(NESTED_NON_TAIL, 42, id="nested-non-tail"),
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
    link = fast_link.clang(
        ["clang", str(RITZ_START), str(ll), "-o", str(exe), "-nostdlib"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    if link.returncode != 0:
        return None, link.stdout + link.stderr
    return subprocess.run([str(exe)], timeout=60).returncode, ""


@pytest.mark.integration
@pytest.mark.parametrize("program,want", RUN_CASES + NESTED_CASES + ALL_INT_CASES)
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
@pytest.mark.parametrize("program,want", NESTED_CASES + ALL_INT_CASES)
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


# --- AGAST #3313: an arm that really is lossy --------------------------------
#
# Converting per arm does not exempt a non-literal i64 arm: it is refused just
# as `let a: f64 = x` is, in both compilers, whether its sibling is an i32
# value, a literal, or the same match nested.

LOSSY_I64_NEXT_TO_I32 = """\
fn f(x: i64, k: i32) -> f64
    let a: f64 = if k > 3 then k else x
    return a

fn main() -> i32
    return f(1, 2) as i32
"""

LOSSY_I64_NEXT_TO_LITERAL = """\
fn f(x: i64, k: i32) -> f64
    let a: f64 = if k > 3 then x else 1
    return a

fn main() -> i32
    return f(1, 2) as i32
"""

LOSSY_I64_NESTED = """\
import ritzlib.option

fn f(o: Option<i32>, x: i64) -> f64
    let a: f64 = match o
        None => 2
        Some(k) => if k > 3 then k else x
    return a

fn main() -> i32
    return f(None, 1) as i32
"""

LOSSY_CASES = [
    pytest.param(LOSSY_I64_NEXT_TO_I32, id="i64-next-to-i32"),
    pytest.param(LOSSY_I64_NEXT_TO_LITERAL, id="i64-next-to-literal"),
    pytest.param(LOSSY_I64_NESTED, id="i64-nested-match"),
]

LOSSY_WORDS = "implicit conversion from `i64` to `f64` can lose precision"


@pytest.mark.integration
@pytest.mark.parametrize("program", LOSSY_CASES)
def test_ritz0_refuses_lossy_int_arm(run_ritz0, tmp_path, program):
    comp = _ritz0_compile(run_ritz0, tmp_path, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "Traceback" not in out, out
    assert LOSSY_WORDS in out, out


@pytest.mark.integration
@pytest.mark.parametrize("program", LOSSY_CASES)
def test_ritz1_refuses_lossy_int_arm(ritz1_bin, tmp_path, program):
    rc, diag = _ritz1_run(ritz1_bin, tmp_path, program)
    assert rc is None, "ritz1 accepted a lossy i64 arm"
    assert LOSSY_WORDS in diag, diag


# AGAST #3332: a u64 payload arm is refused as `u64`, not `i64`: its
# signedness is read in the arm, where `x` is still bound. ritz1 accepts this
# arm with a silent sitofp (AGAST #3345), so the row is ritz0's alone.
LOSSY_U64_PAYLOAD = """\
import ritzlib.option

fn f(o: Option<u64>) -> f64
    let a: f64 = match o
        None => 1
        Some(x) => x
    return a

fn main() -> i32
    return f(None) as i32
"""


@pytest.mark.integration
def test_ritz0_refuses_u64_payload_arm_as_u64(run_ritz0, tmp_path):
    comp = _ritz0_compile(run_ritz0, tmp_path, LOSSY_U64_PAYLOAD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "bad.ritz:6:20:" in out, out
    assert ("implicit conversion from `u64` to `f64` can lose precision"
            in out), out


# --- AGAST #3344: an integer match's ident binding has the scrutinee's type ---
#
# `n => ...` in a match on a u32 bound `n` to the bare LLVM value, so ritz0
# read it as signed: `let b: f64 = n` in the arm, and the float-annotated
# `let a: f64 = match k / ... / n => n`, both gave sitofp, and 4e9 came out
# negative. ritz1 gives 4e9. Each form, u32 and an i32 control, on all three
# compilers; a u64 `n` is refused as `u64` in both forms.

SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

INT_MATCH_BINDING_IN_ARM_LET = """\
fn g(k: TY) -> f64
    match k
        0 => 1.0
        n =>
            let b: f64 = n
            b

fn main() -> i32
    if g(0) != 1.0
        return 1
    let x: TY = VAL
    if g(x) != VAL.0
        return 2
    return 42
"""

INT_MATCH_BINDING_ANNOTATED_ARM = """\
fn g(k: TY) -> f64
    let a: f64 = match k
        0 => 1
        n => n
    return a

fn main() -> i32
    if g(0) != 1.0
        return 1
    let x: TY = VAL
    if g(x) != VAL.0
        return 2
    return 42
"""

INT_MATCH_FORMS = {
    "in-arm-let": INT_MATCH_BINDING_IN_ARM_LET,
    "annotated-arm": INT_MATCH_BINDING_ANNOTATED_ARM,
}
INT_MATCH_TYPES = {"u32": "4000000000", "i32": "-5"}


def _run_with(compiler, ritz1_bin, ritz0_oracle, tmp_path, program):
    """(rc or None, diagnostics) of `program` under `compiler`."""
    if compiler == "ritz0":
        res = ritz0_oracle(program)
        return (res.rc if res.ir_ok else None), res.diagnostics
    binary = ritz1_bin if compiler == "ritz1" else SELFHOSTED_BIN
    return _ritz1_run(binary, tmp_path, program)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(INT_MATCH_TYPES))
@pytest.mark.parametrize("form", sorted(INT_MATCH_FORMS))
def test_int_match_binding_converts_by_scrutinee_type(
        ritz1_bin, ritz0_oracle, tmp_path, compiler, ty, form):
    program = (INT_MATCH_FORMS[form].replace("TY", ty)
               .replace("VAL", INT_MATCH_TYPES[ty]))
    rc, diag = _run_with(compiler, ritz1_bin, ritz0_oracle, tmp_path, program)
    assert rc is not None, diag[-3000:]
    assert rc == 42


# A u64 `n` is refused as `u64` (it was `i64`), at `n`. ritz1 accepts it in
# both forms (AGAST #3358), as it does a u64 payload (#3345), so the rows are
# ritz0's alone, as #3332's u64 row is.
INT_MATCH_U64_AT = {"in-arm-let": "bad.ritz:5:26:", "annotated-arm": "bad.ritz:4:14:"}


@pytest.mark.integration
@pytest.mark.parametrize("form", sorted(INT_MATCH_FORMS))
def test_ritz0_refuses_int_match_u64_binding_as_u64(run_ritz0, tmp_path, form):
    program = (INT_MATCH_FORMS[form].replace("TY", "u64")
               .replace("VAL", "4000000000"))
    comp = _ritz0_compile(run_ritz0, tmp_path, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert INT_MATCH_U64_AT[form] in out, out
    assert ("implicit conversion from `u64` to `f64` can lose precision"
            in out), out
