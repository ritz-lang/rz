"""A package reached through a symlink builds into a per-root output dir.

AGAST #3818 (found in #1499): overlay roots or worktrees that reach one
package dir through a symlink (e.g. /tmp/mut/<name>/examples ->
projects/ritz/examples) all wrote `<resolved pkg>/build/<profile>/<bin>`.
Built in parallel, the binary there when `build.py build` returned was
whichever tree linked last, so a caller that ran it at once could run the
OTHER tree's binary (3 of 3 rounds in the ticket's repro). #1499 stopped
the manifest certifying a foreign binary; this closes the transient half.

The rule (build.py `get_output_dir`): when the path the package was invoked
by crosses a symlink that is not an ancestor of the invoking ROOT, outputs
go to `ROOT/build/linked/<name>-<hash of the logical path>/<profile>/`,
which no other tree writes. A symlink above ROOT (e.g. a symlinked home or
~/dev) is shared by the whole tree and redirects nothing, so ordinary builds
keep `<pkg>/build/<profile>/`. The build prints the binary's path, and the
`<pkg>/<name>` convenience link is not written into the shared package dir.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
BUILD_PY = PKG_DIR / "build.py"
EXAMPLE = PKG_DIR / "examples" / "tier1_basics" / "02_exitcode"
PROFILE = {"name": "debug", "opt_level": 0, "debug": True, "lto": False}


@pytest.fixture
def buildpy(request):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_3818", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def trees(tmp_path):
    """One real package and two overlay roots A and B whose `examples`
    symlinks into the real tree, as the #1448 mutation run had them."""
    real_examples = tmp_path / "real" / "examples"
    pkg = real_examples / "foo"
    pkg.mkdir(parents=True)
    roots = []
    for name in ("A", "B"):
        root = tmp_path / "mut" / name
        root.mkdir(parents=True)
        (root / "examples").symlink_to(real_examples)
        roots.append(root)
    return pkg.resolve(), roots[0], roots[1]


# ---------------------------------------------------------------------------
# Unit: the output-dir rule.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unit_plain_package_keeps_its_own_build_dir(buildpy, trees, monkeypatch):
    pkg, _, _ = trees
    monkeypatch.setattr(buildpy, "ROOT", pkg.parent.parent)
    assert buildpy.get_output_dir(pkg, PROFILE) == pkg / "build" / "debug"
    assert (
        buildpy.get_output_dir(pkg, PROFILE, invoked_as=pkg) == pkg / "build" / "debug"
    )


@pytest.mark.unit
def test_unit_symlinked_package_builds_under_invoking_root(buildpy, trees, monkeypatch):
    pkg, a, _ = trees
    monkeypatch.setattr(buildpy, "ROOT", a)
    out = buildpy.get_output_dir(pkg, PROFILE, invoked_as=a / "examples" / "foo")
    assert out.parent.parent == a / "build" / "linked"
    assert out.name == "debug"
    assert out.parent.name.startswith("foo-")
    assert not out.resolve().is_relative_to(pkg)


@pytest.mark.unit
def test_unit_two_trees_never_share_an_output_dir(buildpy, trees, monkeypatch):
    """Even with one ROOT/build (an overlay that symlinks build/ too), the
    logical path keys the dir, so the two trees still get their own."""
    pkg, a, b = trees
    monkeypatch.setattr(buildpy, "ROOT", a)
    out_a = buildpy.get_output_dir(pkg, PROFILE, invoked_as=a / "examples" / "foo")
    out_b = buildpy.get_output_dir(pkg, PROFILE, invoked_as=b / "examples" / "foo")
    assert out_a != out_b


@pytest.mark.unit
def test_unit_invoked_as_toml_file_is_its_package(buildpy, trees, monkeypatch):
    pkg, a, _ = trees
    (pkg / "ritz.toml").write_text("")
    monkeypatch.setattr(buildpy, "ROOT", a)
    via_dir = buildpy.get_output_dir(pkg, PROFILE, invoked_as=a / "examples" / "foo")
    via_toml = buildpy.get_output_dir(
        pkg, PROFILE, invoked_as=a / "examples" / "foo" / "ritz.toml"
    )
    assert via_dir == via_toml


@pytest.mark.unit
def test_unit_symlink_above_root_redirects_nothing(buildpy, tmp_path, monkeypatch):
    """A symlinked home / ~/dev is an ancestor of ROOT: one tree, no race."""
    (tmp_path / "data" / "projects" / "ritz" / "examples" / "foo").mkdir(parents=True)
    (tmp_path / "dev").symlink_to(tmp_path / "data")
    root = tmp_path / "dev" / "projects" / "ritz"
    monkeypatch.setattr(buildpy, "ROOT", root)
    logical = root / "examples" / "foo"
    pkg = logical.resolve()
    assert (
        buildpy.get_output_dir(pkg, PROFILE, invoked_as=logical)
        == pkg / "build" / "debug"
    )


# ---------------------------------------------------------------------------
# End to end: real `build.py build` through two overlay paths.
# ---------------------------------------------------------------------------


@pytest.fixture
def overlay(tmp_path):
    real = tmp_path / "real"
    shutil.copytree(
        EXAMPLE,
        real / "exitcode_pkg",
        ignore=shutil.ignore_patterns("build", "exitcode"),
    )
    paths = []
    for name in ("A", "B"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "examples").symlink_to(real)
        paths.append(tmp_path / name / "examples" / "exitcode_pkg")
    made = []
    yield real / "exitcode_pkg", paths, made
    for d in made:
        shutil.rmtree(d, ignore_errors=True)


def build(arg, cwd, env_extra=None):
    env = dict(os.environ, RITZ_PATH=str(PKG_DIR), **(env_extra or {}))
    cmd = [sys.executable, str(BUILD_PY), "build"] + ([str(arg)] if arg else [])
    r = subprocess.run(
        cmd, capture_output=True, text=True, cwd=cwd, env=env, check=False
    )
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def reported_binary(stdout: str, cwd: Path = PKG_DIR) -> Path:
    """The binary path the build printed (display_path: relative to ROOT,
    else to cwd, else absolute)."""
    line = next(l for l in stdout.splitlines() if l.strip().startswith(("✓", "=")))
    p = Path(line.split()[-1])
    if p.is_absolute():
        return p
    return PKG_DIR / p if (PKG_DIR / p).exists() else cwd / p


@pytest.mark.integration
def test_e2e_two_overlays_get_their_own_binaries(overlay):
    shared, (a, b), made = overlay
    out_a = reported_binary(build(a, cwd=PKG_DIR))
    made.append(out_a.parent.parent)
    out_b = reported_binary(build(b, cwd=PKG_DIR))
    made.append(out_b.parent.parent)
    assert out_a != out_b
    assert out_a.is_file() and out_b.is_file()
    for out in (out_a, out_b):
        assert out.is_relative_to(PKG_DIR / "build" / "linked")
    # Nothing written into the package dir both trees share.
    assert not (shared / "build").exists()
    assert not (shared / "exitcode").exists() and not (shared / "exitcode").is_symlink()


@pytest.mark.integration
def test_e2e_build_from_overlay_cwd_uses_logical_pwd(overlay):
    """`cd <overlay pkg> && build.py build`: getcwd() is already resolved, so
    the logical path comes from $PWD."""
    shared, (a, _), made = overlay
    out = reported_binary(build(None, cwd=a, env_extra={"PWD": str(a)}), cwd=a)
    made.append(out.parent.parent)
    assert out.is_relative_to(PKG_DIR / "build" / "linked")
    assert not (shared / "build").exists()
