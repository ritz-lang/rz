"""Every pytest the repo runs keeps only failed tests' tmp_path dirs (AGAST #4674).

On 2026-11-24 omegalisk's /tmp (an 8 GB tmpfs every room shares) filled:
each full ritz run left 1-2.5 GB of passing tests' `pytest-of-$USER/pytest-N`
trees and pytest keeps three runs.  `tmp_path_retention_policy = failed`
removes a test's tmp_path as soon as it passes, and the basetemp at session
end when every test passed, so a run leaves behind only what a failure needs.

Where it is set:
  * tools/ suite: tools/pytest.ini (already discovered for `pytest tools/...`).
  * ritz0 suite: `-o tmp_path_retention_policy=failed` on each command line.
    Not an ini in ritz0/: the suite deliberately has no pytest config (see
    tools/pytest.ini), and one there moves rootdir and node IDs for
    `pytest ritz0/tests/x.py` run from projects/ritz (`ritz0/tests/x.py::t`
    becomes `tests/x.py::t`), which the test-count and CPU caps key on.
"""

from __future__ import annotations

import configparser
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

RITZ = Path(__file__).resolve().parent.parent
REPO = RITZ.parent.parent
OPT = "tmp_path_retention_policy=failed"


def _pytest_lines(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text().splitlines()
            if re.search(r"-m pytest\b", ln) and not ln.lstrip().startswith("#")]


def _override(words: list[str]) -> list[str]:
    """The values of every `-o` in an argv."""
    return [b for a, b in zip(words, words[1:]) if a in ("-o", "--override-ini")]


@pytest.mark.unit
def test_makefile_ritz0_pytests_keep_only_failed_tmp_paths():
    lines = _pytest_lines(RITZ / "Makefile")
    ritz0 = [ln for ln in lines if re.search(r"\bcd ritz0\b", ln)]
    assert len(ritz0) >= 2, lines  # unit, tools-ratchets-ritz0
    for line in ritz0:
        assert OPT in _override(shlex.split(line.split("&&", 1)[1])), line
    # Every other pytest the Makefile runs is the tools/ suite, which reads
    # tools/pytest.ini (the next test).
    for line in set(lines) - set(ritz0):
        assert "tools/" in line or "TOOLS_" in line, line


@pytest.mark.unit
def test_tools_ini_keeps_only_failed_tmp_paths():
    ini = configparser.ConfigParser()
    ini.read(RITZ / "tools" / "pytest.ini")
    assert ini["pytest"].get("tmp_path_retention_policy") == "failed"


@pytest.mark.unit
def test_ci_pytest_keeps_only_failed_tmp_paths():
    lines = _pytest_lines(REPO / ".github" / "workflows" / "main.yml")
    assert lines, "main.yml runs no pytest?"
    for line in lines:
        assert OPT in _override(shlex.split(line.split("|", 1)[0])), line


@pytest.mark.unit
def test_smoke_pytest_keeps_only_failed_tmp_paths(monkeypatch):
    sys.path.insert(0, str(RITZ / "tools"))
    import smoke

    argvs = []
    monkeypatch.setattr(smoke, "_run", lambda cmd, **kw: argvs.append(cmd) or 0)
    smoke.pytest_smoke()
    assert len(argvs) == 1 and OPT in _override(argvs[0]), argvs


@pytest.mark.unit
def test_no_other_tools_script_starts_pytest_without_it():
    """A new script that starts pytest has to choose, not inherit pytest's default."""
    for path in sorted((RITZ / "tools").glob("*.py")):
        if path.name.startswith("test_") or path.name == "conftest.py":
            continue
        text = path.read_text()
        if re.search(r"""["']-m["']\s*,\s*["']pytest["']""", text):
            assert OPT in text, f"{path.name} starts pytest without -o {OPT}"


@pytest.mark.unit
def test_ritz0_has_no_pytest_config():
    """The ritz0 rootdir is ritz0/ only because nothing configures it."""
    for name in ("pytest.ini", ".pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg"):
        assert not (RITZ / "ritz0" / name).exists(), name
        assert not (RITZ / name).exists(), name


@pytest.mark.integration  # one nested pytest, ~0.5 s
def test_the_option_removes_passing_dirs_and_keeps_failing_ones(tmp_path):
    """The spelling the command lines use really does what it says.

    pytest only warns on an unknown `-o` key, so a typo would pass every
    check above and keep filling /tmp.
    """
    (tmp_path / "test_x.py").write_text(
        "def test_pass(tmp_path):\n    (tmp_path / 'f').write_text('x')\n\n"
        "def test_fail(tmp_path):\n    (tmp_path / 'f').write_text('x')\n    assert False\n")
    base = tmp_path / "base"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--disable-plugin-autoload", "-W", "error::pytest.PytestConfigWarning",
         "-o", OPT, f"--basetemp={base}", "test_x.py"],
        cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "1 failed, 1 passed" in proc.stdout, proc.stdout
    left = sorted(p.name for p in base.iterdir() if p.is_dir() and not p.is_symlink())
    assert left == ["test_fail0"], left
