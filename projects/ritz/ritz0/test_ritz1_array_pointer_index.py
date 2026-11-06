"""AGAST #2321: `p[i]` on a pointer to an array, `p` a `*[N]T`, `@[N]T` or `@&[N]T`.

    fn f(p: *[3]i32) -> i32
        return p[1]         # ritz0 20, ritz1 0

The pointee was TYPE_ARRAY, which no element path knew, so a read took the byte
path: `p[1]` was one byte at offset 1. A store took the i64 path, so `p[1] = 7`
wrote 8 bytes at offset 8, past `a[1]`, with no diagnostic. `@&` failed at clang.

What `p[i]` means, measured on ritz0, the same for all three pointer kinds:

    read            element i, stride T, of the array behind the pointer
    `p[i] = scalar` refused, and `p[i] += v` with it
    `p[lo..hi]`     refused

Two forms ritz0 lowers at stride `[N]T`, disagreeing with its own read: `@p[i]`,
and `p[i] = <a whole [N]T>`. ritz0 isn't an oracle for those (#2330), so ritz1
refuses them rather than pick a stride. RITZ0_STRIDES_BY_THE_ARRAY pins both.

A byte-wide element hides all of this, and `[2]i32` is 8 bytes, which hides a
wrong-size access, so the grid covers several sizes and element types.
"""

from pathlib import Path

import pytest

from test_borrow_param_ref_field import _compile, _run

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]

# The pointer's spelling, and the `@` that makes one.
KINDS = {"pointer": ("*", "@"), "reference": ("@", "@"), "mut_reference": ("@&", "@&")}

# A fill value, then two others.  bool has only two, so `first` differs from the
# fill and `second` doesn't.
SCALARS = {
    "i8": ("-2", "-3", "-5"),
    "u8": ("200", "201", "202"),
    "i16": ("-300", "-301", "-302"),
    "u16": ("40000", "40001", "40002"),
    "i32": ("-70000", "-70001", "-70002"),
    "u32": ("3000000000", "3000000001", "3000000002"),
    "i64": ("-5000000000", "-5000000001", "-5000000002"),
    "u64": ("5000000000", "5000000001", "5000000002"),
    "f32": ("1.5", "2.5", "3.5"),
    "f64": ("1.5", "2.5", "3.5"),
    "bool": ("true", "false", "true"),
}
SIZES = (2, 3, 8, 17)


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    """_compile, by name.  The gate builds ritz1_selfhosted before pytest."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    """_run, by name."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


def _grid_size(kind: str, addr: str, ty: str, n: int, base: int) -> tuple[str, str]:
    """The fns reading `[n]ty` through `kind`, and the checks in main."""
    fill, first, second = SCALARS[ty]
    last = n - 1
    decls = f"""
fn read_const{n}(p: {kind}[{n}]{ty}) -> {ty}
    return p[{last}]

fn read_var{n}(p: {kind}[{n}]{ty}, i: i32) -> {ty}
    return p[i]
"""
    main = f"""\
    var a{n}: [{n}]{ty}
    var k{n}: i32 = 0
    while k{n} < {n}
        a{n}[k{n}] = {fill}
        k{n} = k{n} + 1
    a{n}[{last}] = {first}
    a{n}[0] = {second}
    if read_const{n}({addr}a{n}) != {first}
        return {base + 1}
    if read_var{n}({addr}a{n}, {last}) != {first}
        return {base + 2}
    if read_var{n}({addr}a{n}, 0) != {second}
        return {base + 3}
"""
    return decls, main


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("ty", sorted(SCALARS))
def test_every_kind_element_type_and_size(run_with, ty, kind, compiler):
    spelled, addr = KINDS[kind]
    parts = [_grid_size(spelled, addr, ty, n, 10 * (k + 1)) for k, n in enumerate(SIZES)]
    program = ("".join(d for d, _ in parts) + "\npub fn main() -> i32\n"
               + "".join(m for _, m in parts) + "    return 0\n")
    assert run_with(compiler, ty, program) == 0


# Stride T, not `[N]T`: row 0's pointer reads row 0, and never reaches row 1.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_the_stride_is_the_element_not_the_array(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = f"""\
fn f(p: {spelled}[3]i32) -> i32
    return p[1]

