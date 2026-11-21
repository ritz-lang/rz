"""AGAST #3973: a `for` variable is an element of what it iterates, in Sema too.

THE GAP

Sema bound a `for` loop variable untyped, so sema_bool_kind answered BK_UNSURE
for a field or method of it, and bool_check refused `if w.d` / `if w.dirty()`
with "ritz1 cannot tell that it is" (prism's compositor/mod.ritz:287 `for
window in self.windows`, angelo's ttf.ritz:64 `for entry in @self.tables`).
ritz0 compiles them.

THE CHANGE

AGAST #3810's sema_bind_for binds the variable with sema_elem_ty: a struct
element of a `[N]S` (local, global or field) or of a `Vec<S>`, through `@` /
`@&` too.  #3973 adds a `Span<S>`, whose element is what its `ptr: *S`
points at, as a Vec's is what `data: *S` does.  Scalar elements and a range's
integer were already judged by bool_check's own note (bool_note_for).

THE TESTS

Each iterable form, with `if w.d` and `if w.dirty()` in the loop, compiles
on all three compilers; and a range's `if i` is "got an integer", not
"cannot tell".  The Span rows failed before the change.
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PRELUDE = """\
import ritzlib.gvec { Vec, vec_new }
import ritzlib.span { Span, span_from_vec }

struct W
    d: bool

impl W
    pub fn dirty(self: @W) -> bool
        self.d

struct H
    ws: Vec<W>
    arr: [2]W
    sp: Span<W>

var g_arr: [2]W

fn main() -> i32
    var ws: Vec<W> = vec_new<W>()
    ws.push(W { d: true })
    ws.push(W { d: false })
    var arr: [2]W = [W { d: true }, W { d: false }]
    g_arr = arr
    var sp: Span<W> = span_from_vec<W>(@ws)
    var h: H = H { ws: vec_new<W>(), arr: arr, sp: sp }
    h.ws.push(W { d: true })
    h.ws.push(W { d: false })
    var n: i32 = 0
"""

# What `for w in <it>` walks.
ITERABLES = {
    "vec": "ws",
    "vec_addr": "@ws",
    "vec_addr_mut": "@&ws",
    "array": "arr",
    "array_addr": "@arr",
    "global_array": "g_arr",
    "vec_field": "h.ws",
    "vec_field_addr": "@h.ws",
    "array_field": "h.arr",
    "span": "sp",
    "span_addr": "@sp",
    "span_field": "h.sp",
}


def _program(it):
    return PRELUDE + (
        f"    for w in {it}\n"
        "        if w.d\n"
        "            n += 1\n"
        f"    for w in {it}\n"
        "        if w.dirty()\n"
        "            n += 1\n"
        "    n\n"
    )


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", ITERABLES)
def test_a_field_or_method_of_a_for_variable_is_a_condition(request, tmp_path, compiler, form):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, f"for_{form}", _program(ITERABLES[form]))
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused `for w in {ITERABLES[form]}`:\n{out}"


RANGE = """\
fn main() -> i32
    var n: i32 = 0
    for i in 0..3
        if i
            n += 1
    n
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_range_variable_is_an_integer(request, tmp_path, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "for_range", RANGE)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted `if i`:\n{out}"
    assert re.search(r":4:12: .*if condition must be bool, got an integer", out), f"{compiler}:\n{out}"
