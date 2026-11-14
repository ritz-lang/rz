"""AGAST #3016: a module-level `var` of a generic struct type has the struct's layout.

    struct Box<T>
        ptr: *T
    var gb: Box<H>
    ...
    gb.ptr = @h        # ritz0 was ValueError "Invalid type for field assignment: i8"

ritz0's monomorphiser found generic instantiations in fn signatures, bodies and
struct fields, but never in a module-level `var`'s type.  A `Box<H>` named only
by a global was never specialised, so the global fell back to the opaque `i8`
placeholder and every store, read and `@` of it went wrong.  ritz1 already
lowered each of these.

Each program returns 0, or the number of the first check that failed.
"""

from pathlib import Path

import pytest

from test_borrow_param_ref_field import _run

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

_BOX = "struct Box<T>\n    ptr: *T\n\nstruct H\n    k: i64\n\n"
# `pad` first, so `v` is not at offset 0: an i8-sized global, or a GEP that
# misses the field index, reads the wrong word.
_P = "struct P<T>\n    pad: i64\n    v: T\n\n"
_MAIN = "pub fn main() -> i32\n"

PROGRAMS = {
    # A store to the global's field and a read back through it.  Box<H> is
    # spelled nowhere but the global's type: a fn signature or let naming it
    # would instantiate it and hide the bug.
    "box": (_BOX + "var gb: Box<H>\n\n"
            + _MAIN + "    var h: H\n    h.k = 9\n    gb.ptr = @h\n"
            "    if gb.ptr.k != 9\n        return 1\n    return 0\n"),
    # `@gb` is a pointer to the struct, not to an i8.
    "address": (_BOX + "var gb: Box<H>\n\n"
                + _MAIN + "    var h: H\n    h.k = 9\n    gb.ptr = @h\n"
                "    let p = @gb\n    if p.ptr.k != 9\n        return 1\n    return 0\n"),
    # Two instances of a user generic struct, each sized by its own T: an i64
    # value that does not fit an i32 shows a shared or wrong layout.
    "two_instances": (_P + "var gi: P<i32>\nvar gl: P<i64>\n\n" + _MAIN
                      + "    gi.v = 7\n    gl.v = 1099511627776\n    gi.pad = 3\n"
                      "    if gi.v != 7\n        return 1\n"
                      "    if gl.v != 1099511627776\n        return 2\n"
                      "    if gi.pad + gi.v != 10\n        return 3\n    return 0\n"),
    # An array of a generic struct, global.
    "array": (_P + "var ga: [2]P<i64>\n\n" + _MAIN
              + "    ga[1].v = 1099511627776\n    ga[0].v = 5\n"
              "    if ga[1].v != 1099511627776\n        return 1\n"
              "    if ga[0].v != 5\n        return 2\n    return 0\n"),
}


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


# ritz1 gaps found here, each "unhandled EXPR_MEMBER": a member of an element of
# a global array of a generic struct (#3025), and a member through `let p = @g`
# of any struct global (#3026).  Strict, so each fix flips its row.
_RITZ1_GAPS = {"array": "AGAST #3025", "address": "AGAST #3026"}


def _row(compiler, name):
    if name in _RITZ1_GAPS and compiler != "ritz0":
        return pytest.param(compiler, name, marks=pytest.mark.xfail(
            strict=True, reason=_RITZ1_GAPS[name]))
    return pytest.param(compiler, name)


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", [_row(c, n) for n in sorted(PROGRAMS)
                                           for c in COMPILERS])
def test_a_global_of_a_generic_struct(run_with, compiler, name):
    assert run_with(compiler, name, PROGRAMS[name]) == 0
