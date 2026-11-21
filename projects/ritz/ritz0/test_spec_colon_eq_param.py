"""AGAST #4062: LANGUAGE_SPEC must define the `:=` parameter modifier.

THE DEFECT

    fn take(c:= C) -> i32
        ...

compiles on ritz0, ritz1 and ritz1_selfhosted (the grammar carries
`SELF COLON_EQ type_spec` for AGAST #3249 and `IDENT COLON_EQ type_spec` for
AGAST #1527), but `docs/LANGUAGE_SPEC.md` did not mention `:=` anywhere: §3.2
listed only `name:& T`, and the grammar sketch at the end never defined the
`param` production at all.  The retired docs/STYLE.md taught `:=` as "move
ownership", so the construct shipped and was taught while the standard was
silent.  docs/STANDARD.md S-PTR-1 then told authors not to write it.

THE RULING

Never delete a shipped, parser-supported construct to match a stale spec.
`name:= T` is a by-value parameter whose move sigil records ownership intent;
it lowers identically to `name: T` and carries no additional semantics (§13.2
already moves a by-value move-only parameter).  `self:= T` is the same
lowering.  The struct-field `:=` that ritz0 alone accepts is NOT a language
feature and must be documented as such.

This test pins the standard to the ruling.  It is text-only; the fenced
`ritz` block it looks for is compiled by tools/check_doc_examples.py under
all three compilers (`make check-doc-examples` and
`make check-doc-examples-ritz1`), so the example's behaviour is gated
separately.
"""

from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
SPEC = RITZ_ROOT / "docs" / "LANGUAGE_SPEC.md"
STANDARD = RITZ_ROOT / "docs" / "STANDARD.md"


def _section(text: str, heading: str) -> str:
    """Return the body of ``heading`` up to the next heading of same or higher level."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip().startswith(heading))
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    for i in range(start + 1, len(lines)):
        stripped = lines[i].lstrip("#")
        if lines[i].startswith("#") and len(lines[i]) - len(stripped) <= level:
            return "\n".join(lines[start:i])
    return "\n".join(lines[start:])


def _fenced_ritz_blocks(text: str):
    """Yield the info-string and body of every ```ritz fenced block."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```ritz"):
            info = line.strip()[3:]
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            yield info, "\n".join(body)
        i += 1


@pytest.mark.unit
def test_pointer_section_lists_move_parameter():
    """§3.2's parameter table must list the `:=` form beside `name:& T`."""
    section = _section(SPEC.read_text(), "### 3.2 Pointer and Reference Types")
    assert "name:= T" in section, (
        "§3.2 does not list `name:= T`; the compiler accepts it (AGAST #4062)"
    )
    assert "name: T" in section or "by-value" in section, (
        "§3.2 must say the `:=` parameter is the by-value `name: T` lowering"
    )


@pytest.mark.unit
def test_move_semantics_defines_colon_eq_as_by_value():
    """§13.2 must define `name:= T` as `name: T` with no extra semantics."""
    section = _section(SPEC.read_text(), "### 13.2 Move Semantics")
    assert "name:= T" in section, (
        "§13.2 does not define `name:= T` (AGAST #4062)"
    )
    assert "lowers identically" in section or "identical" in section, (
        "§13.2 must state that `:=` lowers identically to `name: T`"
    )
    assert "no additional semantics" in section, (
        "§13.2 must state that the `:=` sigil carries no additional semantics"
    )


@pytest.mark.unit
def test_grammar_sketch_defines_param_production():
    """The end-of-spec grammar sketch must define `param`, including `:=`."""
    text = SPEC.read_text()
    assert "param        :=" in text or "param :=" in text, (
        "the grammar sketch never defines the `param` production"
    )
    param_line = next(
        (line for line in text.splitlines()
         if line.strip().startswith("param") and ":=" in line),
        None,
    )
    assert param_line is not None, (
        "the `param` production in the grammar sketch has no `':='` alternative"
    )


@pytest.mark.unit
def test_positive_block_covers_all_three_shapes():
    """A compile-gated positive block must show r:= T, self:= T and the
    external-consumer shape `fn add_contour(self:& GlyphOutline, contour:= Contour)`."""
    positive = [
        body for info, body in _fenced_ritz_blocks(SPEC.read_text())
        if "expect-error" not in info and "no-compile" not in info
    ]
    matching = [
        body for body in positive
        if "r:= R" in body and "self:= " in body
        and "contour:= Contour" in body and "self:& GlyphOutline" in body
    ]
    assert matching, (
        "LANGUAGE_SPEC has no compile-gated positive block covering the `:=` "
        "parameter forms (r:= T, self:= T, and the add_contour shape)"
    )


@pytest.mark.unit
def test_struct_field_colon_eq_is_documented_as_not_a_feature():
    """All three compilers refuse `pos:= i64`; the spec must say so."""
    text = SPEC.read_text()
    assert "struct field" in text.lower(), (
        "LANGUAGE_SPEC must mention the struct-field `:=` position"
    )
    lowered = text.lower()
    assert "not a language feature" in lowered or "not part of the language" in lowered, (
        "the spec must say struct-field `:=` is not a language feature (ritz1 refuses it)"
    )


@pytest.mark.unit
def test_standard_points_at_spec_instead_of_forbidding_colon_eq():
    """S-PTR-1 must stop forbidding `:=` and point at the spec text."""
    section = _section(STANDARD.read_text(), "#### S-PTR-1")
    assert "doesn't define it" not in section and "does not define it" not in section, (
        "S-PTR-1 still says LANGUAGE_SPEC doesn't define `:=`"
    )
    assert ":=" in section, "S-PTR-1 must mention the `:=` parameter modifier"
    assert "§13.2" in section or "#4062" in section, (
        "S-PTR-1 must point at the defining spec text (AGAST #4062)"
    )
