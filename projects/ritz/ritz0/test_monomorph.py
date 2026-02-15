"""
Tests for the Ritz monomorphization pass.
"""

import pytest
from parser import parse
from monomorph import monomorphize, mangle_generic_name, mangle_type_name
import ritz_ast as rast


class TestMangling:
    """Test name mangling functions."""

    def test_mangle_simple_type(self):
        ty = rast.NamedType(None, "i32", [])
        assert mangle_type_name(ty) == "i32"

    def test_mangle_ptr_type(self):
        inner = rast.NamedType(None, "u8", [])
        ty = rast.PtrType(None, inner, False)
        assert mangle_type_name(ty) == "ptr_u8"

    def test_mangle_ptr_mut_type(self):
        inner = rast.NamedType(None, "i32", [])
        ty = rast.PtrType(None, inner, True)
        assert mangle_type_name(ty) == "ptrmut_i32"

    def test_mangle_generic_name_single(self):
        type_args = [rast.NamedType(None, "i32", [])]
        assert mangle_generic_name("Pair", type_args) == "Pair$i32"

    def test_mangle_generic_name_multiple(self):
        type_args = [
            rast.NamedType(None, "i32", []),
            rast.PtrType(None, rast.NamedType(None, "u8", []), False)
        ]
        assert mangle_generic_name("Map", type_args) == "Map$i32_ptr_u8"


