"""The ritz0 suite's test-count cap, checked before a gate (AGAST #4904).

`[suite] tests` in tools/test_budget.toml was only checked after the full
ritz0 suite, by check_test_budget.py on the gate's cost report.  On
2026-11-27 #4899 (26,817) and #4885 (26,806) each turned a train red after a
~25 min gate on that count alone.  The count is exact and needs no run:
tools/check_suite_count.py collects the suite (`pytest --collect-only`, the
gate's own selection, ~10-20 s) and fails with check_test_budget's own line.
`make suite-count` runs it, and `make train-precheck` (train.sh precheck)
runs that beside tools-ratchets.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
PKG = TOOLS.parent
SCRIPT = TOOLS / "check_suite_count.py"

sys.path.insert(0, str(TOOLS))

import check_suite_count as csc
import check_test_budget as ctb


@pytest.mark.unit
@pytest.mark.parametrize(
    "tail, want",
    [
        ("26800 tests collected in 7.64s", 26800),
        ("1 test collected in 0.01s", 1),
        ("========== 3 tests collected in 0.02s ==========", 3),
    ],
)
def test_count_is_read_from_pytests_summary(tail, want):
    assert csc.parse_count(f"a.py::t\n\n{tail}\n") == want


@pytest.mark.unit
def test_no_summary_is_no_count():
    assert csc.parse_count("nothing here\n") is None


@pytest.mark.unit
def test_count_breach_is_the_budget_checks_own_line():
    b = {"suite": {"tests": 2}}
    assert ctb.count_breach(2, b) is None
    assert ctb.count_breach(3, b) == (
        "suite: 3 tests over its cap of 2; "
        "collapse a matrix into table rows before adding cases"
    )
    assert ctb.count_breach(10**6, {"suite": {}}) is None


def _tree(tmp_path: Path, tests: int, cap: int) -> tuple[Path, Path]:
    """A scratch ritz0 dir with `tests` tests, and a budget capping at `cap`."""
    suite = tmp_path / "ritz0"
    suite.mkdir()
    (suite / "test_x.py").write_text(
        "import pytest\n\n"
        f"@pytest.mark.parametrize('i', range({tests}))\n"
        "def test_x(i):\n    pass\n"
    )
    budget = tmp_path / "budget.toml"
    budget.write_text(
        f"[suite]\ncpu_s = 1.0\ntests = {cap}\n[file]\ndefault_cpu_s = 1.0\n"
    )
    return suite, budget


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.integration
def test_at_cap_passes_and_cap_plus_one_fails_with_the_cap_message(tmp_path):
    """The DONE WHEN of #4904: a suite at cap+1 fails, with the cap line."""
    suite, budget = _tree(tmp_path, tests=5, cap=5)
    ok = _run("--ritz0", str(suite), "--budget", str(budget))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert re.search(
        r"suite count: ok, 5 tests \(cap 5\), collected in [0-9.]+ s", ok.stdout
    ), ok.stdout

    budget.write_text(budget.read_text().replace("tests = 5", "tests = 4"))
    red = _run("--ritz0", str(suite), "--budget", str(budget))
    assert red.returncode == 1, red.stdout + red.stderr
    assert "suite: 5 tests over its cap of 4; collapse a matrix" in red.stdout, (
        red.stdout
    )


@pytest.mark.integration
def test_a_collection_error_is_an_error_not_a_count(tmp_path):
    """A file that fails to import hides its tests: the count would read low."""
    suite, budget = _tree(tmp_path, tests=2, cap=5)
    (suite / "test_broken.py").write_text("import no_such_module_4904\n")
    r = _run("--ritz0", str(suite), "--budget", str(budget))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "suite count: collection failed" in r.stdout, r.stdout


@pytest.mark.unit
def test_collection_uses_the_gates_selection():
    """The gate's ritz0 step (main.yml) loads no autoloaded plugin and names
    no path or marker: the count must be of that same set."""
    words = csc.collect_argv()
    assert words[:2] == ["-m", "pytest"], words
    words = words[2:]  # pytest's own arguments
    assert "--collect-only" in words and "--disable-plugin-autoload" in words, words
    assert not any(w == "-m" or w == "-k" or w.endswith(".py") for w in words), words


def _make_n(target: str) -> str:
    return subprocess.run(
        ["make", "-n", "-s", target],
        cwd=PKG,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout


@pytest.mark.integration
def test_train_precheck_runs_the_ratchets_and_the_count():
    """`make train-precheck` is tools-ratchets plus suite-count: every pytest
    tools-ratchets runs, and the count check."""
    pre = _make_n("train-precheck")
    for ln in _make_n("tools-ratchets").splitlines():
        if "-m pytest" in ln:
            assert ln in pre, f"train-precheck misses: {ln}"
    assert "tools/check_suite_count.py" in pre, pre


@pytest.mark.integration
def test_train_sh_precheck_runs_make_train_precheck():
    train = (PKG.parent.parent / ".claude/skills/rz-iterate/train.sh").read_text()
    assert "RZ_PRECHECK_CMD:-make -C projects/ritz train-precheck}" in train
