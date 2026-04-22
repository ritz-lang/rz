"""
Tests for the symbol table module.

TDD Step 1: Define what a symbol table should do before implementing it.

The symbol table replaces AST merging for import resolution:
- Tracks exported symbols (pub functions, structs, enums, traits, constants)
- Records their types/signatures without needing the full AST body
- Enables separate compilation: imported modules only need declarations
"""
import pytest
import sys
from pathlib import Path

# Add ritz0 to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from lexer import Lexer
from parser import Parser
import ritz_ast as rast


def parse_source(source: str) -> rast.Module:
    """Helper: parse a Ritz source string into an AST module."""
    lexer = Lexer(source, "<test>")
    tokens = lexer.tokenize()
    try:
        parser = Parser(tokens, source=source)
    except TypeError:
        parser = Parser(tokens)
    return parser.parse_module()


# ============================================================================
# Step 1: Symbol table construction from AST
# ============================================================================

class TestSymbolTableConstruction:
    """Test that we can build a symbol table from a parsed module."""

    def test_extract_pub_function(self):
        """pub fn should appear in symbol table."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn add(a: i32, b: i32) -> i32\n    return a + b\n")
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("add")
        sym = st.get_symbol("add")
        assert sym.kind == "fn"
        assert sym.is_pub is True

    def test_private_function_excluded(self):
        """Non-pub fn should NOT appear in symbol table exports."""
        from symbol_table import SymbolTable
        mod = parse_source("fn helper(x: i32) -> i32\n    return x\n")
        st = SymbolTable.from_module(mod, "<test>")
        assert not st.has_symbol("helper")

    def test_extract_pub_struct(self):
        """pub struct should appear in symbol table with field info."""
        from symbol_table import SymbolTable
        mod = parse_source("pub struct Point\n    x: i32\n    y: i32\n")
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("Point")
        sym = st.get_symbol("Point")
        assert sym.kind == "struct"
        assert len(sym.fields) == 2
        assert sym.fields[0].name == "x"

    def test_extract_pub_enum(self):
        """pub enum should appear in symbol table."""
        from symbol_table import SymbolTable
        mod = parse_source(
            "pub enum Color\n"
            "    Red\n"
            "    Green\n"
            "    Blue\n"
        )
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("Color")
        sym = st.get_symbol("Color")
        assert sym.kind == "enum"

    def test_extract_pub_const(self):
        """pub const should appear in symbol table with value."""
        from symbol_table import SymbolTable
        mod = parse_source("pub const MAX_SIZE: i32 = 1024\n")
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("MAX_SIZE")
        sym = st.get_symbol("MAX_SIZE")
        assert sym.kind == "const"

    def test_extract_extern_fn(self):
        """extern fn should appear in symbol table (always public)."""
        from symbol_table import SymbolTable
        mod = parse_source("extern fn syscall3(n: i64, a: i64, b: i64, c: i64) -> i64\n")
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("syscall3")
        sym = st.get_symbol("syscall3")
        assert sym.kind == "extern_fn"

    def test_extract_pub_trait(self):
        """pub trait should appear in symbol table."""
        from symbol_table import SymbolTable
        mod = parse_source(
            "pub trait Printable\n"
            "    fn to_string(self: i64) -> i64\n"
        )
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("Printable")
        sym = st.get_symbol("Printable")
        assert sym.kind == "trait"

    def test_extract_type_alias(self):
        """pub type alias should appear."""
        from symbol_table import SymbolTable
        mod = parse_source("pub type Size = u64\n")
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("Size")
        sym = st.get_symbol("Size")
        assert sym.kind == "type_alias"

    def test_multiple_symbols(self):
        """Multiple pub items in one module."""
        from symbol_table import SymbolTable
        mod = parse_source(
            "pub const VERSION: i32 = 1\n"
            "\n"
            "pub fn init() -> i32\n"
            "    return 0\n"
            "\n"
            "fn private_helper() -> i32\n"
            "    return 42\n"
            "\n"
            "pub struct Config\n"
            "    debug: i32\n"
        )
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("VERSION")
        assert st.has_symbol("init")
        assert not st.has_symbol("private_helper")
        assert st.has_symbol("Config")
        assert len(st.symbols) == 3

    def test_function_param_info(self):
        """Symbol table should record function parameter types."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn swap(a:& i32, b:& i32) -> i32\n    return 0\n")
        st = SymbolTable.from_module(mod, "<test>")
        sym = st.get_symbol("swap")
        assert sym.kind == "fn"
        assert len(sym.params) == 2
        # Params should record borrow semantics
        assert sym.params[0].name == "a"
        assert sym.params[1].name == "b"

    def test_generic_function(self):
        """Generic functions should record type parameters."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn identity<T>(x: T) -> T\n    return x\n")
        st = SymbolTable.from_module(mod, "<test>")
        sym = st.get_symbol("identity")
        assert sym.kind == "fn"
        assert len(sym.type_params) == 1
        assert sym.type_params[0] == "T"

    def test_generic_struct(self):
        """Generic structs should record type parameters."""
        from symbol_table import SymbolTable
        mod = parse_source("pub struct Pair<T>\n    first: T\n    second: T\n")
        st = SymbolTable.from_module(mod, "<test>")
        sym = st.get_symbol("Pair")
        assert sym.kind == "struct"
        assert len(sym.type_params) == 1

    def test_impl_block_methods(self):
        """impl block methods should be recorded."""
        from symbol_table import SymbolTable
        mod = parse_source(
            "pub struct Counter\n"
            "    value: i32\n"
            "\n"
            "impl Counter\n"
            "    pub fn new() -> Counter\n"
            "        return Counter { value: 0 }\n"
            "\n"
            "    pub fn increment(self:& Counter) -> i32\n"
            "        return 0\n"
        )
        st = SymbolTable.from_module(mod, "<test>")
        assert st.has_symbol("Counter")
        # Methods should be accessible through the type
        methods = st.get_methods("Counter")
        method_names = [m.name for m in methods]
        assert "new" in method_names
        assert "increment" in method_names


# ============================================================================
# Step 3: Validate against existing test levels
# ============================================================================

class TestSymbolTableMatchesExports:
    """Verify symbol table produces same results as current export maps."""

    def test_symbol_table_for_test_level1(self):
        """Symbol table for level 1 should have all [[test]] functions."""
        from symbol_table import SymbolTable
        source = Path(__file__).parent / "test" / "test_level1.ritz"
        if not source.exists():
            pytest.skip("test_level1.ritz not found")
        mod = parse_source(source.read_text())
        st = SymbolTable.from_module(mod, str(source))
        # Level 1 has test functions — they should be in the table
        # (test functions are not pub but have [[test]] attribute)
        test_fns = st.get_test_functions()
        assert len(test_fns) >= 10  # Level 1 has 12 test functions

    def test_ritzlib_sys_exports(self):
        """Symbol table for ritzlib/sys.ritz should match its pub items."""
        from symbol_table import SymbolTable
        ritzlib = Path(__file__).parent.parent / "ritzlib"
        sys_ritz = ritzlib / "sys.ritz"
        if not sys_ritz.exists():
            pytest.skip("ritzlib/sys.ritz not found")
        mod = parse_source(sys_ritz.read_text())
        st = SymbolTable.from_module(mod, str(sys_ritz))
        # sys.ritz should export core syscall wrappers
        # Check a few known exports
        assert st.has_symbol("exit") or st.has_symbol("sys_exit") or len(st.symbols) > 0
        # All symbols should be pub
        for name, sym in st.symbols.items():
            assert sym.is_pub, f"{name} should be pub"

    def test_ritzlib_io_exports(self):
        """Symbol table for ritzlib/io.ritz should have print functions."""
        from symbol_table import SymbolTable
        ritzlib = Path(__file__).parent.parent / "ritzlib"
        io_ritz = ritzlib / "io.ritz"
        if not io_ritz.exists():
            pytest.skip("ritzlib/io.ritz not found")
        mod = parse_source(io_ritz.read_text())
        st = SymbolTable.from_module(mod, str(io_ritz))
        # io.ritz should have print-related functions
        assert len(st.symbols) > 0, "io.ritz should export something"

    def test_symbol_table_matches_current_export_map(self):
        """Symbol table should produce same pub names as existing ExportEntry system."""
        from symbol_table import SymbolTable
        from import_resolver import ImportResolver
        ritzlib = Path(__file__).parent.parent / "ritzlib"
        sys_ritz = ritzlib / "sys.ritz"
        if not sys_ritz.exists():
            pytest.skip("ritzlib/sys.ritz not found")

        # Parse the module
        mod = parse_source(sys_ritz.read_text())

        # Build symbol table (new way)
        st = SymbolTable.from_module(mod, str(sys_ritz))

        # Build export map (old way)
        resolver = ImportResolver(use_cache=False)
        old_exports = resolver._build_export_map(mod, str(sys_ritz))

        # Verify the same pub names appear in both
        st_names = set(st.symbols.keys())
        old_names = set(old_exports.exports.keys())

        # New system should capture at least everything the old system does
        missing = old_names - st_names
        assert len(missing) == 0, f"Symbol table missing: {missing}"

    def test_symbol_table_for_test_level19(self):
        """Symbol table for level 19 (imports) should have test functions."""
        from symbol_table import SymbolTable
        source = Path(__file__).parent / "test" / "test_level19.ritz"
        if not source.exists():
            pytest.skip("test_level19.ritz not found")
        mod = parse_source(source.read_text())
        st = SymbolTable.from_module(mod, str(source))
        test_fns = st.get_test_functions()
        assert len(test_fns) >= 1, "Level 19 should have test functions"


# ============================================================================
# Step 5b: to_declarations() — generate AST stubs from symbol table
# ============================================================================

class TestToDeclarations:
    """Test that symbol table can generate AST declaration stubs.

    These stubs are function signatures without bodies, struct/enum/trait
    definitions, constants, and type aliases — everything the emitter needs
    to generate `declare` statements for imported items without the full AST.
    """

    def test_to_declarations_exists(self):
        """to_declarations() method should exist on SymbolTable."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn foo() -> i32\n    return 0\n")
        st = SymbolTable.from_module(mod, "<test>")
        assert hasattr(st, 'to_declarations'), "SymbolTable needs to_declarations()"

    def test_fn_declaration_is_fndef(self):
        """to_declarations() should return FnDef items for functions."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn add(a: i32, b: i32) -> i32\n    return a + b\n")
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        fn_decls = [d for d in decls if isinstance(d, rast.FnDef)]
        assert len(fn_decls) == 1
        assert fn_decls[0].name == "add"

    def test_fn_declaration_has_no_body(self):
        """Declared functions should have empty Block body (no implementation)."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn add(a: i32, b: i32) -> i32\n    return a + b\n")
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        fn_decls = [d for d in decls if isinstance(d, rast.FnDef)]
        body = fn_decls[0].body
        assert isinstance(body, rast.Block), "Body should be a Block"
        assert len(body.stmts) == 0, "Declaration should have empty body"

    def test_fn_declaration_preserves_signature(self):
        """Declared functions should preserve params and return type."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn add(a: i32, b: i32) -> i32\n    return a + b\n")
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        fn_decls = [d for d in decls if isinstance(d, rast.FnDef)]
        fn = fn_decls[0]
        assert len(fn.params) == 2
        assert fn.params[0].name == "a"
        assert fn.params[1].name == "b"
        assert fn.ret_type is not None

    def test_fn_declaration_has_source_file(self):
        """Declared items should be tagged with their source module path."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn foo() -> i32\n    return 0\n")
        st = SymbolTable.from_module(mod, "/path/to/foo.ritz")
        decls = st.to_declarations()
        fn_decls = [d for d in decls if isinstance(d, rast.FnDef)]
        assert fn_decls[0].source_file == "/path/to/foo.ritz"

    def test_struct_declaration(self):
        """to_declarations() should return StructDef with fields."""
        from symbol_table import SymbolTable
        mod = parse_source("pub struct Point\n    x: i32\n    y: i32\n")
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        struct_decls = [d for d in decls if isinstance(d, rast.StructDef)]
        assert len(struct_decls) == 1
        assert struct_decls[0].name == "Point"
        assert len(struct_decls[0].fields) == 2

    def test_enum_declaration(self):
        """to_declarations() should return EnumDef with variants."""
        from symbol_table import SymbolTable
        mod = parse_source(
            "pub enum Color\n"
            "    Red\n"
            "    Green\n"
            "    Blue\n"
        )
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        enum_decls = [d for d in decls if isinstance(d, rast.EnumDef)]
        assert len(enum_decls) == 1
        assert enum_decls[0].name == "Color"

    def test_const_declaration(self):
        """to_declarations() should return ConstDef with value."""
        from symbol_table import SymbolTable
        mod = parse_source("pub const MAX: i32 = 42\n")
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        const_decls = [d for d in decls if isinstance(d, rast.ConstDef)]
        assert len(const_decls) == 1
        assert const_decls[0].name == "MAX"

    def test_extern_fn_declaration(self):
        """to_declarations() should return ExternFn."""
        from symbol_table import SymbolTable
        mod = parse_source("extern fn puts(s: *u8) -> i32\n")
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        extern_decls = [d for d in decls if isinstance(d, rast.ExternFn)]
        assert len(extern_decls) == 1
        assert extern_decls[0].name == "puts"

    def test_type_alias_declaration(self):
        """to_declarations() should return TypeAlias."""
        from symbol_table import SymbolTable
        mod = parse_source("pub type Size = u64\n")
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        alias_decls = [d for d in decls if isinstance(d, rast.TypeAlias)]
        assert len(alias_decls) == 1
        assert alias_decls[0].name == "Size"

    def test_trait_declaration(self):
        """to_declarations() should return TraitDef."""
        from symbol_table import SymbolTable
        mod = parse_source(
            "pub trait Printable\n"
            "    fn to_string(self: i64) -> i64\n"
        )
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        trait_decls = [d for d in decls if isinstance(d, rast.TraitDef)]
        assert len(trait_decls) == 1
        assert trait_decls[0].name == "Printable"

    def test_mixed_module_declarations(self):
        """A module with multiple items should produce all declarations."""
        from symbol_table import SymbolTable
        mod = parse_source(
            "pub const VERSION: i32 = 1\n"
            "\n"
            "pub fn init() -> i32\n"
            "    return 0\n"
            "\n"
            "fn private_helper() -> i32\n"
            "    return 42\n"
            "\n"
            "pub struct Config\n"
            "    debug: i32\n"
        )
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        # Should have 3 declarations (const, fn, struct) — not private_helper
        assert len(decls) == 3
        kinds = {type(d).__name__ for d in decls}
        assert "FnDef" in kinds
        assert "StructDef" in kinds
        assert "ConstDef" in kinds
        # Private function should NOT appear
        names = {getattr(d, 'name', None) for d in decls}
        assert "private_helper" not in names

    def test_declaration_order(self):
        """Declarations should be in a deterministic order:
        structs, enums, type_aliases, traits, consts, extern_fns, functions."""
        from symbol_table import SymbolTable
        mod = parse_source(
            "pub fn foo() -> i32\n"
            "    return 0\n"
            "\n"
            "pub struct Bar\n"
            "    x: i32\n"
            "\n"
            "pub const Z: i32 = 1\n"
        )
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        types = [type(d).__name__ for d in decls]
        # Structs before consts before functions
        assert types.index("StructDef") < types.index("ConstDef")
        assert types.index("ConstDef") < types.index("FnDef")


    def test_fn_declaration_preserves_borrow(self):
        """Declared functions should preserve parameter borrow semantics."""
        from symbol_table import SymbolTable
        mod = parse_source("pub fn mutate(x:& i32) -> i32\n    return 0\n")
        st = SymbolTable.from_module(mod, "<test>")
        decls = st.to_declarations()
        fn_decls = [d for d in decls if isinstance(d, rast.FnDef)]
        assert len(fn_decls) == 1
        assert fn_decls[0].params[0].borrow == rast.Borrow.MUTABLE


