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
    "projects/ritz/ritz0/test_reads.py": (
        'NAMED = PROJECTS / "named"\n'
        'SPEC = RITZ_ROOT / "docs" / "LANGUAGE_SPEC.md"\n'),
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
    pytest.param([("projects/ritz/docs/ROADMAP.md", "# new\n")], id="ritz-docs-md"),
    pytest.param([("projects/ritz/docs/NEW.md", "# new\n")], id="new-ritz-doc"),
    pytest.param([("docs/guide.md", "# new\n")], id="root-docs-md"),
    pytest.param([("PROJECTS.md", "# new\n")], id="root-md"),
    pytest.param([(".claude/skills/x/run.sh", "echo bye\n")], id="claude"),
    pytest.param([(".claude/skills/y/new.sh", "echo\n")], id="claude-added"),
    pytest.param([("projects/lonely/src/main.ritz", "fn main() -> i32\n    1\n")],
                 id="unnamed-package-source"),
    pytest.param([("projects/lonely/docs/notes.md", None)], id="unnamed-package-doc-deleted"),
    pytest.param([("projects/ritz/docs/ROADMAP.md", "# a\n"), ("docs/guide.md", "# b\n"),
                  (".claude/skills/x/SKILL.md", "# c\n")], id="mixed-safe"),
])
def test_a_change_outside_every_input_skips(repo, edits):
    r, base = repo
    change(r, *edits)
    d = decide(r, base)
    assert d.skip, d.lines


def test_the_skip_line_names_the_inputs_and_the_base(repo):
    r, base = repo
    change(r, ("projects/ritz/docs/ROADMAP.md", "# new\n"))
    d = decide(r, base)
    assert d.skip
    head = d.lines[0]
    assert head.startswith("SKIPPED ritz0 unit tests: no change under ")
    assert head.endswith(f" (base {base[:7]})")
    # The inputs are named, including the packages measured as read.
    for needle in ("projects/ritz/", ".github/", "ritz.toml", "projects/{deep,dep,named}/"):
        assert needle in head, head
    # And every changed path is listed with why it can't reach the step.
    assert any("projects/ritz/docs/ROADMAP.md" in ln for ln in d.lines[1:]), d.lines


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
    ("projects/ritz/docs/LANGUAGE_SPEC.md", "a .md a ritz source names by basename"),
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
    change(r, ("projects/ritz/ritz0/test_reads.py",
               TREE["projects/ritz/ritz0/test_reads.py"] + 'G = ROOT / ".claude"\n'))
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
    change(r, ("projects/ritz/ritz0/test_globs.py", 'DOCS = sorted(D.glob("*.md"))\n'))
    head = git(r, "rev-parse", "HEAD")
    change(r, ("docs/guide.md", "# x\n"))
    assert not decide(r, head).skip


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
    pytest.param("projects/ritz/ritz0/test_c.py", "x = 1  # see projects/lonely/src\n",
                 id="py-comment"),
    pytest.param("projects/ritz/ritz0/test_c.py",
                 '"""Like projects/lonely/src, but smaller."""\nx = 1\n', id="py-module-docstring"),
    pytest.param("projects/ritz/ritz0/test_c.py",
                 'def f():\n    """reads "lonely" once"""\n    return 1\n', id="py-function-docstring"),
    pytest.param("projects/ritz/tools/smoke_stack/hollow.py", 'P = ROOT / "lonely"\n',
                 id="smoke-stack-is-never-run"),
    pytest.param("projects/ritz/ritz0/test/t.ritz", "# ../lonely/src/main.ritz does this too\n",
                 id="ritz-comment"),
    pytest.param("projects/ritz/scripts/t.sh", "# ../lonely is not built here\n", id="sh-comment"),
    pytest.param("projects/ritz/ritz0/test_c.py", 'URL = "lonely://example.com/x"\n',
                 id="url-scheme"),
    pytest.param("projects/ritz/ritz0/test_c.py", 'CMD = "lonely --help"\n',
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
    pytest.param("projects/ritz/ritz0/test_c.py", 'P = PROJECTS / "lonely"\n', id="py-path"),
    pytest.param("projects/ritz/ritz0/test_c.py", 'P = f"{PROJECTS}/lonely/src"\n',
                 id="py-fstring-path"),
    pytest.param("projects/ritz/ritz0/test_c.py",
                 'PROG = """\nimport lonely.main\nfn main() -> i32\n    0\n"""\n',
                 id="ritz-import-in-py-string"),
    pytest.param("projects/ritz/ritz0/test/t.ritz", "import lonely.main { f }\n",
                 id="ritz-import"),
    pytest.param("projects/ritz/scripts/t.sh", "RITZ_PATH=$ROOT/lonely:$ROOT/x\n",
                 id="sh-search-path"),
    pytest.param("projects/ritz/ritz0/test_c.py", 'P = PROJECTS / "lonely"\ndef f(:\n',
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
