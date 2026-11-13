"""Harland's APIC and AP-startup code lives in arch/x86_64/apic.ritz (AGAST #2750).

#1844 splits kernel/src/main.ritz by subsystem. This slice moves the PIC
remap/disable, Local APIC, I/O APIC and AP bootstrap code (ap_started,
ap_stacks, ap_count, delay_us, the trampoline copy, INIT/SIPI) into its own
module, as a pure move: main's version of each function, with #2118's atomic
ap_count and `extern var` trampoline symbols, not the #1844 branch's older copy.

The checks are structural, at source level:

* apic.ritz defines every moved function, global and constant, and main.ritz
  defines none of them;
* main.ritz takes what kernel_main calls from `import arch.x86_64.apic`;
* the #2118 forms survive the move (the IR-level checks for them, in
  test_harland_kernel_features.py, now compile apic.ritz);
* the symbols sched/mod.ritz and arch/x86_64/exceptions.ritz bind to with
  `extern fn` are still `pub` and still defined, under the same names.

Behaviour is unchanged by construction; the OVMF Tier-1 boot
(tools/test_tier1_boot.sh) is the runtime check.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parent
KERNEL_SRC = RITZ0_DIR.parents[1] / "harland" / "kernel" / "src"
MAIN = KERNEL_SRC / "main.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"

MOVED_FNS = [
    "pic_remap", "pic_disable",
    "lapic_read", "lapic_write", "lapic_id", "lapic_eoi", "lapic_init", "lapic_send_ipi",
    "ioapic_read", "ioapic_write", "ioapic_set_irq", "ioapic_init",
    "get_ap_stack_top", "delay_us", "ap_entry", "ap_setup_trampoline",
    "ap_boot_one", "ap_boot_all", "apic_init_with_mb", "apic_init_from_bootinfo",
]
MOVED_VARS = ["ap_started", "ap_stacks", "ap_count", "bsp_apic_id"]
MOVED_CONST_PREFIXES = ("LAPIC_", "IOAPIC_", "IPI_DELIVERY_", "AP_TRAMPOLINE_ADDR")

# What kernel_main calls; main must import exactly these from the new module.
MAIN_USES = {"pic_remap", "apic_init_with_mb", "apic_init_from_bootinfo", "ap_boot_all"}

# Bound by name through `extern fn` from sched/mod.ritz and exceptions.ritz.
EXTERN_BOUND = {"lapic_id", "lapic_eoi", "lapic_write", "get_ap_stack_top"}


def _code(path):
    """Source with comments stripped (a `#` inside a string doesn't occur here)."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _fns(code):
    return dict((m.group(2), bool(m.group(1)))
                for m in re.finditer(r"^(pub\s+)?fn\s+(\w+)\s*\(", code, re.M))


def _vars(code):
    return set(re.findall(r"^(?:pub\s+)?var\s+(\w+)\s*:", code, re.M))


def _consts(code):
    return set(re.findall(r"^(?:pub\s+)?const\s+(\w+)\s*:", code, re.M))


def _imports_from(code, module):
    m = re.search(rf"^import {re.escape(module)}\s*\{{([^}}]*)\}}", code, re.M)
    return set(re.findall(r"\w+", m.group(1))) if m else None


def test_apic_module_defines_the_moved_code():
    assert APIC.exists(), f"{APIC.relative_to(KERNEL_SRC)} does not exist"
    code = _code(APIC)
    fns = _fns(code)
    assert not set(MOVED_FNS) - set(fns), f"not defined in apic.ritz: {sorted(set(MOVED_FNS) - set(fns))}"
    assert not set(MOVED_VARS) - _vars(code), f"globals missing: {sorted(set(MOVED_VARS) - _vars(code))}"
    consts = _consts(code)
    for p in MOVED_CONST_PREFIXES:
        assert any(c.startswith(p) for c in consts), f"no {p}* constant in apic.ritz"


def test_main_defines_none_of_it():
    code = _code(MAIN)
    left = sorted(set(MOVED_FNS) & set(_fns(code)))
    assert not left, f"main.ritz still defines {left}"
    assert not set(MOVED_VARS) & _vars(code), sorted(set(MOVED_VARS) & _vars(code))
    consts = [c for c in _consts(code) if c.startswith(MOVED_CONST_PREFIXES)]
    assert not consts, f"main.ritz still defines {consts}"
    assert not re.search(r"^extern var ap_trampoline_", code, re.M), "trampoline symbols still in main"


def test_main_imports_what_it_calls_from_apic():
    imported = _imports_from(_code(MAIN), "arch.x86_64.apic")
    assert imported is not None, "main.ritz has no `import arch.x86_64.apic { ... }`"
    assert imported == MAIN_USES, imported
    fns = _fns(_code(APIC))
    assert all(fns.get(n) for n in MAIN_USES), "every fn main imports is `pub` in apic.ritz"


def test_extern_bound_symbols_stay_pub():
    fns = _fns(_code(APIC))
    assert all(fns.get(n) for n in EXTERN_BOUND), {n: fns.get(n) for n in EXTERN_BOUND}
    for rel in ["sched/mod.ritz", "arch/x86_64/exceptions.ritz"]:
        for name in re.findall(r"^extern fn (\w+)\(", _code(KERNEL_SRC / rel), re.M):
            if name.startswith(("lapic_", "get_ap_")):
                assert name in EXTERN_BOUND, f"{rel} binds {name}, which apic.ritz must export"


def test_2118_forms_survive_the_move():
    code = _code(APIC)
    body = re.search(r"^pub fn ap_entry\(.*?(?=^\S)", code + "\nEND", re.M | re.S).group(0)
    assert "atomic_fetch_add(@ap_count as *u32, 1)" in body, body
    assert not re.search(r"ap_count\s*=\s*ap_count\s*\+", body), "racy ap_count increment is back"
    for sym in ["ap_trampoline_start", "ap_trampoline_end"]:
        assert re.search(rf"^extern var {sym}: u8$", code, re.M), sym
        assert f"@{sym} as u64" in code, sym


def test_ap_started_still_indexed_by_apic_id():
    # #1883 is out of scope for a pure move: the indexing bug moves as it is.
    code = _code(APIC)
    assert "ap_started[my_apic_id as i32] = 1" in code
    assert "ap_started[apic_id as i32]" in code
