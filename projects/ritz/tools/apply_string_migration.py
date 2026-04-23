#!/usr/bin/env python3
"""apply_string_migration.py -- mechanical rewriter for the c/s string
migration (AGAST #92).

Consumes the audit CSV produced by `audit_string_literals.py` and applies
the following rewrites to `.ritz` files under a target directory:

  * suggested_prefix=c      insert a `c` prefix before the `"` at
                             (line, col), producing `c"..."`.
  * suggested_prefix=s      NO-OP.  Under terminal state (A) of the
                             migration, bare `"..."` becomes `StrView`
                             once the compilers flip -- so `s` rows stay
                             bare on purpose.
  * suggested_prefix=string  skip and emit to the residual CSV so #97 can
                             handle by hand (likely stdlib constructor).
  * suggested_prefix=?       skip and emit to the residual CSV so #97 can
                             handle by hand.

In addition to the audit-driven pass the tool scans every `.ritz` file
under `--dir` for literal `s"..."` occurrences and rewrites them to bare
`"..."` -- this is the s-prefix deprecation.

Guardrails
----------

  * The line at (line, col) is re-derived to match the CSV `context`
    column.  Any mismatch is skipped and recorded in the residual CSV;
    for c-rows a mismatch flips the exit code to non-zero.
  * Per-file writes are atomic (tmp + os.replace).
  * `--dry-run` prints unified diffs and writes nothing.

CLI
---

    python3 apply_string_migration.py                                   \\
        --csv projects/ritz/docs/string_literal_audit.csv               \\
        --dir projects/ritz/examples                                    \\
        [--dry-run] [--residual PATH]

Exit code
---------

  0 on clean runs, 1 if any guardrail tripped on a c-row (including
  context mismatch, missing file, or `"` missing at the expected column).
"""
from __future__ import annotations

import argparse
import csv
import difflib
import io
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, Optional


# ---------------------------------------------------------------------------
# Line scanner -- the shared primitive for both the c-rewrite column
# verification and the s"..." deprecation pass.  Mirrors the skip rules
# from `audit_string_literals.py` so column numbers line up.
# ---------------------------------------------------------------------------


