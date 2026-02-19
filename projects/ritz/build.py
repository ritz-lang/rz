#!/usr/bin/env python3
"""
🎭 Ritz Build System

A simple build helper that reads ritz.toml configs and compiles examples.

Usage:
    python build.py list              # List all packages
    python build.py build <name>      # Build a specific package
    python build.py build --all       # Build all packages
    python build.py test <name>       # Build and test a package
    python build.py test --all        # Build and test all packages
    python build.py clean             # Remove build artifacts
    python build.py cache-status      # Show cache status
    python build.py cache-clear       # Clear the build cache
"""

import sys
import os
import subprocess
import argparse
import tempfile
from pathlib import Path
from dataclasses import dataclass

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11

from cache import BuildCache


ROOT = Path(__file__).parent
RITZ0 = ROOT / "ritz0" / "ritz0.py"
RUNTIME_DIR = ROOT / "runtime"

# Architecture-specific runtime files
import platform
ARCH = platform.machine()  # e.g., 'x86_64'
RITZ_START = RUNTIME_DIR / f"ritz_start.{ARCH}.o"           # main(argc, argv)
RITZ_START_NOARGS = RUNTIME_DIR / f"ritz_start_noargs.{ARCH}.o"  # main()
RITZ_START_ENVP = RUNTIME_DIR / f"ritz_start_envp.{ARCH}.o"      # main(argc, argv, envp)

# Add ritz0 to path for import resolver (must be done before importing)
RITZ0_DIR = ROOT / "ritz0"
if str(RITZ0_DIR) not in sys.path:
    sys.path.insert(0, str(RITZ0_DIR))

# Global build cache instance
_build_cache = None

def get_build_cache() -> BuildCache:
    """Get or create the global build cache."""
    global _build_cache
    if _build_cache is None:
        _build_cache = BuildCache(project_root=ROOT)
    return _build_cache


def detect_main_signature(source_path: Path) -> int:
    """Detect main function's parameter count from source file.

    Returns:
        0: main() - no arguments
        2: main(argc, argv) - argc and argv
        3: main(argc, argv, envp) - includes envp
    """
    from lexer import Lexer
    from parser import Parser
    import ritz_ast as rast

    try:
        source = source_path.read_text()
        lexer = Lexer(source, str(source_path))
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        module = parser.parse_module()

        for item in module.items:
            if isinstance(item, rast.FnDef) and item.name == 'main':
                return len(item.params)
        return 0  # No main found, assume no args
    except Exception:
        return 0  # On error, default to no args


def get_runtime_object(num_params: int) -> Path:
    """Get the appropriate runtime object file for main's signature."""
    if num_params >= 3:
        return RITZ_START_ENVP
    elif num_params >= 2:
        return RITZ_START
    else:
        return RITZ_START_NOARGS


# =============================================================================
# RFC #109 Phase 1: Entry Point Resolution, Source Discovery, Build Profiles
# =============================================================================

def resolve_entry_point(entry: str, pkg_dir: Path, sources: list[str]) -> tuple[Path, str] | None:
    """Resolve entry = "module::function" to (file_path, function_name).

    Per RFC #109 §2.4:
    - Parse entry = "path.to.module::function"
    - Convert module path to file: path/to/module.ritz
    - Search in sources directories
    - Return (file_path, function_name) or None if not found

    Examples:
        main::main          → src/main.ritz, fn main()
        http.server::run    → src/http/server.ritz, fn run()
        tools.cli::main     → src/tools/cli.ritz, fn main()
    """
    if "::" not in entry:
        return None

    module_path, fn_name = entry.rsplit("::", 1)

    # Convert module path (dots) to file path (slashes)
    # main → main.ritz
    # http.server → http/server.ritz
    file_rel_path = module_path.replace(".", "/") + ".ritz"

    # Search in each source directory
    for src_spec in sources:
        # Handle exclusion patterns (skip them for search)
        if src_spec.startswith("!"):
            continue

        # Normalize source spec to directory
        src_dir = pkg_dir / src_spec.split("*")[0].rstrip("/")
        if not src_dir.is_dir():
            continue

        candidate = src_dir / file_rel_path
        if candidate.exists():
            return (candidate, fn_name)

    return None


def detect_main_function(source_path: Path) -> str | None:
    """Detect the main function name in a source file.

    Used for backward compatibility with path = "file.ritz" syntax.
    Returns "main" if found, or None.
    """
    from lexer import Lexer
    from parser import Parser
    import ritz_ast as rast

    try:
        source = source_path.read_text()
        lexer = Lexer(source, str(source_path))
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        module = parser.parse_module()

        for item in module.items:
            if isinstance(item, rast.FnDef) and item.name == 'main':
                return 'main'
        return None
    except Exception:
        return None


def discover_sources(pkg_dir: Path, sources: list[str] | None) -> list[Path]:
    """Discover source files based on sources configuration.

    Per RFC #109 §2.2:
    - Directory entries expand to dir/**/*.ritz
    - Explicit globs are used as-is
    - Exclusion patterns (!path) filter out matching files
    - Default: ["src"] if src/ exists, else ["."]

    Args:
        pkg_dir: Package directory (where ritz.toml is)
        sources: List of source specs, or None for default

    Returns:
        List of .ritz file paths
    """
    import fnmatch

    # Handle default
    if sources is None:
        if (pkg_dir / "src").is_dir():
            sources = ["src"]
        else:
            sources = ["."]

    include_patterns = []
    exclude_patterns = []

    for spec in sources:
        if spec.startswith("!"):
            # Exclusion pattern
            exclude_patterns.append(spec[1:])
        else:
            include_patterns.append(spec)

    # Collect all matching files
    all_files = set()
    for pattern in include_patterns:
        pattern_path = pkg_dir / pattern

        if pattern_path.is_dir():
            # Directory → recursive glob
            for f in pattern_path.rglob("*.ritz"):
                all_files.add(f)
        elif "*" in pattern:
            # Explicit glob pattern
            for f in pkg_dir.glob(pattern):
                if f.is_file() and f.suffix == ".ritz":
                    all_files.add(f)
        else:
            # Single file
            if pattern_path.exists() and pattern_path.suffix == ".ritz":
                all_files.add(pattern_path)

    # Apply exclusions
    result = []
    for f in sorted(all_files):
        excluded = False
        rel_path = str(f.relative_to(pkg_dir))
        for excl in exclude_patterns:
            # Match against relative path
            excl_path = pkg_dir / excl
            if excl_path.is_dir():
                # Exclude entire directory
                if str(f).startswith(str(excl_path)):
                    excluded = True
                    break
            elif fnmatch.fnmatch(rel_path, excl) or fnmatch.fnmatch(rel_path, excl + "/**"):
                excluded = True
                break
        if not excluded:
            result.append(f)

    return result


def get_build_profile(config: dict, profile_name: str | None) -> dict:
    """Get build profile settings.

    Per RFC #109 §2.3:
    - Profiles inherit from [build] section
    - Override with [profile.debug] or [profile.release]
    - Default profile is "debug"

    Returns dict with:
        name: str - profile name
        opt_level: int - optimization level (0-3)
        debug: bool - include debug info
        lto: bool - link-time optimization
    """
    # Defaults
    result = {
        "name": profile_name or "debug",
        "opt_level": 0,
        "debug": True,
        "lto": False,
    }

    # Inherit from [build] section
    if "build" in config:
        build = config["build"]
        if "opt-level" in build:
            result["opt_level"] = build["opt-level"]
        if "debug" in build:
            result["debug"] = build["debug"]
        if "lto" in build:
            result["lto"] = build["lto"]

    # Apply profile-specific overrides
    # When profile_name is None, default to "debug" profile
    effective_profile_name = profile_name or "debug"
    if "profile" in config:
        profile = config["profile"].get(effective_profile_name, {})
        if "opt-level" in profile:
            result["opt_level"] = profile["opt-level"]
        if "debug" in profile:
            result["debug"] = profile["debug"]
        if "lto" in profile:
            result["lto"] = profile["lto"]

    return result


