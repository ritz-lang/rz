#!/usr/bin/env python3
"""Drive a scripted rzsh session over a guest's serial console (AGAST #4252, #4254).

    shell_session.py LOG TIMEOUT -- QEMU_ARGV...

Listens on a unix socket, starts QEMU with its first serial port connected to
it (`-chardev socket,id=con,path=SOCK -serial chardev:con`, appended to
QEMU_ARGV), and then plays the session below: wait for the `rzsh> ` prompt,
type a command a byte at a time (COM1's receive interrupt drains a 16-byte
FIFO into the console's ring buffer; pacing keeps that FIFO from overrunning),
wait for the next prompt and check what the command printed.

After SESSION, tty_session() checks that the console is a terminal (#4254):
rubout in rzsh's editor and in the kernel's cooked mode, Ctrl-C on a program
blocked in read(0) and on one computing in a loop (`spin`), `$?` = 130 after
each, and Ctrl-C at the prompt leaving rzsh alive.

Every byte the guest sends is written to LOG. Each check prints one
`PASS: ...` or `FAIL: ...` line. Exit status: 0 = every check passed;
1 = a check failed or the guest stopped answering (no prompt within
TIMEOUT seconds of the last command); 3 = QEMU could not be started.

`exit` returns to init_interactive (#1882's per-process table: a child's
exit wakes its parent's sys_wait). rzsh prints "Goodbye!", init_interactive
prints "[init] Shell exited" and returns, and the kernel reports init's exit
("[exit] init exited with code 0, powering off": an ACPI power-off, #2755).
The last check asserts those three in that order, then that QEMU exits by
itself with status 0. Before #1882 the kernel took rzsh's exit as init's and
"[init] Shell exited" never appeared; that now fails.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import tempfile
import time

PROMPT = b"rzsh> "
# Seconds between typed bytes, so COM1's 16-byte FIFO never overruns.
TYPE_DELAY = float(os.environ.get("SHELL_TYPE_DELAY", "0.02"))
FATAL = re.compile(rb"KERNEL PANIC|!!! EXCEPTION !!!|EXCEPTION:")


def _lines(out: bytes) -> list[str]:
    """The lines a command printed, without the echoed command line."""
    text = out.decode(errors="replace").replace("\r", "")
    return [ln.strip() for ln in text.split("\n")[1:]]


# (command, description, check(lines) -> bool). Each command's output is
# what the guest sent between the typed line and the next prompt.
SESSION = [
    ("echo hi", "builtin echo prints its argument",
     lambda ls: "hi" in ls),
    ("pwd", "pwd prints the root directory",
     lambda ls: "/" in ls),
    ("ls /bin", "ls /bin lists rzsh, cat and init",
     lambda ls: all(n in ls for n in ("rzsh", "cat", "init"))),
    ("cat /etc/motd", "/bin/cat (a spawned program) prints /etc/motd",
     lambda ls: "Welcome to Harland!" in ls
     and not any(line.startswith(("[spawn]", "[spawn_args]")) for line in ls)),
    ("ping --help", "prints usage",
     lambda ls: [line for line in ls if line] == ["Usage: ping <host>"]),
    ("ping 1.1.1.1", "reports unavailable ICMP",
     lambda ls: [line for line in ls if line]
     == ["ping: ICMP is unavailable from Harland userspace"]),
    ("mkdir /shell-fs-test", "creates a directory",
     lambda ls: not any(line.startswith("mkdir:") for line in ls)),
    ("cd /shell-fs-test", "enters the created directory",
     lambda ls: not any(line.startswith("cd:") for line in ls)),
    ("mkdir child", "creates a directory relative to the inherited cwd",
     lambda ls: not any(line.startswith("mkdir:") for line in ls)),
    ("ls /shell-fs-test", "lists the new child directory",
     lambda ls: "child" in ls),
    ("cd /", "returns to the root directory",
     lambda ls: not any(line.startswith("cd:") for line in ls)),
    ("echo after-cat", "the shell runs a second command after cat exits",
     lambda ls: "after-cat" in ls),
]


class Console:
    def __init__(self, conn: socket.socket, log):
        self.conn = conn
        self.log = log
        self.buf = b""
        self.conn.settimeout(0.5)

    def _recv(self) -> bool:
        """Read what is waiting. False once the guest has hung up."""
        try:
            data = self.conn.recv(65536)
        except TimeoutError:
            return True
        if not data:
            return False
        self.log.write(data)
        self.log.flush()
        self.buf += data
        return True

    def expect(self, marker: bytes, timeout: float) -> bytes | None:
        """Everything up to and including marker, or None on a timeout, a
        hang-up or a kernel panic/exception."""
        deadline = time.monotonic() + timeout
        while True:
            i = self.buf.find(marker)
            if i >= 0:
                out, self.buf = self.buf[: i + len(marker)], self.buf[i + len(marker):]
                return out
            if FATAL.search(self.buf) or time.monotonic() > deadline:
                return None
            if not self._recv():
                return None

    def drain(self, timeout: float) -> bytes:
        """Everything the guest sends until it hangs up or timeout passes."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and self._recv():
            pass
        out, self.buf = self.buf, b""
        return out

    def type_line(self, line: str) -> None:
        self.type_bytes((line + "\r").encode())

    def type_bytes(self, data: bytes) -> None:
        """Type data. A guest that hung up (rzsh killed, init powered off)
        takes nothing; the next expect() reports it."""
        for b in data:
            try:
                self.conn.sendall(bytes([b]))
            except (BrokenPipeError, ConnectionResetError):
                return
            time.sleep(TYPE_DELAY)


