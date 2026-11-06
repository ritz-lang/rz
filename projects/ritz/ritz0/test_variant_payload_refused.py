#!/usr/bin/env python3
"""A variant payload is bound, never tested (AGAST #2350; LANGUAGE_SPEC §8.2).

`_emit_enum_match` switches on the tag alone, so a pattern inside a variant can
only take the payload. Anything that reads as a test was dropped, and the arm took
every value of that variant:

    match o
        Some(0) => 1
        _ => 2          # f(Some(5)) gave 1

Compiling the test is #1291's decision tree. Until then ritz0 refuses it, at the
pattern. The expected exit codes below come from what each program says, not from
a compiler.

ritz1's grammar takes only a name there, so it refuses every literal with a parse
error. The names that test are its match lowering's, with ritz0's wording at the
same place (#2405): each row of NAMES and NAMES_ON_BOTH runs on all three compilers.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

_C = "enum C\n    R\n    G\n"
_P = "enum P\n    Two(i32, i32)\n    One(i32)\n    Z\n"
_V = "enum E\n    V\n        x: i32\n    W\n"
_Q = _C + "enum Q\n    One(i32)\n    Hold(C)\n    Text(StrView)\n    Z\n"
_S = _C + "enum S\n    V\n        x: i32\n    U\n        c: C\n    W\n"
_K = "const K: i32 = 0\n"
_HINT = " — bind it to a name, then test the name in the arm body"
# Every test compiles beside this module, so a row can import it.
_MODULE = ("pub const MK: i32 = 0\nconst HIDDEN: i32 = 1\npub enum MC\n    MR\n    MG\n"
           "pub fn in_module<T>(x: T, o: Option<i32>) -> i32\n    match o\n"
           "        Some(HIDDEN) => 1\n        _ => 2\n")


def _opt(ty, pattern, arg):
    """`f(Some(arg))`, with `pattern` on line 3 of this text, payload at column 14."""
    return (f"fn f(o: Option<{ty}>) -> i32\n    match o\n        {pattern} => 1\n"
            f"        _ => 2\nfn main() -> i32\n    f(Some({arg}))\n")


def _res(types, pattern, arg):
    """`f(arg)` over `Result<types>`, with `pattern` on line 3 of this text."""
    return (f"fn f(r: Result<{types}>) -> i32\n    match r\n        {pattern} => 1\n"
            f"        _ => 2\nfn main() -> i32\n    f({arg})\n")


def _on(ty, pattern, arg):
    """`f(arg)` over `ty`, with `pattern` on line 3 of this text."""
    return (f"fn f(e: {ty}) -> i32\n    match e\n        {pattern} => 1\n"
            f"        _ => 2\nfn main() -> i32\n    f({arg})\n")


def _nested(ty, pattern, wrap):
    """`f(wrap)` over `ty`, with an `Option<i32>` local `i` to wrap."""
    return (f"fn f(o: {ty}) -> i32\n    match o\n        {pattern} => 1\n        _ => 2\n"
            f"fn main() -> i32\n    let i: Option<i32> = Some(1)\n    f({wrap})\n")


# A `K` test in `main`, on line 11 + len(setup) of this text.
_SCRUTINEE = (_K + "struct T\n    o: Option<i32>\nimpl T\n    fn m(self) -> Option<i32>\n"
              "        Some(5)\nfn g() -> Option<i32>\n    Some(5)\nfn main() -> i32\n")


def _scrutinee(setup, expr):
    body = "".join(f"    {line}\n" for line in setup)
    return (_SCRUTINEE + body + f"    match {expr}\n        Some(K) => 1\n        _ => 2\n",
            11 + len(setup), 14, "K", "Some")


_LOCAL = "let o: Option<i32> = Some(5)"
_GENERIC = "fn f<T>(o: Option<T>) -> i32\n    match o\n        {} => 1\n        _ => 2\n"


# name -> (source, line, col, the pattern as shown, its variant)
LITERALS = {
    "int": (_opt("i32", "Some(0)", "5"), 3, 14, "0", "Some"),
    "int_equal_to_the_payload": (_opt("i32", "Some(5)", "5"), 3, 14, "5", "Some"),
    "bool_true": (_opt("bool", "Some(true)", "false"), 3, 14, "true", "Some"),
    "bool_false": (_opt("bool", "Some(false)", "true"), 3, 14, "false", "Some"),
    "string": (_opt("StrView", 'Some("a")', '"b"'), 3, 14, '"a"', "Some"),
    "second_field": (_P + "fn f(p: P) -> i32\n    match p\n        Two(a, 0) => a\n"
                     "        _ => 2\nfn main() -> i32\n    f(P.Two(1, 5))\n",
                     7, 16, "0", "Two"),
    "qualified_arm": (_P + "fn f(p: P) -> i32\n    match p\n        P.One(0) => 1\n"
                      "        _ => 2\nfn main() -> i32\n    f(P.One(5))\n",
                      7, 15, "0", "One"),
    "struct_variant": (_V + "fn f(e: E) -> i32\n    match e\n        V(0) => 1\n"
                       "        _ => 2\nfn main() -> i32\n    f(E.V(5))\n",
                       7, 11, "0", "V"),
    "result_err": ("fn f(r: Result<i32, i32>) -> i32\n    match r\n        Err(7) => 1\n"
                   "        _ => 2\nfn main() -> i32\n    f(Err(5))\n", 3, 13, "7", "Err"),
    "statement": ("fn main() -> i32\n    var r: i32 = 2\n    let o: Option<i32> = Some(5)\n"
                  "    match o\n        Some(0) => r = 1\n        _ => pass\n    r\n",
                  5, 14, "0", "Some"),
    "generic_fn": ("fn f<T>(o: Option<T>) -> i32\n    match o\n        Some(0) => 1\n"
                   "        _ => 2\nfn main() -> i32\n    let o: Option<i32> = Some(5)\n"
                   "    f<i32>(o)\n", 3, 14, "0", "Some"),
    "untyped_scrutinee": ("struct T\n    v: i32\nimpl T\n    fn o(self) -> Option<i32>\n"
                          "        Some(5)\nfn main() -> i32\n    let t = T { v: 1 }\n"
                          "    match t.o()\n        Some(0) => 1\n        _ => 2\n",
                          9, 14, "0", "Some"),
    "behind_a_covering_arm": ("fn f(o: Option<i32>) -> i32\n    match o\n        Some(0) => 1\n"
                              "        Some(v) => v\n        None => 2\n"
                              "fn main() -> i32\n    f(Some(5))\n", 3, 14, "0", "Some"),
    "more_fields_than_the_variant": (_opt("i32", "Some(a, 0)", "5"), 3, 17, "0", "Some"),
    "payload_on_a_bare_variant": (_P + "fn f(p: P) -> i32\n    match p\n        Z(0) => 1\n"
                                  "        _ => 2\nfn main() -> i32\n    f(P.Z)\n",
                                  7, 11, "0", "Z"),
}

# A type names no value here: `Some(bool)` took an `Option<i32>`'s every `Some`.
TYPES = {
    "matching_type": (_opt("i32", "Some(i32)", "5"), 3, 14, "i32", "Some"),
    "other_type": (_opt("i32", "Some(bool)", "5"), 3, 14, "bool", "Some"),
    "pointer_type": (_opt("*u8", "Some(*u8)", "null"), 3, 14, "*u8", "Some"),
}

# §8.2 makes these tests, though they look like bindings.
NAMES = {
    "const": ("const K: i32 = 0\n" + _opt("i32", "Some(K)", "5"), 4, 14, "K", "Some"),
    "const_declared_later": (_opt("i32", "Some(K)", "5") + "const K: i32 = 0\n",
                             3, 14, "K", "Some"),
    "const_on_a_bool_payload": ("const K: i32 = 0\n" + _opt("bool", "Some(K)", "true"),
                                4, 14, "K", "Some"),
    "variant": (_C + _opt("C", "Some(R)", "C.G"), 6, 14, "R", "Some"),
    "repr_enum_variant": ("enum D: u64\n    X = 0\n    Y = 1\n" + _opt("D", "Some(X)", "D.Y"),
                          6, 14, "X", "Some"),
    "builtin_variant": ("fn f(o: Option<Option<i32>>) -> i32\n    match o\n"
                        "        Some(None) => 1\n        _ => 2\n"
                        "fn main() -> i32\n    let i: Option<i32> = Some(1)\n    f(Some(i))\n",
                        3, 14, "None", "Some"),
}

# The same two rules, over what ritz1 has to work out for itself. Its emitter reads
# a field's type off a mangled `Result$A$B` or the enum tracker, not off a value.
NAMES_ON_BOTH = {
    # Silent on ritz1: `Some(R)` over a one-letter enum only failed at clang by luck.
    "variant_of_a_longer_named_enum": (
        "enum Color\n    Red\n    Green\n" + _opt("Color", "Some(Red)", "Color.Green"),
        6, 14, "Red", "Some"),
    # Which consts: anything numeric, as `_name_tests_payload` reads the table.
    "float_const": ("const K: f64 = 1.0\n" + _opt("i32", "Some(K)", "5"), 4, 14, "K", "Some"),
    "narrow_float_const": ("const K: f32 = 1.0\n" + _opt("i32", "Some(K)", "5"),
                           4, 14, "K", "Some"),
    "bool_const": ("const K: bool = true\n" + _opt("i32", "Some(K)", "5"), 4, 14, "K", "Some"),
    "computed_const": ("const K: i32 = 1 + 2\n" + _opt("i32", "Some(K)", "5"), 4, 14, "K", "Some"),
    "const_of_another_width": ("const K: u8 = 1\n" + _opt("i64", "Some(K)", "5"),
                               4, 14, "K", "Some"),
    # Which payloads are integers.
    **{f"const_on_{ty}": (_K + _opt(ty, "Some(K)", f"5 as {ty}"), 4, 14, "K", "Some")
       for ty in ("i8", "i16", "i64", "u8", "u16", "u32", "u64", "isize", "usize")},
    # Result: each variant's own field.
    "ok_const": (_K + _res("i32, i32", "Ok(K)", "Ok(5)"), 4, 12, "K", "Ok"),
    "err_const": (_K + _res("i32, i32", "Err(K)", "Err(5)"), 4, 13, "K", "Err"),
    "err_const_beside_a_string_ok": (_K + _res("StrView, i32", "Err(K)", "Err(5)"),
                                     4, 13, "K", "Err"),
    "ok_const_beside_a_string_err": (_K + _res("i32, StrView", "Ok(K)", "Ok(5)"),
                                     4, 12, "K", "Ok"),
    "ok_variant": (_C + _res("C, i32", "Ok(R)", "Ok(C.G)"), 6, 12, "R", "Ok"),
    "err_variant": (_C + _res("i32, C", "Err(R)", "Err(C.G)"), 6, 13, "R", "Err"),
    # An Option or Result payload declares its own two names.
    "nested_some": (_nested("Option<Option<i32>>", "Some(Some)", "Some(i)"),
                    3, 14, "Some", "Some"),
    "nested_err": (_nested("Option<Result<i32, i32>>", "Some(Err)", "None"),
                   3, 14, "Err", "Some"),
    "nested_ok": (_nested("Option<Result<i32, i32>>", "Some(Ok)", "None"), 3, 14, "Ok", "Some"),
    "ok_none": (_nested("Result<Option<i32>, i32>", "Ok(None)", "Ok(i)"), 3, 12, "None", "Ok"),
    "err_none": (_nested("Result<i32, Option<i32>>", "Err(None)", "Err(i)"),
                 3, 13, "None", "Err"),
    # User enums, whose fields carry a type code rather than a mangled name.
    "user_variant_const": (_K + _Q + _on("Q", "One(K)", "Q.One(5)"), 12, 13, "K", "One"),
    "qualified_arm_const": (_K + _Q + _on("Q", "Q.One(K)", "Q.One(5)"), 12, 15, "K", "One"),
    "user_variant_holding_an_enum": (_Q + _on("Q", "Hold(R)", "Q.Hold(C.G)"), 11, 14, "R", "Hold"),
    "user_variant_holding_an_option": (
        "enum H\n    Has(Option<i32>)\n    Lacks\n" + _on("H", "Has(None)", "H.Lacks"),
        6, 13, "None", "Has"),
    "struct_variant_const": (_K + _S + _on("S", "V(K)", "S.W"), 13, 11, "K", "V"),
    "struct_variant_holding_an_enum": (_S + _on("S", "U(R)", "S.W"), 12, 11, "R", "U"),
    # A type the parser spelled through an alias, whichever side of it.
    "alias_of_an_integer": (_K + "type Id = i32\n" + _opt("Id", "Some(K)", "5"),
                            5, 14, "K", "Some"),
    "alias_declared_later": (_K + _opt("Id", "Some(K)", "5") + "type Id = i32\n",
                             4, 14, "K", "Some"),
    "alias_of_an_enum": (_C + "type CC = C\n" + _opt("CC", "Some(R)", "C.G"),
                         7, 14, "R", "Some"),
    "alias_of_the_scrutinee": (_K + "type OI = Option<i32>\n" + _on("OI", "Some(K)", "Some(5)"),
                               5, 14, "K", "Some"),
    # Declared elsewhere. A const needn't be `pub`: both tables are whole-program.
    "imported_const": ("import pm\n" + _opt("i32", "Some(MK)", "5"), 4, 14, "MK", "Some"),
    "imported_private_const": ("import pm\n" + _opt("i32", "Some(HIDDEN)", "5"),
                               4, 14, "HIDDEN", "Some"),
    "imported_enum": ("import pm\n" + _opt("MC", "Some(MR)", "MC.MG"), 4, 14, "MR", "Some"),
    # Substituted before the arm is read.
    "generic_fn_const": (_K + _GENERIC.format("Some(K)") + "fn main() -> i32\n"
                         "    let o: Option<i32> = Some(5)\n    f<i32>(o)\n",
                         4, 14, "K", "Some"),
    "generic_fn_variant": (_C + _GENERIC.format("Some(R)") + "fn main() -> i32\n"
                           "    let o: Option<C> = Some(C.G)\n    f<C>(o)\n",
                           6, 14, "R", "Some"),
    "generic_fn_over_a_concrete_option": (
        _K + "fn f<T>(x: T, o: Option<i32>) -> i32\n    match o\n        Some(K) => 1\n"
        "        _ => 2\nfn main() -> i32\n    let o: Option<i32> = Some(5)\n    f<i32>(1, o)\n",
        4, 14, "K", "Some"),
    # However the match came by its enum.
    "scrutinee_call": _scrutinee([], "g()"),
    "scrutinee_method": _scrutinee(["let t = T { o: Some(5) }"], "t.m()"),
    "scrutinee_field": _scrutinee(["let t = T { o: Some(5) }"], "t.o"),
    "scrutinee_borrow": _scrutinee([_LOCAL], "@o"),
    "scrutinee_deref": _scrutinee([_LOCAL, "let p: *Option<i32> = @o"], "*p"),
    "scrutinee_untyped_let": _scrutinee(["let o = g()"], "o"),
    "scrutinee_constructor": _scrutinee([], "Some(5)"),
    "scrutinee_element": _scrutinee(["var a: [2]Option<i32>", "a[1] = Some(5)"], "a[1]"),
    "scrutinee_global": (_K + "var G: Option<i32>\nfn main() -> i32\n    match G\n"
                         "        Some(K) => 1\n        _ => 2\n", 5, 14, "K", "Some"),
    # Wherever the arm stands.
    "behind_a_wildcard": (_K + "fn f(o: Option<i32>) -> i32\n    match o\n        _ => 2\n"
                          "        Some(K) => 1\nfn main() -> i32\n    f(Some(5))\n",
                          5, 14, "K", "Some"),
    "arm_reads_the_name": (_K + "fn f(o: Option<i32>) -> i32\n    match o\n"
                           "        Some(K) => K\n        _ => 2\n"
                           "fn main() -> i32\n    f(Some(5))\n", 4, 14, "K", "Some"),
    "inside_another_arm": (_K + "fn f(o: Option<i32>, q: Option<i32>) -> i32\n    match o\n"
                           "        Some(a) =>\n            match q\n"
                           "                Some(K) => 1\n                _ => a\n"
                           "        _ => 2\nfn main() -> i32\n    f(Some(5), Some(5))\n",
                           6, 22, "K", "Some"),
    "statement_match": (_K + "fn main() -> i32\n    var r: i32 = 2\n"
                        "    let o: Option<i32> = Some(5)\n    match o\n"
                        "        Some(K) => r = 1\n        _ => pass\n    r\n",
                        6, 14, "K", "Some"),
}

REFUSED = {**LITERALS, **TYPES, **NAMES, **NAMES_ON_BOTH}

# name -> (source, exit code). Each is a binding or `_`, so each must still run.
KEPT = {
    "binding": ("fn f(o: Option<i32>) -> i32\n    match o\n        Some(v) => v\n"
                "        _ => 2\nfn main() -> i32\n    f(Some(5))\n", 5),
    "wildcard": (_opt("i32", "Some(_)", "5"), 1),
    "wildcard_on_none": ("fn f(o: Option<i32>) -> i32\n    match o\n        Some(_) => 1\n"
                         "        _ => 2\nfn main() -> i32\n    f(None)\n", 2),
    "two_bindings": (_P + "fn f(p: P) -> i32\n    match p\n        Two(a, b) => a * 10 + b\n"
                     "        _ => 2\nfn main() -> i32\n    f(P.Two(1, 5))\n", 15),
    "binding_and_wildcard": (_P + "fn f(p: P) -> i32\n    match p\n        Two(_, b) => b\n"
                             "        _ => 2\nfn main() -> i32\n    f(P.Two(1, 5))\n", 5),
    "struct_variant": (_V + "fn f(e: E) -> i32\n    match e\n        V(a) => a\n"
                       "        _ => 2\nfn main() -> i32\n    f(E.V(5))\n", 5),
    # Named like a variant, but of an enum this payload isn't.
    "named_like_another_enums_variant": (
        _C + "fn f(o: Option<i32>) -> i32\n    match o\n        Some(R) => R\n"
        "        _ => 2\nfn main() -> i32\n    f(Some(5))\n", 5),
    "named_like_another_enums_variant_on_an_enum": (
        _C + "enum Dir\n    X\n    Y\nfn f(o: Option<Dir>) -> i32\n    match o\n"
        "        Some(R) => 1\n        _ => 2\nfn main() -> i32\n    f(Some(Dir.Y))\n", 1),
    # A repr enum is no integer's type: `u64` doesn't make `X` a variant.
    "named_like_a_repr_enums_variant": (
        "enum D: u64\n    X = 0\n    Y = 1\nfn f(o: Option<u64>) -> i32\n    match o\n"
        "        Some(X) => X as i32\n        _ => 2\n"
        "fn main() -> i32\n    f(Some(5 as u64))\n", 5),
    # Constant patterns compare integers only (§8.2).
    "named_like_a_const_on_a_string": (
        "const K: i32 = 0\nfn f(o: Option<StrView>) -> i32\n    match o\n"
        "        Some(K) => 1\n        _ => 2\n"
        'fn main() -> i32\n    f(Some("abc"))\n', 1),
    # Top-level arms keep their own rules.
    "const_at_the_top_level": ("const K: i64 = 0\nfn main() -> i32\n    let n: i64 = 5\n"
                               "    match n\n        K => 1\n        _ => 2\n", 2),
    "variant_at_the_top_level": (_C + "fn main() -> i32\n    let c: C = C.G\n    match c\n"
                                 "        R => 1\n        _ => 2\n", 2),
    # Not numeric, so no test: ritz0 keeps these out of its const table.
    "named_like_a_string_const": ('const K: StrView = "a"\n' + _opt("i32", "Some(K)", "5"), 1),
    "named_like_a_c_string_const": ('const K: *u8 = c"a"\n' + _opt("i32", "Some(K)", "5"), 1),
    "named_like_a_const_array": ("const K: [2]i32 = [1, 2]\n" + _opt("i32", "Some(K)", "5"), 1),
    # Named like something, but no const.
    "named_like_a_global": ("var G: i32 = 0\n" + _opt("i32", "Some(G)", "5"), 1),
    "named_like_a_fn": ("fn g() -> i32\n    1\n" + _opt("i32", "Some(g)", "5"), 1),
    # Named like a builtin's variant, on a payload that is none.
    "named_none_on_an_integer": (_opt("i32", "Some(None)", "5"), 1),
    "named_some_on_an_integer": (_opt("i32", "Some(Some)", "5"), 1),
    "named_ok_on_an_option": (_nested("Option<Option<i32>>", "Some(Ok)", "Some(i)"), 1),
    "named_none_on_a_result": (_nested("Option<Result<i32, i32>>", "Some(None)", "None"), 2),
    # A payload no integer: a const is only a name there.
    "named_like_a_const_on_a_float": (_K + _opt("f64", "Some(K)", "1.5"), 1),
    "named_like_a_const_on_a_pointer": (_K + _opt("*i32", "Some(K)", "null"), 1),
    "named_like_a_const_on_a_struct": (
        _K + "struct Tee\n    v: i32\n" + _opt("Tee", "Some(K)", "Tee { v: 1 }"), 1),
    "named_like_a_const_on_a_struct_with_an_integer_look": (
        _K + "struct i2c\n    v: i32\n" + _opt("i2c", "Some(K)", "i2c { v: 1 }"), 1),
    "named_like_a_const_on_an_enum": (
        _K + "enum Dir\n    X\n    Y\n" + _opt("Dir", "Some(K)", "Dir.Y"), 1),
    "named_like_a_const_on_an_option": (
        _K + _nested("Option<Option<i32>>", "Some(K)", "Some(i)"), 1),
    "named_like_a_const_on_a_user_string": (
        _K + _Q + _on("Q", "Text(K)", 'Q.Text("a")'), 1),
    # A pointer to an enum is no enum.
    "named_like_a_pointees_variant": (_C + _opt("*C", "Some(R)", "null"), 1),
    "named_like_a_user_pointees_variant": (
        "enum L\n    N\n    B(*L)\n" + _on("L", "B(N)", "L.N"), 2),
    # The other side of a Result has its own type.
    "const_on_a_string_err": (_K + _res("i32, StrView", "Err(K)", 'Err("a")'), 1),
    "const_on_a_string_ok": (_K + _res("StrView, i32", "Ok(K)", 'Ok("a")'), 1),
    "variant_on_an_integer_err": (_C + _res("C, i32", "Err(R)", "Err(5)"), 1),
    "variant_on_an_integer_ok": (_C + _res("i32, C", "Ok(R)", "Ok(5)"), 1),
    # A generic fn is read once it has a type: uninstantiated, it is never read.
    "generic_fn_never_called": (_K + _GENERIC.format("Some(K)") + "fn main() -> i32\n    0\n", 0),
}

# name -> the ticket that keeps ritz1 from reaching this row of NAMES_ON_BOTH. None is
# the rule's: each goes just as wrong with `Some(v)`, so each flips when it's fixed.
RITZ1_NEVER_READS = {
    "generic_fn_const": "#2418: `Option<T>` stays %Option$T in a generic fn's signature",
    "generic_fn_variant": "#2418: `Option<T>` stays %Option$T in a generic fn's signature",
    "scrutinee_constructor": "#2419: `match Some(5)` has no enum, and reads as 0",
}

# name -> why ritz1 can't run this row of KEPT, which ritz0 does.
NOT_ON_RITZ1 = {
    "two_bindings": "its grammar takes one name in a pattern, and one field in a variant",
    "binding_and_wildcard": "its grammar takes one name in a pattern, and one field in a variant",
    "struct_variant": "it can't construct a struct variant (#1295)",
}


def _ritz0(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    (tmp_path / "pm.ritz").write_text(_MODULE)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    return run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300), ll


def _ritz1(request, compiler, tmp_path, source):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    (tmp_path / "pm.ritz").write_text(_MODULE)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz0_refuses_a_payload_that_tests(tmp_path, name):
    source, line, col, shown, variant = REFUSED[name]
    proc, ll = _ritz0(tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"ritz0 accepted {name}:\n{out[-1500:]}"
    message = (f"a variant payload can only be bound, not tested: "
               f"'{shown}' in '{variant}(...)'{_HINT}")
    hits = re.findall(rf"unit\.ritz:{line}:{col}: {re.escape(message)}$", out, re.M)
    assert len(hits) == 1, f"{name}: want one {message!r}:\n{out[-1500:]}"
    assert not ll.exists(), f"ritz0 wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(KEPT))
def test_ritz0_still_runs_a_payload_that_binds(tmp_path, name):
    source, code = KEPT[name]
    proc, ll = _ritz0(tmp_path, source)
    assert proc.returncode == 0, f"{name}:\n{(proc.stdout + proc.stderr)[-1500:]}"
    exe = tmp_path / "unit"
    subprocess.run(["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"], check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, name


@pytest.mark.integration
def test_a_nested_variant_keeps_its_own_message(tmp_path):
    """`Some(Some(x))` is #1291's, and says so."""
    proc, _ = _ritz0(tmp_path, _opt("Option<i32>", "Some(Some(x))", "None"))
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "Nested variant patterns are not supported" in out, out


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted({**LITERALS, **TYPES}))
def test_ritz1_cannot_parse_a_payload_that_tests(request, tmp_path, compiler, name):
    """Goes red when ritz1 learns one, which must then refuse it or compile it."""
    proc, ll = _ritz1(request, compiler, tmp_path, REFUSED[name][0])
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "Parse error" in out, f"{compiler}, {name}:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", [
    pytest.param(name, marks=pytest.mark.xfail(strict=True, reason=RITZ1_NEVER_READS[name]))
    if name in RITZ1_NEVER_READS else name
    for name in sorted({**NAMES, **NAMES_ON_BOTH})])
