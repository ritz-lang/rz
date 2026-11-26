#!/usr/bin/env python3
"""Drive a scripted rzsh session over a guest's serial console (AGAST #4252, #4254).

    shell_session.py [--net PORT] LOG TIMEOUT -- QEMU_ARGV...

Listens on a unix socket, starts QEMU with its first serial port connected to
it (`-chardev socket,id=con,path=SOCK -serial chardev:con`, appended to
QEMU_ARGV), and then plays the session below: wait for the `rzsh> ` prompt,
type a command a byte at a time (COM1's receive interrupt drains a 16-byte
FIFO into the console's ring buffer; pacing keeps that FIFO from overrunning),
wait for the next prompt and check what the command printed.

After SESSION, tty_session() checks that the console is a terminal (#4254):
rubout in rzsh's editor and in the kernel's cooked mode, Ctrl-C on a program
blocked in read(0) and on one computing in a loop (`spin`), `$?` = 130 after
each, and Ctrl-C at the prompt leaving rzsh alive. paste_session() pastes
into a busy reader (#4831): 8 KiB arrives whole, and past the console's
16 KiB queue the reader is told how much was dropped.

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

--net PORT plays net_session() instead of SESSION and the tty checks: the
ring-3 networking acceptance of a translating boot (AGAST #4752, M2.10;
harland docs/RING2_NET.md "Ring-3 tools"), whose QEMU_ARGV forwards host
UDP 127.0.0.1:PORT to the guest's PORT (hostfwd=udp:127.0.0.1:PORT-:PORT)
and runs /bin/netd. Slirp's gateway 10.0.2.2 is the host:

  ping 10.0.2.2               prints one reply and exits 0;
  udp-send 10.0.2.2 L hello   exits 0 and a host listener on L gets `hello`;
  udp-recv PORT               prints a datagram the host sends through
                              the hostfwd, with its peer port, and exits 0;
  udp-recv PORT & udp-recv PORT
                              one bind of a live port: whichever process
                              binds second exits 17 with Errno.Exist, the
                              other gets the host's datagram, and `wait`
                              reaps the job;
  udp-recv PORT, 6 times      each from a new process (more than netd's 5
                              attachments and the free process slots), each
                              gets its datagram and none sees Errno.Exist.

Then `exit` as above.
"""

from __future__ import annotations

import os
import re
import select
import socket
import subprocess
import sys
import tempfile
import time

PROMPT = b"rzsh> "
# Seconds between typed bytes, so COM1's 16-byte FIFO never overruns.
TYPE_DELAY = float(os.environ.get("SHELL_TYPE_DELAY", "0.02"))
# Seconds _feed_until waits after udp-recv's prompt for the datagrams still
# in flight to be dropped (a guest's netd needs them; a stub guest doesn't).
NET_SETTLE = float(os.environ.get("SHELL_NET_SETTLE", "1.0"))
FATAL = re.compile(rb"KERNEL PANIC|!!! EXCEPTION !!!|EXCEPTION:")
# netd's lease line (system/src/netd.ritz log_address). It goes to the
# console like every kernel and service line, so the net session waits for
# it before typing: the tools need the lease, and the line must not land in
# a command's output.
NETD_CONFIGURED = b"[netd] configured "
# What the ring-3 net tools print (indium user/ping.ritz, udp_recv.ritz,
# net_tool.ritz fail()).
PING_REPLY = "reply from 10.0.2.2: 9 bytes: ritz ping"
EXIST_LINE = b"udp-recv: net_bind: Errno.Exist (port in use) (-17)"
# Udp-recv's report, from the host sender's port with `payload`.
def _from_line(port: int, payload: bytes) -> bytes:
    return b"from 10.0.2.2:%d: %d bytes: %s" % (port, len(payload), payload)


def _lines(out: bytes) -> list[str]:
    """The lines a command printed, without the echoed command line."""
    text = out.decode(errors="replace").replace("\r", "")
    return [ln.strip() for ln in text.split("\n")[1:]]


def _listing(lines: list[str]) -> list[str]:
    # Non-empty lines only. No kernel line is filtered: a command's output
    # must be its own (the kernel's mmap success log was dropped for this).
    return [line for line in lines if line]


def _no_error(prefix: str):
    """A check that the command printed no `<prefix>...` error line."""
    return lambda ls: not any(prefix in line for line in ls)


def _only(want: str):
    """A check that the command printed exactly the one line `want`."""
    return lambda ls: _listing(ls) == [want]


