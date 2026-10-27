"""G7 phase 2 (AGAST #1894): everyone else's ritzlib objects come from the CAS.

Phase 1 (#1808, tools/test_cas.py) put build.py and test_runner's dependency
objects in the shared content-addressed store. Three consumers still compiled
ritzlib from scratch on every run:

* tools/run_regression_matrix.py built its baseline ritzlib objects and every
  test file's extra dependencies into a per-run TemporaryDirectory, serially,
  and ran `ritz0/list_deps.py` once per (file, compiler): 375 subprocesses for
  125 files.
* ritz1/Makefile compiled its 16 ritzlib modules with its own clang flags,
  so the ritz1 build could never share an object with the gate.
* `rz compare` ran `build.py clean` before every example, which (ignoring its
  argument) deleted every package's binaries, every __pycache__ and the whole
  .ritz-cache import-scan store, once per example.

Plus the store had a `gc` nobody could reach from `rz`, and no trim ever ran.
"""

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PKG_DIR.parents[1]
RZ_PATH = REPO_ROOT / "rz"
CAS_PY = PKG_DIR / "cas.py"
HAS_CLANG = shutil.which("clang") is not None
needs_clang = pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")


def _load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def private_store(tmp_path, monkeypatch):
    """Never touch the real ~/.cache/ritz/cas."""
    root = tmp_path / "cas"
    monkeypatch.setenv("RITZ_CACHE_DIR", str(root))
    monkeypatch.delenv("RITZ_CAS_STATS_LOG", raising=False)
    monkeypatch.delenv("RITZ_CACHE_MAX_BYTES", raising=False)
    monkeypatch.setenv("RITZ_PATH", str(PKG_DIR))
    return root


@pytest.fixture
def matrix(private_store, tmp_path, monkeypatch):
    """A fresh run_regression_matrix module (and so a fresh build.py) per test,
    with a private per-worktree import-scan cache."""
    mod = _load(f"rrm_{tmp_path.name}", PKG_DIR / "tools" / "run_regression_matrix.py")
    build = mod.build_module()
    build.cas.STATS.__init__()
    cache = build.get_build_cache("ritz0")
    cache._cache_dir = tmp_path / ".ritz-cache"
    return mod


def _spy_ritz0(monkeypatch, module):
    """Record every ritz0 --no-runtime compile `module.subprocess.run` makes."""
    calls = []
    real = module.subprocess.run

    def spy(cmd, *a, **kw):
        if any(str(c).endswith("ritz0.py") for c in cmd) and "--no-runtime" in cmd:
            calls.append(Path(str(cmd[2])).name)
        if any(str(c).endswith("list_deps.py") for c in cmd):
            calls.append("list_deps")
        return real(cmd, *a, **kw)
    monkeypatch.setattr(module.subprocess, "run", spy)
    return calls


# --- run_regression_matrix: closure memo ----------------------------------


@pytest.mark.integration
def test_matrix_closure_is_resolved_once_per_file_and_in_process(matrix, tmp_path, monkeypatch):
    """Three compilers ask for the same file's closure: one resolution, no
    list_deps.py subprocess, and the same answer list_deps.py gives."""
    deps = matrix.DepObjects(tmp_path, os.environ.copy(), [], [])
    calls = _spy_ritz0(monkeypatch, matrix)
    scans = []
    cache = matrix.build_module().get_build_cache("ritz0")
    real_scan = cache.get_transitive_dependencies

    def counting(path, *a, **kw):
        if not a and not kw:
            scans.append(Path(path).name)
        return real_scan(path, *a, **kw)
    monkeypatch.setattr(cache, "get_transitive_dependencies", counting)

    src = matrix.TEST_DIR / "test_import_main.ritz"
    got = [deps.closure(src) for _ in range(3)]
    assert calls == [], "closure still shells out to list_deps.py"
    assert scans == ["test_import_main.ritz"], f"closure resolved {len(scans)}x"
    assert got[0] == got[1] == got[2]

    r = subprocess.run([sys.executable, str(PKG_DIR / "ritz0" / "list_deps.py"), str(src),
                        "--project-root", str(PKG_DIR)],
                       capture_output=True, text=True, timeout=120,
                       env={**os.environ, "RITZ_PATH": str(PKG_DIR)})
    assert r.returncode == 0, r.stderr
    want = {str(Path(p).resolve()) for p in r.stdout.split()} - {str(src.resolve())}
    assert {str(Path(p).resolve()) for p in got[0]} == want


