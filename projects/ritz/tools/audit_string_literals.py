#!/usr/bin/env python3
"""Audit bare `"..."` string literals across the Ritz codebase.

Part of the CS2 string-literal migration (AGAST #90). Walks every `.ritz`
file rooted at `projects/ritz` (discovered relative to this script) and
finds every bare `"..."` literal -- i.e. a double-quoted string that is
NOT immediately preceded by a `c` or `s` prefix character, and is NOT
inside a comment or character literal.

For each literal we emit one CSV row:

    path,line,col,context,suggested_prefix

Where `suggested_prefix` is one of `c`, `s`, `string`, or `?` and is
chosen by a cheap heuristic that looks at:

  * LHS type annotations (`let x: *u8  = "..."`  => c;
                          `let x: StrView = "..."` => s;
                          `let x: String = "..."` => string)
  * Function call sites with well-known stdlib signatures
    (`prints_cstr("..")` => c,  `prints("..")` => s,
     `panic("..")` / `eprintln_cstr("..")` / `eprints_cstr("..")` => c,
     `assert ... , "..."` => c, etc.)
  * Fallback: `c` (matches the dominant current-code shape -- almost all
    bare strings today are flowing into `*u8` arguments).

A per-project / per-directory / per-prefix summary is written to stderr.

Usage:

    python3 projects/ritz/tools/audit_string_literals.py > audit.csv

Exits 0 on success.
"""

from __future__ import annotations

import csv
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator, Optional

# --------------------------------------------------------------------------
# Project root discovery
# --------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent              # projects/ritz/tools
RITZ_ROOT = SCRIPT_DIR.parent                             # projects/ritz
REPO_ROOT = RITZ_ROOT.parent.parent                       # workspace root


# --------------------------------------------------------------------------
# Well-known stdlib signatures -- each function parameter position maps to
# the preferred prefix for a bare string passed at that position.  `c` means
# the parameter expects `*u8`, `s` means it expects `StrView` / `Span<u8>`,
# and `string` means it expects owned `String`.
# --------------------------------------------------------------------------

CALL_SIG: dict[str, dict[int, str]] = {
    # io.ritz -- C-string sinks expect *u8
    "prints_cstr":   {0: "c"},
    "println_cstr":  {0: "c"},
    "eprints_cstr":  {0: "c"},
    "eprintln_cstr": {0: "c"},
    "print_cstr":    {0: "c"},

    # StrView sinks
    "prints":        {0: "s"},
    "println":       {0: "s"},
    "eprints":       {0: "s"},
    "eprintln":      {0: "s"},

    # args_init(parser, name, desc) -- both strings are shown to the user
    # via *u8 usage observed in tier3 coreutils
    "args_init":       {1: "c", 2: "c"},
    "args_flag":       {2: "c", 3: "c"},
    "args_option":     {2: "c", 3: "c"},
    "args_positional": {1: "c", 2: "c"},

    # Panics / asserts -- today panic takes *u8
    "panic":      {0: "c"},
    "panic_cstr": {0: "c"},
    "assert_cstr": {1: "c"},

    # System calls that take *u8 paths
    "sys_open":    {0: "c"},
    "sys_openat":  {1: "c"},
    "sys_execve":  {0: "c"},
    "sys_unlink":  {0: "c"},
    "sys_stat":    {0: "c"},
    "sys_access":  {0: "c"},
    "open_file":   {0: "c"},

    # Compiler print() builtin -- accepts *u8 in ritz1, String in ritz0
    # (the whole point of this audit!).  Mark as `c` because it is what
    # the self-hosted compiler, selfhosted tests, and runtime all use.
    "print":       {0: "c"},

    # Heap-String constructors -- take StrView, so literal stays bare
    # under terminal state (A) (bare -> StrView).
    "string_from":        {0: "s"},
    "string_from_strview": {0: "s"},

    # StrView constructors -- take StrView, stay bare.
    "strview_from":        {0: "s"},
    "strview_eq":          {0: "s", 1: "s"},
}


# --------------------------------------------------------------------------
# Line scanner -- state machine that walks a single line character by
# character, tracking whether we are inside `#` comment / char literal /
# string literal, and emits (col, is_prefixed, full_text) for every string
# literal it finds.
# --------------------------------------------------------------------------

