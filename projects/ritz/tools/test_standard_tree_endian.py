"""Pin ritzlib/endian.ritz against docs/STANDARD.md's raw-ptr-param rule.

AGAST #4644 (reversing #4538).  endian's reads and writes took a raw `*u8`
with no length, all 12 exempt as a "byte-codec boundary": an out-of-range
read was a silent overread.  They now take a `Span<u8>` and an offset and
check the access fits, so the module has no raw pointer parameter and no
exemption.  This file pins that, so a raw `*u8` form cannot quietly return.

Kept in its own file: rooms #4531-#4534 were editing
tools/test_standard_report.py concurrently when #4538 added it.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent


def test_endian_has_no_raw_pointer_parameters():
    """AGAST #4644: every entry point takes a Span<u8>, none is exempt."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "endian.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