# What `exit` prints, in order: rzsh, then init_interactive back from its
# sys_wait (#1882), then the kernel as init itself exits.
EXIT_MARKERS = (b"Goodbye!", b"[init] Shell exited",
                b"[exit] init exited with code 0, powering off")


def _in_order(data: bytes, markers) -> bool:
    """True when every marker appears in data, each after the one before."""
    pos = 0
    for m in markers:
        i = data.find(m, pos)
        if i < 0:
            return False
        pos = i + len(m)
    return True


def _ok(cond: bool, what: str, got: bytes | None = None) -> int:
    if cond:
        print(f"PASS: {what}")
        return 0
    tail = (got or b"")[-200:].decode(errors="replace")
    print(f"FAIL: {what}; got {tail!r}")
    return 1


def tty_session(con: "Console", timeout: float) -> int:
    """The console is a terminal (AGAST #4254): rubout, Ctrl-C, $? = 130.

    Each step ends at a prompt, so a failed step does not derail the next.
    Returns the number of failed checks."""
    fails = 0
    # rzsh's own line editor (raw mode): DEL rubs out the X.
    con.type_bytes(b"echo abX\x7fc\r")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and "abc" in _lines(out[: -len(PROMPT)]),
                 "rzsh's line editor: `echo abX<DEL>c` prints abc", out)

    # A cooked read: cat with no file reads stdin. The kernel's line
    # discipline echoes, rubs the X out (BS SP BS) and hands cat "hello".
    con.type_line("cat")
    time.sleep(1.0)                       # cat is now blocked in read(0)
    con.type_bytes(b"hellX\x7fo\r")
    out = con.expect(b"\x08 \x08o\r\nhello\n", timeout)
    fails += _ok(out is not None,
                 "cooked read(0): the kernel echoes, rubs out DEL and cat reads `hello`", out)
    # Ctrl-C while cat sleeps in read(0): ^C, cat killed, the prompt again.
    con.type_bytes(b"\x03")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and b"^C" in out,
                 "Ctrl-C kills cat blocked in read(0) and rzsh prompts", out)
    con.type_line("echo $?")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and "130" in _lines(out[: -len(PROMPT)]),
                 "a command killed by Ctrl-C exits 130", out)

    # Ctrl-C during a long-running program: spin computes in ring 3 and
    # never enters the kernel, so COM1's interrupt must kill it.
    con.type_line("spin")
    out = con.expect(b"spin: running", timeout)
    fails += _ok(out is not None, "spin (a program that never ends) starts", out)
    time.sleep(1.0)
    con.type_bytes(b"\x03")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and b"^C" in out,
                 "Ctrl-C during a long-running program returns to rzsh", out)
    con.type_line("echo $?")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and "130" in _lines(out[: -len(PROMPT)]),
                 "spin killed by Ctrl-C exits 130", out)

    # Ctrl-C at rzsh's prompt goes to its editor (raw mode: no ISIG), not
    # to the kernel: the shell survives it and runs the next command.
    con.type_bytes(b"junk\x03")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None, "Ctrl-C at the prompt: rzsh drops the line", out)
    con.type_line("echo still-here")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and "still-here" in _lines(out[: -len(PROMPT)]),
                 "rzsh survives Ctrl-C at its prompt", out)

    # Ctrl-C between rzsh's tty_setattr (ISIG back on) and its spawn (#4276).
    # RZSH_DEBUG_TTY_WINDOW holds rzsh there, in a cooked read(0), so the
    # Ctrl-C lands in rzsh's own syscall every time. rzsh has handed the
    # console to its children, so the kernel drops it: rzsh is not killed,
    # and the Enter that ends the read lets it spawn cat. Before #4276 rzsh
    # died here and init_interactive printed "[init] Shell exited". Last, as
    # a failure ends the session.
    con.type_line("RZSH_DEBUG_TTY_WINDOW=1")
    con.expect(PROMPT, timeout)
    con.type_line("cat /etc/motd")
    out = con.expect(b"rzsh: tty window", timeout)
    fails += _ok(out is not None, "rzsh stops between tty_setattr and spawn (debug hook)", out)
    time.sleep(1.0)                       # rzsh is now blocked in read(0)
    con.type_bytes(b"\x03")
    time.sleep(1.0)
    con.type_bytes(b"\r")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and b"Welcome to Harland!" in out,
                 "Ctrl-C between tty_setattr and spawn does not kill rzsh; cat runs", out)
    con.type_line("unset RZSH_DEBUG_TTY_WINDOW")
    con.expect(PROMPT, timeout)
    return fails


