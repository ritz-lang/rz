#!/usr/bin/env python3
"""
🎁 Ritz Packaging System

Implements RFC #107: Package Distribution Strategy

Features:
- Content-addressed global cache (~/.ritz/cache/)
- `ritz install <uri>` command
- Symlink management for installed binaries

Directory structure:
    ~/.ritz/
    ├── config.toml              # User configuration
    ├── bin/                     # Symlinks to installed tools
    │   └── mytool → ../cache/{hash}/x86_64-linux/bin/mytool
    ├── cache/                   # Build cache (content-addressed)
    │   └── {hash}/
    │       ├── metadata.json
    │       └── {target}/
    │           └── bin/mytool
    └── packages/                # Installed package sources
        └── mytool/
            ├── ritz.toml
            └── src/
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib


# =============================================================================
# Constants and Configuration
# =============================================================================

def get_ritz_home() -> Path:
    """Get the Ritz home directory (~/.ritz/)."""
    ritz_home = os.environ.get("RITZ_HOME")
    if ritz_home:
        return Path(ritz_home)
    return Path.home() / ".ritz"


def get_target_triple() -> str:
    """Get the current platform's target triple."""
    machine = platform.machine()
    system = platform.system().lower()

    # Map platform names
    if system == "darwin":
        system = "darwin"
    elif system == "windows":
        system = "windows"
    else:
        system = "linux"

    # Map architecture names
    arch_map = {
        "x86_64": "x86_64",
        "AMD64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    arch = arch_map.get(machine, machine)

    return f"{arch}-{system}"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class PackageMetadata:
    """Metadata for an installed package."""
    name: str
    version: str
    source_uri: str
    source_hash: str
    installed_at: str
    target: str
    compiler_version: str
    binaries: list[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PackageMetadata":
        return cls(**data)


@dataclass
class LockEntry:
    """A single entry in ritz.lock, pinning a dependency to exact version."""
    name: str
    source: str  # git+https://...?rev=abc123 or path:../local
    checksum: str  # sha256:...
    version: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LockEntry":
        return cls(**data)


class LockFile:
    """Manages ritz.lock file for reproducible builds."""

    def __init__(self, entries: list[LockEntry] = None):
        self.entries = entries or []

    def write(self, path: Path):
        """Write lock file in TOML format."""
        lines = ["# ritz.lock - Auto-generated, commit to version control\n"]

        for entry in self.entries:
            lines.append("[[package]]")
            lines.append(f'name = "{entry.name}"')
            lines.append(f'version = "{entry.version}"')
            lines.append(f'source = "{entry.source}"')
            lines.append(f'checksum = "{entry.checksum}"')
            lines.append("")

        path.write_text("\n".join(lines))

    @classmethod
    def read(cls, path: Path) -> "LockFile":
        """Read lock file from disk."""
        with open(path, "rb") as f:
            data = tomllib.load(f)

        entries = []
        for pkg in data.get("package", []):
            entries.append(LockEntry(
                name=pkg["name"],
                source=pkg["source"],
                checksum=pkg["checksum"],
                version=pkg.get("version", "0.0.0")
            ))

        return cls(entries)


# =============================================================================
# Lock File Generation
# =============================================================================

def generate_lock_entries(pkg_dir: Path) -> list[LockEntry]:
    """Generate lock entries from resolved dependencies.

    Reads ritz.toml, resolves all dependencies (including transitive),
    and creates LockEntry for each with pinned source and checksum.

    Args:
        pkg_dir: Package directory containing ritz.toml

    Returns:
        List of LockEntry objects for all dependencies
    """
    # Import here to avoid circular dependency
    import build

    toml_path = pkg_dir / "ritz.toml"
    if not toml_path.exists():
        return []

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    # Get all dependencies (including transitive)
    all_deps = build.get_transitive_dependencies(pkg_dir, config)

    entries = []
    for dep_name, dep_spec in sorted(all_deps.items()):
        # Compute source identifier
        dep_path = dep_spec.path

        # Read dependency's version from its ritz.toml
        dep_toml = dep_path / "ritz.toml"
        version = "0.0.0"
        if dep_toml.exists():
            with open(dep_toml, "rb") as f:
                dep_config = tomllib.load(f)
            version = dep_config.get("package", {}).get("version", "0.0.0")

        # Generate source string
        # For local paths, use relative path from pkg_dir
        try:
            rel_path = os.path.relpath(dep_path, pkg_dir)
            source = f"path:{rel_path}"
        except ValueError:
            # On Windows, relpath can fail across drives
            source = f"path:{dep_path}"

        # Compute checksum of dependency sources
        checksum = f"sha256:{compute_source_hash(dep_path)}"

        entries.append(LockEntry(
            name=dep_name,
            source=source,
            checksum=checksum,
            version=version
        ))

    return entries


def generate_lock_file(pkg_dir: Path) -> Path:
    """Generate ritz.lock for a package.

    Args:
        pkg_dir: Package directory

    Returns:
        Path to generated ritz.lock
    """
    entries = generate_lock_entries(pkg_dir)
    lock = LockFile(entries)
    lock_path = pkg_dir / "ritz.lock"
    lock.write(lock_path)
    return lock_path


# =============================================================================
# Vendoring
# =============================================================================

def vendor_dependencies(pkg_dir: Path, vendor_dir: Path = None) -> Path:
    """Copy all dependencies to vendor/ directory.

    Copies source files (.ritz) and ritz.toml for all dependencies
    (including transitive) to a local vendor/ directory.

    Excludes:
    - build/ directories
    - .ritz-cache/ directories
    - vendor/ directories (from deps)
    - .git/ directories

    Args:
        pkg_dir: Package directory
        vendor_dir: Target vendor directory (default: pkg_dir/vendor)

    Returns:
        Path to vendor directory
    """
    # Import here to avoid circular dependency
    import build

    if vendor_dir is None:
        vendor_dir = pkg_dir / "vendor"

    # Read package config
    toml_path = pkg_dir / "ritz.toml"
    if not toml_path.exists():
        raise FileNotFoundError(f"No ritz.toml in {pkg_dir}")

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    # Get all dependencies
    all_deps = build.get_transitive_dependencies(pkg_dir, config)

    if not all_deps:
        print("No dependencies to vendor")
        return vendor_dir

    # Create vendor directory
    vendor_dir.mkdir(parents=True, exist_ok=True)

    # Directories to exclude when copying
    EXCLUDE_DIRS = {"build", ".ritz-cache", "vendor", ".git", "__pycache__"}

    for dep_name, dep_spec in all_deps.items():
        dep_src = dep_spec.path
        dep_dst = vendor_dir / dep_name

        # Remove existing vendor copy if present
        if dep_dst.exists():
            shutil.rmtree(dep_dst)

        # Copy dependency, filtering out excluded directories
        dep_dst.mkdir(parents=True, exist_ok=True)

        for src_item in dep_src.rglob("*"):
            # Check if any parent is in exclude list
            rel_path = src_item.relative_to(dep_src)
            skip = False
            for part in rel_path.parts:
                if part in EXCLUDE_DIRS:
                    skip = True
                    break

            if skip:
                continue

            dst_item = dep_dst / rel_path

            if src_item.is_dir():
                dst_item.mkdir(parents=True, exist_ok=True)
            elif src_item.is_file():
                # Only copy source-related files
                if src_item.suffix in (".ritz", ".toml", ".md", ".txt", ".json"):
                    dst_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_item, dst_item)
                elif src_item.name in ("LICENSE", "README", "CHANGELOG"):
                    dst_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_item, dst_item)

    return vendor_dir


