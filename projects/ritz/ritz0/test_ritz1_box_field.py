"""LARB R17 as amended (AGAST #3015, after #3006): `.` sees through a struct only
through `Deref` / `DerefMut` (LANGUAGE_SPEC §7.7).

    impl<T> Deref for Box<T>            impl<T> DerefMut for Box<T>
        fn deref(self: @Box<T>) -> @T       fn deref_mut(self: @&Box<T>) -> @&T
            @*self.ptr                          @&*self.ptr

`b.f` is the Box's own field first (`b.ptr`), else T's through the trait: a shared
use through `deref(@b)`, a mutable one through `deref_mut(@&b)`. It's a place in
every position, so the stores, `@`, `@&` and `+=` that #3006 refused now run.
Nothing is special by name: a user's `struct Box<T>` with no impl is an ordinary
struct, and `b.x` on it is rule 5's located error.

Each program returns 0, or the number of the first check that failed, unless a
row says what it returns.
"""

import re
import subprocess
from pathlib import Path

import pytest

from test_borrow_param_ref_field import _compile, _run
from test_ritz1_for_header import _emit, _link
from ref_rules import MOVE_OUT_OF_REF
from deref_rules import (deref_mut_alone, needs_deref_mut, neither_has, no_field,
                         targets_differ)

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


# A user Box with both traits: its own `deref`, not ritzlib's, is what `.` calls.
_BOX = ("struct Box<T>\n    ptr: *T\n\n"
        "impl<T> Deref for Box<T>\n    fn deref(self: @Box<T>) -> @T\n        @*self.ptr\n\n"
        "impl<T> DerefMut for Box<T>\n    fn deref_mut(self: @&Box<T>) -> @&T\n"
        "        @&*self.ptr\n\n")
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
    "reference_param": _in_fn("b: @Box<H>", "@b"),
    "field_of_a_struct": (_BOX + _H + "struct S\n    n: i32\n    b: Box<H>\n\n" + MAIN + _FILL
                          + "    var s: S\n    s.b.ptr = @h\n" + _READS.format(b="s.b")),
    "array_element": (_BOX + _H + MAIN + _FILL + "    var bs: [2]Box<H>\n    bs[1].ptr = @h\n"
                      + _READS.format(b="bs[1]")),
    # A module-level Box (AGAST #3016: ritz0 typed the global `i8`).
    "global": (_BOX + _H + "var gb: Box<H>\n\n" + MAIN + _FILL + "    gb.ptr = @h\n"
               + _READS.format(b="gb")),
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


# A Box's field as a place (R17 rule 3): each was "Unknown field" before #3015.
# The values are the `b.ptr.` probes' in the ruling.
_BUMP = "fn bump(p: @&P)\n    p.x += 1\n\n"
_ARR = "fn third(r: @[3]i32) -> i32\n    return r[2]\n\n"
PLACES = {
    "store": ("    b.k = 11\n    return h.k as i32\n", 11),
    "store_to_an_element": ("    b.a[1] = 7\n    return h.a[1]\n", 7),
    "index": ("    let x = b.a[1]\n    return x\n", 2),
    "index_then_field": ("    return b.ps[1].x\n", 5),
    "address": ("    let r: @[3]i32 = @b.a\n    return r[2]\n", 4),
    "address_into_a_call": ("    return third(@b.a)\n", 4),
    "mutable_address": ("    bump(@&b.q)\n    return h.q.x\n", 9),
    "compound_element": ("    b.a[2] += 3\n    return h.a[2]\n", 7),
    "compound": ("    b.k += 2\n    return h.k as i32\n", 11),
    "store_to_a_field": ("    b.q.y = 6\n    return h.q.y\n", 6),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PLACES))
def test_a_box_field_is_a_place(run_with, compiler, name):
    body, expected = PLACES[name]
    program = _BOX + _H + _BUMP + _ARR + MAIN + _FILL + "    var b: Box<H>\n    b.ptr = @h\n" + body
    assert run_with(compiler, name, program) == expected


