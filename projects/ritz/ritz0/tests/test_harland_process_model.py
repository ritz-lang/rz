"""Harland keeps one Proc per process, so spawn nests (AGAST #1882, LARB v4 M2).

The blocking spawn used to keep one global parent: g_parent_ctx,
g_parent_frame, g_has_parent, g_child_pid = 2 and g_child_pml4
(syscall/runtime/process.ritz). A child that spawned overwrote its parent's
saved frame, every child was pid 2, sys_wait knew only pid 2, and the one
g_cwd (syscall/runtime/cwd.ritz) leaked a child's chdir into its parent.

Now proc/table.ritz holds a Proc per live or not-yet-reaped process: pid,
parent, state, page table, saved syscall frame, exit status and cwd. Its fds
and mmap cursor are its FsProc (fs/syscall.ritz, #2753/#3530), which
fs_process_start/fs_process_end bracket in step with it. spawn pushes a
child Proc and blocks the parent on its own frame; exit makes the child a
zombie, reaps its own zombie children and resumes the parent from the
parent's frame; wait(pid) reaps one child of the caller.

The unused kernel-thread scheduler (sched/mod.ritz, context_switch.s: no
task was ever created, the timer IRQ only EOIs, SYS_YIELD returns 0) is
deleted rather than wired: preemption needs the calibrated timer of #1883 /
#1852 and a scheduler of user processes, not kernel threads.

proc/table.ritz is pure Ritz (only syscall/errno.ritz), so the behaviour test
compiles it into a host program and walks init -> rzsh -> script -> command.
The boot-level check is init's "nested spawn" Tier-1 test (indium/user/
init.ritz), run by projects/harland/tools/test_tier1_boot.sh.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from tracked import is_tracked

# The per-CPU hooks proc/table.ritz, fs/syscall.ritz and syscall/dispatch.ritz
# declare `extern` (AGAST #4879): the kernel's are arch/x86_64/percpu.ritz
# cpu_index and sync/idle.ritz cpu_kick_if_idle. One CPU here.
CPU_HOOKS = """
var g_cpu: i32 = 0
var g_kicks: i32 = 0
var g_kicked: i32 = -1

pub fn cpu_index() -> i32
    g_cpu

pub fn cpu_kick_if_idle(cpu: i32)
    g_kicks = g_kicks + 1
    g_kicked = cpu
"""

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
PROJECTS = RITZ_ROOT.parent
HARLAND = PROJECTS / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
INIT = PROJECTS / "indium" / "user" / "init.ritz"

MODULES = ["syscall/errno.ritz", "proc/table.ritz"]


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(tmp_path, src):
    """Compile the real proc/table.ritz and `src` on the host, link, run."""
    tree = tmp_path / "tree"
    for rel in MODULES:
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text((KERNEL_SRC / rel).read_text())
    # Only the program brings the runtime's _start.
    objs = [str(_compile(tmp_path, tree / rel, rel[:-5].replace("/", "_"), ("--no-runtime",)))
            for rel in MODULES]
    (tmp_path / "t.ritz").write_text(src + CPU_HOOKS)
    objs.insert(0, str(_compile(tmp_path, tmp_path / "t.ritz", "t")))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True, check=False)
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode


NESTING = """\
import syscall.errno { Errno }
import ritzlib.strview { StrView }
import proc.table

# proc_cwd is a StrView over the Proc's Cwd holder, NUL-terminated just past
# its length for getcwd's copy-out (AGAST #4600).
fn cwd_is(want: StrView) -> bool
    let c: StrView = proc_cwd()
    if c.len != want.len or *(c.ptr + c.len) != 0
        return false
    var i: i64 = 0
    while i < want.len
        if *(c.ptr + i) != *(want.ptr + i)
            return false
        i = i + 1
    true

# Blocking spawn as syscall/runtime/process.ritz does it: a new child, the
# parent blocked on it, the child switched to.
fn spawn_blocking() -> i32
    let parent: i32 = proc_current_slot()
    let c: i32 = proc_new_child()
    if c < 0
        return c
    proc_start(c)
    proc_block(BLOCK_CHILD, proc_at(c).pid)
    if proc_pick_next() != c
        return -100
    proc_set_current(c)
    0

# The current process exits; the parent it woke is switched to.
fn exit_to_parent(code: i64) -> *Proc
    let parent: i32 = proc_current().parent
    if proc_exit_current(code) != 0
        return 0 as *Proc
    let next: i32 = proc_pick_next()
    if next != parent
        return 0 as *Proc
    proc_set_current(next)
    proc_at(next)

