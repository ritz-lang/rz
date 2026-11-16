"""AGAST #3397: `syscall0..6` are Ritz fns in ritzlib/sys.ritz, written with
`asm` (LANGUAGE_SPEC §18.6), on every compiler.

They used to be compiler magic: ritz0 lowered `syscallN` / `__syscallN` to an
inline `syscall` at the call site, and ritz1 emitted a hand-written weak_odr
body for each into every module that named one (and `cpuid_raw` likewise).
Now ritzlib.sys has the only bodies, and -O2 must make them what the shims
were: one `asm sideeffect "syscall"` with the number in rax, the arguments in
rdi, rsi, rdx, r10, r8, r9, the result in rax and rcx, r11 and memory
clobbered. A wrapper in the module that calls one (`sys_write`) inlines it:
the bare `syscall`, no call left.
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
SYS_RITZ = RITZ_ROOT / "ritzlib" / "sys.ritz"
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# ritzlib.sys's syscall3, for a test program the harness links as one module,
# without ritzlib: no compiler supplies the name any more.
LOCAL_SYSCALL3 = """\
fn syscall3(n: i64, a1: i64, a2: i64, a3: i64) -> i64
    var r: i64 = n
    asm x86_64 (inout r: rax, in a1: rdi, in a2: rsi, in a3: rdx, clobber rcx, clobber r11):
        syscall
    return r

"""

# The syscall ABI's argument registers, in order.
ARG_REGS = ["rdi", "rsi", "rdx", "r10", "r8", "r9"]


def _sys_ll_o2(request, compiler: str, tmp_path: Path) -> str:
    """ritzlib/sys.ritz compiled by `compiler`, then clang -O2, as IR text."""
    ll = tmp_path / "sys.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0(["--no-runtime", str(SYS_RITZ), "-o", str(ll)], cwd=tmp_path, env=env,
                         timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(SYS_RITZ), "-o", str(ll)], cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]
    opt = tmp_path / "sys.o2.ll"
    clang = subprocess.run(["clang", "-w", "-O2", "-S", "-emit-llvm", "-x", "ir", str(ll),
                            "-o", str(opt)], capture_output=True, text=True, timeout=300)
    assert clang.returncode == 0, clang.stderr[-2000:]
    return opt.read_text()


def _body(ir_text: str, name: str) -> str:
    """The body of `define ... @name(` (quoted or not), up to its closing brace."""
    m = re.search(rf'^define [^\n]*@"?{re.escape(name)}"?\(.*?^}}', ir_text, re.M | re.S)
    assert m, f"no definition of @{name}"
    return m.group(0)


def _asm_calls(body: str):
    """(template, constraints) of each inline asm call in `body`."""
    return re.findall(r'asm sideeffect "([^"]*)", "([^"]*)"', body)


needs_clang = pytest.mark.skipif(shutil.which("clang") is None, reason="clang not on PATH")


@needs_clang
@pytest.mark.parametrize("compiler", COMPILERS)
def test_syscall_wrappers_are_the_bare_instruction_at_o2(request, tmp_path, compiler):
    ir_text = _sys_ll_o2(request, compiler, tmp_path)
    for n in range(7):
        body = _body(ir_text, f"syscall{n}")
        calls = _asm_calls(body)
        assert len(calls) == 1, f"syscall{n}:\n{body}"
        template, constraints = calls[0]
        assert template == "syscall", f"syscall{n}: {template!r}"
        parts = constraints.split(",")
        # The result in rax, the number in rax (pinned or tied to it).
        assert parts[0] in ("={rax}", "=&{rax}"), f"syscall{n}: {constraints}"
        assert parts[1] in ("{rax}", "0"), f"syscall{n}: {constraints}"
        args = [p for p in parts[2:] if not p.startswith("~")]
        assert args == [f"{{{r}}}" for r in ARG_REGS[:n]], f"syscall{n}: {constraints}"
        for clobber in ("~{rcx}", "~{r11}", "~{memory}"):
            assert clobber in parts, f"syscall{n} lacks {clobber}: {constraints}"
        assert "call " not in body.replace("call i64 asm", ""), f"syscall{n}:\n{body}"
    # A wrapper beside them inlines its syscall: the bare instruction.
    body = _body(ir_text, "sys_write")
    assert [t for t, _ in _asm_calls(body)] == ["syscall"], body
    assert not re.search(r'call [^\n]*@"?syscall\d', body), body
