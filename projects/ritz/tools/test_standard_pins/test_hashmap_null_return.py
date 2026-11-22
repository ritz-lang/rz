"""AGAST #4540: a missing hashmap key is None, not null (S-OPTION-1).

Moved verbatim out of `tools/test_standard_report.py` by AGAST #4551, so this
pin lives in its own file and cannot collide with another car's pin.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_hashmap_module_has_no_null_returning_get():
    """AGAST #4540: a missing key is None, not null (S-OPTION-1)."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "hashmap.ritz"]))
    assert summary["null-return"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