def get_output_dir(pkg_dir: Path, profile: dict) -> Path:
    """Get output directory for a build profile.

    Per RFC #109 §3.1:
    - Debug builds → build/debug/
    - Release builds → build/release/
    """
    return pkg_dir / "build" / profile["name"]


# =============================================================================
# RFC #109 Phase 2: Dependency Resolution and Namespacing
# =============================================================================

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


@dataclass
class BinaryConfig:
    """Complete configuration for a binary target.

    Supports both standard hosted builds and freestanding kernel builds.
    """
    name: str                    # Binary name
    src_path: Path               # Main source file
    additional_sources: list[Path]  # Extra sources (deprecated)
    freestanding: bool = False   # If True, no runtime, custom linker
    target: str = ""             # Target triple (e.g., "x86_64-none-elf")
    target_os: str = ""          # Target OS for conditional compilation (e.g., "harland", "linux")
    linker_script: Path | None = None  # Custom linker script
    asm_files: list[Path] | None = None  # Assembly files to compile
    code_model: str = ""         # LLC code model (e.g., "kernel")
    no_red_zone: bool = False    # Disable red zone (for kernels)
    bin_sources: list[str] | None = None  # Per-binary source directories
    pic: bool = False            # Generate position-independent code (for PIE executables)
    link_runtime: bool = False   # Link with Ritz runtime (_start that calls main and sys_exit)
    main_args: int = 0           # Number of args main() takes (0, 2, or 3) for runtime selection

    def __post_init__(self):
        if self.asm_files is None:
            self.asm_files = []
        if self.bin_sources is None:
            self.bin_sources = []


def parse_dependencies(config: dict, pkg_dir: Path) -> dict[str, DependencySpec]:
    """Parse [dependencies] section from ritz.toml config.

    Per RFC #109 §2.6:
    - Dependencies are declared as: name = { path = "..." }
    - Each dependency gets its own namespace for imports
    - Paths are resolved relative to the package directory

    Returns:
        Dict mapping dependency name to DependencySpec
    """
    deps = {}
    deps_config = config.get("dependencies", {})

    for name, spec in deps_config.items():
        if isinstance(spec, dict):
            # Full spec: { path = "...", sources = [...] }
            dep_path = spec.get("path")
            if dep_path is None:
                print(f"  ⚠ Dependency '{name}' missing 'path'", file=sys.stderr)
                continue

            # Resolve path relative to package directory
            dep_path = (pkg_dir / dep_path).resolve()
            if not dep_path.exists():
                print(f"  ⚠ Dependency '{name}' path not found: {dep_path}", file=sys.stderr)
                continue

            # Get sources from dependency's ritz.toml if not specified
            sources = spec.get("sources")
            if sources is None:
                # Try to read from dependency's ritz.toml
                dep_toml = dep_path / "ritz.toml"
                if dep_toml.exists():
                    with open(dep_toml, "rb") as f:
                        dep_config = tomllib.load(f)
                    # Check both top-level and inside [package] (TOML quirk)
                    sources = dep_config.get("sources")
                    if sources is None:
                        sources = dep_config.get("package", {}).get("sources", ["src"])
                else:
                    sources = ["src"]

            if isinstance(sources, str):
                sources = [sources]

            deps[name] = DependencySpec(name=name, path=dep_path, sources=sources)
        elif isinstance(spec, str):
            # Shorthand: just a path
            dep_path = (pkg_dir / spec).resolve()
            if not dep_path.exists():
                print(f"  ⚠ Dependency '{name}' path not found: {dep_path}", file=sys.stderr)
                continue
            deps[name] = DependencySpec(name=name, path=dep_path, sources=["src"])

    return deps


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
        dep_toml = dep_spec.path / "ritz.toml"
        if dep_toml.exists():
            with open(dep_toml, "rb") as f:
                dep_config = tomllib.load(f)
            transitive = get_transitive_dependencies(dep_spec.path, dep_config, seen.copy())

            # Add transitive deps (but don't override direct deps)
            for trans_name, trans_spec in transitive.items():
                if trans_name not in all_deps:
                    all_deps[trans_name] = trans_spec

    return all_deps


# =============================================================================
# End RFC #109 Phase 2
# =============================================================================


def find_package_at(path: Path) -> tuple[Path, dict] | None:
    """Find a package at the given path (looks for ritz.toml)."""
    path = path.resolve()

    # If path is a file, look in its parent directory
    if path.is_file():
        path = path.parent

    # Look for ritz.toml in this directory
    toml_path = path / "ritz.toml"
    if toml_path.exists():
        with open(toml_path, "rb") as f:
            config = tomllib.load(f)
        return (path, config)

    return None


def find_package_by_name_or_path(name_or_path: str) -> tuple[Path, dict] | None:
    """Find a package by name or path.

    Tries in order:
    1. If it's a path to a directory with ritz.toml, use that
    2. If it's a path to a ritz.toml file, use its directory
    3. Look in current directory for matching subdirectory
    """
    path = Path(name_or_path)

    # Try as direct path
    if path.exists():
        return find_package_at(path)

    # Try as subdirectory of current working directory
    cwd = Path.cwd()
    subdir = cwd / name_or_path
    if subdir.exists():
        return find_package_at(subdir)

    return None


def find_all_packages(search_dir: Path = None) -> list[tuple[Path, dict]]:
    """Find all packages with ritz.toml files under search_dir.

    Defaults to current working directory if not specified.
    """
    if search_dir is None:
        search_dir = Path.cwd()

    search_dir = search_dir.resolve()
    packages = []

    # Search for all ritz.toml files recursively
    for toml_path in sorted(search_dir.glob("**/ritz.toml")):
        with open(toml_path, "rb") as f:
            config = tomllib.load(f)
        packages.append((toml_path.parent, config))

    return packages


def find_packages() -> list[tuple[Path, dict]]:
    """Find all packages - searches from current directory."""
    return find_all_packages()


