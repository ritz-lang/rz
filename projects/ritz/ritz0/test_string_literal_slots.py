#!/usr/bin/env python3
"""A string literal takes `*u8` from its slot; nothing else does (LARB R3, #2341).

A literal has no fixed type until a slot gives it one, as `5`, `null` and `[1, 2]`
already behave. `"..."` is StrView by default and `*u8` in any `*u8` slot, and every
literal is stored NUL-terminated. Before this `take("A")` worked but `let p: *u8 =
"A"`, `return` and a field did not, while `take(sv)` compiled with no NUL promise.

A non-literal StrView (`sv as *u8` too) and a String never fit `*u8`: write `.ptr`
or `string_as_ptr`. A literal that doesn't fit its element or scalar type is an
error wherever it is, and a non-literal array element narrows only under section
7.5. `[1, 300]` into `[2]u8` was a silent 44 on both compilers.

Every table goes through ritz0, ritz1 and ritz1_selfhosted, which must give the
same located error. The accepted half is run, not only compiled, so rejecting
everything fails it, and so does a literal handed over as a `{ ptr, len }` pair.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link
from ritz0_inproc import run_ritz0

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = pytest.mark.batched

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# ritz0 needs the import to know a StrView's fields. Each table's line numbers
# count from after it, so `_compile` adds it and the assertion adds its one line.
_PRELUDE = "import ritzlib.strview\n"
_MAIN = "fn main() -> i32\n    0\n"
_SV = "struct Holder\n    p: *u8\n"
_STRVIEW = ("a StrView is not a `*u8`: only a string literal converts; "
            "write `.ptr` if you know it is NUL-terminated")
_STRING = "a String is not a `*u8`: write `string_as_ptr(@&s)`"
_IMPORT_STRING = "import ritzlib.string\n"
_MAKE_STRING = 'var s: String = string_from("A")'


def _fn(params, body, ret="i64"):
    """`fn f(params) -> ret` with `body` indented, then a main: line 2 is body[0]."""
    return f"fn f({params}) -> {ret}\n" + "".join(
        f"    {line}\n" for line in body.split("\n")) + _MAIN


def _fits(value, ty):
    return f"`{value}` does not fit in `{ty}`"


# name -> (source, line, col, message)
REJECTED = {
    # A non-literal StrView, at every slot a literal is legal in.
    "strview_let": (_fn("s: StrView", "let p: *u8 = s\n0"), 2, 18, _STRVIEW),
    "strview_var": (_fn("s: StrView", "var p: *u8 = s\n0"), 2, 18, _STRVIEW),
    "strview_assign": (_fn("s: StrView", "var p: *u8 = null\np = s\n0"), 3, 9, _STRVIEW),
    "strview_return": (_fn("s: StrView", "return s", "*u8"), 2, 12, _STRVIEW),
    "strview_tail": (_fn("s: StrView", "s", "*u8"), 2, 5, _STRVIEW),
    "strview_field": (_SV + _fn("s: StrView", "let h = Holder { p: s }\n0"), 4, 25, _STRVIEW),
    "strview_field_assign": (_SV + _fn("s: StrView, h: *Holder", "h.p = s\n0"), 4, 11, _STRVIEW),
    "strview_element": (_fn("s: StrView", "let a: [1]*u8 = [s]\n0"), 2, 22, _STRVIEW),
    "strview_element_assign": (_fn("s: StrView", "var a: [1]*u8 = [null]\na[0] = s\n0"),
                               3, 12, _STRVIEW),
    "strview_arm": (_fn("s: StrView, n: i64", 'let p: *u8 = if n > 0\n    "A"\nelse\n    s\n0'),
                    5, 9, _STRVIEW),
    "strview_arg": ("fn take(p: *u8) -> i32\n    0\n" + _fn("s: StrView", "take(s)\n0"),
                    4, 10, _STRVIEW),
    "strview_method_arg": ("struct W\n    n: i64\nimpl W\n    fn take(self, p: *u8) -> i32\n"
                           "        0\n" + _fn("s: StrView, w: W", "w.take(s)\n0"),
                           7, 12, _STRVIEW),
    "strview_extern_arg": ('extern fn take(p: *u8) -> i32\n' + _fn("s: StrView", "take(s)\n0"),
                           3, 10, _STRVIEW),
    "strview_arm_local": (_fn("n: i64", 'let p: *u8 = if n > 0\n    let s: StrView = "A"\n    s\n'
                                       'else\n    c"B"\n0'), 4, 9, _STRVIEW),
    "strview_arm_local_inferred": (_fn("n: i64", 'let p: *u8 = if n > 0\n    let s = "A"\n    s\n'
                                                'else\n    c"B"\n0'), 4, 9, _STRVIEW),
    "strview_fn_pointer_arg": ("fn take(p: *u8) -> i32\n    0\n"
                               + _fn("s: StrView", "let f: fn(*u8) -> i32 = take\nf(s)\n0"),
                               5, 7, _STRVIEW),
    "strview_local": (_fn("", 'let s = "A"\nlet p: *u8 = s\n0'), 3, 18, _STRVIEW),
    "strview_as": (_fn("s: StrView", "let p = s as *u8\n0"), 2, 13, _STRVIEW),
    "strview_as_literal_local": (_fn("", 'let s = "A"\nlet p = s as *u8\n0'), 3, 13, _STRVIEW),

    # A String.
    "string_let": (_IMPORT_STRING + _fn("", f"{_MAKE_STRING}\nlet p: *u8 = s\n0"), 4, 18, _STRING),
    "string_arg": (_IMPORT_STRING + "fn take(p: *u8) -> i32\n    0\n"
                   + _fn("", f"{_MAKE_STRING}\ntake(s)\n0"), 6, 10, _STRING),
    "string_return": (_IMPORT_STRING + _fn("", f"{_MAKE_STRING}\nreturn s", "*u8"),
                      4, 12, _STRING),
    "string_field": (_IMPORT_STRING + _SV
                     + _fn("", f"{_MAKE_STRING}\nlet h = Holder {{ p: s }}\n0"), 6, 25, _STRING),
    "string_arm_local": (_IMPORT_STRING + _fn("n: i64", "let p: *u8 = if n > 0\n"
                                              f"    {_MAKE_STRING}\n    s\nelse\n"
                                              '    c"B"\n0'), 5, 9, _STRING),
    "string_as": (_IMPORT_STRING + _fn("", f"{_MAKE_STRING}\nlet p = s as *u8\n0"), 4, 13, _STRING),

    # A literal that doesn't fit, wherever it is.
    "fit_let": (_fn("", "let a: u8 = 300\n0"), 2, 17, _fits(300, "u8")),
    "fit_var": (_fn("", "var a: u8 = 300\n0"), 2, 17, _fits(300, "u8")),
    "fit_negative": (_fn("", "let a: u8 = -1\n0"), 2, 17, _fits(-1, "u8")),
    "fit_i8": (_fn("", "let a: i8 = 200\n0"), 2, 17, _fits(200, "i8")),
    "fit_element": (_fn("", "var a: [2]u8 = [1, 300]\n0"), 2, 24, _fits(300, "u8")),
    "fit_element_let": (_fn("", "let a: [2]u8 = [300, 1]\n0"), 2, 21, _fits(300, "u8")),
    "fit_fill": (_fn("", "let a: [2]u8 = [300; 2]\n0"), 2, 21, _fits(300, "u8")),
    "fit_assign": (_fn("", "var a: u8 = 0\na = 300\n0"), 3, 9, _fits(300, "u8")),
    "fit_return": (_fn("", "return 300", "u8"), 2, 12, _fits(300, "u8")),
    "fit_tail": (_fn("", "300", "u8"), 2, 5, _fits(300, "u8")),
    "fit_arg": ("fn take(b: u8) -> i32\n    0\n" + _fn("", "take(300)\n0"), 4, 10, _fits(300, "u8")),
    "fit_element_field": ("struct A2\n    a: [2]u8\n" + _fn("", "let v = A2 { a: [1, 300] }\n0"),
                          4, 25, _fits(300, "u8")),
    "fit_element_arg": ("fn take(a: [2]u8) -> i32\n    0\n" + _fn("", "take([1, 300])\n0"),
                        4, 14, _fits(300, "u8")),
    "fit_method_tail": ("struct W\n    n: i64\nimpl W\n    fn g(self) -> u8\n        300\n" + _MAIN,
                        5, 9, _fits(300, "u8")),
    "fit_field": ("struct B\n    b: u8\n" + _fn("", "let v = B { b: 300 }\n0"),
                  4, 20, _fits(300, "u8")),
    "fit_arm": (_fn("n: i64", "let a: u8 = if n > 0\n    1\nelse\n    300\n0"),
                5, 9, _fits(300, "u8")),

    "fit_i32_hex": (_fn("", "let a: i32 = 0xDEADBEEF\n0"), 2, 18, _fits(3735928559, "i32")),
    "fit_i64_hex": (_fn("", "let a: i64 = 0xF000000000000000\n0"), 2, 18,
                    _fits(17293822569102704640, "i64")),
    "fit_u64_negative": (_fn("", "let a: u64 = -1\n0"), 2, 18, _fits(-1, "u64")),
    # AGAST #2138: ritz1 holds a literal as an i64, so 2^63.. reads negative and
    # -(2^63 + 1).. reads positive. Both are refused, and named as written.
    "fit_i64_two_63": (_fn("", "let a: i64 = 9223372036854775808\n0"), 2, 18,
                       _fits(9223372036854775808, "i64")),
    "fit_i64_u64_max": (_fn("", "let a: i64 = 18446744073709551615\n0"), 2, 18,
                        _fits(18446744073709551615, "i64")),
    "fit_i64_below_min": (_fn("", "let a: i64 = -9223372036854775809\n0"), 2, 18,
                          _fits(-9223372036854775809, "i64")),
    "fit_u64_below_i64_min": (_fn("", "let a: u64 = -9223372036854775809\n0"), 2, 18,
                              _fits(-9223372036854775809, "u64")),
    "fit_i32_below_i64_min": (_fn("", "let a: i32 = -9223372036854775809\n0"), 2, 18,
                              _fits(-9223372036854775809, "i32")),
    # AGAST #3083: ritz1 read 2^64.. mod 2^64, so these were 0, 10 and -1. A literal
    # past u64 fits nothing, in any base, and is named in decimal as ritz0 does.
    "fit_u64_two_64": (_fn("", "let a: u64 = 18446744073709551616\n0"), 2, 18,
                       _fits(18446744073709551616, "u64")),
    "fit_u8_wraps_small": (_fn("", "let a: u8 = 18446744073709551626\n0"), 2, 17,
                           _fits(18446744073709551626, "u8")),
    "fit_u64_hex_two_64": (_fn("", "let a: u64 = 0x10000000000000000\n0"), 2, 18,
                           _fits(18446744073709551616, "u64")),
    "fit_u64_bin_two_64": (_fn("", "let a: u64 = 0b1" + "0" * 64 + "\n0"), 2, 18,
                           _fits(18446744073709551616, "u64")),
    "fit_i64_neg_u64_max": (_fn("", "let c: i64 = -18446744073709551615\n0"), 2, 18,
                            _fits(-18446744073709551615, "i64")),
    "fit_i64_neg_two_64": (_fn("", "let c: i64 = -18446744073709551616\n0"), 2, 18,
                           _fits(-18446744073709551616, "i64")),
    "fit_const": ("const K: u8 = 300\n" + _MAIN, 1, 15, _fits(300, "u8")),
    "fit_const_element": ("const A: [2]u8 = [1, 300]\n" + _MAIN, 1, 22, _fits(300, "u8")),
    "fit_global": ("var G: u8 = 300\n" + _MAIN, 1, 13, _fits(300, "u8")),

    # A string literal isn't a number, and a number isn't a string.
    "string_lit_into_int": (_fn("", 'let a: i32 = "A"\n0'), 2, 18,
                            "a string literal does not fit in `i32`"),
    "string_lit_into_element": (_fn("", 'let a: [1]i32 = ["A"]\n0'), 2, 22,
                                "a string literal does not fit in `i32`"),

    # A non-literal element narrows only under section 7.5.
    "narrow_element": (_fn("k: i64", "let a: [2]u8 = [1, k]\n0"), 2, 24, "implicit narrowing"),
    "narrow_element_field": ("struct A2\n    a: [2]u8\n"
                             + _fn("k: i64", "let v = A2 { a: [1, k] }\n0"), 4, 25, "implicit narrowing"),
    "narrow_element_arg": ("fn take(a: [2]u8) -> i32\n    0\n"
                           + _fn("k: i64", "take([1, k])\n0"), 4, 14, "implicit narrowing"),
    "narrow_large_fill": (_fn("k: i64", "var a: [100]u8 = [k; 100]\n0"), 2, 23, "implicit narrowing"),
    "narrow_fill": (_fn("k: i64", "let a: [2]u8 = [k; 2]\n0"), 2, 21, "implicit narrowing"),
    "narrow_element_var": (_fn("k: i32", "var a: [2]u8 = [k, 1]\n0"), 2, 21, "implicit narrowing"),
}


def _first(ret_body):
    return f"{ret_body}fn main() -> i32\n    *g() as i32\n"


# name -> (source, exit code)
ACCEPTED = {
    "let": ('fn main() -> i32\n    let p: *u8 = "A"\n    *p as i32\n', 65),
    "var": ('fn main() -> i32\n    var p: *u8 = "A"\n    *p as i32\n', 65),
    "assign": ('fn main() -> i32\n    var p: *u8 = null\n    p = "A"\n    *p as i32\n', 65),
    "return": (_first('fn g() -> *u8\n    return "A"\n'), 65),
    "tail": (_first('fn g() -> *u8\n    "A"\n'), 65),
    "tail_if": ('fn g(n: i64) -> *u8\n    if n > 0\n        "A"\n    else\n        "B"\n'
                "fn main() -> i32\n    *g(0) as i32\n", 66),
    "return_if": ('fn g(n: i64) -> *u8\n    return if n > 0\n        "A"\n    else\n        "B"\n'
                  "fn main() -> i32\n    *g(1) as i32\n", 65),
    "field": (_SV + 'fn main() -> i32\n    let h = Holder { p: "A" }\n    *h.p as i32\n', 65),
    "field_assign": (_SV + "fn main() -> i32\n    var h = Holder { p: null }\n"
                     '    h.p = "A"\n    *h.p as i32\n', 65),
    "field_through_pointer": (_SV + 'fn put(h: *Holder)\n    h.p = "A"\n'
                              "fn main() -> i32\n    var h = Holder { p: null }\n"
                              "    put(@h)\n    *h.p as i32\n", 65),
    "element": ('fn main() -> i32\n    let a: [2]*u8 = ["A", "B"]\n    *a[1] as i32\n', 66),
    "element_assign": ('fn main() -> i32\n    var a: [2]*u8 = [null, null]\n    a[1] = "B"\n'
                       "    *a[1] as i32\n", 66),
    "fill": ('fn main() -> i32\n    let a: [2]*u8 = ["A"; 2]\n    *a[1] as i32\n', 65),
    "arm_if": ('fn main() -> i32\n    let n: i64 = 1\n    let p: *u8 = if n > 0\n        "A"\n'
               '    else\n        "B"\n    *p as i32\n', 65),
    "arm_match": ('fn main() -> i32\n    let n: i64 = 2\n    let p: *u8 = match n\n'
                  '        1 => "A"\n        _ => "B"\n    *p as i32\n', 66),
    "arm_block_tail": ('fn main() -> i32\n    let n: i64 = 0\n    let p: *u8 = if n > 0\n'
                       '        let k: i64 = 1\n        "A"\n    else\n        "B"\n'
                       "    *p as i32\n", 66),
    "arm_beside_pointer": ('fn main() -> i32\n    let n: i64 = 1\n    let q: *u8 = c"B"\n'
                           '    let p: *u8 = if n > 0\n        "A"\n    else\n        q\n'
                           "    *p as i32\n", 65),
    "arg": ('fn take(p: *u8) -> i32\n    *p as i32\nfn main() -> i32\n    take("A")\n', 65),
    "method_arg": ("struct W\n    n: i64\nimpl W\n    fn take(self, p: *u8) -> i32\n"
                   "        *p as i32\nfn main() -> i32\n    let w = W { n: 0 }\n"
                   '    w.take("A")\n', 65),
    "method_tail": ("struct W\n    n: i64\nimpl W\n    fn g(self) -> *u8\n        \"A\"\n"
                    "fn main() -> i32\n    let w = W { n: 0 }\n    *w.g() as i32\n", 65),
    "method_return": ("struct W\n    n: i64\nimpl W\n    fn g(self) -> *u8\n        return \"A\"\n"
                      "fn main() -> i32\n    let w = W { n: 0 }\n    *w.g() as i32\n", 65),
    "array_arg": ("fn take(a: [2]*u8) -> i32\n    *a[1] as i32\n"
                  'fn main() -> i32\n    take(["A", "B"])\n', 66),
    "array_field": ("struct A2\n    a: [2]*u8\n"
                    'fn main() -> i32\n    let v = A2 { a: ["A", "B"] }\n    *v.a[1] as i32\n', 66),
    "large_fill_field": ("struct A2\n    a: [100]*u8\n"
                         'fn main() -> i32\n    let v = A2 { a: ["A"; 100] }\n    *v.a[99] as i32\n', 65),
    "enum_payload": ("enum E\n    V(*u8)\n    N\n"
                     'fn main() -> i32\n    let e = E.V("A")\n    match e\n'
                     "        V(p) => *p as i32\n        N => 0\n", 65),
    "option_payload": ("fn g() -> Option<*u8>\n    Some(\"A\")\n"
                       "fn main() -> i32\n    match g()\n        Some(p) => *p as i32\n        None => 0\n", 65),
    "fn_pointer_arg": ('fn take(p: *u8) -> i32\n    *p as i32\nfn main() -> i32\n'
                       '    let f: fn(*u8) -> i32 = take\n    f("A")\n', 65),
    "fn_pointer_field_arg": ('struct H\n    f: fn(*u8) -> i32\nfn take(p: *u8) -> i32\n    *p as i32\n'
                             'fn main() -> i32\n    let h = H { f: take }\n    (h.f)("A")\n', 65),
    "as_cast": ('fn main() -> i32\n    let p = "A" as *u8\n    *p as i32\n', 65),
    "const": ('const P: *u8 = "A"\nfn main() -> i32\n    *P as i32\n', 65),
    "generic_arg": ('fn id<T>(x: T) -> T\n    x\nfn main() -> i32\n'
                    '    let p: *u8 = id<*u8>("A")\n    *p as i32\n', 65),
    "terminator_ends_a_scan": (
        'fn strlen_of(p: *u8) -> i64\n    var n: i64 = 0\n    while *(p + n) != 0\n        n += 1\n'
        '    n\nfn main() -> i32\n    strlen_of("ABC") as i32\n', 3),

    # Every literal is stored NUL-terminated, whichever type it took.
    "nul_terminated": ('fn main() -> i32\n    let p: *u8 = "AB"\n    *(p + 2) as i32\n', 0),
    "strview_ptr_is_terminated": ('fn main() -> i32\n    let s: StrView = "AB"\n'
                                  "    *(s.ptr + 2) as i32\n", 0),
    "empty_literal": ('fn main() -> i32\n    let p: *u8 = ""\n    *p as i32\n', 0),

    # The default stays StrView, and only the slot's own literal is retyped.
    "default_is_strview": ('fn main() -> i32\n    let s = "AB"\n    s.len as i32\n', 2),
    "strview_slot": ('fn main() -> i32\n    let s: StrView = "AB"\n    s.len as i32\n', 2),
    "literal_inside_call_keeps_its_slot": (
        'fn len(s: StrView) -> *u8\n    s.ptr\n'
        'fn main() -> i32\n    let p: *u8 = len("A")\n    *p as i32\n', 65),
    "literal_into_strview_param": (
        'fn pick(s: StrView) -> i64\n    s.len\nfn main() -> i32\n    let n: i64 = pick("AB")\n'
        "    n as i32\n", 2),

    # The ways out still work.
    "dot_ptr": ('fn take(p: *u8) -> i32\n    *p as i32\nfn main() -> i32\n'
                '    let s: StrView = "A"\n    take(s.ptr)\n', 65),

    # What fits still fits.
    "fit_edges": ("fn main() -> i32\n    let a: u8 = 255\n    let b: i8 = -128\n"
                  "    let c: u16 = 65535\n    (a as i32) - 255 + (b as i32) + 128 + (c as i32) - 65535\n", 0),
    "const_cstr": ('const P: *u8 = c"A"\nfn main() -> i32\n    *P as i32\n', 65),
    "fit_u64_hex": ("fn main() -> i32\n    let a: u64 = 0xF000000000000000\n"
                    "    (a >> 60) as i32\n", 15),
    "fit_i64_min": ("fn main() -> i32\n    let b: i64 = -9223372036854775808\n    if b < 0\n"
                    "        return 3\n    0\n", 3),
    # AGAST #2138: the u64 controls, in decimal, and i64's own edge.
    "fit_u64_two_63": ("fn main() -> i32\n    let a: u64 = 9223372036854775808\n"
                       "    (a >> 63) as i32\n", 1),
    "fit_u64_max": ("fn main() -> i32\n    let a: u64 = 18446744073709551615\n"
                    "    (a >> 60) as i32\n", 15),
    # AGAST #3083: u64::MAX in hex is the last literal that doesn't overflow.
    "fit_u64_hex_max": ("fn main() -> i32\n    let a: u64 = 0xFFFFFFFFFFFFFFFF\n"
                        "    (a >> 60) as i32\n", 15),
    "fit_i64_max": ("fn main() -> i32\n    let a: i64 = 9223372036854775807\n"
                    "    (a >> 62) as i32\n", 1),
    "fit_cast_says_so": ("fn main() -> i32\n    let c: i64 = 0xF000000000000000 as i64\n    if c < 0\n"
                         "        return 4\n    0\n", 4),
    "fit_element_edges": ("fn main() -> i32\n    let a: [2]u8 = [0, 255]\n    a[1] as i32\n", 255),
    "fit_char_element": ("fn main() -> i32\n    let a: [2]u8 = ['A', 'B']\n    a[1] as i32\n", 66),
    "element_proven": ("fn main() -> i32\n    let k: i64 = 300\n    let a: [1]u8 = [k & 255]\n"
                       "    a[0] as i32\n", 44),
    "element_cast": ("fn main() -> i32\n    let k: i64 = 300\n    let a: [1]u8 = [k as u8]\n"
                     "    a[0] as i32\n", 44),
    "element_same_width": ("fn main() -> i32\n    let k: u8 = 7\n    let a: [1]u8 = [k]\n"
                           "    a[0] as i32\n", 7),
    "element_arith": ("fn main() -> i32\n    let k: u8 = 7\n    let a: [1]u8 = [k + 1]\n"
                      "    a[0] as i32\n", 8),
    "element_widens": ("fn main() -> i32\n    let k: u8 = 7\n    let a: [1]i64 = [k as i64]\n"
                       "    a[0] as i32\n", 7),
    # A global and a const array element are slots too: ritz1 points them at the
    # literal's own `@.str` (#2357).
    "global": ('var G: *u8 = "A"\nfn main() -> i32\n    *G as i32\n', 65),
    "const_element": ('const A: [2]*u8 = ["A", "B"]\nfn main() -> i32\n    *A[1] as i32\n', 66),
}


# Shapes ritz1 refuses with an error of its own, whatever the literal: it lowers
# no N-D initializer, no tuple type, no `dyn` and no `await`.
RITZ0_REJECTED = {
    "fit_element_nested": (_fn("", "let a: [1][2]u8 = [ [1, 300] ]\n0"), 2, 29, _fits(300, "u8")),
}
RITZ0_ACCEPTED = {
    "dyn_arg": ('trait T\n    fn take(self, p: *u8) -> i32\nstruct S\n    n: i64\nimpl T for S\n'
                '    fn take(self, p: *u8) -> i32\n        *p as i32\n'
                'fn go(t: dyn T) -> i32\n    t.take("A")\n'
                "fn main() -> i32\n    var s = S { n: 0 }\n    go(@s as dyn T)\n", 65),
    "tuple_element": ('fn main() -> i32\n    let t: (i32, *u8) = (1, "A")\n    *t.1 as i32\n', 65),
    "element_nested": ('fn main() -> i32\n    var a: [1][2]*u8 = [ ["A", "B"] ]\n'
                       "    *a[0][1] as i32\n", 66),
}

# Compiled, not run: nothing to link `take` against, and a one-file link has no
# ritzlib.string to call. A literal that stayed a StrView is refused, so this is
# the extern slot's own test.
# `await` outside an async fn is the poll loop, which passes the arguments itself.
_ASYNC_ARG = 'async fn g(p: *u8) -> i32\n    *p as i32\nfn main() -> i32\n    await g("A")\n'
_EXTERN_ARG = 'extern fn take(p: *u8) -> i32\nfn main() -> i32\n    take("A")\n'
_STRING_AS_PTR = (_IMPORT_STRING + 'fn main() -> i32\n    var s: String = string_from("A")\n'
                  "    let p: *u8 = string_as_ptr(@&s)\n    *p as i32\n")


def _emit(compiler, src, ll, work, roots):
    env = dict(os.environ, RITZ_PATH=roots)
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=work,
                          env=env, capture_output=True, text=True, timeout=300)


def _compile(request, compiler, tmp_path, source):
    batching.per_row()  # AGAST #2806
    src = tmp_path / "unit.ritz"
    src.write_text(_PRELUDE + source)
    ll = tmp_path / "unit.ll"
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    return _emit(compiler, src, ll, tmp_path, f"{RITZ_ROOT}:{tmp_path}"), ll


def _link_cmd(compiler, ll, exe):
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(2, str(RITZ_START))
    return link


def _batch_build(compiler, src, work):
    """batching.run's `build`: compile and link a batch the way `_assert_runs` does a row."""
    ll = work / "unit.ll"
    proc = _emit(compiler, src, ll, work, f"{RITZ_ROOT}:{work}")
    if proc.returncode != 0 or not ll.exists():
        return False, proc.stdout + proc.stderr, None
    exe = work / "unit"
    link = fast_link.clang(_link_cmd(compiler, ll, exe), cwd=work, capture_output=True, text=True)
    return link.returncode == 0, link.stderr, exe


