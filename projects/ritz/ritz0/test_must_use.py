"""AGAST #2137: `[[must_use]]` fns (LANGUAGE_SPEC §17.8).

The result of a call to a `[[must_use]]` fn may not be thrown away. Both
compilers reject a discarded call with the same located diagnostic:

    t.ritz:<line>:<col>: result of [[must_use]] fn '<fn>' is discarded

A call is discarded when it is an expression statement that is not its
block's value: any statement but the last of a block, or the last statement
of a fn that returns nothing.

Why: valet's test_tls.ritz (AGAST #1903) had six void [[test]] fns that
called ritzunit's assert_eq_* as bare statements, so they could never fail.
ritzunit's `pub fn assert_*` are now `[[must_use]]`.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_attr_validation import (COMPILERS, RITZ1_BIN, RITZ_ROOT,
                                  _assert_located_error, _ir, _need)

pytestmark = pytest.mark.integration

RULE = "result of [[must_use]] fn 'check' is discarded"

# The fn every program below calls.
CHECK = """\
[[must_use]]
fn check(x: i32) -> i32
    if x == 0
        return 1
    0

"""

BARE_STMT = CHECK + """\
fn main() -> i32
    check(1)
    0
"""

VOID_TAIL = CHECK + """\
fn run()
    check(1)

fn main() -> i32
    run()
    0
"""

IN_LOOP = CHECK + """\
fn main() -> i32
    var i: i32 = 0
    while i < 3
        check(i)
        i = i + 1
    0
"""

IN_IF_BRANCH = CHECK + """\
fn main() -> i32
    var n: i32 = 0
    if n == 0
        check(n)
        n = 1
    0
"""

USED = CHECK + """\
fn first() -> i32
    check(1)

fn second() -> i32
    return check(2)

fn plain(x: i32) -> i32
    x

fn main() -> i32
    let a: i32 = check(0)
    var b: i32 = 0
    b = check(3)
    if check(4) != 0
        return 9
    plain(5)
    a + b + first() + second()
"""

ON_STRUCT = """\
[[must_use]]
struct S
    a: i32

fn main() -> i32
    0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_bare_must_use_call_is_a_located_error(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, BARE_STMT, 8, 5, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_tail_of_void_fn_discards(request, tmp_path, compiler):
    # The last line of a fn that returns nothing is not a value.
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, VOID_TAIL, 8, 5, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_discard_inside_loop_body(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, IN_LOOP, 10, 9, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_discard_inside_if_branch(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, IN_IF_BRANCH, 10, 9, RULE)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_used_results_compile(request, tmp_path, compiler):
    # let / assignment / return / condition / a non-void fn's tail use the
    # value; a plain fn's result may still be dropped.
    _need(compiler, request)
    _ir(compiler, tmp_path, USED)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_must_use_applies_to_fns_only(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, ON_STRUCT, 1, 3, "must_use",
                          "applies to fn items")


# --- ritzunit's assertions ----------------------------------------------------

RITZUNIT_SRC = RITZ_ROOT.parent / "ritzunit" / "src"

RITZUNIT_DISCARD = """\
import ritzunit.assertions

[[test]]
fn test_discards() -> i32
    assert_eq_i32(1, 2)
    0

fn main() -> i32
    0
"""

RITZUNIT_USED = """\
import ritzunit.assertions

[[test]]
fn test_uses() -> i32
    let r: i32 = assert_eq_i32(1, 1)
    if r != 0
        return r
    assert_true(1)

fn main() -> i32
    0
"""


def _compile_with_ritzunit(compiler, tmp_path, src):
    """Compile `src` with `import ritzunit.<m>` resolving to ritzunit/src."""
    farm = tmp_path / "farm"
    farm.mkdir(exist_ok=True)
    link = farm / "ritzunit"
    if not link.exists():
        link.symlink_to(RITZUNIT_SRC)
    path = tmp_path / "t.ritz"
    path.write_text(src)
    ll = tmp_path / "t.ll"
    env = dict(os.environ, RITZ_PATH=f"{farm}{os.pathsep}{RITZ_ROOT}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=tmp_path, env=env,
                         timeout=300)
    return subprocess.run([str(RITZ1_BIN), str(path), "-o", str(ll)],
                          cwd=tmp_path, env=env, capture_output=True,
                          text=True, timeout=300)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_bare_ritzunit_assert_fails_to_compile(request, tmp_path, compiler):
    # The #2137 acceptance case.
    _need(compiler, request)
    proc = _compile_with_ritzunit(compiler, tmp_path, RITZUNIT_DISCARD)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted it:\n{out}"
    assert re.search(r"t\.ritz:5:5\b", out), out
    assert "result of [[must_use]] fn 'assert_eq_i32' is discarded" in out, out


@pytest.mark.parametrize("compiler", COMPILERS)
def test_used_ritzunit_asserts_compile(request, tmp_path, compiler):
    _need(compiler, request)
    proc = _compile_with_ritzunit(compiler, tmp_path, RITZUNIT_USED)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]


def test_every_ritzunit_assert_is_must_use():
    lines = (RITZUNIT_SRC / "assertions.ritz").read_text().splitlines()
    asserts = [i for i, ln in enumerate(lines) if ln.startswith("pub fn assert_")]
    assert asserts, "no pub fn assert_* found"
    unmarked = [lines[i] for i in asserts if lines[i - 1].strip() != "[[must_use]]"]
    assert not unmarked, f"not [[must_use]]: {unmarked}"