pub fn main() -> i32
    var a: [2][3]i32
    a[0][1] = 2
    a[1][1] = 5
    a[1][0] = 4
    return f({addr}a[0])
"""
    assert run_with(compiler, "stride", program) == 2


def _a(body: str) -> str:
    return "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n" + body


# Every way a local comes to hold the pointer, and every value context.  Each
# program returns 20 unless it says otherwise.
READS = {
    "let_pointer": _a("    let p: *[3]i32 = @a\n    return p[1]\n"),
    "let_reference": _a("    let p: @[3]i32 = @a\n    return p[1]\n"),
    "let_mut_reference": _a("    let p: @&[3]i32 = @&a\n    return p[1]\n"),
    "infer_addr": _a("    let p = @a\n    return p[1]\n"),
    "infer_var_addr": _a("    var p = @a\n    return p[1]\n"),
    "infer_addr_mut": _a("    let p = @&a\n    return p[1]\n"),
    "infer_copy_pointer": "fn f(p: *[3]i32) -> i32\n    let q = p\n    return q[1]\n\n" + _a("    return f(@a)\n"),
    "infer_copy_reference": "fn f(p: @[3]i32) -> i32\n    let q = p\n    return q[1]\n\n" + _a("    return f(@a)\n"),
    "infer_copy_mut_reference": "fn f(p: @&[3]i32) -> i32\n    let q = p\n    return q[1]\n\n" + _a("    return f(@&a)\n"),
    "infer_copy_twice": "fn f(p: *[3]i32) -> i32\n    let q = p\n    let r = q\n    return r[1]\n\n" + _a("    return f(@a)\n"),
    "infer_from_lent": "fn f(a:& [3]i32) -> i32\n    let p = @a\n    return p[1]\n\n" + _a("    return f(@a)\n"),
    "infer_from_by_value": "fn f(a: [3]i32) -> i32\n    let p = @a\n    return p[1]\n\n" + _a("    return f(a)\n"),
    "infer_from_global": "var g: [3]i32\n\npub fn main() -> i32\n    g[1] = 20\n    let p = @g\n    return p[1]\n",
    "infer_mut_from_global": "var g: [3]i32\n\npub fn main() -> i32\n    g[1] = 20\n    let p = @&g\n    return p[1]\n",
    "infer_from_field": "struct H\n    a: [3]i32\n\npub fn main() -> i32\n    var h: H\n    h.a[1] = 20\n    let p = @h.a\n    return p[1]\n",
    "infer_in_a_loop": "pub fn main() -> i32\n    var a: [3]i32 = [5, 7, 8]\n    var i: i32 = 0\n    var t: i32 = 0\n    while i < 3\n        let p = @a\n        t = t + p[i]\n        i = i + 1\n    return t\n",
    "reassigned": _a("    var b: [3]i32 = [1, 20, 3]\n    var p: *[3]i32 = @a\n    p = @b\n    return p[1]\n"),
    "method": "struct S\n    x: i32\n\nimpl S\n    fn get(self, p: *[3]i32) -> i32\n        return p[1]\n\n"
              + _a("    var s: S\n    return s.get(@a)\n"),
    "generic_pointer": "fn f<T>(p: *[3]T) -> T\n    return p[1]\n\n" + _a("    return f<i32>(@a)\n"),
    "generic_reference": "fn f<T>(p: @[3]T) -> T\n    return p[1]\n\n" + _a("    return f<i32>(@a)\n"),
    "generic_mut_reference": "fn f<T>(p: @&[3]T) -> T\n    return p[1]\n\n" + _a("    return f<i32>(@&a)\n"),
    "binary": "fn f(p: *[3]i32) -> i32\n    return p[1] + p[0] - p[0]\n\n" + _a("    return f(@a)\n"),
    "compare": "fn f(p: @[3]i32) -> i32\n    if p[1] == 20\n        return 20\n    return 1\n\n" + _a("    return f(@a)\n"),
    "argument": "fn g(x: i32) -> i32\n    return x\n\nfn f(p: @[3]i32) -> i32\n    return g(p[1])\n\n" + _a("    return f(@a)\n"),
    "cast": "fn f(p: *[3]i32) -> i32\n    let x: i64 = p[1] as i64\n    return x as i32\n\n" + _a("    return f(@a)\n"),
    "infer_element": "fn f(p: *[3]i32) -> i32\n    let x = p[1]\n    return x\n\n" + _a("    return f(@a)\n"),
    "index_is_an_element": "fn f(p: *[3]i32, q: *[3]i32) -> i32\n    return p[q[0]]\n\n"
                           "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n    var i: [3]i32 = [1, 0, 0]\n    return f(@a, @i)\n",
    "cast_to_element_pointer": "fn f(p: *[3]i32) -> i32\n    let q: *i32 = p as *i32\n    return q[1]\n\n" + _a("    return f(@a)\n"),
    "negative_stays_negative": "fn f(p: *[3]i32) -> i32\n    let x: i64 = p[1] as i64\n    if x < 0\n        return 20\n    return 1\n\n"
                               "pub fn main() -> i32\n    var a: [3]i32 = [1, -2, 3]\n    return f(@a)\n",
    "unsigned_stays_positive": "fn f(p: *[3]u32) -> i32\n    let x: u64 = p[1] as u64\n    if x > 2147483648\n        return 20\n    return 1\n\n"
                               "pub fn main() -> i32\n    var a: [3]u32 = [1, 3000000000, 3]\n    return f(@a)\n",
    "double_arithmetic": "fn f(p: *[3]f64) -> f64\n    return p[1] + p[2]\n\n"
                         "pub fn main() -> i32\n    var a: [3]f64 = [1.0, 19.5, 0.5]\n    return f(@a) as i32\n",
    "float_let": "fn f(p: @[3]f32) -> i32\n    let x: f32 = p[1]\n    return x as i32\n\n"
                 "pub fn main() -> i32\n    var a: [3]f32 = [1.0, 20.5, 0.5]\n    return f(@a)\n",
    "bool_condition": "fn f(p: *[3]bool) -> i32\n    if p[1]\n        return 20\n    return 1\n\n"
                      "pub fn main() -> i32\n    var a: [3]bool\n    a[1] = true\n    return f(@a)\n",
    "struct_element_field": "struct S\n    x: i32\n    y: i64\n\nfn f(p: *[3]S) -> i32\n    return p[1].x\n\n"
                            "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 20\n    a[2].x = 9\n    return f(@a)\n",
    "deref_copies_the_whole_array": "fn f(p: *[3]i32) -> i32\n    var b: [3]i32 = *p\n    return b[1]\n\n" + _a("    return f(@a)\n"),
    "deref_store_is_the_way_to_store": "fn f(p: *[3]i32)\n    var b: [3]i32 = [1, 20, 3]\n    *p = b\n\n" + _a("    f(@a)\n    return a[1]\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(READS))
def test_reads(run_with, name, compiler):
    assert run_with(compiler, name, READS[name]) == 20


# An inferred local was an i64 slot.  What it could do then, it does now.
INFERRED_STAYS_A_POINTER = {
    "cast_to_element_pointer": _a("    let p = @a\n    let q: *i32 = p as *i32\n    return q[1]\n"),
    "mut_cast_to_element_pointer": _a("    let p = @&a\n    let q: *i32 = p as *i32\n    return q[1]\n"),
    "cast_to_integer": _a("    let p = @a\n    let x: i64 = p as i64\n    if x == 0\n        return 1\n    return 20\n"),
    "null": _a("    let p = @a\n    if p == null\n        return 1\n    return 20\n"),
    "mut_null": _a("    let p = @&a\n    if p == null\n        return 1\n    return 20\n"),
    "whole_copy": _a("    let p = @a\n    var b: [3]i32 = *p\n    return b[1]\n"),
    "whole_store": _a("    let p = @&a\n    var b: [3]i32 = [1, 20, 3]\n    *p = b\n    return a[1]\n"),
    "to_pointer_param": "fn g(p: *[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @a\n    return g(p)\n"),
    "to_reference_param": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @a\n    return g(p)\n"),
    "to_mut_reference_param": "fn g(p: @&[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    return g(p)\n"),
    "mut_to_pointer_param": "fn g(p: *[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    return g(p)\n"),
    # R1: an `@T` into `:&` is refused, an `@&T` passes (test_bare_place_borrow.py).
    "to_borrow_param": "fn g(p:& [3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    return g(p)\n"),
    "returned": "fn g(a: *[3]i32) -> *[3]i32\n    let q = a\n    return q\n\n" + _a("    let p: *[3]i32 = g(@a)\n    return p[1]\n"),
    # An annotation can't be told from the default here, so these are the same
    # local as `let x = @a`, and must still read as the integer they were.
    "annotated_integer": _a("    let x: i64 = @a\n    return 20\n"),
    "annotated_integer_copy": "fn f(p: *[3]i32) -> i32\n    let x: i64 = p\n    return 20\n\n" + _a("    return f(@a)\n"),
    "annotated_integer_arithmetic": _a("    let x: i64 = @a as i64\n    let y: i64 = x + 4\n    let q: *i32 = y as *i32\n    return *q\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INFERRED_STAYS_A_POINTER))
def test_an_inferred_local_stays_a_pointer(run_with, name, compiler):
    assert run_with(compiler, name, INFERRED_STAYS_A_POINTER[name]) == 20


# `@&T` fits `@T` (LARB R1), but an `@&` local into an `@` param fails at clang on
# ritz1, annotated or not.  An inferred `@&a` is an `@&` local, as an annotated one
# is: R1 makes `@T` read-only, so recording it as `@` to get past this would be
# refused at `*p = b` once that's checked.
MUT_INTO_SHARED = {
    "param": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    return g(p)\n"),
    "copy": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p = @&a\n    let q = p\n    return g(q)\n"),
    "method": "struct W\n    v: i32\n\nimpl W\n    fn m(self:& W, q: @[3]i32) -> i32\n        return q[1]\n\n" + _a("    let p = @&a\n    var w: W\n    w.v = 0\n    return w.m(p)\n"),
    "annotated": "fn g(p: @[3]i32) -> i32\n    return p[1]\n\n" + _a("    let p: @&[3]i32 = @&a\n    return g(p)\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MUT_INTO_SHARED))
def test_ritz0_passes_an_mut_reference_as_a_reference(run_with, name):
    assert run_with("ritz0", name, MUT_INTO_SHARED[name]) == 20


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2334: an `@&` local into an `@` param fails at clang")
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(MUT_INTO_SHARED))
def test_ritz1_passes_an_mut_reference_as_a_reference(run_with, name, compiler):
    assert run_with(compiler, name, MUT_INTO_SHARED[name]) == 20


def _store(kind: str, addr: str, stmt: str, ty: str = "i32") -> str:
    return f"""\
