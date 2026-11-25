"""AGAST #4534: str is C-string interop only; every raw *u8 is a C ABI."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_str_module_has_no_raw_pointer_parameters():
    """AGAST #4534, #4688: str.ritz holds the libc ABI symbols only.

    The C-string API moved to ritzlib.cstr (test_cshape_cstr.py) and strcmp,
    strcpy, strcat, strchr, strstr and atoi were deleted; the remaining 9 raw
    pointer parameters across 5 functions (memset, memcpy, memcmp, bcmp,
    memmove) are the symbols the compiler emits calls to.
    """
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "str.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 9}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
