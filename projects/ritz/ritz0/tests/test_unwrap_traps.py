#!/usr/bin/env python3
"""AGAST #4603: the built-in `unwrap()` traps on None / Err on every compiler.

ritz0 lowers `Option<T>.unwrap()` / `Result<T, E>.unwrap()` to a tag check
that branches to `llvm.trap` (SIGILL) when the value isn't Some / Ok
(emitter_llvmlite `_try_emit_enum_unwrap_method`).  ritz1 loaded the payload
without looking at the tag, so `None.unwrap()` handed back 0 and the program
carried on: the two compilers disagreed on what a program does.

TRAPS rows must die with SIGILL on all three compilers; VALUES rows unwrap a
Some / Ok and must exit with the payload-derived code.  Each payload shape
ritz1 loads differently (a scalar, a struct) has a row on both sides.
"""

import signal
import subprocess

import pytest

from test_ref_into_value import COMPILERS, _compile, _link

pytestmark = pytest.mark.integration

PRELUDE = """\
struct P
    a: i32
    b: i32

fn none_i() -> Option<i32>
    None

fn some_i() -> Option<i32>
    Some(37)

fn err_i() -> Result<i32, i32>
    Err(9)

fn ok_i() -> Result<i32, i32>
    Ok(40)

fn none_p() -> Option<P>
    None

fn some_p() -> Option<P>
    Some(P { a: 20, b: 22 })

"""

# main's body: each returns `v + 5` (or the struct's sum) when unwrap yields.
TRAPS = {
    "option_none_scalar": "    let v: i32 = none_i().unwrap()\n    v + 5\n",
    "result_err_scalar": "    let v: i32 = err_i().unwrap()\n    v + 5\n",
    "option_none_struct": "    let p: P = none_p().unwrap()\n    p.a + p.b\n",
    "option_none_local": "    let o: Option<i32> = none_i()\n    let v: i32 = o.unwrap()\n    v + 5\n",
}

VALUES = {
    "option_some_scalar": ("    let v: i32 = some_i().unwrap()\n    v + 5\n", 42),
    "result_ok_scalar": ("    let v: i32 = ok_i().unwrap()\n    v + 2\n", 42),
    "option_some_struct": ("    let p: P = some_p().unwrap()\n    p.a + p.b\n", 42),
    "option_some_local": ("    let o: Option<i32> = some_i()\n    let v: i32 = o.unwrap()\n    v + 5\n", 42),
}


def _exit_code(compiler, tmp_path, name, body):
    src = PRELUDE + "fn main() -> i32\n" + body
    comp, ll, work = _compile(compiler, tmp_path, name, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused {name}:\n{src}\n{out[-2000:]}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: {name} would not link:\n{link.stderr[-2000:]}"

    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(TRAPS))
def test_unwrap_of_none_or_err_traps(tmp_path, compiler, name):
    got = _exit_code(compiler, tmp_path, name, TRAPS[name])
    assert got == -signal.SIGILL, f"{compiler}: {name} exited {got}, wanted SIGILL (llvm.trap)"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(VALUES))
def test_unwrap_of_some_or_ok_yields_the_payload(tmp_path, compiler, name):
    body, want = VALUES[name]
    assert _exit_code(compiler, tmp_path, name, body) == want
