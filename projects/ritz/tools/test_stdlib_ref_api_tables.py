"""STDLIB_REFERENCE's API tables name symbols that exist (AGAST #4530).

AGAST #4445 turned most of ritzlib's `prefix_verb(x, ...)` free functions into
impl methods (`x.verb(...)`). The doc-example blocks are compiled by
`make check-doc-examples` and were updated with it, but the prose
"Function | Signature" tables are not compiled, and they went on listing
`result_is_ok`, `span_len`, `writer_write`, `socket_bind`, ... as the API.

These checks read the tables against the ritzlib source:

- every `Method` row (`` `v.name(...)` ``) names a `pub fn` inside an impl in
  that section's module (`**Module**: `ritzlib.x``), or in ritzlib if the
  section names none;
- every `Function` row (`` `name` ``) names a top-level fn somewhere in ritzlib;
- a method-call row (`` `v.name(...)` ``) is never under a `Function` header.

They check names, not signatures: a signature column is read by people.
"""

import re
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZLIB = RITZ_ROOT / "ritzlib"
STDLIB_REF = RITZ_ROOT / "docs" / "STDLIB_REFERENCE.md"

FREE_FN = re.compile(r"^(?:pub )?(?:async )?(?:extern )?fn (\w+)", re.MULTILINE)
METHOD_FN = re.compile(r"^\s+(?:pub )?(?:async )?fn (\w+)", re.MULTILINE)
MODULE_LINE = re.compile(r"^\*\*Module\*\*: `ritzlib\.([\w.]+)`")
# First cell of a table row: `v.name(...)` (method call) or `name` (free fn).
METHOD_CELL = re.compile(r"^\| `(\w+)\.(\w+)")
FREE_CELL = re.compile(r"^\| `(\w+)`")


def _module_sources(module: str) -> list[Path]:
    """ritzlib/<module>.ritz plus, for a package, every file under it."""
    base = RITZLIB.joinpath(*module.split("."))
    files = [base.with_suffix(".ritz")] if base.with_suffix(".ritz").exists() else []
    if base.is_dir():
        files += sorted(base.rglob("*.ritz"))
    return files


def _names(pattern: re.Pattern, files) -> set[str]:
    return {n for f in files for n in pattern.findall(f.read_text())}


ALL_SOURCES = sorted(RITZLIB.rglob("*.ritz"))
ALL_FREE = _names(FREE_FN, ALL_SOURCES)
ALL_METHODS = _names(METHOD_FN, ALL_SOURCES)


def _table_rows(text: str):
    """(line_no, header_kind, module, row) for every API table row outside fences.

    header_kind is the first header cell (`Function` or `Method`); module is the
    enclosing section's `**Module**:` (None before the first one in a section).
    """
    module = None
    kind = None
    fenced = False
    for no, line in enumerate(text.split("\n"), 1):
        if line.startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        if line.startswith("### ") or line.startswith("## "):
            module = None
            kind = None
            continue
        m = MODULE_LINE.match(line)
        if m:
            module = m.group(1)
            continue
        if line.startswith("| Function |") or line.startswith("| Method |"):
            kind = line.split("|")[1].strip()
            continue
        if not line.startswith("|"):
            kind = None
            continue
        if kind and not re.match(r"^\|\s*-", line):
            yield no, kind, module, line


def _rows():
    return list(_table_rows(STDLIB_REF.read_text()))


@pytest.mark.unit
def test_method_rows_name_impl_methods():
    """`v.name(...)` in a Method table is an impl method of the section's module."""
    missing = []
    for no, kind, module, row in _rows():
        m = METHOD_CELL.match(row)
        if kind != "Method" or not m:
            continue
        name = m.group(2)
        known = _names(METHOD_FN, _module_sources(module)) if module else ALL_METHODS
        if name not in known:
            missing.append(f"line {no}: {m.group(1)}.{name} (module {module})")
    assert missing == [], "Method rows with no such impl method:\n" + "\n".join(missing)


@pytest.mark.unit
def test_function_rows_name_free_fns():
    """`name` in a Function table is a top-level fn in ritzlib, not a removed one."""
    missing = []
    for no, kind, _module, row in _rows():
        m = FREE_CELL.match(row)
        if kind != "Function" or not m:
            continue
        if m.group(1) not in ALL_FREE:
            missing.append(f"line {no}: {m.group(1)}")
    assert missing == [], "Function rows with no such free fn:\n" + "\n".join(missing)


@pytest.mark.unit
def test_method_calls_are_not_under_a_function_header():
    """A `v.name(...)` row belongs in a `| Method |` table (AGAST #4445's surface)."""
    misfiled = [
        f"line {no}: {row.split('|')[1].strip()}"
        for no, kind, _module, row in _rows()
        if kind == "Function" and METHOD_CELL.match(row)
    ]
    assert misfiled == [], "method rows under a Function header:\n" + "\n".join(misfiled)
