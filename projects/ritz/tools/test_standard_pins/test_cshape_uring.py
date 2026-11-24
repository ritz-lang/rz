"""AGAST #4636: uring.ritz's C-shaped API fns, pinned down-only.

IoUring.submit/submit_and_wait and sys_io_uring_enter return Result<i32, Errno>
(#4637); the 2 left are the exempt setup/register syscall wrappers.

The pin is a ceiling of (violations, violations + exempt) per counting rule
(standard_report.ratchet_breaches): a migration that lowers a count passes,
and a new C-shaped fn, exempt or not, fails.  Lower the pin when you lower
the count.  A rule not listed is pinned at zero.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import ratchet_breaches, scan_source, scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent

PINS = {"status-return": (0, 2)}


def test_uring_c_shapes_only_go_down():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "uring.ritz"]))
    assert ratchet_breaches(summary, PINS) == []


def test_uring_raw_pointers_only_on_the_syscalls():
    """#4637 (was #4647): prep_* take Span/@SockAddrStorage/@KernelTimespec;
    only io_uring_setup/register keep raw-pointer parameters (kernel ABI)."""
    path = RITZ_ROOT / "ritzlib" / "uring.ritz"
    sites = scan_source(path.read_text(), str(path))
    raw = sorted({s.fn for s in sites if s.key == "raw-ptr-param"})
    assert raw == ["sys_io_uring_register", "sys_io_uring_setup"]
