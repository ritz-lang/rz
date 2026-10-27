"""Persisted closure / key memo for warm `rz test --all` (AGAST #1920).

After #1915 a warm `rz test --all` still spent ~40 worker-s in
build_runner_objects and ~50 in compile_dependencies, every one a store hit:
each file unit (its own process) re-resolved ritzunit's import closure
(~900 Path.resolve calls) and recomputed the same `cas_module_key`s
(transitive import scan + per-import interface hash + module identities).

Now both are memoised in the artifact store, keyed on everything the result
depends on except the closure's file contents, and an entry is reused only
while every file of the closure it recorded still has the content it had.
"""

import importlib
import importlib.util
import os
import shutil
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
RITZ0_DIR = PKG_DIR / "ritz0"
for d in (str(PKG_DIR), str(RITZ0_DIR)):
    if d not in sys.path:
        sys.path.insert(0, d)

# By name: test_tools_requirements reads a bare import as a third-party dep.
cas = importlib.import_module("cas")
cache_mod = importlib.import_module("cache")

HAS_CLANG = shutil.which("clang") is not None
needs_clang = pytest.mark.skipif(not HAS_CLANG, reason="clang not on PATH")


@pytest.fixture(autouse=True)
def private_store(tmp_path, monkeypatch):
    """Never touch the real ~/.cache/ritz/cas; reset per-process counters."""
    root = tmp_path / "cas"
    monkeypatch.setenv(cas.CAS_DIR_ENV, str(root))
    monkeypatch.delenv(cas.STATS_LOG_ENV, raising=False)
    monkeypatch.delenv("RITZ_NO_CAS", raising=False)
    monkeypatch.delenv("RITZ_NO_KEY_MEMO", raising=False)
    monkeypatch.delenv("RITZ_VERIFY_IR", raising=False)
    monkeypatch.setattr(cas, "STATS", cas.Stats())
    return root


@pytest.fixture
def buildpy(tmp_path):
    """A fresh build.py, so a monkeypatch cannot leak between tests."""
    spec = importlib.util.spec_from_file_location(
        f"ritz_buildpy_1920_{tmp_path.name}", PKG_DIR / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pkg(tmp_path):
    """src/a.ritz imports b, which imports c."""
    pkg = tmp_path / "pkg"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "c.ritz").write_text("pub fn three() -> i32\n    3\n")
    (pkg / "src" / "b.ritz").write_text(
        "import c\n\npub fn seven() -> i32\n    three() + 4\n")
    (pkg / "src" / "a.ritz").write_text(
        "import b\n\npub fn eight() -> i32\n    seven() + 1\n")
    return pkg


def _fresh_cache(tmp_path, pkg):
    """A BuildCache as a new process sees it: no in-memory scans."""
    c = cache_mod.BuildCache(project_root=tmp_path / "proj", compiler="ritz0")
    c.set_import_context(project_root=pkg, source_roots=["src"])
    return c


def _key(buildpy, tmp_path, pkg, src, **kw):
    return buildpy.cas_module_key(src, _fresh_cache(tmp_path, pkg), "ritz0", **kw)


def _unmemoised(buildpy, tmp_path, pkg, src, monkeypatch, **kw):
    monkeypatch.setenv("RITZ_NO_KEY_MEMO", "1")
    try:
        return _key(buildpy, tmp_path, pkg, src, **kw)
    finally:
        monkeypatch.delenv("RITZ_NO_KEY_MEMO")


def _no_scans(monkeypatch):
    """Fail if anything rescans the import graph."""
    def boom(self, *a, **kw):
        raise AssertionError("import closure rescanned on a memo hit")
    monkeypatch.setattr(cache_mod.BuildCache, "get_transitive_dependencies", boom)


def _bump(path: Path, text: str):
    """Rewrite `path` with a guaranteed-new mtime (memo keys on stat too)."""
    st = path.stat()
    path.write_text(text)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))


# --- cas_module_key -----------------------------------------------------------


@pytest.mark.unit
def test_warm_key_needs_no_closure_scan(tmp_path, monkeypatch, buildpy):
    pkg = _pkg(tmp_path)
    a = pkg / "src" / "a.ritz"
    cold = _key(buildpy, tmp_path, pkg, a)
    assert cold is not None
    _no_scans(monkeypatch)
    assert _key(buildpy, tmp_path, pkg, a) == cold


@pytest.mark.unit
def test_memoised_key_equals_the_unmemoised_one(tmp_path, monkeypatch, buildpy):
    pkg = _pkg(tmp_path)
    a = pkg / "src" / "a.ritz"
    _key(buildpy, tmp_path, pkg, a)
    assert _key(buildpy, tmp_path, pkg, a) == _unmemoised(buildpy, tmp_path, pkg, a, monkeypatch)


@pytest.mark.unit
@pytest.mark.parametrize("edit", ["source", "import_interface", "import_body",
                                  "transitive_interface", "new_import"])
