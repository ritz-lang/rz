#!/usr/bin/env python3
"""Tests for the Ritz packaging system (RFC #107)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from packaging import (
    compute_source_hash,
    compute_cache_key,
    parse_uri,
    GlobalCache,
    PackageMetadata,
    get_target_triple,
)


class TestURIParsing(unittest.TestCase):
    """Tests for parse_uri function."""

    def test_local_absolute_path(self):
        result = parse_uri("/home/user/myproject")
        self.assertEqual(result["type"], "path")
        self.assertEqual(result["path"], "/home/user/myproject")

    def test_local_relative_path(self):
        result = parse_uri("./myproject")
        self.assertEqual(result["type"], "path")
        self.assertEqual(result["path"], "./myproject")

    def test_local_parent_path(self):
        result = parse_uri("../other/project")
        self.assertEqual(result["type"], "path")
        self.assertEqual(result["path"], "../other/project")

    def test_https_url(self):
        result = parse_uri("https://github.com/user/repo")
        self.assertEqual(result["type"], "git")
        self.assertEqual(result["uri"], "https://github.com/user/repo")
        self.assertIsNone(result["ref"])

    def test_https_with_tag(self):
        result = parse_uri("https://github.com/user/repo#tag=v1.0")
        self.assertEqual(result["type"], "git")
        self.assertEqual(result["uri"], "https://github.com/user/repo")
        self.assertEqual(result["ref_type"], "tag")
        self.assertEqual(result["ref"], "v1.0")

    def test_https_with_branch(self):
        result = parse_uri("https://github.com/user/repo#branch=main")
        self.assertEqual(result["type"], "git")
        self.assertEqual(result["ref_type"], "branch")
        self.assertEqual(result["ref"], "main")

    def test_https_with_rev(self):
        result = parse_uri("https://github.com/user/repo#rev=abc123")
        self.assertEqual(result["type"], "git")
        self.assertEqual(result["ref_type"], "rev")
        self.assertEqual(result["ref"], "abc123")


class TestContentHashing(unittest.TestCase):
    """Tests for content hashing."""

    def test_compute_source_hash_deterministic(self):
        """Same files should produce same hash."""
        with tempfile.TemporaryDirectory() as tmp:
            pkg_dir = Path(tmp)
            (pkg_dir / "ritz.toml").write_text('[package]\nname = "test"\n')
            (pkg_dir / "main.ritz").write_text("fn main() -> i32\n    0\n")

            hash1 = compute_source_hash(pkg_dir)
            hash2 = compute_source_hash(pkg_dir)
            self.assertEqual(hash1, hash2)

    def test_compute_source_hash_changes_on_content_change(self):
        """Different content should produce different hash."""
        with tempfile.TemporaryDirectory() as tmp:
            pkg_dir = Path(tmp)
            (pkg_dir / "ritz.toml").write_text('[package]\nname = "test"\n')
            (pkg_dir / "main.ritz").write_text("fn main() -> i32\n    0\n")

            hash1 = compute_source_hash(pkg_dir)

            (pkg_dir / "main.ritz").write_text("fn main() -> i32\n    42\n")
            hash2 = compute_source_hash(pkg_dir)

            self.assertNotEqual(hash1, hash2)

    def test_compute_cache_key_includes_target(self):
        """Cache key should differ for different targets."""
        source_hash = "abc123"
        key1 = compute_cache_key(source_hash, "x86_64-linux", 0)
        key2 = compute_cache_key(source_hash, "aarch64-linux", 0)
        self.assertNotEqual(key1, key2)

    def test_compute_cache_key_includes_opt_level(self):
        """Cache key should differ for different optimization levels."""
        source_hash = "abc123"
        key1 = compute_cache_key(source_hash, "x86_64-linux", 0)
        key2 = compute_cache_key(source_hash, "x86_64-linux", 3)
        self.assertNotEqual(key1, key2)


class TestGlobalCache(unittest.TestCase):
    """Tests for GlobalCache class."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.cache = GlobalCache(Path(self.tmp_dir))
        self.cache.ensure_dirs()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_ensure_dirs_creates_structure(self):
        """ensure_dirs should create required directories."""
        self.assertTrue(self.cache.cache_dir.exists())
        self.assertTrue(self.cache.packages_dir.exists())
        self.assertTrue(self.cache.bin_dir.exists())

    def test_has_cached_build_false_when_empty(self):
        """has_cached_build should return False for non-existent cache."""
        self.assertFalse(self.cache.has_cached_build("nonexistent", "x86_64-linux"))

    def test_store_and_retrieve_build(self):
        """Should be able to store and retrieve a build."""
        cache_key = "test123"
        target = "x86_64-linux"

        # Create a test binary
        test_binary = Path(self.tmp_dir) / "test_bin"
        test_binary.write_text("#!/bin/sh\necho test")
        test_binary.chmod(0o755)

        metadata = PackageMetadata(
            name="testpkg",
            version="1.0.0",
            source_uri="/path/to/source",
            source_hash="abc123",
            installed_at="2026-01-01T00:00:00",
            target=target,
            compiler_version="ritz0-v1",
            binaries=["test_bin"]
        )

        self.cache.store_build(cache_key, target, metadata, {"test_bin": test_binary})

        # Verify it's cached
        self.assertTrue(self.cache.has_cached_build(cache_key, target))

        # Retrieve metadata
        retrieved = self.cache.get_cached_metadata(cache_key)
        self.assertEqual(retrieved.name, "testpkg")
        self.assertEqual(retrieved.version, "1.0.0")

    def test_create_symlinks(self):
        """Should create symlinks in bin directory."""
        cache_key = "test123"
        target = "x86_64-linux"

        # Create a test binary
        test_binary = Path(self.tmp_dir) / "test_bin"
        test_binary.write_text("#!/bin/sh\necho test")
        test_binary.chmod(0o755)

        metadata = PackageMetadata(
            name="testpkg",
            version="1.0.0",
            source_uri="/path/to/source",
            source_hash="abc123",
            installed_at="2026-01-01T00:00:00",
            target=target,
            compiler_version="ritz0-v1",
            binaries=["test_bin"]
        )

        self.cache.store_build(cache_key, target, metadata, {"test_bin": test_binary})
        symlinks = self.cache.create_symlinks(cache_key, target)

        self.assertEqual(len(symlinks), 1)
        self.assertTrue(symlinks[0].is_symlink())

    def test_list_installed(self):
        """Should list all installed packages."""
        # Initially empty
        self.assertEqual(len(self.cache.list_installed()), 0)

        # Add a package
        cache_key = "test123"
        target = "x86_64-linux"
        test_binary = Path(self.tmp_dir) / "test_bin"
        test_binary.write_text("test")
        test_binary.chmod(0o755)

        metadata = PackageMetadata(
            name="testpkg",
            version="1.0.0",
            source_uri="/path/to/source",
            source_hash="abc123",
            installed_at="2026-01-01T00:00:00",
            target=target,
            compiler_version="ritz0-v1",
            binaries=["test_bin"]
        )

        self.cache.store_build(cache_key, target, metadata, {"test_bin": test_binary})

        installed = self.cache.list_installed()
        self.assertEqual(len(installed), 1)
        self.assertEqual(installed[0][1].name, "testpkg")

    def test_clear_removes_all(self):
        """clear should remove all cached data."""
        # Add some data
        cache_key = "test123"
        target = "x86_64-linux"
        test_binary = Path(self.tmp_dir) / "test_bin"
        test_binary.write_text("test")

        metadata = PackageMetadata(
            name="testpkg",
            version="1.0.0",
            source_uri="/path/to/source",
            source_hash="abc123",
            installed_at="2026-01-01T00:00:00",
            target=target,
            compiler_version="ritz0-v1",
            binaries=["test_bin"]
        )

        self.cache.store_build(cache_key, target, metadata, {"test_bin": test_binary})
        self.cache.create_symlinks(cache_key, target)

        # Clear
        self.cache.clear()

        # Verify empty
        self.assertEqual(len(self.cache.list_installed()), 0)


