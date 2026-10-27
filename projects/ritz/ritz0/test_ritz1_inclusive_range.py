"""Regression tests for AGAST #1530 item 1: ritz1 must parse and lower an
inclusive range in a for loop.

    for i in 1..=10
        s += i

ritz0 accepts `..=` (ast.Range.inclusive, lowered as `i <= end`); ritz1's
grammar only had DOTDOT, so the lexer split `..=` into `..` `=` and the
enclosing fn died with `cannot parse item`.  It was the only parse blocker
of the known-failure example tier5_async_66_for_loops.

The fix adds a DOTDOTEQ token and a `FOR IDENT IN expr DOTDOTEQ expr block`
production that builds STMT_FOR with for_inclusive = 1; emitter_stmt lowers
that bound with `icmp sle` instead of `icmp slt`, and monomorph's clone_stmt
carries the flag into generic instantiations.

ritz0 is the oracle: each program's expected exit code is checked against
both compilers.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file (see test_ritz1_ptr_arith_chain.py).
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


# --- programs: name -> (source, expected exit code) ---------------------------

PROGRAMS = {
    # #1530's minimal repro.
    "repro_sum_1_to_10": (
        """\
fn main() -> i32
    var s: i32 = 0
    for i in 1..=10
        s += i
    return s
""",
        55,
    ),
    # Guard: the exclusive form must keep its `<` bound (1+..+9).
    "exclusive_unchanged": (
        """\
fn main() -> i32
    var s: i32 = 0
    for i in 1..10
        s += i
    return s
""",
        45,
    ),
    # start == end runs exactly once for `..=` (and zero times for `..`).
    "single_iteration": (
        """\
fn main() -> i32
    var n: i32 = 0
    for i in 5..=5
        n += 10
    for i in 5..5
        n += 1
    return n
""",
        10,
    ),
    # start > end runs zero times.
    "empty_range": (
        """\
fn main() -> i32
    var n: i32 = 7
    for i in 6..=5
        n += 1
    return n
""",
        7,
    ),
    # Non-literal bounds reaching the end value (2..=12 minus 5 = 72), plus
    # continue and break inside inclusive loops (+1+2).
    "expr_bounds_break_continue": (
        """\
fn lo() -> i32
    2

fn main() -> i32
    var s: i32 = 0
    let hi: i32 = 4
    for i in lo()..=hi * 3
        if i == 5
            continue
        s += i
    for i in 1..=100
        if i == 3
            break
        s += i
    return s
""",
        75,
    ),
    # Generic instantiation: monomorph's clone must keep the inclusive flag.
    "generic_clone": (
        """\
fn count<T>(x: T, n: i32) -> i32
    var c: i32 = 0
    for i in 1..=n
        c += 1
    return c

fn main() -> i32
    count<i32>(0, 6) * 10 + count<i64>(0, 3)
""",
        63,
    ),
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)]
        comp = subprocess.run(
            cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
        )
    return comp, ll, work


def _run(compiler: str, tmp_path: Path, name: str):
    """Compile PROGRAMS[name] with `compiler`, link and run it; return the process."""
    program, _ = PROGRAMS[name]
    comp, ll, work = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)


def _check(proc, name: str) -> None:
    want = PROGRAMS[name][1]
    assert proc.returncode == want, (
        f"{name}: exit {proc.returncode}, want {want}, stdout={proc.stdout!r}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    _check(_run("ritz0", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_inclusive_range(ritz1_bin, tmp_path, name):
    """AGAST #1530 item 1. Before the fix the `..=` programs died with
    `cannot parse item`."""
    _check(_run("ritz1", tmp_path, name), name)
