#!/usr/bin/env python3
"""Flag `tempfile.mkdtemp` in test files when nothing cleans up what it made.

AGAST #2875: three test modules called `mkdtemp` with no `rmtree`, and the
gate runs outside a room's PrivateTmp, so every gate left directories in the
host's /tmp: about 2,700 dirs and 475 MB on one machine in a day. pytest's
`tmp_path` / `tmp_path_factory` clean up after themselves; a bare `mkdtemp`
does not.

The rule: a `mkdtemp(...)` call in a test file (`test_*.py`, `*_test.py`,
`conftest.py`) needs a cleanup in the scope that owns the directory:

  * a method: anywhere in its class (setUp/tearDown pairs);
  * a function that stores the result in a `global`: anywhere in the module
    (pytest_configure/pytest_unconfigure pairs);
  * any other function: inside that function.

A cleanup is a reference to `rmtree`, `atexit`, `addfinalizer`, `addCleanup`,
or a name starting `cleanup`. A line can opt out with
`# tempdir-ok: <reason>`, and the reason must not be empty.

Usage:
    python3 tools/check_test_tempdirs.py [ROOT]

ROOT defaults to this script's project (`projects/ritz`). Exits 0 when
clean, 1 when at least one call has no cleanup.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

CLEANUP_NAMES = {"rmtree", "atexit", "addfinalizer", "addCleanup"}
PRAGMA_RE = re.compile(r"#\s*tempdir-ok:\s*\S")
EXCLUDED_PARTS = {"build", ".venv", "venv", "node_modules", "__pycache__", ".git", "archive"}


def is_test_file(path: Path) -> bool:
    name = path.name
    return name == "conftest.py" or (name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py")))


def _is_mkdtemp(call: ast.Call) -> bool:
    func = call.func
    return (isinstance(func, ast.Name) and func.id == "mkdtemp") or (
        isinstance(func, ast.Attribute) and func.attr == "mkdtemp")


def _cleans_up(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        ident = sub.id if isinstance(sub, ast.Name) else sub.attr if isinstance(sub, ast.Attribute) else None
        if ident is not None and (ident in CLEANUP_NAMES or ident.startswith("cleanup")):
            return True
    return False


def _owner(stack: list[ast.AST], tree: ast.Module) -> ast.AST:
    """The scope that owns a directory created inside `stack[-1]`."""
    funcs = [n for n in stack if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not funcs:
        return tree
    func = funcs[-1]
    if any(isinstance(n, ast.Global) for n in ast.walk(func)):
        return tree
    parent = stack[stack.index(func) - 1] if stack.index(func) > 0 else tree
    return parent if isinstance(parent, ast.ClassDef) else func


def find_violations_in_source(source: str, filename: str = "<src>") -> list[tuple[int, str]]:
    """(lineno, line) for every mkdtemp call with no cleanup in its owning scope."""
    tree = ast.parse(source, filename)
    lines = source.splitlines()
    found: list[tuple[int, str]] = []

    def visit(node: ast.AST, stack: list[ast.AST]):
        if isinstance(node, ast.Call) and _is_mkdtemp(node):
            line = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
            if not PRAGMA_RE.search(line) and not _cleans_up(_owner(stack, tree)):
                found.append((node.lineno, line.strip()))
        for child in ast.iter_child_nodes(node):
            visit(child, stack + [node])

    visit(tree, [])
    return found


def find_violations(root: Path) -> list[tuple[Path, int, str]]:
    out: list[tuple[Path, int, str]] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if EXCLUDED_PARTS.intersection(rel.parts[:-1]) or not is_test_file(path):
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        if "mkdtemp" not in source:
            continue
        for lineno, line in find_violations_in_source(source, str(path)):
            out.append((rel, lineno, line))
    return out


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    violations = find_violations(root)
    for rel, lineno, line in violations:
        print(f"{rel}:{lineno}: mkdtemp with no cleanup: {line}")
    if violations:
        print(f"\n{len(violations)} leaking mkdtemp call(s). Use tmp_path / tmp_path_factory, "
              "or rmtree the directory (AGAST #2875).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
