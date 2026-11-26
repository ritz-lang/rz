"""AGAST #4843: `v[i].f` on a Vec of move-only elements reads the field in place.

LANGUAGE_SPEC §"`[]` sees through one level": `v[i]` on a Vec is its element in
every position, read, `@`, `@&` and `.f`, so `v[i].f` reads, and `@v[i].f`
borrows, the field where it is.  Read by value, the element is a read through
a reference: for a move-only element that's "cannot move out of a reference".

ritz0 lowered `v[i]` to a call of the by-value `Vec<T>.get`, so it instantiated
`get` at the element type, and for a move-only `T` that body's `*(self.data +
idx)` was refused inside gvec.ritz, whatever the program did with the element:

    var v: Vec<Line> = ...          # Line owns a Vec<u8>: move-only
    v[0].term                       # ritz0: gvec.ritz:235:16: cannot move out of a reference

(`./rz build projects/buddhafinger` failed there.)  ritz1 read it in place, but
took a whole element by value, `let x: Line = v[0]`, which gave it two owners:
the binding and the Vec.  Every compiler now refuses that one at the program's
own `v[0]`, as it does `p[0]` through a reference.

Behind that error buddhafinger's buffer.ritz met a second one: an `@self` method
on a slice, `all[a..b].copy_from(src)`, was "can't take the address of a slice"
on ritz0.  A slice is a new value with no place, so it's lent a spill, as any
rvalue receiver is; ritz1 already did.
"""

import pytest

import test_table_rows as table_rows
from ref_rules import MOVE_OUT_OF_REF
from test_ref_into_value import COMPILERS
from test_table_rows import Row, Run, _refusal

pytestmark = pytest.mark.integration

HEADER = """\
import ritzlib.gvec

struct Line
    bytes: Vec<u8>
    term: i32

fn eat(l: Line) -> i32
    l.term

fn eat_bytes(b: Vec<u8>) -> i64
    b.len()

pub fn main() -> i32
    var v: Vec<Line> = vec_new<Line>()
    var b: Vec<u8> = vec_new<u8>()
    b.push(1)
    b.push(2)
    v.push(Line { bytes: b, term: 3 })
"""

# Each exits 3, read from the element in place.
READS = {
    "field": "    v[0].term\n",
    "field_method": "    (v[0].bytes.len() as i32) + 1\n",
    "borrowed_field": "    let p: @Vec<u8> = @v[0].bytes\n    (p.len() as i32) + 1\n",
    "borrowed_element": "    let e: @Line = @v[0]\n    e.term\n",
    "field_store": "    v[0].term = 1\n    v[0].term + 2\n",
    "mut_field_method": "    v[0].bytes.push(7)\n    (v[0].bytes.len() as i32)\n",
    "index_local": "    let i: i64 = 0\n    v[i].term\n",
}

# Refused at the `^`: a move-only element, or a move-only field of one, by value.
MOVES = {
    "let_element": "    let x: Line = ^v[0]\n    x.term\n",
    "var_element": "    var x = ^v[0]\n    x.term\n",
    "argument": "    eat(^v[0])\n",
    "field": "    let b2: Vec<u8> = ^v[0].bytes\n    b2.len() as i32\n",
    "field_argument": "    eat_bytes(^v[0].bytes) as i32\n",
}

# `all[0..2].copy_from(all[2..4])` writes 3, 4 over 1, 2: 3 + 4 + a len of 2.
SLICE_RECEIVER = """\
import ritzlib.gvec
import ritzlib.span

pub fn main() -> i32
    var v: Vec<u8> = vec_new<u8>()
    v.push(1)
    v.push(2)
    v.push(3)
    v.push(4)
    let all = span_from_vec<u8>(@v)
    all[0..2].copy_from(all[2..4])
    let n: i64 = all[1..3].len
    (*(v.data) as i32) + (*(v.data + 1) as i32) + n as i32
"""

RUNS = [Row(f"a_vec_element_is_a_place[{k}]", (c,), Run(HEADER + READS[k], 3))
        for c in COMPILERS for k in sorted(READS)] + \
       [Row("a_slice_lends_an_at_self_method", (c,), Run(SLICE_RECEIVER, 9)) for c in COMPILERS]
REFUSALS = [Row(f"a_move_only_element_does_not_move_out[{k}]", (c,),
                _refusal(HEADER + MOVES[k], MOVE_OUT_OF_REF))
            for c in COMPILERS for k in sorted(MOVES)]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_vec_element_is_a_place(ritz1_bin, tmp_path, compiler):
    table_rows.assert_ritzlib_rows(compiler, table_rows.for_compiler(RUNS, compiler),
                                   ritz1_bin, tmp_path)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_move_only_element_does_not_move_out(ritz1_bin, tmp_path, compiler):
    table_rows.assert_ritzlib_rows(compiler, table_rows.for_compiler(REFUSALS, compiler),
                                   ritz1_bin, tmp_path)
