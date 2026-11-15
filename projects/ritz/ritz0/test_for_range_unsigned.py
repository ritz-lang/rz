#!/usr/bin/env python3
"""A `for` range over u64 bounds compares unsigned (AGAST #1636).

`for j in a..b` desugars to `while j < b` (`<=` for `a..=b`). All three
compilers compared signed whatever the bounds were, so with `big: u64 = 1 << 63`
`for j in 0..big` ran zero times: as an i64, `big` is negative. The loop's
compare now follows binary `<`'s rule (#2361): unsigned when a bound is a u64,
directly or through an operator expression. A signed range keeps its signed
compare, which is what lets `-3..2` cross 0.

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
}


def _program():
    parts, calls = [], []
    for i, body in enumerate(ROWS.values(), 1):
        parts.append(f"fn t{i}() -> i64\n{_indent(body)}")
        calls.append(f"    if t{i}() != 0\n        return {i}\n")
    return "".join(parts) + "fn main() -> i32\n" + "".join(calls) + "    0\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_for_range_compare_follows_bound_signedness(request, compiler, tmp_path):
    code = _run(request, compiler, tmp_path, _program())
    names = list(ROWS)
    wrong = names[code - 1] if 0 < code <= len(names) else code
    assert code == 0, f"{compiler}: {wrong}"
