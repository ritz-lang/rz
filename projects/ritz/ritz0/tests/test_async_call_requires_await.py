"""AGAST #1395: calling an `async fn` needs `await`, whatever its body does.

Decided 2026-09-09: an `async fn` with no suspension point is NOT callable
synchronously.  A bare call `g()` builds g's future (`g_Future`) and runs none
of g's body; only `await g()` (or polling the future yourself) runs it.  So:

  * `await f()` compiles and runs f, even for `async fn f()` with an empty
    body.  It did not: a unit `async fn` lowered to an `i32` `f_poll` whose
    body produced no value, and ritz0 refused it ("function 'f_poll' declares
    a return type but can reach its end without producing a value").
  * `f()` as a statement is refused, located at the call.  It compiled
    silently and did nothing: the future was built and dropped.
  * `let r: i32 = g()` is refused naming the missing `await` (it named only
    `g_Future`, which is what kept 53/54/55 on the known-failures list).
  * Keeping the future is still allowed: `var p: g_Future = g()` is how an
    executor gets one to poll (62/64/75_async_*).

Value uses of a bare call (`take(g())`, `g() + 1`, `return g()`) were already
refused at the call by the struct-is-not-an-integer checks; they are not
re-pinned here.  ritz0 only: ritz1 has no async fns (ritz1/src/main.ritz).
"""

import re

import batching
import pytest
from test_borrow_param_ref_field import _batch_compile, _compile, _run

pytestmark = pytest.mark.batched

_EMPTY = "async fn f()\n    pass\n\n"
_FORTY_TWO = "async fn g() -> i32\n    42\n\n"
_STORE = "fn store(p: *i32, v: i32)\n    *p = v\n\n"


def _main(body: str) -> str:
    return f"pub fn main() -> i32\n{body}"


# name -> (program, exit code)
RUNS = {
    # The ticket's row: the empty body, awaited.
    "empty_body_awaited": (_EMPTY + _main("    await f()\n    3\n"), 3),
    # The body really runs under await: it writes through its parameter.  (By
    # a call: the transform does not yet rewrite a param inside an assignment.)
    "unit_body_runs": (_STORE + "async fn put(p: *i32)\n    store(p, 7)\n\n"
                       + _main("    var x: i32 = 0\n    await put(@x)\n    x\n"), 7),
    # A bare `return` in a unit async fn is `return` from its poll, which ritz0
    # lowers as Ready(0) (`ret i32 0`).
    "unit_bare_return": (_STORE + "async fn put(p: *i32, n: i32)\n    if n > 0\n        return\n    store(p, 9)\n\n"
                         + _main("    var x: i32 = 1\n    await put(@x, 5)\n    x\n"), 1),
    # A unit async fn that does await: its tail is a statement too.
    "unit_with_await": (_STORE + _FORTY_TWO + "async fn put(p: *i32)\n    let v: i32 = await g()\n    store(p, v)\n\n"
                        + _main("    var x: i32 = 0\n    await put(@x)\n    x\n"), 42),
    "no_await_body_awaited": (_FORTY_TWO + _main("    let r: i32 = await g()\n    r\n"), 42),
    # Inside an async fn too.
    "awaited_from_async": (_FORTY_TWO + "async fn h() -> i32\n    let v: i32 = await g()\n    v + 1\n\n"
                           + _main("    await h()\n"), 43),
    # The future itself is still a value: an executor's way in.
    "future_kept": (_EMPTY + _main("    var p: f_Future = f()\n    f_poll(@p)\n    5\n"), 5),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RUNS))
def test_awaited_async_call_runs(tmp_path, name):
    program, want = RUNS[name]
    assert _run("ritz0", None, tmp_path, name, program) == want


# 55_async_state_machine's test_loop_await, which #1395 pinned here as a
# strict xfail: the state machine ran each await once and evaluated only the
# body's tail, so this answered 0.  #3727 made the poll a state machine over the
# whole body; 55 has its test_loop_await back, and this row stays as ritz0's.
_LOOP_AWAIT = ("async fn dbl(x: i32) -> i32\n    x * 2\n\n"
               "async fn loop_await(n: i32) -> i32\n    var sum: i32 = 0\n    var i: i32 = 0\n"
               "    while i < n\n        sum += await dbl(i)\n        i += 1\n    sum\n\n"
               + _main("    let r: i32 = await loop_await(5)\n    r\n"))


@pytest.mark.integration
def test_await_in_a_loop_reruns_each_iteration(tmp_path):
    assert _run("ritz0", None, tmp_path, "loop_await", _LOOP_AWAIT) == 20


_DISCARDED = "calling async fn `{fn}` without `await` builds its future and drops it; its body never runs: write `await {fn}(...)`"
_LET = "`r` is declared `i32` but `g(...)` is an async fn call, which without `await` is its future `g_Future`: write `await g(...)`"

# name -> (program with `^` at the diagnostic, message)
REFUSALS = {
    # The ticket's row: the empty body, not awaited.
    "empty_body_statement": (_EMPTY + _main("    ^f()\n    0\n"), _DISCARDED.format(fn="f")),
    "value_body_statement": (_FORTY_TWO + _main("    ^g()\n    0\n"), _DISCARDED.format(fn="g")),
    # The async transform rewrites h's body into h_poll; the check still sees it.
    "statement_in_async_fn": (_EMPTY + "async fn h() -> i32\n    ^f()\n    1\n\n"
                              + _main("    await h()\n"), _DISCARDED.format(fn="f")),
    # 53/54/55's shape.
    "typed_let": (_FORTY_TWO + _main("    ^let r: i32 = g()\n    r\n"), _LET),
}


def _located(text):
    """`text` without its `^`, and where the `^` was as `line:col`."""
    before = text[:text.index("^")]
    line = before.count("\n") + 1
    return text.replace("^", "", 1), f"{line}:{len(before) - before.rfind(chr(10))}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_async_call_without_await_is_refused(tmp_path, name):
    marked, message = REFUSALS[name]
    src, where = _located(marked)
    got = batching.refused("ritz0", src, _batch_compile(None), at=tuple(map(int, where.split(":"))))
    if got is not None:  # AGAST #2806: this row's diagnostics from its chunk's batch
        out, where = got
    else:
        comp, _ll, _ = _compile("ritz0", None, tmp_path, name, src)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"ritz0 accepted {name}:\n{src}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, message) in found, f"{name}, wanted {where}: {message}\n{src}\n{out[-2000:]}"
