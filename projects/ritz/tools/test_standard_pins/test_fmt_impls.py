"""AGAST #4539: fmt/impls.ritz raw *T parameters are converted or exempt.

None left: AGAST #4685 deleted the 3 C string shims (fmt_show_cstr,
fmt_show_cstr_with, fmt_debug_cstr); `impl Display for *u8` in
ritzlib.fmt.display views the string with strview_from_cstr instead.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_fmt_impls_module_has_no_raw_pointer_parameters():
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "fmt" / "impls.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
