"""AGAST #4035: the parser builds a recursive `TypeRef`.

#1889 FIX step 1, split out as #4035.  This file covers the parser half:

1. `struct TypeRef` (ast.ritz) is the parser's type: `type_spec` returns
   `*TypeRef`, and the pointer/array/reference chain is the recursion
   (`pointee` / `elem`), not a flat kind plus 17 parser side channels.
2. The `Parser.last_*` type side channels are gone.  Every fact a consumer
   needs travels on the `*TypeRef` the grammar hands it.
3. `types.ritz` answers the primitive facts from a `*TypeRef` (`tr_flat`,
   `tr_store_size`, ...), next to the flat `ty_*` table the emitter still uses.

The `LocalVar` collapse (the third invariant of the ticket) is staged
separately: it rewrites ~850 field accesses inside `emitter*.ritz`, which
`ritz-task-1817` is rewriting in the same tree.  See
test_ritz1_localvar_collapse.py.

The tests are source greps (the freeze-test idiom, see
test_ritz1_localvar_fields.py and test_ritz1_emitterstate_fields.py): cheap,
and they fail naming the file that still carries the old shape.  Behaviour --
that parsed `**T` / `[N]*T` / `@&T` lower byte-identically -- is covered by
matrix-full and scripts/regression.sh.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
RITZ1 = TOOLS.parent / "ritz1"
SRC = RITZ1 / "src"
AST = SRC / "ast.ritz"
AST_HELPERS = SRC / "ast_helpers.ritz"
GRAMMAR = TOOLS.parent / "grammars" / "ritz1.grammar"
PARSER_GEN = SRC / "parser_gen.ritz"
TYPES = SRC / "types.ritz"

# The 17 flat type side channels type_spec left on Parser (#4035, #4407).
SIDE_CHANNELS = (
    "last_type_name",
    "last_type_name_len",
    "last_pointee_type",
    "last_inner_pointee_type",
    "last_ptr_depth",
    "last_array_size",
    "last_array_elem_type",
    "last_array_elem_type_name",
    "last_array_elem_type_name_len",
    "last_array_elem_pointee",
    "last_array_shape",
    "last_call_type_suffix",
    "last_call_type_suffix_len",
    "last_ref_inner_type",
    "last_inner_ref",
    "last_fn_sig",
    "last_fn_sig_pos",
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
def test_typeref_is_the_recursive_parser_type():
    fields = _struct_fields(AST, "TypeRef")
    for want in ("kind", "name", "pointee", "elem", "count"):
        assert want in fields, f"ast.ritz: TypeRef.{want} is missing"
    # The chain is the recursion: pointee and elem point at TypeRef.
    assert re.search(r"pointee\s*:\s*\*TypeRef", fields["pointee"]), \
        "TypeRef.pointee is not *TypeRef"
    assert re.search(r"elem\s*:\s*\*TypeRef", fields["elem"]), \
        "TypeRef.elem is not *TypeRef"


@pytest.mark.unit
def test_type_spec_returns_a_typeref():
    grammar = GRAMMAR.read_text()
    for rule in ("type_spec", "type_spec_shr"):
        m = re.search(r"^" + rule + r"\s*->\s*(\S+)\s*$", grammar, re.MULTILINE)
        assert m, f"grammar: rule {rule} not found"
        assert m.group(1) == "*TypeRef", f"grammar: {rule} returns {m.group(1)}, not *TypeRef"
    gen = PARSER_GEN.read_text()
    for fn in ("parse_type_spec", "parse_type_spec_shr"):
        m = re.search(r"fn " + fn + r"\(p: \*Parser\)\s*->\s*(\S+)", gen)
        assert m, f"parser_gen.ritz: {fn} not found"
        assert m.group(1) == "*TypeRef", f"parser_gen.ritz: {fn} returns {m.group(1)}"


@pytest.mark.unit
def test_parser_has_no_type_side_channels():
    fields = _struct_fields(AST, "Parser")
    for name in SIDE_CHANNELS:
        assert name not in fields, f"ast.ritz: Parser.{name} is back (#4035)"


@pytest.mark.unit
def test_nothing_reads_the_removed_side_channels():
    pat = re.compile(r"\bp\.(" + "|".join(SIDE_CHANNELS) + r")\b")
    bad = []
    for f in sorted(SRC.glob("*.ritz")):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if pat.search(line):
                bad.append(f"{f.name}:{i}")
    assert not bad, "Parser.last_* type side channels still read: " + ", ".join(bad[:20])


@pytest.mark.unit
def test_types_answers_from_a_typeref():
    text = TYPES.read_text()
    for fn in ("tr_flat", "tr_store_size", "tr_align", "tr_mem_llvm",
               "tr_value_llvm", "tr_name", "tr_pointee", "tr_elem",
               "tr_is_ptr", "tr_depth"):
        assert re.search(r"^(?:pub )?fn " + fn + r"\(", text, re.MULTILINE), \
            f"types.ritz: {fn} (the *TypeRef form) is missing"
