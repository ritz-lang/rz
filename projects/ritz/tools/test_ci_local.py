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