def get_binaries(pkg_dir: Path, config: dict) -> list[BinaryConfig]:
    """Get list of BinaryConfig objects for all binary targets in a package.

    Returns empty list for test-only packages (no binary to build).

    Supports both RFC #109 syntax and legacy syntax:
    - RFC #109: entry = "module::main"  → resolves to src/module.ritz
    - Legacy:   path = "src/main.ritz"  → direct file path

    Also supports freestanding builds with:
    - freestanding = true
    - target = "x86_64-none-elf"
    - [bin.NAME.linker] script = "linker.ld"
    - [bin.NAME.asm] files = ["boot.s", "isr.s"]
    - [bin.NAME.flags] code-model = "kernel", no-red-zone = true
    """
    binaries = []

    # Check if this is a test-only package
    is_test_only = config.get("build", {}).get("test_only", False)
    if is_test_only:
        return []  # Test-only packages have no binaries

    # Get package-level sources configuration (RFC #109)
    # Check top-level, [package], and [build] sections (TOML puts keys in current section)
    pkg_sources = config.get("sources")
    if pkg_sources is None:
        pkg_sources = config.get("package", {}).get("sources")
    if pkg_sources is None:
        pkg_sources = config.get("build", {}).get("sources")
    if pkg_sources is None:
        pkg_sources = ["src"]  # Default
    if isinstance(pkg_sources, str):
        pkg_sources = [pkg_sources]

    # Check for [[bin]] sections
    if "bin" in config:
        for bin_entry in config["bin"]:
            name = bin_entry["name"]

            # RFC #109: entry = "module::function"
            if "entry" in bin_entry:
                entry = bin_entry["entry"]
                # Use bin-specific sources if provided, else package-level
                bin_sources_list = bin_entry.get("sources", pkg_sources)
                if isinstance(bin_sources_list, str):
                    bin_sources_list = [bin_sources_list]
                result = resolve_entry_point(entry, pkg_dir, bin_sources_list)
                if result is None:
                    print(f"  ⚠ Could not resolve entry point: {entry}", file=sys.stderr)
                    continue
                src_path, _fn_name = result
            # Legacy: path = "src/main.ritz"
            elif "path" in bin_entry:
                src_path = pkg_dir / bin_entry["path"]
                # Skip non-.ritz files (e.g., .py or .sh scripts)
                if not src_path.suffix == ".ritz":
                    continue
            # Default: src/{name}.ritz
            else:
                src_path = pkg_dir / "src" / f"{name}.ritz"

            # Get additional sources if specified (legacy, deprecated)
            additional_sources = []
            if "sources" in bin_entry and isinstance(bin_entry["sources"], list):
                # Check if these are paths or directory specs
                for src in bin_entry["sources"]:
                    src_path_check = pkg_dir / src
                    if src_path_check.is_file():
                        additional_sources.append(src_path_check)

            # Parse freestanding build options
            freestanding = bin_entry.get("freestanding", False)
            target = bin_entry.get("target", "")
            target_os = bin_entry.get("target_os", "")

            # Parse [bin.NAME.linker] section
            # TOML puts [bin.harland.linker] as bin_entry["harland"]["linker"]
            nested_config = bin_entry.get(name, {})
            linker_config = nested_config.get("linker", {})
            linker_script = None
            if linker_config.get("script"):
                linker_script = pkg_dir / linker_config["script"]

            # Parse [bin.NAME.asm] section
            asm_config = nested_config.get("asm", {})
            asm_files = []
            for asm_file in asm_config.get("files", []):
                asm_files.append(pkg_dir / asm_file)

            # Parse [bin.NAME.flags] section
            flags_config = nested_config.get("flags", {})
            code_model = flags_config.get("code-model", "")
            no_red_zone = flags_config.get("no-red-zone", False)
            pic = flags_config.get("pic", False)

            # Parse runtime linking options
            # link_runtime: bool - link with Ritz runtime (_start)
            # main_args: int - number of args main() takes (0, 2, or 3)
            link_runtime = bin_entry.get("link_runtime", False)
            main_args = bin_entry.get("main_args", 0)

            # Per-binary source directories
            bin_sources = bin_entry.get("sources", [])
            if isinstance(bin_sources, str):
                bin_sources = [bin_sources]

            binaries.append(BinaryConfig(
                name=name,
                src_path=src_path,
                additional_sources=additional_sources,
                freestanding=freestanding,
                target=target,
                target_os=target_os,
                linker_script=linker_script,
                asm_files=asm_files,
                code_model=code_model,
                no_red_zone=no_red_zone,
                bin_sources=bin_sources,
                pic=pic,
                link_runtime=link_runtime,
                main_args=main_args,
            ))
    else:
        # Default: single binary with package name
        name = config["package"]["name"]
        src_path = pkg_dir / "src" / "main.ritz"
        binaries.append(BinaryConfig(
            name=name,
            src_path=src_path,
            additional_sources=[],
        ))

    return binaries


