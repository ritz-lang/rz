#!/usr/bin/env python3
"""Packages the builder-image CI matrix runs (AGAST #4825, epic #4783).

main.yml's `builder-packages` job runs `list` to get this run's matrix
(`strategy.matrix.package: ${{ fromJson(...) }}` in `builder-matrix`). A
package is in the list if either:

- it is swept by `rz`'s workspace (`discover_projects()`) and has no open
  `build` or `parity` known-failures entry under ritz1_selfhosted (those
  excuses live in known-failures/, once each, not duplicated here: a
  package ritz1_selfhosted cannot build or whose tests only pass under
  ritz0 would turn every matrix run red for a reason already tracked); or
- it is excluded from the workspace (rz.toml [workspace.exclude]) and its
  reason names `OPT_IN_MARKER`: an excluded package still gets a gate, just
  not this generic one, and this is how it asks for this one too.
  Buddhafinger (AGAST #4826) is the first such package.

`ritz`, the compiler's own package, is never in the list (NOT_IN_MATRIX).

`list_packages()` returns project ids (rz's own id form: the package
directory relative to projects/, so "buddhafinger", "ritz/ritzlib/tests").
`matrix` prints what the job runs (AGAST #4847): one entry per package, with
the package's workspace-relative `path` (a bench package's id is
"../bench/...", which is not a path inside the container) and `build_only`,
true for a package with no tests. `rz test` prints "No tests found" for such a
package (indium, the bench regressions), and run_builder_package.sh's zero-test
guard would fail it, so the job builds it and doesn't test it.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
PKG_DIR = TOOLS_DIR.parent
WORKSPACE = TOOLS_DIR.parents[2]
RZ_PATH = WORKSPACE / "rz"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
import known_failures  # noqa: E402

if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))
import manifest  # noqa: E402

OPT_IN_MARKER = "uses the builder (AGAST #4825)"

#: Swept packages the builder can't run, and why (AGAST #4847).
NOT_IN_MATRIX = {
    # The entrypoint copies the mounted package over the workspace's
    # projects/ritz, which then has no ritz1/build/ritz1_selfhosted: the
    # entrypoint's own compiler check refuses the run (exit 2). The compiler
    # is the image, and main.yml's bootstrap job gates it.
    "ritz": "the compiler's own package, gated by the bootstrap job",
}


def load_rz():
    """`rz` isn't a module (no .py suffix); load it like
    test_buddhafinger_isolation.py and test_nested_packages.py do."""
    spec = importlib.util.spec_from_loader(
        "rz_4825", importlib.machinery.SourceFileLoader("rz_4825", str(RZ_PATH)))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _opted_in_excluded(rz) -> set[str]:
    ids = set()
    for key, reason in rz.workspace_exclusions().items():
        if OPT_IN_MARKER not in reason:
            continue
        if not key.startswith("projects/"):
            # Only paths under projects/ are package ids rz can build/test
            # by name; nothing excluded outside it (docs/archive, ...) can
            # opt in.
            continue
        ids.add(key[len("projects/"):])
    return ids


def list_packages(rz=None, known=None) -> list[str]:
    rz = rz or load_rz()
    known = known or known_failures
    excused = (set(known.entries_for("build", "ritz1_selfhosted")) |
              set(known.entries_for("parity", "ritz1_selfhosted")))
    swept = {p for p in rz.discover_projects()
             if p not in excused and p not in NOT_IN_MATRIX}
    return sorted(swept | _opted_in_excluded(rz))


def has_tests(pkg_dir: Path) -> bool:
    """What `rz test` would run: a .ritz test file (manifest's discovery, the
    one `run_tests` uses) or a test.sh."""
    if (pkg_dir / "test.sh").exists():
        return True
    config = manifest.load(pkg_dir / "ritz.toml")
    return bool(manifest.discover_test_files(pkg_dir, config))


def matrix_entries(rz=None, known=None, workspace: Path = WORKSPACE) -> list[dict]:
    """One entry per list_packages() id, in that order."""
    entries = []
    for pkg in list_packages(rz=rz, known=known):
        # normpath, not resolve(): "projects/../bench/x" -> "bench/x" without
        # following a symlink out of the workspace.
        path = Path(os.path.normpath(f"projects/{pkg}")).as_posix()
        entries.append({"package": pkg, "path": path,
                        "build_only": not has_tests(workspace / path)})
    return entries


def main(argv: list[str]) -> int:
    if argv[1:] == ["list"]:
        print(json.dumps(list_packages()))
        return 0
    if argv[1:] == ["matrix"]:
        print(json.dumps(matrix_entries()))
        return 0
    print(f"usage: {argv[0]} list|matrix", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
