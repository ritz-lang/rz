"""Regression tests for AGAST #1602: int→int `as` casts under ritz1.

ritz1 keeps every integer in an i64 register, with narrow values held
sign- or zero-extended per their type. Its EXPR_CAST lowering treated
int→int as a pass-through, so `0xffffffff as i32` stayed i64 4294967295
instead of -1 and compared wrong against a sext'd i32 load (test_avx2's
rotl/xor checks). A narrowing cast must wrap to the target width and
re-extend by the TARGET's signedness, matching ritz0.

Each program returns 42 when correct and a distinct small code naming the
failed check otherwise. ritz0 is the oracle; casts are applied to runtime
values (params) as well as literals so a constant-folded lowering cannot
pass.
"""

import pytest

from test_ritz1_bool_fields import EXPECTED, _run, ritz1_bin  # noqa: F401

PROGRAMS = {
    # The ticket repro: a wrapped literal vs a sext'd i32 load.
    "i32_literal_vs_load": """\
pub fn main() -> i32
    var arr: [4]i32
    arr[0] = -1
    let a: i32 = arr[0]
    if a != 0xffffffff as i32
        return 1
    if 0x95511559 as i32 >= 0
        return 2
    let w: i64 = 0x95511559 as i32 as i64
    if w != -1789848231
        return 3
    return 42
""",
    # Narrowing to every signed width, from a runtime i64.
    "signed_narrow": """\
fn to_i32(x: i64) -> i64
    x as i32 as i64

fn to_i16(x: i64) -> i64
    x as i16 as i64

fn to_i8(x: i64) -> i64
    x as i8 as i64

pub fn main() -> i32
    if to_i32(0xffffffff) != -1
        return 1
    if to_i32(0x180000000) != -2147483648
        return 2
    if to_i32(0x7fffffff) != 2147483647
        return 3
    if to_i16(0xffff) != -1
        return 4
    if to_i16(0x18000) != -32768
        return 5
    if to_i8(0xff) != -1
        return 6
    if to_i8(0x17f) != 127
        return 7
    if to_i8(-129) != 127
        return 8
    return 42
""",
    # Narrowing to every unsigned width: wrap, then zero-extend.
    "unsigned_narrow": """\
fn to_u32(x: i64) -> i64
    x as u32 as i64

fn to_u16(x: i64) -> i64
    x as u16 as i64

fn to_u8(x: i64) -> i64
    x as u8 as i64

pub fn main() -> i32
    if to_u32(-1) != 4294967295
        return 1
    if to_u32(0x1fffffffe) != 4294967294
        return 2
    if to_u16(-1) != 65535
        return 3
    if to_u16(0x12345) != 0x2345
        return 4
    if to_u8(-1) != 255
        return 5
    if to_u8(0x1ab) != 0xab
        return 6
    return 42
""",
    # Same-width sign flips and widening keep the source value's meaning.
    "sign_change_and_widen": """\
fn u2i(x: u32) -> i32
    x as i32

fn i2u(x: i32) -> u32
    x as u32

fn b2i(x: u8) -> i8
    x as i8

pub fn main() -> i32
    let big: u32 = 0xfffffffe
    if u2i(big) != -2
        return 1
    let neg: i32 = -2
    let u: u32 = i2u(neg)
    if u as i64 != 4294967294
        return 2
    let hb: u8 = 200
    if b2i(hb) != -56
        return 3
    let n8: i8 = -5
    if n8 as i64 != -5
        return 4
    # Widening zexts if EITHER side is unsigned (ritz0's rule, not Rust's).
    if n8 as u64 as i64 != 251
        return 5
    if n8 as u32 as i64 != 251
        return 8
    if n8 as i32 as i64 != -5
        return 9
    let small: u16 = 65535
    if small as i64 != 65535
        return 6
    if small as i32 != 65535
        return 7
    return 42
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_int_cast(ritz1_bin, tmp_path, name):  # noqa: F811
    """ritz1 lowered int→int `as` as a no-op (#1602)."""
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
