"""tools/ritz0_scope.py: may a gate skip the "ritz0 unit tests" step? (AGAST #4027)

Aaron, 2026-11-18: "if we haven't made any changes to ritz0 code or things that
can affect it, we should skip the ritz0 tests."  The step is the longest in
every gate, but it reads far more than ritz0/: ritz1, ritzlib, runtime, tools,
build.py, main.yml, every package manifest and the packages its tests name by
path.  So the rule is an allowlist that fails safe: a gate skips the step only
when EVERY changed path is in a category measured not to reach it.  An
unknown path, an unknown base, an empty diff or a git error all mean run.

Each test builds a throwaway repo shaped like this one, so the verdicts are
the module's, not a fixture's guess.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ritz0_scope

pytestmark = pytest.mark.integration  # every test starts a process (AGAST #4092)

# The tree at the base: a ritz project whose sources name some packages by
# path (as ritz0's tests name harland, indium, cryptosec, ...) and one
# Markdown file by basename, plus packages nothing names.
TREE = {
    "projects/ritz/ritz0/tests/test_reads.py": (
        'NAMED = PROJECTS / "named"\n'
        'SPEC = RITZ_ROOT / "docs" / "LANGUAGE_SPEC.md"\n'
        'KC = REPO / "docs" / "KERNEL_CONTRACT.md"\n'),
    "projects/ritz/ritz0/parser.py": "x = 1\n",
    "projects/ritz/ritz1/src/main.ritz": "fn main() -> i32\n    0\n",
    "projects/ritz/ritzlib/io.ritz": "fn f() -> i32\n    0\n",
    "projects/ritz/runtime/start.ll": "; start\n",
    "projects/ritz/tools/check_test_budget.py": "x = 1\n",
    # A tools/ test runs in the tools step, not the ritz0 step: what it names
    # is not an input of the ritz0 step.
    "projects/ritz/tools/test_other.py": 'P = REPO / ".claude" / "x" / "lonely"\n',
    "projects/ritz/build.py": "x = 1\n",
    "projects/ritz/ritz.toml": '[package]\nname = "ritz"\n',
    "projects/ritz/docs/LANGUAGE_SPEC.md": "# spec\n",
    "projects/ritz/docs/ROADMAP.md": "# roadmap\n",
    "projects/ritz/README.md": "# ritz\n",
    "projects/named/ritz.toml": '[dependencies]\ndep = { path = "../dep" }\n',
    "projects/named/src/main.ritz": "fn main() -> i32\n    0\n",
    "projects/dep/ritz.toml": '[dependencies]\ndeep = { path = "../deep" }\n',
    "projects/deep/ritz.toml": '[package]\nname = "deep"\n',
    "projects/deep/src/lib.ritz": "fn g() -> i32\n    0\n",
    "projects/dep/src/lib.ritz": "fn f() -> i32\n    0\n",
    "projects/lonely/ritz.toml": '[package]\nname = "lonely"\n',
    "projects/lonely/src/main.ritz": "fn main() -> i32\n    0\n",
    "projects/lonely/README.md": "# lonely\n",
    "projects/lonely/docs/notes.md": "# notes\n",
    ".github/workflows/main.yml": "jobs: {}\n",
    ".claude/skills/x/SKILL.md": "# skill\n",
    ".claude/skills/x/run.sh": "echo hi\n",
    "docs/guide.md": "# guide\n",
    "docs/KERNEL_CONTRACT.md": "# contract\n",
    "PROJECTS.md": "# projects\n",
    "rz": "#!/bin/sh\n",
    "rz.toml": '[workspace]\nmembers = ["projects/*"]\n',
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path):
    """A committed tree; returns (repo, base sha)."""
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q")
    git(r, "config", "user.email", "t@t")
    git(r, "config", "user.name", "t")
    for rel, text in TREE.items():
        p = r / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(r, "add", "-A")
    git(r, "commit", "-qm", "base")
    return r, git(r, "rev-parse", "HEAD")


def change(r: Path, *edits: tuple[str, str | None], commit: bool = True) -> None:
    """Apply (path, new text | None to delete) edits, committed by default."""
    for rel, text in edits:
        p = r / rel
        if text is None:
            p.unlink()
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
    if commit:
        git(r, "add", "-A")
        git(r, "commit", "-qm", "change")


def decide(r: Path, base: str | None):
    return ritz0_scope.decide(r, base)


# --------------------------------------------------------------------------
# Skips: every changed path is in a category that cannot reach the step.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("edits", [
    pytest.param([("docs/guide.md", "# new\n")], id="root-docs-md"),
    pytest.param([("PROJECTS.md", "# new\n")], id="root-md"),
    pytest.param([(".claude/skills/x/run.sh", "echo bye\n")], id="claude"),
    pytest.param([(".claude/skills/y/new.sh", "echo\n")], id="claude-added"),
    pytest.param([("projects/lonely/src/main.ritz", "fn main() -> i32\n    1\n")],
                 id="unnamed-package-source"),
    pytest.param([("projects/lonely/docs/notes.md", None)], id="unnamed-package-doc-deleted"),
    pytest.param([("PROJECTS.md", "# a\n"), ("docs/guide.md", "# b\n"),
                  (".claude/skills/x/SKILL.md", "# c\n")], id="mixed-safe"),
])
def test_a_change_outside_every_input_skips(repo, edits):
    r, base = repo
    change(r, *edits)
    d = decide(r, base)
    assert d.skip, d.lines


def test_the_skip_line_names_the_inputs_and_the_base(repo):
    r, base = repo
    change(r, ("docs/guide.md", "# new\n"))
    d = decide(r, base)
    assert d.skip
    head = d.lines[0]
    assert head.startswith("SKIPPED ritz0 unit tests: no change under ")
    assert head.endswith(f" (base {base[:7]})")
    # The inputs are named, including the packages measured as read.
    for needle in ("projects/ritz/", ".github/", "ritz.toml", "projects/{deep,dep,named}/"):
        assert needle in head, head
    # And every changed path is listed with why it can't reach the step.
    assert any("docs/guide.md" in ln for ln in d.lines[1:]), d.lines


# --------------------------------------------------------------------------
# Runs: anything the step reads, or anything not measured.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "projects/ritz/ritz0/parser.py",
    "projects/ritz/ritz1/src/main.ritz",
    "projects/ritz/ritzlib/io.ritz",
    "projects/ritz/runtime/start.ll",
    "projects/ritz/tools/check_test_budget.py",
    "projects/ritz/build.py",
    "projects/ritz/ritz.toml",
    ".github/workflows/main.yml",
])
def test_a_change_to_an_input_runs(repo, path):
    r, base = repo
    change(r, (path, "changed\n"))
    d = decide(r, base)
    assert not d.skip
    assert path in d.lines[0], d.lines


@pytest.mark.parametrize("path, why", [
    ("docs/KERNEL_CONTRACT.md", "a .md a ritz source names by basename"),
    # AGAST #4206: test_ritz1_bin_staleness copies projects/ritz whole, and
    # test_fn_cache_ritz0_identity copies ritz0/: read_guard saw them open
    # every .md there.
    ("projects/ritz/docs/ROADMAP.md", "ritz0 tests copy the projects/ritz tree"),
    ("projects/ritz/docs/NEW.md", "even a new one: copied too"),
    ("projects/named/src/main.ritz", "a package a ritz0 test names by path"),
    ("projects/dep/src/lib.ritz", "a package a named package depends on"),
    ("projects/deep/src/lib.ritz", "a dependency of a dependency"),
    (".github/notes.md", "anything under .github, even Markdown"),
    ("projects/lonely/ritz.toml", "every manifest is read (test_build_lib)"),
    ("rz", "a root file"),
    ("rz.toml", "the workspace manifest"),
    ("newtop/thing.txt", "an unknown top-level dir"),
    ("projects/ritz/examples/x/new.ritz", "anything else under projects/ritz"),
])
def test_a_named_or_unknown_path_runs(repo, path, why):
    r, base = repo
    change(r, (path, "changed\n"))
    d = decide(r, base)
    assert not d.skip, why
    assert path in d.lines[0], d.lines


def test_one_input_among_safe_changes_runs(repo):
    r, base = repo
    change(r, ("docs/guide.md", "# x\n"), ("projects/ritz/ritzlib/io.ritz", "x\n"))
    assert not decide(r, base).skip


@pytest.mark.parametrize("edits, why", [
    ([("projects/lonely/src/new.ritz", "x\n")], "an added file can change a build plan"),
    ([("projects/lonely/src/main.ritz", None)], "a deleted file can change a build plan"),
])
def test_a_file_set_change_in_an_unnamed_package_runs(repo, edits, why):
    r, base = repo
    change(r, *edits)
    assert not decide(r, base).skip, why


def test_a_top_dir_a_ritz_source_names_runs(repo):
    """.claude is allowlisted only while no ritz0-step source names it."""
    r, _ = repo
    change(r, ("projects/ritz/ritz0/tests/test_reads.py",
               TREE["projects/ritz/ritz0/tests/test_reads.py"] + 'G = ROOT / ".claude"\n'))
    head = git(r, "rev-parse", "HEAD")
    change(r, (".claude/skills/x/run.sh", "echo bye\n"))
    assert not decide(r, head).skip


def test_a_tools_test_naming_a_path_does_not_make_it_an_input(repo):
    """tools/test_*.py run in the tools step; `lonely` and .claude stay safe."""
    r, base = repo
    change(r, (".claude/skills/x/run.sh", "echo bye\n"),
           ("projects/lonely/src/main.ritz", "fn main() -> i32\n    2\n"))
    assert decide(r, base).skip


def test_a_wildcard_markdown_read_makes_every_md_an_input(repo):
    r, _ = repo
    change(r, ("projects/ritz/ritz0/tests/test_globs.py", 'DOCS = sorted(D.glob("*.md"))\n'))
    head = git(r, "rev-parse", "HEAD")
    change(r, ("docs/guide.md", "# x\n"))
    assert not decide(r, head).skip


@pytest.mark.parametrize("text", [
    pytest.param('"""Every .md is an input once a source reads *.md by pattern."""\nx = 1\n',
                 id="docstring"),
    pytest.param("x = 1  # D.glob('*.md') would make every doc an input\n", id="comment"),
])
def test_a_markdown_wildcard_in_prose_is_no_read(repo, text):
    """AGAST #4206: ritz0/read_guard.py's docstring says "*.md", and the raw
    scan made every .md an input of the ritz0 step: no docs-only change
    skipped it."""
    r, _ = repo
    change(r, ("projects/ritz/ritz0/prose.py", text))
    head = git(r, "rev-parse", "HEAD")
    change(r, ("docs/guide.md", "# x\n"))
    assert decide(r, head).skip


def test_the_real_tree_reads_no_markdown_by_pattern():
    repo = Path(__file__).resolve().parents[3]
    for step in ritz0_scope.STEPS:
        assert not ritz0_scope.scope(repo, step=step).md_wild, step.name


# --------------------------------------------------------------------------
# The base: no base, a bad base, an empty diff, uncommitted work.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("base", [None, "", "not-a-rev", "0" * 40])
def test_no_usable_base_runs(repo, base):
    r, _ = repo
    change(r, ("docs/guide.md", "# x\n"))
    d = decide(r, base)
    assert not d.skip
    assert "base" in d.lines[0], d.lines


def test_an_empty_diff_runs(repo):
    """A gate on its own base (e.g. a commit already on main) proves nothing
    by skipping; run."""
    r, base = repo
    assert not decide(r, base).skip


def test_uncommitted_and_untracked_changes_count(repo):
    r, base = repo
    change(r, ("docs/guide.md", "# x\n"))
    head = git(r, "rev-parse", "HEAD")
    assert decide(r, base).skip
    change(r, ("projects/ritz/ritz0/parser.py", "y = 2\n"), commit=False)
    assert not decide(r, head).skip and not decide(r, base).skip
    git(r, "checkout", "-q", "--", ".")
    change(r, ("projects/ritz/ritz0/new_test.py", "z = 3\n"), commit=False)
    assert not decide(r, base).skip


def test_a_git_failure_runs(tmp_path):
    d = decide(tmp_path, "HEAD")  # not a repository
    assert not d.skip


# --------------------------------------------------------------------------
# What names a package (AGAST #4032).  Measured 2026-11-18, the text scan
# named all 24 packages, many only from comments, docstrings and
# tools/smoke_stack (which the step never runs), so a package-only change
# never skipped.  A mention that can't make the step read a package must
# not name it; one that can must.  Each row adds one mention of `lonely`,
# then modifies lonely's source.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("rel, text", [
    pytest.param("projects/ritz/ritz0/tests/test_c.py", "x = 1  # see projects/lonely/src\n",
                 id="py-comment"),
    pytest.param("projects/ritz/ritz0/tests/test_c.py",
                 '"""Like projects/lonely/src, but smaller."""\nx = 1\n', id="py-module-docstring"),
    pytest.param("projects/ritz/ritz0/tests/test_c.py",
                 'def f():\n    """reads "lonely" once"""\n    return 1\n', id="py-function-docstring"),
    pytest.param("projects/ritz/tools/smoke_stack/hollow.py", 'P = ROOT / "lonely"\n',
                 id="smoke-stack-is-never-run"),
    pytest.param("projects/ritz/ritz0/test/t.ritz", "# ../lonely/src/main.ritz does this too\n",
                 id="ritz-comment"),
    pytest.param("projects/ritz/scripts/t.sh", "# ../lonely is not built here\n", id="sh-comment"),
    pytest.param("projects/ritz/ritz0/tests/test_c.py", 'URL = "lonely://example.com/x"\n',
                 id="url-scheme"),
    pytest.param("projects/ritz/ritz0/tests/test_c.py", 'CMD = "lonely --help"\n',
                 id="command-string"),
])
def test_a_mention_that_cannot_read_a_package_does_not_name_it(repo, rel, text):
    r, _ = repo
    change(r, (rel, text))
    head = git(r, "rev-parse", "HEAD")
    change(r, ("projects/lonely/src/main.ritz", "fn main() -> i32\n    3\n"))
    d = decide(r, head)
    assert d.skip, d.lines
    assert "lonely" not in ritz0_scope.named_packages(r)


@pytest.mark.parametrize("rel, text", [
    pytest.param("projects/ritz/ritz0/tests/test_c.py", 'P = PROJECTS / "lonely"\n', id="py-path"),
    pytest.param("projects/ritz/ritz0/tests/test_c.py", 'P = f"{PROJECTS}/lonely/src"\n',
                 id="py-fstring-path"),
    pytest.param("projects/ritz/ritz0/tests/test_c.py",
                 'PROG = """\nimport lonely.main\nfn main() -> i32\n    0\n"""\n',
                 id="ritz-import-in-py-string"),
    pytest.param("projects/ritz/ritz0/test/t.ritz", "import lonely.main { f }\n",
                 id="ritz-import"),
    pytest.param("projects/ritz/scripts/t.sh", "RITZ_PATH=$ROOT/lonely:$ROOT/x\n",
                 id="sh-search-path"),
    pytest.param("projects/ritz/ritz0/tests/test_c.py", 'P = PROJECTS / "lonely"\ndef f(:\n',
                 id="unparsable-py-is-read-raw"),
])
def test_a_mention_that_can_read_a_package_names_it(repo, rel, text):
    r, _ = repo
    change(r, (rel, text))
    head = git(r, "rev-parse", "HEAD")
    change(r, ("projects/lonely/src/main.ritz", "fn main() -> i32\n    3\n"))
    assert not decide(r, head).skip
    assert "lonely" in ritz0_scope.named_packages(r)


def test_the_real_tree_measures_the_packages_ritz0_tests_read():
    """The measurement on this repo (AGAST #4032, strace + an audit hook over
    a full run): the packages ritz0's tests open by path are inputs.  If one
    drops out, the scan has stopped seeing them; ritz0/read_guard.py fails
    the test that reads it on the next full run, too."""
    repo = Path(__file__).resolve().parents[3]
    named = ritz0_scope.named_packages(repo)
    for pkg in MEASURED_READ:
        assert pkg in named, sorted(named)
    assert "ritz" not in named  # always an input; not a "package" here


def test_the_real_tree_skips_a_package_the_step_never_reads():
    """The point of #4032: measured 2026-11-18, the step reads no file of
    these but their manifests (and lists their directories: A/D runs).
    The scan used to name all 24 packages, so none of them ever skipped."""
    repo = Path(__file__).resolve().parents[3]
    named = ritz0_scope.named_packages(repo)
    assert not named & NEVER_READ, sorted(named & NEVER_READ)


# The packages the full ritz0 step opened a non-manifest file of, measured
# 2026-11-18 (AGAST #4032): strace -f over the whole step, attributed per test
# with an audit hook.  Others reach it only through these packages' manifests.
MEASURED_READ = ("cryptosec", "harland", "indium", "iris", "larb", "prism",
                 "ritzunit", "spire", "zeus")
# Packages it reads only the manifests of (and lists), and that nothing in its
# sources names: before #4032 each was named by a comment, a docstring, a
# command string or tools/smoke_stack, and the one lint that read every
# package's *.ritz now runs in tools/ (test_package_syscall_numbers.py).
# Others the step never opens stay inputs on purpose: goliath (test_build_lib
# plans it by path), angelo/mausoleum/lexis/sage (dependencies of named
# packages), tempest/tome/http/squeeze (a whole string literal "tempest" may
# be a path, as ("spire", ...) is in test_corpus_import_modules_resolve).
NEVER_READ = frozenset({"nexus", "ritz-lsp", "rzrz", "rzsh", "valet"})


# ==========================================================================
# Per-step read sets (AGAST #4206).  "Differential corpus regression" and
# "Regression harness self-tests" read a narrow, measured part of
# projects/ritz (strace -f over a full run).  A change under projects/ritz
# outside a step's read set skips that step; everything outside projects/ritz
# is judged as for the ritz0 step (unknown runs, A/D in a package runs, every
# manifest is an input), with names found in the step's own sources.
# ==========================================================================

# A step that reads scripts/ and examples/ and the Makefile, and lists tools/
# and projects/ritz/ (Python's import finder does; so does a glob).
NARROW = ritz0_scope.Step(
    "narrow step",
    reads=("projects/ritz/scripts/", "projects/ritz/examples/", "projects/ritz/Makefile"),
    lists=("projects/ritz", "projects/ritz/tools"),
    label="narrow-step")

NARROW_TREE = {
    "projects/ritz/scripts/regression.sh": 'EX="$ROOT_DIR/examples"\n',
    "projects/ritz/examples/hello/src/main.ritz": "fn main() -> i32\n    0\n",
    "projects/ritz/examples/hello/README.md": "# hello\n",
    "projects/ritz/Makefile": "all:\n",
}


@pytest.fixture
def narrow(repo):
    r, _ = repo
    change(r, *NARROW_TREE.items())
    return r, git(r, "rev-parse", "HEAD")


def decide_narrow(r: Path, base: str):
    return ritz0_scope.decide(r, base, NARROW)


@pytest.mark.parametrize("status, path", [
    ("M", "projects/ritz/ritz0/parser.py"),
    ("M", "projects/ritz/ritz1/src/main.ritz"),
    ("A", "projects/ritz/ritz0/new_test.py"),          # ritz0/ is not listed
    ("D", "projects/ritz/runtime/start.ll"),
    ("M", "projects/ritz/tools/check_test_budget.py"),  # modified, in a listed dir
    ("M", "projects/ritz/build.py"),
    ("M", "projects/ritz/docs/ROADMAP.md"),
    ("M", "docs/guide.md"),
    ("M", ".claude/skills/x/run.sh"),
    ("M", "projects/lonely/src/main.ritz"),
])
def test_a_narrow_step_skips_a_change_outside_its_read_set(narrow, status, path):
    r, base = narrow
    change(r, (path, None if status == "D" else "changed\n"))
    d = decide_narrow(r, base)
    assert d.skip, d.lines
    assert d.lines[0].startswith("SKIPPED narrow step: "), d.lines


def test_the_ritz0_step_still_runs_where_a_narrow_step_skips(narrow):
    r, base = narrow
    change(r, ("projects/ritz/ritz0/parser.py", "y = 2\n"))
    assert decide_narrow(r, base).skip
    assert not ritz0_scope.decide(r, base).skip


@pytest.mark.parametrize("status, path, why", [
    ("M", "projects/ritz/scripts/regression.sh", "a file it reads"),
    ("A", "projects/ritz/scripts/test-regression-new.sh", "under a directory it reads"),
    ("M", "projects/ritz/examples/hello/src/main.ritz", "the corpus"),
    ("M", "projects/ritz/examples/hello/README.md", "even Markdown inside its read set"),
    ("D", "projects/ritz/examples/hello/README.md", "a deletion in its read set"),
    ("M", "projects/ritz/Makefile", "a single file it reads"),
    ("A", "projects/ritz/tools/tomllib.py", "an add in a listed dir can shadow an import"),
    ("A", "projects/ritz/newfile.py", "an add in projects/ritz/, which it lists"),
    ("M", "projects/ritz/ritz.toml", "every manifest stays an input"),
    ("A", "projects/ritz/ritz1/ritz.toml", "even one added outside its read set"),
    ("M", ".github/workflows/main.yml", "the workflow defines the step"),
    ("M", "rz", "a root file"),
    ("M", "known-failures/1.toml", "an unknown top-level dir"),
    ("A", "projects/lonely/src/new.ritz", "an add in a package can change a build plan"),
    ("M", "projects/lonely/ritz.toml", "a package manifest"),
])
def test_a_narrow_step_runs_on_a_change_to_its_inputs(narrow, status, path, why):
    r, base = narrow
    change(r, (path, None if status == "D" else "changed\n"))
    d = decide_narrow(r, base)
    assert not d.skip, why
    assert path in d.lines[0], d.lines


def test_a_narrow_steps_sources_name_its_packages(narrow):
    """A package the step's own sources name is an input of that step (and
    a package only the ritz0 step's sources name is not)."""
    r, _ = narrow
    change(r, ("projects/ritz/scripts/regression.sh",
               NARROW_TREE["projects/ritz/scripts/regression.sh"] + 'L="$ROOT/lonely"\n'))
    head = git(r, "rev-parse", "HEAD")
    change(r, ("projects/lonely/src/main.ritz", "fn main() -> i32\n    4\n"))
    assert not decide_narrow(r, head).skip
    # `named` is named only by ritz0/tests/test_reads.py, outside NARROW.
    sc = ritz0_scope.scope(r, step=NARROW)
    assert "lonely" in sc.named and "named" not in sc.named


