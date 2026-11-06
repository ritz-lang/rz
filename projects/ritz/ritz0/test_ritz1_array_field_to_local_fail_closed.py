"""AGAST #2035 — a whole inline array field read into a local array
(`let a: [N]T = x.f`, `a = x.f`) is copied by ritz1 when the length and element
type match; ritz0/test/test_issue_array_field_whole_assign.ritz covers that
through the matrix.

Anything else must fail closed with a diagnostic.  Before #2035 every shape here
compiled with exit 0 and emitted `store i64 <[N x T]>` (or a scalar into an
array slot), which only clang caught.  None of these programs is valid Ritz;
ritz0 rejects five and wrongly accepts one (KNOWN_RITZ0_GAPS, AGAST #2090).
"""

import os
import subprocess
from pathlib import Path

import pytest

from array_rules import ELEMENT_MISMATCH
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

PRELUDE = """\
struct Wide
    vals: [2]i64
    small: [2]i32
    tail: i64

"""

LEN = "array length does not match the local array's length"
ELEM = ELEMENT_MISMATCH
NOT_ARRAY = "whole-array read into a local array from this member"

# name -> (body of main, diagnostic substring)
CASES = {
    "let_len_mismatch": (
        "    let a: [3]i64 = w.vals\n",
        LEN,
    ),
    "assign_len_mismatch": (
        "    var a: [3]i64 = [0, 0, 0]\n    a = w.vals\n",
        LEN,
    ),
    "let_elem_mismatch": (
        "    let a: [2]i64 = w.small\n",
        ELEM,
    ),
    "assign_elem_mismatch": (
        "    var a: [2]i64 = [0, 0]\n    a = w.small\n",
        ELEM,
    ),
    "let_scalar_field": (
        "    let a: [2]i64 = w.tail\n",
        NOT_ARRAY,
    ),
    "assign_scalar_field": (
        "    var a: [2]i64 = [0, 0]\n    a = w.tail\n",
        NOT_ARRAY,
    ),
}

# ritz0 accepts these without a type error (AGAST #2090).  Strict xfail: once
# ritz0 rejects one, its entry must be removed here.
KNOWN_RITZ0_GAPS = {"let_len_mismatch"}


def _program(body: str) -> str:
    return (
        PRELUDE
        + "pub fn main() -> i32\n"
        + "    var w: Wide = Wide { vals: [1, 2], small: [3, 4], tail: 5 }\n"
        + body
        + "    0\n"
    )


def _compile(compiler: str, tmp_path: Path, name: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(_program(CASES[name][0]))
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        proc = subprocess.run(
            [str(RITZ1_BIN), str(src), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize(
    "name",
    [
        pytest.param(
            n,
            marks=pytest.mark.xfail(
                strict=True, reason="AGAST #2090: ritz0 misses this type error"
            ),
        )
        if n in KNOWN_RITZ0_GAPS
        else n
        for n in sorted(CASES)
    ],
)
def test_ritz0_rejects(tmp_path, name):
    """The oracle: none of these programs is valid Ritz."""
    proc, _ = _compile("ritz0", tmp_path, name)
    assert proc.returncode != 0, f"ritz0 accepted {name}; the oracle moved"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_fails_closed(ritz1_bin, tmp_path, name):
    proc, ll = _compile("ritz1", tmp_path, name)
    out = proc.stdout + proc.stderr
    diagnostic = CASES[name][1]
    assert proc.returncode != 0, f"ritz1 accepted {name}:\n{out[-2000:]}"
    assert diagnostic in out, f"missing diagnostic {diagnostic!r}:\n{out[-2000:]}"
    assert not ll.exists(), "ritz1 must refuse to write output on an emit error"
