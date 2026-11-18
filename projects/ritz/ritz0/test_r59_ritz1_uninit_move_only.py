"""ritz1's sources build every move-only value whole (LARB R59, AGAST #3592).

R59: a `var x: T` with no initialiser, T move-only, starts as moved; a field
store, read, borrow, move or return before a whole assignment is refused.
ritz0 (#3477) and ritz1 (#3478) enforce it; once they do, any such `var` in
ritz1's own sources stops ritz0 compiling ritz1, i.e. the bootstrap.

`emit_module` declared `var s: EmitterState` (move-only: five HashMapI64
fields, which have Drop) and filled it field by field.  These tests hook
ritz0's MoveWalk at every `var` statement and record each uninitialised
move-only one, the same recount #3476 ran, so a new one is caught before R59
lands rather than by a broken bootstrap after it.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import move_walk  # noqa: E402
import ritz_ast as rast  # noqa: E402
from ritz0 import compile_file  # noqa: E402

RITZ_ROOT = Path(__file__).resolve().parent.parent
EMITTER = RITZ_ROOT / "ritz1" / "src" / "emitter.ritz"


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


@pytest.mark.unit
def test_hook_sees_an_uninitialised_move_only_var(tmp_path, uninit_move_only):
    """The control: the hook reports the R59 shape, and not a copy type."""
    src = tmp_path / "r59.ritz"
    src.write_text(
        "struct G\n"
        "    p: *u8\n"
        "impl Drop for G\n"
        "    fn drop(self: @&G)\n"
        "        return\n"
        "struct W\n"
        "    g: G\n"
        "    n: i32\n"
        "struct C\n"
        "    n: i32\n"
        "fn mk() -> i32\n"
        "    var w: W\n"
        "    w.n = 1\n"
        "    var c: C\n"
        "    c.n = 2\n"
        "    w.n + c.n\n"
        "fn main() -> i32\n"
        "    0\n")
    _check(src, tmp_path / "r59.ll")
    assert {(line, name) for _f, line, name in uninit_move_only} == {(12, "w")}


@pytest.mark.integration
def test_emit_module_builds_emitter_state_whole(tmp_path, uninit_move_only):
    """emitter.ritz (with its imports) has no uninitialised move-only `var`."""
    _check(EMITTER, tmp_path / "emitter.ll", no_runtime=True)
    assert sorted(set(uninit_move_only)) == []
