"""AGAST #3462 (LARB review/5 ritz1 N1): no new checks on `EmitterState`.

ritz1 ran every semantic check during code generation: each one is a
`pub fn *check*(s: *EmitterState, ...)` that the emitter calls mid-lowering.
From #3462 on, a new check goes into the `Sema` pass (ritz1/src/sema*.ritz),
which runs over the AST between infer_generic_calls / monomorphisation and
emit_module.  See "Where a new check goes" in ritz1/ARCHITECTURE.md.

This test freezes the old pattern.  It greps ritz1/src for

    pub fn <name with "check">(s: *EmitterState

and compares the matches, as `file:fn`, with ritz1_emitter_checks.allow
beside this file (today's matches):

- a match that is not on the list fails: a new emitter-side check, or a moved
  one put back;
- an entry that no longer matches fails too, so a move onto Sema must delete
  its entries and the list only ever shrinks.

Each move off the emitter is a child ticket of #1816.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
RITZ = TOOLS.parent
SRC = RITZ / "ritz1" / "src"
ALLOWLIST = TOOLS / "ritz1_emitter_checks.allow"

# The ticket's pattern, verbatim (git grep -E).
PATTERN = r"pub fn [a-z_]*check[a-z_]*\(s: \*EmitterState"
_HIT = re.compile(r"^(?:.*/)?([^/:]+\.ritz):\d+:\s*pub fn ([a-z_]+)\(")


def grep_hits(src: Path = SRC) -> set[str]:
    """`file:fn` for every frozen-pattern match in ritz1/src (git grep)."""
    proc = subprocess.run(["git", "grep", "-nE", PATTERN, "--", "."],
                          cwd=src, capture_output=True, text=True)
    # 1 = no match; anything else is git failing.
    assert proc.returncode in (0, 1), proc.stderr
    return parse_hits(proc.stdout)


def parse_hits(out: str) -> set[str]:
    hits = set()
    for line in out.splitlines():
        m = _HIT.match(line)
        assert m, f"unparsed git grep line: {line!r}"
        hits.add(f"{m.group(1)}:{m.group(2)}")
    return hits


def read_allowlist(path: Path = ALLOWLIST) -> set[str]:
    entries = set()
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            entries.add(line)
    return entries


def violations(hits: set[str], allowed: set[str]) -> list[str]:
    """Messages for each new match and each stale entry; empty when frozen."""
    out = [f"new emitter-side check {h}: put it on Sema (ritz1/ARCHITECTURE.md "
           f"'Where a new check goes'), not on EmitterState"
           for h in sorted(hits - allowed)]
    out += [f"{a} no longer matches: delete it from {ALLOWLIST.name} "
            f"(the list only shrinks)" for a in sorted(allowed - hits)]
    return out


@pytest.mark.unit
def test_no_new_emitter_state_checks():
    problems = violations(grep_hits(), read_allowlist())
    assert not problems, "\n".join(problems)


@pytest.mark.unit
def test_must_use_check_is_off_the_emitter():
    # The first move (#3462): must_use runs on Sema, so neither the grep
    # nor the list may name it.
    assert not any(e.startswith("must_use.ritz:") for e in read_allowlist())
    assert not any(h.startswith("must_use.ritz:") for h in grep_hits())


@pytest.mark.unit
def test_a_planted_check_is_refused():
    planted = "foo.ritz:12:pub fn foo_check(s: *EmitterState, e: *Expr)\n"
    allowed = {"bar.ritz:bar_check"}
    hits = parse_hits("bar.ritz:3:pub fn bar_check(s: *EmitterState)\n" + planted)
    assert violations(hits, allowed) == [violations({"foo.ritz:foo_check"}, set())[0]]


@pytest.mark.unit
def test_a_stale_entry_is_refused():
    assert violations(set(), {"bar.ritz:bar_check"}) != []
    assert violations({"bar.ritz:bar_check"}, {"bar.ritz:bar_check"}) == []


@pytest.mark.unit
def test_the_pattern_matches_the_ticket_shape(tmp_path):
    # git grep over a scratch repo: the shapes the ticket names, and not
    # a Sema check or a non-check fn on EmitterState.
    (tmp_path / "a.ritz").write_text(
        "pub fn foo_check(s: *EmitterState)\n"
        "pub fn check_tail(s: *EmitterState, e: *Expr)\n"
        "pub fn sema_check(sm: *Sema, e: *Expr)\n"
        "pub fn emit_expr(s: *EmitterState, e: *Expr) -> i32\n"
        "fn private_check(s: *EmitterState)\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "a.ritz"], cwd=tmp_path, check=True)
    assert grep_hits(tmp_path) == {"a.ritz:foo_check", "a.ritz:check_tail"}
