"""AGAST #3011: an `await` in a block's tail, or nested in an expression, is an await point.

    async fn go(x: i32) -> i32
        await fetch(x)

async_transform_v2 recorded the await, but `_generate_final_return` rebuilt the
tail by lowering `await fetch(x)` to plain `fetch(x)`: go$poll returned the
`fetch$Future` struct from an `i32` fn, which ritz0 refuses since #2999 ("a struct
is not an integer").  `(await fetch(x)) + 1` failed the same way, at `+`, and
`return await fetch(x)` answered 0.  The final state now reads each await's
stored result.

ritz0 only: ritz1 has no async fns (ritz1/src/main.ritz).
"""

import pytest
from test_borrow_param_ref_field import _run

pytestmark = pytest.mark.batched

# fetch is Ready with its argument on the first poll; main polls go once.
_FETCH = "async fn fetch(x: i32) -> i32\n    x\n\n"
# One poll: true with the value in `__result` (LARB R78, #3728); 99 if Pending.
_MAIN = ("pub fn main() -> i32\n    var f = go(7)\n    if future_poll(@&f)\n"
         "        return f.__result\n    99\n")

# name -> (go's body, go$poll's value for x = 7)
ROWS = {
    # The ticket's rows.
    "tail": ("    await fetch(x)\n", 7),
    "tail_plus_one": ("    (await fetch(x)) + 1\n", 8),
    # Two awaits in one expression: each its own result, in source order (a
    # swapped pair answers 3 - 10, exit 249).
    "two_in_one_expr": ("    await fetch(10) - await fetch(3)\n", 7),
    "tail_in_if_arm": ("    if x > 0\n        await fetch(x)\n    else\n        0\n", 7),
    # The arm's locals live in the future, where its tail reads them.
    "let_in_if_arm": ("    if x > 0\n        let y: i32 = await fetch(x)\n        let z: i32 = y + 1\n        z\n"
                      + "    else\n        0\n", 8),
    # The inner await is driven first, and the outer one polls its value.
    "nested": ("    await fetch(await fetch(x) + 1)\n", 8),
    # The forms that already lowered.  `return await` compiled but answered 0:
    # the final state read only the body's tail, and it had none.
    "return_await": ("    return await fetch(x)\n", 7),
    "statement": ("    await fetch(x)\n    x + 2\n", 9),
    # AGAST #1318: an untyped binding takes the poll's i32.  Its None type kept
    # `v` out of go$Future while the constructor still set it: "Unknown field v".
    "untyped_let": ("    let v = await fetch(x)\n    v + 1\n", 8),
    # AGAST #3821: only a let whose value IS the await binds its result.  One
    # nested in the value took `v` as its result var, so the state stored the
    # bare 7 in `v` and the `+ 1` was never evaluated.
    "let_await_plus_one": ("    let v = (await fetch(x)) + 1\n    v\n", 8),
    "typed_let_one_plus_await": ("    let v: i32 = 1 + await fetch(x)\n    v\n", 8),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ROWS))
def test_ritz0_await_point_yields_its_value(tmp_path, name):
    body, want = ROWS[name]
    program = _FETCH + "async fn go(x: i32) -> i32\n" + body + "\n" + _MAIN
    assert _run("ritz0", None, tmp_path, name, program) == want


# AGAST #3821: a let around an await runs once.  The body's own let runs in its
# await's state; one in an arm runs in the final state, which re-walks the arm
# (a second run answers 27).
_BUMP = "var CALLS: i32 = 0\n\nfn bump() -> i32\n    CALLS = CALLS + 1\n    0\n\n"
COUNTED = {
    "top_level": "    let v: i32 = (await fetch(x)) + bump()\n    v + CALLS * 10\n",
    "in_if_arm": "    if x > 0\n        let z: i32 = (await fetch(x)) + bump()\n"
                 + "        z + CALLS * 10\n    else\n        0\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(COUNTED))
def test_ritz0_let_around_await_runs_once(tmp_path, name):
    program = _BUMP + _FETCH + "async fn go(x: i32) -> i32\n" + COUNTED[name] + "\n" + _MAIN
    assert _run("ritz0", None, tmp_path, name, program) == 17