fn f(p: {kind}[3]{ty}, i: i32, v: {ty})
    {stmt}

pub fn main() -> i32
    var a: [3]{ty}
    f({addr}a, 1, 7 as {ty})
    return 0
"""


REFUSED = {
    "infer_addr_store": _a("    let p = @a\n    p[1] = 7\n    return a[1]\n"),
    "infer_copy_store": "fn f(p: *[3]i32)\n    let q = p\n    q[1] = 7\n\n" + _a("    f(@a)\n    return a[1]\n"),
    "let_store": _a("    let p: *[3]i32 = @a\n    p[1] = 7\n    return a[1]\n"),
    "generic_pointer_store": "fn f<T>(p: *[3]T, v: T)\n    p[1] = v\n\n" + _a("    f<i32>(@a, 7)\n    return a[1]\n"),
    "generic_mut_reference_store": "fn f<T>(p: @&[3]T, v: T)\n    p[1] = v\n\n" + _a("    f<i32>(@&a, 7)\n    return a[1]\n"),
    "struct_element_store": "struct S\n    x: i32\n    y: i64\n\nfn f(p: *[3]S)\n    var s: S\n    p[1] = s\n\n"
                            "pub fn main() -> i32\n    var a: [3]S\n    f(@a)\n    return 3\n",
}
for _kind, (_spelled, _addr) in KINDS.items():
    REFUSED[f"{_kind}_store_const"] = _store(_spelled, _addr, "p[1] = 7")
    REFUSED[f"{_kind}_store_var"] = _store(_spelled, _addr, "p[i] = v")
    REFUSED[f"{_kind}_store_compound"] = _store(_spelled, _addr, "p[1] += 1")
    REFUSED[f"{_kind}_store_byte"] = _store(_spelled, _addr, "p[1] = 7", "u8")
    REFUSED[f"{_kind}_store_double"] = _store(_spelled, _addr, "p[1] = 7.5", "f64")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_store_through_the_index_is_refused(compile_with, name, compiler):
    comp, _, _ = compile_with(compiler, name, REFUSED[name])
    assert comp.returncode != 0
    if compiler != "ritz0":
        assert "through a pointer to an array" in comp.stderr
        assert "main.ritz:" in comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_range_is_refused(compile_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = f"fn f(p: {spelled}[3]i32) -> i32\n    let t = p[1..3]\n    return t[0]\n\n" + _a(f"    return f({addr}a)\n")
    comp, _, _ = compile_with(compiler, "range", program)
    assert comp.returncode != 0
    if compiler != "ritz0":
        assert "can't be sliced" in comp.stderr


# Row 0's pointer, into a `[2][3]i32`: `@p[1]` is row 1's first element, and a
# store through the index replaces row 1.  Stride T would be a[0][1], and a[0].
RITZ0_STRIDES_BY_THE_ARRAY = {
    "address": ("""\
