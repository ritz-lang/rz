#!/usr/bin/env python3
"""Down-only ratchet on how much ritz1's emitter still speaks C text (AGAST #4696).

Milestone M1.5 (#4695): ritz1 is idiomatic Ritz.  Its emitter wrote IR as
`emit_str(s, c"...")` fragments of NUL-terminated text.  A file ported to the
pattern in ritz1/ARCHITECTURE.md "Emitter style" writes whole instructions with
`format_into(s, "...")` and holds text as a StrView.  This counts, per
hand-written file under ritz1/src, what is left of the old form:

    c_literals   `c"..."` literals            (S-TEXT-1: C interop only)
    emit_str     `emit_str(` calls            (the legacy shim)
    u8_params    `*u8` in fn signatures       (S-PTR-1/2: StrView, not a pointer)

Each count may go down and may not go up: porting a file lowers its row (lower
the baseline when you do).  A file with no baseline row is pinned at 0.  A
ported file pins 0 in every column, and a count above its pin fails
`make tools-ratchets`.

    ritz1_text_ratchet.py            # compare this tree to the baseline
    ritz1_text_ratchet.py --update   # rewrite the baseline to this tree's counts

`--update` only lowers (the first one writes the file): it refuses to write a
count above its pin.  Generated
modules (lexer_scan_gen, parser_gen, tokens_gen) are not counted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from standard_report import count_c_literals  # noqa: E402  (needs the path insert)

DEFAULT_SRC = _TOOLS.parent / "ritz1" / "src"
DEFAULT_BASELINE = _TOOLS / "ritz1_text_baseline.json"
GENERATED_MODULES = ("lexer_scan_gen", "parser_gen", "tokens_gen")
COLUMNS = ("c_literals", "emit_str", "u8_params")

_FN_LINE = re.compile(r"^\s*(?:pub\s+)?fn\s")
_EMIT_STR = re.compile(r"\bemit_str\(")


def _code(line: str) -> str:
    """`line` as code: string contents blanked, a trailing `#` comment cut."""
    out = []
    i, end = 0, len(line)
    while i < end:
        ch = line[i]
        if ch == "#":
            break
        if ch == "'":  # a char literal such as '#' or '\\n'
            j = i + 2 if i + 1 < end and line[i + 1] == "\\" else i + 1
            if j + 1 < end and line[j + 1] == "'":
                i = j + 2
                continue
        if ch == '"':
            i += 1
            while i < end and line[i] != '"':
                i += 2 if line[i] == "\\" else 1
            out.append('""')
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def count_file(text: str) -> dict[str, int]:
    out = dict.fromkeys(COLUMNS, 0)
    for raw in text.split("\n"):
        out["c_literals"] += count_c_literals(raw)
        line = _code(raw)
        out["emit_str"] += len(_EMIT_STR.findall(line))
        if _FN_LINE.match(line):
            out["u8_params"] += line.count("*u8")
    return out


def measure(src: Path) -> dict[str, dict[str, int]]:
    rows: dict[str, dict[str, int]] = {}
    for f in sorted(src.glob("*.ritz")):
        if f.stem in GENERATED_MODULES:
            continue
        rows[f.stem] = count_file(f.read_text(errors="replace"))
    return rows


def breaches(measured: dict[str, dict[str, int]], baseline: dict[str, dict[str, int]]) -> list[str]:
    """Every count above its pin, as `<file>.<column>: <n> > pin <p>`."""
    out = []
    for name, row in measured.items():
        pins = baseline.get(name, {})
        for col in COLUMNS:
            if row[col] > pins.get(col, 0):
                out.append(f"{name}.{col}: {row[col]} > pin {pins.get(col, 0)}")
    return out


def lowered(measured: dict[str, dict[str, int]], baseline: dict[str, dict[str, int]]) -> dict[str, dict[str, int]]:
    """The baseline with this tree's counts, rows that are all zero dropped."""
    out = {}
    for name, row in measured.items():
        if any(row.values()):
            out[name] = dict(row)
    return out


def load(path: Path) -> dict[str, dict[str, int]]:
    return json.loads(path.read_text())["files"] if path.exists() else {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    ap.add_argument("--update", action="store_true", help="lower the baseline to this tree")
    args = ap.parse_args(argv)
    measured = measure(args.src)
    baseline = load(args.baseline)
    # The first --update has no baseline to be held to: it writes the tree's counts.
    bad = [] if args.update and not args.baseline.exists() else breaches(measured, baseline)
    if bad:
        print("ritz1 text ratchet: a count went up (it may only go down):")
        for line in bad:
            print(f"  {line}")
        return 1
    if args.update:
        doc = {
            "comment": "AGAST #4696: per-file counts of the old emitter text form; down-only. "
            "Regenerate with `ritz1_text_ratchet.py --update` after porting a file.",
            "files": lowered(measured, baseline),
        }
        args.baseline.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
        print(f"wrote {args.baseline}")
        return 0
    totals = {c: sum(r[c] for r in measured.values()) for c in COLUMNS}
    print(f"ritz1 text ratchet ok: {totals}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
