#!/usr/bin/env python3
"""AGAST #3034: ritz0 calls through an un-annotated fn local.

`let f = inc` / `f(2)` was "Compiler error: Unknown function: f": the `let`
recorded no Ritz type for `f`, so the call missed the indirect-call path and
was looked up as a fn named `f`. With `let f: fn(i32) -> i32 = inc` it always
compiled, and ritz1 runs both. The local now carries `inc`'s signature, a
`:&` param as the pointer the callee takes (LANGUAGE_SPEC §13.4).

Each row exits 3 only if the right fn ran through the local and its result
(or its write through the `:&` slot) came back.
"""

import pytest
from test_ref_into_value import _run

pytestmark = pytest.mark.integration

ROWS = {
    # The ticket's repro.
    "scalar": ("fn inc(a: i32) -> i32\n    a + 1\n\n",
               "    let f = inc\n    f(2)\n"),
    # `dec` would answer 1: the local names `inc`, not the last fn declared.
    "the_named_fn": ("fn inc(a: i32) -> i32\n    a + 1\n\nfn dec(a: i32) -> i32\n    a - 1\n\n",
                     "    let f = inc\n    f(2)\n"),
    # Two params, and an i64 one: each converts to its own slot.
    "two_params": ("fn add(a: i32, b: i64) -> i32\n    a + b as i32\n\n",
                   "    let f = add\n    f(1, 2)\n"),
    # A `:&` slot borrows the bare place, as `lb(c)` does: the write through
    # it lands in `c`. (ritz0's checker still types the slot by value, #3035,
    # so `g(@&c)` is refused there.)
    "lent_param": ("struct C\n    x: i32\n\nfn lb(c:& C) -> i32\n    c.x = 3\n    0\n\n",
                   "    var c = C { x: 1 }\n    let g = lb\n    g(c)\n    c.x\n"),
    # A struct of SRET_MIN_BYTES or more rides byval when passed by value;
    # behind `:&` it's a plain pointer (a byval would write to a copy).
    "lent_large_param": (("struct B\n    a: [32]i64\n    e: i64\n\n"
                          "fn lb(s:& B) -> i32\n    s.e = 3\n    0\n\n"),
                         ("    var s = B { a: [0; 32], e: 1 }\n    let g = lb\n"
                          "    g(s)\n    s.e as i32\n")),
}


@pytest.mark.parametrize("site", list(ROWS))
def test_a_call_through_an_inferred_fn_local_runs(tmp_path, site):
    fns, body = ROWS[site]
    assert _run("ritz0", tmp_path, site, fns + "fn main() -> i32\n" + body) == 3
