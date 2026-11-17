"""Every `[[bin]]` `path` in a ritz.toml names a tracked file (AGAST #3912).

projects/ritz/ritz.toml once declared `ritz1` with `path = "ritz1/compile.sh"`.
build.py skips any non-`.ritz` path, so the entry built nothing and nothing
ran it; it only pinned compile.sh in place. ritz1 is built by
`make -C projects/ritz ritz1`. A `[[bin]]` whose path is gone would go
unnoticed the same way, so this fails on it instead.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

WORKSPACE = Path(__file__).resolve().parents[3]

# Retired code nothing builds (rz.toml [workspace].exclude, AGAST #1405).
SKIP_DIRS = ("projects/ritz/docs/archive/",)


def _tracked() -> list[str]:
    return subprocess.run(
        ["git", "ls-files"], cwd=WORKSPACE,
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()


def bin_paths() -> list[tuple[str, str, str]]:
    """(manifest, bin name, workspace-relative path) for every `path =` bin."""
    out = []
    for manifest in _tracked():
        if Path(manifest).name != "ritz.toml" or manifest.startswith(SKIP_DIRS):
            continue
        config = tomllib.loads((WORKSPACE / manifest).read_text())
        for b in config.get("bin", []):
            if "path" in b:
                path = (Path(manifest).parent / b["path"]).as_posix()
                out.append((manifest, b["name"], path))
    return out


def test_walk_finds_path_bins():
    # Guard the walk: an empty list would pass the real test vacuously.
    names = {(m, n) for m, n, _ in bin_paths()}
    assert ("projects/ritz/ritz.toml", "ritz0") in names


def test_every_bin_path_is_a_tracked_file():
    tracked = set(_tracked())
    missing = [f"{m}: [[bin]] {n} -> {p}" for m, n, p in bin_paths()
               if p not in tracked]
    assert not missing, "[[bin]] path names no tracked file:\n" + "\n".join(missing)


def test_ritz_manifest_declares_no_ritz1_bin():
    # ritz1 is Makefile-built (`make -C projects/ritz ritz1`); build.py never
    # built the manifest entry, so it must not come back pointing at a script.
    config = tomllib.loads((WORKSPACE / "projects/ritz/ritz.toml").read_text())
    assert "ritz1" not in [b["name"] for b in config.get("bin", [])]
