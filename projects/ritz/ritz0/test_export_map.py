"""
Tests for Phase 2B: Export Map Building

Tests that modules correctly track public vs private items
and build proper export maps.
"""

import pytest
from pathlib import Path
import tempfile
import ritz_ast as rast
from lexer import Lexer
from parser import Parser
from import_resolver import ImportResolver, ExportEntry, ModuleExports, resolve_imports


def parse_module(code: str, filename: str = "test.ritz") -> rast.Module:
    """Parse code into a module AST."""
    lexer = Lexer(code, filename)
    tokens = lexer.tokenize()
    parser = Parser(tokens)
    return parser.parse_module()


class TestExportMapBuilding:
    """Test export map building for modules."""

    def test_build_export_map_public_items(self):
        """Test that export map only includes public items."""
        code = '''
pub fn public_fn()
    prints("public")

fn private_fn()
    prints("private")

pub struct PublicStruct
    x: i32
    y: i32

struct PrivateStruct
    a: i32

pub const PUBLIC_CONST: i32 = 42
const PRIVATE_CONST: i32 = 99
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Should have 3 exports: public_fn, PublicStruct, PUBLIC_CONST
        assert len(exports.exports) == 3
        assert exports.has_export("public_fn")
        assert exports.has_export("PublicStruct")
        assert exports.has_export("PUBLIC_CONST")

        # Should NOT have private items
        assert not exports.has_export("private_fn")
        assert not exports.has_export("PrivateStruct")
        assert not exports.has_export("PRIVATE_CONST")

    def test_export_entry_kinds(self):
        """Test that export entries have correct kinds."""
        code = '''
pub fn my_func()
    prints("test")

pub struct MyStruct
    value: i32

pub enum MyEnum
    A
    B

pub const MY_CONST: i32 = 42
pub var my_var: i32 = 0
pub type MyAlias = i32
pub trait MyTrait
    fn method()
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Check kinds
        assert exports.get_export("my_func").kind == "fn"
        assert exports.get_export("MyStruct").kind == "struct"
        assert exports.get_export("MyEnum").kind == "enum"
        assert exports.get_export("MY_CONST").kind == "const"
        assert exports.get_export("my_var").kind == "var"
        assert exports.get_export("MyAlias").kind == "type_alias"
        assert exports.get_export("MyTrait").kind == "trait"

    def test_export_entry_metadata(self):
        """Test that export entries have correct metadata."""
        code = '''pub fn test_fn()
    prints("test")'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "/path/to/test.ritz")

        entry = exports.get_export("test_fn")
        assert entry.name == "test_fn"
        assert entry.kind == "fn"
        assert entry.module_path == "/path/to/test.ritz"
        assert entry.is_pub == True
        assert entry.is_reexport == False
        assert entry.original_module == "/path/to/test.ritz"

    def test_skip_impl_blocks(self):
        """Test that impl blocks are not exported at module level."""
        code = '''
pub struct MyStruct
    x: i32

impl MyStruct
    fn method()
        prints("method")
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Should only have the struct, not impl block
        assert len(exports.exports) == 1
        assert exports.has_export("MyStruct")

    def test_skip_imports(self):
        """Test that imports are not in the export map."""
        code = '''
import ritzlib.sys

pub fn my_fn()
    prints("test")
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Should only have the function
        assert len(exports.exports) == 1
        assert exports.has_export("my_fn")

    def test_all_items_private(self):
        """Test module with all private items."""
        code = '''
fn fn1()
    prints("1")

fn fn2()
    prints("2")

struct MyStruct
    x: i32
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Should have no exports
        assert len(exports.exports) == 0

    def test_empty_module(self):
        """Test empty module."""
        code = ''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        assert len(exports.exports) == 0

    def test_export_entry_repr(self):
        """Test ExportEntry string representation."""
        entry = ExportEntry(
            name="test_fn",
            kind="fn",
            module_path="/path/to/module.ritz",
            is_pub=True,
            is_reexport=False,
            original_module="/path/to/module.ritz"
        )
        repr_str = repr(entry)
        assert "test_fn" in repr_str
        assert "fn" in repr_str
        assert "pub=True" in repr_str

    def test_module_exports_repr(self):
        """Test ModuleExports string representation."""
        exports = ModuleExports("/path/to/module.ritz")
        entry = ExportEntry(
            name="test_fn",
            kind="fn",
            module_path="/path/to/module.ritz",
            is_pub=True
        )
        exports.add_export(entry)
        repr_str = repr(exports)
        assert "/path/to/module.ritz" in repr_str
        assert "1 exports" in repr_str

    def test_extern_fn_export(self):
        """Test that extern functions can be exported."""
        code = '''
pub extern fn c_function(x: i32) -> i32

extern fn private_c_func(x: i32) -> i32
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Should have c_function but not private_c_func
        assert exports.has_export("c_function")
        assert exports.get_export("c_function").kind == "extern_fn"
        assert not exports.has_export("private_c_func")


class TestValidateSelectiveImport:
    """Test selective import validation."""

    def test_validate_selective_import_all_exist(self):
        """Test validation when all requested items exist."""
        code = '''
