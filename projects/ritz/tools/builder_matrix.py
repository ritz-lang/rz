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

`list_packages()` returns project ids (rz's own id form: the package
directory relative to projects/, so "buddhafinger", "ritz/ritzlib/tests").
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
WORKSPACE = TOOLS_DIR.parents[2]
RZ_PATH = WORKSPACE / "rz"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
import known_failures  # noqa: E402

OPT_IN_MARKER = "uses the builder (AGAST #4825)"


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
    swept = {p for p in rz.discover_projects() if p not in excused}
    return sorted(swept | _opted_in_excluded(rz))


def main(argv: list[str]) -> int:
    if argv[1:] == ["list"]:
        print(json.dumps(list_packages()))
        return 0
    print(f"usage: {argv[0]} list", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
