#!/usr/bin/env python3
"""
Tests for build system Phase 1 features (RFC #109).

Tests:
- Entry point resolution (module::function → file + fn)
- Source discovery with directory/glob expansion
- Build profiles (debug/release)
"""

import pytest
import tempfile
from pathlib import Path

# Import build system functions
import sys
import importlib.util
# Add both ritz0/ and project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
# Import from our build.py explicitly (avoid pip's build package)
_spec = importlib.util.spec_from_file_location("ritz_build", Path(__file__).parent.parent / "build.py")
_build_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_build_module)
resolve_entry_point = _build_module.resolve_entry_point
discover_sources = _build_module.discover_sources
get_build_profile = _build_module.get_build_profile
DependencySpec = _build_module.DependencySpec
parse_dependencies = _build_module.parse_dependencies


class TestEntryPointResolution:
    """Test entry = "module::function" resolution."""

    def test_simple_main(self, tmp_path):
        """main::main → src/main.ritz, fn main()"""
        # Setup: create src/main.ritz
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        main_file = src_dir / "main.ritz"
        main_file.write_text("fn main() -> i32\n  0\n")

        result = resolve_entry_point("main::main", tmp_path, ["src"])
        assert result is not None
        path, fn_name = result
        assert path == main_file
        assert fn_name == "main"

    def test_nested_module(self, tmp_path):
        """http.server::run → src/http/server.ritz, fn run()"""
        src_dir = tmp_path / "src" / "http"
        src_dir.mkdir(parents=True)
        server_file = src_dir / "server.ritz"
        server_file.write_text("fn run() -> i32\n  0\n")

        result = resolve_entry_point("http.server::run", tmp_path, ["src"])
        assert result is not None
        path, fn_name = result
        assert path == server_file
        assert fn_name == "run"

    def test_multiple_sources(self, tmp_path):
        """Search multiple source directories."""
        # Create src/app.ritz (empty)
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create lib/app.ritz (has main)
        lib_dir = tmp_path / "lib"
        lib_dir.mkdir()
        lib_app = lib_dir / "app.ritz"
        lib_app.write_text("fn main() -> i32\n  0\n")

        # First match wins
        result = resolve_entry_point("app::main", tmp_path, ["src", "lib"])
        assert result is not None
        path, fn_name = result
        assert path == lib_app

    def test_not_found(self, tmp_path):
        """Non-existent module returns None."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        result = resolve_entry_point("nonexistent::main", tmp_path, ["src"])
        assert result is None

    def test_backward_compat_path(self, tmp_path):
        """path = "src/main.ritz" still works."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        main_file = src_dir / "main.ritz"
        main_file.write_text("fn main() -> i32\n  0\n")

        # When entry is None but path is given, resolve_entry_point should handle it
        # This is handled at a higher level, but the function should accept file paths
        result = resolve_entry_point_from_path(str(main_file), tmp_path)
        assert result is not None
        path, fn_name = result
        assert path == main_file
        assert fn_name == "main"


