#!/usr/bin/env python3
"""A match's merge phi must not take its type from whichever arm comes first.

AGAST #1653 (found while doing #1476, ritzlib/tests/test_fs_stat.ritz):

    fn err_of(r: *Result<Stat, i32>) -> i32
        match *r
            Ok(_) => 0
            Err(e) => e

ritz0 typed the phi from the first arm. The untyped literal `0` is an i64
constant, so it emitted `phi i64 [0, %arm0], [%.20, %arm1]` with `%.20` an
i32, and clang rejected it ("'%.20' defined with type 'i32' but expected
'i64'"). Swapping the arms made it compile, which is why test_fs_stat.ritz
had the arms in the "wrong" order.

The rule pinned here: an integer-literal arm takes the type of the
non-literal arms (when its value fits that type); otherwise every arm is
widened to the widest arm type, and any conversion of a non-constant value
is emitted in that arm's own block, never in the merge block (an instruction
in the merge block cannot feed a phi at the top of the same block).
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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
    """Parse *and* verify: parse alone misses phi/dominance errors."""
    return subprocess.run(
        [sys.executable, "-c",
         "import sys; import llvmlite.binding as llvm; "
         "m = llvm.parse_assembly(open(sys.argv[1]).read()); m.verify()",
         str(tmp_path / "unit.ll")],
        capture_output=True, text=True)


def _fn_ir(tmp_path, name):
    """Return the IR text of function @name."""
    ir_text = (tmp_path / "unit.ll").read_text()
    start = ir_text.index(f'@"{name}"(') if f'@"{name}"(' in ir_text \
        else ir_text.index(f"@{name}(")
    start = ir_text.rindex("define", 0, start)
    return ir_text[start:ir_text.index("\n}", start)]


def _has_phi(body, ty):
    """llvmlite prints `phi  i32` (two spaces); match any whitespace."""
    return re.search(rf"= phi\s+{ty} ", body) is not None


def _run(tmp_path):
    """Recompile unit.ritz WITH the runtime, link and run it.

    Returns the exit code, or None when clang is unavailable. `-nostdlib`
    matches build.py: ritz0 emits its own `_start`.
    """
    clang = shutil.which("clang")
    if clang is None:
        return None
    ll = tmp_path / "run.ll"
    exe = tmp_path / "run"
    env = dict(os.environ, RITZ_PATH=str(RITZ0.parent.parent))
    build = subprocess.run(
        [sys.executable, str(RITZ0), str(tmp_path / "unit.ritz"), "-o", str(ll)],
        capture_output=True, text=True, env=env, timeout=300)
    assert build.returncode == 0, build.stderr
    link = subprocess.run([clang, str(ll), "-o", str(exe), "-nostdlib"],
                          capture_output=True, text=True, timeout=300)
    assert link.returncode == 0, link.stderr
    return subprocess.run([str(exe)], capture_output=True,
                          timeout=60).returncode


def _assert_valid(tmp_path, source):
    result = _compile(tmp_path, source)
    assert result.returncode == 0, f"ritz0 failed:\n{result.stderr}"
    verify = _verify_ir(tmp_path)
    assert verify.returncode == 0, (
        f"ritz0 emitted invalid IR:\n{verify.stderr}\n\n"
        f"{(tmp_path / 'unit.ll').read_text()}")


# --- enum match (the ticket's shape) ----------------------------------------

ENUM_LITERAL_FIRST = """\
fn err_of(r: *Result<i64, i32>) -> i32
    match *r
        Ok(_) => 0
        Err(e) => e

fn main() -> i32
    let r: Result<i64, i32> = Err(7)
    err_of(@r)
"""


@pytest.mark.unit
def test_enum_match_literal_arm_first_is_valid_ir(tmp_path):
    """`Ok(_) => 0` before `Err(e) => e` (i32) must emit valid IR."""
    _assert_valid(tmp_path, ENUM_LITERAL_FIRST)


@pytest.mark.unit
def test_enum_match_literal_arm_takes_typed_arm_type(tmp_path):
    """The phi is i32 — the typed arm's type — not the literal's i64."""
    _assert_valid(tmp_path, ENUM_LITERAL_FIRST)
    body = _fn_ir(tmp_path, "err_of")
    assert _has_phi(body, "i32"), body
    assert not _has_phi(body, "i64"), body


@pytest.mark.unit
def test_enum_match_literal_arm_first_runs(tmp_path):
    _assert_valid(tmp_path, ENUM_LITERAL_FIRST)
    code = _run(tmp_path)
    if code is not None:
        assert code == 7


ENUM_WIDE_LITERAL = """\
fn pick(r: *Result<i64, i32>) -> i64
    match *r
        Ok(_) => 5000000000
        Err(e) => e

fn main() -> i32
    let r: Result<i64, i32> = Err(3)
    let v = pick(@r)
    if v == 3
        return 0
    1
"""


@pytest.mark.unit
def test_enum_match_literal_too_wide_widens_typed_arm(tmp_path):
    """A literal that does not fit i32 widens the i32 arm (in its own block)."""
    _assert_valid(tmp_path, ENUM_WIDE_LITERAL)
    body = _fn_ir(tmp_path, "pick")
    assert _has_phi(body, "i64"), body
    assert "5000000000" in body, body
    code = _run(tmp_path)
    if code is not None:
        assert code == 0


# --- integer match -------------------------------------------------------------

INTEGER_LITERAL_FIRST = """\
fn sel(n: i32, x: i32) -> i32
    match n
        0 => 0
        _ => x

fn main() -> i32
    sel(1, 9)
"""


@pytest.mark.unit
def test_integer_match_literal_arm_first_is_valid_ir(tmp_path):
    _assert_valid(tmp_path, INTEGER_LITERAL_FIRST)
    body = _fn_ir(tmp_path, "sel")
    assert _has_phi(body, "i32"), body
    code = _run(tmp_path)
    if code is not None:
        assert code == 9


# --- union match ---------------------------------------------------------------

UNION_LITERAL_ARM = """\
type IntOrStr = i32 | *u8

fn get(v: IntOrStr) -> i32
    match v
        *u8 => 0
        i32 => v as i32

fn main() -> i32
    let x: i32 = 5
    let v: IntOrStr = x as IntOrStr
    get(v)
"""


@pytest.mark.unit
def test_union_match_literal_arm_is_valid_ir(tmp_path):
    """Union match used to widen in the merge block: invalid dominance."""
    _assert_valid(tmp_path, UNION_LITERAL_ARM)
    body = _fn_ir(tmp_path, "get")
    assert _has_phi(body, "i32"), body
    code = _run(tmp_path)
    if code is not None:
        assert code == 5
