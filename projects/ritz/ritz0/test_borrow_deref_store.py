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

Rows that READ `*h` read the caller's T on all three (#2971): ritz1 loaded
through the int's value as an address and segfaulted.

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

# name: (program, exit code)
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
""", 33),
    "i32_store": ("""\
fn f(h:& i32, v: i32)
    *h = v

pub fn main() -> i32
    var n: i32 = 2
    f(n, 7)
    return n
""", 7),
    # One byte, so the store is that wide: the neighbours keep their 9s.
    "u8_store_element": ("""\
fn f(h:& u8, v: u8)
    *h = v

pub fn main() -> i32
    var a: [3]u8 = [9, 1, 9]
    f(a[1], 7)
    return (a[0] as i32) * 100 + (a[1] as i32) * 10 + (a[2] as i32) - 900
""", 79),
    "u8_repro": ("""\
fn f(h:& u8) -> u8
    *h = *h + 1
    return *h

pub fn main() -> i32
    var n: u8 = 2
    let r = f(n)
    return (n as i32) * 10 + (r as i32)
""", 33),
    "i32_compound": ("""\
fn f(h:& i32) -> i32
    *h += 1
    return *h

pub fn main() -> i32
    var n: i32 = 2
    let r = f(n)
    return n * 10 + r
""", 33),
    "bool_store": ("""\
fn f(h:& bool, v: bool)
    *h = v

pub fn main() -> i32
    var b: bool = false
    f(b, true)
    if b
        return 33
    return 1
""", 33),
    "bool_not": ("""\
fn f(h:& bool)
    *h = not *h

pub fn main() -> i32
    var b: bool = false
    f(b)
    if b
        return 33
    return 1
""", 33),
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
""", 34),
    # AGAST #2971: `*h` reads the caller's T, whatever its width, and is a
    # value like any other: an operand, and an argument.
    "i64_read": ("""\
fn f(h:& i64) -> i64
    return *h + 1

pub fn main() -> i32
    var n: i64 = 5000000000
    return (f(n) - 4999999970) as i32
""", 31),
    "bool_read": ("""\
fn f(h:& bool) -> i32
    if *h
        return 33
    return 1

pub fn main() -> i32
    var b: bool = true
    return f(b)
""", 33),
    "read_in_expression": ("""\
fn f(h:& i32, k:& u16) -> i32
    return (*h * 3 + (*k as i32)) - *h

pub fn main() -> i32
    var n: i32 = 5
    var m: u16 = 7
    return f(n, m)
""", 17),
    "read_as_argument": ("""\
fn g(v: i32) -> i32
    return v * 2

fn f(h:& i32) -> i32
    return g(*h)

pub fn main() -> i32
    var n: i32 = 6
    return f(n)
""", 12),
    "struct_field_read": ("""\
struct C
    x: i32
    y: i64

fn f(h:& C) -> i32
    return (*h).x + ((*h).y as i32)

pub fn main() -> i32
    var c: C = C { x: 30, y: 4 }
    return f(c)
""", 34),
    # `h:& *i32`: `*p` is through the pointer p holds, as it was.
    "pointer_borrow": ("""\
fn f(p:& *i32)
    *p = 3

pub fn main() -> i32
    var x: i32 = 1
    var p: *i32 = @x
    f(p)
    return x
""", 3),
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
        for name in sorted(PROGRAMS):
            yield pytest.param(compiler, name, id=f"{compiler}-{name}")


@pytest.mark.parametrize("compiler,name", list(_cases()))
def test_store_through_a_borrow_deref(compiler, tmp_path, name):
    src, want = PROGRAMS[name]
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
