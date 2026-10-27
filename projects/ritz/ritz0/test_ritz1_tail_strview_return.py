"""Regression tests for AGAST #1643: ritz1 returning a string literal as the
TAIL expression of a `-> StrView` fn or method.

A bare `"..."` lowers to `%Span$u8`. `return "yes"` already went through the
#168 layout-equivalence coercion (emit_return rebuilds the `{ ptr, i64 }`
aggregate as `%StrView`), but the implicit tail-expression return in the
emit_fn / emit_impl_method epilogue did not, so

    fn yes_no(b: bool) -> StrView
        if b
            return "yes"
        "no"

emitted `ret %StrView %.12` with `%.12` an `insertvalue %Span$u8`, and clang
rejected the IR. This blocked examples/tier2_stdlib/77_args under ritz1.

Each program returns 42 when correct and a distinct small code naming the check
that failed otherwise. ritz0 is the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EXPECTED = 42


# `n` (110) and `o` (111) are checked through the pointer so a tail that
# returned the wrong literal, not just the wrong type, is caught too.
PROGRAMS = {
    # The ticket's repro (77_args `yes_no`): early `return`, tail literal.
    "a_fn_tail_literal": """\
import ritzlib.strview

fn yes_no(b: bool) -> StrView
    if b
        return "yes"
    "no"

pub fn main() -> i32
    let y = yes_no(true)
    if y.len != 3
        return 1
    let n = yes_no(false)
    if n.len != 2
        return 2
    if *n.ptr != 110 or *(n.ptr + 1) != 111
        return 3
    return 42
""",
    # A body that is nothing but the tail literal.
    "b_fn_only_tail_literal": """\
import ritzlib.strview

fn name() -> StrView
    "forty-two"

pub fn main() -> i32
    let s = name()
    if *s.ptr != 102
        return 1
    s.len as i32 + 33
""",
    # The method variant: emit_impl_method has its own copy of the tail path.
    "c_method_tail_literal": """\
import ritzlib.strview

struct Flag
    on: i64

impl Flag
    fn label(self: *Flag) -> StrView
        if self.on != 0
            return "on"
        "off"

pub fn main() -> i32
    var f = Flag { on: 1 }
    let a = f.label()
    if a.len != 2
        return 1
    f.on = 0
    let b = f.label()
    if b.len != 3
        return 2
    if *b.ptr != 111
        return 3
    return 42
""",
    # A tail StrView-valued call must keep returning unchanged.
    "d_fn_tail_strview_call_unchanged": """\
import ritzlib.strview

fn inner() -> StrView
    return "abcd"

fn outer() -> StrView
    inner()

pub fn main() -> i32
    let s = outer()
    if s.len != 4
        return 1
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
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
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
def test_ritz1_tail_strview_return(ritz1_bin, tmp_path, name):
    """A tail `"..."` in a `-> StrView` fn/method returned `%Span$u8` (#1643)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
