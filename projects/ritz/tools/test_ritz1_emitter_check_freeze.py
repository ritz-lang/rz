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

AGAST #3903: a blank line separates each module's group of entries, so two
#1816 rooms deleting neighbouring modules' lines leave an untouched line
between their hunks and cherry-pick onto each other cleanly (the same rule
tools/ritz1_arch.py holds for ARCHITECTURE.md's Checks list, #3896).  A move
deletes only its own entry lines; a run of blank lines left behind is fine.
"""

from __future__ import annotations

import itertools
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


def spacing_violations(text: str) -> list[str]:
    """Entries that start a new module's group without a blank line above."""
    out, prev_mod, prev_blank = [], None, True
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not raw.strip():
            prev_blank = True
            continue
        if not line:  # a comment line: neither entry nor separator
            continue
        mod = line.split(":", 1)[0]
        if prev_mod is not None and mod != prev_mod and not prev_blank:
            out.append(f"{line} starts module {mod}'s group: put a blank line "
                       f"above it in {ALLOWLIST.name} (neighbouring modules' "
                       f"entries must not touch adjacent lines)")
        prev_mod, prev_blank = mod, False
    return out


def violations(hits: set[str], allowed: set[str]) -> list[str]:
    """Messages for each new match and each stale entry; empty when frozen."""
    out = [f"new emitter-side check {h}: put it on Sema (ritz1/ARCHITECTURE.md "
           f"'Where a new check goes'), not on EmitterState"
           for h in sorted(hits - allowed)]
    out += [f"{a} no longer matches: delete it from {ALLOWLIST.name} "
            f"(the list only shrinks)" for a in sorted(allowed - hits)]
    return out


@pytest.mark.integration
def test_no_new_emitter_state_checks():
    problems = violations(grep_hits(), read_allowlist())
    assert not problems, "\n".join(problems)


@pytest.mark.unit
def test_allowlist_separates_modules():
    problems = spacing_violations(ALLOWLIST.read_text())
    assert not problems, "\n".join(problems)


@pytest.mark.unit
def test_a_missing_separator_is_refused():
    assert spacing_violations("a.ritz:x\na.ritz:y\n\nb.ritz:z\n") == []
    # Comments neither separate nor break a group.
    assert spacing_violations("# h\na.ritz:x\n# c\na.ritz:y\n") == []
    assert len(spacing_violations("a.ritz:x\n# c\nb.ritz:z\n")) == 1
    assert len(spacing_violations("a.ritz:x\nb.ritz:y\n")) == 1


def _git(repo: Path, *args: str) -> None:
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "PATH": "/usr/bin:/bin", "HOME": "/nonexistent"}
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, env=env)


def _room(repo: Path, branch: str, drop: set[str]) -> None:
    """A #1816 move on `branch` off `base`: delete the `drop` entries' lines."""
    _git(repo, "checkout", "-q", "-b", branch, "base")
    f = repo / ALLOWLIST.name
    lines = f.read_text().splitlines(keepends=True)
    f.write_text("".join(ln for ln in lines if ln.strip() not in drop))
    _git(repo, "commit", "-qam", branch)


def _groups() -> list[list[str]]:
    groups: dict[str, list[str]] = {}
    for e in sorted(read_allowlist()):
        groups.setdefault(e.split(":", 1)[0], []).append(e)
    return list(groups.values())


def _cross_pick(tmp_path: Path, a: set[str], b: set[str]) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ALLOWLIST.name).write_bytes(ALLOWLIST.read_bytes())
    _git(repo, "init", "-q", "-b", "base")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _room(repo, "a", a)
    _room(repo, "b", b)
    for onto, pick in (("a", "b"), ("b", "a")):
        _git(repo, "checkout", "-q", "-B", f"{onto}-{pick}", onto)
        _git(repo, "cherry-pick", pick)  # check=True: a conflict fails here
        f = repo / ALLOWLIST.name
        assert read_allowlist(f) == read_allowlist() - a - b
        assert spacing_violations(f.read_text()) == []


@pytest.mark.integration
@pytest.mark.parametrize("pair", range(len(_groups()) - 1))
def test_two_moves_of_neighbouring_modules_cherry_pick(tmp_path, pair):
    # #1816's usual rooms: each moves one whole module off the emitter.
    groups = _groups()
    _cross_pick(tmp_path, set(groups[pair]), set(groups[pair + 1]))


@pytest.mark.integration
def test_neighbouring_entries_across_a_module_boundary_cherry_pick(tmp_path):
    # Partial moves: the last entry of one module, the first of the next
    # (pairs of multi-entry groups when there are any, so neither delete
    # empties its group).
    groups = _groups()
    pairs = list(itertools.pairwise(groups))
    if not pairs:
        pytest.skip("one module's group is left: no module boundary to cross")
    g, h = next(((g, h) for g, h in pairs if len(g) > 1 and len(h) > 1), pairs[0])
    _cross_pick(tmp_path, {g[-1]}, {h[0]})


@pytest.mark.integration
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


@pytest.mark.integration
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
