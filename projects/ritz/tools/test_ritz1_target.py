"""Regression tests for AGAST #1485: `make ritz1` must not be a gate that cannot fail.

History: `make ritz1` ran `build.py ritz1-tests`, which iterated a hardcoded
RITZ1_TESTS list of 15 files that had all moved to docs/archive/ritz1_old/test/.
Every entry printed "not found, skipping", the command reported
"0 passed, 0 failed" and exited 0 -- and `make test` depended on it.

Decision (recorded in AGAST #1485): the archived tests exercise a ritz1 that no
longer exists (mem.ritz, utf8.ritz, tokens.ritz, grammar_builder.ritz ... are
not in ritz1/src), so the command and its list are deleted rather than
repointed. The `ritz1` make target is kept but now builds the ritz1 compiler,
which does real work and can fail. It cannot simply be removed: `ritz1/` is a
directory, so an undefined `ritz1` target would resolve to it and make would
exit 0 with "Nothing to be done" -- the same vacuous-success trap as #1402.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
BUILD_PY = RITZ_ROOT / "build.py"
MAKEFILE = RITZ_ROOT / "Makefile"


def _make_dry_run(target: str) -> subprocess.CompletedProcess:
    """`make -n <target>`: print the recipe without executing it."""
    return subprocess.run(
        ["make", "-n", "-C", str(RITZ_ROOT), target],
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.unit
def test_build_py_has_no_ritz1_tests_command():
    """The skip-everything command is gone; invoking it is an argparse error."""
    result = subprocess.run(
        [sys.executable, str(BUILD_PY), "ritz1-tests"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=RITZ_ROOT,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "invalid choice" in result.stderr


@pytest.mark.unit
def test_build_py_has_no_stale_ritz1_test_list():
    """No hardcoded list of ritz1 test files that can silently go missing."""
    source = BUILD_PY.read_text()
    assert "RITZ1_TESTS" not in source
    assert "not found, skipping" not in source


@pytest.mark.unit
def test_make_ritz1_builds_the_compiler():
    """`make ritz1` delegates to ritz1/Makefile's build, a step that can fail."""
    result = _make_dry_run("ritz1")
    out = result.stdout + result.stderr
    assert result.returncode == 0, out
    assert "Nothing to be done" not in out
    assert "ritz1-tests" not in out
    assert re.search(r"make\S*\s+-C\s+ritz1\s+ritz1\b", out), out


@pytest.mark.unit
def test_make_ritz1_is_phony():
    """Must stay .PHONY so the ritz1/ directory can never satisfy the target."""
    phony_lines = [l for l in MAKEFILE.read_text().splitlines() if l.startswith(".PHONY:")]
    assert any(re.search(r"(^|\s)ritz1(\s|$)", l.split(":", 1)[1]) for l in phony_lines)
