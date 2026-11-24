"""AGAST #4636: ritzlib (all modules)'s C-shaped API fns, pinned down-only.

The whole tree, so a new C-shaped fn in a module with no file here fails
too.  The per-module files say where the counts are.

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

PINS = {"bool-return": (6, 6), "out-param": (5, 18), "status-return": (22, 108)}


def test_ritzlib_c_shapes_only_go_down():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib"]))
    assert ratchet_breaches(summary, PINS) == []
