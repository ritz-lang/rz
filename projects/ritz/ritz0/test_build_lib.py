"""AGAST #1340: `[[lib]]` is a real build target.

build.py used to have no idea what a library was. A package declaring `[[lib]]`
and no `[[bin]]` fell through to the default arm of plan_binaries(), which
hardcoded src/main.ritz: `rz build cryptosec` compiled a 5-line stub, linked an
8-symbol binary, and reported success without touching one of the modules the
package declares. So a lib-only package could not fail its build.

What must hold now:
  - `[[lib]]` compiles every module under its sources, implying no binary.
  - One broken module fails the package, whether or not anything imports it.
  - The default arm honours the package's sources, and a missing main is a
    failure rather than a target aimed at nothing.
"""

import importlib.util
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

RITZ_DIR = Path(__file__).parent.parent
WORKSPACE = RITZ_DIR.parent.parent

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(RITZ_DIR))
# Import our build.py explicitly (avoid pip's build package).
_spec = importlib.util.spec_from_file_location("ritz_build_lib", RITZ_DIR / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def _package(root: Path, manifest: str, files: dict[str, str]) -> Path:
    """Write a package: `manifest` follows a generated [package] header."""
    (root / "ritz.toml").write_text(
        f'[package]\nname = "p1340"\nversion = "0.1.0"\n{manifest}')
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def _plan(pkg: Path):
    return build.plan_binaries(pkg, _config(pkg))


def _config(pkg: Path) -> dict:
    return tomllib.loads((pkg / "ritz.toml").read_text())


def _modules(pkg: Path, plan) -> dict[str, list[str]]:
    """Library name -> its modules, relative to the package."""
    return {lib.name: sorted(str(m.relative_to(pkg)) for m in lib.modules)
            for lib in plan.libraries}


class TestLibraryPlan:
    """What plan_binaries() decides for a `[[lib]]`."""

    LIB_ONLY = 'sources = ["lib"]\n\n[[lib]]\nname = "p1340"\n'

    @pytest.mark.unit
    def test_lib_only_package_plans_no_binary(self, tmp_path):
        """The original defect: a stub src/main.ritz must not become a target."""
        pkg = _package(tmp_path, self.LIB_ONLY, {
            "lib/a.ritz": "pub fn a() -> i32\n    1\n",
            "src/main.ritz": "fn main() -> i32\n    0\n",
        })
        plan = _plan(pkg)
        assert plan.buildable == []
        assert plan.unresolved == []
        assert _modules(pkg, plan) == {"p1340": ["lib/a.ritz"]}

    @pytest.mark.unit
    def test_lib_covers_every_module_recursively(self, tmp_path):
        pkg = _package(tmp_path, self.LIB_ONLY, {
            "lib/a.ritz": "pub fn a() -> i32\n    1\n",
            "lib/deep/b.ritz": "pub fn b() -> i32\n    2\n",
        })
        assert _modules(pkg, _plan(pkg)) == {"p1340": ["lib/a.ritz", "lib/deep/b.ritz"]}

    @pytest.mark.unit
    def test_lib_sources_override_the_package_sources(self, tmp_path):
        """zeus: package sources include test/, which is not library code."""
        pkg = _package(
            tmp_path,
            'sources = ["lib", "test"]\n\n[[lib]]\nname = "p1340"\nsources = ["lib"]\n',
            {"lib/a.ritz": "pub fn a() -> i32\n    1\n",
             "test/t.ritz": "fn t() -> i32\n    0\n"})
        assert _modules(pkg, _plan(pkg)) == {"p1340": ["lib/a.ritz"]}

    @pytest.mark.unit
    def test_lib_sources_honour_exclusions(self, tmp_path):
        pkg = _package(
            tmp_path,
            '[[lib]]\nname = "p1340"\nsources = ["src", "!src/main.ritz"]\n',
            {"src/a.ritz": "pub fn a() -> i32\n    1\n",
             "src/main.ritz": "fn main() -> i32\n    0\n"})
        assert _modules(pkg, _plan(pkg)) == {"p1340": ["src/a.ritz"]}

    @pytest.mark.unit
    def test_lib_and_bin_are_both_planned(self, tmp_path):
        pkg = _package(
            tmp_path,
            'sources = ["src", "lib"]\n\n[[bin]]\nname = "tool"\nentry = "main::main"\n'
            '\n[[lib]]\nname = "p1340"\nsources = ["lib"]\n',
            {"src/main.ritz": "fn main() -> i32\n    0\n",
             "lib/a.ritz": "pub fn a() -> i32\n    1\n"})
        plan = _plan(pkg)
        assert [b.name for b in plan.buildable] == ["tool"]
        assert _modules(pkg, plan) == {"p1340": ["lib/a.ritz"]}

    @pytest.mark.unit
    def test_lib_with_no_modules_is_a_failure(self, tmp_path):
        """A library that compiles nothing must not pass for a built one."""
        pkg = _package(tmp_path, self.LIB_ONLY, {"src/main.ritz": "fn main() -> i32\n    0\n"})
        plan = _plan(pkg)
        assert plan.libraries == []
        assert plan.buildable == []
        assert [u.name for u in plan.unresolved] == ["p1340"]
        assert "lib" in plan.unresolved[0].reason

    @pytest.mark.unit
    def test_test_only_package_still_plans_nothing(self, tmp_path):
        pkg = _package(tmp_path, self.LIB_ONLY + '\n[build]\ntest_only = true\n',
                       {"lib/a.ritz": "pub fn a() -> i32\n    1\n"})
        plan = _plan(pkg)
        assert (plan.buildable, plan.libraries, plan.unresolved) == ([], [], [])


class TestDefaultArm:
    """No [[bin]], no [[lib]]: one binary named after the package, from main."""

    @pytest.mark.unit
    def test_default_sources_still_find_src_main(self, tmp_path):
        pkg = _package(tmp_path, "", {"src/main.ritz": "fn main() -> i32\n    0\n"})
        plan = _plan(pkg)
        assert [(b.name, b.src_path) for b in plan.buildable] == [
            ("p1340", pkg / "src" / "main.ritz")]

    @pytest.mark.unit
    def test_main_is_searched_for_in_declared_sources(self, tmp_path):
        """src/ is outside the declared source set, so it must not win."""
        pkg = _package(tmp_path, 'sources = ["app"]\n', {
            "app/main.ritz": "fn main() -> i32\n    0\n",
            "src/main.ritz": "fn main() -> i32\n    1\n",
        })
        assert [b.src_path for b in _plan(pkg).buildable] == [pkg / "app" / "main.ritz"]

    @pytest.mark.unit
    def test_src_main_outside_declared_sources_is_not_used(self, tmp_path):
        pkg = _package(tmp_path, 'sources = ["app"]\n', {
            "app/other.ritz": "pub fn x() -> i32\n    0\n",
            "src/main.ritz": "fn main() -> i32\n    1\n",
        })
        plan = _plan(pkg)
        assert plan.buildable == []
        assert [u.name for u in plan.unresolved] == ["p1340"]

    @pytest.mark.unit
    def test_missing_main_is_unresolved_and_names_where_it_looked(self, tmp_path):
        pkg = _package(tmp_path, "", {"src/other.ritz": "pub fn x() -> i32\n    0\n"})
        plan = _plan(pkg)
        assert plan.buildable == []
        assert [u.name for u in plan.unresolved] == ["p1340"]
        assert "main.ritz" in plan.unresolved[0].reason
        assert "src" in plan.unresolved[0].reason

    @pytest.mark.unit
    def test_missing_main_fails_the_package(self, tmp_path):
        pkg = _package(tmp_path, "", {"src/other.ritz": "pub fn x() -> i32\n    0\n"})
        result = build.build_package(pkg, _config(pkg))
        assert result.ok is False
        assert result.failed == ["p1340"]


class TestWorkspaceManifests:
    """The real packages: the September audit went stale in eight weeks."""

    @pytest.mark.unit
    def test_cryptosec_compiles_all_of_lib_and_no_binary(self):
        pkg = WORKSPACE / "projects" / "cryptosec"
        plan = build.plan_binaries(pkg, _config(pkg))
        assert plan.buildable == []
        assert _modules(pkg, plan) == {"cryptosec": sorted(
            str(m.relative_to(pkg)) for m in (pkg / "lib").rglob("*.ritz"))}

    @pytest.mark.unit
    def test_goliath_keeps_its_binary_alongside_its_library(self):
        """goliath has a real main and relied on the default arm for it."""
        pkg = WORKSPACE / "projects" / "goliath"
        plan = build.plan_binaries(pkg, _config(pkg))
        assert [(b.name, b.src_path) for b in plan.buildable] == [
            ("goliath", pkg / "src" / "main.ritz")]
        assert "src/main.ritz" not in _modules(pkg, plan)["goliath"]

    @pytest.mark.unit
    def test_zeus_library_excludes_tests_and_entry_points(self):
        pkg = WORKSPACE / "projects" / "zeus"
        modules = _modules(pkg, build.plan_binaries(pkg, _config(pkg)))["zeus"]
        assert modules and all(m.startswith("lib/") for m in modules)

    @pytest.mark.unit
    def test_no_package_plans_a_default_binary_without_a_main(self):
        """Every tracked non-test_only manifest resolves all of its targets."""
        tracked = _manifests()
        assert tracked, "found no manifests; this test would be vacuous"
        unresolved = {}
        for toml in tracked:
            config = tomllib.loads(toml.read_text())
            if "bin" in config:     # #1314 owns a declared [[bin]]'s resolution
                continue
            plan = build.plan_binaries(toml.parent, config)
            if plan.unresolved:
                unresolved[str(toml.relative_to(WORKSPACE))] = plan.unresolved
        assert unresolved == {}


def _manifests() -> list[Path]:
    """Package manifests in the tree, minus retired code nothing should build."""
    found = []
    for root in (WORKSPACE / "projects", WORKSPACE / "bench" / "regressions"):
        for toml in root.rglob("ritz.toml"):
            parts = toml.relative_to(WORKSPACE).parts
            if "build" in parts or ("docs" in parts and "archive" in parts):
                continue
            found.append(toml)
    return found


# Real build.py runs share .ritz-cache (#1804, conftest.py).
@pytest.mark.xdist_group("tree")
class TestLibraryBuild:
    """Real ritz0, real clang, real archive."""

    MANIFEST = 'sources = ["lib"]\n\n[[lib]]\nname = "p1340"\n'
    # Nothing imports b: only a build that walks `sources` compiles it.
    FILES = {
        "lib/a.ritz": "pub fn p1340_alpha() -> i32\n    1\n",
        "lib/b.ritz": "pub fn p1340_beta() -> i32\n    2\n",
        "src/main.ritz": "fn main() -> i32\n    0\n",
    }

    def _build(self, pkg: Path):
        env = dict(os.environ, RITZ_PATH=str(RITZ_DIR))
        return subprocess.run(
            [sys.executable, "build.py", "build", str(pkg)],
            cwd=RITZ_DIR, env=env, capture_output=True, text=True, timeout=600)

    def _symbols(self, archive: Path) -> str:
        return subprocess.run(["nm", str(archive)], capture_output=True, text=True,
                              check=True).stdout

    @pytest.mark.integration
    def test_every_module_lands_in_the_archive_and_no_binary_exists(self, tmp_path):
        pkg = _package(tmp_path, self.MANIFEST, self.FILES)
        proc = self._build(pkg)
        output = proc.stdout + proc.stderr
        assert proc.returncode == 0, output
        out = pkg / "build" / "debug"
        symbols = self._symbols(out / "libp1340.a")
        assert "p1340_alpha" in symbols and "p1340_beta" in symbols, output
        assert not (out / "p1340").exists(), "a lib-only package linked a binary"
        assert not (pkg / "p1340").exists(), "a lib-only package got a binary symlink"

    @pytest.mark.integration
    def test_a_broken_unimported_module_fails_the_build(self, tmp_path):
        """The acceptance test: lib-only packages must be able to fail."""
        pkg = _package(tmp_path, self.MANIFEST, dict(
            self.FILES, **{"lib/b.ritz": "fn broken() -> i32\n    @@@ not ritz @@@\n"}))
        proc = self._build(pkg)
        output = proc.stdout + proc.stderr
        assert proc.returncode != 0, "a library with a broken module built\n" + output
        assert "b.ritz" in output, output
        assert not (pkg / "build" / "debug" / "libp1340.a").exists(), output

    @pytest.mark.integration
    def test_failed_rebuild_does_not_leave_the_old_archive_looking_current(self, tmp_path):
        pkg = _package(tmp_path, self.MANIFEST, self.FILES)
        assert self._build(pkg).returncode == 0
        (pkg / "lib" / "b.ritz").write_text("fn broken() -> i32\n    @@@ not ritz @@@\n")
        # Twice: the first failure must not be remembered as a build.
        assert self._build(pkg).returncode != 0
        assert self._build(pkg).returncode != 0

    @pytest.mark.integration
    def test_second_build_is_up_to_date_and_says_so(self, tmp_path):
        """The #1360 rule: never print 🔨/✓ for work that was not done."""
        pkg = _package(tmp_path, self.MANIFEST, self.FILES)
        assert self._build(pkg).returncode == 0
        archive = pkg / "build" / "debug" / "libp1340.a"
        before = archive.stat().st_mtime_ns
        proc = self._build(pkg)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "up to date" in proc.stdout
        assert "🔨" not in proc.stdout
        assert archive.stat().st_mtime_ns == before

    @pytest.mark.integration
    def test_editing_a_module_rebuilds_the_archive(self, tmp_path):
        pkg = _package(tmp_path, self.MANIFEST, self.FILES)
        assert self._build(pkg).returncode == 0
        (pkg / "lib" / "b.ritz").write_text("pub fn p1340_gamma() -> i32\n    3\n")
        proc = self._build(pkg)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "🔨" in proc.stdout
        symbols = self._symbols(pkg / "build" / "debug" / "libp1340.a")
        assert "p1340_gamma" in symbols and "p1340_beta" not in symbols

    @pytest.mark.integration
    def test_editing_an_import_outside_the_library_rebuilds_the_archive(self, tmp_path):
        """A module's object depends on its imports, which are not in `modules`."""
        pkg = _package(
            tmp_path,
            'sources = ["lib", "support"]\n\n[[lib]]\nname = "p1340"\nsources = ["lib"]\n',
            {"lib/a.ritz": "import helper\n\npub fn p1340_alpha() -> i32\n    helper_value()\n",
             "support/helper.ritz": "pub fn helper_value() -> i32\n    1\n"})
        assert self._build(pkg).returncode == 0
        (pkg / "support" / "helper.ritz").write_text(
            "pub fn helper_value() -> i64\n    1\n")
        proc = self._build(pkg)
        assert "up to date" not in proc.stdout, proc.stdout + proc.stderr

    @pytest.mark.integration
    def test_removing_a_module_drops_it_from_the_archive(self, tmp_path):
        pkg = _package(tmp_path, self.MANIFEST, self.FILES)
        assert self._build(pkg).returncode == 0
        (pkg / "lib" / "b.ritz").unlink()
        assert self._build(pkg).returncode == 0
        symbols = self._symbols(pkg / "build" / "debug" / "libp1340.a")
        assert "p1340_alpha" in symbols and "p1340_beta" not in symbols

    @pytest.mark.integration
    def test_lib_and_bin_build_together(self, tmp_path):
        pkg = _package(
            tmp_path,
            '[[bin]]\nname = "tool"\nentry = "main::main"\n'
            '\n[[lib]]\nname = "p1340"\nsources = ["lib"]\n',
            self.FILES)
        # The package's sources default to src/, so tool never sees lib/.
        proc = self._build(pkg)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        out = pkg / "build" / "debug"
        assert (out / "tool").exists()
        assert "p1340_beta" in self._symbols(out / "libp1340.a")
