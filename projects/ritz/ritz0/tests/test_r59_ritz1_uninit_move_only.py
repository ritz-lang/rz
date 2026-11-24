"""ritz1's sources build every move-only value whole (LARB R59, AGAST #3592).

R59, narrowed 2026-11-20 (AGAST #4328): a `var x: T` with no initialiser, T
move-only and *not splittable* (its own Drop, an enum, an array, a tuple),
starts unwritten whole; a field store, read, borrow, move or return before a
whole assignment is refused.  A splittable struct (no Drop of its own) is
definite-initialised field by field instead (#4033), so this recount is
stricter than the rule: it keeps ritz1's sources building every value whole.
ritz0 (#3477) and ritz1 (#3478) enforce the narrowed rule; #3592 converted
these sites before the bootstrap could break.

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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import move_walk  # noqa: E402
import ritz_ast as rast  # noqa: E402
from ritz0 import compile_file  # noqa: E402

RITZ_ROOT = Path(__file__).resolve().parents[2]
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
        "    w.g = G { p: null }\n"   # §13.6 (AGAST #4096): written before w drops
        "    var c: C\n"
        "    c.n = 2\n"
        "    w.n + c.n\n"
        "fn main() -> i32\n"
        "    0\n")
    _check(src, tmp_path / "r59.ll")
    assert {(line, name) for _f, line, name in uninit_move_only} == {(12, "w")}


def test_emit_module_builds_emitter_state_whole(tmp_path, uninit_move_only):
    """emitter.ritz (with its imports) has no uninitialised move-only `var`."""
    _check(EMITTER, tmp_path / "emitter.ll", no_runtime=True)
    assert sorted(set(uninit_move_only)) == []
