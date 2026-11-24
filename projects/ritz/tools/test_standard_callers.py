"""AGAST #4636: calls of ritzlib's exempt raw APIs from outside ritzlib, pinned down-only.

An exemption says a function is a raw boundary (the kernel ABI, the
allocator, C strings); it doesn't make the raw layer the right thing for
the rest of the tree to call.  This counts how far it escapes:
`standard_report.py --callers` finds each call of an exempt public ritzlib
fn in projects/**, outside ritzlib, in a file that imports its module.

Each project's count is a ceiling: porting callers to the idiomatic API
lowers it and passes (lower the pin when you do).  A new raw call fails.

A commit that newly exempts a ritzlib fn makes its existing callers count
for the first time: that commit raises the pins it moves, naming the API
in its message.  That is the only reason to raise one.

This lives in tools/, not tools/test_standard_pins/: it names every package,
and tools/ritz0_scope.py reads the pins directory as a ritz0-step source, so
there it would make every package an input of the ritz0 step (#4032).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from standard_report import callers_by_project, count_callers

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent
PROJECTS = RITZ_ROOT.parent

PINS = {
    "angelo": 31,
    "cryptosec": 402,
    "goliath": 64,
    "harland": 25,
    "http": 129,
    "indium": 123,
    "larb": 5,
    "lexis": 12,
    "mausoleum": 763,
    "nexus": 99,
    "prism": 15,
    "ritz": 3071,
    "ritz-lsp": 102,
    "ritzunit": 58,
    "rzrz": 13,
    "rzsh": 99,
    "sage": 15,
    "spire": 104,
    "squeeze": 6,
    "tempest": 1,
    "tome": 397,
    "valet": 319,
    "zeus": 156,
}


@pytest.fixture(scope="module")
def by_project():
    return callers_by_project(
        count_callers(RITZ_ROOT / "ritzlib", [PROJECTS]), PROJECTS
    )


def test_raw_api_callers_only_go_down(by_project):
    over = {p: (n, PINS.get(p, 0)) for p, n in by_project.items() if n > PINS.get(p, 0)}
    assert over == {}, f"project: (calls, pin) over the pin: {over}"
