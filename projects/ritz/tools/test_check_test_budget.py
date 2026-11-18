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

BUDGET_ENV = ("RITZ_TEST_BUDGET_SCALE", "RITZ_TEST_BUDGET_PARTIAL")


@pytest.fixture(autouse=True)
def _hermetic_budget_env(monkeypatch):
    """AGAST #4138: these tests assert on scale-1, whole-suite output, so a
    host's budget settings must not reach them.  `systemctl --user
    set-environment RITZ_TEST_BUDGET_SCALE=1.5` once put the scale in every
    gate unit's environment, and this file went red on huburght (`cap 135.0`
    where it wanted `cap 90.0`).  A test that wants a setting sets it."""
    for k in BUDGET_ENV:
        monkeypatch.delenv(k, raising=False)


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
# AGAST #3889 collapsed 18 more: 31,171 -> 26,329 (counted on 8eddf0d6).
# AGAST #4141 collapsed 7 more, 28,269 -> 24,431 (267f9e0b), under the same 27,700 cap.
COLLECTED_AT_LAST_CAP = 26_329


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


# --- AGAST #3897: CPU-s normalised by the host's calibration -------------------
#
# The same suite measured 1,454.5 CPU-s on toffee and 2,347 on omegalisk.
# tools/cpu_calibrate.py times a fixed workload on the gate host; its CPU-s
# over `[calibration] reference_cpu_s` is the host's factor, and every CPU
# figure is divided by it before it meets a cap.


def _cal(tmp_path: Path, cpu_s: float) -> Path:
    p = tmp_path / "cal.json"
    p.write_text(json.dumps({"cpu_s": cpu_s, "jobs": 4, "rounds": 3, "samples": [cpu_s]}))
    return p


@pytest.mark.unit
def test_factor_divides_the_suite_figure_before_the_cap():
    b = budget(default=1000.0, suite=1100.0)
    r = report({"test_a.py": 800.0, "test_b.py": 800.0})  # 1,600 raw
    assert len(ctb.check(r, b)) == 1
    assert ctb.check(r, b, factor=1.6) == []  # 1,000 normalised
    errs = ctb.check(r, b, factor=1.4)  # 1,142.9 normalised
    assert len(errs) == 1
    assert "1600.0 CPU-s raw" in errs[0] and "1142.9 normalised" in errs[0], errs


@pytest.mark.unit
def test_factor_divides_each_files_figure_before_its_cap():
    b = budget(default=90.0, suite=1e9,
               overrides={"test_big.py": {"cpu_s": 200.0, "ticket": 1}})
    r = report({"test_a.py": 100.0, "test_big.py": 240.0})
    assert len(ctb.check(r, b)) == 2
    assert ctb.check(r, b, factor=1.25) == []  # 80 and 192
    errs = ctb.check(r, b, partial=True, factor=1.05)  # 95.2 and 228.6
    assert len(errs) == 2 and "95.2" in errs[0] + errs[1]


@pytest.mark.unit
def test_factor_is_measured_over_the_budgets_reference(tmp_path):
    b = budget()
    b["calibration"] = {"reference_cpu_s": 2.0}
    assert ctb.host_factor(b, _cal(tmp_path, 3.2)) == pytest.approx(1.6)
    assert ctb.host_factor(b, None) == 1.0


@pytest.mark.unit
def test_a_missing_calibration_file_is_an_error_not_factor_one(tmp_path, capsys):
    """The gate passes --calibration; a calibration that did not run must not
    quietly grade the suite on the reference host's scale."""
    rep = tmp_path / "cost.json"
    rep.write_text(json.dumps(report({"test_a.py": 1.0})))
    b = tmp_path / "budget.toml"
    b.write_text("[calibration]\nreference_cpu_s = 2.0\n\n[suite]\ncpu_s = 90.0\n\n"
                 "[file]\ndefault_cpu_s = 60.0\n")
    assert ctb.main([str(rep), "--budget", str(b),
                     "--calibration", str(tmp_path / "absent.json")]) == 2
    assert "absent.json" in capsys.readouterr().out


