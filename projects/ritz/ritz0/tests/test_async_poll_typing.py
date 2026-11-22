"""AGAST #3606: an async fn's generated names are unspellable.

`async fn f` makes `f$Future` and `fn f$poll(...) -> bool` (async_transform_v2,
PollAbi / LARB R78).  `$` is not an identifier character in either lexer, so no
source can spell either name.  The typing pass therefore knows nothing about
them (AGAST #3556's `_register_poll` is gone): a rename-era `f_Future` is an
ordinary unknown type and an `f_poll(...)` call is an ordinary undefined
function.  An executor drives a held future through the API instead, with
`future_poll(@&f)`.
"""

import pytest
from name_resolver import resolve_names
from parser import parse
from type_checker import TypeChecker

pytestmark = pytest.mark.unit

ADD_ONE = """
async fn add_one(x: i32) -> i32
    x + 1

"""


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


def names(source: str) -> list:
    return [str(e) for e in resolve_names(parse(source))]


def test_generated_future_type_is_unknown():
    src = ADD_ONE + (
        "fn main() -> i32\n"
        "    var future: add_one_Future = add_one(10)\n"
        "    0\n")
    errors = names(src)
    assert len(errors) == 1 and "Unknown type: add_one_Future" in errors[0], errors


def test_generated_poll_fn_is_undefined():
    src = ADD_ONE + (
        "fn main() -> i32\n"
        "    var future = add_one(10)\n"
        "    if !add_one_poll(@future)\n"
        "        return 1\n"
        "    future.__result\n")
    assert any("undefined function: add_one_poll" in e for e in types(src)), types(src)


def test_a_plain_fn_has_no_poll():
    src = ("fn add_one(x: i32) -> i32\n    x + 1\n\n"
           "fn main() -> i32\n"
           "    let x: i32 = 3\n"
           "    if !add_one_poll(@x)\n"
           "        return 1\n"
           "    0\n")
    assert any("undefined function: add_one_poll" in e for e in types(src))


def test_the_old_names_are_ordinary_user_names():
    # Nothing is generated over a name the module declares itself: `fetch_poll`
    # and `fetch_Future` are plain user names, so they coexist with `fetch`.
    src = ("struct fetch_Future\n    tag: i32\n\n"
           "fn fetch_poll(n: i64) -> i64\n    n\n\n"
           + ADD_ONE.replace("add_one", "fetch") + (
               "fn main() -> i32\n"
               "    let f = fetch_Future { tag: 5 }\n"
               "    let r: i64 = fetch_poll(4)\n"
               "    if f.tag == 5 and r == 4\n"
               "        return 0\n"
               "    var p = fetch(10)\n"
               "    let v: i32 = await p\n"
               "    v\n"))
    assert types(src) == [], types(src)
