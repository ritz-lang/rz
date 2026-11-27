"""Harland's IST layout: no two vectors that can nest share an IST stack (AGAST #4628).

An IST gate always loads RSP from its TSS slot. NMI, #MC, #DF, #SS, #GP and
#PF all used IST1, so a #GP or #PF inside the NMI or #MC handler (or an NMI
inside a #GP/#PF handler) restarted at the top of IST1, over the interrupted
handler's frame, and that handler then returned to garbage.

Now, as Linux does:

  * NMI has IST4 and #MC IST5, each alone on its stack; #DF and #SS share
    IST1 (#DF is fatal); IRQs keep IST2 and the tick IST3.
  * #GP and #PF use no IST: they run on the stack they interrupt (TSS.rsp0
    from ring 3). A kernel stack overflow can't push the #PF frame and becomes
    a #DF, which reports the guard page from CR2.
  * percpu.ritz gives every CPU a guard-paged stack per IST slot, and gdt.ritz
    fills TSS.ist1-5 (CPU 0's early fallbacks included).
  * An AP in the SMP self-test points TSS.rsp0 at the stack its syscalls use:
    its CPU_KSTACK page is its bootstrap stack, where a ring-3 fault would
    now land.
  * the "ist-nest" boot self-test takes a #GP and a #PF inside the NMI
    handler: each must be caught, push below the NMI's frame, and return,
    and the NMI must then return to its probe.

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
IDT = X86 / "idt.ritz"
GDT = X86 / "gdt.ritz"
PERCPU = X86 / "percpu.ritz"
CPU_SMP = X86 / "cpu_smp.ritz"
EXCEPTIONS = X86 / "exceptions.ritz"
NMI_PROBE = X86 / "nmi_probe.ritz"
ISR_S = KERNEL / "isr_stubs.s"
POSTINIT = KERNEL / "src" / "postinit.ritz"
TIER1 = HARLAND / "tools" / "test_tier1_boot.sh"

NMI, DF, SS, GP, PF, MC = 2, 8, 12, 13, 14, 18
TIMER, IRQ1 = 32, 33


def _code(path):
    """The file with comments stripped (both Ritz and GAS use '#')."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _ritz_fn(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


def _gate_ists():
    """vector -> IST slot, from idt_init's idt_set_gate calls."""
    code = _code(IDT)
    consts = {name: int(val) for name, val in re.findall(r"^const (IST_\w+): u8 = (\d+)$", code, re.M)}
    ists = {}
    for vec, ist in re.findall(r"idt_set_gate\((\d+), \w+ as u64, cs, (\w+),", code):
        ists[int(vec)] = consts[ist] if ist in consts else int(ist)
    return ists


# --- the IDT -------------------------------------------------------------------

def test_nmi_and_machine_check_each_have_an_ist_stack_of_their_own():
    ists = _gate_ists()
    for vec in (NMI, MC):
        assert ists[vec] != 0, f"vector {vec} must use an IST stack"
        others = [v for v, ist in ists.items() if ist == ists[vec] and v != vec]
        assert not others, f"vector {vec} shares IST{ists[vec]} with {others}"


def test_gp_and_pf_run_on_the_interrupted_stack():
    ists = _gate_ists()
    assert ists[GP] == 0 and ists[PF] == 0, "#GP/#PF must not use an IST stack"


def test_double_fault_and_stack_fault_share_a_separate_ist():
    ists = _gate_ists()
    assert ists[DF] != 0 and ists[DF] == ists[SS]
    users = sorted(v for v, ist in ists.items() if ist == ists[DF])
    assert users == [DF, SS], f"IST{ists[DF]} must hold only #DF and #SS, not {users}"
    assert ists[DF] not in (ists[TIMER], ists[IRQ1], ists[NMI], ists[MC])


# --- the stacks behind the slots ------------------------------------------------

def test_every_ist_slot_the_idt_uses_has_a_per_cpu_stack():
    used = sorted({ist for ist in _gate_ists().values() if ist})
    percpu = _code(PERCPU)
    count = int(re.search(r"CPU_STACK_COUNT: i32 = (\d+)", percpu).group(1))
    pages = int(re.search(r"CPU_STACK_PAGES: u64 = (\d+)", percpu).group(1))
    # One per IST slot, plus the kernel stack and the idle context's (#4879).
    assert count == max(used) + 2, "one stack per IST slot, plus the kernel and idle stacks"
    assert re.search(rf"CPU_IDLE: i32 = {count - 1}$", percpu, re.M)
    assert pages == 2 * count, "a guard page and a stack each"
    bringup = _ritz_fn(percpu, "cpu_bringup")
    for n in used:
        assert re.search(rf"CPU_IST{n}: i32 = {n}$", percpu, re.M), n
        assert f"cpu_stack_top(cpu_idx, CPU_IST{n})" in bringup, n


