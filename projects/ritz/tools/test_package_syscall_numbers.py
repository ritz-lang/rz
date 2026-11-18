"""No package redeclares syscall numbers beside `import ritzlib.sys` (AGAST #4121),
nor passes a bare number as syscallN's first argument there (AGAST #4145).

Moved from ritz0/test_ritzlib_platform_layering.py by AGAST #4032.  It reads
every package's *.ritz, and it was the only test in the "ritz0 unit tests"
step that did: measured 2026-11-18 (strace + an audit hook over a full run),
the step otherwise opens no file of most packages but their manifests.  In
that step it made every package an input of tools/ritz0_scope.py, so a
package-only gate could never skip the step's ~420-520 s.  It compiles
nothing; here, in the tools step every gate runs, it still guards every
package, and ritz0/read_guard.py stops a ritz0 test reading them again
unnoticed.

The rest of the #1857/#4121 contract (sys.ritz's own table, target gating)
stays in ritz0/test_ritzlib_platform_layering.py.
"""

import re
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
PROJECTS = RITZ_ROOT.parent
RITZLIB = RITZ_ROOT / "ritzlib"
SYS = RITZLIB / "sys.ritz"
# docs/archive is historical and not built (docs/archive/README.md).
ARCHIVE = RITZ_ROOT / "docs" / "archive"

CONST_SYS = re.compile(r"^\s*(?:pub\s+)?const\s+(SYS_\w+)\b")
IMPORTS_SYS = re.compile(r"^import\s+ritzlib\.sys\b", re.M)


def _sys_consts_beside_ritzlib_sys(files):
    """[(path:line, name)] for each `const SYS_*` in a file importing ritzlib.sys."""
    hits = []
    for path in files:
        src = path.read_text()
        if not IMPORTS_SYS.search(src):
            continue
        for n, line in enumerate(src.splitlines(), 1):
            m = CONST_SYS.match(line)
            if m:
                hits.append((f"{path}:{n}", m.group(1)))
    return hits


@pytest.mark.unit
def test_no_package_redeclares_syscall_numbers_beside_ritzlib_sys():
    # The harland kernel keeps its own `enum Syscall`, not ritzlib's table.
    kernel = PROJECTS / "harland" / "kernel"
    files = [p for p in sorted(PROJECTS.rglob("*.ritz"))
             if p != SYS and ARCHIVE not in p.parents and kernel not in p.parents]
    # Not vacuous: the walk reaches the packages, not just ritz/.
    assert any(PROJECTS / "harland" in p.parents for p in files)
    hits = _sys_consts_beside_ritzlib_sys(files)
    assert not hits, "const SYS_* beside `import ritzlib.sys`: " + repr(hits)


@pytest.mark.unit
def test_beside_check_sees_a_redeclaration(tmp_path):
    a = tmp_path / "a.ritz"
    a.write_text("import ritzlib.sys { syscall1 }\nconst SYS_FB_MAP: i64 = 211\n")
    b = tmp_path / "b.ritz"   # freestanding: no ritzlib.sys, its own table
    b.write_text("const SYS_EXIT: i64 = 20\n")
    hits = _sys_consts_beside_ritzlib_sys([a, b])
    assert [name for _, name in hits] == ["SYS_FB_MAP"]


# --- nor do they pass a bare number to syscallN (#4145) ----------------------
# `syscall2(35, ...)  # SYS_NANOSLEEP` hides an x86_64 Linux number from the
# const check above just as well as a local `const SYS_NANOSLEEP` did.

NUMERIC_SYSCALL = re.compile(r"\b(?:__)?syscall[0-6]\(\s*[-+]?\d")


def _numeric_syscalls_beside_ritzlib_sys(files):
    """[path:line] for each syscallN(<number>, ...) in a file importing ritzlib.sys."""
    hits = []
    for path in files:
        src = path.read_text()
        if not IMPORTS_SYS.search(src):
            continue
        for n, line in enumerate(src.splitlines(), 1):
            if NUMERIC_SYSCALL.search(line.split("#", 1)[0]):
                hits.append(f"{path}:{n}")
    return hits


@pytest.mark.unit
def test_no_package_passes_a_bare_syscall_number_beside_ritzlib_sys():
    # ritzlib is where the numbers live; the kernel has its own enum Syscall.
    kernel = PROJECTS / "harland" / "kernel"
    files = [p for p in sorted(PROJECTS.rglob("*.ritz"))
             if RITZLIB not in p.parents and ARCHIVE not in p.parents
             and kernel not in p.parents]
    assert any(PROJECTS / "zeus" in p.parents for p in files)
    hits = _numeric_syscalls_beside_ritzlib_sys(files)
    assert not hits, "syscallN(<number>) beside `import ritzlib.sys`: " + repr(hits)


@pytest.mark.unit
def test_numeric_syscall_check_sees_a_literal(tmp_path):
    a = tmp_path / "a.ritz"
    a.write_text("import ritzlib.sys\n"
                 "fn f() -> i64\n"
                 "    syscall2(35, 0, 0)  # SYS_NANOSLEEP\n"      # flagged
                 "    syscall2(SYS_NANOSLEEP, 0, 0)\n"            # named: fine
                 "    # syscall6(9, 0, 0, 0, 0, 0, 0) in a comment\n"
                 "    syscall0( 39)\n")                           # flagged
    b = tmp_path / "b.ritz"   # freestanding: no ritzlib.sys
    b.write_text("fn f() -> i64\n    syscall1(60, 0)\n")
    hits = _numeric_syscalls_beside_ritzlib_sys([a, b])
    assert hits == [f"{a}:3", f"{a}:6"]
