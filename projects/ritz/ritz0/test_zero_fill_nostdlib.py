"""AGAST #3218: a `[0; N]` zero fill links without libc on every compiler.

THE DEFECT

ritz1 lowered a zero fill such as `var b: [65536]u8 = [0; 65536]` to

    call void @llvm.memset.p0.i64(ptr %b, i8 0, i64 65536, i1 false)

and codegen turns an intrinsic memset that large into a call to libc
`memset`.  Ritz links -nostdlib, so a program that does not import ritzlib
(which defines `memset`) failed to link: `undefined reference to memset`.
ritz0 never had the problem: it defines its own `memset` whenever it uses
the intrinsic (_emit_memset_function).

THE FIX

ritz1 zero-fills through @__ritz_sret_zero, the module-internal byte loop
#1730 already defines for sret returns.  It carries "no-builtins", so clang
cannot turn the loop back into a memset call.

Each form below is a zero fill on its own path: a local (the ticket), an
array of wider elements, a struct-literal field, a large array returned
through sret (#2306), both as a tail literal and through a local, and a
large array passed byval.  `dirty()` fills the stack with 0xAA before each
form, so a fill that silently did nothing fails at run time, not just at
link time.
"""

import os
import subprocess
from pathlib import Path

import fast_link
import pytest
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ("ritz0", "ritz1", "ritz1_selfhosted")

# The ticket's repro: a zero fill and nothing else, so nothing but the fill
# makes the module define its zero helper.
TICKET = """\
fn main() -> i32
    var b: [65536]u8 = [0; 65536]
    b[3] as i32
"""

# No imports: nothing in this module defines `memset` but the compiler.
FORMS = """\
struct Holder
    tag: u8
    buf: [4096]u8

fn dirty() -> i32
    var d: [65536]u8 = [170; 65536]
    d[100] as i32

fn sum(p: *u8, n: i32) -> i32
    var t: i32 = 0
    var i: i32 = 0
    while i < n
        t = t + *(p + i) as i32
        i = i + 1
    t

fn sum_byval(a: [65536]u8) -> i32
    sum(@a[0], 65536)

fn zeros() -> [65536]u8
    [0; 65536]

fn zeros_var() -> [65536]u8
    var b: [65536]u8 = [0; 65536]
    b

fn local() -> i32
    var b: [65536]u8 = [0; 65536]
    sum(@b[0], 65536)

fn wide() -> i32
    var w: [1000]u32 = [0; 1000]
    var t: i32 = 0
    var i: i32 = 0
    while i < 1000
        t = t + w[i] as i32
        i = i + 1
    t

fn field() -> i32
    var h = Holder { tag: 1, buf: [0; 4096] }
    sum(@h.buf[0], 4096) + h.tag as i32 - 1

fn main() -> i32
    dirty()
    if local() != 0
        return 1
    dirty()
    if wide() != 0
        return 2
    dirty()
    if field() != 0
        return 3
    dirty()
    let a: [65536]u8 = zeros()
    if sum(@a[0], 65536) != 0
        return 4
    dirty()
    let c: [65536]u8 = zeros_var()
    if sum(@c[0], 65536) != 0
        return 5
    dirty()
    if sum_byval([0; 65536]) != 0
        return 6
    0
"""


PROGRAMS = {"ticket": TICKET, "forms": FORMS}


def _ll(request, compiler: str, tmp_path: Path, program: str) -> Path:
    src = tmp_path / "zf.ritz"
    src.write_text(program)
    ll = tmp_path / f"zf_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run(
            [str(binary), str(src), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )
    assert proc.returncode == 0 and ll.exists(), (
        f"{compiler} failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
    )
    return ll


@pytest.mark.integration
@pytest.mark.parametrize("opt", ("-O0", "-O2"))
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("prog", PROGRAMS)
def test_zero_fill_links_nostdlib(request, tmp_path, prog, compiler, opt):
    ll = _ll(request, compiler, tmp_path, PROGRAMS[prog])
    obj = tmp_path / f"zf{opt}.o"
    cc = subprocess.run(
        ["clang", "-c", opt, "-Wno-override-module", str(ll), "-o", str(obj)],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cc.returncode == 0, cc.stderr[-2000:]
    undef = subprocess.run(
        ["nm", "-u", str(obj)], capture_output=True, text=True, check=True
    )
    assert "memset" not in undef.stdout.split(), (
        f"{prog} {compiler} {opt}: the object needs libc memset:\n{undef.stdout}"
    )
    exe = tmp_path / f"zf{opt}"
    link = ["clang", "-nostdlib", "-o", str(exe), str(obj)]
    if compiler != "ritz0":
        # ritz0 emits its own _start for `main`; ritz1 links the runtime's.
        link.append(str(RITZ_START))
    built = fast_link.clang(
        link, check=False, capture_output=True, text=True, timeout=120
    )
    assert built.returncode == 0, (
        f"{prog} {compiler} {opt}: link:\n{built.stderr[-2000:]}"
    )
    assert subprocess.run([str(exe)], check=False, timeout=60).returncode == 0
