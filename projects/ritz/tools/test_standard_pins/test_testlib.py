"""testlib.ritz takes no raw pointer and carries no exemption (AGAST #4643).

#4539 exempted 9 raw params (C strings, execve(2) vectors).  #4643 reversed
that: testlib is the template every example test copies, so it takes
StrView / Span<StrView> and returns Result, and its fork/exec lives in
ritzlib.process.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_testlib_module_has_no_raw_pointer_parameters_or_exemptions():
    """AGAST #4643: no rule is violated, and none is exempted either."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "testlib.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert all(counts == {"violations": 0, "exempt": 0}
               for counts in summary.values()), summary