def test_an_edit_in_the_closure_gives_the_fresh_key(tmp_path, monkeypatch, buildpy, edit):
    pkg = _pkg(tmp_path)
    src = pkg / "src"
    a = src / "a.ritz"
    before = _key(buildpy, tmp_path, pkg, a)
    if edit == "source":
        _bump(a, "import b\n\npub fn eight() -> i32\n    seven() + 2 - 1\n")
    elif edit == "import_interface":
        _bump(src / "b.ritz", "import c\n\npub fn seven() -> i64\n    7\n")
    elif edit == "import_body":
        _bump(src / "b.ritz", "import c\n\npub fn seven() -> i32\n    three() + 2 + 2\n")
    elif edit == "transitive_interface":
        _bump(src / "c.ritz", "pub fn three() -> i32\n    3\n\npub fn four() -> i32\n    4\n")
    elif edit == "new_import":
        (src / "d.ritz").write_text("pub fn nine() -> i32\n    9\n")
        _bump(src / "b.ritz",
              "import c\nimport d\n\npub fn seven() -> i32\n    three() + 4\n")
    after = _key(buildpy, tmp_path, pkg, a)
    assert after == _unmemoised(buildpy, tmp_path, pkg, a, monkeypatch)
    # Interfaces, not bodies (G9): only a body edit to an import keeps the key.
    assert (after == before) == (edit == "import_body")


@pytest.mark.unit
def test_a_deleted_closure_file_is_a_memo_miss(tmp_path, monkeypatch, buildpy):
    pkg = _pkg(tmp_path)
    a = pkg / "src" / "a.ritz"
    _key(buildpy, tmp_path, pkg, a)
    (pkg / "src" / "c.ritz").unlink()
    # b's import of c no longer resolves: whatever the key is now, it is the
    # one computed without the memo.
    assert _key(buildpy, tmp_path, pkg, a) == _unmemoised(buildpy, tmp_path, pkg, a,
                                                          monkeypatch)


@pytest.mark.unit
@pytest.mark.parametrize("change", ["verify_ir", "object_flags", "compiler_fp",
                                    "interfaces_off", "import_context"])
def test_the_memo_is_keyed_on_everything_but_the_closure(tmp_path, monkeypatch, buildpy,
                                                         change, private_store):
    pkg = _pkg(tmp_path)
    a = pkg / "src" / "a.ritz"
    base = _key(buildpy, tmp_path, pkg, a)
    kw = {}
    if change == "verify_ir":
        monkeypatch.setenv("RITZ_VERIFY_IR", "1")
    elif change == "object_flags":
        kw["object_flags"] = ["-c", "-O0"]
    elif change == "compiler_fp":
        monkeypatch.setattr(cache_mod.BuildCache, "_get_current_compiler_hash",
                            lambda self: "another-compiler")
    elif change == "interfaces_off":
        monkeypatch.setenv("RITZ0_NO_INTERFACES", "1")
    elif change == "import_context":
        monkeypatch.setenv("RITZ_PATH", str(tmp_path / "elsewhere"))
    changed = _key(buildpy, tmp_path, pkg, a, **kw)
    assert changed == _unmemoised(buildpy, tmp_path, pkg, a, monkeypatch, **kw)
    # Its own memo entry. Another RITZ_PATH resolves this closure the same
    # way, so only there is the key itself unchanged.
    assert len(list(private_store.rglob(f"*.{buildpy.KEY_MEMO_EXT}"))) == 2
    assert (changed == base) == (change == "import_context")


@pytest.mark.unit
def test_an_unparseable_import_is_not_memoised(tmp_path, monkeypatch, buildpy):
    pkg = _pkg(tmp_path)
    a = pkg / "src" / "a.ritz"
    good = (pkg / "src" / "c.ritz").read_text()
    _bump(pkg / "src" / "c.ritz", "pub fn three( -> \n")
    assert _key(buildpy, tmp_path, pkg, a) is None
    _bump(pkg / "src" / "c.ritz", good)
    fixed = _key(buildpy, tmp_path, pkg, a)
    assert fixed is not None
    assert fixed == _unmemoised(buildpy, tmp_path, pkg, a, monkeypatch)


@pytest.mark.unit
def test_a_key_that_could_not_be_computed_is_not_memoised(tmp_path, monkeypatch, buildpy):
    """No key (an interface that would not load, say) is retried next time,
    even with the closure unchanged."""
    pkg = _pkg(tmp_path)
    a = pkg / "src" / "a.ritz"
    real = buildpy._cas_key
    monkeypatch.setattr(buildpy, "_cas_key", lambda *a, **kw: None)
    assert _key(buildpy, tmp_path, pkg, a) is None
    monkeypatch.setattr(buildpy, "_cas_key", real)
    assert _key(buildpy, tmp_path, pkg, a) is not None


