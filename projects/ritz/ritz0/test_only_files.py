"""Tests for only_files, the gate pre-pass's file selection (AGAST #3623).

ci_local's likely-first pre-pass ran ~60 ritz0 test files given as pytest
file ARGUMENTS.  pytest walks a file argument's directory again for every
argument (Session.collect never dedupes a file argument's parent), so 60
arguments over ritz0/'s ~570 modules built ~34,000 Module nodes: 8.7 s of
collection on every xdist worker for 0.3 s of real modules.  `--only-file`
selects the same files from one walk.

One nested pytest per case, plugin autoload off, the plugin loaded by name
as ritz0/conftest.py loads it.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ0_DIR = Path(__file__).resolve().parent

# Counts every module pytest builds a collector for: the cost the plugin cuts.
COUNTING_CONFTEST = """
    MADE = []
    def pytest_pycollect_makemodule(module_path, parent):
        MADE.append(module_path.name)
    def pytest_collection_finish(session):
        print("MODULES", " ".join(sorted(MADE)))
"""


def _tree(root: Path, n_unlisted: int = 6) -> None:
    (root / "conftest.py").write_text(textwrap.dedent(COUNTING_CONFTEST))
    for name in ("test_a.py", "test_b.py", "sub/test_c.py",
                 *(f"test_x{i}.py" for i in range(n_unlisted))):
        (root / name).parent.mkdir(exist_ok=True)
        (root / name).write_text(f"def test_{Path(name).stem}():\n    pass\n")
    # A directory with no listed file is never entered: its conftest would
    # fail the session if it were imported.
    (root / "other").mkdir()
    (root / "other" / "conftest.py").write_text("raise SystemExit('other/ was walked')\n")
    (root / "other" / "test_o.py").write_text("def test_o():\n    pass\n")


def _pytest(root: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(RITZ0_DIR)}
    env.pop("PYTEST_ADDOPTS", None)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--disable-plugin-autoload", "-p", "only_files", "--rootdir", str(root),
         *args],
        cwd=root, env=env, capture_output=True, text=True, timeout=120, check=False)


def test_only_the_listed_files_are_collected_once_in_the_listed_order(tmp_path):
    _tree(tmp_path)
    r = _pytest(tmp_path, "--collect-only", "--only-file=sub/test_c.py",
                "--only-file=test_b.py", "--only-file=test_a.py")
    assert r.returncode == 0, r.stdout + r.stderr
    ids = [ln for ln in r.stdout.splitlines() if "::" in ln]
    # The listed order, not the directory's: ci_local lists the costly first.
    assert ids == ["sub/test_c.py::test_test_c", "test_b.py::test_test_b",
                   "test_a.py::test_test_a"], r.stdout
    # One collector per listed module; the six unlisted ones get none.
    assert "MODULES test_a.py test_b.py test_c.py\n" in r.stdout, r.stdout


def test_without_the_option_everything_is_collected(tmp_path):
    _tree(tmp_path, n_unlisted=1)
    (tmp_path / "other" / "conftest.py").write_text("")
    r = _pytest(tmp_path, "--collect-only")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "5 tests collected" in r.stdout, r.stdout


def test_a_listed_file_that_does_not_exist_is_a_usage_error(tmp_path):
    """As a missing file argument was: the pre-pass must not go green on
    a selection that silently ran nothing."""
    _tree(tmp_path)
    r = _pytest(tmp_path, "--collect-only", "--only-file=test_a.py",
                "--only-file=test_gone.py")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "test_gone.py" in r.stderr
