"""builder_src_key.py: the builder image's content key (AGAST #4903).

Pins what the key must do:

- a commit that touches only `projects/buddhafinger` (or another matrix
  package: `test_matrix_packages_are_not_inputs`) keeps the key, so
  `builder-image` can retag `:src-<key>` instead of re-bootstrapping
  `ritz1_selfhosted`;
- a commit that touches ritz0, ritz1, ritzlib, a runtime shim, a library
  package some shipped package path-depends on, or the builder's own
  recipe (Dockerfile, stage_tree.py, ...) changes the key;
- the input list is read from `stage_tree.py`'s own lists and
  `library_packages()`, not copied, so the two cannot drift apart
  (`test_staged_roots_tracks_stage_tree_py`).

Mutation-check for each "changes the key" test: only the fixture's own
commit moves (buddhafinger alone never does), so breaking one input's
plumbing cannot hide behind another test going green.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import builder_src_key  # noqa: E402
import builder_matrix  # noqa: E402

REPO_ROOT = TOOLS_DIR.parents[2]

pytestmark = pytest.mark.integration  # git init/commit in a scratch repo


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _write(repo: Path, rel: str, content: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _commit(repo: Path, changes: dict[str, str], message: str) -> str:
    """Apply changes (path -> content), commit, return the new commit hash."""
    for rel, content in changes.items():
        _write(repo, rel, content)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                           check=True, capture_output=True, text=True).stdout.strip()


# A minimal tree with one of everything builder_src_key.input_roots() names:
# ritz0/ritz1 sources, ritzlib (also a library_packages() hit through
# widget's dependency), a runtime shim, the builder's recipe files, a
# library package (widget) a shipped package (sage) path-depends on, and
# buddhafinger, which nothing depends on.
_BASE = {
    "projects/ritz/ritz0/lexer.py": "# ritz0 v1\n",
    "projects/ritz/ritz1/src/main.ritz": "// ritz1 v1\n",
    "projects/ritz/requirements.lock": "llvmlite==1\n",
    "projects/ritz/Makefile": "ritz1-bootstrap:\n\t@echo v1\n",
    "projects/ritz/ritzlib/ritz.toml": "[package]\nname = \"ritzlib\"\n",
    "projects/ritz/ritzlib/io.ritz": "// ritzlib v1\n",
    "projects/ritz/runtime/ritz_start.ll": "; shim v1\n",
    "projects/builder/Dockerfile": "FROM scratch\n# v1\n",
    "projects/builder/stage_tree.py": "# placeholder, not imported by this fixture\n",
    "projects/builder/check_fixed_point.sh": "#!/bin/sh\n# v1\n",
    "projects/builder/collect_toolchain.sh": "#!/bin/sh\n# v1\n",
    "known-failures/placeholder.toml": "# none yet\n",
    "projects/ritz/ritz.toml": "[package]\nname = \"ritz\"\n",
    "projects/widget/ritz.toml": (
        "[package]\nname = \"widget\"\n\n"
        "[dependencies]\nritzlib = { path = \"../ritz/ritzlib\" }\n"),
    "projects/widget/src/lib.ritz": "// widget v1\n",
    "projects/sage/ritz.toml": (
        "[package]\nname = \"sage\"\n\n"
        "[dependencies]\nwidget = { path = \"../widget\" }\n"),
    "projects/sage/src/main.ritz": "// sage v1\n",
    "projects/buddhafinger/ritz.toml": "[package]\nname = \"buddhafinger\"\n",
    "projects/buddhafinger/src/main.ritz": "// buddhafinger v1\n",
}


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    sha = _commit(tmp_path, _BASE, "base")
    return tmp_path, sha


def test_staged_roots_includes_a_path_dependency_but_not_buddhafinger(repo):
    root, _ = repo
    roots = builder_src_key.staged_roots(root)
    assert "projects/widget" in roots
    assert "projects/buddhafinger" not in roots
    assert "projects/ritz/ritzlib" in roots


def test_buddhafinger_only_diff_keeps_the_key(repo):
    root, sha_a = repo
    sha_b = _commit(root, {"projects/buddhafinger/src/main.ritz": "// buddhafinger v2\n"},
                     "buddhafinger only")
    assert builder_src_key.src_key(root, sha_a) == builder_src_key.src_key(root, sha_b)


@pytest.mark.parametrize("rel,content", [
    ("projects/ritz/ritz0/lexer.py", "# ritz0 v2\n"),
    ("projects/ritz/ritz1/src/main.ritz", "// ritz1 v2\n"),
    ("projects/ritz/ritzlib/io.ritz", "// ritzlib v2\n"),
    ("projects/ritz/runtime/ritz_start.ll", "; shim v2\n"),
    ("projects/builder/Dockerfile", "FROM scratch\n# v2\n"),
    ("projects/widget/src/lib.ritz", "// widget v2\n"),
])
def test_an_input_diff_changes_the_key(repo, rel, content):
    root, sha_a = repo
    sha_b = _commit(root, {rel: content}, f"touch {rel}")
    assert builder_src_key.src_key(root, sha_a) != builder_src_key.src_key(root, sha_b)


def test_a_new_library_dependency_starts_moving_the_key(repo):
    """A package nothing depends on (buddhafinger) does not move the key;
    the moment some shipped package names it as a path dependency,
    library_packages() picks it up and it does -- proving the exclusion is
    "not a dependency", not "named buddhafinger"."""
    root, sha_a = repo
    sha_b = _commit(root, {
        "projects/widget/ritz.toml": (
            "[package]\nname = \"widget\"\n\n"
            "[dependencies]\n"
            "ritzlib = { path = \"../ritz/ritzlib\" }\n"
            "buddhafinger = { path = \"../buddhafinger\" }\n"),
    }, "widget now depends on buddhafinger")
    assert builder_src_key.src_key(root, sha_a) != builder_src_key.src_key(root, sha_b)


def test_missing_path_hashes_as_zeros_not_a_crash(repo):
    root, sha_a = repo
    lines = builder_src_key.key_lines(root, sha_a)
    assert any("known-failures" in line for line in lines)
    assert all(len(line.rsplit(" ", 1)[-1]) == 40 for line in lines)


def test_staged_roots_tracks_stage_tree_py(repo, monkeypatch):
    """staged_roots() reads stage_tree's lists; it must not keep a second,
    hand-maintained copy that can drift from them (the ticket's "a test
    fails if the key's input list and what the image stages drift apart")."""
    root, _ = repo
    monkeypatch.setattr(builder_src_key.stage_tree, "PYTHON_FILES",
                         [*builder_src_key.stage_tree.PYTHON_FILES,
                          "projects/ritz/a_new_module.py"])
    assert "projects/ritz/a_new_module.py" in builder_src_key.staged_roots(root)


def test_matrix_packages_are_not_inputs(tmp_path):
    """Every package builder_matrix.py's MATRIX_PACKAGES runs (today just
    buddhafinger) must stay out of the real repo's input list: that is the
    whole point of the key (AGAST #4903).

    Exports HEAD with `git archive`, the same clean-tree view test.sh and
    this key's real callers use (projects/builder/test.sh's own context),
    rather than scanning this checkout's live working tree: `rz test`'s own
    package runs leave transient `build/*/ritz.toml` fixtures under
    projects/ritz/build while tools-unit's other workers run concurrently,
    and library_packages()'s rglob has no reason to skip them (they are
    real paths, just not tracked by git) -- a false "buddhafinger is an
    input" or a FileNotFoundError race, neither of which says anything
    about this module."""
    archive = subprocess.run(["git", "-C", str(REPO_ROOT), "archive", "HEAD"],
                              capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(tmp_path)], input=archive, check=True)
    roots = set(builder_src_key.input_roots(tmp_path))
    for pkg in builder_matrix.MATRIX_PACKAGES:
        assert f"projects/{pkg}" not in roots


def test_key_is_a_stable_short_hex_string(repo):
    root, sha = repo
    key = builder_src_key.src_key(root, sha)
    assert len(key) == 16
    assert all(c in "0123456789abcdef" for c in key)
    assert key == builder_src_key.src_key(root, sha)
