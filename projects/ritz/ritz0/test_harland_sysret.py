"""Harland returns from SYSCALL with SYSRETQ (AGAST #4610).

SYSRETQ loads SS = STAR[63:48] + 8 and CS = STAR[63:48] + 16 (RPL forced to
3), so the GDT must hold user data and then 64-bit user code. Until this
ticket gdt.ritz had them the other way round, STAR[63:48] was 0 and every
return to ring 3 was an IRETQ.

Now:

  * gdt.ritz: index 3 is user data (0x1B), index 4 is 64-bit user code
    (0x23), and GDT_SYSRET_BASE (0x13) is what STAR[63:48] holds.
  * Both STAR writers (syscall/runtime/entry.ritz syscall_init and
    syscall_entry.s syscall_msr_init) put that base in STAR[63:48].
  * syscall_entry's exit is SYSRETQ, guarded: a non-canonical return RIP
    would #GP in ring 0 on Intel CPUs with the user's RSP (the SYSRET
    erratum), so it takes the IRETQ exit (syscall_exit_iret) instead. That
    IRETQ #GPs in ring 0 too, but on the kernel stack: the #GP stub swaps GS
    back and exceptions.ritz treats it as the user's fault.
  * Every hand-built ring-3 frame uses the new selectors.
  * The boot-test "sysret" self-test (cpu_smp.ritz) checks STAR and the GDT
    at run time, proves the fast path returned with SYSRETQ and that a
    non-canonical return RIP left through the IRETQ exit and was caught.

The runtime proof is the QEMU boot (tools/test_tier1_boot.sh); these pin the
structure so a revert can't slip through unbooted.
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
PROC_SWITCH_S = KERNEL / "proc_switch.s"
GDT = SRC / "arch" / "x86_64" / "gdt.ritz"
CPU_SMP = SRC / "arch" / "x86_64" / "cpu_smp.ritz"
EXCEPTIONS = SRC / "arch" / "x86_64" / "exceptions.ritz"
SCHED = SRC / "proc" / "sched.ritz"
ENTRY = SRC / "syscall" / "runtime" / "entry.ritz"
POSTINIT = SRC / "postinit.ritz"
TIER1 = HARLAND / "tools" / "test_tier1_boot.sh"

USER_DATA = 0x1B
USER_CODE = 0x23
SYSRET_BASE = 0x13


def _code(path):
    """The file with comments stripped (both Ritz and GAS use '#')."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _const(code, name):
    m = re.search(rf"^(?:pub\s+)?const {name}: \w+ = (0x[0-9A-Fa-f]+|\d+)$", code, re.M)
    assert m, f"const {name} not found"
    return int(m.group(1), 0)


def _asm_set(asm, name):
    m = re.search(rf"^\.set {name}, (0x[0-9A-Fa-f]+|\d+)$", asm, re.M)
    assert m, f".set {name} not found"
    return int(m.group(1), 0)


def _asm_fn(asm, name):
    start = asm.index(f"\n{name}:")
    return asm[start:asm.index(f".size {name}", start)]


