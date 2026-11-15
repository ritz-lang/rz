"""A match whose arms mix `return` and a value yields the value (AGAST #3318).

ritz0's enum match appended an exit block for every arm (`None` for one that
returned) but a value only for the arms that reach the merge. The merge zipped
the two lists, so once a `return` arm came before a value arm the values were
paired with the wrong blocks: the ticket's

    match r
        Ok(v) => return v + 10
        Err(e) => e as i64

paired `Err`'s value with `Ok`'s `None` block, dropped it, and the tail
returned a dummy 0. ritz1 got it right.

Rows: Result and a plain enum, i64 and a struct result, in a fn tail and as
a `let` initialiser, plus the same shape for `if`/`else`: a returning then- or
else-branch, an `else if` chain, a struct result (ritz1's tail if/else lost the
value until #3323). Each `main` runs both the returning and the yielding path,
and every check exits with its own code.
"""

import pytest

from test_match_endless_loop_arm import COMPILERS, _run

pytestmark = pytest.mark.integration

# name -> source. Each `main` exits 0 only if every value is right.
PROGRAMS = {
    # The ticket's program, in a fn tail.
    "result_i64_tail": (
        "import ritzlib.result\n"
        "fn g(r: Result<i64, i32>) -> i64\n"
        "    match r\n"
        "        Ok(v) => return v + 10\n"
        "        Err(e) => e as i64\n"
        "fn main() -> i32\n"
        "    if g(Err(7)) != 7\n"
        "        return 4\n"
        "    if g(Ok(1)) != 11\n"
        "        return 5\n"
        "    0\n"
    ),
    # Two value arms after a `return` arm: each value must keep its own block.
    "plain_enum_i64_tail": (
        "enum E\n"
        "    A(i64)\n"
        "    B(i64)\n"
        "    C(i64)\n"
        "fn g(e: E) -> i64\n"
        "    match e\n"
        "        A(v) => return v + 100\n"
        "        B(v) => v + 20\n"
        "        C(v) => v + 30\n"
        "fn main() -> i32\n"
        "    if g(A(1)) != 101\n"
        "        return 4\n"
        "    if g(B(1)) != 21\n"
        "        return 5\n"
        "    if g(C(1)) != 31\n"
        "        return 6\n"
        "    0\n"
    ),
    "result_struct_tail": (
        "import ritzlib.result\n"
        "struct P\n"
        "    x: i64\n"
        "    y: i64\n"
        "fn g(r: Result<i64, i32>) -> P\n"
        "    match r\n"
        "        Ok(v) => return P { x: v, y: 1 }\n"
        "        Err(e) => P { x: e as i64, y: 2 }\n"
        "fn main() -> i32\n"
        "    let a: P = g(Err(7))\n"
        "    if a.x != 7 or a.y != 2\n"
        "        return 4\n"
        "    let b: P = g(Ok(3))\n"
        "    if b.x != 3 or b.y != 1\n"
        "        return 5\n"
        "    0\n"
    ),
    "plain_enum_let_initialiser": (
        "enum E\n"
        "    A(i64)\n"
        "    B(i64)\n"
        "fn g(e: E) -> i64\n"
        "    let n: i64 = match e\n"
        "        A(v) => return v + 100\n"
        "        B(v) => v + 20\n"
        "    n * 2\n"
        "fn main() -> i32\n"
        "    if g(A(1)) != 101\n"
        "        return 4\n"
        "    if g(B(1)) != 42\n"
        "        return 5\n"
        "    0\n"
    ),
    "if_else_tail": (
        "fn g(c: bool, v: i64) -> i64\n"
        "    if c\n"
        "        return v + 100\n"
        "    else\n"
        "        v + 20\n"
        "fn main() -> i32\n"
        "    if g(true, 1) != 101\n"
        "        return 4\n"
        "    if g(false, 1) != 21\n"
        "        return 5\n"
        "    0\n"
    ),
    # The value branch is the then-branch; the else returns.
    "if_else_returning_else_tail": (
        "fn g(c: bool, v: i64) -> i64\n"
        "    if c\n"
        "        v + 20\n"
        "    else\n"
        "        return v + 100\n"
        "fn main() -> i32\n"
        "    if g(true, 1) != 21\n"
        "        return 4\n"
        "    if g(false, 1) != 101\n"
        "        return 5\n"
        "    0\n"
    ),
    # An `else if` chain: the first branch returns, the rest yield.
    "if_else_if_tail": (
        "fn g(a: i32, v: i64) -> i64\n"
        "    if a == 0\n"
        "        return v + 100\n"
        "    else if a == 1\n"
        "        v + 20\n"
        "    else\n"
        "        v + 30\n"
        "fn main() -> i32\n"
        "    if g(0, 1) != 101\n"
        "        return 4\n"
        "    if g(1, 1) != 21\n"
        "        return 5\n"
        "    if g(2, 1) != 31\n"
        "        return 6\n"
        "    0\n"
    ),
    # An `else if` chain whose middle branch returns.
    "if_else_if_middle_return_tail": (
        "fn g(a: i32, v: i64) -> i64\n"
        "    if a == 0\n"
        "        v + 10\n"
        "    else if a == 1\n"
        "        return v + 100\n"
        "    else\n"
        "        v + 30\n"
        "fn main() -> i32\n"
        "    if g(0, 1) != 11\n"
        "        return 4\n"
        "    if g(1, 1) != 101\n"
        "        return 5\n"
        "    if g(2, 1) != 31\n"
        "        return 6\n"
        "    0\n"
    ),
    # A struct phi: the returning branch feeds it `zeroinitializer`.
    "if_else_struct_tail": (
        "struct P\n"
        "    x: i64\n"
        "    y: i64\n"
        "fn g(c: bool, v: i64) -> P\n"
        "    if c\n"
        "        return P { x: v, y: 1 }\n"
        "    else\n"
        "        P { x: v + 20, y: 2 }\n"
        "fn main() -> i32\n"
        "    let a: P = g(true, 1)\n"
        "    if a.x != 1 or a.y != 1\n"
        "        return 4\n"
        "    let b: P = g(false, 1)\n"
        "    if b.x != 21 or b.y != 2\n"
        "        return 5\n"
        "    0\n"
    ),
    "if_else_let_initialiser": (
        "fn g(c: bool, v: i64) -> i64\n"
        "    let n: i64 = if c\n"
        "        return v + 100\n"
        "    else\n"
        "        v + 20\n"
        "    n * 2\n"
        "fn main() -> i32\n"
        "    if g(true, 1) != 101\n"
        "        return 4\n"
        "    if g(false, 1) != 42\n"
        "        return 5\n"
        "    0\n"
    ),
}


# (name, compiler) -> ticket. Empty: ritz1's tail if/else ended its merge
# block in `unreachable`, dropping the else value, until #3323.
GAPS = {}


def _cases():
    for name in sorted(PROGRAMS):
        for compiler in COMPILERS:
            gap = GAPS.get((name, compiler))
            marks = [pytest.mark.xfail(strict=True, reason=gap)] if gap else []
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.parametrize("name,compiler", _cases())
def test_a_match_with_a_return_arm_yields_the_value_arm(tmp_path, name, compiler):
    assert _run(compiler, tmp_path, PROGRAMS[name]) == 0
