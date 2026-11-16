"""AGAST #3707: a store through a `Span<T>` struct field writes through the view.

`struct H { s: Span<u8> }`, `h.s[i] = x`: the Span is a view, so the store lands
in what it views, and a read of the source after it sees `x`.  ritz1 always did
this.  ritz0 read `h.s[i]` but crashed on the store with an unlocated Python
`ValueError: Cannot index type: %"struct...Span$u8"`: its store path took the
element pointer out of a Vec field only, and handed a Span field to the
general pointer-indexing case.

Each row stores, then reads back through the source (the array or the Vec the
Span views), so a copy instead of a view fails it.  One table per compiler
(test_table_rows.py); the rows separate the paths a Span field is reached by.
"""

import pytest

import test_ritz1_for_header as for_header
import test_table_rows as table_rows
from test_table_rows import Run, case

HEADER = "import ritzlib.gvec\nimport ritzlib.span\n\nstruct H\n    s: Span<u8>\n\n"

# `a` is [1, 2, 3] and `h.s` views all of it.
ARRAY = ("    var a: [3]u8 = [1, 2, 3]\n"
         "    let d: Span<u8> = span_from_ptr<u8>(@a[0], 3)\n"
         "    var h = H { s: d }\n")


def _main(body):
    return f"{HEADER}pub fn main() -> i32\n{body}"


# The ticket's program: a local struct's Span field.
@case()
def a_store_into_a_local_field():
    return Run(_main(ARRAY + "    h.s[1] = 9\n    return a[1] as i32\n"), 9)


# The field reached through a pointer to the struct, `p.s[i]` on a `*H`.
@case()
def a_store_through_a_pointer_to_the_struct():
    return Run(f"{HEADER}fn put(p: *H) -> i32\n    p.s[2] = 7\n    0\n\n"
               f"pub fn main() -> i32\n{ARRAY}    put(@h)\n    return a[2] as i32\n", 7)


# `h.s[i] op= x` reads and stores the same element.
@case()
def a_compound_store():
    return Run(_main(ARRAY + "    h.s[0] += 40\n    return a[0] as i32\n"), 41)


# `@&h.s[i]` is the element's address (the lvalue path's own Vec arm), not a copy's.
@case()
def a_mutable_address_of_an_element():
    return Run(_main(ARRAY + "    let q: *u8 = @&h.s[1]\n    *q = 5\n    return a[1] as i32\n"), 5)


# #1293: a Vec slice into the field is a view, so the store lands in the Vec.
# ritz1 still copies a Vec slice into a struct-literal field: #3706.
@case(compilers=("ritz0",))
def a_store_into_a_vec_view():
    return Run(_main("    var v: Vec<u8> = vec_new<u8>()\n    v.push(1)\n    v.push(2)\n"
                     "    var h = H { s: v[0..2] }\n    h.s[1] = 9\n"
                     "    return *(v.data + 1) as i32\n"), 9)


TABLE = table_rows.cases(globals())


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(TABLE),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(TABLE)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_rows(compiler, table_rows.chunk(TABLE, compiler, chunk),
                           build=for_header.batch_build(ritz1_bin),
                           compile=for_header.batch_compile(ritz1_bin), work=tmp_path)