fn main() -> i32
    proc_table_reset()
    if proc_current() != 0 as *Proc or proc_current_pid() != 0
        return 1
    if proc_enter_init(4096) != 0 or proc_current_pid() != 1 or not cwd_is("/")
        return 2
    let init: *Proc = proc_current()
    if init.pml4 != 4096 or init.parent != -1 or not proc_is_init(init)
        return 3
    # init -> rzsh -> script -> command, each a new pid with the cwd it
    # inherited, the parent blocked on its child
    if spawn_blocking() != 0 or proc_current_pid() != 2 or not cwd_is("/")
        return 4
    let rzsh: *Proc = proc_current()
    if proc_set_cwd("/etc") != 0
        return 5
    if spawn_blocking() != 0 or proc_current_pid() != 3 or not cwd_is("/etc")
        return 6
    let script: *Proc = proc_current()
    if proc_set_cwd("/bin") != 0
        return 7
    if spawn_blocking() != 0 or proc_current_pid() != 4 or not cwd_is("/bin")
        return 8
    let cmd: *Proc = proc_current()
    if proc_state_of(init) != PROC_BLOCKED or proc_state_of(rzsh) != PROC_BLOCKED or proc_state_of(script) != PROC_BLOCKED
        return 9
    if proc_state_of(cmd) != PROC_RUNNING or proc_live_count() != 4
        return 10
    # only the command can run: the round robin never picks a blocked ancestor
    if proc_pick_next() != proc_current_slot()
        return 11
    # command exits 42: script runs again in /bin and reaps it, once
    if exit_to_parent(42) != script or proc_current() != script
        return 12
    if proc_state_of(script) != PROC_RUNNING or not cwd_is("/bin")
        return 13
    if proc_wait(4) != 42 or proc_wait(4) != Errno.Child as i64
        return 14
    # script exits 42: rzsh runs again in /etc
    if exit_to_parent(42) != rzsh or proc_current_pid() != 2 or not cwd_is("/etc")
        return 15
    # rzsh can't reap its parent or a pid that never was
    if proc_wait(1) != Errno.Child as i64 or proc_wait(99) != Errno.Child as i64
        return 16
    if proc_wait(3) != 42
        return 17
    # rzsh exits 7: init runs again in "/", untouched by its children's chdir
    if exit_to_parent(7) != init or proc_current_pid() != 1 or not cwd_is("/")
        return 18
    if proc_wait(2) != 7 or proc_live_count() != 1
        return 19
    # The holder takes PROC_CWD_MAX (255) bytes and refuses one more,
    # leaving the cwd as it was (AGAST #4600)
    var long: [256]u8
    var i: i64 = 0
    while i < 256
        long[i] = 97  # 'a'
        i = i + 1
    long[0] = 47  # '/'
    if proc_set_cwd(StrView { ptr: @long[0], len: 256 }) != Errno.NameTooLong as i32 or not cwd_is("/")
        return 20
    if proc_set_cwd(StrView { ptr: @long[0], len: 255 }) != 0
        return 21
    if not cwd_is(StrView { ptr: @long[0], len: 255 })
        return 22
    0
"""

LIFECYCLE = """\
import syscall.errno { Errno }
import proc.table

fn main() -> i32
    proc_table_reset()
    if proc_new_child() != Errno.Srch as i32
        return 1
    if proc_enter_init(0) != 0
        return 2
    let init: *Proc = proc_current()
    # a spawn that fails before the child runs gives its slot back; init
    # never stopped running
    let c: i32 = proc_new_child()
    if c < 0 or proc_at(c).pid != 2 or proc_state(c) != PROC_NEW or proc_current() != init
        return 3
    # a NEW child is never picked: it has no kernel stack to switch to yet
    if proc_pick_next() != proc_current_slot()
        return 4
    proc_abort_child(c)
    if proc_state_of(init) != PROC_RUNNING or proc_live_count() != 1 or proc_wait(2) != Errno.Child as i64
        return 5
    # init -> a -> b: b exits unreaped, then a exits: a's zombie child goes
    # with it, a stays for init to reap
    let a: i32 = proc_new_child()
    proc_start(a)
    let a_pid: u64 = proc_at(a).pid
    proc_set_current(a)
    let b: i32 = proc_new_child()
    proc_start(b)
    let b_pid: u64 = proc_at(b).pid
    if b_pid == a_pid or a_pid == 1
        return 6
    proc_set_current(b)
    proc_exit_current(3)
    if proc_live_count() != 3 or proc_state(b) != PROC_ZOMBIE
        return 7
    proc_set_current(a)
    proc_exit_current(5)
    proc_set_current(0)
    if proc_live_count() != 2 or proc_wait(b_pid) != Errno.Child as i64 or proc_wait(a_pid) != 5
        return 8
    # MAX_PROCS slots: they fill, then spawn fails and changes nothing
    var n: i32 = 1
    while n < MAX_PROCS
        let s: i32 = proc_new_child()
        if s < 0
            return 9
        proc_start(s)
        n = n + 1
    if proc_new_child() != Errno.Again as i32 or proc_live_count() != MAX_PROCS
        return 10
    # each child exits and init reaps it: nothing leaks
    var i: i32 = 1
    while i < MAX_PROCS
        let pid: u64 = proc_at(i).pid
        proc_set_current(i)
        proc_exit_current(0)
        proc_set_current(0)
        if proc_wait(pid) != 0
            return 11
        i = i + 1
    if proc_live_count() != 1
        return 12
    # init exiting has no parent: the table is left alone
    if proc_exit_current(0) != -1 or proc_current() != init or proc_state_of(init) != PROC_RUNNING
        return 13
    0