# Through the trait, not through `ptr`: a wrapper whose `deref` counts its calls
# and keeps its T inline. `deref` serves the reads and `@`, `deref_mut` the
# writes, and `w.n += 1` calls `deref_mut` once (#2529).
COUNTED = """\
struct C
    n: i64
    a: [2]i32

impl C
    fn twice(self: @C) -> i64
        self.n * 2
    fn inc(self: @&C)
        self.n += 1

struct Cell<T>
    v: T

var READS: i32 = 0
var WRITES: i32 = 0

impl<T> Deref for Cell<T>
    fn deref(self: @Cell<T>) -> @T
        READS += 1
        @self.v

impl<T> DerefMut for Cell<T>
    fn deref_mut(self: @&Cell<T>) -> @&T
        WRITES += 1
        @&self.v

"""
COUNTED_RUNS = {
    "read": ("    let x = w.n\n    if x != 3 or READS != 1 or WRITES != 0\n        return 1\n    0\n"),
    "store": ("    w.n = 5\n    if w.v.n != 5 or READS != 0 or WRITES != 1\n        return 1\n    0\n"),
    "compound_once": ("    w.n += 4\n    if w.v.n != 7 or WRITES != 1 or READS != 0\n        return 1\n    0\n"),
    "element_store": ("    w.a[1] = 9\n    if w.v.a[1] != 9 or WRITES != 1\n        return 1\n    0\n"),
    "address": ("    let r: @[2]i32 = @w.a\n    if r[0] != 6 or READS != 1 or WRITES != 0\n"
                "        return 1\n    0\n"),
    # T's methods too: a `self: @T` one through `deref`, a `self: @&T` one
    # through `deref_mut`.
    "method": ("    if w.twice() != 6 or READS != 1 or WRITES != 0\n        return 1\n    0\n"),
    "mutating_method": ("    w.inc()\n    if w.v.n != 4 or WRITES != 1 or READS != 0\n        return 1\n    0\n"),
    # The own field wins (rule 4): `w.v` is Cell's, and calls neither.
    "own_field": ("    let c = w.v\n    if c.n != 3 or READS != 0 or WRITES != 0\n        return 1\n    0\n"),
}
_COUNTED_MAIN = ("pub fn main() -> i32\n    var w: Cell<C>\n    w.v.n = 3\n    w.v.a[0] = 6\n"
                 "    w.v.a[1] = 0\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(COUNTED_RUNS))
def test_a_field_goes_through_the_trait(run_with, compiler, name):
    assert run_with(compiler, name, COUNTED + _COUNTED_MAIN + COUNTED_RUNS[name]) == 0


# `Ro` has `Deref` only: it reads, and refuses every mutable use (rule 5(c)).
_RO = ("struct Ro<T>\n    ptr: *T\n\n"
       "impl<T> Deref for Ro<T>\n    fn deref(self: @Ro<T>) -> @T\n        @*self.ptr\n\n")
_RO_MAIN = MAIN + _FILL + "    var r: Ro<H>\n    r.ptr = @h\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_deref_alone_reads(run_with, compiler):
    program = _RO + _H + _ARR + _RO_MAIN + "    return (r.k as i32) + r.a[1] + third(@r.a)\n"
    assert run_with(compiler, "ro_read", program) == 15


# `for x in r.f` is a read (rule 3): `deref` serves it, so `Deref` alone will do.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_for_over_a_field_through_deref_alone(run_with, compiler):
    program = (_RO + _H + _RO_MAIN + "    var t: i32 = 0\n    for x in r.a\n        t = t + x\n"
               "    return t\n")
    assert run_with(compiler, "ro_for", program) == 7


# Rule 5's errors, located at the field name (`^`). Wrap has a `*T` field whose T
# has `k`, so its error carries the hint; a user Box with `value: T` has none.
_WRAP = "struct Wrap<T>\n    ptr: *T\n\n"
_PLAIN_BOX = "struct Box<T>\n    value: T\n\n"
REFUSALS = {
    "no_deref_hint": (_WRAP + _H + MAIN + _FILL + "    var w: Wrap<H>\n    w.ptr = @h\n"
                      "    return w.^k as i32\n", no_field("Wrap<H>", "k", "w.ptr.k")),
    "no_deref_store": (_WRAP + _H + MAIN + _FILL + "    var w: Wrap<H>\n    w.ptr = @h\n"
                       "    w.^k = 1\n    return 0\n", no_field("Wrap<H>", "k", "w.ptr.k")),
    # #3015's crash on ritz0: a user Box is an ordinary struct.
    "user_box_no_deref": ("struct P\n    x: i32\n\n" + _PLAIN_BOX + MAIN
                          + "    var b: Box<P>\n    b.value.x = 1\n    return b.^x\n",
                          no_field("Box<P>", "x")),
    "neither_has": (_BOX + _H + MAIN + _FILL + "    var b: Box<H>\n    b.ptr = @h\n"
                    "    return b.^zz\n", neither_has("Box<H>", "H", "zz")),
    # One step only: `bb.k` doesn't reach H.
    "one_step": (_BOX + _H + MAIN + _FILL + "    var b: Box<H>\n    b.ptr = @h\n"
                 "    var bb: Box<Box<H>>\n    bb.ptr = @b\n    return bb.^k as i32\n",
                 neither_has("Box<Box<H>>", "Box<H>", "k")),
    "deref_only_store": (_RO + _H + _RO_MAIN + "    r.^k = 11\n    return 0\n",
                         needs_deref_mut("r.k = …", "Ro<H>")),
    "deref_only_element_store": (_RO + _H + _RO_MAIN + "    r.^a[1] = 7\n    return 0\n",
                                 needs_deref_mut("r.a = …", "Ro<H>")),
    "deref_only_compound": (_RO + _H + _RO_MAIN + "    r.^k += 1\n    return 0\n",
                            needs_deref_mut("r.k op= …", "Ro<H>")),
    "deref_only_mutable_address": (_RO + _H + _BUMP + _RO_MAIN + "    bump(@&r.^q)\n    return 0\n",
                                   needs_deref_mut("@&r.q", "Ro<H>")),
}


def _located(text):
    """`text` without its `^`, and where the `^` was as `line:col`."""
    before = text[:text.index("^")]
    line = before.count("\n") + 1
    return text.replace("^", "", 1), f"{line}:{len(before) - before.rfind(chr(10))}"


def _refused(compile_with, compiler, name, marked, message):
    program, where = _located(marked)
    comp, ll, _ = compile_with(compiler, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name}:\n{program}"
    assert not ll.exists()
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, message) in [(w, m.strip()) for w, m in found], \
        f"{compiler}: {name}, wanted {where}: {message}\n{program}\n{out[-2000:]}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_a_field_neither_struct_has_is_refused(compile_with, compiler, name):
    marked, message = REFUSALS[name]
    _refused(compile_with, compiler, name, marked, message)


