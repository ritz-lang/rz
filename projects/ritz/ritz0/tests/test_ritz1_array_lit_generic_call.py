"""AGAST #2831: a generic call inside an array literal is instantiated.

ritz1's monomorph walk (collect_from_expr) had no case for an array literal
`[a, b]` or an array fill `[v; N]`, so `var a: [2]i64 = [first<i8>(@x), 1]`
called `@first$i8` and never defined it: the link failed.  The same call as a
`let` initializer was found.  ritz0 is the oracle.

Each program returns 0, or the number of the check that failed.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

FIRST = "fn first<T>(p: *T) -> T\n    *p\n\n"

# The ticket's program: the only call to first<i8> sits in an array literal.
LIT = FIRST + (
    "pub fn main() -> i32\n"
    "    var src: [2]i8 = [7, 8]\n"
    "    var a: [2]i64 = [first<i8>(@src[0]) as i64, 1]\n"
    "    if a[0] != 7\n        return 1\n"
    "    if a[1] != 1\n        return 2\n"
    "    0\n"
)

# The only call to first<i64> is the fill value of `[v; N]`.
FILL = FIRST + (
    "pub fn main() -> i32\n"
    "    var x: i64 = 9\n"
    "    var a: [3]i64 = [first<i64>(@x); 3]\n"
    "    if a[0] != 9\n        return 1\n"
    "    if a[2] != 9\n        return 2\n"
    "    0\n"
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_generic_call_in_array_literal(run_with, compiler):
    """`[first<i8>(@src[0]) as i64, 1]` instantiates first$i8."""
    assert run_with(compiler, "lit", LIT) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_generic_call_in_array_fill(run_with, compiler):
    """`[first<i64>(@x); 3]` instantiates first$i64."""
    assert run_with(compiler, "fill", FILL) == 0