"""

# Preemptive scheduling (#3629): several runnable processes, round robin,
# blocking on a child or on console input, detached orphans.
SCHED = """\
import syscall.errno { Errno }
import proc.table

fn main() -> i32
    proc_table_reset()
    if proc_pick_next() != -1
        return 1
    proc_enter_init(0)
    let init: i32 = proc_current_slot()
    # non-blocking spawn: two children run beside init
    let a: i32 = proc_new_child()
    proc_start(a)
    let b: i32 = proc_new_child()
    proc_start(b)
    let a_pid: u64 = proc_at(a).pid
    let b_pid: u64 = proc_at(b).pid
    if proc_current_slot() != init or proc_state(init) != PROC_RUNNING
        return 2
    # round robin: init -> a -> b -> init
    if proc_pick_next() != a
        return 3
    proc_set_current(a)
    if proc_pick_next() != b
        return 4
    proc_set_current(b)
    if proc_pick_next() != init
        return 5
    proc_set_current(init)
    # init waits for a: it is skipped while it waits
    var code: i64 = 0
    if proc_child_status(a_pid, @code) != PROC_CHILD_LIVE
        return 6
    proc_block(BLOCK_CHILD, a_pid)
    if proc_pick_next() != a
        return 7
    proc_set_current(a)
    if proc_pick_next() != b
        return 8
    proc_set_current(b)
    if proc_pick_next() != a
        return 9
    # b exits: init still waits for a
    proc_exit_current(9)
    if proc_state(init) != PROC_BLOCKED or proc_state(b) != PROC_ZOMBIE
        return 10
    if proc_pick_next() != a
        return 11
    proc_set_current(a)
    # a blocks on console input: nothing is runnable
    proc_block(BLOCK_TTY, 0)
    if proc_pick_next() != -1
        return 12
    # input comes: a runs again; init, waiting for a child, still waits
    proc_wake(BLOCK_TTY)
    if proc_state(init) != PROC_BLOCKED
        return 13
    if proc_state(a) != PROC_RUNNING or proc_pick_next() != a
        return 14
    # a exits: init wakes and sees both exit codes, unreaped until it waits
    proc_exit_current(4)
    if proc_state(init) != PROC_RUNNING or proc_pick_next() != init
        return 15
    proc_set_current(init)
    if proc_child_status(a_pid, @code) != PROC_CHILD_EXITED or code != 4
        return 16
    if proc_child_status(b_pid, @code) != PROC_CHILD_EXITED or code != 9
        return 17
    if proc_wait(a_pid) != 4 or proc_wait(b_pid) != 9
        return 18
    if proc_child_status(a_pid, @code) != Errno.Child as i32 or proc_live_count() != 1
        return 19
    # init -> p -> q, q still running when p exits: q is detached, nobody can
    # wait for it, and its own exit frees its slot
    let p: i32 = proc_new_child()
    proc_start(p)
    let p_pid: u64 = proc_at(p).pid
    proc_set_current(p)
    let q: i32 = proc_new_child()
    proc_start(q)
    let q_pid: u64 = proc_at(q).pid
    proc_exit_current(0)
    if proc_at(q).detached == 0 or proc_at(q).parent != -1 or proc_state(q) != PROC_RUNNING
        return 20
    proc_set_current(init)
    if proc_child_status(q_pid, @code) != Errno.Child as i32 or proc_wait(p_pid) != 0
        return 21
    proc_set_current(q)
    proc_exit_current(3)
    if proc_state(q) != PROC_FREE or proc_live_count() != 1
        return 22
    # a detached process is not init: only pid 1 is
    if proc_is_init(proc_at(q)) or not proc_is_init(proc_at(init))
        return 23
    0
