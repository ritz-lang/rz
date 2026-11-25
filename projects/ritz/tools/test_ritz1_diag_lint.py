"""AGAST #3445 (LARB review/5 ritz1 N5): ritz1 prints errors through `diag`.

ritz1 had ~60 bespoke error printers: 42 hand-rolled

    eprints("error: ")

prefixes (then spelled with eprints_cstr and a c-literal; AGAST #4683
moved ritz1's literal prints to `eprints("..")`), each followed by its own
`if file != null ... "<input>"` fallback, and per-module helpers (si_error_at, enum_error_at, own_eprint_loc, ...).
Half printed `error: <file>:<line>:<col>: `, the other half
`<file>:<line>:<col>: error: `.  ritz1/src/diag.ritz is now the one place
that prints the location prefix, always as `<file>:<line>:<col>: error: `.

These tests keep it that way:

- no file under ritz1/src but diag.ritz writes a bare `error: ` prefix,
  `eprints("error: ")`, to put a location after -- go through
  diag_error* instead.  (A location-less fatal such as `c"error: ritz1
  parser arena exhausted ..."` has no file:line:col to give and is not
  covered.)

- the emit_ir_error family (emitter_core.ritz) takes the `span: SrcSpan`
  of the construct it could not lower, so its `ritz1 cannot emit: ` line is
  located like every other error (AGAST #3621).

ALLOWED, the files not yet ported, is empty since AGAST #3621.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS.parent / "ritz1" / "src"

DIAG = "diag.ritz"

# Files still allowed a hand-rolled `error: ` prefix.  Empty since AGAST
# #3621 ported the emitter; it only shrinks, so it stays empty.
ALLOWED: frozenset[str] = frozenset()

# The ticket's pattern: a bare `error: ` prefix (git grep -E).
PATTERN = r'eprints\("error: "\)'


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
    assert rx.search('    eprints("error: ")')
    assert not rx.search('    eprints(": error: ")')


@pytest.mark.unit
def test_pattern_catches_a_planted_prefix(tmp_path):
    # A planted `eprints("error: ")` outside diag.ritz is an offender;
    # the same line in diag.ritz is not.
    (tmp_path / "planted.ritz").write_text('fn f()\n    eprints("error: ")\n')
    (tmp_path / DIAG).write_text('fn g()\n    eprints("error: ")\n')
    bad = offenders(grep(PATTERN, tmp_path))
    assert bad == ['planted.ritz:2:    eprints("error: ")']


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
    assert "pub fn diag_error(file: *u8, span: SrcSpan, msg: StrView)" in text
    assert 'eprints(": error: ")' in text



# AGAST #3621: every emit_ir_error* entry point that starts a message takes
# the span it prints at.  (_end finishes a _begin and prints no prefix.)
EMIT_IR_ERROR_FNS = ("emit_ir_error", "emit_ir_error_begin", "emit_ir_error_kind")

def emit_ir_error_signatures(text: str) -> dict[str, str]:
    """name -> parameter list of each `pub fn emit_ir_error*(...)`."""
    out = {}
    for m in re.finditer(r"^pub fn (emit_ir_error\w*)\(([^)]*)\)", text, re.M):
        out[m.group(1)] = m.group(2)
    return out


@pytest.mark.unit
def test_emit_ir_error_family_takes_a_span():
    sigs = emit_ir_error_signatures((SRC / "emitter_core.ritz").read_text())
    for name in EMIT_IR_ERROR_FNS:
        assert name in sigs, f"{name} not found in emitter_core.ritz"
        assert "span: SrcSpan" in sigs[name], (
            f"{name}({sigs[name]}) must take `span: SrcSpan`: an emitter "
            "error is printed at <file>:<line>:<col> (AGAST #3621)")


@pytest.mark.unit
def test_signature_check_catches_an_unlocated_one():
    sigs = emit_ir_error_signatures("pub fn emit_ir_error(s: *EmitterState, msg: *u8)\n")
    assert "span: SrcSpan" not in sigs["emit_ir_error"]
