"""A no-op build resolves no import closure (AGAST #4775).

`discover_modules` ran ritz0/list_deps.py in a fresh interpreter for every
binary target: ~0.19 s each, lexing and parsing the whole import closure just
to print the module list. `./rz build indium` spent 6.5 of its 7.3 s warm,
all-up-to-date run doing that for its 35 targets, one after another.

Each closure is now recorded (`cache.ClosureStore`, `.ritz-cache/
closures.json`) with the evidence ritz0's own source fast path trusts
(AGAST #2030, #2087): the content hash of every file in it, every
candidate path the resolver probed and found missing before a hit, and the
hash of every ritz.toml that registered an imported namespace. A warm hit
re-hashes those files and re-checks those misses: no subprocess, no parse.

The record is keyed by everything else resolution reads: the entry file,
project root, dependency namespaces, source roots, RITZ_PATH, whether
module interfaces are on, and ritz0's identity. So it must still miss when:
  * an imported module's content changes (it may import something new);
  * a file appears that shadows an import (an earlier RITZ_PATH entry, a
    source root, the importer's own directory);
  * a dependency's path, RITZ_PATH or ritz0 itself changes.
"""

import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

import cache
from cache import ClosureStore


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# --- ClosureStore: the record and its validation (no subprocess) ----------


def _record(*, files, misses=(), configs=()) -> dict:
    return {"files": [str(f) for f in files], "misses": [str(m) for m in misses],
            "configs": [str(c) for c in configs]}


@pytest.fixture
def tree(tmp_path):
    a = write(tmp_path / "a.ritz", "pub fn a() -> i32\n    0\n")
    main = write(tmp_path / "main.ritz", "import a\n")
    return tmp_path, a, main


@pytest.mark.unit
def test_store_hit_returns_recorded_files(tree):
    root, a, main = tree
    store = ClosureStore(root / "c", identity="id")
    store.record("k", _record(files=[a, main]))
    assert store.lookup("k") == [str(a), str(main)]


@pytest.mark.unit
def test_store_persists_across_instances(tree):
    """A new build process (a new store) hits what an earlier one recorded."""
    root, a, main = tree
    ClosureStore(root / "c", identity="id").record("k", _record(files=[a, main]))
    assert ClosureStore(root / "c", identity="id").lookup("k") == [str(a), str(main)]


@pytest.mark.unit
def test_store_misses_on_unknown_key(tree):
    root, a, main = tree
    store = ClosureStore(root / "c", identity="id")
    store.record("k", _record(files=[a, main]))
    assert store.lookup("other") is None


@pytest.mark.unit
def test_store_misses_when_a_closure_file_changes(tree):
    """Editing an imported module may change what it imports."""
    root, a, main = tree
    store = ClosureStore(root / "c", identity="id")
    store.record("k", _record(files=[a, main]))
    a.write_text("import b\npub fn a() -> i32\n    0\n")
    assert ClosureStore(root / "c", identity="id").lookup("k") is None
    assert store.lookup("k") is None, "a process's stat memo must not hide the edit"


@pytest.mark.unit
def test_store_misses_when_a_closure_file_is_gone(tree):
    root, a, main = tree
    store = ClosureStore(root / "c", identity="id")
    store.record("k", _record(files=[a, main]))
    a.unlink()
    assert store.lookup("k") is None


@pytest.mark.unit
def test_store_misses_when_a_missed_candidate_appears(tree):
    """Resolution is first match: a file at a probed-and-missing candidate
    now shadows the import (AGAST #2030)."""
    root, a, main = tree
    shadow = root / "early" / "a.ritz"
    store = ClosureStore(root / "c", identity="id")
    store.record("k", _record(files=[a, main], misses=[shadow]))
    assert store.lookup("k") is not None
    write(shadow, "pub fn a() -> i32\n    1\n")
    assert store.lookup("k") is None


@pytest.mark.unit
def test_store_misses_when_a_namespace_toml_changes(tree):
    """A ritz.toml that registered a namespace decides where `<ns>.*`
    resolves (AGAST #2087)."""
    root, a, main = tree
    toml = write(root / "dep" / "ritz.toml", '[package]\nname = "dep"\n')
    store = ClosureStore(root / "c", identity="id")
    store.record("k", _record(files=[a, main], configs=[toml]))
    assert store.lookup("k") is not None
    toml.write_text('[package]\nname = "dep"\nsources = ["lib"]\n')
    assert store.lookup("k") is None


@pytest.mark.unit
def test_store_misses_when_ritz0_changes(tree):
    """ritz0's identity is in every key: a resolver change re-resolves."""
    root, a, main = tree
    ClosureStore(root / "c", identity="old").record("k", _record(files=[a, main]))
    assert ClosureStore(root / "c", identity="new").lookup("k") is None


@pytest.mark.unit
def test_compiler_change_sweeps_the_closure_store(tmp_path):
    """closures.json goes with the other scans on a compiler change."""
    assert cache.CLOSURES_FILE in cache.SCAN_FILES


