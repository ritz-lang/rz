"""AGAST #4532: Buffer/GrowBuf behaviour lives in impl blocks, not free fns."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent


def test_buf_module_has_no_free_fns_taking_its_own_types():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "buf.ritz"]))
    assert summary["free-fn-method"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
