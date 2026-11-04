#!/usr/bin/env python3
"""CI must run the valet -> zeus -> nexus e2e (AGAST #2107).

projects/nexus/test/e2e_large_page.sh (#2104) needs debug builds of zeus,
valet and nexus. It cannot be nexus's package test.sh: `rz test --all -j N`
would then build zeus and valet from inside nexus's test while their own
tests build them too, racing the same build dirs (build.py has no out-dir).

So it is a step in main.yml's build-all job, after `./rz build --all` has
built all three serially. These tests pin that wiring: the script ran only
by hand for as long as nothing referenced it, and a test nobody runs is a
green tick asserting nothing.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_e2e.py -q
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ci_local  # noqa: E402

E2E = "projects/nexus/test/e2e_large_page.sh"
REPO = ci_local.WORKFLOW.resolve().parents[2]


def _build_all_steps() -> list[ci_local.Step]:
    return [s for s in ci_local.load_steps() if s.job == "build-all"]


def _e2e_index(steps: list[ci_local.Step]) -> int:
    hits = [i for i, s in enumerate(steps) if E2E in s.run]
    assert len(hits) == 1, f"want exactly one build-all step running {E2E}, got {len(hits)}"
    return hits[0]


def test_e2e_script_exists():
    assert (REPO / E2E).is_file()


def test_build_all_runs_e2e_after_building_the_workspace():
    steps = _build_all_steps()
    e2e = _e2e_index(steps)
    builds = [i for i, s in enumerate(steps) if "./rz build --all" in s.run]
    assert builds, "build-all no longer runs ./rz build --all"
    assert builds[0] < e2e, "the e2e step must come after the binaries it needs are built"


def test_e2e_step_runs_from_repo_root():
    step = _build_all_steps()[_e2e_index(_build_all_steps())]
    # The script resolves its binaries relative to itself, but a workdir
    # would make the relative path in `run:` wrong.
    assert step.workdir == "."


def test_e2e_step_is_a_real_gate():
    """No continue-on-error, no `|| true`, and a timeout: the script talks to
    three live servers, and a wedged one should fail in minutes, not burn the
    job-level six hours."""
    spec = yaml.safe_load(ci_local.WORKFLOW.read_text())
    raw = [s for s in spec["jobs"]["build-all"]["steps"] if E2E in str(s.get("run", ""))]
    assert len(raw) == 1
    step = raw[0]
    assert not step.get("continue-on-error", False)
    assert "|| true" not in step["run"]
    assert 0 < int(step.get("timeout-minutes", 0)) <= 10
    assert not spec["jobs"]["build-all"].get("continue-on-error", False)


def test_e2e_never_exits_with_the_setup_code():
    """ci_local reads exit 3 as SETUP ERROR (a missing tool, no verdict on
    the code) and does not stop --fail-fast for it. A red e2e must read as
    a regression, so the script may only exit 0 or 1."""
    src = (REPO / E2E).read_text()
    # Statements, not prose: "curl exit $rc" in a message is not one.
    codes = set(re.findall(r"(?<!curl )\bexit\s+([^\s;})\"']+)", src))
    assert codes <= {"0", "1"}, f"{E2E} exits with {sorted(codes)}"
