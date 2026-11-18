"""No compiled binaries tracked at the projects/ritz/ root (AGAST #3296).

A room debugging `-> [N]T` drops (#3258) compiled a dozen scratch programs at
the project root, `foo.ritz` -> `foo.ritz0` / `foo.ritz1` /
`foo.ritz1_selfhosted`, and `git add -A` committed all ~45 of them. Older ELF
leftovers (hello_test, ritz1_bin, ritzgen_test) had sat there since the import.

Two guards, each with its own test:

1. `projects/ritz/.gitignore` ignores `/*.ritz0`, `/*.ritz1` and
   `/*.ritz1_selfhosted`, anchored to the root, so the same names one directory
   down (a fixture someone means to track) are NOT hidden.
2. No file tracked directly under projects/ritz/ is an ELF, whatever its
   name. This catches extensionless binaries that no ignore pattern could
   name ahead of time, and anything force-added past the ignore.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent
COMPILED_SUFFIXES = (".ritz0", ".ritz1", ".ritz1_selfhosted")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=RITZ_ROOT, capture_output=True, text=True, check=False
    )


def _ignored(rel: str) -> bool:
    """True if `rel` (relative to projects/ritz) would be ignored by git.

    --no-index evaluates the ignore rules even for tracked or absent paths,
    which is what "would a new file here be committed by `git add -A`" means.
    """
    r = _git("check-ignore", "-q", "--no-index", "--", rel)
    assert r.returncode in (0, 1), r.stderr
    return r.returncode == 0


@pytest.mark.integration
@pytest.mark.parametrize("suffix", COMPILED_SUFFIXES)
def test_compiled_output_at_project_root_is_ignored(suffix):
    assert _ignored(f"scratch{suffix}"), (
        f"projects/ritz/scratch{suffix} is not git-ignored; add "
        f"'/*{suffix}' to projects/ritz/.gitignore (#3296)"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    "rel",
    [
        "scratch.ritz",  # the source itself is not ignored
        "examples/scratch.ritz0",  # the rule is anchored to the root only
        "ritz0/test/scratch.ritz1",
        "lib/scratch.ritz1_selfhosted",
    ],
)
def test_root_rule_does_not_hide_other_files(rel):
    assert not _ignored(rel), (
        f"projects/ritz/{rel} is ignored; anchor the rule with '/'"
    )


@pytest.mark.integration
def test_no_elf_tracked_at_project_root():
    r = _git("ls-files", "-z", "--", ".")
    assert r.returncode == 0, r.stderr
    offenders = []
    for rel in filter(None, r.stdout.split("\0")):
        if "/" in rel:
            continue  # only the root itself
        path = RITZ_ROOT / rel
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as f:
                if f.read(4) == b"\x7fELF":
                    offenders.append(rel)
    assert not offenders, (
        "ELF binaries tracked at projects/ritz/ (git rm them; build output "
        f"does not belong at the project root, #3296): {offenders}"
    )


# --- Repo-wide hygiene (AGAST #1268) ----------------------------------------
#
# The same failure one level up: generated output tracked anywhere in the
# repository, not just at the projects/ritz/ root. #1268 found extensionless
# LLVM IR (out/test_json, examples/tier5_async/test_json_bin,
# ritz0/test_loop), build convenience links committed as symlinks into build/
# (projects/indium/cat, 54_async_fs/async_fs_test), and merge/editor leftovers
# (*.orig, *.old). Each check below walks `git ls-files` for the whole repo.

REPO_ROOT = RITZ_ROOT.parent.parent

# ELF files tracked on purpose (test fixtures). Empty today; add a path here,
# with a comment saying which test reads it, rather than weakening the check.
ELF_FIXTURES: frozenset[str] = frozenset()

# Compiler-emitted LLVM IR starts with this line (ritz0 and clang both write
# it). The hand-written runtime/*.ll start stubs do not, so they pass.
IR_MARKER = b"; ModuleID"

LEFTOVER_SUFFIXES = (".orig", ".old", ".rej")


def _tracked_by_mode() -> list[tuple[str, str]]:
    """(git mode, repo-relative path) for every tracked entry."""
    r = subprocess.run(
        ["git", "ls-files", "-s", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    out = []
    for entry in filter(None, r.stdout.split("\0")):
        meta, path = entry.split("\t", 1)
        out.append((meta.split()[0], path))
    return out


def _tracked_regular_files() -> list[str]:
    return [p for mode, p in _tracked_by_mode() if mode in ("100644", "100755")]


def _tracked_symlinks() -> list[str]:
    return [p for mode, p in _tracked_by_mode() if mode == "120000"]


def _head(rel: str, n: int) -> bytes:
    path = REPO_ROOT / rel
    if not path.is_file():
        return b""  # deleted in the working tree; git status shows it
    with path.open("rb") as f:
        return f.read(n)


@pytest.mark.integration
def test_no_elf_tracked_in_repo():
    offenders = [
        rel
        for rel in _tracked_regular_files()
        if rel not in ELF_FIXTURES and _head(rel, 4) == b"\x7fELF"
    ]
    assert not offenders, (
        "ELF binaries tracked in the repo (git rm --cached them and ignore "
        f"the output, or list a deliberate fixture in ELF_FIXTURES): {offenders}"
    )


def test_elf_fixtures_exist():
    # A stale allowlist entry would silently re-open the hole for that path.
    missing = [rel for rel in ELF_FIXTURES if _head(rel, 4) != b"\x7fELF"]
    assert not missing, f"ELF_FIXTURES entries that are not tracked ELF: {missing}"


@pytest.mark.integration
def test_no_merge_or_editor_leftovers_tracked():
    offenders = [
        rel for rel in _tracked_regular_files() if rel.endswith(LEFTOVER_SUFFIXES)
    ]
    assert not offenders, f"leftover {LEFTOVER_SUFFIXES} files tracked: {offenders}"


@pytest.mark.integration
def test_no_compiler_output_ir_tracked():
    """Tracked compiler-emitted LLVM IR, whatever its name, is build output."""
    offenders = [
        rel for rel in _tracked_regular_files() if IR_MARKER in _head(rel, 256)
    ]
    assert not offenders, f"LLVM IR (compiler output) tracked; git rm it: {offenders}"


@pytest.mark.integration
def test_walk_reads_tracked_files():
    # Guard the walk: if listing or reading broke, the content checks above
    # would pass vacuously. The sample is the build driver itself: a source
    # file no cleanup can delete (the runtime shim used here first was
    # removed by #3913).
    sample = "projects/ritz/build.py"
    assert sample in _tracked_regular_files()
    assert _head(sample, 2) == b"#!"


@pytest.mark.integration
def test_no_tracked_symlink_into_a_build_dir():
    """build.py's convenience links point into build/; they dangle on a clone."""
    offenders = []
    for rel in _tracked_symlinks():
        target = os.readlink(REPO_ROOT / rel) if (REPO_ROOT / rel).is_symlink() else ""
        if "build" in Path(target).parts:
            offenders.append(f"{rel} -> {target}")
    assert not offenders, (
        "symlinks into build/ are tracked (git rm --cached them and add the "
        f"link path to .gitignore): {offenders}"
    )


def _repo_ignored(rel: str) -> bool:
    r = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", "--", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode in (0, 1), r.stderr
    return r.returncode == 0


@pytest.mark.integration
@pytest.mark.parametrize(
    "rel",
    [
        "projects/iris/build/debug/main_0123abcd.ll",
        "projects/spire/build/release/spire",
        "projects/ritz/examples/tier1_basics/01_hello/build/debug/hello",
        ".claude/worktrees/rz-task-1/README.md",
        ".ritz-cache-ritz1/obj",
        "projects/ritz/.ritz-cache-ritz1/obj",
        "projects/sage/.ritz-cache/obj",
        "tmpabc123/out",
        "projects/indium/cat",
        "projects/ritz/examples/tier5_async/54_async_fs/async_fs_test",
    ],
)
def test_build_output_is_ignored(rel):
    assert _repo_ignored(rel), f"{rel} is not git-ignored (#1268)"
