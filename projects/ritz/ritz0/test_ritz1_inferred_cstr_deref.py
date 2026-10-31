"""Regression tests for AGAST #1976: a local whose type is inferred from a
c-string literal must be a `*u8`, exactly like the annotated form.

    let s = c"a-b"
    if *(s + 1) == 45       # ritz1: false (FAIL); ritz0: true

ROOT CAUSE: ritz1's emit_var_decl had no inference arm for EXPR_CSTRING_LIT,
so `let s = c"..."` kept the parser default TYPE_I64 with no pointee.
`*(s + 1)` then did `load i64` -- 8 bytes starting at '-' -- and the compare
saw "-b\\0" plus whatever followed in .rodata.  `*(s + 1) as i32` hid the bug
because the trunc kept only the low byte.  `let s: *u8 = c"..."` was right.

The fix narrows the local to TYPE_PTR with pointee TYPE_U8 (the same shape
the EXPR_CAST arm gives `let p = raw as *u8`), so loads are i8, zero-extended.

Each program returns 42 when correct and a distinct small code naming the
failed check otherwise.  ritz0 is the oracle.  The high-bit case (0xC3, the
first byte of UTF-8 "é") catches a sign-extending load: as i8 it would be -61.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

pytestmark = pytest.mark.integration

EXPECTED = 42

PROGRAMS = {
    # --- the ticket repros ---------------------------------------------------
    "ticket_inferred_eq": """\
pub fn main() -> i32
    let s = c"a-b"
    if *(s + 1) == 45
        return 42
    1
""",
    "ticket_typed_eq": """\
pub fn main() -> i32
    let s: *u8 = c"a-b"
    if *(s + 1) == 45
        return 42
    1
""",
    "ticket_inferred_value": """\
pub fn main() -> i32
    let s = c"a-b"
    if *(s + 1) as i32 != 45
        return 1
    42
""",
    # --- other comparisons ---------------------------------------------------
    "inferred_eq_char_lit": """\
pub fn main() -> i32
    let s = c"a-b"
    if *(s + 1) == '-'
        return 42
    1
""",
    "inferred_ne": """\
pub fn main() -> i32
    let s = c"a-b"
    if *(s + 1) != 45
        return 1
    if *s != 97
        return 2
    42
""",
    "inferred_lt_gt": """\
pub fn main() -> i32
    let s = c"a-b"
    if not (*(s + 1) < 46)
        return 1
    if not (*(s + 1) > 44)
        return 2
    if *(s + 2) < 98
        return 3
    if *(s + 2) > 98
        return 4
    42
""",
    "inferred_index": """\
pub fn main() -> i32
    let s = c"a-b"
    if s[1] != 45
        return 1
    if s[2] != 'b'
        return 2
    42
""",
    "inferred_var": """\
pub fn main() -> i32
    var s = c"xy-"
    if *(s + 2) != 45
        return 1
    s = s + 1
    if *s != 'y'
        return 2
    42
""",
    "inferred_nul_terminator": """\
pub fn main() -> i32
    let s = c"ab"
    if *(s + 2) != 0
        return 1
    42
""",
    # --- high-bit byte: must be zero-extended (195), not -61 ------------------
    "inferred_high_bit_eq": """\
pub fn main() -> i32
    let s = c"aé"
    if *(s + 1) != 195
        return 1
    if *(s + 2) != 169
        return 2
    42
""",
    "inferred_high_bit_gt": """\
pub fn main() -> i32
    let s = c"aé"
    if not (*(s + 1) > 127)
        return 1
    if *(s + 1) < 0
        return 2
    42
""",
    "inferred_high_bit_value": """\
pub fn main() -> i32
    let s = c"aé"
    let v: i32 = *(s + 1) as i32
    if v != 195
        return 1
    42
""",
    "typed_high_bit_eq": """\
pub fn main() -> i32
    let s: *u8 = c"aé"
    if *(s + 1) != 195
        return 1
    42
""",
    # --- the inferred local flows through a *u8 parameter ---------------------
    "inferred_passed_to_param": """\
fn second(p: *u8) -> u8
    *(p + 1)

pub fn main() -> i32
    let s = c"a-b"
    if second(s) != 45
        return 1
    42
""",
}


@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """ritz0 gets every case right; if it doesn't, the case is wrong."""
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_inferred_cstr_deref(ritz1_bin, tmp_path, name):
    """ritz1 must agree with ritz0 for an inferred `let s = c"..."`."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
