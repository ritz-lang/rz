"""`build.py build|test --all` honours rz.toml's [workspace.exclude] (AGAST #4644).

`./rz build --all` skipped every [workspace.exclude] entry, but
`build.py --all` (and so `make examples`) used its own `**/ritz.toml` glob,
which knew nothing about the list. It swept
docs/archive/ritz1_old, retired code that "nothing in it should build", so
`make examples` was red on every base.

manifest.find_all_packages now finds the enclosing rz.toml and drops each
excluded directory and everything below it, matched by path component,
the same rule rz's workspace_exclusions uses. One exception: an exclusion
that contains the walk's own start directory does not apply. A walk that
starts inside an excluded tree asked for it, as tools/example_tests.py does
for examples/ (and `make examples` now does too).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RITZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RITZ))

import manifest

pytestmark = pytest.mark.unit


def _pkg(root: Path, rel: str) -> Path:
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "ritz.toml").write_text(
        f'[package]\nname = "{d.name}"\nversion = "0.1.0"\n')
    return d


@pytest.fixture
def ws(tmp_path):
    """A throwaway workspace: rz.toml excluding projects/a/archive."""
    (tmp_path / "rz.toml").write_text(
        '[workspace]\nmembers = ["projects/**"]\n\n'
        '[workspace.exclude]\n'
        '"projects/a/archive" = "retired code"\n')
    _pkg(tmp_path, "projects/a")
    _pkg(tmp_path, "projects/a/examples/one")
    _pkg(tmp_path, "projects/a/archive/old")
    # An excluded manifest is not even read: a broken one must not matter.
    bad = tmp_path / "projects/a/archive/broken"
    bad.mkdir(parents=True)
    (bad / "ritz.toml").write_text("this is [not toml\n")
    return tmp_path


def _names(found):
    return sorted(d.name for d, _ in found)


def test_an_excluded_ritz_toml_is_not_walked(ws):
    found = manifest.find_all_packages(ws / "projects/a")
    assert _names(found) == ["a", "one"]


def test_a_walk_that_starts_inside_an_excluded_tree_walks_it(ws):
    found = manifest.find_all_packages(ws / "projects/a/archive/old")
    assert _names(found) == ["old"]


def test_exclusion_matches_by_path_component(tmp_path):
    (tmp_path / "rz.toml").write_text(
        '[workspace.exclude]\n"projects/a/ex" = "covered elsewhere"\n')
    _pkg(tmp_path, "projects/a/ex/pkg")
    _pkg(tmp_path, "projects/a/examples/pkg2")
    assert _names(manifest.find_all_packages(tmp_path / "projects")) == ["pkg2"]


def test_no_rz_toml_walks_everything(tmp_path):
    _pkg(tmp_path, "a")
    _pkg(tmp_path, "a/archive/old")
    assert _names(manifest.find_all_packages(tmp_path / "a")) == ["a", "old"]


def test_the_real_walk_skips_docs_archive_and_keeps_examples():
    """`make examples` walks examples/: the archive is out, examples are in."""
    from_ritz = [d for d, _ in manifest.find_all_packages(RITZ)]
    assert not [d for d in from_ritz if "docs/archive" in d.as_posix()]
    examples = manifest.find_all_packages(RITZ / "examples")
    assert len(examples) > 50, "examples/ walk lost its packages"