def test_a_narrow_skip_line_names_its_read_set(narrow):
    r, base = narrow
    change(r, ("projects/ritz/ritz0/parser.py", "y = 2\n"))
    head = decide_narrow(r, base).lines[0]
    for needle in ("projects/ritz/scripts/", "projects/ritz/examples/",
                   "projects/ritz/Makefile", ".github/", "ritz.toml", f"(base {base[:7]})"):
        assert needle in head, head


def test_decide_steps_judges_every_step_on_one_diff(narrow):
    r, base = narrow
    change(r, ("projects/ritz/ritz0/parser.py", "y = 2\n"))
    out = ritz0_scope.decide_steps(r, base, (ritz0_scope.RITZ0, NARROW))
    assert not out[ritz0_scope.STEP].skip and out["narrow step"].skip


@pytest.mark.parametrize("base", [None, "", "not-a-rev"])
def test_a_narrow_step_with_no_usable_base_runs(narrow, base):
    r, _ = narrow
    assert not ritz0_scope.decide(r, base, NARROW).skip


def test_a_narrow_step_on_an_empty_diff_runs(narrow):
    r, base = narrow
    assert not decide_narrow(r, base).skip


# --------------------------------------------------------------------------
# The real steps on the real tree: the measured read sets (AGAST #4206).
# --------------------------------------------------------------------------

