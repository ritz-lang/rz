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

# status-return went to (19, 101) when #4929 taught the rule new shapes;
# AGAST #4930 ported those 19 to Result / Option / (), leaving 86 exempt
# protocol boundaries (Writer.push_bytes, the Display bodies, sys_*).
PINS = {"out-param": (0, 13), "status-return": (0, 86)}


def test_ritzlib_c_shapes_only_go_down():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib"]))
    assert ratchet_breaches(summary, PINS) == []


def test_ritzlib_has_no_raw_alloc_violation():
    """AGAST #4689: mapping.munmap, the last one, is exempt (ritzlib.mapping IS the mmap owner)."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib"]))
    assert summary["raw-alloc"]["violations"] == 0
