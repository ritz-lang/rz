"""Content-addressed artifact store (AGAST #1808).

The ticket's acceptance tests:

1. change an imported module -> every dependent misses;
2. change the compiler fingerprint -> miss, old entries untouched;
3. two concurrent build.py processes on one store -> no corruption (20x);
4. flags differ -> distinct entries.

Plus what makes the store worth having: a second worktree (here: a fresh
BuildCache, an empty `.ritz-cache` and no linked binary) hits on everything,
and test_runner fetches dependency objects that build.py stored instead of
recompiling them.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
RITZ0_DIR = PKG_DIR / "ritz0"
for d in (str(PKG_DIR), str(RITZ0_DIR)):
    if d not in sys.path:
        sys.path.insert(0, d)

# Loaded by name rather than `import cas` / `import test_runner`, which
# test_tools_requirements would read as undeclared third-party imports.
cas = importlib.import_module("cas")

HAS_CLANG = shutil.which("clang") is not None


@pytest.fixture(autouse=True)
def private_store(tmp_path, monkeypatch):
    """Never touch the real ~/.cache/ritz/cas; reset per-process counters."""
    root = tmp_path / "cas"
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(root))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    monkeypatch.setattr(cas, "STATS", cas.Stats())
    return root


def _key(src, closure, fp="fp-1", flags=None, repo_root=None):
    return cas.module_key(compiler_fp=fp, source=src, closure=closure,
                          flags=flags or {"opt": "-O2"}, target="t",
                          repo_root=repo_root)


def _tree(root: Path) -> dict:
    """main -> mid -> leaf, plus an unrelated `other`."""
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "leaf": "pub struct S\n    x: i32\n",
        "mid": "pub import leaf { S }\n",
        "main": "import mid { S }\nfn main() -> i32\n    0\n",
        "other": "fn other() -> i32\n    1\n",
    }
    out = {}
    for name, text in files.items():
        p = root / f"{name}.ritz"
        p.write_text(text)
        out[name] = p
    return out


def _keys(t: dict, **kw) -> dict:
    return {
        "main": _key(t["main"], [t["mid"], t["leaf"]], **kw),
        "mid": _key(t["mid"], [t["leaf"]], **kw),
        "leaf": _key(t["leaf"], [], **kw),
        "other": _key(t["other"], [], **kw),
    }


# --- keys ------------------------------------------------------------------


@pytest.mark.unit
def test_changing_an_import_changes_every_dependents_key(tmp_path):
    """Acceptance 1: direct and transitive dependents miss, others hit."""
    t = _tree(tmp_path / "src")
    before = _keys(t)
    t["leaf"].write_text("pub struct S\n    x: i64\n")
    after = _keys(t)
    assert after["leaf"] != before["leaf"]
    assert after["mid"] != before["mid"], "direct dependent kept its key"
    assert after["main"] != before["main"], "transitive dependent kept its key"
    assert after["other"] == before["other"], "unrelated module was invalidated"


@pytest.mark.unit
def test_compiler_change_misses_and_leaves_old_entries(tmp_path):
    """Acceptance 2."""
    t = _tree(tmp_path / "src")
    store = cas.ArtifactStore()
    artifact = tmp_path / "x.o"
    artifact.write_bytes(b"built-by-v1")
    k1 = _key(t["leaf"], [], fp="ritz0-v1")
    store.put(k1, "o", artifact)

    k2 = _key(t["leaf"], [], fp="ritz0-v2")
    assert k2 != k1
    assert store.get(k2, "o") is None, "new compiler hit an old object"
    artifact.write_bytes(b"built-by-v2")
    store.put(k2, "o", artifact)
    assert store.get(k1, "o").read_bytes() == b"built-by-v1", "old entry was disturbed"
    assert store.get(k2, "o").read_bytes() == b"built-by-v2"


@pytest.mark.unit
def test_different_flags_are_distinct_entries(tmp_path):
    """Acceptance 4."""
    t = _tree(tmp_path / "src")
    keys = {
        _key(t["leaf"], [], flags={"opt": "-O2", "verify_ir": False}),
        _key(t["leaf"], [], flags={"opt": "-O0", "verify_ir": False}),
        _key(t["leaf"], [], flags={"opt": "-O2", "verify_ir": True}),
    }
    assert len(keys) == 3


@pytest.mark.unit
def test_target_is_part_of_the_key(tmp_path):
    t = _tree(tmp_path / "src")
    a = cas.module_key(compiler_fp="f", source=t["leaf"], closure=[], flags={}, target="x86_64")
    b = cas.module_key(compiler_fp="f", source=t["leaf"], closure=[], flags={}, target="aarch64")
    assert a != b


@pytest.mark.unit
def test_two_worktrees_agree_on_keys(tmp_path):
    """Identities are repo-relative, so a second checkout shares entries."""
    wt1, wt2 = tmp_path / "wt1", tmp_path / "wt2"
    t1, t2 = _tree(wt1 / "projects" / "ritz"), _tree(wt2 / "projects" / "ritz")
    assert _keys(t1, repo_root=wt1) == _keys(t2, repo_root=wt2)


@pytest.mark.unit
def test_a_moved_module_is_a_different_module(tmp_path):
    """Same bytes at another path in the repo: a different identity."""
    t = _tree(tmp_path / "a")
    moved = tmp_path / "b" / "leaf.ritz"
    moved.parent.mkdir()
    moved.write_text(t["leaf"].read_text())
    assert _key(t["leaf"], [], repo_root=tmp_path) != _key(moved, [], repo_root=tmp_path)


@pytest.mark.unit
def test_closure_order_and_self_do_not_matter(tmp_path):
    t = _tree(tmp_path / "src")
    assert _key(t["main"], [t["mid"], t["leaf"]]) == _key(t["main"], [t["leaf"], t["main"], t["mid"]])


# --- store -----------------------------------------------------------------


@pytest.mark.unit
def test_store_layout_and_counters(tmp_path, private_store):
    store = cas.ArtifactStore()
    assert store.root == private_store
    k = "ab" + "0" * 62
    src = tmp_path / "x.o"
    src.write_bytes(b"obj")
    assert store.get(k, "o") is None
    store.put(k, "o", src, identity="ritzlib/io.ritz")
    store.put_meta(k, {"module": "ritzlib/io.ritz"})
    assert store.get(k, "o") == private_store / "objects" / "ab" / f"{k}.o"
    assert json.loads(store.meta_path(k).read_text())["module"] == "ritzlib/io.ritz"
    assert (cas.STATS.hits, cas.STATS.misses, cas.STATS.bytes_written) == (1, 1, 3)
    leftovers = [p for p in private_store.rglob(".*") if p.is_file()]
    assert leftovers == [], f"temp files left behind: {leftovers}"


def _hammer(args):
    root, key, n, payload_len = args
    store = cas.ArtifactStore(Path(root))
    tmp = Path(root).parent / f"src-{n}"
    tmp.write_bytes(bytes([n % 251]) * payload_len)
    store.put(key, "o", tmp)
    got = store.get(key, "o")
    data = got.read_bytes()
    return len(data) == payload_len and len(set(data)) == 1


@pytest.mark.unit
def test_concurrent_writers_never_expose_a_partial_entry(tmp_path, private_store):
    """Many writers on one key: every read is one writer's complete file."""
    payload = 1 << 20
    with ThreadPoolExecutor(8) as ex:
        ok = list(ex.map(_hammer, [(str(private_store), "cd" + "1" * 62, n, payload)
                                   for n in range(40)]))
    assert all(ok)


