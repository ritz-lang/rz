"""AGAST #1338: ritzlib's `vec_clone<T>` makes `v.clone()` work on a Vec.

Before it, `var w: Vec<i32> = v.clone()` failed on every compiler with
"No method 'clone' found for type 'Vec$i32'": gvec.ritz had no `vec_clone`
for UFCS to find, so callers hand-rolled one (spectree's `vec_clone_u8`) or
used the full-slice `[:]` idiom.

One program per compiler covers what can go wrong separately:
  - `.clone()` resolves through UFCS, and `v.clone()` directly;
  - the copy has the same length and elements;
  - the copy owns its own buffer: writing or pushing either side leaves the
    other alone (a clone that copied the `data` pointer would alias);
  - an empty Vec clones to an empty Vec;
  - a struct element type is copied field for field.
Each check exits with its own code, so a failure says which one broke.
Built as a package: build.py links ritzlib (malloc/realloc), which a bare
single-file compile does not.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

pytestmark = pytest.mark.integration

PROGRAM = """\
import ritzlib.gvec

struct P
    x: i32
    y: i64

pub fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(10)
    v.push(20)
    v.push(30)

    var w: Vec<i32> = v.clone()
    if w.len() != 3
        return 1
    if w.get(0) != 10 or w.get(1) != 20 or w.get(2) != 30
        return 2

    # The copy must not alias the original, in either direction.
    v.set(1, 99)
    if w.get(1) != 20
        return 3
    w.set(0, 77)
    if v.get(0) != 10
        return 4
    w.push(40)
    if v.len() != 3 or w.len() != 4
        return 5

    var direct: Vec<i32> = v.clone()
    if direct.len() != 3 or direct.get(1) != 99
        return 6

    var empty: Vec<i32> = vec_new<i32>()
    var e2: Vec<i32> = empty.clone()
    if e2.len() != 0
        return 7
    e2.push(5)
    if empty.len() != 0 or e2.get(0) != 5
        return 8

    var ps: Vec<P> = vec_new<P>()
    ps.push(P { x: 1, y: 2 })
    ps.push(P { x: 3, y: 4 })
    var qs: Vec<P> = ps.clone()
    let q: P = qs.get(1)
    if qs.len() != 2 or q.x != 3 or q.y != 4
        return 9
    return 0
"""


@pytest.mark.parametrize("compiler", ["ritz0", "ritz1", "ritz1_selfhosted"])
def test_vec_clone_copies_without_aliasing(ritz1_bin, tmp_path, compiler):
    code = _run_pkg(compiler, tmp_path, "vec_clone", PROGRAM)
    assert code == 0, f"{compiler}: vec_clone check {code} failed (see PROGRAM)"