pub fn fn1()
    prints("1")

pub fn fn2()
    prints("2")

pub struct MyStruct
    x: i32
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Create import node requesting these items
        import_node = rast.Import(
            span=rast.Span("test.ritz", 0, 0, 0),
            path=["ritzlib", "test"],
            items=["fn1", "MyStruct"]  # Selective import
        )

        # Should not raise
        result = resolver._validate_selective_import(import_node, exports)
        assert len(result) == 2
        assert "fn1" in result
        assert "MyStruct" in result

    def test_validate_selective_import_missing_item(self):
        """Test validation when requested item doesn't exist."""
        code = '''
pub fn fn1()
    prints("1")

pub fn fn2()
    prints("2")
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Try to import non-existent item
        import_node = rast.Import(
            span=rast.Span("test.ritz", 0, 0, 0),
            path=["ritzlib", "test"],
            items=["fn1", "nonexistent"]
        )

        # Should raise ImportError
        with pytest.raises(Exception) as exc_info:
            resolver._validate_selective_import(import_node, exports)
        assert "nonexistent" in str(exc_info.value)
        assert "not exported" in str(exc_info.value)

    def test_validate_non_selective_import(self):
        """Test that non-selective imports return all exports."""
        code = '''
pub fn fn1()
    prints("1")

pub fn fn2()
    prints("2")
'''
        module = parse_module(code)
        resolver = ImportResolver()
        exports = resolver._build_export_map(module, "test.ritz")

        # Import without items list
        import_node = rast.Import(
            span=rast.Span("test.ritz", 0, 0, 0),
            path=["ritzlib", "test"]
        )

        # Should return all exports
        result = resolver._validate_selective_import(import_node, exports)
        assert len(result) == 2
        assert "fn1" in result
        assert "fn2" in result


class TestImportAliasRegistration:
    """Test import alias registration and qualified name resolution."""

    def test_register_import_alias(self):
        """Test registering an import alias."""
        resolver = ImportResolver()
        resolver._register_import_alias("sys", "/path/to/ritzlib/sys.ritz", "main.ritz")

        # Verify it's registered
        assert "main.ritz" in resolver.import_aliases
        assert resolver.import_aliases["main.ritz"]["sys"] == "/path/to/ritzlib/sys.ritz"

    def test_resolve_qualified_name_found(self):
        """Test resolving a qualified name that exists."""
        resolver = ImportResolver()

        # Set up exports for a module
        module_exports = ModuleExports("/path/to/module.ritz")
        entry = ExportEntry(
            name="my_fn",
            kind="fn",
            module_path="/path/to/module.ritz",
            is_pub=True
        )
        module_exports.add_export(entry)
        resolver.module_exports["/path/to/module.ritz"] = module_exports

        # Register alias
        resolver._register_import_alias("mod", "/path/to/module.ritz", "main.ritz")

        # Resolve qualified name
        result = resolver.resolve_qualified_name("mod", "my_fn", "main.ritz")
        assert result is not None
        assert result.name == "my_fn"

    def test_resolve_qualified_name_not_found(self):
        """Test resolving a qualified name that doesn't exist."""
        resolver = ImportResolver()

        # Set up exports (empty)
        module_exports = ModuleExports("/path/to/module.ritz")
        resolver.module_exports["/path/to/module.ritz"] = module_exports

        # Register alias
        resolver._register_import_alias("mod", "/path/to/module.ritz", "main.ritz")

        # Try to resolve non-existent name
        result = resolver.resolve_qualified_name("mod", "nonexistent", "main.ritz")
        assert result is None

    def test_resolve_unregistered_qualifier(self):
        """Test resolving with unregistered qualifier."""
        resolver = ImportResolver()

        # Try to resolve without registering
        result = resolver.resolve_qualified_name("unknown", "fn", "main.ritz")
        assert result is None


class TestReExportHandling:
    """Test re-export handling with pub import (Phase 2C)."""

    def test_process_re_exports_basic(self):
        """Test basic re-export of public items."""
        # Module A: defines public items
        module_a_code = '''