@dataclass
class CacheEntry:
    """A cached build entry."""
    content_hash: str
    metadata: PackageMetadata
    binary_paths: dict[str, Path]  # binary_name -> path


# =============================================================================
# Content Hashing
# =============================================================================

def compute_source_hash(pkg_dir: Path) -> str:
    """Compute a content hash of all source files in a package.

    Hash includes:
    - All .ritz files
    - ritz.toml
    - ritz.lock (if exists)

    Returns a hex digest suitable for cache keys.
    """
    h = hashlib.sha256()

    # Sort files for deterministic ordering
    files_to_hash = []

    # Add ritz.toml
    toml_path = pkg_dir / "ritz.toml"
    if toml_path.exists():
        files_to_hash.append(toml_path)

    # Add ritz.lock if exists
    lock_path = pkg_dir / "ritz.lock"
    if lock_path.exists():
        files_to_hash.append(lock_path)

    # Add all .ritz files
    for ritz_file in sorted(pkg_dir.rglob("*.ritz")):
        # Skip vendor/ and build/ directories
        rel_path = ritz_file.relative_to(pkg_dir)
        parts = rel_path.parts
        if "vendor" in parts or "build" in parts or ".ritz-cache" in parts:
            continue
        files_to_hash.append(ritz_file)

    # Hash each file
    for file_path in sorted(files_to_hash):
        # Include relative path in hash for file identity
        rel_path = file_path.relative_to(pkg_dir)
        h.update(str(rel_path).encode())
        h.update(file_path.read_bytes())

    return h.hexdigest()[:16]  # First 16 chars is enough


