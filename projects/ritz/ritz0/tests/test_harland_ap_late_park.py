"""A late AP parks instead of running on a boot the BSP gave up on (AGAST #4140).

ap_boot_one sends INIT/SIPI/SIPI and waits up to a second (a TSC deadline
since #4181) for the AP to flag itself started. If it printed TIMEOUT,
nothing stopped an AP that came up afterwards from running ap_entry: on the
trampoline's stack slot, which by then may name the next AP's stack, and
into per-CPU state the BSP had written off.

Now two things close that:
  - a per-CPU boot handshake in cpu_map.ritz: the BSP opens the boot
    (cpu_map_boot_begin) before INIT, the AP claims it (cpu_map_boot_claim,
    a compare-and-swap) first thing in ap_entry, and the BSP on timeout
    abandons it (cpu_map_boot_abandon, the same CAS). Exactly one side wins:
    a late AP's claim fails and it parks (cli; hlt); an AP that claimed just
    before the deadline is running, so the BSP waits for it instead;
  - the trampoline takes its stack with an xchg that zeroes the slot, so no
    two CPUs share a stack; a CPU that finds the slot empty halts in the
    trampoline, and the BSP empties it when it abandons a boot.

The state machine is host-tested in test_harland_cpu_map.py (claims 26-32);
these source checks pin that apic.ritz and the trampoline use it. The
runtime proof that the normal path still boots is the multi-CPU gates
(tools/test_tier1_boot.sh -smp 4, tools/test_irq_dest_boot.sh APIC ID 256).
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parents[1]
HARLAND = RITZ0_DIR.parent.parent / "harland" / "kernel"
APIC = HARLAND / "src" / "arch" / "x86_64" / "apic.ritz"
TRAMPOLINE = HARLAND / "ap_trampoline.s"


def _code(path, comment="#"):
    return "\n".join(line.split(comment, 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


def test_ap_entry_claims_its_boot_before_running():
    body = _body(_code(APIC), "ap_entry")
    claim = body.find("cpu_map_boot_claim(")
    assert claim >= 0, "ap_entry never claims its boot"
    # The claim decides whether this AP runs at all: before it touches any
    # shared state (the serial log, per-CPU bring-up, the started flag).
    for later in ("klog(", "cpu_bringup(", "cpu_map_mark_started(", "atomic_fetch_add(", "enable_interrupts("):
        at = body.find(later)
        assert at > claim, f"ap_entry calls {later} before claiming its boot"
    # A failed claim parks: interrupts off, then halt forever.
    after = body[claim:]
    m = re.search(r"if my_index < 0\n(.*?)(?=\n    \S)", after, re.S)
    assert m, "ap_entry doesn't branch on a failed claim"
    assert "ap_park()" in m.group(1), m.group(1)
    park = _body(_code(APIC), "ap_park")
    assert re.search(r"cli", park) and re.search(r"while true", park) and "hlt" in park, park


def test_bsp_opens_then_abandons_on_timeout():
    body = _body(_code(APIC), "ap_boot_one")
    begin = body.find("cpu_map_boot_begin(cpu_idx)")
    init = body.find("IPI_DELIVERY_INIT")
    assert 0 <= begin < init, "the boot must be opened before INIT"
    timeout = body.find("TIMEOUT")
    abandon = body.find("cpu_map_boot_abandon(cpu_idx)")
    assert 0 <= abandon < timeout, "TIMEOUT printed without abandoning the boot"
    # Abandoning also empties the trampoline's stack slot.
    assert re.search(r"atomic_xchg\(\s*AP_STACK_SLOT as \*u64,\s*0\s*\)", body), body
    # Still pause-free of iteration counts: deadlines only (#4181).
    assert "deadline_after_us(" in body and not re.search(r"while \w+ < \d{4,}", body)


def test_trampoline_takes_the_stack_exclusively():
    asm = _code(TRAMPOLINE)
    lm = asm[asm.find("ap_lm64:"):asm.find("ap_halt:")]
    assert not re.search(r"movq\s+\(AP_TRAMPOLINE_BASE \+ AP_STACK_OFFSET\), %rsp", lm), \
        "the stack is read, not taken: two CPUs can share it"
    assert re.search(r"xchgq\s+%rsp, \(AP_TRAMPOLINE_BASE \+ AP_STACK_OFFSET\)", lm), lm
    assert re.search(r"testq\s+%rsp, %rsp\s*\n\s*jz\s+ap_halt", lm), "an empty slot must halt"
    xchg = lm.find("xchgq")
    call = lm.find("call *%rax")
    assert 0 <= xchg < call


def test_stack_slot_constant_matches_trampoline():
    m = re.search(r"^const AP_STACK_SLOT: u64 = (0x[0-9A-Fa-f]+)$", _code(APIC), re.M)
    assert m, "apic.ritz has no AP_STACK_SLOT"
    t = TRAMPOLINE.read_text()
    base = int(re.search(r"\.set AP_TRAMPOLINE_BASE, (0x[0-9A-Fa-f]+)", t).group(1), 16)
    off = int(re.search(r"\.set AP_STACK_OFFSET, (0x[0-9A-Fa-f]+)", t).group(1), 16)
    assert int(m.group(1), 16) == base + off
