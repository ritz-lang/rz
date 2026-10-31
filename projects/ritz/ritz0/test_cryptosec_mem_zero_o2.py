"""AGAST #1986: cryptosec's mem_zero must survive -O2 dead-store elimination.

Secret wipes (tls_client_free zeroing shared_secret / key_schedule /
x25519_private, then dropping the struct) zero memory that is never read
again. That is a dead store: once mem_zero is inlined into its caller (same
module or LTO), -O2 deleted the wipe, and the buffer with it. Before the fix,
the linked program below optimised to `ret i32 0`.

The test links the caller with the real cryptosec/lib/mem.ritz the way LTO
would, runs -O2, and checks that the zeroing stores, and the barrier that
keeps them, are still in `main` (IR) and in the machine code (object).
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
PROJECTS = RITZ_ROOT.parent
MEM_RITZ = PROJECTS / "cryptosec" / "lib" / "mem.ritz"

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


def _compile(src: Path, out: Path, cwd: Path):
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}{os.pathsep}{PROJECTS}")
    proc = run_ritz0([str(src), "-o", str(out)], cwd=cwd, env=env, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.fixture
def linked(tmp_path):
    """caller + cryptosec mem.ritz in one IR module (what LTO sees)."""
    caller = tmp_path / "t.ritz"
    caller.write_text(CALLER)
    _compile(caller, tmp_path / "t.ll", tmp_path)
    _compile(MEM_RITZ, tmp_path / "mem.ll", tmp_path)
    out = tmp_path / "linked.ll"
    proc = subprocess.run(
        [LLVM_LINK, "-S", str(tmp_path / "t.ll"), str(tmp_path / "mem.ll"),
         "-o", str(out)], capture_output=True, text=True)
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
    assert "@mem_zero" not in main and "@wipe_local" not in main, main
    # The 32 bytes are still zeroed (vector stores, scalar stores or memset)...
    zeroing = re.findall(
        r"store <\d+ x i8> zeroinitializer|store i\d+ 0,|"
        r"call void @llvm\.memset[^\n]*i8 0, i64 32", main)
    assert zeroing, main
    # ...and kept alive by the asm barrier that reads the buffer through ptr.
    assert re.search(r'call void asm sideeffect "nopl[^"]*", "r,~\{memory\}"', main), main


@needs_tools
def test_O2_keeps_the_wipe_of_a_dead_local_in_machine_code(linked):
    asm = _clang_O2(["-S", str(linked), "-o", "-"])
    main = re.search(r"^main:.*?^\s*(?:ret|\.Lfunc_end)", asm, re.M | re.S).group(0)
    stores = re.findall(r"^\s*(?:mov\w*|stos\w*)\s+[^\n]*\(%r[sb]p\)", main, re.M)
    assert stores, main
    assert "nopl" in main, main


def test_mem_zero_has_the_barrier():
    # Guards the fix if the toolchain-dependent tests above are skipped.
    src = MEM_RITZ.read_text()
    body = re.search(r"^pub fn mem_zero\(.*?(?=^\S)", src, re.M | re.S).group(0)
    assert re.search(r"asm x86_64:\s*\n\s*nopl \(\{ptr\}\)", body), body
