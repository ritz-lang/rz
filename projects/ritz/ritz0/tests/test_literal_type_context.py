#!/usr/bin/env python3
"""An integer literal must take its type from context, not force i64.

AGAST #1396.

THE DEFECT

`_emit_expr` types every `rast.IntLit` as i64 unconditionally
(emitter_llvmlite.py, `return ir.Constant(self.i64, expr.value)`). In a binary
expression that drags the *other* operand up to 64 bits, computes there, and
truncates back. The same expression without a literal stays at its natural
width:

    fn clean(x: u32, y: u32) -> u32     fn lit(x: u32) -> u32
        let p: u32 = x + y                  let q: u32 = x + 1

    add i32 %x, %y                      zext i32 %x to i64
                                        add i64 %.6, 1
                                        trunc i64 %.7 to i32

WHY IT MATTERS BEYOND TIDINESS

This is the blocker in front of AGAST #1393 (#1364's decision that implicit
narrowing becomes a hard error). A corpus sweep over 115 packages found 309
unique narrowing sites, of which **292 (94%) are this artifact** — code that is
already correctly annotated:

    fn xtime(x: u8) -> u8               # projects/cryptosec/aes.ritz
        let x32: u32 = x as u32
        let hi: u32 = (x32 >> 7) & 1    # flagged: every operand already u32

Landing #1393 first would demand `as u32` on code that is already right, and it
would land hardest on crypto/hashing/parser code — exactly where explicit widths
matter most.

THE RULE THESE TESTS PIN (LARB R21, AGAST #3112, #3225)

This file first pinned "a literal takes the DECLARED type" and rejected the
sibling-operand rule, because under it

    let big: i64 = x * 1000             # x: u32

multiplies in 32 bits and wraps. R21 (confirmed by Aaron, 2026-11-14) chose the
sibling-operand rule: a literal operand is the other operand's type, so `x + 1`
is a u32 as `x + y` always was. Aaron then ruled on the hazard (#3225): "silent
widening is ok, just not silent wrapping." An operation used directly in a
WIDER integer slot runs at the slot's type, its operands widened first, so
`let big: i64 = x * 1000` is an i64 multiply again, and so is `x * k`. Without
a wider slot (`var n = m + 1`) R21 stands and the u32 wraps; overflow there is
#3197's question.

The declared type still gives a shift's left literal its width
(`let r: u32 = 1 << n`), which R21 leaves an i64 (see _retype_literal_operand).

Narrowing is congruent for `+ - * << & | ^`: `trunc(op(zext a, zext b))` is
`op(a, b)` mod 2**n. The tests assert the IR shape rather than just the exit
code, because a test that only checked "it compiles" would have passed before
the fix.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0
import test_ir

RITZ_ROOT = Path(__file__).resolve().parents[2]

# Every test compiles with ritz0 (AGAST #1805).
pytestmark = pytest.mark.integration


def _emit_ir(tmp_path, source):
    """Compile a source fragment and return its LLVM IR text."""
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    out = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0(
        [str(src), "-o", str(out), "--no-runtime"],
        env=env, timeout=300,
    )
    assert proc.returncode == 0, (
        f"compile failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    return out.read_text()


def _body(ir_text, fn_name):
    """Return the instruction lines of one function, debug metadata stripped."""
    m = re.search(
        r'define [^\n]*' + test_ir.symbol(fn_name) + r'[^\n]*\n\{\n(.*?)\n\}',
        ir_text, re.S,
    )
    assert m, f"function {fn_name} not found in IR"
    lines = []
    for line in m.group(1).splitlines():
        line = re.sub(r",?\s*!dbg.*$", "", line).strip()
        if line and not line.startswith("call void @\"llvm.dbg"):
            lines.append(line)
    return lines


def _ops(ir_text, fn_name):
    """The set of LLVM opcodes used in a function body."""
    found = set()
    for line in _body(ir_text, fn_name):
        m = re.search(r"=\s*(\w+)", line)
        if m:
            found.add(m.group(1))
    return found


# --------------------------------------------------------------------------
# The defect itself: a literal must not widen its neighbours.
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_literal_operand_does_not_force_a_64_bit_round_trip(tmp_path):
    """`x + 1` on a u32 must stay 32-bit, exactly as `x + y` does."""
    ir_text = _emit_ir(tmp_path, (
        "fn lit(x: u32) -> u32\n"
        "    let q: u32 = x + 1\n"
        "    return q\n"
    ))
    ops = _ops(ir_text, "lit")
    assert "zext" not in ops and "sext" not in ops, (
        f"literal widened its neighbour: {_body(ir_text, 'lit')}"
    )
    assert "trunc" not in ops, (
        f"result truncated back down: {_body(ir_text, 'lit')}"
    )
    assert any("add i32" in line for line in _body(ir_text, "lit")), (
        f"expected a 32-bit add: {_body(ir_text, 'lit')}"
    )


@pytest.mark.unit
def test_literal_free_expression_is_the_control(tmp_path):
    """`x + y` was always correct — it must stay correct.

    Without this control, deleting all integer widening would pass the test
    above.
    """
    ir_text = _emit_ir(tmp_path, (
        "fn clean(x: u32, y: u32) -> u32\n"
        "    let p: u32 = x + y\n"
        "    return p\n"
    ))
    ops = _ops(ir_text, "clean")
    assert "zext" not in ops and "trunc" not in ops
    assert any("add i32" in line for line in _body(ir_text, "clean"))


@pytest.mark.unit
@pytest.mark.parametrize("op,mnemonic", [
    ("+", "add"), ("-", "sub"), ("*", "mul"),
    ("&", "and"), ("|", "or"), ("^", "xor"),
])
def test_each_wrapping_operator_stays_at_the_declared_width(
        tmp_path, op, mnemonic):
    """The operators for which narrowing is congruent mod 2**n.

    `>>`, `<<`, `/` and `%` are deliberately NOT in this list — see the
    shift test below for why they are handled separately.
    """
    ir_text = _emit_ir(tmp_path, (
        f"fn f(x: u32) -> u32\n"
        f"    let q: u32 = x {op} 7\n"
        f"    return q\n"
    ))
    body = _body(ir_text, "f")
    assert "zext" not in _ops(ir_text, "f"), f"{op} widened: {body}"
    assert any(f"{mnemonic} i32" in line for line in body), \
        f"expected 32-bit {mnemonic}: {body}"


@pytest.mark.unit
def test_the_cryptosec_shape_is_clean(tmp_path):
    """The real-world site class that dominates the #1393 sweep.

    Every operand here is already declared u32; the author annotated it
    correctly. 292 of the 309 sites the sweep found are this shape.
    """
    ir_text = _emit_ir(tmp_path, (
        "fn xtime(x: u8) -> u32\n"
        "    let x32: u32 = x as u32\n"
        "    let hi: u32 = (x32 >> 7) & 1\n"
        "    return hi\n"
    ))
    body = _body(ir_text, "xtime")
    i64_math = [l for l in body
                if re.search(r"\b(add|sub|mul|and|or|xor|shl|lshr|ashr) i64\b", l)]
    assert not i64_math, f"64-bit arithmetic on u32-only code: {body}"


# --------------------------------------------------------------------------
# The hazard #1396 named: a wider slot. R21 types `x * 1000` as x's, and #3225
# computes it in the wider slot it lands in, so it can't wrap at 32 bits.
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_a_widening_target_keeps_64_bit_arithmetic(tmp_path):
    """`let big: i64 = x * 1000` is an i64 multiply (AGAST #3225).

    Aaron: "silent widening is ok, just not silent wrapping." Each operand is
    widened by its own signedness, so the u32 is zero-extended first. Run on
    all three compilers (x = 5_000_000 gives 5_000_000_000) by
    test_wider_slot_widens.py's `let_mul`.
    """
    ir_text = _emit_ir(tmp_path, (
        "fn widen_mul(x: u32) -> i64\n"
        "    let big: i64 = x * 1000\n"
        "    return big\n"
    ))
    body = _body(ir_text, "widen_mul")
    assert any("mul i64" in line for line in body), f"an i64 slot multiplies in 64 bits: {body}"
    assert not any("mul i32" in line for line in body), body
    assert any(re.search(r"\bzext i32 .* to i64", line) for line in body), (
        f"the u32 operand is zero-extended before the multiply: {body}"
    )


@pytest.mark.unit
def test_without_a_wider_slot_r21_wraps(tmp_path):
    """The control: `var n = m + 1` has no wider slot, so it is m's u32 (R21)."""
    ir_text = _emit_ir(tmp_path, (
        "fn bump(m: u32) -> u32\n"
        "    var n = m + 1\n"
        "    return n\n"
    ))
    body = _body(ir_text, "bump")
    assert any("add i32" in line for line in body), f"m + 1 is a u32 add: {body}"
    assert not any("add i64" in line for line in body), body


@pytest.mark.unit
def test_a_widening_shift_keeps_64_bit_arithmetic(tmp_path):
    """Shift form: `x << 20` into an i64 shifts in 64 bits; the count has no say."""
    ir_text = _emit_ir(tmp_path, (
        "fn widen_shl(x: u32) -> i64\n"
        "    let big: i64 = x << 20\n"
        "    return big\n"
    ))
    body = _body(ir_text, "widen_shl")
    assert any("shl i64" in line for line in body), f"an i64 slot shifts in 64 bits: {body}"


@pytest.mark.unit
def test_a_call_argument_is_its_parameters_slot(tmp_path):
    """The argument's slot is the PARAMETER, never the enclosing declaration.

        fn takes64(v: i64) -> u32
        let q: u32 = takes64(x * 1000)      # x: u32

    #1396's first version leaked the declared u32 into the argument and
    multiplied in 32 bits. The i64 parameter is a wider slot (#3225), so the
    multiply is an i64 one on the zero-extended u32.
    """
    ir_text = _emit_ir(tmp_path, (
        "fn takes64(v: i64) -> u32\n"
        "    return 0u32\n"
        "\n"
        "fn leak(x: u32) -> u32\n"
        "    let q: u32 = takes64(x * 1000)\n"
        "    return q\n"
    ))
    body = _body(ir_text, "leak")
    assert any("mul i64" in line for line in body), f"the i64 parameter multiplies in 64 bits: {body}"
    assert not any("mul i32" in line for line in body), f"the declared u32 leaked in: {body}"
    assert not any(re.search(r"\bsext i32", line) for line in body), (
        f"a u32 operand is widened unsigned: {body}"
    )


@pytest.mark.unit
def test_an_index_expression_does_not_inherit_the_declared_type(tmp_path):
    """Same boundary, index position — the index is not consumed at `u8`."""
    ir_text = _emit_ir(tmp_path, (
        "fn pick(p: *u8, i: u32) -> u8\n"
        "    let b: u8 = p[i + 1]\n"
        "    return b\n"
    ))
    body = _body(ir_text, "pick")
    assert not any(re.search(r"\badd i8\b", line) for line in body), (
        f"index arithmetic was narrowed to the element type: {body}"
    )


# --------------------------------------------------------------------------
# Runtime behaviour, not just IR shape.
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_arithmetic_results_are_unchanged_at_the_declared_width(tmp_path):
    """The narrowed arithmetic must produce the same answers.

    Encoded in the exit code so the assertion does not depend on stdout
    capture (a trap that has produced false greens in this repo before).
    """
    source = (
        "fn calc(x: u32) -> u32\n"
        "    let q: u32 = x + 1\n"
        "    let r: u32 = q * 3\n"
        "    let s: u32 = (r >> 1) & 0xff\n"
        "    return s\n"
        "\n"
        "fn main() -> i32\n"
        "    return calc(9u32) as i32\n"
    )
    # (9+1)*3 = 30; 30 >> 1 = 15; 15 & 0xff = 15
    src = tmp_path / "rt.ritz"
    src.write_text(source)
    ll = tmp_path / "rt.ll"
    exe = tmp_path / "rt"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    build = run_ritz0([str(src), "-o", str(ll)], env=env, timeout=300)
    assert build.returncode == 0, build.stderr
    # -nostdlib matches build.py: ritz0 emits its own `_start`.
    link = fast_link.clang(
        ["clang", str(ll), "-o", str(exe), "-nostdlib"],
        capture_output=True, text=True, timeout=300,
    )
    assert link.returncode == 0, link.stderr
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == 15, (
        f"expected 15, got {run.returncode} — narrowing changed the answer"
    )


@pytest.mark.unit
def test_a_literal_too_large_for_its_context_is_a_located_error(tmp_path):
    """Adopting the declared type must not silently truncate the literal.

    `4294967301` does not fit in u32. Before this change the literal was an
    i64 and the narrowing was hidden in the store; it must now be rejected,
    and rejected with a location rather than a Python traceback.
    """
    src = tmp_path / "toobig.ritz"
    src.write_text(
        "fn f() -> u32\n"
        "    let bad: u32 = 4294967301\n"
        "    return bad\n"
    )
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0(
        [str(src), "-o", str(tmp_path / "toobig.ll"), "--no-runtime"],
        env=env, timeout=300,
    )
    assert proc.returncode != 0, "a literal that cannot fit was accepted"
    combined = proc.stdout + proc.stderr
    assert re.search(r"[\w./-]+\.ritz:\d+:\d+:", combined), (
        f"rejection carries no location:\n{combined}"
    )
    assert "Traceback" not in combined, (
        f"rejection arrived as a Python traceback:\n{combined}"
    )


# --------------------------------------------------------------------------
# AGAST #1445: the context reaches the arm values of an if / match.
# --------------------------------------------------------------------------
#
# An arm's value is consumed at the if / match's own type, which is the slot's,
# so the declared type follows the value tails: then / else block values and
# match arm bodies, through nested if / match / block. Never the condition or
# the scrutinee, which are consumed as a bool and at their own type.
#
# AGAST #4219 (LARB R73): a chain of congruent operators (`+ - * & | ^ <<`)
# carries the slot's width down too, so `x + (if c then x else 255)` is i32.
# `/`, `%` and `>>` still stop it: `2 * (if c then a else 200) / 4` at u8
# would multiply in 8 bits before the `/` (the #1396 `>>` / `/` / `%` hazard),
# where today it does so at 64.

def _no_round_trip(body):
    """No i64 value and no truncation anywhere in a function body."""
    return not any(re.search(r"\bi64\b|\btrunc\b", line) for line in body)


@pytest.mark.unit
def test_a_literal_arm_takes_the_declared_type(tmp_path):
    """The two #1445 lines, plus var / return / match / nested / negative arms.

    One compile for the lot: each function is its own assertion. The
    conditions compare two i32s so that `i64` can only come from an arm.
    """
    ir_text = _emit_ir(tmp_path, (
        "fn let_else(a: i32, b: i32) -> i32\n"
        "    let m: i32 = if a < b then a else 255\n"
        "    return m\n"
        "\n"
        "fn let_then_arith(a: i32, b: i32) -> i32\n"
        "    let k: i32 = if a < b then 255 else a - 1\n"
        "    return k\n"
        "\n"
        "fn var_slot(a: u32, b: u32) -> u32\n"
        "    var m: u32 = if a < b then a else 4000000000\n"
        "    return m\n"
        "\n"
        "fn ret_slot(a: i32, b: i32) -> i32\n"
        "    return if a < b then a else 255\n"
        "\n"
        "fn match_slot(a: i32, b: u8) -> u8\n"
        "    let m: u8 = match a\n"
        "        0 => 200\n"
        "        _ => b\n"
        "    return m\n"
        "\n"
        "fn nested(a: i32, b: i32) -> i32\n"
        "    let m: i32 = if a < b then a else if a == b then 7 else 255\n"
        "    return m\n"
        "\n"
        "fn negative(a: i8, b: i8) -> i8\n"
        "    let m: i8 = if a < b then a else -128\n"
        "    return m\n"
        "\n"
        "fn block_arm(a: i32, b: i32) -> i32\n"
        "    let m: i32 = if a < b\n"
        "        let t = b\n"
        "        a + t\n"
        "    else\n"
        "        255\n"
        "    return m\n"
    ))
    for fn in ("let_else", "let_then_arith", "var_slot", "ret_slot",
               "match_slot", "nested", "negative", "block_arm"):
        body = _body(ir_text, fn)
        assert _no_round_trip(body), f"{fn}: an arm was computed in i64: {body}"


@pytest.mark.unit
def test_a_literal_arm_takes_the_type_of_every_narrowing_slot(tmp_path):
    """AGAST #4164: #1444's slots, not just let / var / return.

    An assignment, a call argument and a fn's tail are narrowing-checked too,
    so a literal arm merged at i64 there was a round-trip that loses no bits.
    (`m += if ...` is `m = m + (if ...)`: an if under a congruent operator,
    which takes the slot's width as a `let` does — AGAST #4219, LARB R73.)
    """
    ir_text = _emit_ir(tmp_path, (
        "fn take_i32(v: i32) -> i32\n"
        "    v\n"
        "\n"
        "fn assign(a: i32, b: i32) -> i32\n"
        "    var m: i32 = b\n"
        "    m = if a < b then a else 255\n"
        "    m\n"
        "\n"
        "fn assign_add(a: i32, b: i32) -> i32\n"
        "    var m: i32 = b\n"
        "    m += if a < b then a else 255\n"
        "    m\n"
        "\n"
        "fn arg(a: i32, b: i32) -> i32\n"
        "    take_i32(if a < b then a else 255)\n"
        "\n"
        "fn tail(a: i32, b: i32) -> i32\n"
        "    if a < b then a else 255\n"
        "\n"
        "fn take_u32(v: u32) -> u32\n"
        "    v\n"
        "\n"
        "fn arg_u32(a: u32, b: u32) -> u32\n"
        "    take_u32(if a < b then a else 4000000000)\n"
    ))
    # arg_u32: the arm fits the slot only read as unsigned.
    for fn in ("assign", "assign_add", "arg", "tail", "arg_u32"):
        body = _body(ir_text, fn)
        assert _no_round_trip(body), f"{fn}: an arm was computed in i64: {body}"


@pytest.mark.unit
def test_an_operator_in_an_arm_takes_the_declared_type(tmp_path):
    """`1 << n` in an arm is #1396's left-literal shift, in the slot's width."""
    ir_text = _emit_ir(tmp_path, (
        "fn shl_arm(c: bool, n: u32, a: u32) -> u32\n"
        "    let r: u32 = if c then 1 << n else a\n"
        "    return r\n"
        "\n"
        "fn shl_match_arm(k: i32, n: u32, a: u32) -> u32\n"
        "    let r: u32 = match k\n"
        "        0 => 1 << n\n"
        "        _ => a\n"
        "    return r\n"
    ))
    for fn in ("shl_arm", "shl_match_arm"):
        body = _body(ir_text, fn)
        assert any("shl i32" in line for line in body), f"{fn}: {body}"
        assert _no_round_trip(body), f"{fn}: {body}"


@pytest.mark.unit
def test_the_condition_and_scrutinee_keep_their_own_type(tmp_path):
    """Not consumed at the slot's type, so not narrowed: `1 << n` stays i64.

    With `n = 31` an i32 `1 << n` is negative, so narrowing the condition
    would change which arm runs.
    """
    ir_text = _emit_ir(tmp_path, (
        "fn cond(n: i32, a: i32) -> i32\n"
        "    let r: i32 = if (1 << n) > 0 then a else 0\n"
        "    return r\n"
        "\n"
        "fn scrut(n: i32, a: i32) -> i32\n"
        "    let r: i32 = match (1 << n) > 0\n"
        "        true => a\n"
        "        false => 0\n"
        "    return r\n"
    ))
    for fn in ("cond", "scrut"):
        body = _body(ir_text, fn)
        assert any("shl i64" in line for line in body), f"{fn}: narrowed: {body}"
        assert not any("shl i32" in line for line in body), f"{fn}: {body}"


@pytest.mark.unit
def test_a_congruent_path_does_not_enter_the_condition(tmp_path):
    """AGAST #4219: following the if through `+` does not follow its condition.

    `1 << n` in the condition stays i64 — with n = 31 an i32 `1 << n` is
    negative, which would flip the comparison and change which arm runs.
    """
    ir_text = _emit_ir(tmp_path, (
        "fn f(n: i32, x: i32) -> i32\n"
        "    let k: i32 = x + (if (1 << n) < 0 then x else 255)\n"
        "    return k\n"
    ))
    body = _body(ir_text, "f")
    assert any("shl i64" in line for line in body), f"condition narrowed: {body}"
    assert not any("shl i32" in line for line in body), body


@pytest.mark.unit
def test_an_if_under_an_operator_is_not_an_arm_of_the_slot(tmp_path):
    """`2 * (if c then 200 else 100) / 4` into u8 must not multiply in 8 bits.

    At u8, 200 * 2 wraps to 144 and the `/` gives 36, not 100: the arms are
    consumed by the `*`, whose result the `/` reads at full width. The value
    stays i64, so the narrowing it is still has to be proven (it can't be).
    """
    src = tmp_path / "under.ritz"
    src.write_text(
        "fn f(c: bool) -> u8\n"
        "    let m: u8 = 2 * (if c then 200 else 100) / 4\n"
        "    return m\n"
    )
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(tmp_path / "under.ll"), "--no-runtime"],
                     env=env, timeout=300)
    assert proc.returncode != 0 and "implicit narrowing:" in proc.stderr, (
        f"the if under `*` took the slot's u8:\n{proc.stdout}{proc.stderr}")


