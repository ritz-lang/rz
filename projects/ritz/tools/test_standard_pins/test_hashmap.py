"""AGAST #4539: hashmap.ritz raw *T parameters are converted or exempt.

4 exemptions: allocator.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_hashmap_module_has_no_raw_pointer_parameters():
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "hashmap.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 4}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}


def test_hashmap_lookups_borrow_not_return_raw_pointers():
    """AGAST #4689: get_ptr / value_ptr became get_mut -> Option<@&V>: no ptr-return."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "hashmap.ritz"]))
    assert summary["ptr-return"] == {"violations": 0, "exempt": 0}
