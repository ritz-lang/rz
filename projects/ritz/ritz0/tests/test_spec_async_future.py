"""LANGUAGE_SPEC §16.2/§16.3, keeping a future (LARB R79, AGAST #4010).

R79 made a future a value that can be held and handed to an executor, with a
built-in `Future` type it is referenced through and a built-in `future_poll`.
§16 is the language standard, so it must state that and stop naming the
compiler's generated items.  This test pins the standard to the ruling; the
fenced `ritz` blocks it adds are compiled by tools/check_doc_examples.py under
all three compilers (`make check-doc-examples`, `...-ritz1`), so their
behaviour is gated separately.
"""

import re

from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = RITZ_ROOT / "docs" / "LANGUAGE_SPEC.md"


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


@pytest.mark.unit
def test_section_16_2_defines_a_kept_future():
    """§16.2: `var p = f(args)` keeps the future; `await p` drives it."""
    section = re.sub(r"\s+", " ", _section(SPEC.read_text(), "### 16.2"))
    assert "var p = f(args)" in section, (
        "§16.2 does not show `var p = f(args)` keeping a future (LARB R79)"
    )
    assert "can't be named" in section or "cannot be named" in section, (
        "§16.2 must say the held future's type can't be named (LARB R79)"
    )
    assert "await p" in section and "drives a held future to completion" in section, (
        "§16.2 must say `await p` drives a held future to completion and "
        "returns its result (LARB R79)"
    )


@pytest.mark.unit
def test_section_16_3_documents_the_executor_interface():
    """§16.3: built-in `Future`, `@&Future`, `future_poll`, and `block_on`."""
    section = re.sub(r"\s+", " ", _section(SPEC.read_text(), "### 16.3"))
    assert "@&Future" in section, "§16.3 must document `@&Future` (LARB R79)"
    assert "`Future` has no size; take it by reference, `@&Future`" in section, (
        "§16.3 must give the by-value error for `Future` (LARB R79)"
    )
    assert "future_poll(f: @&Future) -> bool" in section, (
        "§16.3 must document `future_poll(f: @&Future) -> bool` (LARB R79, R78)"
    )
    assert "block_on" in section and "@&p" in section, (
        "§16.3 must show ritzlib's `rt.block_on(@&p)` (LARB R79)"
    )
    assert "stored by value" in section, (
        "§16.3 must name what isn't covered: a future stored by value"
    )
    assert "`@&Future` field" in section, (
        "§16.3 must say an `@&Future` field to a future held elsewhere works"
    )


@pytest.mark.unit
def test_section_16_names_no_generated_item():
    """No generated `NAME_Future` / `NAME_poll` may appear anywhere in §16."""
    section = _section(SPEC.read_text(), "## 16.")
    assert "_Future" not in section, (
        "§16 still names a generated future type (`NAME_Future`); LARB R79 "
        "makes the held future's type unnameable"
    )
    generated_polls = [
        name for name in re.findall(r"\b\w+_poll\b", section)
        if name != "future_poll"
    ]
    assert not generated_polls, (
        f"§16 still names generated poll fns ({generated_polls!r}); LARB R79 "
        "replaces them with the built-in `future_poll`"
    )
