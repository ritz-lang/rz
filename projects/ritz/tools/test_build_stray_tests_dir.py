"""A package's `tests/` holding .ritz files is a hard error (AGAST #1386).

build.py discovers test files in `test/` (singular) only. Five packages kept
theirs in `tests/`, following a comment in `rz` that claimed build.py globbed
both. It never did: 284 [[test]] functions ran under no gate while every
gate reported green. Each package was then migrated to `test/`.

The fix was deliberately NOT "also glob tests/". That would make two
conventions permanent. Instead a stray `tests/*.ritz` fails the build and
names every file that would never have run, so the next package to drift is
caught on its first `rz test`.

Allowed:
  * `tests/` that is its own package (has a ritz.toml), e.g. ritzlib's
    `ritzlib/tests`. That is a separate package with its own discovery.
  * `tests/` with no .ritz in it (angelo's `tests/fixtures`).
"""

import importlib.util
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_DIR.parents[1]


@pytest.fixture
def buildpy(request):
    # build.py does `from cache import BuildCache`, so its directory must be
    # importable while we exec it by path.
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_1386", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_pkg(root: Path, name: str = "stray") -> Path:
    pkg = root / name
    pkg.mkdir()
    (pkg / "ritz.toml").write_text(
        textwrap.dedent(
            f"""\
            [package]
            name = "{name}"
            version = "0.1.0"

            [build]
            test_only = true
            """
        )
    )
    return pkg


def write(path: Path, text: str = "[[test]]\nfn test_x() -> i32\n    0\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_stray_tests_dir_raises_naming_every_file(tmp_path, buildpy):
    pkg = make_pkg(tmp_path)
    write(pkg / "tests" / "test_a.ritz")
    write(pkg / "tests" / "deep" / "test_b.ritz")
    with pytest.raises(buildpy.StrayTestsDirError) as exc:
        buildpy.discover_test_files(pkg, {"build": {"test_only": True}})
    msg = str(exc.value)
    assert "tests/test_a.ritz" in msg
    assert "tests/deep/test_b.ritz" in msg
    assert "test/" in msg  # tells the user where they belong


def test_test_dir_alone_is_fine(tmp_path, buildpy):
    pkg = make_pkg(tmp_path)
    f = write(pkg / "test" / "test_a.ritz")
    assert buildpy.discover_test_files(pkg, {}) == [f]


def test_tests_dir_without_ritz_files_is_fine(tmp_path, buildpy):
    # angelo keeps non-.ritz fixtures in tests/fixtures.
    pkg = make_pkg(tmp_path)
    write(pkg / "tests" / "fixtures" / "input.txt", "data\n")
    assert buildpy.stray_test_files(pkg) == []
    assert buildpy.discover_test_files(pkg, {}) == []


def test_tests_dir_that_is_its_own_package_is_fine(tmp_path, buildpy):
    # ritzlib/tests is a package (name = "ritzlib-tests"); it is not stray.
    pkg = make_pkg(tmp_path)
    nested = pkg / "tests"
    nested.mkdir()
    (nested / "ritz.toml").write_text('[package]\nname = "nested"\nversion = "0.1.0"\n')
    write(nested / "test_a.ritz")
    assert buildpy.stray_test_files(pkg) == []


def test_cli_fails_loudly_without_traceback(tmp_path):
    pkg = make_pkg(tmp_path)
    write(pkg / "tests" / "test_a.ritz")
    r = subprocess.run(
        [sys.executable, str(PKG_DIR / "build.py"), "test", str(pkg)],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "tests/test_a.ritz" in r.stderr
    assert "Traceback" not in r.stderr


def test_no_package_in_the_repo_has_stray_tests(buildpy):
    # The sweep from AGAST #1386's verification: zero tests/*.ritz anywhere.
    offenders = []
    for manifest in REPO_ROOT.rglob("ritz.toml"):
        parts = manifest.relative_to(REPO_ROOT).parts
        if parts[0] in (".git", "archive") or "target" in parts:
            continue
        offenders += buildpy.stray_test_files(manifest.parent)
    assert offenders == []
