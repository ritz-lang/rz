"""Regression tests for AGAST #1662: a `"..."` arm in a StrView-typed match.

A bare `"..."` lowers to `%Span$u8`. The #1645 merge phi took its type from
the first struct-valued arm, so in

    fn or_none(o: Option<StrView>) -> StrView
        match o
            Some(s) => s
            None => "(none)"

ritz1 emitted `phi %StrView [ ... ], [ %.16, %L3 ]` with `%.16` an
`insertvalue %Span$u8`, and clang rejected the IR (examples/tier2_stdlib/
77_args). With the literal arm first the phi was `%Span$u8` and the StrView
arm (and the `-> StrView` ret of the phi) disagreed instead. Each arm value is
now rebuilt to the phi's type in its own arm block (#168 layout-equiv helper),
and a literal arm yields StrView, so both arm orders produce a `%StrView` phi.

Each program returns 42 when correct and a distinct small code naming the check
that failed otherwise. ritz0 is the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EXPECTED = 42


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; a stale ritz1 asserts the old emitter (#1322)."""
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
            "could not build ritz1 for the match StrView-arm tests:\n"
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


# Byte checks through the pointer catch an arm that yielded the wrong literal,
# not just the wrong type: `(` is 40, `S` is 83, `z` is 122.
PROGRAMS = {
    # The ticket's repro (77_args `or_none`): bound arm first, literal second.
    "a_bound_then_literal": """\
import ritzlib.strview

fn or_none(o: Option<StrView>) -> StrView
    match o
        Some(s) => s
        None => "(none)"

pub fn main() -> i32
    let a = or_none(Some("Seven"))
    if a.len != 5
        return 1
    if *a.ptr != 83
        return 2
    let b = or_none(None)
    if b.len != 6
        return 3
    if *b.ptr != 40
        return 4
    return 42
""",
    # The other arm order: literal first, bound second.
    "b_literal_then_bound": """\
import ritzlib.strview

fn or_none(o: Option<StrView>) -> StrView
    match o
        None => "(none)"
        Some(s) => s

pub fn main() -> i32
    let a = or_none(Some("Seven"))
    if a.len != 5
        return 1
    if *a.ptr != 83
        return 2
    let b = or_none(None)
    if b.len != 6
        return 3
    if *b.ptr != 40
        return 4
    return 42
""",
    # Through a StrView-annotated let, both arm orders.  (`return match ...`
    # does not parse under ritz1 yet: AGAST #1665; an untyped `let v = match`
    # over struct arms mis-types the slot regardless of literals: #1666.)
    "c_let_both_orders": """\
import ritzlib.strview

fn first(o: Option<StrView>) -> StrView
    let v: StrView = match o
        None => "(none)"
        Some(s) => s
    return v

fn second(o: Option<StrView>) -> StrView
    let v: StrView = match o
        Some(s) => s
        None => "(none)"
    v

pub fn main() -> i32
    let a = first(None)
    if a.len != 6 or *a.ptr != 40
        return 1
    let b = first(Some("Seven"))
    if b.len != 5 or *b.ptr != 83
        return 2
    let c = second(None)
    if c.len != 6 or *c.ptr != 40
        return 3
    let d = second(Some("Seven"))
    if d.len != 5 or *d.ptr != 83
        return 4
    return 42
""",
    # An integer scrutinee: literal arm, then a StrView-param catch-all.
    "d_int_scrutinee_literal_then_param": """\
import ritzlib.strview

fn pick(n: i32, other: StrView) -> StrView
    match n
        0 => "zero"
        _ => other

pub fn main() -> i32
    let a = pick(0, "zz")
    if a.len != 4
        return 1
    let b = pick(1, "zz")
    if b.len != 2 or *b.ptr != 122
        return 2
    return 42
""",
    # All-literal arms in a `-> StrView` fn: the phi itself is returned.
    "e_all_literal_arms": """\
import ritzlib.strview

fn name(n: i32) -> StrView
    match n
        0 => "zero"
        _ => "many"

pub fn main() -> i32
    let a = name(0)
    let b = name(5)
    if a.len != 4 or b.len != 4
        return 1
    if *a.ptr != 122 or *b.ptr != 109
        return 2
    return 42
""",
}


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    comp = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_match_strview_literal_arm(ritz1_bin, tmp_path, name):
    """A `"..."` arm fed `%Span$u8` into a StrView match phi (#1662)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
