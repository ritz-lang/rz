"""AGAST #1866: a static lookup table is a `const` array literal (LANGUAGE_SPEC
§3.3 "Constant tables"), not an if-ladder.  ritz0, ritz1 and ritz1_selfhosted
must lower the same table forms and refuse the same elements, with the same
located message.

The forms a table takes:
  - `[N]S` of struct literals whose fields are integers, `"..."` into a
    `StrView` / `Span<u8>`, and so on (#1569, #3651 cover the field kinds);
  - `[N]StrView` of `"..."`;
  - `[N]*u8` of `"..."`, `c"..."` or `null`, as a list or a fill;
  - `[N]u32` / `[N]u64` of hex literals with the top bit set (SHA round K).

What was broken before #1866, one row each:
  - ptr_*: ritz1 lost the `*u8` of `T[i]`, so `*(T[i] + 1)` loaded 8 bytes
    and `for p in T` read an i64; ritz0 refused `c"..."` and `null` elements;
  - ptr_fill_*: neither compiler lowered a `*u8` fill;
  - strview_let, struct_lookup: ritz1 refused `let s = T[i]` on a const
    `[N]StrView` or `[N]S` ("a whole struct is not a value here").

Every program exits 3 when the table reads back right.
"""

import pytest
from test_ref_into_value import _assert_refused, _compile, _ids, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

FORMS = {
    # The status_reason shape: a code and its phrase, searched by a loop.
    "struct_lookup": """\
struct R
    code: i32
    reason: StrView

const T: [3]R = [R { code: 200, reason: "OK" }, R { code: 404, reason: "Not Found" }, R { code: 500, reason: "" }]

fn lookup(c: i32) -> StrView
    for r in T
        if r.code == c
            return r.reason
    "?"

pub fn main() -> i32
    if lookup(404).len != 9 or *(lookup(404).ptr + 4) != 'F'
        return 10
    if lookup(500).len != 0 or lookup(1).len != 1
        return 11
    var i: i32 = 2
    if T[i].code != 500
        return 12
    i = 1
    let r = T[i]
    if r.code != 404 or r.reason.len != 9
        return 13
    3
""",
    # The qpack/hpack shape: `Span<u8>` fields from `"..."`, indexed at run time.
    "struct_span_fields": """\
import ritzlib.span

struct E
    name: Span<u8>
    value: Span<u8>

const T: [2]E = [E { name: ":path", value: "/" }, E { name: "age", value: "" }]

pub fn main() -> i32
    var i: i32 = 1
    if T[i].name.len != 3 or *(T[i].name.ptr + 2) != 'e' or T[i].value.len != 0
        return 10
    if T[0].value.len != 1 or *T[0].value.ptr != '/'
        return 11
    3
""",
    "strview_let": """\
const T: [3]StrView = ["OK", "Not Found", ""]

pub fn main() -> i32
    var i: i64 = 1
    let s = T[i]
    if s.len != 9 or *(s.ptr + 4) != 'F'
        return 10
    let e = T[2]
    if e.len != 0
        return 11
    3
""",
    "ptr_index": """\
const T: [3]*u8 = [c"ab", "cd", null]

pub fn main() -> i32
    var i: i32 = 1
    if *(T[i] + 1) != 'd' or *(T[0] + 1) != 'b' or *(T[i] + 2) != 0
        return 10
    i = 2
    if T[i] != null
        return 11
    3
""",
    "ptr_for": """\
const T: [2]*u8 = [c"ab", "cd"]

pub fn main() -> i32
    var n: i32 = 0
    for p in T
        n = n + (*(p + 1) - 'a') as i32
    if n != 4
        return 10
    3
""",
    "ptr_fill_str": """\
const T: [2]*u8 = ["ab"; 2]

pub fn main() -> i32
    var i: i32 = 1
    if *(T[i] + 1) != 'b'
        return 10
    3
""",
    "ptr_fill_cstr": """\
const T: [2]*u8 = [c"ab"; 2]

pub fn main() -> i32
    var i: i32 = 1
    if *(T[i] + 1) != 'b' or *(T[0] + 2) != 0
        return 10
    3
""",
    "ptr_fill_null": """\
const T: [2]*u8 = [null; 2]

pub fn main() -> i32
    var i: i32 = 1
    if T[i] != null or T[0] != null
        return 10
    3
""",
    # AGAST #3949: ritz1 refused `KS[i]` of a `const [N]bool` ("a whole array
    # is not a value here"); `[N]u8` always indexed.  A list and a fill, read
    # into a `let`, as a condition and at a run-time index.
    "bool_elem": """\
const KS: [2]bool = [true, false]
const KF: [3]bool = [true; 3]

pub fn main() -> i32
    let b: bool = KS[1]
    if b
        return 10
    if not KS[0]
        return 11
    var i: i32 = 1
    if KS[i] or not KF[i]
        return 12
    let c = KS[0]
    if not c
        return 13
    3
""",
    # SHA-256 / SHA-512 round constants: hex with the top bit set.
    "wide_hex": """\
const K: [3]u32 = [0x428a2f98, 0xb5c0fbcf, 0xc67178f2]
const K5: [2]u64 = [0x428a2f98d728ae22, 0xb5c0fbcfec4d3b2f]

pub fn main() -> i32
    var i: i32 = 2
    if K[i] != 0xc67178f2 or K[1] >> 28 != 0xb
        return 10
    i = 1
    if K5[i] != 0xb5c0fbcfec4d3b2f or K5[i] >> 60 != 0xb
        return 11
    3
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", _ids(FORMS))
def test_const_table_reads_back(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, FORMS[name]) == 3


PTR_ELEM = "is not a string literal or null"

# `^` marks where the error is: the element that isn't a string or null.
REFUSED = {
    "ptr_int": ('const T: [2]*u8 = [c"A", ^5]\n', 1),
    # A pointer is `null`, never the integer 0 (§3.2).
    "ptr_zero": ('const T: [2]*u8 = [^0, "A"]\n', 0),
    "ptr_fill_int": ("const T: [2]*u8 = [^7; 2]\n", 0),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", _ids(REFUSED))
def test_ptr_table_element_is_a_string_or_null(tmp_path, compiler, name):
    decl, elem = REFUSED[name]
    src = decl + "\npub fn main() -> i32\n    3\n"
    _assert_refused(compiler, tmp_path, name, src, f"const 'T' element {elem} {PTR_ELEM}")


# AGAST #3946: a struct table can't be a fill (§3.3, "write its elements out").
# ritz0 called the struct literal "not a constant integer expression"; ritz1
# emitted no global, so `T[i].a` failed later as an unlocated "unhandled
# EXPR_MEMBER". Both now refuse it at the fill's value.
STRUCT_FILL = "const 'T': a struct table can't be a fill `[v; N]`: write its elements out"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_struct_table_is_not_a_fill(tmp_path, compiler):
    src = (
        "struct P\n    a: i32\n\n"
        "const T: [2]P = [^P { a: 1 }; 2]\n\n"
        "pub fn main() -> i32\n    var i: i32 = 1\n    T[i].a\n"
    )
    _assert_refused(compiler, tmp_path, "struct_fill", src, STRUCT_FILL)
    # One message: no unlocated cascade from the read `T[i].a`.
    comp, _, _ = _compile(compiler, tmp_path, "struct_fill_once", src.replace("^", ""))
    out = comp.stdout + comp.stderr
    assert out.count("error") <= 1 and "cannot emit" not in out, out