REAL = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def real_scopes():
    return {s.name: ritz0_scope.scope(REAL, step=s) for s in ritz0_scope.STEPS}


def _real(step, status, path, scopes):
    return ritz0_scope.why_safe(status, path, scopes[step.name], step)


def test_every_scoped_step_is_a_step_main_yml_declares():
    """A renamed step would silently never be scoped again."""
    import yaml
    wf = yaml.safe_load((REAL / ".github/workflows/main.yml").read_text())
    names = {s.get("name") for job in wf["jobs"].values() for s in job.get("steps", [])}
    for step in ritz0_scope.STEPS:
        assert step.name in names, step.name


@pytest.mark.parametrize("status, path", [
    ("M", "projects/ritz/tools/ci_local.py"),
    ("M", "projects/ritz/tools/ritz0_scope.py"),
    ("M", "projects/ritz/docs/TESTING.md"),
    ("M", "projects/ritz/ritz0/tests/test_parser.py"),
    ("M", "projects/ritz/ritzlib/tests/test_argspec_errors.ritz"),
    ("M", "projects/ritz/ritzlib/README.md"),
    ("M", ".claude/skills/rz-iterate/run-gate.sh"),
])
def test_a_compiler_free_change_skips_both_regression_steps(real_scopes, status, path):
    for step in (ritz0_scope.HARNESS, ritz0_scope.REGRESSION):
        if path.startswith("projects/ritz/ritz0/") and step is ritz0_scope.REGRESSION:
            continue  # ritz0 is the regression's Stage 1 compiler
        assert _real(step, status, path, real_scopes) is not None, (step.name, path)


