"""Harland pipes and spawn with stdio redirection (AGAST #4955, Buddhafinger M7).

ritz-lsp talks to its client over stdin/stdout and runs ritz1 per compile,
so Harland needs pipe(2) and a spawn that maps a child's fds 0-2.

* fs/pipe.ritz is the pipe: a PIPE_CAPACITY-byte ring with reader and writer
  counts. It never blocks: an empty read with a writer left, or a full
  write, is Err(Again); an empty read with no writer is Ok(0) (EOF); a write
  with no reader is Err(Pipe); a write with room for some is short.
* fs/syscall.ritz binds ends to fds (FD_KIND_PIPE): fs_pipe_open makes the
  two, close and exit release them (fds 0-2 included), fstat says S_IFIFO,
  and fs_process_give_stdio hands a spawned child its 0-2 from the parent's
  fds, sharing pipe ends, refusing files and unopened fds.
* the syscall layer: pipe is number 29, spawn_io (SpawnIo) takes the
  child's stdio map, read/write/close/poll route pipe fds before the
  console, a read or write that would block parks on BLOCK_PIPE, and every
  change wakes those and poll's pipe watchers.

The behaviour tests compile the real modules into host programs (the fd
layer with test_harland_fd_tables.py's stand-ins); exit codes name the
failed claim. The boot-level proof is indium's pipe_test, a Tier-1 program
that pipes a child's stdout back (projects/harland/tools/test_tier1_boot.sh).
"""

import re
import subprocess

import pytest

import test_harland_fd_tables as fdt

KERNEL_SRC = fdt.KERNEL_SRC
INDIUM = fdt.INDIUM
RITZLIB = fdt.RITZ_ROOT / "ritzlib"
COMPILERS = fdt.COMPILERS

# fs/pipe.ritz copies with Span.copy_from, whose memmove is ritzlib/str.ritz's
# (the kernel links it the same way): an absolute path, compiled as it is.
STR = str(RITZLIB / "str.ritz")
# The tests' helpers take StrView text (S-TEXT-1): link the span/strview
# bridges they call, the same way.
TEXT = [str(RITZLIB / "span.ritz"), str(RITZLIB / "strview.ritz")]
PIPE_MODULES = ["fs/pipe.ritz", "syscall/errno.ritz", STR, *TEXT]
FS_MODULES = [*fdt.FS_MODULES, *(m for m in TEXT if m not in fdt.FS_MODULES)]


def _fn(path, name):
    return fdt._fn(path, name)


# --- the ring (fs/pipe.ritz) ------------------------------------------------------

