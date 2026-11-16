#!/usr/bin/env python3
"""An untyped `let` of a method returning `*S`, `@S` or `@&S` (AGAST #3620).

`let buf = self.get_draw_buffer_ref()` with `-> @&Vec<u32>`, then
`buf.set(i, px)`: the local points at the struct, as it does when a free fn
returns one (`let m = get(l)`, AGAST #175 / #1453).

ritz1's untyped-`let` inference read a free call's pointer and reference
returns but, for a method call, only a struct, float or scalar-reference
return.  The local stayed an untyped i64, so a method on it was "cannot
determine receiver type for method call" and a field read was "unhandled
EXPR_MEMBER".  prism's MockBackend hit it in fill_rect and draw_line, which
took test_compositor and test_render_commands (19 tests) with it.

One row per return form, plus a generic pointee as prism's Vec<u32> is; each writes
through the local, so a copy instead of a pointer exits wrong.
"""

import pytest

from test_row_table import assert_runs
from test_ref_into_value import COMPILERS

pytestmark = pytest.mark.integration

TYPES = """\
struct P
    n: i32

impl P
    fn inc(self:&)
        self.n = self.n + 1

struct M
    p: P

impl M
    fn mref(self:&) -> @&P
        @&self.p
    fn sref(self: @M) -> @P
        @self.p
    fn ptr(self:&) -> *P
        @&self.p

"""


def _main(body):
    return f"{TYPES}pub fn main() -> i32\n    var m = M {{ p: P {{ n: 4 }} }}\n{body}"


# name: (program, exit code).
ROWS = {
    # `-> @&S`: a method on the local writes m.p.
    "mut_ref_return_then_method": (_main(
        "    let q = m.mref()\n    q.inc()\n    m.p.n\n"), 5),
    # `-> @&S`: a field store through the local writes m.p.
    "mut_ref_return_then_field_store": (_main(
        "    let q = m.mref()\n    q.n = 9\n    m.p.n\n"), 9),
    # `-> @S`: a field read through the local.
    "shared_ref_return_then_field_read": (_main(
        "    let q = m.sref()\n    q.n + 1\n"), 5),
    # `-> *S`: a method on the local writes m.p.
    "pointer_return_then_method": (_main(
        "    let q = m.ptr()\n    q.inc()\n    q.inc()\n    m.p.n\n"), 6),
    # `-> @&W<u32>`, a generic struct, as prism's `-> @&Vec<u32>` is.
    "mut_ref_to_generic_return": ("""\
struct W<T>
    v: T

impl<T> W<T>
    fn set(self:&, v: T)
        self.v = v

struct B
    w: W<u32>

impl B
    fn buf(self:&) -> @&W<u32>
        @&self.w

pub fn main() -> i32
    var b = B { w: W { v: 1 } }
    let w = b.buf()
    w.set(8)
    b.w.v as i32
""", 8),
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_let_of_method_pointer_return(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS)
