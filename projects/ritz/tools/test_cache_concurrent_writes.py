"""BuildCache writes must be safe with several build.py processes (AGAST #1806).

regression.sh now builds up to REGRESSION_JOBS examples at once, and every
build.py process shares one `.ritz-cache` under projects/ritz. Before this:

* the shared index was rewritten wholesale from each process's in-memory
  copy, so the last process to save dropped every entry the others had added.
* index files and `compiler_hash` were written in place. A concurrent reader
  could see a truncated file.
* `imports.json` went through one fixed `imports.json.tmp`, which two writers
  shared.

The tests below pin each of those for what the cache holds today, the import
scans (`imports.json`) and `compiler_hash`. (The per-module .ll/.o store they
also covered was deleted by AGAST #3454; artifacts live in cas.py.)
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("ritz_cache_1806", PKG_DIR / "cache.py")
_cache_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cache_mod)
BuildCache = _cache_mod.BuildCache


def _project(tmp_path: Path, names) -> list:
    """A project root with a ritz0/ tree (for the fingerprint) and sources."""
    (tmp_path / "ritz0").mkdir(exist_ok=True)
    (tmp_path / "ritz0" / "ritz0.py").write_text("# fake compiler\n")
    srcs = []
    for n in names:
        p = tmp_path / f"{n}.ritz"
        p.write_text(f"fn {n}() -> i32\n    0\n")
        srcs.append(p)
    return srcs


def _cache(root: Path) -> BuildCache:
    c = BuildCache(project_root=root)
    c.set_import_context(project_root=root)
    return c


def _scanned(root: Path) -> set:
    """Source paths with a persisted import scan."""
    db = json.loads((root / ".ritz-cache" / "imports.json").read_text())
    return {k.rsplit("\0", 1)[-1] for k in db}


def _scan(root: Path, src: Path, cache=None) -> None:
    """What one build.py process does for one module: closure, then save."""
    c = cache or _cache(root)
    c.get_transitive_dependencies(src)
    c.save()


@pytest.mark.unit
def test_two_processes_saving_keep_each_others_entries(tmp_path):
    """Last writer must not drop the other process's imports.json entries."""
    a, b = _project(tmp_path, ["a", "b"])
    ca, cb = _cache(tmp_path), _cache(tmp_path)
    # Both load the (empty) store before either saves: two build.py processes
    # started at the same time.
    assert ca._load_imports_db() == {} and cb._load_imports_db() == {}
    _scan(tmp_path, a, ca)
    _scan(tmp_path, b, cb)
    scanned = _scanned(tmp_path)
    assert str(a.resolve()) in scanned, "process B's save dropped A's entry"
    assert str(b.resolve()) in scanned


def _reader_sees_old_content(path: Path, write) -> bool:
    """Open `path`, run `write()`, then read through the old descriptor.

    An atomic tmp+rename leaves the reader on the old inode, so it reads the
    old bytes intact. An in-place rewrite truncates the very file the reader
    holds, which is the torn read a concurrent process can hit.
    """
    old = path.read_bytes()
    with open(path, "rb") as f:
        write()
        return f.read() == old


@pytest.mark.unit
def test_imports_json_is_replaced_atomically(tmp_path):
    a, b = _project(tmp_path, ["a", "b"])
    _scan(tmp_path, a)
    db = tmp_path / ".ritz-cache" / "imports.json"
    assert _reader_sees_old_content(db, lambda: _scan(tmp_path, b))


@pytest.mark.unit
def test_compiler_hash_is_replaced_atomically(tmp_path):
    _project(tmp_path, ["a"])
    _cache(tmp_path).invalidate_if_compiler_changed()
    h = tmp_path / ".ritz-cache" / "compiler_hash"
    (tmp_path / "ritz0" / "ritz0.py").write_text("# changed compiler\n")
    assert _reader_sees_old_content(h, lambda: _cache(tmp_path).invalidate_if_compiler_changed())


@pytest.mark.unit
def test_imports_db_has_no_shared_tmp_file(tmp_path, monkeypatch):
    """Two writers must not share one `imports.json.tmp`."""
    (a,) = _project(tmp_path, ["a"])
    seen = []
    real_replace = os.replace

    def spy(src, dst):
        seen.append((str(src), str(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(_cache_mod.os, "replace", spy)
    _scan(tmp_path, a)
    tmps = [s for s, d in seen if d.endswith("imports.json")]
    assert tmps, "imports.json is not written through os.replace"
    assert all(not s.endswith("imports.json.tmp") for s in tmps), tmps


_WORKER = r"""
import importlib.util, sys, time
from pathlib import Path
spec = importlib.util.spec_from_file_location("c", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
root, name, go = Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
src = root / f"{name}.ritz"
c = m.BuildCache(project_root=root)
c.set_import_context(project_root=root)
while not go.exists():  # start together, like a pool's first wave
    time.sleep(0.005)
c.invalidate_if_compiler_changed()
c.get_transitive_dependencies(src)
c.save()
"""


@pytest.mark.unit
def test_concurrent_processes_all_land(tmp_path):
    """Eight processes building at once, as regression.sh's pool does."""
    names = [f"m{i}" for i in range(8)]
    srcs = _project(tmp_path, names)
    go = tmp_path / "go"
    procs = [
        subprocess.Popen([sys.executable, "-c", _WORKER, str(PKG_DIR / "cache.py"),
                          str(tmp_path), n, str(go)])
        for n in names
    ]
    go.write_text("")
    for p in procs:
        assert p.wait(60) == 0
    scanned = _scanned(tmp_path)
    for n, s in zip(names, srcs):
        assert str(s.resolve()) in scanned, f"{n} lost from imports.json"
