"""AGAST #4475: a byte load through `c"..."` pointer arithmetic is i8.

`*(c"_Future" + i)` lowered to an i64 add of the literal's address and
`load i64`. `*(p + i)` on a `*u8` already used `getelementptr i8` and
`load i8`. The wide load made a suffix compare in the self-hosted
compiler read past the literal (sema_future_ref_fits, #4007).

ritz0 is the oracle: both sides are `getelementptr i8` and `load i8`.
A fix that widened the `*u8` side to i64 as well would still compare
equal, so the IR assertion is the one that names the width.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

SRC = """\
fn check(got: *u8) -> i32
    var i: i32 = 0
    while i < 7
        if *(got + i) != *((c"_Future") + i)
            return 0
        i = i + 1
    return 1

pub fn main() -> i32
    return check(c"_Future")
"""


def _literal_region(ll_text: str) -> str:
    """IR from the c-string global through the compare that reads it."""
    # ritz0 quotes names (`@".str.0"`); ritz1 does not (`@.str.0`).
    start = ll_text.find(".str")
    assert start != -1, ll_text
    end = ll_text.find("icmp", start)
    assert end != -1, ll_text
    return ll_text[start:end]


def _compile(compiler: str, tmp_path: Path) -> str:
    src = tmp_path / f"{compiler}.ritz"
    src.write_text(SRC)
    ll = tmp_path / f"{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        comp = subprocess.run(
            [str(RITZ1_BIN), str(src), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return ll.read_text()


def _run(compiler: str, tmp_path: Path) -> int:
    text = _compile(compiler, tmp_path)
    region = _literal_region(text)
    assert "load i8" in region, region
    assert "load i64" not in region, region
    assert "getelementptr i8" in region, region

    ll = tmp_path / f"{compiler}.ll"
    exe = tmp_path / compiler
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        assert RITZ_START.exists(), f"runtime start object missing: {RITZ_START}"
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
def test_ritz0_cstring_index_loads_a_byte(tmp_path):
    assert _run("ritz0", tmp_path) == 1


@pytest.mark.integration
def test_ritz1_cstring_index_loads_a_byte(ritz1_bin, tmp_path):
    """AGAST #4475. Before the fix the literal side was `load i64` and the
    compare returned 0."""
    assert _run("ritz1", tmp_path) == 1
