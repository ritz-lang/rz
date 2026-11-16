"""AGAST #1986: cryptosec's mem_zero must survive -O2 dead-store elimination.

Secret wipes (tls_client_free zeroing shared_secret / key_schedule /
x25519_private, then dropping the struct) zero memory that is never read
again. That is a dead store: once mem_zero is inlined into its caller (same
module or LTO), -O2 deleted the wipe, and the buffer with it. Before the fix,
the linked program below optimised to `ret i32 0`.

The fix was an asm barrier after a plain loop; since #1864 mem_zero is
ritzlib.memory's secure_zero, whose stores are volatile_store (LANGUAGE_SPEC
§18.4). The test links the caller with the real cryptosec/lib/mem.ritz and
ritzlib.memory (and what it imports) the way LTO would, built by ritz0 and by
ritz1, runs -O2, and checks that the wipe is inlined into `main` as volatile
stores (IR) and is still in the machine code.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
PROJECTS = RITZ_ROOT.parent
MEM_RITZ = PROJECTS / "cryptosec" / "lib" / "mem.ritz"
# ritzlib.memory (secure_zero) and the modules it imports.
RITZLIB = [RITZ_ROOT / "ritzlib" / f"{m}.ritz" for m in ("memory", "str", "sys", "fmt")]

# A secret is filled, wiped and the frame returns: nothing reads it again.
CALLER = """\
import cryptosec.mem

fn fill(p: *u8, n: i64)
    for i in 0..n
        *(p + i) = 0x5a

fn wipe_local() -> i32
    var secret: [32]u8
    fill(@secret[0], 32)
    mem_zero(@secret[0], 32)
    0

fn main() -> i32
    wipe_local()
"""


def _llvm_link():
    """llvm-link, versioned or not, or the one next to clang."""
    for name in ("llvm-link", "llvm-link-21"):
        path = shutil.which(name)
        if path:
            return path
    clang = shutil.which("clang")
    if clang:
        cand = Path(os.path.realpath(clang)).parent / "llvm-link"
        if cand.exists():
            return str(cand)
    return None


LLVM_LINK = _llvm_link()
needs_tools = pytest.mark.skipif(
    shutil.which("clang") is None or LLVM_LINK is None,
    reason="clang / llvm-link not on PATH")


def _compile(compiler: str, src: Path, out: Path, cwd: Path):
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}{os.pathsep}{PROJECTS}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(out)], cwd=cwd, env=env, timeout=300)
    else:
        # Never skip (#1327): the gate builds ritz1 before pytest.
        assert RITZ1_BIN.exists(), f"{RITZ1_BIN} missing; run `make -C ritz1`"
        proc = subprocess.run([str(RITZ1_BIN), str(src), "-o", str(out)], cwd=cwd, env=env,
                              capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.fixture(params=["ritz0", "ritz1"])
def linked(request, tmp_path):
    """caller + cryptosec mem.ritz in one IR module (what LTO sees)."""
    caller = tmp_path / "t.ritz"
    caller.write_text(CALLER)
    _compile(request.param, caller, tmp_path / "t.ll", tmp_path)
    lls = [tmp_path / "t.ll", tmp_path / "mem.ll"]
    _compile(request.param, MEM_RITZ, lls[1], tmp_path)
    for src in RITZLIB:
        lls.append(tmp_path / f"ritzlib_{src.stem}.ll")
        _compile(request.param, src, lls[-1], tmp_path)
    out = tmp_path / "linked.ll"
    proc = subprocess.run(
        [LLVM_LINK, "-S", *map(str, lls), "-o", str(out)],
        capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    return out


def _clang_O2(args):
    proc = subprocess.run(["clang", "-O2", "-Wno-override-module", *args],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


@needs_tools
def test_O2_keeps_the_wipe_of_a_dead_local_in_ir(linked):
    out = _clang_O2(["-S", "-emit-llvm", str(linked), "-o", "-"])
    main = re.search(r"^define [^\n]*@\"?main\"?\(.*?^}", out, re.M | re.S).group(0)
    # The whole call chain is inlined, so this is the case LTO creates.
    for fn in ("@mem_zero", "@secure_zero", "@wipe_local"):
        assert fn not in main, main
    # The 32 bytes are still zeroed, by stores -O2 may not delete.
    assert re.search(r"store volatile i(8|64) 0,", main), main


@needs_tools
def test_O2_keeps_the_wipe_of_a_dead_local_in_machine_code(linked):
    asm = _clang_O2(["-S", str(linked), "-o", "-"])
    main = re.search(r"^main:.*?^\s*(?:ret|\.Lfunc_end)", asm, re.M | re.S).group(0)
    stores = re.findall(r"^\s*(?:mov\w*|stos\w*)\s+[^\n]*\(%r[sb]p\)", main, re.M)
    assert stores, main


def test_mem_zero_is_secure_zero():
    # Guards the fix if the toolchain-dependent tests above are skipped.
    src = MEM_RITZ.read_text()
    body = re.search(r"^pub fn mem_zero\(.*?(?=^\S)", src, re.M | re.S).group(0)
    assert re.search(r"^\s+secure_zero\(ptr, len\)\s*$", body, re.M), body
