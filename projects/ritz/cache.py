#!/usr/bin/env python3
"""
Build cache for Ritz: import closures and the compiler fingerprint.

Compiled artifacts do not live here. Every module's .ll/.o goes through
`cas.ArtifactStore`, keyed on the content of the module's transitive import
closure and on the compiler fingerprint. This module provides those two
inputs:

1. `BuildCache.get_transitive_dependencies`: the import closure, resolved by
   ritz0's own `ImportResolver`, with each file's direct-import scan persisted
   by content hash so a new build process re-parses only edited files.
2. `compute_compiler_hash`: the fingerprint of the compiler (and build.py).

AGAST #3454: BuildCache used to keep its own per-module .ll/.bc/.o store
(`objects/`, `deps.json` and its rebuild checks). It lost its last caller when
the CAS took over and was deleted; do not reintroduce a second artifact cache.

Cache directory structure:
    .ritz-cache[-<compiler>]/
    ├── compiler_hash     # Fingerprint of the compiler the scans belong to
    └── imports.json      # Persisted direct-import scans
"""

import fcntl
import json
import hashlib
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple


CACHE_DIR_NAME = ".ritz-cache"
# Persisted direct-import scans (AGAST #1832): "<context>\0<path>" ->
# {"hash": content hash, "imports": [resolved paths]}.
IMPORTS_FILE = "imports.json"
COMPILER_HASH_FILE = "compiler_hash"
# Left behind in old cache directories by the deleted artifact cache (AGAST
# #3454). Nothing writes them now; a compiler change sweeps them away.
LEGACY_ENTRIES = ("objects", "deps.json", "hashes.json")

# The ritz0 fingerprint walk skips what cannot affect codegen: bytecode and
# pytest caches, the test/ tree and test_*.py modules.
RITZ0_EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", "test"}
RITZ0_EXCLUDE_FILE_PREFIXES = ("test_",)


# ============================================================================
# Concurrent-safe file writes (AGAST #1806)
# ============================================================================
#
# Several build.py processes share one cache directory: regression.sh builds
# up to REGRESSION_JOBS examples at once, and they all scan ritzlib. So:
#
# * Every file is written to a private temp file in the same directory and
#   renamed over the target. A reader sees the old file or the new one, never
#   a truncated one. The temp name is unique per writer: one fixed
#   `<name>.tmp` shared by two writers is the same race one level down.
# * Read-modify-write of the shared imports.json happens under an flock, and
#   a save merges this process's entries into what is on disk. Rewriting the
#   whole file from memory let the last process to save drop every entry the
#   others had added.

LOCK_FILE = ".lock"


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _atomic_write_text(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode())


@contextmanager
def _cache_lock(cache_dir: Path):
    """Exclusive lock over one cache directory's shared index files."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_dir / LOCK_FILE, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _merge_json(path: Path, updates: dict, indent: int = 2, sort_keys: bool = False) -> dict:
    """Write `updates` over the on-disk dict at `path`; return the result.

    Caller holds `_cache_lock`.
    """
    merged = _read_json(path)
    merged.update(updates)
    _atomic_write_text(path, json.dumps(merged, indent=indent, sort_keys=sort_keys))
    return merged


# AGAST #1832: there is deliberately no import scanner in this file. A regex
# that used to live here matched only bare `import a.b` lines and missed
# `import a.b { X }`, `pub import` and `import a as b`: 30% of the imports in
# the tree. A struct change in a module imported that way left its dependents'
# cached .ll/.o stale. The import graph now comes from ritz0's
# `ImportResolver.direct_imports`, the resolver the compiler and list_deps.py
# use. Do not reintroduce a second resolver here.

_RITZ0_DIR = Path(__file__).resolve().parent / "ritz0"


def _import_resolver_module():
    """Import ritz0's import_resolver (it needs ritz0/ on sys.path)."""
    import sys
    if str(_RITZ0_DIR) not in sys.path:
        sys.path.insert(0, str(_RITZ0_DIR))
    import import_resolver
    return import_resolver


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


def _hash_file_into(h: "hashlib._Hash", file_path: Path) -> None:
    """Stream `file_path` into the hash context `h`."""
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file's contents."""
    h = hashlib.sha256()
    _hash_file_into(h, file_path)
    return h.hexdigest()


