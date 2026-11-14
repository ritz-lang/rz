"""AGAST #2525: a whole struct `*(q + 1)`, `q: *S`, where a number goes.

    struct S
        x: i32
        y: i64
    fn f(q: *S) -> i64
        return *(q + 1) + 1         # also `*(q + 1) as i64`, `return *(q + 1)`

ritz1 wrote the `%S` load where an i64 goes and clang refused the .ll, unlocated.
ritz0 refused the cast, the `return`, `==` and the annotated `let` located, but an
arithmetic or ordering operator (`+`, `-`, `<`, ...) on any struct crashed in
llvmlite ("Operands must be the same type"), unlocated.  The rule: a type error,
located at the expression, on all three compilers.

ritz1 refuses it in each integer position, with ritz0's message there: the cast
and `return` (#3008's refusals, which now name a deref's struct), an operator
(ritz0's new one), and an annotated `let` (#2993's, one message for a `[N]S`
element and a deref).  Not at the deref itself: `match *p`, `(*p).m()` and a
struct-valued arm or tail are legal and aren't copies into a struct slot.  The
copies (`let s: S = *(q + 1)`, `g(*(q + 1))`, `return *(q + 1)` from `-> S`, a
field read) stay legal.
"""

import re
from pathlib import Path

import pytest

from test_borrow_param_ref_field import _compile, _run

# Each test's rows share one compile per compiler (batching.py, AGAST #2806).
pytestmark = pytest.mark.batched

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ["ritz1", "ritz1_selfhosted"]
# What each position says, on every compiler that refuses it with a message of
# its own (ritz0, and ritz1 since #2525).  `compared` is #2510's.
MESSAGES = {
    "added": "`+` on struct `S`: a struct is not an integer",
    "added_on_the_right": "`+` on struct `S`: a struct is not an integer",
    "subtracted": "`-` on struct `S`: a struct is not an integer",
    "ordered": "`<` on struct `S`: a struct is not an integer",
    "cast": "cannot cast struct `S` to `i64`: a struct is not an integer",
    "plain": "cannot cast struct `S` to `i64`: a struct is not an integer",
    "returned": "the fn returns `i64`, but this is struct `S`: a struct is not an integer",
    "compared": "'==' is not supported for struct type",
}
LOCATED = re.compile(r"main\.ritz:\d+:\d+:")


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    """_compile, by name.  The gate builds ritz1_selfhosted before pytest."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    """_run, by name."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


_S = "struct S\n    x: i32\n    y: i64\n\n"
# q points at a[0], so *(q + 1) is a[1]: x = 5, y = 6.
_MAIN = ("\n\npub fn main() -> i32\n    var a: [3]S\n    a[1].x = 5\n    a[1].y = 6\n"
         "    return f(@a[0]) as i32\n")


def _f(body: str) -> str:
    return _S + "fn f(q: *S) -> i64\n" + body + _MAIN


# The ticket's three, then the other integer positions.  `plain` is `*q` itself.
WHOLE_STRUCT_DEREF = {
    "added": _f("    return *(q + 1) + 1"),
    "cast": _f("    return *(q + 1) as i64"),
    "returned": _f("    return *(q + 1)"),
    "added_on_the_right": _f("    return 1 + *(q + 1)"),
    "subtracted": _f("    let n: i64 = *(q + 1) - 1\n    return n"),
    "ordered": _f("    if *(q + 1) < 5\n        return 1\n    return 0"),
    "compared": _f("    if *(q + 1) == 5\n        return 1\n    return 0"),
    "let_integer": _f("    let n: i64 = *(q + 1)\n    return n"),
    "plain": _f("    return *q as i64"),
}


# ritz0's message varies with the position ("cannot cast struct", "the fn returns",
# "'==' is not supported"); each is located, and none is a crash.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(WHOLE_STRUCT_DEREF))
def test_a_whole_struct_deref_is_not_a_number(compile_with, name, compiler):
    comp, _, _ = compile_with(compiler, name, WHOLE_STRUCT_DEREF[name])
    assert comp.returncode != 0
    assert LOCATED.search(comp.stderr + comp.stdout), comp.stderr[-2000:]
    assert "Traceback" not in comp.stderr
    assert "Operands must be the same type" not in comp.stderr
    if name in MESSAGES:
        assert MESSAGES[name] in comp.stderr
    elif compiler != "ritz0":
        assert "a whole struct is not a value here in ritz1" in comp.stderr


# ritz0's arithmetic refusal is any struct's, not only a deref's: a local and a
# `[N]S` element crashed the same way.
STRUCT_ARITHMETIC = {
    "local": _S + "pub fn main() -> i32\n    var s: S\n    let n: i64 = s + 1\n    return n as i32\n",
    "element": _S + "pub fn main() -> i32\n    var a: [3]S\n    let n: i64 = a[1] * 2\n    return n as i32\n",
    "deref": _f("    return *(q + 1) + 1"),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(STRUCT_ARITHMETIC))
def test_ritz0_refuses_arithmetic_on_a_struct(compile_with, name):
    comp, _, _ = compile_with("ritz0", name, STRUCT_ARITHMETIC[name])
    assert comp.returncode != 0
    assert "a struct is not an integer" in comp.stderr
    line = 6 if name == "deref" else 7
    assert re.search(rf"main\.ritz:{line}:\d+:", comp.stderr), comp.stderr[-2000:]


# What stays legal: each a copy into a struct slot, or a field read.  All return 6,
# a[1].y.
STRUCT_DEREF_COPIES = {
    "let_annotated": _f("    let s: S = *(q + 1)\n    return s.y"),
    "let_inferred": _f("    let s = *(q + 1)\n    return s.y"),
    "argument": _S + "fn g(s: S) -> i64\n    return s.y\n\nfn f(q: *S) -> i64\n    return g(*(q + 1))" + _MAIN,
    "returned_as_struct": _S + "fn h(q: *S) -> S\n    return *(q + 1)\n\nfn f(q: *S) -> i64\n    let s = h(q)\n"
    + "    return s.y" + _MAIN,
    "field": _f("    return (*(q + 1)).y"),
    "stored": _f("    var s: S\n    s = *(q + 1)\n    return s.y"),
    "stored_through": _f("    *q = *(q + 1)\n    return q[0].y"),
    "if_arm": _f("    let s: S = if q[1].x == 5 then *(q + 1) else *q\n    return s.y"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(STRUCT_DEREF_COPIES))
def test_a_whole_struct_deref_copies(run_with, name, compiler):
    assert run_with(compiler, name, STRUCT_DEREF_COPIES[name]) == 6
