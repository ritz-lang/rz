#!/usr/bin/env python3
"""Check that no `s"..."` literals remain in Ritz source.

AGAST #98 deprecated and removed the `s"..."` span-string prefix — bare
`"..."` now produces a StrView of the same { ptr, len } shape, so `s"..."`
is redundant syntax. This script is the CI guard that prevents it from
creeping back in.

Usage:
    python3 tools/check_no_s_strings.py [ROOT]

ROOT defaults to `projects/ritz/`. Excludes docs/archive/ by default.
Exits 0 when clean, 1 when at least one live `s"..."` token is found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# Match `s"` where the `s` starts a new lexeme (preceded by start-of-line,
# whitespace, or a single-char delimiter like `=(,[{`). Explicitly rejects:
#   - `c"..."` (the `s` inside a c-string would need a preceding `"` or ident)
#   - identifiers ending in `s` followed by `"` like `foo_s"..."` (not valid
#     Ritz syntax anyway; but we filter to be safe)
#   - `s` that appears inside another string literal (we strip strings first)
S_STRING_RE = re.compile(r'(?:^|(?<=[\s=(,\[{]))s"')


def strip_string_content(line: str) -> str:
    """Return the line with the *contents* of every `"..."` / `c"..."`
    string literal blanked out, so occurrences of `s"` inside string
    contents don't trip the regex below. Preserves quote characters so
    we don't accidentally fuse adjacent lexemes.
    """
    out = []
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if ch == '"':
            # Copy the opening quote, then scan until the matching quote,
            # replacing interior characters with spaces.
            out.append(ch)
            i += 1
            while i < n:
                c = line[i]
                if c == '\\' and i + 1 < n:
                    out.append('  ')  # preserve column width
                    i += 2
                    continue
                if c == '"':
                    out.append(c)
                    i += 1
                    break
                out.append(' ')
                i += 1
        elif ch == '#':
            # Comment: blank the rest of the line.
            out.append(' ' * (n - i))
            break
        else:
            out.append(ch)
            i += 1
    return ''.join(out)


def find_violations(root: Path) -> list[tuple[Path, int, str]]:
    violations: list[tuple[Path, int, str]] = []
    for path in sorted(root.rglob('*.ritz')):
        # Skip archived/docs content — those are frozen snapshots of
        # earlier eras and may legitimately contain `s"..."`.
        rel = path.relative_to(root)
        if any(part == 'archive' for part in rel.parts):
            continue
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = strip_string_content(line)
            if S_STRING_RE.search(stripped):
                violations.append((path, lineno, line.rstrip()))
    return violations


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('projects/ritz')
    if not root.exists():
        print(f'check_no_s_strings.py: root {root} does not exist', file=sys.stderr)
        return 2

    violations = find_violations(root)
    if not violations:
        return 0

    print('ERROR: s"..." literals found — deprecated in AGAST #98.')
    print('       Use bare "..." (StrView) or c"..." (*u8) instead.')
    print()
    for path, lineno, line in violations:
        print(f'  {path}:{lineno}: {line}')
    print()
    print(f'{len(violations)} violation(s).')
    return 1


if __name__ == '__main__':
    sys.exit(main())
