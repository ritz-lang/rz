"""AGAST #2794: ArtifactStore.gc races concurrent gc and readers.

Every gate ends with `ci_local.trim_cas()` -> `ArtifactStore().gc()` on the
machine-wide store while other gates and rooms build from it. Two races:

* gc scans with `is_file()` then `stat()`; a concurrent gc unlinking the file
  between the two raised FileNotFoundError and crashed the gate's trim.
* a reader hits (`is_file()`), then copies the stored object out; a gc in
  between made the copy raise and the build fail on a cache hit.
  `ArtifactStore.fetch` treats a vanished object as a miss and rebuilds.

The races are forced deterministically by unlinking the file between the two
calls (monkeypatched), plus one real two-process gc smoke on a private store.
Every store lives under tmp_path, never the shared ~/.cache/ritz/cas.
"""

import ast
import importlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
RITZ0_DIR = PKG_DIR / "ritz0"
for d in (str(PKG_DIR), str(RITZ0_DIR)):
    if d not in sys.path:
        sys.path.insert(0, d)

cas = importlib.import_module("cas")

HAS_CLANG = shutil.which("clang") is not None
KEY = "5f" + "a" * 62


@pytest.fixture(autouse=True)
def private_store(tmp_path, monkeypatch):
    root = tmp_path / "cas"
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(root))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    monkeypatch.setattr(cas, "STATS", cas.Stats())
    return root


def _populate(store, tmp_path, n=6, size=100) -> list:
    keys = []
    for i in range(n):
        key = f"{i:02x}" + "b" * 62
        src = tmp_path / f"src{i}.o"
        src.write_bytes(bytes([i]) * size)
        store.put(key, "o", src)
        store.put_meta(key, {"i": i})
        os.utime(store.path(key, "o"), (1000 + i, 1000 + i))
        keys.append(key)
    return keys


# --- gc vs gc --------------------------------------------------------------


@pytest.mark.unit
def test_gc_survives_a_file_unlinked_between_is_file_and_stat(
    tmp_path, private_store, monkeypatch
):
    """Another gc removes a file after our is_file() said it was there."""
    store = cas.ArtifactStore(private_store)
    keys = _populate(store, tmp_path)
    victim = store.path(keys[2], "o")
    real_is_file = Path.is_file

    def racing_is_file(self):
        found = real_is_file(self)
        if found and self == victim:
            self.unlink()  # the concurrent gc wins the race
        return found

    monkeypatch.setattr(Path, "is_file", racing_is_file)

    removed, freed = store.gc(10**9)  # nothing over the cap: scan only
    assert (removed, freed) == (0, 0)
    monkeypatch.setattr(Path, "is_file", real_is_file)

    # The vanished file is not counted: a cap of the 5 survivors removes none.
    assert store.gc(5 * 100) == (0, 0)


@pytest.mark.unit
def test_gc_counts_a_file_another_gc_already_unlinked_as_not_freed(
    tmp_path, private_store, monkeypatch
):
    """Scanned, then removed by someone else before our unlink: skipped, not counted.

    The race fires inside gc's own `unlink()` of the oldest file, so the scan
    (is_file + stat) is untouched. Hooking `Path.stat` instead was
    interpreter-dependent: on Python <= 3.13 `Path.is_file()` calls
    `self.stat()`, so the file vanished during the scan, gc never tried to
    unlink it, and the test saw (0, 0) on CI's 3.12 (AGAST #2828).
    """
    store = cas.ArtifactStore(private_store)
    keys = _populate(store, tmp_path)  # explicit mtimes: keys[0] oldest, keys[1] next
    oldest = store.path(keys[0], "o")
    real_unlink = Path.unlink
    raced = []

    def racing_unlink(self, *a, **kw):
        if self == oldest:
            raced.append(self)
            os.unlink(self)  # the concurrent gc gets there first
        return real_unlink(self, *a, **kw)

    monkeypatch.setattr(Path, "unlink", racing_unlink)

    removed, freed = store.gc(5 * 100)
    monkeypatch.setattr(Path, "unlink", real_unlink)
    assert raced == [oldest], (
        "gc should have scanned the oldest file and tried to unlink it"
    )
    assert not oldest.exists()
    # Our gc did not remove the oldest file, so it went on to the next one.
    assert (removed, freed) == (1, 100)
    assert not store.path(keys[1], "o").exists()


@pytest.mark.integration
def test_two_processes_gc_one_store_concurrently(tmp_path, private_store):
    """Smoke: two real gc(0) processes over one populated store both succeed."""
    store = cas.ArtifactStore(private_store)
    for i in range(400):
        src = tmp_path / "s.o"
        src.write_bytes(os.urandom(64))
        store.put(f"{i:04x}" + "c" * 60, "o", src)
    code = (
        "import sys, pathlib; sys.path.insert(0, sys.argv[1]); import cas; "
        "print(cas.ArtifactStore(pathlib.Path(sys.argv[2])).gc(0))"
    )
    procs = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(PKG_DIR), str(private_store)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    outs = [p.communicate(timeout=120) for p in procs]
    for p, (out, err) in zip(procs, outs):
        assert p.returncode == 0, err
    removed = sum(ast.literal_eval(out)[0] for out, _ in outs)
    assert removed == 400, outs  # each file removed exactly once between them
    assert [p for p in (private_store / "objects").rglob("*.o")] == []


