#!/usr/bin/env python3
"""Print a Make dependency rule for a ritz module's transitive imports.

    mkdeps.py <source.ritz> <target>...

Writes `<target>... : <every .ritz the source imports, transitively>` plus an
empty rule per dependency (like gcc -MP), so a deleted/renamed module does not
wedge the build with "No rule to make target".

Why transitive: a module's IR bakes in field offsets for every struct it
touches, including structs reached through an import's own imports (AGAST
#1659).  Over-approximating costs a few extra ritz0 runs; under-approximating
links a silently miscompiled ritz1.

Resolution mirrors ritz0/import_resolver.py `_resolve_import_path`: relative
to the importing file (a/b.ritz, then a.b.ritz), then each RITZ_PATH entry.
Imports that resolve nowhere are skipped; ritz0 will report them.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

IMPORT_RE = re.compile(r"^[ \t]*(?:pub[ \t]+)?import[ \t]+([A-Za-z_][\w.]*)", re.M)


def resolve(parts: list[str], from_file: Path, search: list[Path]) -> Path | None:
    nested = Path(*parts[:-1], parts[-1] + ".ritz")
    flat = Path(".".join(parts) + ".ritz")
    for base in [from_file.parent, *search]:
        for rel in (nested, flat):
            cand = base / rel
            if cand.is_file():
                return cand.resolve()
    return None


def closure(source: Path, search: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    todo = [source.resolve()]
    while todo:
        cur = todo.pop()
        for name in IMPORT_RE.findall(cur.read_text(errors="replace")):
            dep = resolve(name.split("."), cur, search)
            if dep is not None and dep not in seen:
                seen.add(dep)
                todo.append(dep)
    seen.discard(source.resolve())
    return sorted(seen)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    source, targets = Path(argv[1]), argv[2:]
    search = [Path(p) for p in os.environ.get("RITZ_PATH", "").split(":") if p]
    # Relative to make's cwd, so prerequisites name the same files the rules
    # do (src/ast.ritz, ../ritzlib/sys.ritz) and a moved tree stays valid.
    deps = [os.path.relpath(d) for d in closure(source, search)]
    out = [" ".join(targets) + ": " + " \\\n  ".join(deps), ""]
    out += [f"{d}:" for d in deps]
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