@pytest.mark.integration
def test_matrix_closure_of_an_unparseable_file_raises(matrix, tmp_path):
    bad = tmp_path / "bad.ritz"
    bad.write_text("import ritzlib.io\nfn (((\n")
    deps = matrix.DepObjects(tmp_path, os.environ.copy(), [], [])
    with pytest.raises(RuntimeError):
        deps.closure(bad)


# --- run_regression_matrix: objects from the store ------------------------


@pytest.mark.integration
@needs_clang
def test_matrix_ritzlib_objects_come_from_the_store(matrix, tmp_path, monkeypatch, private_store):
    """A second run (another tmpdir, another worktree) compiles no ritzlib."""
    monkeypatch.setattr(matrix, "RITZLIB_MODULES", ["sys", "io"])
    build = matrix.build_module()
    calls = _spy_ritz0(monkeypatch, build)

    run1 = tmp_path / "run1"
    run1.mkdir()
    objs, err = matrix.build_ritzlib_objs(run1, os.environ.copy())
    assert err is None, err
    assert sorted(calls) == ["io.ritz", "sys.ritz"]
    assert all(Path(o).is_file() and Path(o).parent == run1 for o in objs)
    stored = list((private_store / "objects").rglob("*.o"))
    assert len(stored) == 2, f"ritzlib objects not stored: {stored}"

    # The keys are build.py's, so build.py / test_runner / ritz1's Makefile hit them.
    cache = build.get_build_cache("ritz0")
    for mod in ("sys", "io"):
        key = build.cas_module_key(matrix.RITZLIB_DIR / f"{mod}.ritz", cache, "ritz0")
        assert (private_store / "objects" / key[:2] / f"{key}.o").is_file()

    calls.clear()
    misses = build.cas.STATS.misses
    run2 = tmp_path / "run2"
    run2.mkdir()
    objs2, err = matrix.build_ritzlib_objs(run2, os.environ.copy())
    assert err is None, err
    assert calls == [], f"ritzlib recompiled despite store hits: {calls}"
    assert build.cas.STATS.misses == misses
    assert [Path(o).read_bytes() for o in objs2] == [Path(o).read_bytes() for o in objs]


@pytest.mark.integration
@needs_clang
def test_matrix_dependency_objects_come_from_the_store(matrix, tmp_path, monkeypatch):
    build = matrix.build_module()
    calls = _spy_ritz0(monkeypatch, build)
    dep = matrix.TEST_DIR / "test_import_lib.ritz"

    d1 = matrix.DepObjects(tmp_path / "a", os.environ.copy(), [], [])
    (tmp_path / "a").mkdir()
    o1, err = d1.obj_for(str(dep))
    assert err is None, err
    assert calls == ["test_import_lib.ritz"]

    calls.clear()
    (tmp_path / "b").mkdir()
    d2 = matrix.DepObjects(tmp_path / "b", os.environ.copy(), [], [])
    o2, err = d2.obj_for(str(dep))
    assert err is None, err
    assert calls == [], "dependency recompiled despite a store hit"
    assert Path(o2).read_bytes() == Path(o1).read_bytes()


@pytest.mark.integration
@needs_clang
def test_matrix_compile_failure_is_reported_and_not_stored(matrix, tmp_path, private_store):
    bad = tmp_path / "broken.ritz"
    bad.write_text("fn f() -> i32\n    undefined_name\n")
    d = matrix.DepObjects(tmp_path, os.environ.copy(), [], [])
    o, err = d.obj_for(str(bad))
    assert o is None and "broken.ritz: ritz0 failed" in err, err  # ritz0's diagnostic, not clang's
    assert not list(private_store.rglob("*.o")), "a failed compile reached the store"


# --- cas.py get-or-build (the ritz1 Makefile shim) ------------------------


def _get_or_build(src, out, env):
    return subprocess.run([sys.executable, str(CAS_PY), "get-or-build", str(src), str(out)],
                          capture_output=True, text=True, timeout=300, env=env)


@pytest.mark.integration
@needs_clang
def test_get_or_build_stores_then_hits(tmp_path, private_store):
    env = {**os.environ, "RITZ_PATH": str(PKG_DIR), "RITZ_CAS_STATS": "1"}
    src = PKG_DIR / "ritzlib" / "sys.ritz"
    r = _get_or_build(src, tmp_path / "a" / "sys.o", env)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "a" / "sys.o").stat().st_size > 0
    assert "misses=1" in r.stderr and "hits=0" in r.stderr

    r = _get_or_build(src, tmp_path / "b" / "sys.o", env)
    assert r.returncode == 0, r.stderr
    assert "hits=1" in r.stderr and "misses=0" in r.stderr
    assert (tmp_path / "b" / "sys.o").read_bytes() == (tmp_path / "a" / "sys.o").read_bytes()


