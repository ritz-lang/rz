"""The ritz0 suite's time budget, and its wiring into the gate (AGAST #3453).

LARB review/5 tooling F1: the ritz0 pytest suite went from 2,898 to 39,054
tests in three weeks and nothing stopped it.  Three pieces now do:

* `ritz0/cost_meter.py`, a pytest plugin the ritz0 conftest loads, measures
  every test's CPU-seconds (its process plus the children it reaps) and, with
  `--cost-report=PATH`, writes them summed per file.  CPU, not wall time:
  the gate's pytest step on one host ran anywhere from 223 to 752 s on the
  same tree depending on what else was running, and a wall-clock budget that
  noisy would be a flaky gate.
* `tools/check_test_budget.py` holds that report to `tools/test_budget.toml`:
  a per-file default, per-file overrides that each name the ticket paying
  them down, and a cap on the whole suite.
* main.yml's ritz0 step (and so every gate, which runs main.yml through
  ci-local) runs pytest with `--durations` and `--cost-report`, then the check.

These tests run in `make tools-unit`.  The end-to-end ones plant a slow test
file, watch the check go red on it, then green under a budget it fits.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
PKG = TOOLS.parent
RITZ0 = PKG / "ritz0"
REPO = PKG.parent.parent
MAIN_YML = REPO / ".github" / "workflows" / "main.yml"

sys.path.insert(0, str(TOOLS))

import check_test_budget as ctb


def report(files: dict[str, float], wall: float = 10.0) -> dict:
    """A cost report as cost_meter writes it: per-file CPU-seconds."""
    return {
        "wall_s": wall,
        "files": {
            f: {"tests": 1, "cpu_s": cpu, "wall_s": cpu} for f, cpu in files.items()
        },
    }


def budget(default=60.0, suite=1000.0, overrides=None) -> dict:
    return {
        "suite": {"cpu_s": suite},
        "file": {"default_cpu_s": default, "override": overrides or {}},
    }


# --- the check ---------------------------------------------------------------


@pytest.mark.unit
def test_file_under_the_default_passes():
    assert ctb.check(report({"test_a.py": 59.0}), budget()) == []


@pytest.mark.unit
def test_file_over_the_default_fails_naming_file_and_seconds():
    errs = ctb.check(report({"test_a.py": 61.5, "test_b.py": 1.0}), budget())
    assert len(errs) == 1
    assert "test_a.py" in errs[0]
    assert "61.5" in errs[0] and "60.0" in errs[0]


@pytest.mark.unit
def test_override_raises_one_files_limit_only():
    b = budget(overrides={"test_big.py": {"cpu_s": 200.0, "ticket": 3460}})
    assert ctb.check(report({"test_big.py": 150.0}), b) == []
    errs = ctb.check(report({"test_big.py": 150.0, "test_other.py": 150.0}), b)
    assert len(errs) == 1 and "test_other.py" in errs[0]
    errs = ctb.check(report({"test_big.py": 201.0}), b)
    assert len(errs) == 1 and "test_big.py" in errs[0] and "#3460" in errs[0]


@pytest.mark.unit
def test_override_must_name_a_ticket():
    b = budget(overrides={"test_big.py": {"cpu_s": 200.0}})
    errs = ctb.check(report({"test_big.py": 1.0}), b)
    assert len(errs) == 1 and "ticket" in errs[0]


@pytest.mark.unit
def test_override_for_a_file_not_in_the_report_is_rotted():
    """A renamed or deleted file must take its override with it."""
    b = budget(overrides={"test_gone.py": {"cpu_s": 200.0, "ticket": 3460}})
    errs = ctb.check(report({"test_a.py": 1.0}), b)
    assert len(errs) == 1 and "test_gone.py" in errs[0]


@pytest.mark.unit
def test_suite_over_its_cap_fails():
    errs = ctb.check(report({"test_a.py": 50.0, "test_b.py": 50.0}), budget(suite=90.0))
    assert len(errs) == 1
    assert "suite" in errs[0] and "100.0" in errs[0] and "90.0" in errs[0]


@pytest.mark.unit
def test_suite_over_its_test_count_cap_fails():
    """Count is what the controller pays per test (collection, dispatch,
    reporting), however cheap the test: 39k tests cost ~150 s of a 490 s
    step outside any test.  It is exact, so this cap is never flaky."""
    b = budget()
    b["suite"]["tests"] = 2
    r = report({"test_a.py": 1.0, "test_b.py": 1.0})
    assert ctb.check(r, b) == []
    r["files"]["test_b.py"]["tests"] = 2
    errs = ctb.check(r, b)
    assert len(errs) == 1 and "3 tests" in errs[0] and "cap of 2" in errs[0]
    # Not scaled: a slower machine runs the same number of tests.
    assert len(ctb.check(r, b, scale=10.0)) == 1


@pytest.mark.unit
def test_scale_multiplies_every_limit():
    b = budget(default=10.0, suite=25.0,
               overrides={"test_big.py": {"cpu_s": 20.0, "ticket": 1}})
    r = report({"test_a.py": 15.0, "test_big.py": 25.0})
    assert len(ctb.check(r, b)) == 3
    assert ctb.check(r, b, scale=2.0) == []


@pytest.mark.unit
def test_real_budget_file_loads_and_every_override_names_a_ticket():
    b = ctb.load_budget(ctb.DEFAULT_BUDGET)
    assert b["file"]["default_cpu_s"] > 0
    assert b["suite"]["cpu_s"] > 0
    assert b["suite"]["tests"] > 0
    for name, o in b["file"]["override"].items():
        assert int(o["ticket"]) > 0, name
        assert o["cpu_s"] > b["file"]["default_cpu_s"], (
            f"{name}: an override at or under the default does nothing; drop it")
        assert (RITZ0 / name).is_file(), f"{name}: override for a missing file"


# Collected by `pytest --collect-only -q` under ritz0 once #3517-#3521 had
# collapsed the eight matrix files (AGAST #3557, at 2c597655): 39,126 -> 29,700.
COLLECTED_AT_LAST_CAP = 29_700


@pytest.mark.unit
def test_real_test_cap_sits_just_above_the_collected_count():
    """The cap is the count plus #3453's ~5% headroom (41,000 over 39,126).
    A cap left far above the count lets the suite grow back unnoticed,
    and that growth is what the cap is meant to stop."""
    cap = ctb.load_budget(ctb.DEFAULT_BUDGET)["suite"]["tests"]
    assert COLLECTED_AT_LAST_CAP < cap <= COLLECTED_AT_LAST_CAP * 1.06, (
        f"[suite] tests = {cap}: set it to the collected count plus ~5%")


@pytest.mark.unit
def test_real_budget_goes_red_on_one_extra_test_file():
    """Under the real budget, a suite already at the cap plus one more test
    file fails, and the failure names the cap.  Without that file it passes."""
    b = ctb.load_budget(ctb.DEFAULT_BUDGET)
    cap = int(b["suite"]["tests"])
    r = report({"test_suite.py": 1.0})
    r["files"]["test_suite.py"]["tests"] = cap
    assert ctb.check(r, b) == []
    r["files"]["test_planted_extra.py"] = {"tests": 1, "cpu_s": 0.1, "wall_s": 0.1}
    errs = ctb.check(r, b)
    assert errs == [f"suite: {cap + 1} tests over its cap of {cap}; "
                    f"collapse a matrix into table rows before adding cases"]


# --- end to end: a planted slow file, red then green -------------------------

PLANTED = '''
import subprocess, sys, time

def _burn(seconds):
    end = time.process_time() + seconds
    while time.process_time() < end:
        pass

def test_slow_in_process():
    _burn(0.6)

def test_slow_in_a_child():
    # CPU spent by a child the test waits for is the test's cost too: that
    # is where a compile or a link spends it.
    subprocess.run([sys.executable, "-c",
        "import time\\nend=time.process_time()+0.6\\n"
        "while time.process_time()<end: pass"], check=True)
'''

FAST = '''
def test_fast():
    assert 1 + 1 == 2
'''


def _run_planted(tmp_path: Path, xdist: bool) -> dict:
    (tmp_path / "test_planted_slow.py").write_text(PLANTED)
    (tmp_path / "test_fast.py").write_text(FAST)
    out = tmp_path / "cost.json"
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--disable-plugin-autoload", "-p", "cost_meter",
           f"--cost-report={out}", "--rootdir", str(tmp_path), str(tmp_path)]
    if xdist:
        cmd[6:6] = ["-p", "xdist", "-n", "2"]
    env = {**os.environ, "PYTHONPATH": str(RITZ0)}
    r = subprocess.run(cmd, cwd=tmp_path, env=env, capture_output=True,
                       text=True, timeout=120, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    # The per-file summary is printed for the gate log, slowest first.
    assert "test files by CPU" in r.stdout
    assert r.stdout.index("test_planted_slow.py") < r.stdout.index("test_fast.py")
    return json.loads(out.read_text())


def _check(tmp_path: Path, rep: dict, default_cpu_s: float) -> subprocess.CompletedProcess:
    rep_path = tmp_path / "cost.json"
    rep_path.write_text(json.dumps(rep))
    b = tmp_path / "budget.toml"
    b.write_text(f"[suite]\ncpu_s = 100.0\n\n[file]\ndefault_cpu_s = {default_cpu_s}\n")
    return subprocess.run(
        [sys.executable, str(TOOLS / "check_test_budget.py"), str(rep_path),
         "--budget", str(b)],
        capture_output=True, text=True, timeout=60, check=False)


@pytest.mark.integration
@pytest.mark.parametrize("xdist", [False, True], ids=["serial", "xdist"])
def test_planted_slow_file_goes_red_then_green(tmp_path, xdist):
    rep = _run_planted(tmp_path, xdist)
    slow = rep["files"]["test_planted_slow.py"]
    assert slow["tests"] == 2
    # 1.2 s burned, half of it in a child: both halves are counted.
    assert slow["cpu_s"] >= 1.1, slow
    assert rep["files"]["test_fast.py"]["cpu_s"] < 0.5

    red = _check(tmp_path, rep, default_cpu_s=0.8)
    assert red.returncode == 1, red.stdout + red.stderr
    assert "test_planted_slow.py" in red.stdout
    assert "test_fast.py" not in red.stdout

    green = _check(tmp_path, rep, default_cpu_s=30.0)
    assert green.returncode == 0, green.stdout + green.stderr


# --- wiring ------------------------------------------------------------------


def _ritz0_step() -> str:
    text = MAIN_YML.read_text()
    start = text.index("- name: ritz0 unit tests")
    end = text.index("\n      - name:", start + 1)
    return text[start:end]


@pytest.mark.unit
def test_gate_pytest_step_publishes_durations_and_a_cost_report():
    step = _ritz0_step()
    line = next(ln for ln in step.splitlines() if "-m pytest" in ln)
    assert "--durations=" in line, "every gate log needs a --durations section"
    assert "--cost-report=" in line


@pytest.mark.unit
def test_gate_pytest_step_runs_the_budget_check_after_pytest():
    step = _ritz0_step()
    lines = step.splitlines()
    py = next(i for i, ln in enumerate(lines) if "-m pytest" in ln)
    chk = next(i for i, ln in enumerate(lines) if "check_test_budget.py" in ln)
    assert chk > py
    assert "set -o pipefail" in step  # a red pytest still stops the step


@pytest.mark.unit
def test_ritz0_conftest_loads_the_cost_meter():
    text = (RITZ0 / "conftest.py").read_text()
    assert '"cost_meter"' in text.split("pytest_plugins", 1)[1].splitlines()[0]