def compile_binary(name: str, src_path: Path, out_dir: Path, additional_sources: list[Path] = None, keep_artifacts: bool = False, use_cache: bool = True, profile: dict = None, dependencies: dict[str, DependencySpec] = None, pkg_dir: Path = None, source_roots: list[str] = None) -> Path:
    """Compile Ritz source file(s) to a binary.

    Args:
        name: Name of the output binary
        src_path: Main source file (entry point with main())
        out_dir: Directory to place the binary
        additional_sources: Additional .ritz files to compile and link (deprecated, use imports)
        keep_artifacts: If True, keep .ll files in build/ for debugging
        use_cache: If True, use build cache to skip unchanged files
        profile: Build profile dict with opt_level, debug, lto settings (RFC #109)
        dependencies: RFC #109 dependency specs for namespace resolution
        pkg_dir: Package directory for project root (defaults to ROOT for standalone builds)
        source_roots: List of source directories to search for imports (e.g., ["src", "kernel/src"])

    Uses separate compilation model:
    1. Discover all source files via import resolution
    2. Compile each source file to .ll (functions from current file: define, imports: declare)
    3. Convert .ll to .bc (bitcode) for faster linking (RFC #109 Phase 3)
    4. Link all .bc files together with clang/gcc

    Uses gcc for linking when clang is not available.
    """
    import json
    import shutil as shutil_mod

    # Default profile if not specified
    if profile is None:
        profile = {"name": "debug", "opt_level": 0, "debug": True, "lto": False}
    bin_path = out_dir / name
    cache = get_build_cache()

    # Check for llvm-as (needed for .ll → .bc conversion)
    has_llvm_as = shutil_mod.which("llvm-as") is not None

    # Discover all source files through import resolution using subprocess
    # This avoids Python import path issues
    list_deps_script = RITZ0_DIR / "list_deps.py"

    # Build command with project root and optional dependencies
    cmd = [sys.executable, str(list_deps_script), str(src_path)]
    # Pass the package directory as project root (fallback to ritz ROOT for standalone builds)
    # This ensures ritzlib is resolved consistently across all dependencies
    project_root = pkg_dir if pkg_dir else ROOT
    cmd.extend(["--project-root", str(project_root)])
    if dependencies:
        # Convert DependencySpec to JSON for passing to subprocess
        deps_json = {
            name: {"path": str(spec.path), "sources": spec.sources}
            for name, spec in dependencies.items()
        }
        cmd.extend(["--deps", json.dumps(deps_json)])
    if source_roots:
        cmd.extend(["--sources", json.dumps(source_roots)])

    # Pass environment including RITZ_PATH for import resolution
    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ)
    if result.returncode != 0:
        print(f"  ✗ import resolution failed: {result.stderr}", file=sys.stderr)
        return None
    all_sources = [Path(f.strip()) for f in result.stdout.strip().split('\n') if f.strip()]

    # Add any explicit additional sources (for backwards compatibility)
    if additional_sources:
        for src in additional_sources:
            if src not in all_sources:
                all_sources.insert(-1, src)  # Insert before main

    # Use build/ directory for artifacts if keeping them, otherwise temp
    if keep_artifacts:
        artifact_dir = ROOT / "build"
        artifact_dir.mkdir(exist_ok=True)
    else:
        artifact_dir = Path(tempfile.mkdtemp())

    # Collect paths for linking: .bc if available, else .ll
    link_files = []

    # Detect main's signature to choose the right runtime
    main_params = detect_main_signature(src_path)
    runtime_obj = get_runtime_object(main_params)

    # Check runtime object exists
    if not runtime_obj.exists():
        print(f"  ✗ Runtime object not found: {runtime_obj}", file=sys.stderr)
        print(f"    Run 'make' in runtime/ directory to build", file=sys.stderr)
        return None

    try:
        # Compile each source file to LLVM IR, optionally convert to bitcode
        # All sources compiled with --no-runtime; _start comes from runtime .o
        for i, src in enumerate(all_sources):
            is_main = (i == len(all_sources) - 1)

            # Use a unique name to avoid collisions (e.g., multiple sys.ritz)
            # Hash the full path to get a unique identifier
            import hashlib
            path_hash = hashlib.md5(str(src).encode()).hexdigest()[:8]
            src_name = f"{src.stem}_{path_hash}"
            ll_path = artifact_dir / f"{src_name}.ll"
            bc_path = artifact_dir / f"{src_name}.bc"

            # RFC #109 Phase 3: Check for cached .bc first (faster than .ll)
            if use_cache and has_llvm_as:
                cached_bc = cache.get_cached_bc(src)
                if cached_bc:
                    # Copy cached .bc to artifact dir
                    shutil_mod.copy2(cached_bc, bc_path)
                    link_files.append(bc_path)
                    continue

            # Check cache for .ll file
            if use_cache:
                needs_rebuild, reason = cache.needs_rebuild(src)
                if not needs_rebuild:
                    cached_ll = cache.get_cached_ll(src)
                    if cached_ll:
                        ll_path.write_text(cached_ll)
                        # Convert to .bc if llvm-as available
                        if has_llvm_as:
                            as_result = subprocess.run(
                                ["llvm-as", str(ll_path), "-o", str(bc_path)],
                                capture_output=True, text=True
                            )
                            if as_result.returncode == 0:
                                cache.update_bc_cache(src, bc_path)
                                link_files.append(bc_path)
                                continue
                        link_files.append(ll_path)
                        continue

            # All sources compiled without runtime - _start comes from external .o
            compile_cmd = [sys.executable, str(RITZ0), str(src), "-o", str(ll_path), "--no-runtime"]

            # Pass dependencies if any (RFC #109 Phase 2)
            if dependencies:
                deps_json = {
                    name: {"path": str(spec.path), "sources": spec.sources}
                    for name, spec in dependencies.items()
                }
                compile_cmd.extend(["--deps", json.dumps(deps_json)])
            # Pass source roots if any (for import resolution)
            if source_roots:
                compile_cmd.extend(["--sources", json.dumps(source_roots)])
            # Pass project root (package directory) for source root resolution
            if pkg_dir:
                compile_cmd.extend(["--project-root", str(pkg_dir)])

            result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ✗ ritz0 failed for {src.name}: {result.stderr}", file=sys.stderr)
                return None

            # Update .ll cache
            if use_cache:
                ll_content = ll_path.read_text()
                cache.update_cache(src, ll_content)

            # RFC #109 Phase 3: Convert .ll to .bc for faster linking
            if has_llvm_as:
                as_result = subprocess.run(
                    ["llvm-as", str(ll_path), "-o", str(bc_path)],
                    capture_output=True, text=True
                )
                if as_result.returncode == 0:
                    if use_cache:
                        cache.update_bc_cache(src, bc_path)
                    link_files.append(bc_path)
                else:
                    # Fallback to .ll if llvm-as fails
                    link_files.append(ll_path)
            else:
                link_files.append(ll_path)

        # Link all .bc/.ll files with the runtime .o
        # Use -g to preserve DWARF debug info, -nostdlib for bare-metal
        # Debug: print number of files to link
        print(f"  ⚡ Linking {len(link_files)} object files...")
        if os.environ.get("RITZ_DEBUG"):
            for lf in link_files:
                print(f"    - {lf}")
        # Try clang first, fall back to gcc
        linker_cmd = None
        linker_name = None

        # Check which linker is available
        import shutil
        if shutil.which("clang"):
            linker_cmd = ["clang"]
            linker_name = "clang"
        elif shutil.which("gcc"):
            linker_cmd = ["gcc"]
            linker_name = "gcc"
        else:
            print(f"  ✗ Neither clang nor gcc found in PATH", file=sys.stderr)
            return None

        # Link: runtime.o + all .bc/.ll files -> binary
        # Build link command with profile-specific options
        # -march=native enables CPU-specific features (SHA-NI, AES-NI, etc.) for code generation
        link_cmd = linker_cmd + [str(runtime_obj)] + [str(f) for f in link_files] + ["-o", str(bin_path), "-nostdlib", "-march=native"]

        # Add optimization level
        opt_level = profile.get("opt_level", 0)
        link_cmd.append(f"-O{opt_level}")

        # Add debug info if requested
        if profile.get("debug", True):
            link_cmd.append("-g")

        # Add LTO if requested
        if profile.get("lto", False):
            link_cmd.append("-flto")

        # Debug: print link command
        if os.environ.get("RITZ_DEBUG"):
            print(f"  [DEBUG] Link cmd: {' '.join(link_cmd[:5])}... ({len(link_files)} files)")
            print(f"  [DEBUG] Full command: {' '.join(link_cmd)}")

        result = subprocess.run(link_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ✗ {linker_name} linking failed: {result.stderr}", file=sys.stderr)
            return None

        return bin_path
    finally:
        # Clean up temp directory if not keeping artifacts
        # Disable cleanup temporarily for debugging
        if os.environ.get("RITZ_KEEP_TEMP"):
            print(f"  [DEBUG] Keeping temp dir: {artifact_dir}")
        elif not keep_artifacts and artifact_dir.exists():
            import shutil
            shutil.rmtree(artifact_dir, ignore_errors=True)


def find_llvm_tool(name: str) -> str:
    """Find LLVM tool, trying versioned names."""
    import shutil as shutil_mod
    # For lld, prefer ld.lld over the generic wrapper, fall back to GNU ld
    if name == "lld":
        if shutil_mod.which("ld.lld"):
            return "ld.lld"
        for ver in ["20", "19", "18", "17", "16", "15"]:
            if shutil_mod.which(f"ld.lld-{ver}"):
                return f"ld.lld-{ver}"
        # Fall back to GNU ld if LLD is not available
        if shutil_mod.which("ld"):
            return "ld"
    # Try unversioned first
    if shutil_mod.which(name):
        return name
    # Try common version suffixes
    for ver in ["20", "19", "18", "17", "16", "15", "14"]:
        versioned = f"{name}-{ver}"
        if shutil_mod.which(versioned):
            return versioned
    # Not found
    return name  # Will fail later with helpful error


def compile_freestanding_binary(
    bin_config: BinaryConfig,
    out_dir: Path,
    pkg_dir: Path,
    keep_artifacts: bool = False,
    use_cache: bool = True,
    profile: dict = None,
    dependencies: dict[str, DependencySpec] = None,
    source_roots: list[str] = None,
) -> Path:
    """Compile a freestanding binary (kernel, bootloader, etc.).

    Unlike compile_binary(), this:
    - Does NOT link with Ritz runtime
    - Uses llc to compile to object files with custom target triple
    - Assembles .s files
    - Links with ld.lld using custom linker script

    Args:
        bin_config: BinaryConfig with freestanding options
        out_dir: Output directory
        pkg_dir: Package directory
        keep_artifacts: Keep .ll, .o files
        use_cache: Use build cache
        profile: Build profile
        dependencies: RFC #109 dependencies
        source_roots: List of source directories to search for imports
    """
    import json
    import shutil as shutil_mod

    if profile is None:
        profile = {"name": "debug", "opt_level": 0, "debug": True, "lto": False}

    name = bin_config.name
    src_path = bin_config.src_path
    target = bin_config.target or "x86_64-none-elf"
    target_os = bin_config.target_os or ""  # For conditional compilation (e.g., "harland")
    linker_script = bin_config.linker_script
    asm_files = bin_config.asm_files or []
    code_model = bin_config.code_model
    no_red_zone = bin_config.no_red_zone
    pic = bin_config.pic

    # UEFI targets need special handling
    is_uefi = "uefi" in target.lower()

    # Output binary path (ELF for kernels, EFI for UEFI)
    if is_uefi:
        bin_path = out_dir / f"{name.upper()}.EFI"
    else:
        bin_path = out_dir / f"{name}.elf"

    # Artifact directory
    if keep_artifacts:
        artifact_dir = out_dir / "obj"
        artifact_dir.mkdir(exist_ok=True)
    else:
        artifact_dir = Path(tempfile.mkdtemp())

    # Find LLVM tools
    lld = find_llvm_tool("lld")

    # Collect object files to link
    object_files = []

    try:
        # Step 1: Discover all Ritz source files via imports
        list_deps_script = RITZ0_DIR / "list_deps.py"
        cmd = [sys.executable, str(list_deps_script), str(src_path)]
        cmd.extend(["--project-root", str(pkg_dir)])
        if dependencies:
            deps_json = {
                dep_name: {"path": str(spec.path), "sources": spec.sources}
                for dep_name, spec in dependencies.items()
            }
            cmd.extend(["--deps", json.dumps(deps_json)])
        if source_roots:
            # Resolve source roots to absolute paths relative to pkg_dir
            abs_source_roots = [str(pkg_dir / sr) for sr in source_roots]
            cmd.extend(["--sources", json.dumps(abs_source_roots)])

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ✗ import resolution failed: {result.stderr}", file=sys.stderr)
            return None

        all_sources = [Path(f.strip()) for f in result.stdout.strip().split('\n') if f.strip()]

        # Step 2: Compile each Ritz source to LLVM IR, then to object file
        print(f"  Compiling {len(all_sources)} Ritz source file(s)...")
        for src in all_sources:
            import hashlib
            path_hash = hashlib.md5(str(src).encode()).hexdigest()[:8]
            src_name = f"{src.stem}_{path_hash}"
            ll_path = artifact_dir / f"{src_name}.ll"
            obj_path = artifact_dir / f"{src_name}.o"

            # Compile Ritz to LLVM IR
            compile_cmd = [
                sys.executable, str(RITZ0), str(src),
                "-o", str(ll_path),
                "--no-runtime"
            ]
            # Pass target OS for [[target_os = "..."]] conditional compilation
            if target_os:
                compile_cmd.extend(["--target-os", target_os])
            if dependencies:
                deps_json = {
                    dep_name: {"path": str(spec.path), "sources": spec.sources}
                    for dep_name, spec in dependencies.items()
                }
                compile_cmd.extend(["--deps", json.dumps(deps_json)])
            if source_roots:
                # Resolve source roots to absolute paths relative to pkg_dir
                abs_source_roots = [str(pkg_dir / sr) for sr in source_roots]
                compile_cmd.extend(["--sources", json.dumps(abs_source_roots)])

            result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ✗ ritz0 failed for {src.name}: {result.stderr}", file=sys.stderr)
                return None

            # Compile LLVM IR to object file with target-specific options
            # Use clang -c which can compile .ll files directly (more portable than llc)
            if is_uefi:
                # UEFI: compile for Windows x64 ABI (produces COFF objects for lld-link)
                clang_cmd = [
                    "clang", "-c",
                    "--target=x86_64-unknown-windows-gnu",  # Windows x64 target for COFF
                    "-fshort-wchar",      # UEFI uses 16-bit wchar
                    "-mno-red-zone",      # Required for UEFI
                    "-fno-stack-protector",
                    "-ffreestanding",
                ]
            else:
                clang_cmd = [
                    "clang", "-c",
                    f"--target={target}",
                    "-march=native",  # Enable CPU-specific features (SHA-NI, AES-NI, etc.)
                ]
                # Add PIC flag if explicitly requested or for Linux targets
                if pic or target.endswith("-linux"):
                    clang_cmd.append("-fPIC")

                if code_model:
                    # Note: -mcmodel=large is incompatible with -fPIC on x86_64
                    # For PIC code, use "small" model (default) which supports
                    # GOT/PLT relocations for position-independent code
                    if pic and code_model == "large":
                        # Skip code model for PIC - use default small model
                        pass
                    else:
                        clang_cmd.append(f"-mcmodel={code_model}")
                if no_red_zone:
                    clang_cmd.append("-mno-red-zone")

            clang_cmd.extend(["-o", str(obj_path), str(ll_path)])

            result = subprocess.run(clang_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ✗ clang failed for {src.name}: {result.stderr}", file=sys.stderr)
                return None

            object_files.append(obj_path)

        # Step 3: Assemble .s files
        if asm_files:
            print(f"  Assembling {len(asm_files)} assembly file(s)...")
            for asm_file in asm_files:
                if not asm_file.exists():
                    print(f"  ⚠ Assembly file not found: {asm_file}")
                    continue

                # Special case: user_elf.s includes an ELF binary that might not exist yet
                # Read the file to check for .incbin directives
                asm_content = asm_file.read_text()
                skip_file = False
                for line in asm_content.split('\n'):
                    if '.incbin' in line:
                        # Extract the path from .incbin "path"
                        import re
                        match = re.search(r'\.incbin\s+"([^"]+)"', line)
                        if match:
                            inc_path = pkg_dir / match.group(1)
                            if not inc_path.exists():
                                print(f"  ⚠ Skipping {asm_file.name}: missing {match.group(1)}")
                                skip_file = True
                                break
                if skip_file:
                    continue

                obj_name = f"{asm_file.stem}.o"
                obj_path = artifact_dir / obj_name

                # Use GNU as for assembly (supports .code32/.code64 directives)
                # Run from pkg_dir so .incbin relative paths work
                as_cmd = ["as", "--64", "-o", str(obj_path), str(asm_file)]
                result = subprocess.run(as_cmd, capture_output=True, text=True, cwd=str(pkg_dir))
                if result.returncode != 0:
                    print(f"  ✗ as failed for {asm_file.name}: {result.stderr}", file=sys.stderr)
                    return None

                object_files.append(obj_path)

        # Step 3.5: Add runtime object file if requested
        # The runtime provides _start which calls main() and then sys_exit()
        if bin_config.link_runtime and not is_uefi:
            # Determine the runtime variant based on main_args and target_os
            main_args = bin_config.main_args
            if main_args == 3:
                runtime_variant = "ritz_start_envp"
            elif main_args == 2:
                runtime_variant = "ritz_start"
            else:
                runtime_variant = "ritz_start_noargs"

            # Choose OS-specific runtime
            if target_os == "harland":
                runtime_suffix = ".harland.x86_64.o"
            else:
                runtime_suffix = ".x86_64.o"

            runtime_name = f"{runtime_variant}{runtime_suffix}"
            runtime_path = RITZ0_DIR.parent / "runtime" / runtime_name

            if runtime_path.exists():
                object_files.insert(0, runtime_path)  # Runtime should be first
                print(f"  📦 Linking with runtime: {runtime_name}")
            else:
                print(f"  ⚠ Runtime not found: {runtime_path}", file=sys.stderr)
                print(f"    Run 'make' in projects/ritz/runtime/ to build", file=sys.stderr)

        # Step 4: Link
        print(f"  ⚡ Linking {len(object_files)} object files...")

        if is_uefi:
            # UEFI: Use lld-link to directly produce PE/COFF EFI application
            # This produces a proper PE32+ with optional header that UEFI expects
            import shutil as shutil_mod

            # Check for lld-link
            lld_link = shutil_mod.which("lld-link")
            if lld_link:
                # Direct PE/COFF linking with lld-link
                print(f"  📦 Linking PE/COFF with lld-link...")
                link_cmd = [
                    lld_link,
                    "/subsystem:efi_application",
                    "/entry:efi_main",
                    f"/out:{bin_path}",
                ]
                link_cmd.extend([str(obj) for obj in object_files])

                result = subprocess.run(link_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"  ✗ lld-link failed: {result.stderr}", file=sys.stderr)
                    return None
            else:
                # Fallback: Link as ELF shared object, then convert to PE with objcopy
                # Note: This produces a minimal PE that may not work with all UEFI firmwares
                elf_path = artifact_dir / f"{name}.so"

                link_cmd = [
                    lld,
                    "-shared",
                    "-Bsymbolic",
                    "--no-undefined",
                    "-o", str(elf_path),
                ]
                link_cmd.extend([str(obj) for obj in object_files])

                result = subprocess.run(link_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"  ✗ Linking failed: {result.stderr}", file=sys.stderr)
                    return None

                # Convert ELF to PE using objcopy
                print(f"  📦 Converting to PE/COFF (objcopy fallback)...")
                objcopy_cmd = [
                    "objcopy",
                    "-j", ".text",
                    "-j", ".rodata",
                    "-j", ".data",
                    "-j", ".bss",
                    "-j", ".rela",
                    "-O", "pei-x86-64",
                    str(elf_path),
                    str(bin_path),
                ]
                result = subprocess.run(objcopy_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"  ✗ objcopy failed: {result.stderr}", file=sys.stderr)
                    return None

                # Fix PE subsystem field - objcopy doesn't set it correctly for UEFI
                # The subsystem field is at offset 0x5C in the PE optional header
                # Value 10 = EFI Application
                print(f"  🔧 Fixing PE subsystem...")
                with open(bin_path, 'r+b') as f:
                    # Read DOS header to find PE header offset
                    f.seek(0x3C)
                    pe_offset = int.from_bytes(f.read(4), 'little')
                    # Subsystem is at PE + 0x5C (in optional header)
                    subsystem_offset = pe_offset + 0x5C
                    f.seek(subsystem_offset)
                    # Write EFI Application subsystem (10)
                    f.write((10).to_bytes(2, 'little'))
        else:
            # Normal freestanding ELF linking
            link_cmd = [lld]

            # For PIE executables, add -pie flag and --no-dynamic-linker
            # (freestanding PIE doesn't need a dynamic linker)
            if pic:
                link_cmd.extend(["--pie", "--no-dynamic-linker"])

            if linker_script and linker_script.exists():
                link_cmd.extend(["-T", str(linker_script)])

            link_cmd.extend(["-o", str(bin_path)])
            link_cmd.extend([str(obj) for obj in object_files])

            result = subprocess.run(link_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ✗ ld.lld linking failed: {result.stderr}", file=sys.stderr)
                return None

        return bin_path

    finally:
        # Clean up temp directory if not keeping artifacts
        if not keep_artifacts and artifact_dir.exists():
            import shutil
            shutil.rmtree(artifact_dir, ignore_errors=True)


def build_package(pkg_dir: Path, config: dict, keep_artifacts: bool = False, use_cache: bool = True, profile_name: str = None) -> list[Path]:
    """Build all binaries in a package.

    Args:
        pkg_dir: Package directory (where ritz.toml is)
        config: Parsed ritz.toml config
        keep_artifacts: Keep intermediate .ll files for debugging
        use_cache: Use build cache to skip unchanged files
        profile_name: Build profile ("debug", "release", or None for default)
    """
    pkg_name = config["package"]["name"]
    profile = get_build_profile(config, profile_name)
    out_dir = get_output_dir(pkg_dir, profile)

    # Create output directory
    out_dir.mkdir(parents=True, exist_ok=True)

    # Parse dependencies (RFC #109 Phase 2)
    dependencies = parse_dependencies(config, pkg_dir)

    # Get source roots for import resolution
    # Check top-level, [package], and [build] sections
    source_roots = config.get("sources")
    if source_roots is None:
        source_roots = config.get("package", {}).get("sources")
    if source_roots is None:
        source_roots = config.get("build", {}).get("sources")
    # Convert single string to list
    if isinstance(source_roots, str):
        source_roots = [source_roots]

    if dependencies:
        print(f"📦 Building {pkg_name} ({profile['name']}) with {len(dependencies)} dependencies...")
    else:
        print(f"📦 Building {pkg_name} ({profile['name']})...")

    binaries = get_binaries(pkg_dir, config)
    built = []

    for bin_config in binaries:
        # Show source files being compiled
        try:
            src_rel = bin_config.src_path.relative_to(pkg_dir)
        except ValueError:
            src_rel = bin_config.src_path

        if bin_config.freestanding:
            # Freestanding build (kernel, bootloader)
            asm_count = len(bin_config.asm_files) if bin_config.asm_files else 0
            target_info = bin_config.target or "freestanding"
            print(f"  🔨 {bin_config.name} <- {src_rel} ({target_info}, {asm_count} asm files)", end="")

            bin_path = compile_freestanding_binary(
                bin_config=bin_config,
                out_dir=out_dir,
                pkg_dir=pkg_dir,
                keep_artifacts=keep_artifacts,
                use_cache=use_cache,
                profile=profile,
                dependencies=dependencies,
                source_roots=source_roots,
            )
        else:
            # Standard hosted build
            if bin_config.additional_sources:
                all_srcs = [src_rel] + [s.relative_to(pkg_dir) for s in bin_config.additional_sources]
                src_display = ", ".join(str(s) for s in all_srcs)
                print(f"  🔨 {bin_config.name} <- [{src_display}]", end="")
            else:
                print(f"  🔨 {bin_config.name} <- {src_rel}", end="")

            bin_path = compile_binary(
                bin_config.name, bin_config.src_path, out_dir,
                additional_sources=bin_config.additional_sources,
                keep_artifacts=keep_artifacts,
                use_cache=use_cache,
                profile=profile,
                dependencies=dependencies,
                pkg_dir=pkg_dir,
                source_roots=source_roots
            )
        if bin_path:
            try:
                rel_path = bin_path.relative_to(ROOT)
            except ValueError:
                # If bin_path is not relative to ROOT (e.g., running from subdirectory),
                # just show relative to cwd
                try:
                    rel_path = bin_path.relative_to(Path.cwd())
                except ValueError:
                    rel_path = bin_path
            print(f"\n  ✓ {rel_path}")
            built.append(bin_path)
        else:
            print(f"\n  ✗ Failed to build {bin_config.name}")

    return built


def run_tests(pkg_dir: Path, config: dict) -> bool:
    """Run tests for a package."""
    pkg_name = config["package"]["name"]
    all_passed = True
    tests_found = False

    # Collect all .ritz test files
    ritz_tests = []

    # Check test/ subdirectory
    test_dir = pkg_dir / "test"
    if test_dir.exists():
        ritz_tests.extend(test_dir.glob("*.ritz"))

    # For test-only packages, also check package root for test_*.ritz files
    is_test_only = config.get("build", {}).get("test_only", False)
    if is_test_only:
        ritz_tests.extend(pkg_dir.glob("test_*.ritz"))

    ritz_tests = sorted(set(ritz_tests))  # Dedupe and sort

    if ritz_tests:
        tests_found = True
        print(f"  🧪 Running {len(ritz_tests)} .ritz test file(s)...")
        result = subprocess.run(
            [sys.executable, str(RITZ0), "--test"] + [str(t) for t in ritz_tests],
            cwd=ROOT,  # Run from project root so imports work
            capture_output=True, text=True,
            timeout=300  # 5 minute timeout per test suite
        )
        if result.returncode == 0:
            # Extract summary from output
            lines = result.stdout.strip().split('\n')
            if lines:
                print(f"    {lines[-1]}")
        else:
            print(f"  ✗ .ritz tests failed:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            all_passed = False

    # Run test.sh if it exists
    test_script = pkg_dir / "test.sh"
    if test_script.exists():
        tests_found = True
        print(f"  🧪 Running test.sh...")
        result = subprocess.run(
            ["bash", str(test_script)],
            cwd=pkg_dir,
            capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"    ✓ test.sh passed")
        else:
            print(f"  ✗ test.sh failed:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            all_passed = False

    if not tests_found:
        print(f"  ⚠ No tests found, skipping")

    return all_passed


def cmd_list(args):
    """List all packages under current directory."""
    packages = find_all_packages()
    if not packages:
        print("No packages found (no ritz.toml files)")
        return 0

    print(f"Found {len(packages)} packages:\n")
    cwd = Path.cwd()
    for pkg_dir, config in packages:
        pkg_name = config["package"]["name"]
        binaries = get_binaries(pkg_dir, config)
        is_test_only = config.get("build", {}).get("test_only", False)

        try:
            rel_path = pkg_dir.relative_to(cwd)
        except ValueError:
            rel_path = pkg_dir

        if is_test_only:
            print(f"  {rel_path}/  →  {pkg_name} (test-only)")
        elif binaries:
            bin_names = ", ".join(b.name for b in binaries)
            print(f"  {rel_path}/  →  {pkg_name} ({bin_names})")
        else:
            print(f"  {rel_path}/  →  {pkg_name}")


def cmd_build(args):
    """Build packages."""
    keep_artifacts = getattr(args, 'debug', False)
    use_cache = not getattr(args, 'no_cache', False)
    profile_name = "release" if getattr(args, 'release', False) else None

    if args.all:
        # Build all packages under current directory
        targets = find_all_packages()
        if not targets:
            print("No packages found (no ritz.toml files)", file=sys.stderr)
            return 1
    elif args.name:
        # Try to find package by path or name
        result = find_package_by_name_or_path(args.name)
        if result:
            targets = [result]
        else:
            print(f"Package '{args.name}' not found", file=sys.stderr)
            return 1
    else:
        # No name specified - try current directory
        result = find_package_at(Path.cwd())
        if result:
            targets = [result]
        else:
            print("No ritz.toml found in current directory", file=sys.stderr)
            print("Usage: ritz build [path] or ritz build --all", file=sys.stderr)
            return 1

    success = True
    for pkg_dir, config in targets:
        built = build_package(pkg_dir, config, keep_artifacts=keep_artifacts, use_cache=use_cache, profile_name=profile_name)
        if not built:
            success = False

    if keep_artifacts:
        print(f"\n📁 Debug artifacts kept in build/")

    return 0 if success else 1


def cmd_test(args):
    """Build and test packages."""
    keep_artifacts = getattr(args, 'debug', False)
    use_cache = not getattr(args, 'no_cache', False)
    profile_name = "release" if getattr(args, 'release', False) else None

    if args.all:
        # Test all packages under current directory
        targets = find_all_packages()
        if not targets:
            print("No packages found (no ritz.toml files)", file=sys.stderr)
            return 1
    elif args.name:
        # Try to find package by path or name
        result = find_package_by_name_or_path(args.name)
        if result:
            targets = [result]
        else:
            print(f"Package '{args.name}' not found", file=sys.stderr)
            return 1
    else:
        # No name specified - try current directory
        result = find_package_at(Path.cwd())
        if result:
            targets = [result]
        else:
            print("No ritz.toml found in current directory", file=sys.stderr)
            print("Usage: ritz test [path] or ritz test --all", file=sys.stderr)
            return 1

    all_passed = True
    for pkg_dir, config in targets:
        # Check if this is a test-only package
        is_test_only = config.get("build", {}).get("test_only", False)

        if is_test_only:
            # For test-only packages, run tests directly without building a binary
            print(f"📦 {config['package']['name']} (test-only)")
            if not run_tests(pkg_dir, config):
                all_passed = False
        else:
            # Normal package: build then test
            built = build_package(pkg_dir, config, keep_artifacts=keep_artifacts, use_cache=use_cache, profile_name=profile_name)
            # Check if there are any .ritz binaries to build
            binaries = get_binaries(pkg_dir, config)
            has_ritz_binaries = len(binaries) > 0

            if has_ritz_binaries:
                # Package has ritz binaries - build result matters
                if built:
                    if not run_tests(pkg_dir, config):
                        all_passed = False
                else:
                    all_passed = False
            else:
                # No ritz binaries (e.g., only scripts) - just run tests
                if not run_tests(pkg_dir, config):
                    all_passed = False

    if keep_artifacts:
        print(f"\n📁 Debug artifacts kept in build/")

    if all_passed:
        print(f"\n✓ All tests passed!")
    else:
        print(f"\n✗ Some tests failed")

    return 0 if all_passed else 1


def cmd_ritz_tests(args):
    """Run ritz0's own .ritz test suite."""
    ritz0_dir = ROOT / "ritz0"
    test_dir = ritz0_dir / "test"

    if not test_dir.exists():
        print("No ritz0/test directory found", file=sys.stderr)
        return 1

    ritz_tests = sorted(test_dir.glob("test_level*.ritz"))
    if not ritz_tests:
        print("No test_level*.ritz tests found in ritz0/test/", file=sys.stderr)
        return 1

    print(f"🧪 Running ritz0 test suite ({len(ritz_tests)} levels)...")
    result = subprocess.run(
        [sys.executable, str(RITZ0), "--test-all", "-v"],
        cwd=ritz0_dir
    )
    return result.returncode


# ritz1 test configuration: (test_file, lib_files)
RITZ1_TESTS = [
    ("test_nfa.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz"]),
    ("test_thompson.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz"]),
    ("test_utf8.ritz", ["mem.ritz", "utf8.ritz"]),
    ("test_regex.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz", "regex.ritz"]),
    ("test_multi_lexer.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz", "regex.ritz", "tokens.ritz", "lexer.ritz"]),
    ("test_token_dsl.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz", "regex.ritz", "tokens.ritz", "lexer.ritz", "token_dsl.ritz"]),
    ("test_ritz_lexer.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz", "regex.ritz", "tokens.ritz", "lexer.ritz", "token_dsl.ritz", "ritz_tokens.ritz"]),
    ("test_grammar_parser_basic.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz", "regex.ritz", "tokens.ritz", "lexer.ritz", "grammar_parser.ritz"]),
    ("test_grammar_builder.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz", "regex.ritz", "tokens.ritz", "lexer.ritz", "grammar_parser.ritz", "grammar_builder.ritz"]),
    ("test_break.ritz", []),
    ("test_parser_ast.ritz", []),  # Self-contained AST structure tests
    ("test_parser_minimal.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz", "regex.ritz", "tokens.ritz", "lexer.ritz", "token_dsl.ritz", "ritz_tokens.ritz", "parser.ritz"]),
    ("test_types.ritz", []),  # Self-contained type system tests
    ("test_symbols.ritz", []),  # Self-contained symbol table tests
    ("test_pipeline.ritz", ["mem.ritz", "nfa.ritz", "utf8.ritz", "regex.ritz", "tokens.ritz", "lexer.ritz", "token_dsl.ritz", "ritz_tokens.ritz"]),  # E2E pipeline tests
]


