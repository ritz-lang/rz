"""AGAST #2529: `x op= v` evaluates the place `x` once.

The parsers spell `x op= v` as `x = x op v`, so a call inside `x` ran twice,
once for the read and once for the store:

    h(@a)[1] += 7           # called h twice on ritz0, ritz1, ritz1_selfhosted

The C-like rule: the place's operands are evaluated once, then the element is
read, modified and written.  Every program returns `calls * K + miss`, where
`miss` is 0 when the store landed and K makes a right count 10.  Each statement
form the parsers build gets a row, since each desugars separately on ritz1.
"""

import pytest

from test_ritz1_array_pointer_index import COMPILERS, run_with  # noqa: F401 (fixture)

pytestmark = pytest.mark.batched

_COUNT = """\
var calls: i32 = 0

struct S
    x: i32
    arr: [3]i32

impl S
    fn me(self: *S) -> *S
        calls = calls + 1
        return self

    fn k(self: *S) -> i64
        calls = calls + 1
        return 0

fn idx(i: i64) -> i64
    calls = calls + 1
    return i

fn h(p: *[3]i32) -> *[3]i32
    calls = calls + 1
    return p

fn cell(p: *i32) -> *i32
    calls = calls + 1
    return p

fn sp(p: *S) -> *S
    calls = calls + 1
    return p

"""

_S = "    var s: S\n    s.x = 4\n    s.arr[0] = 1\n    s.arr[1] = 2\n    s.arr[2] = 3\n"
_PS = "    var t: S\n    var ps: [2]*S = [@s, @t]\n"

PROGRAMS = {
    # `expr op= v`: the general target.
    "call_base_index": _COUNT + "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
                       "    h(@a)[1] += 7\n    return a[1] - 27 + calls * 10\n",
    # `name[k] op= v`.
    "index_call": _COUNT + "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
                  "    a[idx(1)] += 7\n    return a[1] - 27 + calls * 10\n",
    "nested_index_calls": _COUNT + "pub fn main() -> i32\n    var g: [2][3]i32\n    g[1][2] = 1\n"
                          "    g[idx(1)][idx(2)] -= 8\n    return g[1][2] + 7 + calls * 5\n",
    # `*p op= v`.
    "deref_call": _COUNT + "pub fn main() -> i32\n    var x: i32 = 20\n"
                  "    *cell(@x) -= 3\n    return x - 17 + calls * 10\n",
    # `p.f op= v` through a pointer.
    "member_of_element": _COUNT + "pub fn main() -> i32\n" + _S + _PS
                         + "    ps[idx(0)].x *= 3\n    return s.x - 12 + calls * 10\n",
    "member_of_method_index": _COUNT + "pub fn main() -> i32\n" + _S + _PS
                              + "    ps[s.k()].x += 5\n    return s.x - 9 + calls * 10\n",
    # `p.f[k] op= v` through a pointer.
    "member_index_calls": _COUNT + "pub fn main() -> i32\n" + _S + _PS
                          + "    ps[idx(0)].arr[idx(2)] += 5\n    return s.arr[2] - 8 + calls * 5\n",
    "pointer_field_index": _COUNT + "pub fn main() -> i32\n" + _S
                           + "    let p: *S = @s\n    p.arr[idx(1)] += 9\n    return p.arr[1] - 11 + calls * 10\n",
    # `s.f[k] op= v` on a local.
    "local_field_index": _COUNT + "pub fn main() -> i32\n" + _S
                         + "    s.arr[idx(0)] -= 2\n    return s.arr[0] + 1 + calls * 10\n",
    # A float element: the read and the store share the place, not just ints.
    "float_element": _COUNT + "pub fn main() -> i32\n    var f: [2]f64 = [1.5, 2.5]\n"
                     "    f[idx(1)] *= 2.0\n    return (f[1] * 2.0) as i32 - 10 + calls * 10\n",
    # Once per execution: a loop runs the statement three times.
    "loop": _COUNT + "pub fn main() -> i32\n    var a: [3]i32 = [0, 0, 0]\n    var i: i64 = 0\n"
            "    while i < 3\n        a[idx(i)] += 1\n        i = i + 1\n"
            "    return a[0] + a[1] + a[2] - 3 + calls * 3 + 1\n",
    # Once per emission: a `defer` body is emitted at each exit.
    "defer": _COUNT + "fn bump(a: *[3]i32, early: i32) -> i32\n    defer h(a)[0] += 1\n"
             "    if early == 1\n        return 1\n    return 2\n\n"
             "pub fn main() -> i32\n    var a: [3]i32 = [0, 0, 0]\n    bump(@a, 1)\n    bump(@a, 0)\n"
             "    return a[0] - 2 + calls * 5\n",
    # A generic body is a copy of the template, made per instantiation.
    "generic_fn": _COUNT + "fn bump<T>(a: *[3]T, v: T)\n    a[idx(1)] += v\n\n"
                  "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n    bump<i32>(@a, 7)\n"
                  "    return a[1] - 27 + calls * 10\n",
    "generic_two_params": _COUNT + "fn bump<T, U>(a: *[3]T, v: T, u: U)\n    *cell(@a[idx(2)] as *i32) -= v\n\n"
                          "pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n    bump<i32, i64>(@a, 7, 1)\n"
                          "    return a[2] - 23 + calls * 5\n",
    # Control: written out, the read and the store are two places, so two calls
    # (four over two exits), each emission its own.
    "written_out_defer": _COUNT + "fn bump(a: *[3]i32, early: i32) -> i32\n    defer h(a)[0] = h(a)[0] + 1\n"
                         "    if early == 1\n        return 1\n    return 2\n\n"
                         "pub fn main() -> i32\n    var a: [3]i32 = [0, 0, 0]\n    bump(@a, 1)\n    bump(@a, 0)\n"
                         "    return a[0] - 2 + calls * 5 - 10\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_the_place_is_evaluated_once(run_with, name, compiler):  # noqa: F811
    assert run_with(compiler, name, PROGRAMS[name]) == 10


# A field of a `*S` call's result.  ritz1 can't store into one at all yet
# ("unhandled EXPR_MEMBER in assignment", even `sp(@s).x = 3`): AGAST #2879.
RITZ0_ONLY = {
    "member_call": _COUNT + "pub fn main() -> i32\n" + _S
                   + "    sp(@s).x *= 3\n    return s.x - 12 + calls * 10\n",
    "method_member": _COUNT + "pub fn main() -> i32\n" + _S
                     + "    s.me().x += 5\n    return s.x - 9 + calls * 10\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_ONLY))
def test_ritz0_evaluates_a_call_root_once(run_with, name):  # noqa: F811
    assert run_with("ritz0", name, RITZ0_ONLY[name]) == 10
