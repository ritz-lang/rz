"""AGAST #4534: str is C-string interop only; every raw *u8 is a C ABI."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_str_module_has_no_raw_pointer_parameters():
    """AGAST #4534: str is C-string interop only; every raw *u8 is a C ABI.

    The two functions with a StrView/String equivalent and no callers
    (strrchr, strncpy) were deleted; the remaining 25 raw pointer parameters
    across 15 functions are exempted against the C ABI they exist to serve.
    strchr and strstr stay because nexus/zeus test suites still call them.
    """
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "str.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 25}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
