"""Nested packages are reachable from `rz` (AGAST #1383, #1486).

projects/ritzunit/inventory has its own ritz.toml one level below a project.
It went from compile-failed to 24 passing and no gate could see either
state, because:

(a) DISCOVERY WAS POSITIONAL. rz.toml `members` used `projects/*`, a glob
    that matches ONE level, and nested packages had to be listed by hand. A
    package nobody remembered to list was in no gate, and nothing said so.
    `members` now uses `projects/**`, so every ritz.toml under projects/ is a
    workspace project unless rz.toml *declares* it excluded. Each exclusion
    is a [workspace.exclude] entry that names the gate that does cover it.
    That turns "invisible" into "declared as excluded".

(b) ADDRESSING WAS POSITIONAL TOO. `./rz test projects/ritzunit/inventory`
    joined its argument onto projects/ and looked for
    projects/projects/ritzunit/inventory, so it said "Project not found".
    A path to a package directory now resolves to its project id.

(c) THE PR PLAN MAPPED EVERY CHANGE TO THE TOP-LEVEL DIRECTORY. A change
    under projects/ritzunit/inventory/ marked `ritzunit` as changed and
    never the package that contains the change. Changes now map to the
    innermost workspace project that contains them.
"""

import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

RZ_PATH = Path(__file__).resolve().parents[3] / "rz"
WORKSPACE = RZ_PATH.parent


