"""AGAST #3445 (LARB review/5 ritz1 N5): ritz1 prints errors through `diag`.

ritz1 had ~60 bespoke error printers: 42 hand-rolled

    eprints_cstr(c"error: ")

prefixes, each followed by its own `if file != null ... "<input>"` fallback,
and per-module helpers (si_error_at, enum_error_at, own_eprint_loc, ...).
Half printed `error: <file>:<line>:<col>: `, the other half
`<file>:<line>:<col>: error: `.  ritz1/src/diag.ritz is now the one place
that prints the location prefix, always as `<file>:<line>:<col>: error: `.

These tests keep it that way:

- no file under ritz1/src but diag.ritz writes a bare `error: ` prefix,
  `eprints_cstr(c"error: ")`, to put a location after -- go through
  diag_error* instead.  (A location-less fatal such as `c"error: ritz1
  parser arena exhausted ..."` has no file:line:col to give and is not
  covered.)

ALLOWED lists the files not yet ported (the emitter, and with it the
unlocated emit_ir_error family); it only shrinks.  That port is AGAST
#3621.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS.parent / "ritz1" / "src"

DIAG = "diag.ritz"

# Files still allowed a hand-rolled `error: ` prefix (AGAST #3621).
ALLOWED: frozenset[str] = frozenset({
    "emitter.ritz",
    "emitter_core.ritz",
    "emitter_expr_access.ritz",
    "emitter_expr_arith.ritz",
    "emitter_expr_call.ritz",
    "emitter_match.ritz",
    "emitter_print.ritz",
    "enum_as_int.ritz",
})

# The ticket's pattern: a bare `error: ` prefix (git grep -E).
PATTERN = r'eprints_cstr\(c"error: "\)'


def grep(pattern: str, src: Path = SRC) -> list[str]:
    """`file:line:text` for every match under ritz1/src (git grep's shape).

    Read in-process rather than via `git grep`: a unit test starts no
    processes (AGAST #1805)."""
    rx = re.compile(pattern)
    out = []
    for path in sorted(src.glob("*.ritz")):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if rx.search(line):
                out.append(f"{path.name}:{n}:{line}")
    return out


def offenders(lines: list[str]) -> list[str]:
    """The grep lines outside diag.ritz and ALLOWED."""
    out = []
    for ln in lines:
        fname = ln.split(":", 1)[0]
        if fname != DIAG and fname not in ALLOWED:
            out.append(ln)
    return out


@pytest.mark.unit
def test_pattern_catches_the_old_prefix():
    # The pattern itself must still match the shapes it bans.
    rx = re.compile(PATTERN)
    assert rx.search('    eprints_cstr(c"error: ")')
    assert not rx.search('    eprints_cstr(c": error: ")')


@pytest.mark.unit
def test_no_error_prefix_outside_diag():
    bad = offenders(grep(PATTERN))
    assert not bad, (
        "print ritz1 errors with diag_error* (ritz1/src/diag.ritz), not a "
        "hand-rolled `error: ` prefix:\n" + "\n".join(bad))


@pytest.mark.unit
def test_allowlist_only_names_files_that_still_need_it():
    hits = {ln.split(":", 1)[0] for ln in grep(PATTERN)}
    stale = sorted(ALLOWED - hits)
    assert not stale, f"ported, drop from ALLOWED: {stale}"


@pytest.mark.unit
def test_diag_module_prints_the_prefix():
    text = (SRC / DIAG).read_text()
    assert "pub fn diag_error(file: *u8, span: SrcSpan, msg: *u8)" in text
    assert 'c": error: "' in text

