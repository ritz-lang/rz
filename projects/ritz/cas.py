#!/usr/bin/env python3
"""Content-addressed artifact store for compiled Ritz modules (AGAST #1808).

One store, shared by every build.py process, every test_runner process and
every worktree on the machine:

    $RITZ_CACHE_DIR            (default ~/.cache/ritz/cas)
    ├── objects/<k[:2]>/<k>.ll   LLVM IR emitted for the module
    ├── objects/<k[:2]>/<k>.o    `clang -c` of that IR
    └── meta/<k[:2]>/<k>.json    what the key was built from (debugging aid)

`k` is a sha256 over everything that determines the artifact (`module_key`):

* the compiler fingerprint (`cache.compute_compiler_hash`: ritz0's Python
  tree + build.py, or the ritz1 binary),
* the target (OS, machine, clang version),
* the flags (clang object flags, RITZ_VERIFY_IR, ...),
* the module's identity (its path relative to the repository, so two
  worktrees agree) and the sha256 of its source bytes,
* the sorted (identity, sha256) of every module in its transitive import
  closure.

Why it exists: before this, each worktree had its own `.ritz-cache` that was
wiped wholesale whenever the compiler changed, and test_runner ignored it and
recompiled every test file's ritzlib closure from scratch, so one gate
compiled ritzlib thousands of times. A key that names *everything* the
artifact depends on needs no invalidation at all: a change produces a
different key, old entries stay valid for whoever still has the old inputs
(another worktree, a bisect), and `gc` trims by least-recent use.

Concurrency: entries are immutable once written. A writer goes through a
private temp file and `os.replace`, so a reader sees the whole file or no
file. Two processes that miss on the same key both compile and both write
equivalent bytes; there is no shared index file to fight over.

Stats: `RITZ_CAS_STATS=1` prints hits/misses/bytes for the process to stderr
at exit. `RITZ_CAS_STATS_LOG=<file>` appends one JSON line per process with
the same counts plus the identity of every miss; `python3 cas.py summary
<file>` aggregates a whole gate and lists any key compiled more than once.
"""

from __future__ import annotations

import atexit
import fcntl
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional

CAS_DIR_ENV = "RITZ_CACHE_DIR"
STATS_ENV = "RITZ_CAS_STATS"
STATS_LOG_ENV = "RITZ_CAS_STATS_LOG"
# Bumped when the key layout changes, so old and new layouts never collide.
KEY_SCHEMA = "ritz-cas-v1"
DEFAULT_GC_BYTES = 4 * 1024 ** 3


def default_root() -> Path:
    env = os.environ.get(CAS_DIR_ENV)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".cache" / "ritz" / "cas"


# ============================================================================
# Key material
# ============================================================================

def _find_repo_root(start: Path) -> Optional[Path]:
    """Nearest ancestor holding `.git` (a dir, or a worktree's `.git` file)."""
    for d in [start, *start.parents]:
        if (d / ".git").exists():
            return d
    return None


# The repository this file lives in. Module identities are relative to it, so
# the same module in two worktrees gets the same key.
REPO_ROOT: Optional[Path] = _find_repo_root(Path(__file__).resolve().parent)


def module_identity(path: Path, repo_root: Optional[Path] = None) -> str:
    """Worktree-independent name of a module.

    Inside the repository: its repo-relative path. Outside it (a test's
    scratch copy of a helper, a tmp_path fixture): just the file name. The
    path only reaches the IR through DWARF `DIFile`, and the content and
    closure are keyed separately, so that is enough to tell modules apart.
    """
    root = repo_root if repo_root is not None else REPO_ROOT
    p = Path(path).resolve()
    if root is not None:
        try:
            return p.relative_to(root).as_posix()
        except ValueError:
            pass
    return "ext/" + p.name


_FILE_HASHES: Dict[tuple, str] = {}


def file_sha256(path: Path) -> str:
    """sha256 of a file, memoised per (path, size, mtime_ns) for the process."""
    p = Path(path)
    st = p.stat()
    memo_key = (str(p), st.st_size, st.st_mtime_ns)
    digest = _FILE_HASHES.get(memo_key)
    if digest is None:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 16), b""):
                h.update(chunk)
        digest = h.hexdigest()
        _FILE_HASHES[memo_key] = digest
    return digest


_TARGET: Optional[str] = None


def target_id() -> str:
    """OS, machine and clang version: what `clang -c` output depends on."""
    global _TARGET
    if _TARGET is None:
        # Popen, not subprocess.run: tests that spy on subprocess.run count
        # clang invocations, and a version probe is not a compile or a link.
        try:
            with subprocess.Popen(["clang", "--version"], stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True) as proc:
                out, _ = proc.communicate(timeout=30)
            clang = out.splitlines()[0].strip() if out else "clang-unknown"
        except (OSError, subprocess.SubprocessError):
            clang = "clang-missing"
        _TARGET = f"{sys.platform}/{platform.machine()}/{clang}"
    return _TARGET


