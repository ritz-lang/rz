#!/usr/bin/env python3
"""ritzlib's two layers, core and hosted, and the check between them (AGAST #4119).

CORE is the manifest of ritzlib's core: the modules a freestanding target (a
kernel, with no syscalls) can import.  None of them may import a module
outside CORE, so none reaches ritzlib.sys, fs, net, uring, process or os.env
by any path.  Every module not listed is hosted (Linux or Harland userland).

Core reaches the platform only through the hooks ritzlib.memory and
ritzlib.hashmap declare `extern fn` (ritz_platform_page_map,
ritz_platform_page_unmap, ritz_platform_fatal): ritzlib.sys defines them for a
hosted program, and a freestanding one defines its own.

    python3 tools/ritzlib_layers.py [RITZLIB]   # exit 1 naming each violation

tools/test_ritzlib_layers.py::test_core_imports_only_core runs the check in
`make tools-unit`.
"""

import re
import sys
from pathlib import Path

# ritzlib's core, by import path under `ritzlib.`.  fmt.digits, drop and hash are
# here because the others use them.
CORE = frozenset({
    "drop", "fmt.digits", "gvec", "hash", "hashmap", "memory", "option", "ptr",
    "result", "span", "str", "string", "strview",
})

IMPORT = re.compile(r"\s*(?:pub\s+)?import\s+ritzlib\.([A-Za-z_][\w.]*)")


def imports(path):
    """[(line number, module under ritzlib.)] for each `import ritzlib.X` in path."""
    out = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        match = IMPORT.match(line)
        if match:
            out.append((n, match.group(1)))
    return out


def check(ritzlib):
    """One message per violation: a CORE module missing, or importing a hosted one."""
    ritzlib = Path(ritzlib)
    problems = []
    for mod in sorted(CORE):
        rel = f"{mod.replace('.', '/')}.ritz"
        path = ritzlib / rel
        if not path.is_file():
            problems.append(f"ritzlib/{rel}: core module ritzlib.{mod} does not exist")
            continue
        for n, dep in imports(path):
            if dep not in CORE:
                problems.append(f"ritzlib/{rel}:{n}: core module ritzlib.{mod} "
                                f"imports hosted ritzlib.{dep}")
    return problems


def main(argv):
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent / "ritzlib"
    problems = check(root)
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
