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
  covered.);
- the emit_ir_error family takes a `span: SrcSpan`, so no call site can be
  unlocated (the 56 calls that used to print `error: ritz1 cannot emit: ...`
  with no file:line:col).

ALLOWED lists files not yet ported; it only shrinks.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS.parent / "ritz1" / "src"

DIAG = "diag.ritz"

# Files still allowed a hand-rolled `error: ` prefix.  Empty: all ported.
ALLOWED: frozenset[str] = frozenset()

# The ticket's pattern: a bare `error: ` prefix (git grep -E).
PATTERN = r'eprints_cstr\(c"error: "\)'


def grep(pattern: str) -> list[str]:
    proc = subprocess.run(["git", "grep", "-nE", pattern, "--", "*.ritz"],
                          cwd=SRC, capture_output=True, text=True)
    assert proc.returncode in (0, 1), proc.stderr
    return [ln for ln in proc.stdout.splitlines() if ln]


def offenders(lines: list[str]) -> list[str]:
    """The grep lines outside diag.ritz and ALLOWED."""
    out = []
    for ln in lines:
        fname = ln.split(":", 1)[0]
        if fname != DIAG and fname not in ALLOWED:
            out.append(ln)
    return out


def test_pattern_catches_the_old_prefix():
    # The pattern itself must still match the shapes it bans.
    rx = re.compile(PATTERN)
    assert rx.search('    eprints_cstr(c"error: ")')
    assert not rx.search('    eprints_cstr(c": error: ")')


def test_no_error_prefix_outside_diag():
    bad = offenders(grep(PATTERN))
    assert not bad, (
        "print ritz1 errors with diag_error* (ritz1/src/diag.ritz), not a "
        "hand-rolled `error: ` prefix:\n" + "\n".join(bad))


def test_allowlist_only_names_files_that_still_need_it():
    hits = {ln.split(":", 1)[0] for ln in grep(PATTERN)}
    stale = sorted(ALLOWED - hits)
    assert not stale, f"ported, drop from ALLOWED: {stale}"


def test_diag_module_prints_the_prefix():
    text = (SRC / DIAG).read_text()
    assert "pub fn diag_error(file: *u8, span: SrcSpan, msg: *u8)" in text
    assert 'c": error: "' in text


def test_emit_ir_error_family_takes_a_span():
    text = (SRC / "emitter_core.ritz").read_text()
    sigs = re.findall(r"^pub fn (emit_ir_error[a-z_]*)\(([^)]*)\)", text, re.M)
    assert sigs, "emit_ir_error not found in emitter_core.ritz"
    unlocated = [name for name, params in sigs
                 if "span: SrcSpan" not in params and name != "emit_ir_error_end"]
    assert not unlocated, f"emit_ir_error helpers without a span: {unlocated}"
