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

THE RULE THESE TESTS PIN, AND THE ONE THEY REJECT

The tempting fix is "an untyped literal adopts the other operand's type". That
is WRONG, and `test_a_widening_target_keeps_64_bit_arithmetic` is the test that
says so. Consider:

    let big: i64 = x * 1000             # x: u32

Today that multiplies in 64 bits and cannot overflow. Under the sibling-operand
rule it would multiply in 32 bits and silently wrap — a real behaviour change,
in the direction of data loss, invisible to every existing test.

The rule pinned here instead is: **an untyped integer literal takes the
expected (declared/contextual) type.** It fixes `let q: u32 = x + 1` and leaves
`let big: i64 = x * 1000` alone, because in the first case the declared type is
u32 and in the second it is i64.

Narrowing is safe in the first case for a reason worth stating: for `+ - * <<
& | ^`, `trunc(op(zext a, zext b))` is congruent to `op(a, b)` mod 2**n, and the
existing IR *already* truncates — so the high bits it computes are provably
discarded. The tests assert the IR shape rather than just the exit code,
because a test that only checked "it compiles" would have passed before the fix.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"


def _emit_ir(tmp_path, source):
    """Compile a source fragment and return its LLVM IR text."""
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    out = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(out), "--no-runtime"],
        capture_output=True, text=True, env=env, timeout=300,
    )
    assert proc.returncode == 0, (
        f"compile failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    return out.read_text()


def _body(ir_text, fn_name):
    """Return the instruction lines of one function, debug metadata stripped."""
    m = re.search(
        r'define [^\n]*@"%s"[^\n]*\n\{\n(.*?)\n\}' % re.escape(fn_name),
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
# The hazard. This is the test that rejects the obvious-but-wrong fix.
# --------------------------------------------------------------------------

@pytest.mark.unit
def test_a_widening_target_keeps_64_bit_arithmetic(tmp_path):
    """`let big: i64 = x * 1000` must NOT be computed in 32 bits.

    This is the whole reason the rule keys off the *declared* type and not
    the sibling operand. Under a sibling-operand rule the literal would
    become u32, the multiply would happen in 32 bits, and a large `x` would
    silently wrap before being widened — data loss that no existing test
    would catch.
    """
    ir_text = _emit_ir(tmp_path, (
        "fn widen_mul(x: u32) -> i64\n"
        "    let big: i64 = x * 1000\n"
        "    return big\n"
    ))
    body = _body(ir_text, "widen_mul")
    assert any("mul i64" in line for line in body), (
        f"multiply must happen in 64 bits when the target is i64: {body}"
    )
    assert any(re.search(r"\b[zs]ext i32 .* to i64", line) for line in body), (
        f"the u32 operand must be widened before the multiply: {body}"
    )


@pytest.mark.unit
def test_a_widening_shift_keeps_64_bit_arithmetic(tmp_path):
    """Same hazard, shift form: `x << 20` into an i64 must not lose bits."""
    ir_text = _emit_ir(tmp_path, (
        "fn widen_shl(x: u32) -> i64\n"
        "    let big: i64 = x << 20\n"
        "    return big\n"
    ))
    body = _body(ir_text, "widen_shl")
    assert any("shl i64" in line for line in body), (
        f"shift must happen in 64 bits when the target is i64: {body}"
    )


@pytest.mark.unit
def test_the_declared_type_does_not_leak_into_a_call_argument(tmp_path):
    """A nested call argument is consumed at the PARAMETER's type.

    This is a regression test for a defect introduced by the first version of
    the #1396 fix itself, and found only by probing the positions the ticket
    listed as unmeasured.

        fn takes64(v: i64) -> u32
        let q: u32 = takes64(x * 1000)      # x: u32

    `self.expected_ritz_type` is ambient across the whole initialiser and does
    not narrow as emission descends, so `u32` leaked into the argument: the
    multiply was emitted as `mul i32` and WRAPPED, then the wrapped value was
    sign-extended to the i64 the parameter wanted. Silent data loss, in code
    that previously could not overflow.

    The value only adopts the declared width while it is reachable from the
    declared expression through arithmetic — a Call, Index, Field or Cast
    boundary stops it.
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
    assert any("mul i64" in line for line in body), (
        "the multiply feeds an i64 parameter and must happen in 64 bits; "
        f"the declared u32 leaked into the argument: {body}"
    )
    assert not any("mul i32" in line for line in body), (
        f"argument wrapped at 32 bits before being widened: {body}"
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
    build = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(ll)],
        capture_output=True, text=True, env=env, timeout=300,
    )
    assert build.returncode == 0, build.stderr
    # -nostdlib matches build.py: ritz0 emits its own `_start`.
    link = subprocess.run(
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
    proc = subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "toobig.ll"), "--no-runtime"],
        capture_output=True, text=True, env=env, timeout=300,
    )
    assert proc.returncode != 0, "a literal that cannot fit was accepted"
    combined = proc.stdout + proc.stderr
    assert re.search(r"[\w./-]+\.ritz:\d+:\d+:", combined), (
        f"rejection carries no location:\n{combined}"
    )
    assert "Traceback" not in combined, (
        f"rejection arrived as a Python traceback:\n{combined}"
    )
