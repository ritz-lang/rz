"""ritz0/harness/tracked.py lists tracked files only (AGAST #4672).

The ratchets that ask "is X in the tree?" read the tree through it, so a
reused worktree full of ignored leftovers gives the same verdict as a fresh
checkout of the same commit.  This proves the helper ignores both kinds of
leftover omegalisk's checkout had: an ignored file under a tracked
directory, and a directory that holds nothing but ignored files.
"""

from __future__ import annotations

import subprocess

import pytest

import tracked

pytestmark = pytest.mark.integration  # git init/add in a scratch repo


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text("*.sig\n")
    (tmp_path / "test").mkdir()
    (tmp_path / "test" / "test_a.ritz").write_text("[[test]]\n")
    _git(tmp_path, "add", "-A")
    # The leftovers: ignored, and never added.
    (tmp_path / "test" / "ritzlib").mkdir()
    (tmp_path / "test" / "ritzlib" / "sys.ritz.sig").write_text("x")
    (tmp_path / "sched").mkdir()
    (tmp_path / "sched" / "mod.ritz.sig").write_text("x")
    (tmp_path / "untracked.ritz").write_text("x")
    return tmp_path


def test_lists_tracked_files_only(repo):
    got = [p.relative_to(repo).as_posix() for p in tracked.tracked(root=repo)]
    assert got == [".gitignore", "test/test_a.ritz"]


def test_leftover_directory_is_not_tracked(repo):
    assert (repo / "sched").exists()
    assert not tracked.is_tracked("sched", root=repo)
    assert tracked.tracked(repo / "test", root=repo) == [repo / "test" / "test_a.ritz"]


def test_prefix_is_a_path_component(repo):
    """`test` must not match `tests/...` or `test_x`."""
    (repo / "tests").mkdir()
    (repo / "tests" / "b.ritz").write_text("x")
    _git(repo, "add", "tests/b.ritz")
    tracked._ls_files.cache_clear()
    assert tracked.tracked("test", root=repo) == [repo / "test" / "test_a.ritz"]
