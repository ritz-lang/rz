"""An integer literal takes the other operand's type (LARB R21, AGAST #3112).

    fn f(m: u32) -> i64
        var n = m + 1          # a u32: `+ 1` wraps as `+ o` does, `@&n` is an `@&u32`

In a binary arithmetic or bitwise operation an untyped integer literal is the
other operand's type, as it would be in a slot (R1's first exception). Two
literals are an `i64`. A literal that doesn't fit the other operand's type is an
error, as it is in a slot. A shift's count has no say (LANGUAGE_SPEC §7.4), so
the `1` in `1 << n` is an `i64`.

Before, ritz0's checker typed `m + 1` as a u32 while its emitter added in i64 and
gave `n` an i64 slot, and ritz1 followed the emitter: `m + 1` and `m + o` (with
`o: u32 = 1`) gave different answers. Each row is one row of R21's table
(projects/larb/review/4/rulings-2026-11.md), on all three compilers.

Overflow itself isn't this rule's business (#3197): `+ - *` wrap, silently.
Except in a WIDER integer slot, where the operation runs at the slot's type
(AGAST #3225, test_wider_slot_widens.py): `let w: i64 = m + 1` doesn't wrap.
"""

import pytest

from ref_rules import REF_TO_OTHER_TYPE
from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

MAX = "4294967295"

# name -> (program, exit code). Each `main` returns 3 when the row holds, unless
# the row's answer is a value of its own.
RUNS = {
    # `m + 1` wraps, as a u32 does.
    "wraps": (f"fn f(m: u32) -> i32\n    var n = m + 1\n    if n == 0\n        return 3\n    return 4\n\n"
              f"pub fn main() -> i32\n    f({MAX})\n", 3),
    # The literal `1` and a u32 named `o` holding 1 give the same answer.
    "literal_or_name": (f"fn f(m: u32, o: u32) -> i32\n    let a = m + 1\n    let b = m + o\n    if a == b\n        return 3\n"
                        f"    return 4\n\npub fn main() -> i32\n    f({MAX}, 1)\n", 3),
    # In an operand, not only a local: `m + 1 > m` is false at the top.
    "compared": (f"fn f(m: u32) -> i32\n    if m + 1 > m\n        return 4\n    return 3\n\n"
                 f"pub fn main() -> i32\n    f({MAX})\n", 3),
    # Unsigned subtraction below 0 is a big u32, never negative.
    "unsigned_minus": ("fn f(m: u32) -> i32\n    var n = m - 2\n    if n < 0\n        return 4\n"
                       f"    if n == {MAX}\n        return 3\n    return 5\n\npub fn main() -> i32\n    f(1)\n", 3),
    # An i8 wraps to -128.
    "signed_wraps": ("fn f(k: i8) -> i32\n    let c = k + 1\n    if c < 0\n        return 3\n    return 4\n\n"
                     "pub fn main() -> i32\n    f(127)\n", 3),
    # 200 * 2 is 144 in a u8 (exit codes are mod 256, so it's compared), and a
    # literal on the left is the same.
    "u8_multiply": ("fn f(x: u8) -> i32\n    let y = x * 2\n    if y == 144\n        return 3\n    return 4\n\n"
                    "pub fn main() -> i32\n    f(200)\n", 3),
    "literal_left": ("fn f(x: u8) -> i32\n    let y = 2 * x\n    if y == 144\n        return 3\n    return 4\n\n"
                     "pub fn main() -> i32\n    f(200)\n", 3),
    # `~x + 1` on a u8 of 200 is 56, read at the u8's width.
    "bitwise": ("fn f(x: u8) -> i32\n    if ~x + 1 == 56\n        return 3\n    return 4\n\n"
                "pub fn main() -> i32\n    f(200)\n", 3),
    # `var n = m + 1` is a u32 slot, so an `@&u32` of it holds the whole value.
    "u32_slot": ("fn bump(p: @&u32)\n    *p = *p + 2\n\nfn f(m: u32) -> i32\n    var n = m + 1\n    bump(@&n)\n"
                 "    if n == 3\n        return 3\n    return 4\n\npub fn main() -> i32\n    f(0)\n", 3),
    # A u32 sum widened by `as` is zero-extended: 201, not -55.
    "cast_zero_extends": ("fn f(x: u8) -> i32\n    if (x + 1) as i64 == 201\n        return 3\n    return 4\n\n"
                          "pub fn main() -> i32\n    f(200)\n", 3),
    # In a wider slot the sum runs at the slot's type, so it doesn't wrap
    # (AGAST #3225, test_wider_slot_widens.py); `m + o` likewise.
    "into_i64": (f"fn f(m: u32) -> i32\n    let w: i64 = m + 1\n    if w == 4294967296\n        return 3\n    return 4\n\n"
                 f"pub fn main() -> i32\n    f({MAX})\n", 3),
    # Two literals are an i64.
    "two_literals": ("pub fn main() -> i32\n    let z = 4294967295 + 1\n    if z == 4294967296\n        return 3\n"
                     "    return 4\n", 3),
    # A shift's count has no say: `1 << n` is an i64.
    "shift_count": ("fn f(n: u32) -> i32\n    let b = 1 << n\n    if b == 1099511627776\n        return 3\n    return 4\n\n"
                    "pub fn main() -> i32\n    f(40)\n", 3),
    # `a << 4` is a u8, so its high nibble is gone before `>> 4` (§7.4).
    "narrow_shift": ("fn f(a: u8) -> i32\n    ((a << 4) >> 4) as i32\n\npub fn main() -> i32\n    f(248)\n", 8),
    # An i64 operand is unchanged: the control.
    "i64_control": ("fn f(n: i64) -> i32\n    if n + 1 == 4294967296\n        return 3\n    return 4\n\n"
                    f"pub fn main() -> i32\n    f({MAX})\n", 3),
}

@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_a_literal_takes_the_other_operands_type(tmp_path, compiler, name):
    src, want = RUNS[name]
    assert _run(compiler, tmp_path, name, src) == want


DOES_NOT_FIT = "`{v}` does not fit in `{t}`"

# `^` marks where the error lands.
REFUSED = {
    # `var n = m + 1` is a u32, so an `@&i64` of it is a reference to another type.
    "i64_ref": ("fn f(m: u32) -> i64\n    var n = m + 1\n    let p: @&i64 = ^@&n\n    *p\n\n"
                "pub fn main() -> i32\n    0\n", REF_TO_OTHER_TYPE),
    "too_big": ("fn f(x: u8) -> i32\n    let y = x + ^300\n    y as i32\n\npub fn main() -> i32\n    0\n",
                DOES_NOT_FIT.format(v=300, t="u8")),
    "too_big_left": ("fn f(x: u8) -> i32\n    let y = ^300 + x\n    y as i32\n\npub fn main() -> i32\n    0\n",
                     DOES_NOT_FIT.format(v=300, t="u8")),
    "negative_unsigned": ("fn f(m: u32) -> u32\n    m & ^-1\n\npub fn main() -> i32\n    0\n",
                          DOES_NOT_FIT.format(v=-1, t="u32")),
    "too_big_i32": ("fn f(h: i32) -> i32\n    h | ^4294967295\n\npub fn main() -> i32\n    0\n",
                    DOES_NOT_FIT.format(v=4294967295, t="i32")),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_a_literal_that_doesnt_fit_the_other_operand_is_refused(tmp_path, compiler, name):
    src, message = REFUSED[name]
    _assert_refused(compiler, tmp_path, name, src, message)
