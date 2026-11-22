"""Pin String/StrView APIs to their impls (AGAST #4533)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_string_and_strview_modules_have_no_free_fn_methods():
    """AGAST #4533: String/StrView APIs live on their impls, not free fns."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "string.ritz",
                                   RITZ_ROOT / "ritzlib" / "strview.ritz"]))
    assert summary["free-fn-method"] == {"violations": 0, "exempt": 0}