def cmd_ritz1_tests(args):
    """Run ritz1's .ritz test suite (self-hosting lexer tests)."""
    ritz1_dir = ROOT / "ritz1"
    test_dir = ritz1_dir / "test"
    src_dir = ritz1_dir / "src"

    if not test_dir.exists():
        print("No ritz1/test directory found", file=sys.stderr)
        return 1

    print(f"🧪 Running ritz1 test suite ({len(RITZ1_TESTS)} test files)...")

    total_passed = 0
    total_failed = 0
    failures = []

    for test_file, lib_files in RITZ1_TESTS:
        test_path = test_dir / test_file
        if not test_path.exists():
            print(f"  ⚠ {test_file} not found, skipping")
            continue

        # Build command
        cmd = [sys.executable, str(RITZ0), "--test", str(test_path)]
        if lib_files:
            cmd.append("--lib")
            cmd.extend(str(src_dir / f) for f in lib_files)

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse output for pass/fail counts
        output = result.stdout + result.stderr
        lines = output.strip().split('\n')

        # Find summary line (e.g., "7 passed, 0 failed")
        for line in lines:
            if "passed" in line and "failed" in line:
                parts = line.split()
                try:
                    passed = int(parts[0])
                    failed = int(parts[2])
                    total_passed += passed
                    total_failed += failed
                    if failed > 0:
                        failures.append((test_file, output))
                except (ValueError, IndexError):
                    pass
                break

        if result.returncode == 0:
            print(f"  ✓ {test_file}")
        else:
            print(f"  ✗ {test_file}")

    print(f"\n{total_passed} passed, {total_failed} failed")

    if failures:
        print("\nFailures:")
        for test_file, output in failures:
            print(f"\n--- {test_file} ---")
            print(output)

    return 0 if total_failed == 0 else 1


