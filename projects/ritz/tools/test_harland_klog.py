"""Harland logs through one API, klog.ritz (AGAST #1885).

Before #1885 the kernel had four log entry points: klog(*u8) wrote COM1 and
the crash ring buffer, while prints(), serial_print() and a private
prints_str() wrote COM1 only. Most of kernel_main used prints(), so the ring
that exceptions.ritz dumps on a crash held almost none of the boot. Numbers
went through serial_print_dec(u64), which printed -1 as
18446744073709551615.

These read the kernel's source: no kernel module may write COM1 except
klog.ritz (the sink) and serial.ritz (the driver). Runs in `make tools-unit`.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HARLAND = Path(__file__).resolve().parents[2] / "harland"
KERNEL = HARLAND / "kernel" / "src"

# The files allowed to write COM1 directly, relative to kernel/src: the sink,
# the driver, and the TTY's keystroke echo (user I/O, not a kernel message;
# it runs in the COM1 IRQ handler and writes the port straight).
SINKS = {"klog.ritz", "serial.ritz", "tty/console.ritz"}

# Every call that writes COM1 and skips the ring: the polled driver's output
# functions (boot_abi/src/serial.ritz, re-exported by serial.ritz) and the
# kernel's old wrappers over them.
SERIAL_ONLY = re.compile(
    r"\b(prints|println|prints_str|serial_print(?:_sv)?|serial_write|serial_write_byte"
    r"|serial_print_dec|serial_print_hex(?:_width|8|16|32|64)?"
    r"|print_hex_prefix(?:8|16|32|64)?)\s*\("
)


def code(line):
    """line without its comment or string literals."""
    line = re.sub(r'c?"(?:[^"\\]|\\.)*"', '""', line)
    return line.split("#", 1)[0]


def serial_only_calls(root):
    """'file:line: text' for each serial-only output call outside SINKS."""
    hits = []
    for path in sorted(root.rglob("*.ritz")):
        if path.relative_to(root).as_posix() in SINKS:
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            text = code(line)
            if re.match(r"\s*(pub\s+)?(fn|extern\s+fn)\b", text):
                continue
            if SERIAL_ONLY.search(text):
                hits.append(f"{path.relative_to(root)}:{n}: {line.strip()}")
    return hits


def test_scanner_sees_a_serial_only_call(tmp_path):
    (tmp_path / "a.ritz").write_text(
        'fn f()\n    prints("x")  # boot\n    klog("y")\n'
        '    serial_print_dec(n as u64)\n    serial_print_hex64(v)\n'
        '    klog("prints(")\n'
    )
    assert serial_only_calls(tmp_path) == [
        'a.ritz:2: prints("x")  # boot',
        "a.ritz:4: serial_print_dec(n as u64)",
        "a.ritz:5: serial_print_hex64(v)",
    ]


def test_scanner_skips_the_sinks(tmp_path):
    (tmp_path / "klog.ritz").write_text("fn f()\n    serial_write(p, n)\n")
    (tmp_path / "serial.ritz").write_text("fn g()\n    serial_print(s)\n")
    assert serial_only_calls(tmp_path) == []


def test_every_kernel_message_reaches_the_ring():
    hits = serial_only_calls(KERNEL)
    assert not hits, (
        f"{len(hits)} kernel output call(s) skip the crash ring; log through "
        "klog.ritz (klog, klog_dec, klog_udec, klog_hex, "
        "klog_hex_width, klog_hex_prefix):\n" + "\n".join(hits[:40])
    )


def test_kernel_declares_no_strview():
    """The kernel's StrView is ritzlib's (re-exported by serial.ritz)."""
    hits = [
        f"{p.relative_to(KERNEL)}:{n}"
        for p in sorted(KERNEL.rglob("*.ritz"))
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if re.match(r"\s*(pub\s+)?struct\s+StrView\b", line)
    ]
    assert hits == []


def test_one_decimal_formatter():
    """No `% 10` digit loop in the kernel: decimal digits come from
    ritzlib.fmt.digits (through klog_dec / klog_udec or fmt_u64_into)."""
    hits = [
        f"{p.relative_to(KERNEL)}:{n}: {line.strip()}"
        for p in sorted(KERNEL.rglob("*.ritz"))
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"%\s*10\b", code(line))
    ]
    assert hits == []
