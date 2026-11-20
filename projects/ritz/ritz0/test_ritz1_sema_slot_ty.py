"""AGAST #4404 (#1816): Sema annotates the slot type the emitter reads.

THE CHANGE

`get_expr_type` (emitter_core.ritz) is the emitter's typer; it reads
EmitterState mid-lowering.  #1816 moves typing onto Sema.  This first slice
takes the arms whose answer the node alone decides -- literals, a cast's
written target, a comparison's i64 bool slot (#1646), and `@` / `@&` / `not`
/ `~` -- and moves their rule to `expr_local_slot_ty` (ast_query.ritz).
sema_walk records it on every expression it reaches in `Expr.sema_ty`
(`sema_note_expr_ty`), and get_expr_type's arms now read that annotation
through `expr_slot_ty` instead of carrying their own copy.  A node built
after the walk (a print placeholder's parsed expression) has no record, so
`expr_slot_ty` falls back to the same node-local rule: no EmitterState either
way.

Byte-identical IR is the load-bearing requirement: the three tests below pin
(a) which nodes Sema annotates and with what, (b) that an annotation never
changes the emitted IR, and (c) the emit-time nodes that only the fallback
can type (the `ritzlib/iovec.ritz` regression this slice hit: a print
placeholder's `{x as i64}` parsed after the walk printed as `?`).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_ref_into_value import RITZ1_BUILD, RITZ_ROOT, _compile, _emit

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

# TYPE_* and EXPR_* (ritz1/src/ast.ritz).
UNKNOWN, I32, I64, U8, BOOL, PTR, MUT_REF = -1, 1, 2, 3, 4, 5, 103
STRUCT, F64 = 100, 13
E_INT, E_STRING, E_NIL, E_IDENT, E_BINARY = 1, 2, 3, 4, 5
E_UNARY, E_CALL, E_CAST, E_INDEX, E_MEMBER = 6, 7, 8, 9, 10
E_CHAR, E_CSTRING, E_FLOAT = 13, 16, 20

SHAPES = """\
struct P
    x: i32

fn id(n: i64) -> i64
    n

fn main() -> i32
    var v: i32 = 3
    let b: bool = v < 4
    var p: P = P { x: 5 }
    let q: *P = @p
    let r = @&v
    let nb: i64 = (not b) as i64
    let cw: i64 = (~nb) as i64
    let fl: i64 = 1.5 as i64
    let ch: i64 = 'a' as i64
    let u8v: u8 = 7 as u8
    let cs: *u8 = c"hi"
    let np: *P = null
    var arr: [2]i32 = [1, 2]
    let e: i64 = arr[1] as i64
    let st = "x"
    let m: i32 = p.x
    let call: i64 = id(nb)
    ((r as i64) * 0 + (q as i64 as *P as i64) * 0) as i32
"""

# The slot Sema must record, per expression kind: what get_expr_type said
# before #4404, so every one of these is an IR-neutral move.
SLOTS = {
    E_INT: {I64},
    E_FLOAT: {F64},
    E_CHAR: {U8},
    E_STRING: {STRUCT},
    E_CSTRING: {PTR},
    E_NIL: {PTR},
    E_CAST: {I32, I64, U8, PTR},
    E_UNARY: {PTR, MUT_REF, I64},   # @, @&, not / ~ -- never a deref
    E_BINARY: {I64},                # a comparison's bool slot; arithmetic stays unknown
}

# Kinds whose slot needs Sema's scope: the rest of #4404.  They are annotated
# (TYPE_UNKNOWN) but must not print a slot, and the emitter still types them.
NO_SLOT = {E_IDENT, E_CALL, E_INDEX, E_MEMBER}

SLOT = re.compile(r"^sema-slot: (\d+):(\d+) e(\d+) (-?\d+)$", re.M)

# A print placeholder parses its expression *after* the Sema walk, so only
# get_expr_type's node-local fallback can type `{n as i64}` / `{2}`.  Without
# it the cast reads `?` and printing it is refused (the iovec.ritz case).
PLACEHOLDER = """\
fn main() -> i32
    var n: i32 = 3
    print("{n as i64}\\n")
    print("{2}\\n")
    print("{(n + 1) as i64}\\n")
    0
"""


def _probe(value):
    return dict(os.environ, RITZ1_SEMA_PROBE=value)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_sema_annotates_the_node_local_slot_types(request, tmp_path, compiler, monkeypatch):
    request.getfixturevalue("ritz1_bin")
    monkeypatch.setenv("RITZ1_SEMA_PROBE", "dump")
    comp, ll, _ = _compile(compiler, tmp_path, "slots", SHAPES)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"
    seen = {}
    for line, col, kind, slot in SLOT.findall(out):
        seen.setdefault(int(kind), set()).add(int(slot))
    for kind, want in SLOTS.items():
        assert seen.get(kind) == want, \
            f"{compiler}: e{kind} slots {sorted(seen.get(kind, set()))}, wanted {sorted(want)}\n{out}"
    for kind in NO_SLOT:
        assert kind not in seen, \
            f"{compiler}: e{kind} got a slot {sorted(seen[kind])}; it needs Sema's scope\n{out}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_annotation_changes_no_ir(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    # One source path: a private fn's symbol hashes it (AGAST #4356), so a
    # second directory would differ for that reason alone.
    work = tmp_path / f"ir_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(SHAPES)
    ll_off, ll_on = work / "off.ll", work / "on.ll"
    off = _emit(compiler, src, ll_off, work)
    assert off.returncode == 0 and ll_off.exists(), f"{compiler} refused it:\n{off.stdout}{off.stderr}"
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setenv("RITZ1_SEMA_PROBE", "1")
        on = _emit(compiler, src, ll_on, work)
    finally:
        monkeypatch.undo()
    out = on.stdout + on.stderr
    assert on.returncode == 0 and ll_on.exists(), f"{compiler} refused it:\n{out}"
    assert ll_on.read_bytes() == ll_off.read_bytes(), \
        f"{compiler}: the annotation changed the emitted IR"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_print_placeholder_still_prints(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "placeholder", PLACEHOLDER)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), \
        f"{compiler}: a placeholder's post-walk cast lost its slot:\n{out}"