# Relative paths, `.` and `..` (AGAST #4776). The kernel takes absolute paths
# only; ritzlib.path resolves them in userspace, in rzsh (cd, ls, a command
# run by path) and in the programs it spawns (cat, mkdir). The first lines
# are Aaron's session from the ticket, which failed at `cat etc/hostname`.
# Runs from / and ends there.
PATH_SESSION = [
    ("ls etc", "lists a directory named relative to /",
     lambda ls: all(name in " ".join(_listing(ls)).split() for name in ("hostname", "motd"))),
    ("cat etc/hostname", "cat opens a path relative to /", _only("harland")),
    ("cd etc", "cd enters a directory relative to /", _no_error("cd:")),
    ("pwd", "the cwd is /etc", _only("/etc")),
    ("cat hostname", "cat opens a name relative to /etc", _only("harland")),
    ("cat ./motd", "`./` names the cwd", lambda ls: "Welcome to Harland!" in ls),
    ("cd ..", "`..` is the parent", _no_error("cd:")),
    ("pwd", "`cd ..` from /etc is /", _only("/")),
    ("cd ..", "`..` at the root stays at the root", _no_error("cd:")),
    ("pwd", "the cwd is still /", _only("/")),
    ("cd bin/", "a trailing / is the same directory", _no_error("cd:")),
    ("pwd", "the cwd is /bin, without the trailing /", _only("/bin")),
    ("cat ../etc/hostname", "cat opens a path through `..` from /bin", _only("harland")),
    ("./cat ./../etc//hostname", "rzsh runs ./cat, which opens a path with `.`, `..` and `//`",
     _only("harland")),
    ("ls ..", "lists the parent directory",
     lambda ls: all(name in " ".join(_listing(ls)).split() for name in ("bin", "etc"))),
    ("cd ../etc", "cd follows `..` then a name", _no_error("cd:")),
    ("pwd", "the cwd is /etc", _only("/etc")),
    ("cd nowhere", "cd to a missing relative directory fails",
     lambda ls: any("cannot change directory" in line for line in ls)),
    ("pwd", "a failed cd leaves the cwd alone", _only("/etc")),
    ("cd /", "returns to the root directory", _no_error("cd:")),
    ("mkdir x", "mkdir creates a directory relative to /", _no_error("mkdir:")),
    ("cd x", "cd enters it", _no_error("cd:")),
    ("pwd", "the cwd is /x", _only("/x")),
    ("cd ./../x/./", "`.` and `..` fold away in cd", _no_error("cd:")),
    ("pwd", "the cwd is still /x", _only("/x")),
    ("cd /", "returns to the root directory", _no_error("cd:")),
]

# (command, description, check(lines) -> bool). Each command's output is
# what the guest sent between the typed line and the next prompt.
SESSION = [
    ("echo hi", "builtin echo prints its argument",
     lambda ls: "hi" in ls),
    ("pwd", "pwd prints the root directory",
     lambda ls: "/" in ls),
    ("cd /bin", "changes the shell's working directory to /bin",
     lambda ls: not any(line.startswith("cd:") for line in ls)),
    ("ls", "lists /bin in columns after cd",
     lambda ls: all(name in " ".join(_listing(ls)).split() for name in ("cat", "init", "rzsh"))
     and any(len(line.split()) > 1 for line in _listing(ls))),
    ("ls -1", "lists /bin one name per line in sorted order",
     lambda ls: all(name in ls for name in ("cat", "init", "rzsh"))
     and _listing(ls) == sorted(_listing(ls))),
    ("cd /", "returns to the root directory",
     lambda ls: not any(line.startswith("cd:") for line in ls)),
    ("cat /etc/motd", "/bin/cat (a spawned program) prints /etc/motd",
     lambda ls: "Welcome to Harland!" in ls
     and not any(line.startswith(("[spawn]", "[spawn_args]")) for line in ls)),
    ("ping --help", "prints usage",
     lambda ls: [line for line in ls if line] == ["Usage: ping <address>"]),
    # No network service runs in this boot, so ping's first call (NetAttach)
    # answers NoDev (#4751).
    ("ping 1.1.1.1", "reports NetAttach NoDev with no network service",
     lambda ls: [line for line in ls if line]
     == ["ping: NetAttach: Errno.NoDev (no network service) (-19)"]),
    ("mkdir /shell-fs-test", "creates a directory",
     lambda ls: not any(line.startswith("mkdir:") for line in ls)),
    ("cd /shell-fs-test", "enters the created directory",
     lambda ls: not any(line.startswith("cd:") for line in ls)),
    ("mkdir child", "creates a directory relative to the inherited cwd",
     lambda ls: not any(line.startswith("mkdir:") for line in ls)),
    ("ls -1 /shell-fs-test", "lists the new child directory",
     lambda ls: "child" in ls),
    ("cd /", "returns to the root directory",
     lambda ls: not any(line.startswith("cd:") for line in ls)),
] + PATH_SESSION + [
    ("echo after-cat", "the shell runs a second command after cat exits",
     lambda ls: "after-cat" in ls),
]