def _collect_ritz0_sources(ritz0_root: Path) -> List[Path]:
    """Every codegen-relevant `.py` under ritz0/, sorted by relative path.

    Everything not excluded counts: a hand-curated allowlist used to be here,
    and it silently missed new files (`ritz0/emitter/*.py`) twice, so edits
    to them reused stale objects.
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
    """Fingerprint the compiler; part of every CAS key and import-scan store.

    ``ritz0``: build.py plus every ``.py`` under ``ritz0/`` except tests and
    bytecode caches (the source tree is the artifact). ``ritz1`` /
    ``ritz1_selfhosted``: build.py plus the binary under ``ritz1/build/``; a
    missing binary returns the sentinel ``"<compiler>-missing"`` so state
    recorded without it is invalidated once it appears.
    """
    h = hashlib.sha256()
    h.update(f"compiler={compiler}\n".encode())  # namespace the digest

    # build.py is codegen-critical for both compilers: it owns the clang flags
    # (-ffreestanding/-fno-builtin), the runtime shims and the link order.
    # Leaving it out once let a new clang flag reuse every stale object.
    build_driver = project_root / "build.py"
    if build_driver.is_file():
        h.update(b"build-driver\x00")
        _hash_file_into(h, build_driver)

    if compiler == "ritz0":
        ritz0_root = project_root / "ritz0"
        if not ritz0_root.is_dir():
            return h.hexdigest()
        for src in _collect_ritz0_sources(ritz0_root):
            rel = src.relative_to(ritz0_root).as_posix()
            h.update(rel.encode())
            h.update(b'\x00')
            _hash_file_into(h, src)
        return h.hexdigest()

    if compiler in ("ritz1", "ritz1_selfhosted"):
        binary = project_root / "ritz1" / "build" / compiler
        if not binary.is_file():
            return f"{compiler}-missing"
        h.update(f"{compiler}-binary\x00".encode())
        _hash_file_into(h, binary)
        return h.hexdigest()

    raise ValueError(f"unknown compiler: {compiler!r}")


class BuildCache:
    """Import closures of Ritz sources, plus the compiler fingerprint.

    `project_root` is the ritz project (auto-detected when None); `compiler`
    ("ritz0", "ritz1", "ritz1_selfhosted") selects the fingerprint and
    namespaces the cache directory.
    """

    def __init__(self, project_root: Optional[Path] = None, compiler: str = "ritz0"):
        self.project_root = project_root
        self.compiler = compiler
        self._cache_dir: Optional[Path] = None
        self._compiler_hash: Optional[str] = None
        # Import resolution context (AGAST #1832). See `set_import_context`.
        self._import_root: Optional[Path] = None
        self._import_deps: Dict[str, Tuple[Path, List[str]]] = {}
        self._import_source_roots: List[str] = []
        self._resolver = None
        # (resolved path, content hash) -> direct imports. A file is parsed
        # at most once per content per context, however many sources a build
        # checks.
        self._direct_imports: Dict[Tuple[str, str], List[str]] = {}
        # On-disk scan store (IMPORTS_FILE), loaded lazily. Lexing+parsing is
        # slow (~7s cold for ritz1's 39-file closure), so a new build process
        # re-parses only files whose content changed.
        self._imports_db: Optional[Dict[str, dict]] = None
        self._imports_db_dirty = False

    def set_import_context(
        self,
        project_root: Optional[Path] = None,
        dependencies: Optional[Dict[str, Tuple[Path, List[str]]]] = None,
        source_roots: Optional[List[str]] = None,
    ) -> None:
        """Resolve imports exactly as the build does.

        build.py resolves a package's imports with `--project-root <pkg>`,
        its `sources` roots and its dependency namespaces (list_deps.py and
        ritz0 both get them). Pass the same values here, or a module found
        through a source root or a dependency is missing from the cache's
        import graph, and edits to it never invalidate dependents.

        Args:
            project_root: Package directory (defaults to this cache's root).
            dependencies: name -> (dependency root, its source dirs).
            source_roots: Source directories, relative to `project_root`.
        """
        root = Path(project_root).resolve() if project_root else None
        deps = {name: (Path(p), list(srcs)) for name, (p, srcs) in (dependencies or {}).items()}
        roots = list(source_roots or [])
        if (root, deps, roots) == (self._import_root, self._import_deps, self._import_source_roots):
            return
        self._import_root, self._import_deps, self._import_source_roots = root, deps, roots
        self._resolver = None
        self._direct_imports.clear()

    def _context_key(self) -> str:
        """Identifies the resolution context of a persisted scan."""
        root = self._import_root or self.project_root
        return json.dumps([
            str(root) if root else None,
            sorted((n, str(p), s) for n, (p, s) in self._import_deps.items()),
            self._import_source_roots,
            os.environ.get("RITZ_PATH", ""),
        ])

    def _load_imports_db(self) -> Dict[str, dict]:
        if self._imports_db is None:
            self._imports_db = {}
            path = self.cache_dir / IMPORTS_FILE
            if path.exists():
                try:
                    self._imports_db = json.loads(path.read_text())
                except (OSError, ValueError):
                    pass  # corrupt or unreadable: rescan
        return self._imports_db

    def _save_imports_db(self) -> None:
        if self._imports_db_dirty and self._imports_db is not None:
            with _cache_lock(self.cache_dir):
                self._imports_db = _merge_json(
                    self.cache_dir / IMPORTS_FILE, self._imports_db, indent=1, sort_keys=True)
            self._imports_db_dirty = False

    def _scan_direct_imports(self, path: str, file_hash: str) -> List[str]:
        """Direct imports of `path`, from memory, disk, or a fresh parse."""
        key = (path, file_hash)
        imports = self._direct_imports.get(key)
        if imports is not None:
            return imports
        db = self._load_imports_db()
        db_key = f"{self._context_key()}\0{path}"
        entry = db.get(db_key)
        # Reuse only for identical content, and only while every target still
        # exists (a moved module can resolve the same import elsewhere).
        if (entry is not None and entry.get("hash") == file_hash
                and all(Path(p).exists() for p in entry.get("imports", []))):
            imports = list(entry["imports"])
        else:
            imports = self._get_resolver().direct_imports(path)
            db[db_key] = {"hash": file_hash, "imports": imports}
            self._imports_db_dirty = True
        self._direct_imports[key] = imports
        return imports

    def _get_resolver(self):
        if self._resolver is None:
            ir = _import_resolver_module()
            root = self._import_root or self.project_root
            self._resolver = ir.ImportResolver(
                str(root) if root else None,
                use_cache=False,  # discovery only; never write .ritz-meta
                dependencies={
                    name: ir.DependencyMapping(name=name, path=path, sources=srcs)
                    for name, (path, srcs) in self._import_deps.items()
                },
                source_roots=self._import_source_roots,
            )
        return self._resolver

    @property
    def cache_dir(self) -> Path:
        """``.ritz-cache`` for ritz0, ``.ritz-cache-<compiler>`` otherwise."""
        if self._cache_dir is None:
            # RITZ_BUILD_CACHE_DIR (AGAST #2793) moves it out of the project:
            # the ritz0 suite's throwaway package builds keep their index
            # there, out of the tree the xdist_group("tree") tests inspect.
            override = os.environ.get("RITZ_BUILD_CACHE_DIR")
            if override:
                base = Path(override)
            else:
                base = self.project_root if self.project_root else Path.cwd()
            if self.compiler == "ritz0":
                self._cache_dir = base / CACHE_DIR_NAME
            else:
                self._cache_dir = base / f"{CACHE_DIR_NAME}-{self.compiler}"
        return self._cache_dir

    def _get_current_compiler_hash(self) -> str:
        """`compute_compiler_hash` for `self.compiler`, computed once."""
        if self._compiler_hash is None:
            root = self.project_root or find_project_root(Path.cwd())
            self._compiler_hash = compute_compiler_hash(root, self.compiler) if root else "unknown"
        return self._compiler_hash

    def invalidate_if_compiler_changed(self) -> bool:
        """Call once at the top of a build; True if the compiler changed.

        If the recorded fingerprint is missing or differs from the current
        compiler's, the persisted import scans are discarded (a ritz0 change
        can change how imports parse or resolve), along with anything the
        deleted artifact cache left behind, and the current fingerprint is
        recorded. build.py also uses the verdict: a binary linked by the
        previous compiler must not be reused by the project-level fast path.
        """
        current = self._get_current_compiler_hash()
        hash_file = self.cache_dir / COMPILER_HASH_FILE
        # Under the lock: with several builds starting at once, the first
        # wipes and records the new compiler, the rest then see a match and
        # keep what it is building (AGAST #1806).
        with _cache_lock(self.cache_dir):
            try:
                if hash_file.read_text().strip() == current:
                    return False
            except OSError:
                pass  # no record yet
            for name in (IMPORTS_FILE, *LEGACY_ENTRIES):
                path = self.cache_dir / name
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            self._imports_db = {}
            self._imports_db_dirty = False
            self._direct_imports.clear()
            _atomic_write_text(hash_file, current)
            return True

    def save(self):
        """Persist this process's new import scans."""
        self._save_imports_db()

    def clear(self):
        """Clear the entire cache."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self._imports_db = {}
        self._imports_db_dirty = False
        self._direct_imports.clear()

    def import_scan_count(self) -> int:
        """Number of persisted direct-import scans (for `build.py cache-status`)."""
        return len(self._load_imports_db())

    def get_transitive_dependencies(self, source_path: Path, visited: Optional[Set[str]] = None) -> Set[str]:
        """Get all transitive dependencies of a source file.

        Returns a set of absolute file paths that the source file depends on,
        including the file itself.
        """
        if visited is None:
            visited = set()

        source_path = source_path.resolve()
        source_str = str(source_path)
        if source_str in visited:
            return visited
        visited.add(source_str)

        # Every import form, resolved by ritz0's resolver (AGAST #1832).
        imports = self._scan_direct_imports(source_str, compute_file_hash(source_path))
        for imp_path in imports:
            imp_path_obj = Path(imp_path)
            if imp_path_obj.exists():
                self.get_transitive_dependencies(imp_path_obj, visited)

        return visited