"""

# process_mark_exit (#4714, RING1_DRIVER.md "Driver death"): the kernel marks
# another pid PROC_REAP; its next return to user enters sys_exit_impl. The
# table half refuses pid 1 and wakes a parked pid without exiting the caller.
REAP = """\
import syscall.errno { Errno }
import proc.table
import ritzlib.result { Result }

fn refused(r: Result<(), MarkError>, why: MarkError) -> bool
    match r
        Err(e) => e == why
        Ok(_) => false

fn main() -> i32
    proc_table_reset()
    if not refused(proc_mark_exit(1), MarkError.NoProcess)
        return 1
    proc_enter_init(0)
    let init: i32 = proc_current_slot()
    let d: i32 = proc_new_child()
    proc_start(d)
    let d_pid: u64 = proc_at(d).pid
    let b: i32 = proc_new_child()
    proc_start(b)
    let b_pid: u64 = proc_at(b).pid
    # pid 1 is refused, and stays unmarked
    if not refused(proc_mark_exit(1), MarkError.Init) or proc_reap_pending(proc_at(init))
        return 2
    # an unknown pid, and pid 0, are no process
    if not refused(proc_mark_exit(99), MarkError.NoProcess) or not refused(proc_mark_exit(0), MarkError.NoProcess)
        return 3
    # a running pid is marked; nothing else changes, the caller least of all
    if proc_reap_pending(proc_at(d)) or not proc_mark_exit(d_pid).is_ok()
        return 4
    if not proc_reap_pending(proc_at(d)) or proc_state(d) != PROC_RUNNING
        return 5
    if proc_current_slot() != init or proc_state(init) != PROC_RUNNING or proc_reap_pending(proc_at(init))
        return 6
    if proc_reap_pending(proc_at(b))
        return 7
    # a parked pid is woken, so it reaches its return to user
    proc_set_current(b)
    proc_block(BLOCK_IRQ, 0)
    proc_set_current(init)
    if not proc_mark_exit(b_pid).is_ok()
        return 8
    # The wake is the state word's CAS alone (#4879): `block` means something
    # only while BLOCKED, and only its owner writes it.
    if proc_state(b) != PROC_RUNNING or not proc_reap_pending(proc_at(b))
        return 9
    # the marked pid's exit: a zombie for init, and the mark goes with the slot
    proc_set_current(d)
    proc_exit_current(137)
    proc_set_current(init)
    if proc_wait(d_pid) != 137
        return 10
    let n: i32 = proc_new_child()
    if proc_reap_pending(proc_at(n))
        return 11
    # a zombie is not marked: it has already exited
    proc_set_current(b)
    proc_exit_current(0)
    proc_set_current(init)
    if not refused(proc_mark_exit(b_pid), MarkError.NoProcess)
        return 12
    0
