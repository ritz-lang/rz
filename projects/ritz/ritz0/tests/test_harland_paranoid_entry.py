"""Harland's NMI and #MC entries decide GS by MSR_GS_BASE (AGAST #4612).

Between an exit's `swapgs` and its `sysretq`/`iretq` (syscall_entry's two
exits, jump_to_userspace, the ISR exits) and between SYSCALL and
syscall_entry's first `swapgs`, the CPU is in ring 0 with the user's GS. An
NMI or #MC can land there: neither is maskable by IF. SWAPGS_IF_USER decides
by the frame's CS, sees the kernel's, does not swap, and the handler would
run on the user's GS_BASE.

Now (Linux's paranoid entry):

  * isr_stubs.s ISR_PARANOID (vectors 2 and 18): rdmsr MSR_GS_BASE; if it is
    not one of syscall_entry.s's percpu_areas, swapgs and remember (in the
    callee-saved %ebx) to swap back on the way out. It never looks at CS.
  * the "nmi-gs" boot self-test (arch/x86_64/nmi_probe.ritz) sends this CPU
    an NMI while it sits in ring 0 on the user's GS (isr_stubs.s
    nmi_gs_probe) and requires the handler to have run on this CPU's area and
    the exit to have put the user's GS back.

And #4610's ring-0 fixup -- a #GP on syscall_exit_iret, which faults with
the kernel's CS after the exit's swapgs -- is driven on every CPU, TCG
included: syscall_entry.s sysret_ring0_iret_probe IRETQs from
syscall_exit_iret to a frame with a null SS, which #GPs in ring 0 on any
x86-64. The "sysret" self-test requires vector 13 at syscall_exit_iret with
CS 8 and GS back on this CPU's area. Under KVM the real non-canonical case
does the same: tools/test_tier1_boot.sh `kvm` boots it (skipped without a
usable /dev/kvm) and requires the "[sysret] ... CS 8" verdict.

The runtime proof is the QEMU boot; these pin the structure.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parents[1]
REPO = RITZ0_DIR.parents[2]
HARLAND = REPO / "projects" / "harland"
KERNEL = HARLAND / "kernel"
SRC = KERNEL / "src"
ISR_S = KERNEL / "isr_stubs.s"
ENTRY_S = KERNEL / "syscall_entry.s"
EXCEPTIONS = SRC / "arch" / "x86_64" / "exceptions.ritz"
NMI_PROBE = SRC / "arch" / "x86_64" / "nmi_probe.ritz"
SYSRET_CATCH = SRC / "arch" / "x86_64" / "sysret_catch.ritz"
CPU_SMP = SRC / "arch" / "x86_64" / "cpu_smp.ritz"
POSTINIT = SRC / "postinit.ritz"
TIER1 = HARLAND / "tools" / "test_tier1_boot.sh"
MAIN_YML = REPO / ".github" / "workflows" / "main.yml"


def _code(path):
    """The file with comments stripped (both Ritz and GAS use '#')."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _macro(asm, name):
    start = asm.index(f".macro {name}")
    return asm[start:asm.index(".endm", start)]


def _asm_fn(asm, name):
    start = asm.index(f"\n{name}:")
    return asm[start:asm.index(f".size {name}", start)]


