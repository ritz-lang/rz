"""Regression tests for AGAST #3241: `v.push(E.new(..))` in ritz1.

A Vec<E>'s `push` is the UFCS helper `vec_push$E` (emit_ufcs_call,
emitter_expr_call.ritz).  Its scalar-to-newtype box asked get_expr_type whether
the arg was an integer, and get_expr_type has no struct arm for an EXPR_METHOD:
it reports i64.  So a method's `%E` result was boxed with `store i64 %E`, and
clang refused it.  A free call's (`v.push(mk(t, 13))`) was typed and passed
through.  The impl-method path had the same gap and closed it in #2413; both now
ask arg_is_struct_value.

Found in angelo loader/ttf.ritz:109,
`tables.push(TableEntry.new(tag, checksum, offset, length))`.

Each program's exit code is checked on all three compilers (ritz0 the oracle).
"""

import pytest

import test_ritz1_for_header as for_header

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

GVEC = "import ritzlib.gvec\n\n"

PROGRAMS = {
    # The ticket's repro, verbatim: a static method's struct into push.  13 + 1.
    "static_method": (
        GVEC
        + """struct Tag
    b: u32
struct E
    t: Tag
    n: u32
impl E
    pub fn new(t: Tag, n: u32) -> E
        E { t: t, n: n }
pub fn main() -> i32
    var v = vec_with_cap<E>(2)
    let t = Tag { b: 1 }
    v.push(E.new(t, 13))
    let e: E = v[0]
    (e.n + e.t.b) as i32
""",
        14,
    ),
    # An instance method's struct result, pushed twice.  (3 + 4) + (3 + 4).
    "instance_method": (
        GVEC
        + """struct P
    a: u32
    b: u32
impl P
    pub fn me(self: @P) -> P
        P { a: self.a, b: self.b }
pub fn main() -> i32
    var v = vec_with_cap<P>(2)
    let q = P { a: 3, b: 4 }
    v.push(q.me())
    v.push(q.me())
    (v[0].a + v[0].b + v[1].a + v[1].b) as i32
""",
        14,
    ),
    # A single-field struct is the newtype the box is for: a method returning
    # one is still a `%N`, never boxed.  6 + 8.
    "newtype_method": (
        GVEC
        + """struct N
    v: u32
impl N
    pub fn mk(v: u32) -> N
        N { v: v }
pub fn main() -> i32
    var v = vec_with_cap<N>(2)
    v.push(N.mk(6))
    v.push(N.mk(8))
    (v[0].v + v[1].v) as i32
""",
        14,
    ),
    # angelo's shape: a four-u32 TableEntry built by a static `new`.
    "ttf_table_entry": (
        GVEC
        + """struct TableEntry
    tag: u32
    checksum: u32
    offset: u32
    length: u32
impl TableEntry
    pub fn new(tag: u32, checksum: u32, offset: u32, length: u32) -> TableEntry
        TableEntry { tag: tag, checksum: checksum, offset: offset, length: length }
pub fn main() -> i32
    var tables = vec_with_cap<TableEntry>(1)
    var i: u32 = 0
    while i < 3
        tables.push(TableEntry.new(i, 1, 2, i * 3))
        i = i + 1
    let t: TableEntry = tables[2]
    (t.tag + t.checksum + t.offset + t.length + tables.len as u32) as i32
""",
        14,
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_push_a_method_struct_result(run_with, name, compiler):
    program, expected = PROGRAMS[name]
    assert run_with(compiler, name, program) == expected