@pytest.mark.parametrize("path, harness, regression", [
    ("projects/ritz/scripts/regression.sh", True, True),
    ("projects/ritz/scripts/test-regression-xpass.sh", True, True),
    ("projects/ritz/scripts/regression_baseline_keys.py", True, True),
    ("projects/ritz/tools/known_failures.py", True, True),
    ("projects/ritz/cache.py", True, True),
    ("projects/ritz/Makefile", True, True),
    ("projects/ritz/examples/tier1_basics/01_hello/src/main.ritz", True, True),
    ("projects/ritz/examples/tier1_basics/01_hello/test.sh", True, True),
    ("known-failures/4000.toml", True, True),
    ("projects/ritz/ritz0/parser.py", False, True),
    ("projects/ritz/ritz0/compiler_identity.py", True, True),
    ("projects/ritz/ritz1/src/main.ritz", False, True),
    ("projects/ritz/ritzlib/io.ritz", False, True),
    ("projects/ritz/runtime/ritz_start.x86_64.ll", False, True),
    ("projects/ritz/build.py", False, True),
])
def test_a_change_to_each_input_runs_its_step(real_scopes, path, harness, regression):
    """A modification to each measured input runs the step that reads it."""
    for step, reads in ((ritz0_scope.HARNESS, harness), (ritz0_scope.REGRESSION, regression)):
        why = _real(step, "M", path, real_scopes)
        assert (why is None) == reads, (step.name, path, why)


