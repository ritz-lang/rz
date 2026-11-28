#!/usr/bin/env python3
"""Drive Buddhafinger on Harland's serial console under QEMU (AGAST #4833, #4835).

    harland_console.py SESSION LOG TIMEOUT -- QEMU_ARGV...

One boot per call; tools/test_harland_console.sh boots the sessions below in
order, the storage disk (the second virtio-blk, /var's goliath image) kept
across them, so each later boot is a reboot of the one before. It listens on
a unix socket, starts QEMU with COM1 on it, waits for `rzsh> `, plays
SESSION and ends with `exit` (rzsh, init_interactive, then the ACPI power-off,
which also saves a deferred /var save). Each check prints one `PASS: ...` or
`FAIL: ...` line; the exit status is 0 when all passed, 1 otherwise, 3 when
QEMU could not be started.

The editor draws with escape sequences, so `Screen` replays what it sends
(cursor moves, erase, alternate screen) into a grid of rows and the checks
read the status line (mode, `[+]` for a dirty buffer) and the message line
from it, as a person at the terminal would.

Sessions (docs/BUDDHAFINGER_PROPOSAL.md, "Harland acceptance"):

  first          edit /var/notes.txt (new), leave Insert with a bare Escape,
                 `:w`, `:q`; the shell's terminal state afterwards (cooked
                 echo and rubout, Ctrl-C kills, $? = 130); reopen it and
                 check the bytes; an empty save; kills before and after a
                 save's write (`--pause-save`): the file holds the old or the
                 new contents, never a prefix; a new .ritz file, coloured,
                 `ipub<Esc>:wq` with no process fault (AGAST #4921)
  reboot         the same disk: every file of `first` persisted as it was
  contract       the save contract (platform/save_contract.ritz) through the
                 editor's store: `bf-save-contract run plain` prints a PASS
                 line for every case and exits 0; `bf-save-contract prepare
                 persist` and `prepare sync` write the old files the fault
                 boots try to replace
  fault-persist  booted with \\harland\\fault-persist: `:w` fails with the plain
                 "not written" message, the buffer stays dirty, and the
                 running system still reads the old bytes; `bf-save-contract
                 fault persist` passes (its save fails, the old file stays)
  fault-sync     booted with \\harland\\fault-sync: the same for a failed save
                 to storage (`fault sync`); first, the file reads as before
                 fault-persist's save
  after-faults   no faults: the file reads as it was before both failed
                 saves, and `bf-save-contract check persist` / `check sync`
                 find both old files
  ram-only       no storage device: a /tmp save is clean; a /var save stays
                 dirty (without storage kfs makes no /var: the open fails)

A /var save's close is a durable transaction (O_SYNC, harland/kernel/src/fs/
REPLACEMENT.md): a failed one leaves the old file everywhere, for the running
system and the next boot alike.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harland", "tools"))
from shell_session import EXIT_MARKERS, PROMPT, Console, _in_order, _lines, _ok  # noqa: E402

EDITOR = "buddhafinger"
CONTRACT = "bf-save-contract"
# platform/save_contract.ritz's ContractCase names, in order.
CONTRACT_CASES = [
    "round-trips", "final-newline", "large-file", "create-missing", "second-save",
    "permissions", "changed-underneath", "same-size-new-mtime", "created-underneath",
]
NOTES = "/var/notes.txt"
NOTES_TEXT = "hello world"              # one line, then LF: 12 bytes
# Seconds with nothing from the guest that count as the editor having
# painted. A paint is one write; the serial link drains it in well under this.
QUIET = float(os.environ.get("BF_QUIET", "0.8"))
ALT_ON = b"\x1b[?1049h"
ALT_OFF = b"\x1b[?1049l"


# ============================================================================
# Screen: what the editor's escape sequences draw
# ============================================================================

CSI = re.compile(rb"\x1b\[([?0-9;]*)([A-Za-z@])")


class Screen:
    """A rows x cols grid replaying the sequences ritzlib.termsession's
    TermOut writes: CUP (H), EL (K), ED (J), SGR (m, ignored), the cursor
    show/hide and alternate-screen modes (h/l), CR, LF and BS."""

    def __init__(self, rows: int = 24, cols: int = 80):
        self.rows, self.cols = rows, cols
        self.grid = [[" "] * cols for _ in range(rows)]
        self.r = self.c = 0
        self.alt = False
        self.pending = b""

    def feed(self, data: bytes) -> None:
        data = self.pending + data
        self.pending = b""
        i = 0
        while i < len(data):
            b = data[i]
            if b == 0x1B:
                m = CSI.match(data, i)
                if m is None:
                    if len(data) - i < 16:        # a sequence cut in two
                        self.pending = data[i:]
                        return
                    i += 1
                    continue
                self._csi(m.group(1).decode(), m.group(2).decode())
                i = m.end()
                continue
            if b == 0x0D:
                self.c = 0
            elif b == 0x0A:
                self.r = min(self.r + 1, self.rows - 1)
            elif b == 0x08:
                self.c = max(self.c - 1, 0)
            elif b >= 0x20:
                # UTF-8: one cell per code point, its first byte.
                n = 1
                if b >= 0xF0:
                    n = 4
                elif b >= 0xE0:
                    n = 3
                elif b >= 0xC0:
                    n = 2
                if i + n > len(data):
                    self.pending = data[i:]
                    return
                self._put(data[i:i + n].decode(errors="replace"))
                i += n
                continue
            i += 1

    def _put(self, ch: str) -> None:
        if self.c < self.cols:
            self.grid[self.r][self.c] = ch
        self.c += 1

    def _csi(self, params: str, final: str) -> None:
        if params.startswith("?"):
            if params[1:] == "1049":
                self.alt = final == "h"
                self.grid = [[" "] * self.cols for _ in range(self.rows)]
            return
        nums = [int(p) if p else 0 for p in params.split(";")] if params else []
        if final in "Hf":
            row = nums[0] if nums and nums[0] else 1
            col = nums[1] if len(nums) > 1 and nums[1] else 1
            self.r, self.c = min(row, self.rows) - 1, min(col, self.cols) - 1
        elif final == "K":
            for c in range(self.c, self.cols):
                self.grid[self.r][c] = " "
        elif final == "J":
            self.grid = [[" "] * self.cols for _ in range(self.rows)]
        elif final == "G":
            self.c = min(max(nums[0] if nums else 1, 1), self.cols) - 1

    def row(self, r: int) -> str:
        return "".join(self.grid[r]).rstrip()

    def status(self) -> str:
        return self.row(self.rows - 2)

    def message(self) -> str:
        return self.row(self.rows - 1)

    def text(self) -> list[str]:
        return [self.row(r) for r in range(self.rows - 2)]


# ============================================================================
# The editor on the console
# ============================================================================

class Editor:
    """One `buddhafinger ...` run: what it painted, and keys to it."""

    def __init__(self, con: Console, timeout: float, rows: int = 24, cols: int = 80):
        self.con, self.timeout = con, timeout
        self.scr = Screen(rows, cols)
        self.raw = b""

    def settle(self) -> None:
        """Read until the guest has been quiet for QUIET seconds."""
        deadline = time.monotonic() + self.timeout
        last = time.monotonic()
        while time.monotonic() < deadline:
            before = len(self.con.buf)
            if not self.con._recv():
                break
            if len(self.con.buf) > before:
                last = time.monotonic()
            elif time.monotonic() - last >= QUIET:
                break
        data, self.con.buf = self.con.buf, b""
        self.raw += data
        self.scr.feed(data)

    def start(self, args: str) -> bool:
        """Run the editor from the prompt; True once it is on the alternate
        screen with its first frame painted."""
        self.con.type_line(f"{EDITOR} {args}")
        out = self.con.expect(ALT_ON, self.timeout)
        if out is None:
            return False
        self.raw = ALT_ON
        self.scr.feed(ALT_ON)
        self.settle()
        return "NORMAL" in self.scr.status()

    def keys(self, data: bytes) -> None:
        self.con.type_bytes(data)
        self.settle()

    def save(self, data: bytes = b":w\r", answer: str = "written") -> str:
        """Type `data` (ending in `:w`) and return the message line once the
        save has answered on it with `answer` ("written" also matches "not
        written: ..."), or the timeout has passed. A quiet
        QUIET seconds is not an answer: the write and sync to the storage
        disk can take longer than that before the message is painted, which
        on a loaded host left the check reading the `:w` still being typed
        (AGAST #4808's gate)."""
        self.keys(data)
        deadline = time.monotonic() + self.timeout
        while answer not in self.scr.message() and time.monotonic() < deadline:
            self.settle()
        return self.scr.message()

    def dirty(self) -> bool:
        return "[+]" in self.scr.status()

    def quit(self, keys: bytes = b":q\r") -> bytes | None:
        """Quit; what the editor sent up to the shell's next prompt."""
        self.con.type_bytes(keys)
        out = self.con.expect(PROMPT, self.timeout)
        return None if out is None else self.raw + out


def shell(con: Console, cmd: str, timeout: float) -> list[str] | None:
    """Run `cmd` at the prompt: the lines it printed, or None."""
    con.type_line(cmd)
    out = con.expect(PROMPT, timeout)
    if out is None:
        return None
    return [ln for ln in _lines(out[: -len(PROMPT)]) if ln]


def file_is(con: Console, path: str, text: str, nbytes: int, timeout: float, what: str) -> int:
    """`cat` and `wc` of `path`: its lines are text's, its size nbytes."""
    lines = shell(con, f"cat {path}", timeout)
    want = [ln for ln in text.split("\n") if ln]
    fails = _ok(lines == want, f"{what}: `cat {path}` prints {want!r}", repr(lines).encode())
    wc = shell(con, f"wc {path}", timeout)
    size = wc[0].split()[2] if wc and len(wc[0].split()) >= 3 else None
    fails += _ok(size == str(nbytes), f"{what}: {path} holds {nbytes} bytes", repr(wc).encode())
    return fails


def terminal_restored(con: Console, timeout: float, after: str) -> int:
    """The console is the shell's again: a cooked read echoes and rubs out
    (TTY_ECHO, TTY_ICANON) and Ctrl-C kills (TTY_ISIG), $? = 130."""
    fails = 0
    con.type_line("cat")
    time.sleep(1.0)                                 # cat is in read(0)
    con.type_bytes(b"hellX\x7fo\r")
    out = con.expect(b"\x08 \x08o\r\nhello\n", timeout)
    fails += _ok(out is not None, f"after {after}: a cooked read echoes, rubs out and reads `hello`", out)
    con.type_bytes(b"\x03")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None and b"^C" in out, f"after {after}: Ctrl-C kills cat", out)
    lines = shell(con, "echo $?", timeout)
    fails += _ok(lines == ["130"], f"after {after}: cat killed by Ctrl-C exits 130", repr(lines).encode())
    return fails


def write_new(con: Console, path: str, text: str, timeout: float, what: str) -> int:
    """Create `path` with the editor: insert `text`, `:wq`."""
    ed = Editor(con, timeout)
    if not ed.start(path):
        return _ok(False, f"{what}: the editor starts on {path}", ed.raw)
    ed.keys(b"i" + text.encode().replace(b"\n", b"\r") + b"\x1b")
    out = ed.quit(b":wq\r")
    return _ok(out is not None and ALT_OFF in out, f"{what}: {path} written with :wq", out)


def kill_during_save(con: Console, when: str, timeout: float) -> int:
    """`--pause-save WHEN`, then Ctrl-C there: old or new, never a prefix."""
    path = f"/var/kill-{when}.txt"
    fails = write_new(con, path, "old\n", timeout, f"kill {when}")
    ed = Editor(con, timeout)
    fails += _ok(ed.start(f"--pause-save {when} {path}"), f"kill {when}: the editor starts", ed.raw)
    con.type_bytes(b"inew \x1b:w\r")
    out = con.expect(f"save paused {when.replace('-', ' ')}".encode(), timeout)
    fails += _ok(out is not None, f"kill {when}: the save stops {when.replace('-', ' ')}", out)
    time.sleep(1.0)                                 # in its read(0)
    con.type_bytes(b"\x03")
    out = con.expect(PROMPT, timeout)
    fails += _ok(out is not None, f"kill {when}: Ctrl-C kills the editor mid-save", out)
    lines = shell(con, "echo $?", timeout)
    fails += _ok(lines == ["130"], f"kill {when}: the editor exits 130", repr(lines).encode())
    if when == "before-write":
        fails += file_is(con, path, "old\n", 4, timeout, f"kill {when}: the old contents")
    else:
        fails += file_is(con, path, "new old\n", 8, timeout, f"kill {when}: the new contents")
    return fails


def ritz_file(con: Console, timeout: float) -> int:
    """A .ritz file is drawn in colour (AGAST #4921): typing `pub`, a
    keyword, into a new one and `:wq` saves it, with no process fault."""
    path = "/var/hl.ritz"
    ed = Editor(con, timeout)
    fails = _ok(ed.start(path), f"the editor starts on a new {path}", ed.raw)
    ed.keys(b"ipub")
    fails += _ok("INSERT" in ed.scr.status() and ed.scr.text()[0].split() == ["1", "pub"],
                 f"{path}: `ipub` is shown in Insert", repr(ed.scr.text()[:1] + [ed.scr.status()]).encode())
    # The keyword's colour: bold magenta (syntax/highlight.ritz kind_style).
    fails += _ok(b"\x1b[0;1;38;5;5mpub" in ed.raw,
                 f"{path}: the keyword is coloured", ed.raw[-400:])
    ed.keys(b"\x1b")
    out = ed.quit(b":wq\r")
    fails += _ok(out is not None and ALT_OFF in out and b"[fault]" not in out,
                 f"{path}: written with :wq, no process fault", out if out is not None else ed.raw)
    # No newline is added to a new file's last line (as ram_only's "ram").
    fails += file_is(con, path, "pub", 3, timeout, ".ritz save")
    return fails


# One contract verdict: "PASS: <case>" or "FAIL: <case>: <why>", to the end
# of the line (a verdict is the program's last write on its line).
VERDICT = re.compile(r"(?:PASS|FAIL): .*")


def contract(con: Console, args: str, want: list[str], timeout: float, what: str) -> int:
    """`bf-save-contract ARGS`: exactly the verdicts `want`, then $? = 0.
    The kernel logs on the same serial console (a heap grow, an munmap), so
    a verdict can land mid-line after one of its lines: each `PASS: ` /
    `FAIL: ` is read from where it starts, the kernel's text dropped."""
    lines = [m.group(0) for line in shell(con, f"{CONTRACT} {args}", timeout)
             for m in VERDICT.finditer(line)]
    fails = _ok(lines == want, f"{what}: `{CONTRACT} {args}` prints {len(want)} PASS line(s)",
                repr(lines).encode())
    rc = shell(con, "echo $?", timeout)
    fails += _ok(rc == ["0"], f"{what}: `{CONTRACT} {args}` exits 0", repr(rc).encode())
    return fails


def failed_save(con: Console, fault: str, timeout: float) -> int:
    """`:w` with the O_SYNC close failing: dirty, the plain "not written"
    message, and the old file still what the running system reads. The
    editor runs in a 30 x 120 viewport (--rows, --cols: Harland reports no
    size), wide enough for the whole message."""
    fails = 0
    ed = Editor(con, timeout, 30, 120)
    fails += _ok(ed.start(f"--rows 30 --cols 120 {NOTES}") and "NORMAL" in ed.scr.row(28),
                 f"{fault}: the editor starts on {NOTES}, its status line on row 29 of 30", ed.raw)
    msg = ed.save(b"idraft \x1b:w\r", answer="not saved to storage")
    fails += _ok(ed.dirty(), f"{fault}: the buffer stays dirty ([+])", ed.scr.status().encode())
    fails += _ok(f'"{NOTES}" not written: ' in msg and "may already have changed" not in msg,
                 f"{fault}: the message says the file was not written", msg.encode())
    out = ed.quit(b":q!\r")
    fails += _ok(out is not None, f"{fault}: :q! leaves the editor", out)
    fails += file_is(con, NOTES, NOTES_TEXT + "\n", len(NOTES_TEXT) + 1, timeout,
                     f"{fault}: the running system still reads the old file")
    return fails


# ============================================================================
# Sessions
# ============================================================================

def first(con: Console, timeout: float) -> int:
    fails = 0
    ed = Editor(con, timeout)
    fails += _ok(ed.start(NOTES) and "[New]" in ed.scr.message(),
                 f"the editor starts on a new {NOTES} from the serial console", ed.raw)
    ed.keys(b"i" + NOTES_TEXT.encode() + b"\r")
    fails += _ok("INSERT" in ed.scr.status(), "`i` enters Insert", ed.scr.status().encode())
    # A bare Escape: no key follows it, the editor's timed read ends it.
    ed.keys(b"\x1b")
    fails += _ok("NORMAL" in ed.scr.status(), "a bare Escape leaves Insert (no next key)",
                 ed.scr.status().encode())
    fails += _ok(ed.dirty(), "the edited buffer is dirty", ed.scr.status().encode())
    msg = ed.save()
    fails += _ok("written" in msg and not ed.dirty(), "`:w` saves and marks the buffer clean",
                 (msg + " | " + ed.scr.status()).encode())
    out = ed.quit()
    fails += _ok(out is not None and ALT_OFF in out, "`:q` leaves the alternate screen for the prompt", out)
    fails += terminal_restored(con, timeout, "the editor's :q")
    fails += file_is(con, NOTES, NOTES_TEXT + "\n", len(NOTES_TEXT) + 1, timeout, "saved")
    # Reopen: the bytes come back.
    ed = Editor(con, timeout)
    fails += _ok(ed.start(NOTES), f"the editor reopens {NOTES}", ed.raw)
    fails += _ok(ed.scr.text()[0].split() == ["1"] + NOTES_TEXT.split() and f'"{NOTES}" 1L, 12B' in ed.scr.message(),
                 "reopened: the line and its 12 bytes", repr(ed.scr.text()[:2] + [ed.scr.message()]).encode())
    ed.quit()
    # An empty save: write a file, then delete its only line and save.
    fails += write_new(con, "/var/empty.txt", "x", timeout, "empty save")
    ed = Editor(con, timeout)
    ed.start("/var/empty.txt")
    ed.save(b"x:w\r")
    fails += _ok("0L, 0B written" in ed.scr.message() and not ed.dirty(), "an empty buffer saves",
                 ed.scr.message().encode())
    ed.quit()
    fails += file_is(con, "/var/empty.txt", "", 0, timeout, "empty save")
    fails += kill_during_save(con, "before-write", timeout)
    fails += kill_during_save(con, "after-write", timeout)
    fails += ritz_file(con, timeout)
    return fails


def reboot(con: Console, timeout: float) -> int:
    fails = file_is(con, NOTES, NOTES_TEXT + "\n", len(NOTES_TEXT) + 1, timeout, "after a reboot")
    fails += file_is(con, "/var/empty.txt", "", 0, timeout, "after a reboot")
    fails += file_is(con, "/var/kill-before-write.txt", "old\n", 4, timeout, "after a reboot")
    fails += file_is(con, "/var/kill-after-write.txt", "new old\n", 8, timeout, "after a reboot")
    fails += file_is(con, "/var/hl.ritz", "pub", 3, timeout, "after a reboot")
    return fails


# The contract, then the old files the fault boots try to replace: they
# can't be written there (fault-persist fails every /var commit, and under
# fault-sync nothing reaches the storage device).
def contract_session(con: Console, timeout: float) -> int:
    fails = contract(con, "run plain", [f"PASS: {c}" for c in CONTRACT_CASES], timeout, "contract")
    for tag in ("persist", "sync"):
        fails += contract(con, f"prepare {tag}", ["PASS: fault-prepare"], timeout, "contract")
    return fails


# The persistent subtree's commit fails: the close fails, nothing changed.
def fault_persist(con: Console, timeout: float) -> int:
    fails = failed_save(con, "fault-persist", timeout)
    return fails + contract(con, "fault persist", ["PASS: fault-save"], timeout, "fault-persist")


def fault_sync(con: Console, timeout: float) -> int:
    # fault-persist's save never reached the image.
    fails = file_is(con, NOTES, NOTES_TEXT + "\n", len(NOTES_TEXT) + 1, timeout,
                    "rebooted after the failed persistent update")
    # The save to storage fails, so the close publishes nothing either.
    fails += failed_save(con, "fault-sync", timeout)
    return fails + contract(con, "fault sync", ["PASS: fault-save"], timeout, "fault-sync")


def after_faults(con: Console, timeout: float) -> int:
    fails = file_is(con, NOTES, NOTES_TEXT + "\n", len(NOTES_TEXT) + 1, timeout,
                    "rebooted after the failed saves")
    for tag in ("persist", "sync"):
        fails += contract(con, f"check {tag}", ["PASS: fault-check"], timeout, "after-faults")
    return fails


def ram_only(con: Console, timeout: float) -> int:
    fails = 0
    ed = Editor(con, timeout)
    fails += _ok(ed.start("/tmp/ram.txt"), "no storage device: the editor starts on /tmp/ram.txt", ed.raw)
    ed.save(b"iram\x1b:w\r")
    fails += _ok("written" in ed.scr.message() and not ed.dirty(),
                 "no storage device: a RAM-only save is clean", ed.scr.message().encode())
    ed.quit()
    fails += file_is(con, "/tmp/ram.txt", "ram", 3, timeout, "RAM-only save")
    # Without a storage device kfs never makes /var, so the open fails.
    ed = Editor(con, timeout)
    ed.start("/var/nodev.txt")
    msg = ed.save(b"ivar\x1b:w\r")
    fails += _ok(ed.dirty() and "not written: No such file or directory" in msg,
                 "no storage device: a /var save stays dirty and says why", msg.encode())
    ed.quit(b":q!\r")
    return fails


SESSIONS = {
    "first": first,
    "reboot": reboot,
    "contract": contract_session,
    "fault-persist": fault_persist,
    "fault-sync": fault_sync,
    "after-faults": after_faults,
    "ram-only": ram_only,
}


def main(argv: list[str]) -> int:
    if len(argv) < 5 or argv[3] != "--" or argv[0] not in SESSIONS:
        print(f"usage: harland_console.py {{{'|'.join(SESSIONS)}}} LOG TIMEOUT -- QEMU_ARGV...",
              file=sys.stderr)
        return 2
    session, log_path, timeout, qemu = SESSIONS[argv[0]], argv[1], float(argv[2]), argv[4:]
    # Under /tmp: sun_path is 107 bytes (shell_session.py, AGAST #4177).
    sock_dir = tempfile.mkdtemp(prefix="rz_bf_", dir=os.environ.get("SOCK_DIR", "/tmp"))
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
            print("FAIL: QEMU never connected its serial port")
            return 1
        with open(log_path, "wb") as log:
            con = Console(conn, log)
            if con.expect(PROMPT, timeout) is None:
                print(f"FAIL: [{argv[0]}] no rzsh prompt within {timeout:.0f}s")
                return 1
            if session(con, timeout):
                rc = 1
            con.type_line("exit")
            tail = con.drain(timeout)
            try:
                qrc = proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                qrc = None
            if _ok(_in_order(tail, EXIT_MARKERS) and qrc == 0,
                   f"[{argv[0]}] `exit` powers the guest off", tail):
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
