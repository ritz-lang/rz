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
