"""AGAST #2822: a `let`'s annotation survives a generic type arg in its initializer.

ritz1's stmt_var_decl read the parser's last_type_name / last_array_* after
the initializer was parsed, so `let p: *A = pick<*B>(..)` typed p as `*B`
(field GEPs and stride of B: silent miscompile) and `var a: [4]i64 =
[.., sizeof([2]i8)]` took the `[2]i8` shape.  #2805 latched the pointee slots in
capture_var_type; this latches the struct name and array shape too.
ritz0 is the oracle.

A and B put `b` at different offsets and differ in size, so reading the
wrong layout returns a different number rather than failing to compile.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

STRUCTS = (
    "struct A\n    a: i64\n    b: i64\n\n"
    "struct B\n    b: i32\n\n"
    "fn pick<T>(p: *A, t: T) -> *A\n    return p\n\n"
)

MAIN_AB = (
    "pub fn main() -> i32\n"
    "    var xs: [2]A\n"
    "    xs[0].a = 1\n    xs[0].b = 3\n"
    "    xs[1].a = 2\n    xs[1].b = 7\n"
    "    var y: B\n    y.b = 99\n"
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ptr_struct_field(run_with, compiler):
    """`p.b` on `let p: *A = pick<*B>(..)` reads A's b (offset 8), not B's."""
    prog = STRUCTS + MAIN_AB + (
        "    let p: *A = pick<*B>(@xs[0], @y)\n"
        "    return p.b as i32\n"
    )
    assert run_with(compiler, "field", prog) == 3


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ptr_struct_stride(run_with, compiler):
    """`(*(p + 1)).b` strides sizeof(A) = 16, not sizeof(B) = 4."""
    prog = STRUCTS + MAIN_AB + (
        "    let p: *A = pick<*B>(@xs[0], @y)\n"
        "    return (*(p + 1)).b as i32\n"
    )
    assert run_with(compiler, "stride", prog) == 7


# An array initializer re-sets last_array_* through any array type in it.  A
# generic `<[N]T>` call in an array literal is not instantiated by ritz1 yet,
# and `*f(..)` is no array initializer there, so these use `sizeof([N]T)`,
# which parses the type the same way.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_array_shape(run_with, compiler):
    """`var a: [4]i64 = [.. sizeof([2]i8)]`: a is four i64s, not two i8s."""
    prog = (
        "pub fn main() -> i32\n"
        "    var a: [4]i64 = [5, 300, 1000, 3998 + sizeof([2]i8)]\n"
        "    return (a[0] + a[1] + a[2] + a[3] - 5300) as i32\n"
    )
    assert run_with(compiler, "array", prog) == 5


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_array_of_struct_elem(run_with, compiler):
    """`var a: [2]A = [mk(sizeof([1]B)), ..]`: elements are A (stride 16, b at 8)."""
    prog = STRUCTS + (
        "fn mk(t: i64) -> A\n    var r: A\n    r.a = t\n    r.b = t + 1\n    return r\n\n"
        "pub fn main() -> i32\n"
        "    var a: [2]A = [mk(sizeof([1]B)), mk(20)]\n"
        "    return ((a[1].b - a[0].b) * 10 + a[0].a) as i32\n"
    )
    assert run_with(compiler, "array_struct", prog) == 164


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ptr_array_pointee(run_with, compiler):
    """`let q: *[4]i64 = ..<[2]i8>..`: `q[3]` reads the fourth i64."""
    prog = (
        "fn pa<T>(a: *[4]i64) -> *[4]i64\n    return a\n\n"
        "pub fn main() -> i32\n"
        "    var src: [4]i64\n"
        "    src[0] = 5\n    src[1] = 6\n    src[2] = 7\n    src[3] = 8\n"
        "    let q: *[4]i64 = pa<[2]i8>(@src)\n"
        "    return (q[3] + q[1] * 10) as i32\n"
    )
    assert run_with(compiler, "ptr_array", prog) == 68


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_ptr_prim_not_named_by_generic_struct_arg(run_with, compiler):
    """`let p: *i32 = pick<*B>(..)` stays a `*i32`: B's name doesn't leak onto it."""
    prog = (
        "struct B\n    b: i64\n\n"
        "fn pick<T>(a: *i32, b: T) -> *i32\n    return a\n\n"
        "pub fn main() -> i32\n"
        "    var a: [3]i32\n    a[0] = 1\n    a[1] = 2\n    a[2] = 7\n"
        "    var y: B\n"
        "    let p: *i32 = pick<*B>(@a[0], @y)\n"
        "    return *(p + 2)\n"
    )
    assert run_with(compiler, "ptr_prim", prog) == 7


# A typed `let` nested in the initializer (a match block arm) runs
# capture_var_type again before the outer decl is built.  The latch is per
# decl: the outer one must not take the inner's annotation (or lose its own,
# as `let q: i32` once cleared it: "unhandled EXPR_MEMBER in assignment").
NESTED = "pub fn main() -> i32\n    return go(0)\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("inner", ["let q: i32 = 1", "let q: *B = @y", "let q: [2]i8 = [1, 2]"])
def test_nested_let_keeps_outer_ptr_struct(run_with, compiler, inner):
    """`let p: *A = match k / 0 => <inner let>; @xs[0]`: p.b is A's b."""
    prog = STRUCTS + (
        "fn go(k: i32) -> i32\n"
        "    var xs: [2]A\n"
        "    xs[0].a = 1\n    xs[0].b = 3\n"
        "    xs[1].a = 2\n    xs[1].b = 7\n"
        "    var y: B\n    y.b = 99\n"
        "    let p: *A = match k\n"
        "        0 =>\n"
        f"            {inner}\n"
        "            @xs[0]\n"
        "        _ => @xs[0]\n"
        "    p.b = 5\n"
        "    return (*(p + 1)).b as i32 * 10 + xs[0].b as i32\n\n"
    ) + NESTED
    assert run_with(compiler, "nested_ptr", prog) == 75


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_nested_let_keeps_outer_ptr_array(run_with, compiler):
    """`let q: *[4]i64 = match k / 0 => let z: *[2]i8 ..`: q[3] is the 4th i64."""
    prog = (
        "fn go(k: i32) -> i32\n"
        "    var src: [4]i64\n"
        "    src[0] = 5\n    src[1] = 6\n    src[2] = 7\n    src[3] = 8\n"
        "    var t: [2]i8\n"
        "    let q: *[4]i64 = match k\n"
        "        0 =>\n"
        "            let z: *[2]i8 = @t\n"
        "            @src\n"
        "        _ => @src\n"
        "    return (q[3] + q[1] * 10) as i32\n\n"
    ) + NESTED
    assert run_with(compiler, "nested_ptr_array", prog) == 68