def compute_cache_key(source_hash: str, target: str, opt_level: int = 0) -> str:
    """Compute the full cache key including build parameters.

    Cache key = hash(source_hash + target + opt_level + compiler_version)
    """
    h = hashlib.sha256()
    h.update(source_hash.encode())
    h.update(target.encode())
    h.update(str(opt_level).encode())

    # Include compiler version (simplified - could include actual ritz0 version)
    h.update(b"ritz0-v1")

    return h.hexdigest()[:16]


# =============================================================================
# Global Cache Management
# =============================================================================

class GlobalCache:
    """Manages the global package cache (~/.ritz/cache/)."""

    def __init__(self, ritz_home: Path = None):
        self.ritz_home = ritz_home or get_ritz_home()
        self.cache_dir = self.ritz_home / "cache"
        self.packages_dir = self.ritz_home / "packages"
        self.bin_dir = self.ritz_home / "bin"

    def ensure_dirs(self):
        """Create the directory structure if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        self.bin_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, cache_key: str, target: str) -> Path:
        """Get the path to a cached build."""
        return self.cache_dir / cache_key / target

    def has_cached_build(self, cache_key: str, target: str) -> bool:
        """Check if a cached build exists."""
        cache_path = self.get_cache_path(cache_key, target)
        metadata_path = cache_path.parent / "metadata.json"
        return cache_path.exists() and metadata_path.exists()

    def get_cached_metadata(self, cache_key: str) -> Optional[PackageMetadata]:
        """Get metadata for a cached build."""
        metadata_path = self.cache_dir / cache_key / "metadata.json"
        if not metadata_path.exists():
            return None
        with open(metadata_path) as f:
            return PackageMetadata.from_dict(json.load(f))

    def store_build(
        self,
        cache_key: str,
        target: str,
        metadata: PackageMetadata,
        binaries: dict[str, Path]
    ) -> Path:
        """Store a build in the cache.

        Args:
            cache_key: The cache key
            target: Target triple (e.g., x86_64-linux)
            metadata: Package metadata
            binaries: Dict of binary_name -> source_path

        Returns:
            Path to the cache entry
        """
        cache_path = self.get_cache_path(cache_key, target)
        bin_path = cache_path / "bin"
        bin_path.mkdir(parents=True, exist_ok=True)

        # Copy binaries
        for name, src_path in binaries.items():
            dst_path = bin_path / name
            shutil.copy2(src_path, dst_path)
            # Make executable
            dst_path.chmod(0o755)

        # Update metadata with binary names
        metadata.binaries = list(binaries.keys())

        # Write metadata
        metadata_path = self.cache_dir / cache_key / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        return cache_path

    def create_symlinks(self, cache_key: str, target: str) -> list[Path]:
        """Create symlinks in ~/.ritz/bin/ for cached binaries.

        Returns list of created symlinks.
        """
        cache_path = self.get_cache_path(cache_key, target)
        bin_path = cache_path / "bin"
        created = []

        if not bin_path.exists():
            return created

        for binary in bin_path.iterdir():
            if binary.is_file():
                symlink = self.bin_dir / binary.name
                # Remove existing symlink
                if symlink.is_symlink():
                    symlink.unlink()
                elif symlink.exists():
                    print(f"  ⚠ {symlink.name} exists and is not a symlink, skipping")
                    continue
                # Create relative symlink
                rel_path = os.path.relpath(binary, self.bin_dir)
                symlink.symlink_to(rel_path)
                created.append(symlink)

        return created

    def list_installed(self) -> list[tuple[str, PackageMetadata]]:
        """List all installed packages."""
        installed = []
        if not self.cache_dir.exists():
            return installed

        for entry in self.cache_dir.iterdir():
            if entry.is_dir():
                metadata = self.get_cached_metadata(entry.name)
                if metadata:
                    installed.append((entry.name, metadata))

        return installed

    def clear(self):
        """Clear the entire cache."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        # Also remove symlinks
        if self.bin_dir.exists():
            for item in self.bin_dir.iterdir():
                if item.is_symlink():
                    item.unlink()


