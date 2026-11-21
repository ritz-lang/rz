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

Also rejects tracked editor and merge backups (*.orig, *.old) and tracked ELF
binaries anywhere under projects/ritz, which no import graph would see.  The ELF
check covered only ritz0/ until AGAST #3447 found ritz1/ritz1_new tracked.

The same rule covers ritzlib/ (AGAST #3913): every ritzlib module must be
reachable from a non-test .ritz file anywhere in the repo, through `import
ritzlib.x` lines.  #1859 found crt0, entry, meta, async.ritz and lang/* kept
alive only by docs and tests.  RITZLIB_ALLOWLIST names the exceptions.

Runs in `make tools-unit` through test_check_liveness.py::test_real_tree_is_live.
"""

import argparse
import ast
import re
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
    "harness/spawn_guard.py": "pytest plugin; conftest.py names it in pytest_plugins",
    "cost_meter.py": "pytest plugin; conftest.py names it in pytest_plugins",
    "only_files.py": "pytest plugin; conftest.py names it in pytest_plugins",
    "read_guard.py": "pytest plugin; conftest.py names it in pytest_plugins",
}

# Directories under ritz0/ that are sys.path roots of their own: a module in
# one is imported by its bare name.  harness/ holds the pytest harness, kept
# out of the compiler hash (AGAST #3915); conftest.py puts it on sys.path.
SYS_PATH_SUBDIRS = ("harness",)

# Non-test Python outside ritz0/ that runs with ritz0/ on sys.path.  "" is the
# project root itself, non-recursively.
EXTERNAL_DIRS = ("", "tools", "scripts")

# ritzlib modules (paths under ritzlib/) that no production code imports, each
# with the reason it stays.  An entry that gains a production importer is
# reported, so this list cannot outlive its reasons.
RITZLIB_ALLOWLIST = {
    "testlib.ritz": "the test assertion library: every importer is a test by design",
    "ptr.ritz": "ptr_read is LANGUAGE_SPEC §13.2's documented way to move a value "
                "out of raw memory; only ritz0/tests/test_ref_into_value.py calls it so far",
    "fmt.ritz": "#198 Phase 2 (#201) ships the Writer / Display surface tested in "
                "isolation (ritzlib/tests/test_fmt_*); Phase 3 (#202) lowers "
                "interpolation onto it. Drop this entry when #202 lands",
}

# A `.ritz` file with one of these as a directory component, or named test_*,
# is a test: it cannot keep a ritzlib module alive.
RITZ_TEST_DIRS = {"test", "tests"}
# Archived or snapshotted code is not production either.  Matches a path
# component named archive (archive/, docs/archive/) or this prefix.
RITZ_EXCLUDED_PREFIXES = ("projects/larb/review/",)

# `import ritzlib.a.b`, `pub import ...`, with or without `{ items }` / `as x`.
# Anchored at line start, so `# import ritzlib.x` in a comment does not count.
RITZLIB_IMPORT = re.compile(r"^[ \t]*(?:pub[ \t]+)?import[ \t]+ritzlib((?:\.\w+)+)", re.MULTILINE)

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
    if len(parts) > 1 and parts[0] in SYS_PATH_SUBDIRS:
        parts = parts[1:]
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
        parts = list(PurePosixPath(rel).relative_to(RITZ0).parent.parts)
        return parts[1:] if parts[:1] and parts[0] in SYS_PATH_SUBDIRS else parts

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


def repo_root(root):
    """The git toplevel containing `root` (ritzlib's importers span the repo)."""
    return Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip())


def ritzlib_dir(root, repo):
    """`root`'s ritzlib/ as a POSIX path relative to `repo`."""
    rel = Path(root).resolve().relative_to(Path(repo).resolve())
    return (PurePosixPath(rel.as_posix()) / "ritzlib").as_posix()


def _is_ritz_test(rel):
    path = PurePosixPath(rel)
    return path.name.startswith("test_") or bool(RITZ_TEST_DIRS & set(path.parts[:-1]))


def _is_ritz_excluded(rel):
    return "archive" in PurePosixPath(rel).parts[:-1] or rel.startswith(RITZ_EXCLUDED_PREFIXES)


def _ritzlib_imports(root, rel):
    """Dotted names after `ritzlib.` that `rel` imports: {"sys", "async.tasks"}."""
    text = (Path(root) / rel).read_text(encoding="utf-8", errors="replace")
    return {m.lstrip(".") for m in RITZLIB_IMPORT.findall(text)}


def find_ritzlib_orphans(repo, files, lib, allow=None):
    """Modules under `lib` that no non-test .ritz file in `files` reaches.

    `files` are relative to `repo`; `lib` is ritzlib/'s path in it.  `allow`
    (default RITZLIB_ALLOWLIST) maps lib-relative paths to reasons: those
    modules are roots.  An allowlisted module that is missing, or that
    production reaches anyway, is reported as a stale entry.
    """
    allow = RITZLIB_ALLOWLIST if allow is None else allow
    prefix = f"{lib}/"
    modules = {}
    for rel in files:
        if rel.startswith(prefix) and rel.endswith(".ritz"):
            inner = PurePosixPath(rel[len(prefix):])
            if inner.parts[0] not in RITZ_TEST_DIRS:
                modules[".".join(inner.with_suffix("").parts)] = rel

    pending = []
    for rel in files:
        if (rel.endswith(".ritz") and not rel.startswith(prefix)
                and not _is_ritz_test(rel) and not _is_ritz_excluded(rel)):
            pending.extend(_ritzlib_imports(repo, rel))
    production = set(pending) & modules.keys()

    def reach(start):
        live, todo = set(), list(start)
        while todo:
            module = todo.pop()
            if module in live or module not in modules:
                continue
            live.add(module)
            todo.extend(_ritzlib_imports(repo, modules[module]))
        return live

    live_without_allow = reach(production)
    allowed = {".".join(PurePosixPath(a).with_suffix("").parts) for a in allow}
    live = reach(production | (allowed & modules.keys()))

    report = sorted(rel for name, rel in modules.items() if name not in live)
    for entry in sorted(allow):
        name = ".".join(PurePosixPath(entry).with_suffix("").parts)
        if name not in modules:
            report.append(f"{prefix}{entry} (allowlisted module is missing)")
        elif name in live_without_allow:
            report.append(f"{prefix}{entry} (allowlisted but has a production importer; "
                          "drop the entry)")
    return report


def find_strays(root, files):
    """Backup files and ELF binaries anywhere in `files`."""
    strays = []
    for rel in files:
        if rel.endswith(BACKUP_SUFFIXES):
            strays.append(rel)
        else:
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
    repo = repo_root(args.root)
    repo_files = project_files(repo)
    lib_orphans = find_ritzlib_orphans(repo, repo_files, ritzlib_dir(args.root, repo))

    for rel in orphans + lib_orphans:
        print(rel if rel.endswith(")") else f"{rel}: no production importer")
    for rel in strays:
        print(f"{rel}: backup file or binary; delete it")
    if orphans or strays or lib_orphans:
        print("Import it from production code, delete it, or add it to "
              "ENTRY_POINTS / RITZLIB_ALLOWLIST in tools/check_liveness.py with a reason.")
        return 1
    print(f"ritz0 liveness: OK ({sum(f.endswith('.py') for f in files)} Python files read)")
    print(f"ritzlib liveness: OK ({sum(f.endswith('.ritz') for f in repo_files)} .ritz files read)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
