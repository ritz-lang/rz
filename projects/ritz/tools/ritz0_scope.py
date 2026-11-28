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

  * a Markdown file outside projects/ritz whose basename no ritz0-step source
    names (the suite opens docs by name and never globs *.md; if a source
    ever does, every .md is an input; under projects/ritz every file is an
    input, .md too: two tests copy the tree, AGAST #4206);
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
in the tools step, not this one) and this file (it names what it allows, so
its text is never taken as a step naming anything), plus the manifests of the
packages they name.  A source
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

Two more gate steps are scoped by the same rules (AGAST #4206), each with a
measured read set inside projects/ritz rather than all of it (Step, HARNESS,
REGRESSION below): "Regression harness self-tests" (~78 s) and
"Differential corpus regression" (~90 s).  A change under projects/ritz
outside a step's `reads` skips that step, unless it is a manifest or adds or
deletes an entry of a directory the step lists; everything outside
projects/ritz is judged as above, with the names the step's own files use.
They run ritz1, clang and make, which an audit hook cannot see into, so their
read sets are checked by a trace instead (`--audit`, below), and the tests
re-derive what the scripts name and what their Python imports.

    python3 tools/ritz0_scope.py <base>      print the verdict; exit 0 = skip
    python3 tools/ritz0_scope.py <base> --all            every scoped step's
    python3 tools/ritz0_scope.py --audit STEP TRACE      exit 0 = covered
    python3 tools/ritz0_scope.py --trace STEP -- CMD...  run CMD under strace,
                         audit as it streams; exit 0 = passed and covered (CI)
"""

from __future__ import annotations

import fnmatch
import io
import os
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


@dataclass(frozen=True)
class Step:
    """A gate step and the part of projects/ritz it reads (AGAST #4206).

    `reads` None: all of projects/ritz (the ritz0 step).  Otherwise
    repo-relative paths, measured: a trailing / is a directory and all below
    it.  `excludes`: fnmatch patterns (`*` crosses `/`) of files under
    `reads` the step never opens (ritz0's tests: the compiler hash skips
    them too).  `lists`: directories whose listing the step reads (a glob, `find`,
    Python's import finder on sys.path[0]); adding or deleting an entry in
    one runs the step.  Outside projects/ritz every step is judged alike,
    with the packages, top-level dirs and .md names its own sources name."""
    name: str
    reads: tuple[str, ...] | None = None
    lists: tuple[str, ...] = ()
    label: str = "ritz0-step"  # "no <label> source names it"
    excludes: tuple[str, ...] = ()

    def in_reads(self, path: str) -> bool:
        """`path` is, or is under, something the step reads (a directory it
        reads counts too: a script names it as $ROOT_DIR/examples)."""
        if self.reads is None or path in self.reads:
            return True  # a file named outright beats `excludes`
        return any(path == r.rstrip("/") or (r.endswith("/") and path.startswith(r))
                   for r in self.reads) and \
            not any(fnmatch.fnmatchcase(path, x) for x in self.excludes)

    def listed_entries(self, path: str) -> list[str]:
        """The entry of each listed directory that `path` is or is under."""
        return [d + "/" + path[len(d) + 1:].split("/")[0]
                for d in self.lists if path.startswith(d + "/")]


RITZ0 = Step(STEP)

# Measured 2026-11-19 (AGAST #4206): `strace -f -y -e trace=%file,execve`
# over a full `make harness-selftest` (13 scripts, exit 0), every repo path
# opened, stat'd, probed, listed or exec'd, less what git ignores.  Its
# scripts point ROOT_DIR at scratch trees; the real tree is read only
# through SCRIPT_DIR (scripts/), RITZ_ROOT/examples (test-regression-ports,
# -testscripts) and the root known-failures/ (an unknown top-level dir:
# always an input).  Python lists tools/ (known_failures.py's sys.path[0])
# and projects/ritz/.
#
# Re-measured 2026-11-20 (AGAST #4380), same recipe: the baseline-cache
# self-test loads cache.py, whose compiler hash imports ritz0/'s
# compiler_identity to fingerprint ritz0.  It opens
# ritz0/compiler_identity.py and the import finder lists ritz0/ (it is
# sys.path[0] for that import).  Both are required: a change to either can
# change the key the self-test computes, so the harness declares them
# rather than skipping.  #3915 moved the harness out of the package and
# introduced the import, which the first measurement predated.
#
# Re-measured 2026-11-22 (AGAST #4541, #4552), same recipe: the reject-parity
# self-test runs pytest on ritz0/tests/test_reject_parity.py, which loads
# ritz0/conftest.py and the plugins it names (spawn_guard, cost_meter,
# only_files, read_guard; read_guard imports tools/ritz0_scope.py), the five
# corpus tables the test imports, and lists ritz0/tests, ritz0/harness and
# every top-level directory it walks looking for the test (adding a
# pyvenv.cfg/conda-meta marker or an __init__.py changes what it collects or
# ignores).  Only those pytest inputs are reads: modifying any other test
# file still skips the harness.
HARNESS = Step(
    "Regression harness self-tests",
    reads=("projects/ritz/scripts/",
           "projects/ritz/examples/",
           "projects/ritz/Makefile",
           "projects/ritz/cache.py",
           # conftest.py loads cas.py by file location (AGAST #4676).
           "projects/ritz/cas.py",
           "projects/ritz/tools/known_failures.py",
           "projects/ritz/tools/ritz0_scope.py",
           "projects/ritz/ritz0/compiler_identity.py",
           "projects/ritz/ritz0/conftest.py",
           "projects/ritz/ritz0/cost_meter.py",
           "projects/ritz/ritz0/only_files.py",
           "projects/ritz/ritz0/read_guard.py",
           "projects/ritz/ritz0/harness/batching.py",
           "projects/ritz/ritz0/harness/fast_link.py",
           # spawn_guard's allowlist, read by conftest.py (#4627, #4676).
           "projects/ritz/ritz0/harness/integration_without_spawn.txt",
           "projects/ritz/ritz0/harness/ritz0_inproc.py",
           "projects/ritz/ritz0/harness/refusal_capture.py",
           "projects/ritz/ritz0/harness/spawn_guard.py",
           "projects/ritz/ritz0/tests/test_reject_parity.py",
           "projects/ritz/ritz0/tests/test_if_expression_requires_else.py",
           "projects/ritz/ritz0/tests/test_implicit_narrowing.py",
           # Loaded by test_reject_parity.py since #4932/#4933/#4936.
           "projects/ritz/ritz0/tests/test_implicit_narrowing_slots.py",
           "projects/ritz/ritz0/tests/test_ritz1_const_array_fold.py",
           "projects/ritz/ritz0/tests/test_unannotated_mixed_float_arms.py"),
    lists=("projects/ritz", "projects/ritz/tools", "projects/ritz/ritz0",
           "projects/ritz/ritz0/tests", "projects/ritz/ritz0/harness",
           "projects/ritz/ritz0/emitter", "projects/ritz/ritz0/test",
           "projects/ritz/benchmarks", "projects/ritz/docs",
           "projects/ritz/grammars", "projects/ritz/ritz1",
           "projects/ritz/ritzlib", "projects/ritz/runtime",
           "projects/ritz/test"),
    label="harness-step")

# Measured 2026-11-19 (AGAST #4206), as HARNESS, over a cold
# `scripts/regression.sh --no-baseline-cache` with RITZ_VERIFY_IR=1 (CI's).
# Its binaries were built by the step before it ("Build ritz1 +
# ritz1_selfhosted"), so their sources are inputs too: Stage 2/4's make stats
# them (the %file trace sees it), and a change to them changes what the
# binaries accept.
REGRESSION = Step(
    "Differential corpus regression (ritz0 vs ritz1 vs self-hosted)",
    reads=("projects/ritz/ritz0/",
           "projects/ritz/ritz0/test_runner.py",
           "projects/ritz/ritz1/",
           "projects/ritz/ritzlib/",
           "projects/ritz/runtime/",
           "projects/ritz/examples/",
           "projects/ritz/scripts/",
           "projects/ritz/tools/known_failures.py",
           "projects/ritz/Makefile",
           "projects/ritz/build.py",
           "projects/ritz/build_pipeline.py",
           "projects/ritz/producers.py",
           "projects/ritz/build_testrun.py",
           "projects/ritz/build_cli.py",
           "projects/ritz/manifest.py",
           "projects/ritz/bounded_run.py",
           "projects/ritz/cache.py",
           "projects/ritz/cas.py",
           "projects/ritz/packages.py",
           "projects/ritz/resolve.py"),
    # Never opened (the trace): ritz0's tests (the compiler hash follows the
    # compiler's imports, which reach no test), ritzlib/tests, the Markdown.
    # ritz0.py imports test_runner.py (its --test mode): not a test.
    excludes=("projects/ritz/ritz0/test_*", "projects/ritz/ritz0/tests/*",
              "projects/ritz/ritz0/*/test_*",
              "projects/ritz/ritz0/test/*", "projects/ritz/ritz0/*/test/*",
              "projects/ritz/ritzlib/tests/*",
              "projects/ritz/ritz0/*.md", "projects/ritz/ritz1/*.md",
              "projects/ritz/ritzlib/*.md", "projects/ritz/runtime/*.md"),
    # Re-measured 2026-11-20 (AGAST #4385) and 2026-11-21 (#4482), same
    # recipe: every build.py run folds cache.py's ritz0 hash in, which
    # imports ritz0/compiler_identity.py.  Its resolver walks ritz0/ once
    # (os.walk) rather than stat'ing a candidate per module, so it lists
    # every directory under ritz0/; for the excluded test trees that means
    # ritz0/test and, after #4373 moved the Python tests, ritz0/tests.
    # Adding or removing an entry there changes that walk.  The listings are
    # declared, not the subtrees read: the test files are still never
    # opened, so `excludes` keeps a modification a skip.
    lists=("projects/ritz", "projects/ritz/tools",
           "projects/ritz/ritz0/test", "projects/ritz/ritz0/tests"),
    label="regression-step")

# Every step a gate may scope, in no particular order; RITZ0 first.
STEPS = (RITZ0, HARNESS, REGRESSION)


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


def step_files(repo: Path, step: Step = RITZ0) -> list[str]:
    """Every tracked (or untracked, not ignored) file `step` reads under
    projects/ritz: for the ritz0 step, its sources (below)."""
    out = _git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard",
               "--", "projects/ritz")
    files = []
    for rel in out.split("\0"):
        if not rel:
            continue
        if step.reads is not None:
            if step.in_reads(rel):
                files.append(rel)
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
        files.append(rel)
    return sorted(set(files))


def _source_files(repo: Path, step: Step = RITZ0) -> list[tuple[str, str]]:
    """(path, text) of every source of `step`: the files it reads that can
    name a path (code, scripts, manifests, data; not Markdown)."""
    files = []
    for rel in step_files(repo, step):
        p = PurePosixPath(rel)
        if p.name == _SELF:
            # This tool's literals are the allowlist itself (TOP_DIRS names
            # `.claude`, ...).  Reading it must not turn those constants into
            # the step naming every path they enumerate (AGAST #4552).
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


def named_packages(repo: Path, files=None, step: Step = RITZ0) -> set[str]:
    """Packages under projects/ `step` reads: named in its sources, or by a
    named package's manifest (a dependency), to a fixpoint."""
    files = _source_files(repo, step) if files is None else files
    pkgs = _packages(repo)
    named = _direct(files, pkgs)
    frontier = set(named)
    while frontier:
        deps = "\n".join(_package_manifests(repo, p) for p in frontier)
        frontier = {p for p in pkgs if p not in named and _named(p).search(deps)}
        named |= frontier
    return named


def scope(repo: Path, files=None, step: Step = RITZ0) -> Scope:
    """Measure what `step`'s sources reach, once."""
    files = _source_files(repo, step) if files is None else files
    raw = "\n".join(t for _, t in files)
    tops = re.compile(r"""["'/](?:""" + "|".join(re.escape(t) for t in TOP_DIRS)
                      + r")(?![\w-])")
    code = "\n".join(_code(r, t) for r, t in files if tops.search(t))
    return Scope(
        named=frozenset(named_packages(repo, files, step)),
        # On code, not prose (AGAST #4206): read_guard.py's docstring says
        # "*.md", and every .md was an input of the ritz0 step.  Raw text
        # first: only a file that may match is reduced.
        md_wild=any(_MD_WILDCARD.search(_code(r, t)) for r, t in files
                    if _MD_WILDCARD.search(t)),
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


def _listing_changes(repo: Path, base: str, step: Step) -> frozenset[str]:
    """Entries of `step`'s listed directories added or removed since `base`
    (in the work tree, as `os.listdir` would see them)."""
    out: set[str] = set()
    for d in step.lists:
        then = {x.rsplit("/", 1)[-1] for x in
                _git(repo, "ls-tree", "-z", "--name-only", base, "--", d + "/").split("\0") if x}
        try:
            now = set(os.listdir(repo / d))
        except OSError:
            now = set()
        out |= {f"{d}/{x}" for x in then ^ now}
    return frozenset(out)


def why_safe(status: str, path: str, sc: Scope, step: Step = RITZ0,
             listing: frozenset[str] | None = None) -> str | None:
    """Why a change (`status` A/M/D) to repo-relative `path` cannot reach
    `step`, or None if it may (the default).  `listing`: the entries of the
    step's listed directories that changed (None: unknown, so an add or
    delete under one may reach it)."""
    p = PurePosixPath(path)
    if path.startswith(".github/"):
        return None
    if step.reads is not None and path.startswith(RITZ):
        if step.in_reads(path) or p.name in MANIFESTS:
            return None
        entries = step.listed_entries(path)
        if status != "M" and entries and (
                listing is None or any(e in listing for e in entries)):
            return None
        return f"not in the {step.label}'s measured read set"
    if step.reads is None and path.startswith(RITZ):
        # Every file under projects/ritz, Markdown too: ritz0 tests copy the
        # tree (test_ritz1_bin_staleness, test_fn_cache_ritz0_identity), and
        # read_guard saw them open every .md there (AGAST #4206).
        return None
    if p.suffix == ".md":
        if sc.md_wild or p.name in sc.md_names:
            return None
        return f"{p.name}: a .md no {step.label} source names"
    top = p.parts[0]
    if top == "projects" and len(p.parts) >= 3:
        pkg = p.parts[1]
        if pkg in sc.named or p.name in MANIFESTS or status != "M":
            return None
        return f"modified in projects/{pkg}/, which no {step.label} source reads"
    if top in TOP_DIRS and len(p.parts) >= 2:
        if top in sc.named_tops:
            return None
        return f"under {top}/, which no {step.label} source names"
    return None


def inputs_summary(named, step: Step = RITZ0) -> str:
    pkgs = ",".join(sorted(named))
    reads = RITZ if step.reads is None else ", ".join(step.reads)
    return (f"{reads}, .github/, root files, every ritz.toml/rz.toml, "
            f"projects/{{{pkgs}}}/, .md files {step.label} sources name")


def decide_steps(repo: Path, base: str | None, steps=STEPS) -> dict[str, Decision]:
    """Each step's verdict on one diff: skip a step only if every change
    since `base` is measured safe for it."""
    def every(line: str) -> dict[str, Decision]:
        return {s.name: Decision(False, [f"running {s.name}: {line}"]) for s in steps}

    if not base:
        return every("no diff base given")
    try:
        sha = _git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").strip()
    except (subprocess.CalledProcessError, OSError) as e:
        return every(f"base {base!r} does not resolve ({e})")
    try:
        changes = _changes(repo, sha)
    except (subprocess.CalledProcessError, OSError) as e:
        return every(f"could not diff against base {sha[:7]} ({e})")
    if not changes:
        return every(f"nothing differs from base {sha[:7]} (a skip would prove nothing)")
    out = {}
    for step in steps:
        try:
            sc = scope(repo, step=step)
            listing = _listing_changes(repo, sha, step)
        except (subprocess.CalledProcessError, OSError) as e:
            why = f"running {step.name}: could not measure its scope ({e})"
            out[step.name] = Decision(False, [why])
            continue
        out[step.name] = _verdict(step, sha, changes, sc, listing)
    return out


def _verdict(step: Step, sha: str, changes, sc: Scope, listing) -> Decision:
    why = [(s, p, why_safe(s, p, sc, step, listing)) for s, p in changes]
    reach = [(s, p) for s, p, w in why if w is None]
    name = step.name
    if reach:
        s, p = reach[0]
        more = f" (and {len(reach) - 1} more)" if len(reach) > 1 else ""
        head = f"running {name}: {p} ({s}) may reach it{more} (base {sha[:7]})"
        return Decision(False, [head, *(f"  may reach it: {p} ({s})" for s, p in reach)])
    head = (f"SKIPPED {name}: no change under {inputs_summary(sc.named, step)} "
            f"(base {sha[:7]})")
    return Decision(True, [head, *(f"  cannot reach it: {p} ({s}): {w}" for s, p, w in why)])


def decide(repo: Path, base: str | None, step: Step = RITZ0) -> Decision:
    """Skip `step` only if every change since `base` is measured safe."""
    return decide_steps(repo, base, (step,))[step.name]


# --------------------------------------------------------------------------
# The read set's guard (AGAST #4206).  Both measured steps run binaries
# (ritz1, clang, make), which an in-process audit hook cannot see into, so
# the check is a trace of the whole step:
#
#   cd projects/ritz
#   strace -f -qq -y -s 512 -e trace=%file,execve -o /tmp/h.strace make harness-selftest
#   python3 tools/ritz0_scope.py --audit "Regression harness self-tests" /tmp/h.strace
#
#   strace -f -qq -y -s 512 -e trace=%file,execve -o /tmp/r.strace \
#       env RITZ_VERIFY_IR=1 ./scripts/regression.sh --no-baseline-cache
#   python3 tools/ritz0_scope.py --audit "Differential corpus regression \
#       (ritz0 vs ritz1 vs self-hosted)" /tmp/r.strace
#
# It names every repo path the step opened, stat'd or exec'd (a change to it
# must run the step), probed and did not find, or listed (adding one there
# must run it), that the read set would let a gate skip.  Git-ignored paths
# are outputs.  Exit 0: the read set covers the trace.  `--trace` (below)
# does both in one go and stores nothing; CI runs it (AGAST #4315).
# --------------------------------------------------------------------------

_TRACE = re.compile(
    r'^\s*(?:\[pid\s+)?(\d+)\]?\s+(\w+)\((?:(AT_FDCWD|-?\d+)(?:<([^>]*)>)?,\s*)?"((?:[^"\\]|\\.)*)"(.*)$')
_RESUMED = re.compile(r'^\s*(?:\[pid\s+)?(\d+)\]?\s+<\.\.\. (\w+) resumed>(.*)$')
_OPENS = {"open", "openat", "openat2"}
_EXECS = {"execve", "execveat"}
_STATS = {"stat", "lstat", "newfstatat", "fstatat64", "statx", "access", "faccessat",
          "faccessat2", "readlink", "readlinkat", "stat64", "lstat64"}
_WRITE_FLAGS = re.compile(r"O_WRONLY|O_RDWR|O_CREAT|O_TRUNC")


def _trace_accesses(lines, roots: tuple[str, ...]):
    """(kind, rel) for each repo path in an strace log (`-f -y`, so a
    relative path's directory is decoded).  kind: "read" (opened or exec'd:
    its content), "stat" (found by stat/access: its existence and type),
    "probe" (not found) or "list" (a directory opened: its entries).  A call
    strace split into `<unfinished ...>` and `<... resumed>` is judged by its
    result.  Opens for writing are outputs, not reads."""
    cwd: dict[str, str] = {}
    pending: dict[str, tuple[str, str, str]] = {}
    for line in lines.splitlines() if isinstance(lines, str) else lines:
        m = _RESUMED.match(line)
        if m:
            got = pending.pop(m.group(1), None)
            if got is not None and got[0] == m.group(2):
                kind = _kind(got[0], got[2] + m.group(3))
                if kind:
                    yield kind, got[1]
            continue
        m = _TRACE.match(line)
        if not m:
            continue
        pid, call, dirfd, base, path, rest = m.groups()
        if dirfd == "AT_FDCWD" and base:
            cwd[pid] = base
        if call not in _OPENS and call not in _EXECS and call not in _STATS:
            continue
        if not path.startswith("/"):
            anchor = base or cwd.get(pid)
            if anchor is None:
                continue
            path = os.path.join(anchor, path)
        full = os.path.normpath(path)
        rel = next((full[len(r) + 1:] for r in roots if full.startswith(r + "/")), None)
        if not rel:
            continue
        if rest.rstrip().endswith("<unfinished ...>"):
            pending[pid] = (call, rel, rest)
            continue
        kind = _kind(call, rest)
        if kind:
            yield kind, rel


def _kind(call: str, rest: str) -> str | None:
    args, _, result = rest.rpartition("=")
    if call in _OPENS and _WRITE_FLAGS.search(args) and "O_RDONLY" not in args:
        return None  # an output
    if re.match(r"\s*-1 ENOTDIR\b", result):
        # A prefix of the path is a regular file, so the path itself cannot
        # exist: adding it would mean replacing that file with a directory.
        # A change to the file is already judged on its own (if it is in the
        # read set) or is an output, so the probe reads nothing.  pytest does
        # this for every path it collects: `<file>/pyvenv.cfg` and
        # `<file>/conda-meta/history` (AGAST #4552).
        return None
    if re.match(r"\s*-1 ENOENT\b", result):
        return "probe"
    if re.match(r"\s*-1 ", result):
        return None  # refused (EACCES, ...): nothing learnt
    if call in _OPENS:
        return "list" if "O_DIRECTORY" in args else "read"
    return "read" if call in _EXECS else "stat"


def _ignored(repo: Path, rels) -> set[str]:
    rels = sorted(set(rels))
    if not rels:
        return set()
    # Exit 1 is "none ignored": not an error.
    r = subprocess.run(["git", "-C", str(repo), "check-ignore", "--stdin", "-z"],
                       input="\0".join(rels) + "\0", capture_output=True, text=True,
                       check=False)
    return {x for x in r.stdout.split("\0") if x}


def audit(repo: Path, step: Step, trace) -> list[str]:
    """Every repo path an strace of `step` (text, or an iterable of lines)
    touched that its read set would let a gate skip; [] when it covers it."""
    roots = tuple(dict.fromkeys((str(repo.absolute()), os.path.realpath(repo))))
    seen = set(_trace_accesses(trace, roots))
    # Python loads a module from __pycache__/<name>.<tag>.pyc after a stat of
    # its source (the mtime check): that stat reads the source.
    pycs = {(str(PurePosixPath(rel).parent.parent), PurePosixPath(rel).name.split(".")[0])
            for kind, rel in seen if kind == "read" and rel.endswith(".pyc")
            and PurePosixPath(rel).parent.name == "__pycache__"}
    seen = {("read" if kind == "stat" and rel.endswith(".py") and
             (str(PurePosixPath(rel).parent), PurePosixPath(rel).stem) in pycs else kind, rel)
            for kind, rel in seen}
    ignored = _ignored(repo, {rel for _, rel in seen})
    sc = scope(repo, step=step)

    def new_entries(rel: str) -> frozenset[str]:
        # Adding `rel` changes a listed directory only where its entry is
        # not there yet: a new file in an existing ritz0/ leaves the listing
        # of projects/ritz as it was.
        return frozenset(e for e in step.listed_entries(rel) if not (repo / e).exists())

    found = set()
    for kind, rel in seen:
        if rel in ignored:
            continue
        if kind in ("read", "stat") and (repo / rel).is_dir():
            continue  # its existence; its entries are read by a listing
        if kind == "read":
            if why_safe("M", rel, sc, step) is not None:
                found.add(rel)
        elif kind == "stat":
            # Its existence and type, not its content (list_deps.py stats
            # every entry of RITZ_PATH with is_dir()): deleting it must run
            # the step.  Deleting a direct child changes a listed directory.
            gone = frozenset(e for e in step.listed_entries(rel) if e == rel)
            if why_safe("D", rel, sc, step, gone) is not None:
                found.add(f"{rel} (stat)")
        elif kind == "probe":
            if why_safe("A", rel, sc, step, new_entries(rel)) is not None:
                found.add(f"{rel} (probed)")
        else:
            probe = f"{rel}/.audit-probe"
            if why_safe("A", probe, sc, step, new_entries(probe)) is not None:
                found.add(f"{rel}/ (listed)")
    return sorted(found)


# `--trace STEP -- CMD...` (AGAST #4315): run CMD under strace and audit the
# trace as it streams, through a pipe: a full regression run's trace is ~1 GB,
# never stored.  main.yml's read-set-audit job runs it on both steps on every
# push to main, so an input reached only through ritz1, make or clang fails CI
# instead of waiting for someone to re-trace by hand.
STRACE = ("strace", "-f", "-qq", "-y", "-s", "512", "-e", "trace=%file,execve")


def trace(repo: Path, step: Step, cmd: list[str]) -> int:
    """Run `cmd` under strace, audit its trace against `step`'s read set;
    print the verdict.  Exit: cmd's own if it failed (a failed run did not
    read all a passing one reads), else 1 on a finding, else 0."""
    r, w = os.pipe()
    # The command must not inherit the write end: a daemon it leaves behind
    # would hold the pipe open and the audit would never see EOF.  strace's
    # own descriptor for /dev/fd/W is close-on-exec; this closes W itself.
    argv = [*STRACE, "-o", f"/dev/fd/{w}", "--",
            "bash", "-c", f'exec {w}>&-; exec "$@"', "ritz0_scope-trace", *cmd]
    # RITZ_TRACED: test-regression-parallel.sh skips its wall-clock checks
    # (strace -f stretches 8 parallel 1 s sleeps past its 4 s bound).
    env = {**os.environ, "RITZ_TRACED": "1"}
    try:
        proc = subprocess.Popen(argv, pass_fds=(w,), env=env)
    finally:
        os.close(w)
    lines = 0

    def stream():
        nonlocal lines
        with open(r, errors="replace") as f:
            for ln in f:
                lines += 1
                yield ln.rstrip("\n")

    found = audit(repo, step, stream())
    rc = proc.wait()
    sys.stdout.flush()
    if rc != 0:
        print(f"the traced command exited {rc}: a failed run is no measure of the read set")
        return rc
    if lines == 0:
        print("strace wrote no trace")
        return 1
    for f in found:
        print(f"outside the read set of {step.name!r}: {f}")
    print(f"{len(found)} path(s) outside the read set ({lines} trace lines)" if found
          else f"read set covers the trace ({lines} trace lines)")
    return 1 if found else 0


def main(argv: list[str], repo: Path | None = None, steps=STEPS) -> int:
    """`<base>`: the ritz0 step's verdict, exit 0 = skip.  `<base> --all`:
    every step's.  `--audit STEP TRACE`: check STEP's read set against an
    strace of it, exit 0 = covered.  `--trace STEP -- CMD...`: run CMD under
    strace and audit it as it streams, exit 0 = CMD passed and is covered."""
    repo = Path(__file__).resolve().parents[3] if repo is None else repo
    if len(argv) > 1 and argv[1] == "--trace":
        if len(argv) < 5 or argv[3] != "--":
            print("usage: ritz0_scope.py --trace STEP -- CMD...", file=sys.stderr)
            return 2
        by_name = {s.name: s for s in steps}
        if argv[2] not in by_name:
            print(f"no scoped step {argv[2]!r}; steps: {', '.join(by_name)}", file=sys.stderr)
            return 2
        return trace(repo, by_name[argv[2]], argv[4:])
    if len(argv) > 1 and argv[1] == "--audit":
        if len(argv) != 4:
            print("usage: ritz0_scope.py --audit STEP TRACE", file=sys.stderr)
            return 2
        by_name = {s.name: s for s in steps}
        if argv[2] not in by_name:
            print(f"no scoped step {argv[2]!r}; steps: {', '.join(by_name)}", file=sys.stderr)
            return 2
        with open(argv[3], errors="replace") as f:  # a full run's is ~1 GB
            found = audit(repo, by_name[argv[2]], (ln.rstrip("\n") for ln in f))
        for f in found:
            print(f"outside the read set of {argv[2]!r}: {f}")
        print(f"{len(found)} path(s) outside the read set" if found else "read set covers the trace")
        return 1 if found else 0
    base = argv[1] if len(argv) > 1 else None
    if "--all" in argv[2:]:
        ds = decide_steps(repo, base, steps)
        for d in ds.values():
            print("\n".join(d.lines))
        return 0 if all(d.skip for d in ds.values()) else 1
    d = decide(repo, base)
    print("\n".join(d.lines))
    return 0 if d.skip else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
