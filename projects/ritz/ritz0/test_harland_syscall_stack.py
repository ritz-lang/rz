"""Harland's syscall stack: big enough, out of .data, and guarded (AGAST #2761).

Every syscall, and every IRQ taken during one, runs on the single
syscall_stack in kernel/syscall_entry.s. It was 4 KiB in .data, directly
above g_child_pid and fs_current; Tier-1 already peaks at ~8 KiB, and a deep
syscall (a knamespace_write flush, an O_CREAT open) silently overwrote those
globals (#2761, #4064). The fix keeps it in .bss at 64 KiB with a sentinel
quadword at its bottom that syscall_stack_check (syscall/stack.ritz) checks
when a syscall leaves the kernel: after every dispatch, and in sys_exit,
which resumes the parent without returning through syscall_handler.

The checks are structural, at source level. The runtime checks are the OVMF
Tier-1 boot's heap_grow test (indium heap_grow_child) and the panic message
syscall_stack_check prints.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ0_DIR = Path(__file__).resolve().parent
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
    assert _section_of(asm, "syscall_stack") == ".bss"
    size = re.search(r"^\.set SYSCALL_STACK_SIZE,\s*(\w+)", asm, re.MULTILINE)
    assert size and int(size.group(1), 0) >= MIN_STACK, size and size.group(0)
    # The stack is exactly SYSCALL_STACK_SIZE between its two labels.
    assert re.search(
        r"^syscall_stack:\s*\n\s*\.space SYSCALL_STACK_SIZE\s*\nsyscall_stack_top:",
        asm,
        re.MULTILINE,
    )
    # The globals that sit after it stay in .data.
    assert _section_of(asm, "user_rsp_save") == ".data"


def test_sentinel_helpers_use_the_stack_bottom():
    asm = _asm()
    for fn in (
        "syscall_stack_guard_init",
        "syscall_stack_guard_intact",
        "syscall_stack_high_water",
        "syscall_stack_size",
    ):
        assert re.search(rf"^\.global {fn}$", asm, re.MULTILINE), fn
    init = asm[
        asm.index("\nsyscall_stack_guard_init:") : asm.index(
            ".size syscall_stack_guard_init"
        )
    ]
    assert "movq %rax, syscall_stack(%rip)" in init
    intact = asm[
        asm.index("\nsyscall_stack_guard_intact:") : asm.index(
            ".size syscall_stack_guard_intact"
        )
    ]
    assert "cmpq %rcx, syscall_stack(%rip)" in intact


def test_check_panics_and_runs_where_syscalls_leave_the_kernel():
    stack = STACK.read_text()
    check = _body(stack, "syscall_stack_check")
    assert "syscall_stack_guard_intact()" in check and "halt_loop()" in check
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
        "resume_user_frame("
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
    # A whole page, page-aligned, in .bss, then the stack: an overflow of
    # syscall_stack writes into syscall_stack_guard first.
    assert re.search(
        r"^\.align 4096\s*\nsyscall_stack_guard:\s*\n\s*\.space 4096\s*\n"
        r"syscall_stack:",
        asm,
        re.MULTILINE,
    ), "no page-aligned 4 KiB syscall_stack_guard directly below syscall_stack"
    assert _section_of(asm, "syscall_stack_guard") == ".bss"
    assert re.search(r"^\.global syscall_stack_guard_page$", asm, re.MULTILINE)
    page = asm[
        asm.index("\nsyscall_stack_guard_page:") : asm.index(
            ".size syscall_stack_guard_page"
        )
    ]
    assert "leaq syscall_stack_guard(%rip), %rax" in page


def test_init_unmaps_the_guard_page_and_checks_it():
    init = _body(STACK.read_text(), "syscall_stack_init")
    assert "syscall_stack_guard_init()" in init
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
    assert "syscall_stack_guard_page()" in hit
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
