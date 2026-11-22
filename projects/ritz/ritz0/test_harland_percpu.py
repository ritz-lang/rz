"""Harland's per-CPU syscall stacks and the two-CPU boot proof (AGAST #4192).

Follow-up from #1877/#3629. Until this ticket syscall_entry.s kept one set of
user-frame globals (user_rsp_save, syscall_user_*), one kernel-stack pointer
(kstack_current_top) and one TSS (gdt.ritz tss, rsp0 + IST1/2/3 stacks). That
is safe only while the APs never leave the kernel: the BSP alone takes SYSCALL.
After this ticket the APs do enter ring 3 (for the self-test) and then idle in
the kernel with interrupts on, ready for #4220's AP-call IPIs.

This ticket makes the syscall machinery per CPU and proves it:

  * arch/x86_64/percpu.ritz gives every CPU a per-CPU area (syscall_entry.s
    percpu_areas, reached through GS with swapgs at entry/exit), four
    guard-paged kernel stacks in the kernel half (syscall, IST1/2/3), a TSS
    with those stacks, an IDT and its own SYSCALL MSRs.
  * arch/x86_64/cpu_smp.ritz runs after ap_boot_all: every CPU enters a
    ring-3 stub and SYSCALLs, the handler barriers until all of them are
    inside, and the BSP then checks the recorded kernel stacks and per-CPU
    areas are distinct. tools/test_tier1_boot.sh requires its verdict, and
    `make test-smp` runs the acceptance boot at -smp 2.

The runtime checks are the QEMU boots; these are the structural ones.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parent
HARLAND = RITZ0_DIR.parents[1] / "harland"
KERNEL = HARLAND / "kernel"
SRC = KERNEL / "src"
ENTRY_S = KERNEL / "syscall_entry.s"
ISR_S = KERNEL / "isr_stubs.s"
GDT = SRC / "arch" / "x86_64" / "gdt.ritz"
PERCPU = SRC / "arch" / "x86_64" / "percpu.ritz"
CPU_SMP = SRC / "arch" / "x86_64" / "cpu_smp.ritz"
APIC = SRC / "arch" / "x86_64" / "apic.ritz"
STACK = SRC / "syscall" / "stack.ritz"
MAIN = SRC / "main.ritz"
NUMBERS = SRC / "syscall" / "numbers.ritz"
ENTRY = SRC / "syscall" / "runtime" / "entry.ritz"
TIER1 = HARLAND / "tools" / "test_tier1_boot.sh"


def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


# --- the per-CPU area and GS convention -------------------------------------

def test_per_cpu_area_is_gs_addressed_and_big_enough_for_max_cpus():
    asm = _code(ENTRY_S)
    assert re.search(r"^\.set PERCPU_SLOTS, (\d+)", asm, re.M)
    slots = int(re.search(r"^\.set PERCPU_SLOTS, (\d+)", asm, re.M).group(1))
    max_cpus = int(re.search(r"^pub const MAX_CPUS: i32 = (\d+)$",
                             (SRC / "arch/x86_64/cpu_map.ritz").read_text(), re.M).group(1))
    assert slots == max_cpus, "one per-CPU area per CPU index"
    assert re.search(r"^percpu_areas:\n\s+\.space PERCPU_SIZE \* PERCPU_SLOTS", asm, re.M)
    for off in ("PC_SELF", "PC_CPU_INDEX", "PC_KSTACK_TOP", "PC_USER_RSP",
                "PC_USER_RIP", "PC_USER_RFLAGS", "PC_USER_RAX"):
        assert re.search(rf"^\.global {off}$\n\.set {off},", asm, re.M), off


def test_syscall_entry_swaps_gs_and_uses_this_cpus_frame():
    asm = _code(ENTRY_S)
    entry = asm[asm.index("\nsyscall_entry:"):asm.index(".size syscall_entry")]
    # swapgs first: in ring 3 GS is the user's, in the kernel this CPU's area.
    assert entry.index("swapgs") < entry.index("movq %rsp, %gs:PC_USER_RSP")
    assert "movq %gs:PC_KSTACK_TOP, %rsp" in entry
    assert "pushq %gs:PC_USER_RSP" in entry
    # And back to the user's GS for the return.
    assert entry.rindex("swapgs") > entry.index("pushq $0x1B") > entry.index("swapgs")
    # The single-CPU globals must be gone, not merely unused.
    for gone in ("user_rsp_save", "syscall_user_rip", "syscall_user_rsp",
                 "syscall_user_rflags", "syscall_user_rax", "kstack_current_top"):
        assert not re.search(rf"^{gone}:", asm, re.M), f"{gone} is back"


def test_ring3_entries_and_interrupts_keep_the_gs_convention():
    asm = _code(ENTRY_S)
    for fn in ("jump_to_userspace", "jump_to_userspace_with_args"):
        body = asm[asm.index(f"\n{fn}:"):]
        body = body[:body.index(".size")]
        assert body.rindex("swapgs") < body.index("iretq"), fn
    isr = _code(ISR_S)
    # Every stub enters the kernel GS state only for a ring-3 frame, and the
    # common exits restore it only when returning to ring 3.
    assert ".macro SWAPGS_IF_USER_AT cs_off" in isr
    assert isr.count("SWAPGS_IF_USER") >= 3 + 2, "prologue and both exits"
    # An exception with a CPU-pushed error code has CS at 16, not 8: testing
    # 8 would read RIP and leave GS on the user's during the handler.
    err = isr[isr.index(".macro ISR_ERR num"):isr.index(".endm", isr.index(".macro ISR_ERR num"))]
    assert "SWAPGS_IF_USER_AT 16" in err
    for macro in (".macro ISR_NOERR num", ".macro IRQ_STUB num irq"):
        body = isr[isr.index(macro):isr.index(".endm", isr.index(macro))]
        assert "SWAPGS_IF_USER\n" in body, macro
    timer = isr[isr.index("\nirq_stub_timer:"):]
    assert timer.index("SWAPGS_IF_USER") < timer.index("movq %gs:PC_KSTACK_TOP")


# --- per-CPU TSS and stacks --------------------------------------------------

def test_gdt_has_one_tss_descriptor_per_cpu():
    gdt = GDT.read_text()
    max_cpus = int(re.search(r"^pub const MAX_CPUS: i32 = (\d+)$",
                             (SRC / "arch/x86_64/cpu_map.ritz").read_text(), re.M).group(1))
    entries = int(re.search(r"^const GDT_ENTRIES: i32 = (\d+)$", gdt, re.M).group(1))
    first = int(re.search(r"^const GDT_TSS_FIRST: i32 = (\d+)$", gdt, re.M).group(1))
    assert entries == first + 2 * max_cpus, "room for a 16-byte TSS descriptor per CPU"
    assert f"var gdt: [{entries}]GdtEntry" in gdt
    assert f"var tsses: [{max_cpus}]Tss" in gdt
    assert "fn tss_selector(cpu_idx: i32) -> u16" in gdt
    init = _body(gdt, "gdt_init_cpu")
    assert "tss_fill(cpu_idx, rsp0, ist1, ist2, ist3)" in init
    assert "set_tss_entry(GDT_TSS_FIRST + cpu_idx * 2" in init
    assert "tss_load(tss_selector(cpu_idx))" in init


def test_each_cpu_brings_up_its_own_state_before_use():
    percpu = PERCPU.read_text()
    bring = _body(percpu, "cpu_bringup")
    order = ["cpu_stack_alloc(cpu_idx)", "gdt_init_cpu(cpu_idx, ktop,",
             "idt_load_current()", "wrmsr(GS_BASE_MSR, area)", "syscall_msr_init()",
             "kstack_set_current(ktop)"]
    idx = [bring.index(s) for s in order]
    assert idx == sorted(idx), bring
    # The stacks are mapped in the kernel half: every user PML4 shares it.
    assert "CPU_STACK_VA_BASE: u64 = 0xFFFF960000000000" in percpu
    alloc = _body(percpu, "cpu_stack_alloc")
    assert "vmm_unmap_kernel_page(phys)" in alloc and "vmm_map_page(stack_va" in alloc
    assert "SYSCALL_STACK_SENTINEL" in alloc


# --- the boot-time two-CPU proof ---------------------------------------------

def test_stub_syscalls_and_the_handler_barriers():
    smp = CPU_SMP.read_text()
    stub = _body(smp, "smp_write_stub")
    assert "Syscall.Smp as u8" in stub and "0x0F" in stub and "0x05" in stub
    handler = _body(smp, "sys_smp_test_handler")
    assert handler.index("smp_seen_top[cpu] = cpu_kstack_top()") < \
        handler.index("atomic_fetch_add(@smp_in_syscall as *u32, 1)")
    assert "while atomic_load(@smp_in_syscall as *u32) < smp_expected" in handler
    run = _body(smp, "smp_syscall_selftest")
    assert "cpu_map_started(cpu)" in run, "every started AP participates"
    assert run.index("atomic_store(@smp_go as *u32, 1)") < \
        run.index("smp_test_enter_user(SMP_CODE_VA, bsp_stack)"), \
        "the BSP starts the APs before entering ring 3 itself"
    assert "distinct per-CPU stacks and frames" in run, "the boot tests' verdict string"
    assert "SMP_PHASE_DONE" in smp and "smp_test_resume_bsp()" in smp
    # The syscall is not a user ABI: outside the self-test the handler answers
    # ENOSYS (and idles an AP still finishing phase 2).
    assert "smp_bsp_inside == 0" in handler and "Errno.NoSys" in handler


def test_finished_aps_stay_alive_for_the_ap_call_ipi():
    """#4220's AP-call IPI and CPU-local device interrupts need a live AP.

    The self-test must not halt an AP after phase 2, and its syscalls must run
    on a stack the idle/IRQ path can reuse: otherwise the AP is dead to the
    NVMe probe that #4220 runs through vector 240 after boot.
    """
    smp = CPU_SMP.read_text()
    assert "halt_loop" not in smp, "an AP that halts cannot answer an AP call"
    idle = _body(smp, "smp_ap_idle")
    assert "sti_hlt()" in idle and "while true" in idle
    run = _body(smp, "smp_ap_run")
    assert "kstack_set_current(cpu_stack_top(cpu_idx, CPU_IST1))" in run
    handler = _body(smp, "sys_smp_test_handler")
    # Both terminal AP paths (phase 2, and a late phase 2 after the BSP left)
    # idle, never return to ring 3 or halt.
    assert handler.count("smp_ap_idle()") == 2, handler
    assert run.index("kstack_set_current") < run.index("jump_to_userspace")


def test_the_verdict_is_wired_into_the_boot_suites():
    tier1 = TIER1.read_text()
    assert "smp_stacks()" in tier1
    for name in ("native", "grub", "grub-reboot"):
        assert f"smp_stacks {name} || rc=1" in tier1, name
    assert "[smp] syscall stacks OK: $SMP_NCPUS CPUs" in tier1
    makefile = (HARLAND / "Makefile").read_text()
    assert "test-smp:" in makefile
    assert "QEMU_SMP=2 ./tools/test_tier1_boot.sh native" in makefile


def test_smp_is_a_registered_syscall():
    assert re.search(r"^\s+Smp\s*=\s*254\b", NUMBERS.read_text(), re.M)
    assert "syscall_register(Syscall.Smp, sys_smp_test_handler)" in ENTRY.read_text()
