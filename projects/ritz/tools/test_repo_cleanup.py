"""Repo cleanup sweep (AGAST #1875, LARB v4 review/4/packages.md M10).

Pins the acceptance facts so the cruft cannot creep back:

  (a) no agent transcripts, duplicate font or generated image is tracked;
  (b) spectree and angelo-simple are archived (outside the workspace, with
      the reason recorded in archive/README.md) and ritzutils is merged into
      indium;
  (c) ritzunit/patches, ritzunit/known_issues and nexus/wiki are gone.

The manifest half of the ticket, (d), is pinned in test_nested_packages.py.

Run with:
    python3 -m pytest projects/ritz/tools/test_repo_cleanup.py -q
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[3]
PROJECTS = WORKSPACE / "projects"
ARCHIVE = WORKSPACE / "archive"

pytestmark = pytest.mark.unit


@pytest.fixture(scope="module")
def rz():
    spec = importlib.util.spec_from_loader(
        "rz_1875", importlib.machinery.SourceFileLoader("rz_1875", str(WORKSPACE / "rz"))
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_no_transcripts_or_generated_assets_are_tracked():
    # The ticket's acceptance command (a), verbatim.
    files = subprocess.run(
        ["git", "ls-files"], cwd=WORKSPACE, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    bad = re.compile(r"logs/claude_transcript|prism/hello\.ppm|^projects/angelo/aadhunik\.ttf")
    assert [f for f in files if bad.search(f)] == []


@pytest.mark.parametrize("rel", [
    "ritzunit/patches",       # superseded: io.ritz already takes @String
    "ritzunit/known_issues",  # in no gate
    "nexus/wiki",             # restated the READMEs, with false claims
])
def test_superseded_trees_are_gone(rel):
    assert not (PROJECTS / rel).exists()


@pytest.mark.parametrize("pkg", ["spectree", "angelo-simple"])
def test_archived_package_is_out_of_the_workspace(rz, pkg):
    assert pkg not in rz.discover_projects()
    assert not (PROJECTS / pkg).exists()
    assert (ARCHIVE / pkg / "ritz.toml").is_file()


@pytest.mark.parametrize("pkg", ["spectree", "angelo-simple"])
def test_archive_records_why(pkg):
    # A section per package with a non-empty reason under it.
    text = (ARCHIVE / "README.md").read_text()
    m = re.search(rf"^## {re.escape(pkg)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert m, f"archive/README.md has no '## {pkg}' section"
    assert m.group(1).strip(), f"archive/README.md gives no reason for {pkg}"


def test_ritzutils_is_merged_into_indium(rz):
    assert "ritzutils" not in rz.discover_projects()
    assert not (PROJECTS / "ritzutils").exists()
    indium = tomllib.loads((PROJECTS / "indium" / "ritz.toml").read_text())
    cat = [b for b in indium.get("bin", []) if b["name"] == "cat"]
    assert len(cat) == 1 and cat[0]["entry"] == "cat::main"
    assert (PROJECTS / "indium" / "user" / "cat.ritz").is_file()
