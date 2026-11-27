#!/usr/bin/env python3
"""Read harland's framebuffer console back out of a screendump (AGAST #4868).

The kernel draws text with the 8x16 font in
kernel/src/drivers/display/font8x16.ritz (doubled on modes wider than 2000
px), cells packed from the top-left corner. This parses that same table,
cuts a QEMU screendump (binary PPM) into cells, and matches each cell's
on/off pixels (luma above 128: the console's light grey and the panic
screen's white are on; its dark blue and red are off) against the glyphs.
A cell under the cursor matches on its top 14 rows. Anything else is '?'.

  fbcon_screen.py decode SHOT.ppm
      print the screen's text

  fbcon_screen.py watch --qmp SOCK --shots DIR --timeout S
                        [--expect RE]... [--absent RE]... [--idle-after RE]
                        [--send RE KEYS]... -- QEMU ARGV...
      start QEMU with `-qmp unix:SOCK,server=on,wait=off` appended, take a
      screendump every second, and pass once every --expect regex has been
      on screen (in any shot: the boot log scrolls) and, with --idle-after,
      CPU 0 has been seen halted (HLT=1: idle in sti;hlt) after that regex
      appeared. An --absent regex on screen fails at once. QEMU is killed
      at the end; the last screen's text is in DIR/screen.txt, every
      screen's in DIR/screens.txt.

      --send RE KEYS types at the guest's keyboard (AGAST #4888): once RE is
      on screen, each of KEYS (space-separated QEMU key names, `-` joining a
      chord: "e c h o spc h i ret", "ctrl-c", "shift-4"; `@MS` holds it
      down MS milliseconds: "a@1200") goes to QMP send-key in turn. The
      --send steps run in order, each only after the one before it was
      sent, and the watch passes only once all were sent.

Exit: 0 pass; 1 fail (timeout, an --absent match, QEMU exited early);
3 QEMU could not be started (a SETUP ERROR, as the other boot scripts).
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT_SRC = HERE.parent / "kernel/src/drivers/display/font8x16.ritz"

FONT_W = 8
FONT_H = 16
FONT_FIRST = 32
SCALE2_MIN_WIDTH = 2000  # textgrid.ritz GRID_SCALE2_MIN_WIDTH
CURSOR_ROWS = 2  # fbcon.ritz CURSOR_ROWS
LUMA_ON = 128

EXIT_FAIL = 1
EXIT_SETUP = 3


def load_font(src: Path = FONT_SRC) -> dict[bytes, str]:
    """Glyph bitmap (16 row bytes) -> character, from FONT_8X16's table."""
    m = re.search(
        r"^const FONT_8X16: \[\d+\]u8 = \[(.*?)^\]",
        src.read_text(),
        re.DOTALL | re.MULTILINE,
    )
    if m is None:
        raise ValueError(f"{src}: no FONT_8X16 table")
    body = re.sub(r"#[^\n]*", "", m.group(1))
    values = [int(v, 16) for v in re.findall(r"0x[0-9A-Fa-f]{2}", body)]
    if len(values) % FONT_H:
        raise ValueError(
            f"{src}: FONT_8X16 has {len(values)} bytes, not a multiple of {FONT_H}"
        )
    glyphs: dict[bytes, str] = {}
    for i in range(len(values) // FONT_H):
        bitmap = bytes(values[i * FONT_H : (i + 1) * FONT_H])
        glyphs.setdefault(bitmap, chr(FONT_FIRST + i))
    return glyphs


def read_ppm(data: bytes) -> tuple[int, int, bytes]:
    """(width, height, RGB bytes) of a binary (P6, maxval 255) PPM."""
    fields: list[bytes] = []
    pos = 0
    while len(fields) < 4:
        while data[pos : pos + 1].isspace():
            pos += 1
        if data[pos : pos + 1] == b"#":
            pos = data.index(b"\n", pos) + 1
            continue
        end = pos
        while not data[end : end + 1].isspace():
            end += 1
        fields.append(data[pos:end])
        pos = end
    if fields[0] != b"P6" or fields[3] != b"255":
        raise ValueError("not a binary 8-bit PPM")
    width, height = int(fields[1]), int(fields[2])
    pos += 1
    return width, height, data[pos : pos + width * height * 3]


def decode(width: int, height: int, rgb: bytes, glyphs: dict[bytes, str]) -> list[str]:
    """The screen's text, one string per row, trailing blanks dropped."""
    scale = 2 if width > SCALE2_MIN_WIDTH else 1
    cw, ch = FONT_W * scale, FONT_H * scale
    cols, rows = width // cw, height // ch
    top_rows = FONT_H - CURSOR_ROWS
    by_top = {}
    for bitmap, c in glyphs.items():
        by_top.setdefault(bitmap[:top_rows], c)

    def on(x: int, y: int) -> bool:
        i = (y * width + x) * 3
        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
        return (299 * r + 587 * g + 114 * b) // 1000 > LUMA_ON

    lines = []
    for row in range(rows):
        chars = []
        for col in range(cols):
            x0, y0 = col * cw, row * ch
            bitmap = bytes(
                sum(
                    0x80 >> gx
                    for gx in range(FONT_W)
                    if on(x0 + gx * scale, y0 + gy * scale)
                )
                for gy in range(FONT_H)
            )
            c = glyphs.get(bitmap)
            if c is None:
                c = by_top.get(bitmap[:top_rows], "?")
            chars.append(c)
        lines.append("".join(chars).rstrip())
    return lines


def decode_file(path: Path, glyphs: dict[bytes, str] | None = None) -> list[str]:
    width, height, rgb = read_ppm(path.read_bytes())
    return decode(width, height, rgb, glyphs or load_font())


class Qmp:
    def __init__(self, path: str, deadline: float):
        while True:
            try:
                self.sock = socket.socket(socket.AF_UNIX)
                self.sock.connect(path)
                break
            except OSError:
                self.sock.close()
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)
        self.buf = b""
        self._read()  # greeting
        self.call("qmp_capabilities")

    def _read(self) -> dict:
        while b"\n" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("QMP closed")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return json.loads(line)

    def call(self, cmd: str, **args) -> dict:
        msg = {"execute": cmd}
        if args:
            msg["arguments"] = args
        self.sock.sendall(json.dumps(msg).encode() + b"\n")
        while True:
            reply = self._read()
            if "return" in reply or "error" in reply:
                return reply

    def hmp(self, command: str) -> str:
        reply = self.call("human-monitor-command", **{"command-line": command})
        return reply.get("return", "")