@pytest.mark.unit
def test_gc_drops_least_recently_used_first(tmp_path):
    store = cas.ArtifactStore()
    src = tmp_path / "x.o"
    src.write_bytes(b"x" * 100)
    keys = [f"{i:02d}" + "e" * 62 for i in range(5)]
    for i, k in enumerate(keys):
        store.put(k, "o", src)
        store.put_meta(k, {})
        os.utime(store.path(k, "o"), (1000 + i, 1000 + i))
    # Using the oldest makes it the most recent.
    os.utime(store.path(keys[0], "o"), (5000, 5000))
    removed, freed = store.gc(max_bytes=250)
    assert (removed, freed) == (3, 300)
    survivors = {k for k in keys if store.path(k, "o").exists()}
    assert survivors == {keys[0], keys[4]}
    assert not store.meta_path(keys[1]).exists(), "meta of a collected entry left behind"
    assert store.gc(max_bytes=250) == (0, 0), "gc trimmed below the cap"


@pytest.mark.unit
def test_stats_log_summary_flags_double_compiles(tmp_path):
    log = tmp_path / "cas.log"
    recs = [
        {"hits": 3, "misses": 1, "bytes_written": 10, "missed": [["k1", "o", "ritzlib/io.ritz"]]},
        {"hits": 4, "misses": 1, "bytes_written": 10, "missed": [["k1", "o", "ritzlib/io.ritz"]]},
        {"hits": 9, "misses": 1, "bytes_written": 5, "missed": [["k2", "o", "ritzlib/sys.ritz"]]},
    ]
    log.write_text("".join(json.dumps(r) + "\n" for r in recs))
    s = cas.summarise(log)
    assert (s["processes"], s["hits"], s["misses"], s["compiled"]) == (3, 16, 3, 2)
    assert list(s["compiled_more_than_once"].values()) == ["ritzlib/io.ritz"]


