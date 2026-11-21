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
    (tmp_path / "t.ritz").write_text(src)
    objs.insert(0, str(_compile(tmp_path, tmp_path / "t.ritz", "t")))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True, check=False)
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode


NESTING = """\
import syscall.errno { Errno }
import proc.table

fn cwd_is(want: *u8, n: i64) -> bool
    var len: u16 = 0
    let c: *u8 = proc_cwd(@len)
    if len as i64 != n or *(c + n) != 0
        return false
    var i: i64 = 0
    while i < n
        if *(c + i) != *(want + i)
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
    if proc_enter_init(4096) != 0 or proc_current_pid() != 1 or not cwd_is(c"/", 1)
        return 2
    let init: *Proc = proc_current()
    if init.pml4 != 4096 or init.parent != -1 or not proc_is_init(init)
        return 3
    # init -> rzsh -> script -> command, each a new pid with the cwd it
    # inherited, the parent blocked on its child
    if spawn_blocking() != 0 or proc_current_pid() != 2 or not cwd_is(c"/", 1)
        return 4
    let rzsh: *Proc = proc_current()
    if proc_set_cwd(c"/etc", 4) != 0
        return 5
    if spawn_blocking() != 0 or proc_current_pid() != 3 or not cwd_is(c"/etc", 4)
        return 6
    let script: *Proc = proc_current()
    if proc_set_cwd(c"/bin", 4) != 0
        return 7
    if spawn_blocking() != 0 or proc_current_pid() != 4 or not cwd_is(c"/bin", 4)
        return 8
    let cmd: *Proc = proc_current()
    if init.state != PROC_BLOCKED or rzsh.state != PROC_BLOCKED or script.state != PROC_BLOCKED
        return 9
    if cmd.state != PROC_RUNNING or proc_live_count() != 4
        return 10
    # only the command can run: the round robin never picks a blocked ancestor
    if proc_pick_next() != proc_current_slot()
        return 11
    # command exits 42: script runs again in /bin and reaps it, once
    if exit_to_parent(42) != script or proc_current() != script
        return 12
    if script.state != PROC_RUNNING or not cwd_is(c"/bin", 4)
        return 13
    if proc_wait(4) != 42 or proc_wait(4) != Errno.Child as i64
        return 14
    # script exits 42: rzsh runs again in /etc
    if exit_to_parent(42) != rzsh or proc_current_pid() != 2 or not cwd_is(c"/etc", 4)
        return 15
    # rzsh can't reap its parent or a pid that never was
    if proc_wait(1) != Errno.Child as i64 or proc_wait(99) != Errno.Child as i64
        return 16
    if proc_wait(3) != 42
        return 17
    # rzsh exits 7: init runs again in "/", untouched by its children's chdir
    if exit_to_parent(7) != init or proc_current_pid() != 1 or not cwd_is(c"/", 1)
        return 18
    if proc_wait(2) != 7 or proc_live_count() != 1
        return 19
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
    if c < 0 or proc_at(c).pid != 2 or proc_at(c).state != PROC_NEW or proc_current() != init
        return 3
    # a NEW child is never picked: it has no kernel stack to switch to yet
    if proc_pick_next() != proc_current_slot()
        return 4
    proc_abort_child(c)
    if init.state != PROC_RUNNING or proc_live_count() != 1 or proc_wait(2) != Errno.Child as i64
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
    if proc_live_count() != 3 or proc_at(b).state != PROC_ZOMBIE
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
    if proc_exit_current(0) != -1 or proc_current() != init or init.state != PROC_RUNNING
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
    if proc_current_slot() != init or proc_at(init).state != PROC_RUNNING
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
    if proc_at(init).state != PROC_BLOCKED or proc_at(b).state != PROC_ZOMBIE
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
    if proc_at(init).state != PROC_BLOCKED
        return 13
    if proc_at(a).state != PROC_RUNNING or proc_pick_next() != a
        return 14
    # a exits: init wakes and sees both exit codes, unreaped until it waits
    proc_exit_current(4)
    if proc_at(init).state != PROC_RUNNING or proc_pick_next() != init
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
    if proc_at(q).detached == 0 or proc_at(q).parent != -1 or proc_at(q).state != PROC_RUNNING
        return 20
    proc_set_current(init)
    if proc_child_status(q_pid, @code) != Errno.Child as i32 or proc_wait(p_pid) != 0
        return 21
    proc_set_current(q)
    proc_exit_current(3)
    if proc_at(q).state != PROC_FREE or proc_live_count() != 1
        return 22
    # a detached process is not init: only pid 1 is
    if proc_is_init(proc_at(q)) or not proc_is_init(proc_at(init))
        return 23
    0
"""

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
    assert not (KERNEL_SRC / "sched").exists(), "sched/ is back"
    assert not (HARLAND / "kernel" / "context_switch.s").exists()
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


def test_init_boot_suite_runs_three_level_nesting():
    src = INIT.read_text()
    assert "run_nested_spawn_test()" in _code(INIT).split("fn run_tier1_tests", 1)[1]
    # rzsh runs a script line that runs rzsh, which runs /bin/exitcode
    assert re.search(r"rzsh -c .*exitcode", src), "no init -> rzsh -> script -> command line"