# --------------------------------------------------------------------------
# The read set's own guard (AGAST #4206).  Both steps run binaries (ritz1,
# clang, make), so an audit hook like ritz0/read_guard.py sees only what they
# are handed.  `ritz0_scope.py --audit STEP TRACE` reads an
# `strace -f -y -e trace=%file,execve` log of the step and names every path
# it touched that the step's read set would let a gate skip.
# --------------------------------------------------------------------------

def _trace(repo: Path, *lines: str) -> str:
    return "".join(line.replace("@", str(repo)) + "\n" for line in lines)


def test_audit_passes_a_trace_inside_the_read_set(narrow):
    r, _ = narrow
    log = _trace(
        r,
        '1 openat(AT_FDCWD</x>, "@/projects/ritz/scripts/regression.sh", O_RDONLY) = 3<@/projects/ritz/scripts/regression.sh>',
        '1 openat(AT_FDCWD<@/projects/ritz>, "examples/hello/src/main.ritz", O_RDONLY) = 3<@/projects/ritz/examples/hello/src/main.ritz>',
        '1 openat(AT_FDCWD</x>, "@/projects/ritz/tools", O_RDONLY|O_DIRECTORY) = 3<@/projects/ritz/tools>',
        '1 execve("/usr/bin/clang", ["clang"], 0x0 /* 1 vars */) = 0',
        '1 openat(AT_FDCWD</x>, "/etc/passwd", O_RDONLY) = 3</etc/passwd>',
        '1 newfstatat(AT_FDCWD</x>, "@/projects/ritz/scripts/missing.sh", 0x0, 0) = -1 ENOENT (No such file or directory)',
    )
    assert ritz0_scope.audit(r, NARROW, log) == []


def test_audit_names_a_read_outside_the_read_set(narrow):
    r, _ = narrow
    log = _trace(
        r,
        '1 openat(AT_FDCWD<@/projects/ritz>, "ritz0/parser.py", O_RDONLY) = 3<@/projects/ritz/ritz0/parser.py>',
        '2 execve("@/projects/ritz/build.py", ["build.py"], 0x0 /* 1 vars */) = 0',
        '2 newfstatat(AT_FDCWD</x>, "@/projects/ritz/ritzlib/io.ritz", {st_mode=S_IFREG|0644, ...}, 0) = 0',
    )
    found = ritz0_scope.audit(r, NARROW, log)
    assert found == ["projects/ritz/build.py", "projects/ritz/ritz0/parser.py",
                     "projects/ritz/ritzlib/io.ritz (stat)"], found


def test_audit_judges_a_split_call_by_its_result(narrow):
    """strace -f splits a call another process interrupts; the path is on the
    first line, the result on the `resumed` one."""
    r, _ = narrow
    log = _trace(
        r,
        '7 openat(AT_FDCWD</x>, "@/projects/ritz/ritz0/parser.py", O_RDONLY <unfinished ...>',
        '8 newfstatat(AT_FDCWD</x>, "@/projects/ritz/scripts/x.sh", 0x0, 0) = -1 ENOENT (No such file or directory)',
        '7 <... openat resumed>) = 3<@/projects/ritz/ritz0/parser.py>',
        '9 newfstatat(AT_FDCWD</x>, "@/projects/ritz/ritz1/gone" <unfinished ...>',
        '9 <... newfstatat resumed>, 0x0, 0) = -1 ENOENT (No such file or directory)',
        '9 openat(AT_FDCWD</x>, "@/projects/ritz/ritz0/out.ll", O_WRONLY|O_CREAT|O_TRUNC, 0644) = 3<@/projects/ritz/ritz0/out.ll>',
    )
    assert ritz0_scope.audit(r, NARROW, log) == [
        "projects/ritz/ritz0/parser.py", "projects/ritz/ritz1/gone (probed)"]


