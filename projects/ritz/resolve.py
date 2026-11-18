"""Package dependency resolution: the one resolver build.py and `rz` share.

AGAST #1835. There used to be two. build.py read `[dependencies]` here
(parse_dependencies / get_transitive_dependencies), while `rz` walked the
same tables itself to build each child's RITZ_PATH. Its walk followed a
dependency's own dependencies only when that dependency sat directly under
projects/, and it ignored the string shorthand (`z = "../z"`). So a nested
package (projects/x/y, a workspace member since AGAST #1383) put itself on
RITZ_PATH but none of its dependencies.

This module needs only the standard library, so `rz` can import it without
loading the compiler. The manifest schema (AGAST #1837) belongs in its own
module; `read_manifest` is the seam that module will replace.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import manifest  # the strict ritz.toml schema (AGAST #1837)

MANIFEST = "ritz.toml"


def read_manifest(pkg_dir: Path) -> dict | None:
    """The package's parsed ritz.toml, or None if it has none."""
    path = Path(pkg_dir) / MANIFEST
    if not path.exists():
        return None
    return manifest.load(path)


def package_sources(config: dict, default: list[str] | None = None) -> list[str] | None:
    """A package's source roots: its [package] `sources`, as a new list.

    `default` (copied) when the manifest sets none. The one reader of a
    package's own `sources` (AGAST #3894): it used to be accepted at the top
    level, under [package] and under [build], and five readers each carried a
    copy of that fallback chain. The schema now names [package] only and
    rejects the other two with file:line, so nothing else may look there.
    """
    sources = config.get("package", {}).get("sources")
    if sources is None:
        return None if default is None else list(default)
    return [sources] if isinstance(sources, str) else list(sources)


@dataclass
class DependencySpec:
    """Represents a single dependency specification.

    Per RFC #109 §2.6, dependencies are namespaced:
    - import squeeze.gzip → squeeze/src/gzip.ritz (if squeeze is a dependency)
    """
    name: str           # Dependency name (used as import namespace)
    path: Path          # Path to dependency root (absolute)
    sources: list[str]  # Source directories within dependency (default: ["src"])

    def resolve_import(self, module_parts: list[str]) -> Path | None:
        """Resolve an import path within this dependency.

        Args:
            module_parts: Path parts after the dependency name
                         e.g., for "squeeze.gzip", this would be ["gzip"]

        Returns:
            Path to the .ritz file if found, None otherwise
        """
        if not module_parts:
            return None

        # Convert module path to file path: gzip → gzip.ritz, http.server → http/server.ritz
        file_rel = "/".join(module_parts[:-1] + [module_parts[-1] + ".ritz"]) if module_parts else ""

        # Search in dependency's source directories
        for src_dir in self.sources:
            src_path = self.path / src_dir
            if not src_path.is_dir():
                continue
            candidate = src_path / file_rel
            if candidate.exists():
                return candidate

        return None


def parse_dependencies(config: dict, pkg_dir: Path, *, warn: bool = True) -> dict[str, DependencySpec]:
    """Parse [dependencies] section from ritz.toml config.

    Per RFC #109 §2.6:
    - Dependencies are declared as: name = { path = "..." }
    - Each dependency gets its own namespace for imports
    - Paths are resolved relative to the package directory

    A dependency with no `path`, or whose path does not exist, is skipped,
    with a warning on stderr unless `warn` is False.

    Returns:
        Dict mapping dependency name to DependencySpec
    """
    def warning(msg: str) -> None:
        if warn:
            print(msg, file=sys.stderr)

    deps = {}
    deps_config = config.get("dependencies", {})

    for name, spec in deps_config.items():
        if isinstance(spec, dict):
            # Full spec: { path = "...", sources = [...] }
            dep_path = spec.get("path")
            if dep_path is None:
                warning(f"  ⚠ Dependency '{name}' missing 'path'")
                continue

            # Resolve path relative to package directory
            dep_path = (pkg_dir / dep_path).resolve()
            if not dep_path.exists():
                warning(f"  ⚠ Dependency '{name}' path not found: {dep_path}")
                continue

            # Get sources from dependency's ritz.toml if not specified
            sources = spec.get("sources")
            if sources is None:
                dep_config = read_manifest(dep_path)
                sources = package_sources(dep_config or {}, ["src"])

            if isinstance(sources, str):
                sources = [sources]

            deps[name] = DependencySpec(name=name, path=dep_path, sources=sources)
        elif isinstance(spec, str):
            # Shorthand: just a path
            dep_path = (pkg_dir / spec).resolve()
            if not dep_path.exists():
                warning(f"  ⚠ Dependency '{name}' path not found: {dep_path}")
                continue
            deps[name] = DependencySpec(name=name, path=dep_path, sources=["src"])

    return deps


