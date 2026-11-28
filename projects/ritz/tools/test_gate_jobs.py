#!/usr/bin/env python3
"""The gate's -j follows RZ_GATE_JOBS (AGAST #4971).

run-gate.sh hands host.env's RZ_GATE_JOBS to the gate as RZ_GATE_JOBS and as
RITZ1_JOBS / PYTEST_J / RATCHETS_J / REGRESSION_JOBS (test-run-gate.sh and
test_host_budget.py hold that half).  This file holds the other half: every
gate step whose tool takes a -j of its own reads RZ_GATE_JOBS, and with it
unset passes no -j at all, so each tool keeps its own default.

  * the Makefile targets the gate's bootstrap job runs, as `make -n` prints
    them with and without RZ_GATE_JOBS;
  * main.yml's `rz build/test --all` and ritz0 pytest steps, as bash expands
    their -j expressions with and without the knob.

Run with:
    python3 -m pytest projects/ritz/tools/test_gate_jobs.py -q
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration  # every test starts a process (AGAST #4092)

HERE = Path(__file__).resolve().parent
RITZ = HERE.parent
WORKFLOW = HERE.parents[2] / ".github" / "workflows" / "main.yml"

# Prerequisites taken as up to date, so `make -n` prints only the target's own
# recipe (ritz1-bootstrap's $(MAKE) line would otherwise dry-run ritz1 too).
ASSUME_OLD = ("ritz1-bootstrap", "regen-check", "_matrix_ritz1_built")

# Target -> the tool line in its recipe that must carry the gate's -j.
TARGETS = {
    "check-doc-examples": "tools/check_doc_examples.py",
    "check-doc-examples-ritz1": "tools/check_doc_examples.py",
    "example-tests": "tools/example_tests.py",
    "ritz1-unit": "tools/ritz1_unit.py",
    "ritzlib-tests-ritz1": "./rz test",
    "build-all-ritz1": "./rz build",
    "matrix-full": "tools/run_regression_matrix.py",
}

JOB_KNOBS = ("RZ_GATE_JOBS", "RITZ1_JOBS", "PYTEST_J", "RATCHETS_J", "REGRESSION_JOBS")


def _env(jobs: str | None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in JOB_KNOBS and k != "MAKEFLAGS"}
    if jobs is not None:
        env["RZ_GATE_JOBS"] = jobs
    return env


def _dry_run(target: str, jobs: str | None) -> list[str]:
    args = ["make", "-n", "-C", str(RITZ), target]
    args += [f"--assume-old={t}" for t in ASSUME_OLD]
    r = subprocess.run(args, env=_env(jobs), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout.splitlines()


def _tool_lines(target: str, jobs: str | None) -> list[str]:
    lines = [ln for ln in _dry_run(target, jobs) if TARGETS[target] in ln]
    assert lines, f"`make -n {target}` ran no {TARGETS[target]}"
    return lines


@pytest.mark.parametrize("target", sorted(TARGETS))
def test_target_passes_the_gate_jobs(target):
    for ln in _tool_lines(target, "24"):
        assert re.search(r"(^|\s)-j 24(\s|$)", ln), ln


@pytest.mark.parametrize("target", sorted(TARGETS))
def test_target_without_gate_jobs_passes_no_j(target):
    """Unset: the tool's own default (check_doc_examples 8, ritz1_unit 4,
    rz.toml's max_jobs, ...), exactly as before."""
    for ln in _tool_lines(target, None):
        assert not re.search(r"(^|\s)(-j|--jobs)(\s|$)", ln), ln


def _steps() -> dict[str, str]:
    wf = yaml.safe_load(WORKFLOW.read_text())
    return {
        s["name"]: s["run"]
        for job in wf["jobs"].values()
        for s in job.get("steps", [])
        if "name" in s and "run" in s
    }


