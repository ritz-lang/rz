"""AGAST #2972: `*h = v` on an integer or `bool` borrow `h:& T` is `h = v`.

    fn f(h:& i32) -> i32
        *h = *h + 1
        return *h

`name:& T` is a mode: `h` has type `T` and is the caller's place (spec §13.4,
"reading and writing through the parameter"), and `*h` reads as `h` (#2045). The
store now agrees with the read, on all three compilers:

- ritz0's `*ptr = val` arm evaluated `h`, the referent, and raised a Python
  ValueError ("Cannot dereference non-pointer: i32") instead of storing to the
  `_borrow_referent_slot` the read arm already uses.
- ritz1 loaded the referent, took it for an address and stored an i64 there
  (exit -11); `bool_check` called the `bool` slot `*h` an integer and refused
  `*h = true`.

A `h:& *U` borrow keeps the pointer path: `*p = v` stores through the pointer
`p` holds, not into `p`. A struct borrow stores the whole struct, as ritz1
already did (ritz0 raised the same ValueError). An `a:& [N]T` is still refused
(#2290), now located on ritz0 too, and a plain value is still refused (#2885).

Rows that also READ `*h` are strict xfails on ritz1 until #2971 (ritz1's `*h`
read of an integer borrow segfaults); their stores are right.

Every program returns its expected exit code on success.
"""

import os
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link
from array_rules import BORROW_DEREF_STORE
from ritz0_inproc import run_ritz0

pytestmark = [pytest.mark.integration, pytest.mark.batched]

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

READ_2971 = "AGAST #2971: ritz1's `*h` read of an integer or bool borrow segfaults"

# name: (program, exit code, reads `*h`)
PROGRAMS = {
    # The ticket's repro: the caller sees 3, and so does the callee's `*h`.
    "i32_repro": ("""\
fn f(h:& i32) -> i32
    *h = *h + 1
    return *h

pub fn main() -> i32
    var n: i32 = 2
    let r = f(n)
    return n * 10 + r
""", 33, True),
    "i32_store": ("""\
fn f(h:& i32, v: i32)
    *h = v

pub fn main() -> i32
    var n: i32 = 2
    f(n, 7)
    return n
""", 7, False),
    # One byte, so the store is that wide: the neighbours keep their 9s.
    "u8_store_element": ("""\
fn f(h:& u8, v: u8)
    *h = v

pub fn main() -> i32
    var a: [3]u8 = [9, 1, 9]
    f(a[1], 7)
    return (a[0] as i32) * 100 + (a[1] as i32) * 10 + (a[2] as i32) - 900
""", 79, False),
    "u8_repro": ("""\
fn f(h:& u8) -> u8
    *h = *h + 1
    return *h

pub fn main() -> i32
    var n: u8 = 2
    let r = f(n)
    return (n as i32) * 10 + (r as i32)
""", 33, True),
    "i32_compound": ("""\
fn f(h:& i32) -> i32
    *h += 1
    return *h

pub fn main() -> i32
    var n: i32 = 2
    let r = f(n)
    return n * 10 + r
""", 33, True),
    "bool_store": ("""\
fn f(h:& bool, v: bool)
    *h = v

pub fn main() -> i32
    var b: bool = false
    f(b, true)
    if b
        return 33
    return 1
""", 33, False),
    "bool_not": ("""\
fn f(h:& bool)
    *h = not *h

pub fn main() -> i32
    var b: bool = false
    f(b)
    if b
        return 33
    return 1
""", 33, True),
    "struct_store": ("""\
struct H
    i: i32
    j: i64

fn f(h:& H)
    *h = H { i: 3, j: 4 }

pub fn main() -> i32
    var x: H = H { i: 1, j: 1 }
    f(x)
    return x.i * 10 + (x.j as i32)
""", 34, False),
    # `h:& *i32`: `*p` is through the pointer p holds, as it was.
    "pointer_borrow": ("""\
fn f(p:& *i32)
    *p = 3

pub fn main() -> i32
    var x: i32 = 1
    var p: *i32 = @x
    f(p)
    return x
""", 3, False),
}


def _emit(compiler, path, ll, work):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(path), "-o", str(ll)], check=False, cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)


def _link(compiler, ll, work):
    exe = work / "main"
    cmd = ["clang", "-Wno-override-module", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        cmd.insert(1, str(RITZ_START))
    return fast_link.clang(cmd, cwd=work, capture_output=True, text=True), exe


def _batch_build(compiler, path, work):
    ll = work / "main.ll"
    comp = _emit(compiler, path, ll, work)
    if comp.returncode != 0 or not ll.exists():
        return False, comp.stdout + comp.stderr, None
    link, exe = _link(compiler, ll, work)
    return link.returncode == 0, link.stderr, exe


def _batch_compile(compiler, path, work):
    comp = _emit(compiler, path, work / "main.ll", work)
    return comp.returncode, comp.stdout + comp.stderr


def _run(compiler, tmp_path, name, src):
    got = batching.run(compiler, src, _batch_build, compile=_batch_compile)  # #2806
    if got is not None:
        return got
    batching.per_row()
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    path = work / "main.ritz"
    path.write_text(src)
    ll = work / "main.ll"
    comp = _emit(compiler, path, ll, work)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused {name}:\n{src}\n{out[-2000:]}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: {name} would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], check=False, capture_output=True, timeout=60).returncode


def _cases():
    for compiler in COMPILERS:
        for name, (_, _, reads) in sorted(PROGRAMS.items()):
            marks = ()
            if reads and compiler != "ritz0":
                marks = pytest.mark.xfail(strict=True, reason=READ_2971)
            yield pytest.param(compiler, name, marks=marks, id=f"{compiler}-{name}")


@pytest.mark.parametrize("compiler,name", list(_cases()))
def test_store_through_a_borrow_deref(compiler, tmp_path, name):
    src, want, _ = PROGRAMS[name]
    assert _run(compiler, tmp_path, name, src) == want


# `*a` of an `a:& [N]T` reads the array; storing through it is refused (#2290).
ARRAY_STORE = """\
fn f(a:& [2]i32, b:& [2]i32)
    *a = b

pub fn main() -> i32
    var a: [2]i32 = [0, 0]
    var b: [2]i32 = [1, 3]
    f(a, b)
    return a[1]
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_store_through_an_array_borrow_deref_is_refused(compiler, tmp_path):
    work = tmp_path / compiler
    work.mkdir()
    path = work / "main.ritz"
    path.write_text(ARRAY_STORE)
    comp = _emit(compiler, path, work / "main.ll", work)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert f"main.ritz:2:5: {BORROW_DEREF_STORE}" in out, out
