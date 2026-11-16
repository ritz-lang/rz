"""Every `[[bin]]` convenience link is git-ignored (AGAST #3652).

build.py leaves a symlink at `<pkg_dir>/<bin name>` -> `build/<profile>/<bin
name>` for every binary it builds, because integration tests fork/exec
`./<name>` with cwd = pkg_dir. Each link is ignored by name, one pattern per
binary. `projects/tempest/tempest-tab` was never added, so every worktree that
built tempest looked dirty and `adele room rm` refused to remove it.

This walks every ritz.toml in the workspace (rz.toml members, plus the
examples regression.sh builds) and asks git whether a new file at each link
path would be ignored. Adding a `[[bin]]` without its ignore line fails here,
not in the next room teardown.
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


def _git(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=WORKSPACE, input=stdin,
        capture_output=True, text=True, check=False,
    )


def _tracked_dirs() -> set[str]:
    """Every directory holding a tracked file, relative to the workspace."""
    files = _git("ls-files").stdout.splitlines()
    return {str(Path(f).parent) for f in files} | {
        str(p) for f in files for p in Path(f).parents
    }


def bin_link_paths() -> list[str]:
    """`<pkg_dir>/<name>` for every built `[[bin]]`, relative to the workspace.

    Skips bins whose source is not Ritz (projects/ritz's ritz0.py and
    compile.sh entries: build.py never compiles those) and link paths that
    are tracked directories, where no link can be made.
    """
    tracked_dirs = _tracked_dirs()
    manifests = _git("ls-files", "--", "*ritz.toml").stdout.splitlines()
    links = []
    for manifest in manifests:
        if Path(manifest).name != "ritz.toml" or manifest.startswith(SKIP_DIRS):
            continue
        pkg = Path(manifest).parent
        config = tomllib.loads((WORKSPACE / manifest).read_text())
        for b in config.get("bin", []):
            src = b.get("path")
            if src and not src.endswith(".ritz"):
                continue
            link = str(pkg / b["name"])
            if link not in tracked_dirs:
                links.append(link)
    return links


def test_walk_finds_the_reported_link():
    # Guard the walk itself: an empty or partial list would pass vacuously.
    links = bin_link_paths()
    assert "projects/tempest/tempest-tab" in links
    assert "projects/zeus/zeus" in links
    assert "projects/ritz/examples/tier1_basics/01_hello/hello" in links
    assert "projects/ritz/ritz0" not in links


def test_every_bin_link_is_ignored():
    links = bin_link_paths()
    # --no-index: judge the ignore rules alone, as `git add -A` would for a
    # new file. -v -n prints every path, with "::" for the unmatched ones.
    r = _git("check-ignore", "--no-index", "--stdin", "-v", "-n",
             stdin="\n".join(links) + "\n")
    assert r.returncode in (0, 1), r.stderr
    unignored = [line.split("\t", 1)[1] for line in r.stdout.splitlines()
                 if line.startswith("::")]
    assert not unignored, (
        "build.py symlinks each [[bin]] to <pkg_dir>/<name>; these would be "
        "left untracked in the worktree (#3652). Ignore each by name:\n  "
        + "\n  ".join(unignored)
    )
