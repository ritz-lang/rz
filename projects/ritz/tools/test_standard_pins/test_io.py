"""AGAST #4539: io.ritz raw *T parameters are converted or exempt.

2 exemptions: NUL-terminated C string printers (eprints_cstr, eprintln_cstr);
#4565 deleted prints_cstr and println_cstr.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_io_module_has_no_raw_pointer_parameters():
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "io.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
