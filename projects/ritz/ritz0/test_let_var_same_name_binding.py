"""Regression tests for AGAST #1755: a `var x` must not capture a later `let x`.

ritz0 keeps `let` bindings in `self.params` (SSA values) and `var` bindings in
`self.locals` (allocas). Neither map is block-scoped, and Ident lookup tries
`self.locals` first. So once a function had emitted `var v` anywhere, every
later `let v` -- including one in a *sibling* branch -- resolved to the var's
alloca:

    if c
        var v: i32 = f()
        v = g(v)
        return v
    else
        let v: i32 = h()
        return v          # -> load %v.addr, never stored on this path

Found in #1652, where exactly that shape inside ritz1's emit_assign made the
ritz0-built ritz1 emit `store i64 %.32, ptr @g` (%.32 undefined) for every
global scalar assignment: 67 gate failures.

The fix makes each binding replace the same-named binding of the other kind
("most recent binding wins"), which is ritz1's rule (find_local_idx scans
innermost/latest first), so the two compilers agree on the ticket's shape.

Each direction has its own test so a partial revert turns exactly one red:

  * `let` after `var`   -> _bind_let must evict self.locals
  * `var` after `let`   -> _bind_var must evict self.params (the stale let is
                           still reached by params-first lookups, e.g. the
                           enum-name lookup used by `match`)
  * `for x in arr` over an outer `var x` -> the element binding must hide the
                           var in the body and restore it after the loop

Assertions are on runtime exit codes, not IR text.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


# The ticket's shape. pick(true) = g(f()) = 11, pick(false) = h() = 20.
# Before the fix ritz0 returned 22: the else arm read the then arm's slot.
LET_AFTER_SIBLING_VAR = """\
fn f() -> i32
    return 10

fn g(x: i32) -> i32
    return x + 1

fn h() -> i32
    return 20

fn pick(c: bool) -> i32
    if c
        var v: i32 = f()
        v = g(v)
        return v
    else
        let v: i32 = h()
        return v

fn main() -> i32
    return pick(true) + pick(false)
"""

# Mirror image, already correct before the fix (locals-first lookup finds the
# else arm's var). Pinned so the fix cannot break it.
VAR_AFTER_SIBLING_LET = """\
fn pick(c: bool) -> i32
    var r: i32 = 0
    if c
        let v: i32 = 3
        r = v
    else
        var v: i32 = 1
        v = v + 6
        r = v
    return r

fn main() -> i32
    return pick(true) * 10 + pick(false)
"""

# `var x: i32` after a sibling `let x: Color`. `match x` asks for x's enum
# name, and that lookup falls through self.locals (an i32 is no enum) into
# self.params -- where the stale `let x: Color` still sat, so the i32 match
# was lowered as a Color match and ritz0 rejected the module. Expected 2 + 50.
VAR_AFTER_SIBLING_LET_ENUM = """\
enum Color
    Red
    Green

fn pick(c: bool) -> i32
    var r: i32 = 0
    if c
        let x: Color = Green
        r = match x
            Red => 1
            Green => 2
    else
        var x: i32 = 4
        x = x + 1
        r = match x
            5 => 50
            _ => 9
    return r

fn main() -> i32
    return pick(true) + pick(false)
"""

# The element binding of `for x in arr` is a let. Inside the body it must hide
# the outer `var x` (s = 1+2+3, not 3*100), and afterwards the var is back
# (x = 100). Before the fix the body read the var: 300 + 100.
FOR_ELEM_OVER_OUTER_VAR = """\
fn main() -> i32
    var x: i32 = 100
    var arr: [3]i32 = [1, 2, 3]
    var s: i32 = 0
    for x in arr
        s = s + x
    return s + x
"""


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
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
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
def test_ritz0_let_after_sibling_branch_var(tmp_path):
    """The #1755 shape: the else arm's `let v` must not read the then arm's slot."""
    assert _run("ritz0", tmp_path, "let_after_var", LET_AFTER_SIBLING_VAR) == 31


@pytest.mark.integration
def test_ritz0_var_after_sibling_branch_let(tmp_path):
    """Already-working mirror image, pinned against the fix."""
    assert _run("ritz0", tmp_path, "var_after_let", VAR_AFTER_SIBLING_LET) == 37


@pytest.mark.integration
def test_ritz0_var_after_sibling_branch_let_enum_lookup(tmp_path):
    """A `var` must evict the stale `let` that params-first lookups still see."""
    assert (
        _run("ritz0", tmp_path, "var_after_let_enum", VAR_AFTER_SIBLING_LET_ENUM) == 52
    )


@pytest.mark.integration
def test_ritz0_for_element_hides_and_restores_outer_var(tmp_path):
    assert _run("ritz0", tmp_path, "for_elem", FOR_ELEM_OVER_OUTER_VAR) == 106


@pytest.mark.integration
@pytest.mark.parametrize(
    "name,program,expected",
    [
        ("let_after_var", LET_AFTER_SIBLING_VAR, 31),
        ("var_after_let", VAR_AFTER_SIBLING_LET, 37),
    ],
)
def test_ritz1_agrees_on_sibling_branch_bindings(
    ritz1_bin, tmp_path, name, program, expected
):
    """ritz1 already got these right; ritz0 now matches it."""
    assert _run("ritz1", tmp_path, name, program) == expected
