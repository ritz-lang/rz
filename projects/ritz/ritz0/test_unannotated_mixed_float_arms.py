"""AGAST #2094: an unannotated if / match whose arms mix an integer and a float.

`let a = if c > 0 then 0 else 1.5` merged at i64 in ritz0: _emit_if picked
the "larger" arm type by bit size, i64 and f64 are both 64 bits, so the THEN
type won and 1.5 was fptosi'd to 1 with no diagnostic. The match form
(`let a = match ... / 0 => 1.5 / _ => 2`) called the arms irreconcilable,
returned ir.Undefined, and died in LetStmt with a raw AttributeError.

The rule (ritz1's, #1946): with no float annotation to fix the merge type, a
match / if whose VALUE IS USED and whose arms yield both an integer and a
float is a located error, worded as ritz1 words it. Two deliberate limits:

* Only a used value is refused. A statement-position if / match whose arm
  tails happen to be an int call and a float call has no merge to type,
  so it stays legal (`_used_arms`, AGAST #2046, decides "used").
* ritz0 refuses both arm orders. ritz1 refuses only an integer arm BEFORE
  the first float arm (its single pass can no longer convert it); a float
  arm first fixes its phi type and later integer arms are converted. That
  order dependence is ritz1's, ticketed separately, not copied here.

The annotated form (`let a: f64 = if ...`) is #2027's and is covered by
test_let_float_match_int_arm.py.
"""

import os
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent

MESSAGE = "match arms yield both an integer and a float value"

# --- refused: one row per merge site, plus the shapes that reach it ----------

# The ticket repro: _emit_if, integer arm first.
IF_INT_THEN_FLOAT = """\
fn f(c: i32) -> i32
    let a = if c > 0 then 0 else 1.5
    return a as i32

fn main() -> i32
    return f(0)
"""

# _emit_if, float arm first: size alone kept the THEN type (f64) here, so
# this one happened to be right; it is refused all the same (one rule).
IF_FLOAT_THEN_INT = """\
fn f(c: i32) -> i32
    let a = if c > 0 then 2.5 else 7
    return a as i32

fn main() -> i32
    return f(0)
"""

# The nested else-if: the inner if merges first and must be refused there.
ELSE_IF_CHAIN = """\
fn f(c: i32) -> i32
    let a = if c > 1 then 1 else if c > 0 then 2.5 else 3
    return a as i32

fn main() -> i32
    return f(0)
"""

# The value consumed as a call argument, not a let: an i64 parameter took
# the truncated 1.
IF_AS_OPERAND = """\
fn g(x: i64) -> i32
    x as i32

fn f(c: i32) -> i32
    return g(if c > 0 then 0 else 1.5)

fn main() -> i32
    return f(0)
"""

# The tail of a fn that declares a value: its arms are not in _used_arms
# (#1429's carve-out), but the merge is returned.
FN_TAIL = """\
fn f(c: i32) -> i64
    if c > 0 then 0 else 1.5

fn main() -> i32
    return f(0) as i32
"""

# _enum_match_result.
ENUM_MATCH = """\
import ritzlib.option

fn f(o: Option<f64>) -> i32
    let a = match o
        None => 0
        Some(v) => v
    return a as i32

fn main() -> i32
    return f(None)
"""

# _emit_integer_match, float arm first.
INTEGER_MATCH = """\
fn f(c: i32) -> i32
    let a = match c
        0 => 1.5
        _ => 2
    return a as i32

fn main() -> i32
    return f(0)
"""

# _emit_union_match.
UNION_MATCH = """\
type IntOrStr = i32 | *u8

fn f(v: IntOrStr) -> i32
    let a = match v
        *u8 => 1.5
        i32 => 2
    return a as i32

fn main() -> i32
    let x: i32 = 5
    return f(x as IntOrStr)
"""

REFUSED = [
    # (program, line of the offending if / match)
    pytest.param(IF_INT_THEN_FLOAT, 2, id="if-int-then-float"),
    pytest.param(IF_FLOAT_THEN_INT, 2, id="if-float-then-int"),
    pytest.param(ELSE_IF_CHAIN, 2, id="else-if-chain"),
    pytest.param(IF_AS_OPERAND, 5, id="if-as-argument"),
    pytest.param(FN_TAIL, 2, id="fn-tail"),
    pytest.param(ENUM_MATCH, 4, id="enum-match"),
    pytest.param(INTEGER_MATCH, 2, id="integer-match"),
    pytest.param(UNION_MATCH, 4, id="union-match"),
]

# --- accepted ----------------------------------------------------------------

# A statement-position if / match: nothing consumes the arms' values.
STATEMENT_POSITION = """\
fn count(n: i32) -> i32
    n + 1

fn half(n: i32) -> f64
    (n as f64) / 2.0

fn f(c: i32) -> i32
    if c > 0
        count(c)
    else
        half(c)
    match c
        0 => count(c)
        _ => half(c)
    return 42

fn main() -> i32
    return f(0)
"""

# A procedure's tail is discarded too.
PROCEDURE_TAIL = """\
fn count(n: i32) -> i32
    n + 1

fn half(n: i32) -> f64
    (n as f64) / 2.0

fn g(c: i32)
    if c > 0
        count(c)
    else
        half(c)

fn main() -> i32
    g(0)
    return 42
"""

# The union match under a float annotation merges at it, as the enum and
# integer matches already do (#2027): the refusal's advice must hold there.
UNION_MATCH_ANNOTATED = """\
type IntOrStr = i32 | *u8

fn f(v: IntOrStr) -> f64
    let a: f64 = match v
        *u8 => 1.5
        i32 => 2
    return a

fn main() -> i32
    let x: i32 = 5
    if f(x as IntOrStr) != 2.0
        return 1
    return 42
"""

ACCEPTED = [
    pytest.param(STATEMENT_POSITION, id="statement-position"),
    pytest.param(PROCEDURE_TAIL, id="procedure-tail"),
    pytest.param(UNION_MATCH_ANNOTATED, id="union-match-annotated"),
]


def _ritz0_compile(run_ritz0, tmp_path: Path, program: str):
    src = tmp_path / "prog.ritz"
    src.write_text(program)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return run_ritz0([str(src), "-o", str(tmp_path / "prog.ll")],
                     cwd=tmp_path, env=env, timeout=300)


@pytest.mark.integration
@pytest.mark.parametrize("program,line", REFUSED)
def test_ritz0_refuses_unannotated_mixed_arms(run_ritz0, tmp_path, program, line):
    comp = _ritz0_compile(run_ritz0, tmp_path, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "Traceback" not in out and "AttributeError" not in out, out
    assert MESSAGE in out, out
    assert f"prog.ritz:{line}:" in out, out


@pytest.mark.integration
@pytest.mark.parametrize("program", ACCEPTED)
def test_ritz0_accepts(ritz0_oracle, program):
    res = ritz0_oracle(program)
    assert res.ir_ok, res.diagnostics[-3000:]
    assert res.rc == 42