pub fn public_fn()
    prints("public")

fn private_fn()
    prints("private")

pub struct PublicStruct
    x: i32
'''
        # Module B: re-exports items from A
        module_b_code = '''
pub import module_a
'''

        # Parse modules
        module_a = parse_module(module_a_code, "module_a.ritz")
        module_b = parse_module(module_b_code, "module_b.ritz")

        # Build resolver with export maps
        resolver = ImportResolver()

        # Build export map for A
        exports_a = resolver._build_export_map(module_a, "module_a.ritz")
        resolver.module_exports["module_a.ritz"] = exports_a

        # Simulate import path resolution for module_a
        def mock_resolve_import_path(path_parts, from_file):
            if path_parts == ["module_a"]:
                return "module_a.ritz"
            return None

        resolver._resolve_import_path = mock_resolve_import_path

        # Build export map for B
        exports_b = resolver._build_export_map(module_b, "module_b.ritz")

        # Process re-exports from B
        resolver._process_re_exports(module_b, "module_b.ritz", exports_b)

        # B should now have the re-exported items
        assert exports_b.has_export("public_fn")
        assert exports_b.has_export("PublicStruct")
        assert not exports_b.has_export("private_fn")

        # Check that re-exports are marked correctly
        fn_entry = exports_b.get_export("public_fn")
        assert fn_entry.is_reexport == True
        assert fn_entry.original_module == "module_a.ritz"
        assert fn_entry.module_path == "module_b.ritz"

    def test_process_re_exports_selective(self):
        """Test selective re-export with pub import { items }."""
        # Module A: defines multiple public items
        module_a_code = '''
pub fn fn1()
    prints("1")

pub fn fn2()
    prints("2")

pub struct MyStruct
    x: i32
'''
        # Module B: selectively re-exports
        module_b_code = '''
pub import module_a { fn1, MyStruct }
'''

        module_a = parse_module(module_a_code, "module_a.ritz")
        module_b = parse_module(module_b_code, "module_b.ritz")

        resolver = ImportResolver()

        # Build export maps
        exports_a = resolver._build_export_map(module_a, "module_a.ritz")
        resolver.module_exports["module_a.ritz"] = exports_a

        def mock_resolve_import_path(path_parts, from_file):
            if path_parts == ["module_a"]:
                return "module_a.ritz"
            return None

        resolver._resolve_import_path = mock_resolve_import_path

        exports_b = resolver._build_export_map(module_b, "module_b.ritz")
        resolver._process_re_exports(module_b, "module_b.ritz", exports_b)

        # B should only have fn1 and MyStruct
        assert exports_b.has_export("fn1")
        assert exports_b.has_export("MyStruct")
        assert not exports_b.has_export("fn2")

    def test_process_re_exports_with_alias(self):
        """Test re-export with module alias."""
        # Module A: defines public items
        module_a_code = '''
pub fn test_fn()
    prints("test")
'''
        # Module B: re-exports with alias
        module_b_code = '''
pub import module_a as mod_a
'''

        module_a = parse_module(module_a_code, "module_a.ritz")
        module_b = parse_module(module_b_code, "module_b.ritz")

        resolver = ImportResolver()

        # Build export maps
        exports_a = resolver._build_export_map(module_a, "module_a.ritz")
        resolver.module_exports["module_a.ritz"] = exports_a

        def mock_resolve_import_path(path_parts, from_file):
            if path_parts == ["module_a"]:
                return "module_a.ritz"
            return None

        resolver._resolve_import_path = mock_resolve_import_path

        exports_b = resolver._build_export_map(module_b, "module_b.ritz")
        resolver._process_re_exports(module_b, "module_b.ritz", exports_b)

        # B should have the re-exported function
        assert exports_b.has_export("test_fn")
        entry = exports_b.get_export("test_fn")
        assert entry.is_reexport == True

    def test_process_re_exports_chain(self):
        """Test re-export chains: A -> B -> C."""
        # Module A: defines public items
        module_a_code = '''
