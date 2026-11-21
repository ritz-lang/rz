#!/usr/bin/env python3
"""`[]` through a pointer or reference that isn't a name (AGAST #3816).

`h.get()[0].a` with `get(self: @H) -> @Vec<P>` is element 0 of the Vec the
call returns, as `p[0].a` is on a local `p: @Vec<P>` (LARB R9, #2440).
ritz0 indexed the pointer by whole Vecs, took `h.get()[0]` for the Vec
itself and refused `.a` ("Unknown field 'a' in struct 'Vec$P'"); ritz1 and
ritz1_selfhosted were "unhandled EXPR_MEMBER".  A field holding one,
`w.p[0]`, failed the same way.

The rows split by base shape (method call, function call, field) and by use
(read, store, `+=`), with one scalar and one String element.  `calls` counts
how often the base runs: under `+=` it must be once.  Each row exits with what
its program means, so no compiler is the oracle.
"""

import pytest

import test_ritz1_for_header as for_header
import test_table_rows as table_rows
from test_table_rows import ALL, Row, Run

TYPES = """\
import ritzlib.gvec
import ritzlib.string

struct P
    a: i32

struct H
    v: Vec<P>
    n: Vec<i32>
    s: String
    calls: i32

struct W
    p: *Vec<P>

impl H
    pub fn get(self: @H) -> @Vec<P>
        @self.v
    pub fn get_mut(self: @&H) -> @&Vec<P>
        @&self.v
    pub fn raw(self: *H) -> *Vec<P>
        self.calls += 1
        @self.v
    pub fn ints(self: @H) -> @Vec<i32>
        @self.n
    pub fn str(self: @H) -> @String
        @self.s

fn getv(h: @H) -> @Vec<P>
    @h.v

fn mk() -> H
    var s: String
    s.data = vec_new<u8>()
    s.data.push(120)
    s.data.push(121)
    var h = H { v: vec_new<P>(), n: vec_new<i32>(), s: s, calls: 0 }
    h.v.push(P { a: 5 })
    h.v.push(P { a: 7 })
    h.n.push(11)
    h.n.push(13)
    h

"""


def _row(name, body, want):
    return Row(name, ALL, Run(TYPES + "pub fn main() -> i32\n    var h = mk()\n" + body, want))


TABLE = [
    # The ticket's repro: a method returning `@Vec<P>`, read.
    _row("method_ref_read", "    h.get()[1].a\n", 7),
    _row("fn_ref_read", "    getv(@h)[0].a\n", 5),
    _row("method_mut_ref_store", "    h.get_mut()[1].a = 9\n    h.v[1].a\n", 9),
    # `+=` through a `*Vec<P>` call: the call runs once (calls == 1).
    _row("method_ptr_compound", "    h.raw()[0].a += 3\n    h.v[0].a * 10 + h.calls\n", 81),
    _row("field_ptr_read", "    let w = W { p: @h.v }\n    w.p[1].a\n", 7),
    _row("scalar_elem_read", "    h.ints()[1]\n", 13),
    _row("string_byte_read", "    h.str()[1] as i32\n", 121),
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(TABLE),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(TABLE)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_rows(compiler, table_rows.chunk(TABLE, compiler, chunk),
                           build=for_header.batch_build(ritz1_bin),
                           compile=for_header.batch_compile(ritz1_bin), work=tmp_path)