def _scan_line(line: str) -> Iterator[tuple[int, bool, str]]:
    """Yield (1-based column, has_c_or_s_prefix, literal_text) for each
    string literal found in `line`."""
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]

        # Skip to end of line on `#` comments (Ritz uses `#` like Python).
        if ch == "#":
            return

        # Skip single-quoted char literals: '...', with `\` escapes.
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
            # Check for `c"` / `s"` prefix -- a literal prefix requires the
            # preceding char to be `c` or `s` AND the char before that to
            # not be an identifier continuation (so we don't misclassify
            # `foo"` in weird macros).
            prefixed = False
            if i >= 1 and line[i - 1] in ("c", "s"):
                prev2 = line[i - 2] if i >= 2 else ""
                if not (prev2.isalnum() or prev2 == "_"):
                    prefixed = True
            start = i
            j = i + 1
            while j < n:
                if line[j] == "\\" and j + 1 < n:
                    j += 2
                    continue
                if line[j] == '"':
                    j += 1
                    break
                j += 1
            text = line[start:j]
            col = start + 1 if not prefixed else start  # col of `"` or of `c`/`s`
            yield col, prefixed, text
            i = j
            continue

        i += 1


# --------------------------------------------------------------------------
# Prefix heuristics -- once a bare literal is found, look at the line to
# guess what the author probably wants.
# --------------------------------------------------------------------------

# let/var declarations with an explicit type annotation:
#     let NAME: TYPE = "..."
#     var NAME: TYPE = "..."
RE_LET_TYPED = re.compile(
    r"""\b(?:let|var|const)\s+\w+\s*:\s*
        (?P<ty>
            \*\s*u8           |   # *u8
            \*\s*i8           |   # *i8
            \*\s*const\s*u8   |
            StrView           |
            Span\s*<\s*u8\s*> |
            String
        )
        \s*=
    """,
    re.VERBOSE,
)

# Function parameter annotations in a signature line:
#     fn foo(name: *u8, ...)
RE_PARAM_TY = re.compile(
    r""":\s*
        (?P<ty>
            \*\s*u8        |
            \*\s*i8        |
            StrView        |
            Span\s*<\s*u8\s*> |
            String
        )
    """,
    re.VERBOSE,
)

TYPE_TO_PREFIX = {
    "*u8":       "c",
    "*i8":       "c",
    "*constu8":  "c",
    "strview":   "s",
    "span<u8>":  "s",
    "string":    "string",
}


def _normalize_ty(ty: str) -> str:
    return re.sub(r"\s+", "", ty).lower()


def _prefix_from_type_ann(line: str, col: int) -> Optional[str]:
    """Return a prefix if the literal is on the RHS of a typed binding."""
    head = line[:col - 1]
    m = RE_LET_TYPED.search(head)
    if m:
        return TYPE_TO_PREFIX.get(_normalize_ty(m.group("ty")))
    return None


