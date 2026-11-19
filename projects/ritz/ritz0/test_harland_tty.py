"""Harland's serial console is a terminal: blocking read(0), a line
discipline, tcgetattr/tcsetattr and Ctrl-C (AGAST #4254).

read(0) used to poll COM1 and return 0 when nothing had arrived, so the shell
spun on it with sys_yield; the tty attribute calls were stubs; Ctrl-C was just a
byte. Now:

  * tty/ldisc.ritz is the line discipline: TTY_ECHO / TTY_ICANON / TTY_ISIG,
    canonical line editing (rubout, CR -> NL, Ctrl-D) and Ctrl-C. It is pure
    Ritz, so the behaviour test compiles it into a host program and types at
    it; the exit code names the failed claim.
  * tty/console.ritz feeds it COM1's bytes from the IRQ 4 handler, and
    read(0) sleeps (sti; hlt) until the line discipline has something.
  * Ctrl-C kills the foreground process (the running Proc, never init) with
    status 130: from the IRQ when it interrupted ring 3, else at the end of
    the syscall it interrupted, or in the read it wakes.
  * sys_tty_getattr / sys_tty_setattr are syscalls 18 and 19; the shell
    turns echo, canonical mode and ISIG off while it edits a line and restores
    them while a command runs, so Ctrl-C reaches the command and not the shell
    (projects/ritz/tools has the shell-side check).

The runtime check is the scripted serial session boot test (backspace in a
cooked `cat`, Ctrl-C during a long-running program).
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
KERNEL_SRC = PROJECTS / "harland" / "kernel" / "src"
LDISC = KERNEL_SRC / "tty" / "ldisc.ritz"
CONSOLE = KERNEL_SRC / "tty" / "console.ritz"
FILE_RT = KERNEL_SRC / "syscall" / "runtime" / "file.ritz"
EXCEPTIONS = KERNEL_SRC / "arch" / "x86_64" / "exceptions.ritz"
ENTRY = KERNEL_SRC / "syscall" / "runtime" / "entry.ritz"
NUMBERS = KERNEL_SRC / "syscall" / "numbers.ritz"
SYS = RITZ_ROOT / "ritzlib" / "sys.ritz"

# The kernel is built by ritz0 only, so one compiler row (TESTING.md, "What a
# ritz0 pytest case costs").

PROGRAM = """\
import tty.ldisc

var rbuf: [512]u8
var ebuf: [512]u8

fn type_str(s: *u8) -> i32
    var p: *u8 = s
    var raised: i32 = 0
    while *p != 0
        raised = raised + ldisc_input(*p)
        p = p + 1
    raised

# The bytes a read of up to max returns equal s (exactly).
fn read_is(max: i64, s: *u8) -> bool
    let n: i64 = ldisc_read(@rbuf[0], max)
    var i: i64 = 0
    while *(s + i) != 0
        if i >= n or rbuf[i] != *(s + i)
            return false
        i = i + 1
    i == n

fn echo_is(s: *u8) -> bool
    let n: i64 = ldisc_take_echo(@ebuf[0], 512)
    var i: i64 = 0
    while *(s + i) != 0
        if i >= n or ebuf[i] != *(s + i)
            return false
        i = i + 1
    i == n

