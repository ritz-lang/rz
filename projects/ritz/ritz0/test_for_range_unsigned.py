#!/usr/bin/env python3
"""A `for` range over u64 bounds compares unsigned (AGAST #1636).

`for j in a..b` desugars to `while j < b` (`<=` for `a..=b`). All three
compilers compared signed whatever the bounds were, so with `big: u64 = 1 << 63`
`for j in 0..big` ran zero times: as an i64, `big` is negative. The loop's
compare now follows binary `<`'s rule (#2361): unsigned when a bound is a u64,
directly or through an operator expression. A signed range keeps its signed
compare, which is what lets `-3..2` cross 0.

The loop variable takes the same type (AGAST #3328): a u64 when the range
compares unsigned, so `j / 2`, `j % 3`, `j >> 62` and `j < 1` in the body are
unsigned for `j = 1 << 63`. They were sdiv, srem, ashr and slt on ritz0 and
ritz1. One rule decides both, so the compare and `j`'s type can't drift apart. A
signed range's `j` stays signed, even after a u64 loop over the same name.

`usize` is not here: whether it is unsigned is AGAST #2363's call, and until
then a usize range compares like a usize `<`, signed.

Each row is a fn returning 0 when its loop ran right; main exits with the
1-based index of the first wrong row.
"""

import textwrap

import pytest

from test_right_shift import _indent, _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

BIG = "let big: u64 = 9223372036854775808"  # 1 << 63


def _row(text):
    return textwrap.dedent(text).strip("\n")


