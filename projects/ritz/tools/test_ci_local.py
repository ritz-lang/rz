#!/usr/bin/env python3
"""Self-tests for ci_local.py — AGAST #1363.

The point of ci_local.py is that it cannot drift from CI, because it parses
main.yml rather than restating it. These tests hold it to that:

  * every `run:` step in the workflow is enumerated — a runner that silently
    drops a step is a green tick asserting less than you think, which is the
    exact failure this tool exists to prevent
  * `working-directory` is honoured even when declared AFTER the `run:` block,
    which is the layout that made a `grep -A 6` produce a confident wrong
    claim about what CI executes (#1363's own retraction)
  * setup steps are reported when skipped, never silently omitted
  * the real main.yml parses and yields the jobs we expect

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_local.py -q
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ci_local  # noqa: E402


# --------------------------------------------------------------------------
# Against the real workflow
# --------------------------------------------------------------------------

def test_real_workflow_exists():
    assert ci_local.WORKFLOW.is_file(), (
        f"workflow not found at {ci_local.WORKFLOW}; REPO_ROOT resolution is wrong"
    )


def test_every_run_step_is_enumerated():
    """No step may be dropped between the YAML and the runner."""
    spec = yaml.safe_load(ci_local.WORKFLOW.read_text())
    expected = sum(
        1
        for jobspec in spec["jobs"].values()
        for s in (jobspec.get("steps") or [])
        if "run" in s
    )
    assert len(ci_local.load_steps()) == expected


def test_no_uses_only_step_is_enumerated():
    """Checkout/setup-python have no shell command and must not be run."""
    for s in ci_local.load_steps():
        assert s.run, f"{s} has an empty command"


def test_pytest_step_carries_its_working_directory():
    """The specific fact a grep got wrong: this step is NOT run from the root."""
    steps = [s for s in ci_local.load_steps() if "unit tests" in s.name.lower()
             and "ritz0" in s.name.lower()]
    assert steps, "could not find the ritz0 unit tests step"
    assert steps[0].workdir == "projects/ritz/ritz0", (
        f"expected projects/ritz/ritz0, got {steps[0].workdir!r}"
    )


def test_default_job_is_declared_by_the_workflow():
    assert ci_local.DEFAULT_JOB in ci_local.jobs_in(ci_local.load_steps())


# --------------------------------------------------------------------------
# Against a synthetic workflow, so these can actually go red
# --------------------------------------------------------------------------

WORKDIR_AFTER_RUN = """\
jobs:
  alpha:
    steps:
      - uses: actions/checkout@v4
      - name: Install toolchain
        run: echo installing
      - name: Real gate
        run: echo gating
        working-directory: projects/ritz/ritz0
  beta:
    steps:
      - name: Beta step
        run: echo beta
"""


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    wf = tmp_path / "main.yml"
    wf.write_text(WORKDIR_AFTER_RUN)
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    return wf


def test_working_directory_declared_after_run_is_picked_up(synthetic):
    steps = ci_local.load_steps(synthetic)
    gate = next(s for s in steps if s.name == "Real gate")
    assert gate.workdir == "projects/ritz/ritz0"


def test_uses_step_is_excluded(synthetic):
    names = [s.name for s in ci_local.load_steps(synthetic)]
    assert names == ["Install toolchain", "Real gate", "Beta step"]


def test_setup_steps_are_identified(synthetic):
    steps = ci_local.load_steps(synthetic)
    assert [s.is_setup for s in steps] == [True, False, False]


def test_jobs_are_reported_in_declaration_order(synthetic):
    assert ci_local.jobs_in(ci_local.load_steps(synthetic)) == ["alpha", "beta"]


def test_skipped_setup_steps_are_printed_not_silent(synthetic, capsys, monkeypatch):
    monkeypatch.setattr(ci_local, "REPO_ROOT", Path("/"))
    ci_local.main(["--job", "alpha", "--dry-run"])
    out = capsys.readouterr().out
    assert "Install toolchain" in out, "a skipped step was omitted silently"
    assert "skipped" in out.lower()


def test_unknown_job_is_an_error(synthetic, capsys):
    assert ci_local.main(["--job", "nope"]) == 2
    assert "unknown job" in capsys.readouterr().err


def test_list_prints_every_step(synthetic, capsys):
    assert ci_local.main(["--list"]) == 0
    out = capsys.readouterr().out
    for name in ("Install toolchain", "Real gate", "Beta step", "alpha", "beta"):
        assert name in out


def test_missing_working_directory_is_named_not_left_to_the_shell(tmp_path, monkeypatch, capsys):
    """The 127/2 class of failure, reported as itself.

    A bad path used to surface as `exit 127` from bash, which reads like a test
    suite complaining about something pre-existing rather than a command that
    never ran.
    """
    wf = tmp_path / "main.yml"
    wf.write_text("""\
