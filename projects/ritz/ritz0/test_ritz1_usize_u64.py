"""AGAST #3464 (LARB R53): on ritz1, `usize` is `u64` and `isize` is `i64`.

The ruling (projects/larb/review/4/rulings-2026-11.md § R53): "`usize` is
another name for `u64`, and `isize` for `i64`: the same types, not new ones."

#2198 had ritz1 parse both names as TYPE_I64, so every `usize` was lowered
as *signed*.  With `b = 0xFFFFFFFFFFFFFFF8 as usize`, `b >> 60` was an
arithmetic shift, `b > 1` was false, `/` and `%` were signed, and `b as f64`
was negative.  ritz1 now maps `usize` to TYPE_U64 where it maps type names
(type_named for a written type, primitive_type_from_name for a monomorph's
`*T` at T = usize), and `isize` stays TYPE_I64.  A generic argument still
mangles as written (`P$usize`, generic_arg_spelling).

ritz1 doesn't lex `_` digit separators (#3584), so the literals here are
written without them.

These are the ritz0 ticket's (#3463) rows, run on ritz1 and ritz1_selfhosted.
Each program returns 0, or the number of the first check that failed.
"""

import pytest

from test_ritz1_for_iterable import RITZ1S, compile_with, run_with  # noqa: F401  (fixtures)

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = pytest.mark.batched

B = "    let b: usize = 0xFFFFFFFFFFFFFFF8 as usize\n"

CASES = {
    # A logical shift: 0xF, not the sign smeared down (-1).
    "shift": B + "    if b >> 60 != 15\n        return 1\n    0\n",
    # Unsigned compare: the top bit set is large, not negative.
    "compare": B
    + (
        "    if not (b > 1)\n        return 1\n"
        "    if b < 0x8000000000000000 as usize\n        return 2\n    0\n"
    ),
    # Unsigned divide and remainder (udiv / urem, not sdiv / srem).
    "divide": B
    + "    if b / 2 != 0x7FFFFFFFFFFFFFFC as usize\n        return 1\n    0\n",
    "remainder": B + "    if b % 10 != 8\n        return 1\n    0\n",
    # uitofp: positive, about 2^64.
    "as_f64": B
    + (
        "    let f: f64 = b as f64\n"
        "    if f <= 0.0\n        return 1\n"
        "    if f < 18446744073709000000.0\n        return 2\n    0\n"
    ),
    # The largest u64 literal is a usize.
    "max_literal": (
        "    let m: usize = 18446744073709551615\n"
        "    if m != 0xFFFFFFFFFFFFFFFF as usize\n        return 1\n"
        "    if m >> 63 != 1\n        return 2\n    0\n"
    ),
    # Through a param and a return: the type rides the declared name.
    "param": (
        "fn top(n: usize) -> usize\n    n >> 60\n\n"
        "pub fn main() -> i32\n" + B + "    if top(b) != 15\n        return 1\n    0\n"
    ),
    # A monomorph's `p: *T` at T = usize: the pointee is named by the
    # argument's spelling (primitive_type_from_name, subst_pointee_field).
    "generic_pointee": (
        "struct P<T>\n    p: *T\n\n"
        "pub fn main() -> i32\n"
        "    var b: usize = 0xFFFFFFFFFFFFFFF8 as usize\n"
        "    var x: P<usize> = P<usize> { p: @b }\n"
        "    if *x.p >> 60 != 15\n        return 1\n"
        "    if *x.p % 10 != 8\n        return 2\n    0\n"
    ),
    # A monomorph's `v: T` at T = usize: the type argument, as type_named
    # parsed it.
    "generic_field": (
        "struct Box<T>\n    v: T\n\n"
        "pub fn main() -> i32\n"
        "    var x: Box<usize> = Box<usize> { v: 0 as usize }\n"
        "    x.v = 0xFFFFFFFFFFFFFFF8 as usize\n"
        "    if x.v >> 60 != 15\n        return 1\n"
        "    if x.v % 10 != 8\n        return 2\n    0\n"
    ),
    # isize stays i64: an arithmetic shift, a signed compare and divide.
    "isize_signed": (
        "    let i: isize = 0 - 8\n"
        "    if i >> 1 != 0 - 4\n        return 1\n"
        "    if not (i < 0)\n        return 2\n"
        "    if i / 2 != 0 - 4\n        return 3\n    0\n"
    ),
}


def _program(body: str) -> str:
    return (
        body if body.startswith(("fn ", "struct ")) else "pub fn main() -> i32\n" + body
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_usize_is_u64(run_with, compiler, name):  # noqa: F811
    """R53: `usize` lowers as u64 on ritz1 and ritz1_selfhosted (#3464)."""
    assert run_with(compiler, name, _program(CASES[name])) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_usize_generic_arg_keeps_its_spelling(compile_with, compiler):  # noqa: F811
    """`P<usize>` still mangles `P$usize` (#2198), now that usize is TYPE_U64.

    generic_arg_spelling kept the written name only for a TYPE_I64, so the
    switch to TYPE_U64 renamed every usize instance `$u64`: a different symbol
    from the `$usize` one ritz0 and the other ritz1 call sites spell.
    """
    comp, ll, _ = compile_with(compiler, "spelling", _program(CASES["generic_pointee"]))
    assert comp.returncode == 0, comp.stdout + comp.stderr
    ir = ll.read_text()
    assert "%P$usize = type" in ir
    assert "P$u64" not in ir
