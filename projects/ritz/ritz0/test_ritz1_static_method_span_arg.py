"""AGAST #3246: `R.new(@v)`, a static method's `Span<T>` parameter given `@v`
with `v` a `Vec<T>`, gets a Span built from `{ v.data, v.len }`, as the free
call `mk(@v)` does.

Before the fix ritz1 passed the Vec's address as the argument:

    %.3 = ptrtoint ptr %.1 to i64
    call %R @R_new(%Span$u8 %.3)

and clang refused the IR ("'%.3' defined with type 'i64' but expected
'%Span$u8'").  Found in angelo loader/ttf.ritz:181, `Reader.new(@data)`.

`@&v` into a `Span<T>` slot is #3247's, on the free call and here alike.

ritz0 is the oracle: each expected exit status is checked against it too.
"""

import pytest

from test_ritz1_move_param import _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEAD = """\
import ritzlib.gvec
import ritzlib.span

struct R
    d: Span<u8>
    k: i32

impl R
    pub fn new(d: Span<u8>) -> R
        R { d: d, k: 0 }

    pub fn with(k: i32, d: Span<u8>) -> R
        R { d: d, k: k }

    pub fn sum(d: Span<u8>) -> i32
        var t: i32 = 0
        for i in 0..d.len
            t = t + d[i] as i32
        t

fn mk(d: Span<u8>) -> R
    R { d: d, k: 0 }

"""

MAIN = """
pub fn main() -> i32
    var v = vec_with_cap<u8>(4)
    v.push(1)
    v.push(2)
    go(v)
"""

# name -> (go's body, expected exit status)
FORMS = {
    # The ticket's repro: a moved-in Vec param, `R.new(@data)`.
    "static_moved_param": ("""\
fn go(data:= Vec<u8>) -> i32
    let r = R.new(@data)
    r.d.len as i32
""", 2),
    # A Vec local, and the element values reach the callee.
    "static_local": ("""\
fn go(data:= Vec<u8>) -> i32
    var w = vec_with_cap<u8>(4)
    w.push(5)
    w.push(6)
    w.push(7)
    R.sum(@w) + data.len as i32
""", 20),
    # The Span is not the first argument.
    "static_second_arg": ("""\
fn go(data:= Vec<u8>) -> i32
    let r = R.with(40, @data)
    r.k + r.d[1] as i32
""", 42),
    # Controls: the free call always converted; `@array` on the static arm.
    "free_fn": ("""\
fn go(data:= Vec<u8>) -> i32
    let r = mk(@data)
    r.d.len as i32
""", 2),
    "static_array": ("""\
fn go(data:= Vec<u8>) -> i32
    let a: [3]u8 = [1, 2, 4]
    R.sum(@a)
""", 7),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(FORMS))
def test_static_method_span_arg(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    body, expected = FORMS[name]
    rc = _run(compiler, tmp_path, HEAD + body + MAIN)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"
