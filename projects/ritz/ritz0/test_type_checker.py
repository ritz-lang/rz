"""
Tests for the Type Checker

Validates that type errors are caught before code generation.
"""

import pytest
from parser import parse
from type_checker import TypeChecker, TypeError


def check(source: str) -> list:
    """Parse and run type checker, return errors."""
    module = parse(source)
    checker = TypeChecker()
    return checker.check(module)


class TestBasicTypes:
    """Test basic type checking."""

    def test_valid_int_assignment(self):
        """Integer assignment should be valid."""
        errors = check("""
fn main() -> i32
    var x: i32 = 42
    return x
""")
        assert len(errors) == 0

    def test_valid_bool_assignment(self):
        """Boolean assignment should be valid."""
        errors = check("""
fn main() -> i32
    var b: bool = true
    if b
        return 1
    return 0
""")
        assert len(errors) == 0

    def test_int_type_coercion(self):
        """Integer literals should coerce to smaller int types."""
        errors = check("""
fn main() -> i32
    var x: i32 = 42
    var y: i64 = 100
    return x
""")
        assert len(errors) == 0


class TestBinaryOperators:
    """Test binary operator type checking."""

    def test_arithmetic_valid(self):
        """Arithmetic on integers should work."""
        errors = check("""
fn main() -> i32
    var x: i32 = 10
    var y: i32 = 20
    var z: i32 = x + y
    return z
""")
        assert len(errors) == 0

    def test_comparison_returns_bool(self):
        """Comparison should return bool."""
        errors = check("""
fn main() -> i32
    var x: i32 = 10
    var y: i32 = 20
    var b: bool = x < y
    if b
        return 1
    return 0
""")
        assert len(errors) == 0

    def test_logical_requires_bool(self):
        """Logical operators should require bool operands."""
        errors = check("""
fn main() -> i32
    var x: i32 = 10
    var y: i32 = 20
    var b: bool = x && y
    return 0
""")
        # x && y with integers should error
        assert len(errors) > 0
        assert any("logical operator requires bool" in str(e) for e in errors)

    def test_pointer_arithmetic(self):
        """Pointer + integer should be valid."""
        errors = check("""
fn main() -> i32
    var p: *u8 = 0 as *u8
    var q: *u8 = p + 10
    return 0
""")
        assert len(errors) == 0


class TestUnaryOperators:
    """Test unary operator type checking."""

    def test_negation_numeric(self):
        """Negation on numeric types should work."""
        errors = check("""
fn main() -> i32
    var x: i32 = 10
    var y: i32 = -x
    return y
""")
        assert len(errors) == 0

    def test_logical_not_bool(self):
        """Logical not should require bool."""
        errors = check("""
fn main() -> i32
    var x: i32 = 10
    var b: bool = !x
    return 0
""")
        assert len(errors) > 0
        assert any("logical not requires bool" in str(e) for e in errors)

    def test_address_of(self):
        """Address-of should create reference type."""
        errors = check("""
fn main() -> i32
    var x: i32 = 10
    var p: @i32 = @x
    return 0
""")
        assert len(errors) == 0

    def test_dereference(self):
        """Dereference should get inner type."""
        errors = check("""
fn main() -> i32
    var x: i32 = 10
    var p: *i32 = @x as *i32
    var y: i32 = *p
    return y
""")
        assert len(errors) == 0

    def test_dereference_non_pointer(self):
        """Dereferencing non-pointer should error."""
        errors = check("""
fn main() -> i32
    var x: i32 = 10
    var y: i32 = *x
    return y
""")
        assert len(errors) > 0
        assert any("cannot dereference non-pointer" in str(e) for e in errors)


class TestFunctionCalls:
    """Test function call type checking."""

    def test_valid_call(self):
        """Valid function call should pass."""
        errors = check("""
fn add(a: i32, b: i32) -> i32
    return a + b

fn main() -> i32
    return add(10, 20)
""")
        assert len(errors) == 0

    def test_wrong_arg_count(self):
        """Wrong argument count should error."""
        errors = check("""
fn add(a: i32, b: i32) -> i32
    return a + b

fn main() -> i32
    return add(10)
""")
        assert len(errors) > 0
        assert any("expects 2 arguments" in str(e) for e in errors)

    def test_wrong_arg_type(self):
        """Wrong argument type should error."""
        errors = check("""
fn takes_bool(b: bool) -> i32
    if b
        return 1
    return 0

fn main() -> i32
    return takes_bool(42)
""")
        assert len(errors) > 0
        assert any("expected bool" in str(e) for e in errors)

    def test_undefined_function(self):
        """Calling undefined function should error."""
        errors = check("""
fn main() -> i32
    return undefined_fn(10)
""")
        assert len(errors) > 0
        assert any("undefined function" in str(e) for e in errors)


