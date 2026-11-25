"""nexus's World/App tests build the value whole before borrowing it (LARB R59).

R59, narrowed 2026-11-20 (AGAST #4328): a `var x: T` with no initialiser, T
move-only and *not splittable* (its own Drop, an enum, an array, a tuple),
starts unwritten whole; a field store, read, borrow, move or return before a
whole assignment is refused.  A splittable struct (no Drop of its own) is
definite-initialised field by field instead (#4033); this recount is stricter
than the rule and keeps nexus building values whole.  nexus's tests declared
`var w: World` / `var app: App` and then lent them out as `world_open(@w)` /
`app_new(@app)`: 31 sites (AGAST #4158).  This recount hooks ritz0's MoveWalk
at every `var` statement and records each uninitialised move-only one, as
ritz0/test_r59_ritz1_uninit_move_only.py does for ritz1's sources.

It lives in tools/, not ritz0/, because it reads projects/nexus: in the
"ritz0 unit tests" step that would make nexus an input of tools/ritz0_scope.py
again, so a nexus-only gate could never skip that step (AGAST #4032;
tools/test_ritz0_scope.py pins it).  The tools step runs on every gate.
"""

import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
NEXUS = RITZ_ROOT.parent / "nexus"
for _p in (RITZ_ROOT / "ritz0", RITZ_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import move_walk  # noqa: E402
import ritz_ast as rast  # noqa: E402
from ritz0 import compile_file  # noqa: E402


@pytest.fixture
def uninit_move_only(monkeypatch):
    """Every `var x: T` with no initialiser and T move-only that ritz0's
    move checker walks, as (file, line, name)."""
    hits = []
    orig = move_walk.MoveWalk._stmt_var

    def hooked(self, stmt):
        if (stmt.value is None and stmt.type is not None
                and self.types.is_move_only(stmt.type)):
            hits.append((stmt.span.file, stmt.span.line, stmt.name))
        return orig(self, stmt)

    checks = dict(move_walk.MoveWalk.STMT_CHECKS)
    checks[rast.VarStmt] = hooked
    monkeypatch.setattr(move_walk.MoveWalk, "STMT_CHECKS", checks)
    monkeypatch.setenv("RITZ_PATH", str(RITZ_ROOT))
    return hits


def _check(src: Path, out: Path, **kw) -> None:
    assert compile_file(str(src), str(out), check_ownership=True, **kw)


@pytest.mark.integration
def test_nexus_worlds_are_built_whole(tmp_path, monkeypatch, uninit_move_only):
    """No `var w: World` / `var app: App` is lent out before it is whole."""
    # What `rz test nexus` hands build.py: the package's import namespaces,
    # and every package it reaches on RITZ_PATH (spire's `tome.*`).
    from import_resolver import DependencyMapping
    from resolve import (dependency_package_dirs, package_import_namespaces,
                         read_manifest)
    config = read_manifest(NEXUS)
    deps = {name: DependencyMapping(name=name, path=Path(spec.path),
                                    sources=spec.sources)
            for name, spec in package_import_namespaces(config, NEXUS).items()}
    path = [str(p.resolve()) for p in dependency_package_dirs(NEXUS)[1:]]
    monkeypatch.setenv("RITZ_PATH", ":".join(path + [str(RITZ_ROOT)]))
    for name in ("test_wiki_service", "test_presenters", "test_wiki_app"):
        _check(NEXUS / "test" / f"{name}.ritz", tmp_path / f"{name}.ll",
               dependencies=deps, source_roots=["src", "."],
               project_root=str(NEXUS), test_mode=True)
    # ritzlib.ptr's ptr_read is the move-out primitive under Vec.pop/replace:
    # its `var out: T` is filled by a bitwise copy, never lent half-built.
    # tome's Pool<T> instantiates it at a move-only T (AGAST #4692).
    ptr_read = str(RITZ_ROOT / "ritzlib" / "ptr.ritz")
    assert sorted({h for h in uninit_move_only if h[0] != ptr_read}) == []