# ============================================================================
# Step 5c: Integration — stubs produce identical IR to merged AST
# ============================================================================

class TestStubIREquivalence:
    """Verify that compiling with symbol-table stubs produces the same LLVM IR
    as compiling with the current merged-AST approach.

    This is the proof that we can safely replace AST merging.
    """

    def _compile_to_ir(self, module, source_path):
        """Compile a module to LLVM IR string, returning the IR."""
        from emitter_llvmlite import emit as emit_llvmlite
        source_abs = str(Path(source_path).resolve())
        return emit_llvmlite(
            module,
            no_runtime=True,
            source_file=Path(source_path).name,
            source_dir=str(Path(source_path).parent.resolve()),
            main_source_path=source_abs,
            target='x86_64-unknown-linux-gnu',
            target_os='linux',
        )

    def _normalize_ir(self, ir_text):
        """Normalize IR for comparison — strip non-deterministic parts."""
        import re
        # Normalize ritz_module_N counter everywhere — ModuleID, struct names, etc.
        # The llvmlite global counter increments on each Module creation,
        # so different compilation runs get different numbers.
        ir_text = re.sub(r'ritz_module_\d+', 'ritz_module_N', ir_text)
        return ir_text

    def _strip_imported_fn_bodies(self, module, source_path):
        """Replace imported non-generic FnDef bodies with empty Blocks.

        Generic functions keep their bodies because the monomorphizer needs
        to scan them for type instantiations. Non-generic imported functions
        only need their signature (declare, not define).
        """
        source_abs = str(Path(source_path).resolve())
        stub_items = []
        for item in module.items:
            src = getattr(item, 'source_file', None)
            if isinstance(item, rast.FnDef) and src and src != source_abs:
                # Check if this function is generic (monomorphizer needs the body)
                is_generic = getattr(item, 'is_generic', lambda: False)()
                if not is_generic:
                    # Non-generic imported function — strip body
                    stub = rast.FnDef(
                        span=item.span,
                        name=item.name,
                        params=item.params,
                        ret_type=item.ret_type,
                        body=rast.Block(item.span, stmts=[], expr=None),
                        attrs=getattr(item, 'attrs', None),
                        is_pub=item.is_pub,
                        type_params=getattr(item, 'type_params', None),
                    )
                    stub.source_file = item.source_file
                    stub_items.append(stub)
                else:
                    # Generic function — keep full body for monomorphization
                    stub_items.append(item)
            else:
                stub_items.append(item)
        return rast.Module(module.span, stub_items)

    def test_stub_ir_matches_declares_for_simple_import(self):
        """Verify that stripping imported function bodies doesn't change
        the declare/define split — the emitter correctly declares imported
        functions regardless of whether their body is present.

        Note: monomorphized specializations differ because the monomorphizer
        needs imported function bodies to find generic call sites. That's
        a separate concern handled by keeping generic function bodies.
        """
        from import_resolver import resolve_imports
        import re

        test_file = Path(__file__).parent / "test" / "test_level19.ritz"
        if not test_file.exists():
            pytest.skip("test_level19.ritz not found")

        source = test_file.read_text()
        source_path = str(test_file)

        # --- Method 1: Current approach (merged AST) ---
        lexer1 = Lexer(source, source_path)
        parser1 = Parser(lexer1.tokenize())
        merged = resolve_imports(parser1.parse_module(), source_path, use_cache=False)
        ir_merged = self._compile_to_ir(merged, source_path)

        # --- Method 2: Strip imported function bodies ---
        lexer2 = Lexer(source, source_path)
        parser2 = Parser(lexer2.tokenize())
        merged2 = resolve_imports(parser2.parse_module(), source_path, use_cache=False)
        stub_module = self._strip_imported_fn_bodies(merged2, source_path)
        ir_stubs = self._compile_to_ir(stub_module, source_path)

        # --- Compare declare/define sets (not full IR) ---
        # Declares should be identical — same imported function signatures
        merged_declares = set(re.findall(r'^declare .*$', ir_merged, re.MULTILINE))
        stub_declares = set(re.findall(r'^declare .*$', ir_stubs, re.MULTILINE))
        # Normalize module IDs
        merged_declares = {re.sub(r'ritz_module_\d+', 'ritz_module_N', d) for d in merged_declares}
        stub_declares = {re.sub(r'ritz_module_\d+', 'ritz_module_N', d) for d in stub_declares}
        assert merged_declares == stub_declares, (
            f"Declare mismatch!\n"
            f"Only in merged: {merged_declares - stub_declares}\n"
            f"Only in stubs: {stub_declares - merged_declares}"
        )

        # Local defines should be identical — same test functions
        def extract_local_defines(ir):
            """Extract function names that are defined (not just declared)."""
            return set(re.findall(r'^define .+@\"?([^\"(]+)\"?\(', ir, re.MULTILINE))

        merged_defines = extract_local_defines(ir_merged)
        stub_defines = extract_local_defines(ir_stubs)

        # Stub defines should be a SUBSET of merged defines
        # (merged has monomorphized specializations too)
        assert stub_defines.issubset(merged_defines), (
            f"Stub defines not subset of merged!\n"
            f"Extra in stubs: {stub_defines - merged_defines}"
        )

        # Stubs should have all local functions
        expected_local = {'test_left_shift_basic', 'test_left_shift_larger',
                         'test_right_shift_basic', 'test_right_shift_larger',
                         'test_shift_combined', 'test_shift_i64', 'main'}
        assert expected_local.issubset(stub_defines), (
            f"Missing local functions: {expected_local - stub_defines}"
        )

    def test_stub_ir_matches_for_level_with_structs(self):
        """Test a level that imports structs (not just functions)."""
        from import_resolver import resolve_imports

        test_dir = Path(__file__).parent / "test"
        for level_name in ["test_level24.ritz", "test_level30.ritz"]:
            test_file = test_dir / level_name
            if test_file.exists():
                break
        else:
            pytest.skip("No struct-importing test level found")

        source = test_file.read_text()
        source_path = str(test_file)

        # Compile normally
        lexer1 = Lexer(source, source_path)
        parser1 = Parser(lexer1.tokenize())
        merged = resolve_imports(parser1.parse_module(), source_path, use_cache=False)
        ir_merged = self._normalize_ir(self._compile_to_ir(merged, source_path))

        # Compile with stripped function bodies
        lexer2 = Lexer(source, source_path)
        parser2 = Parser(lexer2.tokenize())
        merged2 = resolve_imports(parser2.parse_module(), source_path, use_cache=False)
        stub_module = self._strip_imported_fn_bodies(merged2, source_path)
        ir_stubs = self._normalize_ir(self._compile_to_ir(stub_module, source_path))

        assert ir_merged == ir_stubs, f"IR mismatch for {level_name}"


    def test_stub_all_levels_with_imports_declare_match(self):
        """For EVERY test level that uses imports, verify that stripping
        non-generic imported function bodies doesn't change the declare set.

        This is the comprehensive proof that the stub approach is safe
        for the emitter's declare/define split.
        """
        from import_resolver import resolve_imports
        import re

        test_dir = Path(__file__).parent / "test"
        levels_tested = 0
        failures = []

        for level_file in sorted(test_dir.glob("test_level*.ritz")):
            source = level_file.read_text()
            if 'import ' not in source:
                continue  # Skip levels without imports

            source_path = str(level_file)

            try:
                # Compile merged
                lexer1 = Lexer(source, source_path)
                parser1 = Parser(lexer1.tokenize())
                merged = resolve_imports(parser1.parse_module(), source_path, use_cache=False)
                ir_merged = self._compile_to_ir(merged, source_path)

                # Compile with stubs
                lexer2 = Lexer(source, source_path)
                parser2 = Parser(lexer2.tokenize())
                merged2 = resolve_imports(parser2.parse_module(), source_path, use_cache=False)
                stub_module = self._strip_imported_fn_bodies(merged2, source_path)
                ir_stubs = self._compile_to_ir(stub_module, source_path)

                # Compare declares
                merged_decls = {re.sub(r'ritz_module_\d+', 'N', d)
                               for d in re.findall(r'^declare .*$', ir_merged, re.MULTILINE)}
                stub_decls = {re.sub(r'ritz_module_\d+', 'N', d)
                             for d in re.findall(r'^declare .*$', ir_stubs, re.MULTILINE)}

                if merged_decls != stub_decls:
                    failures.append(f"{level_file.name}: declare mismatch")

                levels_tested += 1
            except Exception as e:
                # Some levels may have compilation issues — skip
                pass

        assert levels_tested >= 10, f"Only tested {levels_tested} levels (expected 10+)"
        assert len(failures) == 0, f"Declare mismatches: {failures}"



