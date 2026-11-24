"""AGAST #4404 / #4410 (#1816): Sema annotates the slot type the emitter reads.

THE CHANGE

`get_expr_type` (emitter_core.ritz) was the emitter's typer; it read
EmitterState mid-lowering.  #4404 moved the arms whose answer the node alone
decides -- literals, a cast's written target, a comparison's i64 bool slot
(#1646), and `@` / `@&` / `not` / `~` -- to `expr_local_slot_ty`
(ast_query.ritz).  #4410 moved the rest onto Sema: identifiers, indexing,
deref, arithmetic, member access, calls and method calls are typed by
`sema_slot_ty` (sema_type.ritz) from Sema's typed scope.  sema_walk records
the answer on every expression it reaches in `Expr.sema_ty`
(`sema_note_expr_ty`), and every former call site reads it through
`expr_slot_ty`.

`get_expr_type` is gone.  The one emitter-side typer left is
`synth_slot_ty`, which types only nodes built after the walk -- a print
placeholder's parsed expression -- and notes their slots at construction.
`expr_slot_ty` still falls back to `expr_local_slot_ty` for any node with no
record.

Byte-identical IR is the load-bearing requirement: the tests below pin
(a) which nodes Sema annotates and with what, (b) that an annotation never
changes the emitted IR, (c) the emit-time nodes the construction-time typer
covers (the `ritzlib/iovec.ritz` regression: a print placeholder's
`{x as i64}` parsed after the walk printed as `?`), (d) Sema's slot agrees
with the emitter's typer on the whole matrix corpus, and (e) `get_expr_type`
and its call sites are gone.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_ref_into_value import RITZ1_BUILD, RITZ_ROOT, _compile, _emit


COMPILERS = ["ritz1", "ritz1_selfhosted"]

# TYPE_* and EXPR_* (ritz1/src/ast.ritz).
UNKNOWN, I32, I64, U8, BOOL, PTR, MUT_REF = -1, 1, 2, 3, 4, 5, 103
STRUCT, ARRAY, F64 = 100, 101, 13
E_INT, E_STRING, E_NIL, E_IDENT, E_BINARY = 1, 2, 3, 4, 5
E_UNARY, E_CALL, E_CAST, E_INDEX, E_MEMBER = 6, 7, 8, 9, 10
E_STRUCT_LIT, E_CHAR, E_CSTRING, E_FLOAT = 11, 13, 16, 20

SHAPES = """\
struct P
    x: i32

fn id(n: i64) -> i64
    n

fn main() -> i32
    var v: i32 = 3
    var w: i32 = 5
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
    let pw: *i32 = @w
    let dw: i32 = *pw
    let fa: f64 = 1.0 + 2.0
    let ia: u8 = u8v + 1
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
    E_UNARY: {I32, PTR, MUT_REF, I64},  # @, @&, not / ~, and a scalar deref
    E_BINARY: {I64, F64, U8},            # comparison, float / narrow arithmetic
    E_IDENT: {I32, I64, U8, PTR, STRUCT, ARRAY, MUT_REF},
    E_CALL: {I64},
    E_INDEX: {I64},
    E_MEMBER: {I32},
    E_STRUCT_LIT: {I64},                # the emitter's default
}

# Kinds whose slot needed Sema's scope: the rest of #4404.  They all print a
# slot now (AGAST #4410), so none is left here.
NO_SLOT = set()

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
    return dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ1_SEMA_PROBE=value)


@pytest.mark.integration
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


@pytest.mark.integration
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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_print_placeholder_still_prints(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "placeholder", PLACEHOLDER)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), \
        f"{compiler}: a placeholder's post-walk cast lost its slot:\n{out}"


SLOT_SUMMARY = re.compile(r"sema-probe-slot: (\d+) compared, (\d+) mismatched, "
                          r"(\d+) lenient")
SLOT_CORPUS_FLOOR = 15000


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_sema_slot_agrees_with_the_emitter_on_the_matrix_corpus(request, tmp_path, compiler):
    """The whole former get_expr_type rule, checked against the emitter's own
    typer on every expression it lowers.  This is the slot half of the probe's
    coverage; test_ritz1_sema_type.py holds the source-type half."""
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    # A private cache: the corpus is also run by test_ritz1_sema_type.py with
    # the same probe, and a shared cache would skip the second run and print
    # no summary.
    env = dict(_probe("1"), RITZ_CACHE_DIR=str(tmp_path / "slot-cache"))
    compared = 0
    mismatches = []
    unsummarised = []
    for src in sorted((RITZ_ROOT / "ritz0" / "test").glob("*.ritz")):
        comp = subprocess.run([str(binary), str(src), "-o", str(tmp_path / "out.ll")],
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
        out = comp.stdout + comp.stderr
        mismatches += [ln for ln in out.splitlines() if ln.startswith("slot at ")]
        summary = SLOT_SUMMARY.search(out)
        if summary:
            compared += int(summary.group(1))
            assert summary.group(2) == "0", f"{compiler}: {src.name}\n{summary.group(0)}"
        elif comp.returncode == 0:
            unsummarised.append(src.name)
    assert not mismatches, f"{compiler}: Sema's slot and the emitter disagree:\n" + "\n".join(mismatches)
    assert not unsummarised, f"{compiler}: compiled without a probe summary: {unsummarised}"
    assert compared >= SLOT_CORPUS_FLOOR, f"{compiler}: only {compared} slots compared"


def test_get_expr_type_and_its_call_sites_are_gone():
    src = RITZ_ROOT / "ritz1" / "src"
    hits = []
    for path in src.glob("*.ritz"):
        for i, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#", 1)[0]
            if "get_expr_type" in code:
                hits.append(f"{path.name}:{i}: {line.strip()}")
    assert not hits, "get_expr_type is gone; these still name it:\n" + "\n".join(hits)
