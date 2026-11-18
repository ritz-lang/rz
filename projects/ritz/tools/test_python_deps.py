#!/usr/bin/env python3
"""CI and the gate install the same Python packages, and drift is visible (AGAST #2300).

requirements.txt and requirements-dev.txt only bound the tools from below, so
CI installed the newest pytest/llvmlite/pytest-xdist/pyyaml on every run while
each host's gate venv kept whatever it had.  pytest 9.2.0 broke xdist_group on
CI only (#2251) and every gate kept passing on 9.1.1.

The fix has two halves, and these tests hold both:

  * requirements.lock pins the whole installed closure with `==`, and the CI
    setup action installs with it as a constraints file (`-c`), so CI moves
    only when someone edits the lock.
  * tools/python_deps.py compares the running interpreter's packages with the
    lock.  main.yml runs it, so the gate (ci_local.py) runs it too.  In CI any
    drift fails, because CI installed from the lock and a difference means the
    lock is incomplete; on a gate host it only reports, because the hosts'
    shared venvs are not this commit's to change.
"""

import re
import sys
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parent
RITZ_ROOT = TOOLS.parent
REPO_ROOT = RITZ_ROOT.parents[1]
LOCK = RITZ_ROOT / "requirements.lock"
MAIN_YML = REPO_ROOT / ".github" / "workflows" / "main.yml"
SETUP_ACTION = REPO_ROOT / ".github" / "actions" / "setup" / "action.yml"

sys.path.insert(0, str(TOOLS))
import python_deps


def _dist(version, *requires):
    return python_deps.Dist(version=version, requires=list(requires))


# ---------------------------------------------------------------------------
# The lock file and how CI uses it.


@pytest.mark.unit
def test_lock_pins_every_requirement_exactly():
    """Each top-level requirement has an exact `==` pin in the lock."""
    pins = python_deps.read_lock(LOCK)
    assert pins, "requirements.lock pins nothing"
    roots = python_deps.top_level(python_deps.REQUIREMENTS)
    # tomli is the <3.11 backport; CI runs 3.12, so it is never installed.
    missing = [r for r in roots if r not in pins and r != "tomli"]
    assert not missing, f"requirements not pinned in requirements.lock: {missing}"
    for line in LOCK.read_text().splitlines():
        line = line.split("#")[0].strip()
        if line:
            assert re.fullmatch(r"[A-Za-z0-9._-]+==[A-Za-z0-9.+!-]+", line), (
                f"not an exact pin: {line!r}"
            )


@pytest.mark.unit
def test_ci_installs_with_the_lock_as_constraints():
    """Every pip install in the setup action is constrained by the lock."""
    installs = [
        ln
        for ln in SETUP_ACTION.read_text().splitlines()
        if "pip install" in ln and not ln.lstrip().startswith("#")
    ]
    assert installs
    for ln in installs:
        assert "-c projects/ritz/requirements.lock" in ln, ln


@pytest.mark.unit
def test_main_yml_runs_the_drift_check_so_the_gate_does_too():
    """A `run:` step (not the `uses:` setup action, which ci_local skips) in a
    gated job runs python_deps.py, from projects/ritz, right after the smoke tier
    (Smoke stays the first gate step, #1803; ci-local skips Smoke but runs this)."""
    spec = yaml.safe_load(MAIN_YML.read_text())
    steps = spec["jobs"]["bootstrap"]["steps"]
    names = [s.get("name") for s in steps]
    found = [s for s in steps if "tools/python_deps.py" in str(s.get("run", ""))]
    assert len(found) == 1, names
    step = found[0]
    assert step.get("working-directory") == "projects/ritz"
    assert names.index(step["name"]) == names.index("Smoke") + 1, names
    sys.path.insert(0, str(TOOLS))
    import ci_local

    assert not any(m in step["name"].lower() for m in ci_local.SETUP_STEP_MARKERS), (
        "ci_local would skip the drift check as a setup step"
    )


@pytest.mark.unit
def test_lock_keeps_the_pytest_cap_from_2251():
    """The cap in requirements.txt stays until a pytest-xdist works with pytest
    >= 9.2 (ritz0/test_xdist_group_holds.py); the lock must respect it."""
    pins = python_deps.read_lock(LOCK)
    major, minor = (int(x) for x in pins["pytest"].split(".")[:2])
    assert (major, minor) < (9, 2), pins["pytest"]


# ---------------------------------------------------------------------------
# The drift comparison.

LOCKED = {"pytest": "9.1.1", "pluggy": "1.7.0", "llvmlite": "0.50.0"}
MATCHING = {
    "pytest": _dist(
        "9.1.1",
        "pluggy<2,>=1.5",
        'colorama>=0.4; sys_platform == "win32"',
        'requests; extra == "dev"',
    ),
    "pluggy": _dist("1.7.0", 'pre-commit; extra == "dev"'),
    "llvmlite": _dist("0.50.0"),
}


