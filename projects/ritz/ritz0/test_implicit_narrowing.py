#!/usr/bin/env python3
"""Implicit narrowing in a typed `let`/`var` initialiser is an error.

AGAST #1393, the decision taken in #1364 (option b), refined 2026-09-24 to
"option 1": reject a narrowing unless the compiler can PROVE it loses no bits.

    fn big() -> i64
        return 4294967301

    let n: i32 = big()     # compiled, n == 5, before this change

The #1393 corpus sweep (115 packages at c58e930) found 35 narrowing sites.
34 were lossless and one was a real bug: harland's munmap truncated a u64
physical address into an i32 and then tested it as a 0=success status (#1443).
Of the 34 lossless sites, 28 fell into two shapes the compiler can prove safe
on its own, and the rule below exempts exactly those shapes:

  * a compile-time constant expression whose value fits the declared type
    (`8 + 4`, `0 - 1`, `2 << 6`, `0x02 | 0x20`, a named `const`)
  * a mask `e & K` with a constant `K >= 0` that fits the declared type,
    whose result therefore lies in [0, K]
  * an `if`/`match` whose every arm is one of the above

Everything else needs an explicit `as T`. The rule deliberately does not try
to reason about comparisons, loop bounds or arithmetic on variables: an
`if x < 255 then x else 255` is rejected even though it happens to be safe,
and a test below pins that, so a future widening of the exemption is a
conscious act.

The accepted controls are load-bearing: without them the check could pass
every rejection test by rejecting every narrowing, including `let ok: i32 = 5`.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"

PRELUDE = """\
const SMALL: i64 = 7
const LARGE: i64 = 300
const SMALL32: i32 = 7

enum Order
    Gray
    RGB
    BGR

fn five() -> i64
    return 5

fn big() -> i64
    return 4294967301