def test_audit_a_stat_of_a_direct_child_of_a_listed_dir_is_covered(narrow):
    """list_deps.py stats every entry of RITZ_PATH (projects/ritz): its
    existence and type, which only an add or delete changes."""
    r, _ = narrow
    log = _trace(r, '1 newfstatat(AT_FDCWD</x>, "@/projects/ritz/build.py", {st_mode=S_IFREG|0644, ...}, 0) = 0')
    assert ritz0_scope.audit(r, NARROW, log) == []


def test_audit_names_a_listing_or_probe_an_add_would_change(narrow):
    """Listing a directory, or probing a path that is not there, reads the
    set of files: adding one there must run the step."""
    r, _ = narrow
    log = _trace(
        r,
        '1 openat(AT_FDCWD</x>, "@/projects/ritz/ritz0", O_RDONLY|O_DIRECTORY) = 3<@/projects/ritz/ritz0>',
        '1 openat(AT_FDCWD</x>, "@/projects/ritz/runtime/gone.ll", O_RDONLY) = -1 ENOENT (No such file or directory)',
    )
    assert ritz0_scope.audit(r, NARROW, log) == [
        "projects/ritz/ritz0/ (listed)", "projects/ritz/runtime/gone.ll (probed)"]


def test_audit_ignores_generated_paths(narrow):
    """Build output git ignores is no input: ritz1/build/ritz1 is made from
    ritz1/'s sources, which make stats (so a %file trace sees them)."""
    r, _ = narrow
    change(r, (".gitignore", "build/\n"))
    log = _trace(
        r,
        '1 openat(AT_FDCWD</x>, "@/projects/ritz/ritz1/build/ritz1.ll", O_RDONLY) = 3<@/projects/ritz/ritz1/build/ritz1.ll>',
    )
    assert ritz0_scope.audit(r, NARROW, log) == []


def test_audit_a_py_loaded_from_its_pyc_is_read(narrow):
    """Python loads a module from __pycache__ after only a stat of its
    source (the mtime check): that stat is a read of the source."""
    r, _ = narrow
    log = _trace(
        r,
        '1 newfstatat(AT_FDCWD</x>, "@/projects/ritz/ritz0/parser.py", {st_mode=S_IFREG|0644, ...}, 0) = 0',
        '1 openat(AT_FDCWD</x>, "@/projects/ritz/ritz0/__pycache__/parser.cpython-314.pyc", O_RDONLY|O_CLOEXEC) = 3<@/projects/ritz/ritz0/__pycache__/parser.cpython-314.pyc>',
    )
    change(r, (".gitignore", "__pycache__/\n"))
    assert ritz0_scope.audit(r, NARROW, log) == ["projects/ritz/ritz0/parser.py"]


def test_audit_cli_exits_nonzero_on_a_finding(narrow, tmp_path):
    r, _ = narrow
    log = tmp_path / "t.strace"
    log.write_text(_trace(
        r, '1 openat(AT_FDCWD</x>, "@/projects/ritz/ritz0/parser.py", O_RDONLY) = 3<@/projects/ritz/ritz0/parser.py>'))
    assert ritz0_scope.main(["x", "--audit", "narrow step", str(log)], repo=r,
                            steps=(NARROW,)) == 1
    log.write_text("")
    assert ritz0_scope.main(["x", "--audit", "narrow step", str(log)], repo=r,
                            steps=(NARROW,)) == 0


# Re-derived from the scripts, without a trace: every repo path the
# regression scripts name by $ROOT_DIR/$RITZ_ROOT/$SCRIPT_DIR, and every
# sibling module a Python input imports, is in the read set of a step that
# runs them.  Catches a new input named in a script or an import before the
# next strace does.

_SCRIPT_REF = re.compile(
    r'\$\{?(ROOT_DIR|RITZ_ROOT|SCRIPT_DIR)\}?"?/([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)')
_ROOTS = {"ROOT_DIR": "projects/ritz/", "RITZ_ROOT": "projects/ritz/",
          "SCRIPT_DIR": "projects/ritz/scripts/"}
# Test scripts point ROOT_DIR at a scratch tree; regression.sh's own ROOT_DIR
# is the real one.  Generated paths are outputs, not inputs.
_GENERATED = ("build", ".regression", ".regression-cache", "ritz1/build")


def _script_refs(text: str) -> set[str]:
    refs = set()
    for var, rest in _SCRIPT_REF.findall(text):
        rel = os.path.normpath(_ROOTS[var] + rest)
        if rest.startswith(".."):
            continue  # the project root itself
        sub = rel[len("projects/ritz/"):]
        if any(sub == g or sub.startswith(g + "/") for g in _GENERATED):
            continue
        refs.add(rel)
    return refs


def test_the_regression_scripts_name_only_paths_in_their_read_set(real_scopes):
    scripts = REAL / "projects/ritz/scripts"
    reg = (scripts / "regression.sh").read_text()
    for rel in sorted(_script_refs(reg)):
        why = _real(ritz0_scope.REGRESSION, "M", rel, real_scopes)
        assert why is None, (rel, why)
    for t in sorted(scripts.glob("test-regression-*.sh")):
        text = t.read_text()
        # Only refs through SCRIPT_DIR/RITZ_ROOT are the real tree here.
        for rel in sorted(r for r in _script_refs(text.replace("$ROOT_DIR", "$SCRATCH"))
                          if r.startswith("projects/ritz/")):
            why = _real(ritz0_scope.HARNESS, "M", rel, real_scopes)
            assert why is None, (t.name, rel, why)


def test_the_harness_reads_compiler_identity_and_lists_ritz0(real_scopes):
    """AGAST #4380: the baseline-cache self-test loads cache.py, whose
    compiler hash imports the real ritz0/compiler_identity.py, and Python's
    import finder lists ritz0/ (it is sys.path[0] for that import).  Both
    are required reads: the 2026-11-19 measurement missed them and the audit
    went red.  Only that one ritz0 source is an input; a modification to any
    other still skips the harness."""
    assert _real(ritz0_scope.HARNESS, "M",
                 "projects/ritz/ritz0/compiler_identity.py", real_scopes) is None
    assert _real(ritz0_scope.HARNESS, "M",
                 "projects/ritz/ritz0/parser.py", real_scopes) is not None
    # The listing: a new entry in ritz0/ changes what sys.path[0] resolves.
    # projects/ritz is listed too, but a file inside an existing top-level
    # directory leaves its listing unchanged, so ritz0/ needs its own entry.
    sc = real_scopes[ritz0_scope.HARNESS.name]
    changed = frozenset({"projects/ritz/ritz0/shadow.py"})
    assert ritz0_scope.why_safe("A", "projects/ritz/ritz0/shadow.py", sc,
                                ritz0_scope.HARNESS, changed) is None