def test_tss_fill_sets_every_used_slot():
    used = sorted({ist for ist in _gate_ists().values() if ist})
    gdt = _code(GDT)
    fill = _ritz_fn(gdt, "tss_fill")
    for n in used:
        assert f"tsses[cpu_idx].ist{n} = ist{n}" in fill, n
    args = ", ".join(f"ist{n}" for n in used)
    assert f"tss_fill(cpu_idx, rsp0, {args})" in _ritz_fn(gdt, "gdt_init_cpu")
    # CPU 0's early fallbacks: one distinct static stack per slot.
    early = _ritz_fn(gdt, "gdt_init")
    stacks = re.findall(r"\(@(\w+)\[0\] as u64\) \+ 4096", early)
    assert len(stacks) == len(used) + 1 and len(set(stacks)) == len(stacks), stacks


def test_double_fault_reports_a_guard_page_hit():
    handler = _ritz_fn(_code(EXCEPTIONS), "exception_handler")
    assert "(vec == 14 or vec == 8) and syscall_stack_guard_hit(read_cr2())" in handler


def test_ap_points_rsp0_at_its_syscall_stack():
    run = _ritz_fn(_code(CPU_SMP), "smp_ap_run")
    top = "cpu_stack_top(cpu_idx, CPU_IST1)"
    assert f"kstack_set_current({top})" in run
    assert f"gdt_set_kernel_stack_cpu(cpu_idx, {top})" in run
    assert run.index("gdt_set_kernel_stack_cpu(") < run.index("jump_to_userspace(")


# --- the "ist-nest" boot self-test ------------------------------------------------

def test_ist_nest_faults_take_a_gp_then_a_pf():
    asm = _code(ISR_S)
    body = asm[asm.index("\nist_nest_faults:"):asm.index(".size ist_nest_faults")]
    labels = ["ist_nest_gp_at:", "ist_nest_gp_resume:", "ist_nest_pf_at:", "ist_nest_pf_resume:"]
    pos = [body.index(lab) for lab in labels]
    assert pos == sorted(pos)
    assert "movabsq $0x8000000000000000, %rax" in body[:pos[0]], "non-canonical address for the #GP"
    assert "movq (%rax), %rax" in body[pos[0]:pos[1]]
    assert "movq (%rdi), %rax" in body[pos[2]:pos[3]], "the unmapped address for the #PF"
    for lab in labels:
        assert f".global {lab[:-1]}" in asm, lab


def test_ist_nest_catch_resumes_only_its_own_faults():
    probe = _code(NMI_PROBE)
    catch = _ritz_fn(probe, "ist_nest_catch")
    assert "if not ist_nest_in_nmi or (cs & 3) != 0" in catch
    assert "vector == GP_VECTOR and rip == ist_nest_gp_at as u64" in catch
    assert "return ist_nest_gp_resume as u64" in catch
    assert "vector == PF_VECTOR and rip == ist_nest_pf_at as u64" in catch
    assert "return ist_nest_pf_resume as u64" in catch
    nmi = _ritz_fn(probe, "nmi_probe_catch")
    assert nmi.index("ist_nest_in_nmi = true") < nmi.index("ist_nest_faults(") < nmi.index("ist_nest_in_nmi = false")
    assert nmi.index("ist_nest_faults(") < nmi.index("nmi_probe_mark()")
    handler = _ritz_fn(_code(EXCEPTIONS), "exception_handler")
    at = handler.index("ist_nest_catch(")
    assert at < handler.index("if fault_on_syscall_iret(frame)")
    assert "(*frame).rip = nest_resume" in handler


def test_ist_nest_selftest_requires_frames_below_the_nmi():
    probe = _code(NMI_PROBE)
    test = _ritz_fn(probe, "ist_nest_selftest")
    assert "nmi_gs_selftest(x2apic, icr, apic_id)" in test
    for why in ("the NMI did not return to the probe intact",
                "the #GP inside the NMI handler was not caught",
                "the #PF inside the NMI handler was not caught",
                "a fault inside the NMI handler did not push below the NMI's frame"):
        assert why in NMI_PROBE.read_text(), why   # raw: "#GP" isn't a comment
    below = _ritz_fn(probe, "ist_nest_below_nmi")
    assert "fault < ist_nest_nmi_frame" in below and "IST_NEST_REACH" in below


def test_ist_nest_is_a_gated_boot_test():
    post = _code(POSTINIT)
    assert re.search(r'boot_test_result\("ist-nest", ist_nest_selftest\(', post)
    assert "cpu_stack_guard(cpu_index(), CPU_KSTACK)" in post
    names = re.search(r'^BOOT_TESTS="([^"]*)"', TIER1.read_text(), re.M).group(1).split()
    assert "ist-nest" in names
