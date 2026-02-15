"""
Integration tests for Ritz syntax features.

Tests the complete compilation pipeline with:
- @ for immutable references and address-of
- @& for mutable references and mutable address-of
- :& for mutable borrow parameters
- := for move parameters
- [[attr]] for attributes
"""

import pytest
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from lexer import Lexer
from parser import Parser
from emitter_llvmlite import LLVMEmitter, emit
import ritz_ast as rast


class TestRERITZIntegration:
    """Integration tests for Ritz syntax features."""

    def compile_to_ir(self, source: str) -> str:
        """Helper to compile source to LLVM IR."""
        lexer = Lexer(source, "test.ritz")
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        module = parser.parse_module()
        return emit(module, no_runtime=True)

    def parse_module(self, source: str) -> rast.Module:
        """Helper to parse source to AST."""
        lexer = Lexer(source, "test.ritz")
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        return parser.parse_module()

    # --- Basic @ and @& Type Tests ---

    def test_immutable_reference_type(self):
        """Test @T type parsing for immutable references."""
        source = """
fn read_value(x: @i32) -> i32
    *x
"""
        module = self.parse_module(source)
        fn = module.items[0]
        param = fn.params[0]
        assert isinstance(param.type, rast.RefType)
        assert param.type.mutable == False
        assert param.type.inner.name == 'i32'

    def test_mutable_reference_type(self):
        """Test @&T type parsing for mutable references."""
        source = """
fn set_value(x: @&i32)
    *x = 42
"""
        module = self.parse_module(source)
        fn = module.items[0]
        param = fn.params[0]
        assert isinstance(param.type, rast.RefType)
        assert param.type.mutable == True
        assert param.type.inner.name == 'i32'

    # --- Borrow Parameter Tests ---

    def test_mutable_borrow_parameter(self):
        """Test :& for mutable borrow parameters."""
        source = """
fn increment(x:& i32)
    x = x + 1
"""
        module = self.parse_module(source)
        fn = module.items[0]
        param = fn.params[0]
        assert param.borrow == rast.Borrow.MUTABLE
        assert param.type.name == 'i32'

    def test_move_parameter(self):
        """Test := for move parameters."""
        source = """
fn consume(x:= Vec) -> i32
    0
"""
        module = self.parse_module(source)
        fn = module.items[0]
        param = fn.params[0]
        assert param.borrow == rast.Borrow.MOVE
        assert param.type.name == 'Vec'

    def test_const_borrow_parameter(self):
        """Test : for const borrow parameters (default)."""
        source = """
fn read_only(x: i32) -> i32
    x
"""
        module = self.parse_module(source)
        fn = module.items[0]
        param = fn.params[0]
        assert param.borrow == rast.Borrow.CONST
        assert param.type.name == 'i32'

    # --- Address-of Operator Tests ---

    def test_immutable_address_of(self):
        """Test @ operator for taking immutable address."""
        source = """
fn main() -> i32
    var x: i32 = 42
    let p: @i32 = @x
    *p
"""
        # Should compile without error
        ir = self.compile_to_ir(source)
        assert 'define' in ir

    def test_mutable_address_of(self):
        """Test @& operator for taking mutable address."""
        source = """
fn main() -> i32
    var x: i32 = 42
    let p: @&i32 = @&x
    *p = 100
    x
"""
        # Should compile without error
        ir = self.compile_to_ir(source)
        assert 'define' in ir

    # --- Borrow at Call Site Tests ---

    def test_mutable_borrow_call(self):
        """Test calling function with mutable borrow parameter."""
        source = """
fn increment(x:& i32)
    x = x + 1

fn main() -> i32
    var counter: i32 = 0
    increment(counter)
    counter
"""
        ir = self.compile_to_ir(source)
        assert 'define' in ir
        # The increment function should receive a pointer
        assert 'i32*' in ir or 'ptr' in ir

    def test_const_borrow_call(self):
        """Test calling function with const borrow parameter."""
        source = """
fn double(x: i32) -> i32
    x + x

fn main() -> i32
    let val: i32 = 21
    double(val)
"""
        ir = self.compile_to_ir(source)
        assert 'define' in ir

    # --- Attribute Syntax Tests ---

    def test_double_bracket_attribute(self):
        """Test [[attr]] syntax for attributes."""
        source = """
[[test]]
fn test_something() -> i32
    0
"""
        module = self.parse_module(source)
        fn = module.items[0]
        assert fn.has_attr('test')

    def test_multiple_attributes(self):
        """Test multiple [[attr]] attributes."""
        source = """
[[inline]]
[[test]]
fn test_inlined() -> i32
    0
"""
        module = self.parse_module(source)
        fn = module.items[0]
        assert fn.has_attr('inline')
        assert fn.has_attr('test')

    # --- String Literal Tests ---

    def test_string_literal_is_strview(self):
        """Test that string literals produce StrView in RERITZ mode."""
        source = '''
fn main() -> i32
    let s = "hello"
    0
'''
        ir = self.compile_to_ir(source)
        # In RERITZ mode, "hello" should produce a StrView struct
        # This means insertvalue operations to build {i8*, i64}
        assert 'insertvalue' in ir
        # The struct should have i8* and i64 fields
        assert 'i8*' in ir or 'ptr' in ir
        assert 'i64' in ir

    def test_cstring_literal_still_works(self):
        """Test that c\"...\" still produces *u8 in RERITZ mode."""
        source = '''
fn main() -> i32
    let s = c"hello"
    0
'''
        ir = self.compile_to_ir(source)
        # c"hello" should still be a simple GEP to get pointer
        assert 'getelementptr' in ir
        # Should NOT have insertvalue (that would be StrView)
        lines = [l for l in ir.split('\n') if 'insertvalue' in l and 'hello' in l]
        # If insertvalue exists, it should not be for the c"hello" literal
        assert len(lines) == 0

    # --- Combined Feature Tests ---

    def test_full_reritz_example(self):
        """Test a complete example using multiple RERITZ features."""
        source = """
fn swap(a:& i32, b:& i32)
    let temp: i32 = a
    a = b
    b = temp

fn main() -> i32
    var x: i32 = 10
    var y: i32 = 20
    swap(x, y)
    x - 20  # Should be 0 after swap
"""
        ir = self.compile_to_ir(source)
        assert 'define' in ir
        assert '@"swap"' in ir or '@swap' in ir
        assert '@"main"' in ir or '@main' in ir


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
