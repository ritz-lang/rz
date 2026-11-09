"""AGAST #2427: a global struct read whole is a value of its struct type.

    var gh: H
    fn mk() -> H
        return gh          # ritz1: `load i64, ptr @gh`, which clang rejects

ritz1 loaded every global it read as a value at `emit_llvm_type(var_type)`,
which is i64 for a struct, so each site that takes the whole value got an i64
where it expected `%H`.  ritz0 compiled all of them.  Each site is here, for a
plain struct and for a monomorphised one (`Vec<i32>`, whose name is mangled).

The read is a copy: a later write to the global doesn't reach it.  The canaries
`k` and `z` either side of the array show up a wrong size or offset.

Each program returns 0, or the number of the first check that failed.
"""

import pytest

from test_borrow_param_ref_field import _run
from test_ritz1_for_iterable import COMPILERS, MAIN, SELFHOSTED_BIN


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    """_run, by compiler name.  The gate builds ritz1_selfhosted before pytest."""
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


H = "struct H\n    k: i64\n    a: [3]i32\n    z: i64\n\nstruct W\n    n: i32\n    h: H\n\nvar gh: H\n\n"
FILL = "    gh.k = 11\n    gh.a[0] = 1\n    gh.a[1] = 2\n    gh.a[2] = 4\n    gh.z = 13\n"
# Clobbers the global, so a copy that aliased it would fail its checks.
CLOBBER = "    gh.k = 0\n    gh.a[1] = 0\n    gh.z = 0\n"


def _check(x: str, base: int = 1) -> str:
    """`x` holds what FILL wrote."""
    return (f"    if {x}.k != 11\n        return {base}\n"
            f"    if {x}.a[0] + {x}.a[1] + {x}.a[2] != 7\n        return {base + 1}\n"
            f"    if {x}.z != 13\n        return {base + 2}\n")


SITES = {
    "return": ("fn mk() -> H\n    return gh\n\n" + MAIN + FILL + "    let h: H = mk()\n"
               + CLOBBER + _check("h") + "    return 0\n"),
    "tail": ("fn mk() -> H\n    gh\n\n" + MAIN + FILL + "    let h: H = mk()\n"
             + CLOBBER + _check("h") + "    return 0\n"),
    "var": MAIN + FILL + "    var h: H = gh\n" + CLOBBER + _check("h") + "    return 0\n",
    "let": MAIN + FILL + "    let h: H = gh\n" + CLOBBER + _check("h") + "    return 0\n",
    "argument": ("fn f(h: H) -> i32\n" + _check("h") + "    return 0\n\n" + MAIN + FILL
                 + "    return f(gh)\n"),
    "field_init": (MAIN + FILL + "    var w: W = W { n: 5, h: gh }\n" + CLOBBER + _check("w.h")
                   + "    if w.n != 5\n        return 4\n    return 0\n"),
    "assign_local": (MAIN + FILL + "    var h: H\n    h = gh\n" + CLOBBER + _check("h")
                     + "    return 0\n"),
    "assign_field": (MAIN + FILL + "    var w: W\n    w.h = gh\n" + CLOBBER + _check("w.h")
                     + "    return 0\n"),
    "assign_global": ("var gi: H\n\n" + MAIN + FILL + "    gi = gh\n" + CLOBBER + _check("gi")
                      + "    return 0\n"),
}

GVEC = "import ritzlib.gvec\n\nvar g: Vec<i32>\n\n"
# A header made by hand: the read copies three fields and calls nothing.
VFILL = "    g.data = null\n    g.len = 3\n    g.cap = 9\n"
VCHECK = ("    if v.len != 3\n        return 1\n    if v.cap != 9\n        return 2\n"
          "    if v.data != null\n        return 3\n    return 0\n")
GENERIC_SITES = {
    "var": GVEC + MAIN + VFILL + "    var v: Vec<i32> = g\n    g.len = 0\n" + VCHECK,
    "return": (GVEC + "fn mk() -> Vec<i32>\n    return g\n\n" + MAIN + VFILL
               + "    let v: Vec<i32> = mk()\n    g.len = 0\n" + VCHECK),
    "argument": GVEC + "fn f(v: Vec<i32>) -> i32\n" + VCHECK + "\n" + MAIN + VFILL + "    return f(g)\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(SITES))
def test_a_global_struct_is_read_whole(run_with, compiler, site):
    assert run_with(compiler, f"whole_{site}", H + SITES[site]) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(GENERIC_SITES))
def test_a_generic_global_struct_is_read_whole(run_with, compiler, site):
    assert run_with(compiler, f"gwhole_{site}", GENERIC_SITES[site]) == 0
