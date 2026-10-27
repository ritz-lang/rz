"""Regression tests for AGAST #1454 (and the indented-block / assignment halves
of #1617): ritz1 must parse and lower a match arm whose body is an indented
block of statements, or a single assignment statement.

    match v
        Some(x) => x
        None =>
            let y: i64 = 40
            y + 2

match_arm's productions only accepted an expression (or a nested match, #1479)
after `=>`, so the whole enclosing fn failed with

    cannot parse item starting at 'fn pick'

ritzlib/os/env.ritz (env_must) was refused for this reason, and angelo has 78
such arms. The fix adds `pattern FAT_ARROW NEWLINE INDENT stmts DEDENT` and
`pattern FAT_ARROW assign_stmt`. Like an `if` branch, a block's value is its
trailing bare expression: match_arm_set_block moves it into MatchArm.body and
keeps the leading statements in MatchArm.body_stmts, which emit_match_arm_body
emits first.

ritz0 is the oracle. Every program exits 42 on success.

Option arguments are bound to typed locals before the call: a constructor
passed straight as an argument is invalid IR under ritz1 (#1498/#1570).
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


# --- programs -----------------------------------------------------------------

# The ticket's repro, verbatim: a block arm last, the match as the fn tail.
REPRO = """\
import ritzlib.option

fn pick(v: Option<i64>) -> i64
    match v
        Some(x) => x
        None =>
            let y: i64 = 40
            y + 2

fn main() -> i32
    return pick(None) as i32
"""

# A block arm FIRST, so more arms follow its DEDENT; it uses the payload
# binding, and the match is a `let` RHS rather than the tail.
FIRST_ARM_LET = """\
import ritzlib.option

fn pick(v: Option<i64>) -> i64
    let r: i64 = match v
        Some(x) =>
            let d: i64 = x * 2
            d + 2
        None => 7
    r

fn main() -> i32
    let a: Option<i64> = Some(20)
    let b: Option<i64> = None
    if pick(b) != 7
        return 1
    pick(a) as i32
"""

# Integer patterns, every arm a block, and each arm declares the same local
# name: arm-scoped locals must not leak into the next arm.
ALL_BLOCKS_SHADOW = """\
fn classify(n: i64) -> i64
    match n
        0 =>
            let k: i64 = 10
            k
        1 =>
            let k: i64 = 30
            var t: i64 = k
            t = t + 2
            t
        _ =>
            let k: i64 = 99
            k

fn main() -> i32
    let a: i64 = classify(0)
    let b: i64 = classify(1)
    if classify(5) != 99
        return 1
    (a + b) as i32
"""

# Statement-position match whose block arms only mutate state (no value).
STMT_NO_VALUE = """\
fn main() -> i32
    var acc: i64 = 0
    var i: i64 = 0
    while i < 3
        match i
            0 =>
                acc = acc + 10
                acc = acc + 4
            _ =>
                acc = acc + 14
        i = i + 1
    acc as i32
"""

# A block arm that returns early from the enclosing fn. The arm's `ret` must
# not leave the match's phi naming a block that does not branch to its end.
EARLY_RETURN = """\
import ritzlib.option

fn pick(v: Option<i64>) -> i64
    let r: i64 = match v
        Some(x) => x
        None =>
            let e: i64 = 42
            return e
    r + 100

fn main() -> i32
    let n: Option<i64> = None
    pick(n) as i32
"""

# Control flow inside a block arm: an if/else and a nested statement match.
CONTROL_FLOW_INSIDE = """\
fn f(a: i64, b: i64) -> i64
    match a
        0 =>
            var r: i64 = 0
            if b > 5
                r = 40
            else
                r = 1
            match b
                9 => r = r + 2
                _ => pass
            r
        _ => 0

fn main() -> i32
    f(0, 9) as i32
"""

# env_must's shape: a struct-valued (StrView) match whose block arm builds
# its value in a local. The phi must be typed %StrView on both arms.
STRVIEW_BLOCK = """\
import ritzlib.strview
import ritzlib.option

fn name_or_default(v: Option<StrView>) -> StrView
    match v
        Some(s) => s
        None =>
            var d: StrView = "forty-two characters of default text......"
            d

fn main() -> i32
    let n: Option<StrView> = None
    let r: StrView = name_or_default(n)
    r.len as i32
"""

# #1617's repro: assignment arm bodies (`5 => r = 5`) in a statement match.
ASSIGN_ARMS = """\
fn t(n: i64) -> i64
    var r: i64 = 0
    match n
        5 => r = 42
        _ => r = 1
    r

fn main() -> i32
    if t(4) != 1
        return 1
    t(5) as i32
"""

# A block arm in a generic fn: monomorph must clone the arm's statements.
GENERIC_BLOCK = """\
fn choose<T>(k: i64, x: T, y: T) -> T
    match k
        0 =>
            let tmp = x
            tmp
        _ => y

fn main() -> i32
    let a: i64 = choose<i64>(0, 42, 7)
    let b: i64 = choose<i64>(1, 0, 42)
    if a != b
        return 1
    a as i32
"""

PROGRAMS = {
    "repro": REPRO,
    "first_arm_let": FIRST_ARM_LET,
    "all_blocks_shadow": ALL_BLOCKS_SHADOW,
    "stmt_no_value": STMT_NO_VALUE,
    "early_return": EARLY_RETURN,
    "control_flow_inside": CONTROL_FLOW_INSIDE,
    "strview_block": STRVIEW_BLOCK,
    "assign_arms": ASSIGN_ARMS,
    "generic_block": GENERIC_BLOCK,
}

# Syntax errors that must still be rejected.
MALFORMED = {
    # `=>` then a newline with no indented block.
    "empty_block": """\
fn pick(a: i64) -> i64
    match a
        0 =>
        _ => 1

fn main() -> i32
    42
""",
    # A statement that is neither an expression nor an assignment, inline.
    "let_inline": """\
fn pick(a: i64) -> i64
    match a
        0 => let q: i64 = 1
        _ => 1

fn main() -> i32
    42
""",
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str, src_path=None):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    if src_path is None:
        src.write_text(program)
    else:
        src = src_path
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
    comp, ll, work = _compile(compiler, tmp_path, name, PROGRAMS[name])
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = work / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(
        ["timeout", "60", *link_cmd], cwd=work, capture_output=True, text=True
    )
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
def test_ritz1_block_match_arm(ritz1_bin, tmp_path, name):
    """AGAST #1454 / #1617. Before the fix these died with `cannot parse item`."""
    _check(_run("ritz1", tmp_path, name), name)


@pytest.mark.integration
def test_ritz1_compiles_os_env(ritz1_bin, tmp_path):
    """#1454 acceptance: ritz1 compiles ritzlib/os/env.ritz (env_must) standalone."""
    comp, ll, _ = _compile(
        "ritz1", tmp_path, "os_env", "", RITZ_ROOT / "ritzlib" / "os" / "env.ritz"
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"ritz1 refused ritzlib/os/env.ritz:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    assert "@env_must" in ll.read_text(), "env_must was not emitted"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz1_rejects_malformed_block_arm(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed arm {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_ritz0_rejects_malformed_block_arm(tmp_path, name):
    """Keep the malformed cases honest: the oracle rejects them too."""
    comp, _, _ = _compile("ritz0", tmp_path, name, MALFORMED[name])
    assert comp.returncode != 0, f"ritz0 accepted {name!r}; not a syntax error"
