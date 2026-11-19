"""The typing pass knows an async fn's poll fn (AGAST #3556).

`async fn f` makes `f_Future` and `fn f_poll(self: *f_Future) -> bool`
(async_transform_v2.PollAbi, LARB R78).  The emitter calls and accepts
`f_poll`; the typing pass answered "undefined function: f_poll", which
refused examples/tier5_async/62_async_compiler, 64_async_io and
75_async_reference once its errors are always reported.
"""

import pytest
from parser import parse
from type_checker import TypeChecker

pytestmark = pytest.mark.unit

ADD_ONE = """
async fn add_one(x: i32) -> i32
    x + 1

"""


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


def test_poll_of_an_async_fn_is_defined():
    src = ADD_ONE + (
        "fn main() -> i32\n"
        "    var future: add_one_Future = add_one(10)\n"
        "    if !add_one_poll(@future)\n"
        "        return 1\n"
        "    future.__result\n")
    assert types(src) == []


def test_poll_answers_bool():
    # PollAbi.RET_TYPE: true once Ready, not the fn's own i32.
    src = ADD_ONE + (
        "fn main() -> i32\n"
        "    var future: add_one_Future = add_one(10)\n"
        "    let ready: i32 = add_one_poll(@future)\n"
        "    ready\n")
    errors = types(src)
    assert len(errors) == 1 and "bool" in errors[0], errors


def test_poll_takes_its_own_future():
    src = ADD_ONE + (
        "fn main() -> i32\n"
        "    let x: i32 = 3\n"
        "    if !add_one_poll(@x)\n"
        "        return 1\n"
        "    0\n")
    errors = types(src)
    assert any("expected *add_one_Future, got @i32" in e for e in errors), errors


def test_a_plain_fn_has_no_poll():
    src = ("fn add_one(x: i32) -> i32\n    x + 1\n\n"
           "fn main() -> i32\n"
           "    let x: i32 = 3\n"
           "    if !add_one_poll(@x)\n"
           "        return 1\n"
           "    0\n")
    assert any("undefined function: add_one_poll" in e for e in types(src))


def test_a_declared_fn_of_the_poll_name_keeps_its_own_signature():
    # Nothing is generated over a fn the module declares itself, declared
    # before the async fn or after it.
    src = "fn add_one_poll(n: i64) -> i64\n    n\n\n" + ADD_ONE + (
        "fn main() -> i32\n"
        "    let r: i64 = add_one_poll(4)\n"
        "    0\n")
    assert types(src) == []
