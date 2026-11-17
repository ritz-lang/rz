"""AGAST #3794: an assert message is a `"..."` literal, never `c"..."`.

LANGUAGE_SPEC gives the form as `assert cond, "message"`: the message is a
StrView literal.  A `c"..."` message is "C in Ritz clothing" (AGENT.md, the
No Concessions Doctrine) and every compiler refuses it with a located error
(ritz0/test_assert_rules.py).  This guard keeps the tree clean of the form,
so a file nobody compiles in CI can't keep it alive either.

Only the *message* is matched: the c-string literal after the assert's last
top-level comma, at the end of the line.  A `c"..."` argument inside the
condition (`assert buf_eq(p, c"a\\n", 2) == 1, "msg"`) is a *u8 value, not a
message, and is fine.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECTS = Path(__file__).resolve().parents[2]

# `assert <cond>, c"<msg>"` with only a comment after the literal.
CSTRING_MESSAGE_RE = re.compile(
    r'^\s*assert\b.*,\s*c"(?:[^"\\]|\\.)*"\s*(?:#.*)?$')


def find_cstring_messages(root: Path) -> list[str]:
    """Every `path:line` under root whose assert message is a c-string."""
    hits = []
    for path in sorted(root.rglob("*.ritz")):
        text = path.read_text(errors="replace")
        if 'c"' not in text:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if CSTRING_MESSAGE_RE.match(line):
                hits.append(f"{path.relative_to(root)}:{n}")
    return hits


@pytest.mark.parametrize("line", [
    'assert n == 3, c"three"',
    '    assert ok, c"say \\"hi\\""  # why',
    '    assert buf_eq(p, c"a\\n", 2) == 1, c"buffer"',
])
def test_detects_a_cstring_message(line):
    assert CSTRING_MESSAGE_RE.match(line)


@pytest.mark.parametrize("line", [
    'assert n == 3, "three"',
    '    assert buf_eq(p, c"a\\n", 2) == 1, "buffer"',
    '    assert buf_eq(p, c"a\\n", 2) == 1',
    '    let s: *u8 = c"assert x, c\\"m\\""',
    '    # assert x, c"m"',
])
def test_ignores_anything_else(line):
    assert not CSTRING_MESSAGE_RE.match(line)


def test_no_assert_has_a_cstring_message():
    hits = find_cstring_messages(PROJECTS)
    assert not hits, (
        'an assert message is a "..." literal: drop the `c` (AGAST #3794):\n  '
        + "\n  ".join(hits))
