"""STDLIB_REFERENCE documents ritzlib.strview (AGAST #1546).

#1472 made ritzlib/str.ritz C-string interop only and pointed its readers at
StrView, but the reference had no `### strview` section: ~30 pub fns were
undocumented. These checks fail if a pub fn (free or impl method) in
strview.ritz is missing from that section, if the section loses its compiled
example, or if it stops coming ahead of `### str` (readers meet the idiomatic
API first).
"""

import re
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
STRVIEW = RITZ_ROOT / "ritzlib" / "strview.ritz"
STDLIB_REF = RITZ_ROOT / "docs" / "STDLIB_REFERENCE.md"

PUB_FN = re.compile(r"^(\s*)pub fn (\w+)", re.MULTILINE)


def _section(text: str, heading: str) -> str:
    """Body of `### heading` up to the next `##`/`###` heading."""
    m = re.search(
        rf"^### {re.escape(heading)}\n(.*?)(?=^##)", text, re.MULTILINE | re.DOTALL
    )
    assert m, f"STDLIB_REFERENCE.md has no `### {heading}` section"
    return m.group(1)


def _pub_fns():
    """(name, is_method) for every pub fn in strview.ritz."""
    src = STRVIEW.read_text()
    return [(name, bool(indent)) for indent, name in PUB_FN.findall(src)]


@pytest.mark.unit
def test_every_pub_fn_is_documented():
    body = _section(STDLIB_REF.read_text(), "strview")
    missing = []
    for name, is_method in _pub_fns():
        # Each free fn needs its own table row; methods appear as `.name(` in the
        # methods table, so `slice` is not satisfied by `strview_slice`.
        needle = f".{name}(" if is_method else f"\n| `{name}` |"
        if needle not in body:
            missing.append(name if not is_method else f"StrView.{name}")
    assert missing == []


@pytest.mark.unit
def test_section_has_a_compiled_example():
    body = _section(STDLIB_REF.read_text(), "strview")
    # A bare ```ritz fence is compiled by check-doc-examples; no-compile is not.
    assert re.search(r"^```ritz\n", body, re.MULTILINE), (
        "strview section has no compiled ```ritz example"
    )


@pytest.mark.unit
def test_strview_comes_before_str_and_is_in_toc():
    text = STDLIB_REF.read_text()
    assert text.index("### strview\n") < text.index("### str\n")
    toc = text[text.index("## Table of Contents") : text.index("## Core Types")]
    assert toc.index("[strview](#strview)") < toc.index("[str](#str)")