# name -> body of `fn t() -> i64`: 0 when the loop ran right.
ROWS = {
    # The ticket: a top-bit end, stopped by `break` after 5 trips.
    "zero_to_big": _row(f"""
        {BIG}
        let a: u64 = 0
        var n: i64 = 0
        for j in a..big
            n = n + 1
            if n == 5
                break
        if n != 5
            return 1
        0
    """),
    "literal_zero_to_big": _row(f"""
        {BIG}
        var n: i64 = 0
        for j in 0..big
            n = n + 1
            if n == 5
                break
        if n != 5
            return 1
        0
    """),
    # Both bounds past 2^63: big - 3, big - 2, big - 1.
    "top_bit_exclusive": _row(f"""
        {BIG}
        let lo: u64 = big - 3
        var n: i64 = 0
        var last: u64 = 0
        for j in lo..big
            n = n + 1
            last = j
        if n != 3
            return 1
        if last != big - 1
            return 2
        0
    """),
    # ..= runs once more, ending on big itself.
    "top_bit_inclusive": _row(f"""
        {BIG}
        let lo: u64 = big - 3
        var n: i64 = 0
        var last: u64 = 0
        for j in lo..=big
            n = n + 1
            last = j
        if n != 4
            return 1
        if last != big
            return 2
        0
    """),
    # An operator expression of u64s is a u64.
    "operator_end": _row(f"""
        {BIG}
        let z: u64 = 0
        var n: i64 = 0
        for j in z..(big | z)
            n = n + 1
            if n == 5
                break
        if n != 5
            return 1
        0
    """),
    # A small u64 range is unchanged.
    "small_u64": _row("""
        let a: u64 = 2
        let b: u64 = 5
        var n: i64 = 0
        for j in a..b
            n = n + 1
        if n != 3
            return 1
        0
    """),
    "small_u64_inclusive": _row("""
        let a: u64 = 2
        let b: u64 = 5
        var n: i64 = 0
        for j in a..=b
            n = n + 1
        if n != 4
            return 1
        0
    """),
    # A signed range crossing 0 keeps its signed compare.
    "signed_cross_zero": _row("""
        let a: i64 = -3
        let b: i64 = 2
        var n: i64 = 0
        var sum: i64 = 0
        for j in a..b
            n = n + 1
            sum = sum + j
        if n != 5
            return 1
        if sum != -5
            return 2
        0
    """),
    "signed_cross_zero_inclusive": _row("""
        let a: i64 = -3
        let b: i64 = 2
        var n: i64 = 0
        for j in a..=b
            n = n + 1
        if n != 6
            return 1
        0
    """),
    "signed_literal_start": _row("""
        var n: i64 = 0
        for j in -2..2
            n = n + 1
        if n != 4
            return 1
        0
    """),
    # AGAST #3328: j is a u64 in the body. Signed, 1 << 63 is -2^63, and
    # these are -2^62, -2, -2 and true.
    "body_ops_top_bit": _row(f"""
        {BIG}
        var n: i64 = 0
        for j in big..=big
            n = n + 1
            if j / 2 != 4611686018427387904
                return 1
            if j % 3 != 2
                return 2
            if j >> 62 != 2
                return 3
            if j < 1
                return 4
        if n != 1
            return 5
        0
    """),
    # The end alone is a u64: j is one too, as the compare is unsigned.
    "body_ops_end_only_u64": _row(f"""
        {BIG}
        let s: i64 = 9223372036854775807
        var n: i64 = 0
        for j in s..=big
            n = n + 1
            if n == 2
                if j / 2 != 4611686018427387904
                    return 1
                if j >> 62 != 2
                    return 2
        if n != 2
            return 3
        0
    """),
    # A signed range's j stays signed.
    "body_ops_signed": _row("""
        let a: i64 = -4
        var n: i64 = 0
        for j in a..=a
            n = n + 1
            if j / 2 != -2
                return 1
            if j % 3 != -1
                return 2
            if j >> 1 != -2
                return 3
            if j > 0
                return 4
        if n != 1
            return 5
        0
    """),
    # ... even after a u64 loop that bound the same name.
    "body_ops_signed_after_u64": _row(f"""
        {BIG}
        for j in big..=big
            if j / 2 != 4611686018427387904
                return 1
        let a: i64 = -4
        for j in a..=a
            if j / 2 != -2
                return 2
            if j >> 1 != -2
                return 3
        0
    """),
    # AGAST #3327: mixed widths. The narrower bound widens by its own type,
    # zext for unsigned: sign-extended, 3000000000 became 0xFFFFFFFFB2D05E00
    # and the loop ran 0 times on ritz0.
    "mixed_u32_start_u64_end": _row("""
        let a: u32 = 3000000000
        let b: u64 = 3000000003
        var n: i64 = 0
        var last: u64 = 0
        for j in a..b
            n = n + 1
            last = j
        if n != 3
            return 1
        if last != 3000000002
            return 2
        0
    """),
    # The narrower end: sign-extended, it is 2^64 - 1 and the loop doesn't
    # stop at 3. `break` bounds the wrong case.
    "mixed_u64_start_u32_end": _row("""
        let a: u64 = 4294967292
        let b: u32 = 4294967295
        var n: i64 = 0
        for j in a..b
            n = n + 1
            if n == 10
                break
        if n != 3
            return 1
        0
    """),
    "mixed_u8_start_u64_end": _row("""
        let a: u8 = 250
        let b: u64 = 253
        var n: i64 = 0
        for j in a..b
            n = n + 1
        if n != 3
            return 1
        0
    """),
    # Signed controls: a negative narrower bound still sign-extends.
    "mixed_i32_start_i64_end": _row("""
        let a: i32 = -3
        let b: i64 = 2
        var n: i64 = 0
        var sum: i64 = 0
        for j in a..b
            n = n + 1
            sum = sum + j
        if n != 5
            return 1
        if sum != -5
            return 2
        0
    """),
    "mixed_i64_start_i32_end": _row("""
        let a: i64 = -5
        let b: i32 = -2
        var n: i64 = 0
        for j in a..b
            n = n + 1
        if n != 3
            return 1
        0
    """),
}


def _program():
    parts, calls = [], []
    for i, body in enumerate(ROWS.values(), 1):
        parts.append(f"fn t{i}() -> i64\n{_indent(body)}")
        calls.append(f"    if t{i}() != 0\n        return {i}\n")
    return "".join(parts) + "fn main() -> i32\n" + "".join(calls) + "    0\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_for_range_follows_bound_signedness(request, compiler, tmp_path):
    code = _run(request, compiler, tmp_path, _program())
    names = list(ROWS)
    wrong = names[code - 1] if 0 < code <= len(names) else code
    assert code == 0, f"{compiler}: {wrong}"
