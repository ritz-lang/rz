#!/usr/bin/env python3
"""Copy the part of an rz checkout the builder image ships (AGAST #4822).

    python3 projects/builder/stage_tree.py <checkout> <dest>

<dest> becomes a workspace root that `./rz build|test <pkg> --compiler
ritz1_selfhosted` runs in.  What goes in, and why, is the survey in
projects/builder/README.md; in short:

- rz, known-failures/*.toml (rz's build verdicts read them), and an rz.toml
  written from the checkout's (write_workspace);
- the Python modules `rz build` and `rz test` import under ritz1_selfhosted,
  traced with an audit hook (README, "Python");
- ritzlib and the runtime shims, without their tests;
- every package another package names as a path dependency, plus ritzunit
  (which `rz test` links into every test binary): its ritz.toml and its
  sources (.ritz, linker scripts, .s, .ll), no tests, docs or examples;
- ritz1_selfhosted, at the path build_pipeline.RITZ1_SELFHOSTED_BIN names.

Nothing else: no .git, no build caches, no ritz0 compiler back end (ritz0
needs llvmlite, which the image does not carry).
"""

from __future__ import annotations

import shutil
import sys
import tomllib
from pathlib import Path

# rz and the modules it imports in-process or runs as a child, traced while
# `rz build --all` and `rz test` ran under ritz1_selfhosted.  build_pipeline
# imports ritz0/module_interface for its interface hashes, and runs
# ritz0/list_deps.py for the import graph, so ritz0's front end ships; its
# back end (emitter_llvmlite and the rest) does not.
PYTHON_FILES = [
    "rz",
    "projects/ritz/bounded_run.py",
    "projects/ritz/build.py",
    "projects/ritz/build_cli.py",
    "projects/ritz/build_pipeline.py",
    "projects/ritz/build_testrun.py",
    "projects/ritz/cache.py",
    "projects/ritz/cas.py",
    "projects/ritz/manifest.py",
    "projects/ritz/resolve.py",
    "projects/ritz/tools/known_failures.py",
    "projects/ritz/ritz0/compiler_identity.py",
    "projects/ritz/ritz0/emitter/__init__.py",
    "projects/ritz/ritz0/emitter/fn_cache.py",
    "projects/ritz/ritz0/import_resolver.py",
    "projects/ritz/ritz0/index_rules.py",
    "projects/ritz/ritz0/interp_spec.py",
    "projects/ritz/ritz0/lexer.py",
    "projects/ritz/ritz0/list_deps.py",
    "projects/ritz/ritz0/metadata.py",
    "projects/ritz/ritz0/module_interface.py",
    "projects/ritz/ritz0/monomorph.py",
    "projects/ritz/ritz0/monomorph_core.py",
    "projects/ritz/ritz0/monomorph_infer.py",
    "projects/ritz/ritz0/monomorph_rewrite.py",
    "projects/ritz/ritz0/parser.py",
    "projects/ritz/ritz0/qualified_access.py",
    "projects/ritz/ritz0/ref_rules.py",
    "projects/ritz/ritz0/ritz_ast.py",
    "projects/ritz/ritz0/selective_import.py",
    "projects/ritz/ritz0/test_runner.py",
    "projects/ritz/ritz0/tokens.py",
    "projects/ritz/ritz0/trait_bounds.py",
    "projects/ritz/ritz0/typed.py",
]

# Single files outside any package.  projects/ritz/ritz.toml makes `ritz` a
# package, which tempest names as a dependency (`ritz = { path = "../ritz" }`).
DATA_FILES = ["projects/ritz/ritz.toml"]

SELFHOSTED = "projects/ritz/ritz1/build/ritz1_selfhosted"

# What a package's build reads: sources, linker scripts, assembly, IR shims.
SOURCE_SUFFIXES = {".ritz", ".ld", ".s", ".S", ".ll"}

# Directories that are not a build input unless the package's manifest names
# them in a `sources` list: zeus builds bins from examples/, mausoleum lists
# test/ and tools/ as sources, so those names are not on this list and a
# listed test/ ships (declared_roots).
SKIP_DIRS = {"test", "tests", "docs", "doc", "bench", "benchmarks", "build",
             "archive", "fixtures", "testdata"}

# Packages that ship even though no ritz.toml names them: `rz test` links
# ritzunit's runner into every test binary.
ALWAYS = ["projects/ritzunit"]


def library_packages(root: Path) -> list[Path]:
    """Every package dir named as a path dependency by some ritz.toml under
    projects/ (archive and examples excluded), plus ALWAYS, sorted."""
    found = {(root / p).resolve() for p in ALWAYS}
    for manifest in sorted((root / "projects").rglob("ritz.toml")):
        rel = manifest.relative_to(root).parts
        if "archive" in rel or "examples" in rel:
            continue
        deps = tomllib.loads(manifest.read_text()).get("dependencies", {})
        for spec in deps.values():
            if not isinstance(spec, dict) or "path" not in spec:
                continue
            dep = (manifest.parent / spec["path"]).resolve()
            if dep.is_dir() and (dep / "ritz.toml").is_file():
                found.add(dep)
    return sorted(found)