@pytest.mark.integration
def test_stats_env_reports_at_exit(tmp_path):
    log = tmp_path / "cas.log"
    code = ("import cas, pathlib; s = cas.ArtifactStore(); "
            "s.get('ff' + '0'*62, 'o')")
    env = {**os.environ, cas.STATS_ENV: "1", cas.STATS_LOG_ENV: str(log)}
    r = subprocess.run([sys.executable, "-c", code], cwd=PKG_DIR, env=env,
                       capture_output=True, text=True, timeout=60)
    assert "[ritz-cas]" in r.stderr and "misses=1" in r.stderr
    assert json.loads(log.read_text())["misses"] == 1


# --- build.py --------------------------------------------------------------


def _load_build(name):
    spec = importlib.util.spec_from_file_location(name, PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pkg(tmp_path: Path, width="i32") -> tuple:
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True, exist_ok=True)
    (pkg / "src" / "b.ritz").write_text(f"pub struct S\n    x: {width}\n")
    main = pkg / "src" / "main.ritz"
    main.write_text("import b { S }\nfn main() -> i32\n    return sizeof(S) as i32\n")
    return pkg, main


def _fresh_worktree_build(buildpy, tmp_path, pkg, main, tag):
    """compile_binary as a new process in another worktree would run it:
    empty per-worktree .ritz-cache, no linked binary, only the shared store."""
    cache = buildpy.BuildCache(project_root=PKG_DIR)
    cache._cache_dir = tmp_path / f".ritz-cache-{tag}"
    buildpy._build_cache["ritz0"] = cache
    out = tmp_path / f"out-{tag}"
    out.mkdir()
    bin_path = buildpy.compile_binary("app", main, out, use_cache=True,
                                      pkg_dir=pkg, source_roots=["src"])
    assert bin_path is not None, "build failed"
    return subprocess.run([str(bin_path)], timeout=30).returncode


@pytest.mark.integration
@pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")
def test_second_worktree_build_compiles_nothing(tmp_path, monkeypatch):
    buildpy = _load_build("ritz_buildpy_1808_a")
    pkg, main = _pkg(tmp_path)
    assert _fresh_worktree_build(buildpy, tmp_path, pkg, main, "wt1") == 4
    first = (cas.STATS.hits, cas.STATS.misses)
    assert first[1] >= 2 and first[0] == 0

    calls = []
    real_run = buildpy.subprocess.run

    def spy(cmd, *a, **kw):
        if any(str(c).endswith("ritz0.py") for c in cmd):
            calls.append(cmd)
        return real_run(cmd, *a, **kw)
    monkeypatch.setattr(buildpy.subprocess, "run", spy)

    assert _fresh_worktree_build(buildpy, tmp_path, pkg, main, "wt2") == 4
    assert calls == [], "a module was recompiled although the store had it"
    assert cas.STATS.misses == first[1], "second worktree missed"

    # Acceptance 1 end to end: change the import, the dependent rebuilds.
    (pkg / "src" / "b.ritz").write_text("pub struct S\n    x: i64\n")
    assert _fresh_worktree_build(buildpy, tmp_path, pkg, main, "wt3") == 8
    assert len(calls) == 2, "b and main must both recompile"


