"""`build.py test` through another tree's symlink runs in a per-root dir.

AGAST #3831 (found in #3818): `build.py build` sends a package reached
through a foreign symlink (an overlay root's `examples -> real/examples`)
to `ROOT/build/linked/<name>-<hash>/<profile>/`, but `build.py test` still
built into the shared `<pkg>/build/<profile>/` and refreshed the shared
`<pkg>/<name>` link its tests exec as `./<name>`. Two overlays testing one
package in parallel could each test the other's binary.

The rule: such a test builds where `build` does, and runs its test files
and test.sh with cwd in a per-root shadow of the package,
`ROOT/build/linked/<name>-<hash>/cwd-<profile>/`: one symlink per package
entry (never `build/` or a `<name>` link), plus `<name>` -> this root's
binary. Nothing is written into the shared package dir. `build.py clean`
removes `ROOT/build/linked/`.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
BUILD_PY = PKG_DIR / "build.py"
EXAMPLE = PKG_DIR / "examples" / "tier1_basics" / "02_exitcode"


@pytest.fixture
def buildpy(request):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_3831", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Unit: the shadow cwd.
# ---------------------------------------------------------------------------


def _pkg(tmp_path: Path) -> tuple[Path, dict]:
    pkg = tmp_path / "real" / "foo"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text("fn main() -> i32\n    0\n")
    (pkg / "test").mkdir()
    (pkg / "test.sh").write_text("./foo\n")
    (pkg / "data.txt").write_text("x")
    (pkg / "build" / "debug").mkdir(parents=True)
    (pkg / "foo").symlink_to("build/debug/foo")   # another tree's link
    config = {"package": {"name": "foo"},
              "bin": [{"name": "foo", "entry": "main::main"}]}
    return pkg, config


@pytest.mark.unit
def test_unit_plain_package_runs_in_its_own_dir(buildpy, tmp_path):
    pkg, config = _pkg(tmp_path)
    assert buildpy.test_run_dir(pkg, config, pkg / "build" / "debug") == pkg


@pytest.mark.unit
def test_unit_linked_package_runs_in_a_per_root_shadow(buildpy, tmp_path):
    pkg, config = _pkg(tmp_path)
    out_dir = tmp_path / "A" / "build" / "linked" / "foo-abc" / "debug"
    out_dir.mkdir(parents=True)
    run = buildpy.test_run_dir(pkg, config, out_dir)
    assert run == out_dir.parent / "cwd-debug"
    # Every package entry, through a link to the real one...
    for name in ("src", "test", "test.sh", "data.txt"):
        assert (run / name).is_symlink()
        assert (run / name).resolve() == (pkg / name).resolve()
    # ...but never the shared build/, and `./foo` is THIS root's binary.
    assert not (run / "build").exists() and not (run / "build").is_symlink()
    assert os.readlink(run / "foo") == str(out_dir / "foo")
    # Idempotent: a second call (the next --unit-file) rebuilds nothing.
    assert buildpy.test_run_dir(pkg, config, out_dir) == run
    assert os.readlink(run / "foo") == str(out_dir / "foo")


@pytest.mark.unit
def test_unit_shadow_drops_entries_the_package_lost(buildpy, tmp_path):
    pkg, config = _pkg(tmp_path)
    out_dir = tmp_path / "A" / "build" / "linked" / "foo-abc" / "debug"
    out_dir.mkdir(parents=True)
    run = buildpy.test_run_dir(pkg, config, out_dir)
    (pkg / "data.txt").unlink()
    buildpy.test_run_dir(pkg, config, out_dir)
    assert not (run / "data.txt").is_symlink()


@pytest.mark.unit
def test_unit_clean_removes_linked_outputs(buildpy, tmp_path, monkeypatch):
    build_cli = importlib.import_module("build_cli")

    linked = tmp_path / "build" / "linked" / "foo-abc" / "debug"
    linked.mkdir(parents=True)
    monkeypatch.setattr(build_cli, "ROOT", tmp_path)
    monkeypatch.setattr(build_cli, "find_packages", lambda: [])
    monkeypatch.setattr(
        build_cli, "get_build_cache",
        lambda: SimpleNamespace(cache_dir=tmp_path / "no-cache"))
    build_cli.cmd_clean(SimpleNamespace())
    assert not (tmp_path / "build" / "linked").exists()
    assert (tmp_path / "build").is_dir()   # only linked/ is ours to remove


# ---------------------------------------------------------------------------
# End to end: real `build.py test` through an overlay path.
# ---------------------------------------------------------------------------

DECOY = "#!/bin/sh\nexit 7\n"


@pytest.fixture
def overlay(buildpy, tmp_path):
    """02_exitcode (test.sh only: `./exitcode` must exit 42) shared by an
    overlay root A through `A/examples -> real`. The shared dir holds a
    decoy `exitcode` exiting 7: the other tree's binary, as far as A is
    concerned."""
    real = tmp_path / "real"
    shared = real / "exitcode_pkg"
    shutil.copytree(EXAMPLE, shared,
                    ignore=shutil.ignore_patterns("build", "exitcode", "test"))
    (shared / "exitcode").write_text(DECOY)
    (shared / "exitcode").chmod(0o755)
    (tmp_path / "A").mkdir()
    (tmp_path / "A" / "examples").symlink_to(real)
    via_a = tmp_path / "A" / "examples" / "exitcode_pkg"
    yield shared, via_a
    # This overlay's per-root dir and nothing else: other xdist workers'
    # dirs appear under the same build/linked/ meanwhile.
    out_dir = buildpy.get_output_dir(shared.resolve(), {"name": "debug"},
                                     invoked_as=via_a)
    assert out_dir.parent.parent == PKG_DIR / "build" / "linked"
    shutil.rmtree(out_dir.parent, ignore_errors=True)


def run_test(args, cwd=PKG_DIR):
    env = dict(os.environ, RITZ_PATH=str(PKG_DIR))
    return subprocess.run([sys.executable, str(BUILD_PY), "test"] + args,
                          capture_output=True, text=True, cwd=cwd, env=env,
                          check=False)


def _assert_shared_untouched(shared: Path):
    assert not (shared / "build").exists()
    assert not (shared / "exitcode").is_symlink()
    assert (shared / "exitcode").read_text() == DECOY


@pytest.mark.integration
def test_e2e_overlay_test_runs_its_own_binary(overlay):
    shared, via_a = overlay
    r = run_test([str(via_a)])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "test.sh passed" in r.stdout
    _assert_shared_untouched(shared)


@pytest.mark.unit
def test_unit_file_mode_runs_in_the_shadow(buildpy, overlay, tmp_path, monkeypatch):
    """`--unit-file` builds nothing; it must still run in the run dir its
    `--unit-plan` built for, recomputed from the same package path."""
    build_cli = importlib.import_module("build_cli")

    shared, via_a = overlay
    seen = []
    monkeypatch.setattr(build_cli, "unit_file",
                        lambda run_dir, *a, **kw: seen.append(run_dir) or 0)
    args = SimpleNamespace(all=False, name=str(via_a), unit_plan=None,
                           unit_file="t.ritz", unit_result="r.json",
                           unit_test_sh=False)
    assert build_cli.cmd_test(args) == 0
    assert seen and seen[0].name == "cwd-debug"
    assert seen[0].is_relative_to(PKG_DIR / "build" / "linked")


@pytest.mark.integration
def test_e2e_overlay_unit_mode_runs_its_own_binary(overlay, tmp_path):
    """rz's `--unit-plan` then `--unit-test-sh`, as `rz test -j N` runs them."""
    shared, via_a = overlay
    plan = tmp_path / "plan.json"
    r = run_test([str(via_a), "--unit-plan", str(plan)])
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(plan.read_text())["test_sh"] is True
    r = run_test([str(via_a), "--unit-test-sh"])
    assert r.returncode == 0, r.stdout + r.stderr
    _assert_shared_untouched(shared)