class TestStructs:
    """Test struct type checking."""

    def test_valid_struct_lit(self):
        """Valid struct literal should pass."""
        errors = check("""
struct Point
    x: i32
    y: i32

fn main() -> i32
    var p: Point = Point { x: 10, y: 20 }
    return p.x
""")
        assert len(errors) == 0

    def test_field_access(self):
        """Field access should work."""
        errors = check("""
struct Point
    x: i32
    y: i32

fn main() -> i32
    var p: Point = Point { x: 10, y: 20 }
    var x: i32 = p.x
    return x
""")
        assert len(errors) == 0

    def test_undefined_field(self):
        """Accessing undefined field should error."""
        errors = check("""
struct Point
    x: i32
    y: i32

fn main() -> i32
    var p: Point = Point { x: 10, y: 20 }
    return p.z
""")
        assert len(errors) > 0
        assert any("no field 'z'" in str(e) for e in errors)

    def test_wrong_field_type(self):
        """Wrong field type in struct literal should error."""
        errors = check("""
struct Point
    x: i32
    y: i32

fn main() -> i32
    var p: Point = Point { x: true, y: 20 }
    return 0
""")
        assert len(errors) > 0
        assert any("expected i32" in str(e) for e in errors)


class TestControlFlow:
    """Test control flow type checking."""

    def test_if_bool_condition(self):
        """If condition must be bool."""
        errors = check("""
fn main() -> i32
    if 42
        return 1
    return 0
""")
        assert len(errors) > 0
        assert any("condition must be bool" in str(e) for e in errors)

    def test_while_bool_condition(self):
        """While condition must be bool."""
        errors = check("""
fn main() -> i32
    var x: i32 = 0
    while x
        x = x + 1
    return x
""")
        assert len(errors) > 0
        assert any("condition must be bool" in str(e) for e in errors)

    def test_if_branches_same_type(self):
        """If branches should have compatible types for expression form."""
        errors = check("""
fn main() -> i32
    var x: i32 = 0
    if true
        x = 1
    else
        x = 2
    return x
""")
        assert len(errors) == 0


class TestReturnTypes:
    """Test return type checking."""

    def test_correct_return_type(self):
        """Return type matching function signature should pass."""
        errors = check("""
fn get_int() -> i32
    return 42

fn main() -> i32
    return get_int()
""")
        assert len(errors) == 0

    def test_wrong_return_type(self):
        """Return type mismatch should error."""
        errors = check("""
fn get_int() -> i32
    return true

fn main() -> i32
    return 0
""")
        assert len(errors) > 0
        assert any("return type" in str(e) for e in errors)


class TestAssignment:
    """Test assignment type checking."""

    def test_valid_assignment(self):
        """Valid assignment should pass."""
        errors = check("""
fn main() -> i32
    var x: i32 = 0
    x = 42
    return x
""")
        assert len(errors) == 0

    def test_type_mismatch_assignment(self):
        """Type mismatch in assignment should error."""
        errors = check("""
fn main() -> i32
    var x: i32 = 0
    x = true
    return 0
""")
        assert len(errors) > 0
        assert any("cannot assign" in str(e) for e in errors)


class TestArrays:
    """Test array type checking."""

    def test_array_literal(self):
        """Array literal should work."""
        errors = check("""
fn main() -> i32
    var arr: [3]i32 = [1, 2, 3]
    return arr[0]
""")
        assert len(errors) == 0

    def test_array_index(self):
        """Array indexing should return element type."""
        errors = check("""
fn main() -> i32
    var arr: [3]i32 = [1, 2, 3]
    var x: i32 = arr[0]
    return x
""")
        assert len(errors) == 0

    def test_non_integer_index(self):
        """Non-integer index should error."""
        errors = check("""
fn main() -> i32
    var arr: [3]i32 = [1, 2, 3]
    var x: i32 = arr[true]
    return x
""")
        assert len(errors) > 0
        assert any("index must be integer" in str(e) for e in errors)


class TestEnums:
    """Test enum type checking."""

    def test_enum_variant_constructor(self):
        """Enum variant constructor should work."""
        errors = check("""
enum Option
    Some(i32)
    None

fn main() -> i32
    var opt: Option = Some(42)
    return 0
""")
        assert len(errors) == 0

    def test_unit_variant(self):
        """Unit variant should work."""
        errors = check("""
enum Option
    Some(i32)
    None

fn main() -> i32
    var opt: Option = None
    return 0
""")
        assert len(errors) == 0


class TestCasts:
    """Test cast type checking."""

    def test_integer_cast(self):
        """Integer cast should work."""
        errors = check("""
fn main() -> i32
    var x: i64 = 100
    var y: i32 = x as i32
    return y
""")
        assert len(errors) == 0

    def test_pointer_cast(self):
        """Pointer cast should work."""
        errors = check("""
fn main() -> i32
    var x: i32 = 0
    var p: *i32 = @x as *i32
    return 0
""")
        assert len(errors) == 0


class TestSpanStringLiterals:
    """Test span string literal type checking: s"..." -> Span<u8>"""

    def test_span_string_produces_span_u8(self):
        """s"..." should produce Span<u8> type."""
        # Note: This currently requires Span<u8> to be defined or builtin.
        # For now we just test that the syntax parses and type checks.
        errors = check("""
struct Span<T>
    ptr: *T
    len: i64

fn main() -> i32
    let s: Span<u8> = s"hello"
    return 0
""")
        assert len(errors) == 0

    def test_span_string_empty(self):
        """Empty span string should also work."""
        errors = check("""
struct Span<T>
    ptr: *T
    len: i64

fn main() -> i32
    let s: Span<u8> = s""
    return 0
""")
        assert len(errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
