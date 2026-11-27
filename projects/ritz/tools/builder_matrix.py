#!/usr/bin/env python3
"""Packages the builder-image CI matrix runs (AGAST #4825, epic #4783).

main.yml's `builder-packages` job runs `matrix` to get this run's matrix
(`strategy.matrix.package: ${{ fromJson(...) }}` in `builder-matrix`), and
`woodpecker --write` turns the same list into .woodpecker/builder.yml.

The run list is MATRIX_PACKAGES: buddhafinger only (AGAST #4846, Aaron,
2026-11-27), on Woodpecker and in GitHub's hosted fallback alike. Every
package in it must also be eligible (below); one that isn't is an error,
since an empty matrix runs nothing anywhere. Widening the matrix again is a
change to MATRIX_PACKAGES alone.

A package is eligible (`eligible_packages()`) if either:

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

`list_packages()` returns the run list's project ids (rz's own id form: the package
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

#: What the matrix runs, in this order (AGAST #4846, Aaron, 2026-11-27:
#: buddhafinger only, on Woodpecker and in the hosted fallback).
MATRIX_PACKAGES = ("buddhafinger",)

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


def eligible_packages(rz=None, known=None) -> list[str]:
    """Every package the builder could run, sorted (module docstring)."""
    rz = rz or load_rz()
    known = known or known_failures
    excused = (set(known.entries_for("build", "ritz1_selfhosted")) |
              set(known.entries_for("parity", "ritz1_selfhosted")))
    swept = {p for p in rz.discover_projects()
             if p not in excused and p not in NOT_IN_MATRIX}
    return sorted(swept | _opted_in_excluded(rz))


def list_packages(rz=None, known=None, only=MATRIX_PACKAGES) -> list[str]:
    """The run list `only`, in its order, once each of its packages is
    checked eligible. Raises ValueError on an empty or ineligible list."""
    if not only:
        raise ValueError("the builder matrix run list is empty")
    eligible = set(eligible_packages(rz=rz, known=known))
    missing = [p for p in only if p not in eligible]
    if missing:
        raise ValueError(
            f"builder matrix packages not eligible: {missing} (neither swept "
            f"nor opted in, or swept with a build/parity known failure under "
            f"ritz1_selfhosted)")
    return list(only)


def has_tests(pkg_dir: Path) -> bool:
    """What `rz test` would run: a .ritz test file (manifest's discovery, the
    one `run_tests` uses) or a test.sh."""
    if (pkg_dir / "test.sh").exists():
        return True
    config = manifest.load(pkg_dir / "ritz.toml")
    return bool(manifest.discover_test_files(pkg_dir, config))


def matrix_entries(rz=None, known=None, workspace: Path = WORKSPACE,
                   only=MATRIX_PACKAGES) -> list[dict]:
    """One entry per list_packages() id, in that order."""
    entries = []
    for pkg in list_packages(rz=rz, known=known, only=only):
        # normpath, not resolve(): "projects/../bench/x" -> "bench/x" without
        # following a symlink out of the workspace.
        path = Path(os.path.normpath(f"projects/{pkg}")).as_posix()
        entries.append({"package": pkg, "path": path,
                        "build_only": not has_tests(workspace / path)})
    return entries


#: Generated from matrix_entries() by `woodpecker --write` (AGAST #4846).
WOODPECKER_PIPELINE = WORKSPACE / ".woodpecker" / "builder.yml"

#: The first step's image: POSIX sh and curl, enough to poll a registry.
WAIT_IMAGE = ("curlimages/curl:8.23.0@sha256:"
              "3fb7e13e5d179a845c97d78204f3f1064d1907037f26a3ebf91710571151fd93")

_WOODPECKER_HEADER = """\
# GENERATED by `python3 projects/ritz/tools/builder_matrix.py woodpecker --write`
# from `builder_matrix.py matrix`, the package list main.yml's builder-matrix
# runs; do not edit (projects/ritz/tools/test_woodpecker_builder.py checks it).
# That list is MATRIX_PACKAGES: buddhafinger only (Aaron, 2026-11-27).
#
# AGAST #4846: the builder matrix on huburght's Woodpecker
# (https://ci.fucken.ninja, kubernetes backend). Each package step is a pod
# whose image IS the builder image of the commit, published by main.yml's
# builder-image job; the first step waits for it, since a pod that can't
# pull fails at once. GitHub's builder-matrix runs only when
# woodpecker_fleet.py finds the fleet down or this pipeline doesn't start
# within 10 min of its creation; a pipeline that starts later than that
# (plus slack) skips its steps, since GitHub ran the commit
# (woodpecker_builder_step.sh). Steps have no depends_on, so
# they run one at a time, in order; each package runs whatever the one
# before it did (fail-fast: false, as on GitHub).
#
# `pool: rz-builder` routes the workflow to the agent carrying that label: for
# now one of adele's shared agents, steps in `woodpecker-steps`, no rz quota
# (projects/builder/README.md, "CI on huburght's Woodpecker"). No privilege,
# volumes, services or secrets; uid 1000, never root; no CPU request or
# limit (adele's no-CPU-limits rule, and the smallest CPU weight on the box);
# 8Gi memory. No seccomp profile: ritzlib's io_uring tests (should the list
# widen again) fail under RuntimeDefault, and baseline Pod Security forbids
# naming Unconfined.
"""


def woodpecker_step_name(path: str) -> str:
    """A step name from a workspace path: projects/ dropped, '/' -> '-'."""
    return path.removeprefix("projects/").replace("/", "-")


def woodpecker_pipeline(entries: list[dict]) -> str:
    """.woodpecker/builder.yml for these matrix entries, as text."""
    names = [woodpecker_step_name(e["path"]) for e in entries]
    dupes = sorted({n for n in names if names.count(n) > 1} | ({"wait-for-image"} & set(names)))
    if dupes:
        raise ValueError(f"two packages map to one step name: {dupes}")
    lines = [_WOODPECKER_HEADER,
             "labels:",
             "  pool: rz-builder",
             "",
             "when:",
             "  - event: push",
             "    branch: main",
             "  - event: manual",
             "",
             "steps:",
             "  - name: wait-for-image",
             f"    image: {WAIT_IMAGE}",
             "    commands:",
             ("      - sh .github/scripts/wait_for_builder_image.sh"
              " ghcr.io/ritz-lang/rz-builder ${CI_COMMIT_SHA}")]
    for name, e in zip(names, entries):
        flag = " --build-only" if e["build_only"] else ""
        lines += ["",
                  f"  - name: {name}",
                  "    image: ghcr.io/ritz-lang/rz-builder:${CI_COMMIT_SHA}",
                  "    commands:",
                  f"      - bash .github/scripts/woodpecker_builder_step.sh{flag} {e['path']}",
                  "    when:",
                  "      - status: [success, failure]",
                  "    backend_options:",
                  "      kubernetes:",
                  "        resources:",
                  "          requests:",
                  "            memory: 1Gi",
                  "          limits:",
                  "            memory: 8Gi",
                  "        securityContext:",
                  "          runAsNonRoot: true",
                  "          runAsUser: 1000",
                  "          runAsGroup: 1000",
                  "          allowPrivilegeEscalation: false"]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if argv[1:] == ["list"]:
        print(json.dumps(list_packages()))
        return 0
    if argv[1:] == ["matrix"]:
        print(json.dumps(matrix_entries()))
        return 0
    if argv[1:] == ["woodpecker"]:
        sys.stdout.write(woodpecker_pipeline(matrix_entries()))
        return 0
    if argv[1:] == ["woodpecker", "--write"]:
        WOODPECKER_PIPELINE.parent.mkdir(exist_ok=True)
        WOODPECKER_PIPELINE.write_text(woodpecker_pipeline(matrix_entries()))
        print(f"wrote {WOODPECKER_PIPELINE.relative_to(WORKSPACE)}")
        return 0
    print(f"usage: {argv[0]} list|matrix|woodpecker [--write]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