def package_import_namespaces(config: dict, pkg_dir: Path) -> dict[str, DependencySpec]:
    """Import namespaces visible to a package's own sources.

    The declared [dependencies], plus the package's OWN name mapped onto its
    own source roots, so `import tome.resp` inside tome resolves to
    tome/lib/resp.ritz exactly as it does for a consumer that declares
    `tome = { path = "../tome" }` (AGAST #1538).

    Before this, a package's self-qualified imports resolved only when
    something happened to put the package itself on RITZ_PATH (`./rz`
    does, as a side effect of collecting dependency paths); a plain
    `build.py build projects/tome` failed "Cannot find module: tome.resp".

    An explicit dependency of the same name always wins over the
    self-mapping.
    """
    namespaces = parse_dependencies(config, pkg_dir)
    pkg_name = config.get("package", {}).get("name")
    if pkg_name and pkg_name not in namespaces:
        namespaces[pkg_name] = DependencySpec(
            name=pkg_name, path=pkg_dir.resolve(),
            sources=package_sources(config, ["src"]))
    return namespaces


def get_transitive_dependencies(
    pkg_dir: Path,
    config: dict,
    seen: set[str] = None
) -> dict[str, DependencySpec]:
    """Get all dependencies including transitive ones.

    Walks the dependency tree and collects all dependencies.
    Detects cycles and raises an error.

    Args:
        pkg_dir: Package directory
        config: Package config
        seen: Set of already-seen package paths (for cycle detection)

    Returns:
        Dict mapping dependency name to DependencySpec
    """
    if seen is None:
        seen = set()

    pkg_key = str(pkg_dir.resolve())
    if pkg_key in seen:
        raise ValueError(f"Circular dependency detected involving: {pkg_dir}")

    seen.add(pkg_key)
    all_deps = {}

    # Get direct dependencies
    direct_deps = parse_dependencies(config, pkg_dir)
    all_deps.update(direct_deps)

    # Get transitive dependencies
    for dep_name, dep_spec in direct_deps.items():
        dep_config = read_manifest(dep_spec.path)
        if dep_config is not None:
            transitive = get_transitive_dependencies(dep_spec.path, dep_config, seen.copy())

            # Add transitive deps (but don't override direct deps)
            for trans_name, trans_spec in transitive.items():
                if trans_name not in all_deps:
                    all_deps[trans_name] = trans_spec

    return all_deps


def dependency_package_dirs(pkg_dir: Path) -> list[Path]:
    """`pkg_dir`, then every package it depends on, directly or not.

    Depth-first, in declaration order: each dependency is followed by its own
    dependencies, wherever it lives (projects/c or projects/x/y alike). This
    is the order `rz` puts on a child's RITZ_PATH, which is searched first
    match wins. Each package appears once, and a cycle ends the walk instead
    of raising: the build reports a real cycle (get_transitive_dependencies).
    Resolves exactly the packages get_transitive_dependencies does.
    """
    out: list[Path] = []
    seen: set[Path] = set()

    def walk(pkg: Path) -> None:
        key = pkg.resolve()
        if key in seen:
            return
        seen.add(key)
        out.append(pkg)
        config = read_manifest(pkg)
        if config is None:
            return
        for spec in parse_dependencies(config, key, warn=False).values():
            walk(spec.path)

    walk(Path(pkg_dir))
    return out
