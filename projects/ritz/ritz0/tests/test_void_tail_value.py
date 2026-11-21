#!/usr/bin/env python3
"""A `-> void` fn's tail value is discarded, as a bare procedure's is (AGAST #4085).

`-> void` declares no value (`_is_procedure`, #2246), but the fn-tail path in
ritz0's emitter still keyed "procedure" off `fn_def.ret_type is None`.  So a
`-> void` fn (lowered to i8) whose last statement yields a value of another
type returned that value:

- `simd_storeu(...)` (a void store): `ret void %x` in an i8 fn, which clang
  rejects ("value doesn't match function result type 'i8'").  cryptosec's
  aes_*_rounds_ni carried a trailing `return` to dodge it.
- a struct-returning call: `ret %S` in an i8 fn, the same clang error.
- a bool-returning call: refused as "cannot use bool as an integer".
- an enum-returning call: refused as "expected void, found enum".

Each program is run on all three compilers: the discarded tail must not stop
the fn's side effect (`g = 3`) from reaching main's exit code.
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

# Each `p() -> void` ends in a call whose value is not void-typed; main
# returns 3 only if p ran and returned.
PROGRAMS = {
    # The ticket's repro: the tail is a void store intrinsic.
    "simd_storeu": """\
fn store_it(input: *u8, output: *u8) -> void
    let state: v2i64 = simd_loadu(input as *i64)
    simd_storeu(output as *i64, state)

pub fn main() -> i32
    var a: [16]u8
    var b: [16]u8
    a[0] = 3
    store_it(@a[0], @b[0])
    b[0] as i32
""",
    "struct_call": """\
struct S
    a: i64
    b: i64
var g: i32
fn mk() -> S
    g = 3
    S { a: 1, b: 2 }
fn p() -> void
    mk()
fn main() -> i32
    p()
    g
""",
    "bool_call": """\
var g: i32
fn t() -> bool
    g = 3
    true
fn p() -> void
    t()
fn main() -> i32
    p()
    g
""",
    "enum_call": """\
enum E
    A
    B(i64)
var g: i32
fn mk() -> E
    g = 3
    E.B(4)
fn p() -> void
    mk()
fn main() -> i32
    p()
    g
""",
}


def _compile(request, compiler, tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_void_fn_discards_its_tail_value(request, tmp_path, compiler, name):
    proc, ll = _compile(request, compiler, tmp_path, PROGRAMS[name])
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler}, {name}:\n{out[-1500:]}"
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(2, str(RITZ_START))
    built = fast_link.clang(link, cwd=tmp_path, capture_output=True, text=True)
    assert built.returncode == 0, f"{compiler}, {name}: link:\n{built.stderr[-1500:]}"
    assert subprocess.run([str(exe)], timeout=60).returncode == 3, f"{compiler}, {name}"
