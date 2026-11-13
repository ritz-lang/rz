"""AGAST #1946: ritz1 match / if arms that mix a float with a non-float.

The working cases (float arms of either width, untyped / annotated lets,
`return match`, nested matches, if-expressions) are the matrix case
ritz0/test/test_diff_match_float_arms.ritz, with ritz0 as the oracle.  This
module covers what that file cannot: paths ritz0 rejects or crashes on (#2094).
ritz0 now converts the annotated integer arm too; both compilers are checked
against each other in test_let_float_match_int_arm.py (#2027).

* An unannotated match whose integer arm comes BEFORE its first float arm.
  The phi's float type is fixed by the first float arm.  The integer arm's
  value and its `br` are already emitted by then, so it cannot be converted.
  ritz1 must say so rather than emit `phi double [ i64 ... ]`.
* A float match with a pointer arm: a diagnostic, not invalid IR.
* With a float annotation the merge type is known up front, so an integer
  arm is converted (sitofp) and the program runs.
"""

import os
import subprocess
from pathlib import Path

import fast_link
import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
# Build product, not a tracked file; see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

INT_BEFORE_FLOAT = """\
import ritzlib.option

fn f(o: Option<f64>) -> i32
    let a = match o
        None => 0
        Some(v) => v
    return 0

fn main() -> i32
    return f(None)
"""

POINTER_ARM = """\
import ritzlib.option

fn f(o: Option<f64>) -> i32
    let p: *u8 = c"x"
    let a: f64 = match o
        Some(v) => v
        None => p
    return 0

fn main() -> i32
    return f(None)
"""

ANNOTATED_INT_ARM = """\
import ritzlib.option

fn f(o: Option<f64>) -> f64
    let a: f64 = match o
        None => 2
        Some(v) => v
    return a

fn main() -> i32
    if f(None) != 2.0
        return 1
    if f(Some(2.5)) != 2.5
        return 2
    return 42
"""


def _compile(ritz1_bin: Path, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    comp = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    return comp, ll


@pytest.mark.integration
def test_int_arm_before_float_arm_is_a_diagnostic(ritz1_bin, tmp_path):
    comp, _ = _compile(ritz1_bin, tmp_path, "int_before_float", INT_BEFORE_FLOAT)
    assert comp.returncode != 0, comp.stdout + comp.stderr
    assert "match arms yield both an integer and a float value" in comp.stderr


@pytest.mark.integration
def test_pointer_arm_in_float_match_is_a_diagnostic(ritz1_bin, tmp_path):
    comp, _ = _compile(ritz1_bin, tmp_path, "pointer_arm", POINTER_ARM)
    assert comp.returncode != 0, comp.stdout + comp.stderr
    assert "match arm yields a non-numeric value" in comp.stderr


@pytest.mark.integration
def test_annotated_int_arm_is_converted(ritz1_bin, tmp_path):
    comp, ll = _compile(ritz1_bin, tmp_path, "annotated_int", ANNOTATED_INT_ARM)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    exe = tmp_path / "annotated_int"
    link = fast_link.clang(
        ["clang", str(RITZ_START), str(ll), "-o", str(exe), "-nostdlib"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert link.returncode == 0, link.stderr[-2000:]
    assert subprocess.run([str(exe)], timeout=60).returncode == 42
