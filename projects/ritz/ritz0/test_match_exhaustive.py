#!/usr/bin/env python3
"""A `match` that does not cover its scrutinee is an error (LARB R6, AGAST #2344).

Before this, `f(5)` matching no arm gave 2 on ritz0 (LLVM folded the unreachable
switch default into the last arm) and 0 on ritz1 (a zero fallthrough), silently.

Covered means an unguarded `_` or binding; every variant of an enum; `true` and
`false`; or every member of a union. An integer needs a catch-all. Every table
here goes through ritz0, ritz1 and ritz1_selfhosted, which must give the same
located error, naming what is missing.

The accepted half is load-bearing: it is run, not only compiled, so rejecting
everything fails it, and so does a scrutinee whose type a compiler lost. ritz1
used to read `R` in `match a[1]` as a binding, and take the first arm.
"""

import os
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import match_coverage
import parser as ritz_parser
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]

_C = "enum C\n    R\n    G\n    B\n"
_MAIN = "fn main() -> i32\n    0\n"
_OPT = "import ritzlib.option\n"
_RES = "import ritzlib.result\n"
_S = "struct S\n    c: C\nimpl S\n    fn get(self) -> C\n        self.c\n"
_COLORS = {"colors.ritz": "pub enum Color\n    Red\n    Green\n    Blue\n"
                          "pub fn pick() -> Color\n    Color.Green\n"}
_CATCH_ALL = "a catch-all"


def _int_fn(body):
    return "fn f(n: i64) -> i64\n" + body + _MAIN