def scan_literals(line: str) -> Iterator[tuple[int, Optional[str], int, int]]:
    """Yield ``(start, prefix, body_start, end)`` for each string literal
    in *line*.

    * ``start``       -- 0-based column of the prefix char (``c`` / ``s``)
                         when the literal is prefixed, else of the opening
                         ``"``.
    * ``prefix``      -- ``'c'``, ``'s'``, or ``None``.
    * ``body_start``  -- 0-based column of the first char after the
                         opening ``"``.
    * ``end``         -- 0-based column immediately after the closing
                         ``"``.

    Scanning stops at a ``#`` comment and skips char literals (``'x'``).
    """
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]

        # Comments end the scan.
        if ch == "#":
            return

        # Char literals (`'x'`, with backslash escapes) -- skip entirely so
        # that a `"` inside a char lit isn't picked up as a string.
        if ch == "'":
            j = i + 1
            while j < n:
                if line[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if line[j] == "'":
                    j += 1
                    break
                j += 1
            i = j
            continue

        if ch == '"':
            prefix: Optional[str] = None
            start = i
            if i >= 1 and line[i - 1] in ("c", "s"):
                prev2 = line[i - 2] if i >= 2 else ""
                # A prefix is only a prefix if the char before it isn't an
                # identifier continuation -- otherwise we'd eat the trailing
                # letter of some unrelated identifier.
                if not (prev2.isalnum() or prev2 == "_"):
                    prefix = line[i - 1]
                    start = i - 1
            body_start = i + 1
            j = i + 1
            while j < n:
                if line[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if line[j] == '"':
                    j += 1
                    break
                j += 1
            yield start, prefix, body_start, j
            i = j
            continue

        i += 1


# ---------------------------------------------------------------------------
# Single-line mutation primitives.
# ---------------------------------------------------------------------------


def apply_c_rewrite_to_line(line: str, col_1based: int) -> Optional[str]:
    """Insert ``c`` immediately before the ``"`` at 1-based column
    *col_1based* in *line*, returning the new line.

    Returns ``None`` if verification fails (no ``"`` at that column, or
    the literal is already c/s-prefixed).
    """
    idx = col_1based - 1
    if idx < 0 or idx >= len(line) or line[idx] != '"':
        return None
    # Already prefixed?  Walk the scan_literals rule to avoid adding `cc"`.
    if idx >= 1 and line[idx - 1] in ("c", "s"):
        prev2 = line[idx - 2] if idx >= 2 else ""
        if not (prev2.isalnum() or prev2 == "_"):
            return None
    return line[:idx] + "c" + line[idx:]


def strip_s_prefix_from_line(line: str) -> tuple[str, int]:
    """Remove the ``s`` prefix from every ``s"..."`` literal on *line*.

    Returns ``(new_line, n_stripped)``.  Comments and char literals are
    skipped via the shared scanner, so ``s`` characters that are part of
    an identifier (e.g. ``callfoos("x")``) are preserved.
    """
    drops: list[int] = []
    for start, prefix, _body, _end in scan_literals(line):
        if prefix == "s":
            drops.append(start)
    if not drops:
        return line, 0
    out = line
    for idx in sorted(drops, reverse=True):
        out = out[:idx] + out[idx + 1:]
    return out, len(drops)


# ---------------------------------------------------------------------------
# Context verification -- re-derive the CSV `context` field from a source
# line.  This must mirror the truncation rule in audit_string_literals.py
# exactly (>160 chars -> first 157 + "...").
# ---------------------------------------------------------------------------


def csv_context_from_line(line: str) -> str:
    ctx = line.strip()
    if len(ctx) > 160:
        ctx = ctx[:157] + "..."
    return ctx


# ---------------------------------------------------------------------------
# Residual reason codes.
# ---------------------------------------------------------------------------


R_STRING = "skipped:string"
R_UNKNOWN = "skipped:?"
R_MISMATCH = "mismatch:context"
R_NOT_QUOTE = "mismatch:no-quote-at-col"
R_ALREADY = "skipped:already-prefixed"
R_MISSING_FILE = "mismatch:file-not-found"
R_MISSING_LINE = "mismatch:line-out-of-range"


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def load_csv_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def ritz_root_from_csv(csv_path: Path) -> Path:
    # audit CSV lives at  `<ritz_root>/docs/<name>.csv`, so the root is two
    # levels up.
    return csv_path.resolve().parent.parent


def row_path_under(row_path: str, rel_dir: Path) -> bool:
    rp = Path(row_path).as_posix()
    rd = rel_dir.as_posix()
    if rd in (".", ""):
        return True
    return rp == rd or rp.startswith(rd + "/")


def _split_newline(line_with_nl: str) -> tuple[str, str]:
    """Return (line_text_without_newline, newline_suffix)."""
    if line_with_nl.endswith("\r\n"):
        return line_with_nl[:-2], "\r\n"
    if line_with_nl.endswith("\n"):
        return line_with_nl[:-1], "\n"
    return line_with_nl, ""


def _emit_diff(out: io.TextIOBase, label: str, old: str, new: str) -> None:
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
    )
    out.writelines(diff)


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp.migrate")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _write_residual(path: Path, rows: list[dict]) -> None:
    fieldnames = ["path", "line", "col", "context", "suggested_prefix", "reason"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


# ---------------------------------------------------------------------------
# Core driver.
# ---------------------------------------------------------------------------


def apply_migration(
    csv_path: Path,
    dir_path: Path,
    dry_run: bool = False,
    residual_path: Optional[Path] = None,
    out: io.TextIOBase = sys.stdout,
) -> tuple[int, list[dict]]:
    """Run the migration.  Returns ``(exit_code, residual_rows)``.

    *out* is the sink for dry-run diffs and the summary.  Residual rows
    are always returned in-memory; they are also written to *residual_path*
    (defaulting to ``<csv_path>.residual.csv``) when non-empty.
    """
    csv_path = Path(csv_path).resolve()
    dir_path = Path(dir_path).resolve()
    ritz_root = ritz_root_from_csv(csv_path)

    try:
        rel_dir = dir_path.relative_to(ritz_root)
    except ValueError:
        print(
            f"error: --dir {dir_path} is not inside ritz root {ritz_root}",
            file=sys.stderr,
        )
        return 2, []

    rows = load_csv_rows(csv_path)
    in_scope = [r for r in rows if row_path_under(r["path"], rel_dir)]

    per_file: dict[str, list[dict]] = defaultdict(list)
    for r in in_scope:
        per_file[r["path"]].append(r)

    residual: list[dict] = []
    guardrail_failure = False
    counters: Counter[str] = Counter()

    # ----- Pass 1: audit-driven rewrites (c / s / string / ?) ---------------

    for rel_path in sorted(per_file):
        rows_for_file = per_file[rel_path]
        abs_path = ritz_root / rel_path
        if not abs_path.exists():
            for r in rows_for_file:
                residual.append({**r, "reason": R_MISSING_FILE})
                if r.get("suggested_prefix") == "c":
                    guardrail_failure = True
                counters["missing-file"] += 1
            continue

        original = abs_path.read_text(encoding="utf-8")
        lines = original.splitlines(keepends=True)
        # Keep a pristine copy for context verification so that prior
        # rewrites on the same line can't invalidate later context checks.
        original_lines = list(lines)
        changed = False

        # Sort rows (line, col) descending so multiple edits on the same
        # line don't shift the column offsets of their neighbours.
        rows_sorted = sorted(
            rows_for_file,
            key=lambda r: (int(r["line"]), int(r["col"])),
            reverse=True,
        )

        for r in rows_sorted:
            prefix = r.get("suggested_prefix", "?")
            line_no = int(r["line"])
            col = int(r["col"])
            context = r.get("context", "")

            if line_no < 1 or line_no > len(lines):
                residual.append({**r, "reason": R_MISSING_LINE})
                if prefix == "c":
                    guardrail_failure = True
                counters["line-oor"] += 1
                continue

            line_with_nl = lines[line_no - 1]
            line_text, nl = _split_newline(line_with_nl)
            orig_text, _ = _split_newline(original_lines[line_no - 1])

            if csv_context_from_line(orig_text) != context:
                residual.append({**r, "reason": R_MISMATCH})
                if prefix == "c":
                    guardrail_failure = True
                counters["mismatch"] += 1
                continue

            if prefix == "s":
                counters["s-noop"] += 1
                continue
            if prefix == "string":
                residual.append({**r, "reason": R_STRING})
                counters["string"] += 1
                continue
            if prefix == "?":
                residual.append({**r, "reason": R_UNKNOWN})
                counters["unknown"] += 1
                continue
            if prefix != "c":
                residual.append({**r, "reason": f"skipped:unexpected:{prefix}"})
                counters[f"weird:{prefix}"] += 1
                continue

            new_line = apply_c_rewrite_to_line(line_text, col)
            if new_line is None:
                # Distinguish "already prefixed" (benign) from "no quote"
                # (guardrail failure).
                if 1 <= col <= len(line_text) and line_text[col - 1] == '"':
                    residual.append({**r, "reason": R_ALREADY})
                    counters["already"] += 1
                else:
                    residual.append({**r, "reason": R_NOT_QUOTE})
                    guardrail_failure = True
                    counters["not-quote"] += 1
                continue

            lines[line_no - 1] = new_line + nl
            changed = True
            counters["c-rewrite"] += 1

        if changed:
            new_text = "".join(lines)
            if dry_run:
                _emit_diff(out, rel_path, original, new_text)
            else:
                _atomic_write(abs_path, new_text)

    # ----- Pass 2: s"..." deprecation scan across all .ritz under --dir ----

    if dir_path.is_dir():
        for fpath in sorted(dir_path.rglob("*.ritz")):
            if fpath.suffixes[-2:] == [".ritz", ".sig"]:
                continue
            # Read AFTER pass 1 has written so c-rewrites are preserved.
            original = fpath.read_text(encoding="utf-8")
            lines = original.splitlines(keepends=True)
            n_stripped = 0
            for i, line_with_nl in enumerate(lines):
                line_text, nl = _split_newline(line_with_nl)
                new_text, n = strip_s_prefix_from_line(line_text)
                if n:
                    lines[i] = new_text + nl
                    n_stripped += n
            if n_stripped:
                counters["s-deprecated"] += n_stripped
                new_file = "".join(lines)
                try:
                    rel_label = str(fpath.relative_to(ritz_root))
                except ValueError:
                    rel_label = str(fpath)
                if dry_run:
                    _emit_diff(out, rel_label, original, new_file)
                else:
                    _atomic_write(fpath, new_file)

    # ----- Residual CSV ----------------------------------------------------

    written_residual: Optional[Path] = None
    if residual and not dry_run:
        if residual_path is None:
            residual_path = csv_path.with_suffix(".residual.csv")
        _write_residual(residual_path, residual)
        written_residual = residual_path

    # ----- Summary ---------------------------------------------------------

    print("", file=out)
    print("=== migration summary ===", file=out)
    if not counters:
        print("  (no rows in scope)", file=out)
    for k, v in counters.most_common():
        print(f"  {v:6d}  {k}", file=out)
    print(f"  residual rows: {len(residual)}", file=out)
    if written_residual is not None:
        print(f"  residual CSV: {written_residual}", file=out)
    if dry_run:
        print("  (dry-run: no files written)", file=out)

    return (1 if guardrail_failure else 0), residual


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply the CS3 string-literal migration to a directory.",
    )
    parser.add_argument("--csv", required=True, type=Path, help="Audit CSV path")
    parser.add_argument("--dir", required=True, type=Path, help="Target directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned diffs to stdout without touching files.",
    )
    parser.add_argument(
        "--residual",
        type=Path,
        default=None,
        help=(
            "Path for the residual CSV (default: <csv>.residual.csv). "
            "Only written when there are residual rows."
        ),
    )
    args = parser.parse_args(argv)
    exit_code, _ = apply_migration(
        csv_path=args.csv,
        dir_path=args.dir,
        dry_run=args.dry_run,
        residual_path=args.residual,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
