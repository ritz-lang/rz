#!/usr/bin/env python3
"""Report brace-import names a Ritz file never uses.

LARB review/5 harland F4 (AGAST #3458): after kernel main.ritz was split
into postinit/process/apic, main.ritz still imported 300 names, 210 of
which its body never mentioned. Nothing failed, so nothing noticed, and
the import list overstated main's coupling to the scheduler. This is the
mechanism that fails.

A name `n` in `import mod { a, n, b }` (or `n` from `x as n`) is *used*
when it appears as an identifier token anywhere in the file outside the
import statements, comments and string literals. Asm blocks count: their
`{operand}` and `call sym` text names Ritz symbols.

Bare `import mod` is not checked (it names no symbols).

Usage:
    python3 tools/check_unused_imports.py PATH [PATH...]

PATH is a .ritz file or a directory (searched recursively). Exits 0 when
clean, 1 on an unused name, 2 on a bad path. There is no allowlist: one
existed to ratchet the kernel's pre-existing offenders down (#3458), and
#4174 burned it to zero and deleted it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_no_s_strings import strip_string_content  # noqa: E402

# `import a.b.c { x, y as z, ... }` at the start of a line; the brace list
# may span lines. Comments inside the braces are stripped before this runs.
BRACE_IMPORT_RE = re.compile(r"^[ \t]*import[ \t]+([\w.]+)[ \t]*\{([^}]*)\}", re.M)
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _strip(text: str) -> str:
    """Blank comments and string contents, keeping line structure."""
    return "\n".join(strip_string_content(line) for line in text.split("\n"))


def unused_imports(text: str) -> list[tuple[int, str, str]]:
    """Return (lineno, module, name) for every brace-imported name the
    file's body never mentions, in source order."""
    code = _strip(text)
    imports: list[tuple[int, str, str]] = []
    body = code
    for m in BRACE_IMPORT_RE.finditer(code):
        start_line = code.count("\n", 0, m.start()) + 1
        for raw in m.group(2).split(","):
            parts = raw.split()
            if not parts:
                continue
            # `x as y` binds y; plain `x` binds x.
            name = parts[-1]
            imports.append((start_line, m.group(1), name))
        # Blank the whole import statement out of the body.
        span = code[m.start() : m.end()]
        body = body[: m.start()] + re.sub(r"[^\n]", " ", span) + body[m.end() :]
    used = set(IDENT_RE.findall(body))
    return [(ln, mod, name) for (ln, mod, name) in imports if name not in used]


def collect(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob("*.ritz")))
        else:
            files.append(p)
    return files


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: check_unused_imports.py PATH [PATH...]", file=sys.stderr)
        return 2
    paths = [Path(a) for a in argv]
    for p in paths:
        if not p.exists():
            print(f"check_unused_imports.py: {p} does not exist", file=sys.stderr)
            return 2
    total = 0
    for f in collect(paths):
        for ln, mod, name in unused_imports(
            f.read_text(encoding="utf-8", errors="replace")
        ):
            print(f"{f}:{ln}: unused import `{name}` from {mod}")
            total += 1
    if total:
        print(f"{total} unused-import problem(s).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