"""
# Lines of PRELUDE, so a test can assert the diagnostic's line number.
PRELUDE_LINES = PRELUDE.count("\n")


def _compile(tmp_path, body):
    src = tmp_path / "unit.ritz"
    src.write_text(PRELUDE + body)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True, text=True, env=env, timeout=300,
    )


def _fn(stmt, params="x: i32, o: Order"):
    """Wrap one statement in a function; the statement is on line 2 of it."""
    return f"fn f({params}) -> i32\n    {stmt}\n    return 0\n"


# --------------------------------------------------------------------------
# Rejected: a narrowing the compiler cannot prove lossless.
# --------------------------------------------------------------------------

REJECTED = {
    "call_i64_into_i32":      "let n: i32 = big()",
    "var_call_i64_into_i32":  "var n: i32 = big()",
    "param_i32_into_u8":      "let n: u8 = x",
    "mask_one_past_u8":       "let n: u8 = five() & 256",
    "mask_into_signed_i8":    "let n: i8 = five() & 255",
    "const_expr_too_big_u8":  "let n: u8 = 2 << 8",
    "named_const_too_big_u8": "let n: u8 = LARGE",
    "negative_into_unsigned": "let n: u8 = 0 - 1",
    # A negative mask bounds nothing: `e & -1` is `e`.
    "negative_mask":          "let n: i8 = big() & (0 - 1)",
    # `x << 64` is poison in LLVM, not 0, so it is not a known constant.
    "shift_by_64_is_poison":  "let n: u8 = 0 << 64",
    # A sub-64-bit named constant is only trusted as the WHOLE initialiser;
    # inside an expression it is computed at its own width and could wrap.
    "narrow_const_in_expr":   "let n: i8 = SMALL32 + 1",
    # `>>`, `/`, `%` fold only for a non-negative left operand: for a negative
    # one the result depends on signedness (ashr vs lshr, sdiv vs udiv).
    "shift_right_too_big_u8": "let n: u8 = 1024 >> 1",
    "negative_shift_right":   "let n: i8 = (0 - 16) >> 2",
    "negative_division":      "let n: i8 = (0 - 16) / 4",
    "division_by_zero":       "let n: u8 = 8 / 0",
    # 16 in exact arithmetic, but the multiply wraps to 0 at 64 bits first.
    "shift_right_by_64":      "let n: u8 = 1 >> 64",
    "wrapped_before_shift":   "let n: u8 = (1 << 62) * 4 >> 60",
    "match_one_arm_runtime":  ("let n: u8 = match o\n"
                               "        Gray => 0\n"
                               "        RGB => five()\n"
                               "        BGR => 2"),
    # Safe at runtime, but only by reasoning about the comparison. Pinned as
    # rejected on purpose: the rule does not do range analysis on conditions.
    "if_bounded_by_comparison": "let n: i32 = if five() < 255 then five() else 255",
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_unprovable_narrowing_is_rejected(tmp_path, name):
    r = _compile(tmp_path, _fn(REJECTED[name]))
    assert r.returncode != 0, (
        f"{name}: `{REJECTED[name].splitlines()[0]}` compiled; it narrows "
        f"without proof and must be rejected")
    # The diagnostic itself, not just "narrow": a compiler CRASH has a
    # traceback through _check_implicit_narrowing and must not count.
    assert "implicit narrowing:" in r.stderr and "Traceback" not in r.stderr, (
        f"{name}: rejected, but not by the narrowing diagnostic:\n{r.stderr[-1500:]}")


@pytest.mark.unit
def test_diagnostic_names_both_types_suggests_as_and_is_located(tmp_path):
    r = _compile(tmp_path, _fn("let n: i32 = big()"))
    assert r.returncode != 0
    err = r.stderr
    assert "`n`" in err, err[-1500:]
    assert "`i32`" in err and "`i64`" in err, err[-1500:]
    assert "as i32" in err, err[-1500:]
    # f's statement is on line 2 of the function, after the prelude.
    assert f"unit.ritz:{PRELUDE_LINES + 2}:" in err, err[-1500:]


# --------------------------------------------------------------------------
# Accepted: provably lossless, explicit, or not a narrowing at all.
# --------------------------------------------------------------------------

ACCEPTED = {
    # Load-bearing control from #1393's acceptance list.
    "plain_literal_fits":        "let n: i32 = 5",
    "explicit_cast":             "let n: i32 = big() as i32",
    "var_explicit_cast":         "var n: i32 = big() as i32",
    # Group A: constant expressions that fit.
    "const_sum":                 "let n: i32 = 8 + 4",
    "const_negative_into_i32":   "let n: i32 = 0 - 1",
    "const_shift_fits_u8":       "let n: u8 = 2 << 6",
    "const_or_flags":            "let n: i32 = 0x02 | 0x20",
    "named_const_fits":          "let n: i8 = SMALL",
    "narrow_named_const_whole":  "let n: i8 = SMALL32",
    "var_const_sum":             "var n: i32 = 8 + 4",
    "const_shift_right":         "var n: i32 = 8 >> 0",
    "const_shift_right_u8":      "let n: u8 = 256 >> 1",
    "const_division":            "let n: i32 = 7 / 2",
    "const_remainder":           "let n: u8 = 7 % 4",
    "match_constant_arms":       ("let n: u8 = match o\n"
                                  "        Gray => 0\n"
                                  "        RGB => 1\n"
                                  "        BGR => 2"),
    "if_constant_arms":          "let n: u8 = if x > 0 then 1 else 0",
    # Group B: masks that fit.
    "mask_255_into_i32":         "let n: i32 = big() & 255",
    "mask_1_into_u8":            "let n: u8 = (big() >> 3) & 1",
    "mask_constant_on_left":     "let n: i32 = 255 & big()",
    "mask_255_into_u8":          "let n: u8 = big() & 255",
    "var_mask":                  "var n: i32 = big() & 255",
    # Not narrowings: must be untouched.
    "widening":                  "let n: i64 = x",
    "same_width_sign_change":    "let n: u64 = five()",
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_provably_lossless_or_explicit_is_accepted(tmp_path, name):
    r = _compile(tmp_path, _fn(ACCEPTED[name]))
    assert r.returncode == 0, (
        f"{name}: `{ACCEPTED[name].splitlines()[0]}` was rejected:\n{r.stderr[-1500:]}")
