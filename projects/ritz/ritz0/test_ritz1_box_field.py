"""AGAST #3006: a field of a `Box<T>`, read as a value, is the field of the T it points at.

    var b: Box<H>
    if b.k != 9         # ritz1 was "Unknown field 'k' in struct 'Box$H'"

ritz0 (the oracle) reads `b.f` through the Box's `ptr` whenever it evaluates the
member as a value: `b.k`, `b.q.x`, `let q = b.q`, `f(b.k)`, wherever the Box
lives.  #2426 taught ritz1 that only inside a `for`.  ritz1 now does it in the
general member path (emit_member_ptr / resolve_member_chain_field), and the `for`
arm uses that path too.

ritz0 does not reach a Box's field as a *place*: `b.a[1]`, `b.a[1] = 7`, `b.k = 1`,
`b.ps[1].x` and `@b.a` are all "Unknown field ... in struct 'Box$H'" there, so
ritz1 refuses them as well (test_a_box_field_is_no_place).  The ticket asked for
those to work; that is a language decision for ritz0 first (#3015).

A Box's own field still comes first: `b.ptr` is the Box's `*T` (#2426's pin, in
test_ritz1_for_iterable.py).

Each program returns 0, or the number of the first check that failed.
"""

import subprocess
from pathlib import Path

import pytest

from test_borrow_param_ref_field import _compile, _run
from test_ritz1_for_header import _emit, _link

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

MAIN = "pub fn main() -> i32\n"


@pytest.fixture
def compile_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _compile("ritz0", None, tmp_path, name, program)
        return _compile("ritz1", bins[compiler], tmp_path, name, program)
    return go


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    bins = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        if compiler == "ritz0":
            return _run("ritz0", None, tmp_path, name, program)
        return _run("ritz1", bins[compiler], tmp_path, name, program)
    return go


_BOX = "struct Box<T>\n    ptr: *T\n\n"
# `k` first, so no field of H sits at offset 0: a read that misses the Box's
# dereference, or GEPs the Box for H's index, reads the wrong word.
_H = ("struct P\n    x: i32\n    y: i32\n\n"
      "struct H\n    k: i64\n    a: [3]i32\n    ps: [2]P\n    q: P\n    p: *P\n\n"
      "fn id(v: i64) -> i64\n    return v\n\n")
_FILL = ("    var h: H\n    h.k = 9\n    h.a[0] = 1\n    h.a[1] = 2\n    h.a[2] = 4\n"
         "    h.ps[1].x = 5\n    h.q.x = 8\n    h.q.y = 3\n    h.p = @h.q\n")
# Every value read ritz0 takes through a Box: a scalar, as an operand and a call
# argument; a member chain through a struct field and through a pointer field; a
# copy of a struct field.
_READS = ("    if {b}.k != 9\n        return 1\n"
          "    if {b}.k + 1 != 10\n        return 2\n"
          "    if id({b}.k) != 9\n        return 3\n"
          "    if {b}.q.x != 8\n        return 4\n"
          "    if {b}.p.y != 3\n        return 5\n"
          "    let c = {b}.q\n    if c.x + c.y != 11\n        return 6\n"
          "    return 0\n")
_HELD = _BOX + _H + MAIN + _FILL + "    var b: Box<H>\n    b.ptr = @h\n"


def _in_fn(sig: str, arg: str) -> str:
    return (_BOX + _H + f"fn f({sig}) -> i32\n" + _READS.format(b="b") + "\n" + MAIN + _FILL
            + f"    var b: Box<H>\n    b.ptr = @h\n    return f({arg})\n")


READS = {
    "local": _HELD + _READS.format(b="b"),
    "param": _in_fn("b: Box<H>", "b"),
    "pointer_param": _in_fn("b: *Box<H>", "@b"),
    "mut_reference_param": _in_fn("b: @&Box<H>", "@&b"),
    "field_of_a_struct": (_BOX + _H + "struct S\n    n: i32\n    b: Box<H>\n\n" + MAIN + _FILL
                          + "    var s: S\n    s.b.ptr = @h\n" + _READS.format(b="s.b")),
    "array_element": (_BOX + _H + MAIN + _FILL + "    var bs: [2]Box<H>\n    bs[1].ptr = @h\n"
                      + _READS.format(b="bs[1]")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(READS))
def test_a_box_field_reads_the_inner_structs(run_with, compiler, name):
    assert run_with(compiler, name, READS[name]) == 0


# A Box held in a Vec: `vv[0].k`.  Linked with the real allocator, which a Vec's
# push needs (test_ritz1_for_header.py's _link).
_VEC = ("import ritzlib.gvec\n\n" + _BOX + "struct H\n    k: i64\n\n" + MAIN
        + "    var h: H\n    h.k = 9\n    var b: Box<H>\n    b.ptr = @h\n"
        "    var vv: Vec<Box<H>> = vec_new<Box<H>>()\n    vv.push(b)\n"
        "    if vv[0].k != 9\n        return 1\n    return 0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_box_in_a_vec(ritz1_bin, tmp_path, compiler):
    src, ll = tmp_path / "main.ritz", tmp_path / "main.ll"
    src.write_text(_VEC)
    comp = _emit(compiler, ritz1_bin, src, ll)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    link, exe = _link(compiler, ritz1_bin, ll, tmp_path)
    assert link.returncode == 0, link.stderr
    assert subprocess.run([str(exe)], capture_output=True, timeout=60).returncode == 0


# A Box's field as a place: ritz0 says "Unknown field '<f>' in struct 'Box$H'" for
# each, and ritz1 refuses each too.  The two index forms name the field as ritz0
# does; a store or an `@` is refused by the place path, which has no Box arm.
PLACES = {
    "index": ("    let x = b.a[1]\n    return x\n", "Unknown field 'a' in struct 'Box$H'"),
    "index_then_field": ("    return b.ps[1].x\n", None),
    "store": ("    b.k = 11\n    return 0\n", None),
    "store_to_an_element": ("    b.a[1] = 7\n    return 0\n", None),
    "address": ("    let r: @[3]i32 = @b.a\n    return 0\n", None),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PLACES))
def test_a_box_field_is_no_place(compile_with, compiler, name):
    body, message = PLACES[name]
    comp, ll, _ = compile_with(compiler, name, _HELD + body)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert not ll.exists()
    if compiler == "ritz0":
        assert "in struct 'Box$H'" in out, out
    elif message is not None:
        assert message in out, out
