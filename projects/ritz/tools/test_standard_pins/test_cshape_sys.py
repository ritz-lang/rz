"""AGAST #4636: sys.ritz's C-shaped API fns, pinned down-only.

The sys_* kernel ABI is exempt by `standard-exempt-file(sys_*)`; the last
non-exempt fns (signal_ignore, tcgetattr, get_winsize, ...) moved to
ritzlib.process and ritzlib.term as Results (AGAST #4686).

The pin is a ceiling of (violations, violations + exempt) per counting rule
(standard_report.ratchet_breaches): a migration that lowers a count passes,
and a new C-shaped fn, exempt or not, fails.  Lower the pin when you lower
the count.  A rule not listed is pinned at zero.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import ratchet_breaches, scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent

PINS = {"out-param": (0, 9), "status-return": (0, 71)}


def test_sys_c_shapes_only_go_down():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "sys.ritz"]))
    assert ratchet_breaches(summary, PINS) == []


# sentinel-return isn't a C_SHAPE_KEYS rule, so it's pinned here (AGAST #4691):
# signalfd_read's "0 = none pending, negative = errno" went to ritzlib.process
# as Result<Option<i32>, Errno>.  What's left is at_fdcwd (AT_FDCWD, -100, not
# an error) in sys.ritz, and 4 in all of ritzlib.  Down only.
def test_sentinel_returns_only_go_down():
    sys_ritz = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "sys.ritz"]))["sentinel-return"]
    ritzlib = summarise(scan_tree([RITZ_ROOT / "ritzlib"]))["sentinel-return"]
    assert sys_ritz["violations"] == 0 and sys_ritz["exempt"] <= 1
    assert ritzlib["violations"] == 0 and ritzlib["exempt"] <= 4
