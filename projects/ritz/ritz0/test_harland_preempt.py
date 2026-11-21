"""Harland preempts user processes on a calibrated LAPIC timer (AGAST #3629).

Before: the LAPIC timer was masked ("conflicts with userspace"), irq_handler
only EOI'd vector 32, sys_yield was a no-op, spawn was blocking with one
global syscall stack and one TSS.rsp0, and a child ran until it exited. Two
busy processes could not both make progress.

Now:
  * arch/x86_64/apic.ritz calibrates the LAPIC timer against the TSC of
    #4181 (tsc.ritz's delay_us over LAPIC_CAL_WINDOW_US; no second PIT gate),
    logs its rate and runs a periodic SCHED_HZ tick on vector 32. The NVMe
    watchdog's one-shot use of the same timer gives the tick back.
  * every process-table slot has its own kernel stack (syscall_entry.s
    proc_kstacks, a guard page and a sentinel each). syscall_entry and
    TSS.rsp0 use the running process's; proc/sched.ritz switches page table,
    TSS.rsp0, the syscall stack and the fs table on every switch, then the
    kernel context (proc_switch.s sched_switch).
  * a timer IRQ from ring 3 round-robins the runnable processes; one from
    ring 0 (a syscall, the idle hlt) only counts the tick.
  * spawn_bg (syscall 28) starts a child without waiting; wait(pid) and the
    blocking spawn sleep in the scheduler; yield switches; read(0) sleeps
    until COM1's IRQ wakes it.

The arithmetic (tsc_calc.ritz) and the table's round robin
(test_harland_process_model.py) are host-tested; the rest is pinned here at
source level, and run by init's Tier-1 `preempt` test: init spawn_bg's two
/bin/busy children that print progress and never yield, and
tools/test_tier1_boot.sh requires their progress lines to interleave.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
PROJECTS = RITZ_ROOT.parent
HARLAND = PROJECTS / "harland"
KERNEL = HARLAND / "kernel"
KERNEL_SRC = KERNEL / "src"
TSC_CALC = KERNEL_SRC / "arch" / "x86_64" / "tsc_calc.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
EXCEPTIONS = KERNEL_SRC / "arch" / "x86_64" / "exceptions.ritz"
IDT = KERNEL_SRC / "arch" / "x86_64" / "idt.ritz"
SCHED = KERNEL_SRC / "proc" / "sched.ritz"
PROCESS = KERNEL_SRC / "syscall" / "runtime" / "process.ritz"
ENTRY = KERNEL_SRC / "syscall" / "runtime" / "entry.ritz"
NUMBERS = KERNEL_SRC / "syscall" / "numbers.ritz"
CONSOLE = KERNEL_SRC / "tty" / "console.ritz"
MAIN = KERNEL_SRC / "main.ritz"
ENTRY_S = KERNEL / "syscall_entry.s"
SWITCH_S = KERNEL / "proc_switch.s"
INDIUM = PROJECTS / "indium"
INIT = INDIUM / "user" / "init.ritz"
BUSY = INDIUM / "user" / "busy.ritz"
TIER1 = HARLAND / "tools" / "test_tier1_boot.sh"
SYS = RITZ_ROOT / "ritzlib" / "sys.ritz"


def _code(path):
    """Source with `#` comments stripped (no `#` inside the strings checked here)."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


def _asm_fn(asm, label):
    start = asm.index(f"\n{label}:")
    return asm[start:asm.index(f".size {label}", start)]


# --- the calibration arithmetic ------------------------------------------------------

