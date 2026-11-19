#!/usr/bin/env python3
"""ritz1's `:&` borrow check runs on Sema (AGAST #4244).

A bare argument to a `name:& T` param must be a place of `T`, or the pointer to
one (AGAST #2335, test_bare_place_borrow.py).  ritz1 refuses a temporary, a
place through an `@T`, a place of another type, and an argument it can't type,
as "argument N of `f` has the wrong type: ...".

That check ran in the emitter, and a Sema error stops the compile before
emission (#4011): one unknown call anywhere in the module hid every borrow
error.  call_check.ritz now says it beside the other call checks, so each row
here, a borrow error plus an unrelated Sema error, gets both.  `^` marks where
the borrow error lands.  Each row runs on ritz1 and ritz1_selfhosted.
"""

import re

import pytest

from test_ref_into_value import _compile, _ids, _located

pytestmark = [pytest.mark.integration]

COMPILERS = ["ritz1", "ritz1_selfhosted"]

TYPES = """\
struct C
    x: i32
    y: i64

fn w(r:& i32)
    r = 3

impl C
    fn bump(self:& C, r:& i32)
        r = self.x

    fn mk(r:& i32) -> i32
        r = 1
        0

fn shared(c: @C)
    w(^c.x)

fn other() -> i32
    nope(1)

"""

TEMPORARY = "a `:&` parameter needs a place to borrow, and this is a temporary"
MISFIT = "this place doesn't hold what the `:&` parameter borrows"
SHARED = "a `:&` parameter can't borrow through an `@T`, which is read-only"
UNTYPED = "ritz1 can't tell what this argument is: write `@&` before it"


def _dummy_shared(body: str) -> str:
    """Only one `^` per program: `shared`'s goes when the row is elsewhere."""
    return TYPES.replace("^", "") if "^" in body else TYPES


# name: (main's body, callee, argument number, why)
ROWS = {
    "free_temporary": ("    w(^1 + 2)\n    0\n", "w", 1, TEMPORARY),
    "free_misfit": ("    var n: i64 = 1\n    w(^n)\n    0\n", "w", 1, MISFIT),
    "free_through_shared": ("    0\n", "w", 1, SHARED),
    "free_untyped": ("    w(^*g())\n    0\n", "w", 1, UNTYPED),
    "method_temporary": ("    var c: C = C { x: 1, y: 0 }\n    c.bump(^1 + 2)\n    0\n", "bump", 2, TEMPORARY),
    "static_temporary": ("    C.mk(^1 + 2)\n", "mk", 1, TEMPORARY),
}

G = "fn g() -> *i32\n    null\n\n"


def _program(name: str) -> str:
    body = ROWS[name][0]
    return _dummy_shared(body) + G + "pub fn main() -> i32\n" + body


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", _ids(ROWS))
def test_borrow_error_beside_a_sema_error(tmp_path, compiler, name):
    _, callee, argno, why = ROWS[name]
    src, where = _located(_program(name))
    comp, ll, _ = _compile(compiler, tmp_path, name, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted {name}:\n{src}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert any("Unknown function: nope" in msg for _, msg in found), f"{compiler}: no Sema error:\n{out}"
    said = f"argument {argno} of `{callee}` has the wrong type: {why}"
    assert (where, said) in found, f"{compiler}: {name}, wanted {where}: {said}\n{src}\n{out[-2000:]}"
