"""Regression tests for AGAST #1479: ritz1 must parse a match arm whose body
is a nested `match` (`None => match g()` followed by indented arms).

The only match_arm production was

    match_arm : pattern FAT_ARROW arm_body NEWLINE

arm_body -> expr already includes the match expression, but that form ends in
DEDENT with no trailing NEWLINE, so the mandatory NEWLINE could never match. The
whole enclosing fn then failed with

    cannot parse item starting at 'fn f'

let/var had already hit this and gained `match_expr_rhs` alternatives. The
fix gives match_arm the same `pattern FAT_ARROW match_expr_rhs` alternative,
placed ahead of the generic one.

Not covered: block-bodied arms (`None =>` + NEWLINE + indented statements),
which are #1454. ritz1 has no block-expression node, so that one needs emitter
work as well as grammar.

ritz0 is the oracle. Every program exits 42 on success.

Option arguments are bound to typed locals before the call because a
constructor passed straight as an argument (`pick(None, Some(41))`) is invalid
IR under ritz1 whether or not a match is nested (#1498/#1570).
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
            "could not build ritz1 for the nested-match tests:\n"
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

# The ticket's repro: a statement-position match whose last arm is a nested
# match, with void arms. The ticket printed via ritzlib.io; single-file
# compilation doesn't link imported bodies, so local void fns stand in.
REPRO = """\
import ritzlib.option

fn g() -> Option<i64>
    None

fn print_int(n: i64)
    pass

fn prints_none()
    pass

fn f() -> i32
    match g()
        Some(n) => print_int(n)
        None => match g()
            Some(m) => print_int(m)
            None => prints_none()
    42

fn main() -> i32
    f()
"""

# A value-producing nested match in the LAST arm of a `let` match. The inner
# match's DEDENT and the outer one's DEDENT arrive back to back.
LET_LAST_ARM = """\
import ritzlib.option

fn pick(a: Option<i64>, b: Option<i64>) -> i64
    let r: i64 = match a
        Some(x) => x
        None => match b
            Some(y) => y + 1
            None => 0
    r

fn main() -> i32
    let a: Option<i64> = None
    let b: Option<i64> = Some(41)
    pick(a, b) as i32
"""

# The nested match in the FIRST arm, so more outer arms follow its DEDENT.
FIRST_ARM = """\
import ritzlib.option

fn pick(a: Option<i64>, b: Option<i64>) -> i64
    let r: i64 = match a
        Some(x) => match b
            Some(y) => x + y
            None => x
        None => 7
    r

fn main() -> i32
    let a1: Option<i64> = Some(40)
    let b1: Option<i64> = Some(2)
    let s: i64 = pick(a1, b1)
    let a2: Option<i64> = Some(9)
    let b2: Option<i64> = None
    let t: i64 = pick(a2, b2)
    let a3: Option<i64> = None
    let b3: Option<i64> = Some(5)
    let u: i64 = pick(a3, b3)
    if s == 42 and t == 9 and u == 7
        return 42
    1
"""

# The outer match is the fn's tail expression rather than a let RHS.
TAIL_EXPR = """\
import ritzlib.option

fn pick(a: Option<i64>, b: Option<i64>) -> i64
    match a
        Some(x) => x
        None => match b
            Some(y) => y * 2
            None => 0

fn main() -> i32
    let a: Option<i64> = None
    let b: Option<i64> = Some(21)
    pick(a, b) as i32
"""

# Two levels of nesting, on integer literal patterns.
DOUBLY_NESTED = """\
fn pick(a: i64, b: i64, c: i64) -> i64
    let r: i64 = match a
        0 => match b
            0 => match c
                0 => 42
                _ => 3
            _ => 2
        _ => 1
    r

fn main() -> i32
    pick(0, 0, 0) as i32
"""

# Plain expression and `pass` arms must keep parsing next to a nested one.
MIXED_ARMS = """\
fn main() -> i32
    let a: i64 = 40
    let b: i64 = 1
    let r: i64 = match a
        40 => a + 2
        _ => match b
            1 => 0
            _ => 1
    match b
        0 => pass
        _ => match a
            40 => pass
            _ => pass
    r as i32
"""

PROGRAMS = {
    "mixed_arms": MIXED_ARMS,
    "let_last_arm": LET_LAST_ARM,
    "first_arm": FIRST_ARM,
    "tail_expr": TAIL_EXPR,
    "doubly_nested": DOUBLY_NESTED,
}

# Parse-and-compile only. A statement match with void arms still emits a
# `phi i64` over an undefined register (#1468), which clang rejects with or
# without nesting. When #1468 lands, move these into PROGRAMS.
COMPILE_ONLY = {"repro": REPRO}

# A nested `match` with no indented arms is still a syntax error.
MALFORMED = {
    "no_inner_arms": """\
fn pick(a: i64) -> i64
    let r: i64 = match a
        0 => match a
        _ => 1
    r

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
    assert proc.returncode == 42, (
        f"{name}: exit {proc.returncode}, stdout={proc.stdout!r}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    _check(_run("ritz0", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_nested_match_arm(ritz1_bin, tmp_path, name):
    """AGAST #1479. Before the fix these died with `cannot parse item`."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(COMPILE_ONLY))
def test_ritz1_parses_void_nested_match(ritz1_bin, tmp_path, name):
    """The ticket repro. ritz1 used to refuse `fn f` with `cannot parse item`."""
    comp, ll, _ = _compile("ritz1", tmp_path, name, COMPILE_ONLY[name])
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(COMPILE_ONLY))
def test_ritz0_accepts_void_nested_match(tmp_path, name):
    comp, ll, _ = _compile("ritz0", tmp_path, name, COMPILE_ONLY[name])
    assert comp.returncode == 0 and ll.exists(), comp.stderr[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_malformed_nested_match(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed nested match {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