KEY_GAP_S = 0.1  # between keys: each send-key is a press and a release


Chord = tuple[list[str], int | None]


def parse_keys(keys: str) -> list[Chord]:
    """'e ctrl-c a@900' -> [(['e'], None), (['ctrl', 'c'], None), (['a'], 900)]:
    one chord per key, with its hold time in ms if it has one."""
    chords: list[Chord] = []
    for token in keys.split():
        names, at, hold = token.partition("@")
        chord = names.split("-")
        if any(not n for n in chord) or (at and not hold.isdigit()):
            raise ValueError(f"bad key list: {keys!r}")
        chords.append((chord, int(hold) if hold else None))
    if not chords:
        raise ValueError(f"bad key list: {keys!r}")
    return chords


def send_keys(qmp: Qmp, chords: list[Chord]) -> None:
    for chord, hold in chords:
        args: dict = {"keys": [{"type": "qcode", "data": n} for n in chord]}
        if hold is not None:
            args["hold-time"] = hold
        reply = qmp.call("send-key", **args)
        if "error" in reply:
            raise ConnectionError(f"send-key {'-'.join(chord)}: {reply['error']}")
        # send-key returns at once; a held key is released hold ms later.
        time.sleep(KEY_GAP_S + (hold or 0) / 1000)


def cpu0_halted(qmp: Qmp) -> bool:
    qmp.hmp("cpu 0")
    return re.search(r"\bHLT=1\b", qmp.hmp("info registers")) is not None


