"""AGAST #4837: a Vec or String slice passed to a method's `[T]` / `Span<T>`
parameter is a view, as it is for a free fn's (LANGUAGE_SPEC §3.4: "unless a
`Span` is expected ... a `Span<T>` (or `[T]`) `let`, return value, argument").

Before the fix ritz1 and ritz1_selfhosted passed vec_slice's copy, a
`%Vec$u8`, where `H_rec` takes a `%Span$u8`, and exited 0 on IR clang refused;
ritz0 refused the program ("parameter `a` is declared `Span$u8` but its
argument is a `Vec$u8`").  The free call `take(v[0..n])` was right on all three.

Each callee folds the length and the bytes it sees into its result, so a
copy, a wrong length or a view at the wrong offset shows as a wrong exit code.
The `push_span` rows read `out` back: Vec<T>.push_span is a generic method.
"""

import pytest

import test_table_rows as table_rows
from test_table_rows import ALL, Row, Run

pytestmark = pytest.mark.integration

HEAD = """\
import ritzlib.gvec
import ritzlib.span
import ritzlib.string

struct H
    n: i64

impl H
    # 100 * len + 10 * a[0] + a[len - 1]
    pub fn rec(self: @H, a: [u8]) -> i64
        self.n + 100 * a.len + 10 * (a[0] as i64) + (a[a.len - 1] as i64)

    # The span after another argument.
    pub fn rec2(self: @H, k: i64, a: Span<u8>) -> i64
        k + 100 * a.len + 10 * (a[0] as i64) + (a[a.len - 1] as i64)

    # A static method: no receiver.
    pub fn count(a: [u8]) -> i64
        100 * a.len + 10 * (a[0] as i64) + (a[a.len - 1] as i64)

fn take(a: [u8]) -> i64
    100 * a.len + 10 * (a[0] as i64) + (a[a.len - 1] as i64)

fn bytes() -> Vec<u8>
    var v: Vec<u8> = vec_new<u8>()
    v.push(1)
    v.push(2)
    v.push(3)
    v.push(4)
    v
"""

W_DECL = """
struct W
    h: H

impl W
    pub fn go(self: @W, v: @Vec<u8>) -> i64
        self.h.rec(v[1..3])
"""

# name -> (main's body, expected exit status[, declarations it needs])
FORMS = {
    # The ticket's repro: a `let` Vec, whole, to a non-generic method.
    "vec_let_whole": ("""\
    let v: Vec<u8> = bytes()
    let h = H { n: 0 }
    (h.rec(v[0..v.len()]) - 300) as i32
""", 114),
    # A `var` Vec, part of it: the view starts at `lo`.
    "vec_var_part": ("""\
    var v: Vec<u8> = bytes()
    v.push(5)
    let h = H { n: 0 }
    (h.rec(v[1..3]) - 100) as i32
""", 123),
    # The span is the method's second argument.
    "vec_second_arg": ("""\
    let v: Vec<u8> = bytes()
    let h = H { n: 0 }
    (h.rec2(7, v[2..4]) - 200) as i32
""", 41),
    # A static method's param: `H.count(v[1..3])`.
    "static_method": ("""\
    let v: Vec<u8> = bytes()
    (H.count(v[1..3]) - 200) as i32
""", 23),
    # A String's bytes, sliced.
    "string_part": ("""\
    var s: String = String.from("abcd")
    let h = H { n: 0 }
    (h.rec(s[1..3]) - 1000 - 200) as i32
""", 79),
    # The receiver is a field of `self`: `self.h.rec(v[1..3])`.
    "self_field_receiver": ("""\
    let v: Vec<u8> = bytes()
    let w = W { h: H { n: 1 } }
    (w.go(@v) - 200) as i32
""", 24, W_DECL),
    # Vec<T>.push_span(span: Span<T>), a generic method.
    "generic_push_span": ("""\
    let v: Vec<u8> = bytes()
    var out: Vec<u8> = vec_new<u8>()
    out.push(9)
    out.push_span(v[1..3])
    (out.len() * 100 + (out.get(1) as i64) * 10 + out.get(2) as i64 - 300) as i32
""", 23),
    # A String's slice is a view in every Span slot, a free fn's too: ritz1
    # passed (and stored) the String, ritz0 refused it.
    "string_free_fn": ("""\
    var s: String = String.from("abcd")
    (take(s[0..3]) - 300 - 970) as i32
""", 99),
    "string_let": ("""\
    var s: String = String.from("abcd")
    let t: [u8] = s[2..4]
    (t.len * 100 + t[1] as i64 - 200) as i32
""", 100),
    # Control: the free call was always a view.
    "free_fn": ("""\
    let v: Vec<u8> = bytes()
    (take(v[1..4]) - 300) as i32
""", 24),
}


def _program(name: str) -> str:
    body, _want, *decls = FORMS[name]
    return HEAD + "".join(decls) + "\npub fn main() -> i32\n" + body


ROWS = [Row(f"method_span_slice_arg[{name}]", ALL, Run(_program(name), FORMS[name][1]))
        for name in sorted(FORMS)]


@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(ROWS),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(ROWS)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_ritzlib_rows(compiler, table_rows.chunk(ROWS, compiler, chunk), ritz1_bin, tmp_path)