@pytest.mark.integration
@needs_clang
def test_get_or_build_failure_exits_nonzero_and_leaves_no_output(tmp_path, private_store):
    bad = tmp_path / "broken.ritz"
    bad.write_text("fn f() -> i32\n    undefined_name\n")
    out = tmp_path / "broken.o"
    r = _get_or_build(bad, out, {**os.environ, "RITZ_PATH": str(PKG_DIR)})
    assert r.returncode != 0
    assert "broken.ritz: ritz0 failed" in r.stderr, r.stderr
    assert not out.exists()


@pytest.mark.integration
def test_ritz1_makefile_takes_ritzlib_objects_from_the_store(tmp_path):
    """The ritz1 build shares ritzlib objects with the gate: its ritzlib rule
    is the store shim, not its own ritz0 + clang pair."""
    out = tmp_path / "b"
    r = subprocess.run(["make", "-n", "-C", str(PKG_DIR / "ritz1"), f"BUILD_DIR={out}",
                        f"{out}/ritzlib_sys.o", f"{out}/ritzlib_os_env.o"],
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    shim = [ln for ln in r.stdout.splitlines() if "cas.py get-or-build" in ln]
    assert any("ritzlib/sys.ritz" in ln for ln in shim), r.stdout
    assert any("ritzlib/os/env.ritz" in ln for ln in shim), r.stdout
    assert "clang -c" not in r.stdout, "ritzlib objects still compiled outside the store"


# --- rz cache gc / periodic trim ------------------------------------------


def _fill(store_root, n, size=100):
    for i in range(n):
        k = f"{i:02d}" + "a" * 62
        p = store_root / "objects" / k[:2] / f"{k}.o"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * size)
        os.utime(p, (1000 + i, 1000 + i))


@pytest.mark.integration
def test_rz_cache_gc_trims_to_the_cap(private_store):
    _fill(private_store, 5)
    r = subprocess.run([str(RZ_PATH), "cache", "gc", "--max-bytes", "250"],
                       capture_output=True, text=True, timeout=60, env=os.environ.copy())
    assert r.returncode == 0, r.stdout + r.stderr
    assert "removed 3 files" in r.stdout
    assert len(list(private_store.rglob("*.o"))) == 2


@pytest.mark.integration
def test_rz_cache_path_prints_the_store(private_store):
    r = subprocess.run([str(RZ_PATH), "cache", "path"],
                       capture_output=True, text=True, timeout=60, env=os.environ.copy())
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == str(private_store)


@pytest.mark.unit
def test_default_cap_honours_env(monkeypatch):
    cas = _load("cas_cap", CAS_PY)
    monkeypatch.delenv("RITZ_CACHE_MAX_BYTES", raising=False)
    assert cas.default_max_bytes() == cas.DEFAULT_GC_BYTES
    monkeypatch.setenv("RITZ_CACHE_MAX_BYTES", "1234")
    assert cas.default_max_bytes() == 1234


@pytest.mark.unit
def test_ci_local_trims_the_store_after_the_gate(private_store, monkeypatch, capsys):
    """The periodic trim: every gate ends by bounding the store."""
    _fill(private_store, 5)
    monkeypatch.setenv("RITZ_CACHE_MAX_BYTES", "250")
    ci_local = _load("ci_local_trim", PKG_DIR / "tools" / "ci_local.py")
    ci_local.trim_cas()
    assert len(list(private_store.rglob("*.o"))) == 2
    assert "[ritz-cas] gc: removed 3 files" in capsys.readouterr().out


# --- rz compare ------------------------------------------------------------


@pytest.mark.unit
def test_rz_compare_does_not_clean_per_example(monkeypatch):
    rz = _load("rz_cli_1894", RZ_PATH)
    cmds = []

    class R:
        returncode = 0
        stdout = stderr = ""

    def fake_run(cmd, *a, **kw):
        cmds.append([str(c) for c in cmd])
        return R()
    monkeypatch.setattr(rz.subprocess, "run", fake_run)
    assert rz.build_example_with_build_py("examples/tier1_basics/01_hello", "ritz1")
    assert [c for c in cmds if "clean" in c] == [], "rz compare still wipes the cache per example"
    assert any("build" in c and "ritz1" in c for c in cmds)
