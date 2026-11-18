#!/usr/bin/env python3
"""Self-tests for likely_tests.py -- AGAST #3456 (LARB review/5 tooling F4).

The gate runs the ritz0 test files that the last commits changed BEFORE the
rest of the gate, so a likely failure surfaces in the first four minutes
instead of nine to eleven.  These hold the selection to its rule:

  * newest first: the gated commit's own test files lead
  * each file once, at its newest position
  * only ritz0 test modules that still exist (a deleted or renamed test is
    not passed to pytest, which would error on a missing path)
  * a file outside ritz0, or a non-test file in it, is never selected
  * the commit window and the file cap bound the pass

Run with:
    python3 -m pytest projects/ritz/tools/test_likely_tests.py -q
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import likely_tests

pytestmark = pytest.mark.integration  # shells out to git


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path):
    """A repo shaped like ours: projects/ritz/ritz0 holds the tests."""
    r = tmp_path / "repo"
    (r / "projects/ritz/ritz0").mkdir(parents=True)
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "t")
    return r


def commit(repo: Path, *paths: str, delete: tuple[str, ...] = ()) -> None:
    """One commit that writes `paths` (fresh content) and deletes `delete`."""
    for p in paths:
        f = repo / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"{f.read_text() if f.exists() else ''}x\n")
        _git(repo, "add", p)
    for p in delete:
        _git(repo, "rm", "-q", p)
    _git(repo, "commit", "-q", "-m", "c")


R0 = "projects/ritz/ritz0/"


def test_newest_commit_first(repo):
    commit(repo, R0 + "test_old.py")
    commit(repo, R0 + "test_mid.py")
    commit(repo, R0 + "test_new.py")   # the gated commit
    assert likely_tests.select(repo) == ["test_new.py", "test_mid.py", "test_old.py"]


def test_a_file_appears_once_at_its_newest_position(repo):
    commit(repo, R0 + "test_a.py")
    commit(repo, R0 + "test_b.py")
    commit(repo, R0 + "test_a.py")
    assert likely_tests.select(repo) == ["test_a.py", "test_b.py"]


def test_only_ritz0_test_modules_are_selected(repo):
    commit(repo, R0 + "test_keep.py", R0 + "parser.py", R0 + "conftest.py",
           R0 + "test/test_level24.ritz", "projects/ritz/tools/test_tool.py",
           "projects/other/test_x.py", R0 + "emitter/test_nested.py")
    assert likely_tests.select(repo) == ["emitter/test_nested.py", "test_keep.py"]


def test_deleted_test_files_are_dropped(repo):
    commit(repo, R0 + "test_gone.py", R0 + "test_stays.py")
    commit(repo, delete=(R0 + "test_gone.py",))
    assert likely_tests.select(repo) == ["test_stays.py"]


def test_window_counts_commits_not_files(repo):
    commit(repo, R0 + "test_outside.py")
    commit(repo, R0 + "test_in1.py", R0 + "test_in2.py")
    commit(repo, R0 + "test_in3.py")
    got = likely_tests.select(repo, commits=2)
    assert sorted(got) == ["test_in1.py", "test_in2.py", "test_in3.py"]


def test_commits_outside_ritz0_do_not_use_up_the_window(repo):
    commit(repo, R0 + "test_wanted.py")
    for _ in range(3):
        commit(repo, "projects/other/file.txt")
    assert likely_tests.select(repo, commits=1) == ["test_wanted.py"]


def test_cap_keeps_the_newest(repo):
    for i in range(5):
        commit(repo, R0 + f"test_{i}.py")
    assert likely_tests.select(repo, max_files=2) == ["test_4.py", "test_3.py"]


def test_not_a_git_repo_selects_nothing(tmp_path):
    """No history is no pre-pass, not a crash: the full step still runs."""
    (tmp_path / "projects/ritz/ritz0").mkdir(parents=True)
    assert likely_tests.select(tmp_path) == []


def test_real_repo_selects_existing_ritz0_tests():
    root = HERE.parents[2]
    got = likely_tests.select(root)
    assert got, "no ritz0 test file changed in the last commits?"
    for f in got:
        assert (root / R0 / f).is_file(), f
        assert Path(f).name.startswith("test_") and f.endswith(".py"), f
    assert len(got) <= likely_tests.MAX_FILES


def test_serial_files_are_left_to_the_full_step(repo):
    """An xdist_group or slow file runs on one worker, one test at a time: in
    the pre-pass it would be the tail every other worker waits on.  The full
    step already schedules those first (ritz0/conftest.py item 6)."""
    commit(repo, R0 + "test_plain.py", R0 + "test_grouped.py", R0 + "test_slow.py")
    (repo / R0 / "test_grouped.py").write_text(
        'import pytest\npytestmark = pytest.mark.xdist_group("tree")\n')
    (repo / R0 / "test_slow.py").write_text(
        "import pytest\n@pytest.mark.slow\ndef test_x(): pass\n")
    assert likely_tests.select(repo) == ["test_plain.py"]


# AGAST #3623: the pre-pass hands out its costly files first, so their tests
# are not the tail seven idle workers wait on.  Costs come from the last
# gate on the host; a file it never saw (new since) leads, being both the
# likeliest to fail and of unknown cost.
def test_costliest_first_new_files_then_known_by_cost():
    files = ["new_b.py", "cheap.py", "new_a.py", "dear.py", "mid.py", "mid2.py"]
    costs = {"cheap.py": 0.5, "dear.py": 57.5, "mid.py": 4.0, "mid2.py": 4.0,
             "gone.py": 99.0}
    assert likely_tests.costliest_first(files, costs) == [
        "new_b.py", "new_a.py", "dear.py", "mid.py", "mid2.py", "cheap.py"]


def test_costliest_first_without_costs_keeps_the_order():
    files = ["b.py", "a.py", "c.py"]
    assert likely_tests.costliest_first(files, {}) == files