@pytest.mark.unit
def test_budget_line_prints_raw_factor_and_normalised(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("RITZ_TEST_BUDGET_PARTIAL", raising=False)
    rep = tmp_path / "cost.json"
    rep.write_text(json.dumps(report({"test_a.py": 50.0, "test_b.py": 50.0})))
    b = tmp_path / "budget.toml"
    b.write_text("[calibration]\nreference_cpu_s = 2.0\n\n[suite]\ncpu_s = 90.0\n\n"
                 "[file]\ndefault_cpu_s = 60.0\n")
    cal = _cal(tmp_path, 2.5)  # factor 1.25: 100 raw -> 80 normalised
    assert ctb.main([str(rep), "--budget", str(b), "--calibration", str(cal)]) == 0
    out = capsys.readouterr().out
    assert "100.0 CPU-s raw" in out and "factor 1.250" in out and "80.0 normalised" in out
    assert "cap 90.0" in out
    # Uncalibrated, the same report is over the cap, and the line says so.
    assert ctb.main([str(rep), "--budget", str(b)]) == 1
    assert "uncalibrated" in capsys.readouterr().out


# --- AGAST #4172: a host's fixed factor --------------------------------------------
#
# cpu_calibrate.py --factor F (host.env's RZ_CPU_FACTOR) writes {"factor": F,
# "fixed": true} and times nothing; the check takes F as it stands.


def _fixed(tmp_path: Path, factor: float) -> Path:
    p = tmp_path / "fixed.json"
    p.write_text(json.dumps({"factor": factor, "fixed": True}))
    return p


@pytest.mark.unit
def test_fixed_factor_is_used_as_is_not_over_the_reference(tmp_path):
    b = budget()
    b["calibration"] = {"reference_cpu_s": 2.0}
    assert ctb.host_factor(b, _fixed(tmp_path, 1.67)) == pytest.approx(1.67)


@pytest.mark.unit
def test_budget_line_says_whether_the_factor_was_fixed_or_measured(tmp_path, capsys):
    """skronk's false red: 1,330.4 raw / 1.054 measured = 1,262.8 > 1,260.  At
    its fixed 1.67 the same report fits."""
    rep = tmp_path / "cost.json"
    rep.write_text(json.dumps(report({"test_a.py": 665.2, "test_b.py": 665.2})))
    b = tmp_path / "budget.toml"
    b.write_text("[calibration]\nreference_cpu_s = 2.0\n\n[suite]\ncpu_s = 1260.0\n\n"
                 "[file]\ndefault_cpu_s = 1000.0\n")
    assert ctb.main([str(rep), "--budget", str(b),
                     "--calibration", str(_cal(tmp_path, 2.108))]) == 1
    assert "factor 1.054 measured" in capsys.readouterr().out
    assert ctb.main([str(rep), "--budget", str(b),
                     "--calibration", str(_fixed(tmp_path, 1.67))]) == 0
    assert "factor 1.670 fixed" in capsys.readouterr().out


def _run_ritz0_step_factor_lines(tmp_path: Path, env: dict) -> dict[str, str]:
    """The ritz0 step's RZ_CPU_FACTOR handling, run as the step runs it, with
    `python` a stand-in.  Returns {"calibrate": its argv, "pytest": the
    RZ_CPU_FACTOR pytest would inherit}."""
    lines = [ln.strip() for ln in _ritz0_step().splitlines()]
    keep = [ln for ln in lines if not ln.startswith("#") and (
        "CPU_FACTOR" in ln or "-m pytest" in ln or "cpu_calibrate.py" in ln)]
    stub = ('python() { case "$*" in *"-m pytest"*) '
            'echo "${RZ_CPU_FACTOR-unset}" > "$OUT/pytest" ;; '
            '*cpu_calibrate.py*) echo "$*" > "$OUT/calibrate" ;; esac; }')
    base = {k: v for k, v in os.environ.items() if k != "RZ_CPU_FACTOR"}
    r = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", stub + "\n" + "\n".join(keep)],
                       cwd=tmp_path, env={**base, "OUT": str(tmp_path),
                                          "BASETEMP": str(tmp_path), **env},
                       capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode == 0, r.stderr
    return {n: (tmp_path / n).read_text().strip() for n in ("calibrate", "pytest")}


@pytest.mark.integration
def test_gate_cpu_factor_reaches_the_calibration_only(tmp_path):
    """AGAST #4172: run-gate.sh passes RZ_CPU_FACTOR in; the step hands it to
    cpu_calibrate.py as --factor and takes it out of pytest's environment.
    Without it the step calibrates live, as before."""
    seen = _run_ritz0_step_factor_lines(tmp_path, {"RZ_CPU_FACTOR": "1.67"})
    assert seen["calibrate"].endswith("--factor 1.67"), seen
    assert seen["pytest"] == "unset", seen
    seen = _run_ritz0_step_factor_lines(tmp_path, {})
    assert "--factor" not in seen["calibrate"], seen


@pytest.mark.unit
def test_real_budget_names_its_reference_workload_figure():
    b = ctb.load_budget(ctb.DEFAULT_BUDGET)
    assert b["calibration"]["reference_cpu_s"] > 0


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
def test_gate_pytest_step_calibrates_before_pytest_and_checks_with_it():
    """AGAST #3897: the factor is measured on this host, just before the suite,
    and the check reads the same file the calibration wrote."""
    lines = _ritz0_step().splitlines()
    cal = next(i for i, ln in enumerate(lines) if "cpu_calibrate.py" in ln)
    py = next(i for i, ln in enumerate(lines) if "-m pytest" in ln)
    chk = next(i for i, ln in enumerate(lines) if "check_test_budget.py" in ln)
    assert cal < py < chk
    out = lines[cal].split("--out", 1)[1].split()[0].lstrip("=")
    assert f"--calibration {out}" in lines[chk] or f"--calibration={out}" in lines[chk]


@pytest.mark.unit
def test_gate_pytest_step_puts_basetemp_on_disk_and_removes_it():
    """AGAST #3897: on toffee /tmp is tmpfs, and a /tmp full of tmp_path trees
    put the host under memory pressure that inflated per-file CPU-s 2-12x.
    The step makes a fresh directory under ~/.cache (a disk on every gate
    host and on CI), hands it to --basetemp, and removes it however pytest
    exits.  Fresh per run: two gates on one host must not share it."""
    step = _ritz0_step()
    lines = step.splitlines()
    py = next(ln for ln in lines if "-m pytest" in ln)
    assert '--basetemp="$BASETEMP"' in py
    mk = next(ln for ln in lines if ln.strip().startswith("BASETEMP="))
    assert "mktemp -d" in mk and "$HOME/.cache/" in mk and "/tmp" not in mk
    assert lines.index(mk) < lines.index(py)
    assert any("trap" in ln and 'rm -rf "$BASETEMP"' in ln and "EXIT" in ln
               for ln in lines[:lines.index(py)])


@pytest.mark.integration
def test_gate_basetemp_snippet_makes_a_fresh_dir_and_removes_it(tmp_path):
    """The step's BASETEMP/trap lines, run as the step runs them (bash -e):
    a directory that exists during the run and is gone after, even on failure."""
    lines = _ritz0_step().splitlines()
    snippet = "\n".join(ln.strip() for ln in lines
                        if ln.strip().startswith(("BASETEMP=", "mkdir -p", "trap ")))
    for tail, rc in (("exit 0", 0), ("false", 1)):
        seen = tmp_path / f"seen{rc}"
        script = f'{snippet}\necho "$BASETEMP" > {seen}\ntest -d "$BASETEMP"\n{tail}\n'
        r = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script],
                           env={**os.environ, "HOME": str(tmp_path)},
                           capture_output=True, text=True, timeout=30, check=False)
        assert r.returncode == rc, r.stderr
        made = Path(seen.read_text().strip())
        assert made.is_relative_to(tmp_path / ".cache")
        assert not made.exists()


