#!/usr/bin/env python3
"""Fail on ritz0 modules that production cannot reach (AGAST #1822).

ritz0/ once carried ~15k dead lines: a Phase 3 mixin rewrite never wired in, a
generated parser and its adapter, and a copy of the struct layout code that 13
tests covered while production ran the other copy.  Nothing noticed, because a
dead module still parses, still imports, and can still have passing tests.

The rule: every non-test `.py` under ritz0/ must be reachable from a production
root.  The roots are ENTRY_POINTS plus whatever non-test code outside ritz0/
imports (build.py, cache.py, tools/, scripts/).

This is reachability, not "has an importer": two orphans importing each other
each have one.  Test modules are never roots, so a test cannot keep the code it
tests alive.  Imports are read from the AST, so a commented-out import does not
count and one inside a function does.

Also rejects editor and merge backups (*.orig, *.old) and ELF binaries in
ritz0/, which no import graph would see.

Runs in `make tools-unit` through test_check_liveness.py::test_real_tree_is_live.
"""

import argparse
import ast
import subprocess
import sys
from pathlib import Path, PurePosixPath

RITZ0 = "ritz0"

# ritz0 modules that nothing imports by a name this tool can see, each with the
# reason it stays.  Keep this short: an entry here switches the check off for
# that module and for everything it imports.
ENTRY_POINTS = {
    "ritz0.py": "the compiler CLI; build.py runs it as a script",
    "list_deps.py": "build.py runs it as a script",
    "test_runner.py": "build.py loads it with importlib; not a test despite the name",
    "conftest.py": "pytest loads it",
    "spawn_guard.py": "pytest plugin; conftest.py names it in pytest_plugins",
    "symbol_table.py": "tests only for now; it is the interface model for #1810",
}

# Non-test Python outside ritz0/ that runs with ritz0/ on sys.path.  "" is the
# project root itself, non-recursively.
EXTERNAL_DIRS = ("", "tools", "scripts")

BACKUP_SUFFIXES = (".orig", ".old")
ELF_MAGIC = b"\x7fELF"


def project_files(root, untracked=True):
    """Project files as relative POSIX paths, ignored build output excluded.

    With `untracked`, an orphan fails before it is ever `git add`ed.  Strays
    are checked on tracked files only: a local binary is not yet the tree's
    problem, and a test may be writing one.
    """
    extra = ["--others", "--exclude-standard"] if untracked else []
    out = subprocess.run(
        ["git", "ls-files", "--cached", *extra],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout
    return sorted(f for f in out.splitlines() if (Path(root) / f).is_file())


def _is_test(rel):
    name = PurePosixPath(rel).name
    return name.startswith("test_") and name != "test_runner.py"


def _module_name(rel):
    """`ritz0/emitter/fn_cache.py` -> `emitter.fn_cache`; a package's
    `__init__.py` takes the package's name."""
    parts = PurePosixPath(rel).relative_to(RITZ0).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _is_external_production(rel):
    path = PurePosixPath(rel)
    if path.suffix != ".py" or _is_test(rel):
        return False
    if len(path.parts) == 1:
        return "" in EXTERNAL_DIRS
    return path.parts[0] != RITZ0 and path.parts[0] in EXTERNAL_DIRS


def _imported_names(root, rel, package):
    """Every dotted name `rel` imports, with each parent package.

    `package` is the importing module's package, for relative imports.  `from
    a import b` yields `a.b` too, since b may be a submodule; a name that isn't
    a module simply matches nothing.
    """
    source = (Path(root) / rel).read_text(encoding="utf-8")
    names = set()
    for node in ast.walk(ast.parse(source, filename=rel)):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                keep = len(package) - (node.level - 1)
                base = ".".join(package[:max(keep, 0)] + ([base] if base else []))
            names.add(base)
            names.update(f"{base}.{alias.name}".lstrip(".") for alias in node.names)
    parents = set()
    for name in names:
        parts = name.split(".")
        parents.update(".".join(parts[:i]) for i in range(1, len(parts)))
    return names | parents


def find_orphans(root, files):
    """Paths under ritz0/ that no production root reaches, sorted.

    A listed entry point with no file is reported too: a stale list would
    otherwise keep vouching for a module that has gone.
    """
    modules = {}
    for rel in files:
        if rel.startswith(f"{RITZ0}/") and rel.endswith(".py") and not _is_test(rel):
            parts = PurePosixPath(rel).parts
            if "test" not in parts[1:-1]:
                modules[_module_name(rel)] = rel

    def package_of(rel):
        return list(PurePosixPath(rel).relative_to(RITZ0).parent.parts)

    entries = [f"{RITZ0}/{entry}" for entry in ENTRY_POINTS]
    missing = [e for e in entries if e not in files]

    pending = [_module_name(e) for e in entries if e not in missing]
    for rel in files:
        if _is_external_production(rel):
            pending.extend(_imported_names(root, rel, []) & modules.keys())

    live = set()
    while pending:
        module = pending.pop()
        if module in live:
            continue
        live.add(module)
        rel = modules[module]
        pending.extend(_imported_names(root, rel, package_of(rel)) & modules.keys())

    orphans = [rel for name, rel in modules.items() if name not in live]
    return sorted(orphans) + [f"{e} (listed entry point is missing)" for e in missing]


def find_strays(root, files):
    """Backup files anywhere in `files`, and ELF binaries under ritz0/."""
    strays = []
    for rel in files:
        if rel.endswith(BACKUP_SUFFIXES):
            strays.append(rel)
        elif rel.startswith(f"{RITZ0}/"):
            with open(Path(root) / rel, "rb") as f:
                if f.read(len(ELF_MAGIC)) == ELF_MAGIC:
                    strays.append(rel)
    return strays


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="the projects/ritz directory (default: this checkout's)")
    args = parser.parse_args(argv)

    files = project_files(args.root)
    orphans = find_orphans(args.root, files)
    strays = find_strays(args.root, project_files(args.root, untracked=False))

    for rel in orphans:
        print(f"{rel}: no production importer")
    for rel in strays:
        print(f"{rel}: backup file or binary; delete it")
    if orphans or strays:
        print("Import it from production code, delete it, or add it to "
              "ENTRY_POINTS in tools/check_liveness.py with a reason.")
        return 1
    print(f"ritz0 liveness: OK ({sum(f.endswith('.py') for f in files)} Python files read)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
