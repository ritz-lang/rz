"""builder_matrix.py: the package list main.yml's builder-matrix job runs
(AGAST #4825, epic #4783). Buddhafinger (#4826) is the first package to
opt in from outside the swept workspace.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import builder_matrix  # noqa: E402

REPO_ROOT = TOOLS_DIR.parents[2]


class _FakeKnown:
    def __init__(self, build=None, parity=None):
        self._build = set(build or [])
        self._parity = set(parity or [])

    def entries_for(self, gate, compiler):
        assert compiler == "ritz1_selfhosted"
        if gate == "build":
            return {u: None for u in self._build}
        if gate == "parity":
            return {u: None for u in self._parity}
        raise AssertionError(gate)


def _fake_rz(swept, exclusions):
    return SimpleNamespace(
        discover_projects=lambda: list(swept),
        workspace_exclusions=lambda: dict(exclusions))


@pytest.mark.unit
def test_swept_packages_with_no_known_failure_are_included():
    rz = _fake_rz(["sage", "buddhafinger-not-here"], {})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown())
    assert got == ["buddhafinger-not-here", "sage"]


@pytest.mark.unit
def test_a_build_failure_under_ritz1_selfhosted_excludes_the_package():
    rz = _fake_rz(["sage", "angelo"], {})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown(build={"angelo"}))
    assert got == ["sage"]


@pytest.mark.unit
def test_a_parity_failure_under_ritz1_selfhosted_excludes_the_package():
    rz = _fake_rz(["sage", "goliath"], {})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown(parity={"goliath"}))
    assert got == ["sage"]


@pytest.mark.unit
def test_an_excluded_package_is_skipped_without_the_opt_in_marker():
    rz = _fake_rz([], {"projects/buddhafinger": "builds and tests with "
                       "ritz1_selfhosted only, no marker here"})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown())
    assert got == []


@pytest.mark.unit
def test_an_excluded_package_with_the_opt_in_marker_is_included():
    rz = _fake_rz([], {"projects/buddhafinger": f"... {builder_matrix.OPT_IN_MARKER} ..."})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown())
    assert got == ["buddhafinger"]


@pytest.mark.unit
def test_an_opt_in_marker_outside_projects_is_ignored():
    """Only paths under projects/ are rz ids; nothing else can opt in."""
    rz = _fake_rz([], {"docs/archive": f"retired, {builder_matrix.OPT_IN_MARKER}"})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown())
    assert got == []


@pytest.mark.unit
def test_swept_and_opted_in_merge_and_dedupe():
    rz = _fake_rz(["sage"],
                  {"projects/buddhafinger": f"{builder_matrix.OPT_IN_MARKER}"})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown())
    assert got == ["buddhafinger", "sage"]


@pytest.mark.unit
def test_cli_list_prints_a_json_array_sorted():
    rz = _fake_rz(["sage", "angelo"], {})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown())
    assert json.loads(json.dumps(got)) == sorted(got)


@pytest.mark.unit
def test_buddhafinger_opts_in_via_rz_toml():
    """The real rz.toml, not a fake: buddhafinger's own exclusion names the
    marker, so it is in the real matrix without being swept."""
    rz = builder_matrix.load_rz()
    reason = rz.workspace_exclusions().get("projects/buddhafinger")
    assert reason, "rz.toml [workspace.exclude] has no projects/buddhafinger entry"
    assert builder_matrix.OPT_IN_MARKER in reason
    assert "buddhafinger" not in rz.discover_projects()


@pytest.mark.integration
def test_buddhafinger_is_in_the_real_matrix():
    got = builder_matrix.list_packages()
    assert "buddhafinger" in got


@pytest.mark.integration
def test_cli_list_runs_and_includes_buddhafinger():
    r = subprocess.run([sys.executable, str(TOOLS_DIR / "builder_matrix.py"), "list"],
                       cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    packages = json.loads(r.stdout)
    assert isinstance(packages, list) and packages == sorted(packages)
    assert "buddhafinger" in packages