def module_key(
    *,
    compiler_fp: str,
    source: Path,
    closure: Iterable[Path],
    flags: Dict[str, object],
    target: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> str:
    """The store key of one compiled module. See the module docstring.

    `closure` is the module's transitive imports; the module itself may be
    in it and is skipped.
    """
    src = Path(source).resolve()
    deps = sorted(
        (module_identity(d, repo_root), file_sha256(d))
        for d in {Path(d).resolve() for d in closure}
        if d != src
    )
    material = {
        "schema": KEY_SCHEMA,
        "compiler": compiler_fp,
        "target": target if target is not None else target_id(),
        "flags": flags,
        "module": [module_identity(src, repo_root), file_sha256(src)],
        "imports": deps,
    }
    blob = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


# ============================================================================
# Store
# ============================================================================

class Stats:
    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.bytes_written = 0
        self.missed: List[List[str]] = []  # [key, ext, identity]

    def as_dict(self) -> dict:
        return {"pid": os.getpid(), "argv0": Path(sys.argv[0]).name if sys.argv else "",
                "hits": self.hits, "misses": self.misses,
                "bytes_written": self.bytes_written, "missed": self.missed}


STATS = Stats()


def _report_stats() -> None:
    if STATS.hits == 0 and STATS.misses == 0:
        return
    if os.environ.get(STATS_ENV, "") not in ("", "0"):
        print(f"[ritz-cas] {Path(sys.argv[0]).name if sys.argv else '?'}: "
              f"hits={STATS.hits} misses={STATS.misses} "
              f"bytes_written={STATS.bytes_written}", file=sys.stderr)
    log = os.environ.get(STATS_LOG_ENV)
    if log:
        line = json.dumps(STATS.as_dict()) + "\n"
        try:
            with open(log, "a") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(line)
        except OSError:
            pass


atexit.register(_report_stats)


def _atomic_copy(src: Path, dst: Path) -> int:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dst.parent, prefix=f".{dst.name}.", suffix=".tmp")
    os.close(fd)
    try:
        shutil.copyfile(src, tmp)
        os.chmod(tmp, 0o644)
        os.replace(tmp, dst)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return dst.stat().st_size


def _atomic_write(dst: Path, data: bytes) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dst.parent, prefix=f".{dst.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o644)
        os.replace(tmp, dst)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class ArtifactStore:
    """Immutable key -> file store. See the module docstring."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root is not None else default_root()

    def path(self, key: str, ext: str) -> Path:
        return self.root / "objects" / key[:2] / f"{key}.{ext}"

    def meta_path(self, key: str) -> Path:
        return self.root / "meta" / key[:2] / f"{key}.json"

    def get(self, key: str, ext: str) -> Optional[Path]:
        """The stored artifact, or None. Counts a hit or a miss."""
        p = self.path(key, ext)
        if p.is_file():
            STATS.hits += 1
            try:
                os.utime(p)  # least-recently-used order for gc
            except OSError:
                pass
            return p
        STATS.misses += 1
        return None

    def put(self, key: str, ext: str, src: Path, identity: str = "") -> Path:
        """Store a copy of `src` under (key, ext), atomically."""
        dst = self.path(key, ext)
        STATS.bytes_written += _atomic_copy(Path(src), dst)
        if identity:
            STATS.missed.append([key, ext, identity])
        return dst

    def put_meta(self, key: str, meta: dict) -> None:
        _atomic_write(self.meta_path(key), json.dumps(meta, indent=1, sort_keys=True).encode())

    def gc(self, max_bytes: int) -> tuple:
        """Delete least-recently-used entries until the store fits `max_bytes`.

        Returns (files removed, bytes freed). Never removes everything just
        because it can: only the oldest files beyond the cap go.
        """
        files = []
        total = 0
        objects = self.root / "objects"
        if not objects.is_dir():
            return 0, 0
        for p in objects.rglob("*"):
            if not p.is_file() or p.name.startswith("."):
                continue
            st = p.stat()
            files.append((st.st_mtime, st.st_size, p))
            total += st.st_size
        files.sort()
        removed = freed = 0
        for _mtime, size, p in files:
            if total <= max_bytes:
                break
            try:
                p.unlink()
            except OSError:
                continue
            key = p.name.split(".", 1)[0]
            if not any(self.path(key, e).exists() for e in ("ll", "o")):
                try:
                    self.meta_path(key).unlink()
                except OSError:
                    pass
            total -= size
            freed += size
            removed += 1
        return removed, freed


# ============================================================================
# CLI
# ============================================================================

def summarise(log: Path) -> dict:
    """Aggregate a RITZ_CAS_STATS_LOG over a whole gate."""
    hits = misses = written = procs = 0
    seen: Dict[tuple, List[str]] = {}
    for line in Path(log).read_text().splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        procs += 1
        hits += rec.get("hits", 0)
        misses += rec.get("misses", 0)
        written += rec.get("bytes_written", 0)
        for key, ext, ident in rec.get("missed", []):
            seen.setdefault((key, ext), []).append(ident)
    dup = {f"{k[:12]}.{e}": ids[0] for (k, e), ids in seen.items() if len(ids) > 1}
    return {"processes": procs, "hits": hits, "misses": misses,
            "bytes_written": written, "compiled": len(seen),
            "compiled_more_than_once": dup}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Ritz content-addressed artifact store")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("path", help="print the store directory")
    g = sub.add_parser("gc", help="trim least-recently-used entries")
    g.add_argument("--max-bytes", type=int, default=DEFAULT_GC_BYTES)
    s = sub.add_parser("summary", help="aggregate a RITZ_CAS_STATS_LOG file")
    s.add_argument("log")
    args = ap.parse_args(argv)
    store = ArtifactStore()
    if args.cmd == "path":
        print(store.root)
    elif args.cmd == "gc":
        removed, freed = store.gc(args.max_bytes)
        print(f"removed {removed} files, freed {freed} bytes from {store.root}")
    elif args.cmd == "summary":
        res = summarise(Path(args.log))
        print(f"[ritz-cas] gate: processes={res['processes']} hits={res['hits']} "
              f"misses={res['misses']} compiled={res['compiled']} "
              f"bytes_written={res['bytes_written']}")
        for k, ident in sorted(res["compiled_more_than_once"].items()):
            print(f"  compiled more than once: {ident} ({k})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