# --- discover_modules: hits spawn nothing, misses re-resolve -------------


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    """build_pipeline with a private closure store and a list_deps spy."""
    import build_pipeline
    monkeypatch.setattr(build_pipeline, "_CLOSURES",
                        ClosureStore(tmp_path / "closures", identity="test"))
    calls = []
    real = build_pipeline.bounded_run.step

    def spy(cmd, *a, **kw):
        if any(str(c).endswith("list_deps.py") for c in cmd):
            calls.append(Path(str(cmd[2])).name)
        return real(cmd, *a, **kw)
    monkeypatch.setattr(build_pipeline.bounded_run, "step", spy)
    build_pipeline.calls = calls
    yield build_pipeline
    del build_pipeline.calls


def _pkg(root: Path) -> tuple[Path, Path]:
    pkg = root / "pkg"
    write(pkg / "src" / "util.ritz", "pub fn util() -> i32\n    0\n")
    main = write(pkg / "src" / "main.ritz",
                 "import util\n\nfn main() -> i32\n    util()\n")
    return pkg, main


@pytest.mark.integration
def test_warm_discover_spawns_nothing(pipeline, tmp_path):
    pkg, main = _pkg(tmp_path)
    cold = pipeline.discover_modules(main, project_root=pkg)
    assert pipeline.calls == ["main.ritz"]
    warm = pipeline.discover_modules(main, project_root=pkg)
    assert pipeline.calls == ["main.ritz"], "a warm closure re-ran list_deps.py"
    assert warm == cold
    assert [m.name for m in warm] == ["util.ritz", "main.ritz"]


@pytest.mark.integration
def test_edited_import_re_resolves(pipeline, tmp_path):
    """util.ritz now imports extra.ritz: the closure must grow."""
    pkg, main = _pkg(tmp_path)
    pipeline.discover_modules(main, project_root=pkg)
    write(pkg / "src" / "extra.ritz", "pub fn extra() -> i32\n    0\n")
    (pkg / "src" / "util.ritz").write_text(
        "import extra\n\npub fn util() -> i32\n    extra()\n")
    got = pipeline.discover_modules(main, project_root=pkg)
    assert [m.name for m in got] == ["extra.ritz", "util.ritz", "main.ritz"]
    assert len(pipeline.calls) == 2


@pytest.mark.integration
def test_shadowing_module_on_ritz_path_re_resolves(pipeline, tmp_path, monkeypatch):
    """`import shared` resolves through the second RITZ_PATH entry until a
    shared.ritz appears in the first."""
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    write(second / "shared.ritz", "pub fn shared() -> i32\n    2\n")
    monkeypatch.setenv("RITZ_PATH", f"{first}:{second}")
    pkg = tmp_path / "pkg"
    main = write(pkg / "src" / "main.ritz", "import shared\n\nfn main() -> i32\n    shared()\n")
    got = pipeline.discover_modules(main, project_root=pkg)
    assert got[0] == (second / "shared.ritz").resolve()
    write(first / "shared.ritz", "pub fn shared() -> i32\n    1\n")
    got = pipeline.discover_modules(main, project_root=pkg)
    assert got[0] == (first / "shared.ritz").resolve()


@pytest.mark.integration
def test_changed_ritz_path_re_resolves(pipeline, tmp_path, monkeypatch):
    """RITZ_PATH is in the key: a reordered path resolves `shared` anew."""
    first, second = tmp_path / "first", tmp_path / "second"
    for d in (first, second):
        write(d / "shared.ritz", "pub fn shared() -> i32\n    0\n")
    pkg = tmp_path / "pkg"
    main = write(pkg / "src" / "main.ritz", "import shared\n\nfn main() -> i32\n    shared()\n")
    for a, b in ((first, second), (second, first)):
        monkeypatch.setenv("RITZ_PATH", f"{a}:{b}")
        got = pipeline.discover_modules(main, project_root=pkg)
        assert got[0] == (a / "shared.ritz").resolve()


@pytest.mark.integration
def test_changed_dependency_path_re_resolves(pipeline, tmp_path):
    """`import dd.m` follows the dependency to its new path."""
    spec = pipeline.DependencySpec
    for d in ("d1", "d2"):
        write(tmp_path / d / "src" / "m.ritz", "pub fn m() -> i32\n    0\n")
    pkg = tmp_path / "pkg"
    main = write(pkg / "src" / "main.ritz", "import dd.m\n\nfn main() -> i32\n    m()\n")
    for d in ("d1", "d2", "d1"):
        deps = {"dd": spec(name="dd", path=tmp_path / d, sources=["src"])}
        got = pipeline.discover_modules(main, project_root=pkg, dependencies=deps)
        assert got[0] == (tmp_path / d / "src" / "m.ritz").resolve()
    assert len(pipeline.calls) == 2, "switching back to d1 should hit its record"


@pytest.mark.integration
def test_failed_resolution_is_not_recorded(pipeline, tmp_path):
    pkg = tmp_path / "pkg"
    main = write(pkg / "src" / "main.ritz", "import nowhere\n\nfn main() -> i32\n    0\n")
    assert pipeline.discover_modules(main, project_root=pkg) is None
    assert pipeline.discover_modules(main, project_root=pkg) is None
    assert len(pipeline.calls) == 2
    pipeline._REACHED.reset()