"""

REAP_CLAIMS = {1: "no process before init: nothing to mark",
               2: "process_mark_exit refuses pid 1",
               3: "an unknown pid is Errno.Srch",
               4: "a running child is marked",
               5: "the mark is PROC_REAP; the pid stays runnable",
               6: "the caller is not the process that exits",
               7: "only the named pid is marked",
               8: "a parked pid is marked",
               9: "marking a parked pid wakes it",
               10: "the marked pid's exit is reaped as any exit",
               11: "a reused slot carries no mark",
               12: "a zombie can't be marked"}

NESTING_CLAIMS = {1: "no process before init", 2: "init is pid 1 in /",
                  3: "init records its page table and has no parent",
                  4: "rzsh is pid 2 and inherits /", 5: "rzsh can chdir",
                  6: "script is pid 3 and inherits rzsh's /etc", 7: "script can chdir",
                  8: "command is pid 4 and inherits /bin",
                  9: "every ancestor blocks on its child",
                  10: "the command runs; four processes live",
                  11: "only the command is runnable",
                  12: "command's exit wakes script", 13: "script runs again, still in /bin",
                  14: "script reaps 4's exit 42 exactly once",
                  15: "script's exit wakes rzsh in /etc",
                  16: "wait on a non-child fails with Errno.Child", 17: "rzsh reaps script's 42",
                  18: "init runs again in / despite its children's chdir",
                  19: "init reaps rzsh's 7; only init is left"}

LIFECYCLE_CLAIMS = {1: "no spawn before init", 2: "init enters",
                    3: "a new child is pid 2, NEW, and init stays current",
                    4: "a NEW child is never scheduled",
                    5: "an aborted child frees its slot and can't be waited for",
                    6: "pids are distinct",
                    7: "b stays a zombie until reaped",
                    8: "a's exit frees its zombie child; init reaps a",
                    9: "MAX_PROCS slots fill", 10: "a full table fails with Errno.Again",
                    11: "each child is reaped", 12: "nothing leaks",
                    13: "init's exit has no parent and changes nothing"}

SCHED_CLAIMS = {1: "nothing runnable before init", 2: "non-blocking spawn leaves init running",
                3: "round robin: init -> a", 4: "a -> b", 5: "b -> init",
                6: "a running child is LIVE to proc_child_status",
                7: "a process waiting for a child is skipped", 8: "a -> b while init waits",
                9: "b -> a while init waits",
                10: "another child's exit doesn't wake init", 11: "a still runs",
                12: "with everyone blocked nothing is runnable",
                13: "an input wake leaves a child-waiter blocked",
                14: "console input wakes its reader",
                15: "the awaited child's exit wakes init",
                16: "init sees a's exit code before reaping", 17: "and b's",
                18: "init reaps both", 19: "reaped children are gone",
                20: "a child whose parent exits is detached and still runs",
                21: "nobody can wait for a detached child",
                22: "a detached child's exit frees its slot",
                23: "only pid 1 is init"}


@pytest.mark.integration
def test_spawn_nests_init_rzsh_script_command(tmp_path):
    rc = _run(tmp_path, NESTING)
    assert rc == 0, NESTING_CLAIMS.get(rc, f"exit {rc}")


@pytest.mark.integration
def test_spawn_abort_orphans_and_full_table(tmp_path):
    rc = _run(tmp_path, LIFECYCLE)
    assert rc == 0, LIFECYCLE_CLAIMS.get(rc, f"exit {rc}")


@pytest.mark.integration
def test_round_robin_blocking_and_detached_children(tmp_path):
    rc = _run(tmp_path, SCHED)
    assert rc == 0, SCHED_CLAIMS.get(rc, f"exit {rc}")


@pytest.mark.integration
def test_mark_exit_refuses_init_and_wakes_a_parked_pid(tmp_path):
    rc = _run(tmp_path, REAP)
    assert rc == 0, REAP_CLAIMS.get(rc, f"exit {rc}")

# The state word and per-CPU current (AGAST #4879, SMP_USER.md §2 and §4).
# g_cpu, g_kicks and g_kicked are CPU_HOOKS's: the CPU index the table sees,
# and the kicks its wakes sent.
SMP_STATE = """\
import syscall.errno { Errno }
import proc.table

fn main() -> i32
    proc_table_reset()
    proc_enter_init(0)
    let init: i32 = proc_current_slot()
    let a: i32 = proc_new_child()
    g_kicks = 0
    proc_start(a)
    # A start publishes RUNNING and kicks the process's CPU (the BSP).
    if proc_state(a) != PROC_RUNNING or g_kicks != 1 or g_kicked != PROC_BSP_CPU
        return 1

    # Per CPU: CPU 1 has no current process and its pick finds nothing
    # (no process is homed there); CPU 0's is untouched.
    g_cpu = 1
    if proc_current_slot() != -1 or proc_current() != 0 as *Proc or proc_pick_next() != -1
        return 2
    proc_set_current(a)
    g_cpu = 0
    if proc_current_slot() != init
        return 3
    g_cpu = 1
    proc_set_current(-1)
    g_cpu = 0

    # The eventcount re-check: announce BLOCKED, find the condition met, run on.
    proc_set_current(a)
    proc_block(BLOCK_WAIT, 0)
    if proc_state(a) != PROC_BLOCKED
        return 4
    proc_unblock_current()
    if proc_state(a) != PROC_RUNNING
        return 5

    # A wake is one CAS: a waker that read the word, then lost the race to
    # another wake, changes nothing.
    proc_block(BLOCK_WAIT, 0)
    let seen: u64 = proc_word(a)
    g_kicks = 0
    if not proc_wake_seen(a, seen) or proc_state(a) != PROC_RUNNING or g_kicks != 1
        return 6
    if proc_wake_seen(a, seen) or g_kicks != 1
        return 7

    # The generation: a waker that read the slot's last process cannot wake
    # the next one in the same slot, though both are BLOCKED.
    proc_block(BLOCK_WAIT, 0)
    let stale: u64 = proc_word(a)
    proc_set_current(init)
    if not proc_mark_exit(proc_at(a).pid).is_ok()
        return 8
    proc_set_current(a)
    proc_exit_current(0)
    proc_set_current(init)
    proc_wait(proc_at(a).pid)
    if proc_state(a) != PROC_FREE
        return 9
    let b: i32 = proc_new_child()
    if b != a
        return 10
    proc_start(b)
    proc_set_current(b)
    proc_block(BLOCK_WAIT, 0)
    proc_set_current(init)
    if proc_wake_seen(b, stale) or proc_state(b) != PROC_BLOCKED
        return 11
    if not proc_wake_pid(proc_at(b).pid, BLOCK_WAIT) or proc_state(b) != PROC_RUNNING
        return 12
    0
