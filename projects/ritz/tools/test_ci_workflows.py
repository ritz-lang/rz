"""CI has no dead or duplicated parts (AGAST #1838, LARB tooling F9/F11/F14/F16).

What these tests pin, and why:

* pr.yml is gone. Rooms land by `git merge --ff-only` on a local machine,
  so a `pull_request` workflow never triggers; its last run was 2026-09-04.
  Its affected-project logic (`cut -d/ -f2`) also ignored reverse
  dependencies. A workflow that never runs reads as a gate that does.
* No job or step is `continue-on-error`. lint-all was, and it also exited 0
  whenever the `claude` CLI was missing, which is always on a runner: a green
  tick that asserted nothing. ritz-lint is a local pre-commit hook now
  (projects/ritz/tools/ritz-lint/install-hook.sh).
* One composite setup action (.github/actions/setup: Python, the pinned
  LLVM toolchain, ritz0's pip requirements) is used by every job, so the
  ~16 setup lines are not copied into each job, and no job pins its own
  Python or toolchain.
* CLANG_VERSION is set in one workflow file.
* One ritz-lint copy (there were two, 92 diff lines apart).
* scripts/regression.sh is shellcheck-clean.
* The "Gate coverage" section main.yml cites exists: it states that
  test-all never runs before a merge.
"""

import subprocess
from pathlib import Path

import re

import pytest
import yaml

import shellcheck_tool

PKG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_DIR.parents[1]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
ACTIONS = REPO_ROOT / ".github" / "actions"
SETUP_ACTION = "./.github/actions/setup"


def _workflow_files():
    return sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))


def _jobs():
    for wf in _workflow_files():
        spec = yaml.safe_load(wf.read_text())
        for name, job in (spec.get("jobs") or {}).items():
            yield wf.name, name, job


@pytest.mark.unit
def test_only_main_workflow_exists():
    assert [p.name for p in _workflow_files()] == ["main.yml"]


@pytest.mark.unit
def test_no_job_or_step_is_continue_on_error():
    offenders = []
    for wf, name, job in _jobs():
        if job.get("continue-on-error"):
            offenders.append(f"{wf}:{name}")
        for step in job.get("steps") or []:
            if step.get("continue-on-error"):
                offenders.append(f"{wf}:{name}:{step.get('name')}")
    assert not offenders, offenders


@pytest.mark.unit
def test_every_job_checks_out_then_uses_the_setup_action():
    for wf, name, job in _jobs():
        uses = [str(s.get("uses", "")) for s in job.get("steps") or []]
        assert uses[:2] == ["actions/checkout@v4", SETUP_ACTION], (wf, name, uses[:2])


@pytest.mark.unit
def test_no_job_repeats_setup_inline():
    """setup-python, the toolchain and pip live in the action, nowhere else."""
    for wf, name, job in _jobs():
        for step in job.get("steps") or []:
            uses = str(step.get("uses", ""))
            assert "setup-python" not in uses, (wf, name, step)
            assert "install-toolchain" not in uses, (wf, name, step)
            assert "requirements" not in str(step.get("run", "")), (wf, name, step)


@pytest.mark.unit
def test_setup_action_is_the_only_action_and_is_composite():
    assert sorted(p.name for p in ACTIONS.iterdir()) == ["setup"]
    spec = yaml.safe_load((ACTIONS / "setup" / "action.yml").read_text())
    assert spec["runs"]["using"] == "composite"
    assert spec["inputs"]["clang-version"]["required"] is True
    text = (ACTIONS / "setup" / "action.yml").read_text()
    for needle in ("actions/setup-python", "projects/ritz/requirements.txt",
                   "projects/ritz/requirements-dev.txt", "GITHUB_PATH"):
        assert needle in text, needle


@pytest.mark.unit
def test_clang_version_is_pinned_in_one_workflow_file():
    pinned = [p.name for p in _workflow_files() if "CLANG_VERSION:" in p.read_text()]
    assert pinned == ["main.yml"]


@pytest.mark.unit
def test_one_ritz_lint():
    copies = sorted(p.relative_to(REPO_ROOT).as_posix()
                    for p in (REPO_ROOT / "projects").rglob("ritz_lint.py"))
    assert copies == ["projects/ritz/tools/ritz-lint/ritz_lint.py"]


@pytest.mark.unit
def test_gate_coverage_is_documented_where_main_yml_points():
    """main.yml cites the "Gate coverage" section; the section exists, names
    every job, and every job runs before a merge (AGAST #3969: test-all
    too, run-gate.sh's --job list)."""
    main = (WORKFLOWS / "main.yml").read_text()
    assert '"Gate coverage" in .claude/skills/rz-iterate/SKILL.md' in main
    skill = (REPO_ROOT / ".claude" / "skills" / "rz-iterate" / "SKILL.md").read_text()
    head = "### Gate coverage"
    assert head in skill
    section = skill.split(head, 1)[1].split("\n### ", 1)[0]
    # One table row per main.yml job, each gated before the merge, as
    # run-gate.sh's `--job` list says.
    rows = {line.split("`")[1]: line for line in section.splitlines()
            if line.startswith("| `")}
    jobs = sorted(yaml.safe_load(main)["jobs"])
    assert sorted(rows) == jobs, sorted(rows)
    # read-set-audit (AGAST #4315) is the one job a merge does not wait on:
    # ~15 min under strace, and it audits the gate's skip rule, not a change.
    not_gated = {"read-set-audit"}
    for job, row in rows.items():
        gated = row.split("|")[2].strip()
        assert gated.startswith("no" if job in not_gated else "yes"), row
    gate = (REPO_ROOT / ".claude/skills/rz-iterate/run-gate.sh").read_text()
    cmd = next(line for line in gate.splitlines() if line.startswith("CMD="))
    assert sorted(re.findall(r"--job ([\w-]+)", cmd)) == sorted(set(jobs) - not_gated), cmd


# Spawns shellcheck (AGAST #4264); the pinned one, which fails rather than
# skips when it is missing (AGAST #4360).
@pytest.mark.integration
def test_regression_sh_is_shellcheck_clean():
    r = subprocess.run([shellcheck_tool.shellcheck(), "-x", "scripts/regression.sh"],
                       cwd=PKG_DIR, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.unit
def test_every_step_trap_that_removes_a_dir_makes_it_removable_first():
    """AGAST #4274: tests leave dirs with no read/search bit (mode 000), and a
    bare `rm -rf` can't descend into one: pytest basetemps of 110-145k files
    each survived that way until bangerang's /tmp ran out of inodes.  So a
    step's `trap ... rm -rf "$X"` runs `chmod -R u+rwx "$X"` first."""
    traps = []
    for wf, job, spec in _jobs():
        for step in spec.get("steps") or []:
            for m in re.finditer(r"trap '([^']*)'", step.get("run") or ""):
                for target in re.findall(r'rm -rf ("\$\w+")', m.group(1)):
                    traps.append((wf, job, step.get("name"), m.group(1), target))
    assert traps, "no step trap removes a dir: the ritz0 step's BASETEMP trap moved?"
    bad = [t for t in traps if f"chmod -R u+rwx {t[4]}" not in t[3].split("rm -rf")[0]]
    assert not bad, bad
