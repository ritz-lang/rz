"""Regression tests for AGAST #1798: an un-annotated local initialised from a
method call takes the method's return type.

    var s = a.slice(0, a.len())     # Vec<i32>, via UFCS -> vec_slice$i32
    var s = a[:]                    # lowers to the same call (#1794)
    var v = b.items()               # user impl method returning Vec<i32>

ritz1's var-decl inference typed a method-call initializer only through a
user impl block, never through UFCS.  `s` stayed the parser's default i64, so
`s.push(5)` / `s.len()` failed "cannot determine receiver type for method
call".  monomorph never recorded `s` either, so a method reached only through
`s` (here `vec_get`, `vec_pop`, `vec_last` -- `a` never calls them) was never
instantiated.  Each `*_only_local_*` program uses such a method.

ritz0 is the oracle: each program's expected exit code is checked against
both compilers.  ritz0 has the same monomorph gap (AGAST #2095), so for the
programs in RITZ0_ANNOTATE it compiles the program with the local annotated
-- the same program, typed the way ritz1 must now infer it.

A generic impl method returning its struct (`let d = w.dup()`, W<i32>) is
inferred too, but its call is mis-emitted even when annotated (AGAST #2096);
that ticket adds the case here.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

PROGRAMS = {
    # The ticket's repro.
    "slice_then_push": (
        """\
import ritzlib.memory
import ritzlib.gvec

fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    a.push(3)
    var s = a.slice(0, a.len())
    s.push(5)
    return s.len() as i32
""",
        2,
    ),
    # `push` and `get` are reached only through `s`.
    "slice_only_local_methods": (
        """\
import ritzlib.memory
import ritzlib.gvec

fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    var s = a.slice(0, a.len())
    s.push(5)
    s.push(6)
    return (s.len() as i32) * 10 + s.get(1)
""",
        26,
    ),
    # `a[:]`; `pop` and `last` are reached only through `s`.
    "full_slice_only_local_methods": (
        """\
import ritzlib.memory
import ritzlib.gvec

fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    a.push(3)
    a.push(4)
    a.push(9)
    var s = a[:]
    let x: i32 = s.pop()
    return x * 10 + s.last() + (s.len() as i32) + (a.len() as i32)
""",
        99,
    ),
    # A user impl method returning a plain struct.
    "impl_method_struct": (
        """\
struct P
    x: i32
    y: i32

impl P
    fn shifted(self: *P, d: i32) -> P
        return P { x: self.x + d, y: self.y }

fn main() -> i32
    var p: P = P { x: 1, y: 2 }
    let q = p.shifted(40)
    return q.x + q.y
""",
        43,
    ),
    # A user impl method returning a Vec; `last` is reached only through `v`.
    "impl_method_vec_only_local_methods": (
        """\
import ritzlib.memory
import ritzlib.gvec

struct Bag
    n: i32

impl Bag
    fn items(self: *Bag) -> Vec<i32>
        var v: Vec<i32> = vec_new<i32>()
        v.push(self.n)
        return v

fn main() -> i32
    var b: Bag = Bag { n: 7 }
    var v = b.items()
    v.push(8)
    return (v.len() as i32) * 10 + v.last()
""",
        28,
    ),
}


# AGAST #2095: ritz0 never instantiates a method reached only through an
# un-annotated method-call local.  Until it does, its oracle run spells the
# local's type out.  Drop an entry once ritz0 compiles the bare program.
RITZ0_ANNOTATE = {
    "slice_only_local_methods": ("var s = ", "var s: Vec<i32> = "),
    "full_slice_only_local_methods": ("var s = ", "var s: Vec<i32> = "),
    "impl_method_vec_only_local_methods": ("var v = ", "var v: Vec<i32> = "),
}


def _check(compiler: str, tmp_path, name: str) -> None:
    program, want = PROGRAMS[name]
    if compiler == "ritz0" and name in RITZ0_ANNOTATE:
        bare, typed = RITZ0_ANNOTATE[name]
        assert program.count(bare) == 1, name
        program = program.replace(bare, typed)
    code = _run_pkg(compiler, tmp_path, name, program)
    assert code == want, f"{compiler} {name}: exit {code}, want {want}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    _check("ritz0", tmp_path, name)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_infers_method_call_local(ritz1_bin, tmp_path, name):
    """`var s = recv.method(..)` takes the method's return type."""
    _check("ritz1", tmp_path, name)