class TestMonomorphization:
    """Test the full monomorphization pass."""

    def test_generic_struct_instantiation(self):
        source = """
struct Pair<T>
    first: T
    second: T

fn main() -> i32
    var p: Pair<i32> = Pair<i32> { first: 1, second: 2 }
    0
"""
        mod = parse(source)
        result = monomorphize(mod)

        # Should have removed the generic Pair<T> and added Pair$i32
        struct_names = [item.name for item in result.items if isinstance(item, rast.StructDef)]
        assert "Pair$i32" in struct_names
        assert "Pair" not in struct_names  # Generic should be removed

        # The Pair$i32 struct should have i32 fields
        pair_i32 = next(item for item in result.items
                        if isinstance(item, rast.StructDef) and item.name == "Pair$i32")
        assert pair_i32.fields[0][1].name == "i32"
        assert pair_i32.fields[1][1].name == "i32"

    def test_generic_function_instantiation(self):
        source = """
fn identity<T>(x: T) -> T
    x

fn main() -> i32
    identity<i32>(42)
"""
        mod = parse(source)
        result = monomorphize(mod)

        # Should have removed generic identity<T> and added identity$i32
        fn_names = [item.name for item in result.items if isinstance(item, rast.FnDef)]
        assert "identity$i32" in fn_names
        assert "identity" not in fn_names  # Generic should be removed
        assert "main" in fn_names

    def test_call_rewritten_to_specialized(self):
        source = """
fn double<T>(x: T) -> T
    x

fn main() -> i32
    double<i32>(21)
"""
        mod = parse(source)
        result = monomorphize(mod)

        # Find main function
        main = next(item for item in result.items
                    if isinstance(item, rast.FnDef) and item.name == "main")

        # The call should now be to double$i32, not double<i32>
        call = main.body.expr
        assert isinstance(call, rast.Call)
        assert call.func.name == "double$i32"
        assert call.type_args == []  # Type args should be removed

    def test_struct_literal_rewritten(self):
        source = """
struct Box<T>
    value: T

fn main() -> i32
    var b: Box<i32> = Box<i32> { value: 42 }
    0
"""
        mod = parse(source)
        result = monomorphize(mod)

        # Find main function
        main = next(item for item in result.items
                    if isinstance(item, rast.FnDef) and item.name == "main")

        # The struct literal should use Box$i32
        var_stmt = main.body.stmts[0]
        assert isinstance(var_stmt, rast.VarStmt)
        struct_lit = var_stmt.value
        assert isinstance(struct_lit, rast.StructLit)
        assert struct_lit.name == "Box$i32"
        assert struct_lit.type_args == []

    def test_type_annotation_rewritten(self):
        source = """
struct Wrapper<T>
    inner: T

fn main() -> i32
    var w: Wrapper<i32> = Wrapper<i32> { inner: 5 }
    0
"""
        mod = parse(source)
        result = monomorphize(mod)

        # Find main function
        main = next(item for item in result.items
                    if isinstance(item, rast.FnDef) and item.name == "main")

        # The type annotation should be Wrapper$i32
        var_stmt = main.body.stmts[0]
        assert isinstance(var_stmt, rast.VarStmt)
        assert var_stmt.type.name == "Wrapper$i32"
        assert var_stmt.type.args == []

    def test_multiple_instantiations(self):
        source = """
struct Pair<T>
    first: T
    second: T

fn main() -> i32
    var p1: Pair<i32> = Pair<i32> { first: 1, second: 2 }
    var p2: Pair<i64> = Pair<i64> { first: 10, second: 20 }
    0
"""
        mod = parse(source)
        result = monomorphize(mod)

        struct_names = [item.name for item in result.items if isinstance(item, rast.StructDef)]
        assert "Pair$i32" in struct_names
        assert "Pair$i64" in struct_names
        assert "Pair" not in struct_names

    def test_non_generic_unchanged(self):
        source = """
struct Point
    x: i32
    y: i32

fn add(a: i32, b: i32) -> i32
    a + b

fn main() -> i32
    var p: Point = Point { x: 1, y: 2 }
    add(p.x, p.y)
"""
        mod = parse(source)
        result = monomorphize(mod)

        # Non-generic struct and function should remain
        struct_names = [item.name for item in result.items if isinstance(item, rast.StructDef)]
        fn_names = [item.name for item in result.items if isinstance(item, rast.FnDef)]
        assert "Point" in struct_names
        assert "add" in fn_names
        assert "main" in fn_names

    def test_pointer_type_arg(self):
        source = """
struct Wrapper<T>
    value: T

fn main() -> i32
    var w: Wrapper<*u8> = Wrapper<*u8> { value: 0 as *u8 }
    0
"""
        mod = parse(source)
        result = monomorphize(mod)

        struct_names = [item.name for item in result.items if isinstance(item, rast.StructDef)]
        assert "Wrapper$ptr_u8" in struct_names

    def test_generic_param_used_in_function_body(self):
        source = """
struct Pair<T>
    first: T
    second: T

fn swap<T>(p: *Pair<T>) -> i32
    let tmp: T = p.first
    p.first = p.second
    p.second = tmp
    return 0

fn main() -> i32
    var p: Pair<i32> = Pair<i32> { first: 1, second: 2 }
    swap<i32>(@p)
"""
        mod = parse(source)
        result = monomorphize(mod)

        # Should have Pair$i32 struct
        struct_names = [item.name for item in result.items if isinstance(item, rast.StructDef)]
        assert "Pair$i32" in struct_names

        # Should have swap$i32 function
        fn_names = [item.name for item in result.items if isinstance(item, rast.FnDef)]
        assert "swap$i32" in fn_names

        # swap$i32 should take *Pair$i32
        swap_fn = next(item for item in result.items
                       if isinstance(item, rast.FnDef) and item.name == "swap$i32")
        param_type = swap_fn.params[0].type
        assert isinstance(param_type, rast.PtrType)
        assert param_type.inner.name == "Pair$i32"


class TestVisibilityPreservation:
    """Test that is_pub visibility is preserved through monomorphization."""

    def test_pub_fn_preserved(self):
        """pub fn visibility should be preserved after monomorphization."""
        source = """
pub fn exported() -> i32
    42

fn private() -> i32
    0
"""
        mod = parse(source)
        result = monomorphize(mod)

        exported = next(item for item in result.items
                       if isinstance(item, rast.FnDef) and item.name == "exported")
        private = next(item for item in result.items
                      if isinstance(item, rast.FnDef) and item.name == "private")

        assert exported.is_pub is True
        assert private.is_pub is False

    def test_generic_fn_visibility_preserved(self):
        """pub generic fn should have is_pub preserved after specialization."""
        source = """
pub fn identity<T>(x: T) -> T
    x

fn main() -> i32
    identity<i32>(42)
"""
        mod = parse(source)
        result = monomorphize(mod)

        # The specialized identity$i32 should inherit is_pub
        identity_i32 = next(item for item in result.items
                           if isinstance(item, rast.FnDef) and item.name == "identity$i32")
        assert identity_i32.is_pub is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