RING = """\
import ritzlib.option
import ritzlib.result
import ritzlib.span { Span, Bytes, span_from_strview }
import ritzlib.strview { StrView }
import syscall.errno { Errno }
import fs.pipe

var g_buf: [8192]u8

# A result as one number: the count, or the Errno's (negative) value.
fn n_of(r: Result<i64, Errno>) -> i64
    match r
        Ok(n) => n
        Err(e) => e as i64

fn bytes(s: StrView) -> Span<u8>
    span_from_strview(s)

# g_buf[a..b] as a span.
fn region(a: i64, b: i64) -> Span<u8>
    let all: Span<u8> = @g_buf
    all.slice(a, b)

fn out(n: i64) -> Span<u8>
    region(0, n)

# The first want.len() bytes of g_buf are exactly `want`.
fn got(want: StrView) -> bool
    let head: Span<u8> = out(want.len())
    head.as_strview().eq(want)

fn main() -> i32
    if pipe_count() != 0 or PIPE_CAPACITY != 4096
        return 1
    var p: i32 = -1
    match pipe_create()
        Ok(n) => p = n
        Err(_) => return 2
    # empty with a writer: would block
    if n_of(pipe_read(p, out(16))) != Errno.Again as i64 or pipe_readable(p)
        return 3
    if not pipe_writable(p)
        return 4
    # bytes come out in order, a partial read leaves the rest
    if n_of(pipe_write(p, bytes("hello"))) != 5 or not pipe_readable(p)
        return 5
    if n_of(pipe_read(p, out(3))) != 3 or not got("hel")
        return 6
    if n_of(pipe_read(p, out(16))) != 2 or not got("lo")
        return 7
    # a full pipe: a short write, then Again; reading makes room again
    var i: i64 = 0
    while i < 8192
        g_buf[i] = (i % 251) as u8
        i = i + 1
    if n_of(pipe_write(p, region(0, 4000))) != 4000
        return 8
    if n_of(pipe_write(p, region(4000, 4200))) != 96 or pipe_writable(p)
        return 9
    if n_of(pipe_write(p, region(0, 1))) != Errno.Again as i64
        return 10
    # wrap around the ring's end: drain 1000, write 1000 more, read it all back
    if n_of(pipe_read(p, out(1000))) != 1000 or g_buf[999] != (999 % 251) as u8
        return 11
    var src: [1000]u8
    i = 0
    while i < 1000
        src[i] = ((4096 + i) % 251) as u8
        i = i + 1
    if n_of(pipe_write(p, @src)) != 1000
        return 12
    if n_of(pipe_read(p, out(8192))) != 4096
        return 13
    i = 0
    while i < 4096
        if g_buf[i] != ((1000 + i) % 251) as u8
            return 14
        i = i + 1
    # the last writer gone: drain what is left, then end of file
    if n_of(pipe_write(p, bytes("tail"))) != 4
        return 15
    pipe_release(pipe_writer(p))
    if not pipe_readable(p) or n_of(pipe_read(p, out(16))) != 4 or not got("tail")
        return 16
    if n_of(pipe_read(p, out(16))) != 0 or n_of(pipe_read(p, out(16))) != 0
        return 17
    # both ends gone: the pipe is free and its number reads as closed
    pipe_release(pipe_reader(p))
    if pipe_count() != 0 or n_of(pipe_read(p, out(1))) != Errno.BadF as i64
        return 18
    # the last reader gone: a write is Pipe; a held end needs two releases
    var q: i32 = -1
    match pipe_create()
        Ok(n) => q = n
        Err(_) => return 19
    pipe_hold(pipe_reader(q))
    pipe_release(pipe_reader(q))
    if n_of(pipe_write(q, bytes("x"))) != 1
        return 20
    pipe_release(pipe_reader(q))
    if n_of(pipe_write(q, bytes("x"))) != Errno.Pipe as i64 or not pipe_writable(q)
        return 21
    pipe_release(pipe_writer(q))
    # PIPE_MAX at once, then NFile; zero-length calls touch nothing
    var k: i32 = 0
    while k < PIPE_MAX
        match pipe_create()
            Ok(_) => pass
            Err(_) => return 22
        k = k + 1
    match pipe_create()
        Ok(_) => return 23
        Err(e) =>
            if e != Errno.NFile
                return 23
    if n_of(pipe_read(0, out(0))) != 0 or n_of(pipe_write(0, bytes(""))) != 0
        return 24
    # a write that wraps: 3000 buffered from offset 1000, then 1000 more
    # (96 to the ring's end, 904 from its start)
    k = 0
    while k < PIPE_MAX
        pipe_release(pipe_reader(k))
        pipe_release(pipe_writer(k))
        k = k + 1
    var w: i32 = -1
    match pipe_create()
        Ok(n) => w = n
        Err(_) => return 25
    i = 0
    while i < 8192
        g_buf[i] = (i % 251) as u8
        i = i + 1
    if n_of(pipe_write(w, region(0, 4000))) != 4000 or n_of(pipe_read(w, out(1000))) != 1000
        return 25
    i = 0
    while i < 1000
        src[i] = ((4000 + i) % 251) as u8
        i = i + 1
    if n_of(pipe_write(w, @src)) != 1000 or n_of(pipe_read(w, out(8192))) != 4000
        return 26
    i = 0
    while i < 4000
        if g_buf[i] != ((1000 + i) % 251) as u8
            return 26
        i = i + 1
    0
"""

