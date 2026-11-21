#!/usr/bin/env python3
"""Character literal patterns in `match` (LANGUAGE_SPEC §8.2, LARB R72, AGAST #4196).

A char literal is `u8` (§2.6), so a char pattern is an integer literal pattern
typed `u8`: it compares a `u8` scrutinee exactly as `40` does, under the same
catch-all and repeated-arm rules. On any other scrutinee it is an error at the
pattern. `40 =>` beside `'(' =>` is the same test, so the second is unreachable.

Every row goes through ritz0, ritz1 and ritz1_selfhosted, which must agree. The
run rows are load-bearing: they execute each arm's result, so a compiler that
refuses every char pattern fails them.
"""

import pytest
from test_match_exhaustive import (
    COMPILERS,
    _MAIN,
    _assert_error,
    _assert_runs,
    _compile,
    _unreachable,
)

_CHAR_NEEDS_U8 = "a character pattern needs a u8 scrutinee"
_C = "enum C\n    R\n    G\n"


def _u8_fn(body):
    return "fn f(c: u8) -> i64\n" + body


# name -> (source, exit code).  `main` returns 0 only when every call took the
# arm its character names.
RUNS = {
    # The acceptance shape: one arm per punctuation character, picked by value.
    "picks_each_arm": (_u8_fn("    match c\n        '(' => 1\n        ')' => 2\n"
                              "        'a' => 3\n        _ => 4\n")
                       + "fn main() -> i32\n"
                         "    if f(40) != 1\n        return 1\n"
                         "    if f(41) != 2\n        return 2\n"
                         "    if f(97) != 3\n        return 3\n"
                         "    if f(65) != 4\n        return 4\n"
                         "    0\n", 0),
    # An escape, the hex escape, a quote and a backslash all cook to one byte.
    "escapes": (_u8_fn("    match c\n        '\\n' => 1\n        '\\x41' => 2\n"
                       "        '\\'' => 3\n        '\\\\' => 4\n        _ => 5\n")
                + "fn main() -> i32\n"
                  "    if f(10) != 1\n        return 1\n"
                  "    if f(65) != 2\n        return 2\n"
                  "    if f(39) != 3\n        return 3\n"
                  "    if f(92) != 4\n        return 4\n"
                  "    if f(0) != 5\n        return 5\n"
                  "    0\n", 0),
    # A char pattern and an integer pattern are one kind: `40` and `'('` may
    # sit in different arms, and a catch-all name still binds the u8.
    "char_and_integer_arms": (_u8_fn("    match c\n        'A' => 10\n"
                                     "        40 => 20\n        other => other as i64\n")
                              + "fn main() -> i32\n"
                                "    if f(65) != 10\n        return 1\n"
                                "    if f(40) != 20\n        return 2\n"
                                "    if f(7) != 7\n        return 3\n"
                                "    0\n", 0),
    # A char literal is a u8 scrutinee too.
    "char_literal_scrutinee": ("fn main() -> i32\n    match 'b'\n"
                               "        'a' => return 1\n"
                               "        'b' => return 2\n"
                               "        _ => return 3\n", 2),
    # A u8 struct field scrutinee, as sage's `lexer_scan_punct(lex, c)` reads c.
    "field_scrutinee": ("struct T\n    c: u8\n"
                        "fn g(t: T) -> i32\n    match t.c\n"
                        "        '(' => 1\n        _ => 0\n"
                        "fn main() -> i32\n    let a = T { c: 40 }\n"
                        "    let b = T { c: 41 }\n"
                        "    g(a) * 10 + g(b) - 10\n", 0),
}

# name -> (source, line, col, message)
REFUSED = {
    # Only a u8 takes one: a char pattern on a wider integer is an error at it.
    "char_on_an_i32": ("fn f(n: i32) -> i64\n    match n\n        '(' => 1\n"
                       "        _ => 2\n" + _MAIN, 3, 9, _CHAR_NEEDS_U8),
    "char_on_an_i64": ("fn f(n: i64) -> i64\n    match n\n        '(' => 1\n"
                       "        _ => 2\n" + _MAIN, 3, 9, _CHAR_NEEDS_U8),
    "char_on_a_u16": ("fn f(n: u16) -> i64\n    match n\n        '(' => 1\n"
                      "        _ => 2\n" + _MAIN, 3, 9, _CHAR_NEEDS_U8),
    # An unsuffixed integer literal scrutinee is i64, not u8.
    "char_on_an_integer_literal": ("fn main() -> i32\n    match 2\n        '(' => 1\n"
                                   "        _ => 2\n", 3, 9, _CHAR_NEEDS_U8),
    "char_on_a_bool": ("fn f(b: bool) -> i64\n    match b\n        '(' => 1\n"
                       "        _ => 2\n" + _MAIN, 3, 9, _CHAR_NEEDS_U8),
    "char_on_a_strview": ("fn f(s: StrView) -> i64\n    match s\n        '(' => 1\n"
                          "        _ => 2\n" + _MAIN, 3, 9, _CHAR_NEEDS_U8),
    "char_on_a_cstr": ("fn f(p: *u8) -> i64\n    match p\n        '(' => 1\n"
                       "        _ => 2\n" + _MAIN, 3, 9, _CHAR_NEEDS_U8),
    "char_on_an_enum": (_C + "fn f(c: C) -> i64\n    match c\n        '(' => 1\n"
                        "        _ => 2\n" + _MAIN, 6, 9, _CHAR_NEEDS_U8),
    # A char pattern is an integer literal pattern: a repeat is unreachable.
    "repeated_char": (_u8_fn("    match c\n        '(' => 1\n        '(' => 2\n"
                             "        _ => 3\n") + _MAIN, 4, 9, _unreachable(3)),
    "char_after_integer": (_u8_fn("    match c\n        40 => 1\n        '(' => 2\n"
                                  "        _ => 3\n") + _MAIN, 4, 9, _unreachable(3)),
    "integer_after_char": (_u8_fn("    match c\n        '(' => 1\n        40 => 2\n"
                                  "        _ => 3\n") + _MAIN, 4, 9, _unreachable(3)),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_char_match_takes_the_arm_that_equals(request, tmp_path, compiler, name):
    _assert_runs(request, compiler, tmp_path, name, RUNS[name])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_char_match_refuses_at_the_pattern(request, tmp_path, compiler, name):
    source, line, col, message = REFUSED[name]
    proc, ll = _compile(request, compiler, tmp_path, source, {})
    _assert_error(proc, ll, compiler, name, line, col, message)
