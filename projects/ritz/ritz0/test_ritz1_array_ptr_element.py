"""AGAST #2332: an element of a `[N]*T` array is a `*T`, and ritz1 forgot the T.

    var x: [2]i16
    var a: [2]*i16
    a[1] = @x[0]
    *a[1] = 7           # ritz0 stores 2 bytes, ritz1 stored 8: x[1] gone

Nothing recorded the pointee of `a[i]`, so everything asking for it guessed:

    *a[i]               8-byte load, and a store that overwrites the neighbours
    let q = a[i]        an i64, so `*q` guessed too, and `q.f` didn't compile
    a[i] + k, a[i][j]   stride 1, and `a[i][j] = v` wrote through the *value*
    for p in a          as `let q = a[i]`
    h.a[i].f            GEP'd `[N x %S]`: a `*S` array read as inline structs
    *a[i] on a float    a clang error

The exit code is the low byte, so `return *a[1] as i32` can't see a wide load:
x[0] is in that byte either way.  Every check here compares the whole value.

Each GRID program runs its checks in order and returns the number of the first
that failed (see _CHECKS), so a red cell says which path broke.

`p[i]` on a pointer TO an array of pointers stays refused (#2347, LARB's call):
test_ritz1_array_pointer_index.py pins POINTER_ELEMENT.
"""

from pathlib import Path

import pytest

from test_borrow_param_ref_field import _compile, _run

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]

# Three distinct values, then the one the stores write.  Each differs from its
# neighbours in the low byte AND above it, so neither a narrow nor a wide access
# passes by luck.  bool has two values, so its row leans on the order.
SCALARS = {
    "i8": ("-2", "-3", "-5", "7"),
    "u8": ("200", "201", "202", "7"),
    "i16": ("-300", "-301", "-302", "7"),
    "u16": ("40000", "40001", "40002", "7"),
    "i32": ("-70000", "-70001", "-70002", "7"),
    "u32": ("3000000000", "3000000001", "3000000002", "7"),
    "i64": ("-5000000000", "-5000000001", "-5000000002", "7"),
    "u64": ("5000000000", "5000000001", "5000000002", "7"),
    "f32": ("1.5", "2.5", "3.5", "4.5"),
    "f64": ("1.5", "2.5", "3.5", "4.5"),
    "bool": ("true", "false", "true", "false"),
}

# 1-7 load, inferred `let`, stride and index; 8-13 the stores, each checking the
# element it was aimed at and the one after it.  `{a}` is the holder's spelling
# of the array, `x` the three scalars behind it, and a[1] points at x[0].
_CHECKS = """\
    if *{a}[1] != {v0}
        return 1
    let q = {a}[1]
    if *q != {v0}
        return 2
    var r = {a}[1]
    if *r != {v0}
        return 3
    if *({a}[1] + 1) != {v1}
        return 4
    if {a}[1][1] != {v1}
        return 5
    if q[1] != {v1}
        return 6
    if *(q + 2) != {v2}
        return 7
    *{a}[1] = {v3}
    if x[0] != {v3}
        return 8
    if x[1] != {v1}
        return 9
    *({a}[1] + 1) = {v3}
    if x[1] != {v3}
        return 10
    if x[2] != {v2}
        return 11
    x[1] = {v1}
    {a}[1][1] = {v3}
    if x[1] != {v3}
        return 12
    if x[2] != {v2}
        return 13
    return 0
"""

_FILL = """\
    var x: [3]{t}
    x[0] = {v0}
    x[1] = {v1}
    x[2] = {v2}
"""


def _in_main(pre: str, setup: str) -> str:
    """The checks inline in main, after `setup` points the holder at x."""
    return pre + "pub fn main() -> i32\n" + _FILL + setup + _CHECKS


def _in_fn(params: str, call: str, pre: str = "") -> str:
    """The checks in `f(<params>, x: *T)`, called with the local array `a`."""
    return (pre + f"fn f({params}, x: *{{t}}) -> i32\n" + _CHECKS + "\n"
            + "pub fn main() -> i32\n" + _FILL
            + "    var a: [2]*{t}\n    a[1] = @x[0]\n"
            + f"    return f({call}, @x[0])\n")