@pytest.mark.unit
def test_ritz0_conftest_loads_the_cost_meter():
    text = (RITZ0 / "conftest.py").read_text()
    assert '"cost_meter"' in text.split("pytest_plugins", 1)[1].splitlines()[0]


# --- AGAST #3456: the gate splits the step in two ------------------------------
#
# ci_local.py runs the likely-failing files first (tools/likely_tests.py), then
# the full step with those files --ignore'd.  The first run is a subset: only
# its per-file caps mean anything (RITZ_TEST_BUDGET_PARTIAL).  The second run's
# report folds the first one's in (RITZ_COST_REPORT_INCLUDE), so the budget
# still sees the whole suite: the suite caps, and every override's file.


@pytest.mark.unit
def test_partial_report_skips_the_suite_wide_checks():
    b = budget(default=60.0, suite=90.0,
               overrides={"test_elsewhere.py": {"cpu_s": 200.0, "ticket": 3460}})
    b["suite"]["tests"] = 1
    r = report({"test_a.py": 50.0, "test_b.py": 50.0})
    assert len(ctb.check(r, b)) == 3  # suite cpu, suite tests, missing override
    assert ctb.check(r, b, partial=True) == []


@pytest.mark.unit
def test_partial_report_still_holds_each_file_to_its_cap():
    b = budget(default=60.0,
               overrides={"test_big.py": {"cpu_s": 200.0}})  # no ticket
    r = report({"test_a.py": 61.0, "test_big.py": 1.0})
    errs = ctb.check(r, b, partial=True)
    assert len(errs) == 2
    assert any("test_a.py" in e for e in errs)
    assert any("ticket" in e for e in errs)


