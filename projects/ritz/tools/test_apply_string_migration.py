#!/usr/bin/env python3
"""Self-tests for apply_string_migration.py.

Covers, per AGAST #92:

  * c-rewrite path       — `"X"` -> `c"X"` at (line, col)
  * s-noop path          — suggested_prefix=s stays bare
  * skip-string path     — suggested_prefix=string goes to residual
  * skip-? path          — suggested_prefix=? goes to residual
  * s"..." deprecation   — literal `s"..."` gets stripped to `"..."`
  * context mismatch     — audit raced w/ edits => residual + exit non-zero
  * dry-run              — no file writes, diff on stdout
  * scope discipline     — --dir filters CSV rows correctly

Run with:
    python3 -m pytest projects/ritz/tools/test_apply_string_migration.py -q
"""
from __future__ import annotations

import csv
import io
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import apply_string_migration as asm  # noqa: E402


# ---------------------------------------------------------------------------
# Line-level primitives (unit)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_scan_literals_bare():
    line = 'print("hello")'
    lits = list(asm.scan_literals(line))
    assert len(lits) == 1
    start, prefix, body_start, end = lits[0]
    assert prefix is None
    assert start == 6           # the `"`
    assert body_start == 7
    assert end == 13            # index just past the closing `"`


@pytest.mark.unit
def test_scan_literals_c_prefixed():
    line = 'print(c"hello")'
    lits = list(asm.scan_literals(line))
    assert len(lits) == 1
    start, prefix, body_start, end = lits[0]
    assert prefix == "c"
    assert start == 6           # the `c`
    assert body_start == 8
    assert end == 14            # index just past the closing `"`


@pytest.mark.unit
def test_scan_literals_s_prefixed():
    line = 'let x = s"hi"'
    lits = list(asm.scan_literals(line))
    assert len(lits) == 1
    start, prefix, body_start, end = lits[0]
    assert prefix == "s"
    assert start == 8           # the `s`
    assert body_start == 10
    assert end == 13


@pytest.mark.unit
def test_scan_literals_stops_at_comment():
    line = 'let x = "a" # and "b" is a comment'
    lits = list(asm.scan_literals(line))
    assert len(lits) == 1
    assert lits[0][1] is None          # `"a"`


@pytest.mark.unit
def test_scan_literals_skips_char_literal():
    line = "let x = '\"' + \"body\""
    lits = list(asm.scan_literals(line))
    # Only the outer `"body"` should be seen; the `'"'` is a char literal.
    assert len(lits) == 1
    start, prefix, _, _ = lits[0]
    assert prefix is None
    assert line[start] == '"'


@pytest.mark.unit
def test_apply_c_rewrite_to_line_basic():
    line = 'print("hello")'
    # col of the `"` is 7 (1-based).
    new = asm.apply_c_rewrite_to_line(line, 7)
    assert new == 'print(c"hello")'


@pytest.mark.unit
def test_apply_c_rewrite_to_line_already_prefixed_returns_none():
    line = 'print(c"hello")'
    # col of the inner `"` is 8 (1-based).
    new = asm.apply_c_rewrite_to_line(line, 8)
    assert new is None


@pytest.mark.unit
def test_apply_c_rewrite_to_line_not_a_quote_returns_none():
    line = 'print(hello)'
    new = asm.apply_c_rewrite_to_line(line, 7)
    assert new is None


@pytest.mark.unit
def test_strip_s_prefix_from_line_basic():
    line = 'let x = s"hi"'
    new, n = asm.strip_s_prefix_from_line(line)
    assert n == 1
    assert new == 'let x = "hi"'


@pytest.mark.unit
def test_strip_s_prefix_from_line_preserves_c_prefix():
    line = 'print(c"hello")'
    new, n = asm.strip_s_prefix_from_line(line)
    assert n == 0
    assert new == line


@pytest.mark.unit
def test_strip_s_prefix_from_line_preserves_bare():
    line = 'print("hello")'
    new, n = asm.strip_s_prefix_from_line(line)
    assert n == 0
    assert new == line


@pytest.mark.unit
def test_strip_s_prefix_from_line_does_not_eat_identifier_s():
    # `callfoos("x")` — the s is part of identifier `callfoos`, not a prefix.
    line = 'callfoos("x")'
    new, n = asm.strip_s_prefix_from_line(line)
    assert n == 0
    assert new == line


@pytest.mark.unit
def test_strip_s_prefix_from_line_multiple():
    line = 'foo(s"a", s"b")'
    new, n = asm.strip_s_prefix_from_line(line)
    assert n == 2
    assert new == 'foo("a", "b")'


@pytest.mark.unit
def test_strip_s_prefix_ignores_s_in_comment():
    line = 'let x = 1 # s"not a literal"'
    new, n = asm.strip_s_prefix_from_line(line)
    assert n == 0
    assert new == line