def test_the_harness_audit_covers_compiler_identity_and_the_listing():
    """The exact trace shape CI rejected after #3915 (AGAST #4380)."""
    log = _trace(
        REAL,
        '1 openat(AT_FDCWD<@/projects/ritz>, "ritz0", O_RDONLY|O_NONBLOCK|O_CLOEXEC|O_DIRECTORY) = 3<@/projects/ritz/ritz0>',
        '1 openat(AT_FDCWD<@/projects/ritz>, "ritz0/compiler_identity.py", O_RDONLY|O_CLOEXEC) = 3<@/projects/ritz/ritz0/compiler_identity.py>',
    )
    assert ritz0_scope.audit(REAL, ritz0_scope.HARNESS, log) == []


def test_the_harness_glob_is_in_its_read_set(real_scopes):
    mk = (REAL / "projects/ritz/Makefile").read_text()
    assert "scripts/test-regression-*.sh" in mk
    assert _real(ritz0_scope.HARNESS, "A", "projects/ritz/scripts/test-regression-new.sh",
                 real_scopes) is None


@pytest.mark.parametrize("dir", ("test", "tests"))
def test_the_regression_lists_the_ritz0_test_directories(real_scopes, dir):
    """AGAST #4385, #4482: every build.py run computes cache.py's ritz0 hash,
    which loads ritz0/compiler_identity.py; its resolver os.walks ritz0/ (one
    walk instead of a stat per candidate module), so the corpus regression
    lists ritz0/test and, since #4373 renamed the Python tests in, ritz0/tests
    — an entry added to or removed from either changes that walk.  The
    listings are declared rather than the subtrees read: a test file's
    contents are still never opened, so a modification still skips."""
    sc = real_scopes[ritz0_scope.REGRESSION.name]
    new, old = (f"projects/ritz/ritz0/{dir}/test_new.ritz",
                f"projects/ritz/ritz0/{dir}/test_parser.ritz")
    changed = frozenset({new})
    assert ritz0_scope.why_safe("A", new, sc, ritz0_scope.REGRESSION, changed) is None
    assert _real(ritz0_scope.REGRESSION, "M", old, real_scopes) is not None
    # A directory's listing covers that directory only: a new entry one level
    # deeper changes the listing of a directory the trace never listed.
    nested = frozenset({f"projects/ritz/ritz0/{dir}/fixtures/x.py"})
    assert ritz0_scope.why_safe(
        "A", f"projects/ritz/ritz0/{dir}/fixtures/x.py",
        sc, ritz0_scope.REGRESSION, nested) is not None


def test_every_declared_ritz0_listing_still_exists():
    """AGAST #4482: a renaming of a declared ritz0 directory would otherwise
    leave a stale entry that covers nothing (the #4373 `test/` -> `tests/`
    drift), which the trace audit only catches on the next push to main."""
    for d in ritz0_scope.REGRESSION.lists:
        if d.startswith("projects/ritz/ritz0/"):
            assert (REAL / d).is_dir(), f"{d}: declared listing, not a directory"


def test_the_regression_audit_covers_every_ritz0_directory_the_walk_lists():
    """AGAST #4482: compiler_identity's resolver os.walks ritz0/ and opens
    every directory under it, so the read set must cover each listing — an
    excluded tree (ritz0's tests) needs a declared entry, while a directory
    under an unexcluded read is covered by `reads`.  Replaying one listing
    per directory in the real tree makes a rename fail here, not in CI."""
    pkg = REAL / "projects/ritz/ritz0"
    log = "".join(
        f'1 openat(AT_FDCWD</x>, "{p}", O_RDONLY|O_NONBLOCK|O_CLOEXEC|O_DIRECTORY) = 3<{p}>\n'
        for p in sorted(x for x in pkg.rglob("*") if x.is_dir()))
    assert log, "no ritz0 directories found"
    assert ritz0_scope.audit(REAL, ritz0_scope.REGRESSION, log) == []


def test_the_regression_audit_covers_the_ritz0_test_listing():
    """The exact trace shape CI rejected (AGAST #4385, #4482): the walk opens
    ritz0/ and each test directory as directories; all listings are in the
    read set.  #4373 moved the Python tests from test/ to tests/, so the
    latter is the entry that drifted."""
    log = _trace(
        REAL,
        '1 openat(AT_FDCWD<@/projects/ritz>, "ritz0", O_RDONLY|O_NONBLOCK|O_CLOEXEC|O_DIRECTORY) = 3<@/projects/ritz/ritz0>',
        '1 openat(AT_FDCWD<@/projects/ritz/ritz0>, "test", O_RDONLY|O_NONBLOCK|O_CLOEXEC|O_DIRECTORY) = 3<@/projects/ritz/ritz0/test>',
        '1 openat(AT_FDCWD<@/projects/ritz/ritz0>, "tests", O_RDONLY|O_NONBLOCK|O_CLOEXEC|O_DIRECTORY) = 3<@/projects/ritz/ritz0/tests>',
    )
    assert ritz0_scope.audit(REAL, ritz0_scope.REGRESSION, log) == []


def test_the_regression_audit_still_names_an_undeclared_excluded_listing():
    """Declaring ritz0/test must not cover another excluded directory the
    trace lists: ritzlib/tests is excluded from the read set too (the corpus
    does not open its files), and it is not declared, so listing it stays a
    finding.  A directory under an unexcluded read is covered by `reads`."""
    log = _trace(
        REAL,
        '1 openat(AT_FDCWD</x>, "@/projects/ritz/ritzlib/tests", O_RDONLY|O_DIRECTORY) = 3<@/projects/ritz/ritzlib/tests>',
    )
    assert ritz0_scope.audit(REAL, ritz0_scope.REGRESSION, log) == [
        "projects/ritz/ritzlib/tests/ (listed)"]


