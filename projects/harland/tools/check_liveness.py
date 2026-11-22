#!/usr/bin/env python3
"""Every kernel module must be reachable from the kernel's entry point.

`rz build harland` compiles only the kernel binary's import closure
(ritz/build_pipeline.py runs ritz0/list_deps.py over the entry file), so a
module nothing imports is never compiled. It cannot fail a build, so it rots:
`arch/x86_64/interrupts.ritz` still defined a second exception_handler long
after exceptions.ritz replaced it (AGAST #1886).

This check walks that same closure from the [[bin]] entry and fails when a
`.ritz` module under the package's sources is not in it. It does not resolve
imports itself: ritz0/list_deps.py is the one resolver the build uses.

An allowlist entry is a module deliberately not imported *yet*, with the
reason it is not. An entry whose file no longer exists is an error, so the
list cannot quietly outlive its reason.

    python3 projects/harland/tools/check_liveness.py
    python3 projects/harland/tools/check_liveness.py --package projects/harland
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECTS = REPO_ROOT / "projects"
RITZ = PROJECTS / "ritz"
LIST_DEPS = RITZ / "ritz0" / "list_deps.py"

# Repo-relative paths, each with the reason it is not imported.
ALLOWED = {
    # DMA is WIP: no production importer, but its page helpers are exercised
    # by test/test_dma.ritz (AGAST #4427). Import it in kernel/src/main.ritz
    # and delete this entry when DMA lands.
    Path("projects/harland/kernel/src/mm/dma.ritz"):
        "WIP; covered by test/test_dma.ritz (AGAST #4427)",
}


def _resolve_module():
    """The one resolver the build uses: `manifest` and `resolve` from ritz."""
    sys.path.insert(0, str(RITZ))
    import manifest  # noqa: E402
    import resolve  # noqa: E402
    return manifest, resolve


def _kernel_bin(config: dict, package: Path, name: str | None) -> dict:
    bins = config.get("bin", [])
    if not bins:
        raise SystemExit(f"{package}: no [[bin]] target")
    wanted = name or config.get("package", {}).get("name")
    for target in bins:
        if target.get("name") == wanted:
            return target
    # A package whose single bin has another name is the common case.
    if len(bins) == 1:
        return bins[0]
    raise SystemExit(f"{package}: no [[bin]] named {wanted!r}")


def _allowlist_for(package: Path) -> tuple[dict[Path, str], list[Path]]:
    """(allowlisted package-relative paths, stale repo-relative entries)."""
    try:
        pkg_rel = package.relative_to(REPO_ROOT)
    except ValueError:
        return {}, []  # a fixture outside the repo: no package allowlist applies
    allowed: dict[Path, str] = {}
    stale: list[Path] = []
    for repo_rel, reason in ALLOWED.items():
        if pkg_rel not in repo_rel.parents:
            continue
        if (REPO_ROOT / repo_rel).is_file():
            allowed[repo_rel.relative_to(pkg_rel)] = reason
        else:
            stale.append(repo_rel)
    return allowed, stale


def find_orphans(package: Path, bin_name: str | None = None):
    """(orphans, stale allowlist entries, reachable count, allowed count)."""
    manifest, resolve = _resolve_module()
    config = manifest.load(package / "ritz.toml")
    if config is None:
        raise SystemExit(f"{package}/ritz.toml not found")
    target = _kernel_bin(config, package, bin_name)
    sources = target.get("sources") or resolve.package_sources(config, ["src"])
    entry = target.get("entry")
    if not entry:
        raise SystemExit(f"{package}: [[bin]] has no entry")

    from_entry = entry.rsplit("::", 1)[0].replace(".", "/") + ".ritz"
    entry_file = next((package / src / from_entry for src in sources
                       if not src.startswith("!") and (package / src / from_entry).is_file()), None)
    if entry_file is None:
        raise SystemExit(f"{package}: entry {entry!r} names no source file under {sources}")

    # The closure is ritz0/list_deps.py's: exactly what the build uses.
    deps = {name: {"path": str(spec.path), "sources": spec.sources}
            for name, spec in resolve.package_import_namespaces(config, package).items()}
    env = dict(os.environ)
    # ritzlib resolves through RITZ_PATH, as it does in the build.
    env["RITZ_PATH"] = str(RITZ) + (os.pathsep + env["RITZ_PATH"] if env.get("RITZ_PATH") else "")
    cmd = [sys.executable, str(LIST_DEPS), str(entry_file),
           "--project-root", str(package),
           "--deps", json.dumps(deps), "--sources", json.dumps(sources)]

    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"import closure failed for {entry_file}:\n{proc.stderr.strip()}")

    closure = {Path(line.strip()).resolve() for line in proc.stdout.splitlines() if line.strip()}
    modules = [path.resolve() for path in manifest.discover_sources(package, sources)]
    allowed, stale = _allowlist_for(package)
    orphans = sorted(path for path in modules
                     if path not in closure and path.relative_to(package) not in allowed)
    return orphans, stale, len(closure), len(allowed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--package", type=Path, default=PROJECTS / "harland",
                        help="package directory (default: projects/harland)")
    parser.add_argument("--bin", help="[[bin]] name (default: package name)")
    args = parser.parse_args(argv)

    package = args.package.resolve()
    orphans, stale, reachable, allowed = find_orphans(package, args.bin)

    for path in stale:
        print(f"✗ allowlisted but missing: {path} (remove it from ALLOWED)", file=sys.stderr)
    for path in orphans:
        print(f"✗ unreachable: {path.relative_to(REPO_ROOT)} "
              f"(import it from the kernel entry, or allowlist it with a reason)", file=sys.stderr)

    if not orphans and not stale:
        print(f"liveness: {reachable} modules in the import closure from "
              f"{args.bin or package.name}, {allowed} allowlisted under the "
              f"package, 0 orphaned")
    return 1 if orphans or stale else 0


if __name__ == "__main__":
    sys.exit(main())
