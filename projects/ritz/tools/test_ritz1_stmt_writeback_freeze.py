"""AGAST #4407: lowering does not write type facts back into the Stmt.

An unannotated `let` / `var` is typed during lowering, arm by arm: `let p =
@x` is a `*T`, `let q = h(p)` a `@[N]S`, `let o = Some(5)` an Option.  Until
#4407 each arm wrote its answer into the Stmt node (`stmt.var_type = ...`,
267 writes in emitter_stmt.ritz) and the next arm read it back.  Sema's
checks and the emitter's tagged-enum scans read the same fields, so the
parser's facts and the emitter's inference shared one mutable channel.

From #4407 the inference lives in a lowering-local `DeclTy` (emitter_stmt.ritz)
for the length of one declaration; the Stmt keeps only what the parser and
pre-Sema passes put there.  This test freezes that: in the emitter modules, a
function whose parameter is a `*Stmt` must not assign one of the inferred-type
fields on it.

A new write is either a reintroduced side channel (put the fact in DeclTy) or
a new Stmt field that belongs to the parser/Sema design instead.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS.parent / "ritz1" / "src"
EMITTER_STMT = SRC / "emitter_stmt.ritz"

# The type an inferred binding takes, as emit_var_decl_at / infer_* work it
# out.  The parser also writes them for an annotated declaration; that is the
# fact Sema reads, and it stays on the Stmt.  This list is what the emitter
# must no longer write.
INFERRED_FIELDS = (
    "var_type",
    "var_type_name",
    "var_type_name_len",
    "var_array_size",
    "var_array_elem_type",
    "var_array_elem_pointee",
    "var_array_shape",
    "var_array",
    "var_pointee_type",
    "var_inner_pointee_type",
    "var_inner_ref",
    "var_pointee_array_size",
    "var_pointee_array_elem_type",
    "var_pointee_array_elem_pointee",
    "var_pointee_array_shape",
)

_FIELD_ALT = "|".join(sorted(INFERRED_FIELDS, key=len, reverse=True))
_FN_START = re.compile(r"^(?:pub )?fn (\w+)\s*\(")
_STMT_PARAM = re.compile(r"(\w+):\s*\*Stmt\b")
_FIELD_WRITE = re.compile(r"\.(" + _FIELD_ALT + r")\s*=(?!=)")


def _signature(lines: list[str], i: int) -> str:
    """The text of the `fn` at lines[i], through its closing `)`."""
    out, depth = [], 0
    while i < len(lines):
        out.append(lines[i])
        depth += lines[i].count("(") - lines[i].count(")")
        if depth <= 0 and ")" in lines[i]:
            break
        i += 1
    return "\n".join(out)


def stmt_writes(text: str, where: str = "") -> list[str]:
    """`where:line: receiver.field` for each inferred-field write on a *Stmt.

    `receiver` is a parameter the enclosing function declares as `*Stmt`
    (usually `stmt`; `st` and `decl` occur too), so a write to a `*LocalVar`
    or `*GlobalVarDef` with the same field names is not a finding.
    """
    lines = text.splitlines()
    current, receivers = None, set()
    found = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _FN_START.match(line)
        if m:
            current = m.group(1)
            receivers = set(_STMT_PARAM.findall(_signature(lines, i)))
        if current is not None:
            for w in _FIELD_WRITE.finditer(line):
                dot = line.rfind(".", 0, w.start() + 1)
                recv = re.search(r"([A-Za-z_][A-Za-z_0-9]*)$", line[:dot])
                if recv and recv.group(1) in receivers:
                    found.append(f"{where}:{i + 1}: {recv.group(1)}.{w.group(1)}")
        i += 1
    return found


def emitter_writes(src: Path = SRC) -> list[str]:
    found = []
    for path in sorted(src.glob("emitter*.ritz")):
        found += stmt_writes(path.read_text(), path.name)
    return found


def decl_ty_fields(path: Path = EMITTER_STMT) -> set[str]:
    """The field names `struct DeclTy` declares."""
    text = path.read_text()
    m = re.search(r"^struct DeclTy\n(.*?)(?=^\S)", text, re.M | re.S)
    assert m, "struct DeclTy is missing from emitter_stmt.ritz"
    return set(re.findall(r"^    (\w+):", m.group(1), re.M))


@pytest.mark.integration
def test_the_emitter_never_writes_an_inferred_type_back_to_the_stmt():
    problems = emitter_writes()
    assert not problems, (
        "lowering wrote a type fact into the Stmt; hold it in the DeclTy "
        "declared in emit_var_decl_at instead:\n" + "\n".join(problems))


@pytest.mark.integration
def test_decl_ty_is_the_one_home_for_every_inferred_field():
    # A field dropped from DeclTy and written to the Stmt again is exactly the
    # regression this file exists for; keep the two lists identical.
    assert decl_ty_fields() == set(INFERRED_FIELDS)


@pytest.mark.unit
def test_a_planted_write_is_detected():
    text = (
        "fn typed(s: *EmitterState, stmt: *Stmt) -> i32\n"
        "    stmt.var_type = TYPE_PTR\n"
        "    stmt.var_pointee_type = TYPE_I64\n"
        "    1\n"
    )
    assert [w.split(": ")[1] for w in stmt_writes(text)] == [
        "stmt.var_type", "stmt.var_pointee_type"]


@pytest.mark.unit
def test_a_renamed_stmt_parameter_is_detected():
    text = (
        "fn typed(decl: *Stmt) -> i32\n"
        "    decl.var_type_name = c\"S\"\n"
        "    1\n"
    )
    assert [w.split(": ")[1] for w in stmt_writes(text)] == ["decl.var_type_name"]


@pytest.mark.unit
def test_a_local_var_write_is_not_a_finding():
    # Registration writes LocalVar fields with the same names; they are the
    # lowering's own record, not the AST.
    text = (
        "fn reg(s: *EmitterState, stmt: *Stmt) -> i32\n"
        "    let loc: *LocalVar = local_at(s, 0)\n"
        "    loc.var_type = TYPE_PTR\n"
        "    1\n"
    )
    assert stmt_writes(text) == []
