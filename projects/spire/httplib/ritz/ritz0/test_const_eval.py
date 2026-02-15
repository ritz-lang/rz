"""
Tests for constant expression evaluation.
"""

import pytest
from lexer import Lexer
from parser import Parser
from const_eval import (
    ConstEvaluator,
    ConstEvalError,
    evaluate_const_expr,
    evaluate_array_sizes,
)
import ritz_ast as rast


def parse_expr(source: str) -> rast.Expr:
    """Helper to parse an expression."""
    lexer = Lexer(source, "test")
    tokens = list(lexer.tokenize())
    parser = Parser(tokens)
    return parser.parse_expr()


def parse_type(source: str) -> rast.Type:
    """Helper to parse a type."""
    # Wrap in a function to get valid token stream
    full_source = f"fn f(x: {source}) -> void\n    pass"
    lexer = Lexer(full_source, "test")
    tokens = list(lexer.tokenize())
    parser = Parser(tokens)
    fn = parser.parse_module().items[0]
    return fn.params[0].type


def parse_module(source: str) -> rast.Module:
    """Helper to parse a module."""
    lexer = Lexer(source, "test")
    tokens = list(lexer.tokenize())
    parser = Parser(tokens)
    return parser.parse_module()


class TestConstEvaluator:
    """Tests for ConstEvaluator class."""

    def test_integer_literal(self):
        """Integer literals evaluate to themselves."""
        evaluator = ConstEvaluator()
        expr = parse_expr("42")
        assert evaluator.evaluate(expr) == 42

    def test_negative_literal(self):
        """Negative integers evaluate correctly."""
        evaluator = ConstEvaluator()
        expr = parse_expr("-1")
        assert evaluator.evaluate(expr) == -1

    def test_named_constant(self):
        """Named constants resolve to their values."""
        evaluator = ConstEvaluator({"SIZE": 512})
        expr = parse_expr("SIZE")
        assert evaluator.evaluate(expr) == 512

    def test_unknown_constant(self):
        """Unknown constants raise ConstEvalError."""
        evaluator = ConstEvaluator()
        expr = parse_expr("UNKNOWN")
        with pytest.raises(ConstEvalError, match="Unknown constant"):
            evaluator.evaluate(expr)

    def test_addition(self):
        """Addition of constants."""
        evaluator = ConstEvaluator({"A": 10, "B": 20})
        expr = parse_expr("A + B")
        assert evaluator.evaluate(expr) == 30

    def test_subtraction(self):
        """Subtraction of constants."""
        evaluator = ConstEvaluator()
        expr = parse_expr("100 - 37")
        assert evaluator.evaluate(expr) == 63

    def test_multiplication(self):
        """Multiplication of constants."""
        evaluator = ConstEvaluator({"PAGE_SIZE": 4096, "PAGES": 16})
        expr = parse_expr("PAGE_SIZE * PAGES")
        assert evaluator.evaluate(expr) == 65536

    def test_division(self):
        """Division of constants (integer)."""
        evaluator = ConstEvaluator()
        expr = parse_expr("100 / 7")
        assert evaluator.evaluate(expr) == 14  # Integer division

    def test_division_by_zero(self):
        """Division by zero raises ConstEvalError."""
        evaluator = ConstEvaluator()
        expr = parse_expr("100 / 0")
        with pytest.raises(ConstEvalError, match="Division by zero"):
            evaluator.evaluate(expr)

    def test_modulo(self):
        """Modulo of constants."""
        evaluator = ConstEvaluator()
        expr = parse_expr("100 % 7")
        assert evaluator.evaluate(expr) == 2

    def test_left_shift(self):
        """Left shift operator."""
        evaluator = ConstEvaluator()
        expr = parse_expr("1 << 9")
        assert evaluator.evaluate(expr) == 512

    def test_right_shift(self):
        """Right shift operator."""
        evaluator = ConstEvaluator()
        expr = parse_expr("1024 >> 2")
        assert evaluator.evaluate(expr) == 256

    def test_bitwise_and(self):
        """Bitwise AND operator."""
        evaluator = ConstEvaluator()
        expr = parse_expr("0xFF & 0x0F")
        assert evaluator.evaluate(expr) == 0x0F

    def test_bitwise_or(self):
        """Bitwise OR operator."""
        evaluator = ConstEvaluator()
        expr = parse_expr("0xF0 | 0x0F")
        assert evaluator.evaluate(expr) == 0xFF

    def test_bitwise_xor(self):
        """Bitwise XOR operator."""
        evaluator = ConstEvaluator()
        expr = parse_expr("0xFF ^ 0x0F")
        assert evaluator.evaluate(expr) == 0xF0

    def test_bitwise_not(self):
        """Bitwise NOT operator."""
        evaluator = ConstEvaluator()
        expr = parse_expr("~0")
        assert evaluator.evaluate(expr) == -1

    def test_parenthesized(self):
        """Parenthesized expressions."""
        evaluator = ConstEvaluator()
        expr = parse_expr("(1 + 2) * 3")
        assert evaluator.evaluate(expr) == 9

    def test_complex_expression(self):
        """Complex expression with multiple operators."""
        evaluator = ConstEvaluator({"BITS": 9})
        expr = parse_expr("1 << BITS")
        assert evaluator.evaluate(expr) == 512

    def test_precedence(self):
        """Operator precedence is respected."""
        evaluator = ConstEvaluator()
        # * binds tighter than +
        expr = parse_expr("2 + 3 * 4")
        assert evaluator.evaluate(expr) == 14


