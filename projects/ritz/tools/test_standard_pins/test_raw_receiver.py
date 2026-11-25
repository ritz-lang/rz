"""AGAST #4682: ritzlib's raw `self: *T` method receivers, pinned down-only.

STANDARD.md S-IMPL-3: the receiver says what the method does to `self`,
`self: @T` to read and `self: @&T` / `self:&` to change it.  A raw
`self: *T` says neither, so `standard_report.py` counts it as
`raw-receiver`.  The base had 161, every one `pub`; this pins each module.

A module not listed is pinned at zero, so a new `pub fn m(self: *Foo)`
anywhere in ritzlib fails here.  The pin is a ceiling of
(violations, violations + exempt): a `*T` receiver that has to stay is
exempt with a reason, which keeps its total and passes.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree

pytestmark = pytest.mark.unit

RITZLIB = Path(__file__).resolve().parent.parent.parent / "ritzlib"

# module (path under ritzlib) -> (violations, violations + exempt).  #4682
# ported all 161 (async/tasks 44, uring 27, timer 16, memory 14, iovec 14,
# async/runtime 13, span 12, elf 7, fs 6, result 5, option 3) to @T / @&T,
# with none left exempt, so every module is pinned at zero.
PINS: dict[str, tuple[int, int]] = {}


def raw_receivers(root: Path) -> dict[str, tuple[int, int]]:
    """{module: (violations, violations + exempt)} of raw-receiver under `root`."""
    out: dict[str, list[int]] = {}
    for s in scan_tree([root]):
        if s.key == "raw-receiver":
            c = out.setdefault(Path(s.path).relative_to(root).as_posix(), [0, 0])
            c[0] += s.exempt is None
            c[1] += 1
    return {k: (v, t) for k, (v, t) in out.items()}


def test_raw_receivers_only_go_down():
    breaches = [
        f"{mod}: {got} raw receivers (violations, total) > pin {PINS.get(mod, (0, 0))}"
        for mod, got in sorted(raw_receivers(RITZLIB).items())
        if got[0] > PINS.get(mod, (0, 0))[0] or got[1] > PINS.get(mod, (0, 0))[1]
    ]
    assert breaches == []


def test_a_new_raw_receiver_turns_the_pin_red(tmp_path):
    """Mutation check: one `pub fn m(self: *Foo)` in an unpinned module fails."""
    (tmp_path / "foo.ritz").write_text(
        "struct Foo\n    n: i64\n\nimpl Foo\n    pub fn m(self: *Foo) -> i64\n        self.n\n")
    assert raw_receivers(tmp_path) == {"foo.ritz": (1, 1)}
