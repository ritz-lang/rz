"""G7 phase 3 (AGAST #1911): CAS single-flight.

Gate 1894-3e0033ff55dc reported 40 keys "compiled more than once": parallel
test_runner / build.py processes missed on the same key at the same moment
and both compiled it. `ArtifactStore.get_or_build` takes a per-key lock
(flock on `objects/<k[:2]>/.<k>.lock`) and re-checks the store once it holds
it, so the second process waits and then hits instead of compiling.

Unit tests drive the store directly with a slow fake `build_fn`; integration
tests run the real consumers (cas.py get-or-build, build.py, test_runner) as
concurrent processes on one cold store and read the gate summary, which is
the ticket's acceptance criterion.
"""

import importlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
RITZ0_DIR = PKG_DIR / "ritz0"
for d in (str(PKG_DIR), str(RITZ0_DIR)):
    if d not in sys.path:
        sys.path.insert(0, d)

cas = importlib.import_module("cas")

HAS_CLANG = shutil.which("clang") is not None
needs_clang = pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")
KEY = "5f" + "a" * 62


@pytest.fixture(autouse=True)
def private_store(tmp_path, monkeypatch):
    root = tmp_path / "cas"
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(root))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    monkeypatch.setattr(cas, "STATS", cas.Stats())
    return root


# --- store: get_or_build ---------------------------------------------------


# Run in a child process: N of these race on one key. Each appends a line to
# `builds` when its build_fn runs, and prints what get_or_build returned.
_RACER = r"""
import sys, time, pathlib
sys.path.insert(0, sys.argv[1])
import cas
root, key, builds, work, go = sys.argv[2:7]
while not pathlib.Path(go).exists():   # start line: everyone misses together
    time.sleep(0.001)
def build_fn():
    with open(builds, "a") as f:
        f.write("built\n")
    time.sleep(0.5)                     # a compile, long enough to overlap
    out = pathlib.Path(work) / "x.o"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(b"object")
    return {"o": out}
path, built = cas.ArtifactStore(pathlib.Path(root)).get_or_build(key, "o", build_fn,
                                                                  identity="m.ritz")
print(path.read_bytes().decode(), built)
"""