class TestArraySizeParsing:
    """Tests for parsing array types with const expression sizes."""

    def test_integer_literal_size(self):
        """Array with integer literal size."""
        ty = parse_type("[512]u8")
        assert isinstance(ty, rast.ArrayType)
        # Before const eval, size is an IntLit expression
        assert isinstance(ty.size, rast.IntLit)
        assert ty.size.value == 512
        assert isinstance(ty.inner, rast.NamedType)
        assert ty.inner.name == "u8"

    def test_constant_name_size(self):
        """Array with constant name as size."""
        ty = parse_type("[SIZE]u8")
        assert isinstance(ty, rast.ArrayType)
        # Before const eval, size is an Ident
        assert isinstance(ty.size, rast.Ident)
        assert ty.size.name == "SIZE"

    def test_shift_expression_size(self):
        """Array with shift expression as size."""
        ty = parse_type("[1 << 9]u8")
        assert isinstance(ty, rast.ArrayType)
        assert isinstance(ty.size, rast.BinOp)
        assert ty.size.op == "<<"

    def test_complex_expression_size(self):
        """Array with complex expression as size."""
        ty = parse_type("[SIZE * 2]u8")
        assert isinstance(ty, rast.ArrayType)
        assert isinstance(ty.size, rast.BinOp)

    def test_slice_type_still_works(self):
        """Slice types [T] still parse correctly."""
        ty = parse_type("[u8]")
        assert isinstance(ty, rast.SliceType)
        assert isinstance(ty.inner, rast.NamedType)
        assert ty.inner.name == "u8"


class TestConstEvalPass:
    """Tests for the const eval pass on modules."""

    def test_simple_const_array(self):
        """Const expression in array size is evaluated."""
        source = """
const SIZE: i32 = 512

fn f() -> void
    var buf: [SIZE]u8
"""
        module = parse_module(source)
        errors = evaluate_array_sizes(module)
        assert errors == []

        # Find the function and check the array type
        fn = module.items[1]
        assert isinstance(fn, rast.FnDef)
        var_decl = fn.body.stmts[0]
        assert isinstance(var_decl, rast.VarStmt)
        assert isinstance(var_decl.type, rast.ArrayType)
        assert var_decl.type.size == 512

    def test_shift_expression_in_array(self):
        """Shift expression in array size is evaluated."""
        source = """
fn f() -> void
    var buf: [1 << 10]u8
"""
        module = parse_module(source)
        errors = evaluate_array_sizes(module)
        assert errors == []

        fn = module.items[0]
        var_decl = fn.body.stmts[0]
        assert var_decl.type.size == 1024

    def test_const_with_expression(self):
        """Const defined with expression."""
        source = """
const BITS: i32 = 9
const SIZE: i32 = 1 << 9

fn f() -> void
    var buf: [SIZE]u8
"""
        module = parse_module(source)
        errors = evaluate_array_sizes(module)
        # SIZE depends on a literal, should work
        # Note: BITS isn't used in SIZE (would need multi-pass for that)
        assert errors == []

        fn = module.items[2]
        var_decl = fn.body.stmts[0]
        assert var_decl.type.size == 512

    def test_struct_field_array(self):
        """Array size in struct field is evaluated."""
        source = """
const BUFFER_SIZE: i32 = 256

struct Buffer
    data: [BUFFER_SIZE]u8
    len: i64
"""
        module = parse_module(source)
        errors = evaluate_array_sizes(module)
        assert errors == []

        struct = module.items[1]
        assert isinstance(struct, rast.StructDef)
        field_name, field_type = struct.fields[0]
        assert field_name == "data"
        assert isinstance(field_type, rast.ArrayType)
        assert field_type.size == 256

    def test_function_param_array(self):
        """Array size in function parameter is evaluated."""
        source = """
const N: i32 = 16

fn process(data: [N]i32) -> void
    pass
"""
        module = parse_module(source)
        errors = evaluate_array_sizes(module)
        assert errors == []

        fn = module.items[1]
        param_type = fn.params[0].type
        assert isinstance(param_type, rast.ArrayType)
        assert param_type.size == 16

    def test_return_type_array(self):
        """Array size in return type is evaluated."""
        source = """
const SIZE: i32 = 4

fn get_vec() -> [SIZE]f32
    var v: [SIZE]f32
    return v
"""
        module = parse_module(source)
        errors = evaluate_array_sizes(module)
        assert errors == []

        fn = module.items[1]
        assert isinstance(fn.ret_type, rast.ArrayType)
        assert fn.ret_type.size == 4

    def test_multiplication_expression(self):
        """Multiplication in array size."""
        source = """
const PAGE_SIZE: i32 = 4096
const PAGES: i32 = 16

fn f() -> void
    var buf: [PAGE_SIZE * PAGES]u8
"""
        module = parse_module(source)
        errors = evaluate_array_sizes(module)
        # This requires PAGE_SIZE to be evaluated first
        # Currently our pass collects constants in order, so this should work
        assert errors == []

        fn = module.items[2]
        var_decl = fn.body.stmts[0]
        # 4096 * 16 = 65536
        assert var_decl.type.size == 65536

    def test_unknown_constant_error(self):
        """Unknown constant in array size produces error."""
        source = """
fn f() -> void
    var buf: [UNKNOWN]u8
"""
        module = parse_module(source)
        errors = evaluate_array_sizes(module)
        assert len(errors) == 1
        assert "Unknown constant" in str(errors[0])


class TestEvaluateConstExpr:
    """Tests for the convenience function."""

    def test_simple_expression(self):
        """Simple expression evaluation."""
        expr = parse_expr("2 + 3")
        assert evaluate_const_expr(expr) == 5

    def test_with_constants(self):
        """Expression with provided constants."""
        expr = parse_expr("X * Y")
        assert evaluate_const_expr(expr, {"X": 10, "Y": 5}) == 50
