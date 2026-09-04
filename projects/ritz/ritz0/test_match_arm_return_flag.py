#!/usr/bin/env python3
"""A return inside one match arm must not suppress the function's tail.

AGAST #1321 (angelo loader/ttf.ritz). The shape:

    match font.get_table(TAG_MAXP)
        Some(data) =>
            font.num_glyphs = parse_maxp_table(data)?
        None =>
            return Err("missing required 'maxp' table")

    Ok(font)

`_emit_if` saves/restores `has_returned` per branch; the match emitters
never did. The `return` in the None arm left `has_returned = True`, so
`_emit_function_body` skipped the trailing `Ok(font)` — leaving the
match's merge block empty and unterminated: `expected instruction
opcode` at link.
"""

import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
    )


def _verify_ir(tmp_path):
    return subprocess.run(
        [sys.executable, "-c",
         "import sys; import llvmlite.binding as llvm; "
         "llvm.parse_assembly(open(sys.argv[1]).read())",
         str(tmp_path / "unit.ll")],
        capture_output=True, text=True)


RETURNING_ARM_THEN_TAIL = """\
fn get(n: i32) -> Option<i32>
    if n > 0
        Some(n)
    else
        None

fn parse(v: i32) -> Result<i32, i32>
    if v > 100
        return Err(1)
    Ok(v * 2)

fn build(n: i32) -> Result<i32, i32>
    var acc = 0
    match get(n)
        Some(v) =>
            acc = parse(v)?
        None =>
            return Err(2)
    Ok(acc)

fn main() -> i32
    match build(3)
        Ok(v) => v
        Err(_) => 1
"""


def test_returning_arm_does_not_eat_function_tail(tmp_path):
    result = _compile(tmp_path, RETURNING_ARM_THEN_TAIL)
    assert result.returncode == 0, (
        f"match-with-returning-arm shape failed to compile:\n{result.stderr}"
    )
    verify = _verify_ir(tmp_path)
    assert verify.returncode == 0, f"invalid IR: {verify.stderr}"


# Guard: when EVERY arm returns, the tail (if any) stays suppressed and the
# function must still emit valid IR.
ALL_ARMS_RETURN = """\
fn pick(n: i32) -> i32
    match n
        0 => return 10
        _ => return 20

fn main() -> i32
    pick(0) - 10
"""


def test_all_arms_return_still_valid(tmp_path):
    result = _compile(tmp_path, ALL_ARMS_RETURN)
    assert result.returncode == 0, (
        f"all-arms-return guard failed to compile:\n{result.stderr}"
    )
    verify = _verify_ir(tmp_path)
    assert verify.returncode == 0, f"invalid IR: {verify.stderr}"