@pytest.mark.unit
def test_csv_context_truncation():
    short = 'print("hi")'
    assert asm.csv_context_from_line(short) == 'print("hi")'
    long = "x" * 200
    out = asm.csv_context_from_line(long)
    assert len(out) == 160
    assert out.endswith("...")


# ---------------------------------------------------------------------------
# Integration: full driver over a fake ritz root.
# ---------------------------------------------------------------------------


def _make_ritz_root(tmp_path: Path, files: dict[str, str]) -> Path:
    """Materialise a fake `projects/ritz`-style tree.  Returns ritz_root."""
    ritz_root = tmp_path / "ritz"
    (ritz_root / "docs").mkdir(parents=True)
    for rel, text in files.items():
        fp = ritz_root / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(text, encoding="utf-8")
    return ritz_root


def _write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["path", "line", "col", "context", "suggested_prefix"]
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)


@pytest.mark.integration
def test_c_rewrite_applied(tmp_path: Path):
    ritz_root = _make_ritz_root(
        tmp_path,
        {"examples/a.ritz": 'fn main() -> i32\n    print("hi")\n    0\n'},
    )
    csv_path = ritz_root / "docs" / "audit.csv"
    # col of `"` in `    print("hi")` — spaces 1..4, p=5..9, (=10, "=11
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "11",
                "context": 'print("hi")',
                "suggested_prefix": "c",
            }
        ],
    )

    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        out=buf,
    )
    assert rc == 0
    assert residual == []
    text = (ritz_root / "examples" / "a.ritz").read_text()
    assert "print(c\"hi\")" in text


@pytest.mark.integration
def test_s_row_is_noop(tmp_path: Path):
    src = 'fn main() -> i32\n    let msg = "hi"\n    0\n'
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": src})
    csv_path = ritz_root / "docs" / "audit.csv"
    # col of `"` in `    let msg = "hi"` — 15 (`    let msg = "`, the `"` is 15th)
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "15",
                "context": 'let msg = "hi"',
                "suggested_prefix": "s",
            }
        ],
    )

    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        out=buf,
    )
    assert rc == 0
    assert residual == []
    assert (ritz_root / "examples" / "a.ritz").read_text() == src


@pytest.mark.integration
def test_string_row_goes_to_residual(tmp_path: Path):
    src = 'fn main() -> i32\n    let s = "hi"\n    0\n'
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": src})
    csv_path = ritz_root / "docs" / "audit.csv"
    # col of `"` in `    let s = "hi"` — 13
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "13",
                "context": 'let s = "hi"',
                "suggested_prefix": "string",
            }
        ],
    )

    residual_path = tmp_path / "residual.csv"
    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        residual_path=residual_path,
        out=buf,
    )
    assert rc == 0
    assert len(residual) == 1
    assert residual[0]["suggested_prefix"] == "string"
    assert "skipped:string" in residual[0]["reason"]
    assert (ritz_root / "examples" / "a.ritz").read_text() == src

    # Residual CSV written
    assert residual_path.exists()
    rows = list(csv.DictReader(residual_path.open()))
    assert len(rows) == 1
    assert rows[0]["reason"] == "skipped:string"


@pytest.mark.integration
def test_question_row_goes_to_residual(tmp_path: Path):
    src = 'fn main() -> i32\n    return "oops"\n'
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": src})
    csv_path = ritz_root / "docs" / "audit.csv"
    # col of `"` in `    return "oops"` — 12
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "12",
                "context": 'return "oops"',
                "suggested_prefix": "?",
            }
        ],
    )
    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        out=buf,
    )
    assert rc == 0
    assert len(residual) == 1
    assert residual[0]["suggested_prefix"] == "?"
    assert residual[0]["reason"] == "skipped:?"
    assert (ritz_root / "examples" / "a.ritz").read_text() == src


@pytest.mark.integration
def test_s_quote_deprecation_rewrite(tmp_path: Path):
    # No audit rows — deprecation is driven by the directory scan.
    src = (
        'fn main() -> i32\n'
        '    let a = s"hello"\n'
        '    let b = s"world"\n'
        '    0\n'
    )
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": src})
    csv_path = ritz_root / "docs" / "audit.csv"
    _write_csv(csv_path, [])

    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        out=buf,
    )
    assert rc == 0
    out = (ritz_root / "examples" / "a.ritz").read_text()
    assert 's"hello"' not in out
    assert 's"world"' not in out
    assert '"hello"' in out
    assert '"world"' in out