def test_ritz1_refuses_a_name_that_tests(request, tmp_path, compiler, name):
    source, line, col, shown, variant = REFUSED[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-800:]}"
    message = (f"a variant payload can only be bound, not tested: "
               f"'{shown}' in '{variant}(...)'{_HINT}")
    hits = re.findall(rf"unit\.ritz:{line}:{col}: error: {re.escape(message)}$", out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r}:\n{out[-800:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(set(KEPT) - set(NOT_ON_RITZ1)))
def test_ritz1_still_runs_a_payload_that_binds(request, tmp_path, compiler, name):
    source, code = KEPT[name]
    proc, ll = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, f"{compiler}, {name}:\n{(proc.stdout + proc.stderr)[-800:]}"
    exe = tmp_path / "unit"
    subprocess.run(["clang", "-w", str(ll), str(RITZ_START), "-o", str(exe), "-nostdlib"],
                   check=True)
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


# Each arm has no field to read. ritz0 stops at both (#2423, and its own `Unknown
# variant`); ritz1 binds, which #2408 and #2421 own. Here it must only get through.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("source", [
    pytest.param(_K + _Q + _on("Q", "Z(K)", "Q.Z"), id="unit_variant"),
    # An integer field just before B's: a miss must not read it.
    pytest.param(_K + "enum A\n    Last(i32)\nenum B\n    Y\n" + _on("B", "Nope(K)", "B.Y"),
                 id="no_such_variant"),
    pytest.param(_K + _opt("i32", "None(K)", "5"), id="none"),
])
def test_ritz1_reads_no_field_where_an_arm_has_none(request, tmp_path, compiler, source):
    proc, _ = _ritz1(request, compiler, tmp_path, source)
    assert proc.returncode == 0, (proc.stdout + proc.stderr)[-800:]


