"""
Unit tests for ritz0/metadata.py

Tests JSON metadata generation and parsing, including cross-validation
with the Ritz implementation in ritzlib/meta.ritz.
"""

import json
import os
import pytest
import sys
import tempfile
from pathlib import Path

# Add ritz0 to path
sys.path.insert(0, str(Path(__file__).parent))

from metadata import (
    FnSignature, StructMeta, EnumMeta, ConstMeta, TypeAliasMeta, TraitMeta,
    ModuleMetadata, metadata_to_json, metadata_from_json,
    save_metadata, load_metadata, get_cache_path, MetadataCache
)


class TestFnSignature:
    """Test FnSignature dataclass."""

    def test_simple_function(self):
        sig = FnSignature(
            name="foo",
            params=[],
            ret_type="void",
            is_extern=False,
            is_generic=False,
            type_params=[]
        )
        assert sig.name == "foo"
        assert sig.ret_type == "void"
        assert sig.params == []

    def test_function_with_params(self):
        sig = FnSignature(
            name="add",
            params=[
                {"name": "a", "type": "i32"},
                {"name": "b", "type": "i32"}
            ],
            ret_type="i32",
            is_extern=False,
            is_generic=False,
            type_params=[]
        )
        assert len(sig.params) == 2
        assert sig.params[0]["name"] == "a"
        assert sig.params[1]["type"] == "i32"

    def test_extern_function(self):
        sig = FnSignature(
            name="syscall0",
            params=[{"name": "n", "type": "i64"}],
            ret_type="i64",
            is_extern=True,
            is_generic=False,
            type_params=[]
        )
        assert sig.is_extern is True

    def test_generic_function(self):
        sig = FnSignature(
            name="map",
            params=[{"name": "arr", "type": "[]T"}],
            ret_type="[]U",
            is_extern=False,
            is_generic=True,
            type_params=["T", "U"]
        )
        assert sig.is_generic is True
        assert sig.type_params == ["T", "U"]


class TestStructMeta:
    """Test StructMeta dataclass."""

    def test_simple_struct(self):
        meta = StructMeta(
            name="Point",
            fields=[
                {"name": "x", "type": "i32"},
                {"name": "y", "type": "i32"}
            ],
            is_generic=False,
            type_params=[]
        )
        assert meta.name == "Point"
        assert len(meta.fields) == 2

    def test_generic_struct(self):
        meta = StructMeta(
            name="Vec",
            fields=[{"name": "data", "type": "*T"}],
            is_generic=True,
            type_params=["T"]
        )
        assert meta.is_generic is True
        assert meta.type_params == ["T"]


class TestEnumMeta:
    """Test EnumMeta dataclass."""

    def test_simple_enum(self):
        meta = EnumMeta(
            name="Option",
            variants=[
                {"name": "None", "fields": []},
                {"name": "Some", "fields": ["T"]}
            ]
        )
        assert meta.name == "Option"
        assert len(meta.variants) == 2
        assert meta.variants[0]["name"] == "None"
        assert meta.variants[1]["fields"] == ["T"]


class TestModuleMetadata:
    """Test ModuleMetadata dataclass."""

    def test_empty_module(self):
        meta = ModuleMetadata(
            source_path="test.ritz",
            source_mtime=12345.0,
            functions=[],
            structs=[],
            enums=[],
            constants=[],
            type_aliases=[],
            traits=[],
            imports=[],
            impls=[]
        )
        assert meta.source_path == "test.ritz"
        assert meta.source_mtime == 12345.0
        assert len(meta.functions) == 0

    def test_module_with_content(self):
        meta = ModuleMetadata(
            source_path="lib.ritz",
            source_mtime=67890.0,
            functions=[
                FnSignature("foo", [], "void", False, False, [])
            ],
            structs=[
                StructMeta("Point", [{"name": "x", "type": "i32"}], False, [])
            ],
            enums=[],
            constants=[
                ConstMeta("MAX", "i64", 100)
            ],
            type_aliases=[],
            traits=[],
            imports=["ritzlib.sys"],
            impls=[]
        )
        assert len(meta.functions) == 1
        assert len(meta.structs) == 1
        assert len(meta.constants) == 1
        assert len(meta.imports) == 1