fn f(p: *[3]i32) -> i32
    let q: *i32 = @p[1]
    return *q

pub fn main() -> i32
    var a: [2][3]i32
    a[0][1] = 2
    a[1][0] = 4
    return f(@a[0])
""", 4, "address of an element"),
    "whole_array_store": ("""\
fn f(p: *[3]i32)
    var b: [3]i32 = [1, 2, 3]
    p[1] = b

pub fn main() -> i32
    var a: [2][3]i32
    a[0][1] = 7
    a[1][0] = 9
    f(@a[0])
    return a[0][1] * 10 + a[1][0]
""", 71, "through a pointer to an array"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_STRIDES_BY_THE_ARRAY))
def test_ritz0_strides_these_by_the_array(run_with, name):
    program, expected, _ = RITZ0_STRIDES_BY_THE_ARRAY[name]
    assert run_with("ritz0", name, program) == expected


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(RITZ0_STRIDES_BY_THE_ARRAY))
def test_ritz1_picks_no_stride_for_these(compile_with, name, compiler):
    program, _, message = RITZ0_STRIDES_BY_THE_ARRAY[name]
    comp, _, _ = compile_with(compiler, name, program)
    assert comp.returncode != 0
    assert message in comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("addr_op", ["@", "@&"])
def test_ritz1_refuses_every_address_of_an_element(compile_with, kind, addr_op, compiler):
    spelled, addr = KINDS[kind]
    program = (f"fn g(q: *i32) -> i32\n    return *q\n\nfn f(p: {spelled}[3]i32) -> i32\n"
               f"    return g({addr_op}p[1] as *i32)\n\n" + _a(f"    return f({addr}a)\n"))
    comp, _, _ = compile_with(compiler, "addr", program)
    assert comp.returncode != 0
    assert "address of an element" in comp.stderr


# ritz0 refuses both.  ritz1 was already right, at stride T, and stays so (#2330).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_keeps_a_struct_element_s_field(run_with, compiler):
    program = """\
