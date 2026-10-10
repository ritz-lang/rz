"""Regression tests for AGAST #1618 (dups #1579, #1665): ritz1 must parse a
block-form `match` as the operand of `return`.

    fn f(v: i64) -> i64
        return match v
            0 => 1
            _ => 2

`return_stmt` only had `RETURN expr NEWLINE`. A block-form match ends in DEDENT
with no trailing NEWLINE, so that alternative could never match, and the whole
enclosing fn failed with

    cannot parse item starting at 'fn f'

let/var and match arms had already hit this and gained `match_expr_rhs`
alternatives (#1479). The fix gives return_stmt the same alternative.

Not covered: an inline `return` as a match-arm body (`Ok(v) => return v + 1`),
which is #1689 and needs emitter work as well as grammar.

ritz0 is the oracle. Every program exits 42 on success.

"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file (see test_ritz1_ptr_arith_chain.py).
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date so we never assert against a stale grammar."""
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the return-match tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    proc = subprocess.run(
        ["make", "-C", "runtime", RITZ_START.name],
        cwd=RITZ_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0 or not RITZ_START.exists():
        pytest.fail(
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    _build_runtime_start()
    return RITZ1_BIN


# --- programs -----------------------------------------------------------------

# #1618's repro: integer literal patterns with a wildcard.
INT_LITERAL = """\
fn f(v: i64) -> i64
    return match v
        0 => 40
        _ => 2

fn main() -> i32
    (f(0) + f(7)) as i32
"""

# #1579's repro: an Option<i32> scrutinee with a binding arm.
OPTION_I32 = """\
import ritzlib.option

fn pick(o: Option<i32>) -> i32
    return match o
        Some(v) => v + 1
        None => 0

fn main() -> i32
    pick(Some(41)) + pick(None)
"""

# #1665's repro: an Option<StrView> scrutinee, returning a StrView.
OPTION_STRVIEW = """\
import ritzlib.option
import ritzlib.strview

fn first(o: Option<StrView>) -> StrView
    return match o
        None => "(none)"
        Some(s) => s

fn main() -> i32
    let a = first(Some("Seven"))
    if a.len != 5 or *a.ptr != 83
        return 1
    let b = first(None)
    if b.len != 6 or *b.ptr != 40
        return 2
    42
"""

# `return match` in a nested block, not as the fn's last statement, so the
# statements after the DEDENT must still parse and run.
NON_TAIL = """\
fn f(flag: i64, v: i64) -> i64
    if flag == 1
        return match v
            0 => 100
            _ => 42
    let w: i64 = v + 1
    w

fn main() -> i32
    let a: i64 = f(1, 5)
    let b: i64 = f(0, 41)
    if a == 42 and b == 42
        return 42
    1
"""

# An arm of the returned match is itself a nested match (#1479's form).
NESTED = """\
fn f(a: i64, b: i64) -> i64
    return match a
        0 => match b
            0 => 42
            _ => 1
        _ => 2

fn main() -> i32
    f(0, 0) as i32
"""

# Several `return match` statements in a row inside one fn.
SEQUENTIAL = """\
fn f(a: i64, b: i64) -> i64
    if a == 0
        return match b
            0 => 10
            _ => 20
    return match b
        0 => 30
        _ => 42

fn main() -> i32
    let x: i64 = f(0, 0)
    let y: i64 = f(1, 1)
    if x == 10 and y == 42
        return 42
    1
"""

PROGRAMS = {
    "int_literal": INT_LITERAL,
    "option_i32": OPTION_I32,
    "option_strview": OPTION_STRVIEW,
    "non_tail": NON_TAIL,
    "nested": NESTED,
    "sequential": SEQUENTIAL,
}

# `return match` with no indented arms is still a syntax error.
MALFORMED = {
    "no_arms": """\
fn f(v: i64) -> i64
    return match v
    0

fn main() -> i32
    42
""",
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(RITZ_ROOT)]
    comp = subprocess.run(
        cmd, cwd=work, env=env, capture_output=True, text=True, timeout=300
    )
    return comp, ll, work


def _run(compiler: str, tmp_path: Path, name: str):
    """Compile PROGRAMS[name] with `compiler`, link and run it; return the process."""
    comp, ll, work = _compile(compiler, tmp_path, name, PROGRAMS[name])
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
    assert proc.returncode == 42, f"{name}: exit {proc.returncode}, stdout={proc.stdout!r}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    _check(_run("ritz0", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_return_match(ritz1_bin, tmp_path, name):
    """AGAST #1618. Before the fix these died with `cannot parse item`."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_malformed_return_match(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed return match {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
