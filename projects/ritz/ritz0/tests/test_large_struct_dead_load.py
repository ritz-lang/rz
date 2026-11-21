"""AGAST #3952: no dead first-class load of a large struct reaches clang.

THE DEFECT

After every sret call ritz1 loaded the result slot as a first-class value:

    call void @resp_new(ptr sret(%Resp) %.3, i32 200)
    %.4 = load %Resp, ptr %.3
    call void @__ritz_sret_copy(ptr %ret.sret, ptr %.3, i64 ...)

#1732's rewrite turns the matching `store` into the copy call and leaves the
load dead "for -O2 to delete".  -O2 does not delete it first: IPSCCP and
InstCombine expand it per leaf.  spire's lib/presenter/mod.ritz, with ~20 dead
`load %Response` (a [65536 x i8] body each), ran clang -O2 past build.py's
300 s bound and out of memory.  Five spire test files failed the same way
(`./rz test spire --compiler ritz1`).

THE FIX

ritz1's rewrite_large_struct_copies drops every large-struct `load` whose
register has no use.  ritz0 never emitted these loads.
"""

import pytest

from test_large_struct_copy import _ll
from test_ritz1_large_struct_ret import _o2_object

COMPILERS = ("ritz0", "ritz1", "ritz1_selfhosted")

# The shape of spire's Response: a 64 KB inline body.
DECLS = """\
struct Resp
    status: i32
    body: [65536]u8
    len: i64

extern fn resp_new(code: i32) -> Resp
extern fn resp_set(r: *Resp, code: i32)
"""

SHAPES = """
pub fn tail_call() -> Resp
    resp_new(200)

pub fn return_call() -> Resp
    return resp_new(201)

pub fn modify_then_return(code: i32) -> Resp
    var r: Resp = resp_new(200)
    resp_set(@r, code)
    r

pub fn discard()
    resp_new(1)

fn inner(code: i32) -> Resp
    resp_new(code)

pub fn chained() -> Resp
    inner(7)

pub fn used_field() -> i32
    let r = resp_new(3)
    r.status
"""

# Enough wrappers that the dead loads cost clang -O2 well past the 20 s bound
# (about 0.5 s each before the fix).
MANY = "".join(f"\npub fn w{i}() -> Resp\n    resp_new({i})\n" for i in range(64))


def _first_class_resp_loads(text: str) -> list:
    # `load %Resp, ptr` (ritz1) / `load %"struct.m.Resp", ptr` (ritz0); a
    # field load (`load i32, ptr`) or pointer load is fine.
    return [
        ln.strip()
        for ln in text.splitlines()
        if "load %" in ln and "Resp" in ln.split("load %", 1)[1].split(",", 1)[0]
    ]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_no_dead_large_struct_load_survives(ritz1_bin, tmp_path, compiler):
    text = _ll(compiler, tmp_path, "dead_load", DECLS + SHAPES).read_text()
    loads = _first_class_resp_loads(text)
    assert not loads, f"first-class large-struct loads survive: {loads}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_many_sret_wrappers_compile_at_O2_within_bound(ritz1_bin, tmp_path, compiler):
    _o2_object(_ll(compiler, tmp_path, "many_wrappers", DECLS + MANY))