@pytest.mark.integration
def test_ritz0_locates_a_refusal_in_the_module_that_holds_it(tmp_path):
    source = ("import pm\nfn main() -> i32\n    let o: Option<i32> = Some(5)\n"
              "    in_module<i32>(1, o)\n")
    proc, _ = _ritz0(tmp_path, source)
    assert re.search(r"pm\.ritz:8:14: a variant payload", proc.stdout + proc.stderr)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_locates_a_refusal_in_the_module_that_holds_it(request, tmp_path, compiler):
    source = ("import pm\nfn main() -> i32\n    let o: Option<i32> = Some(5)\n"
              "    in_module<i32>(1, o)\n")
    proc, _ = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert re.search(r"pm\.ritz:8:14: error: a variant payload", out), out[-800:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_reports_every_name_that_tests(request, tmp_path, compiler):
    """ritz0 stops at the first; ritz1 carries on, and must not lose the second."""
    source = (_K + "const J: i32 = 1\nfn f(o: Option<i32>) -> i32\n    match o\n"
              "        Some(K) => 1\n        Some(J) => 3\n        _ => 2\n"
              "fn main() -> i32\n    f(Some(5))\n")
    proc, _ = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert re.search(r"unit\.ritz:5:14: error: a variant payload", out), out[-800:]
    assert re.search(r"unit\.ritz:6:14: error: a variant payload", out), out[-800:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_coverage_comes_first_on_ritz1_too(request, tmp_path, compiler):
    """As on ritz0: a match that misses says so, whatever else is wrong with it."""
    source = (_K + "fn f(o: Option<i32>) -> i32\n    match o\n        Some(K) => 1\n"
              "fn main() -> i32\n    f(Some(5))\n")
    proc, _ = _ritz1(request, compiler, tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "non-exhaustive match: missing None" in out, out[-800:]
