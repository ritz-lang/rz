#!/usr/bin/env python3
"""
Build Cache for Ritz

Implements incremental build support through:
1. Dependency tracking - parsing imports to build a DAG
2. Hash computation - SHA256 of source file contents
3. Cache management - storing compiled artifacts and metadata

Cache directory structure:
    .ritz-cache/
    ├── deps.json         # Dependency graph
    ├── hashes.json       # Source file hashes
    └── objects/
        ├── main.ritz.ll  # Generated IR
        └── main.ritz.o   # Compiled object
"""

import json
import hashlib
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass, field, asdict


# ============================================================================
# Cache directory constants
# ============================================================================

CACHE_DIR_NAME = ".ritz-cache"
DEPS_FILE = "deps.json"
HASHES_FILE = "hashes.json"
OBJECTS_DIR = "objects"


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class FileInfo:
    """Information about a source file for caching purposes."""
    hash: str                    # SHA256 of file content
    imports: List[str]           # List of import paths (e.g., ["ritzlib/sys.ritz"])
    mtime: float                 # Last modification time

    def to_dict(self) -> dict:
        return {
            "hash": self.hash,
            "imports": self.imports,
            "mtime": self.mtime
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FileInfo":
        return cls(
            hash=data["hash"],
            imports=data["imports"],
            mtime=data["mtime"]
        )


@dataclass
class CacheState:
    """The complete cache state."""
    deps: Dict[str, FileInfo] = field(default_factory=dict)  # path -> FileInfo

    def save(self, cache_dir: Path):
        """Save cache state to disk."""
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Save deps.json
        deps_data = {path: info.to_dict() for path, info in self.deps.items()}
        deps_file = cache_dir / DEPS_FILE
        with open(deps_file, 'w') as f:
            json.dump(deps_data, f, indent=2)

    @classmethod
    def load(cls, cache_dir: Path) -> "CacheState":
        """Load cache state from disk."""
        state = cls()

        deps_file = cache_dir / DEPS_FILE
        if deps_file.exists():
            with open(deps_file, 'r') as f:
                deps_data = json.load(f)
            state.deps = {
                path: FileInfo.from_dict(info)
                for path, info in deps_data.items()
            }

        return state


# ============================================================================
# Dependency Scanner
# ============================================================================

# Regex to match import statements: import foo, import foo.bar
IMPORT_PATTERN = re.compile(r'^import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*$', re.MULTILINE)


def scan_imports(source: str) -> List[str]:
    """Extract import paths from source code.

    Returns a list of import paths like ["ritzlib.sys", "mem"].
    """
    imports = []
    for match in IMPORT_PATTERN.finditer(source):
        imports.append(match.group(1))
    return imports


def resolve_import_path(import_path: str, source_file: Path, project_root: Optional[Path] = None) -> Optional[Path]:
    """Resolve an import path to an actual file path.

    Resolution order:
    1. Relative to importing file: foo.ritz, foo/bar.ritz
    2. From project root: ritzlib/sys.ritz
    3. From RITZ_PATH directories
    """
    parts = import_path.split('.')
    base_dir = source_file.parent

    # Try 1: Relative to importing file - foo/bar.ritz
    relative_path = Path(*parts[:-1]) / f"{parts[-1]}.ritz" if len(parts) > 1 else Path(f"{parts[0]}.ritz")
    candidate = base_dir / relative_path
    if candidate.exists():
        return candidate.resolve()

    # Try 1b: Relative to importing file - foo.bar.ritz (flat name)
    flat_name = '.'.join(parts) + '.ritz'
    candidate = base_dir / flat_name
    if candidate.exists():
        return candidate.resolve()

    # Try 2: From project root
    if project_root:
        candidate = project_root / relative_path
        if candidate.exists():
            return candidate.resolve()
        candidate = project_root / flat_name
        if candidate.exists():
            return candidate.resolve()

    # Try 3: From RITZ_PATH directories
    ritz_path = os.environ.get('RITZ_PATH', '')
    if ritz_path:
        for p in ritz_path.split(':'):
            if p and Path(p).exists():
                import_dir = Path(p).resolve()
                candidate = import_dir / relative_path
                if candidate.exists():
                    return candidate.resolve()
                candidate = import_dir / flat_name
                if candidate.exists():
                    return candidate.resolve()

    return None


def find_project_root(start_dir: Path) -> Optional[Path]:
    """Walk up from start_dir looking for project root indicators."""
    current = start_dir.resolve()
    while current != current.parent:
        if (current / '.git').exists():
            return current
        if (current / 'ritzlib').is_dir():
            return current
        current = current.parent
    return None


# ============================================================================
# Hash Computation
# ============================================================================

def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file's contents."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


# ============================================================================
# Build Cache
# ============================================================================

class BuildCache:
    """Manages the build cache for incremental compilation."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the build cache.

        Args:
            project_root: Root directory of the project. If not provided,
                         will be auto-detected when needed.
        """
        self.project_root = project_root
        self._state: Optional[CacheState] = None
        self._cache_dir: Optional[Path] = None

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory path."""
        if self._cache_dir is None:
            if self.project_root:
                self._cache_dir = self.project_root / CACHE_DIR_NAME
            else:
                self._cache_dir = Path.cwd() / CACHE_DIR_NAME
        return self._cache_dir

    @property
    def objects_dir(self) -> Path:
        """Get the objects subdirectory path."""
        return self.cache_dir / OBJECTS_DIR

    @property
    def state(self) -> CacheState:
        """Get the current cache state, loading from disk if needed."""
        if self._state is None:
            self._state = CacheState.load(self.cache_dir)
        return self._state

    def save(self):
        """Save the cache state to disk."""
        if self._state is not None:
            self._state.save(self.cache_dir)

    def clear(self):
        """Clear the entire cache."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self._state = CacheState()

    def _get_safe_cache_name(self, source_path: Path) -> str:
        """Get a safe filename for caching based on source path."""
        # Use the source file's relative path (from project root) as the cache key
        if self.project_root and source_path.is_absolute():
            try:
                rel_path = source_path.relative_to(self.project_root)
            except ValueError:
                rel_path = source_path
        else:
            rel_path = source_path

        # Create a safe filename by replacing path separators
        return str(rel_path).replace('/', '_').replace('\\', '_')

    def get_cached_ll_path(self, source_path: Path) -> Path:
        """Get the path where cached .ll file would be stored."""
        safe_name = self._get_safe_cache_name(source_path)
        return self.objects_dir / f"{safe_name}.ll"

    def get_cached_bc_path(self, source_path: Path) -> Path:
        """Get the path where cached .bc (LLVM bitcode) file would be stored.

        RFC #109 Phase 3: LLVM BC caching for faster rebuilds.
        Bitcode is faster to load than text IR and enables better LTO.
        """
        safe_name = self._get_safe_cache_name(source_path)
        return self.objects_dir / f"{safe_name}.bc"

    def scan_file(self, source_path: Path) -> FileInfo:
        """Scan a source file and return its FileInfo."""
        source_path = source_path.resolve()

        # Read file content
        content = source_path.read_text()

        # Compute hash
        file_hash = compute_file_hash(source_path)

        # Scan imports
        import_strs = scan_imports(content)

        # Resolve imports to actual file paths
        project_root = self.project_root or find_project_root(source_path.parent)
        resolved_imports = []
        for imp in import_strs:
            resolved = resolve_import_path(imp, source_path, project_root)
            if resolved:
                resolved_imports.append(str(resolved))

        # Get mtime
        mtime = source_path.stat().st_mtime

        return FileInfo(
            hash=file_hash,
            imports=resolved_imports,
            mtime=mtime
        )

    def get_transitive_dependencies(self, source_path: Path, visited: Optional[Set[str]] = None) -> Set[str]:
        """Get all transitive dependencies of a source file.

        Returns a set of absolute file paths that the source file depends on.
        """
        if visited is None:
            visited = set()

        source_str = str(source_path.resolve())
        if source_str in visited:
            return visited
        visited.add(source_str)

        # Scan the file for its direct imports
        info = self.scan_file(source_path)

        # Recursively get dependencies
        for imp_path in info.imports:
            imp_path_obj = Path(imp_path)
            if imp_path_obj.exists():
                self.get_transitive_dependencies(imp_path_obj, visited)

        return visited

    def needs_rebuild(self, source_path: Path) -> Tuple[bool, str]:
        """Check if a source file needs to be rebuilt.

        Returns:
            (needs_rebuild, reason) tuple
        """
        source_path = source_path.resolve()
        source_str = str(source_path)

        # Check if cached .ll exists
        cached_ll = self.get_cached_ll_path(source_path)
        if not cached_ll.exists():
            return True, "no cached .ll file"

        # Check if we have cached info for this file
        if source_str not in self.state.deps:
            return True, "not in cache"

        cached_info = self.state.deps[source_str]

        # Check if source file changed
        current_hash = compute_file_hash(source_path)
        if current_hash != cached_info.hash:
            return True, "source file changed"

        # Check if any transitive dependency changed
        all_deps = self.get_transitive_dependencies(source_path)
        for dep_path in all_deps:
            if dep_path == source_str:
                continue  # Skip self

            if dep_path not in self.state.deps:
                return True, f"dependency not in cache: {dep_path}"

            dep_info = self.state.deps[dep_path]
            current_dep_hash = compute_file_hash(Path(dep_path))
            if current_dep_hash != dep_info.hash:
                return True, f"dependency changed: {dep_path}"

        return False, "cache is valid"

    def update_cache(self, source_path: Path, ll_content: str):
        """Update the cache after a successful compilation.

        Args:
            source_path: The source file that was compiled
            ll_content: The generated LLVM IR content
        """
        source_path = source_path.resolve()

        # Ensure objects directory exists
        self.objects_dir.mkdir(parents=True, exist_ok=True)

        # Write the .ll file to cache
        cached_ll = self.get_cached_ll_path(source_path)
        cached_ll.write_text(ll_content)

        # Scan and update dependency info for the source file and all its deps
        all_deps = self.get_transitive_dependencies(source_path)
        for dep_path in all_deps:
            dep_path_obj = Path(dep_path)
            info = self.scan_file(dep_path_obj)
            self.state.deps[dep_path] = info

        # Save state to disk
        self.save()

    def get_cached_ll(self, source_path: Path) -> Optional[str]:
        """Get the cached .ll content if valid, or None if rebuild is needed."""
        source_path = source_path.resolve()

        needs_rebuild, reason = self.needs_rebuild(source_path)
        if needs_rebuild:
            return None

        cached_ll = self.get_cached_ll_path(source_path)
        if cached_ll.exists():
            return cached_ll.read_text()

        return None

    def has_valid_bc(self, source_path: Path) -> bool:
        """Check if a valid .bc (bitcode) file exists in cache.

        RFC #109 Phase 3: LLVM BC caching.
        Returns True if .bc exists and source hasn't changed.
        """
        source_path = source_path.resolve()

        needs_rebuild, _ = self.needs_rebuild(source_path)
        if needs_rebuild:
            return False

        cached_bc = self.get_cached_bc_path(source_path)
        return cached_bc.exists()

    def get_cached_bc(self, source_path: Path) -> Optional[Path]:
        """Get the path to cached .bc file if valid, or None if rebuild needed.

        RFC #109 Phase 3: Returns the path (not content) since .bc is binary.
        """
        source_path = source_path.resolve()

        needs_rebuild, reason = self.needs_rebuild(source_path)
        if needs_rebuild:
            return None

        cached_bc = self.get_cached_bc_path(source_path)
        if cached_bc.exists():
            return cached_bc

        return None

    def update_bc_cache(self, source_path: Path, bc_path: Path):
        """Copy a .bc file to the cache.

        RFC #109 Phase 3: Store compiled bitcode for faster rebuilds.
        """
        source_path = source_path.resolve()

        # Ensure objects directory exists
        self.objects_dir.mkdir(parents=True, exist_ok=True)

        # Copy the .bc file to cache
        cached_bc = self.get_cached_bc_path(source_path)
        import shutil
        shutil.copy2(bc_path, cached_bc)


# ============================================================================
# CLI for testing
# ============================================================================

def main():
    """CLI for testing the cache module."""
    import argparse

    parser = argparse.ArgumentParser(description="Ritz Build Cache")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a file for imports")
    scan_parser.add_argument("file", help="Source file to scan")

    # deps command
    deps_parser = subparsers.add_parser("deps", help="Show transitive dependencies")
    deps_parser.add_argument("file", help="Source file to analyze")

    # status command
    status_parser = subparsers.add_parser("status", help="Check if file needs rebuild")
    status_parser.add_argument("file", help="Source file to check")

    # clear command
    subparsers.add_parser("clear", help="Clear the cache")

    # show command
    subparsers.add_parser("show", help="Show cache contents")

    args = parser.parse_args()

    cache = BuildCache()

    if args.command == "scan":
        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return 1

        info = cache.scan_file(file_path)
        print(f"File: {file_path}")
        print(f"Hash: {info.hash[:16]}...")
        print(f"Imports: {info.imports}")
        print(f"Mtime: {info.mtime}")

    elif args.command == "deps":
        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return 1

        deps = cache.get_transitive_dependencies(file_path)
        print(f"Transitive dependencies of {file_path}:")
        for dep in sorted(deps):
            print(f"  {dep}")

    elif args.command == "status":
        file_path = Path(args.file).resolve()
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return 1

        needs_rebuild, reason = cache.needs_rebuild(file_path)
        if needs_rebuild:
            print(f"Needs rebuild: {reason}")
        else:
            print("Cache is valid, no rebuild needed")

    elif args.command == "clear":
        cache.clear()
        print("Cache cleared")

    elif args.command == "show":
        if not cache.cache_dir.exists():
            print("No cache exists")
            return 0

        print(f"Cache directory: {cache.cache_dir}")
        print(f"\nDependency entries: {len(cache.state.deps)}")
        for path, info in sorted(cache.state.deps.items()):
            print(f"  {path}")
            print(f"    hash: {info.hash[:16]}...")
            print(f"    imports: {len(info.imports)}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main() or 0)