RING_CLAIMS = {1: "no pipes at boot; capacity 4096", 2: "create", 3: "empty read with a writer -> Again",
               4: "an empty pipe is writable", 5: "write", 6: "partial read, in order",
               7: "the rest", 8: "fill most of it", 9: "a short write fills it",
               10: "full -> Again", 11: "drain some", 12: "write across the ring's end",
               13: "read a full ring", 14: "the bytes across the wrap are in order",
               15: "write before the writer goes", 16: "drain after the last writer",
               17: "then EOF, repeatedly", 18: "both ends released frees the pipe",
               19: "create again", 20: "a held reader keeps the pipe readable",
               21: "no reader -> Pipe (and poll says writable)", 22: "PIPE_MAX pipes",
               23: "then NFile", 24: "zero-length read and write",
               25: "a pipe with its head past the start", 26: "a write that wraps keeps the bytes in order"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_pipe_ring_state_machine(compiler, tmp_path):
    rc = fdt._run(compiler, tmp_path, RING, PIPE_MODULES)
    assert rc == 0, f"{compiler}: {RING_CLAIMS.get(rc, f'exit {rc}')}"


# --- pipe fds (fs/syscall.ritz) ---------------------------------------------------

PIPE_FD_PRELUDE = fdt.FS_PRELUDE + """\
import ritzlib.result
import ritzlib.span { Span, Bytes, span_from_strview }
import ritzlib.strview { StrView }
import fs.pipe { pipe_count }
import fs.vfs { S_IFIFO }

var g_out: [64]u8

fn n_of(r: Result<i64, Errno>) -> i64
    match r
        Ok(n) => n
        Err(e) => e as i64

# g_out[0..n] as a span.
fn inbox(n: i64) -> Span<u8>
    let all: Span<u8> = @g_out
    all.slice(0, n)

fn put(fd: i32, s: StrView) -> i64
    n_of(fs_pipe_write(fd, span_from_strview(s)))

# One read of fd yields exactly `want`.
fn take(fd: i32, want: StrView) -> bool
    let n = n_of(fs_pipe_read(fd, inbox(64)))
    if n != want.len()
        return false
    let head: Span<u8> = inbox(n)
    head.as_strview().eq(want)

fn open_pipe() -> PipeFds
    match fs_pipe_open()
        Ok(f) => f
        Err(_) => PipeFds { read: -1, write: -1 }

fn is_fifo(fd: i32) -> bool
    match sys_fstat(fd)
        Some(st) => (st.st_mode as u32 & 61440) == S_IFIFO
        None => false

"""

# pipe(2) in one process: the lowest free fds, read end and write end, not
# files, S_IFIFO; each end refuses the other's direction; close releases
# them (the reader then sees EOF); exit releases what is left open. Nothing
# stays allocated.
PIPE_FDS = PIPE_FD_PRELUDE + """\
fn main() -> i32
    let base: i64 = heap_live()
    if fs_process_start(1) != 0
        return 1
    let f: PipeFds = open_pipe()
    if f.read != 3 or f.write != 4 or pipe_count() != 1
        return 2
    if not is_pipe_fd(3) or not is_pipe_fd(4) or is_fs_fd(3) or is_fs_fd(4) or is_pipe_fd(0)
        return 3
    if not is_fifo(3) or not is_fifo(4)
        return 4
    if put(4, "ping") != 4 or not take(3, "ping")
        return 5
    if put(3, "x") != Errno.BadF as i64 or n_of(fs_pipe_read(4, inbox(1))) != Errno.BadF as i64
        return 6
    # sys_fs_read is the read(2) entry under test, *u8 by the syscall ABI
    if put(1, "x") != Errno.BadF as i64 or sys_fs_read(3, @g_out[0], 1) != Errno.BadF as i64
        return 7
    # an open file is not a pipe
    if sys_open(c"/a", 2, O_RDONLY, 420) != 5 or is_pipe_fd(5) or put(5, "x") != Errno.BadF as i64
        return 8
    if put(4, "bye") != 3 or sys_close(4) != 0 or is_pipe_fd(4)
        return 9
    if not take(3, "bye") or not take(3, "")
        return 10
    # a second pipe takes the freed fd 4 and the next free one
    let g: PipeFds = open_pipe()
    if g.read != 4 or g.write != 6 or pipe_count() != 2
        return 11
    if sys_close(3) != 0 or pipe_count() != 1
        return 12
    if put(6, "left") != 4
        return 13
    if fs_process_end() != 3 or pipe_count() != 0 or heap_live() != base
        return 14
    0
"""

PIPE_FDS_CLAIMS = {1: "init gets a table", 2: "pipe() is fds 3 (read) and 4 (write)",
                   3: "pipe fds are not files", 4: "fstat says S_IFIFO",
                   5: "bytes written to 4 are read from 3", 6: "each end refuses the other's direction",
                   7: "the console and file reads don't take pipe fds", 8: "a file fd is not a pipe",
                   9: "closing the write end", 10: "the reader drains, then EOF",
                   11: "the next pipe takes the lowest free fds", 12: "closing the first pipe's reader frees it",
                   13: "write to the second", 14: "exit releases every pipe fd; nothing leaked"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_pipe_fds_open_close_and_exit(compiler, tmp_path):
    rc = fdt._run(compiler, tmp_path, PIPE_FDS, FS_MODULES)
    assert rc == 0, f"{compiler}: {PIPE_FDS_CLAIMS.get(rc, f'exit {rc}')}"


# A spawn's stdio: init makes a pipe and starts a child whose stdout is the
# write end (stdin and stderr inherited: the console). init closes its copy;
# the child writes to its fd 1 and exits, and init reads the bytes, then EOF.
# A grandchild started with the inherit map gets its parent's piped fd 1. A
# map naming an unopened fd or a file is BadF and gives nothing. A child
# whose stdin is the read end sees EOF once every writer (the parent's and
# its own inherited copies) is gone.
INHERIT = PIPE_FD_PRELUDE + """\
fn spawn_with(pid: u64, map: SpawnStdio) -> bool
    # spawn_child_begin's order: the child's table, the parent current again,
    # then the handover.
    if fs_process_start(pid) != 0 or fs_process_select(fs_parent_pid(pid)) != 0
        return false
    match fs_process_give_stdio(pid, map)
        Ok(_) => true
        Err(_) => false

var g_parent: [8]u64

fn fs_parent_pid(pid: u64) -> u64
    g_parent[pid as i32]

fn main() -> i32
    let base: i64 = heap_live()
    if fs_process_start(1) != 0
        return 1
    let f: PipeFds = open_pipe()
    g_parent[2] = 1
    if not spawn_with(2, SpawnStdio { stdin: 0, stdout: f.write, stderr: 2 })
        return 2
    if sys_close(f.write) != 0
        return 3
    # the child: fd 1 is the pipe, 0 and 2 are the console
    if fs_process_select(2) != 0 or not is_pipe_fd(1) or is_pipe_fd(0) or is_pipe_fd(2) or is_pipe_fd(f.write)
        return 4
    if not is_fifo(1) or put(1, "out") != 3
        return 5
    # a grandchild inherits the child's piped fd 1
    g_parent[3] = 2
    if not spawn_with(3, spawn_stdio_inherit())
        return 6
    if fs_process_select(3) != 0 or not is_pipe_fd(1) or put(1, "!") != 1
        return 7
    if fs_process_end() != 1
        return 8
    if fs_process_select(2) != 0 or fs_process_end() != 1
        return 9
    # init: the bytes, then EOF: every writer is gone
    if fs_process_select(1) != 0 or not take(f.read, "out!") or not take(f.read, "")
        return 10
    # BadF for an unopened fd and for a file, and the child gets nothing
    g_parent[2] = 1
    if spawn_with(2, SpawnStdio { stdin: 9, stdout: 1, stderr: 2 })
        return 11
    if fs_process_select(2) != 0 or fs_process_end() != 0 or fs_process_select(1) != 0
        return 12
    if sys_open(c"/a", 2, O_RDONLY, 420) != 4
        return 13
    let g: PipeFds = open_pipe()
    if spawn_with(2, SpawnStdio { stdin: g.read, stdout: 4, stderr: 2 })
        return 14
    if fs_process_select(2) != 0 or is_pipe_fd(0) or fs_process_end() != 0 or fs_process_select(1) != 0
        return 15
    # stdin from the read end: EOF only once init's write end is closed too
    if not spawn_with(2, SpawnStdio { stdin: g.read, stdout: 1, stderr: g.read })
        return 16
    if sys_close(g.read) != 0 or put(g.write, "in") != 2
        return 17
    if fs_process_select(2) != 0 or not take(0, "in") or n_of(fs_pipe_read(0, inbox(1))) != Errno.Again as i64
        return 18
    # closing a redirected fd 2 makes it the console again; 0 still reads
    if sys_close(2) != 0 or is_pipe_fd(2) or not is_pipe_fd(0)
        return 19
    if fs_process_select(1) != 0 or sys_close(g.write) != 0
        return 20
    if fs_process_select(2) != 0 or not take(0, "") or fs_process_end() != 1
        return 21
    if fs_process_select(1) != 0 or fs_process_end() != 2 or pipe_count() != 0 or heap_live() != base
        return 22
    0
"""

INHERIT_CLAIMS = {1: "init gets a table", 2: "spawn with stdout = the pipe's write end",
                  3: "the parent closes its write end", 4: "the child's fd 1 is the pipe, 0 and 2 the console",
                  5: "the child writes its stdout", 6: "a grandchild with the inherit map",
                  7: "inherits the piped fd 1", 8: "the grandchild exits", 9: "the child exits",
                  10: "the parent reads both writes, then EOF", 11: "an unopened fd is refused",
                  12: "and the child got no pipe", 13: "open a file", 14: "a file fd is refused",
                  15: "and nothing was given", 16: "stdin and stderr from the read end",
                  17: "the parent writes", 18: "the child reads its stdin; empty is Again",
                  19: "closing a redirected stdio fd", 20: "the parent closes its writer",
                  21: "then the child reads EOF", 22: "exit releases everything"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_spawn_hands_the_child_its_stdio(compiler, tmp_path):
    rc = fdt._run(compiler, tmp_path, INHERIT, FS_MODULES)
    assert rc == 0, f"{compiler}: {INHERIT_CLAIMS.get(rc, f'exit {rc}')}"


# --- the syscall layer (source pins) ------------------------------------------------

RUNTIME = KERNEL_SRC / "syscall" / "runtime"
FILE = RUNTIME / "file.ritz"
POLL = RUNTIME / "poll.ritz"
PIPE_RT = RUNTIME / "pipe.ritz"
PROCESS = RUNTIME / "process.ritz"
ENTRY = RUNTIME / "entry.ritz"
NUMBERS = KERNEL_SRC / "syscall" / "numbers.ritz"


def test_pipe_is_syscall_29_and_spawn_io_is_registered():
    nums = NUMBERS.read_text()
    assert re.search(r"^\s*Pipe = 29\b", nums, re.M)
    m = re.search(r"^\s*SpawnIo = (\d+)\b", nums, re.M)
    assert m, "no SpawnIo in enum Syscall"
    entry = ENTRY.read_text()
    assert re.search(r"Syscall\.Pipe\b.*sys_pipe_handler", entry)
    assert re.search(r"Syscall\.SpawnIo\b.*sys_spawn_io_handler", entry)
    # ritzlib's copy of the numbers (test_harland_syscall_dispatch diffs all of them)
    sys = (RITZLIB / "sys.ritz").read_text()
    assert re.search(r"const SYS_PIPE: i64 = 29\b", sys)
    assert re.search(rf"const SYS_SPAWN_IO: i64 = {m.group(1)}\b", sys)


def test_pipe_syscalls_run_on_the_bsp():
    # The pipe pool and the BLOCK_PIPE park assume one CPU touches them: none
    # of the syscalls that reach a pipe may be marked SYS_LOCAL (an AP then
    # forwards them to the BSP, docs/SMP_USER.md §2).
    local = set(re.findall(r"syscall_mark_local\(Syscall\.(\w+)\)", ENTRY.read_text()))
    reach = {"Pipe", "SpawnIo", "SpawnBg", "Read", "Write", "Close", "Poll", "Fstat", "Exit"}
    assert not (local & reach), local & reach


def test_read_write_close_route_pipe_fds_before_the_console():
    for name, call in (("sys_read_handler", "pipe_read_wait("), ("sys_write_handler", "pipe_write_wait(")):
        body = _fn(FILE, name)
        assert call in body, f"{name} never reaches the pipe"
        # before the console path, so a redirected 0-2 reaches the pipe
        console = "tty_console_read(" if name == "sys_read_handler" else "klog_serial_write("
        assert body.index(call) < body.index(console), name
    assert "is_pipe_fd(" in _fn(FILE, "sys_close_handler")
    # a redirected stdio fd is no terminal
    assert "is_pipe_fd(" in _fn(FILE, "tty_fd_ok")


def test_blocking_pipe_io_parks_and_every_change_wakes():
    text = PIPE_RT.read_text()
    for name in ("pipe_read_wait", "pipe_write_wait"):
        body = _fn(PIPE_RT, name)
        assert "proc_block(BLOCK_PIPE" in body and "sched_block()" in body, name
        assert "disable_interrupts()" in body, f"{name}: check and park must be atomic"
        assert "pipe_may_wait()" in body, f"{name}: a process told to exit must stop waiting"
        assert "pipe_changed()" in body, name
    assert "proc_reap_pending(" in _fn(PIPE_RT, "pipe_may_wait")
    changed = _fn(PIPE_RT, "pipe_changed")
    assert "proc_wake(BLOCK_PIPE)" in changed and "waitset_pipes_changed()" in changed
    assert "BLOCK_PIPE" in (KERNEL_SRC / "proc" / "table.ritz").read_text()
    # close and exit release ends: both wake
    assert "pipe_changed()" in _fn(FILE, "sys_close_handler")
    assert "pipe_changed()" in _fn(PROCESS, "sys_exit_impl")
    assert "sys_pipe_handler" in text


def test_pipe_changed_keeps_the_callers_interrupt_state():
    # A Ctrl-C (tty/console.ritz) or a ring-3 fault kills the running process
    # from its IRQ or exception handler: sys_exit_impl runs on that stack
    # (CPU 0's IST2 for the USB keyboard's MSI-X vector) with IF clear, and
    # must keep it clear. An `sti` in pipe_changed, which exit calls, let the
    # next IST2 interrupt start again at that stack's top, over the exit
    # path's frames: a ret to garbage (CS 8, RSP in IST2) once in a few USB
    # keyboard boots, at the `spin` Ctrl-C.
    changed = _fn(PIPE_RT, "pipe_changed")
    assert "interrupts_enabled()" in changed, "pipe_changed must save IF before its cli"
    # the only sti is the conditional one restoring what the caller had
    lines = [ln.strip() for ln in changed.splitlines()]
    sti = [i for i, ln in enumerate(lines) if ln == "enable_interrupts()"]
    assert sti, "pipe_changed never restores IF"
    for i in sti:
        assert lines[i - 1].startswith("if "), f"unconditional enable_interrupts() in pipe_changed: {lines[i - 1]!r}"


def test_poll_reports_and_waits_for_pipe_fds():
    revents = _fn(POLL, "poll_revents")
    assert "pipe_revents(" in revents
    ends = _fn(POLL, "pipe_revents")
    assert "pipe_readable(" in ends and "pipe_writable(" in ends
    # a pipe check first: fd 0 may be a pipe
    assert revents.index("fs_pipe_end(") < revents.index("fd == 0")
    handler = _fn(POLL, "sys_poll_handler")
    assert "waitset_watch_pipes(" in handler


def test_every_user_spawn_hands_over_stdio():
    begin = _fn(PROCESS, "spawn_child_begin")
    assert begin.index("fs_process_start(") < begin.index("fs_process_give_stdio(")
    # a process's spawns carry a map; a kernel spawn (netd, its respawn in
    # the dying netd's exit) carries none and the child keeps the console
    assert "spawn_stdio_inherit())" not in begin
    assert "Some(spawn_stdio_inherit())" in _fn(PROCESS, "spawn_and_block")
    assert "Some(spawn_stdio_inherit())" in _fn(PROCESS, "sys_spawn_bg_handler")
    assert "Some(stdio)" in _fn(PROCESS, "sys_spawn_io_handler")
    assert "PROC_BSP_CPU, None)" in _fn(PROCESS, "process_spawn_program")
    io = _fn(PROCESS, "sys_spawn_io_handler")
    # the map is copied out of user memory before any page-table switch
    assert "uptr_check_read(" in io and "SpawnStdio" in io


def test_init_runs_the_pipe_test():
    init = (INDIUM / "user" / "init.ritz").read_text()
    assert re.search(r'run_test\("/bin/pipe_test",\s*"pipe_test",\s*0\)', init)
    toml = (INDIUM / "ritz.toml").read_text()
    assert 'name = "pipe_test"' in toml