def copy_file(root: Path, dest: Path, rel: Path) -> None:
    out = dest / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / rel, out)


def declared_roots(pkg: Path) -> set[str]:
    """The first path component of every `sources` entry in pkg's ritz.toml:
    [package], each [[bin]] and each [[lib]].  A `!path` exclusion counts too,
    harmlessly: its directory is a source root anyway."""
    cfg = tomllib.loads((pkg / "ritz.toml").read_text())
    lists = [cfg.get("package", {}).get("sources")]
    lists += [t.get("sources") for kind in ("bin", "lib") for t in cfg.get(kind, [])]
    roots = set()
    for srcs in lists:
        for s in [srcs] if isinstance(srcs, str) else (srcs or []):
            roots.add(Path(s.lstrip("!")).parts[0] if s.lstrip("!") else ".")
    return roots


def copy_sources(root: Path, dest: Path, pkg: Path) -> int:
    """Copy pkg's ritz.toml and its source files; return the file count."""
    n = 0
    keep = declared_roots(pkg) if (pkg / "ritz.toml").is_file() else set()
    for path in sorted(pkg.rglob("*")):
        rel_in_pkg = path.relative_to(pkg).parts
        dirs = rel_in_pkg[:-1]
        if any(p.startswith(".") for p in dirs):
            continue
        # A skipped name anywhere drops the file, except as the package's
        # top-level directory when the manifest declares it a source root.
        if any(p in SKIP_DIRS and not (i == 0 and p in keep) for i, p in enumerate(dirs)):
            continue
        if path.is_file() and (path.suffix in SOURCE_SUFFIXES or path.name == "ritz.toml"):
            copy_file(root, dest, path.relative_to(root))
            n += 1
    return n


def toml_value(v: object) -> str:
    """The TOML for the scalar and string-list values rz.toml uses."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(v, list):
        return "[" + ", ".join(toml_value(x) for x in v) + "]"
    raise TypeError(f"rz.toml value {v!r}: stage_tree.py cannot write {type(v).__name__}")


def write_workspace(root: Path, dest: Path) -> None:
    """dest/rz.toml: the checkout's, less what names a path the image lacks.

    rz refuses a member glob that matches no package and an exclusion that
    matches none (test_nested_packages.py), and the image ships neither the
    benchmarks nor examples/ritz1/harland's boot, so those entries go."""
    cfg = tomllib.loads((root / "rz.toml").read_text())
    ws = dict(cfg["workspace"])
    ws["members"] = [m for m in ws.get("members", [])
                     if any(dest.glob(f"{m}/ritz.toml"))]
    exclude = {p: why for p, why in ws.pop("exclude", {}).items()
               if any((dest / p).rglob("ritz.toml"))}
    lines = ["# Written by projects/builder/stage_tree.py from the checkout's rz.toml,",
             "# less the members and exclusions that name paths this image does not ship.",
             "", "[workspace]"]
    lines += [f"{k} = {toml_value(v)}" for k, v in ws.items()]
    if exclude:
        lines += ["", "[workspace.exclude]"]
        lines += [f"{toml_value(p)} = {toml_value(why)}" for p, why in exclude.items()]
    for table, body in cfg.items():
        if table == "workspace":
            continue
        if not all(isinstance(v, (bool, int, str, list)) for v in body.values()):
            raise TypeError(f"rz.toml [{table}]: stage_tree.py writes flat tables only")
        lines += ["", f"[{table}]"] + [f"{k} = {toml_value(v)}" for k, v in body.items()]
    (dest / "rz.toml").write_text("\n".join(lines) + "\n")


def stage(root: Path, dest: Path) -> None:
    root = root.resolve()
    for rel in [*PYTHON_FILES, *DATA_FILES]:
        copy_file(root, dest, Path(rel))
    for toml in sorted((root / "known-failures").glob("*.toml")):
        copy_file(root, dest, toml.relative_to(root))
    copy_file(root, dest, Path(SELFHOSTED))

    # ritz itself is a dependency (tempest), but only ritzlib and the shims
    # are build inputs: its compilers' sources are not.
    ritz = root / "projects/ritz"
    copy_sources(root, dest, ritz / "ritzlib")
    for shim in sorted((ritz / "runtime").glob("*.ll")):
        copy_file(root, dest, shim.relative_to(root))

    for pkg in library_packages(root):
        if pkg == ritz or pkg.is_relative_to(ritz):
            continue
        n = copy_sources(root, dest, pkg)
        print(f"  {pkg.relative_to(root)}: {n} files")
    write_workspace(root, dest)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    stage(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