fn main() -> i32
    ldisc_reset()
    if ldisc_get_flags() != (TTY_ECHO | TTY_ICANON | TTY_ISIG)
        return 1
    # Canonical: nothing readable until the line ends; CR ends it as NL.
    type_str(c"ab")
    if ldisc_readable()
        return 2
    type_str(c"\\r")
    if not ldisc_readable() or not read_is(100, c"ab\\n")
        return 3
    if ldisc_readable()
        return 4
    # Echo: the bytes, then CR NL for the line end.
    if not echo_is(c"ab\\r\\n")
        return 5
    # Rubout: DEL and BS each erase one byte, echoed as BS SP BS.
    type_str(c"abX\\x7fc\\r")
    if not read_is(100, c"abc\\n")
        return 6
    if not echo_is(c"abX\\x08 \\x08c\\r\\n")
        return 7
    type_str(c"x\\x08\\x08\\x08y\\n")
    if not read_is(100, c"y\\n")
        return 8
    if not echo_is(c"x\\x08 \\x08y\\r\\n")
        return 9
    # Ctrl-C (ISIG): no input, the line is dropped, ^C echoed, interrupt up.
    if type_str(c"sleep\\x03") != 1
        return 10
    if ldisc_readable() or not ldisc_intr_pending()
        return 11
    if not echo_is(c"sleep^C\\r\\n")
        return 12
    if not ldisc_take_intr() or ldisc_take_intr()
        return 13
    type_str(c"ok\\r")
    if not read_is(100, c"ok\\n")
        return 14
    echo_is(c"")
    # A canonical read returns one line at a time.
    type_str(c"one\\rtwo\\r")
    if not read_is(100, c"one\\n") or not read_is(100, c"two\\n")
        return 15
    # ... and no more than asked for.
    type_str(c"abcdef\\r")
    if not read_is(4, c"abcd") or not read_is(100, c"ef\\n")
        return 16
    # Ctrl-D: on an empty line read returns 0 once; else it ends the line.
    type_str(c"\\x04")
    if not ldisc_readable() or ldisc_read(@rbuf[0], 100) != 0 or ldisc_readable()
        return 17
    type_str(c"hi\\x04")
    if not read_is(100, c"hi")
        return 18
    echo_is(c"")
    # A long line keeps 255 bytes and its NL.
    var i: i32 = 0
    while i < 300
        ldisc_input(120)
        i = i + 1
    ldisc_input(13)
    if ldisc_read(@rbuf[0], 512) != 256 or rbuf[254] != 120 or rbuf[255] != 10
        return 19
    ldisc_take_echo(@ebuf[0], 512)
    # No ECHO: nothing echoed, editing still works.
    ldisc_set_flags(TTY_ICANON | TTY_ISIG)
    type_str(c"ab\\x7fc\\r")
    if not read_is(100, c"ac\\n") or not echo_is(c"")
        return 20
    # Raw (the shell's line editor): every byte readable at once, Ctrl-C, DEL and
    # CR are data, nothing echoed, no interrupt.
    ldisc_set_flags(0)
    if ldisc_get_flags() != 0
        return 21
    if type_str(c"a\\x03\\x7f\\r") != 0 or ldisc_intr_pending()
        return 22
    if not read_is(2, c"a\\x03") or not read_is(100, c"\\x7f\\r") or not echo_is(c"")
        return 23
    # Raw with ECHO echoes the byte as it is.
    ldisc_set_flags(TTY_ECHO)
    type_str(c"q")
    if not echo_is(c"q") or not read_is(100, c"q")
        return 24
    # Leaving canonical mode makes a half-edited line readable.
    ldisc_set_flags(TTY_FLAGS_DEFAULT)
    type_str(c"half")
    ldisc_set_flags(0)
    if not read_is(100, c"half")
        return 25
    # Turning ISIG off drops an undelivered interrupt; unknown bits dropped.
    ldisc_set_flags(TTY_FLAGS_DEFAULT)
    type_str(c"\\x03")
    ldisc_set_flags(TTY_ECHO | TTY_ICANON)
    if ldisc_intr_pending()
        return 26
    ldisc_set_flags(0xFFFF)
    if ldisc_get_flags() != TTY_FLAGS_ALL
        return 27
    # A small echo take leaves the rest queued.
    echo_is(c"")
    type_str(c"wxyz")
    if ldisc_take_echo(@ebuf[0], 2) != 2 or ebuf[1] != 120 or not echo_is(c"yz")
        return 28
    0
