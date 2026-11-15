"""A match arm that is an endless `loop` contributes no type (AGAST #3270).

The arm leaves only by `return`, so control never reaches the match's merge
from it. ritz0 branched the loop's dead exit block to the merge as a live arm
with no value, which made the match read as a statement:

* an integer match in a `-> T` tail was refused as "trailing expression
  produces no value" (test_fn_tail_requires_value.py has those rows), and
* an enum or union match next to an arm with a value fell back to a dummy
  `i32 0`, so `f(E.A)` below silently returned 0 instead of 7.

One row per match emitter (integer, enum, union), each run so the value is
the one checked, not just that it compiles. ritz1 has no unions.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

_LOOP_ARM = ("            loop\n"
             "                if n > 1\n"
             "                    return 2\n")

# name -> (source, exit code). Each `main` takes the value arm.
PROGRAMS = {
    "integer_match": (
        "fn f(n: i64) -> i64\n"
        "    match n\n"
        "        0 => 7\n"
        "        _ =>\n" + _LOOP_ARM
        + "fn main() -> i32\n"
        "    f(0) as i32\n", 7),
    "enum_match": (
        "enum E\n"
        "    A\n"
        "    B(i64)\n"
        "fn f(e: E, n: i64) -> i64\n"
        "    match e\n"
        "        A => 7\n"
        "        B(v) =>\n" + _LOOP_ARM
        + "fn main() -> i32\n"
        "    f(E.A, 0) as i32\n", 7),
    "enum_match_in_an_unsafe_block": (
        "enum E\n"
        "    A\n"
        "    B(i64)\n"
        "fn f(e: E, n: i64) -> i64\n"
        "    match e\n"
        "        A => 7\n"
        "        B(v) =>\n"
        "            unsafe\n"
        "                loop\n"
        "                    if n > 1\n"
        "                        return 2\n"
        "fn main() -> i32\n"
        "    f(E.A, 0) as i32\n", 7),
}

RITZ0_ONLY = {
    "union_match": (
        "type U = i64 | bool\n"
        "fn f(x: U, n: i64) -> i64\n"
        "    match x\n"
        "        i64 => 7\n"
        "        bool =>\n" + _LOOP_ARM
        + "fn main() -> i32\n"
        "    let x: U = 42 as U\n"
        "    f(x, 0) as i32\n", 7),
}


def _run(compiler, tmp_path, src):
    path = tmp_path / "t.ritz"
    path.write_text(src)
    ll = tmp_path / f"t_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
        objs = [str(ll)]
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
        objs = [str(RITZ_START), str(ll)]
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected:\n{src}\n{out}"
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                            "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_the_value_arm_of_a_match_with_an_endless_loop_arm(tmp_path, compiler, name):
    src, want = PROGRAMS[name]
    assert _run(compiler, tmp_path, src) == want


@pytest.mark.parametrize("name", sorted(RITZ0_ONLY))
def test_the_value_arm_of_a_union_match_with_an_endless_loop_arm(tmp_path, name):
    src, want = RITZ0_ONLY[name]
    assert _run("ritz0", tmp_path, src) == want
