"""Regression test for AGAST #2194 / #3619: two forms prism's test_input.ritz
had to annotate (#1696) compile un-annotated on all three compilers.

    let events = r.take()      # impl in an imported module, returns Vec<Ev>
    let e = events[0]          # needs vec_get$Ev instantiated
    var h = H { a: vec_new<u32>() }
    h.a.push(1)                # needs Vec$u32's methods instantiated

The first was fixed by 9349e763 (#2442); at 0879eb0a it failed "Vec indexing
requires vec_get$Ev to be defined".  The second was fixed by 1ac3e164 (#3064);
before it, "No method 'push' found for type 'Vec$u32'".

The impl lives in a second module, as prism's InputRouter does.  One program
covers both forms; it is built as a package because build.py is what compiles
and links the imported module.  Red-checked: ritz0 exported at 9349e763^ fails
the first form, at 1ac3e164^ the second, each with the error quoted above.
"""

import pytest
from test_ritz1_builtin_struct_shadow import _run_pkg

pytestmark = pytest.mark.integration

ROUTER = """\
import ritzlib.gvec

pub struct Ev
    code: i32

pub struct Router
    n: i32

impl Router
    pub fn new() -> Router
        return Router { n: 8 }

    pub fn take(self:&) -> Vec<Ev>
        var v: Vec<Ev> = vec_new<Ev>()
        v.push(Ev { code: self.n * 10 })
        return v
"""

MAIN = """\
import ritzlib.gvec
import router { Router, Ev }

struct H
    a: Vec<u32>

pub fn main() -> i32
    var r = Router.new()
    let events = r.take()
    let e = events[0]
    var h = H { a: vec_new<u32>() }
    h.a.push(1)
    h.a.push(1)
    return e.code + h.a.len() as i32
"""


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
def test_imported_impl_vec_index_and_struct_literal_field_push(
    ritz1_bin, tmp_path, compiler
):
    """Both forms, un-annotated: 8 * 10 + two pushes = 82."""
    code = _run_pkg(compiler, tmp_path, "evpkg", MAIN, {"router.ritz": ROUTER})
    assert code == 82, f"{compiler}: exit {code}, want 82"