class Console:
    def __init__(self, conn: socket.socket, log):
        self.conn = conn
        self.log = log
        self.buf = b""
        self.seen = b""                   # every byte received, for markers
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
        self.seen += data
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


class HostUdp:
    """The host's end of the guest's UDP: a listener udp-send sends to
    (10.0.2.2:listen_port in the guest), and a sender into the hostfwd'd
    guest port, from one fixed source port udp-recv must print."""

    def __init__(self, fwd_port: int):
        self.fwd_port = fwd_port
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listen_port = self.listener.getsockname()[1]
        self.sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sender.bind(("127.0.0.1", 0))
        self.send_port = self.sender.getsockname()[1]

    def send(self, payload: bytes) -> None:
        self.sender.sendto(payload, ("127.0.0.1", self.fwd_port))

    def received(self, timeout: float) -> list[bytes]:
        """Every datagram the listener got within timeout of the first."""
        got = []
        deadline = time.monotonic() + timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0 or not select.select([self.listener], [], [], left)[0]:
                return got
            got.append(self.listener.recv(4096))
            deadline = time.monotonic() + 0.5

    def close(self) -> None:
        self.listener.close()
        self.sender.close()


def _feed_until(con: "Console", host: HostUdp, payload: bytes, timeout: float) -> bytes | None:
    """Wait for the next prompt, sending `payload` into the hostfwd every
    half second meanwhile: a datagram before the guest's bind is dropped
    (no endpoint holds the port), so the first one that lands after it is
    the one udp-recv reports. None on a timeout, hang-up or panic."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        host.send(payload)
        out = con.expect(PROMPT, 0.5)
        if out is not None:
            # The copies still in flight land while no endpoint holds the
            # port (netd drops them), not on the next step's fresh bind.
            time.sleep(NET_SETTLE)
            return out
        if FATAL.search(con.buf):
            return None
    return None


def net_session(con: "Console", host: HostUdp, timeout: float) -> int:
    """The M2.10 checks (AGAST #4752); the number that failed. Each step
    ends at a prompt, so a failed step does not derail the next."""
    fails = 0
    if NETD_CONFIGURED not in con.seen and con.expect(NETD_CONFIGURED, timeout) is None:
        print(f"FAIL: netd logged no lease ({NETD_CONFIGURED.decode().strip()} A) "
              f"within {timeout:.0f}s of the prompt")
        return 1
    # The rest of netd's line, and any prompt redraw, before the first command.
    con.drain(1.0)

    con.type_line("ping 10.0.2.2 ; echo $?")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and _listing(_lines(out[: -len(PROMPT)])) == [PING_REPLY, "0"],
                 f"`ping 10.0.2.2`: one echo through netd prints `{PING_REPLY}` and exits 0", out)

    con.type_line(f"udp-send 10.0.2.2 {host.listen_port} hello ; echo $?")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and _listing(_lines(out[: -len(PROMPT)])) == ["0"],
                 f"`udp-send 10.0.2.2 {host.listen_port} hello` exits 0", out)
    got = host.received(10.0)
    fails += _ok(got == [b"hello"],
                 f"the host listener on {host.listen_port} got one datagram `hello` (got {got!r})")

    port = host.fwd_port
    want = _from_line(host.send_port, b"datagram-1")
    con.type_line(f"udp-recv {port} ; echo $?")
    out = _feed_until(con, host, b"datagram-1", timeout)
    fails += _ok(out is not None and _listing(_lines(out[: -len(PROMPT)])) == [want.decode(), "0"],
                 f"`udp-recv {port}` prints the host's datagram through hostfwd=udp "
                 f"(`{want.decode()}`) and exits 0", out)

    # Two live binds of one port. The job and the next command race to bind
    # it, so neither is assumed first: the second one exits 17 with
    # Errno.Exist and the other gets the datagram, whichever it is. Nothing
    # is sent until that Errno.Exist is on the console: a datagram before
    # it would let the first holder take it, close the port and leave the
    # second bind nothing to collide with.
    start = len(con.seen)
    con.type_line(f"udp-recv {port} &")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and re.search(rb"\[1\] [0-9]+", out) is not None,
                 f"`udp-recv {port} &` starts a background job", out)
    want = _from_line(host.send_port, b"datagram-2")
    con.type_line(f"udp-recv {port} ; echo fg=$?")
    if EXIST_LINE not in con.seen[start:] and con.expect(EXIST_LINE, timeout) is None:
        print(f"FAIL: neither bind of live port {port} answered Errno.Exist within {timeout:.0f}s")
        return fails + 1
    fg = _feed_until(con, host, b"datagram-2", timeout)
    con.type_line("wait ; echo job=$?")
    job = _feed_until(con, host, b"datagram-2", timeout)
    phase = con.seen[start:]
    statuses = sorted(re.findall(rb"(?:fg|job)=([0-9]+)", phase))
    fails += _ok(fg is not None and job is not None and phase.count(EXIST_LINE) == 1
                 and phase.count(want) == 1 and statuses == [b"0", b"17"],
                 f"a second bind of live port {port} exits 17 with Errno.Exist while the "
                 f"first holds it and gets the datagram", phase)

    # A new process each time: its attachment and process slot are the ones
    # the last run freed, and the port its net_close freed binds again.
    for i in range(3, 9):
        payload = b"datagram-%d" % i
        want = _from_line(host.send_port, payload)
        con.type_line(f"udp-recv {port} ; echo $?")
        out = _feed_until(con, host, payload, timeout)
        fails += _ok(out is not None and _listing(_lines(out[: -len(PROMPT)])) == [want.decode(), "0"],
                     f"`udp-recv {port}` run {i - 2} of 6 from a new process rebinds the port "
                     f"and prints `{want.decode()}` (no Errno.Exist)", out)
    return fails


# A paste into a busy reader (AGAST #4831). The console's input queue holds
# 16 KiB; bytes past it are dropped and counted, and the reader sees the
# count (TtyAttrs.overruns, termsession's KeyReader.take_overruns).
# /bin/paste_check reads nothing for 3 s after `ready`, then reports what it
# read. The paste is sent in one go: QEMU's COM1 takes bytes from the socket
# only as its FIFO has room, so none is lost before the kernel's queue.
PASTE_QUEUE = 16384
PASTE_RESULT = re.compile(rb"paste_check: (\d+) bytes sum (\d+) overrun (\d+)")


def _paste_bytes(n: int) -> bytes:
    """n printable bytes, a..z repeating: no control byte for the console."""
    return bytes(97 + i % 26 for i in range(n))


def _paste(con: "Console", n: int, timeout: float):
    """Paste n bytes into paste_check: (bytes read, their sum, overrun), or
    None if it never got ready or never reported."""
    con.type_line("paste_check")
    if con.expect(b"paste_check: ready", timeout) is None:
        return None
    try:
        con.conn.sendall(_paste_bytes(n))
    except (BrokenPipeError, ConnectionResetError):
        return None
    out = con.expect(PROMPT, timeout)
    m = PASTE_RESULT.search(out or b"")
    return tuple(int(g) for g in m.groups()) if m else None


def paste_session(con: "Console", timeout: float) -> int:
    """A paste that fits the queue arrives whole; a larger one is dropped
    past the queue, and the reader is told how much. Returns the failures."""
    fails = 0
    fit = 8192                              # 8x the 1 KiB queue before #4831
    got = _paste(con, fit, timeout)
    fails += _ok(got == (fit, sum(_paste_bytes(fit)), 0),
                 f"an {fit}-byte paste into a busy reader arrives whole, no overrun",
                 repr(got).encode())
    big = PASTE_QUEUE + 3616
    got = _paste(con, big, timeout)
    fails += _ok(got is not None and got[2] > 0 and got[0] + got[2] == big
                 and got[0] >= PASTE_QUEUE,
                 f"a {big}-byte paste: the queue keeps {PASTE_QUEUE} and the reader "
                 f"sees the rest as an overrun", repr(got).encode())
    return fails


def main(argv: list[str]) -> int:
    fwd_port = None
    if argv[:1] == ["--net"] and len(argv) > 1 and argv[1].isdigit():
        fwd_port, argv = int(argv[1]), argv[2:]
    if len(argv) < 4 or argv[2] != "--":
        print("usage: shell_session.py [--net PORT] LOG TIMEOUT -- QEMU_ARGV...", file=sys.stderr)
        return 2
    log_path, timeout, qemu = argv[0], float(argv[1]), argv[3:]
    host = HostUdp(fwd_port) if fwd_port is not None else None

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
            if host is not None:
                if net_session(con, host, timeout):
                    rc = 1
            else:
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
                if paste_session(con, timeout):
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
        if host is not None:
            host.close()
        try:
            os.unlink(sock_path)
            os.rmdir(sock_dir)
        except OSError:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
