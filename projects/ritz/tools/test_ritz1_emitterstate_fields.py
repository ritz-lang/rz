"""AGAST #1816: EmitterState carries lowering state, not Sema side-channels.

#1816 asked for "the EmitterState fields that only carry facts between Sema
checks and lowering" to be deleted, and offered a grep over
`last_match_agg_name` / `ctx_enum_name` / `sret_last_val` as the acceptance
test (101 hits).  That grep measures the wrong thing.  As measured on the
train tail this file was written against (`8f62d1af`):

- Sema runs before `emit_module` and never holds an `EmitterState`: no
  `sema*.ritz` imports an emitter module or names the type outside a comment.
- The Sema->lowering channel is the **AST annotation**, not EmitterState:
  `Expr.sema_ty` (#4404), `Expr.value_ty_name` (#3042) and
  `Expr.sema_levels` (#4428).  Sema writes them; the emitter reads them.
- The grep's 101 hits are all **lowering state** -- match slot/hint types,
  scrutinee typing, slot context, current fn/sret/narrowing/frame/tables/
  counters/the IR buffer.  Deleting them would need new Sema annotations,
  not deletion.  `EmitterState` was 91 fields before and after.

So the closing artefact is this test: the field count is frozen at the
measured value, and the channel is asserted to be the AST annotation.  A new
EmitterState field is lowering state -- update `MEASURED_FIELDS` in the commit
that adds it.  A new fact that Sema knows and lowering needs goes on the AST
annotation instead; the checks below fail if a `sema*.ritz` grows an
EmitterState.

The tests are source greps (the freeze-test idiom, see
test_ritz1_emitter_check_freeze.py and test_ritz1_localvar_fields.py): cheap,
and they fail naming the file that carried the fact.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS.parent / "ritz1" / "src"
EMITTER_CORE = SRC / "emitter_core.ritz"
AST = SRC / "ast.ritz"
AST_QUERY = SRC / "ast_query.ritz"
SEMA_WALK = SRC / "sema_walk.ritz"
SEMA_TYPE = SRC / "sema_type.ritz"

# Measured on `8f62d1af` (2026-11-21): 91 fields, unchanged from #1816's
# 026c732b measurement despite the Sema-annotation work landed between them.
# The count is the ticket: the side-channel fields were never there to delete.
#
# #4460 added five, all lowering state: entry_allocas and its saved out/reg
# (the entry-block buffer and the swap), plus ea_marks/ea_count/ea_cap (the
# frame-limit marks each buffered alloca records as it is emitted).
#
# #4461 added three, all lowering state: dloads/dload_count/dload_cap hold the
# whole-struct loads this fn deferred (the sret copy choice is made at the
# store site now), so they are the emitter's own buffer and counters, exactly
# like entry_allocas and its marks -- not a fact Sema knows.
#
# #4462 removed one and added two: packed_types_emitted went (the module-wide
# "run the align pass" flag), and packed_marks/packed_marks_cap arrived -- the
# per-register packed provenance each GEP records as it is emitted, which the
# load/store sites consult.  Both are lowering state, like the buffers above.
#
# #4454 added `mono`: monomorphisation's tables, which were module globals.
# Lowering records a generic enum first named at emission there.
#
# #4607 added one: platform_stop, the PSTOP_* bits for a freestanding
# module's stops (is the target a kernel; did a stop call
# ritz_platform_fatal; did emit_platform_hooks define it).  Lowering state,
# moved off three module globals so #4454's budget holds.
#
# #4697 split it, counting unchanged: the 102 are EmitterState's own fields
# plus those of its four parts (PARTS), so moving a field between parts is
# not a new field, and a new one counts wherever it lands.
#
# #4852 added one: fcx.x86_features, the X86F_* bits add_extern sets as a fn
# body names an x86 ISA-extension intrinsic (it replaced a 3x memcmp scan of
# each fn's IR text).  Per-fn lowering state, reset at each fn's start.
#
# #4773 removed seven: each FnCtx name that was a `*u8` + `_len: i32` pair
# (ret_type_name, ctx_enum_name, ctx_slot_name, ctx_simd_name,
# last_match_agg_name, last_if_stmt_agg_name, match_agg_hint) is one
# StrView, so the same state is seven fields fewer.
MEASURED_FIELDS = 96

# AGAST #4697: EmitterState is these four parts (field -> struct), the
# dispatch seam and the hooks.  Each part is a struct in emitter_core.ritz.
PARTS = {"ir": "IrBuf", "fcx": "FnCtx", "sym": "SymTab", "diag": "Diag"}
TOP_FIELDS = ("own", "emit", "own_before_ret_fn", "ref_cast_reads_referent_fn")

# The three names the superseded acceptance grep counted (101 hits on main).
# They are lowering state: every file that touches them is emitter-side.
GREP_NAMES = ("last_match_agg_name", "ctx_enum_name", "sret_last_val")

# The AST annotations that are the Sema->lowering channel.
AST_ANNOTATIONS = ("sema_ty", "value_ty_name", "sema_levels")


def _struct_fields(text: str, name: str) -> dict[str, str]:
    """Field name -> line of every field in the `struct <name>` block.

    An indented `name: type` line is a field; a comment or a blank line is
    not.  Only the struct's own block is read, not the fns that take it.
    """
    m = re.search(rf"^struct {re.escape(name)}\n((?:[ \t]+.*\n|\n)*)",
                  text, re.MULTILINE)
    assert m, f"struct {name} not found"
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        f = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
        if f:
            fields[f.group(1)] = line
    return fields


def _strip_comments(text: str) -> str:
    """The source with `# ...` to end of line removed."""
    return re.sub(r"#[^\n]*", "", text)


def _field_lines() -> dict[str, str]:
    """Every lowering-state field: EmitterState's own, a part's expanded.

    A part field (`ir: IrBuf`) is not counted itself; its struct's fields are,
    keyed `ir.out`, so the count is the state, not the grouping (#4697).
    """
    text = EMITTER_CORE.read_text()
    fields: dict[str, str] = {}
    for name, line in _struct_fields(text, "EmitterState").items():
        if name in PARTS:
            for sub, sub_line in _struct_fields(text, PARTS[name]).items():
                fields[f"{name}.{sub}"] = sub_line
        else:
            fields[name] = line
    return fields


def _references(value: str, files: list[Path]) -> list[str]:
    """`file:line` per non-comment mention of `value` in `files`."""
    pat = re.compile(r"\b" + re.escape(value) + r"\b")
    hits = []
    for f in files:
        for i, line in enumerate(_strip_comments(f.read_text()).splitlines(), 1):
            if pat.search(line):
                hits.append(f"{f.name}:{i}")
    return hits


@pytest.mark.unit
def test_emitterstate_fields_are_frozen_at_the_measured_count():
    fields = _field_lines()
    found = len(fields)
    assert found == MEASURED_FIELDS, (
        f"emitter_core.ritz: EmitterState has {found} fields, frozen at "
        f"{MEASURED_FIELDS} (#1816).  A new field is lowering state: update "
        f"MEASURED_FIELDS in this file deliberately.  A fact Sema knows and "
        f"lowering needs belongs on the AST annotation (Expr.sema_ty, "
        f"value_ty_name, sema_levels), not on EmitterState."
    )
    assert len(fields) == len(set(fields)), "duplicate field name in EmitterState"


@pytest.mark.unit
def test_emitterstate_is_its_four_parts_the_seam_and_the_hooks():
    # AGAST #4697: the 102 fields were one struct.  They are four parts by
    # lifetime (the module's IR, the fn being emitted, the module's symbols,
    # what was reported); only the seam and the two hooks stay on top.  A new
    # field joins a part, not EmitterState itself.
    own = _struct_fields(EMITTER_CORE.read_text(), "EmitterState")
    want = [f"{n}: {t}" for n, t in PARTS.items()] + list(TOP_FIELDS)
    got = [f"{n}: {line.split(':', 1)[1].split('#')[0].strip()}" if n in PARTS else n
           for n, line in own.items()]
    assert got == want, (
        f"emitter_core.ritz: EmitterState's own fields are {got}, expected "
        f"{want}: a new field belongs in IrBuf / FnCtx / SymTab / Diag (#4697)")
    for part in PARTS.values():
        assert _struct_fields(EMITTER_CORE.read_text(), part), f"struct {part} is empty"


@pytest.mark.unit
def test_sema_modules_never_name_emitterstate():
    # The Sema->lowering channel is the AST: a sema module holding or naming
    # an EmitterState would be the side-channel #1816 looked for.  Comments
    # may discuss it (the module header does), code may not.
    sema = sorted(SRC.glob("sema*.ritz"))
    assert {"sema", "sema_type", "sema_walk", "sema_probe"} <= {
        p.stem for p in sema}
    for f in sema:
        hits = _references("EmitterState", [f])
        assert not hits, (
            f"{', '.join(hits)}: Sema names EmitterState; the channel is the "
            f"AST annotation (#1816)")


@pytest.mark.unit
def test_the_annotations_live_on_the_ast():
    expr = _struct_fields(AST.read_text(), "Expr")
    for name in AST_ANNOTATIONS:
        assert name in expr, (
            f"ast.ritz: Expr.{name} is missing; the Sema->lowering channel is "
            f"the AST annotation (#1816)")
    # Written and read through ast_query, never by poking the field directly.
    query = AST_QUERY.read_text()
    for fn in ("expr_note_sema_ty", "expr_sema_ty", "expr_has_sema_ty",
               "expr_slot_ty"):
        assert re.search(rf"^pub fn {fn}\(", query, re.MULTILINE), (
            f"ast_query.ritz: {fn} is missing; the annotation has no accessor")


@pytest.mark.unit
def test_sema_writes_the_annotation_and_the_emitter_reads_it():
    # Sema side: sema_type's slot typer notes the kind on the node.
    assert _references("expr_note_sema_ty", [SEMA_TYPE]), (
        "sema_type.ritz no longer writes Expr.sema_ty")
    # Lowering side: the emitter asks ast_query, which reads the annotation.
    assert "expr_slot_ty" in _strip_comments(EMITTER_CORE.read_text()), (
        "emitter_core.ritz no longer reads Expr.sema_ty via expr_slot_ty")
    slot_ty = re.search(r"^pub fn expr_slot_ty\(.*?\n(.*?)(?=\n(?:pub )?fn )",
                        AST_QUERY.read_text(), re.MULTILINE | re.DOTALL)
    assert slot_ty, "ast_query.ritz: expr_slot_ty body not found"
    assert "sema_ty" in slot_ty.group(1), (
        "ast_query.ritz: expr_slot_ty no longer reads e.sema_ty")
    # The other two annotations are read by the emitter directly.
    assert _references("value_ty_name", sorted(SRC.glob("emitter*.ritz"))), (
        "no emitter module reads Expr.value_ty_name (#3042)")
    assert _references("sema_levels", sorted(SRC.glob("emitter*.ritz"))), (
        "no emitter module reads Expr.sema_levels (#4428)")


@pytest.mark.unit
def test_the_superseded_grep_names_are_lowering_state():
    fields = _field_lines()
    bare = {k.rsplit(".", 1)[-1] for k in fields}
    for name in GREP_NAMES:
        assert name in bare, (
            f"EmitterState.{name} is gone; the #1816 grep measured lowering "
            f"state, so its deletion needs a new AST annotation, not a delete")
        hits = _references(name, sorted(SRC.glob("*.ritz")))
        assert hits, f"nothing in ritz1/src uses EmitterState.{name}"
        sema_hits = [h for h in hits if h.startswith("sema")]
        assert not sema_hits, (
            f"{', '.join(sema_hits)}: Sema names EmitterState.{name}; it is "
            f"lowering state and must stay emitter-side (#1816)")


@pytest.mark.unit
def test_the_field_parser_counts_only_real_fields():
    # The guard is only as good as its scan: a planted field counts, a
    # comment that looks like one and a blank line do not.
    text = (
        "struct EmitterState\n"
        "    a: i32\n"
        "    # b: i32\n"
        "\n"
        "    c: *u8\n"
        "\n"
        "pub fn f(s: *EmitterState)\n"
        "    s.a = 1\n"
    )
    assert _struct_fields(text, "EmitterState") == {
        "a": "    a: i32", "c": "    c: *u8"}