"""

CLAIMS = {1: "cooked by default", 2: "canonical: no partial line readable",
          3: "CR completes a line, read as NL", 4: "a line is read once",
          5: "echo: bytes, CR NL at the end", 6: "DEL rubs out", 7: "rubout echoes BS SP BS",
          8: "BS rubs out, not past the line start", 9: "rubout on an empty line echoes nothing",
          10: "Ctrl-C raises an interrupt", 11: "Ctrl-C drops the line and is pending",
          12: "Ctrl-C echoes ^C", 13: "take_intr clears it", 14: "input works after Ctrl-C",
          15: "a canonical read returns one line", 16: "a short read keeps the rest",
          17: "Ctrl-D on an empty line: one read of 0", 18: "Ctrl-D ends a partial line",
          19: "a long line keeps 255 bytes and its NL", 20: "no ECHO: edit without echo",
          21: "flags 0 is raw", 22: "raw: Ctrl-C is data, no interrupt",
          23: "raw: bytes readable at once, no echo", 24: "raw + ECHO echoes",
          25: "leaving canonical flushes the line", 26: "ISIG off drops the interrupt",
          27: "unknown flag bits dropped", 28: "a short echo take keeps the rest"}


@pytest.mark.integration
def test_line_discipline(tmp_path):
    tree = tmp_path / "tree" / "tty"
    tree.mkdir(parents=True)
    (tree / "ldisc.ritz").write_text(LDISC.read_text())
    (tmp_path / "t.ritz").write_text(PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "ldisc.ritz", "ldisc", ("--no-runtime",))]:
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


# --- source level: the kernel goes through it ------------------------------

def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", code + "\nEND", re.S | re.M)
    assert m, f"fn {name} not found"
    return m.group(0)


def test_ldisc_is_pure():
    assert "import" not in _code(LDISC), "the host test compiles ldisc.ritz alone"


def test_read_zero_sleeps_on_the_console():
    read = _body(_code(FILE_RT), "sys_read_handler")
    assert "tty_console_read" in read
    assert "serial_poll" not in read and "serial_buf_read_many" not in read
    loop = _body(_code(CONSOLE), "tty_console_read")
    assert "sti_hlt()" in loop, "read(0) sleeps until an interrupt, no busy loop"
    assert "yield" not in loop and "cpu_pause" not in loop


def test_irq4_feeds_the_line_discipline_and_delivers_ctrl_c():
    irq = _body(_code(EXCEPTIONS), "irq_handler")
    assert "tty_console_irq(" in irq
    assert "serial_poll" not in irq
    pull = _body(_code(CONSOLE), "tty_console_pull")
    assert "ldisc_input(" in pull
    kill = _body(_code(CONSOLE), "tty_console_kill_foreground")
    assert "process_kill_current(TTY_INTR_STATUS)" in kill
    assert re.search(r"TTY_INTR_STATUS: i32 = 130\b", _code(CONSOLE))
    due = _body(_code(CONSOLE), "tty_console_intr_due")
    assert "tty_fg_is_current()" in due, "only the foreground; init never (tty/fg.ritz)"


def test_syscall_exit_delivers_a_pending_ctrl_c():
    handler = _body(_code(ENTRY), "syscall_handler")
    assert "tty_console_check_intr()" in handler


def test_tty_syscalls_numbered_and_registered():
    nums = _code(NUMBERS)
    assert re.search(r"TtyGetattr = 18\b", nums) and re.search(r"TtySetattr = 19\b", nums)
    entry = _code(ENTRY)
    assert "syscall_register(Syscall.TtyGetattr, sys_tty_getattr_handler)" in entry
    assert "syscall_register(Syscall.TtySetattr, sys_tty_setattr_handler)" in entry
    sys = _code(SYS)
    assert re.search(r"SYS_TTY_GETATTR: i64 = 18\b", sys) and re.search(r"SYS_TTY_SETATTR: i64 = 19\b", sys)
    get = _body(sys, "sys_tty_getattr")
    assert "SYS_TTY_GETATTR" in get, "no stub: a real syscall"
    assert "SYS_TTY_SETATTR" in _body(sys, "sys_tty_setattr")


# --- the console's foreground (#4276) ---------------------------------------
#
# rzsh turns ISIG back on (tty_setattr) a few syscalls before it spawns the
# command. A Ctrl-C typed in between used to be delivered at the end of
# rzsh's own syscall, and the running process then was rzsh: it was killed.
# Now the console has a foreground (tty/fg.ritz) that the shell sets, as
# tcsetpgrp does: TTY_FG_CHILDREN hands the console to the caller's
# descendants (spawn is blocking, so the shell can't name the child's pid
# ahead), TTY_FG_PID to a pid and its descendants, TTY_FG_NONE back to
# #4254's "the running process". A Ctrl-C for a process outside the
# foreground is dropped, as for init.

FG = KERNEL_SRC / "tty" / "fg.ritz"
PROC_TABLE = KERNEL_SRC / "proc" / "table.ritz"
ERRNO = KERNEL_SRC / "syscall" / "errno.ritz"

FG_PROGRAM = """\
import syscall.errno { Errno }
import proc.table
import tty.fg

