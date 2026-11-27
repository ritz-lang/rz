#!/usr/bin/env python3
"""CI must boot harland with no serial port and read its screen (AGAST #4868).

projects/harland/tools/test_fbcon_boot.sh boots harland under OVMF with
`-serial none` and std VGA, and tools/fbcon_screen.py decodes QMP
screendumps of the framebuffer console with the kernel's own font table
(kernel/src/drivers/display/font8x16.ritz). These pin:

  * the wiring: the step runs after the serial shell boot and before the log
    upload, gates for real and has a timeout;
  * the decoder: text drawn with the kernel's font, as fbcon.ritz draws it
    (x1 and the x2 of modes wider than 2000 px, light grey on dark blue or
    white on red, a cursor underline), decodes back to the same text; a
    missing QEMU is a SETUP ERROR (exit 3).

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_fbcon_boot.py -q
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ci_local

REPO = ci_local.REPO_ROOT
FBCON_SCRIPT = "projects/harland/tools/test_fbcon_boot.sh"
SHELL_SCRIPT = "projects/harland/tools/test_shell_boot.sh"
DECODER = REPO / "projects/harland/tools/fbcon_screen.py"

sys.path.insert(0, str(DECODER.parent))
import fbcon_screen

GREY_ON_BLUE = ((0xC8, 0xC8, 0xC8), (0x10, 0x20, 0x40))  # fbcon.ritz FG_* / BG_*
WHITE_ON_RED = ((0xFF, 0xFF, 0xFF), (0xA0, 0x00, 0x00))  # PANIC_FG_* / PANIC_BG_*


# --------------------------------------------------------------------------
# Wiring: main.yml
# --------------------------------------------------------------------------


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _indices(steps: list[dict], script: str) -> list[int]:
    return [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]


def test_fbcon_boot_runs_after_the_shell_boot_and_before_the_log_upload():
    assert (REPO / FBCON_SCRIPT).is_file()
    steps = _build_all()
    [fbcon] = _indices(steps, FBCON_SCRIPT)
    assert fbcon > max(_indices(steps, SHELL_SCRIPT))
    uploads = [
        i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))
    ]
    assert uploads and min(uploads) > fbcon, "the decoded screens must be uploaded too"


def test_fbcon_step_is_a_real_gate_with_a_timeout():
    steps = _build_all()
    [step] = [steps[i] for i in _indices(steps, FBCON_SCRIPT)]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    parsed = [s for s in ci_local.load_steps() if FBCON_SCRIPT in s.run]
    assert len(parsed) == 1 and not parsed[0].is_setup


def test_the_boot_runs_without_a_serial_port():
    text = (REPO / FBCON_SCRIPT).read_text()
    assert "-serial none" in text
    assert "panic-test" in text and "--idle-after" in text


# --------------------------------------------------------------------------
# The decoder
# --------------------------------------------------------------------------


def _render(lines: list[str], width: int, height: int, colours, cursor=None) -> bytes:
    """A P6 PPM of `lines` drawn as fbcon.ritz draws them."""
    by_char = {c: g for g, c in fbcon_screen.load_font().items()}
    fg, bg = colours
    scale = 2 if width > fbcon_screen.SCALE2_MIN_WIDTH else 1
    px = [[bg] * width for _ in range(height)]
    for row, line in enumerate(lines):
        for col, c in enumerate(line):
            glyph = by_char[c]
            for gy in range(16):
                bits = glyph[gy]
                if cursor == (row, col) and gy >= 14:
                    bits = 0xFF
                for gx in range(8):
                    if bits & (0x80 >> gx):
                        for sy in range(scale):
                            for sx in range(scale):
                                px[row * 16 * scale + gy * scale + sy][
                                    col * 8 * scale + gx * scale + sx
                                ] = fg
    body = b"".join(bytes(p) for line in px for p in line)
    return b"P6\n# fbcon test\n%d %d\n255\n" % (width, height) + body


@pytest.mark.parametrize(
    "width,height,colours",
    [
        (320, 64, GREY_ON_BLUE),
        (2048, 64, WHITE_ON_RED),  # x2 glyphs
    ],
)
def test_decoder_reads_back_what_the_kernel_font_draws(
    tmp_path, width, height, colours
):
    lines = ["Hello from Harland!", "rzsh> ls ~/{a,b} | cat", "*** KERNEL PANIC ***"][
        : height // (16 * (2 if width > 2000 else 1))
    ]
    shot = tmp_path / "shot.ppm"
    shot.write_bytes(_render(lines, width, height, colours))
    got = fbcon_screen.decode_file(shot)
    assert got[: len(lines)] == lines


def test_decoder_reads_the_cell_under_the_cursor(tmp_path):
    shot = tmp_path / "shot.ppm"
    shot.write_bytes(_render(["rzsh> x"], 160, 32, GREY_ON_BLUE, cursor=(0, 6)))
    assert fbcon_screen.decode_file(shot)[0] == "rzsh> x"


@pytest.mark.integration
def test_decode_cli_prints_the_screen(tmp_path):
    shot = tmp_path / "shot.ppm"
    shot.write_bytes(_render(["No COM1"], 160, 32, GREY_ON_BLUE))
    out = subprocess.run(
        [sys.executable, str(DECODER), "decode", str(shot)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.splitlines()[0] == "No COM1"


@pytest.mark.integration
def test_watch_without_qemu_is_a_setup_error(tmp_path):
    r = subprocess.run(
        [
            sys.executable,
            str(DECODER),
            "watch",
            "--qmp",
            str(tmp_path / "q.sock"),
            "--shots",
            str(tmp_path / "s"),
            "--timeout",
            "1",
            "--",
            str(tmp_path / "no-such-qemu"),
        ],
        capture_output=True,
        text=True,
        env={**os.environ},
        check=False,
    )
    assert r.returncode == 3
    assert "SETUP ERROR" in r.stderr


def test_send_keys_parse_chords_and_hold_times():
    """--send's KEYS (AGAST #4888): one QEMU key name per key, `-` joining a
    chord, `@MS` a hold time; anything else is refused before QEMU starts."""
    assert fbcon_screen.parse_keys("e spc ctrl-c shift-4 x@1200") == [
        (["e"], None),
        (["spc"], None),
        (["ctrl", "c"], None),
        (["shift", "4"], None),
        (["x"], 1200),
    ]
    for bad in ("", "ctrl-", "x@", "x@soon"):
        with pytest.raises(ValueError):
            fbcon_screen.parse_keys(bad)


def test_qmp_do_parses_and_keeps_its_place_among_the_sends():
    """--qmp-do RE CMD (AGAST #4889's hot-plug): CMD is a QMP command's name
    and key=value arguments, and it runs in order with the --send steps."""
    assert fbcon_screen.parse_qmp_do("device_add driver=usb-kbd id=kbd bus=xhci1.0") == (
        "device_add",
        {"driver": "usb-kbd", "id": "kbd", "bus": "xhci1.0"},
    )
    for bad in ("device_del id", "device_del =kbd"):
        with pytest.raises(ValueError):
            fbcon_screen.parse_qmp_do(bad)
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", nargs=2, action=fbcon_screen.Step, const="keys", dest="steps", default=[])
    ap.add_argument("--qmp-do", nargs=2, action=fbcon_screen.Step, const="qmp", dest="steps", default=[])
    args = ap.parse_args(["--send", "a", "x", "--qmp-do", "b", "device_del id=kbd", "--send", "c", "y"])
    assert args.steps == [("keys", "a", "x"), ("qmp", "b", "device_del id=kbd"), ("keys", "c", "y")]
