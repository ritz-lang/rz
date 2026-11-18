#!/usr/bin/env python3
"""ritz0_scope.py -- can a change reach the "ritz0 unit tests" step? (AGAST #4027)

Aaron, 2026-11-18: "if we haven't made any changes to ritz0 code or things that
can affect it, we should skip the ritz0 tests. They take ages, and will only
break if we make changes to ritz0."

The step is the longest in every room and train gate.  It reads far more than
ritz0/: most test_ritz1_*.py files and every COMPILERS-parametrized row run
ritz1 and ritz1_selfhosted, compile ritzlib and runtime/, import build.py and
tools/, read main.yml (test_no_artifact_skips), every package manifest
(test_build_lib), and the packages and docs its tests open by path
(harland, indium, cryptosec, larb, zeus, tome, ritzunit, KERNEL_CONTRACT.md,
LANGUAGE_SPEC.md, ...).  Measured 2026-11-18 by grepping the suite for the paths
it opens; the scan below repeats that measurement on every call, so a test that
starts reading a package makes the package an input in the same commit.

So this is an ALLOWLIST that fails safe.  A gate skips the step only when every
changed path is in one of these categories:

  * a Markdown file whose basename no ritz0-step source names (the suite opens
    docs by name and never globs *.md; if a source ever does, every .md is an
    input);
  * a file MODIFIED (not added or deleted: those can change a build plan) in a
    package under projects/ that no ritz0-step source names by path, directly
    or through a named package's manifest, and that is not a manifest itself
    (test_build_lib reads every ritz.toml);
  * a file under an allowlisted top-level dir (TOP_DIRS) that no ritz0-step
    source names.

Everything else runs it: projects/ritz/**, .github/**, root files, an unknown
top-level dir, no base or a base git can't resolve, an empty diff, a git error.
CI on main passes no base, so main keeps running the step on every push.

"ritz0-step sources" are the tracked text files under projects/ritz except
docs/, tools/test_*.py (those run in the tools step, not this one) and this
file (it names what it allows; the step never runs it), plus
the manifests of the packages they name.

Known limit: a source that walks projects/ for something other than manifests
(say every *.ritz) would read an unnamed package without naming it.  None does
today; the file-set rule (A/D run) and main's CI are the backstops.

    python3 tools/ritz0_scope.py <base>      print the verdict; exit 0 = skip
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

STEP = "ritz0 unit tests"
RITZ = "projects/ritz/"

# Top-level dirs a change may live in without reaching the step, while no
# ritz0-step source names them.  Not a pattern: a new top-level dir is
# unknown, and unknown runs.
TOP_DIRS = (".claude", ".borque", "archive", "bench", "docs")

MANIFESTS = ("ritz.toml", "rz.toml")

# This file names what it allows; the step never runs it.
_SELF = Path(__file__).name

# What makes a source file part of the scan.
_SOURCE_SUFFIXES = {".py", ".sh", ".toml", ".ritz", ".yml", ".yaml", ".ll", ".txt", ".json"}
_SOURCE_NAMES = {"Makefile"}

# A source that reads Markdown by pattern rather than by name.
_MD_WILDCARD = re.compile(
    r"""\*\.md\b|\}\.md\b|suffix\s*[!=]=\s*['"]\.md|endswith\(\s*['"]\.md""")


def _named(name: str) -> re.Pattern[str]:
    """`name` as a path component: after a quote or slash, not mid-word."""
    return re.compile(r"""["'/]""" + re.escape(name) + r"(?![\w-])")


def _basename(name: str) -> re.Pattern[str]:
    return re.compile(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-])")


@dataclass
class Decision:
    skip: bool
    # lines[0] is the verdict; the rest say why, one changed path each.
    lines: list[str] = field(default_factory=list)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _sources(repo: Path) -> str:
    """The text of every ritz0-step source, concatenated."""
    out = _git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard",
               "--", "projects/ritz")
    texts = []
    for rel in out.split("\0"):
        if not rel:
            continue
        p = PurePosixPath(rel)
        sub = p.parts[2:]  # below projects/ritz
        if not sub or sub[0] == "docs":
            continue
        if sub[0] == "tools" and len(sub) == 2 and (
                p.name.startswith("test_") or p.name == _SELF):
            continue
        if p.suffix not in _SOURCE_SUFFIXES and p.name not in _SOURCE_NAMES:
            continue
        try:
            texts.append((repo / rel).read_text(errors="replace"))
        except OSError:
            continue  # deleted in the work tree: not read by anything
    return "\n".join(texts)


def _packages(repo: Path) -> list[str]:
    root = repo / "projects"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.name != "ritz")


