#!/usr/bin/env python3
"""`bool` is its own type (LARB R4, AGAST #2342).

Before this `2 and 1` as a condition was false on ritz0 and true on ritz1, and so
were `let b: bool = 2` and `256 as bool`, silently; `if p` was a clang error on
ritz0 and compiled on ritz1.

Conditions and `and`/`or`/`not` take bool. Bitwise operators take integers on both
sides. `==`/`!=` need both sides the same kind. bool converts to nothing implicitly
and nothing converts to it: `b as i32` is 0 or 1, and `x as bool` is gone. Every
table here goes through ritz0, ritz1 and ritz1_selfhosted, which must give the
same located error.

The accepted half is load-bearing: it is run, not only compiled, so rejecting
everything fails it, and so does a value whose type a compiler lost. ritz1 keeps a
bool local in an i64 slot, so losing track of one reads as an integer condition.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

_MAIN = "fn main() -> i32\n    0\n"
_WRITE_NE0 = "`x != 0`"
_WRITE_NULL = "`p != null`"
_WRITE_AS = "`b as i32`"
_INT_COND = f"must be bool, got an integer: write {_WRITE_NE0}"
_PTR_COND = f"must be bool, got a pointer: write {_WRITE_NULL}"
_PAREN = "`x & 1 == 1` is `x & (1 == 1)`: parenthesise `(x & 1) == 1`"
_S = "struct S\n    b: bool\n    n: i64\n"
_I2B = f"cannot use an integer as bool: write {_WRITE_NE0}"
_B2I = f"cannot use bool as an integer: write {_WRITE_AS}"


def _fn(params, body, ret="i64"):
    """`fn f(params) -> ret` with `body` indented, then a main: line 2 is body[0]."""
    return f"fn f({params}) -> {ret}\n" + "".join(
        f"    {line}\n" for line in body.split("\n")) + _MAIN


# name -> (source, line, col, message)
REJECTED = {
    # Conditions.
    "if_int": (_fn("n: i64", "if n\n    return 1\n0"), 2, 8, f"if condition {_INT_COND}"),
    "if_int_literal": (_fn("", "if 1\n    return 1\n0"), 2, 8, f"if condition {_INT_COND}"),
    "if_call": ("fn g() -> i32\n    1\n" + _fn("", "if g()\n    return 1\n0"),
                4, 8, f"if condition {_INT_COND}"),
    "if_pointer": (_fn("p: *u8", "if p\n    return 1\n0"), 2, 8, f"if condition {_PTR_COND}"),
    "if_float": (_fn("x: f64", "if x\n    return 1\n0"), 2, 8,
                 "if condition must be bool, got a float"),
    "if_struct": (_S + _fn("s: S", "if s\n    return 1\n0"), 5, 8,
                  "if condition must be bool, got a struct or enum"),
    "else_if_int": (_fn("n: i64", "if n > 0\n    return 1\nelse if n\n    return 2\n0"),
                    4, 13, f"if condition {_INT_COND}"),
    "if_value_int": (_fn("n: i64", "let v: i64 = if n\n    1\nelse\n    2\nv"), 2, 21,
                     f"if condition {_INT_COND}"),
    "while_int": (_fn("n: i64", "while n\n    return 1\n0"), 2, 11, f"while condition {_INT_COND}"),
    "while_literal": (_fn("", "while 1\n    return 1\n0"), 2, 11, f"while condition {_INT_COND}"),
    "assert_int": ("[[test]]\nfn t() -> i32\n    let n: i64 = 1\n    assert n\n    0\n" + _MAIN,
                   4, 12, f"assert condition {_INT_COND}"),

    # `and`, `or`, `not`.
    "and_ints": (_fn("", "if 2 and 1\n    return 1\n0"), 2, 8,
                 f"operand of `and` {_INT_COND}"),
    "or_ints": (_fn("a: i64, b: i64", "if a or b\n    return 1\n0"), 2, 8,
                f"operand of `or` {_INT_COND}"),
    "and_right_int": (_fn("a: bool, n: i64", "if a and n\n    return 1\n0"), 2, 14,
                      f"operand of `and` {_INT_COND}"),
    "or_left_pointer": (_fn("p: *u8, a: bool", "if p or a\n    return 1\n0"), 2, 8,
                        f"operand of `or` {_PTR_COND}"),
    "and_as_a_value": (_fn("a: i64, b: i64", "let v: bool = a and b\nif v\n    return 1\n0"),
                       2, 19, f"operand of `and` {_INT_COND}"),
    "ampamp_is_and": (_fn("a: i64, b: bool", "if a && b\n    return 1\n0"), 2, 8,
                      f"operand of `and` {_INT_COND}"),
    "pipepipe_is_or": (_fn("a: bool, b: i64", "if a || b\n    return 1\n0"), 2, 13,
                       f"operand of `or` {_INT_COND}"),
    "bang_is_not": (_fn("n: i64", "if !n\n    return 1\n0"), 2, 9, f"operand of `not` {_INT_COND}"),
    "not_int": (_fn("n: i64", "if not n\n    return 1\n0"), 2, 12, f"operand of `not` {_INT_COND}"),
    "not_binds_tighter_than_compare": (_fn("n: i64", "if not n == 1\n    return 1\n0"), 2, 12,
                                       f"operand of `not` {_INT_COND}"),
    "not_pointer": (_fn("p: *u8", "if not p\n    return 1\n0"), 2, 12,
                    f"operand of `not` {_PTR_COND}"),

    # Bitwise.
    "and_bits_on_a_compare": (_fn("x: i64", "if x & 1 == 1\n    return 1\n0"), 2, 12,
                              f"operand of `&` must be an integer, got bool: {_PAREN}"),
    "or_bits_on_a_compare": (_fn("x: i64", "let v: i64 = x | 1 == 1\nv"), 2, 22,
                             f"operand of `|` must be an integer, got bool: {_PAREN}"),
    "bits_left_bool": (_fn("a: bool, x: i64", "let v: i64 = a ^ x\nv"), 2, 18,
                       "operand of `^` must be an integer, got bool"),
    "bits_bool_with_bool": (_fn("a: bool, b: bool", "let v: bool = a & b\nif v\n    return 1\n0"),
                            2, 19, "operand of `&` must be an integer, got bool"),
    "shift_bool": (_fn("a: bool", "let v: i64 = a << 1\nv"), 2, 18,
                   "operand of `<<` must be an integer, got bool"),
    "shift_by_bool": (_fn("a: bool", "let v: i64 = 1 >> a\nv"), 2, 23,
                      "operand of `>>` must be an integer, got bool"),
    "bit_not_bool": (_fn("a: bool", "let v: i64 = ~a\nv"), 2, 19,
                     "operand of `~` must be an integer, got bool"),

    # Arithmetic is a conversion to an integer too.
    "add_bool": (_fn("a: bool", "let v: i64 = a + 1\nv"), 2, 18,
                 "operand of `+` must be a number, got bool"),
    "compound_add_bool": (_fn("", "var b: bool = true\nb += 1\n0"), 3, 5,
                          "operand of `+` must be a number, got bool"),
    "negate_bool": (_fn("a: bool", "let v: i64 = -a\nv"), 2, 19,
                    "operand of `-` must be a number, got bool"),

    # `==` and `!=`.
    "eq_bool_int": (_fn("b: bool", "if b == 1\n    return 1\n0"), 2, 8,
                    "cannot compare bool with an integer"),
    "ne_int_bool": (_fn("b: bool, n: i64", "if n != b\n    return 1\n0"), 2, 8,
                    "cannot compare bool with an integer"),
    "eq_compare_int": (_fn("a: i64", "if (a == 1) == 1\n    return 1\n0"), 2, 9,
                       "cannot compare bool with an integer"),
    "eq_bool_pointer": (_fn("b: bool, p: *u8", "if b == p\n    return 1\n0"), 2, 8,
                        "cannot compare bool with a pointer"),
    "lt_bool_int": (_fn("b: bool", "if b < 1\n    return 1\n0"), 2, 8,
                    "cannot compare bool with an integer"),

    # A bool into an integer slot, and an integer into a bool slot.
    "if_arm_mixes": (_fn("a: bool", "let v: i64 = if a then 1 else true\nv"), 2, 35, _B2I),
    "match_arm_mixes": (_fn("n: i64", "match n\n    0 => true\n    _ => 1", "bool"), 4, 14, _I2B),
    "tail_if_arm_int": (_fn("a: bool", "if a\n    1\nelse\n    0", "bool"), 2, 5, _I2B),
    "tail_match_all_ints": (_fn("n: i64", "match n\n    0 => 1\n    _ => 2", "bool"), 2, 5, _I2B),
    "return_if_value": (_fn("a: bool", "return if a then 1 else 0", "bool"), 2, 12, _I2B),
    "payload_int_as_condition": ("import ritzlib.option\n" + _fn(
        "o: Option<i32>", "match o\n    Some(v) =>\n        if v\n            return 1\n"
        "        0\n    None => 0"), 5, 16, f"if condition {_INT_COND}"),
    "binding_int_as_condition": (_fn("n: i64", "match n\n    v =>\n        if v\n"
                                     "            return 1\n        0"), 4, 16,
                                 f"if condition {_INT_COND}"),
    "payload_bool_as_int": ("import ritzlib.option\n" + _fn(
        "o: Option<bool>", "match o\n    Some(v) => v as i64 + (v + 1)\n    None => 0"), 4, 32,
        "operand of `+` must be a number, got bool"),
    "user_enum_payload_bool": ("enum E\n    A(bool)\n    B\n" + _fn(
        "e: E", "match e\n    A(v) =>\n        let n: i64 = v\n        n\n    B => 0"),
        7, 26, _B2I),
    "pointer_field_assign": (_S + _fn("p: *S", "p.b = 1\n0"), 5, 11, _I2B),
    "array_field_store": ("struct A\n    f: [2]bool\n" + _fn(
        "", "var a: A = A { f: [true, false] }\na.f[0] = 1\n0"), 5, 14, _I2B),
    "tail_if_own_local": (_fn("a: bool", "if a\n    let x: i64 = 2\n    x\nelse\n    3", "bool"),
                          2, 5, _I2B),
    "tail_if_arms_mix": (_fn("a: bool", "if a\n    let x: i64 = 2\n    x\nelse\n    false", "bool"),
                         6, 9, _B2I),
    "let_bool_int": (_fn("", "let b: bool = 2\nif b\n    return 1\n0"), 2, 19, _I2B),
    "var_bool_int": (_fn("", "var b: bool = 2\nif b\n    return 1\n0"), 2, 19, _I2B),
    "let_int_bool": (_fn("a: i64", "let n: i64 = a == 1\nn"), 2, 18, _B2I),
    "let_i32_true": (_fn("", "let n: i32 = true\nn as i64"), 2, 18, _B2I),
    "let_bool_pointer": (_fn("p: *u8", "let b: bool = p\nif b\n    return 1\n0"), 2, 19,
                         f"cannot use a pointer as bool: write {_WRITE_NULL}"),
    "let_float_bool": (_fn("a: bool", "let x: f64 = a\nx as i64"), 2, 18,
                       "cannot use bool as a float"),
    "return_bool_as_int": (_fn("a: i64", "return a == 1"), 2, 12, _B2I),
    "return_int_as_bool": (_fn("a: i64", "return a", "bool"), 2, 12, _I2B),
    "tail_bool_as_int": (_fn("a: i64", "a == 1"), 2, 5, _B2I),
    "tail_int_as_bool": (_fn("a: i64", "a", "bool"), 2, 5, _I2B),
    "tail_literal_as_bool": (_fn("", "1", "bool"), 2, 5, _I2B),
    "assign_int_to_bool": (_fn("", "var b: bool = false\nb = 1\nif b\n    return 1\n0"), 3, 9, _I2B),
    "assign_bool_to_int": (_fn("a: bool", "var n: i64 = 0\nn = a\nn"), 3, 9, _B2I),
    "argument_int_as_bool": ("fn g(b: bool) -> i64\n    0\n" + _fn("n: i64", "g(n)"), 4, 7, _I2B),
    "argument_bool_as_int": ("fn g(n: i64) -> i64\n    n\n" + _fn("a: i64", "g(a == 1)"),
                             4, 7, _B2I),
    "first_of_a_repeated_argument": ("fn g(b: bool, n: i64) -> i64\n    n\n"
                                     + _fn("n: i64", "g(n, n)"), 4, 7, _I2B),
    # A `let` is one SSA value, so these two arguments are the same object.
    "first_of_repeated_method_arguments": (
        _S + "impl S\n    fn m(self, b: bool, k: i64) -> i64\n        k\n"
        + _fn("s: S", "let n: i64 = 1\ns.m(n, n)"), 9, 9, _I2B),
    "first_of_repeated_static_arguments": (
        _S + "impl S\n    fn m(b: bool, k: i64) -> i64\n        k\n"
        + _fn("", "let n: i64 = 1\nS.m(n, n)"), 9, 9, _I2B),
    "first_of_repeated_pointer_arguments": (
        "fn g(b: bool, k: i64) -> i64\n    k\n"
        + _fn("", "let n: i64 = 1\nlet h: fn(bool, i64) -> i64 = g\nh(n, n)"), 6, 7, _I2B),
    "second_argument": ("fn g(n: i64, b: bool) -> i64\n    n\n" + _fn("n: i64", "g(n, n)"),
                        4, 10, _I2B),
    "method_argument": (_S + "impl S\n    fn m(self, b: bool) -> i64\n        self.n\n"
                        + _fn("s: S", "s.m(1)"), 8, 9, _I2B),
    "field_lit_int_as_bool": (_S + _fn("", "let s: S = S { b: 1, n: 2 }\ns.n"), 5, 23, _I2B),
    "field_lit_bool_as_int": (_S + _fn("", "let s: S = S { b: true, n: true }\ns.n"), 5, 32, _B2I),
    "field_assign_int": (_S + _fn("", "var s: S = S { b: true, n: 2 }\ns.b = 1\ns.n"), 6, 11, _I2B),
    "field_assign_bool": (_S + _fn("", "var s: S = S { b: true, n: 2 }\ns.n = s.b\ns.n"),
                          6, 11, _B2I),
    "deref_store_int": (_fn("p: *bool", "*p = 1\n0"), 2, 10, _I2B),
    "index_store_int": (_fn("p: *bool", "p[0] = 1\n0"), 2, 12, _I2B),
    "index_store_bool": (_fn("p: *i64, a: bool", "p[0] = a\n0"), 2, 12, _B2I),
    "index_by_bool": (_fn("p: *i64, a: bool", "p[a]"), 2, 7, _B2I),
    "array_lit_int_as_bool": (_fn("", "var a: [2]bool = [true, 1]\nif a[0]\n    return 1\n0"),
                              2, 29, _I2B),
    "global_assign": ("var g: bool\n" + _fn("", "g = 1\n0"), 3, 9, _I2B),
    "global_init": ("var g: bool = 2\n" + _MAIN, 1, 15, _I2B),
    "const_init": ("const C: bool = 2\n" + _MAIN, 1, 17, _I2B),

    # Inferred bindings carry what they were given.
    "inferred_let_is_a_bool": (_fn("a: i64", "let v = a == 1\nlet n: i64 = v\nn"), 3, 18, _B2I),
    "inferred_var_is_a_bool": (_fn("a: i64", "var v = a == 1\nv = 1\n0"), 3, 9, _I2B),
    "inferred_let_is_an_int": (_fn("a: i64", "let v = a + 1\nif v\n    return 1\n0"), 3, 8,
                               f"if condition {_INT_COND}"),

    # `x as bool` is gone.
    "cast_int": (_fn("n: i64", "if n as bool\n    return 1\n0"), 2, 8,
                 f"`as bool` is removed: write {_WRITE_NE0}"),
    "cast_literal": (_fn("", "let b: bool = 256 as bool\nif b\n    return 1\n0"), 2, 19,
                     f"`as bool` is removed: write {_WRITE_NE0}"),
    "cast_bool_to_float": (_fn("a: bool", "let x: f64 = a as f64\nx as i64"), 2, 18,
                           "cannot cast bool to a float"),
    "cast_bool_to_pointer": (_fn("a: bool", "let p: *u8 = a as *u8\n0"), 2, 18,
                             "cannot cast bool to a pointer"),
}

# name -> (source, exit code[, extra files])
ACCEPTED = {
    "cast_zero_or_one": ("fn t(a: i64) -> bool\n    a == 7\n"
                         "fn main() -> i32\n    (t(7) as i32) * 4 + (t(6) as i32)\n", 4),
    "cast_each_width": ("fn main() -> i32\n    let b: bool = true\n"
                        "    ((b as i8) as i32) + ((b as u8) as i32) + ((b as i16) as i32)"
                        " + ((b as u16) as i32) + ((b as u32) as i32) + ((b as i64) as i32)"
                        " + ((b as u64) as i32)\n", 7),
    "bool_local": ("fn main() -> i32\n    let b: bool = 1 == 1\n    if b\n        return 3\n    0\n", 3),
    "bool_var": ("fn main() -> i32\n    var b: bool = false\n    b = true\n"
                 "    while b\n        b = false\n    if not b\n        return 3\n    0\n", 3),
    "bool_inferred": ("fn main() -> i32\n    let a = 2 > 1\n    var b = a and true\n"
                      "    b = not a or b\n    if b\n        return 3\n    0\n", 3),
    "bool_param": ("fn f(a: bool, b: bool) -> i32\n    if a and not b\n        return 3\n    0\n"
                   "fn main() -> i32\n    f(true, false)\n", 3),
    "bool_return": ("fn y() -> bool\n    return 2 > 1\nfn z() -> bool\n    1 > 2\n"
                    "fn main() -> i32\n    if y() and not z()\n        return 3\n    0\n", 3),
    "bool_field": (_S + "fn main() -> i32\n    var s: S = S { b: false, n: 3 }\n"
                   "    s.b = s.n == 3\n    if s.b\n        return 3\n    0\n", 3),
    "bool_through_pointer": ("fn f(p: *bool) -> i32\n    *p = true\n    if *p\n        return 3\n    0\n"
                             "fn main() -> i32\n    var b: bool = false\n    f(@b)\n", 3),
    "bool_field_through_pointer": (_S + "fn f(s: *S) -> i32\n    if s.b and s.n > 0\n"
                                   "        return 3\n    0\n"
                                   "fn main() -> i32\n    var s: S = S { b: true, n: 1 }\n"
                                   "    f(@s)\n", 3),
    "bool_field_of_deref": (_S + "fn f(p: *S) -> i32\n    if (*p).b\n        return 3\n    0\n"
                            "fn main() -> i32\n    var s: S = S { b: true, n: 1 }\n    f(@s)\n", 3),
    "bool_field_of_element": (_S + "fn main() -> i32\n    var a: [2]S\n    a[1].b = true\n"
                              "    if a[1].b and not a[0].b\n        return 3\n    0\n", 3),
    "bool_field_of_pointer_element": (_S + "fn f(p: *S) -> i32\n    if p[1].b\n        return 3\n    0\n"
                                      "fn main() -> i32\n    var a: [2]S\n    a[1].b = true\n"
                                      "    f(@a[0])\n", 3),
    "bool_field_of_nested": (_S + "struct T\n    s: S\nfn main() -> i32\n"
                             "    var t: T = T { s: S { b: true, n: 1 } }\n"
                             "    if t.s.b\n        return 3\n    0\n", 3),
    "bool_field_of_call": (_S + "fn mk() -> S\n    S { b: true, n: 1 }\n"
                           "fn main() -> i32\n    if mk().b\n        return 3\n    0\n", 3),
    "bool_static_method": (_S + "impl S\n    fn yes() -> bool\n        true\n"
                           "fn main() -> i32\n    if S.yes()\n        return 3\n    0\n", 3),
    "bool_method_on_pointer": (_S + "impl S\n    fn ok(self) -> bool\n        self.b\n"
                               "fn f(p: *S) -> i32\n    if p.ok()\n        return 3\n    0\n"
                               "fn main() -> i32\n    var s: S = S { b: true, n: 1 }\n    f(@s)\n", 3),
    "bool_method_on_field": (_S + "struct T\n    s: S\nimpl S\n    fn ok(self) -> bool\n"
                             "        self.b\nfn main() -> i32\n"
                             "    var t: T = T { s: S { b: true, n: 1 } }\n"
                             "    if t.s.ok()\n        return 3\n    0\n", 3),
    "bool_method_on_element": (_S + "impl S\n    fn ok(self) -> bool\n        self.b\n"
                               "fn main() -> i32\n    var a: [2]S\n    a[1].b = true\n"
                               "    if a[1].ok()\n        return 3\n    0\n", 3),
    "bool_builtin_is_some": ("import ritzlib.option\nfn main() -> i32\n"
                             "    let o: Option<i32> = Some(1)\n"
                             "    if o.is_some() and not o.is_none()\n        return 3\n    0\n", 3),
    "bool_unwrap": ("import ritzlib.option\nfn main() -> i32\n"
                    "    let o: Option<bool> = Some(true)\n    if o.unwrap()\n        return 3\n    0\n", 3),
    "bool_try": ("import ritzlib.result\nfn r() -> Result<bool, i32>\n    Ok(true)\n"
                 "fn g() -> Result<i32, i32>\n    if r()?\n        return Ok(3)\n    Ok(0)\n"
                 "fn main() -> i32\n    match g()\n        Ok(v) => v\n        Err(e) => e\n", 3),
    "bool_module_const": ("import colors\nfn main() -> i32\n    if colors.ON\n        return 3\n"
                          "    0\n", 3, {"colors.ritz": "pub const ON: bool = true\n"}),
    "bool_element_of_array_pointer": ("fn f(p: *[3]bool) -> i32\n    if p[1]\n        return 3\n    0\n"
                                      "fn main() -> i32\n    var a: [3]bool\n    a[1] = true\n"
                                      "    f(@a)\n", 3),
    "bool_array": ("fn main() -> i32\n    var a: [2]bool = [false, true]\n"
                   "    if a[1] and not a[0]\n        return 3\n    0\n", 3),
    "bool_const": ("const C: bool = true\nfn main() -> i32\n    if C\n        return 3\n    0\n", 3),
    # AGAST #3001: a `bool` global is one i1 byte, as on ritz0, and reads as the
    # i64 every bool value is; ritz1 stored the i64 as i1 and handed `not`, `and`,
    # a cast and a by-value arg the raw i1 load.
    "bool_global": (("var g: bool\nfn main() -> i32\n    g = false\n    g = not g\n"
                     "    if g\n        return 3\n    0\n"), 3),
    "bool_global_operands": (("var g: bool\nvar h: bool\nfn main() -> i32\n    g = true\n"
                              "    h = g and not h\n    if g and h and (h or g) and g == h\n"
                              "        return 3\n    0\n"), 3),
    "bool_global_cast": ("var g: bool\nfn main() -> i32\n    g = 2 > 1\n    (g as i32) * 3\n", 3),
    "bool_global_value": (("var g: bool\nfn f(b: bool) -> i32\n    if b\n        return 3\n    0\n"
                           "fn y() -> bool\n    g\nfn main() -> i32\n    g = true\n"
                           "    let b: bool = y()\n    if b\n        return f(g)\n    0\n"), 3),
    "bool_method": (_S + "impl S\n    fn ok(self) -> bool\n        self.b\n"
                    "fn main() -> i32\n    let s: S = S { b: true, n: 1 }\n"
                    "    if s.ok()\n        return 3\n    0\n", 3),
    "bool_fn_pointer": ("fn y() -> bool\n    true\nfn main() -> i32\n"
                        "    let f: fn() -> bool = y\n    if f()\n        return 3\n    0\n", 3),
    "bool_if_value": ("fn main() -> i32\n    let n: i64 = 1\n"
                      "    let b: bool = if n > 0 then true else false\n"
                      "    if b\n        return 3\n    0\n", 3),
    "bool_match_value": ("fn f(n: i64) -> bool\n    match n\n        0 => false\n        _ => true\n"
                         "fn main() -> i32\n    if f(1)\n        return 3\n    0\n", 3),
    "bool_match_on_bool": ("fn main() -> i32\n    let b: bool = 1 > 0\n    match b\n"
                           "        true => 3\n        false => 0\n", 3),
    "bool_match_binding": ("fn f(b: bool) -> i32\n    match b\n        v =>\n            if v\n"
                           "                return 3\n            0\n"
                           "fn main() -> i32\n    f(true)\n", 3),
    "bool_generic": ("fn id<T>(x: T) -> T\n    x\nfn main() -> i32\n"
                     "    if id<bool>(true)\n        return 3\n    0\n", 3),
    "bool_compare": ("fn main() -> i32\n    let a: bool = 1 > 0\n    let b: bool = 2 > 1\n"
                     "    if a == b and not (a != b)\n        return 3\n    0\n", 3),
    "bool_compare_literal": ("fn main() -> i32\n    let a: bool = 1 > 0\n"
                             "    if a == true and a != false\n        return 3\n    0\n", 3),
    "bits_then_compare": ("fn main() -> i32\n    let x: i64 = 6\n"
                          "    if (x & 2) == 2 and (x | 1) != 0 and (x ^ 1) > 0\n"
                          "        return 3\n    0\n", 3),
    "pointer_null_tests": ("fn main() -> i32\n    var n: i64 = 0\n    let p: *i64 = @n\n"
                           "    if p != null and not (p == null)\n        return 3\n    0\n", 3),
    "payload_int_compared": ("import ritzlib.option\nfn f(o: Option<i32>) -> i32\n    match o\n"
                             "        Some(v) =>\n            if v == 7\n                return 3\n"
                             "            0\n        None => 0\n"
                             "fn main() -> i32\n    f(Some(7))\n", 3),
    "bool_user_enum_payload": ("enum E\n    A(bool)\n    B\nfn f(e: E) -> i32\n    match e\n"
                               "        A(v) =>\n            if v\n                return 3\n"
                               "            0\n        B => 0\n"
                               "fn main() -> i32\n    f(A(true))\n", 3),
    "bool_result_payload": ("import ritzlib.result\nfn r() -> Result<bool, i32>\n    Ok(true)\n"
                            "fn main() -> i32\n    match r()\n        Ok(v) =>\n            if v\n"
                            "                return 3\n            0\n        Err(e) => e\n", 3),
    "and_short_circuits": ("fn boom() -> bool\n    let p: *i64 = null\n    *p == 1\n"
                           "fn main() -> i32\n    if false and boom()\n        return 1\n"
                           "    if true or boom()\n        return 3\n    0\n", 3),
    "option_of_bool": ("import ritzlib.option\nfn main() -> i32\n"
                       "    let o: Option<bool> = Some(true)\n    match o\n"
                       "        Some(v) =>\n            if v\n                return 3\n"
                       "            0\n        None => 0\n", 3),
}


# ritz1 can't lower these at all: a tuple or destructuring `let`, a member of a
# cast, a generic impl method taking `self` by value, a method of a method's result.
RITZ0_ONLY_ACCEPTED = {
    "bool_field_of_cast": (_S + "fn f(q: *u8) -> i32\n    if (q as *S).b\n        return 3\n    0\n"
                           "fn main() -> i32\n    var s: S = S { b: true, n: 1 }\n"
                           "    f(@s as *u8)\n", 3),
    "bool_generic_method": ("struct W<T>\n    v: T\nimpl<T> W<T>\n    fn ok(self) -> bool\n"
                            "        true\nfn main() -> i32\n    let w: W<i32> = W<i32> { v: 1 }\n"
                            "    if w.ok()\n        return 3\n    0\n", 3),
    "bool_method_chain": (_S + "impl S\n    fn me(self) -> S\n        self\n"
                          "    fn ok(self) -> bool\n        self.b\n"
                          "fn main() -> i32\n    let s: S = S { b: true, n: 1 }\n"
                          "    if s.me().ok()\n        return 3\n    0\n", 3),
    "tuple_of_bool": ("fn f() -> (bool, i64)\n    (true, 3)\nfn main() -> i32\n"
                      "    let (a, b) = f()\n    if a\n        return b as i32\n    0\n", 3),
}


def _compile(request, compiler, tmp_path, source, extra=None):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    for name, text in (extra or {}).items():
        (tmp_path / name).write_text(text)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        request.getfixturevalue("ritz1_bin")
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_a_mixed_bool_is_a_located_error(request, tmp_path, compiler, name):
    source, line, col, message = REJECTED[name]
    proc, ll = _compile(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    hits = re.findall(rf"unit\.ritz:{line}:{col}: (?:error: )?{re.escape(message)}$", out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


def _assert_runs(request, compiler, tmp_path, name, source, code, extra=None):
    proc, ll = _compile(request, compiler, tmp_path, source, extra)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler}, {name}:\n{out[-1500:]}"
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(2, str(RITZ_START))
    built = fast_link.clang(link, cwd=tmp_path, capture_output=True, text=True)
    assert built.returncode == 0, f"{compiler}, {name}: link:\n{built.stderr[-1500:]}"
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_bool_used_as_bool_compiles_and_runs(request, tmp_path, compiler, name):
    _assert_runs(request, compiler, tmp_path, name, *ACCEPTED[name])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_bool_global_is_one_byte(request, tmp_path, compiler):
    """AGAST #3001: `@g` is the i1 every access is, as ritz0 lays it out.

    ritz1 declared it an i64 slot; opaque pointers let that run, so only the
    declaration shows it.
    """
    proc, ll = _compile(request, compiler, tmp_path, "var g: bool\n" + _MAIN)
    assert proc.returncode == 0 and ll.exists(), (proc.stdout + proc.stderr)[-1500:]
    decl = re.search(r'^@"?g"? = .*$', ll.read_text(), re.MULTILINE)
    assert decl and re.search(r"\bglobal i1\b", decl.group(0)), decl and decl.group(0)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_ONLY_ACCEPTED))
def test_ritz0_only_bool_shapes(request, tmp_path, name):
    _assert_runs(request, "ritz0", tmp_path, name, *RITZ0_ONLY_ACCEPTED[name])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_a_condition_ritz1_cannot_type_is_an_error(request, tmp_path, compiler):
    """#1364's "stay silent when unsure" doesn't transfer to a condition."""
    proc, ll = _compile(request, compiler, tmp_path, _fn("", "if pass\n    return 1\n0"))
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted a condition it can't type:\n{out[-1500:]}"
    assert re.search(r"unit\.ritz:2:8: error: if condition must be bool, and ritz1 cannot tell", out), out
    assert not ll.exists()
