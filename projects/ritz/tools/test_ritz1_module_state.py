"""AGAST #4454: ritz1's per-compile state lives in ctx structs, not globals.

ritz1 carried 316 column-0 `var`s of per-compile state (measured on
380f6d08).  Module globals make a compile non-re-entrant and hide which
pass reads what, so #4454 moves them into structs passed through the calls
(MonoCtx for monomorphisation, file by file) toward <= 5 justified globals.

This is the ratchet for that move, a source grep like the other ritz1 freeze
tests: the total may only fall, and a file converted to a ctx struct stays at
zero.  Lower `BUDGET` (and add the file to `CONVERTED`) in the commit that
converts one; a new global needs a reason good enough to raise it.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parent.parent / "ritz1" / "src"

# Column-0 `var`s across ritz1/src.  317 on #4454's base; monomorph's 50 went
# into MonoCtx.
BUDGET = 267

# Files whose state is a ctx struct: no module `var` at all.
CONVERTED = ("monomorph.ritz",)

VAR = re.compile(r"^var ", re.M)


def _globals(path: Path) -> int:
    return len(VAR.findall(path.read_text()))


def test_module_globals_within_budget():
    counts = {p.name: _globals(p) for p in sorted(SRC.glob("*.ritz"))}
    total = sum(counts.values())
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    assert total <= BUDGET, f"{total} module globals > budget {BUDGET}; most: {top}"


@pytest.mark.parametrize("name", CONVERTED)
def test_converted_file_has_no_module_globals(name):
    text = (SRC / name).read_text()
    found = [l for l in text.splitlines() if l.startswith("var ")]
    assert not found, f"{name} keeps its state in a ctx struct: {found}"
