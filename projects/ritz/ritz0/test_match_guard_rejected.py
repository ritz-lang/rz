#!/usr/bin/env python3
"""Match-arm guards (`n if n == 4 => ...`) are rejected (AGAST #1939).

ritz0 used to parse a guard into `MatchArm.guard`, but the emitter never read
it: `match k / n if n == 4 => 1 / _ => 0` lowered to an unconditional jump to
arm 0, so `f(8)` returned 1. That was a silent miscompile.

Guards are not in docs/LANGUAGE_SPEC.md, and ritz1 does not parse them.
Whether to add them is a language decision. Until then ritz0 must refuse the
syntax with a diagnostic that names it, not compile it to the wrong program.
"""

import os
from pathlib import Path

import pytest

from parser import ParseError, parse
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent

# The #1939 repro: the guard must never be ignored.
GUARDED_MATCH = """\
fn f(k: i64) -> i64
    match k
        n if n == 4 => 1
        _ => 0

fn main() -> i32
    if f(8) == 0
        return 0
    1
"""

# A guard on a multiline arm goes through the same parse path.
GUARDED_MULTILINE_ARM = """\
fn f(k: i64) -> i64
    match k
        n if n > 0 =>
            return 1
        _ => 0
"""

# Unguarded binding arm: must still parse (the rejection must not catch
# `if` anywhere else in an arm).
UNGUARDED_ARM_WITH_IF_BODY = """\
fn f(k: i64) -> i64
    match k
        n =>
            if n == 4
                return 1
            return 0
"""


@pytest.mark.unit
@pytest.mark.parametrize("source", [GUARDED_MATCH, GUARDED_MULTILINE_ARM])
def test_parser_rejects_match_guard(source):
    with pytest.raises(ParseError, match="match-arm guards"):
        parse(source)


@pytest.mark.unit
def test_parser_accepts_unguarded_arm_with_if_in_body():
    mod = parse(UNGUARDED_ARM_WITH_IF_BODY)
    assert mod.items[0].name == "f"


@pytest.mark.integration
def test_ritz0_refuses_to_compile_match_guard(tmp_path):
    src = tmp_path / "unit.ritz"
    src.write_text(GUARDED_MATCH)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    result = run_ritz0([str(src), "-o", str(tmp_path / "unit.ll")], env=env)
    assert result.returncode != 0, (
        "ritz0 compiled a guarded match arm; the guard is silently dropped"
    )
    assert "match-arm guards" in result.stderr, result.stderr
    assert not (tmp_path / "unit.ll").exists()