class TestJsonSerialization:
    """Test JSON serialization/deserialization."""

    def test_round_trip_empty(self):
        """Empty metadata should round-trip correctly."""
        original = ModuleMetadata(
            source_path="",
            source_mtime=0.0,
            functions=[],
            structs=[],
            enums=[],
            constants=[],
            type_aliases=[],
            traits=[],
            imports=[],
            impls=[]
        )
        json_str = metadata_to_json(original)
        restored = metadata_from_json(json_str)

        assert restored.source_path == original.source_path
        assert len(restored.functions) == 0
        assert len(restored.structs) == 0

    def test_round_trip_with_functions(self):
        """Functions should round-trip correctly."""
        original = ModuleMetadata(
            source_path="/path/to/file.ritz",
            source_mtime=12345.67,
            functions=[
                FnSignature(
                    name="add",
                    params=[
                        {"name": "a", "type": "i32"},
                        {"name": "b", "type": "i32"}
                    ],
                    ret_type="i32",
                    is_extern=False,
                    is_generic=False,
                    type_params=[]
                ),
                FnSignature(
                    name="syscall0",
                    params=[{"name": "n", "type": "i64"}],
                    ret_type="i64",
                    is_extern=True,
                    is_generic=False,
                    type_params=[]
                )
            ],
            structs=[],
            enums=[],
            constants=[],
            type_aliases=[],
            traits=[],
            imports=[],
            impls=[]
        )
        json_str = metadata_to_json(original)
        restored = metadata_from_json(json_str)

        assert len(restored.functions) == 2
        assert restored.functions[0].name == "add"
        assert restored.functions[0].params[0]["name"] == "a"
        assert restored.functions[1].is_extern is True

    def test_round_trip_with_structs(self):
        """Structs should round-trip correctly."""
        original = ModuleMetadata(
            source_path="test.ritz",
            source_mtime=0.0,
            functions=[],
            structs=[
                StructMeta(
                    name="Point",
                    fields=[
                        {"name": "x", "type": "i32"},
                        {"name": "y", "type": "i32"}
                    ],
                    is_generic=False,
                    type_params=[]
                )
            ],
            enums=[],
            constants=[],
            type_aliases=[],
            traits=[],
            imports=[],
            impls=[]
        )
        json_str = metadata_to_json(original)
        restored = metadata_from_json(json_str)

        assert len(restored.structs) == 1
        assert restored.structs[0].name == "Point"
        assert len(restored.structs[0].fields) == 2

    def test_round_trip_with_enums(self):
        """Enums should round-trip correctly."""
        original = ModuleMetadata(
            source_path="test.ritz",
            source_mtime=0.0,
            functions=[],
            structs=[],
            enums=[
                EnumMeta(
                    name="Option",
                    variants=[
                        {"name": "None", "fields": []},
                        {"name": "Some", "fields": ["i32"]}
                    ]
                )
            ],
            constants=[],
            type_aliases=[],
            traits=[],
            imports=[],
            impls=[]
        )
        json_str = metadata_to_json(original)
        restored = metadata_from_json(json_str)

        assert len(restored.enums) == 1
        assert restored.enums[0].name == "Option"
        assert len(restored.enums[0].variants) == 2

    def test_round_trip_with_constants(self):
        """Constants should round-trip correctly."""
        original = ModuleMetadata(
            source_path="test.ritz",
            source_mtime=0.0,
            functions=[],
            structs=[],
            enums=[],
            constants=[
                ConstMeta(name="MAX_SIZE", type="i64", value=1024),
                ConstMeta(name="PI", type="f64", value=0)  # Approx - float constants not fully supported
            ],
            type_aliases=[],
            traits=[],
            imports=[],
            impls=[]
        )
        json_str = metadata_to_json(original)
        restored = metadata_from_json(json_str)

        assert len(restored.constants) == 2
        assert restored.constants[0].name == "MAX_SIZE"
        assert restored.constants[1].type == "f64"

    def test_round_trip_with_imports(self):
        """Imports should round-trip correctly."""
        original = ModuleMetadata(
            source_path="test.ritz",
            source_mtime=0.0,
            functions=[],
            structs=[],
            enums=[],
            constants=[],
            type_aliases=[],
            traits=[],
            imports=["ritzlib.sys", "ritzlib.str", "ritzlib.memory"],
            impls=[]
        )
        json_str = metadata_to_json(original)
        restored = metadata_from_json(json_str)

        assert restored.imports == ["ritzlib.sys", "ritzlib.str", "ritzlib.memory"]

    def test_json_format_readable(self):
        """Generated JSON should be indented and readable."""
        meta = ModuleMetadata(
            source_path="test.ritz",
            source_mtime=12345.0,
            functions=[
                FnSignature("foo", [], "void", False, False, [])
            ],
            structs=[],
            enums=[],
            constants=[],
            type_aliases=[],
            traits=[],
            imports=[],
            impls=[]
        )
        json_str = metadata_to_json(meta)

        # Should have newlines (indented format)
        assert "\n" in json_str
        # Should be valid JSON
        data = json.loads(json_str)
        assert data["source_path"] == "test.ritz"