def cmd_run(args):
    """Compile and run a single .ritz file."""
    src_path = Path(args.file)
    if not src_path.exists():
        print(f"File not found: {src_path}", file=sys.stderr)
        return 1

    keep_artifacts = getattr(args, 'debug', False)
    name = src_path.stem

    # Use build/ directory for output
    out_dir = ROOT / "build"
    out_dir.mkdir(exist_ok=True)

    print(f"🔨 Compiling {src_path}...")
    bin_path = compile_binary(name, src_path, out_dir, keep_artifacts=keep_artifacts)
    if not bin_path:
        return 1

    print(f"🚀 Running {bin_path.name}...", flush=True)
    print(flush=True)  # Blank line before output

    # Run the binary with any additional arguments
    result = subprocess.run([str(bin_path)] + args.args)
    return result.returncode


def cmd_clean(args):
    """Remove build artifacts."""
    packages = find_packages()

    for pkg_dir, config in packages:
        binaries = get_binaries(pkg_dir, config)
        for bin_name, _, _ in binaries:
            bin_path = pkg_dir / bin_name
            if bin_path.exists():
                bin_path.unlink()
                print(f"  🗑 {bin_path.relative_to(ROOT)}")

    # Clean pycache
    for pycache in ROOT.rglob("__pycache__"):
        import shutil
        shutil.rmtree(pycache)

    # Clean build cache
    cache = get_build_cache()
    if cache.cache_dir.exists():
        import shutil
        shutil.rmtree(cache.cache_dir)
        print(f"  🗑 {cache.cache_dir.relative_to(ROOT)}")

    print("✓ Cleaned")