class TestSourceDiscovery:
    """Test sources = [...] discovery."""

    def test_directory_expands_to_glob(self, tmp_path):
        """sources = ["src"] expands to all .ritz files recursively."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create some files
        (src_dir / "main.ritz").write_text("fn main() -> i32\n  0\n")
        (src_dir / "lib.ritz").write_text("fn helper() -> i32\n  1\n")

        subdir = src_dir / "http"
        subdir.mkdir()
        (subdir / "request.ritz").write_text("fn request() -> i32\n  2\n")

        sources = discover_sources(tmp_path, ["src"])
        assert len(sources) == 3
        assert src_dir / "main.ritz" in sources
        assert src_dir / "lib.ritz" in sources
        assert subdir / "request.ritz" in sources

    def test_explicit_glob(self, tmp_path):
        """sources = ["src/*.ritz"] only matches top-level."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        (src_dir / "main.ritz").write_text("fn main() -> i32\n  0\n")

        subdir = src_dir / "http"
        subdir.mkdir()
        (subdir / "request.ritz").write_text("fn request() -> i32\n  2\n")

        sources = discover_sources(tmp_path, ["src/*.ritz"])
        assert len(sources) == 1
        assert src_dir / "main.ritz" in sources

    def test_exclusion_pattern(self, tmp_path):
        """sources = ["src", "!src/generated"] excludes matching paths."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.ritz").write_text("fn main() -> i32\n  0\n")

        gen_dir = src_dir / "generated"
        gen_dir.mkdir()
        (gen_dir / "auto.ritz").write_text("fn auto() -> i32\n  3\n")

        sources = discover_sources(tmp_path, ["src", "!src/generated"])
        assert len(sources) == 1
        assert src_dir / "main.ritz" in sources

    def test_default_sources(self, tmp_path):
        """Default: ["src"] if src/ exists, else ["."]"""
        # With src/
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.ritz").write_text("fn main() -> i32\n  0\n")

        sources = discover_sources(tmp_path, None)  # None = use default
        assert src_dir / "main.ritz" in sources

        # Without src/ - should use current dir
        tmp_path2 = Path(tempfile.mkdtemp())
        (tmp_path2 / "main.ritz").write_text("fn main() -> i32\n  0\n")

        sources2 = discover_sources(tmp_path2, None)
        assert tmp_path2 / "main.ritz" in sources2


class TestBuildProfiles:
    """Test build profile resolution."""

    def test_default_profile(self):
        """Default profile is debug."""
        config = {"package": {"name": "test"}}
        profile = get_build_profile(config, None)
        assert profile["name"] == "debug"
        assert profile["opt_level"] == 0
        assert profile["debug"] is True

    def test_debug_profile(self):
        """--debug selects debug profile."""
        config = {
            "package": {"name": "test"},
            "profile": {
                "debug": {"opt-level": 0, "debug": True}
            }
        }
        profile = get_build_profile(config, "debug")
        assert profile["name"] == "debug"
        assert profile["opt_level"] == 0

    def test_release_profile(self):
        """--release selects release profile."""
        config = {
            "package": {"name": "test"},
            "profile": {
                "release": {"opt-level": 3, "debug": False, "lto": True}
            }
        }
        profile = get_build_profile(config, "release")
        assert profile["name"] == "release"
        assert profile["opt_level"] == 3
        assert profile["lto"] is True

    def test_profile_inherits_build(self):
        """Profiles inherit from [build] section."""
        config = {
            "package": {"name": "test"},
            "build": {"opt-level": 2, "debug": True},
            "profile": {
                "release": {"opt-level": 3}  # Only override opt-level
            }
        }
        profile = get_build_profile(config, "release")
        assert profile["opt_level"] == 3  # Overridden
        assert profile["debug"] is True   # Inherited from [build]


# Helper function that will be implemented
def resolve_entry_point_from_path(path: str, pkg_dir: Path) -> tuple[Path, str] | None:
    """Resolve a direct file path to (path, function_name).

    Backward compatibility for path = "src/main.ritz" syntax.
    """
    from build import detect_main_function
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = pkg_dir / file_path
    if not file_path.exists():
        return None
    fn_name = detect_main_function(file_path)
    return (file_path, fn_name) if fn_name else None


# =============================================================================
# Phase 2: Dependency Resolution Tests
# =============================================================================

class TestDependencyParsing:
    """Test [dependencies] section parsing."""

    def test_parse_path_dependency(self, tmp_path):
        """Parse a simple path dependency."""
        # DependencySpec and parse_dependencies imported at module level

        # Create dependency directory
        dep_dir = tmp_path / "squeeze"
        dep_dir.mkdir()
        (dep_dir / "src").mkdir()
        (dep_dir / "src" / "gzip.ritz").write_text("pub fn compress() -> i32\n  0\n")

        config = {
            "package": {"name": "test"},
            "dependencies": {
                "squeeze": {"path": "squeeze"}
            }
        }

        deps = parse_dependencies(config, tmp_path)
        assert "squeeze" in deps
        assert deps["squeeze"].name == "squeeze"
        assert deps["squeeze"].path == dep_dir
        assert deps["squeeze"].sources == ["src"]

    def test_parse_dependency_with_sources(self, tmp_path):
        """Parse dependency with explicit sources."""
        from build import parse_dependencies

        # Create dependency with lib/ directory
        dep_dir = tmp_path / "mylib"
        dep_dir.mkdir()
        (dep_dir / "lib").mkdir()

        config = {
            "package": {"name": "test"},
            "dependencies": {
                "mylib": {"path": "mylib", "sources": ["lib"]}
            }
        }

        deps = parse_dependencies(config, tmp_path)
        assert deps["mylib"].sources == ["lib"]

    def test_dependency_reads_sources_from_toml(self, tmp_path):
        """Dependency sources read from its ritz.toml."""
        from build import parse_dependencies

        # Create dependency with its own ritz.toml
        # Note: sources is at top level per RFC #109, not inside [package]
        dep_dir = tmp_path / "squeeze"
        dep_dir.mkdir()
        (dep_dir / "lib").mkdir()
        (dep_dir / "ritz.toml").write_text('[package]\nname = "squeeze"\n\nsources = ["lib"]\n')

        config = {
            "package": {"name": "test"},
            "dependencies": {
                "squeeze": {"path": "squeeze"}
            }
        }

        deps = parse_dependencies(config, tmp_path)
        assert deps["squeeze"].sources == ["lib"]


@pytest.mark.xfail(reason="DependencySpec.resolve_import moved to import_resolver.DependencyMapping")
class TestDependencyResolution:
    """Test dependency import resolution."""

    def test_resolve_import_in_dependency(self, tmp_path):
        """squeeze.gzip resolves to squeeze/src/gzip.ritz"""
        # DependencySpec imported at module level

        # Create dependency structure
        dep_dir = tmp_path / "squeeze"
        dep_dir.mkdir()
        src_dir = dep_dir / "src"
        src_dir.mkdir()
        gzip_file = src_dir / "gzip.ritz"
        gzip_file.write_text("pub fn compress() -> i32\n  0\n")

        dep = DependencySpec(name="squeeze", path=dep_dir, sources=["src"])

        # Resolve "gzip" within squeeze
        result = dep.resolve_import(["gzip"])
        assert result is not None
        assert result == gzip_file

    def test_resolve_nested_import_in_dependency(self, tmp_path):
        """squeeze.deflate.raw resolves to squeeze/src/deflate/raw.ritz"""
        # DependencySpec imported at module level

        # Create nested structure
        dep_dir = tmp_path / "squeeze"
        dep_dir.mkdir()
        src_dir = dep_dir / "src" / "deflate"
        src_dir.mkdir(parents=True)
        raw_file = src_dir / "raw.ritz"
        raw_file.write_text("pub fn inflate() -> i32\n  0\n")

        dep = DependencySpec(name="squeeze", path=dep_dir, sources=["src"])

        # Resolve "deflate.raw" within squeeze
        result = dep.resolve_import(["deflate", "raw"])
        assert result is not None
        assert result == raw_file

    def test_resolve_import_not_found(self, tmp_path):
        """Non-existent module returns None."""
        # DependencySpec imported at module level

        dep_dir = tmp_path / "squeeze"
        dep_dir.mkdir()
        (dep_dir / "src").mkdir()

        dep = DependencySpec(name="squeeze", path=dep_dir, sources=["src"])

        result = dep.resolve_import(["nonexistent"])
        assert result is None


class TestTransitiveDependencies:
    """Test transitive dependency resolution."""

    def test_simple_transitive(self, tmp_path):
        """A -> B -> C gives all three."""
        from build import get_transitive_dependencies

        # Create C
        c_dir = tmp_path / "c"
        c_dir.mkdir()
        (c_dir / "src").mkdir()
        (c_dir / "ritz.toml").write_text('[package]\nname = "c"\n')

        # Create B depending on C
        b_dir = tmp_path / "b"
        b_dir.mkdir()
        (b_dir / "src").mkdir()
        (b_dir / "ritz.toml").write_text('''
[package]
name = "b"
[dependencies]
c = { path = "../c" }
''')

        # Create A depending on B
        a_dir = tmp_path / "a"
        a_dir.mkdir()
        (a_dir / "src").mkdir()
        config = {
            "package": {"name": "a"},
            "dependencies": {
                "b": {"path": "../b"}
            }
        }

        deps = get_transitive_dependencies(a_dir, config)
        assert "b" in deps
        assert "c" in deps

    def test_circular_dependency_error(self, tmp_path):
        """Circular dependency raises error."""
        from build import get_transitive_dependencies

        # Create A depending on B
        a_dir = tmp_path / "a"
        a_dir.mkdir()
        (a_dir / "src").mkdir()
        (a_dir / "ritz.toml").write_text('''
[package]
name = "a"
[dependencies]
b = { path = "../b" }
''')

        # Create B depending on A (circular!)
        b_dir = tmp_path / "b"
        b_dir.mkdir()
        (b_dir / "src").mkdir()
        (b_dir / "ritz.toml").write_text('''
[package]
name = "b"
[dependencies]
a = { path = "../a" }
''')

        config = {
            "package": {"name": "a"},
            "dependencies": {
                "b": {"path": "../b"}
            }
        }

        with pytest.raises(ValueError, match="Circular dependency"):
            get_transitive_dependencies(a_dir, config)


# =============================================================================
# Cache Compiler Hash Tests
# =============================================================================

class TestCacheCompilerHash:
    """Test compiler hash for cache invalidation."""

    def test_compiler_hash_computed(self, tmp_path):
        """Compiler hash is computed from critical files."""
        from cache import compute_compiler_hash, COMPILER_CRITICAL_FILES

        # Create a fake project root with some compiler files
        ritz0_dir = tmp_path / "ritz0"
        ritz0_dir.mkdir()

        # Create a minimal set of critical files
        (ritz0_dir / "emitter_llvmlite.py").write_text("# emitter code")
        (ritz0_dir / "parser_gen.py").write_text("# parser code")

        h = compute_compiler_hash(tmp_path)
        assert len(h) == 64  # SHA256 hex digest

    def test_compiler_hash_changes_with_file(self, tmp_path):
        """Compiler hash changes when a critical file changes."""
        from cache import compute_compiler_hash

        ritz0_dir = tmp_path / "ritz0"
        ritz0_dir.mkdir()
        emitter = ritz0_dir / "emitter_llvmlite.py"
        emitter.write_text("# version 1")

        h1 = compute_compiler_hash(tmp_path)

        # Change the file
        emitter.write_text("# version 2")

        h2 = compute_compiler_hash(tmp_path)
        assert h1 != h2

    def test_cache_invalidated_on_compiler_change(self, tmp_path):
        """Cache is invalidated when compiler hash changes."""
        from cache import BuildCache

        # Setup project
        ritz0_dir = tmp_path / "ritz0"
        ritz0_dir.mkdir()
        emitter = ritz0_dir / "emitter_llvmlite.py"
        emitter.write_text("# version 1")

        cache = BuildCache(project_root=tmp_path)

        # Initially invalid (no compiler_hash file)
        assert cache._check_compiler_hash() is False

        # Update hash
        cache._update_compiler_hash()
        assert cache._check_compiler_hash() is True

        # Change compiler - should invalidate
        emitter.write_text("# version 2")
        cache._compiler_hash = None  # Reset cached value
        cache._compiler_hash_valid = None
        assert cache._check_compiler_hash() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