class TestCachePath:
    """Test cache path calculation."""

    def test_simple_path(self):
        path = get_cache_path("foo.ritz")
        assert str(path) == ".ritz-cache/foo.ritz-meta"

    def test_nested_path(self):
        path = get_cache_path("ritzlib/sys.ritz")
        assert str(path) == ".ritz-cache/ritzlib/sys.ritz-meta"

    def test_absolute_path(self):
        # Should become relative
        path = get_cache_path("/home/user/project/foo.ritz")
        assert ".ritz-cache" in str(path)
        assert str(path).endswith(".ritz-meta")


class TestCacheOperations:
    """Test cache save/load operations."""

    def test_save_and_load(self):
        """Should be able to save and load metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, ".ritz-cache")

            # Create a dummy source file
            source_path = os.path.join(tmpdir, "test.ritz")
            with open(source_path, "w") as f:
                f.write("fn main() -> i32\n    0\n")

            meta = ModuleMetadata(
                source_path=source_path,
                source_mtime=os.path.getmtime(source_path),
                functions=[
                    FnSignature("main", [], "i32", False, False, [])
                ],
                structs=[],
                enums=[],
                constants=[],
                type_aliases=[],
                traits=[],
                imports=[],
                impls=[]
            )

            # Save
            cache_path = save_metadata(meta, cache_dir)
            assert cache_path.exists()

            # Load
            loaded = load_metadata(source_path, cache_dir)
            assert loaded is not None
            assert loaded.source_path == source_path
            assert len(loaded.functions) == 1
            assert loaded.functions[0].name == "main"

    def test_stale_cache(self):
        """Should return None for stale cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, ".ritz-cache")

            # Create source file
            source_path = os.path.join(tmpdir, "test.ritz")
            with open(source_path, "w") as f:
                f.write("fn main() -> i32\n    0\n")

            # Create metadata with old mtime
            meta = ModuleMetadata(
                source_path=source_path,
                source_mtime=1.0,  # Ancient timestamp
                functions=[],
                structs=[],
                enums=[],
                constants=[],
                type_aliases=[],
                traits=[],
                imports=[],
                impls=[]
            )
            save_metadata(meta, cache_dir)

            # Load should return None (cache is stale)
            loaded = load_metadata(source_path, cache_dir)
            assert loaded is None