"""

SMP_STATE_CLAIMS = {
    1: "a start publishes RUNNING and kicks the BSP once",
    2: "another CPU has no current process and picks nothing",
    3: "CPU 0's current process is its own",
    4: "proc_block announces BLOCKED",
    5: "the re-check's unblock makes it RUNNING",
    6: "a wake from the word it read succeeds and kicks",
    7: "a second wake from the same word does nothing",
    8: "mark_exit",
    9: "the exited, reaped slot is free",
    10: "the next child reuses the slot",
    11: "a wake from the last generation's word does nothing",
    12: "a wake by pid wakes the new process",
}


@pytest.mark.integration
def test_state_word_cas_generation_and_per_cpu_current(tmp_path):
    rc = _run(tmp_path, SMP_STATE)
    assert rc == 0, SMP_STATE_CLAIMS.get(rc, f"exit {rc}")

# Pinning (AGAST #4881, docs/SMP_USER.md §1, §2, §5): a process's home is
# where its user code runs, `on` where it is right now (its home, or the
# BSP during a forwarded syscall). A CPU picks only what is on it; a start
# and a wake kick the CPU the process is on.
PINNING = """\
import syscall.errno { Errno }
import proc.table

fn main() -> i32
    proc_table_reset()
    proc_enter_init(0)
    let init: i32 = proc_current_slot()
    if proc_home(init) != PROC_BSP_CPU or proc_on(init) != PROC_BSP_CPU
        return 1
    let a: i32 = proc_new_child()
    if proc_home(a) != PROC_BSP_CPU
        return 2
    proc_set_home(a, 3)
    g_kicks = 0
    proc_start(a)
    if g_kicks != 1 or g_kicked != 3 or proc_on(a) != 3 or proc_on_cpu(proc_at(a).pid) != 3
        return 3
    # CPU 3 picks it, the BSP never does.
    g_cpu = 3
    if proc_pick_next() != a
        return 4
    g_cpu = 0
    if proc_pick_next() != init
        return 5
    # Live processes homed on CPU 3, and runnable ones on each CPU.
    if proc_homed_count(3) != 1 or proc_homed_count(0) != 1 or proc_runnable_on(3) != 1 or proc_runnable_on(0) != 1
        return 6
    # A child of a process homed on an AP is homed on the BSP.
    g_cpu = 3
    proc_set_current(a)
    let c: i32 = proc_new_child()
    if proc_home(c) != PROC_BSP_CPU
        return 7
    proc_abort_child(c)
    # A forwarded syscall: `a` is on the BSP, still homed on 3.
    proc_set_current(-1)
    proc_set_on(a, PROC_BSP_CPU)
    if proc_pick_next() != -1 or proc_home(a) != 3 or proc_on_cpu(proc_at(a).pid) != PROC_BSP_CPU
        return 8
    g_cpu = 0
    if proc_runnable_on(0) != 2
        return 9
    # It blocks on the BSP; a wake kicks the BSP, where it is.
    proc_set_current(a)
    proc_block(BLOCK_WAIT, 0)
    proc_set_current(init)
    g_kicks = 0
    if not proc_wake_pid(proc_at(a).pid, BLOCK_WAIT) or g_kicked != PROC_BSP_CPU
        return 10
    # Back home: it blocks there, and a wake kicks CPU 3.
    proc_set_on(a, 3)
    g_cpu = 3
    proc_set_current(a)
    proc_block(BLOCK_WAIT, 0)
    g_cpu = 0
    if not proc_wake_pid(proc_at(a).pid, BLOCK_WAIT) or g_kicked != 3
        return 11
    # A zombie is not a live homed process; a home set after the start is
    # refused (only spawn places).
    proc_set_home(a, 1)
    if proc_home(a) != 3
        return 12
    g_cpu = 3
    proc_set_current(a)
    proc_exit_current(0)
    if proc_homed_count(3) != 0
        return 13
    0