def watch(args: argparse.Namespace) -> int:
    shots = Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    glyphs = load_font()
    argv = args.qemu + ["-qmp", f"unix:{args.qmp},server=on,wait=off"]
    try:
        with open(shots / "qemu.out", "wb") as qemu_out:
            qemu = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=qemu_out,
                stderr=subprocess.STDOUT,
            )
    except OSError as e:
        print(f"SETUP ERROR: QEMU could not be started: {e}", file=sys.stderr)
        return EXIT_SETUP
    deadline = time.monotonic() + args.timeout
    pending = list(args.expect)
    idle_re = re.compile(args.idle_after) if args.idle_after else None
    idle_armed = False
    idle_seen = idle_re is None
    absent = [re.compile(a) for a in args.absent]
    steps = [(re.compile(r), parse_keys(k)) for r, k in args.send]
    screens = (shots / "screens.txt").open("w")
    lines: list[str] = []
    rc = EXIT_FAIL
    why = "timeout"
    try:
        qmp = Qmp(args.qmp, deadline)
        n = 0
        while time.monotonic() < deadline:
            if qemu.poll() is not None:
                why = f"QEMU exited ({qemu.returncode})"
                break
            shot = shots / "shot.ppm"
            reply = qmp.call("screendump", filename=str(shot))
            if "error" in reply or not shot.exists():
                time.sleep(1)
                continue
            lines = decode_file(shot, glyphs)
            text = "\n".join(lines)
            n += 1
            screens.write(f"===== screen {n} =====\n{text}\n")
            bad = [a.pattern for a in absent if a.search(text)]
            if bad:
                why = f"on screen, must not be: {bad}"
                break
            pending = [e for e in pending if not re.search(e, text)]
            if steps and steps[0][0].search(text):
                send_keys(qmp, steps.pop(0)[1])
                time.sleep(1)
                continue
            if idle_re is not None and not idle_armed and idle_re.search(text):
                idle_armed = True
            if idle_armed and not idle_seen:
                idle_seen = any(cpu0_halted(qmp) for _ in range(20))
            if not pending and idle_seen and not steps:
                rc = 0
                why = "pass"
                break
            time.sleep(1)
    except (OSError, ConnectionError) as e:
        why = f"QMP: {e}"
    finally:
        qemu.kill()
        qemu.wait()
        screens.close()
        (shots / "screen.txt").write_text("\n".join(lines) + "\n")
    if rc != 0:
        print(f"FAIL: {why}")
        for e in pending:
            print(f"  never on screen: {e}")
        if idle_re is not None and not idle_seen:
            state = "after it appeared" if idle_armed else "(it never appeared)"
            print(f"  CPU 0 never idle (HLT=1) {state}: {args.idle_after}")
        for r, _ in steps:
            print(f"  never on screen to type at: {r.pattern}")
    return rc


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("decode")
    d.add_argument("shot")
    w = sub.add_parser("watch")
    w.add_argument("--qmp", required=True)
    w.add_argument("--shots", required=True)
    w.add_argument("--timeout", type=float, default=300)
    w.add_argument("--expect", action="append", default=[])
    w.add_argument("--absent", action="append", default=[])
    w.add_argument("--idle-after")
    w.add_argument("--send", nargs=2, action="append", default=[], metavar=("RE", "KEYS"))
    w.add_argument("qemu", nargs=argparse.REMAINDER)
    args = ap.parse_args(argv)
    if args.cmd == "decode":
        print("\n".join(decode_file(Path(args.shot))))
        return 0
    if args.qemu and args.qemu[0] == "--":
        args.qemu = args.qemu[1:]
    if not args.qemu:
        ap.error("watch needs -- QEMU ARGV")
    for _, keys in args.send:
        try:
            parse_keys(keys)
        except ValueError as e:
            ap.error(str(e))
    return watch(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
