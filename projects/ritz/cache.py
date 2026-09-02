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
COMPILER_HASH_FILE = "compiler_hash"

# Compiler fingerprint inputs — used by `compute_compiler_hash()` to invalidate
# every cached artifact when the compiler that produced them changes.
#
# History: this used to be a hand-curated list of ten ritz0 paths, which was
# fragile in two ways: (a) any new compiler file (like the post-#192 split-out
# `ritz0/emitter/*.py`) silently slipped past it, returning stale `.o` files
# from the cache after legitimate compiler edits; (b) it didn't cover ritz1 at
# all, even though ritz1 is now the default compiler for the stack. Today's
# debugging session burned hours chasing "codegen regressions" that turned out
# to be stale-cache placebos — that's the second time this hole has cost us.
#
# New shape: discover compiler inputs by walking the relevant tree, so adding
# a new file Just Works. Two compilers, two strategies:
#
#   ritz0 (Python source tree): walk `ritz0/`, hash every `.py` file except
#       tests and bytecode caches. Source is the artifact — no separate binary.
#
#   ritz1 (self-hosted, single binary): hash the `ritz1` binary directly. The
#       binary is the artifact; whatever produced it (ritz1/src/*.ritz at
#       whatever revision) is captured by the binary's content hash. If the
#       binary is missing, return a sentinel so any cache built without it is
#       invalidated when it appears.
#
# The legacy constant below is retained for the existing `test_build.py`
# tests, but is no longer used by `compute_compiler_hash()`.
COMPILER_CRITICAL_FILES = [
    "ritz0/emitter_llvmlite.py",
    "ritz0/parser_gen.py",
    "ritz0/parser_adapter.py",
    "ritz0/async_transform_v2.py",
    "ritz0/monomorph.py",
    "ritz0/name_resolver.py",
    "ritz0/import_resolver.py",
    "ritz0/ritz0.py",
    "ritz0/ritz_ast.py",
    "ritz0/type_checker.py",
]

# Directory- and filename-pattern excludes for the ritz0 fingerprint walk.
# These do not affect codegen, so we leave them out of the fingerprint:
#   - __pycache__/        : .pyc bytecode (regenerated on every run)
#   - .pytest_cache/      : pytest run state
#   - test/               : test fixtures and runner scaffolding
#   - test_*.py           : individual test modules
RITZ0_EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "test"}
RITZ0_EXCLUDE_FILE_PREFIXES = ("test_",)


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


def _hash_file_into(h: "hashlib._Hash", file_path: Path) -> None:
    """Stream `file_path` into the hash context `h`."""
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)


def _collect_ritz0_sources(ritz0_root: Path) -> List[Path]:
    """Walk the ritz0 Python tree and return every `.py` file that affects
    code generation, sorted by relative path for deterministic hashing.

    Excludes:
      - directories listed in `RITZ0_EXCLUDE_DIRS` (bytecode caches, test trees)
      - filenames starting with any prefix in `RITZ0_EXCLUDE_FILE_PREFIXES`
        (i.e. `test_*.py` test modules)

    Everything else under `ritz0/` is considered codegen-critical. This is
    the *correct* default: a hand-curated allowlist will silently miss new
    files (it has, twice).
    """
    sources: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(ritz0_root):
        # Prune excluded directories in-place so os.walk doesn't descend.
        dirnames[:] = [d for d in dirnames if d not in RITZ0_EXCLUDE_DIRS]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            if fn.startswith(RITZ0_EXCLUDE_FILE_PREFIXES):
                continue
            sources.append(Path(dirpath) / fn)
    sources.sort(key=lambda p: p.relative_to(ritz0_root).as_posix())
    return sources


