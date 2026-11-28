"""AGAST #4929: the status shapes status-return learned to see, pinned by name.

#4929 taught status-return a callee's negative passed back up (`if r < 0` /
`return r`), `Err(e) => return -e.code()`, a trailing negative literal and an
integer return that is only ever 0.  async/ and uring.ritz were ported to
Result/TaskStep in the same commit and have none left.  These are the rest of
ritzlib, the fmt/timer/buf methods of the sibling ticket (AGAST #4930) plus
hashmap's `-1`-when-full slot: pinned down-only by name, so the list may shrink
(delete the row you port) and never grow.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree

pytestmark = pytest.mark.unit

RITZLIB = Path(__file__).resolve().parent.parent.parent / "ritzlib"

# (module, fn) of every non-exempt status-return site left in ritzlib.
PINNED = {
    ("buf.ritz", "clear"),
    ("buf.ritz", "free"),
    ("buf.ritz", "from_str"),
    ("buf.ritz", "get_loc"),
    ("buf.ritz", "init"),
    ("buf.ritz", "restore"),
    ("buf.ritz", "skip"),
    ("fmt.ritz", "writeln"),
    ("fmt/display.ritz", "fmt_show_with"),
    ("fmt/impls.ritz", "fmt_debug_bytes"),
    ("fmt/impls.ritz", "fmt_debug_strview"),
    ("fmt/writer.ritz", "push_bytes"),
    ("fmt/writer.ritz", "write_fill"),
    ("hashmap.ritz", "find_slot"),
    ("timer.ritz", "init"),
    ("timer.ritz", "print"),
    ("timer.ritz", "reset"),
}


def _sites(key):
    return [s for s in scan_tree([RITZLIB]) if s.key == key and s.exempt is None]


def test_status_return_sites_are_only_the_pinned_ones():
    found = {(Path(s.path).relative_to(RITZLIB).as_posix(), s.fn) for s in _sites("status-return")}
    assert found <= PINNED, f"new status-return sites: {sorted(found - PINNED)}"


def test_async_and_uring_have_no_status_return():
    """#4929 acceptance: the new detections are 0 for async/ and uring.ritz."""
    sites = scan_tree([RITZLIB / "async", RITZLIB / "uring.ritz"])
    assert [s for s in sites if s.key == "status-return" and s.exempt is None] == []


def test_no_raw_pointer_in_a_public_callback_type():
    """#4929: a `fn(*T)` parameter makes every callback take a raw pointer."""
    assert [s for s in _sites("raw-ptr-param") if "fn(" in s.detail] == []
