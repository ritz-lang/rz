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
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown())
    assert got == ["buddhafinger-not-here", "sage"]


@pytest.mark.unit
def test_a_build_failure_under_ritz1_selfhosted_excludes_the_package():
    rz = _fake_rz(["sage", "angelo"], {})
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown(build={"angelo"}))
    assert got == ["sage"]


@pytest.mark.unit
def test_a_parity_failure_under_ritz1_selfhosted_excludes_the_package():
    rz = _fake_rz(["sage", "goliath"], {})
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown(parity={"goliath"}))
    assert got == ["sage"]


@pytest.mark.unit
def test_an_excluded_package_is_skipped_without_the_opt_in_marker():
    rz = _fake_rz([], {"projects/buddhafinger": "builds and tests with "
                       "ritz1_selfhosted only, no marker here"})
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown())
    assert got == []


@pytest.mark.unit
def test_an_excluded_package_with_the_opt_in_marker_is_included():
    rz = _fake_rz([], {"projects/buddhafinger": f"... {builder_matrix.OPT_IN_MARKER} ..."})
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown())
    assert got == ["buddhafinger"]


@pytest.mark.unit
def test_an_opt_in_marker_outside_projects_is_ignored():
    """Only paths under projects/ are rz ids; nothing else can opt in."""
    rz = _fake_rz([], {"docs/archive": f"retired, {builder_matrix.OPT_IN_MARKER}"})
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown())
    assert got == []


@pytest.mark.unit
def test_swept_and_opted_in_merge_and_dedupe():
    rz = _fake_rz(["sage"],
                  {"projects/buddhafinger": f"{builder_matrix.OPT_IN_MARKER}"})
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown())
    assert got == ["buddhafinger", "sage"]


@pytest.mark.unit
def test_cli_list_prints_a_json_array_sorted():
    rz = _fake_rz(["sage", "angelo"], {})
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown())
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
    assert got == ["buddhafinger"]


@pytest.mark.integration
def test_cli_list_runs_and_includes_buddhafinger():
    r = subprocess.run([sys.executable, str(TOOLS_DIR / "builder_matrix.py"), "list"],
                       cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    packages = json.loads(r.stdout)
    assert isinstance(packages, list) and packages == sorted(packages)
    assert packages == ["buddhafinger"]


# --- AGAST #4846: the matrix runs buddhafinger only --------------------------


@pytest.mark.unit
def test_the_matrix_runs_buddhafinger_only():
    """Aaron, 2026-11-27: on Woodpecker and in the hosted fallback alike, the
    builder matrix runs buddhafinger and nothing else."""
    assert builder_matrix.MATRIX_PACKAGES == ("buddhafinger",)


@pytest.mark.unit
def test_list_packages_is_the_run_list_not_every_eligible_package():
    rz = _fake_rz(["sage", "goliath"],
                  {"projects/buddhafinger": builder_matrix.OPT_IN_MARKER})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown())
    assert got == ["buddhafinger"]


@pytest.mark.unit
def test_list_packages_keeps_the_run_lists_order():
    rz = _fake_rz(["sage", "angelo"], {})
    got = builder_matrix.list_packages(rz=rz, known=_FakeKnown(), only=("sage", "angelo"))
    assert got == ["sage", "angelo"]


@pytest.mark.unit
def test_a_run_list_package_that_isnt_eligible_fails_loudly():
    """An empty matrix would make GitHub's builder-matrix job error out and
    Woodpecker run nothing; a package the eligibility rules drop (a lost
    opt-in marker, a swept package's known failure) is an error, not a
    silent skip."""
    rz = _fake_rz(["sage"], {"projects/buddhafinger": "no marker"})
    with pytest.raises(ValueError, match="buddhafinger"):
        builder_matrix.list_packages(rz=rz, known=_FakeKnown())
    rz = _fake_rz(["sage"], {})
    with pytest.raises(ValueError, match="sage"):
        builder_matrix.list_packages(rz=rz, known=_FakeKnown(parity={"sage"}),
                                     only=("sage",))


@pytest.mark.unit
def test_an_empty_run_list_is_refused():
    rz = _fake_rz(["sage"], {})
    with pytest.raises(ValueError, match="empty"):
        builder_matrix.list_packages(rz=rz, known=_FakeKnown(), only=())


