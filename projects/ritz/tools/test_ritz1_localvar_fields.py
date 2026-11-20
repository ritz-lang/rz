"""AGAST #4406: LocalVar keeps only the emitter's lowering state (#1816).

`LocalVar` (ritz1/src/ast_query.ritz) is the emitter's record of a local.
Several of its fields exist only to carry a fact between a Sema check and
lowering -- or to carry it into the Sema-side place image `ref_check` builds
(`RsNote.loc`) -- and the emitter never reads them.  They are deleted here;
the fact is read from Sema instead.

Each deleted field, the fact it carried, and where that fact now comes from:

- `is_caller_place` (#2340): 1 for a `:&` param / `self:&` receiver whose
  place is the caller's.  `ref_mark_params` set it on the emitter's local and
  nothing read it.  own_check reads `RsNote.caller_place`, filled from
  `rv_caller_place` on Sema.
- `ref_ptr_pointee` (#2364): U of an `@*U` / `@&*U` param or local.  Read
  only by `ref_of_local` typing Sema's place image; the emitter's lowering
  callers of `ref_ty_of` read the kind and the name, never the pointee.
  `RsNote.ptr_pointee` carries it now, set from `Param.param_ref_ptr_pointee`
  / `ref_decl_ptr_pointee` by ref_value's hooks, and `ref_of_ident_in` copies
  it onto the RefTy.

The tests are source greps (the freeze-test idiom, see
test_ritz1_emitter_check_freeze.py): cheap, and they fail naming the file
that still carries a field.  The behaviour the two facts drive is covered by
the borrow/reference suites (test_value_into_ref.py's #2364 rows,
test_borrow_param_ref_slot.py, test_at_into_mut.py).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
SRC = TOOLS.parent / "ritz1" / "src"
LOCALVAR = SRC / "ast_query.ritz"
REF_CHECK = SRC / "ref_check.ritz"

# Deleted from LocalVar by #4406, with the Sema home of the fact they carried.
GONE = {
    "is_caller_place": "RsNote.caller_place",
    "ref_ptr_pointee": "RsNote.ptr_pointee",
}


def _field_lines(text: str) -> dict[str, str]:
    """The field name -> line of every `LocalVar` field in its struct block."""
    m = re.search(r"^struct LocalVar\n((?:[ \t]+.*\n|\n)*)", text, re.MULTILINE)
    assert m, "struct LocalVar not found in ast_query.ritz"
    fields = {}
    for line in m.group(1).splitlines():
        f = re.match(r"^    ([a-z_]+):", line)
        if f:
            fields[f.group(1)] = line
    return fields


@pytest.mark.unit
def test_localvar_has_no_side_channel_field():
    fields = _field_lines(LOCALVAR.read_text())
    for name in GONE:
        assert name not in fields, f"ast_query.ritz: LocalVar.{name} is back (#4406)"


@pytest.mark.unit
def test_nothing_in_ritz1_reads_the_deleted_fields():
    # \b: `param_ref_ptr_pointee` and `field_ref_ptr_pointee` are other facts.
    for name in GONE:
        pat = re.compile(r"\b" + re.escape(name) + r"\b")
        for f in sorted(SRC.glob("*.ritz")):
            hit = [f"{f.name}:{i}" for i, line in enumerate(f.read_text().splitlines(), 1)
                   if pat.search(line)]
            assert not hit, f"{name} is still on LocalVar: {', '.join(hit)}"


@pytest.mark.unit
def test_the_deleted_facts_live_on_sema():
    ref = REF_CHECK.read_text()
    m = re.search(r"^(?:pub )?struct RsNote\n((?:[ \t]+.*\n|\n)*)", ref, re.MULTILINE)
    assert m, "struct RsNote not found in ref_check.ritz"
    for name, home in GONE.items():
        field = home.split(".")[1]
        assert re.search(r"^    " + re.escape(field) + r":", m.group(1), re.MULTILINE), \
            f"RsNote.{field} is missing; LocalVar.{name}'s fact has no Sema home"
    # ref_of_local types the image from LocalVar; the pointer pointee now rides
    # on the note at the ident, so the image no longer carries it.
    assert "ref_ptr_pointee" not in ref.split("fn ref_of_local", 1)[1].split("\nfn ", 1)[0], \
        "ref_of_local still reads LocalVar.ref_ptr_pointee"