struct S
    x: i32
    y: i64

fn f(p: *[3]S) -> i32
    p[1].x = 7
    let q: *i32 = @p[2].x
    return *q

pub fn main() -> i32
    var a: [3]S
    a[1].x = 5
    a[2].x = 9
    return f(@a) * 10 + a[1].x
"""
    assert run_with(compiler, "field", program) == 97


# ritz0 fails at clang; a value that was a row must not come out as an integer.
ROWS = {
    "row_element": "fn f(p: @[2][3]i32) -> i32\n    return p[1][2]\n\n",
    "row": "fn f(p: @[2][3]i32) -> i32\n    let r: *i32 = p[1] as *i32\n    return r[2]\n\n",
    "inferred": "fn f(a:& [2][3]i32) -> i32\n    let p = @a\n    return p[1][2]\n\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_ritz1_refuses_to_index_a_pointer_to_rows(compile_with, name, compiler):
    program = ROWS[name] + "pub fn main() -> i32\n    var a: [2][3]i32\n    a[1][2] = 6\n    return f(@a)\n"
    comp, _, _ = compile_with(compiler, name, program)
    assert comp.returncode != 0
    # Not "multi-dimensional": emit_module's unlocated backstop says that too.
    assert "a pointer to a multi-dimensional array can't be indexed" in comp.stderr


# AGAST #2332: nothing records what an element points at, so `*p[1]` would take 8
# bytes of an `i16`, and `*p[1] = 7` its neighbour.  Each returns 72 on ritz0.
_PTRS = """
pub fn main() -> i32
    var x: [2]i16
    x[0] = 1
    x[1] = 2
    var a: [2]*i16
    a[0] = @x[1]
    a[1] = @x[0]
    return f({addr}a) + (x[0] * 10 + x[1]) as i32
