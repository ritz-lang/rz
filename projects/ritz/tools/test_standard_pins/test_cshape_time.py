"""AGAST #4637: time.ritz's Duration/sleep/now: no C shapes.

The pin is a ceiling of (violations, violations + exempt) per counting rule
(standard_report.ratchet_breaches): a new C-shaped fn, exempt or not, fails.
A rule not listed is pinned at zero.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import ratchet_breaches, scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent

PINS: dict[str, tuple[int, int]] = {}


def test_time_c_shapes_only_go_down():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "time.ritz"]))
    assert ratchet_breaches(summary, PINS) == []
