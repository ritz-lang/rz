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

The second pin (#4673) is the count of `c"..."` literals per project
(`standard_report.py --c-literals`).  STANDARD.md S-TEXT-1: a NUL-terminated
literal belongs only at a C-interop boundary, so a project's count only goes
down.  Porting a call site to a StrView API lowers it (lower the pin); a new
`c""` anywhere in the project fails, tests included.  There is no reason to
raise it: a boundary that needs a new NUL-terminated string belongs in a
ritzlib wrapper that takes a StrView.

This lives in tools/, not tools/test_standard_pins/: it names every package,
and tools/ritz0_scope.py reads the pins directory as a ritz0-step source, so
there it would make every package an input of the ritz0 step (#4032).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from standard_report import (
    c_literal_breaches,
    c_literals_by_project,
    callers_by_project,
    count_callers,
)

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent
PROJECTS = RITZ_ROOT.parent

PINS = {
    "angelo": 7,
    "cryptosec": 109,
    "goliath": 36,
    "harland": 23,
    "http": 125,
    "indium": 123,
    "larb": 3,
    "lexis": 10,
    "mausoleum": 499,
    "nexus": 45,
    "prism": 7,
    "ritz": 2014,
    "ritz-lsp": 87,
    "ritzunit": 43,
    "rzrz": 11,
    "rzsh": 18,
    "sage": 13,
    "spire": 85,
    "squeeze": 2,
    "tempest": 1,
    "tome": 151,
    "valet": 72,
    "zeus": 76,
}


@pytest.fixture(scope="module")
def by_project():
    return callers_by_project(
        count_callers(RITZ_ROOT / "ritzlib", [PROJECTS]), PROJECTS
    )


def test_raw_api_callers_only_go_down(by_project):
    over = {p: (n, PINS.get(p, 0)) for p, n in by_project.items() if n > PINS.get(p, 0)}
    assert over == {}, f"project: (calls, pin) over the pin: {over}"


# `c"..."` literals per project, on the #4673 base (3e49c82c5049).  Down only.
C_LITERAL_PINS = {
    "cryptosec": 295,
    "goliath": 45,
    "harland": 60,
    "http": 148,
    "indium": 165,
    "iris": 1,
    "larb": 14,
    "mausoleum": 161,
    "nexus": 229,
    "prism": 17,
    "ritz": 5643,
    "ritz-lsp": 82,
    "ritzunit": 108,
    "rzrz": 41,
    "rzsh": 6,
    "sage": 1,
    "spire": 25,
    "tome": 9,
    "valet": 2,
    "zeus": 158,
}


def test_c_literals_only_go_down():
    over = c_literal_breaches(c_literals_by_project([PROJECTS]), C_LITERAL_PINS)
    assert over == [], f"new c\"\" literals (S-TEXT-1: C interop only): {over}"
