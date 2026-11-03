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
both compilers, un-annotated.  ritz0 had the same monomorph gap (AGAST #2095):
its `_infer_value_type` knew nothing of method calls or `a[:]`, so it too
never instantiated a method reached only through such a local.

A generic impl method returning its own generic struct (`w.dup()` on W<i32>)
is covered annotated and un-annotated (AGAST #2096).
"""

import re
import subprocess

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
    # A chain: `t` is inferred from a method on `s`, itself inferred from
    # `a[:]`.  `pop` and `last` are reached only through `t`.
    "slice_chain_only_local_methods": (
        """\
import ritzlib.memory
import ritzlib.gvec

fn main() -> i32
    var a: Vec<i32> = vec_new<i32>()
    a.push(3)
    a.push(4)
    a.push(9)
    var s = a[:]
    var t = s.slice(0, 2)
    let x: i32 = t.pop()
    return x * 10 + t.last() + (t.len() as i32)
""",
        44,
    ),
    # A user impl method returning another generic type; `is_ok` / `is_err`
    # are reached only through `r`.
    "impl_method_result_only_local_methods": (
        """\
import ritzlib.result

struct Gate
    n: i32

impl Gate
    fn check(self: *Gate) -> Result<i32, i32>
        if self.n > 0
            return Ok(self.n)
        return Err(0)

fn main() -> i32
    var g: Gate = Gate { n: 5 }
    var r = g.check()
    return r.is_ok() * 10 + r.is_err()
""",
        10,
    ),
    # AGAST #2096: a generic impl method returning its own generic struct.
    # ritz1 called `W$i32_dup` as `i64 (ptr)` against its `%W$i32 (i64)`
    # definition, annotated or not.
    "generic_impl_method_self_struct_annotated": (
        """\
struct W<T>
    v: T

impl<T> W<T>
    fn dup(self: *W<T>) -> W<T>
        return W<T> { v: self.v + self.v }

fn main() -> i32
    var w: W<i32> = W<i32> { v: 5 }
    let d: W<i32> = w.dup()
    return d.v
""",
        10,
    ),
    "generic_impl_method_self_struct_inferred": (
        """\
struct W<T>
    v: T

impl<T> W<T>
    fn dup(self: *W<T>) -> W<T>
        return W<T> { v: self.v + self.v }

fn main() -> i32
    var w: W<i32> = W<i32> { v: 5 }
    let d = w.dup()
    return d.v
""",
        10,
    ),
    # Same path: `-> T` was `call i64` against `define i32`, so a negative
    # i32 came back unsign-extended; an extra `T` arg must narrow to i32.
    "generic_impl_method_scalar_ret_and_arg": (
        """\
struct B<T>
    v: T

impl<T> B<T>
    fn get(self: *B<T>) -> T
        return self.v
    fn plus(self: *B<T>, d: T) -> B<T>
        return B<T> { v: self.v + d }

fn main() -> i32
    var b: B<i32> = B<i32> { v: 0 - 3 }
    let c = b.plus(10)
    if b.get() < 0
        return c.get()
    return 1
""",
        7,
    ),
}


def _check(compiler: str, tmp_path, name: str) -> None:
    program, want = PROGRAMS[name]
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


@pytest.mark.integration
@pytest.mark.parametrize(
    "name",
    [
        "generic_impl_method_self_struct_annotated",
        "generic_impl_method_scalar_ret_and_arg",
    ],
)
def test_ritz1_spec_method_call_matches_define(ritz1_bin, tmp_path, name):
    """Each call to a specialized `Type$T_method` uses its define's signature.

    The define is a free fn, so its `*W<T>` self is i64 and its `-> T`
    return the concrete type.  LLVM accepts a direct call whose signature
    differs from the define's, so a mismatch need not fail the build (AGAST
    #2096): compare the text.
    """
    src = tmp_path / "main.ritz"
    src.write_text(PROGRAMS[name][0])
    ll = tmp_path / "main.ll"
    comp = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(ll)], capture_output=True, text=True
    )
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()

    def types(arglist: str) -> list[str]:
        # "i64 %self.arg, i32 %d.arg" -> ["i64", "i32"]
        return [a.strip().rsplit(" ", 1)[0] for a in arglist.split(",") if a.strip()]

    defines = {
        m["name"]: (m["ret"], types(m["args"]))
        for m in re.finditer(
            r"^define \S+ (?P<ret>\S+) @(?P<name>\w+\$\w+_\w+)\((?P<args>[^)]*)\)",
            ir,
            re.M,
        )
    }
    assert defines, ir
    calls = list(
        re.finditer(r"= call (?P<ret>\S+) @(?P<name>[\w$]+)\((?P<args>[^)]*)\)", ir)
    )
    checked = 0
    for c in calls:
        if c["name"] in defines:
            assert (c["ret"], types(c["args"])) == defines[c["name"]], c.group(0)
            checked += 1
    assert checked, ir
