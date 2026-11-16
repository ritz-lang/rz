"""Regression tests for AGAST #3651: ritz1 must lower the pointer, float and
nested-struct fields of a struct element of a module const array, and refuse
any other field with a located error.

emit_const_field_value wrote every field that wasn't an integer or a StrView
as `<emit_llvm_type> <int_val>`.  So `const T: [1]P = [P { p: null, f: 1.5 }]`
became `%P { i64 0, double 0 }`: an `i64` in a `ptr` slot, and 0 for 1.5,
because a float literal's int_val is 0.  A string in a `*u8` field, an enum
field and a nested struct literal were all written as a silent `i64 0` too.

The supported set:
  - `*u8` field: `null`, `"..."` or `c"..."`; any other pointer field: `null`;
  - f64 / f32 field: a float literal, or an integer literal (LANGUAGE_SPEC
    7.5's literal exemption), or a negated one.  f32 is rounded the way
    ritz1 rounds it at run time (decimal -> double -> float), so an f32 literal
    is refused when it has more digits than ritz1 can round exactly;
  - struct field: a nested struct literal, recursively (or `"..."` into a
    StrView, as before).
Everything else is an error at the field's value naming the const, element and
field (a dotted path inside a nested literal), worded like #1569's.

Every program exits 3 when the fields hold the right values.  Pointer and f32
fields are read through a typed local: a direct `*(T[0].s + 1)` or f32
`T[0].a != x` read is mistyped by ritz1 (AGAST #3671).  ritz0 refuses
lowers the same set and raises the same located errors (AGAST #3670), but
rounds every f32 literal exactly, so it has no f32_too_precise rows.
"""

import pytest
from test_ref_into_value import _assert_refused, _ids, _run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The ticket's repro: with the bug p is `i64 0` (clang rejects the IR) and f is 0.
REPRO = """\
struct P
    p: *u8
    f: f64
    x: i32

const T: [1]P = [P { p: null, f: 1.5, x: -5 }]

pub fn main() -> i32
    if T[0].p != null
        return 10
    if T[0].f != 1.5
        return 11
    return T[0].x + 8
"""

# A string in a `*u8` field points at its NUL-terminated bytes, `"..."` and
# `c"..."` alike, beside a null and a typed-pointer null.
POINTERS = """\
struct P
    s: *u8
    c: *u8
    n: *u8
    q: *i64

const T: [2]P = [P { s: "hey", c: c"cs", n: null, q: null }, P { s: "", c: c"x\\ty", n: "z", q: null }]

pub fn main() -> i32
    let s0: *u8 = T[0].s
    let c0: *u8 = T[0].c
    let s1: *u8 = T[1].s
    let c1: *u8 = T[1].c
    let n1: *u8 = T[1].n
    if *(s0 + 1) != 'e' or *(s0 + 3) != 0
        return 10
    if *(c0 + 0) != 'c' or *(c0 + 2) != 0
        return 11
    if T[0].n != null or T[0].q != null or T[1].q != null
        return 12
    if *(s1 + 0) != 0
        return 13
    if *(c1 + 1) != 9 or *(c1 + 3) != 0
        return 14
    if *(n1 + 0) != 'z'
        return 15
    return 3
"""

# f64 fields, exact and inexact, negated, and zero of either sign; each equals
# the same literal read at run time.
F64 = """\
struct P
    a: f64
    b: f64
    c: f64
    d: f64

const T: [2]P = [P { a: 1.5, b: -2.25, c: 0.1, d: 0.0 }, P { a: -0.0, b: 3.14159265358979, c: -0.3, d: 123456789.125 }]

pub fn main() -> i32
    if T[0].a != 1.5 or T[0].b != -2.25 or T[0].c != 0.1 or T[0].d != 0.0
        return 10
    if T[1].a != 0.0
        return 11
    if T[1].b != 3.14159265358979 or T[1].c != -0.3 or T[1].d != 123456789.125
        return 12
    return 3
"""

# f32 fields hold what a run-time f32 of the same literal holds: 1.3 and -0.1
# round, 2.5 is exact.
F32 = """\
struct P
    a: f32
    b: f32
    c: f32
    w: f64

const T: [1]P = [P { a: 1.3, b: -0.1, c: 2.5, w: 0.7 }]

pub fn main() -> i32
    let a: f32 = 1.3
    let b: f32 = -0.1
    let c: f32 = 2.5
    let ta: f32 = T[0].a
    let tb: f32 = T[0].b
    let tc: f32 = T[0].c
    if ta != a
        return 10
    if tb != b
        return 11
    if tc != c
        return 12
    if T[0].w != 0.7
        return 13
    return 3
"""

