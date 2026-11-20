"""AGAST #2590: stack canaries for harland (GitHub #116's leftover).

THE DEFECT

Neither compiler ever asked LLVM for a stack protector, and build.py hands
clang already-emitted .ll, so clang's `-fstack-protector-strong` (a frontend
flag) could not add one either. A stack buffer overrun in the kernel
silently overwrote a saved return address.

THE FIX

* `--stack-protector` (ritz0 and ritz1) puts LLVM's `sspstrong` on every
  function the module defines, except a [[naked]] one (no frame, no
  prologue to store the canary in). Without the flag nothing changes.
* The flag keys each compiler's own IR cache (ritz0's compile mode, ritz1's
  sig fingerprint): a warm compile must not reuse IR built without it.
* build.py passes it for a [[bin]] whose `[bin.NAME.flags]` set
  `stack-protector = true` (tools/test_build_stack_protector.py).
* harland's kernel [[bin]] opts in and supplies what the instrumented code
  references on a `*-none-elf` target: the global `__stack_chk_guard`
  (seeded in boot.s before the first Ritz frame exists) and
  `__stack_chk_fail`, which panics. The UEFI loader does not opt in.

The bare `x86_64-none-elf` target reads the canary from the global
`__stack_chk_guard` (Linux targets read %fs:0x28), which the last test
checks on a real object file.
"""

import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
import test_ir

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
HARLAND = RITZ_ROOT.parent / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"

pytestmark = pytest.mark.integration

# One plain fn with a stack array (the case sspstrong instruments), one
# impl method (a separate define path in ritz1), one [[naked]] fn (must be
# left alone) and one extern declaration (nothing to instrument).
PROGRAM = """\
extern fn ext_sink(p: *u8)

struct Ctr
    n: i64

impl Ctr
    fn bump(self: *Ctr) -> i64
        self.n = self.n + 1
        self.n

fn fill() -> i32
    var buf: [32]u8
    buf[0] = 1 as u8
    ext_sink(@buf[0])
    0

[[naked]]
fn bare()
    asm x86_64:
        ret

fn main() -> i32
    var c: Ctr = Ctr { n: 0 }
    c.bump()
    fill()
"""


def _define_lines(ir: str) -> dict:
    """{fn name: its `define` line}, quoted or bare names."""
    out = {}
    for line in ir.splitlines():
        m = re.match(r'define [^@]*@"?([A-Za-z0-9_$.]+)"?\(', line)
        if m:
            # A private fn's symbol carries its file (AGAST #1858).
            out[test_ir.strip(m.group(1))] = line
    return out


def _assert_protected(ir: str, method_name: str) -> None:
    defs = _define_lines(ir)
    for fn in ("fill", "main", method_name):
        assert fn in defs, f"no define for {fn} in:\n{ir}"
        assert "sspstrong" in defs[fn], f"{fn} not protected: {defs[fn]}"
    assert "bare" in defs, ir
    assert "sspstrong" not in defs["bare"], f"naked fn protected: {defs['bare']}"
    for line in ir.splitlines():
        if line.startswith("declare") and "ext_sink" in line:
            assert "sspstrong" not in line, line


