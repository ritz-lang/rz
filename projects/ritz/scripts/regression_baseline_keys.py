#!/usr/bin/env python3
"""Cache keys for regression.sh's Stage 1 (ritz0) baseline (AGAST #1806).

Stage 1 builds every example with ritz0, runs its test.sh and records its
stdout and exit code. That observation is a function of:

  * the ritz0 compiler: `cache.compute_compiler_hash(root, "ritz0")`, which
    hashes every codegen-relevant ritz0/*.py plus build.py, the same
    fingerprint the build cache uses;
  * the toolchain: clang (codegen, link), opt / llvm-as (build.py verifies
    and assembles with them when present), the Python running ritz0, the
    machine;
  * the RITZ_* environment build.py and ritz0 read (RITZ_VERIFY_IR turns the
    IR verifier on, RITZ_PATH moves import resolution), except the two this
    harness sets for itself;
  * what every example links against or is run by: ritzlib/, runtime/,
    cache.py, and regression.sh itself (the run sandbox, environment and
    budgets live there);
  * where it runs: BUILD_DIR, because the per-example sandbox lives under it
    and a program that prints its cwd prints that path;
  * the example: its whole tree plus every `path = "..."` dependency named in
    its ritz.toml.

Usage:
    regression_baseline_keys.py ROOT BUILD_DIR HARNESS EXTRA -- NAME=DIR ...

Prints one `NAME<TAB>KEY` line per example. EXTRA is folded into every key
(regression.sh passes its run budgets). Changing one example changes only its
key; changing anything global changes all of them.
"""

import hashlib
import importlib.util
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

KEY_VERSION = "regression-baseline-v1"

# Generated next to sources by builds and test runs; never an input.
SKIP_DIRS = {"build", "__pycache__", ".pytest_cache", ".regression", ".regression-cache"}
SKIP_DIR_PREFIXES = (".ritz-cache",)
SKIP_SUFFIXES = (".ritz.sig", ".o", ".bc", ".pyc")

PATH_DEP = re.compile(r'path\s*=\s*"([^"]+)"')


def _load_cache_module():
    here = Path(__file__).resolve().parent.parent / "cache.py"
    spec = importlib.util.spec_from_file_location("ritz_cache_baseline", here)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tree_hash(root: Path) -> str:
    """Content hash of every input file under `root`, by relative path."""
    h = hashlib.sha256()
    if root.is_file():
        h.update(root.read_bytes())
        return h.hexdigest()
    if not root.is_dir():
        return "absent"
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if d not in SKIP_DIRS and not d.startswith(SKIP_DIR_PREFIXES)
        )
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            # Symlinks are what test runs leave behind (./true -> build/...).
            if p.is_symlink() or fn.endswith(SKIP_SUFFIXES):
                continue
            h.update(p.relative_to(root).as_posix().encode() + b"\0")
            h.update(p.read_bytes())
            h.update(b"\0")
    return h.hexdigest()


# Not inputs: chosen per run by regression.sh, or where the cache lives.
ENV_NOT_INPUTS = {"RITZ_EXAMPLE_PORT", "RITZ_REGRESSION_BASELINE_CACHE",
                  "RITZ_REGRESSION_LIB_ONLY"}


def _first_line(cmd) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True).stdout
    except OSError:
        return f"{cmd[0]}-missing"
    return (out.splitlines() or [""])[0]


def toolchain() -> str:
    tools = [_first_line([t, "--version"]) for t in ("clang", "opt", "llvm-as")]
    env = [f"{k}={v}" for k, v in sorted(os.environ.items())
           if k.startswith("RITZ_") and k not in ENV_NOT_INPUTS]
    return "|".join(tools + env + [sys.version, platform.machine()])


def global_key(root: Path, build_dir: str, harness: Path, extra: str) -> str:
    cache = _load_cache_module()
    h = hashlib.sha256()
    for part in (
        KEY_VERSION,
        cache.compute_compiler_hash(root, "ritz0"),
        toolchain(),
        tree_hash(root / "ritzlib"),
        tree_hash(root / "runtime"),
        tree_hash(root / "cache.py"),
        tree_hash(harness),
        build_dir,
        extra,
    ):
        h.update(part.encode() + b"\0")
    return h.hexdigest()


def example_key(glob: str, name: str, example_dir: Path) -> str:
    h = hashlib.sha256()
    h.update(f"{glob}\0{name}\0{tree_hash(example_dir)}\0".encode())
    toml = example_dir / "ritz.toml"
    if toml.is_file():
        for dep in sorted(set(PATH_DEP.findall(toml.read_text()))):
            dep_dir = (example_dir / dep).resolve()
            h.update(f"dep\0{dep}\0{tree_hash(dep_dir)}\0".encode())
    return h.hexdigest()


def main(argv) -> int:
    if len(argv) < 5 or argv[4] != "--":
        print(__doc__, file=sys.stderr)
        return 2
    root, build_dir, harness, extra = Path(argv[0]), argv[1], Path(argv[2]), argv[3]
    glob = global_key(root, build_dir, harness, extra)
    for pair in argv[5:]:
        name, _, d = pair.partition("=")
        print(f"{name}\t{example_key(glob, name, Path(d))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