# An integer literal converts into a float field (LANGUAGE_SPEC 7.5), as it
# does into a run-time float slot; 16777217 is the first integer f32 rounds.
INT_INTO_FLOAT = """\
struct P
    a: f64
    b: f64
    c: f32
    d: f32

const T: [1]P = [P { a: 2, b: -3, c: 16777217, d: -7 }]

pub fn main() -> i32
    let c: f32 = 16777217
    let d: f32 = -7
    let tc: f32 = T[0].c
    let td: f32 = T[0].d
    if T[0].a != 2.0 or T[0].b != -3.0
        return 10
    if tc != c or td != d
        return 11
    return 3
"""

# An integer converts straight to f32, rounded once, as `sitofp` does.
# 2^54 + 2^30 + 1 is 2^54 + 2^31 in f32, but 2^54 by way of a double: the
# double is 2^54 + 2^30, a tie that rounds to even.
INT_INTO_F32_ONCE = """\
struct P
    c: f32
    d: f32

const T: [1]P = [P { c: 18014399583223809, d: -18014399583223809 }]

pub fn main() -> i32
    let tc: f32 = T[0].c
    let td: f32 = T[0].d
    if tc != 18014400657965056.0
        return 10
    if td != -18014400657965056.0
        return 11
    return 3
"""

# ritz0 rounds an f32 literal exactly, past ritz1's fast-path limit (the
# REFUSED f32_too_many_* rows), to what a run-time f32 of it holds.
F32_PRECISE = """\
struct P
    a: f32
    b: f32

const T: [1]P = [P { a: 1234567890.1234567, b: -0.00000000000000000000001 }]

pub fn main() -> i32
    let a: f32 = 1234567890.1234567
    let b: f32 = -0.00000000000000000000001
    let ta: f32 = T[0].a
    let tb: f32 = T[0].b
    if ta != a
        return 10
    if tb != b or tb == 0.0
        return 11
    return 3
"""

# A nested struct literal, two levels deep, holding integers, a folded const
# expression, a StrView, a pointer and a float.
NESTED = """\
struct Leaf
    v: i16
    name: StrView

struct In
    a: i32
    leaf: Leaf
    p: *u8
    f: f64

struct P
    x: i32
    inn: In

const K: i32 = 6

const T: [2]P = [P { x: 1, inn: In { a: -4, leaf: Leaf { v: K * 2, name: "ab" }, p: "pq", f: -0.5 } }, P { x: 2, inn: In { a: 7, leaf: Leaf { v: -1, name: "" }, p: null, f: 2.0 } }]

pub fn main() -> i32
    if T[0].inn.a != -4 or T[1].inn.a != 7
        return 10
    if T[0].inn.leaf.v != 12 or T[1].inn.leaf.v != -1
        return 11
    let name: StrView = T[0].inn.leaf.name
    if name.len != 2 or *(name.ptr + 1) != 'b'
        return 12
    if T[1].inn.leaf.name.len != 0
        return 13
    let p0: *u8 = T[0].inn.p
    if *(p0 + 1) != 'q' or T[1].inn.p != null
        return 14
    if T[0].inn.f != -0.5 or T[1].inn.f != 2.0
        return 15
    return T[0].x + T[1].x
"""

FORMS = {
    "repro": REPRO,
    "pointers": POINTERS,
    "f64": F64,
    "f32": F32,
    "int_into_float": INT_INTO_FLOAT,
    "nested": NESTED,
    "int_into_f32_once": INT_INTO_F32_ONCE,
    "f32_precise": F32_PRECISE,
}

# ritz1 refuses these literals (see REFUSED's f32_too_many_* rows).
RITZ0_ONLY = {"f32_precise"}


def _params(table, ritz1_only=(), ritz0_only=()):
    for name in _ids(table):
        for compiler in COMPILERS:
            skip = ritz1_only if compiler == "ritz0" else ritz0_only
            if name in skip:
                continue
            yield pytest.param(name, compiler)


