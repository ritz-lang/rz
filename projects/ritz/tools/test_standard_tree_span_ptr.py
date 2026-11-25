"""Pin span.ritz / strview.ritz / string.ritz at zero raw-ptr-param violations.

AGAST #4535.  The three modules expose Span/StrView/String APIs.  The
routines whose parameters are pointers to containers now take borrows
(`@Span<u8>`, `@Vec<T>`) instead of raw `*Span<u8>`; the remaining `*u8`
parameters are genuine C-string / raw-pair constructor boundaries, so they
take the standard's documented exemption path.

Counts are pinned per module so a later edit cannot quietly reintroduce a
raw pointer parameter or drop an exemption's reason.  Kept in its own file:
tools/test_standard_report.py is being split concurrently (#4551).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent


def _summary(module: str) -> dict[str, dict[str, int]]:
    return summarise(scan_tree([RITZ_ROOT / "ritzlib" / module]))


@pytest.mark.parametrize(
    ("module", "exempt"),
    [
        ("span.ritz", 3),     # 3 raw-pair constructor boundaries (#4639 deleted span_from_cstr, span_eq_cstr)
        ("strview.ritz", 1),  # the raw-pair constructor boundary; the C-string API moved to ritzlib.cstr (#4688)
        ("string.ritz", 2),   # 2 *Allocator; the C-string API moved to ritzlib.cstr (#4688)
    ],
)
def test_raw_pointer_parameters_are_converted_or_exempted(module, exempt):
    """AGAST #4535: every raw-ptr-param site is a borrow or a documented exemption."""
    summary = _summary(module)
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": exempt}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
