"""The ritz0 compiler hash is ritz0's import set, nothing more (AGAST #4314, #3915).

`cache.compute_compiler_hash("ritz0")` keys the CAS and the persisted import
scans; `emitter/fn_cache.COMPILER_HASH` keys every `.ritz.sig`.  Both used to
walk ritz0/ minus `test_*` names, so they disagreed about test_runner.py
(#4314) and both covered conftest.py and the test harness (batching.py,
fast_link.py, ritz0_inproc.py, spawn_guard.py): an edit to the harness
invalidated every sig and cached artifact (LARB review/5 ritz0.md N3).

Now one function, `compiler_identity.hash_ritz0_sources`, hashes the files
ritz0's entry points can import.  The oracle here walks the real import graph
with `ast` (every `import` and `from ... import`, including those inside
functions, plus the `__init__.py` of each package entered); the production
scanner is a line regex, ~40x faster, and must find the same set.
"""

import ast
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
RITZ0 = PKG_DIR / "ritz0"
HARNESS_FILES = ("batching.py", "fast_link.py", "ritz0_inproc.py", "spawn_guard.py")

_spec = importlib.util.spec_from_file_location("ritz_cache_3915", PKG_DIR / "cache.py")
cache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cache)

if str(RITZ0) not in sys.path:
    sys.path.append(str(RITZ0))
import compiler_identity  # noqa: E402


def _package_inits(base: Path, parts):
    """`__init__.py` of each package `parts` passes through, under `base`."""
    return [base.joinpath(*parts[:i], "__init__.py") for i in range(1, len(parts) + 1)
            if base.joinpath(*parts[:i], "__init__.py").is_file()]


def _local_module(dotted: str):
    """The repo files a top-level import of `dotted` loads, or [] (stdlib,
    third party). ritz0.py runs with ritz0/ and projects/ritz on sys.path."""
    parts = dotted.split(".")
    for base in (RITZ0, PKG_DIR):
        for cand in (base.joinpath(*parts).with_suffix(".py"),
                     base.joinpath(*parts) / "__init__.py"):
            if cand.is_file():
                return [cand, *_package_inits(base, parts[:-1])]
    return []


def _imports_of(path: Path):
    """Local files `path` imports, anywhere in its body."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        if isinstance(node, ast.Import):
            for a in node.names:
                found += _local_module(a.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found += _local_module(node.module)
            # `from pkg import submodule`
            for a in node.names:
                found += _local_module(f"{node.module}.{a.name}")
        elif isinstance(node, ast.ImportFrom):
            base = path.parent
            for _ in range(node.level - 1):
                base = base.parent
            mod = node.module.split(".") if node.module else []
            for cand in (base.joinpath(*mod).with_suffix(".py") if mod else None,
                         base.joinpath(*mod, "__init__.py")):
                if cand is not None and cand.is_file():
                    found.append(cand)
                    break
            for a in node.names:
                for cand in (base.joinpath(*mod, a.name).with_suffix(".py"),
                             base.joinpath(*mod, a.name, "__init__.py")):
                    if cand.is_file():
                        found.append(cand)
                        break
    return [f.resolve() for f in found]


def _ritz0_import_closure():
    seen = set()
    todo = [(RITZ0 / e).resolve() for e in compiler_identity.ENTRY_POINTS]
    while todo:
        f = todo.pop()
        if f not in seen:
            seen.add(f)
            todo += _imports_of(f)
    return seen


def _hashed():
    return {p.resolve() for p in compiler_identity.ritz0_sources(RITZ0)}


def test_the_import_graph_reaches_test_runner():
    """Sanity: the walk sees the `--test` mode's deferred import."""
    assert (RITZ0 / "test_runner.py").resolve() in _ritz0_import_closure()


def test_the_hash_covers_exactly_the_import_graph():
    """The regex scanner finds what `ast` finds: no module ritz0 can import is
    missed, and nothing it cannot import (tests, harness) is hashed."""
    oracle = _ritz0_import_closure()
    hashed = _hashed()
    rel = lambda s: sorted(str(p.relative_to(PKG_DIR)) for p in s)  # noqa: E731
    assert not oracle - hashed, f"imported by ritz0 but not hashed: {rel(oracle - hashed)}"
    assert not hashed - oracle, f"hashed but not imported by ritz0: {rel(hashed - oracle)}"


def test_the_hash_covers_list_deps():
    """build.py runs ritz0/list_deps.py for every compile's --deps."""
    assert (RITZ0 / "list_deps.py").resolve() in _hashed()


def test_cache_and_fn_cache_share_one_hash_function():
    from emitter import fn_cache
    assert fn_cache.hash_ritz0_sources is compiler_identity.hash_ritz0_sources
    assert fn_cache.COMPILER_HASH == compiler_identity.hash_ritz0_sources(RITZ0)


def test_harness_lives_outside_the_compiler_package():
    for name in HARNESS_FILES:
        assert not (RITZ0 / name).exists(), f"ritz0/{name} is test harness, not compiler"
        assert (RITZ0 / "harness" / name).is_file(), name


@pytest.fixture
def tree(tmp_path):
    """A copy of projects/ritz's Python: the compiler, drivers and harness."""
    def ignore(d, names):
        return [n for n in names
                if n in ("__pycache__", ".pytest_cache", "test")
                or (not n.endswith(".py") and not Path(d, n).is_dir())
                or (n.startswith("test_") and n != "test_runner.py")]
    root = tmp_path / "ritz"
    shutil.copytree(RITZ0, root / "ritz0", ignore=ignore)
    for f in PKG_DIR.glob("*.py"):
        shutil.copy(f, root)
    return root


def _touch(path: Path):
    path.write_text(path.read_text() + "\n# edited\n")


@pytest.mark.parametrize("rel", [
    "ritz0/conftest.py",
    *(f"ritz0/harness/{n}" for n in HARNESS_FILES),
    "ritz0/test_lexer.py",
])
def test_editing_test_support_leaves_the_hash(tree, rel):
    path = tree / rel
    if not path.exists():
        path.write_text("# a pytest module\n")
    before = cache.compute_compiler_hash(tree, "ritz0")
    sig_before = compiler_identity.hash_ritz0_sources(tree / "ritz0")
    _touch(path)
    assert cache.compute_compiler_hash(tree, "ritz0") == before, rel
    assert compiler_identity.hash_ritz0_sources(tree / "ritz0") == sig_before, rel


@pytest.mark.parametrize("rel", [
    "ritz0/emitter_llvmlite.py",
    "ritz0/test_runner.py",
    "ritz0/emitter/fn_cache.py",
    "ritz0/emitter/__init__.py",
    "ritz0/list_deps.py",
    "cas.py",
    "build.py",
])
def test_editing_compiler_code_changes_the_hash(tree, rel):
    before = cache.compute_compiler_hash(tree, "ritz0")
    sig_before = compiler_identity.hash_ritz0_sources(tree / "ritz0")
    _touch(tree / rel)
    assert cache.compute_compiler_hash(tree, "ritz0") != before, rel
    if rel != "build.py":  # a driver, not imported by ritz0
        assert compiler_identity.hash_ritz0_sources(tree / "ritz0") != sig_before, rel
