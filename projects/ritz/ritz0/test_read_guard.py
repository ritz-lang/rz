"""Tests for read_guard, which checks tools/ritz0_scope.py on every run (AGAST #4032).

ritz0_scope lets a gate skip this whole step when no change can reach it, and
it finds what can by scanning this step's sources.  read_guard fails a test
that reads, lists or hands a child a path the scope would let a gate skip, so
a read the scan missed is caught on the next full run instead of becoming a
skipped regression.

The rules are tested on a throwaway repo with an explicit scope (no git, no
subprocess): `named` is an input package, `lonely` is not.  One nested
session proves a hit fails the test, or the collection, that made it.
"""

import contextlib
import os
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import read_guard
import ritz0_scope

RITZ0_DIR = Path(__file__).resolve().parent

SCOPE = ritz0_scope.Scope(named=frozenset({"named"}), md_wild=False,
                          md_names=frozenset({"SPEC.md"}), named_tops=frozenset())

FILES = (
    "projects/ritz/build.py",
    "projects/ritz/docs/NOTES.md",
    "projects/ritz/ritzlib/io.ritz",
    "projects/named/src/a.ritz",
    "projects/lonely/ritz.toml",
    "projects/lonely/src/a.ritz",
    ".claude/skills/s.sh",
    ".github/workflows/main.yml",
    "docs/guide.md",
    "docs/SPEC.md",
)


@pytest.fixture
def fake(tmp_path):
    repo = tmp_path / "repo"
    for rel in FILES:
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x\n")
    (repo / "projects" / "ritzlib").symlink_to("ritz/ritzlib")
    return repo, read_guard.Guard(repo, SCOPE)


@pytest.mark.parametrize("rel, skippable", [
    ("projects/lonely/src/a.ritz", True),
    ("projects/lonely/src", True),          # a directory read: anything in it
    ("projects/lonely/ritz.toml", False),   # every manifest is an input
    ("projects/named/src/a.ritz", False),
    ("projects/ritz/build.py", False),
    ("projects/ritzlib/io.ritz", False),    # the symlink into projects/ritz
    (".claude/skills/s.sh", True),
    (".github/workflows/main.yml", False),
    ("docs/guide.md", True),
    ("docs/SPEC.md", False),                # a .md a source names
    ("projects/ritz/docs/NOTES.md", True),  # judged by basename, even here
])
def test_a_read_is_judged_as_a_modification(fake, rel, skippable):
    repo, g = fake
    hit = g.read(repo / rel)
    assert bool(hit) == skippable, hit
    if hit:
        assert hit[0].rstrip("/") == rel and hit[1]


def test_a_relative_read_resolves_against_the_cwd(fake):
    repo, g = fake
    assert g.read("src/a.ritz", cwd=str(repo / "projects" / "lonely"))
    assert not g.read("src/a.ritz", cwd=str(repo / "projects" / "named"))


def test_a_tree_with_no_scope_turns_the_guard_off(fake):
    """A copy of ritz0/ outside a checkout (a nested session's): git can't
    list sources, so there is no gate scope to check; the guard steps aside
    rather than fail every read."""
    repo, _ = fake
    g = read_guard.Guard(repo)  # measured on first use, and not a git repo
    assert g.read(repo / "projects" / "lonely" / "src" / "a.ritz") is None
    assert g.broken


def test_a_path_outside_the_repo_is_not_judged(fake, tmp_path):
    _, g = fake
    (tmp_path / "elsewhere.md").write_text("x\n")
    assert g.read(tmp_path / "elsewhere.md") is None


@pytest.mark.parametrize("rel, skippable", [
    ("projects/lonely/src", False),  # an add in any package runs the step
    ("projects", False),
    ("projects/ritz/docs", False),   # a new .md is read by name or not at all
    (".claude/skills", True),        # an add there would skip
])
def test_a_listing_is_judged_as_an_add(fake, rel, skippable):
    repo, g = fake
    assert bool(g.listing(repo / rel)) == skippable


@pytest.mark.parametrize("argv, cwd, ritz_path, skippable", [
    (["ritz1", "projects/lonely/src/a.ritz"], "", None, True),
    (["ritz1", "projects/named/src/a.ritz"], "", None, False),
    (["clang", "-I{repo}/projects/lonely/src"], None, None, True),
    (["make", "--dir={repo}/projects/lonely"], None, None, True),
    (["ritz1", "main.ritz"], "projects/lonely", None, True),
    (["ritz1", "/tmp/x.ritz"], None, "{repo}/projects/ritz:{repo}/projects/lonely", True),
    (["ritz1", "/tmp/x.ritz"], None, "{repo}/projects/ritz:{repo}/projects/named", False),
], ids=["arg", "named-arg", "flag-glued", "flag-equals", "cwd", "ritz-path", "named-ritz-path"])
def test_what_a_child_is_handed_is_judged(fake, argv, cwd, ritz_path, skippable):
    repo, g = fake
    argv = [a.format(repo=repo) for a in argv]
    cwd = None if cwd is None else str(repo / cwd)
    env = {"RITZ_PATH": ritz_path.format(repo=repo)} if ritz_path else {}
    assert bool(g.exec(argv, cwd, env)) == skippable


