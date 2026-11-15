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
* Both compilers refuse both arm orders (LARB R43; ritz1 let a float arm
  that came first fix the phi and converted later integer arms until #3385).

The annotated form (`let a: f64 = if ...`) is #2027's and is covered by
test_let_float_match_int_arm.py.
"""

import os
import subprocess
from pathlib import Path

import fast_link
import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

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

# --- LARB R43 (#3384): a return type or parameter type is a float slot -------
#
# `-> f64` and an `f64` parameter fix the merge type as an annotated let does:
# an integer *literal* arm converts. Each row checks the values, so a merge at
# i64 (1.5 truncated to 1) fails too.

# `return <if>` and `return <match>` in a `-> f64` fn.
RETURN_HINT = """\
fn f(c: i32) -> f64
    return if c > 0 then 1.5 else 0

fn g(c: i32) -> f64
    return match c
        0 => 0
        _ => 1.5

fn main() -> i32
    if f(0) != 0.0 or f(1) != 1.5
        return 1
    if g(0) != 0.0 or g(1) != 1.5
        return 2
    return 42
"""

# The tail of a `-> f64` fn, integer arm first: FN_TAIL above refuses the
# same arms under `-> i64`.
TAIL_HINT = """\
fn f(c: i32) -> f64
    if c > 0 then 0 else 1.5

fn main() -> i32
    if f(1) != 0.0 or f(0) != 1.5
        return 1
    return 42
"""

# An argument for an `f64` parameter: IF_AS_OPERAND above refuses the same
# arms for an `i64` parameter. A direct call, a fn-pointer local and an
# expression callee each find the parameter type on their own path.
PARAM_HINT = """\
fn g(x: f64) -> f64
    x

fn f(c: i32) -> f64
    g(if c > 0 then 0 else 1.5)

fn fp(c: i32) -> f64
    let h: fn(f64) -> f64 = g
    h(if c > 0 then 0 else 1.5)

fn fe(c: i32) -> f64
    let hs: [1]fn(f64) -> f64 = [g]
    hs[0](if c > 0 then 0 else 1.5)

fn main() -> i32
    if f(1) != 0.0 or f(0) != 1.5
        return 1
    if fp(1) != 0.0 or fp(0) != 1.5
        return 2
    if fe(1) != 0.0 or fe(0) != 1.5
        return 3
    return 42
"""

# An argument for an `f64` parameter of a method and of a static method.
METHOD_PARAM_HINT = """\
struct Acc
    total: f64

impl Acc
    fn make(x: f64) -> Acc
        Acc { total: x }

    fn add(self: @Acc, x: f64) -> f64
        self.total + x

fn f(c: i32) -> f64
    let a = Acc { total: 0.5 }
    a.add(if c == 0 then 2 else 1.5)

fn fs(c: i32) -> f64
    Acc.make(if c > 0 then 0 else 1.5).total

fn main() -> i32
    if f(0) != 2.5 or f(1) != 2.0
        return 1
    if fs(1) != 0.0 or fs(0) != 1.5
        return 2
    return 42
"""

ACCEPTED = [
    pytest.param(STATEMENT_POSITION, id="statement-position"),
    pytest.param(PROCEDURE_TAIL, id="procedure-tail"),
    pytest.param(UNION_MATCH_ANNOTATED, id="union-match-annotated"),
    pytest.param(RETURN_HINT, id="return-hint"),
    pytest.param(TAIL_HINT, id="tail-hint"),
    pytest.param(PARAM_HINT, id="param-hint"),
    pytest.param(METHOD_PARAM_HINT, id="method-param-hint"),
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


# --- a float slot refuses an arm §7.5 calls lossy (LARB R43a) ----------------
#
# An `i64` arm is not exact in f64 (§7.5): the slot gives the merge its type,
# then refuses that arm as a typed let does. LOSSY_ARMS below runs these on
# all three compilers.

RETURN_NON_LITERAL = """\
fn f(c: i32, n: i64) -> f64
    return if c > 0 then n else 1.5

fn main() -> i32
    return f(0, 3) as i32
"""

PARAM_NON_LITERAL = """\
fn g(x: f64) -> f64
    x

fn f(c: i32, n: i64) -> f64
    g(if c == 0 then 1.5 else n)

fn main() -> i32
    return f(0, 3) as i32
"""



# --- the R43a slot rows, on all three compilers (#3384, #3385) ---------------
#
# The rule is order-free: with no float slot an integer arm is refused on
# either side of a float arm. A float slot is a typed let / var, a `return` or
# tail in a `-> f64` fn and an `f64` / `f32` parameter; it is known before the
# first arm is emitted, so the merge takes its type up front and each integer
# arm converts as `let a: f64 = n` would (§7.5): a literal, or a type exact in
# the slot (f64: i8..i32, u8..u32; f32: i8, i16, u8, u16), by its own
# signedness. Any other integer arm is refused with §7.5's message.

RITZ1_REFUSED = [
    pytest.param(IF_INT_THEN_FLOAT, id="if-int-then-float"),
    pytest.param(IF_FLOAT_THEN_INT, id="if-float-then-int"),
    pytest.param(INTEGER_MATCH, id="integer-match"),
]

# Each slot, integer arm on both sides, literal and exact non-literal arms.
# Every value is checked: a merge at i64 (1.5 truncated) fails too.

# `return <if / match>` in a `-> f64` fn; the R43a i32 row.
RETURN_SLOT = """\
fn f(c: i32, k: i32) -> f64
    return if c > 0 then 2.5 else k

fn g(c: i32, k: i32) -> f64
    return if c > 0 then k else 2.5

fn h(c: i32) -> f64
    return match c
        0 => 0
        _ => 1.5

fn main() -> i32
    if f(1, 3) != 2.5 or f(0, 3) != 3.0 or f(0, -3) != -3.0
        return 1
    if g(1, 3) != 3.0 or g(0, 3) != 2.5
        return 2
    if h(0) != 0.0 or h(1) != 1.5
        return 3
    return 42
"""

# The tail of a `-> f64` fn and of a method: an expression tail and a
# statement-form `match` tail. A u32 arm converts by uitofp.
TAIL_SLOT = """\
struct P
    x: f64

impl P
    fn pick(self: @P, c: i32, k: i32) -> f64
        if c > 0 then k else self.x

fn f(c: i32, k: u32) -> f64
    if c > 0 then k else 2.5

fn g(c: i32) -> f64
    match c
        0 => 1.5
        _ => 7

fn main() -> i32
    if f(1, 4000000000) != 4000000000.0 or f(0, 9) != 2.5
        return 1
    if g(0) != 1.5 or g(1) != 7.0
        return 2
    let p = P { x: 0.5 }
    if p.pick(1, 6) != 6.0 or p.pick(0, 6) != 0.5
        return 3
    return 42
"""

# An argument for an `f64` parameter of a fn, a method and a static method,
# and for an `f32` one (a u16 arm is exact there).
PARAM_SLOT = """\
struct Acc
    total: f64

impl Acc
    fn make(x: f64) -> Acc
        Acc { total: x }

    fn add(self: @Acc, x: f64) -> f64
        self.total + x

fn g(x: f64) -> f64
    x

fn h(x: f32) -> f32
    x

fn main() -> i32
    let c: i32 = 0
    let k: i32 = 3
    let u: u16 = 9
    if g(if c > 0 then 1.5 else k) != 3.0 or g(if c == 0 then 1.5 else k) != 1.5
        return 1
    let a = Acc { total: 0.5 }
    if a.add(if c == 0 then k else 1.5) != 3.5
        return 2
    if Acc.make(if c > 0 then 1.5 else 2).total != 2.0
        return 3
    if h(if c == 0 then u else 0.5) != 9.0
        return 4
    return 42
"""

SLOTS = [
    pytest.param(RETURN_SLOT, id="return-slot"),
    pytest.param(TAIL_SLOT, id="tail-slot"),
    pytest.param(PARAM_SLOT, id="param-slot"),
]

# R43a: an arm whose type is not exact in the slot is refused as lossy, in
# either order, where the slot comes from.
RETURN_I64_ARM = """\
fn f(c: i32, n: i64) -> f64
    return if c > 0 then 2.5 else n

fn main() -> i32
    return f(0, 3) as i32
"""

TAIL_I64_ARM_FIRST = """\
fn f(c: i32, n: i64) -> f64
    if c > 0 then n else 2.5

fn main() -> i32
    return f(0, 3) as i32
"""

PARAM_U64_ARM = """\
fn g(x: f64) -> f64
    x

fn f(c: i32, n: u64) -> f64
    g(if c == 0 then 1.5 else n)

fn main() -> i32
    return f(0, 3) as i32
"""

F32_I32_ARM = """\
fn f(c: i32, n: i32) -> f32
    return if c > 0 then 0.5 else n

fn main() -> i32
    return f(0, 3) as i32
"""

LOSSY_ARMS = [
    pytest.param(RETURN_NON_LITERAL, "i64", "f64", id="return-non-literal"),
    pytest.param(PARAM_NON_LITERAL, "i64", "f64", id="param-non-literal"),
    pytest.param(RETURN_I64_ARM, "i64", "f64", id="return-i64-arm"),
    pytest.param(TAIL_I64_ARM_FIRST, "i64", "f64", id="tail-i64-arm-first"),
    pytest.param(PARAM_U64_ARM, "u64", "f64", id="param-u64-arm"),
    pytest.param(F32_I32_ARM, "i32", "f32", id="f32-i32-arm"),
]


def _lossy(src, dst):
    return f"implicit conversion from `{src}` to `{dst}` can lose precision: write `<expr> as {dst}`"


@pytest.mark.integration
@pytest.mark.parametrize("program", SLOTS)
def test_ritz0_float_slot_converts_int_arms(ritz0_oracle, program):
    res = ritz0_oracle(program)
    assert res.ir_ok, res.diagnostics[-3000:]
    assert res.rc == 42


@pytest.mark.integration
@pytest.mark.parametrize("program,src,dst", LOSSY_ARMS)
def test_ritz0_float_slot_refuses_lossy_int_arm(run_ritz0, tmp_path, program, src, dst):
    comp = _ritz0_compile(run_ritz0, tmp_path, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "Traceback" not in out, out
    assert _lossy(src, dst) in out, out
    assert MESSAGE not in out, out


# ritz1 runs #3384's literal-arm rows too: each slot path again, plus the
# fn-pointer and expression callees.
ACCEPTED_SLOTS = SLOTS + [p for p in ACCEPTED if p.id.endswith("-hint")]


def _ritz1(request, compiler, tmp_path, program):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    src = tmp_path / "prog.ritz"
    src.write_text(program)
    ll = tmp_path / "prog.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("program", RITZ1_REFUSED)
def test_ritz1_refuses_unannotated_mixed_arms(request, tmp_path, compiler, program):
    proc, ll = _ritz1(request, compiler, tmp_path, program)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler}:\n{out[-800:]}"
    assert MESSAGE in out, f"{compiler}:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("program", ACCEPTED_SLOTS)
def test_ritz1_float_slot_converts_int_arms(request, tmp_path, compiler, program):
    proc, ll = _ritz1(request, compiler, tmp_path, program)
    assert proc.returncode == 0, f"{compiler}:\n{(proc.stdout + proc.stderr)[-800:]}"
    exe = tmp_path / "prog"
    fast_link.clang(["clang", "-w", str(ll), str(RITZ_START), "-o", str(exe), "-nostdlib"],
                    check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == 42, compiler


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("program,src,dst", LOSSY_ARMS)
def test_ritz1_float_slot_refuses_lossy_int_arm(request, tmp_path, compiler, program, src, dst):
    proc, ll = _ritz1(request, compiler, tmp_path, program)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler}:\n{out[-800:]}"
    assert _lossy(src, dst) in out, out[-800:]
    assert MESSAGE not in out, out[-800:]