# =============================================================================
# Package Installation
# =============================================================================

def parse_uri(uri: str) -> dict:
    """Parse a package URI into components.

    Supports:
    - https://github.com/user/repo
    - https://github.com/user/repo#tag=v1.0
    - https://github.com/user/repo#branch=main
    - https://github.com/user/repo#rev=abc123
    - git@github.com:user/repo.git
    - /path/to/local/package
    - relative/path/to/package
    """
    result = {
        "uri": uri,
        "type": "git",
        "ref": None,
        "ref_type": None,
    }

    # Check for local path - either absolute, relative, or exists on disk
    if uri.startswith("/") or uri.startswith("./") or uri.startswith("../"):
        result["type"] = "path"
        result["path"] = uri
        return result

    # Check if it's a local path that exists
    if Path(uri).exists() and (Path(uri) / "ritz.toml").exists():
        result["type"] = "path"
        result["path"] = uri
        return result

    # Check for fragment (e.g., #tag=v1.0)
    if "#" in uri:
        uri_part, fragment = uri.split("#", 1)
        result["uri"] = uri_part
        if "=" in fragment:
            ref_type, ref = fragment.split("=", 1)
            result["ref_type"] = ref_type  # tag, branch, rev
            result["ref"] = ref
    else:
        result["uri"] = uri

    return result