PROGRAM = """\
import arch.x86_64.tsc_calc

fn main() -> i32
    # a 10 ms window
    if LAPIC_CAL_WINDOW_US != 10000
        return 1
    # 1 GHz bus / 16 = 62.5 MHz: 625000 counted in 10 ms
    if lapic_timer_hz(625000, 10000) != 62500000
        return 2
    if lapic_timer_hz(625000, 0) != 0 or lapic_timer_hz(0, 10000) != 0
        return 3
    # 100 Hz tick at 62.5 MHz: 625000 per period
    if lapic_timer_initial(62500000, 100) != 625000
        return 4
    # no rate, no tick: 0 (the caller leaves the timer masked)
    if lapic_timer_initial(0, 100) != 0 or lapic_timer_initial(62500000, 0) != 0
        return 5
    # a timer slower than the tick still ticks: at least 1
    if lapic_timer_initial(50, 100) != 1
        return 6
    # the count register is 32 bits: saturate, don't wrap
    if lapic_timer_initial(0x1000000000, 1) != 0xFFFFFFFF
        return 7
    0
"""

CLAIMS = {1: "10 ms calibration window", 2: "count over the window -> Hz",
          3: "empty window or no count -> 0 Hz", 4: "Hz / tick rate -> initial count",
          5: "no rate -> no tick", 6: "a slow timer still ticks", 7: "the 32-bit count saturates"}


@pytest.mark.integration
def test_lapic_timer_calibration_arithmetic(tmp_path):
    tree = tmp_path / "tree" / "arch" / "x86_64"
    tree.mkdir(parents=True)
    (tree / "tsc_calc.ritz").write_text(TSC_CALC.read_text())
    (tmp_path / "t.ritz").write_text(PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "tsc_calc.ritz", "tsc_calc", ("--no-runtime",))]:
        ll = tmp_path / f"{name}.ll"
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
        assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
        objs.append(str(ll))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == 0, f"exit {rc}: {CLAIMS.get(rc, 'crash')}"


# --- the timer -----------------------------------------------------------------------

def _isr_s():
    return "\n".join(l.split("#", 1)[0].rstrip() for l in (KERNEL / "isr_stubs.s").read_text().splitlines())


def test_timer_is_calibrated_against_the_tsc_not_a_second_pit_gate():
    apic = _code(APIC)
    cal = _body(apic, "lapic_timer_calibrate")
    assert "delay_us(LAPIC_CAL_WINDOW_US)" in cal and "lapic_timer_hz(" in cal
    assert "outb" not in cal and "0x42" not in cal and "0x61" not in cal, "a second PIT gate"
    start = _body(apic, "lapic_timer_start")
    assert "lapic_timer_calibrate()" in start and "lapic_timer_initial(" in start
    # the rate is logged, and the tick is periodic on vector 32
    assert "[timer] LAPIC timer " in APIC.read_text()
    resume = _body(apic, "lapic_timer_resume")
    assert "LAPIC_WATCHDOG_VECTOR | LAPIC_TIMER_PERIODIC" in resume
    assert re.search(r"LAPIC_TIMER_PERIODIC: u32 = 0x20000\b", apic)
    # the NVMe watchdog borrows the timer one-shot and gives the tick back
    assert "lapic_timer_resume()" in _body(apic, "lapic_watchdog_stop")


def test_one_lapic_write_signature():
    # sched/mod.ritz extern-declared lapic_write(reg: u32, ...) against
    # apic.ritz's lapic_write(offset: u64, ...); the one left is apic.ritz's.
    defs = [p for p in KERNEL_SRC.rglob("*.ritz") if re.search(r"fn lapic_write\(", _code(p))]
    assert defs == [APIC], defs
    assert re.search(r"^pub fn lapic_write\(offset: u64, value: u32\)", _code(APIC), re.M)


def test_scheduler_starts_the_tick_before_init_enters_ring_3():
    start = _body(_code(SCHED), "sched_start")
    assert "lapic_timer_start(SCHED_HZ)" in start and "sched_use_kstack(slot)" in start
    assert "sched_start(proc_current_slot())" in _body(_code(PROCESS), "process_enter_init")
    run = _body(_code(MAIN), "run_init")
    assert run.index("process_enter_init()") < run.index("jump_to_userspace(")