@pytest.mark.unit
def test_partial_is_read_from_the_environment(tmp_path, monkeypatch, capsys):
    rep = tmp_path / "cost.json"
    rep.write_text(json.dumps(report({"test_a.py": 50.0, "test_b.py": 50.0})))
    b = tmp_path / "budget.toml"
    b.write_text("[suite]\ncpu_s = 90.0\n\n[file]\ndefault_cpu_s = 60.0\n")
    monkeypatch.delenv("RITZ_TEST_BUDGET_PARTIAL", raising=False)
    assert ctb.main([str(rep), "--budget", str(b)]) == 1
    monkeypatch.setenv("RITZ_TEST_BUDGET_PARTIAL", "1")
    assert ctb.main([str(rep), "--budget", str(b)]) == 0
    assert "partial" in capsys.readouterr().out


@pytest.mark.unit
def test_scale_is_read_from_the_environment(tmp_path, monkeypatch, capsys):
    """RITZ_TEST_BUDGET_SCALE multiplies the caps main() checks and prints."""
    rep = tmp_path / "cost.json"
    rep.write_text(json.dumps(report({"test_a.py": 50.0, "test_b.py": 50.0})))
    b = tmp_path / "budget.toml"
    b.write_text("[suite]\ncpu_s = 90.0\n\n[file]\ndefault_cpu_s = 60.0\n")
    assert ctb.main([str(rep), "--budget", str(b)]) == 1  # 100 > 90
    assert "cap 90.0" in capsys.readouterr().out
    monkeypatch.setenv("RITZ_TEST_BUDGET_SCALE", "1.5")
    assert ctb.main([str(rep), "--budget", str(b)]) == 0  # 100 <= 135
    out = capsys.readouterr().out
    assert "cap 135.0" in out and "scale 1.5" in out