@pytest.mark.unit
def test_no_drift_when_the_closure_matches_the_lock():
    assert python_deps.drift(LOCKED, MATCHING, ["pytest", "llvmlite"]) == []


@pytest.mark.unit
def test_a_different_version_is_drift():
    dists = {**MATCHING, "pytest": _dist("9.2.0", "pluggy<2,>=1.5")}
    out = python_deps.drift(LOCKED, dists, ["pytest", "llvmlite"])
    assert out == ["pytest: installed 9.2.0, lock 9.1.1"]


@pytest.mark.unit
def test_a_pinned_package_that_is_not_installed_is_drift():
    dists = {k: v for k, v in MATCHING.items() if k != "llvmlite"}
    out = python_deps.drift(LOCKED, dists, ["pytest", "llvmlite"])
    assert out == ["llvmlite: not installed, lock 0.50.0"]


@pytest.mark.unit
def test_an_installed_dependency_missing_from_the_lock_is_drift():
    """A new transitive dependency would float in CI: the lock must name it."""
    dists = {
        **MATCHING,
        "pluggy": _dist("1.7.0", "newdep>=1"),
        "newdep": _dist("1.2.3"),
    }
    out = python_deps.drift(LOCKED, dists, ["pytest", "llvmlite"])
    assert out == ["newdep: installed 1.2.3, not in the lock"]


@pytest.mark.unit
def test_unrelated_installed_packages_are_not_drift():
    """The hosts' venvs carry django, ddtrace, ...; only the closure counts,
    and an `extra == ...` dependency (pytest[dev]: requests) is not in it."""
    dists = {**MATCHING, "django": _dist("5.0"), "requests": _dist("2.0")}
    assert python_deps.drift(LOCKED, dists, ["pytest", "llvmlite"]) == []


@pytest.mark.unit
def test_names_are_normalized():
    lock = {"pyyaml": "6.0.3"}
    dists = {"pyyaml": _dist("6.0.3")}
    assert python_deps.drift(lock, dists, ["PyYAML"]) == []
    assert python_deps.normalize("Py_YAML.x") == "py-yaml-x"


@pytest.mark.unit
def test_read_lock_and_top_level(tmp_path):
    lock = tmp_path / "lock"
    lock.write_text("# header\nPyYAML==6.0.3  # comment\n\npytest_xdist==3.8.0\n")
    assert python_deps.read_lock(lock) == {"pyyaml": "6.0.3", "pytest-xdist": "3.8.0"}
    req = tmp_path / "req"
    req.write_text(
        'llvmlite>=0.44  # x\npytest>=8.0,<9.2\ntomli>=2.0; python_version < "3.11"\n'
    )
    assert python_deps.top_level([req]) == ["llvmlite", "pytest", "tomli"]


# ---------------------------------------------------------------------------
# Exit status: fail in CI, report on a gate host.


def _run_main(monkeypatch, capsys, dists, ci):
    if ci:
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
    else:
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setattr(python_deps, "installed", lambda: dists)
    monkeypatch.setattr(python_deps, "read_lock", lambda path: dict(LOCKED))
    monkeypatch.setattr(python_deps, "top_level", lambda paths: ["pytest", "llvmlite"])
    rc = python_deps.main([])
    return rc, capsys.readouterr().out


@pytest.mark.unit
def test_drift_fails_in_ci(monkeypatch, capsys):
    dists = {**MATCHING, "pytest": _dist("9.2.0", "pluggy<2,>=1.5")}
    rc, out = _run_main(monkeypatch, capsys, dists, ci=True)
    assert rc == 1
    assert "pytest: installed 9.2.0, lock 9.1.1" in out


@pytest.mark.unit
def test_drift_only_reports_on_a_gate_host(monkeypatch, capsys):
    dists = {**MATCHING, "pytest": _dist("9.2.0", "pluggy<2,>=1.5")}
    rc, out = _run_main(monkeypatch, capsys, dists, ci=False)
    assert rc == 0
    assert "DRIFT" in out and "pytest: installed 9.2.0, lock 9.1.1" in out
    assert "-c projects/ritz/requirements.lock" in out, "says how to fix it"


@pytest.mark.unit
def test_no_drift_passes_everywhere(monkeypatch, capsys):
    for ci in (True, False):
        rc, out = _run_main(monkeypatch, capsys, MATCHING, ci=ci)
        assert rc == 0
        assert "match requirements.lock" in out


@pytest.mark.unit
def test_installed_reads_this_interpreter():
    """The real metadata walk finds pytest, which is running this test."""
    dists = python_deps.installed()
    assert "pytest" in dists
    assert dists["pytest"].version