@pytest.mark.unit
def test_memo_entries_are_gc_able_store_objects_and_not_counted(tmp_path, buildpy,
                                                                private_store):
    pkg = _pkg(tmp_path)
    _key(buildpy, tmp_path, pkg, pkg / "src" / "a.ritz")
    _key(buildpy, tmp_path, pkg, pkg / "src" / "a.ritz")
    memos = list((private_store / "objects").rglob(f"*.{buildpy.KEY_MEMO_EXT}"))
    assert len(memos) == 1
    # Store hit/miss counts are about artifacts; a warm gate reports 0 misses.
    assert (cas.STATS.hits, cas.STATS.misses) == (0, 0)
    removed, _ = cas.ArtifactStore().gc(0)
    assert removed >= 1 and not memos[0].exists()


@pytest.mark.unit
def test_no_key_memo_env_bypasses_the_memo(tmp_path, monkeypatch, buildpy, private_store):
    pkg = _pkg(tmp_path)
    monkeypatch.setenv("RITZ_NO_KEY_MEMO", "1")
    _key(buildpy, tmp_path, pkg, pkg / "src" / "a.ritz")
    assert not list(private_store.rglob(f"*.{buildpy.KEY_MEMO_EXT}"))


# --- ritzunit's source closure ------------------------------------------------


@pytest.fixture
def test_runner():
    return importlib.import_module("test_runner")


def _fake_ritzunit(tmp_path, monkeypatch, test_runner):
    root = tmp_path / "ritzunit"
    (root / "src").mkdir(parents=True)
    (root / "ritz.toml").write_text(
        '[package]\nname = "ritzunit"\nversion = "0.1.0"\nsources = ["src"]\n')
    (root / "src" / "util.ritz").write_text("pub fn one() -> i32\n    1\n")
    main = root / "src" / "bin_main.ritz"
    main.write_text("import util\n\nfn main() -> i32\n    one() - 1\n")
    monkeypatch.setattr(test_runner, "RITZUNIT_ROOT", root)
    monkeypatch.setattr(test_runner, "RITZUNIT_MAIN", main)
    return root, main


def _no_resolves(monkeypatch, test_runner):
    def boom(*a, **kw):
        raise AssertionError("ritzunit's closure re-resolved on a memo hit")
    monkeypatch.setattr(test_runner, "collect_all_source_files", boom)


@pytest.mark.unit
def test_ritzunit_sources_resolve_once(tmp_path, monkeypatch, test_runner):
    _fake_ritzunit(tmp_path, monkeypatch, test_runner)
    cold = test_runner._ritzunit_sources()
    assert [Path(s).name for s in cold] == ["util.ritz", "bin_main.ritz"]
    _no_resolves(monkeypatch, test_runner)
    assert test_runner._ritzunit_sources() == cold


@pytest.mark.unit
def test_ritzunit_sources_follow_a_new_import(tmp_path, monkeypatch, test_runner):
    root, main = _fake_ritzunit(tmp_path, monkeypatch, test_runner)
    test_runner._ritzunit_sources()
    (root / "src" / "extra.ritz").write_text("pub fn two() -> i32\n    2\n")
    _bump(main, "import util\nimport extra\n\nfn main() -> i32\n    one() + two() - 3\n")
    assert sorted(Path(s).name for s in test_runner._ritzunit_sources()) == [
        "bin_main.ritz", "extra.ritz", "util.ritz"]


@pytest.mark.unit
def test_ritzunit_sources_without_the_memo_resolve_every_time(tmp_path, monkeypatch,
                                                              test_runner):
    _fake_ritzunit(tmp_path, monkeypatch, test_runner)
    test_runner._ritzunit_sources()
    monkeypatch.setenv("RITZ_NO_KEY_MEMO", "1")
    _no_resolves(monkeypatch, test_runner)
    with pytest.raises(AssertionError):
        test_runner._ritzunit_sources()


@pytest.mark.integration
@needs_clang
def test_warm_runner_objects_rescan_nothing(tmp_path, monkeypatch, test_runner):
    """The real ritzunit: a second build_runner_objects (as a new file unit
    would run it) neither resolves imports nor scans a closure."""
    (tmp_path / "a").mkdir()
    first, err = test_runner.build_runner_objects(str(tmp_path / "a"), {})
    assert err is None, err
    test_runner._build_module()._build_cache.clear()  # a new process' cache
    _no_resolves(monkeypatch, test_runner)
    _no_scans(monkeypatch)

    def no_compile(*a, **kw):
        raise AssertionError("ritzunit module compiled uncached on a warm run")
    monkeypatch.setattr(test_runner, "_ritz0_compile_dependency", no_compile)
    (tmp_path / "b").mkdir()
    second, err = test_runner.build_runner_objects(str(tmp_path / "b"), {})
    assert err is None, err
    assert len(second) == len(first)
