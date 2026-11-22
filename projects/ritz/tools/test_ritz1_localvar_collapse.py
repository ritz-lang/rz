"""AGAST #4035 (staged): LocalVar collapses to name + `*TypeRef` + flags.

This is the third invariant of #4035:

    LocalVar (ast_query.ritz) keeps only `name` + `*TypeRef` + the binding
    mode/refinement flags the emitter mutates, <= 12 fields.

#4035 shipped the parser half; #4528 attached the `*TypeRef` to
Stmt.var_ty / Param.param_ty, populated LocalVar.ty in add_local_full and
rewrote the flat reads to the lv_* accessors, so this test is live.

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
def test_localvar_is_name_ty_and_binding_flags():
    fields = _struct_fields(AST_QUERY, "LocalVar")
    assert len(fields) <= LOCALVAR_LIMIT, (
        f"ast_query.ritz: LocalVar has {len(fields)} fields, limit {LOCALVAR_LIMIT}")
    assert "ty" in fields, "LocalVar.ty (the parsed *TypeRef) is missing"
    assert re.search(r"ty\s*:\s*\*TypeRef", fields["ty"]), "LocalVar.ty is not *TypeRef"
    for flat in FLAT_TYPE_FACTS:
        assert flat not in fields, f"ast_query.ritz: LocalVar.{flat} is still flat"