def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[2] != "--":
        print("usage: shell_session.py LOG TIMEOUT -- QEMU_ARGV...", file=sys.stderr)
        return 2
    log_path, timeout, qemu = argv[0], float(argv[1]), argv[3:]

    # Under /tmp, not $TMPDIR: a gate's TMPDIR is deep enough to overrun
    # sun_path's 107 bytes (AGAST #4177).
    # SOCK_DIR overrides it where /tmp is private or full (a room's unit).
    sock_dir = tempfile.mkdtemp(prefix="rz_shell_", dir=os.environ.get("SOCK_DIR", "/tmp"))
    sock_path = os.path.join(sock_dir, "con.sock")
    srv = socket.socket(socket.AF_UNIX)
    srv.bind(sock_path)
    srv.listen(1)
    srv.settimeout(30)
    qemu += ["-chardev", f"socket,id=con,path={sock_path}", "-serial", "chardev:con"]
    try:
        proc = subprocess.Popen(qemu, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except OSError as e:
        print(f"SETUP ERROR: could not start QEMU: {e}", file=sys.stderr)
        return 3
    rc = 0
    try:
        try:
            conn, _ = srv.accept()
        except TimeoutError:
            err = proc.stderr.read().decode(errors="replace") if proc.poll() is not None else ""
            print(f"FAIL: QEMU never connected its serial port {err.strip()}")
            return 1
        with open(log_path, "wb") as log:
            con = Console(conn, log)
            if con.expect(PROMPT, timeout) is None:
                print(f"FAIL: no rzsh prompt on the serial console (waited up to "
                      f"{timeout:.0f}s; the guest stopped, panicked or hung up)")
                return 1
            print("PASS: rzsh prompt on the serial console")
            for cmd, what, check in SESSION:
                con.type_line(cmd)
                out = con.expect(PROMPT, timeout)
                if out is None:
                    print(f"FAIL: `{cmd}`: no prompt afterwards within {timeout:.0f}s")
                    return 1
                lines = _lines(out[: -len(PROMPT)])
                if check(lines):
                    print(f"PASS: `{cmd}`: {what}")
                else:
                    print(f"FAIL: `{cmd}`: {what}; got {lines!r}")
                    rc = 1
            if tty_session(con, timeout):
                rc = 1
            con.type_line("exit")
            tail = con.drain(timeout)
            ok_exit = _in_order(tail, EXIT_MARKERS)
            try:
                qrc = proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                qrc = None
            if ok_exit and qrc == 0:
                print("PASS: `exit`: rzsh returns to init_interactive "
                      "(\"[init] Shell exited\"), then init exits and the VM powers off")
            else:
                print(f"FAIL: `exit`: want Goodbye!, [init] Shell exited, init's exit, in that "
                      f"order, and a power-off "
                      f"(QEMU status 0); got QEMU status {qrc}, "
                      f"tail {tail[-200:].decode(errors='replace')!r}")
                rc = 1
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        srv.close()
        try:
            os.unlink(sock_path)
            os.rmdir(sock_dir)
        except OSError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
