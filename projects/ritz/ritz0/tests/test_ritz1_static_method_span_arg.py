"""AGAST #3246: `R.new(@v)`, a static method's `Span<T>` parameter given `@v`
with `v` a `Vec<T>`, gets a Span built from `{ v.data, v.len }`, as the free
call `mk(@v)` does.

Before the fix ritz1 passed the Vec's address as the argument:

    %.3 = ptrtoint ptr %.1 to i64
    call %R @R_new(%Span$u8 %.3)

and clang refused the IR ("'%.3' defined with type 'i64' but expected
'%Span$u8'").  Found in angelo loader/ttf.ritz:181, `Reader.new(@data)`.

AGAST #3247: `@&v` builds the same Span, on the free call and here alike.
`@&` yields the slot's `ptr` where `@` yields its ptrtoint, so ritz1 passed
the borrow's `ptr` as the argument and clang refused the IR ("'%.1' defined
with type 'ptr' but expected '%Span$u8'").

ritz0 is the oracle: each expected exit status is checked against it too.

Every form is a row of one table (test_table_rows.py, AGAST #3889), checked
per compiler as one build linking the ritzlib it imports (test_table_rows.ritzlib_build).
A row keeps the id its parametrised test had, less the compiler
(`test_static_method_span_arg[free_fn-ritz1]` is `static_method_span_arg[free_fn]`
on ritz1).
"""

import pytest

import test_table_rows as table_rows
from test_table_rows import ALL, Row, Run

pytestmark = pytest.mark.integration

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
    # AGAST #3247: `@&v` into a `Span<T>` param, free and static alike.
    "free_fn_mut": ("""\
fn go(data:= Vec<u8>) -> i32
    let r = mk(@&data)
    r.d.len as i32 + 1
""", 3),
    "static_mut_param": ("""\
fn go(data:= Vec<u8>) -> i32
    R.sum(@&data) + 10
""", 13),
    "static_mut_local_second_arg": ("""\
fn go(data:= Vec<u8>) -> i32
    var w = vec_with_cap<u8>(4)
    w.push(5)
    w.push(6)
    let r = R.with(40, @&w)
    r.k + r.d[1] as i32 + data.len as i32
""", 48),
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


ROWS = [Row(f"static_method_span_arg[{name}]", ALL, Run(HEAD + FORMS[name][0] + MAIN, FORMS[name][1]))
        for name in sorted(FORMS)]


@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(ROWS),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(ROWS)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_ritzlib_rows(compiler, table_rows.chunk(ROWS, compiler, chunk), ritz1_bin, tmp_path)
