"""AGAST #4929: the status shapes status-return learned to see, pinned by name.

#4929 taught status-return a callee's negative passed back up (`if r < 0` /
`return r`), `Err(e) => return -e.code()`, a trailing negative literal and an
integer return that is only ever 0.  async/ and uring.ritz were ported to
Result/TaskStep in the same commit and have none left.  The rest of ritzlib
(fmt/timer/buf and hashmap's `-1`-when-full slot) were pinned here by name
until AGAST #4930 ported them; the by-name allowance is gone and the count is
0.  A site that is a genuine protocol boundary carries a `standard-exempt:
status-return:` comment instead.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree

pytestmark = pytest.mark.unit

RITZLIB = Path(__file__).resolve().parent.parent.parent / "ritzlib"

def _sites(key):
    return [s for s in scan_tree([RITZLIB]) if s.key == key and s.exempt is None]


def test_ritzlib_has_no_status_return_site():
    """#4930 acceptance: the by-name pin is gone; every site is ported or exempt."""
    found = sorted((Path(s.path).relative_to(RITZLIB).as_posix(), s.fn) for s in _sites("status-return"))
    assert found == []


def test_async_and_uring_have_no_status_return():
    """#4929 acceptance: the new detections are 0 for async/ and uring.ritz."""
    sites = scan_tree([RITZLIB / "async", RITZLIB / "uring.ritz"])
    assert [s for s in sites if s.key == "status-return" and s.exempt is None] == []


def test_no_raw_pointer_in_a_public_callback_type():
    """#4929: a `fn(*T)` parameter makes every callback take a raw pointer."""
    assert [s for s in _sites("raw-ptr-param") if "fn(" in s.detail] == []
