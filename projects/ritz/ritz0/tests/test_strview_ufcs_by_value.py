"""`v.m(..)` on a StrView reaches a by-value `strview_m(s: StrView, ..)` (#2414).

ritz1 dispatches a method call on a StrView to the free fn `strview_<method>`
(UFCS, emitter_expr_call.ufcs_fn_def) and always passed the receiver as a
`ptr`. Once ritzlib's `strview_*` took their StrView by value, that call put
a pointer where the callee reads `{ptr, len}`: wrong at run time, and clang
did not object, because a call with opaque pointers may disagree with the
callee's declared type. The receiver now goes in as the callee's first
param says, by value or by pointer.

Each row's source declares its own StrView, helpers and forwarding impl, as
ritzlib/strview.ritz does, so it needs no ritzlib: ritz0 calls the impl
method, ritz1 the helper. The exit code is the answer.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

pytestmark = pytest.mark.integration

PRELUDE = """\
struct StrView
    ptr: *u8
    len: i64

fn strview_cnt(s: StrView) -> i32
    s.len as i32

fn strview_plus(s: StrView, other: StrView) -> i32
    (s.len + other.len) as i32

fn strview_plen(s: @StrView) -> i32
    s.len as i32

fn view(n: i64) -> StrView
    StrView { ptr: null, len: n }

impl StrView
    fn cnt(self: StrView) -> i32
        strview_cnt(self)

    fn plus(self: StrView, other: StrView) -> i32
        strview_plus(self, other)

    fn plen(self: @StrView) -> i32
        strview_plen(self)

"""

ROWS = {
    # A local receiver into a by-value first param.
    "local": ("pub fn main() -> i32\n    let v = view(7)\n    v.cnt()\n", 7),
    # Another StrView argument after the by-value receiver.
    "with_arg": ("pub fn main() -> i32\n    let v = view(4)\n    let w = view(5)\n    v.plus(w)\n", 9),
    # The receiver is an `@StrView` param: read through it, passed by value.
    "through_borrow": ("fn g(p: @StrView) -> i32\n    p.cnt()\n\n"
                       "pub fn main() -> i32\n    let v = view(6)\n    g(@v)\n", 6),
    # A struct field receiver.
    "field": ("struct H\n    v: StrView\n\npub fn main() -> i32\n    let h = H { v: view(3) }\n    h.v.cnt()\n", 3),
    # A helper that still takes `@StrView` keeps its pointer receiver.
    "pointer_helper": ("pub fn main() -> i32\n    let v = view(8)\n    v.plen()\n", 8),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", list(ROWS))
def test_strview_method_reaches_by_value_helper(tmp_path, compiler, row):
    src, want = ROWS[row]
    assert _run(compiler, tmp_path, f"sv_{row}", PRELUDE + src) == want
