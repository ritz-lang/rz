"""AGAST #2832: an array type argument names its instance.

ritz1 spelled no array type argument at all, so `Box<[2]i8>` and `Box<[4]i64>`
were one struct, `%Box$ = {i64, i64}`, and `first<*[2]i8>` / `first<*[3]i64>`
one function, `@first$`.  Its T was void, so a body that used it failed to
compile.  A field after the array silently read the wrong offset.

ritz1 now spells `[N]E` as `arrN_E` and `*[N]E` as `ptr_arrN_E`, the form
ritz0's mangle_type_name spells (`arr{size}_{inner}`), and the monomorphizer
takes `arrN_E` back to an array T.  ritz0 is the oracle.

ritz0 printed the size's AST node there, `first$arrIntLit(span=/tmp/.../
main.ritz:10:27, value=2)_i8`, until #2843: the symbol named the build path
and column.  It now prints the folded size, so both compilers agree.

Each program returns 0, or the number of the check that failed.
"""

import re

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# Box<[2]i8> is 16 bytes with tag at 8; Box<[4]i64> is 40 with tag at 32.
# Reading the tag at its raw offset tells the two layouts apart.
BOX = (
    "struct Box<T>\n    v: T\n    tag: i64\n\n"
    "fn put2(b: *Box<[2]i8>, t: i64)\n    b.tag = t\n\n"
    "fn put4(b: *Box<[4]i64>, t: i64)\n    b.tag = t\n\n"
    "pub fn main() -> i32\n"
    "    var a: Box<[2]i8>\n"
    "    var b: Box<[4]i64>\n"
    "    put2(@a, 3)\n"
    "    put4(@b, 5)\n"
    "    b.v[3] = 77\n"
    "    let ta: *i64 = ((@a as *u8) + 8) as *i64\n"
    "    let tb: *i64 = ((@b as *u8) + 32) as *i64\n"
    "    let v3: *i64 = ((@b as *u8) + 24) as *i64\n"
    "    if *ta != 3\n        return 1\n"
    "    if *tb != 5\n        return 2\n"
    "    if *v3 != 77\n        return 3\n"
    "    0\n"
)

# Element kinds other than a primitive: (argument, offset of tag).  The last
# element is written through the field too, so a short array would put it on
# the tag.  (`sizeof(Box<[2]*u8>)` parses on neither compiler, so no sizeof.)
ELEMS = {
    "struct": ("[3]P", 48, "x.v[2].b = 1"),
    "ptr_prim": ("[2]*u8", 16, "x.v[1] = null"),
    "ptr_struct": ("[5]*P", 40, "x.v[4] = null"),
}


def _elem_box(arg, tag_at, store):
    return (
        "struct P\n    a: i64\n    b: i64\n\n"
        "struct Box<T>\n    v: T\n    tag: i64\n\n"
        "pub fn main() -> i32\n"
        f"    var x: Box<{arg}>\n"
        "    x.tag = 6\n"
        f"    {store}\n"
        f"    let t: *i64 = ((@x as *u8) + {tag_at}) as *i64\n"
        "    if *t != 6\n        return 1\n"
        "    0\n"
    )


# Two-parameter template: the multi-argument path substitutes each argument.
PAIR = (
    "struct Pair<A, B>\n    a: A\n    b: B\n\n"
    "pub fn main() -> i32\n"
    "    var p: Pair<[3]i64, i64>\n"
    "    var q: Pair<[1]i8, i64>\n"
    "    p.b = 9\n"
    "    q.b = 4\n"
    "    let pb: *i64 = ((@p as *u8) + 24) as *i64\n"
    "    let qb: *i64 = ((@q as *u8) + 8) as *i64\n"
    "    if *pb != 9\n        return 1\n"
    "    if *qb != 4\n        return 2\n"
    "    0\n"
)