def _ritz_fn(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


# --- the GDT order SYSRET needs ----------------------------------------------

def test_gdt_has_user_data_then_64bit_user_code():
    gdt = _code(GDT)
    assert _const(gdt, "GDT_USER_DATA") == USER_DATA
    assert _const(gdt, "GDT_USER_CODE") == USER_CODE
    init = _ritz_fn(gdt, "gdt_init")
    # Entry 3 is a data segment (no L bit), entry 4 a long-mode code segment.
    e3 = re.search(r"gdt\[3\] = make_gdt_entry\(0, 0xFFFFF, (\w+), (\w+)\)", init)
    e4 = re.search(r"gdt\[4\] = make_gdt_entry\(0, 0xFFFFF, (\w+), (\w+)\)", init)
    assert e3 and e4
    assert re.search(rf"let {e3.group(1)}: u8 = .*GDT_ACCESS_RING3 \| GDT_ACCESS_DATA$", init, re.M)
    assert re.search(rf"let {e3.group(2)}: u8 = GDT_FLAG_GRANULARITY$", init, re.M)
    assert re.search(rf"let {e4.group(1)}: u8 = .*GDT_ACCESS_RING3 \| GDT_ACCESS_CODE$", init, re.M)
    assert re.search(rf"let {e4.group(2)}: u8 = GDT_FLAG_LONG \| GDT_FLAG_GRANULARITY$", init, re.M)


def test_sysret_base_selects_user_data_and_code():
    gdt = _code(GDT)
    base = _const(gdt, "GDT_SYSRET_BASE")
    assert base == SYSRET_BASE
    # SYSRETQ: SS = base + 8, CS = base + 16, RPL forced to 3.
    assert (base + 8) | 3 == _const(gdt, "GDT_USER_DATA")
    assert (base + 16) | 3 == _const(gdt, "GDT_USER_CODE")


# --- STAR[63:48] is set by both writers --------------------------------------

def test_syscall_init_puts_the_sysret_base_in_star_63_48():
    entry = _code(ENTRY)
    init = _ritz_fn(entry, "syscall_init")
    assert _const(entry, "STAR_SYSRET_BASE_SHIFT") == 48
    assert _const(entry, "STAR_KERNEL_CS_SHIFT") == 32
    assert re.search(
        r"wrmsr\(MSR_STAR, \(SYSRET_BASE << STAR_SYSRET_BASE_SHIFT\) \| "
        r"\(KERNEL_CS << STAR_KERNEL_CS_SHIFT\)\)", init), "STAR[63:48] left 0"
    assert _const(entry, "SYSRET_BASE") == SYSRET_BASE


def test_syscall_msr_init_puts_the_sysret_base_in_star_63_48():
    asm = _code(ENTRY_S)
    assert _asm_set(asm, "SYSRET_BASE") == SYSRET_BASE
    assert _asm_set(asm, "KERNEL_CS") == 0x08
    body = _asm_fn(asm, "syscall_msr_init")
    star = body[body.index("movl $MSR_STAR, %ecx"):body.index("movl $MSR_LSTAR")]
    # EDX = STAR[63:32]: kernel CS in the low half, SYSRET base in the high.
    assert "movl $(KERNEL_CS | (SYSRET_BASE << 16)), %edx" in star, "STAR[63:48] left 0"


# --- the exit: SYSRETQ, IRETQ only for a non-canonical RIP --------------------

def test_syscall_exit_is_sysretq_guarded_by_a_canonical_rip_check():
    asm = _code(ENTRY_S)
    entry = _asm_fn(asm, "syscall_entry")
    assert "sysretq" in entry
    assert entry.count("iretq") == 1, "only the non-canonical exit is an IRETQ"
    # The guard runs before SYSRETQ: sign-extend bit 47 and compare.
    guard = entry.index("shlq $16, %r11")
    assert guard < entry.index("sarq $16, %r11") < entry.index("cmpq %rcx, %r11")
    assert entry.index("cmpq %rcx, %r11") < entry.index("jne .Lsyscall_exit_iret") < entry.index("sysretq")
    # The fast path restores RCX/R11/RSP and swaps GS just before SYSRETQ.
    fast = entry[entry.index("jne .Lsyscall_exit_iret"):entry.index("sysretq")]
    assert fast.index("popq %rcx") < fast.index("popq %r11") < fast.index("popq %rsp") < fast.index("swapgs")


def test_noncanonical_exit_is_an_iretq_on_the_kernel_stack():
    asm = _code(ENTRY_S)
    entry = _asm_fn(asm, "syscall_entry")
    slow = entry[entry.index(".Lsyscall_exit_iret:"):]
    # The frame is built at the kernel stack's top, never on the user stack.
    assert "popq %rsp" not in slow
    for push in ("pushq $USER_SS", "pushq %gs:PC_USER_RSP", "pushq %gs:PC_USER_RFLAGS",
                 "pushq $USER_CS", "pushq %gs:PC_USER_RIP"):
        assert push in slow, push
    assert slow.index("swapgs") < slow.index("\nsyscall_exit_iret:") < slow.index("iretq")
    assert re.search(r"^\.global syscall_exit_iret$", asm, re.M)
    # Counted, so the boot self-test can tell which exit ran.
    assert "lock incq syscall_iret_exits(%rip)" in slow


def test_a_fault_on_the_syscall_iretq_is_the_users():
    isr = _code(ISR_S)
    macro = isr[isr.index(".macro SWAPGS_IF_USER_ERR"):]
    macro = macro[:macro.index(".endm")]
    assert "testq $3, 16(%rsp)" in macro
    assert "leaq syscall_exit_iret(%rip), %rax" in macro
    err = isr[isr.index(".macro ISR_ERR num"):isr.index(".endm", isr.index(".macro ISR_ERR num"))]
    assert "SWAPGS_IF_USER_ERR" in err
    exc = _code(EXCEPTIONS)
    handler = _ritz_fn(exc, "exception_handler")
    assert "syscall_exit_iret as u64" in exc
    # Its own check, ahead of (and apart from) the ring-3 test that
    # test_harland_fault_hardening pins: it kills the process, reading the
    # user's RIP from the IRETQ frame.
    bad = handler.index("if fault_on_syscall_iret(frame)")
    assert bad < handler.index("if ((*frame).cs & 3) == 3")
    case = handler[bad:handler.index("if ((*frame).cs & 3) == 3")]
    assert "log_user_fault(frame, *((*frame).rsp as *u64), true)" in case
    assert "process_kill_current(128 + ((*frame).vector as i32))" in case
    # The self-test's catch runs before either kill.
    log = _ritz_fn(exc, "log_user_fault")
    assert "sysret_selftest_catch(" in log


# --- every ring-3 frame uses the new selectors -------------------------------

def test_hand_built_ring3_frames_use_the_new_selectors():
    asm = _code(ENTRY_S)
    assert _asm_set(asm, "USER_CS") == USER_CODE
    assert _asm_set(asm, "USER_SS") == USER_DATA
    for fn in ("jump_to_userspace", "jump_to_userspace_with_args"):
        body = _asm_fn(asm, fn)
        assert "pushq $USER_SS" in body and "pushq $USER_CS" in body, fn
    # No literal selector pushes left anywhere.
    for path in (ENTRY_S, PROC_SWITCH_S):
        assert not re.search(r"pushq \$0x(1[Bb]|23)\b", _code(path)), path.name
    sched = _code(SCHED)
    assert _const(sched, "USER_CS") == USER_CODE
    assert _const(sched, "USER_SS") == USER_DATA


# --- the boot self-test and the gate ----------------------------------------

def test_sysret_boot_self_test_is_run_and_gated():
    smp = _code(CPU_SMP)
    test = _ritz_fn(smp, "sysret_selftest")
    assert "rdmsr(MSR_STAR)" in test
    assert "NONCANONICAL_RIP" in smp and _const(smp, "NONCANONICAL_RIP") == 0x0000800000000000
    assert "gdt_user_segments_ok()" in test
    post = _code(POSTINIT)
    assert 'boot_test_result("sysret", sysret_selftest())' in post
    tier1 = TIER1.read_text()
    names = re.search(r'^BOOT_TESTS="([^"]*)"', tier1, re.M).group(1).split()
    assert "sysret" in names
