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
(harland, indium, cryptosec, larb, zeus, ritzunit, KERNEL_CONTRACT.md,
LANGUAGE_SPEC.md, ...).

Measured 2026-11-18 (AGAST #4032): strace -f over a full run, attributed per
test with an audit hook.  The step opened a non-manifest file in 9 packages
(cryptosec harland indium iris larb prism ritzunit spire zeus); every other
package only through its manifest and a directory listing, plus one lint that
read every package's *.ritz (moved to tools/test_package_syscall_numbers.py).
The text scan below named all 24, mostly from comments, docstrings and
tools/smoke_stack, so a package-only change never skipped.

So this is an ALLOWLIST that fails safe.  A gate skips the step only when every
changed path is in one of these categories:

  * a Markdown file whose basename no ritz0-step source names (the suite opens
    docs by name and never globs *.md; if a source ever does, every .md is an
    input);
  * a file MODIFIED (not added or deleted: those can change a build plan, and
    the step lists every package's directories) in a package under projects/
    that no ritz0-step source names, directly or through a named package's
    manifest, and that is not a manifest itself (test_build_lib reads every
    ritz.toml);
  * a file under an allowlisted top-level dir (TOP_DIRS) that no ritz0-step
    source names.

Everything else runs it: projects/ritz/**, .github/**, root files, an unknown
top-level dir, no base or a base git can't resolve, an empty diff, a git error.
CI on main passes no base, so main keeps running the step on every push.

"ritz0-step sources" are the tracked text files under projects/ritz except
docs/, tools/smoke_stack/ (the smoke step runs it), tools/test_*.py (those run
in the tools step, not this one) and this file (it names what it allows; the
step never runs it), plus the manifests of the packages they name.  A source
names a package by a path to it ("pkg", /pkg, pkg/...) or a Ritz import of it
(`import pkg.x`, also inside a Python string holding a program).  Comments
and docstrings don't name anything: in Python only string literals that are
not docstrings are scanned (tokenize; a file that won't tokenize is scanned
whole), in the other formats a line starting with `#` is dropped.

The scan is checked, not trusted: ritz0/read_guard.py fails any ritz0 test
that opens, or hands a process, a file this module would let a gate skip.  CI
on main runs the whole step, so a test that starts reading an unnamed package
fails there on its first push.  What neither sees: a child process (ritz1,
build.py) reading a package it was not handed by path, through RITZ_PATH.
The scan's import rule covers that for programs in the step's own sources.

    python3 tools/ritz0_scope.py <base>      print the verdict; exit 0 = skip
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
import tokenize
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
# Formats whose comments are whole lines starting with `#` (AGAST #4032).
_HASH_COMMENTS = {".sh", ".toml", ".ritz", ".yml", ".yaml", ".txt"}
_HASH_LINE = re.compile(r"^[ \t]*#.*$", re.M)

# Under projects/ritz but never run by the step (AGAST #4032): the smoke
# step runs the stack; ritz0's tests only lint its text.
_NOT_RUN = ("tools/smoke_stack/",)

# A source that reads Markdown by pattern rather than by name.
_MD_WILDCARD = re.compile(
    r"""\*\.md\b|\}\.md\b|suffix\s*[!=]=\s*['"]\.md|endswith\(\s*['"]\.md""")
# A Markdown basename a source mentions ends here; _md_names reads back to
# its start (a leading [\w.-]+ class would cost the literal scan: ~1.3 s).
_MD_END = re.compile(r"\.md(?![\w-])")
_MD_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")


def _md_names(text: str) -> set[str]:
    """Every *.md basename in `text`, as a whole word: the name the suite
    would open it by."""
    names = set()
    for m in _MD_END.finditer(text):
        i = m.start()
        while i > 0 and (text[i - 1] in _MD_CHARS or text[i - 1].isalnum()):
            i -= 1
        if i < m.start():
            names.add(text[i:m.end()])
    return names


def _named(name: str) -> re.Pattern[str]:
    """`name` as a path component: after a quote or slash, not mid-word."""
    return re.compile(r"""["'/]""" + re.escape(name) + r"(?![\w-])")


def _refs(names) -> tuple[re.Pattern[str], ...]:
    """Any of `names` as a path: a whole string or a string's first component
    ("pkg", "pkg/src"; not "pkg --help"), or after a slash (/pkg, $ROOT/pkg:);
    or as the root of a Ritz import (`import pkg.x`).  Separate patterns, so
    each starts on a literal the regex engine can scan for quickly."""
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return (re.compile(rf"""["']({alt})(?=["'/])"""),
            re.compile(rf"/({alt})(?![\w-]|:/)"),
            # No leading \b: it would cost the literal scan; "reimport x"
            # naming x errs toward running.
            re.compile(rf"import[ \t]+({alt})(?![\w-])"))


def _found(refs, text: str) -> set[str]:
    return {n for r in refs for n in r.findall(text)}


@dataclass
class Decision:
    skip: bool
    # lines[0] is the verdict; the rest say why, one changed path each.
    lines: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Scope:
    """What the ritz0 step's sources reach: everything why_safe needs, so a
    caller (ritz0/read_guard.py) computes it once."""
    named: frozenset[str]       # packages under projects/ the step reads
    md_wild: bool               # a source reads *.md by pattern
    md_names: frozenset[str]    # .md basenames sources mention
    named_tops: frozenset[str]  # TOP_DIRS sources name


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def _source_files(repo: Path) -> list[tuple[str, str]]:
    """(path, text) of every ritz0-step source."""
    out = _git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard",
               "--", "projects/ritz")
    files = []
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
        if any("/".join(sub).startswith(d) for d in _NOT_RUN):
            continue
        if p.suffix not in _SOURCE_SUFFIXES and p.name not in _SOURCE_NAMES:
            continue
        try:
            files.append((rel, (repo / rel).read_text(errors="replace")))
        except OSError:
            continue  # deleted in the work tree: not read by anything
    return files


def _sources(repo: Path) -> str:
    """The text of every ritz0-step source, concatenated."""
    return "\n".join(t for _, t in _source_files(repo))


def _py_strings(text: str) -> str:
    """The string literals of Python `text`, less docstrings and other bare
    string statements: the only place a path or an embedded Ritz import can
    be.  Comments go too.  Text that won't tokenize is returned whole."""
    out = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError, ValueError):
        return text
    skip = {tokenize.NL, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT}
    stmt_start = True  # the next significant token begins a statement
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.type in skip:
            i += 1
            continue
        if t.type == tokenize.STRING and stmt_start:
            # A statement of only strings (a docstring, implicitly joined or
            # not) has no effect: drop it.
            j = i
            while j < len(toks) and toks[j].type in (tokenize.STRING, tokenize.NL,
                                                     tokenize.COMMENT):
                j += 1
            if j >= len(toks) or toks[j].type in (tokenize.NEWLINE, tokenize.ENDMARKER) \
                    or toks[j].string == ";":
                i = j
                continue
        if t.type == tokenize.STRING:
            out.append(t.string)
        elif t.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            out.append(t.string)
        stmt_start = t.type == tokenize.NEWLINE or t.string == ";" or (
            t.type == tokenize.OP and t.string == ":" and _ends_line(toks, i))
        i += 1
    return "\n".join(out)


def _ends_line(toks, i: int) -> bool:
    """A `:` closing a compound statement's header (`def f():`), so what
    follows on the next line begins a statement."""
    j = i + 1
    while j < len(toks) and toks[j].type == tokenize.COMMENT:
        j += 1
    return j < len(toks) and toks[j].type in (tokenize.NEWLINE, tokenize.NL)


def _code(rel: str, text: str) -> str:
    """The part of a source that can make the step read something."""
    suffix = PurePosixPath(rel).suffix
    if suffix == ".py":
        return _py_strings(text)
    if suffix in _HASH_COMMENTS or PurePosixPath(rel).name in _SOURCE_NAMES:
        return _HASH_LINE.sub("", text)
    return text


def _packages(repo: Path) -> list[str]:
    root = repo / "projects"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.name != "ritz")


def _package_manifests(repo: Path, pkg: str) -> str:
    texts = []
    for p in (repo / "projects" / pkg).rglob("*.toml"):
        if p.name in MANIFESTS and "build" not in p.parts:
            texts.append(_HASH_LINE.sub("", p.read_text(errors="replace")))
    return "\n".join(texts)


def _direct(files, pkgs) -> set[str]:
    """Packages the sources name.  The raw text is searched first (cheap); a
    file is reduced to its code only when that would name something new."""
    refs = _refs(pkgs) if pkgs else None
    named: set[str] = set()
    if refs is None:
        return named
    for rel, text in files:
        if _found(refs, text) - named:
            named |= _found(refs, _code(rel, text))
    return named


def named_packages(repo: Path, files=None) -> set[str]:
    """Packages under projects/ the ritz0 step reads: named in its sources,
    or by a named package's manifest (a dependency), to a fixpoint."""
    files = _source_files(repo) if files is None else files
    pkgs = _packages(repo)
    named = _direct(files, pkgs)
    frontier = set(named)
    while frontier:
        deps = "\n".join(_package_manifests(repo, p) for p in frontier)
        frontier = {p for p in pkgs if p not in named and _named(p).search(deps)}
        named |= frontier
    return named


def scope(repo: Path, files=None) -> Scope:
    """Measure what the step's sources reach, once."""
    files = _source_files(repo) if files is None else files
    raw = "\n".join(t for _, t in files)
    tops = re.compile(r"""["'/](?:""" + "|".join(re.escape(t) for t in TOP_DIRS)
                      + r")(?![\w-])")
    code = "\n".join(_code(r, t) for r, t in files if tops.search(t))
    return Scope(
        named=frozenset(named_packages(repo, files)),
        md_wild=bool(_MD_WILDCARD.search(raw)),
        md_names=frozenset(_md_names(raw)),
        named_tops=frozenset(t for t in TOP_DIRS if _named(t).search(code)),
    )


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


def why_safe(status: str, path: str, sc: Scope) -> str | None:
    """Why a change (`status` A/M/D) to repo-relative `path` cannot reach the
    step, or None if it may (the default)."""
    p = PurePosixPath(path)
    if path.startswith(".github/"):
        return None
    if p.suffix == ".md":
        if sc.md_wild or p.name in sc.md_names:
            return None
        return f"{p.name}: a .md no ritz0-step source names"
    if path.startswith(RITZ):
        return None
    top = p.parts[0]
    if top == "projects" and len(p.parts) >= 3:
        pkg = p.parts[1]
        if pkg in sc.named or p.name in MANIFESTS or status != "M":
            return None
        return f"modified in projects/{pkg}/, which no ritz0-step source reads"
    if top in TOP_DIRS and len(p.parts) >= 2:
        if top in sc.named_tops:
            return None
        return f"under {top}/, which no ritz0-step source names"
    return None


def inputs_summary(named) -> str:
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
        sc = scope(repo)
    except (subprocess.CalledProcessError, OSError) as e:
        why = f"could not diff against base {sha[:7]} ({e})"
        return Decision(False, [f"running {STEP}: {why}"])
    if not changes:
        why = f"nothing differs from base {sha[:7]} (a skip would prove nothing)"
        return Decision(False, [f"running {STEP}: {why}"])
    why = [(s, p, why_safe(s, p, sc)) for s, p in changes]
    reach = [(s, p) for s, p, w in why if w is None]
    if reach:
        s, p = reach[0]
        more = f" (and {len(reach) - 1} more)" if len(reach) > 1 else ""
        head = f"running {STEP}: {p} ({s}) may reach it{more} (base {sha[:7]})"
        return Decision(False, [head, *(f"  may reach it: {p} ({s})" for s, p in reach)])
    head = f"SKIPPED {STEP}: no change under {inputs_summary(sc.named)} (base {sha[:7]})"
    return Decision(True, [head, *(f"  cannot reach it: {p} ({s}): {w}" for s, p, w in why)])


def main(argv: list[str]) -> int:
    repo = Path(__file__).resolve().parents[3]
    d = decide(repo, argv[1] if len(argv) > 1 else None)
    print("\n".join(d.lines))
    return 0 if d.skip else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
