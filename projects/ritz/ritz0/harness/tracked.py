"""The files git tracks, for ratchets that ask "is X in the tree?" (AGAST #4672).

A ratchet that globs or stats the working tree sees whatever a previous run
left behind: ignored build products (`*.ritz.sig` beside a source a test
compiled in place) and the directories they keep alive after the sources
went.  omegalisk's shared checkout failed two ratchets that way
(`ritz1/test/ritzlib/*.sig`, `harland/kernel/src/sched/mod.ritz.sig`), while a
fresh worktree of the same commit passed: the verdict depended on the
checkout, not the commit.  Read the tree through `tracked()` instead, and a
reused worktree gives the same verdict as a fresh one.

`git ls-files` is a spawn, which spawn_guard fails in a non-`integration`
test; this is bookkeeping, not the test's own work (the read guard's git
call is the precedent), so it runs `unwatched()`.  One call per process:
the index does not change under a test session.
"""

from __future__ import annotations

import functools
import subprocess
from pathlib import Path

try:
    import spawn_guard as _sg
except ImportError:  # imported outside a pytest session
    _sg = None

# The workspace root: harness/ -> ritz0/ -> ritz/ -> projects/ -> root.
WORKSPACE = Path(__file__).resolve().parents[4]


@functools.lru_cache(maxsize=None)
def _ls_files(root: str) -> frozenset[str]:
    cmd = ["git", "-C", root, "ls-files", "-z"]
    if _sg is not None:
        with _sg.unwatched():
            out = subprocess.run(cmd, capture_output=True, check=True).stdout
    else:
        out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return frozenset(p for p in out.decode().split("\0") if p)


def tracked(under: Path | str = "", *, root: Path | str = WORKSPACE) -> list[Path]:
    """Every tracked file at or below `under` (absolute, or relative to
    `root`), as absolute paths, sorted.  Untracked and ignored files are
    never listed, whatever the working tree holds."""
    root = Path(root).resolve()
    under = Path(under)
    rel = (under.resolve() if under.is_absolute() else (root / under)).relative_to(root)
    prefix = "" if str(rel) == "." else rel.as_posix()
    files = _ls_files(str(root))
    hits = (f for f in files if not prefix or f == prefix or f.startswith(prefix + "/"))
    return sorted(root / f for f in hits)


def is_tracked(path: Path | str, *, root: Path | str = WORKSPACE) -> bool:
    """Whether `path` is a tracked file or a directory holding one."""
    return bool(tracked(path, root=root))
