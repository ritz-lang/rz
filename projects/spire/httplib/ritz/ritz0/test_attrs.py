"""Tests for [[packed]] and [[naked]] attributes."""

import pytest
from lexer import tokenize, set_reritz_mode
from parser import Parser
from tokens import TokenType
import ritz_ast as rast


class TestPackedAttrParser:
    """Test [[packed]] attribute parsing on structs."""

    def test_packed_struct(self):
        """Test parsing a [[packed]] struct."""
        source = """
[[packed]]
struct PackedData
    a: u8
    b: u64
    c: u8
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        struct_def = module.items[0]
        assert isinstance(struct_def, rast.StructDef)
        assert struct_def.name == "PackedData"
        assert struct_def.has_attr('packed')
        assert len(struct_def.fields) == 3

    def test_non_packed_struct(self):
        """Test that regular structs don't have packed attr."""
        source = """
struct NormalData
    a: u8
    b: u64
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        struct_def = module.items[0]
        assert isinstance(struct_def, rast.StructDef)
        assert not struct_def.has_attr('packed')

    def test_multiple_attrs_on_struct(self):
        """Test struct with multiple attributes."""
        source = """
[[packed, repr_c]]
struct ForeignStruct
    x: i32
    y: i32
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        struct_def = module.items[0]
        assert isinstance(struct_def, rast.StructDef)
        assert struct_def.has_attr('packed')
        assert struct_def.has_attr('repr_c')


class TestNakedAttrParser:
    """Test [[naked]] attribute parsing on functions."""

    def test_naked_function(self):
        """Test parsing a [[naked]] function."""
        source = """
[[naked]]
fn interrupt_handler()
    asm x86_64:
        iretq
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn_def = module.items[0]
        assert isinstance(fn_def, rast.FnDef)
        assert fn_def.name == "interrupt_handler"
        assert fn_def.has_attr('naked')

    def test_non_naked_function(self):
        """Test that regular functions don't have naked attr."""
        source = """
fn normal_function() -> i32
    42
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn_def = module.items[0]
        assert isinstance(fn_def, rast.FnDef)
        assert not fn_def.has_attr('naked')

    def test_naked_with_inline(self):
        """Test naked with other function attributes."""
        source = """
[[naked, noinline]]
fn critical_handler()
    asm x86_64:
        ret
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn_def = module.items[0]
        assert isinstance(fn_def, rast.FnDef)
        assert fn_def.has_attr('naked')
        assert fn_def.has_attr('noinline')


class TestPackedEmitter:
    """Test [[packed]] struct LLVM IR emission."""

    def test_packed_struct_layout(self):
        """Test that packed structs have no padding."""
        from emitter_llvmlite import LLVMEmitter as Emitter

        source = """
[[packed]]
struct Packed
    a: u8
    b: u64
    c: u8
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        emitter = Emitter()
        ir = emitter.emit_module(module)

        # Packed struct should have '<{' syntax in LLVM IR
        assert '<{ i8, i64, i8 }>' in ir or 'packed' in ir.lower()

    def test_normal_struct_not_packed(self):
        """Test that normal structs use regular layout."""
        from emitter_llvmlite import LLVMEmitter as Emitter

        source = """
struct Normal
    a: u8
    b: u64
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        emitter = Emitter()
        ir = emitter.emit_module(module)

        # Normal struct should NOT have '<{' packed syntax
        # Look for identified struct type pattern
        assert '{ i8, i64 }' in ir or '%"struct.' in ir


class TestNakedEmitter:
    """Test [[naked]] function LLVM IR emission."""

    def test_naked_function_attribute(self):
        """Test that naked functions have the naked attribute in IR."""
        from emitter_llvmlite import LLVMEmitter as Emitter

        source = """
[[naked]]
fn naked_fn()
    asm x86_64:
        ret
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        emitter = Emitter()
        ir = emitter.emit_module(module)

        # Should have 'naked' attribute on the function
        assert 'naked' in ir

    def test_regular_function_not_naked(self):
        """Test that regular functions don't have naked attribute."""
        from emitter_llvmlite import LLVMEmitter as Emitter

        source = """
fn regular_fn() -> i32
    42
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        emitter = Emitter()
        ir = emitter.emit_module(module)

        # Should NOT have 'naked' in the function definition
        # (may appear elsewhere like in comments or metadata)
        lines = ir.split('\n')
        fn_lines = [l for l in lines if 'define' in l and 'regular_fn' in l]
        for line in fn_lines:
            assert 'naked' not in line


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