# name -> (source, line, col, what the error must name[, extra files])
REJECTED = {
    # R6's table: every position a `match` can stand in.
    "value_tail": (_int_fn("    match n\n        0 => 1\n        1 => 2\n"),
                   2, 5, _CATCH_ALL),
    "value_let": (_int_fn("    let v = match n\n        0 => 1\n        1 => 2\n    v\n"),
                  2, 13, _CATCH_ALL),
    "value_return": (_int_fn("    return match n\n        0 => 1\n"), 2, 12, _CATCH_ALL),
    "arms_return": (_int_fn("    match n\n        0 => return 1\n        1 => return 2\n"),
                    2, 5, _CATCH_ALL),
    "statement": ("fn f(n: i64)\n    match n\n        0 => pass\n" + _MAIN,
                  2, 5, _CATCH_ALL),
    # #2245: this is the shape that reached emit_implicit_return_tail at run time.
    "in_an_if_arm": ("fn f(n: i64, c: i64) -> i64\n"
                     "    if c > 0\n"
                     "        match n\n"
                     "            0 => return 1\n"
                     "    else\n"
                     "        return 2\n" + _MAIN, 3, 9, _CATCH_ALL),
    "in_a_loop": (_int_fn("    var i: i64 = 0\n    while i < 3\n        match i\n"
                          "            0 => pass\n        i = i + 1\n    i\n"),
                  4, 9, _CATCH_ALL),
    "in_a_method": ("struct T\n    v: i64\nimpl T\n    fn m(self) -> i64\n"
                    "        match self.v\n            0 => 1\n" + _MAIN,
                    5, 9, _CATCH_ALL),
    "inner_of_a_covered_match": (_int_fn("    match n\n        0 =>\n"
                                         "            match n\n                1 => 2\n"
                                         "        _ => 3\n"), 4, 13, _CATCH_ALL),
    "in_a_fn_nothing_calls": ("fn dead(n: i64) -> i64\n    match n\n        0 => 1\n" + _MAIN,
                              2, 5, _CATCH_ALL),

    # What counts as a catch-all. A name that is a const compares; it binds nothing.
    "consts_only": ("const A: i64 = 0\nconst B: i64 = 1\n" + _int_fn(
        "    match n\n        A => 1\n        B => 2\n"), 4, 5, _CATCH_ALL),

    # Enums, named in declaration order however the arms are written.
    "enum_one_missing": (_C + "fn f(c: C) -> i64\n    match c\n        R => 1\n        G => 2\n" + _MAIN,
                         6, 5, "B"),
    "enum_two_missing": (_C + "fn f(c: C) -> i64\n    match c\n        G => 1\n" + _MAIN,
                         6, 5, "R, B"),
    "enum_qualified_arms": (_C + "fn f(c: C) -> i64\n    match c\n        C.R => 1\n        C.B => 2\n" + _MAIN,
                            6, 5, "G"),
    "enum_statement": (_C + "fn f(c: C)\n    match c\n        R => pass\n        G => pass\n" + _MAIN,
                       6, 5, "B"),
    "enum_arms_return": (_C + "fn f(c: C) -> i64\n    match c\n        R => return 1\n" + _MAIN,
                         6, 5, "G, B"),
    "enum_payload_missing": ("enum P\n    Hit(i64)\n    Miss\n"
                             "fn f(p: P) -> i64\n    match p\n        Hit(v) => v\n" + _MAIN,
                             5, 5, "Miss"),
    "option_no_none": (_OPT + "fn f(o: Option<i64>) -> i64\n    match o\n        Some(v) => v\n" + _MAIN,
                       3, 5, "None"),
    "option_no_some": (_OPT + "fn f(o: Option<i64>) -> i64\n    match o\n        None => 0\n" + _MAIN,
                       3, 5, "Some"),
    "result_no_err": (_RES + "fn f(r: Result<i64, i32>) -> i64\n    match r\n        Ok(v) => v\n" + _MAIN,
                      3, 5, "Err"),
    # Neither needs an import, so ritz1's enum tracker has no entry for them.
    "option_unimported": ("fn f(o: Option<i64>) -> i64\n    match o\n        Some(v) => v\n" + _MAIN,
                          2, 5, "None"),
    "option_unimported_bare_none": ("fn f(o: Option<i64>) -> i64\n    match o\n        None => 0\n" + _MAIN,
                                    2, 5, "Some"),
    "result_unimported": ("fn f(r: Result<i64, i32>) -> i64\n    match r\n        Err(e) => 0\n" + _MAIN,
                          2, 5, "Ok"),
    "unimported_from_a_method": (
        "struct T\n    v: i64\nimpl T\n    fn o(self) -> Option<i32>\n        Some(1)\n"
        "fn f(t: T) -> i32\n    match t.o()\n        Some(x) => x\n" + _MAIN, 7, 5, "None"),
    # No import and no type: only the arm says which of the two this is.
    "unimported_untyped_option": (
        "struct T\n    v: i64\nimpl T\n    fn o(self) -> Option<i32>\n        Some(1)\n"
        "struct H\n    t: T\nfn f(h: H) -> i32\n    match h.t.o()\n        Some(x) => x\n" + _MAIN,
        9, 5, "None"),
    "unimported_untyped_result": (
        "struct T\n    v: i64\nimpl T\n    fn r(self) -> Result<i32, i32>\n        Ok(1)\n"
        "struct H\n    t: T\nfn f(h: H) -> i32\n    match h.t.r()\n        Err(e) => e\n" + _MAIN,
        9, 5, "Ok"),
    "generic_user_enum": ("enum W<T>\n    A(T)\n    Bb\n"
                          "fn f(w: W<i32>) -> i32\n    match w\n        A(x) => x\n" + _MAIN,
                          5, 5, "Bb"),

    # Every way to reach an enum. Each of these was a catch-all to a name-based
    # reading, because a bare variant looks exactly like a binding.
    "scrutinee_field": (_C + "struct H\n    c: C\nfn f(h: H) -> i64\n    match h.c\n"
                        "        R => 1\n" + _MAIN, 8, 5, "G, B"),
    "scrutinee_index": (_C + "fn f() -> i64\n    var a: [2]C = [C.R, C.G]\n    match a[1]\n"
                        "        R => 1\n        G => 2\n" + _MAIN, 7, 5, "B"),
    "scrutinee_deref": (_C + "fn f(p: *C) -> i64\n    match *p\n        R => 1\n" + _MAIN,
                        6, 5, "G, B"),
    "scrutinee_global": (_C + "var g: C\nfn f() -> i64\n    match g\n        R => 1\n" + _MAIN,
                         7, 5, "G, B"),
    "scrutinee_pointer_index": (_C + "fn f(p: *C) -> i64\n    match p[1]\n        R => 1\n" + _MAIN,
                                6, 5, "G, B"),
    "scrutinee_borrow": (_C + "fn f() -> i64\n    var c: C = C.R\n    match @c\n        R => 1\n" + _MAIN,
                         7, 5, "G, B"),
    "scrutinee_call": (_C + "fn k() -> C\n    C.R\nfn f() -> i64\n    match k()\n        R => 1\n" + _MAIN,
                       8, 5, "G, B"),
    "scrutinee_method": (_C + _S + "fn f(s: S) -> i64\n    match s.get()\n        R => 1\n        G => 2\n" + _MAIN,
                         11, 5, "B"),
    "scrutinee_method_option": (
        _OPT + "struct T\n    v: i64\nimpl T\n    fn o(self) -> Option<i32>\n        Some(1)\n"
        "fn f(t: T) -> i32\n    match t.o()\n        Some(x) => x\n" + _MAIN, 8, 5, "None"),
    "scrutinee_untyped_let": (_C + "fn k() -> C\n    C.R\nfn f() -> i64\n    let c = k()\n"
                              "    match c\n        R => 1\n" + _MAIN, 9, 5, "G, B"),
    # Shapes ritz1 has no type for. ritz0 reads the emitted value; ritz1 goes by
    # the arm, or `R` binds and the match reads as covered (match_arms_enum).
    "untyped_scrutinee_cast": (_C + "fn f(x: i64) -> i64\n    match x as C\n        R => 1\n"
                               "        G => 2\n" + _MAIN, 6, 5, "B"),
    "untyped_scrutinee_deref_of_field": (
        _C + "struct H\n    p: *C\nfn f(h: H) -> i64\n    match *h.p\n        R => 1\n"
        "        G => 2\n" + _MAIN, 8, 5, "B"),
    "untyped_scrutinee_method_on_field": (
        _C + _S + "struct H\n    s: S\nfn f(h: H) -> i64\n    match h.s.get()\n        R => 1\n"
        "        G => 2\n" + _MAIN, 13, 5, "B"),
    "untyped_scrutinee_method_on_method": (
        _C + _S + "struct H\n    s: S\nimpl H\n    fn get_s(self) -> S\n        self.s\n"
        "fn f(h: H) -> i64\n    match h.get_s().get()\n        R => 1\n        G => 2\n" + _MAIN,
        16, 5, "B"),
    "untyped_scrutinee_if": (_C + "fn f(b: bool) -> i64\n    match if b then C.R else C.G\n"
                             "        R => 1\n        G => 2\n" + _MAIN, 6, 5, "B"),
    "untyped_scrutinee_try": (_OPT + _C + "fn k() -> Option<C>\n    Some(C.R)\n"
                              "fn f() -> Option<i64>\n    let v = match k()?\n        R => 1\n"
                              "        G => 2\n    Some(v)\n" + _MAIN, 9, 13, "B"),
    # The limit R6 names: the enum is declared in another file.
    "imported_bare_variants": (
        "import colors\nfn f() -> i64\n    match pick()\n        Red => 1\n        Green => 2\n" + _MAIN,
        3, 5, "Blue", _COLORS),

    # bool: `true` and `false`, not the integers that lower to them.
    "bool_no_false": ("fn f(b: bool) -> i64\n    match b\n        true => 1\n" + _MAIN,
                      2, 5, "false"),
    "bool_no_true": ("fn f(b: bool) -> i64\n    match b\n        false => 1\n" + _MAIN,
                     2, 5, "true"),
    "bool_comparison": ("fn f(n: i64) -> i64\n    match n > 2\n        true => 1\n" + _MAIN,
                        2, 5, "false"),
    # A const compares, so it is no catch-all here either.
    "bool_const_arm": ("const A: i64 = 1\nfn f(b: bool) -> i64\n    match b\n        A => 1\n" + _MAIN,
                       3, 5, "true, false"),
    "bool_integer_arms": ("fn f(b: bool) -> i64\n    match b\n        1 => 1\n        0 => 2\n" + _MAIN,
                          2, 5, "true, false"),
}