def _expand(cmd: str, env: dict[str, str]) -> str:
    """The words bash makes of `cmd` (one line), without running it."""
    r = subprocess.run(
        ["bash", "-c", 'set -- $(eval "printf \'%s \' $1"); echo "$*"', "_", cmd],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


# Step -> (its rz command line, the words it expands to with RZ_GATE_JOBS=24,
# and unset).  `nproc` is the runner's: the job count without the knob.
RZ_STEPS = {
    "Build workspace": ("./rz build --all", "./rz build --all"),
    "Test workspace": ("./rz test --all -j 24", "./rz test --all -j {nproc}"),
    "Test every package with ritz1": (
        "./rz test --all --compiler ritz1 -j 24",
        "./rz test --all --compiler ritz1 -j {nproc}",
    ),
}


@pytest.mark.parametrize("step", sorted(RZ_STEPS))
def test_workflow_rz_steps_follow_the_gate_jobs(step):
    run = _steps()[step]
    (line,) = [ln.strip() for ln in run.splitlines() if ln.strip().startswith("./rz ")]
    want24, want_unset = RZ_STEPS[step]
    nproc = subprocess.run(["nproc"], capture_output=True, text=True).stdout.strip()
    got24 = _expand(line, _env("24"))
    # `rz build --all` takes rz.toml's max_jobs unless told otherwise.
    if step == "Build workspace":
        want24 = "./rz build --all -j 24"
    assert got24 == want24, line
    assert _expand(line, _env(None)) == want_unset.format(nproc=nproc), line


def test_workflow_ritz0_pytest_follows_pytest_j():
    """The bootstrap job's ritz0 suite: `-n auto --maxprocesses 8` on a hosted
    runner, PYTEST_J's count in a gate that sets it."""
    run = _steps()["ritz0 unit tests"]
    (line,) = [ln for ln in run.splitlines() if "-m pytest" in ln]
    m = re.search(r"--maxprocesses (\S+)", line)
    assert m, line
    assert _expand(m.group(1), {**_env(None), "PYTEST_J": "24"}) == "24"
    assert _expand(m.group(1), _env(None)) == "8"


# --- the builder image's bootstrap (projects/builder/resolve_image.sh) -------
#
# A gate whose commit has no published builder image builds one: the
# Dockerfile's bootstrap stage runs `make ritz1-bootstrap`, whose -j is the
# RITZ1_JOBS build-arg (empty: ritz1-jobs.sh's cap).  It follows the gate's
# RITZ1_JOBS when set, and is left off when not, as projects/builder/test.sh
# does, so the Dockerfile's own default stays in the build cache key.

RESOLVE = HERE.parents[1] / "builder" / "resolve_image.sh"

FAKE_DOCKER = """#!/usr/bin/env bash
echo "docker $*" >> "$FAKE_DOCKER_LOG"
case "$1" in
    info) exit 0 ;;
    image) [[ "$2" == inspect ]] && exit 1; exit 0 ;;
    pull) exit 1 ;;
    run) echo "0000  projects/ritz/ritz1/build/ritz1_selfhosted" ;;
    build) cat >/dev/null ;;
esac
exit 0
"""


def _builds(tmp_path: Path, ritz1_jobs: str | None) -> list[str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "docker").write_text(FAKE_DOCKER)
    (bin_dir / "docker").chmod(0o755)
    log = tmp_path / "docker.log"
    env = _env(None)
    env.pop("RZ_BUILDER_IMAGE", None)
    env.update(PATH=f"{bin_dir}:{env['PATH']}", FAKE_DOCKER_LOG=str(log), RZ_BUILDER_NO_PULL="1")
    if ritz1_jobs is not None:
        env["RITZ1_JOBS"] = ritz1_jobs
    r = subprocess.run(["bash", str(RESOLVE)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    builds = [ln for ln in log.read_text().splitlines() if ln.startswith("docker build ")]
    assert len(builds) == 2, builds  # the bootstrap stage, then the runtime image
    return builds


def test_builder_bootstrap_follows_ritz1_jobs(tmp_path):
    boot = [b for b in _builds(tmp_path, "24") if "--target bootstrap" in b]
    assert len(boot) == 1 and "--build-arg RITZ1_JOBS=24" in boot[0], boot


def test_builder_bootstrap_without_ritz1_jobs_passes_no_build_arg(tmp_path):
    assert not [b for b in _builds(tmp_path, None) if "RITZ1_JOBS" in b]
