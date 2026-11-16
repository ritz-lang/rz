"""Regression tests for AGAST #1569: ritz1 must fold each integer field of a
struct element of a module const array.  `const T: [1]P = [P { x: -5 }]` has to
become `[%P { i32 -5 }]`.

emit_const_field_value emitted each scalar field's raw `int_val`.  A `-5` is an
EXPR_UNARY(NEG) node whose own int_val is 0, so the field became 0; so did a
const name (`K`) and a const expression (`A * 4 - 1`).  This is the
struct-element sibling of #1557 (test_ritz1_const_array_fold.py).  Each integer
field now goes through const_fold_int; one that doesn't fold is an error at
the field's value, not a silent 0.

Every program exits 3 when the fields hold the right values, on all three
compilers.  ritz0 folds each integer field through its ConstEvaluator and
reports an unfoldable one with ritz1's wording (AGAST #3650).

AGAST #3669: a struct-typed field (`i: I { v: 3 }`) is a nested literal, not
`i64 0`; #3651's recursion in emit_const_field_value fixed it, and the nested
rows pin it, including a nested field holding a const expression.
"""

import pytest
from test_ref_into_value import _assert_refused, _ids, _run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The ticket's repro: -5 + 8 == 3.  With the bug T[0].x is 0 and it exits 8.
NEG_REPRO = """\
struct P
    x: i32

const T: [1]P = [P { x: -5 }]

pub fn main() -> i32
    return T[0].x + 8
"""

# A field naming an integer const, one declared before the array and one after
# it (still PENDING at parse time; emit-time folding resolves it).
CONST_NAME = """\
struct P
    x: i32
    y: i32

const K: i32 = -5

const T: [2]P = [P { x: K, y: 1 }, P { x: 2, y: L }]

const L: i32 = 7

pub fn main() -> i32
    if T[1].y != 7
        return 10
    if T[1].x != 2
        return 11
    return T[0].x + 8
"""

# Arithmetic const expressions, including the ones a raw int_val reads as 0,
# and a bool field folded from a comparison.
CONST_EXPR = """\
struct P
    x: i32
    y: i32
    ok: bool

const A: i32 = 2

const T: [2]P = [P { x: A * 4 - 1, y: -A, ok: A > 1 }, P { x: ~0, y: (A + 1) << 2, ok: !A }]

pub fn main() -> i32
    if T[0].x != 7
        return 10
    if T[0].y != -2
        return 11
    if T[1].x != -1
        return 12
    if T[1].y != 12
        return 13
    if T[0].ok != true or T[1].ok != false
        return 14
    return 3
"""

# Every integer width, a negative needing the high word, a bool, and a string
# field beside them: each field keeps its own value and slot.  `0xFFFF + 18`
# (wrapping to the u16 17) and
# `!0` are folded, not literal (AGAST #3650).
WIDTHS = """\
struct Q
    a: i8
    b: i64
    name: StrView
    c: u16
    d: bool

const T: [1]Q = [Q { a: -3, b: -8589934595, name: "hi", c: 0xFFFF + 18, d: !0 }]

pub fn main() -> i32
    if T[0].b != -8589934595
        return 10
    if T[0].c != 17
        return 11
    if T[0].d != true
        return 12
    if T[0].name.len != 2
        return 13
    return (T[0].a + 6) as i32
"""

# AGAST #3669: a struct-typed field of an element.  ritz1 emitted the nested
# literal as `i64 0`, which clang rejects.
NESTED = """\
struct I
    v: i32

struct P
    x: i32
    i: I

const T: [1]P = [P { x: 1, i: I { v: 3 } }]

pub fn main() -> i32
    if T[0].x != 1
        return 10
    return T[0].i.v
"""

# The nested struct's field is a const expression, and the struct nests two
# deep beside a scalar after it, so every field keeps its own slot.
NESTED_CONST_EXPR = """\
struct I
    v: i32

struct M
    i: I
    w: i64

struct P
    x: i32
    m: M
    z: i8

const A: i32 = 2

const T: [2]P = [P { x: 1, m: M { i: I { v: A + 1 }, w: -A }, z: 5 }, P { x: -A, m: M { i: I { v: A * 4 }, w: 9 }, z: -1 }]

pub fn main() -> i32
    if T[0].m.w != -2
        return 10
    if T[0].z != 5 or T[1].z != -1
        return 11
    if T[1].x != -2 or T[1].m.i.v != 8 or T[1].m.w != 9
        return 12
    if T[0].x != 1
        return 13
    return T[0].m.i.v
"""

FORMS = {
    "nested": NESTED,
    "neg_repro": NEG_REPRO,
    "widths": WIDTHS,
    "const_name": CONST_NAME,
    "const_expr": CONST_EXPR,
    "nested_const_expr": NESTED_CONST_EXPR,
}


@pytest.mark.parametrize("name", _ids(FORMS))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_const_struct_array_integer_fields_fold(tmp_path, compiler, name):
    rc = _run(compiler, tmp_path, name, FORMS[name])
    assert rc == 3, f"{compiler} build of {name} exited {rc}, expected 3"


# --- an integer field that doesn't fold is a located error ------------------
# `^` marks the field's value, where the error is reported.

UNFOLDABLE = {
    "call": """\
fn f() -> i32
    return 1

struct P
    x: i32
    y: i32

const T: [1]P = [P { x: 1, y: ^f() }]
""",
    "unknown_name": """\
struct P
    x: i32

const T: [2]P = [P { x: 1 }, P { x: ^NOPE + 1 }]
""",
}

UNFOLDABLE_FIELD = {"call": (0, "y"), "unknown_name": (1, "x")}


@pytest.mark.parametrize("name", _ids(UNFOLDABLE))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_unfoldable_integer_field_is_a_located_error(tmp_path, compiler, name):
    elem, field = UNFOLDABLE_FIELD[name]
    src = UNFOLDABLE[name] + "\npub fn main() -> i32\n    return 3\n"
    _assert_refused(
        compiler,
        tmp_path,
        name,
        src,
        f"const 'T' element {elem} field '{field}' is not a constant integer expression",
    )