# A scrutinee ritz1 can't type must still not bind a variant: with every variant
# named it compiles and takes the right arm, or it fails. name -> (source, code).
UNTYPED_BUT_COVERED = {
    "cast": (_C + "fn main() -> i32\n    let x: i64 = 2\n    match x as C\n"
             "        R => 1\n        G => 2\n        B => 3\n", 3),
    "deref_of_field": (_C + "struct H\n    p: *C\nfn main() -> i32\n    var c: C = C.B\n"
                       "    let h = H { p: @c }\n    match *h.p\n"
                       "        R => 1\n        G => 2\n        B => 3\n", 3),
    "method_on_field": (_C + _S + "struct H\n    s: S\nfn main() -> i32\n"
                        "    let h = H { s: S { c: C.B } }\n    match h.s.get()\n"
                        "        R => 1\n        G => 2\n        B => 3\n", 3),
    "if_value": (_C + "fn main() -> i32\n    let b: bool = false\n"
                 "    match if b then C.R else C.B\n"
                 "        R => 1\n        G => 2\n        B => 3\n", 3),
    "try": (_OPT + _C + "fn k() -> Option<C>\n    Some(C.B)\nfn f() -> Option<i32>\n"
            "    let v: i32 = match k()?\n        R => 1\n        G => 2\n        B => 3\n"
            "    Some(v)\nfn main() -> i32\n    match f()\n        Some(v) => v\n"
            "        None => 9\n", 3),
}

