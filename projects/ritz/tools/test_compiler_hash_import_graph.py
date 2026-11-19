"""The ritz0 compiler hash covers every module ritz0.py can import (AGAST #4314).

`cache.compute_compiler_hash("ritz0")` keys the CAS and the persisted import
scans. `_collect_ritz0_sources` skipped every `test_*.py` under ritz0/, which
also skipped `ritz0/test_runner.py`: ritz0.py imports it for `--test`, so an
edit to it reused stale state for `build.py test --compiler ritz0` runs.

The module set is derived from ritz0.py's real import graph (every `import`
and `from ... import`, including those inside functions, followed
transitively through the local modules), not a hand list, so a new local
import that the hash misses fails here.
"""

import ast
import importlib.util
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parents[1]
RITZ0 = PKG_DIR / "ritz0"

_spec = importlib.util.spec_from_file_location("ritz_cache_4314", PKG_DIR / "cache.py")
cache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cache)


def _local_module(dotted: str):
    """The repo file a top-level import of `dotted` loads, or None (stdlib,
    third party). ritz0.py runs with ritz0/ and projects/ritz on sys.path."""
    parts = dotted.split(".")
    for base in (RITZ0, PKG_DIR):
        for cand in (base.joinpath(*parts).with_suffix(".py"),
                     base.joinpath(*parts) / "__init__.py"):
            if cand.is_file():
                return cand
    return None


def _imports_of(path: Path):
    """Local files `path` imports, anywhere in its body."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(), str(path))):
        if isinstance(node, ast.Import):
            found += [_local_module(a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append(_local_module(node.module))
            # `from pkg import submodule`
            found += [_local_module(f"{node.module}.{a.name}") for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = path.parent
            for _ in range(node.level - 1):
                base = base.parent
            mod = node.module.split(".") if node.module else []
            for a in node.names:
                for cand in (base.joinpath(*mod, a.name).with_suffix(".py"),
                             base.joinpath(*mod).with_suffix(".py"),
                             base.joinpath(*mod, "__init__.py")):
                    if cand.is_file():
                        found.append(cand)
                        break
    return [f.resolve() for f in found if f is not None]


def _ritz0_import_closure():
    seen, todo = set(), [(RITZ0 / "ritz0.py").resolve()]
    while todo:
        f = todo.pop()
        if f not in seen:
            seen.add(f)
            todo += _imports_of(f)
    return seen


def test_the_import_graph_reaches_test_runner():
    """Sanity: the walk sees the `--test` mode's deferred import."""
    assert (RITZ0 / "test_runner.py").resolve() in _ritz0_import_closure()


def test_every_module_ritz0_can_import_is_hashed():
    hashed = {p.resolve() for p in cache._collect_ritz0_sources(RITZ0)}
    hashed |= {(PKG_DIR / n).resolve() for n in cache.RITZ0_DRIVER_FILES}
    missing = sorted(str(p.relative_to(PKG_DIR))
                     for p in _ritz0_import_closure() - hashed)
    assert not missing, f"imported by ritz0.py but not in its compiler hash: {missing}"


def test_editing_test_runner_changes_the_ritz0_hash(tmp_path):
    ritz0 = tmp_path / "ritz0"
    ritz0.mkdir()
    (ritz0 / "ritz0.py").write_text("# main")
    runner = ritz0 / "test_runner.py"
    runner.write_text("# v1")
    (ritz0 / "test_lexer.py").write_text("# a pytest module")
    h1 = cache.compute_compiler_hash(tmp_path, "ritz0")
    runner.write_text("# v2")
    assert cache.compute_compiler_hash(tmp_path, "ritz0") != h1
    # Real test modules still don't count.
    h2 = cache.compute_compiler_hash(tmp_path, "ritz0")
    (ritz0 / "test_lexer.py").write_text("# edited")
    assert cache.compute_compiler_hash(tmp_path, "ritz0") == h2
