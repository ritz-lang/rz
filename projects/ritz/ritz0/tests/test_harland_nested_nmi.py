"""Harland's NMI entry survives a nested NMI (AGAST #4650).

NMI runs alone on IST4 (AGAST #4628), but the CPU unblocks NMIs at any
IRETQ: one returning from a #GP/#PF/#DB taken inside the NMI handler. A
second NMI then restarts at the top of IST4, over the first's IRET frame,
and the first NMI returns to garbage. As Linux's asm_exc_nmi does:

  * isr_stubs.s isr_stub_2 keeps an "NMI executing" slot, an "iret" frame
    and an "outermost" frame below the CPU's. A nested NMI (from ring 0, and
    RIP in the repeat window, or "executing" set, or RSP on this stack with
    DF set) runs no handler: it rewrites the iret frame to return to
    .Lnmi_repeat and IRETQs. The first NMI's IRETQ then runs the paranoid
    body again, GS check included (AGAST #4612).
  * The window from the first NMI's `std` to its IRETQ is told apart by
    RFLAGS.DF, so SYSCALL must clear DF: SFMASK holds IF | DF.
  * The "nmi-nest" boot self-test sends a second self-NMI from inside the
    first, after the "ist-nest" faults' IRETs, and requires it latched,
    handled after the first's handler on this CPU's GS, and the first to
    return to its probe.

The runtime proof is the QEMU boot (tools/test_tier1_boot.sh, TCG and KVM);
these pin the structure.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parents[1]
REPO = RITZ0_DIR.parents[2]
HARLAND = REPO / "projects" / "harland"
KERNEL = HARLAND / "kernel"
X86 = KERNEL / "src" / "arch" / "x86_64"
ISR_S = KERNEL / "isr_stubs.s"
ENTRY_S = KERNEL / "syscall_entry.s"
ENTRY_RITZ = KERNEL / "src" / "syscall" / "runtime" / "entry.ritz"
NMI_PROBE = X86 / "nmi_probe.ritz"
PERCPU = X86 / "percpu.ritz"
GDT = X86 / "gdt.ritz"
POSTINIT = KERNEL / "src" / "postinit.ritz"
TIER1 = HARLAND / "tools" / "test_tier1_boot.sh"
CI_BOOT = REPO / "projects" / "ritz" / "tools" / "test_ci_harland_boot.py"
SOCK_PATH = REPO / "projects" / "ritz" / "tools" / "test_tier1_boot_sock_path.py"


def _code(path):
    """The file with comments stripped (both Ritz and GAS use '#')."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _ritz_fn(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


def _nmi_parts():
    """isr_stub_2 split at its labels: {label: its instructions}."""
    asm = _code(ISR_S)
    stub = asm[asm.index("\nisr_stub_2:"):]
    stub = stub[:stub.index("iretq", stub.index("PARANOID_BODY 2")) + len("iretq")]
    parts, label = {}, "isr_stub_2"
    for line in stub.splitlines()[2:]:
        m = re.match(r"^(\.?\w+):$", line.strip())
        if m:
            label = m.group(1)
            continue
        if line.strip():
            parts.setdefault(label, []).append(" ".join(line.split()))
    return parts


def test_nmi_stub_is_its_own_entry_on_the_paranoid_body():
    parts = _nmi_parts()
    assert list(parts) == ["isr_stub_2", "1", ".Lnmi_nested", ".Lnmi_nested_out",
                           ".Lnmi_first", ".Lnmi_repeat", ".Lnmi_end_repeat"]
    assert parts["isr_stub_2"][:2] == ["cld", "pushq %rdx"]
    assert parts[".Lnmi_end_repeat"][0] == "PARANOID_BODY 2"


def test_nested_checks_ring_repeat_window_executing_and_df():
    parts = _nmi_parts()
    entry = parts["isr_stub_2"]
    # From ring 3 nothing is nested.
    assert entry[2:4] == ["testq $3, 16(%rsp)", "jnz .Lnmi_first"]
    # RIP in [.Lnmi_repeat, .Lnmi_end_repeat): return at once.
    assert entry[4:10] == ["leaq .Lnmi_repeat(%rip), %rdx", "cmpq %rdx, 8(%rsp)", "jb 1f",
                           "leaq .Lnmi_end_repeat(%rip), %rdx", "cmpq %rdx, 8(%rsp)",
                           "jb .Lnmi_nested_out"]
    # "NMI executing" (slot 10, just below the saved RDX), off %rdx.
    assert parts["1"][:3] == ["movq %rsp, %rdx", "cmpq $1, -8(%rdx)", "je .Lnmi_nested"]
    # RSP within this stack, and DF set: the first NMI's last instructions.
    assert parts["1"][3:] == ["leaq 48(%rsp), %rdx", "cmpq %rdx, 32(%rsp)", "ja .Lnmi_first",
                              "subq $NMI_STACK_SIZE, %rdx", "cmpq %rdx, 32(%rsp)", "jb .Lnmi_first",
                              "testq $RFLAGS_DF, 24(%rsp)", "jz .Lnmi_first"]