def _batch_compile(compiler, src, work):
    proc = _emit(compiler, src, work / "unit.ll", work, f"{RITZ_ROOT}:{work}")
    return proc.returncode, proc.stdout + proc.stderr


def _refusal(request, compiler, tmp_path, source, line, col):
    """(returncode, output, "line:col" to look for): batched if it can be (AGAST #2806)."""
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    got = batching.refused(compiler, _PRELUDE + source, _batch_compile, at=(line + 1, col),
                           filename="unit.ritz")
    if got is not None:
        return 1, got[0], got[1]
    proc, _ = _compile(request, compiler, tmp_path, source)
    return proc.returncode, proc.stdout + proc.stderr, f"{line + 1}:{col}"


def _assert_runs(request, compiler, tmp_path, name, source, code):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    got = batching.run(compiler, _PRELUDE + source, _batch_build, compile=_batch_compile,  # #2806
                       filename="unit.ritz")
    if got is not None:
        assert got == code, f"{compiler}, {name}"
        return
    proc, ll = _compile(request, compiler, tmp_path, source)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    exe = tmp_path / "unit"
    built = subprocess.run(_link_cmd(compiler, ll, exe), cwd=tmp_path, capture_output=True, text=True)
    assert built.returncode == 0, f"{compiler}, {name}: link:\n{built.stderr[-1500:]}"
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_what_does_not_fit_is_a_located_error(request, tmp_path, compiler, name):
    source, line, col, message = REJECTED[name]
    code, output, where = _refusal(request, compiler, tmp_path, source, line, col)
    assert code != 0, f"{compiler} accepted it:\n{output}"
    assert message in output, output
    assert re.search(rf"unit\.ritz:{where}\b", output), output


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_what_fits_compiles_and_runs(request, tmp_path, compiler, name):
    source, code = ACCEPTED[name]
    _assert_runs(request, compiler, tmp_path, name, source, code)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_REJECTED))
