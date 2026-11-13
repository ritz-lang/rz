"""Harland's post-init self-tests live in postinit.ritz, its logging in klog.ritz (AGAST #2752).

#1844 splits kernel/src/main.ritz by subsystem. This slice (#1844.6) is a pure
move of two pieces of it:

* the tail of kernel_main: the VMM / higher-half / heap / IPC self-tests, the
  PCI listing, the DHCP + ping loop, the virtio_blk_test call and the
  test_elf_loader call, into postinit.ritz;
* the early-boot ring buffer and the klog helpers (klog, klogs, klog_hex),
  into klog.ritz.

It ports main's code, not the #1844 branch's (83af7f1d): main has since edited
kernel_main (#2118/#2130/#2143), and the branch's ring_write_byte grew a
defensive clamp that would change behaviour. #1887 will gate the self-tests
later; this move doesn't touch what they do or print.

The serial output order is part of the behaviour, so kernel_main still calls
the self-tests, prints "Kernel initialized successfully.", sets up SYSCALL,
then runs the diagnostics: two postinit entry points, in that order.

The checks are structural, at source level. The OVMF QEMU boot
(tools/test_tier1_boot.sh) is the runtime check: its serial log matches main's.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parent
HARLAND = RITZ0_DIR.parents[1] / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
MAIN = KERNEL_SRC / "main.ritz"
KLOG = KERNEL_SRC / "klog.ritz"
POSTINIT = KERNEL_SRC / "postinit.ritz"
METRICS = RITZ0_DIR.parents[1] / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"

# klog.ritz: the ring buffer and the loggers. pub = called from another module.
KLOG_FNS = {
    "ring_write_byte": False, "ring_write": False, "ring_write_hex": False,
    "ring_clear": True, "ring_len": False, "ring_dump": True,
    "klog": True, "klogs": True, "klog_hex": True,
}
KLOG_VARS = {"ring_buffer", "ring_head", "ring_wrapped"}
KLOG_CONSTS = {"RING_BUFFER_SIZE"}

# postinit.ritz: two entry points, each running its checks in this order.
POSTINIT_ENTRIES = {
    "postinit_self_tests": ["vmm_self_test", "higher_half_self_test", "heap_self_test", "ipc_self_test"],
    "postinit_diagnostics": ["pci_print_all_devices", "network_dhcp_ping", "virtio_blk_check",
                             "test_elf_loader"],
}
POSTINIT_FNS = {"vmm_self_test", "higher_half_self_test", "heap_self_test", "ipc_self_test",
                "network_dhcp_ping", "virtio_blk_check"}

# One marker line per moved block, as it is printed. Each must leave main.ritz
# and appear, unchanged, in postinit.ritz.
MOVED_LINES = [
    r'prints("\nTesting Virtual Memory...\n")',
    r'prints("  VMM test PASSED!\n")',
    r'prints("\nTesting Higher-Half Mapping...\n")',
    r'prints("  Higher-half mapping PASSED!\n")',
    r'prints("\nTesting Kernel Heap...\n")',
    r'prints("  Heap test PASSED!\n")',
    r'prints("\nTesting IPC Channels...\n")',
    r'prints("  IPC test PASSED!\n")',
    r'prints("\n=== PCI Devices ===\n")',
    r'prints("\n=== Initializing Network Stack ===\n")',
    r'prints("\n  Got IP! Pinging gateway...\n")',
    r'prints("\n=== VirtIO Block Device ===\n")',
    "virtio_blk_test(blk_dev)",
    "test_elf_loader()",
]

# kernel_main's SLOC (ritz-metrics) before this move, and the ceiling after it.
KERNEL_MAIN_SLOC_BEFORE = 402
KERNEL_MAIN_SLOC_AFTER_MAX = 240
MAIN_SLOC_BEFORE = 595
MAIN_SLOC_AFTER_MAX = 380


def _code(path):
    """Source with `#` comments stripped (no `#` occurs inside a string literal here)."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _fns(code):
    return {m.group(2): bool(m.group(1)) for m in re.finditer(r"^(pub\s+)?fn\s+(\w+)\s*\(", code, re.M)}


def _vars(code):
    return set(re.findall(r"^(?:pub\s+)?var\s+(\w+)\s*:", code, re.M))


def _consts(code):
    return set(re.findall(r"^(?:pub\s+)?const\s+(\w+)\s*:", code, re.M))


def _imports_from(code, module):
    m = re.search(rf"^import {re.escape(module)}\s*\{{([^}}]*)\}}", code, re.M)
    return set(re.findall(r"\w+", m.group(1))) if m else None