@pytest.mark.parametrize("name,compiler", list(_params(FORMS, ritz0_only=RITZ0_ONLY)))
def test_const_struct_array_field_kinds_lower(tmp_path, compiler, name):
    rc = _run(compiler, tmp_path, name, FORMS[name])
    assert rc == 3, f"{compiler} build of {name} exited {rc}, expected 3"


# --- every other field is a located error -----------------------------------
# `^` marks the field's value, where the error is reported.

DECLS = """\
enum Color
    Red
    Blue

struct In
    a: i32

const K: i32 = 1

const PI: f64 = 3.25

fn mk() -> In
    return In { a: 1 }

fn name() -> *u8
    return c"n"

"""

F32_TOO_PRECISE = ("field 'f' is an f32 literal with more digits than ritz1 rounds exactly "
                   "(at most 15 significant, 22 after the point)")

REFUSED = {
    # A pointer field takes only null or a string.
    "ptr_int": ("struct P\n    p: *u8\n\nconst T: [1]P = [P { p: ^K }]\n",
                "field 'p' is not a constant pointer (null or a string literal)"),
    "ptr_call": ("struct P\n    p: *u8\n\nconst T: [1]P = [P { p: ^name() }]\n",
                 "field 'p' is not a constant pointer (null or a string literal)"),
    "ptr_str_not_u8": ("struct P\n    p: *i64\n\nconst T: [1]P = [P { p: ^\"s\" }]\n",
                       "field 'p' is not a constant pointer (null or a string literal)"),
    # A float field takes only a float or integer literal, or a negated one.
    # A const name isn't a literal: §7.5 wants `as` for a non-literal.
    "float_int_const": ("struct P\n    f: f64\n\nconst T: [1]P = [P { f: ^K }]\n",
                        "field 'f' is not a float literal or an integer literal"),
    "float_const": ("struct P\n    f: f64\n\nconst T: [2]P = [P { f: 1.0 }, P { f: ^PI }]\n",
                    "field 'f' is not a float literal or an integer literal"),
    "float_null": ("struct P\n    f: f32\n\nconst T: [1]P = [P { f: ^null }]\n",
                   "field 'f' is not a float literal or an integer literal"),
    # An f32 literal outside the exact fast path: digits above 2^53, or more
    # than 22 after the point (10^23 isn't exact in a double).
    "f32_too_many_digits": ("struct P\n    f: f32\n\nconst T: [1]P = [P { f: ^1234567890.1234567 }]\n",
                            F32_TOO_PRECISE),
    "f32_too_many_decimals": ("struct P\n    f: f32\n\nconst T: [1]P = [P { f: ^-0.00000000000000000000001 }]\n",
                              F32_TOO_PRECISE),
    # A struct field takes only a struct literal (or a string, for a StrView).
    "struct_call": ("struct P\n    inn: In\n\nconst T: [1]P = [P { inn: ^mk() }]\n",
                    "field 'inn' is not a struct literal"),
    # A nested field is named by its dotted path.
    "nested_path": ("struct P\n    inn: In\n\nconst T: [1]P = [P { inn: In { a: ^mk() } }]\n",
                    "field 'inn.a' is not a constant integer expression"),
    # Enum and array fields aren't lowered yet (AGAST #3673).
    "enum": ("struct P\n    c: Color\n\nconst T: [1]P = [P { c: ^Color.Blue }]\n",
             "field 'c' has a type ritz1 can't lower in a const (integer, bool, float, pointer and struct fields are)"),
    "array": ("struct P\n    a: [2]i32\n\nconst T: [1]P = [P { a: ^[1, 2] }]\n",
              "field 'a' has a type ritz1 can't lower in a const (integer, bool, float, pointer and struct fields are)"),
}

# The element each row's bad field is in, when it isn't element 0.
REFUSED_ELEM = {"float_const": 1}

# ritz1's limit: ritz0 rounds every f32 literal exactly and lowers these (#3670).
RITZ1_ONLY = {"f32_too_many_digits", "f32_too_many_decimals"}


@pytest.mark.parametrize("name,compiler", list(_params(REFUSED, RITZ1_ONLY)))
def test_unsupported_const_field_is_a_located_error(tmp_path, compiler, name):
    body, why = REFUSED[name]
    src = DECLS + body + "\npub fn main() -> i32\n    return 3\n"
    elem = REFUSED_ELEM.get(name, 0)
    _assert_refused(compiler, tmp_path, name, src, f"const 'T' element {elem} {why}")
