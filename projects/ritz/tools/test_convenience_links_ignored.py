"""Every package's `./<name>` build link is git-ignored (AGAST #4217).

build_pipeline.link_convenience_binary() drops a symlink `<pkg>/<name>` into
build/<profile>/<name> for each hosted [[bin]], so tests can exec `./<name>`.
An unignored link is an untracked file after any build, and `adele room rm`
refuses to tear down a worktree holding one (#1387, #4217: 53_async's
async_test and 55_async_state_machine's async_state_machine_test, whose
.gitignore entries still named the pre-tier `examples/53_async/` layout).

Building every package to watch `git status` would cost minutes; instead this
asks the manifest code which links a build would create (the same
plan_binaries() + wants_convenience_link() build_package uses) and asks git
whether each path is ignored.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = RITZ_ROOT.parent.parent

sys.path.insert(0, str(RITZ_ROOT))
import manifest  # noqa: E402


def _git(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def _convenience_links() -> list[str]:
    """Repo-relative `<pkg>/<name>` for every link a build would create."""
    r = _git("ls-files", "-z", "--", "*ritz.toml")
    assert r.returncode == 0, r.stderr
    links = []
    for rel in filter(None, r.stdout.split("\0")):
        toml = REPO_ROOT / rel
        if not toml.is_file():
            continue  # deleted in the working tree
        plan = manifest.plan_binaries(toml.parent, manifest.load(toml))
        for bin_config in plan.buildable:
            if manifest.wants_convenience_link(bin_config):
                links.append(str(Path(rel).parent / bin_config.name))
    return links


@pytest.fixture(scope="module")
def links() -> list[str]:
    return _convenience_links()


def test_walk_finds_the_links(links):
    # Guard against a vacuous pass if manifest discovery breaks.
    assert "projects/ritz/examples/tier5_async/53_async/async_test" in links
    assert "projects/ritz/examples/tier1_basics/01_hello/hello" in links
    assert len(links) > 50


def test_every_convenience_link_is_ignored(links):
    # --no-index: judge the ignore rules alone, whether or not the link exists.
    r = _git("check-ignore", "--no-index", "--stdin", stdin="\n".join(links) + "\n")
    assert r.returncode in (0, 1), r.stderr
    ignored = set(r.stdout.splitlines())
    offenders = [link for link in links if link not in ignored]
    assert not offenders, (
        "build convenience links not git-ignored; a build leaves them untracked "
        "and blocks room teardown. Add each path to the nearest .gitignore "
        f"(#4217): {offenders}"
    )
