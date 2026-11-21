"""Harland's kernel stacks: big enough, out of .data, and guarded (AGAST #2761).

Every syscall runs on a kernel stack in kernel/syscall_entry.s. It was one
4 KiB syscall_stack in .data, directly above g_child_pid and fs_current;
Tier-1 already peaks at ~8 KiB, and a deep syscall (a knamespace_write
flush, an O_CREAT open) silently overwrote those globals (#2761, #4064).
The fix kept it in .bss at 64 KiB with a sentinel quadword at its bottom
that syscall_stack_check (syscall/stack.ritz) checks when a syscall leaves
the kernel: after every dispatch, and in sys_exit, which leaves the CPU
without returning through syscall_handler.

Since #3629 each process-table slot has its own such stack (proc_kstacks),
each with a sentinel and a guard page: a process blocked or preempted in
the kernel keeps its frames there while others run.

The checks are structural, at source level. The runtime checks are the OVMF
Tier-1 boot's heap_grow test (indium heap_grow_child) and the panic message
syscall_stack_check prints.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parents[1]
KERNEL = RITZ0_DIR.parents[1] / "harland" / "kernel"
ENTRY_S = KERNEL / "syscall_entry.s"
STACK = KERNEL / "src" / "syscall" / "stack.ritz"
RUNTIME = KERNEL / "src" / "syscall" / "runtime"

# What Tier-1 measured (8176 bytes, mmap_isolation) with headroom: 4 KiB was
# the overflowing size.
MIN_STACK = 65536


def _asm():
    """syscall_entry.s with `#` comments stripped."""
    return "\n".join(
        line.split("#", 1)[0].rstrip() for line in ENTRY_S.read_text().splitlines()
    )


def _section_of(asm, label):
    """The last `.section` directive before `label:`."""
    at = asm.index(f"\n{label}:")
    sections = re.findall(r"^\.section\s+(\S+)", asm[:at], re.MULTILINE)
    assert sections, f"no .section before {label}"
    return sections[-1]


def _body(code, fn):
    m = re.search(
        rf"^(?:pub\s+)?fn {fn}\(.*?(?=^\S)", code + "\nEND", re.MULTILINE | re.DOTALL
    )
    assert m, f"no fn {fn}"
    return m.group(0)


def test_syscall_stack_is_in_bss_and_big_enough():
    asm = _asm()
    assert _section_of(asm, "proc_kstacks") == ".bss"
    size = re.search(r"^\.set SYSCALL_STACK_SIZE,\s*(\w+)", asm, re.MULTILINE)
    assert size and int(size.group(1), 0) >= MIN_STACK, size and size.group(0)
    # One guard page plus one stack per process-table slot.
    assert re.search(r"^\.set KSTACK_STRIDE,\s*KSTACK_GUARD_SIZE \+ SYSCALL_STACK_SIZE", asm, re.M)
    assert re.search(r"^\.set KSTACK_GUARD_SIZE,\s*4096", asm, re.M)
    slots = re.search(r"^\.set KSTACK_SLOTS,\s*(\d+)", asm, re.M)
    table = (KERNEL / "src" / "proc" / "table.ritz").read_text()
    assert slots and f"MAX_PROCS: i32 = {slots.group(1)}" in table, "a kernel stack per Proc slot"
    assert re.search(
        r"^proc_kstacks:\s*\n\s*\.space KSTACK_STRIDE \* KSTACK_SLOTS", asm, re.MULTILINE
    )


def test_per_cpu_area_holds_the_syscall_frame():
    """AGAST #4192: one user frame and one kernel-stack pointer per CPU, in the
    area GS points at -- not the globals that two CPUs could clobber."""
    asm = _asm()
    assert _section_of(asm, "percpu_areas") == ".bss"
    for off in ("PC_KSTACK_TOP", "PC_USER_RSP", "PC_USER_RIP", "PC_USER_RFLAGS", "PC_USER_RAX"):
        assert re.search(rf"^\.global {off}$\n\.set {off},", asm, re.M), off
    # The old single-CPU globals are gone.
    for gone in ("user_rsp_save", "syscall_user_rip", "kstack_current_top"):
        assert not re.search(rf"^{gone}:", asm, re.M), f"{gone} is back"
    # syscall_entry runs on this CPU's stack, saved through GS.
    entry = asm[asm.index("\nsyscall_entry:"):asm.index(".size syscall_entry")]
    assert entry.index("swapgs") < entry.index("movq %gs:PC_KSTACK_TOP, %rsp")
    assert "movq %rsp, %gs:PC_USER_RSP" in entry
    assert "movq %rax, %gs:PC_USER_RAX" in entry
    assert "pushq %gs:PC_USER_RSP" in entry
    # ...and returns to the user's GS before iretq.
    assert entry.rindex("swapgs") > entry.index("pushq $0x1B")
    # The accessors read this CPU's area too.
    for fn, off in (("get_syscall_user_rip", "PC_USER_RIP"),
                    ("get_syscall_user_rsp", "PC_USER_RSP"),
                    ("get_syscall_user_rflags", "PC_USER_RFLAGS"),
                    ("kstack_get_current", "PC_KSTACK_TOP")):
        body = asm[asm.index(f"\n{fn}:"):]
        assert f"movq %gs:{off}, %rax" in body.split("ret")[0], fn
    assert "movq %rdi, %gs:PC_KSTACK_TOP" in asm[asm.index("\nkstack_set_current:"):]


def test_tss_and_stacks_are_per_cpu():
    """AGAST #4192: TSS.rsp0 and the IST stacks are per CPU, and every CPU
    loads its own at bring-up; one shared TSS would let two CPUs' IRQs use
    the same stack."""
    gdt = (KERNEL / "src" / "arch" / "x86_64" / "gdt.ritz").read_text()
    assert "var tsses: [64]Tss" in gdt
    assert "tsses[cpu_idx].rsp0 = rsp0" in gdt
    for ist in ("ist1", "ist2", "ist3"):
        assert f"tsses[cpu_idx].{ist} = {ist}" in gdt, ist
    assert "gdt_set_kernel_stack_cpu(cpu_idx: i32, stack_top: u64)" in gdt
    percpu = (KERNEL / "src" / "arch" / "x86_64" / "percpu.ritz").read_text()
    assert "pub fn cpu_bringup(cpu_idx: i32) -> i32" in percpu
    assert "gdt_init_cpu(cpu_idx, ktop," in percpu
    assert "wrmsr(GS_BASE_MSR, area)" in percpu
    # The AP brings itself up before it flags started: ap_boot_all then
    # returns to the self-test with a CPU that can enter ring 3.
    apic = (KERNEL / "src" / "arch" / "x86_64" / "apic.ritz").read_text()
    entry = apic[apic.index("\npub fn ap_entry()"):]
    assert entry.index("cpu_bringup(my_index)") < entry.index("cpu_map_mark_started("), \
        "an AP is flagged started before its per-CPU state exists"


def test_sentinel_helpers_use_the_stack_bottom():
    asm = _asm()
    for fn in ("proc_kstacks_base", "kstack_stride", "kstack_slots", "syscall_stack_size",
               "kstack_set_current", "kstack_get_current"):
        assert re.search(rf"^\.global {fn}$", asm, re.MULTILINE), fn
    stack = STACK.read_text()
    # each slot's sentinel sits directly above its guard page
    bottom = _body(stack, "kstack_bottom")
    assert "kstack_guard(slot) + GUARD_PAGE_SIZE" in bottom
    init = _body(stack, "syscall_stack_init")
    assert "*(kstack_bottom(slot) as *u64) = SYSCALL_STACK_SENTINEL" in init
    intact = _body(stack, "kstack_sentinel_intact")
    assert "*(kstack_bottom(slot) as *u64) == SYSCALL_STACK_SENTINEL" in intact


def test_check_panics_and_runs_where_syscalls_leave_the_kernel():
    stack = STACK.read_text()
    check = _body(stack, "syscall_stack_check")
    assert "kstack_sentinel_intact(kstack_current_slot())" in check and "halt_loop()" in check
    assert (
        "KERNEL PANIC: syscall stack overflow" in check
    )  # tools/test_*boot.sh grep KERNEL PANIC
    entry = (RUNTIME / "entry.ritz").read_text()
    assert "syscall_stack_init()" in _body(entry, "syscall_init")
    handler = _body(entry, "syscall_handler")
    assert handler.index("syscall_dispatch(") < handler.index(
        "syscall_stack_check()"
    ), handler
    exit_body = _body((RUNTIME / "process.ritz").read_text(), "sys_exit_impl")
    assert exit_body.index("syscall_stack_check()") < exit_body.index(
        "sched_exit()"
    ), exit_body


# ---------------------------------------------------------------------------
# AGAST #1877: an unmapped guard page under the stack, and no big locals on
# syscall paths. The sentinel only notices an overflow when the syscall
# returns; the guard page faults on the first write past the bottom, and #PF
# runs on IST1, so the fault is reported instead of corrupting .bss.
# ---------------------------------------------------------------------------

VMM = KERNEL / "src" / "mm" / "vmm.ritz"
EXCEPTIONS = KERNEL / "src" / "arch" / "x86_64" / "exceptions.ritz"
IDT = KERNEL / "src" / "arch" / "x86_64" / "idt.ritz"
INDIUM = RITZ0_DIR.parents[1] / "indium"


def test_guard_page_sits_directly_below_the_stack():
    asm = _asm()
    # Page-aligned slots in .bss, each a 4 KiB guard page then the stack: an
    # overflow of a stack writes into its guard page first.
    assert re.search(r"^\.align 4096\s*\nproc_kstacks:", asm, re.MULTILINE), \
        "proc_kstacks is not page-aligned"
    stack = STACK.read_text()
    assert "proc_kstacks_base() + slot * kstack_stride()" in _body(stack, "kstack_guard")
    assert "kstack_guard(slot as u64) + kstack_stride()" in _body(stack, "kstack_top")


def test_each_cpu_stack_has_a_guard_page_too():
    """AGAST #4192: the per-CPU stacks are guard-paged as well, in the kernel
    half (every user PML4 shares PML4[256..511]), and their guard pages are
    unmapped before the stack is used."""
    percpu = (KERNEL / "src" / "arch" / "x86_64" / "percpu.ritz").read_text()
    alloc = percpu[percpu.index("pub fn cpu_stack_alloc"):]
    assert "vmm_unmap_kernel_page(phys)" in alloc
    assert "vmm_virt_to_phys(phys) != 0" in alloc
    assert "vmm_map_page(stack_va, phys + CPU_STACK_GUARD, PTE_WRITABLE)" in alloc
    assert "CPU_STACK_VA_BASE: u64 = 0xFFFF960000000000" in percpu
    stack = STACK.read_text()
    hit = _body(stack, "syscall_stack_guard_hit")
    assert "cpu_stack_guard(cpu, which)" in hit and "CPU_STACK_GUARD" in hit


def test_init_unmaps_the_guard_page_and_checks_it():
    init = _body(STACK.read_text(), "syscall_stack_init")
    assert "while slot < kstack_slots()" in init, "every slot's guard page"
    assert init.index("vmm_unmap_kernel_page(") < init.index("vmm_virt_to_phys(")
    # Still mapped after the unmap: a boot-time panic, which the boot tests catch.
    assert "KERNEL PANIC" in init


def test_vmm_unmap_kernel_page_splits_a_2mib_page():
    unmap = _body(VMM.read_text(), "vmm_unmap_kernel_page")
    # The kernel image is mapped with 2 MiB pages (boot_highhalf.s, the UEFI
    # loader): split the one holding the page into a page table first.
    assert "PTE_HUGE" in unmap and "vmm_split_huge_pd_entry(" in unmap
    split = _body(VMM.read_text(), "vmm_split_huge_pd_entry")
    assert "vmm_alloc_table()" in split and "while" in split
    assert "vmm_flush_tlb_all()" in unmap


def test_page_fault_on_the_guard_page_reports_the_overflow():
    exc = EXCEPTIONS.read_text()
    handler = _body(exc, "exception_handler")
    assert "syscall_stack_guard_hit(" in handler
    hit = _body(STACK.read_text(), "syscall_stack_guard_hit")
    assert "kstack_guard(slot)" in hit and "while slot < kstack_slots()" in hit
    assert "KERNEL PANIC: syscall stack overflow" in handler
    # #PF and #DF run on IST1, so the fault handler never uses the overflowed
    # stack.
    idt = IDT.read_text()
    for vec in (8, 14):
        assert re.search(rf"idt_set_gate\({vec}, isr_stub_{vec} as u64, cs, 1,", idt), vec


def test_no_big_locals_on_syscall_paths():
    # The ticket's grep: no [64]KDirEntry (~21 KiB) and no [NNNN]u8 locals
    # (spawn_args' 4 KiB argv copy) in the syscall runtime.
    big = re.compile(r"^\s+var \w+: \[(?:64\]KDirEntry|\d{4,}\]u8)", re.MULTILINE)
    for src in sorted(RUNTIME.glob("*.ritz")):
        hits = big.findall(src.read_text())
        assert not hits, f"{src.name}: {hits}"


def test_tier1_runs_the_readdir_and_open_child():
    init = (INDIUM / "user" / "init.ritz").read_text()
    assert 'run_test(c"/bin/readdir64_child", c"readdir64", 0)' in init
    toml = (INDIUM / "ritz.toml").read_text()
    assert 'name = "readdir64_child"' in toml
    child = (INDIUM / "user" / "readdir64_child.ritz").read_text()
    assert "sys_readdir(" in child and "100" in child and "64" in child
