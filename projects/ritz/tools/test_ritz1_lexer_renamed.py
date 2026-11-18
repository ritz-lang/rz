"""ritz1's lexer is `lexer.ritz`, not `lexer_nfa.ritz` (AGAST #3887).

#1821 replaced the NFA with a direct-coded scanner but kept the module name
so the diff stayed reviewable. #3887 renamed it. These tests fail if the old
name comes back in a live file. Historical records (LARB reviews,
docs/archive, the pre-#1821 lexer profile, ticket scrubs, the legacy ritzgen
example) keep it on purpose and are not scanned.
"""

import subprocess
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_DIR.parents[1]
RITZ1 = PKG_DIR / "ritz1"

# Live files that named the module before the rename: the importers, the
# build, the generator, and the docs that describe the current layout.
LIVE_PATHSPECS = (
    ".github",
    "projects/ritz/ritz0",
    "projects/ritz/ritz1",
    "projects/ritz/tools",
    "projects/ritz/grammars",
    "projects/ritz/docs/PARSER_ARCHITECTURE.md",
    "projects/ritz/docs/TESTING.md",
    ":!projects/ritz/tools/test_ritz1_lexer_renamed.py",
)


@pytest.mark.unit
def test_lexer_module_has_its_new_name():
    assert (RITZ1 / "src" / "lexer.ritz").is_file()
    assert not (RITZ1 / "src" / "lexer_nfa.ritz").exists()


@pytest.mark.unit
def test_lexer_unit_test_has_its_new_name():
    assert (RITZ1 / "test" / "test_lexer.ritz").is_file()
    assert not (RITZ1 / "test" / "test_lexer_nfa.ritz").exists()


@pytest.mark.unit
def test_makefile_builds_lexer():
    sources = (RITZ1 / "Makefile").read_text()
    assert "\tlexer \\" in sources
    assert "lexer_nfa" not in sources


# integration: it spawns `git grep`, and ritz0's spawn guard (AGAST #1805)
# fails an unmarked test that starts a process whenever ritz0's conftest is
# loaded in the same session.
@pytest.mark.integration
def test_no_live_file_names_lexer_nfa():
    hits = subprocess.run(
        ["git", "grep", "-n", "lexer_nfa", "--", *LIVE_PATHSPECS],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    # git grep: 0 = matches, 1 = none, anything else = git itself failed.
    assert hits.returncode in (0, 1), hits.stderr
    assert hits.returncode == 1, hits.stdout
