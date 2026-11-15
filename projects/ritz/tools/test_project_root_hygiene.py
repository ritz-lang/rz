"""No compiled binaries tracked at the projects/ritz/ root (AGAST #3296).

A room debugging `-> [N]T` drops (#3258) compiled a dozen scratch programs at
the project root, `foo.ritz` -> `foo.ritz0` / `foo.ritz1` /
`foo.ritz1_selfhosted`, and `git add -A` committed all ~45 of them. Older ELF
leftovers (hello_test, ritz1_bin, ritzgen_test) had sat there since the import.

Two guards, each with its own test:

1. `projects/ritz/.gitignore` ignores `/*.ritz0`, `/*.ritz1` and
   `/*.ritz1_selfhosted`, anchored to the root, so the same names one directory
   down (a fixture someone means to track) are NOT hidden.
2. No file tracked directly under projects/ritz/ is an ELF, whatever its
   name. This catches extensionless binaries that no ignore pattern could
   name ahead of time, and anything force-added past the ignore.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent
COMPILED_SUFFIXES = (".ritz0", ".ritz1", ".ritz1_selfhosted")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=RITZ_ROOT, capture_output=True, text=True, check=False
    )


def _ignored(rel: str) -> bool:
    """True if `rel` (relative to projects/ritz) would be ignored by git.

    --no-index evaluates the ignore rules even for tracked or absent paths,
    which is what "would a new file here be committed by `git add -A`" means.
    """
    r = _git("check-ignore", "-q", "--no-index", "--", rel)
    assert r.returncode in (0, 1), r.stderr
    return r.returncode == 0


@pytest.mark.parametrize("suffix", COMPILED_SUFFIXES)
def test_compiled_output_at_project_root_is_ignored(suffix):
    assert _ignored(f"scratch{suffix}"), (
        f"projects/ritz/scratch{suffix} is not git-ignored; add "
        f"'/*{suffix}' to projects/ritz/.gitignore (#3296)"
    )


@pytest.mark.parametrize(
    "rel",
    [
        "scratch.ritz",  # the source itself is not ignored
        "examples/scratch.ritz0",  # the rule is anchored to the root only
        "ritz0/test/scratch.ritz1",
        "lib/scratch.ritz1_selfhosted",
    ],
)
def test_root_rule_does_not_hide_other_files(rel):
    assert not _ignored(rel), (
        f"projects/ritz/{rel} is ignored; anchor the rule with '/'"
    )


def test_no_elf_tracked_at_project_root():
    r = _git("ls-files", "-z", "--", ".")
    assert r.returncode == 0, r.stderr
    offenders = []
    for rel in filter(None, r.stdout.split("\0")):
        if "/" in rel:
            continue  # only the root itself
        path = RITZ_ROOT / rel
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as f:
                if f.read(4) == b"\x7fELF":
                    offenders.append(rel)
    assert not offenders, (
        "ELF binaries tracked at projects/ritz/ (git rm them; build output "
        f"does not belong at the project root, #3296): {offenders}"
    )