@pytest.mark.unit
def test_concurrent_processes_on_one_key_build_once(tmp_path, private_store):
    builds = tmp_path / "builds"
    go = tmp_path / "go"
    procs = [subprocess.Popen(
        [sys.executable, "-c", _RACER, str(PKG_DIR), str(private_store), KEY,
         str(builds), str(tmp_path / f"w{i}"), str(go)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(6)]
    time.sleep(0.3)
    go.touch()
    outs = [p.communicate(timeout=60) for p in procs]
    assert all(p.returncode == 0 for p in procs), [e for _, e in outs]
    assert builds.read_text().count("built") == 1, "a key was compiled more than once"
    lines = sorted(o.strip() for o, _ in outs)
    assert lines == ["object False"] * 5 + ["object True"]


@pytest.mark.unit
def test_concurrent_threads_on_one_key_build_once(tmp_path, private_store):
    """The regression matrix calls in from a thread pool within one process."""
    store = cas.ArtifactStore()
    calls = []
    barrier = threading.Barrier(6)

    def build_fn(i):
        calls.append(i)
        time.sleep(0.3)
        out = tmp_path / f"t{i}.o"
        out.write_bytes(b"object")
        return {"o": out}

    def race(i):
        barrier.wait()
        return store.get_or_build(KEY, "o", lambda: build_fn(i))

    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(race, range(6)))
    assert len(calls) == 1
    assert sorted(b for _, b in results) == [False] * 5 + [True]
    assert {p for p, _ in results} == {store.path(KEY, "o")}


@pytest.mark.unit
def test_get_or_build_hit_does_not_call_build_fn(tmp_path, private_store):
    store = cas.ArtifactStore()
    src = tmp_path / "x.o"
    src.write_bytes(b"obj")
    store.put(KEY, "o", src)

    def boom():
        raise AssertionError("built on a hit")
    assert store.get_or_build(KEY, "o", boom) == (store.path(KEY, "o"), False)
    assert (cas.STATS.hits, cas.STATS.misses) == (1, 0)


@pytest.mark.unit
def test_get_or_build_stores_every_artifact_meta_and_identity(tmp_path, private_store):
    store = cas.ArtifactStore()
    ll = tmp_path / "x.ll"
    ll.write_text("ir")
    o = tmp_path / "x.o"
    o.write_bytes(b"obj")
    path, built = store.get_or_build(KEY, "o", lambda: {"ll": ll, "o": o},
                                     identity="ritzlib/io.ritz",
                                     meta={"module": "ritzlib/io.ritz"})
    assert built and path == store.path(KEY, "o")
    assert store.path(KEY, "ll").read_text() == "ir"
    assert json.loads(store.meta_path(KEY).read_text()) == {"module": "ritzlib/io.ritz"}
    # One miss, recorded once (with the identity) for the gate summary.
    assert cas.STATS.misses == 1
    assert cas.STATS.missed == [[KEY, "o", "ritzlib/io.ritz", str(private_store)]]
    leftovers = [p for p in private_store.rglob(".*") if p.is_file()]
    assert leftovers == [], f"lock or temp files left behind: {leftovers}"


@pytest.mark.unit
def test_failed_build_stores_nothing_and_releases_the_lock(tmp_path, private_store):
    store = cas.ArtifactStore()

    class Failed(Exception):
        pass

    def fail():
        raise Failed("ritz0 failed")
    with pytest.raises(Failed):
        store.get_or_build(KEY, "o", fail)
    assert not store.path(KEY, "o").exists()

    # The lock was released: another caller (a thread, so a deadlock would
    # show as a timeout rather than a hung test) gets to build.
    o = tmp_path / "x.o"
    o.write_bytes(b"obj")
    with ThreadPoolExecutor(1) as ex:
        fut = ex.submit(store.get_or_build, KEY, "o", lambda: {"o": o})
        assert fut.result(timeout=10) == (store.path(KEY, "o"), True)


@pytest.mark.unit
def test_build_fn_must_produce_the_requested_artifact(tmp_path, private_store):
    store = cas.ArtifactStore()
    ll = tmp_path / "x.ll"
    ll.write_text("ir")
    with pytest.raises(ValueError):
        store.get_or_build(KEY, "o", lambda: {"ll": ll})
    assert not store.path(KEY, "ll").exists(), "a partial entry was stored"


@pytest.mark.unit
def test_gc_ignores_lock_files(tmp_path, private_store):
    store = cas.ArtifactStore()
    lock = store.lock_path(KEY)
    assert lock == private_store / "objects" / KEY[:2] / f".{KEY}.lock"
    lock.parent.mkdir(parents=True)
    lock.touch()
    assert store.gc(0) == (0, 0)


@pytest.mark.unit
def test_summary_counts_double_compiles_per_store(tmp_path, private_store):
    """ritz0/conftest.py gives each pytest session a private RITZ_CACHE_DIR,
    and some tests one each, while all inherit the gate's stats log. One
    compile per store is not a double compile: no lock can or should make
    two stores share it. Gate 1911-183a0ca2af9d flagged ext/main.ritz that
    way."""
    o = tmp_path / "x.o"
    o.write_bytes(b"obj")
    cas.ArtifactStore(tmp_path / "s1").put(KEY, "o", o, identity="ext/main.ritz")
    cas.ArtifactStore(tmp_path / "s2").put(KEY, "o", o, identity="ext/main.ritz")
    log = tmp_path / "gate.jsonl"
    log.write_text(json.dumps(cas.STATS.as_dict()) + "\n")
    assert cas.summarise(log)["compiled_more_than_once"] == {}

    # The same store twice still is one; so are pre-#1911 records with no root.
    log.write_text(2 * (json.dumps(cas.STATS.as_dict()) + "\n"))
    s = cas.summarise(log)
    assert list(s["compiled_more_than_once"].values()) == ["ext/main.ritz"] * 2
    log.write_text(2 * (json.dumps({"missed": [[KEY, "o", "ritzlib/io.ritz"]]}) + "\n"))
    assert list(cas.summarise(log)["compiled_more_than_once"].values()) == ["ritzlib/io.ritz"]


# --- consumers: concurrent processes on one cold store ---------------------


def _summary(log: Path) -> dict:
    return cas.summarise(log)


def _env(private_store, log):
    return {**os.environ, "RITZ_PATH": str(PKG_DIR), cas.CAS_DIR_ENV: str(private_store),
            cas.STATS_LOG_ENV: str(log)}


@pytest.mark.integration
@needs_clang
def test_concurrent_cas_py_get_or_build_compiles_once(tmp_path, private_store):
    """cas.py get-or-build (ritz1's Makefile) -> build.cas_object."""
    log = tmp_path / "gate.jsonl"
    env = _env(private_store, log)
    src = PKG_DIR / "ritzlib" / "sys.ritz"
    procs = [subprocess.Popen([sys.executable, str(PKG_DIR / "cas.py"), "get-or-build",
                               str(src), str(tmp_path / f"o{i}" / "sys.o")],
                              env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True) for i in range(4)]
    for p in procs:
        _, err = p.communicate(timeout=300)
        assert p.returncode == 0, err
    s = _summary(log)
    assert s["compiled_more_than_once"] == {}, s
    assert s["compiled"] == 1 and s["hits"] == 3, s


@pytest.mark.integration
@needs_clang
def test_concurrent_build_py_processes_compile_each_module_once(tmp_path, private_store):
    """build.compile_binary."""
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "b.ritz").write_text("pub struct S\n    x: i32\n")
    (pkg / "src" / "main.ritz").write_text(
        "import b { S }\nfn main() -> i32\n    return sizeof(S) as i32\n")
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "app"\nversion = "0.1.0"\nsources = ["src"]\n\n'
        '[[bin]]\nname = "app"\npath = "src/main.ritz"\n')
    log = tmp_path / "gate.jsonl"
    env = _env(private_store, log)
    procs = []
    for i in range(3):
        mine = tmp_path / f"p{i}"
        shutil.copytree(pkg, mine)
        procs.append(subprocess.Popen(
            [sys.executable, str(PKG_DIR / "build.py"), "build", str(mine)],
            cwd=PKG_DIR, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
    for p in procs:
        out, _ = p.communicate(timeout=300)
        assert p.returncode == 0, out
    s = _summary(log)
    assert s["compiled_more_than_once"] == {}, s
    assert s["compiled"] == 2, s


@pytest.mark.integration
@needs_clang
def test_concurrent_test_runner_processes_compile_each_dependency_once(tmp_path, private_store):
    """ritz0/test_runner.compile_dependencies."""
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "ritz.toml").write_text('[package]\nname = "t"\nversion = "0.1.0"\nsources = ["src"]\n')
    (pkg / "src" / "b.ritz").write_text("pub fn seven() -> i32\n    7\n")
    t = pkg / "src" / "test_b.ritz"
    t.write_text("import b\n\n[[test]]\nfn test_seven() -> i32\n    assert seven() == 7\n    0\n")
    log = tmp_path / "gate.jsonl"
    env = _env(private_store, log)
    procs = [subprocess.Popen([sys.executable, str(RITZ0_DIR / "test_runner.py"), str(t)],
                              cwd=pkg, env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True) for _ in range(4)]
    for p in procs:
        out, _ = p.communicate(timeout=300)
        assert p.returncode == 0, out
    s = _summary(log)
    assert s["compiled_more_than_once"] == {}, s
    assert s["compiled"] >= 1, s
