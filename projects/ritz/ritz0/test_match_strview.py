#!/usr/bin/env python3
"""String literal patterns in `match` (LANGUAGE_SPEC §8.2, AGAST #1876).

`match name` with `"html" => ...` arms compares a StrView scrutinee with each
literal, byte for byte: the length first, then the bytes. Only a StrView takes
one; a `*u8` or a `String` is converted by the caller (`strview_from_cstr`,
`string_as_view`), so a string arm on anything else is an error at the arm.
Like an integer, a StrView needs a catch-all, and a repeated literal is an arm
no value can reach.

Every row goes through ritz0, ritz1 and ritz1_selfhosted, which must agree.
The run rows are what makes a compiler that refuses everything fail: each is
built, linked and run, and each arm a row's `main` reaches is checked by its
exit code.
"""

import pytest
from test_match_exhaustive import (
    _CATCH_ALL,
    _LITERAL_NEEDS_INTEGER,
    _MAIN,
    _VARIANT_NEEDS_ENUM,
    COMPILERS,
    _assert_error,
    _assert_runs,
    _compile,
    _unreachable,
)

_STR_NEEDS_STRVIEW = "a string pattern needs a StrView scrutinee"
_C = "enum C\n    R\n    G\n"


def _str_fn(body, ret="i64"):
    return f"fn f(s: StrView) -> {ret}\n" + body


# name -> (source, exit code). `main` returns 0 only when every call took its
# arm; otherwise the number of the first call that went wrong.
RUNS = {
    # The acceptance shape: the spec's own example, three-way.
    "picks_each_arm": (_str_fn("    match s\n        \"html\" => 1\n        \"body\" => 2\n"
                               "        _ => 3\n")
                       + "fn main() -> i32\n    (f(\"html\") * 100 + f(\"body\") * 10 + f(\"head\")) as i32\n",
                       123),
    # Same length, other bytes, first or last; a prefix; the empty string; an
    # escape, which compares as its one byte.
    "length_then_bytes": (_str_fn("    match s\n        \"ab\" => 1\n        \"ac\" => 2\n"
                                  "        \"a\" => 3\n        \"\" => 4\n        \"\\n\" => 5\n"
                                  "        _ => 6\n")
                          + "fn main() -> i32\n"
                            "    if f(\"ab\") != 1\n        return 1\n"
                            "    if f(\"ac\") != 2\n        return 2\n"
                            "    if f(\"a\") != 3\n        return 3\n"
                            "    if f(\"\") != 4\n        return 4\n"
                            "    if f(\"\\n\") != 5\n        return 5\n"
                            "    if f(\"abc\") != 6\n        return 6\n"
                            "    if f(\"b\") != 6\n        return 7\n"
                            # Unequal before the last byte: each byte decides.
                            "    if f(\"cb\") != 6\n        return 8\n"
                            "    0\n", 0),
    # A catch-all name binds the StrView itself.
    "binding_is_the_strview": (_str_fn("    match s\n        \"x\" => 0\n        other => other.len\n")
                               + "fn main() -> i32\n    f(\"wxyz\") as i32\n", 4),
    # A field scrutinee, and a statement match whose arms assign.
    "field_and_statement": ("struct T\n    name: StrView\n"
                            "fn g(t: T) -> i32\n    var r: i32 = 0\n    match t.name\n"
                            "        \"div\" => r = 7\n        _ => r = 9\n    r\n"
                            "fn main() -> i32\n    let a = T { name: \"div\" }\n"
                            "    let b = T { name: \"dix\" }\n    g(a) * 10 + g(b)\n", 79),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_string_match_takes_the_arm_that_equals(request, tmp_path, compiler, name):
    _assert_runs(request, compiler, tmp_path, name, RUNS[name])


# name -> (source, line, col, message)
REFUSED = {
    "no_catch_all": (_str_fn("    match s\n        \"a\" => 1\n        \"b\" => 2\n") + _MAIN,
                     2, 5, f"non-exhaustive match: missing {_CATCH_ALL}"),
    "repeated_literal": (_str_fn("    match s\n        \"a\" => 1\n        \"b\" => 2\n"
                                 "        \"a\" => 3\n        _ => 4\n") + _MAIN,
                         5, 9, _unreachable(3)),
    # Only a StrView takes a string arm.
    "string_on_an_integer": ("fn f(n: i64) -> i64\n    match n\n        \"a\" => 1\n"
                             "        _ => 2\n" + _MAIN, 3, 9, _STR_NEEDS_STRVIEW),
    "string_on_a_cstr": ("fn f(p: *u8) -> i64\n    match p\n        \"a\" => 1\n"
                         "        _ => 2\n" + _MAIN, 3, 9, _STR_NEEDS_STRVIEW),
    "string_on_an_enum": (_C + "fn f(c: C) -> i64\n    match c\n        \"hi\" => 1\n"
                          "        _ => 2\n" + _MAIN, 6, 9, _STR_NEEDS_STRVIEW),
    # ... and a StrView takes no other literal or variant.
    "integer_on_a_strview": (_str_fn("    match s\n        \"a\" => 1\n        5 => 2\n"
                                     "        _ => 3\n") + _MAIN, 4, 9, _LITERAL_NEEDS_INTEGER),
    "bool_on_a_strview": (_str_fn("    match s\n        true => 1\n        _ => 2\n") + _MAIN,
                          3, 9, "a `true` or `false` pattern needs a bool scrutinee"),
    "variant_on_a_strview": (_str_fn("    match s\n        Some(v) => 1\n        _ => 2\n") + _MAIN,
                             3, 9, _VARIANT_NEEDS_ENUM),
    # An integer const compares only an integer; on a StrView its name binds,
    # and a binding can't take a const's name (§4.3).
    "const_name_on_a_strview": ("const K: i64 = 1\n" + _str_fn(
        "    match s\n        \"a\" => 1\n        K => 2\n") + _MAIN, 5, 9,
        "a local can't take the name of a const: 'K' — rename the local"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_string_match_refuses_at_the_arm(request, tmp_path, compiler, name):
    source, line, col, message = REFUSED[name]
    proc, ll = _compile(request, compiler, tmp_path, source, {})
    _assert_error(proc, ll, compiler, name, line, col, message)
