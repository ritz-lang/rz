#!/usr/bin/env python3
"""Do this interpreter's Python packages match requirements.lock?  AGAST #2300.

requirements.txt and requirements-dev.txt say what ritz0 and the tools need,
bounded from below.  On their own they let CI install the newest release of
everything on every run, while each host's gate venv keeps what it has: pytest
9.2.0 broke xdist_group on CI only, and every gate kept passing on 9.1.1
(#2251).  requirements.lock pins the whole installed closure, and the CI setup
action installs with it as a constraints file, so CI's packages change only
when the lock does.

This compares the running interpreter with the lock.  It walks the dependency
closure of the requirements files through the installed metadata (so the
hosts' unrelated packages -- django, ddtrace, ... -- are not drift) and reports:

  * a pinned package installed at a different version;
  * a pinned package that is not installed;
  * a package in the closure that the lock does not name (it would float in CI).

main.yml runs it as a step, so the gate (ci_local.py) runs it too.  Under
GitHub Actions any drift fails the step: CI installed from the lock, so a
difference means the lock is incomplete or inconsistent.  Anywhere else it
reports and exits 0, because the hosts share one venv per machine and a gate
must not fail every room on it; the report says how to bring the venv in line.

Markers are not evaluated (that needs `packaging`, which this keeps out of the
tools' requirements): a dependency is followed only when it is installed,
which is what a marker that excluded it would have produced anyway.
`extra == ...` dependencies are never followed.

Upgrading a pin is deliberate: edit requirements.lock, install it into a
scratch venv, run ritz0/test_xdist_group_holds.py and the gate, then land it.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parents[1]
LOCK = RITZ_ROOT / "requirements.lock"
REQUIREMENTS = [RITZ_ROOT / "requirements.txt", RITZ_ROOT / "requirements-dev.txt"]

INSTALL = (
    "python -m pip install -r projects/ritz/requirements.txt "
    "-r projects/ritz/requirements-dev.txt -c projects/ritz/requirements.lock"
)

_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


@dataclass
class Dist:
    version: str
    requires: list[str] = field(default_factory=list)


def normalize(name: str) -> str:
    """PEP 503: case- and separator-insensitive."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _lines(path: Path):
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            yield line


def read_lock(path: Path) -> dict[str, str]:
    """`name==version` lines -> {normalized name: version}."""
    pins: dict[str, str] = {}
    for line in _lines(path):
        name, _, version = line.partition("==")
        pins[normalize(name.strip())] = version.split(";", 1)[0].strip()
    return pins


def top_level(paths: list[Path]) -> list[str]:
    """The distribution names the requirements files declare, in order."""
    names: list[str] = []
    for path in paths:
        for line in _lines(path):
            m = _NAME.match(line)
            if m and normalize(m.group(1)) not in names:
                names.append(normalize(m.group(1)))
    return names


def installed() -> dict[str, Dist]:
    """Every distribution visible to this interpreter."""
    dists: dict[str, Dist] = {}
    for d in importlib.metadata.distributions():
        name = d.metadata["Name"]
        if name:
            dists.setdefault(normalize(name), Dist(d.version, list(d.requires or [])))
    return dists


def _deps(requires: list[str]) -> list[str]:
    out = []
    for req in requires:
        marker = req.split(";", 1)[1] if ";" in req else ""
        if "extra" in marker:
            continue
        m = _NAME.match(req)
        if m:
            out.append(normalize(m.group(1)))
    return out


def closure(dists: dict[str, Dist], roots: list[str]) -> list[str]:
    """Installed names reachable from `roots`, roots included if installed."""
    seen: list[str] = []
    todo = [normalize(r) for r in roots]
    while todo:
        name = todo.pop(0)
        if name in seen or name not in dists:
            continue
        seen.append(name)
        todo.extend(_deps(dists[name].requires))
    return seen


def drift(lock: dict[str, str], dists: dict[str, Dist], roots: list[str]) -> list[str]:
    """One line per difference between the installed closure and the lock."""
    lock = {normalize(k): v for k, v in lock.items()}
    reach = closure(dists, roots)
    out = []
    for name in sorted(lock):
        if name not in dists:
            out.append(f"{name}: not installed, lock {lock[name]}")
        elif dists[name].version != lock[name]:
            out.append(f"{name}: installed {dists[name].version}, lock {lock[name]}")
    for name in sorted(reach):
        if name not in lock:
            out.append(f"{name}: installed {dists[name].version}, not in the lock")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on drift (the default under GitHub Actions)",
    )
    args = p.parse_args(argv)
    strict = args.strict or os.environ.get("GITHUB_ACTIONS") == "true"

    lock = read_lock(LOCK)
    roots = top_level(REQUIREMENTS)
    problems = drift(lock, installed(), roots)
    where = f"{sys.executable} (Python {sys.version.split()[0]})"
    if not problems:
        print(
            f"python deps: {where} packages match requirements.lock ({len(lock)} pins)"
        )
        return 0
    print(f"python deps: DRIFT from requirements.lock in {where}:")
    for line in problems:
        print(f"  {line}")
    if strict:
        print(
            "::error::the installed packages differ from projects/ritz/"
            "requirements.lock; CI installs with it as constraints, so the "
            "lock is incomplete or inconsistent (AGAST #2300)"
        )
        return 1
    print("This gate is NOT running what CI runs (AGAST #2300); reported, not failed.")
    print(f"To match CI, from the repo root: {INSTALL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