@pytest.mark.integration
def test_this_file_passes_with_a_host_budget_in_the_environment(tmp_path):
    """AGAST #4138, end to end: the two tests that went red on huburght, run
    in a pytest whose environment carries a host's scale and the partial flag."""
    ids = [f"{__file__}::test_budget_line_prints_raw_factor_and_normalised",
           f"{__file__}::test_partial_is_read_from_the_environment"]
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--rootdir", str(PKG), *ids],
        cwd=PKG, capture_output=True, text=True, timeout=120, check=False,
        env={**os.environ, "RITZ_TEST_BUDGET_SCALE": "1.5",
             "RITZ_TEST_BUDGET_PARTIAL": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "2 passed" in r.stdout


def _run_ritz0_step_scale_lines(tmp_path: Path, env: dict) -> dict[str, dict]:
    """The ritz0 step's scale handling, run as the step runs it, with `python`
    a stand-in that records the environment each command would see.  Returns
    {"pytest": env, "budget": env}."""
    lines = [ln.strip() for ln in _ritz0_step().splitlines()]
    keep = [ln for ln in lines if not ln.startswith("#") and (
        "BUDGET_SCALE" in ln or "-m pytest" in ln or "check_test_budget.py" in ln)]
    stub = ('python() { case "$*" in *"-m pytest"*) n=pytest ;; '
            '*check_test_budget.py*) n=budget ;; *) n=other ;; esac; '
            'env > "$OUT/$n.env"; }')
    script = stub + "\n" + "\n".join(keep) + "\n"
    base = {k: v for k, v in os.environ.items()
            if k not in ("RZ_TEST_BUDGET_SCALE", *BUDGET_ENV)}
    r = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", script], cwd=tmp_path,
                       env={**base, "OUT": str(tmp_path), **env},
                       capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode == 0, r.stderr
    seen = {}
    for n in ("pytest", "budget"):
        pairs = (ln.split("=", 1) for ln in (tmp_path / f"{n}.env").read_text().splitlines()
                 if "=" in ln)
        seen[n] = {k: v for k, v in pairs if "TEST_BUDGET" in k}
    return seen


@pytest.mark.integration
@pytest.mark.parametrize("env, scale", [
    ({}, "1"),                                          # CI, most hosts
    ({"RZ_TEST_BUDGET_SCALE": "1.5"}, "1.5"),           # host.env via run-gate.sh
    ({"RITZ_TEST_BUDGET_SCALE": "1.5"}, "1.5"),         # set-environment, as #4004 did
    ({"RZ_TEST_BUDGET_SCALE": "2", "RITZ_TEST_BUDGET_SCALE": "1.5"}, "2"),
])
def test_gate_budget_scale_reaches_the_budget_check_only(tmp_path, env, scale):
    """AGAST #4138: a host's scale applies to the budget line, never to pytest,
    whose tests assert on scale-1 output."""
    seen = _run_ritz0_step_scale_lines(tmp_path, env)
    assert seen["pytest"] == {}, seen
    assert seen["budget"] == {"RITZ_TEST_BUDGET_SCALE": scale}, seen


def _session(tmp_path: Path, files: list[str], out: Path, env: dict) -> None:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
           "--disable-plugin-autoload", "-p", "cost_meter",
           f"--cost-report={out}", "--rootdir", str(tmp_path),
           *[str(tmp_path / f) for f in files]]
    r = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, timeout=120,
                       env={**os.environ, "PYTHONPATH": str(RITZ0), **env}, check=False)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.integration
def test_included_report_is_folded_into_this_sessions_report(tmp_path):
    (tmp_path / "test_planted_slow.py").write_text(PLANTED)
    (tmp_path / "test_fast.py").write_text(FAST)
    first, second = tmp_path / "first.json", tmp_path / "second.json"
    _session(tmp_path, ["test_planted_slow.py"], first, {})
    _session(tmp_path, ["test_fast.py"], second,
             {"RITZ_COST_REPORT_INCLUDE": str(first)})
    a, b = json.loads(first.read_text()), json.loads(second.read_text())
    assert sorted(b["files"]) == ["test_fast.py", "test_planted_slow.py"]
    assert b["files"]["test_planted_slow.py"] == a["files"]["test_planted_slow.py"]
    assert b["cpu_s"] == pytest.approx(sum(v["cpu_s"] for v in b["files"].values()))
    # A missing include is ignored: that file's run did not happen.
    _session(tmp_path, ["test_fast.py"], second,
             {"RITZ_COST_REPORT_INCLUDE": str(tmp_path / "absent.json")})
    assert sorted(json.loads(second.read_text())["files"]) == ["test_fast.py"]