"""
POINTER_ELEMENT = {
    "deref_store": ("fn f(p: *[2]*i16) -> i32\n    *p[1] = 7\n    return 0\n" + _PTRS.format(addr="@"), 72),
    "deref_store_reference": ("fn f(p: @[2]*i16) -> i32\n    *p[1] = 7\n    return 0\n" + _PTRS.format(addr="@"), 72),
    "deref_store_mut_reference": ("fn f(p: @&[2]*i16) -> i32\n    *p[1] = 7\n    return 0\n" + _PTRS.format(addr="@&"), 72),
    "deref_load": ("fn f(p: *[2]*i16) -> i32\n    return *p[1] as i32\n" + _PTRS.format(addr="@"), 13),
    "infer_then_deref": ("fn f(p: *[2]*i16) -> i32\n    let q = p[1]\n    return *q as i32\n" + _PTRS.format(addr="@"), 13),
    "annotated": ("fn f(p: *[2]*i16) -> i32\n    let q: *i16 = p[1]\n    return *q as i32\n" + _PTRS.format(addr="@"), 13),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(POINTER_ELEMENT))
def test_ritz0_reads_a_pointer_element(run_with, name):
    program, expected = POINTER_ELEMENT[name]
    assert run_with("ritz0", name, program) == expected


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(POINTER_ELEMENT))
def test_ritz1_refuses_a_pointer_element(compile_with, name, compiler):
    comp, _, _ = compile_with(compiler, name, POINTER_ELEMENT[name][0])
    assert comp.returncode != 0
    assert "array of pointers" in comp.stderr


# AGAST #1562's gap, on this path: no by-value read of a whole struct element.
# ritz0 reads the first three.  The rest it refuses, and each read a byte here,
# with no diagnostic.
_S = "struct S\n    x: i32\n    y: i64\n\n"
_SMAIN = "pub fn main() -> i32\n    var a: [3]S\n    a[1].x = 5\n    a[1].y = 6\n    return f(@a) as i32\n"
_SMUT = _SMAIN.replace("f(@a)", "f(@&a)")
WHOLE_STRUCT_ELEMENT = {
    "by_value": _S + "fn f(p: *[3]S) -> i32\n    let s: S = p[1]\n    return s.x\n\n" + _SMAIN,
    "by_value_argument": _S + "fn g(s: S) -> i32\n    return s.x\n\nfn f(p: *[3]S) -> i32\n    return g(p[1])\n\n" + _SMAIN,
    "by_value_inferred": _S + "fn f(p: *[3]S) -> i32\n    let s = p[1]\n    return s.x\n\n" + _SMAIN,
    "cast": _S + "fn f(p: *[3]S) -> i64\n    return p[1] as i64\n\n" + _SMAIN,
    "let_integer": _S + "fn f(p: *[3]S) -> i64\n    let n: i64 = p[1]\n    return n\n\n" + _SMAIN,
    "returned": _S + "fn f(p: *[3]S) -> i64\n    return p[1]\n\n" + _SMAIN,
    "compared": _S + "fn f(p: @[3]S) -> i64\n    if p[1] == 5\n        return 1\n    return 0\n\n" + _SMAIN,
    "added": _S + "fn f(p: *[3]S) -> i64\n    return p[1] + 1\n\n" + _SMAIN,
    "mut_reference": _S + "fn f(p: @&[3]S) -> i64\n    return p[1] as i64\n\n" + _SMUT,
    "variable_index": _S + "fn f(p: *[3]S, i: i32) -> i64\n    return p[i] as i64\n\npub fn main() -> i32\n    var a: [3]S\n    return f(@a, 1) as i32\n",
    "inferred_copy": _S + "fn f(p: *[3]S) -> i64\n    let q = p\n    return q[1] as i64\n\n" + _SMAIN,
    "inferred_copy_of_reference": _S + "fn f(p: @[3]S) -> i64\n    let q = p\n    return q[1] as i64\n\n" + _SMAIN,
    "inferred_copy_of_mut_reference": _S + "fn f(p: @&[3]S) -> i64\n    let q = p\n    return q[1] as i64\n\n" + _SMUT,
    "inferred_var_copy": _S + "fn f(p: @[3]S) -> i64\n    var q = p\n    return q[1] as i64\n\n" + _SMAIN,
    "inferred_local": _S + "pub fn main() -> i32\n    var a: [3]S\n    let p = @a\n    return p[1] as i32\n",
    "inferred_mut_local": _S + "pub fn main() -> i32\n    var a: [3]S\n    let p = @&a\n    return p[1] as i32\n",
    "inferred_borrow": _S + "fn f(a:& [3]S) -> i64\n    let p = @a\n    return p[1] as i64\n\n" + _SMAIN,
    "inferred_global": _S + "var G: [3]S\n\npub fn main() -> i32\n    let p = @G\n    return p[1] as i32\n",
    "inferred_field": _S + "struct H\n    cs: [3]S\n\npub fn main() -> i32\n    var h: H\n    let p = @h.cs\n    return p[1] as i32\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(WHOLE_STRUCT_ELEMENT))
def test_ritz1_refuses_a_whole_struct_element(compile_with, name, compiler):
    comp, _, _ = compile_with(compiler, name, WHOLE_STRUCT_ELEMENT[name])
    assert comp.returncode != 0
    assert "a whole struct element can't be read through a pointer to an array" in comp.stderr


# The ordinary pointer stays pointer arithmetic, and its store stays a store.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_pointer_to_an_element_still_stores(run_with, compiler):
    program = """\
