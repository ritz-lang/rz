#!/usr/bin/env python3
"""IR-identity check: a candidate ritz1 must emit the reference's IR, byte for byte.

A refactor of ritz1's emitter that is not meant to change what it emits (a
split, a port to `format_into`, a new output type) is checked by compiling the
same modules with a reference build and the candidate build and comparing the
`.ll` bytes.  AGAST #1818's fourteen slices did this by hand on "402 modules
(ritz0/test + ritzlib + ritz1/src, cache disabled), under ritz1 and
ritz1_selfhosted"; this is that check as a tool (AGAST #4696).

    ritz1_ir_identity.py --ref REF/ritz1 --cand build/ritz1
    ritz1_ir_identity.py --ref REF/ritz1_selfhosted --cand build/ritz1_selfhosted

The reference is built from the commit before the change (the train tail the
change is based on), the candidate from the change.  Run it once per compiler
(`ritz1` and `ritz1_selfhosted`): the self-hosted one is the emitter compiling
itself, which is where a miscompiled emitter shows.

Both compilers read the same corpus from `--root` (the candidate's tree), so a
change to a source under `ritz1/src` is compared on the new text, not on two
different texts.  Each compile gets its own empty `RITZ_CACHE_DIR`, so no
signature cache can answer in place of the emitter.

A module is identical when both compilers exit with the same status and write
the same bytes (or, when both refuse it, print the same diagnostics).  The
exit status is 0 when every module is identical, 1 when any differs (they are
listed), 2 when the check could not run (no binary, empty corpus).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

# Relative to the project root (projects/ritz): the corpus #1818 used.
CORPUS_DIRS = ("ritz0/test", "ritzlib", "ritz1/src")

# A compile that takes longer than this is a hang, and a difference.
COMPILE_TIMEOUT_S = 120


@dataclass(frozen=True)
class Outcome:
    """What one compiler did with one module."""

    status: int
    ir: bytes  # the .ll it wrote; empty when it wrote none
    diagnostics: bytes  # stderr; compared only when the module was refused

    def same_as(self, other: "Outcome") -> bool:
        if self.status != other.status or self.ir != other.ir:
            return False
        return self.status == 0 or self.diagnostics == other.diagnostics


def corpus(root: Path) -> list[Path]:
    """Every `.ritz` module of the identity corpus, in a stable order."""
    found: list[Path] = []
    for name in CORPUS_DIRS:
        found.extend(sorted((root / name).rglob("*.ritz")))
    return found


def compile_module(compiler: Path, src: Path, root: Path) -> Outcome:
    """Run `compiler src -o out.ll` with an empty cache and RITZ_PATH=root."""
    with tempfile.TemporaryDirectory(prefix="ir-identity-") as scratch:
        out = Path(scratch) / "out.ll"
        env = dict(os.environ)
        env["RITZ_PATH"] = str(root)
        env["RITZ_CACHE_DIR"] = str(Path(scratch) / "cache")
        try:
            run = subprocess.run(
                [str(compiler), str(src), "-o", str(out)],
                env=env,
                cwd=scratch,
                capture_output=True,
                timeout=COMPILE_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return Outcome(status=-1, ir=b"", diagnostics=b"timeout")
        ir = out.read_bytes() if out.exists() else b""
        # The diagnostics name the scratch dir only through the cache path.
        return Outcome(run.returncode, ir, run.stderr.replace(scratch.encode(), b"<tmp>"))


def compare(ref: Path, cand: Path, root: Path, src: Path) -> tuple[Path, str | None]:
    """The module, and why the two compilers disagree on it (None: they agree)."""
    a = compile_module(ref, src, root)
    b = compile_module(cand, src, root)
    if a.same_as(b):
        return src, None
    if a.status != b.status:
        return src, f"exit status {a.status} (reference) vs {b.status} (candidate)"
    if a.status != 0:
        return src, "diagnostics differ"
    at = next((i for i, (x, y) in enumerate(zip(a.ir, b.ir)) if x != y), min(len(a.ir), len(b.ir)))
    return src, f"IR differs at byte {at} ({len(a.ir)} vs {len(b.ir)} bytes)"


def check(ref: Path, cand: Path, root: Path, jobs: int, limit: int | None = None) -> int:
    modules = corpus(root)
    if limit is not None:
        modules = modules[:limit]
    if not modules:
        print(f"ritz1_ir_identity: no .ritz modules under {root}", file=sys.stderr)
        return 2
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(lambda m: compare(ref, cand, root, m), modules))
    differing = [(m, why) for m, why in results if why is not None]
    for module, why in differing:
        print(f"DIFF {module.relative_to(root)}: {why}")
    verdict = "differ" if differing else "identical"
    print(
        f"ritz1_ir_identity: {len(modules) - len(differing)}/{len(modules)} modules "
        f"identical ({cand.name} vs {ref.name}), {len(differing)} differ: {verdict}"
    )
    return 1 if differing else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ref", type=Path, required=True, help="the reference compiler binary")
    ap.add_argument("--cand", type=Path, required=True, help="the candidate compiler binary")
    ap.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="the project root holding the corpus (default: projects/ritz)",
    )
    ap.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 8))
    ap.add_argument("--limit", type=int, help="compare only the first N modules")
    args = ap.parse_args(argv)
    for binary in (args.ref, args.cand):
        if not binary.is_file() or not os.access(binary, os.X_OK):
            print(f"ritz1_ir_identity: not an executable: {binary}", file=sys.stderr)
            return 2
    return check(args.ref.resolve(), args.cand.resolve(), args.root.resolve(), args.jobs, args.limit)


if __name__ == "__main__":
    sys.exit(main())
