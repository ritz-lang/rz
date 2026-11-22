"""AGAST #2965: a Vec of a zero-size element grows, on all three compilers.

THE DEFECT

    struct Unit
    pub fn main() -> i32
        var v: Vec<Unit> = vec_new<Unit>()
        v.push(Unit {})
        v.len as i32     # 0; expected 1

vec_grow asked realloc for `new_cap * sizeof(T)` = 0 bytes.  realloc(null, 0)
is malloc(0), which returns null, so vec_grow returned -1 and vec_push
returned -1 without bumping `len`.

THE FIX

vec_grow sets `cap` for a zero `sizeof(T)` without allocating, and points
`data` at a non-null dangling address (no element has bytes to read or write
there).  Neither `Vec.deinit` nor the Vec's scope-end Drop (AGAST #2159) hands
that address to free, which would read a block header below it and fault.
realloc itself is unchanged.

Each program builds through build.py (gvec needs ritzlib.memory) and exits
with its expected code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

UNIT = """\
import ritzlib.gvec

struct Unit

"""

# name: (program, exit code)
PROGRAMS = {
    # `len` counts pushes and pops: 3 after three pushes, 2 after a pop.
    # Before the fix both were 0 (exit 0).
    "zst_push_pop_len": (UNIT + """\
pub fn main() -> i32
    var v: Vec<Unit> = vec_new<Unit>()
    v.push(Unit {})
    v.push(Unit {})
    v.push(Unit {})
    let pushed: i32 = v.len as i32
    let u: Unit = v.pop()
    return pushed * 10 + v.len as i32
""", 32),
    # vec_get of a zero-size element is a valid (empty) value, and the push
    # that put it there succeeded (returned true).
    "zst_get": (UNIT + """\
fn relay(u: Unit) -> Unit
    u

pub fn main() -> i32
    var v: Vec<Unit> = vec_new<Unit>()
    let ok: bool = v.push(Unit {})
    let u: Unit = relay(v.get(0))
    if not ok
        return 1
    return 7
""", 7),
    # Twenty pushes cross the first capacity (8) twice, and the drop at scope
    # end must not free the dangling data pointer.  Exit 20 only if both hold;
    # a free(1) faults instead of returning.
    "zst_grow_drop": (UNIT + """\
fn push_twenty() -> i32
    var v: Vec<Unit> = vec_new<Unit>()
    for i in 0..20
        v.push(Unit {})
    return v.len as i32

pub fn main() -> i32
    return push_twenty()
""", 20),
    # A non-zero element is unchanged: real storage, values read back,
    # and the drop frees it.  1 + 2 + 3 = 6, popped 3, len 2: 6 * 10 + 3 + 2.
    "i32_control": ("""\
import ritzlib.gvec

pub fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    for i in 1..4
        v.push(i as i32)
    let sum: i32 = v.get(0) + v.get(1) + v.get(2)
    let last: i32 = v.pop()
    let r: i32 = sum * 10 + last + v.len as i32
    return r
""", 65),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_gvec_zero_size(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, expected = PROGRAMS[name]
    rc = _run_pkg(compiler, tmp_path, name, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"
