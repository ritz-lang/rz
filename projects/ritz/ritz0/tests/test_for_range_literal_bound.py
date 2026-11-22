#!/usr/bin/env python3
"""A range's literal bound takes the other bound's type when it fits (AGAST #4080).

THE GAP

ritz0's `_emit_for` gave `for i in a..b`'s variable the end's type only for a
literal `0` start. Any other literal widened the loop to i64:

    for i in 0..n          # n: i32 -> i: i32
    for i in 1..n          #        -> i: i64, so #1444 refuses take(i)
    for i in 1..(n + 1)    #        -> i64 too

ritz1 bound every range variable as an i64 (a u64 over a u64 bound) whatever
its bounds were, and Sema left its type unknown, so it never refused a narrowing
of it.

THE RULE (LANGUAGE_SPEC §6.3, the ruling recorded on #4080)

A lone untyped integer literal bound is the other bound's type when it fits
there, as a binary operator's literal operand is (LARB R21, #3112). So `1..n`
and `k..10` (n, k: i32) bind an i32, `1..m` (m: u32) a u32. A literal that
doesn't fit (`-129..m`, m: i8) widens, as it did. Two literals are an i64. Otherwise the
wider bound's width, unsigned when a bound is (#1636 / #3328).

The variable's arithmetic is at that width, so `i -% 2` with `i: u32 = 1`
wraps (plain `-` would stop the program, LARB R63). The #4080 corpus IR diff
found no loop whose result that changes.

THE TESTS

`RUNS`: each row's fn returns 0 when the loop bound the type the rule names,
on all three compilers; main exits with the first wrong row's index.
`REFUSED`: a loop variable the rule leaves an i64 is refused as an i32
argument, on all three: ritz1 used to accept it because Sema did not type it.
"""

import re

import pytest

from test_right_shift import _compile, _indent, _run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = """\
fn take(v: i32) -> i32
    v

fn take_u(v: u32) -> u32
    v

"""

# name -> body of `fn t() -> i64`: 0 when the loop's variable has the
# rule's type.
RUNS = {
    # The ticket: a literal start with an i32 end is an i32, so take(i) is
    # no narrowing.
    "literal_start": """\
let n: i32 = 4
var s: i32 = 0
for i in 1..n
    s = s + take(i)
if s != 6
    return 1
0""",
    "literal_start_expr_end": """\
let n: i32 = 4
var s: i32 = 0
for i in 1..(n + 1)
    s = s + take(i)
if s != 10
    return 1
0""",
    # A literal end takes the start's type.
    "literal_end": """\
let k: i32 = 7
var s: i32 = 0
for i in k..10
    s = s + take(i)
if s != 24
    return 1
0""",
    # An unsigned bound gives its type: `i -% 2` at i = 1 wraps in u32 (it was
    # -1 at i64).
    "literal_start_unsigned": """\
let m: u32 = 3
var s: u32 = 0
var big: i64 = 0
for i in 1..m
    s = s + take_u(i)
    if i -% 2 > 100
        big = big + 1
if s != 3
    return 1
if big != 1
    return 2
0""",
    # `-129` doesn't fit an i8: the loop widens to i64 and runs -129, -128.
    # Adopting the i8 anyway would start at 127 and never run.
    "literal_that_does_not_fit_widens": """\
let m: i8 = -127
var n: i64 = 0
for i in -129..m
    n = n + 1
if n != 2
    return 1
0""",
    # AGAST #4261: `-1` doesn't fit the u32 end, so the loop widens to an
    # i64, and at 64 bits only a u64 bound is unsigned (§6.3): the compare is
    # signed and runs -1, 0, 1, 2. ritz0 compared unsigned (-1 as u64 > 3) and
    # ran it 0 times.
    "negative_literal_unsigned_end": """\
let m: u32 = 3
var n: i64 = 0
var s: i64 = 0
for i in -1..m
    n = n + 1
    s = s + i
if n != 4
    return 1
if s != 2
    return 2
0""",
    "negative_literal_unsigned_end_inclusive": """\
let m: u32 = 3
var n: i64 = 0
for i in -1..=m
    n = n + 1
if n != 5
    return 1
0""",
    # The same without a literal: an i64 start and a u32 end are an i64.
    "i64_start_u32_end": """\
let a: i64 = -2
let m: u32 = 2
var n: i64 = 0
for i in a..m
    n = n + 1
if n != 4
    return 1
0""",
    # A u32 end beyond i32 still zero-extends into the signed i64 range.
    "negative_literal_big_u32_end": """\
let m: u32 = 4294967295
var n: i64 = 0
for i in -1..m
    n = n + 1
    if n > 2
        break
if n != 3
    return 1
0""",
}

# name -> (program body of main, the `take(i)` line)
REFUSED = {
    # Two literals are an i64 (unchanged).
    "two_literals": """\
var s: i32 = 0
for i in 1..3
    s = s + take(i)
s""",
    # A literal adopts an i64 end: still an i64.
    "literal_and_i64": """\
let n: i64 = 3
var s: i32 = 0
for i in 1..n
    s = s + take(i)
s""",
}


def _program():
    parts, calls = [], []
    for i, body in enumerate(RUNS.values(), 1):
        parts.append(f"fn t{i}() -> i64\n{_indent(body)}\n")
        calls.append(f"    if t{i}() != 0\n        return {i}\n")
    return PRELUDE + "".join(parts) + "fn main() -> i32\n" + "".join(calls) + "    0\n"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_literal_bound_takes_the_other_bounds_type(request, tmp_path, compiler):
    rc = _run(request, compiler, tmp_path, _program())
    names = list(RUNS)
    assert rc == 0, (
        f"{compiler}: row {names[rc - 1] if 0 < rc <= len(names) else rc} is wrong"
    )


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", REFUSED)
def test_an_i64_loop_variable_is_refused_as_an_i32_argument(
    request, tmp_path, compiler, form
):
    src = PRELUDE + "fn main() -> i32\n" + _indent(REFUSED[form])
    proc, ll = _compile(request, compiler, tmp_path, src)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, (
        f"{compiler} accepted `take(i)` over an i64 `i`:\n{src}"
    )
    assert re.search(
        r"implicit narrowing: argument 1 of `take` is `i32` but this value has type `i64`",
        out,
    ), f"{compiler}:\n{out}"