class TestPackageMetadata(unittest.TestCase):
    """Tests for PackageMetadata class."""

    def test_to_dict_and_from_dict(self):
        """Should serialize and deserialize correctly."""
        metadata = PackageMetadata(
            name="test",
            version="1.0.0",
            source_uri="https://example.com",
            source_hash="abc123",
            installed_at="2026-01-01",
            target="x86_64-linux",
            compiler_version="ritz0-v1",
            binaries=["bin1", "bin2"]
        )

        data = metadata.to_dict()
        restored = PackageMetadata.from_dict(data)

        self.assertEqual(metadata.name, restored.name)
        self.assertEqual(metadata.version, restored.version)
        self.assertEqual(metadata.binaries, restored.binaries)


class TestTargetTriple(unittest.TestCase):
    """Tests for get_target_triple."""

    def test_returns_string(self):
        """Should return a non-empty string."""
        target = get_target_triple()
        self.assertIsInstance(target, str)
        self.assertGreater(len(target), 0)

    def test_has_arch_and_os(self):
        """Should include architecture and OS."""
        target = get_target_triple()
        parts = target.split("-")
        self.assertGreaterEqual(len(parts), 2)


class TestLockFile(unittest.TestCase):
    """Tests for ritz.lock file generation."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.pkg_dir = Path(self.tmp_dir) / "myproject"
        self.pkg_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_lock_entry_creation(self):
        """LockEntry should store package pinning info."""
        from packaging import LockEntry

        entry = LockEntry(
            name="json",
            source="git+https://github.com/ritz-lang/json?rev=abc123def",
            checksum="sha256:e3b0c44298fc1c149afbf4c8996fb924",
            version="1.0.0"
        )

        self.assertEqual(entry.name, "json")
        self.assertEqual(entry.source, "git+https://github.com/ritz-lang/json?rev=abc123def")
        self.assertIn("sha256:", entry.checksum)

    def test_lock_entry_serialization(self):
        """LockEntry should serialize to/from dict."""
        from packaging import LockEntry

        entry = LockEntry(
            name="json",
            source="git+https://github.com/ritz-lang/json?rev=abc123",
            checksum="sha256:abc123",
            version="1.0.0"
        )

        data = entry.to_dict()
        restored = LockEntry.from_dict(data)

        self.assertEqual(entry.name, restored.name)
        self.assertEqual(entry.source, restored.source)
        self.assertEqual(entry.checksum, restored.checksum)

    def test_lock_file_write_and_read(self):
        """LockFile should write and read ritz.lock."""
        from packaging import LockFile, LockEntry

        lock_path = self.pkg_dir / "ritz.lock"

        entries = [
            LockEntry("json", "git+https://github.com/ritz-lang/json?rev=abc123",
                      "sha256:abc123def456", "1.0.0"),
            LockEntry("http", "path:../http",
                      "sha256:def456abc789", "2.0.0"),
        ]

        lock = LockFile(entries)
        lock.write(lock_path)

        self.assertTrue(lock_path.exists())

        # Read back
        restored = LockFile.read(lock_path)
        self.assertEqual(len(restored.entries), 2)
        self.assertEqual(restored.entries[0].name, "json")
        self.assertEqual(restored.entries[1].name, "http")

    def test_lock_file_format(self):
        """Lock file should be TOML format per RFC."""
        from packaging import LockFile, LockEntry

        lock_path = self.pkg_dir / "ritz.lock"
        entries = [
            LockEntry("json", "git+https://github.com/ritz-lang/json?rev=abc123",
                      "sha256:abc123", "1.0.0"),
        ]

        lock = LockFile(entries)
        lock.write(lock_path)

        content = lock_path.read_text()
        # Should contain TOML array header
        self.assertIn("[[package]]", content)
        self.assertIn('name = "json"', content)
        self.assertIn("source = ", content)
        self.assertIn("checksum = ", content)

    def test_generate_lock_from_dependencies(self):
        """Should generate lock entries from resolved dependencies."""
        from packaging import generate_lock_entries

        # Create a mock package with dependencies
        (self.pkg_dir / "ritz.toml").write_text('''
[package]
name = "myproject"
version = "1.0.0"

[dependencies]
mylib = { path = "../mylib" }
''')

        # Create the dependency
        dep_dir = Path(self.tmp_dir) / "mylib"
        dep_dir.mkdir()
        (dep_dir / "ritz.toml").write_text('''
[package]
name = "mylib"
version = "0.5.0"
''')
        (dep_dir / "lib.ritz").write_text("pub fn hello() -> i32\n    42\n")

        entries = generate_lock_entries(self.pkg_dir)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "mylib")
        self.assertIn("path:", entries[0].source)


class TestVendoring(unittest.TestCase):
    """Tests for ritz vendor command."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.pkg_dir = Path(self.tmp_dir) / "myproject"
        self.pkg_dir.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_vendor_creates_directory(self):
        """vendor_dependencies should create vendor/ directory."""
        from packaging import vendor_dependencies

        # Create a package with a path dependency
        (self.pkg_dir / "ritz.toml").write_text('''
[package]
name = "myproject"
version = "1.0.0"

[dependencies]
mylib = { path = "../mylib" }
''')

        # Create the dependency
        dep_dir = Path(self.tmp_dir) / "mylib"
        dep_dir.mkdir()
        (dep_dir / "ritz.toml").write_text('''
[package]
name = "mylib"
version = "0.5.0"
''')
        (dep_dir / "lib.ritz").write_text("pub fn hello() -> i32\n    42\n")

        vendor_dir = vendor_dependencies(self.pkg_dir)

        self.assertTrue(vendor_dir.exists())
        self.assertTrue((vendor_dir / "mylib").exists())
        self.assertTrue((vendor_dir / "mylib" / "ritz.toml").exists())
        self.assertTrue((vendor_dir / "mylib" / "lib.ritz").exists())

    def test_vendor_copies_source_files(self):
        """vendor should copy .ritz files and ritz.toml."""
        from packaging import vendor_dependencies

        # Create a package with nested sources
        (self.pkg_dir / "ritz.toml").write_text('''
[package]
name = "myproject"

[dependencies]
mylib = { path = "../mylib" }
''')

        # Create the dependency with nested structure
        dep_dir = Path(self.tmp_dir) / "mylib"
        dep_dir.mkdir()
        (dep_dir / "ritz.toml").write_text('[package]\nname = "mylib"')
        (dep_dir / "src").mkdir()
        (dep_dir / "src" / "lib.ritz").write_text("fn lib_fn() -> i32\n    1\n")
        (dep_dir / "src" / "util.ritz").write_text("fn util_fn() -> i32\n    2\n")

        vendor_dir = vendor_dependencies(self.pkg_dir)

        # Check nested files are copied
        self.assertTrue((vendor_dir / "mylib" / "src" / "lib.ritz").exists())
        self.assertTrue((vendor_dir / "mylib" / "src" / "util.ritz").exists())

    def test_vendor_excludes_build_artifacts(self):
        """vendor should not copy build/, .ritz-cache/, vendor/ dirs."""
        from packaging import vendor_dependencies

        (self.pkg_dir / "ritz.toml").write_text('''
[package]
name = "myproject"

[dependencies]
mylib = { path = "../mylib" }
''')

        # Create dependency with build artifacts
        dep_dir = Path(self.tmp_dir) / "mylib"
        dep_dir.mkdir()
        (dep_dir / "ritz.toml").write_text('[package]\nname = "mylib"')
        (dep_dir / "lib.ritz").write_text("fn f() -> i32\n    1\n")

        # Create directories that should be excluded
        (dep_dir / "build").mkdir()
        (dep_dir / "build" / "debug").mkdir()
        (dep_dir / "build" / "debug" / "mylib").write_bytes(b"binary data")
        (dep_dir / ".ritz-cache").mkdir()
        (dep_dir / ".ritz-cache" / "cache.json").write_text("{}")

        vendor_dir = vendor_dependencies(self.pkg_dir)

        # Excluded dirs should not exist
        self.assertFalse((vendor_dir / "mylib" / "build").exists())
        self.assertFalse((vendor_dir / "mylib" / ".ritz-cache").exists())

        # But source files should
        self.assertTrue((vendor_dir / "mylib" / "lib.ritz").exists())

    def test_vendor_transitive_dependencies(self):
        """vendor should include transitive dependencies."""
        from packaging import vendor_dependencies

        # Create main package
        (self.pkg_dir / "ritz.toml").write_text('''
[package]
name = "myproject"

[dependencies]
liba = { path = "../liba" }
''')

        # Create liba which depends on libb
        liba_dir = Path(self.tmp_dir) / "liba"
        liba_dir.mkdir()
        (liba_dir / "ritz.toml").write_text('''
[package]
name = "liba"

[dependencies]
libb = { path = "../libb" }
''')
        (liba_dir / "a.ritz").write_text("fn a() -> i32\n    1\n")

        # Create libb (leaf)
        libb_dir = Path(self.tmp_dir) / "libb"
        libb_dir.mkdir()
        (libb_dir / "ritz.toml").write_text('[package]\nname = "libb"')
        (libb_dir / "b.ritz").write_text("fn b() -> i32\n    2\n")

        vendor_dir = vendor_dependencies(self.pkg_dir)

        # Both deps should be vendored
        self.assertTrue((vendor_dir / "liba").exists())
        self.assertTrue((vendor_dir / "libb").exists())
        self.assertTrue((vendor_dir / "liba" / "a.ritz").exists())
        self.assertTrue((vendor_dir / "libb" / "b.ritz").exists())


if __name__ == "__main__":
    unittest.main()