fn f(p: *i32)
    p[1] = 7

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    f(@a[0])
    return a[0] + a[1] + a[2]
"""
    assert run_with(compiler, "element", program) == 47


# AGAST #2329: bases that record no N and T.  Fields, globals and call results.
_H = "struct H\n    r: {ty}\n\nfn f(h: *H) -> i32\n    return h.r[1]\n\npub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n    var h: H\n    h.r = @a\n    return f(@h)\n"
_G = "var g: *[3]i32 = null\n\n" + _a("    g = @a\n    return g[1]\n")
_R = "fn h(p: *[3]i32) -> {ty}\n    return p\n\nfn f(p: *[3]i32) -> i32\n    return h(p)[1]\n\n" + _a("    return f(@a)\n")
OPEN_BASES = {
    "field_pointer": _H.format(ty="*[3]i32"),
    "field_reference": _H.format(ty="@[3]i32"),
    "global": _G,
    "call_pointer": _R.format(ty="*[3]i32"),
    "call_reference": _R.format(ty="@[3]i32"),
    "let_from_call": "fn h(p: *[3]i32) -> *[3]i32\n    return p\n\nfn f(p: *[3]i32) -> i32\n    let q = h(p)\n    return q[1]\n\n" + _a("    return f(@a)\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(OPEN_BASES))
def test_ritz0_indexes_every_base(run_with, name):
    assert run_with("ritz0", name, OPEN_BASES[name]) == 20


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2329: this base records no N and T, so `p[i]` reads 0")
@pytest.mark.parametrize("name", sorted(OPEN_BASES))
def test_ritz1_indexes_every_base(run_with, name):
    assert run_with("ritz1", name, OPEN_BASES[name]) == 20


GLOBAL_STORE = "var g: *[3]i32 = null\n\n" + _a("    g = @a\n    g[1] = 7\n    return a[1]\n")


@pytest.mark.integration
def test_ritz0_refuses_a_store_through_a_global(compile_with):
    comp, _, _ = compile_with("ritz0", "global_store", GLOBAL_STORE)
    assert comp.returncode != 0


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2329: `g[i] = v` stores 8 bytes at stride 8")
def test_ritz1_refuses_a_store_through_a_global(compile_with):
    comp, _, _ = compile_with("ritz1", "global_store", GLOBAL_STORE)
    assert comp.returncode != 0
