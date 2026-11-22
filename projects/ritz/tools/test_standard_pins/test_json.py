"""AGAST #4446: json's API takes references, Span and StrView."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_json_module_has_no_raw_pointer_parameters():
    """AGAST #4446: json's API takes references, Span and StrView."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "json.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