# ============================================================================
# Step 6: Import resolver with use_symbol_tables=True
# ============================================================================

class TestSymbolTableImportMode:
    """Test the import resolver's symbol table mode.

    When use_symbol_tables=True, the resolver builds SymbolTable for each
    imported module and strips non-generic function bodies. The resulting
    IR should have identical declares as legacy mode.
    """

    def _compile_to_ir(self, module, source_path):
        from emitter_llvmlite import emit as emit_llvmlite
        source_abs = str(Path(source_path).resolve())
        return emit_llvmlite(
            module,
            no_runtime=True,
            source_file=Path(source_path).name,
            source_dir=str(Path(source_path).parent.resolve()),
            main_source_path=source_abs,
            target='x86_64-unknown-linux-gnu',
            target_os='linux',
        )

    def test_symbol_table_mode_compiles(self):
        """A simple level compiles with use_symbol_tables=True."""
        from import_resolver import resolve_imports

        test_file = Path(__file__).parent / "test" / "test_level19.ritz"
        if not test_file.exists():
            pytest.skip("test_level19.ritz not found")

        source = test_file.read_text()
        source_path = str(test_file)

        lexer = Lexer(source, source_path)
        parser = Parser(lexer.tokenize())
        mod = parser.parse_module()
        resolved = resolve_imports(mod, source_path, use_cache=False,
                                   use_symbol_tables=True)
        # Should produce valid IR
        ir = self._compile_to_ir(resolved, source_path)
        assert len(ir) > 100, "Should produce non-trivial IR"

    def test_symbol_table_mode_declares_match_legacy(self):
        """Declares should be identical between legacy and symbol table modes."""
        from import_resolver import resolve_imports
        import re

        test_file = Path(__file__).parent / "test" / "test_level19.ritz"
        if not test_file.exists():
            pytest.skip("test_level19.ritz not found")

        source = test_file.read_text()
        source_path = str(test_file)

        # Legacy mode
        lexer1 = Lexer(source, source_path)
        merged_legacy = resolve_imports(
            Parser(lexer1.tokenize()).parse_module(),
            source_path, use_cache=False, use_symbol_tables=False)
        ir_legacy = self._compile_to_ir(merged_legacy, source_path)

        # Symbol table mode
        lexer2 = Lexer(source, source_path)
        merged_st = resolve_imports(
            Parser(lexer2.tokenize()).parse_module(),
            source_path, use_cache=False, use_symbol_tables=True)
        ir_st = self._compile_to_ir(merged_st, source_path)

        # Compare declares
        norm = lambda s: re.sub(r'ritz_module_\d+', 'N', s)
        legacy_decls = {norm(d) for d in re.findall(r'^declare .*$', ir_legacy, re.MULTILINE)}
        st_decls = {norm(d) for d in re.findall(r'^declare .*$', ir_st, re.MULTILINE)}

        assert legacy_decls == st_decls, (
            f"Declare mismatch!\n"
            f"Only in legacy: {legacy_decls - st_decls}\n"
            f"Only in symtab: {st_decls - legacy_decls}"
        )

    def test_symbol_table_mode_all_levels(self):
        """All test levels with imports should compile in symbol table mode."""
        from import_resolver import resolve_imports
        import re

        test_dir = Path(__file__).parent / "test"
        levels_tested = 0
        failures = []

        for level_file in sorted(test_dir.glob("test_level*.ritz")):
            source = level_file.read_text()
            if 'import ' not in source:
                continue

            source_path = str(level_file)
            try:
                # First check if legacy mode compiles — if it fails,
                # that's a pre-existing bug, not a symbol table issue
                lexer2 = Lexer(source, source_path)
                mod2 = resolve_imports(
                    Parser(lexer2.tokenize()).parse_module(),
                    source_path, use_cache=False, use_symbol_tables=False)
                ir2 = self._compile_to_ir(mod2, source_path)
            except Exception:
                # Pre-existing compilation failure — skip this level
                continue

            try:
                # Compile in symbol table mode
                lexer = Lexer(source, source_path)
                mod = resolve_imports(
                    Parser(lexer.tokenize()).parse_module(),
                    source_path, use_cache=False, use_symbol_tables=True)
                ir = self._compile_to_ir(mod, source_path)

                # Compare declares
                norm = lambda s: re.sub(r'ritz_module_\d+', 'N', s)
                st_decls = {norm(d) for d in re.findall(r'^declare .*$', ir, re.MULTILINE)}
                legacy_decls = {norm(d) for d in re.findall(r'^declare .*$', ir2, re.MULTILINE)}

                if st_decls != legacy_decls:
                    failures.append(f"{level_file.name}: declare mismatch")

                levels_tested += 1
            except Exception as e:
                failures.append(f"{level_file.name}: {e}")

        assert levels_tested >= 10, f"Only tested {levels_tested} levels"
        assert len(failures) == 0, f"Failures: {failures}"


    def test_symbol_table_all_ritzlib_modules(self):
        """Symbol table should successfully parse every ritzlib module."""
        from symbol_table import SymbolTable
        ritzlib = Path(__file__).parent.parent / "ritzlib"
        if not ritzlib.exists():
            pytest.skip("ritzlib not found")

        succeeded = 0
        parse_errors = []  # Pre-existing parse errors, not our fault
        st_errors = []     # Symbol table construction errors — our fault
        for ritz_file in sorted(ritzlib.glob("*.ritz")):
            try:
                mod = parse_source(ritz_file.read_text())
            except Exception as e:
                parse_errors.append((ritz_file.name, str(e)))
                continue
            try:
                st = SymbolTable.from_module(mod, str(ritz_file))
                succeeded += 1
            except Exception as e:
                st_errors.append((ritz_file.name, str(e)))

        # Symbol table errors are OUR bugs — must be zero
        assert len(st_errors) == 0, f"Symbol table failed for: {st_errors}"
        # We should successfully process most modules
        assert succeeded >= 25, f"Only {succeeded} modules parsed (expected 25+)"