def cmd_cache_status(args):
    """Show cache status."""
    cache = get_build_cache()

    if not cache.cache_dir.exists():
        print("No cache exists")
        return 0

    print(f"Cache directory: {cache.cache_dir}")
    print(f"Dependency entries: {len(cache.state.deps)}")

    if args.verbose:
        print("\nCached files:")
        for path, info in sorted(cache.state.deps.items()):
            try:
                rel_path = Path(path).relative_to(ROOT)
            except ValueError:
                rel_path = path
            print(f"  {rel_path}")
            print(f"    hash: {info.hash[:16]}...")
            print(f"    imports: {len(info.imports)}")

    # Show objects directory size
    objects_dir = cache.objects_dir
    if objects_dir.exists():
        ll_files = list(objects_dir.glob('*.ll'))
        bc_files = list(objects_dir.glob('*.bc'))
        total_size = sum(f.stat().st_size for f in objects_dir.rglob("*") if f.is_file())
        print(f"\nCached objects: {len(ll_files)} .ll, {len(bc_files)} .bc files, {total_size / 1024:.1f} KB")

    return 0


def cmd_cache_clear(args):
    """Clear the build cache."""
    cache = get_build_cache()
    cache.clear()
    print("Cache cleared")
    return 0


# =============================================================================
# RFC #107: Global Install Commands
# =============================================================================