def test_nested_nmi_rewrites_the_iret_frame_and_runs_no_handler():
    parts = _nmi_parts()
    nested = parts[".Lnmi_nested"]
    assert nested == ["lock incl nmi_repeats_latched(%rip)", "subq $8, %rsp", "movq %rsp, %rdx",
                      "subq $80, %rdx", "pushq $KERNEL_DS", "pushq %rdx", "pushfq",
                      "pushq $KERNEL_CS", "leaq .Lnmi_repeat(%rip), %rdx", "pushq %rdx",
                      "addq $48, %rsp"]
    assert parts[".Lnmi_nested_out"] == ["popq %rdx", "iretq"]
    asm = _code(ISR_S)
    assert re.search(r"^\.set KERNEL_CS, 0x08$", asm, re.M)
    assert re.search(r"^\.set KERNEL_DS, 0x10$", asm, re.M)
    assert re.search(r"^\.set RFLAGS_DF, 0x400$", asm, re.M)


def test_first_nmi_copies_the_outermost_frame_and_repeats_from_it():
    parts = _nmi_parts()
    assert parts[".Lnmi_first"] == ["movq (%rsp), %rdx", "pushq $0", "subq $40, %rsp",
                                    ".rept 5", "pushq 88(%rsp)", ".endr"]
    # Every GPR is the interrupted code's here: the copy uses none.
    assert parts[".Lnmi_repeat"] == ["movq $1, 80(%rsp)", ".rept 5", "popq 32(%rsp)", ".endr",
                                     "subq $40, %rsp"]
    # After the body: the iret frame, DF set, executing cleared, IRETQ.
    assert parts[".Lnmi_end_repeat"][1:] == ["addq $40, %rsp", "std", "movq $0, 40(%rsp)", "iretq"]


def test_nmi_stack_size_is_ist4s():
    asm = _code(ISR_S)
    size = int(re.search(r"^\.set NMI_STACK_SIZE, (\d+)$", asm, re.M).group(1))
    percpu = _code(PERCPU)
    pages = int(re.search(r"CPU_STACK_PAGES: u64 = (\d+)", percpu).group(1))
    count = int(re.search(r"CPU_STACK_COUNT: i32 = (\d+)", percpu).group(1))
    assert pages == 2 * count and size == 4096, "a guard page and one 4 KiB stack each"
    assert re.search(rf"^var nmi_stack: \[{size}\]u8$", _code(GDT), re.M)


def test_syscall_clears_df():
    asm = _code(ENTRY_S)
    init = asm[asm.index("\nsyscall_msr_init:"):asm.index(".size syscall_msr_init")]
    assert re.search(r"^\.set RFLAGS_DF, 0x400$", asm, re.M)
    assert "movl $(RFLAGS_IF | RFLAGS_DF), %eax" in init
    ritz = _code(ENTRY_RITZ)
    assert "const RFLAGS_DF: u64 = 0x400" in ritz
    assert "wrmsr(MSR_SFMASK, RFLAGS_IF | RFLAGS_DF)" in _ritz_fn(ritz, "syscall_init")


# --- the "nmi-nest" boot self-test ------------------------------------------------

def test_nmi_nest_sends_the_second_nmi_after_the_faults():
    probe = _code(NMI_PROBE)
    catch = _ritz_fn(probe, "nmi_probe_catch")
    # The second NMI's handler is caught first, and notes whether it ran
    # inside the first's.
    assert catch.index("if nmi_nest_second_due") < catch.index("if not nmi_probe_armed")
    assert "nmi_nest_second_inside = nmi_nest_outer_running" in catch
    assert "nmi_nest_second_gs = rdmsr(GS_BASE_MSR)" in catch
    # Sent after the faults' IRETs have unblocked NMIs.
    assert catch.index("ist_nest_in_nmi = false") < catch.index("nmi_nest_send_second()")
    send = _ritz_fn(probe, "nmi_nest_send_second")
    assert send.index("nmi_nest_outer_running = true") < send.index("nmi_self_send(") \
        < send.index("nmi_nest_outer_running = false")
    assert "nmi_nest_latched = nmi_repeats() != before" in send


def test_nmi_nest_selftest_requires_latch_repeat_and_return():
    test = _ritz_fn(_code(NMI_PROBE), "nmi_nest_selftest")
    assert "ist_nest_selftest(x2apic, icr, apic_id, unmapped)" in test
    assert "nmi_nest_second_gs != area" in test
    for why in ("the first NMI did not return to the probe intact",
                "the second NMI's handler ran inside the first's",
                "the second NMI was not latched by the nested entry",
                "the first NMI did not repeat for the second",
                "the repeated NMI handler ran on the user's GS"):
        assert why in test, why


def test_nmi_nest_is_a_gated_boot_test():
    assert re.search(r'boot_test_result\("nmi-nest", nmi_nest_selftest\(', _code(POSTINIT))
    names = re.search(r'^BOOT_TESTS="([^"]*)"', TIER1.read_text(), re.M).group(1).split()
    assert "nmi-nest" in names
    assert '"nmi-nest"' in CI_BOOT.read_text()
    assert " nmi-nest " in SOCK_PATH.read_text()