def _package_manifests(repo: Path, pkg: str) -> str:
    texts = []
    for p in (repo / "projects" / pkg).rglob("*.toml"):
        if p.name in MANIFESTS and "build" not in p.parts:
            texts.append(p.read_text(errors="replace"))
    return "\n".join(texts)


def named_packages(repo: Path, sources: str | None = None) -> set[str]:
    """Packages under projects/ the ritz0 step reads: named by path in its
    sources, or by a named package's manifest (a dependency), to a fixpoint."""
    text = _sources(repo) if sources is None else sources
    pkgs = _packages(repo)
    named = {p for p in pkgs if _named(p).search(text)}
    frontier = set(named)
    while frontier:
        deps = "\n".join(_package_manifests(repo, p) for p in frontier)
        frontier = {p for p in pkgs if p not in named and _named(p).search(deps)}
        named |= frontier
    return named


def _changes(repo: Path, base: str) -> list[tuple[str, str]]:
    """(status, path) for every path that differs from `base` in the work
    tree: committed, uncommitted and untracked.  Renames are split into a
    delete and an add, so both sides are judged."""
    seen: dict[str, str] = {}
    out = _git(repo, "diff", "-z", "--name-status", "--no-renames", base)
    parts = [x for x in out.split("\0") if x]
    for status, path in zip(parts[0::2], parts[1::2]):
        seen[path] = status[0]
    out = _git(repo, "ls-files", "-z", "--others", "--exclude-standard")
    for path in out.split("\0"):
        if path:
            seen[path] = "A"
    return sorted((s, p) for p, s in seen.items())


def _why_safe(status: str, path: str, text: str, named: set[str],
              md_wild: bool) -> str | None:
    """Why `path` cannot reach the step, or None if it may (the default)."""
    p = PurePosixPath(path)
    if path.startswith(".github/"):
        return None
    if p.suffix == ".md":
        if md_wild:
            return None
        if _basename(p.name).search(text):
            return None
        return f"{p.name}: a .md no ritz0-step source names"
    if path.startswith(RITZ):
        return None
    top = p.parts[0]
    if top == "projects" and len(p.parts) >= 3:
        pkg = p.parts[1]
        if pkg in named or p.name in MANIFESTS or status != "M":
            return None
        return f"modified in projects/{pkg}/, which no ritz0-step source reads"
    if top in TOP_DIRS and len(p.parts) >= 2:
        if _named(top).search(text):
            return None
        return f"under {top}/, which no ritz0-step source names"
    return None


def inputs_summary(named: set[str]) -> str:
    pkgs = ",".join(sorted(named))
    return (f"{RITZ}, .github/, root files, every ritz.toml/rz.toml, "
            f"projects/{{{pkgs}}}/, .md files ritz0 sources name")


def decide(repo: Path, base: str | None) -> Decision:
    """Skip the step only if every change since `base` is measured safe."""
    if not base:
        return Decision(False, [f"running {STEP}: no diff base given"])
    try:
        sha = _git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").strip()
    except (subprocess.CalledProcessError, OSError) as e:
        return Decision(False, [f"running {STEP}: base {base!r} does not resolve ({e})"])
    try:
        changes = _changes(repo, sha)
        text = _sources(repo)
        named = named_packages(repo, text)
    except (subprocess.CalledProcessError, OSError) as e:
        why = f"could not diff against base {sha[:7]} ({e})"
        return Decision(False, [f"running {STEP}: {why}"])
    if not changes:
        why = f"nothing differs from base {sha[:7]} (a skip would prove nothing)"
        return Decision(False, [f"running {STEP}: {why}"])
    md_wild = bool(_MD_WILDCARD.search(text))
    why = [(s, p, _why_safe(s, p, text, named, md_wild)) for s, p in changes]
    reach = [(s, p) for s, p, w in why if w is None]
    if reach:
        s, p = reach[0]
        more = f" (and {len(reach) - 1} more)" if len(reach) > 1 else ""
        head = f"running {STEP}: {p} ({s}) may reach it{more} (base {sha[:7]})"
        return Decision(False, [head, *(f"  may reach it: {p} ({s})" for s, p in reach)])
    head = f"SKIPPED {STEP}: no change under {inputs_summary(named)} (base {sha[:7]})"
    return Decision(True, [head, *(f"  cannot reach it: {p} ({s}): {w}" for s, p, w in why)])


def main(argv: list[str]) -> int:
    repo = Path(__file__).resolve().parents[3]
    d = decide(repo, argv[1] if len(argv) > 1 else None)
    print("\n".join(d.lines))
    return 0 if d.skip else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
