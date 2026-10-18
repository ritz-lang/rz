"""AGAST #1745: a fn pointer to an sret-returning fn is sret too (ritz0).

THE DEFECT

#1736 made a function returning a named struct of at least 256 bytes return
it via sret: `define void @big_make(%Big* sret(%Big) %ret.sret, i32 %n)`.
ritz0's fn-pointer TYPE did not follow, so `let g: fn(i32) -> Big = big_make`
emitted

    bitcast void (%Big*, i32)* @big_make to %Big (i32)*

and the indirect call was `call %Big %g(i32 5)`: the callee wrote through an
sret pointer the caller never passed.  ritz1 was already correct.

THE FIX (the return-side twin of #1739's byval params)

ritz0 lowers `fn(..) -> Big` to `void (%Big*, ..)*`, the physical signature
of every fn it can point at (named fns and closures alike), and an indirect
call through it allocates the result slot and passes it `sret(%Big)`.
"""

import re

import pytest

from test_large_struct_param import BIG_T, MID, _ll
from test_ritz1_builtin_struct_shadow import ritz1_bin  # noqa: F401
from test_ritz1_large_struct_ret import _assert_no_libc_mem, _link_run, _o2_object

COMPILERS = ("ritz0", "ritz1")

FNPTR_RET = (
    MID
    + """
fn take(b: Big) -> i32
    return total(@b)

# sret return AND a byval param through one pointer.
fn twice(b: Big) -> Big
    var c: Big = b
    c.count = c.count * 2
    return c

fn make_via(f: fn(i32) -> Big, n: i32) -> i32
    var b: Big = f(n)
    return total(@b)

fn pass_via(f: fn(Big) -> Big, p: *Big) -> i32
    var r: Big = f(*p)
    return total(@r)

pub fn main() -> i32
    # the ticket repro
    let g: fn(i32) -> Big = big_make
    var x: Big = g(5)
    if total(@x) != 21
        return 1
    # a fn-pointer param
    if make_via(big_make, 2) != 2 + 3 + 4
        return 2
    # the sret result as a by-value arg, straight from the call
    if take(g(1)) != 1 + 2 + 2
        return 3
    # sret return + byval param
    if pass_via(twice, @x) != 10 + 6 + 10
        return 4
    let h: fn(Big) -> Big = twice
    let p: *Big = @x
    var y: Big = h(*p)
    if y.count != 10
        return 5
    # assignment into an existing var
    y = g(7)
    if total(@y) != 7 + 8 + 14
        return 6
    return 42
"""
)

# ritz0's other indirect-call path: a callee that is not an identifier.
# ritz0-only: ritz1 types this sret result i64 (AGAST #1747).
INDEXED_RET = (
    MID
    + """
pub fn main() -> i32
    let fs: [2]fn(i32) -> Big = [big_make, big_make]
    var z: Big = fs[1](3)
    if total(@z) != 3 + 4 + 6
        return 1
    return 42
"""
)

CLOSURE_RET = (
    MID
    + """
pub fn main() -> i32
    let k: fn(i32) -> Big = |n| big_make(n + 1)
    var x: Big = k(4)
    if total(@x) != 5 + 6 + 10
        return 1
    # a capturing closure goes through a per-instance thunk
    let base: i32 = 2
    let k2: fn(i32) -> Big = |n| big_make(n + base)
    var y: Big = k2(1)
    if total(@y) != 3 + 4 + 6
        return 2
    return 42
"""
)

# A fn-pointer type with a first-class %Big return: the miscompile's shape.
FIRST_CLASS_RET = rf"{BIG_T} \([^)]*\)\*"


def _indirect_calls(text: str) -> list:
    return [
        line
        for line in text.splitlines()
        if re.search(r"call [^@]*%[\w.\"]+\(", line) and "Big" in line
    ]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_sret_fn_pointer_type_and_call_are_sret(ritz1_bin, tmp_path, compiler):  # noqa: F811
    text = _ll(compiler, tmp_path, "fnptr_ret", FNPTR_RET).read_text()
    assert not re.search(FIRST_CLASS_RET, text), (
        f"a fn-pointer type returns %Big first-class:\n"
        f"{[ln for ln in text.splitlines() if re.search(FIRST_CLASS_RET, ln)]}"
    )
    indirect = _indirect_calls(text)
    assert indirect, f"no indirect call involving %Big:\n{text[-3000:]}"
    for line in indirect:
        assert re.search(r"call void ", line), (
            f"indirect call is not void (sret):\n{line}"
        )
        assert re.search(rf"sret\({BIG_T}\)", line), (
            f"indirect call passes no sret:\n{line}"
        )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_sret_fn_pointer_runs_at_O2(ritz1_bin, tmp_path, compiler):  # noqa: F811
    ll = _ll(compiler, tmp_path, "fnptr_ret_run", FNPTR_RET)
    obj = _o2_object(ll)
    _assert_no_libc_mem(obj)
    exe = tmp_path / f"fnptr_ret_{compiler}"
    assert _link_run([obj], exe, with_start=(compiler == "ritz1")) == 42


@pytest.mark.integration
def test_sret_closure_pointer_runs_at_O2(tmp_path):
    """A closure behind `fn(i32) -> Big` must have the sret signature too."""
    ll = _ll("ritz0", tmp_path, "closure_ret", CLOSURE_RET)
    text = ll.read_text()
    assert not re.search(FIRST_CLASS_RET, text), (
        "closure fn-pointer returns %Big first-class"
    )
    hdr = [
        ln for ln in text.splitlines() if ln.startswith("define") and "__closure_" in ln
    ]
    assert hdr and "sret" in hdr[0], f"closure is not sret:\n{hdr}"
    obj = _o2_object(ll)
    _assert_no_libc_mem(obj)
    assert _link_run([obj], tmp_path / "closure_ret", with_start=False) == 42


@pytest.mark.integration
def test_sret_fn_pointer_non_identifier_callee_runs_at_O2(tmp_path):
    ll = _ll("ritz0", tmp_path, "indexed_ret", INDEXED_RET)
    for line in _indirect_calls(ll.read_text()):
        assert re.search(rf"call void .*sret\({BIG_T}\)", line), line
    obj = _o2_object(ll)
    _assert_no_libc_mem(obj)
    assert _link_run([obj], tmp_path / "indexed_ret", with_start=False) == 42
