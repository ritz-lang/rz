"""AGAST #3600: the typing pass on pointer difference (LANGUAGE_SPEC §7.1).

    let a: *u8 = @buf[0]
    let b: *u8 = @buf[3]
    (b - a) as i32 - 3     # "arithmetic operator requires numeric type, got *u8", twice

`q - p` on two `*T` is their distance in elements, an i64; the emitter has
lowered it since #2928 (test_pointer_difference.py), but `--check-types`
refused both operands.  `*T ± int` is a `*T` and `int + *T` too; nothing else
an arithmetic operator does to a pointer is.  A reference operand (`@T`, `@&T`,
or the `@x` that infers one) stays refused (LARB R16, test_ref_arith_refused.py).
Two pointee types are refused by the emitter on every compile (#2957), so the
checker leaves that to it.

In-process TypeChecker: each row is one parse and one check, no compile.
"""

import pytest
from parser import parse
from type_checker import TypeChecker
from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals, assert_runs

pytestmark = pytest.mark.unit

_PTRS = ("fn f(a: *u8, b: *u8, r: @u8, n: i64) -> i32\n"
         "    var buf: [4]u8 = [1, 2, 3, 4]\n")


def types(body: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(_PTRS + body + "    0\n"))]


def test_ticket_repro_types():
    src = ("fn main() -> i32\n"
           "    var buf: [4]u8 = [1, 2, 3, 4]\n"
           "    let a: *u8 = @buf[0]\n"
           "    let b: *u8 = @buf[3]\n"
           "    (b - a) as i32 - 3\n")
    assert [str(e) for e in TypeChecker().check(parse(src))] == []


def test_difference_is_an_i64():
    # A `*u8` slot takes an integer here, so a bool slot shows the type.
    assert types("    let c: bool = b - a\n") == [
        "<stdin>:3:5: cannot initialize bool with i64"]


def test_difference_through_an_alias():
    src = ("type P = *u8\n\n"
           "fn f(a: P, b: P) -> i64\n"
           "    b - a\n")
    assert [str(e) for e in TypeChecker().check(parse(src))] == []


def test_opaque_minus_ptr_is_not_judged():
    # A type parameter may stand for a `*T`: `int - ptr` is refused, `T - ptr` not.
    src = ("fn g<T>(x: T, a: *u8) -> i64\n"
           "    let d: i64 = x - a\n"
           "    d\n")
    assert [str(e) for e in TypeChecker().check(parse(src))] == []


# Each row separates one path through the arithmetic rule.
ACCEPTED = {
    "diff_is_i64": "    let d: i64 = b - a\n",
    "ptr_plus_int": "    let c: *u8 = a + n\n",
    "ptr_minus_int": "    let c: *u8 = a - 1\n",
    "int_plus_ptr": "    let c: *u8 = 1 + a\n",
}

REFUSED = {
    # the sum of two pointers is no element count
    "ptr_plus_ptr": "    let d: i64 = b + a\n",
    # only `+` / `-` step a pointer
    "ptr_times_int": "    let c: *u8 = a * 2\n",
    "int_minus_ptr": "    let c: *u8 = 1 - a\n",
    # a reference operand stays an error (R16)
    "ref_minus_ptr": "    let d: i64 = r - a\n",
    "addr_of_minus_addr_of": "    let d: i64 = @buf[3] - @buf[0]\n",
}


@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_pointer_arithmetic_accepted(name):
    assert types(ACCEPTED[name]) == []


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_pointer_arithmetic_refused(name):
    assert types(REFUSED[name]) != []


# ---- every compiler (AGAST #4657) -------------------------------------------
#
# The same rule on ritz0, ritz1 and ritz1_selfhosted, located at the operand
# that has no arithmetic.  ritz1 lowered each REFUSED row (`a * 2` as a
# `mul` of a `ptrtoint`); ritz0's emitter refused `a * 2` and `1 - a` only by
# an llvmlite traceback, and now says the checker's words first.

_NUMERIC = "arithmetic operator requires numeric type, got "
_REFUSE_AT = {
    "ptr_plus_ptr": ("    let d: i64 = ^b + a\n", "*u8"),
    "ptr_times_int": ("    let c: *u8 = ^a * 2\n", "*u8"),
    "ptr_div_int": ("    let d: i64 = ^a / 2\n", "*u8"),
    "int_minus_ptr": ("    let c: *u8 = 1 - ^a\n", "*u8"),
    "int_mod_ptr": ("    let d: i64 = 7 % ^a\n", "*u8"),
    "addr_of_minus_addr_of": ("    let d: i64 = ^@buf[3] - @buf[0]\n", "@u8"),
    "addr_of_times_int": ("    let d: i64 = ^@buf[3] * 2\n", "@u8"),
}
EVERY_REFUSED = {name: (_PTRS + body + "    0\n" + "\nfn main() -> i32\n    0\n", _NUMERIC + ty)
                 for name, (body, ty) in _REFUSE_AT.items()}

# Each accepted shape, run: `b - a` is 3 elements, `a + n` / `1 + a` step.
_RUN = ("fn main() -> i32\n"
        "    var buf: [4]u8 = [1, 2, 3, 4]\n"
        "    let a: *u8 = @buf[0]\n"
        "    let b: *u8 = @buf[3]\n"
        "    let n: i64 = 2\n")
EVERY_RUNS = {
    "diff_is_i64": (_RUN + "    (b - a) as i32\n", 3),
    "ptr_plus_int": (_RUN + "    *(a + n) as i32\n", 3),
    "ptr_minus_int": (_RUN + "    *(b - 1) as i32\n", 3),
    "int_plus_ptr": (_RUN + "    *(1 + a) as i32\n", 2),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_compiler_refuses_pointer_arithmetic(tmp_path, compiler):
    assert_refusals(compiler, tmp_path, EVERY_REFUSED)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_compiler_runs_pointer_arithmetic(tmp_path, compiler):
    assert_runs(compiler, tmp_path, EVERY_RUNS)