# A generic fn at two `*[N]E` arguments: each instance returns its own
# pointer, and indexing it reads that array's element width.
FIRST = (
    "fn first<T>(a: T, z: *i64) -> T\n"
    "    *z = *z + 1\n"
    "    a\n\n"
    "pub fn main() -> i32\n"
    "    var x: [2]i8 = [1, 2]\n"
    "    var y: [3]i64 = [5, 6, 7]\n"
    "    var z: i64 = 0\n"
    "    let px: *[2]i8 = first<*[2]i8>(@x, @z)\n"
    "    let py: *[3]i64 = first<*[3]i64>(@y, @z)\n"
    "    if px[1] != 2\n        return 1\n"
    "    if py[2] != 7\n        return 2\n"
    "    if z != 2\n        return 3\n"
    "    0\n"
)

# `c:& T` at two array arguments: each instance's param points at its own
# array, so the argument is accepted and the write lands in it.
LENT = (
    "fn id<T>(c:& T) -> @&T\n    return @&c\n\n"
    "pub fn main() -> i32\n"
    "    var a: [2]i8 = [1, 1]\n"
    "    var b: [3]i64 = [1, 1, 1]\n"
    "    let p: @&[2]i8 = id<[2]i8>(@&a)\n"
    "    let q: @&[3]i64 = id<[3]i64>(@&b)\n"
    "    *p = [4, 5]\n"
    "    *q = [6, 7, 8]\n"
    "    if a[1] != 5\n        return 1\n"
    "    if b[2] != 8\n        return 2\n"
    "    0\n"
)

# sizeof(T) at two array arguments: the instance that would be shared must
# answer for its own T.
SIZEOF = (
    "fn sz<T>() -> i64\n    sizeof(T)\n\n"
    "pub fn main() -> i32\n"
    "    if sz<[2]i8>() != 2\n        return 1\n"
    "    if sz<[3]i64>() != 24\n        return 2\n"
    "    if sz<*[3]i64>() != 8\n        return 3\n"
    "    0\n"
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_at_two_array_args(run_with, compiler):
    """`Box<[2]i8>` and `Box<[4]i64>` are two layouts, not one `%Box$`."""
    assert run_with(compiler, "box", BOX) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("elem", sorted(ELEMS))
def test_struct_at_array_of_elem(run_with, compiler, elem):
    """`Box<[3]P>`, `Box<[2]*u8>`, `Box<[5]*P>` lay out their array."""
    assert run_with(compiler, f"elem_{elem}", _elem_box(*ELEMS[elem])) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_multi_param_struct_array_arg(run_with, compiler):
    """`Pair<[3]i64, i64>`: the array argument sizes field a."""
    assert run_with(compiler, "pair", PAIR) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_fn_at_two_ptr_array_args(run_with, compiler):
    """`first<*[2]i8>` and `first<*[3]i64>` are two instances, T a pointer."""
    assert run_with(compiler, "first", FIRST) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_lent_param_at_two_array_args(run_with, compiler):
    """`id<[2]i8>(@&a)` and `id<[3]i64>(@&b)` through `c:& T`."""
    assert run_with(compiler, "lent", LENT) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_sizeof_array_type_param(run_with, compiler):
    """`sizeof(T)` at T = `[2]i8`, `[3]i64` and `*[3]i64`."""
    assert run_with(compiler, "sizeof", SIZEOF) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_mangled_names(compile_with, compiler):
    """Each array argument spells as `arrN_E` / `ptr_arrN_E` on every compiler.

    ritz1 named none at all before #2832; ritz0 named the size's AST node
    (source path and column included) before #2843.
    """
    comp, ll, _ = compile_with(compiler, "names", FIRST)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    defined = set(re.findall(r'define [^@]*@"?(first[^"(]*)', ir))
    assert defined == {"first$ptr_arr2_i8", "first$ptr_arr3_i64"}
    assert "IntLit" not in ir and "span=" not in ir
    comp, ll, _ = compile_with(compiler, "box_names", BOX)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    # ritz0 qualifies a struct by module: `%"struct.ritz_module_1.Box$arr2_i8"`.
    structs = set(re.findall(r'%"?(?:struct\.[\w.]+\.)?(Box\$[^" ]*)"? = type', ir))
    assert structs == {"Box$arr2_i8", "Box$arr4_i64"}