def _body(code, fn):
    m = re.search(rf"^(?:pub\s+)?fn {fn}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"no fn {fn}"
    return m.group(0)


def _calls_in_order(body, names):
    pos = [body.find(f"{n}(") for n in names]
    assert all(p >= 0 for p in pos), {n: p >= 0 for n, p in zip(names, pos)}
    assert pos == sorted(pos), f"out of order: {names}"
    return pos


def test_klog_module_defines_the_ring_buffer_and_loggers():
    assert KLOG.exists(), "kernel/src/klog.ritz does not exist"
    code = _code(KLOG)
    fns = _fns(code)
    assert {f: fns.get(f) for f in KLOG_FNS} == KLOG_FNS
    assert KLOG_VARS <= _vars(code), sorted(KLOG_VARS - _vars(code))
    assert KLOG_CONSTS <= _consts(code)


def test_postinit_module_defines_the_self_tests():
    assert POSTINIT.exists(), "kernel/src/postinit.ritz does not exist"
    code = _code(POSTINIT)
    fns = _fns(code)
    assert all(fns.get(e) for e in POSTINIT_ENTRIES), {e: fns.get(e) for e in POSTINIT_ENTRIES}
    assert POSTINIT_FNS <= set(fns), sorted(POSTINIT_FNS - set(fns))
    for entry, steps in POSTINIT_ENTRIES.items():
        _calls_in_order(_body(code, entry), steps)
    # The memory/IPC self-tests still only run with boot info.
    body = _body(code, "postinit_self_tests")
    assert body.index("if has_boot_info") < body.index("vmm_self_test(")


@pytest.mark.parametrize("line", MOVED_LINES)
def test_moved_block_is_in_postinit_not_main(line):
    assert line in POSTINIT.read_text(), f"postinit.ritz lacks {line}"
    assert line not in _code(MAIN), f"main.ritz still has {line}"


def test_each_fn_defined_once_across_the_kernel():
    """Kernel symbols are global (`extern fn` binds by bare name), so a moved fn
    must not survive as a second definition anywhere."""
    moved = set(KLOG_FNS) | set(POSTINIT_ENTRIES) | POSTINIT_FNS
    seen = {}
    for p in KERNEL_SRC.rglob("*.ritz"):
        for fn in _fns(_code(p)):
            if fn in moved:
                seen.setdefault(fn, []).append(str(p.relative_to(KERNEL_SRC)))
    assert set(seen) == moved, sorted(moved - set(seen))
    dup = {fn: ps for fn, ps in seen.items() if len(ps) > 1}
    assert not dup, dup


def test_main_defines_none_of_it():
    code = _code(MAIN)
    left = sorted((set(KLOG_FNS) | set(POSTINIT_ENTRIES) | POSTINIT_FNS) & set(_fns(code)))
    assert not left, f"main.ritz still defines {left}"
    assert not KLOG_VARS & _vars(code), sorted(KLOG_VARS & _vars(code))
    assert not KLOG_CONSTS & _consts(code)


def test_main_imports_what_it_calls():
    code = _code(MAIN)
    assert _imports_from(code, "klog") == {"ring_clear", "klog"}
    assert _imports_from(code, "postinit") == {"postinit_self_tests", "postinit_diagnostics"}


def test_kernel_main_keeps_the_boot_order():
    """Self-tests, the success banner, SYSCALL setup, diagnostics, then init:
    the same serial order as before the move."""
    body = _body(_code(MAIN), "kernel_main")
    assert "postinit_self_tests(has_boot_info)" in body
    # \b: fs_syscall_init() runs earlier and must not match syscall_init().
    steps = [
        r"\bscheduler_init\(\)",
        r"\bpostinit_self_tests\(has_boot_info\)",
        re.escape(r'prints("\nKernel initialized successfully.\n")'),
        r"\bsyscall_init\(\)",
        r"\bpostinit_diagnostics\(\)",
        r"\brun_init\(\)",
    ]
    hits = [list(re.finditer(s, body)) for s in steps]
    assert all(len(h) == 1 for h in hits), {s: len(h) for s, h in zip(steps, hits)}
    order = [h[0].start() for h in hits]
    assert order == sorted(order), body


def test_ring_dump_stays_bound_from_exceptions():
    """exceptions.ritz binds ring_dump by bare name; it must stay pub."""
    assert re.search(r"^extern fn ring_dump\(\) -> i32$",
                     _code(KERNEL_SRC / "arch" / "x86_64" / "exceptions.ritz"), re.M)
    assert _fns(_code(KLOG))["ring_dump"]


def test_ring_write_byte_not_changed():
    """main's ring_write_byte came across, not the branch's clamped one."""
    body = _body(_code(KLOG), "ring_write_byte")
    assert body.index("ring_buffer[ring_head as i32] = c") < body.index("if ring_head >= RING_BUFFER_SIZE")
    assert body.count("if ring_head >= RING_BUFFER_SIZE") == 1


def _metrics(tmp_path):
    out = tmp_path / "m.json"
    proc = subprocess.run([sys.executable, str(METRICS), "--json", str(out), str(MAIN)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(out.read_text())


@pytest.mark.integration   # runs ritz-metrics in a subprocess (AGAST #1805)
def test_main_sloc_dropped(tmp_path):
    m = _metrics(tmp_path)
    km = [f for f in m["functions"] if f["name"] == "kernel_main"]
    assert len(km) == 1, km
    assert km[0]["sloc"] <= KERNEL_MAIN_SLOC_AFTER_MAX, \
        f"kernel_main SLOC {km[0]['sloc']} (was {KERNEL_MAIN_SLOC_BEFORE})"
    sloc = m["files"][0]["sloc"]
    assert sloc <= MAIN_SLOC_AFTER_MAX, f"main.ritz SLOC {sloc} (was {MAIN_SLOC_BEFORE})"