pub fn original_fn()
    prints("original")
'''
        # Module B: re-exports from A
        module_b_code = '''
pub import module_a
'''
        # Module C: re-exports from B (which are themselves re-exports from A)
        module_c_code = '''
pub import module_b
'''

        module_a = parse_module(module_a_code, "module_a.ritz")
        module_b = parse_module(module_b_code, "module_b.ritz")
        module_c = parse_module(module_c_code, "module_c.ritz")

        resolver = ImportResolver()

        # Build export maps in order
        exports_a = resolver._build_export_map(module_a, "module_a.ritz")
        resolver.module_exports["module_a.ritz"] = exports_a

        def mock_resolve_import_path(path_parts, from_file):
            if path_parts == ["module_a"]:
                return "module_a.ritz"
            elif path_parts == ["module_b"]:
                return "module_b.ritz"
            return None

        resolver._resolve_import_path = mock_resolve_import_path

        # B re-exports A's items
        exports_b = resolver._build_export_map(module_b, "module_b.ritz")
        resolver.module_exports["module_b.ritz"] = exports_b
        resolver._process_re_exports(module_b, "module_b.ritz", exports_b)

        # C re-exports B's items
        exports_c = resolver._build_export_map(module_c, "module_c.ritz")
        resolver._process_re_exports(module_c, "module_c.ritz", exports_c)

        # C should have the original function
        assert exports_c.has_export("original_fn")
        entry = exports_c.get_export("original_fn")
        # The re-export is marked at C level, but original_module traces back to A
        assert entry.is_reexport == True
        assert entry.module_path == "module_c.ritz"
        assert entry.original_module == "module_a.ritz"

    def test_re_export_missing_module(self):
        """Test re-export when imported module is not in export map yet."""
        module_code = '''
pub import nonexistent
'''
        module = parse_module(module_code, "test.ritz")
        resolver = ImportResolver()

        def mock_resolve_import_path(path_parts, from_file):
            return None  # Can't resolve

        resolver._resolve_import_path = mock_resolve_import_path

        exports = resolver._build_export_map(module, "test.ritz")
        # Should not crash, just skip re-exports for missing modules
        resolver._process_re_exports(module, "test.ritz", exports)
        assert len(exports.exports) == 0



class TestAliasedImportRewrites:
    """Behavior tests for alias-qualified import rewrites."""

    def test_alias_import_without_items_exposes_all_qualified(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "mod.ritz").write_text("""
pub fn foo() -> i32
    1

pub fn bar() -> i32
    2
""")
            main = parse_module("""
import mod as m

fn call_foo() -> i32
    m::foo()

fn call_bar() -> i32
    m::bar()
""", str(root / "main.ritz"))

            merged = resolve_imports(main, str(root / "main.ritz"), project_root=str(root), use_cache=False)
            fn_names = {item.name for item in merged.items if isinstance(item, rast.FnDef)}

            assert "__imp_m_foo" in fn_names
            assert "__imp_m_bar" in fn_names

    def test_selective_alias_only_allows_selected_names(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "mod.ritz").write_text("""
pub fn foo() -> i32
    1

pub fn bar() -> i32
    2
""")
            main = parse_module("""
import mod { foo } as m

fn call_foo() -> i32
    m::foo()

fn call_bar() -> i32
    m::bar()
""", str(root / "main.ritz"))

            with pytest.raises(Exception) as exc:
                resolve_imports(main, str(root / "main.ritz"), project_root=str(root), use_cache=False)

            assert "not exported by aliased module 'm'" in str(exc.value)

    def test_two_aliases_can_call_same_export_name(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.ritz").write_text("""
pub fn init() -> i32
    10
""")
            (root / "b.ritz").write_text("""
pub fn init() -> i32
    20
""")
            main = parse_module("""
import a as aa
import b as bb

fn main() -> i32
    aa::init() + bb::init()
""", str(root / "main.ritz"))

            merged = resolve_imports(main, str(root / "main.ritz"), project_root=str(root), use_cache=False)
            fn_names = {item.name for item in merged.items if isinstance(item, rast.FnDef)}

            assert "__imp_aa_init" in fn_names
            assert "__imp_bb_init" in fn_names
            assert "main" in fn_names

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