@pytest.mark.integration
@pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")
def test_concurrent_build_py_processes_share_one_store(tmp_path, private_store):
    """Acceptance 3: two build.py processes, one cold store, 20 rounds."""
    pkg, main = _pkg(tmp_path)
    (pkg / "ritz.toml").write_text(
        '[package]\nname = "app"\nversion = "0.1.0"\nsources = ["src"]\n\n'
        '[[bin]]\nname = "app"\npath = "src/main.ritz"\n')
    env = {**os.environ, "RITZ_PATH": str(PKG_DIR), cas.CAS_DIR_ENV: str(private_store)}

    def build(i):
        # Each process its own copy of the package, so only the store is shared.
        mine = tmp_path / f"p{i}"
        shutil.copytree(pkg, mine)
        r = subprocess.run([sys.executable, str(PKG_DIR / "build.py"), "build", str(mine)],
                           cwd=PKG_DIR, env=env, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        return subprocess.run([str(mine / "build" / "debug" / "app")], timeout=30).returncode

    for rnd in range(20):
        shutil.rmtree(private_store, ignore_errors=True)
        with ThreadPoolExecutor(2) as ex:
            codes = list(ex.map(build, [f"{rnd}a", f"{rnd}b"]))
        assert codes == [4, 4], f"round {rnd}: {codes}"
        objs = list((private_store / "objects").rglob("*.o"))
        assert len(objs) == 2, f"round {rnd}: {objs}"
        leftovers = [p for p in private_store.rglob(".*") if p.is_file()]
        assert leftovers == [], f"round {rnd}: temp files left: {leftovers}"


# --- test_runner -----------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")
def test_test_runner_takes_dependency_objects_from_the_store(tmp_path, monkeypatch):
    test_runner = importlib.import_module("test_runner")
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "ritz.toml").write_text('[package]\nname = "t"\nversion = "0.1.0"\nsources = ["src"]\n')
    (pkg / "src" / "b.ritz").write_text("pub fn seven() -> i32\n    7\n")
    t = pkg / "src" / "test_b.ritz"
    t.write_text("import b\n\n[[test]]\nfn test_seven() -> i32\n    assert seven() == 7\n    0\n")

    ritz0_dep_compiles = []
    real_run = test_runner.subprocess.run

    def spy(cmd, *a, **kw):
        if (any(str(c).endswith("ritz0.py") for c in cmd) and "--no-runtime" in cmd):
            ritz0_dep_compiles.append(Path(cmd[2]).name)
        return real_run(cmd, *a, **kw)
    monkeypatch.setattr(test_runner.subprocess, "run", spy)

    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert "b.ritz" in ritz0_dep_compiles
    stored = list(Path(os.environ[cas.CAS_DIR_ENV]).rglob("*.o"))
    assert stored, "test_runner did not store its dependency objects"

    ritz0_dep_compiles.clear()
    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert ritz0_dep_compiles == [], "dependencies recompiled despite store hits"

    monkeypatch.setenv("RITZ_NO_CAS", "1")
    assert test_runner.run_test_file(str(t))[:2] == (1, 0)
    assert "b.ritz" in ritz0_dep_compiles, "RITZ_NO_CAS did not bypass the store"


@pytest.mark.unit
def test_ci_local_prints_the_gate_summary(tmp_path, capsys):
    """The gate log carries the proof the ticket asks for."""
    ci_local = importlib.import_module("ci_local")
    log = tmp_path / "gate.jsonl"
    log.write_text(json.dumps({"hits": 7, "misses": 2, "bytes_written": 9,
                               "missed": [["k1", "o", "ritzlib/io.ritz"],
                                          ["k1", "o", "ritzlib/io.ritz"]]}) + "\n")
    ci_local.print_cas_summary(log)
    out = capsys.readouterr().out
    assert "[ritz-cas] gate: processes=1 hits=7 misses=2 compiled=1" in out
    assert "compiled more than once: ritzlib/io.ritz" in out
