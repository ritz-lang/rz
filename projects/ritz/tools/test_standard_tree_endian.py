"""Pin ritzlib/endian.ritz against docs/STANDARD.md's raw-ptr-param rule.

AGAST #4538.  endian.ritz is a byte-codec module: every entry point is a raw
`*u8` offset into a caller-owned buffer, and the callers walk a stream with
`p + n` in crypto inner loops (`block + i * 8`, `out + p`, `@key[4]`).  There
is no length at the call boundary -- `sha512_transform(ctx, block: *u8)` takes
exactly 128 bytes, `poly1305_init(ctx, key: *u8)` exactly 32 -- so a Span
parameter could not check anything; it would have to invent a length.  The 12
functions therefore take the standard's documented exemption path, and this
file pins that decision so a later edit cannot quietly change it.

Kept in its own file: rooms #4531-#4534 are editing
tools/test_standard_report.py concurrently, and this pin belongs to #4538.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent


def test_endian_raw_pointer_parameters_are_exempted_with_reasons():
    """AGAST #4538: 12 byte-codec entry points, all exempt, none malformed."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "endian.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 12}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
