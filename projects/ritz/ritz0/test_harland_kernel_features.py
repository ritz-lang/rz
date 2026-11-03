"""Harland uses the #1879 kernel features instead of its workarounds (AGAST #2118).

#1879 gave the language volatile_load/volatile_store (LANGUAGE_SPEC §18.4),
atomic_* and fence (§18.5), `extern var` (§5.3) and `[[callconv = "win64"]]`
(§17.7). Before them harland open-coded each one, and several of those
stand-ins were wrong rather than merely ugly:

* sched_lock was an asm `xchg` on a hard-coded `lea scheduler_lock(%rip)`,
  and sched_unlock a plain store the optimiser may reorder;
* every AP ran `ap_count = ap_count + 1`, a racy read-modify-write;
* vq_submit published the avail index with no barrier at all ("In a real
  implementation, we'd use a proper memory barrier"), and the virtio MMIO
  helpers were plain derefs the optimiser may fold or repeat;
* ENA and virtio-net open-coded mfence/lfence beside io.ritz's barriers;
* linker symbols were `extern fn __bss_start()`, a function declaration
  standing in for a data symbol;
* the bootloader called UEFI through hand-written MS x64 asm shims
  (uefi_call1..5).

Each test below compiles the real harland module with ritz0 (the compiler
`./rz build harland` uses) and checks the IR of the function concerned, so a
regression to the workaround fails the test that names it. The last test is
the ticket's source-level acceptance scan.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration   # each fixture runs ritz0 (AGAST #1805)

RITZ0_DIR = Path(__file__).resolve().parent
RITZ0 = RITZ0_DIR / "ritz0.py"
HARLAND = RITZ0_DIR.parents[1] / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
BOOT_SRC = HARLAND / "boot" / "src"


def _compile(tmp_path_factory, rel, boot=False):
    """ritz0 IR of one harland module, compiled as `rz build harland` would."""
    out = tmp_path_factory.mktemp("harland_ir") / (Path(rel).stem + ".ll")
    if boot:
        src, sources, target, extra = BOOT_SRC / rel, '["boot/src"]', "x86_64-unknown-uefi", []
    else:
        src, sources, target, extra = KERNEL_SRC / rel, '["kernel/src"]', "x86_64-none-elf", ["--no-runtime"]
    proc = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(out), *extra,
         "--project-root", str(HARLAND), "--sources", sources, "--target", target],
        capture_output=True, text=True, cwd=RITZ0_DIR, timeout=300,
        # syscall/numbers.ritz imports ritzlib.option (#2121); `rz build` sets this too.
        env=dict(os.environ, RITZ_PATH=str(RITZ0_DIR.parent)))
    assert proc.returncode == 0 and out.exists(), \
        f"ritz0 rejected harland {rel}:\n{proc.stdout}{proc.stderr}"
    return out.read_text()


def _body(ir, name):
    """The IR text of `define ... @"name"(...) { ... }`."""
    m = re.search(rf'^define [^\n]*@"{re.escape(name)}"\(.*?^}}', ir, re.M | re.S)
    assert m, f"no definition of {name} in the IR"
    return m.group(0)


@pytest.fixture(scope="module")
def sched_ir(tmp_path_factory):
    return _compile(tmp_path_factory, "sched/mod.ritz")


@pytest.fixture(scope="module")
def main_ir(tmp_path_factory):
    return _compile(tmp_path_factory, "main.ritz")


@pytest.fixture(scope="module")
def virtio_ir(tmp_path_factory):
    return _compile(tmp_path_factory, "drivers/virtio/common.ritz")


@pytest.fixture(scope="module")
def boot_ir(tmp_path_factory):
    return _compile(tmp_path_factory, "main.ritz", boot=True)


# --- sched/mod.ritz: the scheduler spinlock -------------------------------

def test_sched_lock_is_atomic_xchg(sched_ir):
    body = _body(sched_ir, "sched_lock")
    assert re.search(r'atomicrmw xchg i32\* @"scheduler_lock", i32 \S+ seq_cst', body), body
    # A `pause` spin hint is fine; the swap itself must not be asm.
    assert not re.search(r"asm [^\n]*xchg", body), f"sched_lock still swaps in inline asm:\n{body}"


def test_sched_unlock_is_atomic_store(sched_ir):
    body = _body(sched_ir, "sched_unlock")
    assert re.search(r'store atomic i32 \S+, i32\* @"scheduler_lock" seq_cst', body), body


# --- main.ritz: AP bring-up counter and linker symbols ---------------------

def test_ap_count_increment_is_atomic(main_ir):
    body = _body(main_ir, "ap_entry")
    assert re.search(r'atomicrmw add i32\* @"ap_count", i32 \S+ seq_cst', body), body


@pytest.mark.parametrize("sym", ["__bss_start", "__bss_end",
                                 "ap_trampoline_start", "ap_trampoline_end"])
def test_linker_symbols_are_extern_vars(main_ir, sym):
    assert re.search(rf'^@"{sym}" = external global i8\b', main_ir, re.M), \
        f"{sym} is not an `extern var NAME: u8`"
    assert not re.search(rf'^declare [^\n]*@"{sym}"\(', main_ir, re.M), \
        f"{sym} is still declared as a function"


# --- drivers/virtio/common.ritz: ring publish and MMIO ---------------------

def test_vq_submit_fences_before_idx_publish(virtio_ir):
    body = _body(virtio_ir, "vq_submit")
    stores = [m.start() for m in re.finditer(r"^\s+store ", body, re.M)]
    fence = body.find("fence seq_cst")
    assert fence != -1, f"vq_submit has no fence:\n{body}"
    # The ring entry is written before the fence, the avail idx after it.
    assert any(s < fence for s in stores) and any(s > fence for s in stores), body


@pytest.mark.parametrize("width", [8, 16, 32])
def test_virtio_mmio_accesses_are_volatile(virtio_ir, width):
    assert re.search(rf"load volatile i{width}, ", _body(virtio_ir, f"mmio_read{width}"))
    assert re.search(rf"store volatile i{width} ", _body(virtio_ir, f"mmio_write{width}"))


def test_io_memory_barrier_is_fence(tmp_path_factory):
    # ENA and virtio-net call this instead of open-coding mfence.
    body = _body(_compile(tmp_path_factory, "io.ritz"), "memory_barrier")
    assert "fence seq_cst" in body and "asm" not in body, body


# --- boot/src/main.ritz: UEFI calls ---------------------------------------

def test_boot_calls_uefi_through_win64_fn_types(boot_ir):
    assert not re.search(r'^define [^\n]*@"uefi_call\d', boot_ir, re.M), \
        "the uefi_call* MS-x64 asm shims are still defined"
    assert "call *%rax" not in boot_ir, "boot still calls through inline asm"
    # get_memory_map is a five-argument service: the old shim passed the
    # fifth on the stack by hand.
    body = _body(boot_ir, "efi_get_memory_map")
    assert re.search(r"call win64cc i64 %[^\n]*\(i64 [^\n]*, i64 [^\n]*, i64 [^\n]*, i64 [^\n]*, i64 ", body), body


# --- the ticket's acceptance scan ------------------------------------------

def _ritz_lines():
    for path in sorted(HARLAND.rglob("*.ritz")):
        rel = path.relative_to(HARLAND)
        if rel.parts[0] in ("build", "docs"):
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#", 1)[0]
            if code.strip():
                yield rel, n, code


def test_no_workarounds_left_in_harland():
    # io.ritz and arch/ are where the instruction-level primitives live.
    allowed = {Path("kernel/src/io.ritz")}
    bad = []
    for rel, n, code in _ritz_lines():
        where = f"{rel}:{n}: {code.strip()}"
        if re.search(r"\bextern fn (__bss_|ap_trampoline_)", code):
            bad.append(where)
        if re.search(r"\buefi_call\d", code):
            bad.append(where)
        in_arch = rel.parts[:3] == ("kernel", "src", "arch")
        if rel not in allowed and not in_arch and re.search(r"^\s*(m|l|s)fence\b|\bxchg[bwlq]?\b", code):
            bad.append(where)
    assert not bad, "workarounds #2118 replaces are still present:\n" + "\n".join(bad)