@pytest.mark.unit
def test_literal_arms_give_the_same_answers(tmp_path):
    """Runtime check of the #1445 shapes, encoded in the exit code."""
    source = (
        "fn clamp(a: i32) -> i32\n"
        "    let m: i32 = if a < 255 then a else 255\n"
        "    return m\n"
        "\n"
        "fn clamp1(a: i32) -> i32\n"
        "    let k: i32 = if a - 1 < 255 then a - 1 else 255\n"
        "    return k\n"
        "\n"
        "fn low(a: i8) -> i8\n"
        "    let m: i8 = if a < 0 then -128 else a\n"
        "    return m\n"
        "\n"
        "fn id8(v: i8) -> i8\n"
        "    v\n"
        "\n"
        "fn assign(a: i8) -> i8\n"
        "    var m: i8 = a\n"
        "    m = if a < 0 then -128 else a\n"
        "    m\n"
        "\n"
        "fn tail(a: i8) -> i8\n"
        "    id8(if a < 0 then -128 else a)\n"
        "\n"
        "fn main() -> i32\n"
        "    if assign(-1) != -128 or assign(9) != 9\n"
        "        return 7\n"
        "    if tail(-1) != -128 or tail(9) != 9\n"
        "        return 8\n"
        "    if clamp(1000) != 255\n"
        "        return 1\n"
        "    if clamp(-5) != -5\n"
        "        return 2\n"
        "    if clamp1(1000) != 255\n"
        "        return 3\n"
        "    if clamp1(10) != 9\n"
        "        return 4\n"
        "    if low(-1) != -128\n"
        "        return 5\n"
        "    if low(9) != 9\n"
        "        return 6\n"
        "    return 42\n"
    )
    src = tmp_path / "arms.ritz"
    src.write_text(source)
    ll = tmp_path / "arms.ll"
    exe = tmp_path / "arms"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    build = run_ritz0([str(src), "-o", str(ll)], env=env, timeout=300)
    assert build.returncode == 0, build.stderr
    link = fast_link.clang(
        ["clang", str(ll), "-o", str(exe), "-nostdlib"],
        capture_output=True, text=True, timeout=300,
    )
    assert link.returncode == 0, link.stderr
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == 42, f"case {run.returncode} gave the wrong answer"