jobs:
  alpha:
    steps:
      - name: Bad dir
        run: echo hi
        working-directory: does/not/exist
""")
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    monkeypatch.setattr(ci_local, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ci_local, "DEFAULT_JOB", "alpha")
    assert ci_local.main([]) == 1
    err = capsys.readouterr().err
    assert "working-directory does not exist" in err


# --------------------------------------------------------------------------
# AGAST #1802: fail-fast, per-step timing, ritz1 built before pytest
# --------------------------------------------------------------------------

THREE_STEPS = """\
jobs:
  alpha:
    steps:
      - name: First ok
        run: echo first
      - name: Second fails
        run: exit 3
      - name: Third leaves a marker
        run: touch {marker}
"""


@pytest.fixture
def three_steps(tmp_path, monkeypatch):
    marker = tmp_path / "third-ran"
    wf = tmp_path / "main.yml"
    wf.write_text(THREE_STEPS.format(marker=marker))
    monkeypatch.setattr(ci_local, "WORKFLOW", wf)
    monkeypatch.setattr(ci_local, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(ci_local, "DEFAULT_JOB", "alpha")
    return marker


def test_fail_fast_stops_at_the_first_failing_step(three_steps, capsys):
    """A broken compiler must not cost the whole gate (design §5)."""
    assert ci_local.main(["--fail-fast"]) == 1
    assert not three_steps.exists(), "--fail-fast ran a step after a failure"
    out = capsys.readouterr().out
    # Steps that never ran are named, never silently dropped.
    assert "not run" in out and "Third leaves a marker" in out


def test_without_fail_fast_every_step_runs(three_steps):
    """Default keeps per-step semantics: a failure is recorded, later steps run."""
    assert ci_local.main([]) == 1
    assert three_steps.exists()


def test_each_step_prints_start_and_end_with_duration(three_steps, capsys):
    ci_local.main([])
    out = capsys.readouterr().out
    iso = r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d"
    for name, rc in (("First ok", 0), ("Second fails", 3),
                     ("Third leaves a marker", 0)):
        assert re.search(rf"\[{re.escape(name)}\] START {iso}", out), out
        assert re.search(
            rf"\[{re.escape(name)}\] END {iso}\S* \d+(\.\d+)?s rc={rc}\b", out), out


def test_final_timing_table_lists_every_step_run(three_steps, capsys):
    ci_local.main(["--fail-fast"])
    out = capsys.readouterr().out
    table = out[out.index("step timings"):]
    assert re.search(r"First ok\s+\d+(\.\d+)?s\s+rc=0", table), table
    assert re.search(r"Second fails\s+\d+(\.\d+)?s\s+rc=3", table), table
    assert re.search(r"total\s+\d+(\.\d+)?s", table), table


def test_ritz1_is_built_before_pytest_in_the_bootstrap_job():
    """pytest's ~80 module fixtures must find ritz1 already built, not each
    race a cold serial build (design §2)."""
    names = [s.name for s in ci_local.load_steps() if s.job == "bootstrap"]
    build = [i for i, n in enumerate(names)
             if "build ritz1" in n.lower() and "selfhosted" in n.lower()]
    pytest_ix = [i for i, n in enumerate(names)
                 if "ritz0 unit tests" in n.lower()]
    assert build and pytest_ix, names
    assert build[0] < pytest_ix[0], names


def test_ritz1_build_step_is_parallel():
    step = next(s for s in ci_local.load_steps()
                if s.job == "bootstrap" and "build ritz1" in s.name.lower())
    assert "ritz1-bootstrap" in step.run or "-j" in step.run, step.run


def test_gate_runner_defaults_to_fail_fast():
    gate = ci_local.REPO_ROOT / ".claude/skills/rz-iterate/run-gate.sh"
    if not gate.is_file():
        pytest.skip("run-gate.sh is not part of this checkout")
    cmd_line = next(line for line in gate.read_text().splitlines()
                    if line.startswith("CMD="))
    assert "ARGS=--fail-fast" in cmd_line, cmd_line