"""

PINNING_CLAIMS = {
    1: "init is homed on and on the BSP",
    2: "a new child is homed on the BSP",
    3: "a start on an AP kicks that AP once and puts the process on it",
    4: "the home CPU picks it",
    5: "the BSP does not pick a process on an AP",
    6: "homed and runnable counts are per CPU",
    7: "a child of an AP-homed process is homed on the BSP",
    8: "on the BSP for a forwarded call: the home picks nothing, the home stays",
    9: "the BSP counts the forwarded process as runnable there",
    10: "a wake of a process on the BSP kicks the BSP",
    11: "a wake of a process back home kicks its home",
    12: "the home of a started process does not change",
    13: "an exited process is not homed anywhere",
}


@pytest.mark.integration
def test_pinned_home_on_pick_and_kicks(tmp_path):
    rc = _run(tmp_path, PINNING)
    assert rc == 0, PINNING_CLAIMS.get(rc, f"exit {rc}")

# --- source-level acceptance -------------------------------------------------------

def _code(path):
    """Source with `#` comments stripped (no `#` occurs inside a string literal here)."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _kernel_sources():
    return sorted(KERNEL_SRC.rglob("*.ritz"))


@pytest.mark.parametrize("name", ["g_parent_ctx", "g_parent_frame", "g_has_parent",
                                  "g_child_pid", "g_child_pml4", "g_child_exit_code", "g_cwd"])
def test_no_single_parent_globals(name):
    hits = [str(p.relative_to(KERNEL_SRC)) for p in _kernel_sources()
            if re.search(rf"\b{name}\b", _code(p))]
    assert not hits, f"{name} still in {hits}"


def test_scheduler_is_deleted_and_main_no_longer_imports_it():
    # Tracked files only (AGAST #4672): a reused checkout keeps sched/ alive
    # with an ignored mod.ritz.sig, which is not the scheduler coming back.
    assert not is_tracked(KERNEL_SRC / "sched"), "sched/ is back"
    assert not is_tracked(HARLAND / "kernel" / "context_switch.s")
    assert "context_switch.s" not in (HARLAND / "ritz.toml").read_text()
    main = _code(KERNEL_SRC / "main.ritz")
    assert not re.search(r"^import sched\b", main, re.MULTILINE)
    for sym in ("tasks", "cpu_sched", "scheduler_lock", "scheduler_initialized", "scheduler_init"):
        assert not re.search(rf"\b{sym}\b", main), sym


def test_process_layer_runs_spawn_wait_and_cwd_on_the_table():
    process = _code(KERNEL_SRC / "syscall" / "runtime" / "process.ritz")
    for fn in ("proc_new_child", "proc_start", "proc_abort_child", "proc_exit_current",
               "proc_wait", "proc_child_status", "proc_block", "proc_enter_init"):
        assert re.search(rf"\b{fn}\(", process), fn
    # blocking goes through the scheduler (#3629), not a saved user frame
    for fn in ("sched_block", "sched_exit", "sched_yield", "sched_prepare_user"):
        assert re.search(rf"\b{fn}\(", process), fn
    assert "resume_user_frame" not in process and "syscall_save_user_frame" not in process
    # the child's pid comes from the table, not a constant
    assert not re.search(r"pid\s*=\s*2\b", process)
    cwd = _code(KERNEL_SRC / "syscall" / "runtime" / "cwd.ritz")
    assert re.search(r"\bproc_cwd\(", cwd) and re.search(r"\bproc_set_cwd\(", cwd)


def _asm_code(path):
    """Assembly with `#` comments stripped."""
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _asm_body(src, start, end):
    """The text of `src` from label `start:` up to the first `end` after it."""
    head = src.split(f"\n{start}:", 1)
    assert len(head) == 2, f"no {start}: label"
    return head[1].split(end, 1)[0]


KERNEL = HARLAND / "kernel"


# A PROC_REAP pid enters sys_exit_impl from the return to user instead of
# returning there (#4714): the syscall exit before it picks sysretq or the
# IRETQ fallback, and every interrupt return to CPL 3. reap_if_marked
# (syscall_entry.s) is the only way in, and it runs process_reap_exit on the
# pid's own kernel stack (PC_KSTACK_TOP).
@pytest.mark.parametrize("path, start, end", [
    ("syscall_entry.s", "syscall_entry", "sysretq"),
    ("isr_stubs.s", "isr_common", "iretq"),
    ("isr_stubs.s", "irq_common", "iretq"),
    ("proc_switch.s", "proc_first_entry", "iretq"),
])
def test_return_to_user_checks_proc_reap(path, start, end):
    body = _asm_body(_asm_code(KERNEL / path), start, end)
    assert "call reap_if_marked" in body, f"{start} returns to user without the PROC_REAP check"
    # the check runs before the GPRs come off the frame: a call clobbers them
    assert body.index("call reap_if_marked") < body.index("popq %r15")
    if start == "syscall_entry":
        tail = body.split("call syscall_handler", 1)[1]
        # after the handler, with IF=0, before the sysretq / IRETQ choice
        assert tail.index("cli") < tail.index("call reap_if_marked") < tail.index("jne .Lsyscall_exit_iret")
    elif start != "proc_first_entry":
        # an interrupt return checks only a frame whose CS has a non-zero RPL
        pre = body.split("call reap_if_marked", 1)[0]
        assert re.search(r"testq \$3, 144\(%rsp\)\s*\n\s*jz ", pre), "no CPL check"


