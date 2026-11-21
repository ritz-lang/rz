"""AGAST #4035 (staged): LocalVar collapses to name + `*TypeRef` + flags.

This is the third invariant of #4035:

    LocalVar (ast_query.ritz) keeps only `name` + `*TypeRef` + the binding
    mode/refinement flags the emitter mutates, <= 12 fields.

It is staged separately from the parser half (test_ritz1_typeref.py) because
the flat facts on LocalVar are read ~850 times inside `emitter*.ritz` --
`emitter_stmt`, `emitter_expr_call`, `emitter_expr`, `emitter_expr_arith`,
`emitter_expr_access`, `emitter_match`, `emitter_print` and `emitter_core`.
`ritz-task-1817` is rewriting those same files (+2755/-3269 unmerged) into
typed `emitter_ir` builders, so a field-by-field rewrite of them here would
collide on nearly every changed line.  The room's brief keeps this diff off
`emitter*.ritz`.

The test is written and skipped against `ast_query.ritz`, not deleted, so the
invariant is executable the moment the emitter rewrite lands: drop the skip,
replace each flat read with the accessor in ast_query.ritz, and this passes.

The `ty` field arrives with the parser half and is asserted there
(test_ritz1_typeref.py); the Sema-side facts already moved to RsNote
(test_ritz1_localvar_fields.py).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS.parent / "ritz1" / "src"
AST_QUERY = SRC / "ast_query.ritz"

LOCALVAR_LIMIT = 12

# The flat type facts the `*TypeRef` answers instead.
FLAT_TYPE_FACTS = (
    "var_type",
    "type_name",
    "type_name_len",
    "pointee_type",
    "array_size",
    "array_elem_type",
    "array_elem_pointee",
    "inner_pointee_type",
    "inner_ref",
    "pointee_array_size",
    "pointee_array_elem_type",
    "pointee_array_elem_pointee",
    "pointee_array_elem_name",
    "pointee_array_elem_name_len",
    "array_shape",
    "pointee_array_shape",
    "array_rec",
)


def _struct_fields(path: Path, name: str) -> dict[str, str]:
    text = path.read_text()
    m = re.search(r"^(?:pub )?struct " + re.escape(name) + r"\n((?:[ \t]+.*\n|\n)*)",
                  text, re.MULTILINE)
    assert m, f"struct {name} not found in {path.name}"
    fields: dict[str, str] = {}
    for line in m.group(1).splitlines():
        f = re.match(r"^[ \t]+([a-z_][a-z0-9_]*)\s*:", line)
        if f:
            fields[f.group(1)] = line
    return fields


@pytest.mark.unit
@pytest.mark.skip(
    reason="staged after ritz-task-1817 rewrites emitter*.ritz; see module docstring")
def test_localvar_is_name_ty_and_binding_flags():
    fields = _struct_fields(AST_QUERY, "LocalVar")
    assert len(fields) <= LOCALVAR_LIMIT, (
        f"ast_query.ritz: LocalVar has {len(fields)} fields, limit {LOCALVAR_LIMIT}")
    assert "ty" in fields, "LocalVar.ty (the parsed *TypeRef) is missing"
    assert re.search(r"ty\s*:\s*\*TypeRef", fields["ty"]), "LocalVar.ty is not *TypeRef"
    for flat in FLAT_TYPE_FACTS:
        assert flat not in fields, f"ast_query.ritz: LocalVar.{flat} is still flat"