def test_timer_irq_runs_on_ist3_and_moves_a_ring3_frame_to_the_process_stack():
    idt = IDT.read_text()
    assert re.search(r"idt_set_gate\(32, irq_stub_timer as u64, cs, 3,", idt)
    gdt = (KERNEL_SRC / "arch" / "x86_64" / "gdt.ritz").read_text()
    assert "tss.ist3 = " in gdt
    asm = _isr_s()
    stub = asm[asm.index("\nirq_stub_timer:"):]
    # ring 3 only: copy the 5-word IRET frame to kstack_current_top and run there
    assert "testq $3, 8(%rsp)" in stub
    assert "movq kstack_current_top(%rip), %rax" in stub and "subq $40, %rax" in stub
    for off in (0, 8, 16, 24, 32):
        assert f"movq %rbx, {off}(%rax)" in stub, off
    assert "pushq $32" in stub and "jmp irq_common" in stub
    assert not re.search(r"^IRQ_STUB 0,\s*32", asm, re.M), "the old IST0 timer stub is back"


def test_timer_stub_never_addresses_below_rsp():
    # #4308's check_no_red_zone.py fails the boot on any -N(%rsp) operand;
    # the stub saves %rax/%rbx with push, not with stores below %rsp.
    asm = _isr_s()
    stub = asm[asm.index("\nirq_stub_timer:"):]
    stub = stub[:stub.index("jmp irq_common")]
    assert not re.search(r"-(0x)?[0-9a-fA-F]+\(%rsp[,)]", stub), stub
    assert "pushq %rax" in stub.split("1:")[0] and "pushq %rbx" in stub.split("1:")[0]
    for off in (16, 24, 32, 40, 48):  # the IRET frame, above the two pushes
        assert f"movq {off}(%rsp), %rbx" in stub, off


def test_tick_preempts_only_ring_3_after_its_eoi():
    irq = _body(_code(EXCEPTIONS), "irq_handler")
    timer = irq[irq.index("if irq_num == 0"):irq.index("if irq_num == 4")]
    assert timer.index("lapic_eoi()") < timer.index("sched_tick(((*frame).cs & 3) == 3)")
    tick = _body(_code(SCHED), "sched_tick")
    assert "if not from_user or sched_running == 0" in tick and "sched_switch_to(next)" in tick


# --- the switch ----------------------------------------------------------------------

def test_switch_points_everything_per_process_at_the_next_process():
    sw = _body(_code(SCHED), "sched_switch_to")
    order = ["proc_set_current(next)", "vmm_switch_pml4(p.pml4)", "sched_use_kstack(next)",
             "fs_process_select(p.pid)", "sched_switch(@(*from).ksp, p.ksp)"]
    idx = [sw.index(s) for s in order]
    assert idx == sorted(idx), sw
    use = _body(_code(SCHED), "sched_use_kstack")
    assert "gdt_set_kernel_stack(top)" in use and "kstack_set_current(top)" in use


def test_sched_switch_saves_callee_saved_registers_and_rflags():
    asm = "\n".join(l.split("#", 1)[0].rstrip() for l in SWITCH_S.read_text().splitlines())
    sw = _asm_fn(asm, "sched_switch")
    pushes = re.findall(r"pushq %(\w+)", sw)
    pops = re.findall(r"popq %(\w+)", sw)
    assert pushes == ["rbp", "rbx", "r12", "r13", "r14", "r15"] and pops == pushes[::-1], (pushes, pops)
    assert sw.index("pushfq") < sw.index("movq %rsp, (%rdi)") < sw.index("movq %rsi, %rsp") < sw.index("popfq")
    first = _asm_fn(asm, "proc_first_entry")
    assert "addq $16, %rsp" in first and "iretq" in first
    toml = (HARLAND / "ritz.toml").read_text()
    assert '"kernel/proc_switch.s"' in toml


