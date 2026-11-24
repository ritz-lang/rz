"""AGAST #4636: net.ritz's C-shaped API fns, pinned down-only.

Only the sys_* socket ABI, exempt by `standard-exempt-file(sys_*)`.

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

PINS = {"out-param": (0, 4), "status-return": (0, 9)}


def test_net_c_shapes_only_go_down():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "net.ritz"]))
    assert ratchet_breaches(summary, PINS) == []
