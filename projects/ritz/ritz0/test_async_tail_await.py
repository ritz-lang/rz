"""AGAST #3011: an `await` in a block's tail, or nested in an expression, is an await point.

    async fn go(x: i32) -> i32
        await fetch(x)

async_transform_v2 recorded the await, but `_generate_final_return` rebuilt the
tail by lowering `await fetch(x)` to plain `fetch(x)`: go_poll returned the
`fetch_Future` struct from an `i32` fn, which ritz0 refuses since #2999 ("a struct
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
_MAIN = "pub fn main() -> i32\n    var f: go_Future = go(7)\n    return go_poll(@f)\n"

# name -> (go's body, go_poll's value for x = 7)
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
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ROWS))
def test_ritz0_await_point_yields_its_value(tmp_path, name):
    body, want = ROWS[name]
    program = _FETCH + "async fn go(x: i32) -> i32\n" + body + "\n" + _MAIN
    assert _run("ritz0", None, tmp_path, name, program) == want
