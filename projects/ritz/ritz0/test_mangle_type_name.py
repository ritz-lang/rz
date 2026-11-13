"""Every type spells a distinct name in `mangle_type_name` (AGAST #2270).

`mangle_type_name` named NamedType, PtrType, RefType, ArrayType and SliceType
and returned "unknown" for everything else. Every tuple, fn type, `dyn` trait,
SIMD vector and union therefore mangled the same, so `wrap<Result<(), Er>>`
and `wrap<Result<(i64, i64), Er>>` were both `wrap$Result_unknown_Er`. The
second instantiation reused the first, and ritz0 rejected a valid program:

    argument 1 of `wrap$Result_unknown_Er` has the wrong type

A tuple spells the way the emitter's `_type_to_name_suffix` spells it
(`unit`, `tuple_A_B`), so a type has one name whether or not the
monomorphizer routes it.
"""

import pytest
import ritz_ast as rast
from monomorph import mangle_generic_name, mangle_type_name

pytestmark = pytest.mark.unit


def named(name, *args):
    return rast.NamedType(None, name, list(args))


I32 = named("i32")
I64 = named("i64")


def tup(*elems):
    return rast.TupleType(None, list(elems))


def fn(params, ret):
    return rast.FnType(None, list(params), ret)


class TestTuple:
    def test_unit(self):
        assert mangle_type_name(tup()) == "unit"

    def test_pair(self):
        assert mangle_type_name(tup(I64, I64)) == "tuple_i64_i64"

    def test_nested_tuple_elements_mangle(self):
        assert mangle_type_name(tup(tup(), I32)) == "tuple_unit_i32"

    def test_in_generic_args(self):
        assert mangle_type_name(named("Result", tup(), named("Er"))) == (
            "Result_unit_Er")
        assert mangle_generic_name("wrap", [named("Result", tup(I64, I64),
                                                  named("Er"))]) == (
            "wrap$Result_tuple_i64_i64_Er")


class TestFn:
    def test_fn_names_params_and_ret(self):
        assert mangle_type_name(fn([I32, I64], I32)) == "fn2_i32_i64_ret_i32"

    def test_fn_without_ret_is_unit(self):
        assert mangle_type_name(fn([], None)) == "fn0_ret_unit"

    def test_ret_and_params_are_distinct(self):
        assert mangle_type_name(fn([I32], I64)) != mangle_type_name(
            fn([I64], I32))


class TestOtherTypes:
    def test_dyn(self):
        assert mangle_type_name(rast.DynType(None, "Animal")) == "dyn_Animal"

    def test_dyn_with_args(self):
        ty = rast.DynType(None, "Iterator", [I32])
        assert mangle_type_name(ty) == "dyn_Iterator_i32"

    def test_vector(self):
        assert mangle_type_name(rast.VectorType(None, 4, I32)) == "vec4_i32"

    def test_union(self):
        ty = rast.UnionType(None, [I32, named("Er")])
        assert mangle_type_name(ty) == "union2_i32_Er"


class TestArray:
    """AGAST #2843: the size is the folded integer, not its AST node.

    The parser leaves `[2]i8` in a call's type argument as an IntLit, which
    printed as `arrIntLit(span=/path/main.ritz:10:27, value=2)_i8`: a symbol
    that embedded the build path and column, so one instance had a name per
    module and the IR changed with the build directory.
    """

    def test_int_literal_size_prints_its_value(self):
        ty = rast.ArrayType(None, rast.IntLit(None, 2), named("i8"))
        assert mangle_type_name(ty) == "arr2_i8"

    def test_folded_int_size(self):
        ty = rast.ArrayType(None, 3, I64)
        assert mangle_type_name(ty) == "arr3_i64"

    def test_pointer_to_array(self):
        arr = rast.ArrayType(None, rast.IntLit(None, 2), named("i8"))
        ty = rast.PtrType(None, arr, False)
        assert mangle_type_name(ty) == "ptr_arr2_i8"

    def test_unfolded_size_is_an_error(self):
        """A size const eval never reached must not print an AST node."""
        ty = rast.ArrayType(None, rast.Ident(None, "N"), named("i8"))
        with pytest.raises(TypeError, match="Ident"):
            mangle_type_name(ty)


def test_distinct_types_never_share_a_name():
    """The defect: these all used to spell `unknown`."""
    types = [
        tup(), tup(I64, I64), tup(I32),
        fn([], None), fn([I32], I32), fn([I64], I32),
        rast.DynType(None, "A"), rast.DynType(None, "B"),
        rast.VectorType(None, 4, I32), rast.VectorType(None, 2, I64),
        rast.UnionType(None, [I32, I64]), rast.UnionType(None, [I64, I32]),
    ]
    names = [mangle_type_name(t) for t in types]
    assert "unknown" not in names
    assert len(set(names)) == len(names), names


def test_unhandled_type_node_is_an_error():
    """A new Type node must get a spelling, not silently share one."""
    class Mystery(rast.Type):
        pass

    with pytest.raises(TypeError, match="Mystery"):
        mangle_type_name(Mystery(None))
