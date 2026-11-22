"""AGAST #4539: async/blocking_fs.ritz raw *T parameters are converted or exempt.

4 exemptions: NUL-terminated paths handed to open(2).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_async_blocking_fs_module_has_no_raw_pointer_parameters():
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "async" / "blocking_fs.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 4}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
