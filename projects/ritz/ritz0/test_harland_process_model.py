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

RITZ0_DIR = Path(__file__).resolve().parent
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

fn main() -> i32
    proc_table_reset()
    if proc_current() != 0 as *Proc or proc_current_pid() != 0
        return 1
    if proc_enter_init(4096) != 0 or proc_current_pid() != 1 or not cwd_is(c"/", 1)
        return 2
    let init: *Proc = proc_current()
    if init.pml4 != 4096 or init.parent != -1
        return 3
    # init -> rzsh -> script -> command, each a new pid with the cwd it
    # inherited, the parent blocked on its own frame
    if proc_spawn_child() != 0 or proc_current_pid() != 2 or not cwd_is(c"/", 1)
        return 4
    let rzsh: *Proc = proc_current()
    if proc_set_cwd(c"/etc", 4) != 0
        return 5
    if proc_spawn_child() != 0 or proc_current_pid() != 3 or not cwd_is(c"/etc", 4)
        return 6
    let script: *Proc = proc_current()
    if proc_set_cwd(c"/bin", 4) != 0
        return 7
    if proc_spawn_child() != 0 or proc_current_pid() != 4 or not cwd_is(c"/bin", 4)
        return 8
    let cmd: *Proc = proc_current()
    if init.state != PROC_BLOCKED or rzsh.state != PROC_BLOCKED or script.state != PROC_BLOCKED
        return 9
    if cmd.state != PROC_RUNNING or proc_live_count() != 4
        return 10
    # every process saves its own frame: writing one leaves the others
    *proc_frame(init) = 11
    *proc_frame(rzsh) = 22
    *proc_frame(script) = 33
    if *proc_frame(init) != 11 or *proc_frame(rzsh) != 22 or *proc_frame(script) != 33
        return 11
    # command exits 42: script resumes in /bin and reaps it, once
    if proc_exit_current(42) != script or proc_current() != script
        return 12
    if script.state != PROC_RUNNING or not cwd_is(c"/bin", 4)
        return 13
    if proc_wait(4) != 42 or proc_wait(4) != Errno.Child as i64
        return 14
    # script exits 42: rzsh resumes in /etc
    if proc_exit_current(42) != rzsh or proc_current_pid() != 2 or not cwd_is(c"/etc", 4)
        return 15
    # rzsh can't reap its parent or a pid that never was
    if proc_wait(1) != Errno.Child as i64 or proc_wait(99) != Errno.Child as i64
        return 16
    if proc_wait(3) != 42
        return 17
    # rzsh exits 7: init resumes in "/", untouched by its children's chdir
    if proc_exit_current(7) != init or proc_current_pid() != 1 or not cwd_is(c"/", 1)
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
    if proc_spawn_child() != Errno.Srch as i32
        return 1
    if proc_enter_init(0) != 0
        return 2
    let init: *Proc = proc_current()
    # a spawn that fails before the child runs gives init back, unblocked
    if proc_spawn_child() != 0 or proc_current_pid() != 2
        return 3
    proc_abort_child()
    if proc_current() != init or init.state != PROC_RUNNING or proc_live_count() != 1
        return 4
    if proc_wait(2) != Errno.Child as i64
        return 5
    # init -> a -> b: b exits unreaped, then a exits: a's zombie child goes
    # with it, a stays for init to reap
    if proc_spawn_child() != 0
        return 6
    let a: u64 = proc_current_pid()
    if proc_spawn_child() != 0
        return 7
    let b: u64 = proc_current_pid()
    if b == a or a == 1
        return 8
    proc_exit_current(3)
    if proc_live_count() != 3
        return 9
    proc_exit_current(5)
    if proc_live_count() != 2 or proc_wait(b) != Errno.Child as i64 or proc_wait(a) != 5
        return 10
    # MAX_PROCS slots: nesting fills them, then spawn fails and changes nothing
    var depth: i32 = 1
    while depth < MAX_PROCS
        if proc_spawn_child() != 0
            return 11
        depth = depth + 1
    let deepest: u64 = proc_current_pid()
    if proc_spawn_child() != Errno.Again as i32 or proc_current_pid() != deepest
        return 12
    # unwinding frees them all
    while proc_current() != init
        let pid: u64 = proc_current_pid()
        proc_exit_current(0)
        if proc_wait(pid) != 0
            return 13
    if proc_live_count() != 1
        return 14
    # init exiting has no parent to resume
    if proc_exit_current(0) != 0 as *Proc
        return 15
    0
"""

NESTING_CLAIMS = {1: "no process before init", 2: "init is pid 1 in /",
                  3: "init records its page table and has no parent",
                  4: "rzsh is pid 2 and inherits /", 5: "rzsh can chdir",
                  6: "script is pid 3 and inherits rzsh's /etc", 7: "script can chdir",
                  8: "command is pid 4 and inherits /bin",
                  9: "every ancestor blocks on its child",
                  10: "the command runs; four processes live",
                  11: "each process has its own saved frame",
                  12: "command's exit resumes script", 13: "script runs again, still in /bin",
                  14: "script reaps 4's exit 42 exactly once",
                  15: "script's exit resumes rzsh in /etc",
                  16: "wait on a non-child fails with Errno.Child", 17: "rzsh reaps script's 42",
                  18: "init resumes in / despite its children's chdir",
                  19: "init reaps rzsh's 7; only init is left"}

LIFECYCLE_CLAIMS = {1: "no spawn before init", 2: "init enters", 3: "spawn makes pid 2",
                    4: "an aborted spawn gives init back, unblocked, with no slot used",
                    5: "an aborted child can't be waited for",
                    6: "init spawns a", 7: "a spawns b", 8: "pids are distinct",
                    9: "b stays a zombie until reaped",
                    10: "a's exit reaps its zombie child; init reaps a",
                    11: "spawn nests MAX_PROCS deep", 12: "a full table fails with Errno.Again",
                    13: "each level unwinds and is reaped", 14: "nothing leaks",
                    15: "init's exit has no parent"}


@pytest.mark.integration
def test_spawn_nests_init_rzsh_script_command(tmp_path):
    rc = _run(tmp_path, NESTING)
    assert rc == 0, NESTING_CLAIMS.get(rc, f"exit {rc}")


@pytest.mark.integration
def test_spawn_abort_orphans_and_full_table(tmp_path):
    rc = _run(tmp_path, LIFECYCLE)
    assert rc == 0, LIFECYCLE_CLAIMS.get(rc, f"exit {rc}")


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
    for fn in ("proc_spawn_child", "proc_abort_child", "proc_exit_current", "proc_wait",
               "proc_frame", "proc_enter_init"):
        assert re.search(rf"\b{fn}\(", process), fn
    # the child's pid comes from the table, not a constant
    assert not re.search(r"pid\s*=\s*2\b", process)
    cwd = _code(KERNEL_SRC / "syscall" / "runtime" / "cwd.ritz")
    assert re.search(r"\bproc_cwd\(", cwd) and re.search(r"\bproc_set_cwd\(", cwd)


def test_init_boot_suite_runs_three_level_nesting():
    src = INIT.read_text()
    assert "run_nested_spawn_test()" in _code(INIT).split("fn run_tier1_tests", 1)[1]
    # rzsh runs a script line that runs rzsh, which runs /bin/exitcode
    assert re.search(r"rzsh -c .*exitcode", src), "no init -> rzsh -> script -> command line"