@pytest.mark.parametrize("step", ritz0_scope.STEPS[1:], ids=lambda s: s.name)
def test_every_python_input_imports_only_inputs(real_scopes, step):
    """A Python file the step reads finds its siblings on sys.path[0]: each
    sibling module it can import is in the read set.  (cache.py's lazy
    ritz0 import is not a sibling and is not checked here; the harness does
    take that read and declares it explicitly, AGAST #4380.)"""
    import ast
    for rel in ritz0_scope.step_files(REAL, step):
        if not rel.endswith(".py") or "/examples/" in rel:
            continue
        src = REAL / rel
        try:
            tree = ast.parse(src.read_text())
        except SyntaxError:
            continue
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree)
                 if isinstance(n, ast.ImportFrom) and n.module and not n.level}
        for m in mods:
            for cand in (src.parent / f"{m}.py", src.parent / m / "__init__.py"):
                if cand.is_file():
                    crel = cand.relative_to(REAL).as_posix()
                    why = _real(step, "M", crel, real_scopes)
                    assert why is None, (step.name, rel, "imports", crel, why)


# --------------------------------------------------------------------------
# The read set's audit, run by CI (AGAST #4315).  `--trace STEP -- CMD`
# runs CMD under strace and streams the trace through a pipe into the
# audit: a full regression run's trace is ~1 GB, never stored.  main.yml's
# read-set-audit job runs it on both scoped steps on every push to main.
# --------------------------------------------------------------------------

def _can_strace() -> bool:
    import shutil
    if not shutil.which("strace"):
        return False
    r = subprocess.run(["strace", "-qq", "-o", "/dev/null", "true"],
                       capture_output=True, check=False)
    return r.returncode == 0


needs_strace = pytest.mark.skipif(not _can_strace(), reason="strace missing or ptrace denied")


def _trace_main(r: Path, *cmd: str) -> int:
    return ritz0_scope.main(["x", "--trace", "narrow step", "--", *cmd], repo=r,
                            steps=(NARROW,))


@needs_strace
def test_trace_passes_a_command_inside_the_read_set(narrow, capsys):
    r, _ = narrow
    assert _trace_main(r, "cat", str(r / "projects/ritz/Makefile")) == 0
    out = capsys.readouterr().out
    assert "read set covers the trace" in out, out


@needs_strace
def test_trace_names_a_read_outside_the_read_set(narrow, capsys):
    r, _ = narrow
    (r / "projects/ritz/ritz0").mkdir(parents=True, exist_ok=True)
    (r / "projects/ritz/ritz0/parser.py").write_text("x = 1\n")
    assert _trace_main(r, "cat", str(r / "projects/ritz/ritz0/parser.py")) == 1
    out = capsys.readouterr().out
    assert "outside the read set of 'narrow step': projects/ritz/ritz0/parser.py" in out, out


@needs_strace
def test_trace_fails_when_the_traced_command_fails(narrow, capsys):
    """A step that fails under the trace did not read all it reads."""
    r, _ = narrow
    assert _trace_main(r, "sh", "-c", f"cat {r}/projects/ritz/Makefile; exit 3") == 3
    assert "exited 3" in capsys.readouterr().out


@needs_strace
def test_trace_tells_the_step_it_is_traced(narrow):
    """test-regression-parallel.sh's wall-clock checks skip under the trace:
    strace -f makes 8 parallel one-second sleeps take longer than 4 s."""
    r, _ = narrow
    assert _trace_main(r, "sh", "-c", 'test "$RITZ_TRACED" = 1') == 0


@needs_strace
def test_the_traced_command_does_not_hold_the_trace_pipe(narrow, capsys):
    """The command gets no copy of the pipe's write end: a leaked copy in a
    daemon the step leaves running would keep the audit from ever ending."""
    r, _ = narrow
    assert _trace_main(r, "sh", "-c",
                      'for f in /proc/$$/fd/*; do [ -e "$f" ] && [ "${f##*/}" -gt 2 ] && exit 9; done; exit 0') == 0


def test_trace_usage(narrow, capsys):
    r, _ = narrow
    assert ritz0_scope.main(["x", "--trace", "narrow step"], repo=r, steps=(NARROW,)) == 2
    assert ritz0_scope.main(["x", "--trace", "nope", "--", "true"], repo=r,
                            steps=(NARROW,)) == 2


def _job_steps(job: str) -> list[dict]:
    import yaml
    wf = yaml.safe_load((REAL / ".github/workflows/main.yml").read_text())
    return wf["jobs"][job]["steps"]


@pytest.mark.parametrize("step", ritz0_scope.STEPS[1:], ids=lambda s: s.name)
def test_ci_traces_each_scoped_step_exactly_as_the_gate_runs_it(step):
    """The read-set-audit job traces the very command, env and directory of
    the bootstrap step it audits, under the step's own name."""
    import shlex
    gated = next(s for s in _job_steps("bootstrap") if s.get("name") == step.name)
    traced = [s for s in _job_steps("read-set-audit")
              if f"--trace {shlex.quote(step.name)} -- " in s.get("run", "")
              or f'--trace "{step.name}" -- ' in s.get("run", "")]
    assert len(traced) == 1, (step.name, traced)
    t = traced[0]
    argv = shlex.split(t["run"])
    assert argv[:2] == ["python3", "tools/ritz0_scope.py"], argv
    assert argv[2:5] == ["--trace", step.name, "--"], argv
    assert argv[5:] == shlex.split(gated["run"]), (argv, gated["run"])
    assert t.get("working-directory") == gated.get("working-directory")
    assert (t.get("env") or {}) == (gated.get("env") or {})


def test_the_audit_job_installs_strace_and_is_not_gated():
    """The gate (run-gate.sh: build-all, test-all, bootstrap) must not run
    a ~15-minute traced job; CI runs it on main."""
    steps = _job_steps("read-set-audit")
    runs = " ".join(s.get("run", "") for s in steps)
    assert "strace" in runs.split("--trace")[0], runs
    gate = (REAL / ".claude/skills/rz-iterate/run-gate.sh").read_text()
    assert "read-set-audit" not in gate