# --- reader vs gc ----------------------------------------------------------


def _builder(dest, calls):
    """A build_fn that, like build.py's, writes its object straight to dest."""

    def build_fn():
        calls.append(1)
        dest.write_bytes(b"rebuilt")
        return {"o": dest}

    return build_fn


@pytest.mark.unit
def test_fetch_hit_copies_the_stored_object(tmp_path, private_store):
    store = cas.ArtifactStore(private_store)
    src = tmp_path / "a.o"
    src.write_bytes(b"stored")
    store.put(KEY, "o", src)
    calls = []
    dest = tmp_path / "out" / "a.o"
    dest.parent.mkdir()
    assert store.fetch(KEY, "o", _builder(dest, calls), dest) is False
    assert calls == [] and dest.read_bytes() == b"stored"


@pytest.mark.unit
def test_fetch_treats_an_object_gc_removed_after_the_hit_as_a_miss(
    tmp_path, private_store, monkeypatch
):
    """gc unlinks the object between the reader's hit and its copy."""
    store = cas.ArtifactStore(private_store)
    src = tmp_path / "a.o"
    src.write_bytes(b"stored")
    store.put(KEY, "o", src)
    real_hit = cas.ArtifactStore._hit

    def racing_hit(self, p):
        p = real_hit(self, p)
        p.unlink()  # the gate's trim runs right now
        return p

    monkeypatch.setattr(cas.ArtifactStore, "_hit", racing_hit)

    calls = []
    dest = tmp_path / "out.o"
    built = store.fetch(KEY, "o", _builder(dest, calls), dest)
    assert calls == [1], "a vanished object must be rebuilt, not crash the build"
    assert built is True and dest.read_bytes() == b"rebuilt"
    assert store.path(KEY, "o").read_bytes() == b"rebuilt"


def _load_build():
    spec = importlib.util.spec_from_file_location(
        "ritz_buildpy_2794", PKG_DIR / "build.py"
    )
    buildpy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(buildpy)
    return buildpy


def _gc_after_every_hit(monkeypatch):
    """Each store hit is followed at once by a gc that removes that object."""
    real_hit = cas.ArtifactStore._hit
    hits = []

    def racing_hit(self, p):
        p = real_hit(self, p)
        hits.append(p)
        p.unlink()
        return p

    monkeypatch.setattr(cas.ArtifactStore, "_hit", racing_hit)
    return hits


@pytest.mark.integration
@pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")
def test_build_py_cas_object_rebuilds_when_gc_wins_after_the_hit(
    tmp_path, private_store, monkeypatch
):
    buildpy = _load_build()
    src = tmp_path / "m.ritz"
    src.write_text("pub fn seven() -> i32\n    7\n")
    assert (
        buildpy.cas_object(src, tmp_path / "a" / "m.o", project_root=tmp_path) is None
    )
    hits = _gc_after_every_hit(monkeypatch)
    out = tmp_path / "b" / "m.o"
    assert buildpy.cas_object(src, out, project_root=tmp_path) is None
    assert hits, "the second call should have hit the store"
    assert out.is_file() and out.stat().st_size > 0


@pytest.mark.integration
@pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")
def test_build_py_compile_modules_rebuilds_when_gc_wins_after_the_hit(
    tmp_path, private_store, monkeypatch
):
    buildpy = _load_build()
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "b.ritz").write_text("pub fn seven() -> i32\n    7\n")
    main = pkg / "src" / "main.ritz"
    main.write_text("import b { seven }\nfn main() -> i32\n    return seven()\n")

    def build(tag):
        # A fresh worktree's view: empty per-worktree cache, only the store shared.
        cache = buildpy.BuildCache(project_root=PKG_DIR)
        cache._cache_dir = tmp_path / f".ritz-cache-{tag}"
        buildpy._build_cache["ritz0"] = cache
        out = tmp_path / f"out-{tag}"
        out.mkdir()
        return buildpy.compile_binary(
            "app", main, out, use_cache=True, pkg_dir=pkg, source_roots=["src"]
        )

    assert build("wt1") is not None
    hits = _gc_after_every_hit(monkeypatch)
    bin_path = build("wt2")
    assert hits, "the second build should have hit the store"
    assert bin_path is not None, "a cache hit gc'd before the copy failed the build"
    assert subprocess.run([str(bin_path)], timeout=30, check=False).returncode == 7