@contextlib.contextmanager
def recording(guard):
    """The live hook judging against `guard`, into a window of its own; the
    phase's window (and guard) come back after, free of the fake hits."""
    saved = read_guard._guard, read_guard._window
    read_guard.install(guard)  # hooks, even in a RITZ_READ_GUARD=0 session
    read_guard._window = []
    try:
        yield read_guard._window
    finally:
        read_guard._guard, read_guard._window = saved


def test_the_hook_sees_reads_and_listings_but_not_writes(fake):
    repo, g = fake
    src = repo / "projects" / "lonely" / "src" / "a.ritz"
    with recording(g) as window:
        src.write_text("written\n")
        os.close(os.open(src, os.O_WRONLY))
        writes = list(window)
        src.read_text()
        os.listdir(repo / ".claude" / "skills")
        read_guard.note_exec(["main.ritz"], str(repo / "projects" / "lonely"), {})
    assert writes == []
    assert [(rel, how) for rel, how, _ in window] == [
        ("projects/lonely/src/a.ritz", "open"), (".claude/skills/", "list"),
        ("projects/lonely/main.ritz", "ritz0 (in-process)"),
        ("projects/lonely/", "ritz0 (in-process)")]


def test_the_hook_is_idle_outside_a_window(fake):
    repo, g = fake
    with recording(g):
        read_guard._window = None
        (repo / "projects" / "lonely" / "src" / "a.ritz").read_text()  # no record
        assert read_guard._window is None


# One nested session: a test or a module that reads a skippable path fails,
# naming it; one that reads only inputs passes.
CASES = {
    "reads_skippable": """
        def test_reads():
            (REPO / "projects" / "lonely" / "src" / "a.ritz").read_text()
    """,
    "reads_input": """
        def test_reads():
            (REPO / "projects" / "named" / "src" / "a.ritz").read_text()
    """,
    "collects_skippable": """
        TEXT = (REPO / "docs" / "guide.md").read_text()
        def test_nothing():
            pass
    """,
}

CONFTEST = """
import os, sys
from pathlib import Path
import pytest, read_guard, ritz0_scope
REPO = Path(os.environ["READ_GUARD_FAKE_REPO"])
@pytest.hookimpl(trylast=True)  # after read_guard installs the real repo's guard
def pytest_configure(config):
    read_guard.install(read_guard.Guard(REPO, ritz0_scope.Scope(
        named=frozenset({"named"}), md_wild=False, md_names=frozenset(),
        named_tops=frozenset())))
"""


@pytest.mark.integration
def test_a_hit_fails_the_test_or_the_collection_that_made_it(fake, tmp_path):
    repo, _ = fake
    d = tmp_path / "cases"
    d.mkdir()
    (d / "conftest.py").write_text(CONFTEST)
    for name, body in CASES.items():
        (d / f"test_{name}.py").write_text(
            "import os\nfrom pathlib import Path\n"
            "REPO = Path(os.environ['READ_GUARD_FAKE_REPO'])\n" + textwrap.dedent(body))
    xml = tmp_path / "junit.xml"
    env = dict(os.environ, READ_GUARD_FAKE_REPO=str(repo), PYTHONDONTWRITEBYTECODE="1",
               RITZ_READ_GUARD="1",
               PYTHONPATH=os.pathsep.join([str(RITZ0_DIR), os.environ.get("PYTHONPATH", "")]))
    env.pop("PYTEST_ADDOPTS", None)
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "--disable-plugin-autoload", "-p", "read_guard", f"--junitxml={xml}",
         "--continue-on-collection-errors",
         "--rootdir", str(d), "-c", os.devnull, str(d)],
        cwd=d, env=env, capture_output=True, text=True, timeout=120)
    out = proc.stdout + proc.stderr
    verdicts = {}
    for case in ET.parse(xml).getroot().iter("testcase"):
        where = f"{case.get('classname')} {case.get('name')}"
        name = next(n for n in CASES if f"test_{n}" in where)
        bad = case.find("failure") if case.find("failure") is not None else case.find("error")
        verdicts[name] = (bad.get("message", "") + (bad.text or "")) if bad is not None else ""
    out += f"\nverdicts: {verdicts}"
    assert verdicts.keys() == CASES.keys(), out
    assert verdicts["reads_input"] == "", out
    assert "projects/lonely/src/a.ritz (open)" in verdicts["reads_skippable"], out
    assert "docs/guide.md (open)" in verdicts["collects_skippable"], out


def test_this_session_is_guarded():
    """conftest.py loads the guard, so every ritz0 run checks the scope.
    RITZ_READ_GUARD=0 is the only way off."""
    if os.environ.get("RITZ_READ_GUARD") == "0":
        pytest.skip("RITZ_READ_GUARD=0: the guard is off by request")
    assert read_guard._hooked and read_guard._guard is not None
    assert Path(read_guard._guard.repo) == RITZ0_DIR.parents[2]


@pytest.mark.integration
def test_a_forked_ritz0_compile_is_judged_by_what_it_is_handed(fake, tmp_path):
    """ritz0_inproc compiles in a forked child the hook can't see into, so
    it tells the guard what the child was handed."""
    import ritz0_inproc
    repo, g = fake
    with recording(g) as window:
        ritz0_inproc.run_ritz0([str(repo / "projects" / "lonely" / "src" / "a.ritz"),
                                "-o", str(tmp_path / "a.ll")])
    assert ("projects/lonely/src/a.ritz", "ritz0 (in-process)") in \
        [(rel, how) for rel, how, _ in window]