# ritz1 parses none of these patterns or types; RITZ1_CANNOT_PARSE pins that.
REJECTED_RITZ0_ONLY = {
    "value_call_argument": ("fn id(v: i64) -> i64\n    v\n" + _int_fn(
        "    id(match n\n        0 => 1\n    )\n"), 4, 8, _CATCH_ALL),
    "union_member_missing": ("type U = i64 | *u8 | bool\nfn f(x: U) -> i64\n    match x\n"
                             "        i64 => 1\n" + _MAIN, 3, 5, "*u8, bool"),
    # `Some(0)` covers one value of `Some`, so it does not cover `Some`.
    "literal_payload": (_OPT + "fn f(o: Option<i32>) -> i32\n    match o\n"
                        "        Some(0) => 1\n        None => 2\n" + _MAIN, 3, 5, "Some"),
    "two_field_variant": ("enum P\n    Two(i64, i64)\n    Z\nfn f(p: P) -> i64\n    match p\n"
                          "        Two(a, b) => a\n" + _MAIN, 5, 5, "Z"),
}

# name -> (source, exit code[, extra files]); None compiles without running,
# because ritz1 compiles a module at a time and `pick` lives in another.
ACCEPTED = {
    "wildcard": ("fn main() -> i32\n    let n: i64 = 5\n    match n\n"
                 "        0 => 1\n        _ => 2\n", 2),
    "binding": ("fn main() -> i32\n    let n: i64 = 5\n    match n\n"
                "        0 => 1\n        k => k as i32\n", 5),
    # A binding named like a variant (`R =>` on an integer) is no catch-all but an
    # error since R12 (#2407): test_local_takes_module_name.py, arm_over_a_variant_*.
    "catch_all_before_const": ("const A: i64 = 0\nfn main() -> i32\n    let n: i64 = 5\n"
                               "    match n\n        A => 1\n        _ => 2\n", 2),
    "statement_wildcard": ("fn main() -> i32\n    var r: i32 = 0\n    let n: i64 = 5\n"
                           "    match n\n        0 => r = 1\n        _ => r = 2\n    r\n", 2),
    "enum_all": (_C + "fn main() -> i32\n    let c: C = C.B\n    match c\n"
                 "        R => 1\n        G => 2\n        B => 3\n", 3),
    "enum_any_order": (_C + "fn main() -> i32\n    let c: C = C.G\n    match c\n"
                       "        B => 3\n        R => 1\n        G => 2\n", 2),
    "enum_qualified": (_C + "fn main() -> i32\n    let c: C = C.B\n    match c\n"
                       "        C.R => 1\n        C.G => 2\n        C.B => 3\n", 3),
    "enum_wildcard": (_C + "fn main() -> i32\n    let c: C = C.B\n    match c\n"
                      "        R => 1\n        _ => 9\n", 9),
    # Not a variant of this enum, so a binding, so a catch-all.
    "enum_binding": (_C + "fn main() -> i32\n    let c: C = C.B\n    match c\n"
                     "        R => 1\n        other => 9\n", 9),
    "enum_arms_return": (_C + "fn f(c: C) -> i32\n    match c\n        R => return 1\n"
                         "        G => return 2\n        B => return 3\n"
                         "fn main() -> i32\n    f(C.G)\n", 2),
    "option": (_OPT + "fn f(o: Option<i32>) -> i32\n    match o\n        Some(v) => v\n"
               "        None => 8\nfn main() -> i32\n    f(None)\n", 8),
    "option_wildcard_payload": (_OPT + "fn f(o: Option<i32>) -> i32\n    match o\n"
                                "        Some(_) => 4\n        None => 8\n"
                                "fn main() -> i32\n    f(Some(1))\n", 4),
    "option_unimported": ("fn f(o: Option<i32>) -> i32\n    match o\n        Some(v) => v\n"
                          "        None => 8\nfn main() -> i32\n    f(None)\n", 8),
    "result_unimported": ("fn f(r: Result<i32, i32>) -> i32\n    match r\n        Ok(v) => v\n"
                          "        Err(e) => e\nfn main() -> i32\n    f(Err(6))\n", 6),
    "unimported_wildcard": ("fn f(o: Option<i32>) -> i32\n    match o\n        None => 1\n"
                            "        _ => 8\nfn main() -> i32\n    f(Some(2))\n", 8),
    "unimported_binding": ("fn f(o: Option<i32>) -> i32\n    match o\n        None => 1\n"
                           "        other => 8\nfn main() -> i32\n    f(Some(2))\n", 8),
    "result": (_RES + "fn f(r: Result<i32, i32>) -> i32\n    match r\n        Ok(v) => v\n"
               "        Err(e) => e\nfn main() -> i32\n    f(Err(6))\n", 6),
    "scrutinee_field": (_C + "struct H\n    c: C\nfn main() -> i32\n    let h = H { c: C.B }\n"
                        "    match h.c\n        R => 1\n        G => 2\n        B => 3\n", 3),
    # These two are the miscompiles: before #2344, ritz1 gave 1 and invalid IR.
    "scrutinee_index": (_C + "fn main() -> i32\n    var a: [2]C = [C.R, C.B]\n    match a[1]\n"
                        "        R => 1\n        G => 2\n        B => 3\n", 3),
    "scrutinee_method": (_C + _S + "fn main() -> i32\n    let s = S { c: C.G }\n    match s.get()\n"
                         "        R => 1\n        G => 2\n        B => 3\n", 2),
    "scrutinee_method_option": (
        _OPT + "struct T\n    v: i64\nimpl T\n    fn o(self) -> Option<i32>\n        Some(7)\n"
        "fn main() -> i32\n    let t = T { v: 1 }\n    match t.o()\n"
        "        Some(x) => x\n        None => 9\n", 7),
    "scrutinee_global": (_C + "var g: C\nfn main() -> i32\n    g = C.B\n    match g\n"
                         "        R => 1\n        G => 2\n        B => 3\n", 3),
    "scrutinee_pointer_index": (_C + "fn f(p: *C) -> i32\n    match p[1]\n        R => 1\n"
                                "        G => 2\n        B => 3\n"
                                "fn main() -> i32\n    var a: [2]C = [C.R, C.B]\n"
                                "    f(@a[0])\n", 3),
    "scrutinee_deref": (_C + "fn f(p: *C) -> i32\n    match *p\n        R => 1\n        G => 2\n"
                        "        B => 3\nfn main() -> i32\n    var c: C = C.B\n    f(@c)\n", 3),
    "scrutinee_borrow": (_C + "fn main() -> i32\n    var c: C = C.G\n    match @c\n"
                         "        R => 1\n        G => 2\n        B => 3\n", 2),
    "scrutinee_call": (_C + "fn k() -> C\n    C.B\nfn main() -> i32\n    match k()\n"
                       "        R => 1\n        G => 2\n        B => 3\n", 3),
    "imported_bare_variants": (
        "import colors\nfn f() -> i64\n    match pick()\n        Red => 1\n"
        "        Green => 2\n        Blue => 3\n" + _MAIN, None, _COLORS),
    "bool": ("fn f(b: bool) -> i32\n    match b\n        true => 1\n        false => 2\n"
             "fn main() -> i32\n    f(false) * 10 + f(true)\n", 21),
    "bool_either_order": ("fn f(b: bool) -> i32\n    match b\n        false => 2\n"
                          "        true => 1\nfn main() -> i32\n    f(false) * 10 + f(true)\n", 21),
    "bool_comparison": ("fn main() -> i32\n    let n: i64 = 3\n    match n > 2\n"
                        "        true => 1\n        false => 2\n", 1),
    "bool_untyped_let": ("fn main() -> i32\n    let n: i64 = 3\n    let b = n > 2\n    match b\n"
                         "        true => 1\n        false => 2\n", 1),
    "bool_not": ("fn main() -> i32\n    let b: bool = false\n    match !b\n"
                 "        true => 1\n        false => 2\n", 1),
    "bool_field": ("struct H\n    b: bool\nfn main() -> i32\n    let h = H { b: true }\n    match h.b\n"
                   "        true => 1\n        false => 2\n", 1),
    "bool_call": ("fn t() -> bool\n    true\nfn main() -> i32\n    match t()\n"
                  "        true => 1\n        false => 2\n", 1),
    "bool_wildcard": ("fn f(b: bool) -> i32\n    match b\n        true => 1\n        _ => 2\n"
                      "fn main() -> i32\n    f(false)\n", 2),
    "bool_value_let": ("fn main() -> i32\n    let b: bool = false\n    let v: i32 = match b\n"
                       "        true => 1\n        false => 2\n    v\n", 2),
    # A `-> T` fn ending here relies on the `unreachable` behind every arm.
    "tail_enum_all_arms_return_in_an_if": (
        _C + "fn f(c: C, k: i64) -> i32\n    if k > 0\n        match c\n"
        "            R => return 1\n            G => return 2\n            B => return 3\n"
        "    else\n        return 4\nfn main() -> i32\n    f(C.B, 1)\n", 3),
}