fn main() -> i32
    proc_table_reset()
    tty_fg_reset()
    if tty_fg_is_current()
        return 1
    proc_enter_init(4096)
    if tty_fg_is_current()
        return 2
    # rzsh, pid 2. Nothing set: the running process (#4254).
    proc_spawn_child()
    if not tty_fg_is_current()
        return 3
    # rzsh hands the console to its children: from here on a Ctrl-C while
    # rzsh runs (tty_setattr .. spawn) is not rzsh's.
    if tty_fg_set(TTY_FG_CHILDREN, 0) != 0 or tty_fg_is_current()
        return 4
    # the command, pid 3, and what it spawns, pid 4
    proc_spawn_child()
    if not tty_fg_is_current()
        return 5
    proc_spawn_child()
    if not tty_fg_is_current()
        return 6
    proc_exit_current(0)
    proc_exit_current(130)
    if proc_current_pid() != 2 or tty_fg_is_current()
        return 7
    # A pid: that process and its descendants, not its parent.
    proc_spawn_child()
    if proc_current_pid() != 5 or tty_fg_set(TTY_FG_PID, 5) != 0 or not tty_fg_is_current()
        return 8
    proc_spawn_child()
    if not tty_fg_is_current()
        return 9
    proc_exit_current(0)
    proc_exit_current(0)
    if tty_fg_is_current()
        return 10
    # A pid that is not running matches nothing.
    if tty_fg_set(TTY_FG_PID, 99) != 0 or tty_fg_is_current()
        return 11
    # TTY_FG_NONE: the running process again; anything else is EINVAL.
    if tty_fg_set(TTY_FG_NONE, 0) != 0 or not tty_fg_is_current()
        return 12
    if tty_fg_set(3, 0) != Errno.Inval as i32 or tty_fg_set(TTY_FG_PID, 0) != Errno.Inval as i32
        return 13
    if not tty_fg_is_current()
        return 13
    # init is never the foreground, not even by its pid.
    proc_exit_current(0)
    if proc_current_pid() != 1 or tty_fg_set(TTY_FG_PID, 1) != 0 or tty_fg_is_current()
        return 14
    if tty_fg_set(TTY_FG_CHILDREN, 0) != 0 or tty_fg_is_current()
        return 15
    0
"""

FG_CLAIMS = {1: "nothing running: no foreground", 2: "init alone: no foreground",
             3: "unset: the running process is the foreground",
             4: "TTY_FG_CHILDREN: the shell itself is not the foreground (the window)",
             5: "TTY_FG_CHILDREN: the shell's child is", 6: "... and its child",
             7: "back in the shell: still not the foreground",
             8: "a pid: that process is", 9: "a pid: its child is",
             10: "a pid: its parent is not", 11: "a dead pid matches nothing",
             12: "TTY_FG_NONE: the running process again", 13: "a bad mode or pid 0 is EINVAL, and changes nothing",
             14: "init is never the foreground by pid", 15: "init is never the foreground"}


@pytest.mark.integration
def test_foreground_group(tmp_path):
    tree = tmp_path / "tree"
    for src, rel in [(ERRNO, "syscall/errno.ritz"), (PROC_TABLE, "proc/table.ritz"), (FG, "tty/fg.ritz")]:
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(src.read_text())
    (tmp_path / "t.ritz").write_text(FG_PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tree}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "syscall/errno.ritz", "errno", ("--no-runtime",)),
                             (tree / "proc/table.ritz", "table", ("--no-runtime",)),
                             (tree / "tty/fg.ritz", "fg", ("--no-runtime",))]:
        ll = tmp_path / f"{name}.ll"
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
        assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
        objs.append(str(ll))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == 0, f"exit {rc}: {FG_CLAIMS.get(rc, 'crash')}"


def test_ctrl_c_goes_only_to_the_foreground():
    due = _body(_code(CONSOLE), "tty_console_intr_due")
    assert "tty_fg_is_current()" in due, "the console asks tty/fg.ritz whose Ctrl-C it is"
    assert "ldisc_take_intr()" in due, "a Ctrl-C outside the foreground is dropped"
    assert "proc." not in _code(FG).replace("import proc.table", ""), \
        "fg.ritz keeps pids, not Proc pointers (#3629 rewrites the table)"


def test_tty_setfg_syscall():
    assert re.search(r"TtySetfg = 16\b", _code(NUMBERS))
    assert "syscall_register(Syscall.TtySetfg, sys_tty_setfg_handler)" in _code(ENTRY)
    handler = _body(_code(FILE_RT), "sys_tty_setfg_handler")
    assert "tty_fd_ok(" in handler and "tty_console_set_fg(" in handler
    sys = _code(SYS)
    assert re.search(r"SYS_TTY_SETFG: i64 = 16\b", sys)
    assert "SYS_TTY_SETFG" in _body(sys, "sys_tty_setfg")
    for code in (sys, _code(FG)):
        for name, n in (("NONE", 0), ("CHILDREN", 1), ("PID", 2)):
            assert re.search(rf"TTY_FG_{name}: u64 = {n}\b", code), name