def test_ritz0_only_rejected(request, tmp_path, name):
    source, line, col, message = RITZ0_REJECTED[name]
    code, output, where = _refusal(request, "ritz0", tmp_path, source, line, col)
    assert code != 0 and message in output, output
    assert re.search(rf"unit\.ritz:{where}\b", output), output


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_ACCEPTED))
def test_ritz0_only_accepted(request, tmp_path, name):
    source, code = RITZ0_ACCEPTED[name]
    _assert_runs(request, "ritz0", tmp_path, name, source, code)


# `--check-types` runs before emission and has its own wording. Generic sites only.
CHECKED_ACCEPTED = ["let", "var", "assign", "return", "tail", "field", "arg", "element",
                    "arm_if", "arm_match", "arm_beside_pointer", "tail_if", "strview_slot"]
CHECKED_REJECTED = ["strview_let", "strview_return", "strview_arg", "strview_field",
                    "strview_arm", "string_let", "string_arg"]


def _check_types(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(_PRELUDE + source)
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    return run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), "--check-types"],
                     cwd=tmp_path, env=env, timeout=300)


@pytest.mark.integration
@pytest.mark.parametrize("name", CHECKED_ACCEPTED)
def test_check_types_takes_a_literal_in_a_pointer_slot(tmp_path, name):
    proc = _check_types(tmp_path, ACCEPTED[name][0])
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", CHECKED_REJECTED)
def test_check_types_refuses_a_non_literal_in_a_pointer_slot(tmp_path, name):
    proc = _check_types(tmp_path, REJECTED[name][0])
    output = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "*u8" in output, output
    # The checker's own words: the emitter would have refused it anyway.
    assert "is not a `*u8`" not in output, output


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_literal_fits_an_extern_param(request, tmp_path, compiler):
    proc, _ = _compile(request, compiler, tmp_path, _EXTERN_ARG)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.integration
def test_a_literal_fits_an_async_param(request, tmp_path):
    # ritz0 only: ritz1 has no `await`, and ritz0's output for this doesn't link yet.
    proc, _ = _compile(request, "ritz0", tmp_path, _ASYNC_ARG)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_string_as_ptr_is_the_way_out(request, tmp_path, compiler):
    proc, _ = _compile(request, compiler, tmp_path, _STRING_AS_PTR)
    assert proc.returncode == 0, proc.stdout + proc.stderr
