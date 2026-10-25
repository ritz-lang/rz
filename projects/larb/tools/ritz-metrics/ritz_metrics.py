#!/usr/bin/env python3
"""ritz-metrics — static structure metrics for Ritz (.ritz) and Python sources.

LARB review v4 (AGAST #1800) measures, it does not eyeball. This script reads
source files only (no compiler, no build) and reports:

  * per-function length (lines, from `fn` header to the last indented line)
  * per-function cyclomatic complexity (1 + decision points), counting
    if / elif / while / for / match-arm `=>` lines / `and` / `or` / `?`-try
  * per-function max nesting depth (indent levels below the fn header)
  * duplication: identical normalised N-line windows within and across files
  * string-handling smells (C-in-Ritz-clothing indicators), per file and fn

Ritz is indentation-scoped (like Python), so a function body is every line
indented deeper than its `fn` header up to the next line at or above that
indent.  Comment-only and blank lines are excluded from SLOC and complexity.

Usage:
    ritz_metrics.py PATH... [--top N] [--json OUT] [--dup-window 6]
                            [--min-dup-occurrences 2] [--lang ritz|py]

Output is Markdown on stdout (ranked tables), optionally JSON for tooling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Lexical helpers
# --------------------------------------------------------------------------

_STR_RE = re.compile(r'(?:[cs]?"(?:[^"\\]|\\.)*")|(?:\'(?:[^\'\\]|\\.)*\')')


def strip_strings_and_comment(line: str) -> str:
    """Remove string/char literals and a trailing `#` comment."""
    no_str = _STR_RE.sub('""', line)
    hash_at = no_str.find("#")
    return no_str[:hash_at] if hash_at >= 0 else no_str


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def is_code(line: str) -> bool:
    s = line.strip()
    return bool(s) and not s.startswith("#")


# --------------------------------------------------------------------------
# Language profiles
# --------------------------------------------------------------------------

RITZ_FN_RE = re.compile(
    r"^(\s*)(?:pub\s+)?(?:extern\s+)?(?:async\s+)?fn\s+([A-Za-z_][\w$]*)"
)
PY_FN_RE = re.compile(r"^(\s*)(?:async\s+)?def\s+([A-Za-z_]\w*)")

# Decision points.  Each regex is applied to the comment/string-stripped line;
# every match adds one to the cyclomatic number.
RITZ_DECISIONS = [
    re.compile(r"^\s*(?:if|elif|while|for)\b"),
    re.compile(r"\belse\s+if\b"),
    re.compile(r"=>"),  # match arm
    re.compile(r"\band\b"),
    re.compile(r"\bor\b"),
    re.compile(r"\?\s*$|\?\)|\?\s*[,.]"),  # `expr?` early-return try operator
]
PY_DECISIONS = [
    re.compile(r"^\s*(?:if|elif|while|for|except|case)\b"),
    re.compile(r"\bif\b.*\belse\b"),  # conditional expression
    re.compile(r"\band\b"),
    re.compile(r"\bor\b"),
    re.compile(r"\bfor\b.*\bin\b.*[\]\)]"),  # comprehension (approx.)
]

# String / C-idiom smells for Ritz.  Name -> regex over stripped code lines.
# These are indicators for review, not verdicts; the review doc cites lines.
RITZ_SMELLS = {
    # (*u8, len) parameter pairs: `name: *u8, name_len: i32`
    "ptr_len_param_pair": re.compile(
        r"\w+\s*:\s*\*u8\s*,\s*\w*len\w*\s*:\s*i(?:32|64)"
    ),
    # fixed-size stack byte buffers used as strings
    "fixed_u8_buffer": re.compile(r":\s*\[\d+\]u8\b"),
    # libc-shaped helpers
    "strlen_call": re.compile(r"\b(?:strlen|cstr_len|c_strlen)\s*\("),
    "memcpy_call": re.compile(r"\b(?:memcpy|memmove|mem_copy)\s*\("),
    "memcmp_or_streq_call": re.compile(
        r"\b(?:memcmp|strcmp|strncmp|streq|str_eq|bytes_eq|name_eq)\s*\("
    ),
    # byte-by-byte copy/compare loops:  buf[i] = src[i]   /  a[i] != b[i]
    "manual_byte_copy": re.compile(
        r"\w+\[\s*\w+(?:\s*\+\s*\w+)?\s*\]\s*=\s*\*?\(?\w+(?:\.\w+)*\s*\[\s*\w+\s*\]"
    ),
    "manual_byte_compare": re.compile(
        r"\w+\[\s*\w+\s*\]\s*!=\s*\w+(?:\.\w+)*\[\s*\w+\s*\]"
    ),
    # char-code literals compared one at a time:  name[0] == 118 and name[1] == 101 ...
    "char_code_compare": re.compile(r"\[\s*\d+\s*\]\s*==\s*\d{2,3}\b"),
    # C-string literals
    "cstr_literal": re.compile(r'\bc"'),
    # raw malloc + cast instead of typed allocation
    "malloc_cast": re.compile(r"\bmalloc\s*\([^)]*\)\s*as\s*\*"),
    # magic-number struct sizes in allocation
    "malloc_magic_size": re.compile(r"\bmalloc\s*\(\s*\d+\s*\)"),
    # bool modelled as i32 flags
    "i32_as_bool": re.compile(r"\bas\s+i32\b.*==|:\s*i32\s*=\s*[01]\b"),
}

PY_SMELLS: dict[str, re.Pattern[str]] = {
    "bare_except": re.compile(r"^\s*except\s*:"),
    "subprocess_shell_true": re.compile(r"shell\s*=\s*True"),
    "global_stmt": re.compile(r"^\s*global\s+"),
}


@dataclass
class FnMetric:
    file: str
    name: str
    line: int
    length: int  # physical lines incl. header, excluding trailing blanks
    sloc: int  # code lines (non-blank, non-comment)
    complexity: int
    max_depth: int
    smells: dict[str, int] = field(default_factory=dict)


@dataclass
class FileMetric:
    file: str
    lines: int
    sloc: int
    functions: int
    smells: dict[str, int] = field(default_factory=dict)


# --------------------------------------------------------------------------
# Function extraction
# --------------------------------------------------------------------------


def extract_functions(path: Path, lines: list[str], lang: str) -> list[FnMetric]:
    fn_re = RITZ_FN_RE if lang == "ritz" else PY_FN_RE
    decisions = RITZ_DECISIONS if lang == "ritz" else PY_DECISIONS
    smells = RITZ_SMELLS if lang == "ritz" else PY_SMELLS
    out: list[FnMetric] = []
    n = len(lines)
    i = 0
    while i < n:
        m = fn_re.match(lines[i])
        if not m:
            i += 1
            continue
        base = indent_of(lines[i])
        name = m.group(2)
        start = i
        j = i + 1
        last_body = i
        # Python signatures may span lines; skip continuation until ':' ends a line.
        if lang == "py":
            while j < n and not strip_strings_and_comment(
                lines[j - 1]
            ).rstrip().endswith(":"):
                j += 1
            last_body = j - 1
        while j < n:
            ln = lines[j]
            if is_code(ln) and indent_of(ln) <= base:
                break
            if is_code(ln):
                last_body = j
            j += 1
        body = lines[start : last_body + 1]
        cc = 1
        depth = 0
        sloc = 0
        sm: dict[str, int] = defaultdict(int)
        # Indent unit: smallest positive indent delta inside the body.
        body_indents = sorted(
            {indent_of(b) for b in body[1:] if is_code(b) and indent_of(b) > base}
        )
        unit = (body_indents[0] - base) if body_indents else 4
        unit = unit or 4
        for b in body[1:]:
            if not is_code(b):
                continue
            sloc += 1
            code = strip_strings_and_comment(b)
            for d in decisions:
                cc += len(d.findall(code))
            depth = max(depth, (indent_of(b) - base) // unit)
            for k, rx in smells.items():
                if rx.search(b if k == "cstr_literal" else code):
                    sm[k] += 1
        out.append(
            FnMetric(
                file=str(path),
                name=name,
                line=start + 1,
                length=last_body - start + 1,
                sloc=sloc + 1,
                complexity=cc,
                max_depth=depth,
                smells=dict(sm),
            )
        )
        # Nested functions (Python closures, Ritz impl blocks) are scanned too:
        # continue from the line after the header, not after the body.
        i = start + 1
    return out


# --------------------------------------------------------------------------
# Duplication
# --------------------------------------------------------------------------

_NUM_RE = re.compile(r"\b\d+\b")
_WS_RE = re.compile(r"\s+")


def normalise(line: str) -> str:
    code = strip_strings_and_comment(line).strip()
    code = _NUM_RE.sub("N", code)
    return _WS_RE.sub(" ", code)


def find_duplicates(files: dict[str, list[str]], window: int) -> list[dict]:
    """Return clusters of identical normalised `window`-line code windows.

    Windows made mostly of trivial lines (imports, `0`, `return`, single
    tokens) are ignored so the report surfaces real copy-paste.
    """
    index: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for fname, lines in files.items():
        code = [(k, normalise(ln)) for k, ln in enumerate(lines) if is_code(ln)]
        for s in range(0, len(code) - window + 1):
            chunk = [c for _, c in code[s : s + window]]
            meaningful = sum(
                1 for c in chunk if len(c) > 12 and not c.startswith("import ")
            )
            if meaningful < window - 1:
                continue
            h = hashlib.sha1("\n".join(chunk).encode()).hexdigest()
            index[h].append((fname, code[s][0] + 1))
    clusters = []
    for h, locs in index.items():
        # Collapse overlapping windows from the same run into its first line.
        uniq: list[tuple[str, int]] = []
        for f, ln in sorted(locs):
            if uniq and uniq[-1][0] == f and ln - uniq[-1][1] < window:
                continue
            uniq.append((f, ln))
        if len(uniq) >= 2:
            clusters.append({"hash": h, "count": len(uniq), "locations": uniq})
    # Merge clusters that are shifted copies of the same longer duplicated run:
    # keep only one cluster per distinct location set signature (first lines).
    seen: set[tuple] = set()
    merged = []
    for c in sorted(clusters, key=lambda c: (-c["count"], c["locations"])):
        sig = tuple((f, ln // (window * 2)) for f, ln in c["locations"])
        if sig in seen:
            continue
        seen.add(sig)
        merged.append(c)
    return merged


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def collect(paths: list[str], lang: str) -> list[Path]:
    ext = ".ritz" if lang == "ritz" else ".py"
    out: list[Path] = []
    for p in paths:
        pp = Path(p)
        if pp.is_file():
            out.append(pp)
        else:
            out.extend(
                sorted(q for q in pp.rglob(f"*{ext}") if "/archive/" not in str(q))
            )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--lang", choices=["ritz", "py"], default="ritz")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--dup-window", type=int, default=6)
    ap.add_argument("--min-dup-occurrences", type=int, default=2)
    args = ap.parse_args(argv)

    files = collect(args.paths, args.lang)
    if not files:
        print("no source files found", file=sys.stderr)
        return 1

    texts: dict[str, list[str]] = {}
    fns: list[FnMetric] = []
    fmetrics: list[FileMetric] = []
    smells = RITZ_SMELLS if args.lang == "ritz" else PY_SMELLS
    for f in files:
        lines = f.read_text(errors="replace").splitlines()
        texts[str(f)] = lines
        ffns = extract_functions(f, lines, args.lang)
        fns.extend(ffns)
        fs: dict[str, int] = defaultdict(int)
        for ln in lines:
            if not is_code(ln):
                continue
            code = strip_strings_and_comment(ln)
            for k, rx in smells.items():
                if rx.search(ln if k == "cstr_literal" else code):
                    fs[k] += 1
        fmetrics.append(
            FileMetric(
                str(f),
                len(lines),
                sum(1 for ln in lines if is_code(ln)),
                len(ffns),
                dict(fs),
            )
        )

    dups = [
        d
        for d in find_duplicates(texts, args.dup_window)
        if d["count"] >= args.min_dup_occurrences
    ]
    dup_lines_by_file: dict[str, int] = defaultdict(int)
    for d in dups:
        for f, _ in d["locations"]:
            dup_lines_by_file[f] += args.dup_window

    top = args.top
    total_sloc = sum(m.sloc for m in fmetrics)
    print(
        f"# ritz-metrics: {len(files)} files, {total_sloc} SLOC, {len(fns)} functions\n"
    )

    def table(title: str, rows: list, cols: list[tuple[str, str]]) -> None:
        print(f"## {title}\n")
        print("| " + " | ".join(h for h, _ in cols) + " |")
        print("|" + "---|" * len(cols))
        for r in rows:
            print(
                "| "
                + " | ".join(
                    str(fn(r)) if callable(fn) else str(getattr(r, fn))
                    for _, fn in cols
                )
                + " |"
            )
        print()

    loc = lambda r: f"`{r.file}:{r.line}`"  # noqa: E731
    table(
        f"Longest functions (top {top})",
        sorted(fns, key=lambda r: -r.sloc)[:top],
        [
            ("fn", "name"),
            ("where", loc),
            ("SLOC", "sloc"),
            ("CC", "complexity"),
            ("depth", "max_depth"),
        ],
    )
    table(
        f"Highest cyclomatic complexity (top {top})",
        sorted(fns, key=lambda r: -r.complexity)[:top],
        [
            ("fn", "name"),
            ("where", loc),
            ("CC", "complexity"),
            ("SLOC", "sloc"),
            ("depth", "max_depth"),
        ],
    )
    table(
        f"Deepest nesting (top {top})",
        sorted(fns, key=lambda r: (-r.max_depth, -r.sloc))[:top],
        [("fn", "name"), ("where", loc), ("depth", "max_depth"), ("SLOC", "sloc")],
    )

    # Distribution summary
    def pct(pred) -> str:
        k = sum(1 for f in fns if pred(f))
        return f"{k} ({100 * k / max(1, len(fns)):.1f}%)"

    print("## Distribution\n")
    print(
        f"- functions > 100 SLOC: {pct(lambda f: f.sloc > 100)}; > 300 SLOC: {pct(lambda f: f.sloc > 300)}"
    )
    print(
        f"- CC > 20: {pct(lambda f: f.complexity > 20)}; CC > 50: {pct(lambda f: f.complexity > 50)}"
    )
    print(f"- nesting depth >= 6: {pct(lambda f: f.max_depth >= 6)}\n")

    table(
        "Files by size",
        sorted(fmetrics, key=lambda r: -r.sloc)[:top],
        [
            ("file", lambda r: f"`{r.file}`"),
            ("lines", "lines"),
            ("SLOC", "sloc"),
            ("fns", "functions"),
            ("dup-window lines", lambda r: dup_lines_by_file.get(r.file, 0)),
        ],
    )

    smell_keys = list(smells)
    print("## String / C-idiom smell counts per file\n")
    print("| file | " + " | ".join(smell_keys) + " | total |")
    print("|" + "---|" * (len(smell_keys) + 2))
    for m in sorted(fmetrics, key=lambda r: -sum(r.smells.values()))[:top]:
        tot = sum(m.smells.values())
        if not tot:
            continue
        print(
            f"| `{m.file}` | "
            + " | ".join(str(m.smells.get(k, 0)) for k in smell_keys)
            + f" | {tot} |"
        )
    totals = {k: sum(m.smells.get(k, 0) for m in fmetrics) for k in smell_keys}
    print(
        "| **total** | "
        + " | ".join(str(totals[k]) for k in smell_keys)
        + f" | {sum(totals.values())} |\n"
    )

    print(
        f"## Duplicated {args.dup_window}-line windows (top {top} clusters by occurrences)\n"
    )
    for d in dups[:top]:
        locs = ", ".join(f"`{f}:{ln}`" for f, ln in d["locations"][:8])
        more = f" (+{len(d['locations']) - 8} more)" if len(d["locations"]) > 8 else ""
        f0, l0 = d["locations"][0]
        snippet = texts[f0][l0 - 1].strip()[:80]
        print(f"- **{d['count']}×** `{snippet}` — {locs}{more}")
    print(f"\nTotal duplicate clusters: {len(dups)}")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(
                {
                    "files": [asdict(m) for m in fmetrics],
                    "functions": [asdict(f) for f in fns],
                    "duplicates": dups,
                },
                indent=1,
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
