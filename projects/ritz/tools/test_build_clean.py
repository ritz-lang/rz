"""`build.py clean` removes what a build writes (AGAST #2206).

`make clean` runs `build.py clean`. Its loop unpacked each `BinaryConfig`
from `get_binaries()` as a 3-tuple (`for bin_name, _, _ in binaries`), a
leftover from when targets were tuples, so it raised TypeError on the first
package with a binary. It also looked for `<pkg>/<bin>`, where nothing has
been written since RFC #109 moved outputs to `<pkg>/build/<profile>/`, and
never touched the `lib<name>.a` archives that live there too.

Each test runs against a throwaway package under tmp_path: ROOT,
find_packages and the build cache are all pointed there, so nothing in the
real tree can be deleted.
"""

import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]

TOML = """\
[package]
name = "pkg_2206"
version = "0.1.0"

[[bin]]
name = "app"
path = "src/main.ritz"

[[lib]]
name = "util"
path = "src/main.ritz"
"""


@pytest.fixture
def buildpy(request):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_2206", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sandbox(buildpy, tmp_path, monkeypatch):
    """A built-looking package under tmp_path, which build.py treats as ROOT."""
    root = tmp_path / "root"
    pkg = root / "pkg_2206"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text("fn main() -> i32\n    0\n")
    (pkg / "ritz.toml").write_text(TOML)
    for profile in ("debug", "release"):
        out = pkg / "build" / profile
        out.mkdir(parents=True)
        (out / "app").write_text("binary")
        (out / "libutil.a").write_text("archive")
    config = tomllib.loads(TOML)
    assert [b.name for b in buildpy.get_binaries(pkg, config)] == ["app"]

    monkeypatch.setattr(buildpy, "ROOT", root)
    monkeypatch.setattr(buildpy, "find_packages", lambda: [(pkg, config)])
    monkeypatch.delenv("RITZ_BUILD_CACHE_DIR", raising=False)
    monkeypatch.setattr(buildpy, "_build_cache", {})
    real_cache = buildpy.BuildCache
    monkeypatch.setattr(buildpy, "BuildCache",
                        lambda project_root, compiler="ritz0": real_cache(root, compiler))
    return pkg


def _clean(buildpy):
    return buildpy.cmd_clean(None) or 0


def test_removes_profile_outputs(buildpy, sandbox, capsys):
    assert _clean(buildpy) == 0
    assert not (sandbox / "build" / "debug").exists()
    assert not (sandbox / "build" / "release").exists()
    assert "✓ Cleaned" in capsys.readouterr().out


def test_keeps_sources_and_unrelated_build_files(buildpy, sandbox):
    keep = sandbox / "build" / "notes.txt"
    keep.write_text("not a build output")
    assert _clean(buildpy) == 0
    assert (sandbox / "src" / "main.ritz").exists()
    assert (sandbox / "ritz.toml").exists()
    assert keep.exists()


def test_cache_dir_outside_root(buildpy, sandbox, tmp_path, monkeypatch):
    """RITZ_BUILD_CACHE_DIR (#2793) can put the cache outside ROOT."""
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv("RITZ_BUILD_CACHE_DIR", str(elsewhere))
    cache = buildpy.get_build_cache()
    cache.cache_dir.mkdir(parents=True, exist_ok=True)
    assert elsewhere in cache.cache_dir.parents
    assert _clean(buildpy) == 0
    assert not cache.cache_dir.exists()


def test_removes_build_run_outputs(buildpy, sandbox):
    """`build.py run` links each source under ROOT/build/run/<digest>/
    (#2252); every pytest session adds some, so clean removes them (#4167)."""
    root = sandbox.parent
    run_dir = root / "build" / "run" / "0123456789abcdef"
    run_dir.mkdir(parents=True)
    (run_dir / "main").write_text("binary")
    keep = root / "build" / "notes.txt"
    keep.write_text("not ours")
    assert _clean(buildpy) == 0
    assert not (root / "build" / "run").exists()
    assert keep.exists()   # only build/run/ is removed, not ROOT/build