ACCEPTED_RITZ0_ONLY = {
    "union": ("type U = i64 | bool\nfn main() -> i32\n    let x: U = 42 as U\n    match x\n"
              "        i64 => 1\n        bool => 2\n", 1),
    "union_wildcard": ("type U = i64 | bool\nfn main() -> i32\n    let x: U = true as U\n"
                       "    match x\n        i64 => 1\n        _ => 2\n", 2),
    "two_field_variant": ("enum P\n    Two(i64, i64)\n    Z\nfn main() -> i32\n"
                          "    let p = P.Two(1, 2)\n    match p\n"
                          "        Two(a, b) => (a + b) as i32\n        Z => 0\n", 3),
    # ritz1 can't return a generic user enum yet: `ret %W$i32` of an i64.
    "generic_user_enum": ("enum W<T>\n    A(T)\n    Bb\nfn mk() -> W<i32>\n    A(7)\n"
                          "fn f(w: W<i32>) -> i32\n    match w\n        A(x) => x\n"
                          "        Bb => 9\nfn main() -> i32\n    f(mk())\n", 7),
}

RITZ1_CANNOT_PARSE = ("union_member_missing", "literal_payload", "two_field_variant",
                      "value_call_argument")

# A `true` pattern tests a bool. On an integer ritz0 emitted `switch i64 true`,
# which clang rejected, and the pattern is meaningless there either way.
NOT_A_BOOL = {
    "true_on_an_integer": ("fn f(n: i64) -> i64\n    match n\n        true => 1\n        _ => 2\n" + _MAIN,
                           3, 9),
    "false_on_an_integer": ("fn f(n: i64) -> i64\n    match n\n        0 => 0\n        false => 1\n"
                            "        _ => 2\n" + _MAIN, 4, 9),
}


