#!/usr/bin/env python3
"""Drive a scripted rzsh session over a guest's serial console (AGAST #4252).

    shell_session.py LOG TIMEOUT -- QEMU_ARGV...

Listens on a unix socket, starts QEMU with its first serial port connected to
it (`-chardev socket,id=con,path=SOCK -serial chardev:con`, appended to
QEMU_ARGV), and then plays the session below: wait for the `rzsh> ` prompt,
type a command a byte at a time (sys_read(0) polls COM1, whose FIFO is only
16 bytes deep), wait for the next prompt and check what the command printed.

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
# Seconds between typed bytes: COM1 is polled, not interrupt driven.
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
     lambda ls: "Welcome to Harland!" in ls),
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
        for b in (line + "\r").encode():
            self.conn.sendall(bytes([b]))
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

def main(argv: list[str]) -> int:
    if len(argv) < 4 or argv[2] != "--":
        print("usage: shell_session.py LOG TIMEOUT -- QEMU_ARGV...", file=sys.stderr)
        return 2
    log_path, timeout, qemu = argv[0], float(argv[1]), argv[3:]

    # Under /tmp, not $TMPDIR: a gate's TMPDIR is deep enough to overrun
    # sun_path's 107 bytes (AGAST #4177).
    sock_dir = tempfile.mkdtemp(prefix="rz_shell_", dir="/tmp")
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
