"""AGAST #1654 / #1468: a ritz1 `match` with a void-call arm emits no phi.

ritz1 built `phi i64 [ %.0, %L1 ], ...` at match.end for every match. A void
call's emit_expr result is register 0, which is never defined, so clang
rejected the module. The runtime cases are in the matrix
(ritz0/test/test_diff_match_void_arms.ritz, ritz0 as the oracle). This module
checks what a runtime test can't: there is no phi at all, not just a
well-formed one (a `phi i64 [ 0, .. ]` placeholder would also run).
"""

import os
import re
import subprocess
from pathlib import Path

import fast_link
import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent

# The ticket's repro.
VOID_ARMS = """\
import ritzlib.option

fn get() -> Option<i32>
    None

fn say(x: i32)
    pass

fn main() -> i32
    var next: Option<i32> = get()
    match next
        Some(e) => say(e)
        None => say(0)
    0
"""

# A void arm next to a StrView-valued arm: before the fix this also typed a
# `%StrView` phi whose incoming value from the void arm was %.0.
VOID_AND_STRUCT_ARMS = """\
import ritzlib.option

fn say(x: i32)
    pass

fn pick(o: Option<StrView>) -> i32
    match o
        Some(s) => s
        None => say(0)
    0

fn main() -> i32
    pick(None)
"""

# A void-arm match as the tail of a void procedure (#1468).
VOID_PROC_TAIL = """\
import ritzlib.option

fn say(x: i32)
    pass

fn tail(o: Option<i32>)
    match o
        Some(e) => say(e)
        None => pass

fn main() -> i32
    tail(None)
    0
"""


def _fn_body(ll: str, name: str) -> str:
    m = re.search(r"^define [^\n]*@" + re.escape(name) + r"\(.*?^}", ll, re.S | re.M)
    assert m, f"no definition of @{name} in the IR"
    return m.group(0)


def _compile(ritz1_bin: Path, tmp_path: Path, name: str, program: str) -> str:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    comp = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300,
    )
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    # clang accepts the module (it rejected `%.0` before the fix).
    obj = tmp_path / f"{name}.o"
    cc = fast_link.clang(
        ["clang", "-c", str(ll), "-o", str(obj)],
        capture_output=True, text=True,
    )
    assert cc.returncode == 0, cc.stderr[-2000:]
    return ll.read_text()


@pytest.mark.integration
@pytest.mark.parametrize(
    "name,program,fn",
    [
        ("void_arms", VOID_ARMS, "main"),
        ("void_and_struct_arms", VOID_AND_STRUCT_ARMS, "pick"),
        ("void_proc_tail", VOID_PROC_TAIL, "tail"),
    ],
)
def test_void_arm_match_emits_no_phi(ritz1_bin, tmp_path, name, program, fn):
    body = _fn_body(_compile(ritz1_bin, tmp_path, name, program), fn)
    assert " phi " not in body, body
    assert "%.0" not in body, body
