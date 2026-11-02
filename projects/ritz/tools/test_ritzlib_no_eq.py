"""ritzlib.eq is gone and stays gone (AGAST #2066).

ritzlib/eq.ritz held three wrappers around `==` (eq_i32, eq_i64, eq_u64) that
returned 1/0 as i32 instead of bool. The docs called it an "Equality trait",
which it was not. Its only importers were hashmap.ritz and test_level33.ritz,
and neither called it. Example 77 called it only to show it off.

These checks fail while the module, its bootstrap symlink, a ritz1 link entry,
an import or a doc entry is still around. A real Eq/Hash trait would be a new
module with a new name. It would not bring this one back.
"""

import re
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent

# History, not live docs: these record that eq.ritz once existed.
ARCHIVE_DIRS = {RITZ_ROOT / "docs" / "archive"}
SKIP_PARTS = {"build", ".git", "node_modules", "__pycache__"}

IMPORT_EQ = re.compile(r"^\s*import\s+ritzlib\.eq\b", re.MULTILINE)
EQ_FN = re.compile(r"\beq_(i32|i64|u64)\s*\(")


def _ritz_sources():
    for path in RITZ_ROOT.rglob("*.ritz"):
        rel = path.relative_to(RITZ_ROOT)
        if SKIP_PARTS.intersection(rel.parts):
            continue
        # A dangling symlink (the bootstrap one, if left behind) has no text.
        if not path.exists():
            continue
        yield path


def test_eq_module_is_deleted():
    assert not (RITZ_ROOT / "ritzlib" / "eq.ritz").exists()


def test_bootstrap_symlink_is_deleted():
    link = RITZ_ROOT / "ritz1" / "bootstrap_ritzlib" / "eq.ritz"
    # lexists, not exists: a symlink to a deleted file must go as well.
    assert not link.is_symlink() and not link.exists()


def test_ritz1_does_not_link_eq():
    text = (RITZ_ROOT / "ritz1" / "Makefile").read_text()
    m = re.search(r"^RITZLIB_MODULES\s*=(.*)$", text, re.MULTILINE)
    assert m, "ritz1/Makefile has no RITZLIB_MODULES line"
    assert "eq" not in m.group(1).split()


def test_nothing_imports_ritzlib_eq():
    offenders = [str(p.relative_to(RITZ_ROOT)) for p in _ritz_sources()
                 if IMPORT_EQ.search(p.read_text(errors="replace"))]
    assert offenders == []


def test_nothing_calls_the_eq_wrappers():
    offenders = [str(p.relative_to(RITZ_ROOT)) for p in _ritz_sources()
                 if EQ_FN.search(p.read_text(errors="replace"))]
    assert offenders == []


@pytest.mark.parametrize("doc", [
    "docs/STDLIB_REFERENCE.md",
    "docs/RITZLIB.md",
    "ritzlib/README.md",
])
def test_docs_do_not_list_eq(doc):
    text = (RITZ_ROOT / doc).read_text()
    assert "ritzlib.eq" not in text
    assert "eq.ritz" not in text
    # \b keeps ritzlib.testing's assert_eq_i32 & co. out of it.
    assert not re.search(r"\beq_(i32|i64|u64)\b", text)