_H = "struct H\n    n: i64\n    a: [2]*{t}\n\n"
HOLDERS = {
    "local": ("a", _in_main("", "    var a: [2]*{t}\n    a[1] = @x[0]\n")),
    "mut_param": ("a", _in_fn("a:& [2]*{t}", "a")),
    "value_param": ("a", _in_fn("a: [2]*{t}", "a")),
    "field": ("h.a", _in_main(_H, "    var h: H\n    h.a[1] = @x[0]\n")),
    "nested_field": ("o.h.a", _in_main(
        _H + "struct O\n    m: i64\n    h: H\n\n", "    var o: O\n    o.h.a[1] = @x[0]\n")),
    "field_of_element": ("o[1].a", _in_main(_H, "    var o: [2]H\n    o[1].a[1] = @x[0]\n")),
    "field_by_pointer": ("h.a", (
        _H + "fn f(h: *H, x: *{t}) -> i32\n" + _CHECKS + "\n"
        + "pub fn main() -> i32\n" + _FILL
        + "    var h: H\n    h.a[1] = @x[0]\n    return f(@h, @x[0])\n")),
    "global": ("g", _in_main("var g: [2]*{t}\n\n", "    g[1] = @x[0]\n")),
    "two_dimensional": ("b[1]", _in_main("", "    var b: [2][2]*{t}\n    b[1][1] = @x[0]\n")),
}


def _grid_program(holder: str, ty: str) -> str:
    spelling, template = HOLDERS[holder]
    v0, v1, v2, v3 = SCALARS[ty]
    # _CHECKS carries `{a}`, so the holder's text is formatted once, whole.
    return template.format(a=spelling, t=ty, v0=v0, v1=v1, v2=v2, v3=v3)


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(SCALARS))
@pytest.mark.parametrize("holder", sorted(HOLDERS))
def test_element_is_a_pointer_to_its_own_type(run_with, holder, ty, compiler):
    assert run_with(compiler, f"{holder}_{ty}", _grid_program(holder, ty)) == 0


def _is(expr: str, want: str = "1") -> str:
    return f"    if {expr} == {want}\n        return 0\n    return 1\n"


_X = """\
    var x: [3]i16
    x[0] = 1
    x[1] = 2
    x[2] = 3
    var a: [2]*i16
    a[0] = @x[1]
    a[1] = @x[0]
"""


def _x(body: str, pre: str = "") -> str:
    return pre + "pub fn main() -> i32\n" + _X + body


_MIXED = """\
struct S
    p: i16
    q: i16
    f: f32
    d: f64
    b: bool

"""
_S_INIT = """\
    var s: S
    s.p = 1
    s.q = 2
    s.f = 1.5
    s.d = 2.5
    s.b = true
    var a: [2]*S
    a[1] = @s
"""


def _s(body: str, pre: str = "") -> str:
    return _MIXED + pre + "pub fn main() -> i32\n" + _S_INIT + body


_W = "struct W\n    n: i64\n    a: [2]*S\n\n"
_G = "var g: [2]*S\n\n"
_PAIR = "struct S\n    p: i16\n    q: i16\n    r: i32\n\n"
_PAIR_MAIN = "pub fn main() -> i32\n    var s: [2]S\n    s[1].q = 2\n    var a: [2]*S\n    a[1] = @s[0]\n"

