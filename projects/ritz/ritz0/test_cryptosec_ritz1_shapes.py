"""AGAST #2204: two shapes cryptosec's lib uses that ritz1 couldn't compile.

`@b.f[i]` with a `f: *T` field (rsa.ritz's `@bit_string.content[1]`) is
`b.f + i`, one T per step, whatever `b` is: a struct value, a `*S`, a member
chain.  ritz1 refused a struct value's ("cannot take address") and, through a
`*S`, stepped the `*u32` by a byte (`u32_through_ptr` read 0).

`*p` with `p: *v4i32` (chacha20_avx2.ritz's `*row0`) loads the vector
`<4 x i32>`.  ritz1 loaded a struct `%v4i32`, which clang rejects ("load
operand must be a pointer to a first class type").

ritz0 is the oracle: every row's exit code is what ritz0's build returns.
mem.ritz's inline `asm` was the third failure, and #1619's: ritz1 lowers it
since #3395 (test_cryptosec_mem_compiles here; test_cryptosec_mem_zero_o2.py
runs the wipe).
"""

import os
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link
from ritz0_inproc import run_ritz0

pytestmark = [pytest.mark.integration, pytest.mark.batched]

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
MEM_RITZ = RITZ_ROOT.parent / "cryptosec" / "lib" / "mem.ritz"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PTR_FIELD = """\
struct P
    x: i32
    y: i32

struct D
    b: *u8
    w: *u32
    ps: *P
    n: i32

struct O
    d: D

fn rd(p: *u8) -> i32
    return *p as i32

fn rw(p: *u32) -> i32
    return *p as i32

fn mk(b: *u8, w: *u32, ps: *P) -> D
    var d: D
    d.b = b
    d.w = w
    d.ps = ps
    d.n = 0
    return d

{fns}pub fn main() -> i32
    var bs: [4]u8 = [1, 2, 3, 4]
    var ws: [3]u32 = [10, 20, 30]
    var pa: [2]P
    pa[0] = P { x: 1, y: 2 }
    pa[1] = P { x: 5, y: 6 }
    var d: D = mk(@bs[0], @ws[0], @pa[0])
{body}
"""

SIMD = """\
fn sum4(v: v4i32) -> i32
    var a: [4]i32
    simd_storeu(@a[0], v)
    return a[0] + a[1] + a[2] + a[3]

{fns}pub fn main() -> i32
    var xs: [4]i32 = [1, 2, 3, 4]
    var ys: [4]i32 = [10, 20, 30, 40]
    var x: v4i32 = simd_loadu(@xs[0])
    var y: v4i32 = simd_loadu(@ys[0])
{body}
"""

# name: (template, helper fns, main's tail, exit code)
PROGRAMS = {
    # `@b.f[i]`, f: *T.  The element type sets the stride: u8, u32, a struct.
    "ptr_field_u8_local": (PTR_FIELD, "", "    return rd(@d.b[2])", 3),
    "ptr_field_u32_local": (PTR_FIELD, "", "    return rw(@d.w[2])", 30),
    "ptr_field_struct_local": (PTR_FIELD, "", "    let q: *P = @d.ps[1]\n    return q.y", 6),
    "ptr_field_u8_param": (PTR_FIELD, "fn f(d: D) -> i32\n    return rd(@d.b[1])\n\n",
                           "    return f(d)", 2),
    "ptr_field_u32_through_ptr": (PTR_FIELD, "fn f(d: *D) -> i32\n    return rw(@d.w[1])\n\n",
                                  "    return f(@d)", 20),
    "ptr_field_u32_chain": (PTR_FIELD, "", "    var o: O\n    o.d = d\n    return rw(@o.d.w[1])", 20),
    "ptr_field_store_through": (PTR_FIELD, "",
                                "    let p: *u32 = @d.w[1]\n    *p = 7\n    return ws[1] as i32", 7),
    # `*p`, p: *v4i32: read, as an operand, and stored back through.
    "simd_deref_read": (SIMD, "fn rd(p: *v4i32) -> i32\n    return sum4(*p)\n\n",
                        "    return rd(@x)", 10),
    "simd_deref_operand": (SIMD, "fn ad(p: *v4i32, q: *v4i32) -> i32\n    return sum4(simd_add(*p, *q))\n\n",
                           "    return ad(@x, @y)", 110),
    "simd_deref_store_through": (SIMD, "fn st(p: *v4i32, q: *v4i32)\n    *p = simd_add(*p, *q)\n\n",
                                 "    st(@x, @y)\n    return sum4(x)", 110),
}


def _src(name):
    template, fns, body, _ = PROGRAMS[name]
    return template.replace("{fns}", fns).replace("{body}", body)


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
def test_cryptosec_shape_runs_as_ritz0_runs_it(compiler, tmp_path, name):
    assert _run(compiler, tmp_path, name, _src(name)) == PROGRAMS[name][3]


@pytest.mark.skipif(not MEM_RITZ.is_file(), reason="cryptosec not checked out")
@pytest.mark.parametrize("compiler", COMPILERS)
def test_cryptosec_mem_compiles(compiler, tmp_path):
    # mem_zero's `nopl ({ptr})` barrier (#1986): ritz1 refused it until #3395.
    comp = _emit(compiler, MEM_RITZ, tmp_path / "mem.ll", tmp_path)
    assert comp.returncode == 0, comp.stdout + comp.stderr
    assert "nopl" in (tmp_path / "mem.ll").read_text()
