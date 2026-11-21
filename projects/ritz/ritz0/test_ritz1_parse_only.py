"""RITZ1_PARSE_ONLY / `--parse-only` stops after the parse (AGAST #4379).

#4374's FIRST-set dispatch changed how long a parse takes, and the only way to
measure that before was a throwaway patch to main.ritz: an early return right
after `parse_program`.  The mode is now supported: it lexes and parses (the
alias second pass included), prints the wall time to stderr, and exits 0
before anything reads the AST.

PROGRAM below is syntactically valid but refused by Sema (an arity error,
call_check).  Compiling it normally must fail, and under the mode must
succeed with no .ll written -- that pair is what pins "the mode stops before
Sema/emit" rather than merely "it exits 0".
"""

import os
import re
import subprocess

import pytest

# Every test runs a compiler process (AGAST #1805).
pytestmark = pytest.mark.integration

PROGRAM = """\
fn f(a: i32) -> i32
    a

fn main() -> i32
    f(1, 2)
"""

REFUSAL = "called with 2 argument(s) but defined with 1"

# The timing line RITZ1_PARSE_ONLY prints on stderr.
TIMING = re.compile(r"^ritz1 parse-only: path=.+ lex_ns=\d+ parse_ns=\d+$", re.M)


def _run(ritz1_bin, tmp_path, env_extra=None, extra_args=()):
    src = tmp_path / "main.ritz"
    src.write_text(PROGRAM)
    out = tmp_path / "main.ll"
    # Drop an inherited RITZ1_PARSE_ONLY so "unset" really is unset.
    env = {k: v for k, v in os.environ.items() if k != "RITZ1_PARSE_ONLY"}
    env.update(env_extra or {})
    cmd = [str(ritz1_bin), str(src), "-o", str(out), *extra_args]
    proc = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    return proc, out


def _detail(proc):
    return f"stdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"


def test_the_program_is_refused_without_the_mode(ritz1_bin, tmp_path):
    """The premise: this source parses but Sema refuses it."""
    proc, out = _run(ritz1_bin, tmp_path)
    assert proc.returncode != 0, _detail(proc)
    assert REFUSAL in proc.stderr, _detail(proc)
    assert not out.exists()
    assert "parse-only:" not in proc.stderr


def test_env_stops_after_the_parse(ritz1_bin, tmp_path):
    """RITZ1_PARSE_ONLY=1: the Sema error is never reached, exit 0, no IR."""
    proc, out = _run(ritz1_bin, tmp_path, {"RITZ1_PARSE_ONLY": "1"})
    assert proc.returncode == 0, _detail(proc)
    assert REFUSAL not in proc.stderr, _detail(proc)
    assert not out.exists(), "parse-only wrote IR"
    assert TIMING.search(proc.stderr), _detail(proc)


def test_flag_spelling_stops_after_the_parse(ritz1_bin, tmp_path):
    """`--parse-only` is the same mode as RITZ1_PARSE_ONLY=1."""
    proc, out = _run(ritz1_bin, tmp_path, extra_args=("--parse-only",))
    assert proc.returncode == 0, _detail(proc)
    assert REFUSAL not in proc.stderr, _detail(proc)
    assert not out.exists(), "parse-only wrote IR"
    assert TIMING.search(proc.stderr), _detail(proc)


def test_zero_is_a_no_op(ritz1_bin, tmp_path):
    """RITZ1_PARSE_ONLY=0 compiles as if unset -- no behaviour change."""
    proc, out = _run(ritz1_bin, tmp_path, {"RITZ1_PARSE_ONLY": "0"})
    assert proc.returncode != 0, _detail(proc)
    assert REFUSAL in proc.stderr, _detail(proc)
    assert "parse-only:" not in proc.stderr