def _case(entry, arity):
    """Split a table entry into its fixed fields and its extra files."""
    return (*entry[:arity], entry[arity] if len(entry) > arity else {})


def _compile(request, compiler, tmp_path, source, extra):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    for name, text in extra.items():
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


def _assert_error(proc, ll, compiler, name, line, col, message):
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{out[-1500:]}"
    hits = re.findall(rf"unit\.ritz:{line}:{col}: (?:error: )?{re.escape(message)}$", out, re.M)
    assert len(hits) == 1, f"{compiler}, {name}: want one {message!r}:\n{out[-1500:]}"
    assert not ll.exists(), f"{compiler} wrote IR for {name}"


def _assert_rejected(request, compiler, tmp_path, name, entry):
    source, line, col, missing, extra = _case(entry, 4)
    proc, ll = _compile(request, compiler, tmp_path, source, extra)
    _assert_error(proc, ll, compiler, name, line, col,
                  f"non-exhaustive match: missing {missing}")


def _assert_runs(request, compiler, tmp_path, name, entry):
    source, code, extra = _case(entry, 2)
    proc, ll = _compile(request, compiler, tmp_path, source, extra)
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0 and ll.exists(), f"{compiler}, {name}:\n{out[-1500:]}"
    if code is None:
        return
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(2, str(RITZ_START))
    built = subprocess.run(link, cwd=tmp_path, capture_output=True, text=True)
    assert built.returncode == 0, f"{compiler}, {name}: link:\n{built.stderr[-1500:]}"
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REJECTED))
def test_a_match_that_misses_is_an_error(request, tmp_path, compiler, name):
    _assert_rejected(request, compiler, tmp_path, name, REJECTED[name])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_a_covering_match_compiles_and_picks_the_right_arm(request, tmp_path, compiler, name):
    _assert_runs(request, compiler, tmp_path, name, ACCEPTED[name])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(UNTYPED_BUT_COVERED))
