"""help: every Linux [[bin]] answers --help with exit 0."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
import tomllib
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from .harness import PROJECTS, REPO, Broken, CheckFailed, Reporter, run_cmd, short


def _load(name: str, path: Path):
    # `rz` has no .py suffix, so name the loader explicitly.
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def targets_linux(target: str, target_os: str) -> bool:
    """By target, never by name: harland ELFs (ritzutils cat.elf, rzsh.elf)
    and the UEFI loader segfault or refuse to exec on Linux."""
    if target_os and target_os != "linux":
        return False
    return not target or "linux" in target


@dataclass
class Bin:
    project: str   # rz project id, e.g. "mausoleum" or "larb/tools/ritz-stats"
    name: str
    path: Path

    @property
    def check(self) -> str:
        return f"help:{self.project}/{self.name}"


def linux_bins() -> tuple[list[Bin], dict[str, str]]:
    """Every buildable Linux [[bin]] in the workspace, from the same member
    discovery and binary planning `./rz build --all` uses, plus the
    {project: reason} of rz.toml [ci.known_failing.build] (those are not built)."""
    rz = _load("rz_cli_2456", REPO / "rz")
    if str(PROJECTS / "ritz") not in sys.path:
        sys.path.insert(0, str(PROJECTS / "ritz"))  # build.py imports cache, cas, ...
    build = _load("ritz_buildpy_2456", PROJECTS / "ritz" / "build.py")
    known = rz.known_failing_from_config("build")
    bins = []
    for project in rz.discover_projects():
        pkg = (PROJECTS / project).resolve()
        config = tomllib.loads((pkg / "ritz.toml").read_text())
        for b in build.plan_binaries(pkg, config).buildable:
            if not targets_linux(b.target, b.target_os):
                continue
            out = pkg / "build" / "debug" / (f"{b.name}.elf" if b.freestanding else b.name)
            bins.append(Bin(project, b.name, out))
    return bins, known


def check_help(b: Bin, tmp: Path) -> None:
    if not b.path.is_file():
        raise Broken(f"not built: {b.path.relative_to(REPO)}")
    cwd = tmp / "help" / b.project.replace("/", "_") / b.name
    cwd.mkdir(parents=True, exist_ok=True)
    res = run_cmd([str(b.path), "--help"], cwd, timeout=5, split_stderr=True)
    if res.returncode != 0:
        raise CheckFailed(f"exit {res.returncode}: {short(res.stdout + res.stderr, 90)}")
    # #2462: --help answers before doing any work: usage on stdout,
    # nothing written into cwd (angelo's demos used to render a PGM).
    if not res.stdout.strip():
        raise CheckFailed(f"exit 0 but no usage on stdout (stderr: {short(res.stderr, 60)})")
    left = sorted(x.name for x in cwd.iterdir())
    if left:
        raise CheckFailed(f"--help wrote into cwd: {', '.join(left)[:80]}")


def suite_help(r: Reporter, tmp: Path) -> None:
    bins, known = linux_bins()
    if len(bins) < 20:
        r.broken("help:discovery", f"found only {len(bins)} Linux binaries (expected 20+): discovery is broken")
    for b in bins:
        if b.project in known:
            r.skip(b.check, f"package not built: rz.toml [ci.known_failing.build] {known[b.project][:60]}")
            continue
        r.run(b.check, partial(check_help, b, tmp))