def test_new_process_frame_matches_the_switch_and_irq_layouts():
    prep = _body(_code(SCHED), "sched_prepare_user")
    assert "*(sw + SWITCH_RET) = proc_first_entry as u64" in prep and "*sw = KERNEL_RFLAGS" in prep
    sched = _code(SCHED)
    # InterruptFrame: 15 GPRs (r15 first: rdi is word 9, rsi 10), vector,
    # error code, RIP 17, CS, RFLAGS, RSP, SS 21
    for name, word in (("FRAME_WORDS", 22), ("FRAME_RDI", 9), ("FRAME_RSI", 10), ("FRAME_RIP", 17),
                       ("FRAME_CS", 18), ("FRAME_RFLAGS", 19), ("FRAME_RSP", 20), ("FRAME_SS", 21),
                       ("SWITCH_WORDS", 8), ("SWITCH_RET", 7)):
        assert re.search(rf"const {name}: u64 = {word}\b", sched), name
    assert re.search(r"USER_RFLAGS: u64 = 0x202\b", sched), "a new process runs with IF=1"


# --- the syscalls --------------------------------------------------------------------

def test_spawn_bg_yield_and_wait_are_real():
    nums = _code(NUMBERS)
    assert re.search(r"^\s+SpawnBg = 28\b", nums, re.M)
    entry = _code(ENTRY)
    assert "syscall_register(Syscall.SpawnBg, sys_spawn_bg_handler)" in entry
    process = _code(PROCESS)
    bg = _body(process, "sys_spawn_bg_handler")
    assert "return spawn_process(" in bg and "wait_for_child" not in bg
    assert "spawn_process(" in _body(process, "spawn_and_block") and \
        "wait_for_child(" in _body(process, "spawn_and_block")
    assert "sched_yield()" in _body(process, "sys_yield_handler")
    wait = _body(process, "wait_for_child")
    assert "proc_block(BLOCK_CHILD, pid)" in wait and "sched_block()" in wait
    sys = SYS.read_text()
    assert re.search(r"const SYS_SPAWN_BG: i64 = 28\b", sys)
    assert "pub fn sys_spawn_bg(path: *u8, argv: **u8, argc: i32) -> i64" in sys


# --- the boot test -------------------------------------------------------------------

def test_init_runs_two_busy_children_side_by_side():
    init = _code(INIT)
    suite = _body(init, "run_tier1_tests")
    assert "run_preempt_test()" in suite
    steps = _body(init, "preempt_steps")
    assert steps.count('sys_spawn_bg(c"/bin/busy"') == 2
    assert steps.index("sys_spawn_bg") < steps.index("sys_wait(a as i32)")
    busy = _code(BUSY)
    loop = busy[busy.index("while i < BUSY_SPIN"):busy.index("report(tag, step)")]
    assert "sys_" not in loop, "the busy loop makes no syscall: only the timer can preempt it"
    toml = (INDIUM / "ritz.toml").read_text()
    assert 'name = "busy"\nentry = "busy::main"' in toml


def test_tier1_boot_requires_the_busy_lines_to_interleave():
    script = TIER1.read_text()
    fn = script[script.index("preempted() {"):]
    fn = fn[:fn.index("\n}\n")]
    # The run count only has to show both children were alive at once: 16
    # lines alternating gives 16 runs, but a loaded host can give each child
    # two steps per timeslice (ABBAABBA..., 9 runs) while the scheduler
    # preempts normally (AGAST #4438). The genuine failure shapes are 2 runs
    # (no preemption: A..A..B..B) and 4 (#4332's starved child, caught by the
    # ratio below). 6 sits between: two clear of 4, three below the measured
    # CI tail of 9, seven below the 13..16 healthy pair.
    assert "runs < 6" in fn and 'done != {"A", "B"}' in fn
    # The interleave count alone is timing-sensitive, so the script must also
    # read the scheduler's counters: the regression left one child running
    # alone for hundreds of ticks (911 ticks / 195 preemptions, ratio 4.7)
    # where a healthy pair measured 1.10..1.23 on an idle and a loaded host
    # (AGAST #4438, 39 boots at load 2..23).
    assert r"\[sched\]" in fn and "preemptions * 3" in fn
    assert r"\[timer\] LAPIC timer" in fn
    for boot in ("native", "grub"):
        assert f"preempted {boot} || rc=1" in script, boot