def compute_compiler_hash(project_root: Path, compiler: str = "ritz0") -> str:
    """Compute a fingerprint of the compiler that produced cached artifacts.

    The fingerprint is what gates cache validity: if the compiler that
    produced the cached `.ll`/`.bc`/`.o` files differs from the compiler
    about to be invoked, the cache is invalidated wholesale.

    Strategies are per-compiler:

    ``ritz0`` (Python bootstrap)
        Walk ``ritz0/`` and hash every ``.py`` file except tests and
        bytecode caches. The source tree *is* the artifact — there is no
        separate compiled binary.

    ``ritz1`` (self-hosted, single binary)
        Hash the ``ritz1`` binary at ``ritz1/build/ritz1``. The binary is
        the artifact; whatever ritz1/src/*.ritz revision produced it is
        captured by the binary's content hash. If the binary does not
        exist, return a sentinel so cache built before the binary was
        produced is invalidated when it appears.

    Args:
        project_root: directory containing ``ritz0/`` and ``ritz1/``.
        compiler: "ritz0", "ritz1", or "ritz1_selfhosted".

    Returns:
        Hex-encoded SHA256 digest, or the sentinel ``"ritz1-missing"`` when
        ``compiler == "ritz1"`` and the binary does not exist (likewise
        ``"ritz1_selfhosted-missing"`` for the self-hosted binary).
    """
    h = hashlib.sha256()
    h.update(f"compiler={compiler}\n".encode())  # namespace the digest

    # build.py is codegen-critical for BOTH compilers: it owns the clang flag
    # list (notably -ffreestanding/-fno-builtin), the runtime shim selection and
    # the link order. Changing any of those changes the emitted objects just as
    # surely as changing a file inside ritz0/ does.
    #
    # It was previously omitted, so the fingerprint could not see a codegen
    # change that lived outside ritz0/. Adding -ffreestanding to the clang
    # invocation left the fingerprint identical, every cached .o was reused
    # verbatim, and the build kept failing with the exact same link error the
    # flag was added to fix — including the same object hash, which is what
    # gave it away.
    build_driver = project_root / "build.py"
    if build_driver.is_file():
        h.update(b"build-driver\x00")
        _hash_file_into(h, build_driver)

    if compiler == "ritz0":
        ritz0_root = project_root / "ritz0"
        if not ritz0_root.is_dir():
            # No ritz0 tree at all — fall through to an empty digest under
            # the namespace prefix above. Any future ritz0 install will
            # produce a different hash and invalidate.
            return h.hexdigest()
        for src in _collect_ritz0_sources(ritz0_root):
            rel = src.relative_to(ritz0_root).as_posix()
            h.update(rel.encode())
            h.update(b'\x00')
            _hash_file_into(h, src)
        return h.hexdigest()

    if compiler == "ritz1":
        ritz1_bin = project_root / "ritz1" / "build" / "ritz1"
        if not ritz1_bin.is_file():
            return "ritz1-missing"
        h.update(b"ritz1-binary\x00")
        _hash_file_into(h, ritz1_bin)
        return h.hexdigest()

    if compiler == "ritz1_selfhosted":
        sh_bin = project_root / "ritz1" / "build" / "ritz1_selfhosted"
        if not sh_bin.is_file():
            return "ritz1_selfhosted-missing"
        h.update(b"ritz1_selfhosted-binary\x00")
        _hash_file_into(h, sh_bin)
        return h.hexdigest()

    raise ValueError(f"unknown compiler: {compiler!r}")


# ============================================================================
# Build Cache
# ============================================================================