# Rule 3: `deref` lends the T, so a by-value read of a move-only field is a move
# out of a reference (§13.2), located at the place. A copy field reads.
_MOVE_ONLY = ("struct R\n    n: i32\n\nimpl Drop for R\n    fn drop(self: @&R)\n        self.n = 0\n\n"
              "struct W\n    r: R\n    m: i32\n\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_move_only_field_through_deref_is_not_moved(compile_with, compiler):
    marked = (_BOX + _MOVE_ONLY + MAIN + "    var w: W\n    var b: Box<W>\n    b.ptr = @w\n"
              "    let x = ^b.r\n    return x.n\n")
    _refused(compile_with, compiler, "move_out", marked, MOVE_OUT_OF_REF)


# Rule 1, at the impl's trait name.
_HP = "struct H\n    k: i64\n\nstruct G\n    k: i32\n\n"
IMPL_REFUSALS = {
    "deref_mut_alone": (_HP + "struct W\n    h: H\n\nimpl ^DerefMut for W\n"
                        "    fn deref_mut(self: @&W) -> @&H\n        @&self.h\n\n" + MAIN + "    return 0\n",
                        deref_mut_alone("W")),
    "targets_differ": (_HP + "struct W\n    h: H\n    g: G\n\n"
                       "impl Deref for W\n    fn deref(self: @W) -> @H\n        @self.h\n\n"
                       "impl ^DerefMut for W\n    fn deref_mut(self: @&W) -> @&G\n        @&self.g\n\n"
                       + MAIN + "    return 0\n", targets_differ("W", "H", "G")),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(IMPL_REFUSALS))
def test_a_deref_mut_impl_must_match_a_deref(compile_with, compiler, name):
    marked, message = IMPL_REFUSALS[name]
    _refused(compile_with, compiler, name, marked, message)


# Rule 6 (R11a): a step through the trait is a path step `*`. Two `*` steps on one
# root overlap and the paths are compared on after them; a `*` step overlaps
# every own field of the root, since writing `b.ptr` re-aims it.
def _borrow(here, held, verb="assign", kind="immutable"):
    head = f"cannot assign to `{here}`" if verb == "assign" else f"cannot borrow `{here}` as {verb}"
    return f"{head} - `{held}` is already borrowed as {kind}"


_HELD_B = _BOX + _H + MAIN + _FILL + "    var b: Box<H>\n    b.ptr = @h\n    var g: H\n"
BORROW_CONFLICTS = {
    "same_field": ("    let r: @[3]i32 = @b.a\n    ^b.a[0] = 2\n    return r[0]\n",
                   _borrow("b.a[_]", "b.a")),
    "own_field": ("    let r: @[3]i32 = @b.a\n    ^b.ptr = @g\n    return r[0]\n",
                  _borrow("b.ptr", "b.a")),
    "whole_root": ("    let r: @[3]i32 = @b.a\n    ^b = b\n    return r[0]\n",
                   _borrow("b", "b.a")),
    "mutable_then_read_borrow": ("    let r: @&[3]i32 = @&b.a\n    let q: @i32 = ^@b.a[1]\n"
                                 "    return r[0] + *q\n",
                                 _borrow("b.a[_]", "b.a", "immutable", "mutable")),
}
BORROW_LEGAL = {
    # Different fields behind the same `*`.
    "other_field": ("    let r: @[3]i32 = @b.a\n    b.k = 2\n    return r[2] + (h.k as i32)\n", 6),
    "two_shared": ("    let r: @[3]i32 = @b.a\n    let q: @i64 = @b.k\n    return r[2] + (*q as i32)\n", 13),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(BORROW_CONFLICTS))
def test_a_deref_step_overlaps(compile_with, compiler, name):
    marked, message = BORROW_CONFLICTS[name]
    _refused(compile_with, compiler, name, _HELD_B + marked, message)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(BORROW_LEGAL))
def test_different_fields_behind_a_deref_step_run(run_with, compiler, name):
    body, expected = BORROW_LEGAL[name]
    assert run_with(compiler, name, _HELD_B + body) == expected