# Everything here returns 0, on all three compilers.
SHAPES = {
    # `let v = *a[i]` takes the pointee's width and sign.
    "inferred_value": _x("    let v = *a[1]\n" + _is("v")),
    "cast_value": _x(_is("*a[1] as i64")),
    # A wide read-modify-write carries into the neighbour: ritz0 2, ritz1 3.
    "compound_stops_at_the_element": _x(
        "    x[0] = -1\n    *a[1] += 1\n" + _is("x[1]", "2")),
    "inferred_sum": _x("    let q = a[1] + 1\n" + _is("*q", "2")),
    "inferred_reassigned": _x("    var q = a[1]\n    q = a[0]\n" + _is("*q", "2")),
    "inferred_store": _x("    let q = a[1]\n    *q = 7\n" + _is("x[1]", "2")),
    "for_load": _x(
        "    a[0] = @x[0]\n    var t: i32 = 0\n    for p in a\n"
        "        if *p == 1\n            t = t + 1\n" + _is("t", "2")),
    "for_store": _x("    for p in a\n        *p = 7\n" + _is("x[2]", "3")),
    "for_stride": _x(
        "    var t: i64 = 0\n    for p in a\n        t = t + *(p + 1)\n" + _is("t", "5")),
    "for_mut_param": _x(
        "    return f(a)\n",
        "fn f(a:& [2]*i16) -> i32\n    a[0] = a[1]\n    var t: i32 = 0\n    for p in a\n"
        "        if *p == 1\n            t = t + 1\n" + _is("t", "2") + "\n"),
    "two_dimensional_inferred": _x(
        "    var b: [2][2]*i16\n    b[1][1] = @x[0]\n    let q = b[1][1]\n" + _is("*q")),
    "float_literal_store": (
        "pub fn main() -> i32\n    var x: [2]f32\n    x[0] = 1.5\n    x[1] = 2.5\n"
        "    var a: [2]*f32\n    a[1] = @x[0]\n    *a[1] = 3.5\n" + _is("x[1]", "2.5")),
    "bool_condition": (
        "pub fn main() -> i32\n    var x: [2]bool\n    x[0] = true\n    x[1] = false\n"
        "    var a: [2]*bool\n    a[1] = @x[0]\n    if *a[1]\n        return 0\n    return 1\n"),
    # A generic clone keeps the pointee: monomorph copied the element type only.
    "generic_mut_param": _x(
        "    return f<i32>(a, 0)\n",
        "fn f<T>(a:& [2]*i16, t: T) -> i32\n" + _is("*a[1]") + "\n"),
    "generic_value_param": _x(
        "    return f<i32>(a, 0)\n",
        "fn f<T>(a: [2]*i16, t: T) -> i32\n" + _is("*a[1]") + "\n"),
    "generic_local": (
        "fn f<T>(t: T) -> i32\n" + _X + _is("*a[1]") + "\n"
        "pub fn main() -> i32\n    return f<i32>(0)\n"),
    "generic_field": (
        "struct B<T>\n    t: T\n    a: [2]*i16\n\n"
        "pub fn main() -> i32\n" + _X + "    var b: B<i32>\n    b.a[1] = @x[0]\n" + _is("*b.a[1]")),
    "generic_element_local": (
        "fn f<T>(t: T, p: *T) -> i32\n    var a: [2]*T\n    a[1] = p\n" + _is("*a[1]") + "\n"
        "pub fn main() -> i32\n" + _X + "    return f<i16>(0 as i16, @x[0])\n"),
    "generic_element_field": (
        "struct B<T>\n    a: [2]*T\n\n"
        "pub fn main() -> i32\n" + _X + "    var b: B<i16>\n    b.a[1] = @x[0]\n" + _is("*b.a[1]")),
    # Struct pointees.  `h.a[i].f` read `[N x %S]` at the array's own address.
    "struct_field_of_element": _s(_is("a[1].q", "2")),
    "struct_f32_field": _s(_is("a[1].f", "1.5")),
    "struct_f64_field": _s(_is("a[1].d", "2.5")),
    "struct_bool_field": _s("    if a[1].b\n        return 0\n    return 1\n"),
    "struct_deref_then_field": _s(_is("(*a[1]).q", "2")),
    "struct_copy": _s("    let c: S = *a[1]\n" + _is("c.q", "2")),
    "struct_store": _s("    var t: S\n    t.q = 8\n    *a[1] = t\n" + _is("s.q", "8")),
    "struct_inferred": _s("    let q = a[1]\n" + _is("q.q", "2")),
    "struct_inferred_store": _s("    let q = a[1]\n    q.q = 7\n" + _is("s.q", "7")),
    "struct_for": _s(
        "    a[0] = @s\n    var t: i32 = 0\n    for p in a\n        t = t + p.q as i32\n" + _is("t", "4")),
    "struct_for_store": _s("    a[0] = @s\n    for p in a\n        p.q = 7\n" + _is("s.q", "7")),
    "struct_global": _s("    g[1] = @s\n" + _is("g[1].q", "2"), _G),
    "struct_global_store": _s("    g[1] = @s\n    g[1].q = 7\n" + _is("s.q", "7"), _G),
    "struct_global_inferred": _s("    g[1] = @s\n    let q = g[1]\n" + _is("q.q", "2"), _G),
    "struct_in_field": _s("    var h: W\n    h.a[1] = @s\n" + _is("h.a[1].q", "2"), _W),
    "struct_in_field_store": _s("    var h: W\n    h.a[1] = @s\n    h.a[1].q = 7\n" + _is("s.q", "7"), _W),
    "struct_in_field_inferred": _s("    var h: W\n    h.a[1] = @s\n    let q = h.a[1]\n" + _is("q.q", "2"), _W),
    "struct_in_field_by_pointer": _s(
        "    var h: W\n    h.a[1] = @s\n    return f(@h)\n",
        _W + "fn f(h: *W) -> i32\n" + _is("h.a[1].q", "2") + "\n"),
    "struct_mut_param_inferred": _s(
        "    return f(a)\n", "fn f(a:& [2]*S) -> i32\n    let q = a[1]\n" + _is("q.q", "2") + "\n"),
    "struct_two_dimensional": _s("    var b: [2][2]*S\n    b[1][0] = @s\n" + _is("b[1][0].q", "2")),
    "struct_sum_inferred": _PAIR + _PAIR_MAIN + "    let q = a[1] + 1\n" + _is("q.q", "2"),
    "struct_sum_deref": _PAIR + _PAIR_MAIN + _is("(*(a[1] + 1)).q", "2"),
    "struct_index": _PAIR + _PAIR_MAIN + _is("a[1][1].q", "2"),
    "struct_index_copy": _PAIR + _PAIR_MAIN + "    let c: S = a[1][1]\n" + _is("c.q", "2"),
    "struct_index_store": (
        _PAIR + "pub fn main() -> i32\n    var s: [2]S\n    var t: S\n    t.q = 2\n"
        "    var a: [2]*S\n    a[1] = @s[0]\n    a[1][1] = t\n" + _is("s[1].q", "2")),
    "struct_method": _s(
        "    return a[1].m()\n",
        "impl S\n    fn m(self: *S) -> i32\n        if self.q == 2\n            return 0\n        return 1\n\n"),
    "struct_inferred_method": _s(
        "    let q = a[1]\n    return q.m()\n",
        "impl S\n    fn m(self: *S) -> i32\n        if self.q == 2\n            return 0\n        return 1\n\n"),
    "struct_index_f32_field": (
        _MIXED + "pub fn main() -> i32\n    var s: [2]S\n    s[1].f = 1.5\n    var a: [2]*S\n"
        "    a[1] = @s[0]\n" + _is("a[1][1].f", "1.5")),
    # The chain goes on through the pointee: an array inside what `a[i]` points at.
    "element_of_global_element": (
        "struct N\n    m: i64\n    b: [2]*i16\n\nvar g: [2]*N\n\npub fn main() -> i32\n" + _X
        + "    var n: N\n    n.b[1] = @x[0]\n    g[1] = @n\n" + _is("*g[1].b[1]")),
    # The annotation is the type: `let` infers only what isn't written.
    "annotation_wins": _x("    x[0] = 258\n    let q: *u8 = a[1]\n" + _is("*q", "2")),
    "generic_element_value_param": (
        "fn f<T>(a: [2]*T, t: T) -> i32\n" + _is("*a[1]") + "\n"
        "pub fn main() -> i32\n" + _X + "    return f<i16>(a, 0 as i16)\n"),
    "generic_element_for": (
        "fn f<T>(p: *T) -> i32\n    var a: [2]*T\n    a[0] = p\n    a[1] = p\n    var t: i32 = 0\n"
        "    for e in a\n        if *e == 1\n            t = t + 1\n" + _is("t", "2") + "\n"
        "pub fn main() -> i32\n" + _X + "    return f<i16>(@x[0])\n"),
    "generic_two_params": (
        "struct B<T, U>\n    t: T\n    a: [2]*U\n\n"
        "pub fn main() -> i32\n" + _X + "    var b: B<i32, i16>\n    b.a[1] = @x[0]\n" + _is("*b.a[1]")),
    "generic_struct_element": _s(
        "    var b: B<S>\n    b.a[1] = @s\n" + _is("b.a[1].q", "2"), "struct B<T>\n    a: [2]*T\n\n"),
    # An enum isn't a StructDef, and it loads as itself.
    "enum_copy": (
        "enum E\n    A\n    B\n\npub fn main() -> i32\n    var e: E = E.B\n    var a: [2]*E\n"
        "    a[1] = @e\n    let c: E = *a[1]\n    if c == E.B\n        return 0\n    return 1\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SHAPES))
def test_element_shape(run_with, name, compiler):
    assert run_with(compiler, name, SHAPES[name]) == 0


# AGAST #2376: an element of a `[N]**T` is a `**T`, and `**b[i]` is a T: two
# bytes here, where ritz1 took 8 and the store overwrote x[1].  `@a[i]` with
# `a: [N]*T` is the same `**T`.
_B = "    var q: *i16 = @x[0]\n    var b: [2]**i16\n    b[1] = @q\n"
_BG = "var g: [2]**i16\n\n"
_BH = "struct H\n    n: i64\n    b: [2]**i16\n\n"
POINTER_TO_POINTER = {
    "load": _x(_B + _is("**b[1]")),
    "store": _x(_B + "    **b[1] = 7\n" + _is("x[1]", "2")),
    "store_lands": _x(_B + "    **b[1] = 7\n" + _is("x[0]", "7")),
    "compound": _x(_B + "    x[0] = -1\n    **b[1] += 1\n" + _is("x[1]", "2")),
    "inner_stride": _x(_B + _is("*(*b[1] + 1)", "2")),
    "inferred": _x(_B + "    let r = b[1]\n" + _is("**r")),
    "inferred_store": _x(_B + "    let r = b[1]\n    **r = 7\n" + _is("x[1]", "2")),
    "inferred_deref": _x(_B + "    let r = *b[1]\n" + _is("*r")),
    "inferred_deref_store": _x(_B + "    let r = *b[1]\n    *r = 7\n" + _is("x[1]", "2")),
    "address_of_element": _x("    let r = @a[1]\n" + _is("**r")),
    "address_of_element_store": _x("    let r = @a[1]\n    **r = 7\n" + _is("x[1]", "2")),
    "global": _x("    var q: *i16 = @x[0]\n    g[1] = @q\n    **g[1] = 7\n" + _is("x[1]", "2"), _BG),
    "global_load": _x("    var q: *i16 = @x[0]\n    g[1] = @q\n" + _is("**g[1]"), _BG),
    "field": _x("    var q: *i16 = @x[0]\n    var h: H\n    h.b[1] = @q\n    **h.b[1] = 7\n"
                + _is("x[1]", "2"), _BH),
    "field_load": _x("    var q: *i16 = @x[0]\n    var h: H\n    h.b[1] = @q\n" + _is("**h.b[1]"), _BH),
    "param": _x("    var q: *i16 = @x[0]\n    var b: [2]**i16\n    b[1] = @q\n    return f(b)\n",
                "fn f(b: [2]**i16) -> i32\n    **b[1] = 7\n    if **b[1] == 7\n        return 0\n"
                "    return 1\n\n"),
    "two_dimensional": _x("    var q: *i16 = @x[0]\n    var b: [2][2]**i16\n    b[1][1] = @q\n"
                          "    **b[1][1] = 7\n" + _is("x[1]", "2")),
    "mut_param": _x("    var q: *i16 = @x[0]\n    var b: [2]**i16\n    b[1] = @q\n    return f(b)\n",
                    "fn f(b:& [2]**i16) -> i32\n    let r = b[1]\n    **r = 7\n" + _is("**b[1]", "7") + "\n"),
    # A struct pointee: `(**b[i]).f` and `(**r).f` reach S.
    "struct_load": _s("    var p: *S = @s\n    var b: [2]**S\n    b[1] = @p\n" + _is("(**b[1]).q", "2")),
    "struct_store": _s("    var p: *S = @s\n    var b: [2]**S\n    b[1] = @p\n    (**b[1]).q = 7\n"
                       + _is("s.q", "7")),
    "struct_inferred": _s("    var p: *S = @s\n    var b: [2]**S\n    b[1] = @p\n    let r = b[1]\n"
                          + _is("(**r).q", "2")),
    "struct_address_of_element": _s("    let r = @a[1]\n" + _is("(**r).q", "2")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(POINTER_TO_POINTER))
def test_pointer_to_pointer_element(run_with, name, compiler):
    assert run_with(compiler, name, POINTER_TO_POINTER[name]) == 0


# The new stride mustn't reach here: `q - p` scaled q as if it were a count.
# AGAST #2928: the distance is in elements (LANGUAGE_SPEC §7.1 "Pointer
# difference"), on all three compilers: `@x[2] - @x[0]` is 2, not 4 bytes.
DIFFERENCES = {
    "two_elements": "    a[0] = @x[2]\n    return (a[0] - a[1]) as i32\n",
    "element_and_local": "    a[0] = @x[2]\n    let p: *i16 = @x[0]\n    return (a[0] - p) as i32\n",
    # `d` is an integer, so `+ 1` is one and not sizeof(i16).
    "inferred": "    a[0] = @x[2]\n    let d = a[0] - a[1]\n    return (d + 1) as i32 - 1\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(DIFFERENCES))
def test_difference_of_pointers_is_not_a_stride(run_with, name, compiler):
    assert run_with(compiler, name, _x(DIFFERENCES[name])) == 2


# An integer on the right is still a stride.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_minus_a_count_strides_back(run_with, compiler):
    assert run_with(compiler, "minus", _x("    return " "*(a[0] - 1) as i32 - 1\n")) == 0


# Elements that aren't pointers keep their arithmetic: nothing here has a pointee.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_integer_element_has_no_stride(run_with, compiler):
    program = "pub fn main() -> i32\n    var a: [2]i32\n    a[1] = 5\n    return a[1] + 1\n"
    assert run_with(compiler, "integer", program) == 6


# A store through an element is a store to a T, so a literal has to fit a T.
# Each of these truncated without a word, or (`a[1][1]`) wrote through the value.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("target", ["*a[1]", "a[1][1]", "*(a[1] + 1)"])
def test_literal_has_to_fit_the_pointee(compile_with, target, compiler):
    comp, _, _ = compile_with(compiler, "fit", _x(f"    {target} = 70000\n    return 0\n"))
    assert comp.returncode != 0
    assert "does not fit in `i16`" in comp.stdout + comp.stderr


# The chain through `c[i][j]`, `*(c[i] + j)`.  ritz0 segfaulted (#2380) until
# #2968 took an element that's a `*N` for a raw buffer.
_INDEXED_SETUP = (
    "struct N\n    m: i64\n    b: [2]*i16\n\npub fn main() -> i32\n" + _X
    + "    var n: [2]N\n    n[1].b[1] = @x[0]\n    var c: [2]*N\n    c[1] = @n[0]\n")
_INDEXED_ELEMENT = {
    "deref": _is("*c[1][1].b[1]"),
    "let": "    let e: *i16 = c[1][1].b[1]\n" + _is("*e"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(_INDEXED_ELEMENT))
def test_element_of_indexed_element(run_with, form, compiler):
    assert run_with(compiler, "indexed", _INDEXED_SETUP + _INDEXED_ELEMENT[form]) == 0


# AGAST #2379: `a[i][j]` is `*(a[i] + j)`, so `@a[i][j]` is `a[i] + j`, a `*T`.
# ritz0 took the address of the `[N]*T` slot j (typed) or failed at clang
# (inferred); ritz1 said "cannot take address".  a[1] points at x[0], so
# `@a[1][1]` is x[1].  A 2-D array's `@b[i][j]` is still its own slot.
_ADDR_H = "struct H\n    n: i64\n    a: [2]*i16\n\n"
ELEMENT_ADDRESSES = {
    "typed": _x("    let r: *i16 = @a[1][1]\n" + _is("*r", "2")),
    "inferred": _x("    let r = @a[1][1]\n" + _is("*r", "2")),
    "typed_store": _x("    let r: *i16 = @a[1][1]\n    *r = 7\n" + _is("x[1] * 10 + x[2]", "73")),
    "inferred_store": _x("    let r = @&a[1][1]\n    *r = 7\n" + _is("x[1] * 10 + x[2]", "73")),
    "inferred_stride": _x("    let r = @a[1][1]\n" + _is("*(r + 1)", "3")),
    "deref": _x(_is("*@a[1][1]", "2")),
    "field": _x("    var h: H\n    h.a[1] = @x[0]\n    let r = @&h.a[1][1]\n    *r = 7\n"
                + _is("x[1]", "7"), _ADDR_H),
    "struct": _PAIR + _PAIR_MAIN + "    let r = @&a[1][1]\n    r.q = 5\n" + _is("s[1].q", "5"),
    "two_dimensional_pointers": _x(
        "    var b: [2][2]*i16\n    b[1][1] = @x[0]\n    let r = @b[1][1]\n" + _is("**r")),
    "two_dimensional_values": (
        "pub fn main() -> i32\n    var b: [2][2]i16\n    let r = @&b[1][1]\n    *r = 7\n"
        + _is("b[1][1]", "7")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ELEMENT_ADDRESSES))
def test_address_of_element_index_is_the_sum(run_with, name, compiler):
    assert run_with(compiler, f"addr_{name}", ELEMENT_ADDRESSES[name]) == 0


# A range isn't an element, so it has no address either.  ritz0 refuses it with
# a NotImplementedError traceback (#3088), the ritz1s in words.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_address_of_element_slice_is_refused(compile_with, compiler):
    # AGAST #3088: ritz0 raised NotImplementedError (Range) from the `@` path.
    _refused_at(compile_with, compiler, "addr_slice", _x("    let r = @a[1][0..2]\n    return 0\n"),
                ELEMENT_NOT_SLICED, "9:14")


# ritz0 slices no pointer element.  ritz1 took `a[1][0..2]` at stride 1.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_element_is_not_sliced(compile_with, compiler):
    _refused_at(compile_with, compiler, "slice", _x("    let r = a[1][0..2]\n    return 0\n"),
                ELEMENT_NOT_SLICED, "9:13")


ELEMENT_NOT_SLICED = "an element of an array of pointers can't be sliced (only String, Vec and Span can)"


def _refused_at(compile_with, compiler, name, program, message, where):
    """`program` fails to compile with `message`, at `main.ritz:<where>:`."""
    comp, _, _ = compile_with(compiler, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} took {name}"
    assert "Traceback" not in out, out[-1500:]
    assert message in out, out[-1500:]
    assert f"main.ritz:{where}:" in out, out[-1500:]


# AGAST #3088: `@x[lo..hi]` on any other place refuses as `x[lo..hi]` does, at
# the place, where ritz0 raised NotImplementedError.  ritz1 said "unknown
# expression kind" or "cannot take address", unlocated (AGAST #3145).  An i32
# field shares only the tail: ritz0 calls it "a struct" (AGAST #3146).
_ADDR_H = "struct H\n    a: [2]*i16\n    p: *i16\n    k: i32\n\n"
_UNSLICEABLE = "can't be sliced (only String, Vec and Span can)"
ADDR_OF_SLICE = {
    "array_local": ("", "    let r = @x[0..2]\n", "an array can't be sliced"),
    "pointer_local": ("", "    var p: *i16 = @x[0]\n    let r = @p[0..2]\n", "a pointer can't be sliced"),
    "array_field": (_ADDR_H, "    var h: H\n    let r = @h.a[0..2]\n", "an array can't be sliced"),
    "pointer_field": (_ADDR_H, "    var h: H\n    h.p = @x[0]\n    let r = @h.p[0..2]\n",
                      "a pointer can't be sliced"),
    "int_field": (_ADDR_H, "    var h: H\n    h.k = 1\n    let r = @h.k[0..2]\n", _UNSLICEABLE),
    # A String slices, but its slice is a new value, with no place to point at.
    "string": ("import ritzlib.string\n\n",
               '    var s: String = string_from("abcd")\n    let r = @s[0..2]\n',
               "can't take the address of a slice"),
    "vec": ("import ritzlib.gvec\n\n",
            "    var v: Vec<i32> = vec_new<i32>()\n    let r = @v[0..1]\n",
            "can't take the address of a slice"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ADDR_OF_SLICE))
def test_address_of_a_slice_is_refused_located(compile_with, name, compiler):
    pre, body, message = ADDR_OF_SLICE[name]
    program = _x(body + "    return 0\n", pre)
    line = program.splitlines().index(body.splitlines()[-1]) + 1
    _refused_at(compile_with, compiler, name, program, message, f"{line}:14")


# No store takes a range.  Each compiler says so in its own words.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_element_slice_is_not_a_store_target(compile_with, compiler):
    comp, _, _ = compile_with(compiler, "slice_store", _x("    a[1][0..2] = 7\n    return 0\n"))
    assert comp.returncode != 0


_FOR_G = "var g: [2]*i16\n\n"
_FOR_H = "struct H\n    a: [2]*i16\n\n"
# AGAST #2375: `for p in` a global or a field binds what the element points at,
# so `*p` reads 2 bytes.  x[1] is in the 8 a wide load would take.
FOR_OVER = {
    "global": _x(
        "    g[0] = @x[0]\n    g[1] = @x[0]\n    var t: i32 = 0\n    for p in g\n"
        "        if *p == 1\n            t = t + 1\n" + _is("t", "2"), _FOR_G),
    "field": _x(
        "    var h: H\n    h.a[0] = @x[0]\n    h.a[1] = @x[0]\n    var t: i32 = 0\n    for p in h.a\n"
        "        if *p == 1\n            t = t + 1\n" + _is("t", "2"), _FOR_H),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(FOR_OVER))
def test_a_loop_binding_knows_its_pointee(run_with, compiler, name):
    assert run_with(compiler, name, FOR_OVER[name]) == 0


# AGAST #2542 (was a #2377 known gap): `let c = *a[1]` with `a: [2]*S` is an S.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_inferred_copy_of_a_struct_element_deref(run_with, compiler):
    program = _s("    let c = *a[1]\n" + _is("c.q", "2"))
    assert run_with(compiler, "struct_inferred_copy", program) == 0


# AGAST #2377: an untyped `let` of a struct read through a pointer is that struct,
# as `let c: S = ...`.  `a[1][1]` stayed i64: "unhandled EXPR_MEMBER".  `p[0]` is
# KNOWN_GAPS' (#3052).
# s[1] is the one with q == 2; a[0] and p point at it, a[1] at s[0].
_COPY_MAIN = (_PAIR + "pub fn main() -> i32\n    var s: [2]S\n    s[1].q = 2\n    var a: [2]*S\n"
              "    a[0] = @s[1]\n    a[1] = @s[0]\n    let p: *S = @s[1]\n")
INFERRED_COPIES = {
    "deref": "*p",
    "deref_element": "*a[0]",
    "element_index": "a[1][1]",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INFERRED_COPIES))
def test_untyped_let_through_a_pointer_is_the_struct(run_with, name, compiler):
    program = _COPY_MAIN + f"    let c = {INFERRED_COPIES[name]}\n" + _is("c.q", "2")
    assert run_with(compiler, name, program) == 0


# A copy, not an alias: writing `c` leaves s[1] alone.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_untyped_let_of_an_element_index_is_a_copy(run_with, compiler):
    program = _COPY_MAIN + "    var c = a[1][1]\n    c.q = 5\n" + _is("s[1].q + c.q", "7")
    assert run_with(compiler, "element_index_copy", program) == 0


# AGAST #3058: with `b: [2]**S`, `b[1][0]` is `*(b[1] + 0)`, a `*S`, so `let c`
# is one, as `let c: *S = b[1][0]`.  ritz1 left it i64 with no pointee:
# `c[1].q` was "unhandled EXPR_MEMBER".  p0 points at s0[0], so c[1] is s0[1];
# b[0] points at ps, so `b[0][1]` is ps[1], one pointer on, also at s0[1].
_PP_MAIN = (_PAIR + "pub fn main() -> i32\n    var s0: [2]S\n    s0[0].q = 1\n    s0[1].q = 2\n"
            "    var p0: *S = @s0[0]\n    var ps: [2]*S\n    ps[0] = @s0[0]\n    ps[1] = @s0[1]\n"
            "    var b: [2]**S\n    b[0] = @ps[0]\n    b[1] = @p0\n    let c = b[1][0]\n")
PTR_PTR_ELEMENT_INDEX = {
    "index_field": _is("c[1].q", "2"),
    "deref_field": _is("(*c).q", "1"),
    "store": "    c[1].q = 7\n" + _is("s0[1].q", "7"),
    "pointer_stride": "    let d = b[0][1]\n" + _is("d[0].q", "2"),
    # The load and the stride without the inference: ritz1 read one byte.
    "annotated": "    let e: *S = b[1][0]\n" + _is("e[1].q", "2"),
    "sum_stride": _is("(*(b[0] + 1)).q", "2"),
    # A store to `b[i][j]` is one to ps[1]; ritz1 stored through its value.
    "element_store": "    b[0][1] = @s0[0]\n" + _is("ps[1].q", "1"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PTR_PTR_ELEMENT_INDEX))
def test_ptr_ptr_element_index_is_a_pointer(run_with, name, compiler):
    program = _PP_MAIN + PTR_PTR_ELEMENT_INDEX[name]
    assert run_with(compiler, f"pp_{name}", program) == 0


# A Drop pointee isn't copied out: each compiler refuses it at the read, as
# ritz0 does `let c = *p`.  ritz1 copied `*a[0]` silently.
_DROP_MAIN = (
    "var DROPS: i32 = 0\n\nstruct T\n    id: i32\n\nimpl Drop for T\n    fn drop(self: @&T)\n"
    "        DROPS = DROPS + 1\n\npub fn main() -> i32\n    var s: [2]T\n    var a: [2]*T\n"
    "    a[0] = @s[1]\n    a[1] = @s[0]\n    let p: *T = @s[1]\n")
_DROP_LINE = _DROP_MAIN.count("\n") + 1
DROP_READS = {**INFERRED_COPIES, "pointer_index": "p[0]"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(DROP_READS))
def test_untyped_let_does_not_copy_a_drop_pointee(compile_with, name, compiler):
    program = _DROP_MAIN + f"    let c = {DROP_READS[name]}\n    return c.id\n"
    comp, _, _ = compile_with(compiler, f"drop_{name}", program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "cannot move out of a reference" in out, out
    assert f":{_DROP_LINE}:13" in out, out


# AGAST #2378: the clone of a generic `a:& [N]*T` took T for the element, so
# ritz1 read `[2]*i16` as `[2]i16` and refused its own array at the call.  The
# element is a `*T`: T is what it points at.
_GENERIC_PTR_FN = (
    "struct P\n    m: i64\n    q: i16\n\n"
    "fn f<T>(a:& [2]*T, t: T) -> i32\n    *a[0] = t\n    return 0\n\n")
GENERIC_PTR_ELEMENT = {
    "scalar_read": "fn g<T>(a:& [2]*T, t: T) -> i32\n" + _is("*a[1]") + "\n"
    + "pub fn main() -> i32\n" + _X + "    return g<i16>(a, 0 as i16)\n",
    "scalar_write": _GENERIC_PTR_FN + "pub fn main() -> i32\n" + _X
    + "    f<i16>(a, 9 as i16)\n" + _is("x[1]", "9"),
    "struct_write": _GENERIC_PTR_FN + "pub fn main() -> i32\n    var s: [2]P\n    s[1].q = 4\n"
    + "    var a: [2]*P\n    a[0] = @s[1]\n    a[1] = @s[0]\n    var t: P\n    t.m = 0\n    t.q = 6\n"
    + "    f<P>(a, t)\n" + _is("s[1].q", "6"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(GENERIC_PTR_ELEMENT))
def test_generic_pointer_element_mut_param(run_with, name, compiler):
    assert run_with(compiler, f"generic_ptr_{name}", GENERIC_PTR_ELEMENT[name]) == 0


# What it still refuses: another length, or an element that isn't a `*T`.
GENERIC_PTR_WRONG = {
    "wrong_len": "    var b: [3]*i16\n    b[0] = @x[0]\n    return f<i16>(b, 0 as i16)\n",
    "value_element": "    var y: [2]i16\n    return f<i16>(y, 0 as i16)\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(GENERIC_PTR_WRONG))
def test_generic_pointer_element_refuses_another_array(compile_with, name, compiler):
    program = _GENERIC_PTR_FN + "pub fn main() -> i32\n" + _X + GENERIC_PTR_WRONG[name]
    comp, _, _ = compile_with(compiler, f"generic_ptr_wrong_{name}", program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    if compiler != "ritz0":
        assert "the array isn't the one the parameter points at" in out, out


# ritz0 has these right, ritz1 doesn't, and each is its own bug.  Strict, so the
# fix flags the row.
KNOWN_GAPS = {
    "pointer_index_inferred_copy": (3052, _COPY_MAIN + "    let c = p[0]\n" + _is("c.q", "2")),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(KNOWN_GAPS))
def test_ritz0_has_the_known_gaps_right(run_with, name):
    assert run_with("ritz0", name, KNOWN_GAPS[name][1]) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize(
    "name",
    [pytest.param(n, marks=pytest.mark.xfail(strict=True, reason=f"AGAST #{KNOWN_GAPS[n][0]}"))
     for n in sorted(KNOWN_GAPS)])
def test_ritz1_known_gaps(run_with, name, compiler):
    assert run_with(compiler, name, KNOWN_GAPS[name][1]) == 0