class BuildCache:
    """Manages the build cache for incremental compilation."""

    def __init__(self, project_root: Optional[Path] = None, compiler: str = "ritz0"):
        """Initialize the build cache.

        Args:
            project_root: Root directory of the project. If not provided,
                         will be auto-detected when needed.
            compiler: Name of the compiler producing artifacts ("ritz0" or
                     "ritz1"). The cache directory is namespaced by compiler
                     so warm rebuilds across compilers don't pick up the
                     wrong artifact (different IR, different ABI assumptions).
        """
        self.project_root = project_root
        self.compiler = compiler
        self._state: Optional[CacheState] = None
        self._cache_dir: Optional[Path] = None
        self._compiler_hash: Optional[str] = None
        self._compiler_hash_valid: Optional[bool] = None

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory path.

        ritz0 uses ``.ritz-cache`` (legacy); ritz1 uses ``.ritz-cache-ritz1``
        so its incremental .ll/.bc/.o store is partitioned from ritz0's. The
        suffix is intentionally short — these directories live next to source
        and end up in `.gitignore` patterns.
        """
        if self._cache_dir is None:
            base = self.project_root if self.project_root else Path.cwd()
            if self.compiler == "ritz0":
                self._cache_dir = base / CACHE_DIR_NAME
            else:
                self._cache_dir = base / f"{CACHE_DIR_NAME}-{self.compiler}"
        return self._cache_dir

    @property
    def objects_dir(self) -> Path:
        """Get the objects subdirectory path."""
        return self.cache_dir / OBJECTS_DIR

    @property
    def compiler_hash_file(self) -> Path:
        """Get the compiler hash file path."""
        return self.cache_dir / COMPILER_HASH_FILE

    def _get_current_compiler_hash(self) -> str:
        """Get the current compiler hash, computing if needed.

        The fingerprint is computed for `self.compiler` — ritz0 walks the
        Python tree, ritz1 hashes the binary. See `compute_compiler_hash`.
        """
        if self._compiler_hash is None:
            root = self.project_root or find_project_root(Path.cwd())
            if root:
                self._compiler_hash = compute_compiler_hash(root, self.compiler)
            else:
                self._compiler_hash = "unknown"
        return self._compiler_hash

    def _check_compiler_hash(self) -> bool:
        """Check if the cached compiler hash matches current compiler.

        Returns True if cache is valid, False if compiler changed.
        """
        if self._compiler_hash_valid is not None:
            return self._compiler_hash_valid

        current_hash = self._get_current_compiler_hash()

        if not self.compiler_hash_file.exists():
            # No cached hash - cache is invalid
            self._compiler_hash_valid = False
            return False

        cached_hash = self.compiler_hash_file.read_text().strip()
        self._compiler_hash_valid = (cached_hash == current_hash)
        return self._compiler_hash_valid

    def _update_compiler_hash(self):
        """Update the stored compiler hash."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        current_hash = self._get_current_compiler_hash()
        self.compiler_hash_file.write_text(current_hash)
        self._compiler_hash_valid = True

    def invalidate_if_compiler_changed(self) -> bool:
        """One-shot wholesale invalidation when the compiler has changed.

        Call this *once* at the top of a build, before any per-source
        decisions are made. If the on-disk compiler hash exists and
        mismatches the current compiler's fingerprint, every cached
        ``.ll``/``.bc``/``.o`` is stale (it was emitted by a different
        compiler) and must be discarded. This wipes the objects directory,
        the dependency graph, and the per-file hashes, then refreshes the
        compiler hash file so that artifacts produced *by this build* are
        treated as fresh.

        Why this is necessary: ``needs_rebuild()`` checks the compiler hash
        per-source. After the first source is recompiled, ``update_cache``
        runs and refreshes the compiler-hash file as a side effect — which
        flips ``_compiler_hash_valid`` to True. Every subsequent source
        then sees a "fresh" compiler hash and returns the cached
        (compiler-stale) ``.o``. So without this method the cache only
        actually rebuilds the *first* source after a compiler change; the
        rest are silently mismatched.

        Returns:
            True if invalidation actually happened (compiler changed),
            False if cache was already up-to-date.
        """
        if self._check_compiler_hash():
            # Compiler hash matches what produced the cached artifacts;
            # nothing to invalidate. Each source still goes through
            # `needs_rebuild()` for its own per-file freshness check.
            return False

        # Mismatch (or no record at all). Wipe the artifact store so
        # every per-source cache lookup misses and triggers a fresh
        # compile, then write the fingerprint of the *current* compiler
        # so that artifacts emitted during this build are recorded as
        # produced by it.
        if self.objects_dir.exists():
            shutil.rmtree(self.objects_dir)
        self._state = CacheState()  # forget dep graph + hashes too
        self._update_compiler_hash()
        return True

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

    def get_cached_obj_path(self, source_path: Path) -> Path:
        """Path of the cached native ``.o`` produced by ``clang -c``.

        AGAST #192: Caching .o (rather than re-running ``clang -c`` each
        warm rebuild) is what makes the touched-source case meet the <3s
        gate.  Without this, even though ritz1 itself short-circuits via
        fn_cache.ritz, clang would still re-lower every cached .ll on each
        invocation — ~3s for an 8-source project like zeus.
        """
        safe_name = self._get_safe_cache_name(source_path)
        return self.objects_dir / f"{safe_name}.o"

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

        # Check if compiler itself changed (invalidates entire cache)
        if not self._check_compiler_hash():
            return True, "compiler changed"

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
        # Sorted (AGAST #1286): `get_transitive_dependencies` returns a set, so
        # iterating it raw picks a hash-seed-dependent order. The rebuild
        # *decision* is order-independent, but the reason string is not — with
        # several changed deps this named a different one each run, which is the
        # same "reports a different thing every time" symptom that made build
        # failures impossible to diagnose.
        all_deps = sorted(self.get_transitive_dependencies(source_path))
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

        # Update compiler hash (ensures cache matches current compiler)
        self._update_compiler_hash()

        # Write the .ll file to cache
        cached_ll = self.get_cached_ll_path(source_path)
        cached_ll.write_text(ll_content)

        # Scan and update dependency info for the source file and all its deps
        # Sorted (AGAST #1286): this populates `self.state.deps`, a plain dict
        # that `CacheState.save` serialises to `deps.json` in insertion order.
        # Set iteration order made that file's key order vary run to run —
        # harmless for build decisions, but it left the cache non-reproducible
        # and noisy to diff when investigating "the cache lies" reports.
        all_deps = sorted(self.get_transitive_dependencies(source_path))
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

    def get_cached_obj(self, source_path: Path) -> Optional[Path]:
        """Path of a valid cached .o, or None if a rebuild is needed."""
        source_path = source_path.resolve()
        needs_rebuild, _ = self.needs_rebuild(source_path)
        if needs_rebuild:
            return None
        cached_obj = self.get_cached_obj_path(source_path)
        if cached_obj.exists():
            return cached_obj
        return None

    def update_obj_cache(self, source_path: Path, obj_path: Path):
        """Copy a freshly produced .o into the cache."""
        source_path = source_path.resolve()
        self.objects_dir.mkdir(parents=True, exist_ok=True)
        cached_obj = self.get_cached_obj_path(source_path)
        import shutil
        shutil.copy2(obj_path, cached_obj)


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