def test_reap_check_enters_sys_exit_impl_on_the_pid_kernel_stack():
    fn = _asm_body(_asm_code(KERNEL / "syscall_entry.s"), "reap_if_marked", ".size reap_if_marked")
    assert "call proc_reap_current" in fn
    # the frame being returned through is abandoned: the pid's own stack top
    switch = fn.index("movq %gs:PC_KSTACK_TOP, %rsp")
    assert fn.index("call proc_reap_current") < switch < fn.index("call process_reap_exit")
    process = _code(KERNEL_SRC / "syscall" / "runtime" / "process.ritz")
    reap = process.split("pub fn process_reap_exit", 1)[1].split("\npub fn ", 1)[0].split("\nfn ", 1)[0]
    assert re.search(r"\bsys_exit_impl\(PROC_REAP_STATUS\)", reap)
    assert "process_kill_current" not in reap


def test_mark_exit_is_not_kill_current_and_no_wait_loop_grows_the_check():
    process = _code(KERNEL_SRC / "syscall" / "runtime" / "process.ritz")
    mark = process.split("pub fn process_mark_exit", 1)[1].split("\npub fn ", 1)[0]
    assert re.search(r"\bproc_mark_exit\(", mark)
    assert "process_kill_current" not in mark and "sys_exit_impl" not in mark
    # round-3 item 15: wait_for_child, the tty read and BLOCK_IRQ don't check it
    wait = process.split("fn wait_for_child", 1)[1].split("\nfn ", 1)[0]
    assert "proc_reap" not in wait and "PROC_REAP" not in wait
    for rel in ("proc/sched.ritz", "tty/fg.ritz"):
        p = KERNEL_SRC / rel
        if p.exists():
            assert "PROC_REAP" not in _code(p), rel


def test_init_boot_suite_runs_three_level_nesting():
    src = INIT.read_text()
    assert "run_nested_spawn_test()" in _code(INIT).split("fn run_tier1_tests", 1)[1]
    # rzsh runs a script line that runs rzsh, which runs /bin/exitcode
    assert re.search(r"rzsh -c .*exitcode", src), "no init -> rzsh -> script -> command line"


# Buddhafinger M7 (#4954, review finding 9): init, rzsh, the editor, ritz-lsp
# and the ritz1 it runs per compile take five slots before the ring-1 driver,
# netd or anything the user starts. The table holds 32, and the one constant
# per module sizes every per-slot array, so raising it can't leave one behind.
PROC_SLOTS = 32

PER_SLOT_ARRAYS = [
    ("proc/table.ritz", "procs", "MAX_PROCS", "Proc"),
    ("fs/syscall.ritz", "fs_procs", "FS_MAX_PROCS", r"\*FsProc"),
    ("proc/waitset.ritz", "waitset_deadline", "MAX_PROCS", "u64"),
    ("proc/waitset.ritz", "waitset_console", "MAX_PROCS", "bool"),
    ("proc/waitset.ritz", "inbox", r"MAX_PROCS \* INBOX_CAP", "WaitEvent"),
    ("proc/waitset.ritz", "inbox_len", "MAX_PROCS", "u32"),
    ("proc/waitset.ritz", "inbox_pid", "MAX_PROCS", "u64"),
]


@pytest.mark.unit
def test_the_table_holds_thirty_two_processes():
    table = _code(KERNEL_SRC / "proc" / "table.ritz")
    assert re.search(rf"^pub const MAX_PROCS: i32 = {PROC_SLOTS}$", table, re.M)
    fs = _code(KERNEL_SRC / "fs" / "syscall.ritz")
    assert re.search(rf"^pub const FS_MAX_PROCS: i32 = {PROC_SLOTS}$", fs, re.M), \
        "an FsProc per Proc slot"


@pytest.mark.unit
@pytest.mark.parametrize("rel,name,length,elem", PER_SLOT_ARRAYS,
                         ids=[a[1] for a in PER_SLOT_ARRAYS])
def test_per_slot_arrays_take_their_length_from_the_constant(rel, name, length, elem):
    src = _code(KERNEL_SRC / rel)
    assert re.search(rf"^var {name}: \[{length}\]{elem}$", src, re.M), \
        f"{rel}: {name} is not [{length.replace(chr(92), '')}]"