def test_an_untyped_scrutinee_never_takes_the_wrong_arm(request, tmp_path, compiler, name):
    source, code = UNTYPED_BUT_COVERED[name]
    proc, ll = _compile(request, compiler, tmp_path, source, {})
    if compiler == "ritz0":
        assert proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]
    if proc.returncode != 0:
        return
    exe = tmp_path / "unit"
    link = ["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link.insert(2, str(RITZ_START))
    if subprocess.run(link, cwd=tmp_path, capture_output=True).returncode != 0:
        assert compiler != "ritz0", "ritz0 emitted invalid IR"
        return
    assert subprocess.run([str(exe)], timeout=60).returncode == code, f"{compiler}, {name}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REJECTED_RITZ0_ONLY))
def test_ritz0_only_shapes_that_miss(request, tmp_path, name):
    _assert_rejected(request, "ritz0", tmp_path, name, REJECTED_RITZ0_ONLY[name])


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ACCEPTED_RITZ0_ONLY))
def test_ritz0_only_shapes_that_cover(request, tmp_path, name):
    _assert_runs(request, "ritz0", tmp_path, name, ACCEPTED_RITZ0_ONLY[name])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", RITZ1_CANNOT_PARSE)
def test_ritz1_still_cannot_parse_the_held_back_cases(request, tmp_path, compiler, name):
    """Goes red when ritz1 learns a shape, so it joins the shared table."""
    source = REJECTED_RITZ0_ONLY[name][0]
    proc, _ = _compile(request, compiler, tmp_path, source, {})
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0 and "Parse error" in out, f"{compiler}, {name}:\n{out[-800:]}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_A_BOOL))
def test_a_bool_pattern_needs_a_bool_scrutinee(request, tmp_path, compiler, name):
    source, line, col = NOT_A_BOOL[name]
    proc, ll = _compile(request, compiler, tmp_path, source, {})
    _assert_error(proc, ll, compiler, name, line, col,
                  "a `true` or `false` pattern needs a bool scrutinee")


