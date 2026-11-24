"""`build.py test --all` (`make examples`) doesn't sweep docs/archive (AGAST #4648).

rz.toml's [workspace.exclude] keeps projects/ritz/docs/archive out of the
workspace: "retired, non-authoritative code; nothing in it should build".
manifest.find_all_packages, which `build.py build/test --all` walks from the
current directory, globbed every ritz.toml and so built
docs/archive/ritz1_old, whose [[bin]] names a src/ritz1.ritz that was never
committed: `make examples` failed on it in every fresh checkout.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RITZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RITZ))

import manifest  # noqa: E402

pytestmark = pytest.mark.unit

TOML = '[package]\nname = "{name}"\nversion = "0.1.0"\n'


def _pkg(root: Path, rel: str) -> Path:
    d = root / rel
    d.mkdir(parents=True)
    (d / "ritz.toml").write_text(TOML.format(name=d.name))
    return d


def test_archive_packages_are_not_found(tmp_path):
    live = _pkg(tmp_path, "examples/hello")
    _pkg(tmp_path, "docs/archive/old_compiler")
    found = [p for p, _ in manifest.find_all_packages(tmp_path)]
    assert found == [live.resolve()]


def test_a_package_merely_named_archive_is_still_found(tmp_path):
    # Only docs/archive is retired; an `archive` package elsewhere builds.
    pkg = _pkg(tmp_path, "examples/archive")
    found = [p for p, _ in manifest.find_all_packages(tmp_path)]
    assert found == [pkg.resolve()]


def test_the_real_tree_has_no_archive_package():
    found = manifest.find_all_packages(RITZ)
    archive = (RITZ / "docs" / "archive").resolve()
    assert not [p for p, _ in found if archive in p.parents or p == archive]
