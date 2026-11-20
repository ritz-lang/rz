"""AGAST #3462 / #1816 (LARB review/5 ritz1 N1): no checks on `EmitterState`.

ritz1 ran every semantic check during code generation: each one was a
`pub fn *check*(s: *EmitterState, ...)` that the emitter called mid-lowering.
From #3462 on, a new check goes into the `Sema` pass (ritz1/src/sema*.ritz),
which runs over the AST between infer_generic_calls / monomorphisation and
emit_module.  See "Where a new check goes" in ritz1/ARCHITECTURE.md.

Every such check has now moved off the emitter (#1816), so the freeze is
simply that the grep

    pub fn <name with "check">(s: *EmitterState

matches nothing in ritz1/src.  The allowlist that used to hold the matches
still to move (`tools/ritz1_emitter_checks.allow`) is deleted: a match is now
a moved check put back or a new one written on the emitter, and the
allowlist's reappearance fails the same way.

The second half of this file freezes #3513 (LARB F5): Sema and the checks
import no emitter module.
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


def violations(hits: set[str]) -> list[str]:
    """A message per match; empty when the freeze holds."""
    return [f"emitter-side check {h}: put it on Sema (ritz1/ARCHITECTURE.md "
            f"'Where a new check goes'), not on EmitterState"
            for h in sorted(hits)]


@pytest.mark.integration
def test_no_emitter_state_checks():
    problems = violations(grep_hits())
    assert not problems, "\n".join(problems)


@pytest.mark.unit
def test_the_allowlist_is_gone():
    # #1816 is closed: the freeze is the grep being empty, not a shrinking
    # list.  Bringing the list back would let a check sit on the emitter
    # again without the grep noticing.
    assert not ALLOWLIST.exists(), (
        f"{ALLOWLIST.name} is back: the freeze is the grep being empty now")


@pytest.mark.unit
def test_a_planted_check_is_refused():
    planted = "foo.ritz:12:pub fn foo_check(s: *EmitterState, e: *Expr)\n"
    assert violations(parse_hits(planted)) == [violations({"foo.ritz:foo_check"})[0]]
    assert violations(parse_hits("")) == []


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


# ---------------------------------------------------------------------------
# AGAST #3513 (LARB F5): Sema and the checks import no emitter module.
#
# A sema*.ritz module, and ast_query (the pure AST queries Sema shares with
# the emitter), may never import an emitter* module.  A module in
# ARCHITECTURE.md's **Checks** list may only if ritz1_check_emitter_imports.allow
# names it (the EmitterState checks still to move); that list only shrinks.
# Imports are read as ritz1_arch.scan reads them (`import X` and `pub import X`).
# ---------------------------------------------------------------------------

import ritz1_arch  # noqa: E402

IMPORT_ALLOWLIST = TOOLS / "ritz1_check_emitter_imports.allow"
ARCH_DOC = RITZ / "ritz1" / "ARCHITECTURE.md"
NEVER = ("ast_query",)


def _is_emitter(mod: str) -> bool:
    return mod.startswith("emitter")


def _is_sema(mod: str) -> bool:
    return mod.startswith("sema")


def read_import_allowlist(path: Path = IMPORT_ALLOWLIST) -> set[str]:
    return {ln.split("#", 1)[0].strip() for ln in path.read_text().splitlines()} - {""}


def import_violations(imports: dict[str, list[str]], checks: list[str],
                      allowed: set[str]) -> list[str]:
    """One message per sema / check module importing an emitter* module
    that it may not, and per allowlist entry that is stale."""
    out = []
    for mod in sorted(imports):
        bad = [i for i in imports[mod] if _is_emitter(i)]
        if not bad:
            continue
        names = ", ".join(bad)
        if _is_sema(mod) or mod in NEVER:
            out.append(f"{mod}.ritz imports {names}: Sema imports no emitter "
                       f"module (#3513); move the helper to ast_query")
        elif mod in checks and mod not in allowed:
            out.append(f"check module {mod}.ritz imports {names}: a check "
                       f"runs on Sema and imports no emitter module (#3513)")
    for mod in sorted(allowed):
        if _is_sema(mod) or mod in NEVER:
            out.append(f"{IMPORT_ALLOWLIST.name} lists {mod}, which may never "
                       f"import an emitter module")
        elif not any(_is_emitter(i) for i in imports.get(mod, [])):
            out.append(f"{mod} no longer imports an emitter module: delete it "
                       f"from {IMPORT_ALLOWLIST.name} (the list only shrinks)")
    return out


def _tree_imports() -> dict[str, list[str]]:
    return {m.name: m.imports for m in ritz1_arch.scan(SRC).values()}


def _checks() -> list[str]:
    return ritz1_arch.doc_entries(ARCH_DOC.read_text())[1]


@pytest.mark.integration
def test_sema_and_checks_import_no_emitter_module():
    problems = import_violations(_tree_imports(), _checks(),
                                 read_import_allowlist())
    assert not problems, "\n".join(problems)


@pytest.mark.integration
def test_sema_modules_exist_and_are_scanned():
    # The rule must bite something: Sema's own modules are in the scan.
    imports = _tree_imports()
    assert {"sema", "sema_type", "sema_walk", "ast_query"} <= set(imports)
    assert "ast_query" in imports["sema"]


@pytest.mark.unit
def test_a_sema_module_importing_the_emitter_is_refused():
    imports = {"sema_x": ["ast", "emitter_core"]}
    assert len(import_violations(imports, [], set())) == 1
    # Not even the allowlist lets it: both the import and the entry fail.
    assert len(import_violations(imports, [], {"sema_x"})) == 2
    assert len(import_violations({"ast_query": ["emitter_expr"]}, [], set())) == 1


@pytest.mark.unit
def test_a_check_module_importing_the_emitter_needs_an_entry():
    imports = {"foo_check": ["emitter_core"], "other": ["emitter_core"]}
    assert len(import_violations(imports, ["foo_check"], set())) == 1
    assert import_violations(imports, ["foo_check"], {"foo_check"}) == []
    # A module outside the Checks list (the emitter's own helpers) is free.
    assert import_violations({"other": ["emitter_core"]}, [], set()) == []


@pytest.mark.unit
def test_a_stale_import_entry_is_refused():
    assert len(import_violations({"foo_check": ["ast_query"]}, ["foo_check"],
                                 {"foo_check"})) == 1


@pytest.mark.unit
def test_import_allowlist_separates_entries():
    # One module per entry, a blank line between (as #3903's rule above).
    entries = [ln for ln in IMPORT_ALLOWLIST.read_text().splitlines()
               if ln.strip() and not ln.startswith("#")]
    assert entries == sorted(entries)
    text = IMPORT_ALLOWLIST.read_text()
    for a, b in itertools.pairwise(entries):
        assert f"{a}\n{b}\n" not in text + "\n", f"{a} and {b} touch"
