"""The gate host's CPU calibration (AGAST #3897).

cost_meter's CPU-seconds aren't the same on every host: at ef9a7e2b the same
suite measured 1,454.5 CPU-s on toffee and 2,347 on omegalisk.  So
tools/cpu_calibrate.py times a small fixed workload at the start of the
ritz0 step, and check_test_budget.py divides the suite's CPU-s by the host's
factor: that workload's CPU-s here over its CPU-s on the reference host
(`[calibration] reference_cpu_s` in test_budget.toml).

These tests run in `make tools-unit`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import cpu_calibrate as cal


# --- how many copies run at once -----------------------------------------------
#
# The suite runs under `-n auto --maxprocesses 8`, and a core shared by two
# busy hyperthreads spends more CPU-s on the same work.  The workload runs as
# many copies at once as the suite has workers, so it pays the same contention.


@pytest.mark.unit
def test_jobs_follow_xdist_auto_capped_at_maxprocesses(monkeypatch):
    monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "3")
    assert cal.default_jobs() == 3
    monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "20")
    assert cal.default_jobs() == cal.MAX_PROCESSES == 8


@pytest.mark.unit
def test_jobs_without_the_override_use_the_cpu_count(monkeypatch):
    monkeypatch.delenv("PYTEST_XDIST_AUTO_NUM_WORKERS", raising=False)
    n = cal.default_jobs()
    assert 1 <= n <= cal.MAX_PROCESSES
    assert n <= (os.cpu_count() or 1)


# --- the workload ----------------------------------------------------------------


@pytest.mark.unit
def test_workload_is_fixed_and_independent_of_the_tree():
    """A workload made of ritz0 compiles would slow down with ritz0, and a
    2x slower compiler would leave the normalised suite figure where it was:
    the budget would stop seeing exactly what it exists to see.  So the
    workload uses nothing from the tree; only the host (CPU, kernel, Python,
    clang) moves it."""
    src = (TOOLS / "cpu_calibrate.py").read_text()
    for name in ("ritz0", "ritzlib", "build.py", "RITZ_PATH"):
        assert name not in src.split('"""', 2)[2], name
    assert isinstance(cal.PY_WORKLOAD, str)
    assert "define" in cal.reference_ir() and cal.reference_ir() == cal.reference_ir()


@pytest.mark.integration
def test_measure_counts_the_childrens_cpu_and_is_quick(tmp_path):
    t0 = time.monotonic()
    r = cal.measure(jobs=2, rounds=1, scratch=tmp_path)
    wall = time.monotonic() - t0
    # Every part of the workload runs in a child: the parent's own CPU is
    # bookkeeping.  A measurement that missed the children would read ~0.
    assert r["cpu_s"] > 0.2, r
    assert r["jobs"] == 2 and r["rounds"] == 1
    assert len(r["samples"]) == 1
    assert wall < 30, f"calibration took {wall:.1f} s wall; it must stay a few seconds"
    # Scratch is cleaned up: the gate runs this twice per gate.
    assert list(tmp_path.iterdir()) == []


@pytest.mark.integration
def test_cli_writes_the_report(tmp_path):
    out = tmp_path / "cal.json"
    r = subprocess.run([sys.executable, str(TOOLS / "cpu_calibrate.py"),
                        "--out", str(out), "--jobs", "1", "--rounds", "1"],
                       capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(out.read_text())
    assert d["cpu_s"] > 0 and d["jobs"] == 1
    assert "cpu calibration:" in r.stdout and f"{d['cpu_s']:.3f}" in r.stdout


@pytest.mark.unit
def test_median_of_rounds_ignores_one_outlier():
    assert cal.summarise([1.0, 1.1, 9.0]) == pytest.approx(1.1)
    assert cal.summarise([2.0]) == 2.0