def cmd_install(args):
    """Install a package globally (RFC #107)."""
    from packaging import GlobalCache, install_package
    cache = GlobalCache()
    success = install_package(
        args.uri,
        cache,
        Path(__file__),  # build.py path
        release=getattr(args, "release", False),
        force=getattr(args, "force", False)
    )
    return 0 if success else 1


def cmd_uninstall(args):
    """Uninstall a global package (RFC #107)."""
    from packaging import cmd_uninstall as pkg_uninstall
    return pkg_uninstall(args)


def cmd_global_list(args):
    """List globally installed packages (RFC #107)."""
    from packaging import cmd_list_installed
    return cmd_list_installed(args)


def cmd_global_cache(args):
    """Show global cache information (RFC #107)."""
    from packaging import cmd_cache_info
    return cmd_cache_info(args)


def cmd_lock(args):
    """Generate ritz.lock for reproducible builds (RFC #107)."""
    from packaging import generate_lock_file

    # Determine package directory
    if args.name:
        pkg_dir = Path(args.name)
    else:
        pkg_dir = Path.cwd()

    if not (pkg_dir / "ritz.toml").exists():
        print(f"Error: No ritz.toml found in {pkg_dir}", file=sys.stderr)
        return 1

    try:
        lock_path = generate_lock_file(pkg_dir)
        print(f"✓ Generated {lock_path}")
        return 0
    except Exception as e:
        print(f"Error generating lock file: {e}", file=sys.stderr)
        return 1


def cmd_vendor(args):
    """Vendor dependencies for offline builds (RFC #107)."""
    from packaging import vendor_dependencies

    # Determine package directory
    if args.name:
        pkg_dir = Path(args.name)
    else:
        pkg_dir = Path.cwd()

    if not (pkg_dir / "ritz.toml").exists():
        print(f"Error: No ritz.toml found in {pkg_dir}", file=sys.stderr)
        return 1

    try:
        vendor_dir = vendor_dependencies(pkg_dir)
        # Count vendored packages
        if vendor_dir.exists():
            count = len([d for d in vendor_dir.iterdir() if d.is_dir()])
            print(f"✓ Vendored {count} package(s) to {vendor_dir}")
        return 0
    except Exception as e:
        print(f"Error vendoring dependencies: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(description="🎭 Ritz Build System")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all packages")

    # build
    build_parser = subparsers.add_parser("build", help="Build packages")
    build_parser.add_argument("name", nargs="?", help="Package path or directory (default: current directory)")
    build_parser.add_argument("--all", action="store_true", help="Build all packages under current directory")
    build_parser.add_argument("--release", action="store_true",
                              help="Build with release profile (optimizations enabled)")
    build_parser.add_argument("-g", "--debug", action="store_true",
                              help="Keep intermediate files (.ll, .o) in build/ for debugging")
    build_parser.add_argument("--no-cache", action="store_true",
                              help="Disable build cache (always rebuild)")

    # test
    test_parser = subparsers.add_parser("test", help="Build and test packages")
    test_parser.add_argument("name", nargs="?", help="Package path or directory (default: current directory)")
    test_parser.add_argument("--all", action="store_true", help="Test all packages under current directory")
    test_parser.add_argument("--release", action="store_true",
                             help="Build with release profile before testing")
    test_parser.add_argument("-g", "--debug", action="store_true",
                             help="Keep intermediate files (.ll, .o) in build/ for debugging")
    test_parser.add_argument("--no-cache", action="store_true",
                             help="Disable build cache (always rebuild)")

    # run
    run_parser = subparsers.add_parser("run", help="Compile and run a single .ritz file")
    run_parser.add_argument("file", help="Ritz source file to run")
    run_parser.add_argument("args", nargs="*", help="Arguments to pass to the program")
    run_parser.add_argument("-g", "--debug", action="store_true",
                            help="Keep intermediate files in build/ for debugging")

    # clean
    subparsers.add_parser("clean", help="Remove build artifacts and cache")

    # ritz-tests
    subparsers.add_parser("ritz-tests", help="Run ritz0's .ritz test suite")

    # ritz1-tests
    subparsers.add_parser("ritz1-tests", help="Run ritz1's .ritz test suite (self-hosting lexer)")

    # cache-status
    cache_status_parser = subparsers.add_parser("cache-status", help="Show build cache status")
    cache_status_parser.add_argument("-v", "--verbose", action="store_true",
                                      help="Show detailed cache information")

    # cache-clear
    subparsers.add_parser("cache-clear", help="Clear the build cache")

    # install (RFC #107)
    install_parser = subparsers.add_parser("install", help="Install a package globally")
    install_parser.add_argument("uri", help="Package URI (git URL or local path)")
    install_parser.add_argument("--release", action="store_true",
                                help="Build with release profile")
    install_parser.add_argument("--force", action="store_true",
                                help="Force reinstall")

    # uninstall (RFC #107)
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall a global package")
    uninstall_parser.add_argument("name", help="Package name")

    # global-list (RFC #107)
    subparsers.add_parser("global-list", help="List globally installed packages")

    # global-cache (RFC #107)
    subparsers.add_parser("global-cache", help="Show global cache information")

    # lock (RFC #107)
    lock_parser = subparsers.add_parser("lock", help="Generate ritz.lock for reproducible builds")
    lock_parser.add_argument("name", nargs="?", help="Package directory (default: current directory)")

    # vendor (RFC #107)
    vendor_parser = subparsers.add_parser("vendor", help="Copy dependencies to vendor/ for offline builds")
    vendor_parser.add_argument("name", nargs="?", help="Package directory (default: current directory)")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "build": cmd_build,
        "test": cmd_test,
        "run": cmd_run,
        "clean": cmd_clean,
        "ritz-tests": cmd_ritz_tests,
        "ritz1-tests": cmd_ritz1_tests,
        "cache-status": cmd_cache_status,
        "cache-clear": cmd_cache_clear,
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "global-list": cmd_global_list,
        "global-cache": cmd_global_cache,
        "lock": cmd_lock,
        "vendor": cmd_vendor,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