def clone_package(uri_info: dict, dest_dir: Path) -> bool:
    """Clone a package from a git URI.

    Returns True on success.
    """
    uri = uri_info["uri"]

    # Build git clone command
    cmd = ["git", "clone", "--depth", "1"]

    if uri_info.get("ref_type") == "branch":
        cmd.extend(["--branch", uri_info["ref"]])
    elif uri_info.get("ref_type") == "tag":
        cmd.extend(["--branch", uri_info["ref"]])

    cmd.extend([uri, str(dest_dir)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ git clone failed: {result.stderr}", file=sys.stderr)
        return False

    # If rev specified, checkout that specific commit
    if uri_info.get("ref_type") == "rev":
        result = subprocess.run(
            ["git", "checkout", uri_info["ref"]],
            cwd=dest_dir,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"  ✗ git checkout failed: {result.stderr}", file=sys.stderr)
            return False

    return True


def install_package(
    uri: str,
    cache: GlobalCache,
    build_script: Path,
    release: bool = False,
    force: bool = False
) -> bool:
    """Install a package from a URI.

    Args:
        uri: Package URI (git URL or local path)
        cache: Global cache instance
        build_script: Path to build.py
        release: Build with release profile
        force: Force reinstall even if cached

    Returns:
        True on success
    """
    cache.ensure_dirs()
    target = get_target_triple()
    uri_info = parse_uri(uri)

    print(f"📦 Installing from {uri}...")

    # Handle local path
    repo_name = None
    if uri_info["type"] == "path":
        pkg_dir = Path(uri_info["path"]).resolve()
        if not pkg_dir.exists():
            print(f"  ✗ Path not found: {pkg_dir}", file=sys.stderr)
            return False
        repo_name = pkg_dir.name
    else:
        # Clone to packages directory
        # Use repo name as package dir name
        repo_name = uri_info["uri"].rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        pkg_dir = cache.packages_dir / repo_name

        # Check if already cloned
        if pkg_dir.exists():
            if force:
                shutil.rmtree(pkg_dir)
            else:
                print(f"  Using existing source at {pkg_dir}")

        if not pkg_dir.exists():
            print(f"  Cloning repository...")
            if not clone_package(uri_info, pkg_dir):
                return False

    # Read package config
    toml_path = pkg_dir / "ritz.toml"
    if not toml_path.exists():
        print(f"  ✗ No ritz.toml found in {pkg_dir}", file=sys.stderr)
        return False

    with open(toml_path, "rb") as f:
        config = tomllib.load(f)

    pkg_name = config.get("package", {}).get("name", repo_name or "unknown")
    pkg_version = config.get("package", {}).get("version", "0.0.0")

    # Compute content hash
    source_hash = compute_source_hash(pkg_dir)
    opt_level = 3 if release else 0
    cache_key = compute_cache_key(source_hash, target, opt_level)

    print(f"  Package: {pkg_name} v{pkg_version}")
    print(f"  Source hash: {source_hash}")

    # Check cache
    if cache.has_cached_build(cache_key, target) and not force:
        print(f"  ✓ Using cached build ({cache_key})")
        cache.create_symlinks(cache_key, target)
        return True

    # Build the package
    print(f"  Compiling for {target}...")
    profile = "--release" if release else ""
    cmd = [sys.executable, str(build_script), "build", str(pkg_dir)]
    if profile:
        cmd.append(profile)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ Build failed:", file=sys.stderr)
        print(result.stdout)
        print(result.stderr)
        return False

    # Find built binaries
    profile_name = "release" if release else "debug"
    build_dir = pkg_dir / "build" / profile_name
    binaries = {}

    if build_dir.exists():
        for item in build_dir.iterdir():
            if item.is_file() and os.access(item, os.X_OK):
                binaries[item.name] = item

    if not binaries:
        print(f"  ✗ No binaries found in {build_dir}", file=sys.stderr)
        return False

    # Store in cache
    metadata = PackageMetadata(
        name=pkg_name,
        version=pkg_version,
        source_uri=uri,
        source_hash=source_hash,
        installed_at=datetime.now().isoformat(),
        target=target,
        compiler_version="ritz0-v1",
        binaries=list(binaries.keys())
    )

    cache.store_build(cache_key, target, metadata, binaries)
    symlinks = cache.create_symlinks(cache_key, target)

    print(f"  ✓ Installed {len(binaries)} binary(ies)")
    for symlink in symlinks:
        print(f"    → {symlink}")

    return True


# =============================================================================
# CLI Commands
# =============================================================================

def cmd_install(args, build_script: Path) -> int:
    """Install a package from URI."""
    cache = GlobalCache()
    success = install_package(
        args.uri,
        cache,
        build_script,
        release=getattr(args, "release", False),
        force=getattr(args, "force", False)
    )
    return 0 if success else 1


def cmd_list_installed(args) -> int:
    """List installed packages."""
    cache = GlobalCache()
    installed = cache.list_installed()

    if not installed:
        print("No packages installed")
        return 0

    print(f"Installed packages ({len(installed)}):\n")
    for cache_key, metadata in installed:
        print(f"  {metadata.name} v{metadata.version}")
        print(f"    Source: {metadata.source_uri}")
        print(f"    Target: {metadata.target}")
        print(f"    Hash: {cache_key}")
        print(f"    Binaries: {', '.join(metadata.binaries)}")
        print()

    return 0


def cmd_cache_info(args) -> int:
    """Show global cache info."""
    cache = GlobalCache()

    print(f"Ritz home: {cache.ritz_home}")
    print(f"Cache dir: {cache.cache_dir}")
    print(f"Packages dir: {cache.packages_dir}")
    print(f"Bin dir: {cache.bin_dir}")

    # Count cached entries
    if cache.cache_dir.exists():
        entries = list(cache.cache_dir.iterdir())
        total_size = sum(
            f.stat().st_size
            for f in cache.cache_dir.rglob("*")
            if f.is_file()
        )
        print(f"\nCached builds: {len(entries)}")
        print(f"Total size: {total_size / 1024 / 1024:.1f} MB")

    # Count symlinks
    if cache.bin_dir.exists():
        symlinks = [f for f in cache.bin_dir.iterdir() if f.is_symlink()]
        print(f"Installed binaries: {len(symlinks)}")

    return 0


def cmd_cache_clear(args) -> int:
    """Clear the global cache."""
    cache = GlobalCache()
    cache.clear()
    print("✓ Global cache cleared")
    return 0


def cmd_uninstall(args) -> int:
    """Uninstall a package."""
    cache = GlobalCache()
    name = args.name

    # Find the package
    found = False
    for cache_key, metadata in cache.list_installed():
        if metadata.name == name:
            found = True
            # Remove symlinks
            for bin_name in metadata.binaries:
                symlink = cache.bin_dir / bin_name
                if symlink.is_symlink():
                    symlink.unlink()
                    print(f"  Removed {symlink}")
            # Remove cache entry
            cache_path = cache.cache_dir / cache_key
            if cache_path.exists():
                shutil.rmtree(cache_path)
            # Remove source
            source_path = cache.packages_dir / name
            if source_path.exists():
                shutil.rmtree(source_path)
            print(f"✓ Uninstalled {name}")
            break

    if not found:
        print(f"Package '{name}' not found")
        return 1

    return 0


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """CLI entry point for packaging commands."""
    import argparse

    parser = argparse.ArgumentParser(description="🎁 Ritz Package Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # install
    install_parser = subparsers.add_parser("install", help="Install a package")
    install_parser.add_argument("uri", help="Package URI (git URL or local path)")
    install_parser.add_argument("--release", action="store_true",
                                help="Build with release profile")
    install_parser.add_argument("--force", action="store_true",
                                help="Force reinstall")

    # list
    subparsers.add_parser("list", help="List installed packages")

    # uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall a package")
    uninstall_parser.add_argument("name", help="Package name")

    # cache
    subparsers.add_parser("cache-info", help="Show cache information")
    subparsers.add_parser("cache-clear", help="Clear the global cache")

    args = parser.parse_args()

    # Find build.py relative to this script
    build_script = Path(__file__).parent / "build.py"

    commands = {
        "install": lambda: cmd_install(args, build_script),
        "list": lambda: cmd_list_installed(args),
        "uninstall": lambda: cmd_uninstall(args),
        "cache-info": lambda: cmd_cache_info(args),
        "cache-clear": lambda: cmd_cache_clear(args),
    }

    return commands[args.command]()


if __name__ == "__main__":
    sys.exit(main() or 0)
