#!/usr/bin/env python3
"""A method called on a field, or on an element of a Vec field (AGAST #3622).

`self.f.get(1)` and `self.ws[0].bounds()`: the receiver is a member, or an
element of a `Vec<S>` field.  emit_expr_method dispatches both, but the
resolvers that answer "what does this call return" (`call_callee_def`, behind
`call_result_struct_name`, and `method_recv_type_name`) only knew a name, a
call or another method call as the receiver.  So `match self.f.get(1)` was a
clang error (`'%.7' defined with type '%"Option$i32"' but expected 'i64'`,
angelo's font.ritz), and `self.d.add(self.ws[0].bounds(), 0)` was refused as
"argument 2 of `add` has the wrong type" (prism's compositor).

One row per reader (match, argument, untyped let) per receiver form; each
exits with what it means.
"""

import pytest

from test_ref_into_value import COMPILERS
from test_table_rows import assert_runs

pytestmark = pytest.mark.integration

TYPES = """\
struct Vec<T>
    data: *T
    len: i64
    cap: i64

struct Rc
    w: i32
    h: i32

struct F
    n: i32

impl F
    fn get(self, k: i32) -> Option<i32>
        if k == self.n
            return Some(k + 2)
        None
    fn rc(self) -> Rc
        Rc { w: self.n, h: 4 }

struct Win
    w: i32

impl Win
    fn bounds(self) -> Rc
        Rc { w: self.w, h: 2 }
    fn find(self, k: i32) -> Option<i32>
        if k == self.w
            return Some(k * 2)
        None

struct D
    base: i32

impl D
    fn add(self, r: Rc, k: i32) -> i32
        self.base + r.w + r.h + k

struct G
    f: F
    d: D
    ws: Vec<Win>

impl G
    fn nop(self) -> i32
        0
"""

TAIL = """
fn mk(arr: *Win) -> G
    G { f: F { n: 1 }, d: D { base: 10 }, ws: Vec<Win> { data: arr, len: 2, cap: 2 } }

pub fn main() -> i32
    var arr: [2]Win = [Win { w: 5 }, Win { w: 6 }]
"""


def _prog(method, body):
    """G gets `method` (indented under `impl G`); main runs `body`."""
    return f"{TYPES}{method}{TAIL}{body}"


def _go(lines):
    return "    fn go(self:&) -> i32\n" + "".join(f"        {ln}\n" for ln in lines)


# name: (program, exit code).
ROWS = {
    # `match self.f.get(1)`: a method on a field of self (angelo's font.ritz).
    "member_match_on_self": (_prog(_go([
        "match self.f.get(1)",
        "    Some(d) => d",
        "    None => 7",
    ]), "    var g = mk(@&arr[0])\n    g.go()\n"), 3),
    # ... on a field of a local.
    "member_match_on_local": (_prog("", (
        "    var g = mk(@&arr[0])\n"
        "    match g.f.get(2)\n"
        "        Some(d) => d\n"
        "        None => 7\n")), 7),
    # A field's method result as an argument: typed as the Rc it is.
    "member_as_argument": (_prog(_go([
        "self.d.add(self.f.rc(), 0)",
    ]), "    var g = mk(@&arr[0])\n    g.go()\n"), 15),
    # An untyped `let` of a field's method result, then a field of it.
    "member_untyped_let": (_prog(_go([
        "let r = self.f.rc()",
        "r.w + r.h",
    ]), "    var g = mk(@&arr[0])\n    g.go()\n"), 5),
    # `match self.ws[1].find(6)`: a method on a Vec field's element.
    "vec_elem_match": (_prog(_go([
        "match self.ws[1].find(6)",
        "    Some(d) => d",
        "    None => 7",
    ]), "    var g = mk(@&arr[0])\n    g.go()\n"), 12),
    # A Vec field element's method result as an argument (prism's compositor).
    "vec_elem_as_argument": (_prog(_go([
        "self.d.add(self.ws[0].bounds(), 1)",
    ]), "    var g = mk(@&arr[0])\n    g.go()\n"), 18),
    # An untyped `let` of a Vec field element's method result.
    "vec_elem_untyped_let": (_prog(_go([
        "let b = self.ws[1].bounds()",
        "b.w * b.h",
    ]), "    var g = mk(@&arr[0])\n    g.go()\n"), 12),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_method_on_field_receiver(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