@pytest.mark.integration
def test_c_rewrite_and_s_deprecation_combined(tmp_path: Path):
    src = (
        'fn main() -> i32\n'
        '    print("hi")\n'         # bare -> c
        '    let sv = s"view"\n'    # s"..." -> "..."
        '    0\n'
    )
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": src})
    csv_path = ritz_root / "docs" / "audit.csv"
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "11",
                "context": 'print("hi")',
                "suggested_prefix": "c",
            }
        ],
    )
    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        out=buf,
    )
    assert rc == 0
    out = (ritz_root / "examples" / "a.ritz").read_text()
    assert 'print(c"hi")' in out
    assert 'let sv = "view"' in out
    assert 's"view"' not in out


@pytest.mark.integration
def test_context_mismatch_is_residual_and_guardrail_failure(tmp_path: Path):
    # File doesn't match the audit's context anymore — should NOT rewrite.
    src = 'fn main() -> i32\n    print("DIFFERENT")\n    0\n'
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": src})
    csv_path = ritz_root / "docs" / "audit.csv"
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "11",
                "context": 'print("hi")',       # stale!
                "suggested_prefix": "c",
            }
        ],
    )
    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        out=buf,
    )
    # Guardrail failure => non-zero exit.
    assert rc != 0
    assert len(residual) == 1
    assert residual[0]["reason"].startswith("mismatch")
    # File unchanged.
    assert (ritz_root / "examples" / "a.ritz").read_text() == src


@pytest.mark.integration
def test_dry_run_writes_nothing(tmp_path: Path):
    src = 'fn main() -> i32\n    print("hi")\n    0\n'
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": src})
    csv_path = ritz_root / "docs" / "audit.csv"
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "11",
                "context": 'print("hi")',
                "suggested_prefix": "c",
            }
        ],
    )
    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=True,
        out=buf,
    )
    assert rc == 0
    # File must be untouched.
    assert (ritz_root / "examples" / "a.ritz").read_text() == src
    # Diff was printed.
    diff = buf.getvalue()
    assert "a/examples/a.ritz" in diff
    assert 'print(c"hi")' in diff


@pytest.mark.integration
def test_dir_filter_excludes_out_of_scope_rows(tmp_path: Path):
    ritz_root = _make_ritz_root(
        tmp_path,
        {
            "examples/a.ritz": 'fn main() -> i32\n    print("hi")\n    0\n',
            "ritzlib/b.ritz": 'fn other() -> i32\n    print("ho")\n    0\n',
        },
    )
    csv_path = ritz_root / "docs" / "audit.csv"
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "11",
                "context": 'print("hi")',
                "suggested_prefix": "c",
            },
            {
                "path": "ritzlib/b.ritz",
                "line": "2",
                "col": "11",
                "context": 'print("ho")',
                "suggested_prefix": "c",
            },
        ],
    )
    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        out=buf,
    )
    assert rc == 0
    # examples/a.ritz got rewritten; ritzlib/b.ritz did not.
    assert 'print(c"hi")' in (ritz_root / "examples" / "a.ritz").read_text()
    assert 'print(c"ho")' not in (ritz_root / "ritzlib" / "b.ritz").read_text()
    assert 'print("ho")' in (ritz_root / "ritzlib" / "b.ritz").read_text()


@pytest.mark.integration
def test_nonexistent_dir_runs_clean(tmp_path: Path):
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": "fn main() -> i32\n    0\n"})
    csv_path = ritz_root / "docs" / "audit.csv"
    _write_csv(csv_path, [])
    buf = io.StringIO()
    # --dir that doesn't exist inside ritz_root but is a subpath.
    # We construct a path that IS under ritz_root but has no files.
    empty = ritz_root / "empty_subdir"
    empty.mkdir()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=empty,
        dry_run=True,
        out=buf,
    )
    assert rc == 0
    assert residual == []


@pytest.mark.integration
def test_multiple_rewrites_same_line(tmp_path: Path):
    # Two c-rewrites on the same line — column reordering must not clobber.
    src = 'fn main() -> i32\n    foo("a", "b")\n    0\n'
    ritz_root = _make_ritz_root(tmp_path, {"examples/a.ritz": src})
    csv_path = ritz_root / "docs" / "audit.csv"
    # cols of the two `"` chars in `    foo("a", "b")`
    #   index: 0123456789012345678
    #          `    foo("a", "b")`
    #   `"` positions (1-based): 9 and 14
    _write_csv(
        csv_path,
        [
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "9",
                "context": 'foo("a", "b")',
                "suggested_prefix": "c",
            },
            {
                "path": "examples/a.ritz",
                "line": "2",
                "col": "14",
                "context": 'foo("a", "b")',
                "suggested_prefix": "c",
            },
        ],
    )
    buf = io.StringIO()
    rc, residual = asm.apply_migration(
        csv_path=csv_path,
        dir_path=ritz_root / "examples",
        dry_run=False,
        out=buf,
    )
    assert rc == 0
    out = (ritz_root / "examples" / "a.ritz").read_text()
    assert 'foo(c"a", c"b")' in out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q", "-x"]))
