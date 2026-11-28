#!/usr/bin/env python3
"""The builder image's content key (AGAST #4903, epic #4783).

main.yml's `builder-image` job (and `projects/builder/test.sh`) used to tag
every commit's image `:<commit>` alone, so huburght's Woodpecker waited
~5 min for a fresh bootstrap even when a push touched only
`projects/buddhafinger` and the image that would come out was byte-for-byte
the one already published. This module's key says whether that bootstrap
is needed: a sha256 over the git tree hash of every input that actually
feeds the image (`projects/builder/README.md`, "Survey: what a build
executes"), so a commit that moves none of them gets the same key as its
parent and `builder-image` can retag instead of rebuild.

    python3 projects/ritz/tools/builder_src_key.py [-v] [<commit>]

Prints the key (sha256, truncated to 16 hex chars: short enough for a
Docker tag, `:src-<key>`, long enough that this registry's handful of
images will never collide). `-v` also prints, to stderr, the sorted
"<path> <git-tree-hash>" lines the key was computed from.

The input list is two parts:

- `BOOTSTRAP_ROOTS` / `BUILDER_ROOTS` below: what the Dockerfile's
  `bootstrap` stage builds from (ritz0 compiles ritz1, stage 1; ritz1
  compiles itself, stage 2; `check_fixed_point.sh` re-derives stage 3 from
  the same two) and the builder's own recipe for it (the Dockerfile itself,
  which pins `BASE` and `LLVM_MAJOR`, and the scripts it runs there).
- `staged_roots()`: what `stage_tree.py` copies into `/stage`, read from
  `stage_tree`'s own lists and `library_packages()` rather than copied here
  a second time, so the two cannot drift apart (test_builder_src_key.py's
  `test_staged_roots_tracks_stage_tree_py` is the regression test for that:
  it fails if `stage_tree.py` grows a list this module doesn't consult).

Deliberately absent: `projects/buddhafinger` and every other matrix
package (`projects/ritz/tools/builder_matrix.py`'s `MATRIX_PACKAGES`). None
of them is named as a path dependency by any shipped package's `ritz.toml`
(`rz.toml`'s `[workspace.exclude]` entry for buddhafinger says why it isn't
swept at all), so `stage_tree.library_packages()` never returns it and this
module never hashes it. A package that starts being path-depended-on by a
shipped package would start moving this key on its own changes, which is
the bug this ticket exists to keep from reappearing elsewhere
(`test_matrix_packages_are_not_inputs` pins today's list).

A path below that does not exist at `<commit>` (deleted, or one of the
generated/ignored directories — `ritz1/build`, `__pycache__` — that `git
rev-parse` correctly treats as absent from the tree) hashes as 40 zeros, so
a key still comes out instead of a crash; `rev-parse` on a workspace with
nothing checked out there is itself the proof that the tree has no such
path, which is a valid key input, not a tooling error.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent          # projects/ritz/tools
RITZ_DIR = TOOLS_DIR.parent                          # projects/ritz
WORKSPACE = TOOLS_DIR.parents[2]                     # repo root
BUILDER_DIR = WORKSPACE / "projects" / "builder"

if str(BUILDER_DIR) not in sys.path:
    sys.path.insert(0, str(BUILDER_DIR))
import stage_tree  # noqa: E402

# What the Dockerfile's `bootstrap` stage builds from, not what stage_tree
# copies out of it: ritz0 (stage 1, ritz0 -> ritz1), ritz1 (stage 2, ritz1
# -> ritz1_selfhosted; its own `test/` and docs are tracked by git but not
# read by `make ritz1-bootstrap`, and ritz1/build is untracked, so neither
# moves this key — see the module docstring on a path git has no tree for),
# `requirements.lock` (llvmlite's pin, and pytest's), and the top Makefile,
# whose `ritz1-bootstrap` target is what the Dockerfile RUNs.
BOOTSTRAP_ROOTS = (
    "projects/ritz/ritz0",
    "projects/ritz/ritz1",
    "projects/ritz/requirements.lock",
    "projects/ritz/Makefile",
)

# The builder's own build recipe, and the two files its runtime stage COPYs
# in beside /rz: entrypoint.sh (`rz-builder`) and summary.py. Without those
# an entrypoint fix never reached an image whose key it left alone (AGAST
# #4865: the cache-eviction fix ran the old entrypoint in three gates). Not
# test.sh, accept.sh, README.md or Dockerfile.dockerignore: a `git archive`
# build (what test.sh and main.yml's builder-image job both use) never looks
# at any of those, and a .dockerignore only matters to a context built from
# a working tree.
BUILDER_ROOTS = (
    "projects/builder/Dockerfile",
    "projects/builder/stage_tree.py",
    "projects/builder/check_fixed_point.sh",
    "projects/builder/collect_toolchain.sh",
    "projects/builder/entrypoint.sh",
    "projects/builder/summary.py",
)


def staged_roots(root: Path) -> list[str]:
    """What stage_tree.py copies into /stage, as root-relative posix paths.

    Reads stage_tree's own lists and library_packages(root) rather than
    repeating them, so this module cannot drift from what the image
    actually stages (AGAST #4903's build note)."""
    roots = [*stage_tree.PYTHON_FILES, *stage_tree.DATA_FILES, *stage_tree.ALWAYS,
             "projects/ritz/ritzlib"]
    roots += [p.relative_to(root).as_posix()
              for p in sorted((root / "known-failures").glob("*.toml"))]
    roots += [p.relative_to(root).as_posix()
              for p in sorted((root / "projects/ritz/runtime").glob("*.ll"))]
    ritz = (root / "projects/ritz").resolve()
    for pkg in stage_tree.library_packages(root):
        if pkg == ritz or pkg.is_relative_to(ritz):
            continue
        roots.append(pkg.relative_to(root).as_posix())
    return roots


def input_roots(root: Path) -> list[str]:
    """Every path this key hashes, sorted and de-duplicated."""
    return sorted(set(BOOTSTRAP_ROOTS) | set(BUILDER_ROOTS) | set(staged_roots(root)))


def _git_tree_hash(root: Path, commit: str, relpath: str) -> str:
    """<commit>'s git object hash of relpath (blob or tree); 40 zeros if
    <commit> has no tree there (deleted, or generated/untracked)."""
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "-q", "--verify", f"{commit}:{relpath}"],
        capture_output=True, text=True)
    if result.returncode != 0:
        return "0" * 40
    return result.stdout.strip()


def key_lines(root: Path, commit: str = "HEAD") -> list[str]:
    """Sorted "<path> <git-tree-hash>" lines: the key's exact input."""
    return [f"{p} {_git_tree_hash(root, commit, p)}" for p in input_roots(root)]


def src_key(root: Path, commit: str = "HEAD") -> str:
    """The content key: sha256 of key_lines(), truncated to 16 hex chars."""
    text = "\n".join(key_lines(root, commit))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def main(argv: list[str]) -> int:
    args = argv[1:]
    verbose = "-v" in args
    args = [a for a in args if a != "-v"]
    commit = args[0] if args else "HEAD"
    if verbose:
        for line in key_lines(WORKSPACE, commit):
            print(line, file=sys.stderr)
    print(src_key(WORKSPACE, commit))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