def _ritz0(tmp_path: Path, src: Path, *extra) -> str:
    ll = tmp_path / (src.stem + ".ll")
    proc = run_ritz0([src, "-o", ll, "--no-runtime", *extra], cwd=RITZ0_DIR,
                     env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return ll.read_text()


def _ritz1(tmp_path: Path, src: Path, *extra) -> str:
    ll = tmp_path / (src.stem + ".ll")
    proc = subprocess.run([str(RITZ1_BIN), str(src), "-o", str(ll), *extra],
                          cwd=tmp_path, capture_output=True, text=True, timeout=300,
                          env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return ll.read_text()


@pytest.fixture
def program(tmp_path):
    src = tmp_path / "ssp_prog.ritz"
    src.write_text(PROGRAM)
    return src


# --- ritz0 -----------------------------------------------------------------

def test_ritz0_flag_protects_every_defined_fn_but_naked(tmp_path, program):
    _assert_protected(_ritz0(tmp_path, program, "--stack-protector"), "Ctr_bump")


def test_ritz0_default_emits_no_stack_protector(tmp_path, program):
    assert "sspstrong" not in _ritz0(tmp_path, program)


def test_ritz0_warm_compile_keys_on_the_flag(tmp_path, program):
    """Same source, same output path: off, then on, then off again."""
    assert "sspstrong" not in _ritz0(tmp_path, program)
    assert "sspstrong" in _ritz0(tmp_path, program, "--stack-protector")
    assert "sspstrong" not in _ritz0(tmp_path, program)


# --- ritz1 (the gate builds it first, as for test_ritz1_target_os.py) -------

def test_ritz1_flag_protects_every_defined_fn_but_naked(tmp_path, program):
    _assert_protected(_ritz1(tmp_path, program, "--stack-protector"), "Ctr_bump")


def test_ritz1_warm_compile_keys_on_the_flag(tmp_path, program):
    """ritz1's sig fast path (AGAST #1807) must not hand back unprotected IR."""
    assert "sspstrong" not in _ritz1(tmp_path, program)
    assert "sspstrong" in _ritz1(tmp_path, program, "--stack-protector")
    assert "sspstrong" not in _ritz1(tmp_path, program)


# --- harland ---------------------------------------------------------------

def _harland_bins() -> dict:
    """[[bin]] tables by name.  `[bin.NAME.flags]` lands in the entry as
    entry[NAME]["flags"], which is where build.py reads it."""
    cfg = tomllib.loads((HARLAND / "ritz.toml").read_text())
    return {b["name"]: b for b in cfg["bin"]}


def test_harland_kernel_opts_in_and_the_uefi_loader_does_not():
    bins = _harland_bins()
    assert bins["harland"]["harland"]["flags"].get("stack-protector") is True
    assert not bins["bootx64"].get("bootx64", {}).get("flags", {}).get("stack-protector")


def test_harland_defines_the_guard_and_the_failure_handler(tmp_path):
    ir = _ritz0(tmp_path, KERNEL_SRC / "stack_protector.ritz",
                "--project-root", HARLAND, "--sources", '["kernel/src"]',
                "--target", "x86_64-none-elf", "--target-os", "harland",
                "--stack-protector")
    # Exact, unmangled C names: LLVM's instrumentation references these.
    assert re.search(r'^@"?__stack_chk_guard"? = (dso_local )?global i64 ', ir, re.M), ir
    assert "__stack_chk_fail" in _define_lines(ir), ir


def _harland_seed_code() -> str:
    """higher_half_entry up to `call kernel_main`, comments stripped: the
    window in which the guard must be seeded (every later frame copies it)."""
    boot = (HARLAND / "kernel" / "boot.s").read_text()
    start = boot.find("\nhigher_half_entry:")
    call = boot.find("call kernel_main", start)
    assert 0 <= start < call, "higher_half_entry must call kernel_main"
    return re.sub(r"#.*", "", boot[start:call])


def test_harland_boot_seeds_the_guard_before_kernel_main():
    """In higher_half_entry (the guard is a higher-half .data symbol), before
    the first Ritz frame: guard ^= seed through its absolute address, where
    the seed always includes the TSC (the fallback when RDRAND is absent)."""
    entry = _harland_seed_code()
    m = re.search(r"\brdtsc\b.*movabsq\s+\$__stack_chk_guard,\s*(%r\w+)\s*\n"
                  r"\s*xorq\s+%r\w+,\s*\(\1\)\s*\n\s*movb\s+\$0,\s*\(\1\)",
                  entry, re.S)
    assert m, "boot.s must XOR a TSC-based seed into __stack_chk_guard " \
              "(low byte cleared) before kernel_main"


def test_harland_boot_mixes_rdrand_only_when_cpuid_reports_it():
    """AGAST #4097: RDRAND is mixed in only behind CPUID.01H:ECX[30] (it
    raises #UD on CPUs without it), retried while CF=0, and both happen
    before the guard store."""
    entry = _harland_seed_code()
    store = entry.find("$__stack_chk_guard")
    m = re.search(r"movl\s+\$1,\s*%eax\s*\n\s*cpuid\s*\n\s*btl\s+\$30,\s*%ecx\s*\n"
                  r"\s*jnc\s+(\w+)", entry)
    assert m, "RDRAND must be gated on CPUID.01H:ECX bit 30"
    rd = re.search(r"(\d+):\s*rdrand\s+%r\w+\s*\n\s*jc\s+\w+\s*\n"
                   r"\s*decl\s+%\w+\s*\n\s*jnz\s+(\d+)b", entry)
    assert rd and rd.group(1) == rd.group(2), \
        "RDRAND must retry on CF=0 with a bounded count"
    assert m.start() < rd.start() < store, \
        "the CPUID check and RDRAND must precede the guard store"


@pytest.mark.skipif(shutil.which("clang") is None, reason="clang not on PATH")
def test_freestanding_object_reads_the_global_guard(tmp_path, program):
    """On x86_64-none-elf the canary comes from the global harland defines."""
    ll = tmp_path / "ssp_prog.ll"
    ll.write_text(_ritz0(tmp_path, program, "--stack-protector"))
    obj = tmp_path / "ssp_prog.o"
    subprocess.run(["clang", "-c", "--target=x86_64-none-elf", "-ffreestanding",
                    "-mcmodel=kernel", "-mno-red-zone", "-Wno-override-module",
                    str(ll), "-o", str(obj)], check=True, timeout=120)
    syms = subprocess.run(["nm", "-u", str(obj)], capture_output=True, text=True,
                          check=True).stdout
    assert "__stack_chk_guard" in syms and "__stack_chk_fail" in syms, syms
