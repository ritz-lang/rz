"""AGAST #4539: fmt/digits.ritz raw *T parameters are converted or exempt.

None left: AGAST #4685 made the four digit routines take a `[u8]` and return a
StrView, so neither the 4 "format buffer sink" raw-ptr-param exemptions nor
the 4 "false positive" ptr-len-param ones remain.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_fmt_digits_module_has_no_raw_pointer_parameters():
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "fmt" / "digits.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert summary["ptr-len-param"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