# --- AGAST #4847: what each matrix entry runs -------------------------------


@pytest.mark.unit
def test_the_compiler_package_itself_is_never_in_the_matrix():
    """`ritz` is the compiler: the entrypoint replaces the image's own
    projects/ritz with the mounted one, so its ritz1_selfhosted check can
    never pass (run 45804261861, exit 2). The bootstrap job gates it."""
    rz = _fake_rz(["ritz", "ritz/ritzlib/tests", "sage"], {})
    got = builder_matrix.eligible_packages(rz=rz, known=_FakeKnown())
    assert got == ["ritz/ritzlib/tests", "sage"]
    assert "ritz" in builder_matrix.NOT_IN_MATRIX


def _pkg(root: Path, rel: str, *, test_file: bool = False, test_sh: bool = False) -> Path:
    d = root / rel
    (d / "src").mkdir(parents=True)
    (d / "ritz.toml").write_text('[package]\nname = "x"\nversion = "0.1.0"\n')
    (d / "src" / "main.ritz").write_text("fn main() -> i32\n    0\n")
    if test_file:
        (d / "test").mkdir()
        (d / "test" / "test_x.ritz").write_text("[[test]]\nfn test_x() -> i32\n    0\n")
    if test_sh:
        (d / "test.sh").write_text("#!/bin/bash\nexit 0\n")
    return d


@pytest.mark.unit
def test_a_package_with_no_tests_is_build_only(tmp_path):
    """indium, bench s2/s3: `rz test` says "No tests found", which the zero-
    test guard rightly fails; such a package is built, not tested."""
    _pkg(tmp_path / "projects", "lib")
    assert builder_matrix.has_tests(tmp_path / "projects" / "lib") is False


@pytest.mark.unit
def test_a_test_file_or_a_test_sh_is_tests(tmp_path):
    _pkg(tmp_path / "projects", "a", test_file=True)
    _pkg(tmp_path / "projects", "b", test_sh=True)
    assert builder_matrix.has_tests(tmp_path / "projects" / "a") is True
    assert builder_matrix.has_tests(tmp_path / "projects" / "b") is True


@pytest.mark.unit
def test_entries_carry_a_normalized_workspace_path_and_build_only(tmp_path):
    """A bench package's id is "../bench/..."; "projects/../bench/..." does not
    exist in the container (run 45804261861: "no ritz.toml in
    /src/projects/../bench/..."), so the entry carries bench/... itself."""
    projects = tmp_path / "projects"
    _pkg(projects, "sage", test_file=True)
    _pkg(tmp_path, "bench/r/s2")
    rz = _fake_rz(["sage", "../bench/r/s2"], {})
    got = builder_matrix.matrix_entries(rz=rz, known=_FakeKnown(), workspace=tmp_path,
                                        only=("../bench/r/s2", "sage"))
    assert got == [
        {"package": "../bench/r/s2", "path": "bench/r/s2", "build_only": True},
        {"package": "sage", "path": "projects/sage", "build_only": False},
    ]


@pytest.mark.integration
def test_the_real_matrix_is_buddhafinger_with_its_tests():
    got = builder_matrix.matrix_entries()
    assert got == [{"package": "buddhafinger", "path": "projects/buddhafinger",
                    "build_only": False}]
    assert (REPO_ROOT / "projects/buddhafinger/ritz.toml").is_file()


@pytest.mark.integration
def test_every_eligible_package_would_still_map_to_a_real_path():
    """The eligibility rules still run (list_packages checks the run list
    against them), so their ids must stay valid workspace paths: widening
    the run list again is then a one-line change."""
    got = builder_matrix.matrix_entries(only=tuple(builder_matrix.eligible_packages()))
    by_pkg = {e["package"]: e for e in got}
    assert "ritz" not in by_pkg
    assert by_pkg["indium"]["build_only"] is True
    assert by_pkg["rllvm"]["build_only"] is False  # test.sh, pytest in the image
    for e in got:
        assert (REPO_ROOT / e["path"] / "ritz.toml").is_file(), e


@pytest.mark.integration
def test_cli_matrix_prints_the_entries():
    r = subprocess.run([sys.executable, str(TOOLS_DIR / "builder_matrix.py"), "matrix"],
                       cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    entries = json.loads(r.stdout)
    assert [e["package"] for e in entries] == builder_matrix.list_packages()