def _prefix_from_call(
    line: str, col: int, file_sig: Optional[dict[str, dict[int, str]]] = None
) -> Optional[str]:
    """If the literal is an argument to a known stdlib function (or a
    file-local function whose signature was harvested into *file_sig*),
    return the prefix that the callee expects at that arg position."""
    head = line[:col - 1]
    # Match the nearest `ident(` or `ident( arg , arg ,` preceding col.
    # A cheap approach: find all `name(` openings and pick the last one
    # whose parentheses are still open at `col`.
    opens: list[tuple[int, str]] = []  # (open_paren_index, name)
    depth = 0
    i = 0
    last_call: Optional[tuple[int, str]] = None
    name_re = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(")
    while i < len(head):
        m = name_re.match(head, i)
        if m:
            # Walk forward from the `(` matching parens until we run out
            # or depth goes negative (the last open call stays).
            open_idx = m.end() - 1
            # Simple: push onto stack, continue scanning.
            opens.append((open_idx, m.group(1)))
            i = m.end()
            continue
        if head[i] == "(":
            opens.append((i, ""))
        elif head[i] == ")":
            if opens:
                opens.pop()
        i += 1

    # Innermost remaining call = argument context
    call_name = ""
    call_open = -1
    for op, nm in reversed(opens):
        if nm:
            call_name = nm
            call_open = op
            break
    # Look up in stdlib CALL_SIG first, then fall back to the file-local
    # signatures harvested from the current file.
    sig_map: Optional[dict[int, str]] = None
    if call_name in CALL_SIG:
        sig_map = CALL_SIG[call_name]
    elif file_sig is not None and call_name in file_sig:
        sig_map = file_sig[call_name]
    if sig_map is None:
        return None

    # Count commas at depth 1 between call_open+1 and col-1 -> arg index
    arg_idx = 0
    depth = 0
    in_str = False
    in_char = False
    j = call_open + 1
    while j < len(head):
        c = head[j]
        if in_str:
            if c == "\\":
                j += 2
                continue
            if c == '"':
                in_str = False
        elif in_char:
            if c == "\\":
                j += 2
                continue
            if c == "'":
                in_char = False
        else:
            if c == '"':
                in_str = True
            elif c == "'":
                in_char = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == "," and depth == 0:
                arg_idx += 1
        j += 1
    return sig_map.get(arg_idx)


def _prefix_from_context(line: str, col: int, file_sig: Optional[dict] = None) -> str:
    """Best-effort guess at the correct prefix.

    *file_sig* is an optional per-file mapping ``{fn_name: {argpos: prefix}}``
    harvested from `fn foo(arg: TYPE, ...)` declarations in the current
    file; it supplements `CALL_SIG` so we can match user-defined helpers
    in the same file (e.g. `fn first_byte_len(s: StrView)` -> literal
    passed at arg 0 stays bare).
    """
    # Line-local comments are already stripped by the scanner.

    # 0) Attribute contexts: `[[name = "..."]]`, `[[cfg(name = "...")]]`,
    # etc.  The ritz parser only accepts `TokenType.STRING` for the rhs of
    # attribute equalities, so the literal MUST stay bare.  Tag as `s`
    # (stays bare under terminal state (A)).
    stripped = line.lstrip()
    if stripped.startswith("[["):
        return "s"

    # 1) Typed binding wins if present.
    p = _prefix_from_type_ann(line, col)
    if p:
        return p

    # 2) Stdlib + file-local call signatures.
    p = _prefix_from_call(line, col, file_sig=file_sig)
    if p:
        return p

    # 3) Struct literal field detection -- if the literal is directly
    # after a `field:` in a struct-literal context (e.g.
    # `Pair { a: "x", b: "y" }`), the field's declared type could be
    # StrView or *u8 -- we cannot tell without cross-file analysis.
    # Flag as `?` rather than risk a wrong `c`-rewrite.
    head = line[:col - 1]
    # The literal is immediately preceded by `FIELD:\s*` and we're
    # inside a `{ ... }` block (struct literal or const init).
    m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$", head)
    if m and "{" in head[:m.start()]:
        return "?"

    # 3b) Array / collection literal element -- the line is just
    # whitespace + `"..."` + optional `,` / `]` trailing.  We cannot
    # tell the element type without multi-line analysis, so flag `?`.
    tail = line[col - 1:]
    if head.strip() == "" and re.match(r'^"(?:[^"\\]|\\.)*"\s*[,\]]?\s*$', tail):
        return "?"

    # 4) Fallbacks based on common idioms.
    if stripped.startswith("assert ") and "," in stripped:
        # `assert cond, "msg"` -- msg goes to panic, which takes *u8
        return "c"
    if stripped.startswith("return "):
        # Best guess: functions returning string-ish from a bare literal
        # probably want cstr.  Not always true; flag it explicitly.
        return "?"
    return "c"


# Regex to harvest file-local function signatures.  Matches
#   fn NAME(a: TYPE, b: TYPE, ...)
# with TYPE in the same whitelist as RE_LET_TYPED.  Multiline because
# parameter lists can wrap.
RE_FN_SIG = re.compile(
    r"""^\s*(?:pub\s+)?fn\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*
        (?:<[^>]*>)?\s*
        \(\s*(?P<params>[^)]*)\)
    """,
    re.VERBOSE | re.MULTILINE,
)


def _harvest_file_sig(text: str) -> dict[str, dict[int, str]]:
    """Scan *text* for top-level `fn NAME(a: TYPE, b: TYPE)` declarations
    and build a mapping compatible with CALL_SIG."""
    sig: dict[str, dict[int, str]] = {}
    for m in RE_FN_SIG.finditer(text):
        name = m.group("name")
        params = m.group("params").strip()
        if not params:
            continue
        # Split on commas at top level (no generics nesting here; keep simple).
        arg_map: dict[int, str] = {}
        parts = [p.strip() for p in params.split(",") if p.strip()]
        for idx, p in enumerate(parts):
            # Each part is `NAME: TYPE` (optionally with leading @& or &).
            ptm = re.match(r"[A-Za-z_][A-Za-z0-9_]*\s*:\s*(?P<ty>.+)$", p)
            if not ptm:
                continue
            ty = _normalize_ty(ptm.group("ty"))
            prefix = TYPE_TO_PREFIX.get(ty)
            if prefix:
                arg_map[idx] = prefix
        if arg_map:
            # If a fn is declared multiple times (e.g. with cfg gates), union
            # the maps -- first-seen wins on conflict.
            existing = sig.setdefault(name, {})
            for k, v in arg_map.items():
                existing.setdefault(k, v)
    return sig


# --------------------------------------------------------------------------
# File walking
# --------------------------------------------------------------------------

SKIP_DIRS = {
    "out",
    "build",
    ".git",
    "cache",
    "__pycache__",
    "benchmarks",           # heavy, generated
    "docs/archive",         # retired
}

def _iter_ritz_files() -> Iterator[Path]:
    for p in RITZ_ROOT.rglob("*.ritz"):
        parts = p.relative_to(RITZ_ROOT).parts
        # Skip any path component in SKIP_DIRS, and composite
        # directories like "docs/archive".
        skip = False
        rel = "/".join(parts)
        for bad in SKIP_DIRS:
            if bad in parts or rel.startswith(bad + "/") or ("/" + bad + "/") in ("/" + rel):
                skip = True
                break
        if skip:
            continue
        # Skip `.ritz.sig` sibling (sig files are declaration-only and
        # unlikely to carry literals anyway, but be safe).
        if p.suffixes[-2:] == [".ritz", ".sig"]:
            continue
        yield p


def _project_of(rel: Path) -> str:
    """Return the top-level project bucket for a path relative to
    `projects/ritz`."""
    parts = rel.parts
    if not parts:
        return "(root)"
    return parts[0]


def _directory_of(rel: Path) -> str:
    """Return a coarse two-level directory key."""
    parts = rel.parts
    if len(parts) <= 1:
        return parts[0] if parts else "(root)"
    return "/".join(parts[:2])


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> int:
    writer = csv.writer(sys.stdout)
    writer.writerow(["path", "line", "col", "context", "suggested_prefix"])

    per_project: Counter[str] = Counter()
    per_directory: Counter[str] = Counter()
    per_prefix: Counter[str] = Counter()
    total = 0
    files_scanned = 0

    for fpath in _iter_ritz_files():
        files_scanned += 1
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"warn: {fpath}: {e}", file=sys.stderr)
            continue

        rel = fpath.relative_to(RITZ_ROOT)
        rel_str = str(rel)
        proj = _project_of(rel)
        dkey = _directory_of(rel)

        # Harvest per-file function signatures so we can correctly infer
        # prefixes for literals passed to user-defined helpers in the same
        # file.
        file_sig = _harvest_file_sig(text)

        for lineno, raw in enumerate(text.splitlines(), start=1):
            for col, prefixed, lit in _scan_line(raw):
                if prefixed:
                    continue  # skip c"..." / s"..."
                total += 1
                prefix = _prefix_from_context(raw, col, file_sig=file_sig)
                per_project[proj] += 1
                per_directory[dkey] += 1
                per_prefix[prefix] += 1
                # Context: trimmed source line, de-noised
                ctx = raw.strip()
                if len(ctx) > 160:
                    ctx = ctx[:157] + "..."
                writer.writerow([rel_str, lineno, col, ctx, prefix])

    # --- Summary to stderr --------------------------------------------------
    out = sys.stderr
    print(f"\n=== bare-string audit summary ===", file=out)
    print(f"files scanned : {files_scanned}", file=out)
    print(f"bare literals : {total}", file=out)
    print(f"\n-- per project --", file=out)
    for k, v in per_project.most_common():
        print(f"  {v:6d}  {k}", file=out)
    print(f"\n-- per directory (top 20) --", file=out)
    for k, v in per_directory.most_common(20):
        print(f"  {v:6d}  {k}", file=out)
    print(f"\n-- per suggested prefix --", file=out)
    for k, v in per_prefix.most_common():
        print(f"  {v:6d}  {k}", file=out)
    print("", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