def _ritz_fn(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


# --- the paranoid entry ------------------------------------------------------

def test_nmi_and_machine_check_use_the_paranoid_entry():
    isr = _code(ISR_S)
    assert re.search(r"^ISR_PARANOID 2\b", isr, re.M), "NMI must take the paranoid entry"
    assert re.search(r"^ISR_PARANOID 18\b", isr, re.M), "#MC must take the paranoid entry"
    assert not re.search(r"^ISR_NOERR\s+(2|18)\b", isr, re.M)
    # Every other stub keeps the CS-based entry: only 2 and 18 are paranoid.
    assert sorted(re.findall(r"^ISR_PARANOID (\d+)", isr, re.M)) == ["18", "2"]


def test_paranoid_entry_decides_by_gs_base_not_cs():
    isr = _code(ISR_S)
    assert re.search(r"^\.set MSR_GS_BASE, 0xC0000101$", isr, re.M)
    body = _macro(isr, "ISR_PARANOID num")
    # It never asks the frame's CS.
    assert "testq $3" not in body and "SWAPGS_IF_USER" not in body
    entry = body[:body.index("call exception_handler")]
    exit_ = body[body.index("call exception_handler"):]
    # GS_BASE, read before anything touches per-CPU state ...
    assert entry.index("movl $MSR_GS_BASE, %ecx") < entry.index("rdmsr")
    # ... compared against this kernel's per-CPU areas ...
    assert "leaq percpu_areas(%rip)" in entry
    assert "leaq percpu_areas_end(%rip)" in entry
    # ... swapping only when it is not one, and noting that in %ebx, which
    # exception_handler (SysV) preserves.
    assert entry.count("swapgs") == 1
    assert "xorl %ebx, %ebx" in entry
    assert entry.index("xorl %ebx, %ebx") < entry.index("swapgs") < entry.index("movl $1, %ebx")
    # The exit swaps back the same way, and returns itself (isr_common's exit
    # would decide by CS again).
    assert "testl %ebx, %ebx" in exit_
    assert exit_.count("swapgs") == 1
    assert exit_.index("testl %ebx, %ebx") < exit_.index("swapgs") < exit_.index("iretq")
    assert "isr_common" not in body


def test_paranoid_frame_matches_the_interrupt_frame():
    """Same push order as ISR_NOERR, so exception_handler reads the same
    InterruptFrame: dummy error, vector, then RAX .. R15."""
    isr = _code(ISR_S)
    pushes = lambda m: re.findall(r"pushq (\S+)", _macro(isr, m))
    assert pushes("ISR_PARANOID num") == pushes("ISR_NOERR num")
    pops = re.findall(r"popq (\S+)", _macro(isr, "ISR_PARANOID num"))
    assert pops == list(reversed(pushes("ISR_NOERR num")[2:]))


def test_percpu_areas_are_visible_to_the_isr_stubs():
    asm = _code(ENTRY_S)
    assert re.search(r"^\.global percpu_areas$", asm, re.M)
    assert re.search(r"^\.global percpu_areas_end$", asm, re.M)


# --- the "nmi-gs" boot self-test ----------------------------------------------

def test_nmi_gs_probe_sends_the_nmi_on_the_users_gs():
    isr = _code(ISR_S)
    probe = _asm_fn(isr, "nmi_gs_probe")
    first, second = [m.start() for m in re.finditer(r"swapgs", probe)]
    send = probe.index("wrmsr")                       # x2APIC ICR
    mmio = probe.index("movl %eax, (%rdi)")           # xAPIC ICR low: sends
    assert first < send < second and first < mmio < second
    # It waits for the handler (nmi_probe_mark) before swapping back, and
    # reports GS_BASE as the NMI's exit left it.
    assert "cmpl $0, nmi_probe_hit(%rip)" in probe
    assert probe.index("movl $MSR_GS_BASE, %ecx") < second
    mark = _asm_fn(isr, "nmi_probe_mark")
    assert "movl $1, nmi_probe_hit(%rip)" in mark


def test_nmi_gs_selftest_checks_both_halves():
    probe = _code(NMI_PROBE)
    catch = _ritz_fn(probe, "nmi_probe_catch")
    assert "rdmsr(GS_BASE_MSR)" in catch and "nmi_probe_mark()" in catch
    test = _ritz_fn(probe, "nmi_gs_selftest")
    # A user GS that can't be mistaken for 0 or a kernel address.
    assert "wrmsr(KERNEL_GS_BASE_MSR, USER_GS_SENTINEL)" in test
    assert "nmi_gs_probe(" in test
    for why in ("the NMI never arrived", "the NMI came from ring 3",
                "the NMI handler ran on the user's GS",
                "the NMI's exit did not restore the user's GS",
                "GS is not back on this CPU's area"):
        assert why in probe, why
    exc = _code(EXCEPTIONS)
    handler = _ritz_fn(exc, "exception_handler")
    # Ahead of everything else, so a mis-swapped NMI still gets recorded.
    first = handler.index("if (*frame).vector == 2 and nmi_probe_catch(")
    assert first < handler.index("if fault_on_syscall_iret(frame)")
    post = _code(POSTINIT)
    assert re.search(r'boot_test_result\("nmi-gs", nmi_gs_selftest\(x2apic_mode != 0, lapic_icr_lo_mmio\(\), lapic_id\(\)\)\)', post)


def test_nmi_gs_is_a_gated_boot_test():
    names = re.search(r'^BOOT_TESTS="([^"]*)"', TIER1.read_text(), re.M).group(1).split()
    assert "nmi-gs" in names


# --- #4610's ring-0 fixup, driven on any CPU -----------------------------------

def test_ring0_iret_probe_faults_on_syscall_exit_iret():
    asm = _code(ENTRY_S)
    probe = _asm_fn(asm, "sysret_ring0_iret_probe")
    # Resumable through smp_test_resume_bsp, like smp_test_enter_user.
    assert "movq %rsp, smp_test_bsp_rsp(%rip)" in probe
    # A null SS for a ring-3 return: IRETQ #GPs in ring 0, TCG included.
    frame = probe[probe.index("pushq $0"):probe.index("swapgs")]
    assert re.findall(r"pushq (\S+)", frame) == ["$0", "%rsi", "$2", "$USER_CS", "%rdi"]
    # The exit's GS state, then the exit's own IRETQ (past its counter).
    assert probe.index("swapgs") < probe.index("jmp syscall_exit_iret")


def test_sysret_selftest_requires_the_ring0_catch():
    catch = _code(SYSRET_CATCH)
    test = _ritz_fn(catch, "sysret_ring0_selftest")
    assert "sysret_ring0_iret_probe(" in test
    assert "syscall_exit_iret as u64" in test
    for why in ("the ring-0 IRETQ fault was not caught",
                "the ring-0 IRETQ fault was not vector 13 at syscall_exit_iret in ring 0",
                "GS is not back on this CPU's area after the ring-0 IRETQ fault"):
        assert why in catch, why
    smp = _ritz_fn(_code(CPU_SMP), "sysret_selftest")
    assert "sysret_ring0_selftest()" in smp


# --- the KVM boot ---------------------------------------------------------------

def test_tier1_has_a_kvm_mode_that_skips_without_kvm():
    sh = TIER1.read_text()
    assert re.search(r"case \"\$MODE\" in native\|grub\|kvm\|all\)", sh)
    # Skipped, not failed, where KVM can't run, and decided before any build.
    # tools/test_tier1_boot_kvm_skip.py drives each skip (absent, unopenable,
    # accelerator fails) and the FAIL of a broken boot under working KVM.
    gate = sh.index('[ "$MODE" = kvm ]; then\n    KVM_DEV=')
    assert gate < sh.index('if [ "${SKIP_BUILD:-0}" != "1" ]')
    assert '( exec 3<>"$KVM_DEV" )' in sh, "open the device read-write, not [ -r ]/[ -w ]"
    assert "-accel kvm" in sh
    # It requires the real non-canonical exit's fault in ring 0.
    assert "sysret_ring0 kvm" in sh
    fn = sh[sh.index("sysret_ring0() {"):]
    fn = fn[:fn.index("\n}\n")]
    assert r"CS 8$" in fn
    # `all` (the default, and what the fake-QEMU tests run) has no KVM boot.
    assert re.search(r'if \[ "\$MODE" = kvm \]', sh)


def test_ci_boots_harland_under_kvm():
    wf = MAIN_YML.read_text()
    assert "bash projects/harland/tools/test_tier1_boot.sh kvm" in wf
