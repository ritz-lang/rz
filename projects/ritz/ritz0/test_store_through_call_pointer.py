"""AGAST #2879: a store into a field of a `*S` call's result.

A function or method returning `*S` gives a real place, so

    sp(@s).x = 3            # ritz1: "unhandled EXPR_MEMBER in assignment"
    s.me().x = 4            # same
    sp(@s).arr[2] = 5       # ritz1: "unhandled indexed EXPR_MEMBER in assignment"
                            # ritz0: ValueError: Cannot get address of: Call

store through the returned pointer, calling once.  A method on such a
result, `s.me().me().x = 12` (#2883), takes the returned pointer as its
receiver, so every link runs once; so does a free call's, `sp(@s).me().x`
(#2946).  (#2518's by-value results
are not places; #2517 is ritz1's reads through a `*R` call.)

Each program returns 0 when right, else the number of the first check that
failed.  Reads go through `s` itself, so only the store is under test.
`x op= v` on these places is in test_compound_assign_once.py.
"""

import pytest

from test_ritz1_array_pointer_index import COMPILERS, run_with  # noqa: F401 (fixture)

pytestmark = pytest.mark.batched

_DEFS = """\
var calls: i32 = 0

struct In
    y: i16

struct S
    x: i32
    b: u8
    f: f64
    ok: bool
    w: i64
    arr: [3]i32
    farr: [2]f64
    inner: In
    next: *S

impl S
    fn me(self: *S) -> *S
        calls = calls + 1
        return self

fn sp(p: *S) -> *S
    calls = calls + 1
    return p

fn idx(i: i64) -> i64
    calls = calls + 1
    return i

"""

_ZERO = ("    var s: S\n    var t: S\n    s.x = 0\n    s.b = 0\n    s.f = 0.0\n    s.ok = false\n"
         "    s.w = 0\n    s.arr[0] = 0\n    s.arr[1] = 0\n    s.arr[2] = 0\n    s.farr[0] = 0.0\n"
         "    s.farr[1] = 0.0\n    s.inner.y = 0\n    s.next = @t\n    t.x = 0\n")

# Each row: (store statements, the check that it landed, calls it makes).
STORES = [
    ("sp(@s).x = 3", "s.x == 3", 1),
    ("s.me().x = 4", "s.x == 4", 1),
    ("sp(@s).arr[2] = 5", "s.arr[2] == 5 and s.arr[1] == 0", 1),
    ("sp(@s).arr[idx(1)] = 6", "s.arr[1] == 6 and s.arr[2] == 5", 2),
    ("s.me().arr[0] = 7", "s.arr[0] == 7", 1),
    # Each field width stores its own width: a neighbour is untouched.
    ("sp(@s).b = 200", "s.b == 200 and s.x == 4", 1),
    ("sp(@s).f = 2.5", "s.f == 2.5", 1),
    ("sp(@s).ok = true", "s.ok", 1),
    ("sp(@s).w = 0 - 9", "s.w == 0 - 9", 1),
    ("sp(@s).farr[1] = 1.5", "s.farr[1] == 1.5 and s.farr[0] == 0.0", 1),
    # Through a field of the result.
    ("sp(@s).inner.y = 0 - 3", "s.inner.y == 0 - 3", 1),
    ("sp(@s).next.x = 8", "t.x == 8 and s.x == 4", 1),
    # A pointer receiver, and a call in the call.
    ("let p: *S = @s\n    p.me().x = 11", "s.x == 11", 1),
    ("sp(sp(@s)).arr[2] = 13", "s.arr[2] == 13", 2),
    # AGAST #2883: a method on a `*S` method's result -- the returned pointer
    # is the receiver, so each link runs once and the store lands in `s`.
    ("let q: *S = s.me().me()\n    q.x = 9", "s.x == 9", 2),
    ("s.me().me().x = 12", "s.x == 12", 2),
    ("let r: i32 = s.me().me().x", "r == 12", 2),
    ("s.me().me().x += 5", "s.x == 17", 2),
    ("s.me().me().me().arr[1] = 14", "s.arr[1] == 14", 3),
    # AGAST #2946: a method on a `*S` free call's result -- the same, with a
    # free function as the first link.
    ("let q2: *S = sp(@s).me()\n    q2.x = 21", "s.x == 21", 2),
    ("sp(@s).me().x = 22", "s.x == 22", 2),
    ("let r2: i32 = sp(@s).me().x", "r2 == 22", 2),
    ("sp(@s).me().x += 3", "s.x == 25", 2),
    ("sp(@s).me().me().arr[0] = 23", "s.arr[0] == 23", 3),
    ("sp(sp(@s)).me().w = 24", "s.w == 24", 3),
]


def _program() -> str:
    body = _ZERO
    want = 0
    for n, (store, check, k) in enumerate(STORES, start=1):
        want += k
        body += (f"    {store}\n    if not ({check})\n        return {n}\n"
                 f"    if calls != {want}\n        return {100 + n}\n")
    return _DEFS + "pub fn main() -> i32\n" + body + "    return 0\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_field_of_a_pointer_call_is_a_place(run_with, compiler):  # noqa: F811
    assert run_with(compiler, "store_through_call", _program()) == 0