# Behaviour can't show these: a dead `ret i32 0` and a dead `unreachable` run the
# same. Only the IR says the fallback is gone.
_ALL_ARMS_RETURN = (_C + "fn f(c: C, k: i64) -> i32\n    if k > 0\n        match c\n"
                    "            R => return 1\n            G => return 2\n"
                    "            B => return 3\n    else\n        return 4\n" + _MAIN)
_VALUE_MATCH = (_C + "fn f(c: C) -> i64\n    let v: i64 = match c\n        R => 1\n"
                "        G => 2\n        B => 3\n    v\n" + _MAIN)
_VOID_ARMS = ("fn g()\n    var i: i64 = 1\nfn f(n: i64)\n    match n\n        0 => g()\n"
              "        _ => g()\n" + _MAIN)
_STRUCT_TAIL = ("struct P\n    a: i64\n    b: i64\n    c: i64\n    d: i64\n    e: i64\n"
                "fn f(k: i64) -> P\n    if k > 0\n        return P { a: 1, b: 2, c: 3, d: 4, e: 5 }\n"
                "    else\n        return P { a: 6, b: 7, c: 8, d: 9, e: 0 }\n" + _MAIN)


def _fn_ir(ll, name):
    text = ll.read_text()
    return text[text.index(f"@{name}("):].split("\n}\n", 1)[0]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("source", [_ALL_ARMS_RETURN, _STRUCT_TAIL], ids=["scalar", "sret"])
def test_ritz1_fn_tail_has_no_zero_fallback(request, tmp_path, compiler, source):
    proc, ll = _compile(request, compiler, tmp_path, source, {})
    assert proc.returncode == 0, proc.stderr[-1500:]
    body = _fn_ir(ll, "f")
    assert "unreachable" in body, body
    assert "ret i32 0" not in body and "__ritz_sret_zero" not in body, body


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_match_has_no_fallthrough_edge(request, tmp_path, compiler):
    proc, ll = _compile(request, compiler, tmp_path, _VALUE_MATCH, {})
    assert proc.returncode == 0, proc.stderr[-1500:]
    body = _fn_ir(ll, "f")
    phi = next(line for line in body.splitlines() if " = phi " in line)
    assert phi.count("[") == 3, f"one edge per arm: {phi}"
    assert "unreachable" in body, body


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_void_match_ends_in_unreachable(request, tmp_path, compiler):
    proc, ll = _compile(request, compiler, tmp_path, _VOID_ARMS, {})
    assert proc.returncode == 0, proc.stderr[-1500:]
    assert "unreachable" in _fn_ir(ll, "f")


# --- The rule itself, for what no source program can reach yet -----------------

def _arm(pattern, guard=None):
    return SimpleNamespace(pattern=pattern, guard=guard)


def _parse_arms(body):
    module = ritz_parser.parse("fn f(n: i64) -> i64\n    match n\n" + body)
    return module.items[0].body.expr.arms


@pytest.mark.unit
def test_a_guarded_arm_never_counts():
    """Both parsers refuse guards (#1939), so only the rule can show this."""
    wildcard, variant = _parse_arms("        _ => 1\n        R => 2\n")
    guard = object()
    assert match_coverage.scalar_gap([_arm(wildcard.pattern, guard)], ()) == [_CATCH_ALL]
    assert match_coverage.enum_gap([_arm(variant.pattern, guard)], ["R"]) == ["R"]
    assert match_coverage.enum_gap([_arm(wildcard.pattern, guard)], ["R"]) == ["R"]
    assert match_coverage.bool_gap([_arm(wildcard.pattern, guard)], ()) == ["true", "false"]


@pytest.mark.unit
def test_a_bool_arm_is_not_the_integer_it_equals():
    """`True == 1` in Python, so a `1` arm must not read as `true`."""
    one, zero = _parse_arms("        1 => 1\n        0 => 2\n")
    assert match_coverage.bool_gap([one, zero], ()) == ["true", "false"]
