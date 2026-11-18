"""A freestanding binary gets no `<pkg>/<name>` convenience link (AGAST #4131).

build.py links `<pkg>/<name>` -> `build/<profile>/<name>` so host tests that
run with cwd=<pkg> can fork/exec `./<name>`. A freestanding binary (target
x86_64-unknown-none, harland, uefi...) cannot run on the host, and its
consumers (indium's Makefile and mkiso.sh, harland's test_tier1_boot.sh) copy
`build/<profile>/*.elf`. The link only dirtied the package root: every new
indium bin needed its own `.gitignore` line, and a tree built before that
line existed kept an untracked `projects/indium/fault_child` that blocked
`adele room rm`'s clean-worktree check.

The rule: freestanding binaries stay under build/; hosted binaries keep their
link. The end-to-end test is the ticket's: build a package in a clean git
tree and `git status --porcelain --ignored` names nothing but build/ and the
hosted link.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
BUILD_PY = PKG_DIR / "build.py"
INDIUM = PKG_DIR.parent / "indium"


@pytest.fixture
def buildpy(request):
    sys.path.insert(0, str(PKG_DIR))
    request.addfinalizer(lambda: sys.path.remove(str(PKG_DIR)))
    spec = importlib.util.spec_from_file_location("ritz_buildpy_4131", BUILD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cfg(buildpy, freestanding: bool):
    return buildpy.BinaryConfig(
        name="x", src_path=Path("x.ritz"), additional_sources=[], freestanding=freestanding
    )


@pytest.mark.unit
def test_unit_freestanding_binary_gets_no_convenience_link(buildpy):
    assert buildpy.wants_convenience_link(_cfg(buildpy, freestanding=True)) is False


@pytest.mark.unit
def test_unit_hosted_binary_keeps_its_convenience_link(buildpy):
    assert buildpy.wants_convenience_link(_cfg(buildpy, freestanding=False)) is True


MANIFEST = """\
[package]
name = "mini_indium"
version = "0.1.0"
sources = ["user", "src"]

[[bin]]
name = "true"
entry = "true::main"
target = "x86_64-unknown-none"
target_os = "harland"
sources = ["user"]
freestanding = true
link_runtime = true

[bin.true.linker]
script = "user/linker_pie.ld"

[bin.true.flags]
pic = true

[[bin]]
name = "hosted"
entry = "hosted::main"
"""


@pytest.fixture
def mini_repo(tmp_path):
    """A clean git tree holding one indium freestanding bin and one hosted bin."""
    pkg = tmp_path / "mini_indium"
    shutil.copytree(INDIUM / "user", pkg / "user")
    (pkg / "src").mkdir()
    (pkg / "src" / "hosted.ritz").write_text("fn main() -> i32\n    0\n")
    (pkg / "ritz.toml").write_text(MANIFEST)
    # build/ as the repo root ignores it; the hosted link as .gitignore lists
    # the hosted links it keeps.
    (pkg / ".gitignore").write_text("build/\n/hosted\n")

    def git(*args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
            cwd=pkg, capture_output=True, text=True, check=True,
        ).stdout

    git("init", "-q")
    git("add", "-A")
    git("commit", "-qm", "fixture")
    return pkg, git


@pytest.mark.integration
def test_e2e_build_leaves_only_build_dir_and_hosted_link(mini_repo):
    pkg, git = mini_repo
    env = dict(os.environ, RITZ_PATH=str(PKG_DIR))
    r = subprocess.run(
        [sys.executable, str(BUILD_PY), "build", str(pkg)],
        capture_output=True, text=True, cwd=PKG_DIR, env=env, check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert (pkg / "build" / "debug" / "true.elf").is_file()

    assert not (pkg / "true").is_symlink() and not (pkg / "true").exists(), (
        "freestanding bin got a <pkg>/true convenience link (#4131)"
    )
    assert (pkg / "hosted").is_symlink(), "hosted bin lost its convenience link"

    status = sorted(git("status", "--porcelain", "--ignored").splitlines())
    assert status == ["!! build/", "!! hosted"], status
