#!/usr/bin/env python3
"""A match whose value nothing reads has no value, so its arms needn't agree
(AGAST #4928).

rzsh's `on_history_down` ended a fn with no return type in a match whose
arms were a `Result<(), Errno>` call and an `i64` one. ritz0 ran it; ritz1
built a phi over the arms anyway, typed by the first (`phi %Result$unit_Errno
[ %.11 ... ]` over an i64), which clang refused. The value of a match that is
a statement (one not last in its block) or the tail of a fn with no return
type is read by nothing: ritz1 now joins its arms with no phi, as it does
for a void-call arm (AGAST #1654).

Every row runs on ritz0, ritz1 and ritz1_selfhosted.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = (
    "struct P\n    a: i64\n    b: i64\n"
    "var g: i64 = 0\n"
    "fn pair() -> P\n    g = g + 1\n    P { a: 1, b: 2 }\n"
    "fn num() -> i64\n    g = g + 10\n    3\n"
)

# name -> (source, exit code)
ROWS = {
    # The tail of a fn with no return type.
    "void_fn_tail": (
        PRELUDE
        + "fn f(c: i32)\n    match c\n        0 => pair()\n        _ => num()\n"
        "fn main() -> i32\n    f(0)\n    f(1)\n    g as i32\n", 11),
    # ...of a method with none.
    "void_method_tail": (
        PRELUDE
        + "struct S\n    k: i32\n"
        "impl S\n    fn f(self: @S)\n        match self.k\n"
        "            0 => pair()\n            _ => num()\n"
        "fn main() -> i32\n    let s: S = S { k: 0 }\n    s.f()\n"
        "    let t: S = S { k: 1 }\n    t.f()\n    g as i32\n", 11),
    # A match statement with a statement after it, in a fn with a value.
    "statement_before_tail": (
        PRELUDE
        + "fn f(c: i32) -> i32\n    match c\n        0 => pair()\n        _ => num()\n"
        "    7\n"
        "fn main() -> i32\n    f(0) + f(1) + g as i32\n", 25),
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    return proc, ll


# ROWS are table rows of one test per compiler (the suite's case cap,
# docs/TESTING.md): every row runs, and each failing row is named.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_discarded_match_needs_no_common_arm_type(request, tmp_path, compiler):
    failed = []
    for name in sorted(ROWS):
        source, code = ROWS[name]
        work = tmp_path / name
        work.mkdir()
        proc, ll = _compile(request, compiler, work, source)
        if proc.returncode != 0:
            failed.append(f"{name}: refused:\n{(proc.stdout + proc.stderr)[-800:]}")
            continue
        exe = work / "unit"
        link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
        if compiler != "ritz0":
            link.insert(3, str(RITZ_START))
        fast_link.clang(link, check=True)
        got = subprocess.run([str(exe)], timeout=60).returncode
        if got != code:
            failed.append(f"{name}: exit {got}, want {code}")
    assert failed == [], f"{compiler}:\n" + "\n".join(failed)