@pytest.fixture(scope="module")
def rz():
    spec = importlib.util.spec_from_loader(
        "rz_1383", importlib.machinery.SourceFileLoader("rz_1383", str(RZ_PATH))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _toml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


@pytest.fixture
def fake_ws(rz, monkeypatch, tmp_path):
    """A throwaway workspace: rz.toml with `members` (+ optional exclude
    table) and a ritz.toml per package directory."""

    def make(members, packages, exclude=None):
        body = "[workspace]\nmembers = [\n"
        body += "".join(f"    {_toml_str(m)},\n" for m in members) + "]\n"
        if exclude is not None:
            body += "\n[workspace.exclude]\n"
            body += "".join(f"{_toml_str(k)} = {_toml_str(v)}\n"
                            for k, v in exclude.items())
        (tmp_path / "rz.toml").write_text(body)
        (tmp_path / "projects").mkdir(exist_ok=True)
        for rel in packages:
            d = tmp_path / rel
            d.mkdir(parents=True, exist_ok=True)
            (d / "ritz.toml").write_text(f'[package]\nname = "{d.name}"\n')
        monkeypatch.setattr(rz, "WORKSPACE_ROOT", tmp_path)
        monkeypatch.setattr(rz, "PROJECTS_DIR", tmp_path / "projects")
        return tmp_path

    return make


# --------------------------------------------------------------------------
# (a) discovery walks, and exclusions are declared
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestRecursiveMembers:
    def test_double_star_reaches_any_depth(self, rz, fake_ws):
        fake_ws(["projects/**"],
                ["projects/a", "projects/a/inner", "projects/b/x/y"])
        assert rz.discover_projects() == ["a", "a/inner", "b/x/y"]

    def test_single_star_is_still_one_level(self, rz, fake_ws):
        # `*` keeps its meaning; only `**` recurses.
        fake_ws(["projects/*"], ["projects/a", "projects/a/inner"])
        assert rz.discover_projects() == ["a"]

    def test_exclusion_removes_the_directory_and_everything_below(self, rz, fake_ws):
        fake_ws(["projects/**"],
                ["projects/a", "projects/a/examples/e1", "projects/a/examples/e2",
                 "projects/b"],
                exclude={"projects/a/examples": "covered by regression.sh"})
        assert rz.discover_projects() == ["a", "b"]

    def test_exclusion_is_by_path_component_not_string_prefix(self, rz, fake_ws):
        # Excluding projects/a/ex must not swallow projects/a/examples.
        fake_ws(["projects/**"],
                ["projects/a/ex", "projects/a/examples"],
                exclude={"projects/a/ex": "covered elsewhere"})
        assert rz.discover_projects() == ["a/examples"]

    def test_exclusion_matching_no_package_is_an_error(self, rz, fake_ws):
        # A stale exclusion is a rotted allowlist: if the package moves, the
        # exclusion must not silently keep excusing nothing.
        fake_ws(["projects/**"], ["projects/a"],
                exclude={"projects/gone": "covered elsewhere"})
        with pytest.raises(SystemExit) as exc:
            rz.discover_projects()
        assert "projects/gone" in str(exc.value)

    @pytest.mark.parametrize("reason", ["", "   "])
    def test_exclusion_without_a_reason_is_an_error(self, rz, fake_ws, reason):
        fake_ws(["projects/**"], ["projects/a", "projects/a/b"],
                exclude={"projects/a/b": reason})
        with pytest.raises(SystemExit) as exc:
            rz.discover_projects()
        assert "projects/a/b" in str(exc.value)

    def test_exclusion_reason_must_be_a_string(self, rz, fake_ws, tmp_path):
        root = fake_ws(["projects/**"], ["projects/a", "projects/a/b"])
        (root / "rz.toml").write_text(
            '[workspace]\nmembers = ["projects/**"]\n'
            '[workspace.exclude]\n"projects/a/b" = 3\n')
        with pytest.raises(SystemExit):
            rz.discover_projects()

    def test_no_exclude_table_is_fine(self, rz, fake_ws):
        fake_ws(["projects/**"], ["projects/a"])
        assert rz.discover_projects() == ["a"]


@pytest.mark.unit
class TestRealWorkspace:
    """The acceptance facts, against the real rz.toml."""

    def test_inventory_is_a_workspace_project(self, rz):
        assert "ritzunit/inventory" in rz.discover_projects()

    @pytest.mark.parametrize("pkg", [
        "ritz/ritzlib/tests",          # #1345, now by walk instead of by name
        "larb/tools/ritz-stats",
        "spire/httplib",
    ])
    def test_other_nested_packages_are_projects(self, rz, pkg):
        assert pkg in rz.discover_projects()

    def test_examples_are_left_to_regression_sh(self, rz):
        assert not [p for p in rz.discover_projects()
                    if p.startswith("ritz/examples/")]

    def test_archive_is_not_a_project(self, rz):
        assert not [p for p in rz.discover_projects()
                    if p.startswith("ritz/docs/archive/")]

    def test_every_package_is_discovered_or_declared_excluded(self, rz):
        # The floor from the ticket: no ritz.toml under projects/ may be in
        # neither set. Walk independently of rz so a bug in rz's walk shows.
        found = set(rz.discover_projects())
        excluded = rz.workspace_exclusions()
        projects = WORKSPACE / "projects"
        orphans = []
        for manifest in projects.rglob("ritz.toml"):
            pkg = manifest.parent
            pid = pkg.relative_to(projects).as_posix()
            rel = pkg.relative_to(WORKSPACE)
            covered = any(rel == Path(e) or Path(e) in rel.parents
                          for e in excluded)
            if pid not in found and not covered:
                orphans.append(pid)
        assert orphans == []

    def test_harland_boot_exclusion_is_true(self, rz):
        # Excluded because the parent builds it. Pin that claim so the
        # exclusion cannot outlive it.
        import tomllib
        cfg = tomllib.loads((WORKSPACE / "projects/harland/ritz.toml").read_text())
        bins = cfg.get("bin", [])
        assert any("boot/src" in b.get("sources", []) for b in bins)
        assert "projects/harland/boot" in rz.workspace_exclusions()


# --------------------------------------------------------------------------
# (b) a package can be addressed by its path
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestResolveProject:
    @pytest.mark.parametrize("arg", [
        "ritzunit/inventory",
        "projects/ritzunit/inventory",
        "./projects/ritzunit/inventory",
        "projects/ritzunit/inventory/",
        str(WORKSPACE / "projects/ritzunit/inventory"),
    ])
    def test_spellings_resolve_to_the_project_id(self, rz, arg):
        assert rz.resolve_project(arg) == "ritzunit/inventory"

    def test_bare_top_level_name_is_unchanged(self, rz):
        assert rz.resolve_project("ritz") == "ritz"

    def test_cwd_relative_path(self, rz, monkeypatch):
        monkeypatch.chdir(WORKSPACE / "projects" / "ritzunit")
        assert rz.resolve_project("inventory") == "ritzunit/inventory"
        assert rz.resolve_project(".") == "ritzunit"

    def test_bench_member_by_path(self, rz):
        assert (rz.resolve_project("bench/regressions/2026-05-04/s2_module_init")
                == "../bench/regressions/2026-05-04/s2_module_init")

    @pytest.mark.parametrize("arg", ["no-such-project", "projects/ritzunit/test"])
    def test_non_package_is_none(self, rz, arg):
        # projects/ritzunit/test exists but has no ritz.toml.
        assert rz.resolve_project(arg) is None

    def test_cmd_test_runs_build_py_on_the_package(self, rz, monkeypatch):
        seen = []
        monkeypatch.setattr(rz.subprocess, "run",
                            lambda cmd, **kw: seen.append(cmd) or
                            SimpleNamespace(returncode=0))
        args = SimpleNamespace(project="projects/ritzunit/inventory",
                               all=False, compiler="ritz0")
        assert rz.cmd_test(args) == 0
        target = Path(seen[0][3]).resolve()
        assert target == (WORKSPACE / "projects/ritzunit/inventory").resolve()

    def test_cmd_build_rejects_unknown_with_exit_1(self, rz, capsys):
        args = SimpleNamespace(project="projects/nope", all=False,
                               compiler="ritz0", release=False)
        assert rz.cmd_build(args) == 1
        assert "not found" in capsys.readouterr().err


@pytest.mark.integration
def test_cli_tests_inventory_by_path(tmp_path):
    """The exact command from the ticket, which printed "Project not found"."""
    r = subprocess.run(
        [str(RZ_PATH), "test", "projects/ritzunit/inventory"],
        cwd=WORKSPACE, capture_output=True, text=True, timeout=600)
    assert "not found" not in r.stderr
    assert r.returncode == 0, r.stdout + r.stderr


# --------------------------------------------------------------------------
# (c) the PR plan maps a change to the package that contains it
# --------------------------------------------------------------------------

@pytest.mark.unit
class TestImpactMapsToInnermostPackage:
    PROJECTS = ["ritz", "ritz/ritzlib/tests", "ritzunit", "ritzunit/inventory"]

    def _direct(self, rz, files):
        _impacted, direct = rz.compute_impacted_projects(files, self.PROJECTS, {}, {})
        return direct

    def test_nested_change_marks_the_nested_package(self, rz):
        assert self._direct(rz, ["projects/ritzunit/inventory/test/t.ritz"]) == {
            "ritzunit/inventory"}

    def test_parent_change_marks_the_parent(self, rz):
        assert self._direct(rz, ["projects/ritzunit/src/x.ritz"]) == {"ritzunit"}

    def test_unrelated_path_marks_nothing(self, rz):
        assert self._direct(rz, ["docs/x.md", "projects/nope/a.ritz"]) == set()
