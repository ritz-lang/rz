"""AGAST #4539: async_net.ritz raw *T parameters are converted or exempt."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_async_net_module_has_no_raw_pointer_parameters():
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "async_net.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
