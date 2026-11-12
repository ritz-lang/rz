"""RITZ_BUILD_CACHE_DIR moves build.py's per-project cache (AGAST #2793).

`BuildCache` keeps `.ritz-cache` (ritz0) / `.ritz-cache-<compiler>` next to
the project.  For projects/ritz that is the source tree, shared by every
build in the worktree.  The ritz0 suite builds hundreds of throwaway packages
through build.py; it used to pass `--no-cache` so those builds left the tree's
cache alone (the `xdist_group("tree")` tests inspect it), which also meant
every case recompiled ritzlib from scratch, 3-6 s a case.

With RITZ_BUILD_CACHE_DIR set, the cache directory lives under it instead,
so a test can keep the content-addressed store (RITZ_CACHE_DIR) and its
ritzlib hits while its per-project index stays out of the tree.
"""

import importlib.util
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("ritz_cache_2793", PKG_DIR / "cache.py")
_cache_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cache_mod)
BuildCache = _cache_mod.BuildCache


def test_default_is_next_to_the_project(tmp_path, monkeypatch):
    monkeypatch.delenv("RITZ_BUILD_CACHE_DIR", raising=False)
    assert BuildCache(project_root=tmp_path).cache_dir == tmp_path / ".ritz-cache"
    assert (BuildCache(project_root=tmp_path, compiler="ritz1").cache_dir
            == tmp_path / ".ritz-cache-ritz1")


def test_env_moves_it_and_keeps_compilers_apart(tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    monkeypatch.setenv("RITZ_BUILD_CACHE_DIR", str(elsewhere))
    project = tmp_path / "project"
    assert BuildCache(project_root=project).cache_dir == elsewhere / ".ritz-cache"
    assert (BuildCache(project_root=project, compiler="ritz1").cache_dir
            == elsewhere / ".ritz-cache-ritz1")


def test_empty_env_is_unset(tmp_path, monkeypatch):
    monkeypatch.setenv("RITZ_BUILD_CACHE_DIR", "")
    assert BuildCache(project_root=tmp_path).cache_dir == tmp_path / ".ritz-cache"
