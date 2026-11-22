"""AGAST #4539: testlib.ritz raw *T parameters are converted or exempt.

9 exemptions: C strings / execve(2) ABI.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_testlib_module_has_no_raw_pointer_parameters():
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "testlib.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 9}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