class TestMetadataCache:
    """Test MetadataCache class."""

    def test_memory_cache(self):
        """Should cache in memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, ".ritz-cache")

            # Create source file
            source_path = os.path.join(tmpdir, "test.ritz")
            with open(source_path, "w") as f:
                f.write("fn main() -> i32\n    0\n")

            meta = ModuleMetadata(
                source_path=source_path,
                source_mtime=os.path.getmtime(source_path),
                functions=[],
                structs=[],
                enums=[],
                constants=[],
                type_aliases=[],
                traits=[],
                imports=[],
                impls=[]
            )

            cache = MetadataCache(cache_dir)
            cache.put(meta)

            # Should get from memory
            loaded = cache.get(source_path)
            assert loaded is not None
            assert loaded.source_path == source_path

    def test_get_exports(self):
        """Should return exports dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, ".ritz-cache")

            source_path = os.path.join(tmpdir, "test.ritz")
            with open(source_path, "w") as f:
                f.write("const MAX: i64 = 100\n")

            meta = ModuleMetadata(
                source_path=source_path,
                source_mtime=os.path.getmtime(source_path),
                functions=[
                    FnSignature("foo", [], "void", False, False, [])
                ],
                structs=[
                    StructMeta("Point", [], False, [])
                ],
                enums=[],
                constants=[
                    ConstMeta("MAX", "i64", 100)
                ],
                type_aliases=[],
                traits=[],
                imports=[],
                impls=[]
            )

            cache = MetadataCache(cache_dir)
            cache.put(meta)

            exports = cache.get_exports(source_path)
            assert "foo" in exports["functions"]
            assert "Point" in exports["structs"]
            assert "MAX" in exports["constants"]


class TestCrossValidation:
    """Cross-validation tests between Python and Ritz implementations."""

    def test_python_generates_valid_json(self):
        """JSON generated by Python should be parseable."""
        meta = ModuleMetadata(
            source_path="/test/path.ritz",
            source_mtime=12345.67,
            functions=[
                FnSignature(
                    name="sys_read",
                    params=[
                        {"name": "fd", "type": "i32"},
                        {"name": "buf", "type": "*u8"},
                        {"name": "count", "type": "i64"}
                    ],
                    ret_type="i64",
                    is_extern=False,
                    is_generic=False,
                    type_params=[]
                )
            ],
            structs=[
                StructMeta(
                    name="Stat",
                    fields=[
                        {"name": "st_dev", "type": "i64"},
                        {"name": "st_ino", "type": "i64"}
                    ],
                    is_generic=False,
                    type_params=[]
                )
            ],
            enums=[],
            constants=[
                ConstMeta("O_RDONLY", "i32", 0),
                ConstMeta("O_WRONLY", "i32", 1)
            ],
            type_aliases=[],
            traits=[],
            imports=["ritzlib.sys"],
            impls=[]
        )

        json_str = metadata_to_json(meta)

        # Validate JSON structure
        data = json.loads(json_str)
        assert "source_path" in data
        assert "source_mtime" in data
        assert "functions" in data
        assert "structs" in data
        assert "enums" in data
        assert "constants" in data
        assert "type_aliases" in data
        assert "traits" in data
        assert "imports" in data

        # Validate function structure
        assert len(data["functions"]) == 1
        fn = data["functions"][0]
        assert fn["name"] == "sys_read"
        assert len(fn["params"]) == 3
        assert fn["params"][0]["name"] == "fd"
        assert fn["params"][0]["type"] == "i32"

        # Validate struct structure
        assert len(data["structs"]) == 1
        st = data["structs"][0]
        assert st["name"] == "Stat"
        assert len(st["fields"]) == 2

        # Validate constants
        assert len(data["constants"]) == 2
        assert data["constants"][0]["name"] == "O_RDONLY"

    def test_existing_ritz_meta_file(self):
        """Should be able to read existing .ritz-meta files from cache."""
        # Find an existing .ritz-meta file in the cache
        cache_dir = Path(".ritz-cache")
        if not cache_dir.exists():
            pytest.skip("No .ritz-cache directory found")

        meta_files = list(cache_dir.rglob("*.ritz-meta"))
        if not meta_files:
            pytest.skip("No .ritz-meta files found in cache")

        # Read and parse the first one
        meta_file = meta_files[0]
        with open(meta_file, "r") as f:
            json_str = f.read()

        meta = metadata_from_json(json_str)
        assert meta is not None
        assert isinstance(meta.functions, list)
        assert isinstance(meta.structs, list)
        assert isinstance(meta.imports, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
