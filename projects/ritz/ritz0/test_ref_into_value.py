#!/usr/bin/env python3
"""A reference doesn't fit a by-value slot, and nothing moves out through one
(LANGUAGE_SPEC §13.2-13.4, LARB ruling R1, AGAST #2336).

Rule 1: an `@T`, `@&T` or `*T` where a `T` goes is a located error at every
slot: there's no implicit deref. `@x` into a by-value slot is the same mistake.
Rule 2: `*r`, `r.f`, `p[i]` and a by-value `self` read a copy type through a
reference, and are "cannot move out of a reference" for a move-only one, behind
`@T`, `@&T`, `*T` and `:&` alike, checked after monomorphisation.
`ptr_read<T>` is the escape: the caller takes ownership of what it reads.

Each row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must report
the same `line:col: message`.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link

from ref_rules import ADDR_INTO_VALUE, MOVE_OUT_OF_REF, REF_INTO_VALUE
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

REFS = {"shared": "@C", "mutable": "@&C", "pointer": "*C"}

COPY = """\
struct C
    x: i32

struct W
    c: C

enum E
    V(C)
    N

impl C
    fn get(self: C) -> i32
        self.x
    fn plus(self: @C, o: C) -> i32
        self.x + o.x

fn val(c: C) -> i32
    c.x

"""

# Rule 1's slots. `{R}` is the reference type; `^` marks where the error lands.
SLOTS = {
    "argument": "fn f(r: {R}) -> i32\n    val(^r)\n",
    "method_argument": "fn f(r: {R}, d: C) -> i32\n    d.plus(^r)\n",
    "let": "fn f(r: {R}) -> i32\n    let d: C = ^r\n    d.x\n",
    "var": "fn f(r: {R}) -> i32\n    var d: C = ^r\n    d.x\n",
    "assign": "fn f(r: {R}, e: C) -> i32\n    var d: C = e\n    d = ^r\n    d.x\n",
    "field_assign": "fn f(r: {R}, e: C) -> i32\n    var w = W { c: e }\n    w.c = ^r\n    w.c.x\n",
    "return": "fn f(r: {R}) -> C\n    return ^r\n",
    "tail": "fn f(r: {R}) -> C\n    ^r\n",
    "field": "fn f(r: {R}) -> i32\n    let w = W { c: ^r }\n    w.c.x\n",
    "element": "fn f(r: {R}) -> i32\n    let a: [1]C = [^r]\n    a[0].x\n",
    "payload": "fn f(r: {R}) -> i32\n    let e: E = E.V(^r)\n    0\n",
    "if_arm": "fn f(r: {R}, b: i32) -> C\n    if b > 0\n        ^r\n    else\n        *r\n",
    "match_arm": "fn f(r: {R}, b: i32) -> C\n    match b\n        0 => ^r\n        _ => *r\n",
    "generic_instance": "fn g<T>(r: *T) -> T\n    return ^r\n\nfn f(r: {R}) -> C\n    g<C>(r)\n",
}

# What the value is, rather than where it lands.
SHAPES = {
    "self": "impl C\n    fn me(self: @C) -> C\n        return ^self\n",
    "scalar_argument": "fn v(n: i32) -> i32\n    n\n\nfn f(r: @i32) -> i32\n    v(^r)\n",
    "scalar_return": "fn f(r: *i32) -> i32\n    return ^r\n",
    "scalar_let": "fn f(r: @&i32) -> i32\n    let n: i32 = ^r\n    n\n",
    "i64_let": "fn f(r: *i64) -> i64\n    let n: i64 = ^r\n    n\n",
    "i64_return": "fn f(r: @i64) -> i64\n    return ^r\n",
    "float_return": "fn f(r: @f64) -> f64\n    return ^r\n",
    "inferred_reference": "fn f(d: C) -> i32\n    let p = @d\n    val(^p)\n",
    "inferred_scalar": "fn v(n: i32) -> i32\n    n\n\nfn f(n: i32) -> i32\n    let p = @n\n    v(^p)\n",
    "global_pointer": "var G: *C = null\n\nfn f() -> i32\n    val(^G)\n",
    "pointer_field": "struct P\n    p: *C\n\nfn f(q: P) -> i32\n    val(^q.p)\n",
    "call_result": "fn g(r: *C) -> *C\n    r\n\nfn f(r: *C) -> i32\n    val(^g(r))\n",
    "reference_result": "fn g(r: @C) -> @C\n    r\n\nfn f(r: @C) -> i32\n    val(^g(r))\n",
    "method_result": "impl C\n    fn me(self: @C) -> @C\n        self\n\nfn f(r: @C) -> i32\n    val(^r.me())\n",
    "offset": "fn f(r: *C) -> i32\n    val((^r + 1))\n",
    "cast": "fn f(n: i64) -> i32\n    val(^n as *C)\n",
    "some_payload": "fn f(r: @C) -> Option<C>\n    return Some(^r)\n",
    "array_fill": "fn f(r: @C) -> i32\n    let a: [2]C = [^r; 2]\n    a[1].x\n",
    "nested_call": "fn f(r: @C) -> i32\n    val(C { x: val(^r) })\n",
    "element_store": "fn f(r: @C, e: C) -> i32\n    var a: [1]C = [e]\n    a[0] = ^r\n    a[0].x\n",
    "through_a_pointer": "fn f(r: @C, q: *C)\n    *q = ^r\n",
    "field_through_a_pointer": "fn f(r: @C, q: *W)\n    q.c = ^r\n",
    "nested_arm": "fn f(r: @C, b: i32) -> C\n    if b > 0\n        if b > 1\n            ^r\n        else\n            *r\n    else\n        *r\n",
    "statement_arm_return": "fn f(r: @C, b: i32) -> C\n    match b\n        0 => return ^r\n        _ => return *r\n",
    "bare_payload": "fn f(r: @C) -> i32\n    let e = V(^r)\n    0\n",
    "tuple_element": "fn f(r: @C) -> i32\n    let t: (C, i32) = (^r, 1)\n    t.1\n",
    "fn_pointer": "fn f(r: @C, g: fn(C) -> i32) -> i32\n    g(^r)\n",
    "assign_in_an_arm": "fn f(r: @C, e: C, b: i32) -> i32\n    var d = e\n    match b\n        0 => d = ^r\n        _ => d = *r\n    d.x\n",
    "value_arm": "fn f(r: @C, b: i32) -> i32\n    let d: C = if b > 0\n        ^r\n    else\n        *r\n    d.x\n",
}

# ritz1 doesn't record what an un-annotated `let p = @n` points at for a scalar.
SHAPE_GAPS = {"inferred_scalar": 2352, "tuple_element": 1526}

ADDR_SLOTS = {
    "shared": "fn f(d: C) -> i32\n    val(^@d)\n",
    "mutable": "fn f(e: C) -> i32\n    var d = e\n    val(^@&d)\n",
    "field": "fn f(w: W) -> i32\n    val(^@w.c)\n",
    "method_argument": "fn f(d: C) -> i32\n    d.plus(^@d)\n",
}

# The same reads, written out: what rule 1's error tells you to do.
READS = {
    "argument": ("fn f(r: {R}) -> i32\n    val(*r)\n", 3),
    "let": ("fn f(r: {R}) -> i32\n    let d: C = *r\n    d.x\n", 3),
    "assign": ("fn f(r: {R}) -> i32\n    var d = C { x: 0 }\n    d = *r\n    d.x\n", 3),
    "return": ("fn g(r: {R}) -> C\n    return *r\n\nfn f(r: {R}) -> i32\n    var d = g(r)\n    d.x\n", 3),
    "tail": ("fn g(r: {R}) -> C\n    *r\n\nfn f(r: {R}) -> i32\n    var d = g(r)\n    d.x\n", 3),
    "var": ("fn f(r: {R}) -> i32\n    var d: C = *r\n    d.x\n", 3),
    "field": ("fn f(r: {R}) -> i32\n    let w = W { c: *r }\n    w.c.x\n", 3),
    "field_assign": ("fn f(r: {R}) -> i32\n    var w = W { c: C { x: 0 } }\n    w.c = *r\n    w.c.x\n", 3),
    "element": ("fn f(r: {R}) -> i32\n    let a: [1]C = [*r]\n    a[0].x\n", 3),
    "payload": ("fn f(r: {R}) -> i32\n    let e: E = E.V(*r)\n    match e\n        V(c) => c.x\n        N => 0\n", 3),
    "method_argument": ("fn f(r: {R}) -> i32\n    let d = C { x: 0 }\n    d.plus(*r)\n", 3),
    "if_arm": ("fn g(r: {R}, b: i32) -> C\n    if b > 0\n        *r\n    else\n        *r\n\n"
               "fn f(r: {R}) -> i32\n    var d = g(r, 1)\n    d.x\n", 3),
    "match_arm": ("fn g(r: {R}, b: i32) -> C\n    match b\n        0 => *r\n        _ => *r\n\n"
                  "fn f(r: {R}) -> i32\n    var d = g(r, 1)\n    d.x\n", 3),
    "copy_field": ("fn f(r: {R}) -> i32\n    let n = r.x\n    n\n", 3),
    "value_self": ("fn f(r: {R}) -> i32\n    r.get()\n", 3),
    # A reference is a value too, in a slot of its own type.
    "reference_binding": ("fn f(r: {R}) -> i32\n    let q = r\n    q.x\n", 3),
    "reference_field_read": ("fn f(r: {R}) -> i32\n    let n: i32 = (*r).x\n    n\n", 3),
}

# Each fails on ritz1 with no reference in sight, or only behind a `*C`.
# `reference_binding` through a `*C` (`let q = r`) closed by #2596.  A `*r`
# arm types its phi i64 (#2950; #2288 fixed a `c:& C` arm).
READ_GAPS = {"if_arm": 2950, "match_arm": 2950}

MOVE = """\
var DROPS: i32 = 0

struct T
    id: i32

impl Drop for T
    fn drop(self: @&T)
        DROPS = DROPS + 1

impl T
    fn burn(self: T) -> i32
        self.id
    fn look(self: @T) -> i32
        self.id

struct H
    t: T
    n: i32

struct W
    t: T

enum E
    V(T)
    N

fn eat(t: T) -> i32
    t.id

"""

TS = {"shared": "@T", "mutable": "@&T", "pointer": "*T"}
HS = {"shared": "@H", "mutable": "@&H", "pointer": "*H"}

# Rule 2's sites. `{T}` is a reference to T, `{H}` to a holder of one.
MOVES = {
    "deref_argument": "fn f(r: {T}) -> i32\n    eat(^*r)\n",
    "deref_let": "fn f(r: {T}) -> i32\n    let x = ^*r\n    0\n",
    "deref_var": "fn f(r: {T}) -> i32\n    var x = ^*r\n    0\n",
    "deref_assign": "fn f(r: {T}, s: T) -> i32\n    var x = s\n    x = ^*r\n    0\n",
    "deref_return": "fn f(r: {T}) -> T\n    return ^*r\n",
    "deref_tail": "fn f(r: {T}) -> T\n    ^*r\n",
    "deref_field": "fn f(r: {T}) -> i32\n    let w = W { t: ^*r }\n    0\n",
    "deref_element": "fn f(r: {T}) -> i32\n    let a: [1]T = [^*r]\n    0\n",
    "deref_payload": "fn f(r: {T}) -> i32\n    let e: E = E.V(^*r)\n    0\n",
    "field_argument": "fn f(h: {H}) -> i32\n    eat(^h.t)\n",
    "field_binding": "fn f(h: {H}) -> i32\n    var x = ^h.t\n    0\n",
    "field_return": "fn f(h: {H}) -> T\n    return ^h.t\n",
    "receiver": "fn f(r: {T}) -> i32\n    ^r.burn()\n",
    "field_receiver": "fn f(h: {H}) -> i32\n    ^h.t.burn()\n",
}

# Behind a raw pointer only, or written for `:&`.
POINTER_MOVES = {
    "index": "fn f(p: *T) -> i32\n    eat(^p[0])\n",
    "offset": "fn f(p: *T) -> i32\n    eat(^*(p + 1))\n",
}

LENT_MOVES = {
    "whole": "fn f(t:& T) -> i32\n    eat(^t)\n",
    "field": "fn f(h:& H) -> i32\n    eat(^h.t)\n",
    "deref": "fn f(t:& T) -> i32\n    eat(^*t)\n",
    "receiver": "fn f(t:& T) -> i32\n    ^t.burn()\n",
}

GENERIC_MOVES = {
    "fn": "fn g<X>(p: *X) -> X\n    ^*p\n\nfn f(r: *T) -> T\n    g<T>(r)\n",
    "impl": ("struct B<X>\n    p: *X\n\nimpl<X> B<X>\n    fn first(self: @B<X>) -> X\n"
             "        ^*self.p\n\nfn f(r: *T) -> T\n    let b = B<T> { p: r }\n    b.first()\n"),
}

# What stays legal around a move-only value.
NOT_MOVES = {
    "copy_field": "fn f(h: {H}) -> i32\n    h.n\n",
    "field_of_the_field": "fn f(h: {H}) -> i32\n    h.t.id\n",
    "lent_receiver": "fn f(r: {T}) -> i32\n    r.look()\n",
    "field_lent_receiver": "fn f(h: {H}) -> i32\n    h.t.look()\n",
    "borrow_the_field": "fn g(t: @T) -> i32\n    t.id\n\nfn f(h: {H}) -> i32\n    g(@h.t)\n",
    "deref_read": "fn f(r: {T}) -> i32\n    (*r).id\n",
    "pass_it_on": "fn g(t: @T) -> i32\n    t.id\n\nfn f(r: {T}) -> i32\n    g(r)\n",
    # A match through a reference reads: it takes nothing from the owner.
    "match_deref": "fn g(e: E) -> i32\n    0\n\nfn f(r: {T}) -> i32\n    match (*r).id\n        4 => 4\n        _ => 0\n",
}

MATCHES = {
    "deref": "fn f(e: {E}) -> i32\n    match *e\n        V(t) => 4\n        N => 0\n",
    "field": "fn f(w: {W}) -> i32\n    match w.e\n        V(t) => 4\n        N => 0\n",
}
ES = {"shared": "@E", "mutable": "@&E", "pointer": "*E"}
WS = {"shared": "@Y", "mutable": "@&Y", "pointer": "*Y"}

GENERIC_COPY = "fn g<X>(p: *X) -> X\n    *p\n\npub fn main() -> i32\n    var n: i32 = 3\n    g<i32>(@n)\n"

# A pointer as an integer is a different question: this rule leaves it alone.
INT_CONTROLS = {
    "pointer_of_another_width": ("fn a(n: i64) -> i32\n    0\n\npub fn main() -> i32\n"
                                 "    var b: i32 = 3\n    a(@b)\n    b\n", 3),
}

# Two instances of one enum: `Some` means whichever the slot says, and the
# other instance's payload is no reason to refuse it (angelo's font registry).
TWO_INSTANCES = """\
import ritzlib.option

struct C
    x: i32

fn by_ref(r: @C) -> Option<@C>
    return Some(r)

fn by_value(c: C) -> Option<C>
    return Some(c)

pub fn main() -> i32
    var c = C { x: 3 }
    by_value(c)
    by_ref(@c)
    c.x
"""

PTR_READ = MOVE + """\
import ritzlib.ptr

fn f() -> i32
    var a: [1]T
    var t = T { id: 5 }
    write_slot(@a as *T, @t)
    let n = eat(ptr_read<T>(@a as *T))
    return n

fn write_slot(d: *T, s: *T)
    let dp: *u8 = d as *u8
    let sp: *u8 = s as *u8
    var i: i64 = 0
    while i < sizeof(T)
        *(dp + i) = *(sp + i)
        i = i + 1

pub fn main() -> i32
    let n = f()
    return n * 10 + DROPS
"""


def _emit(compiler, path, ll, work):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)


def _compile(compiler, tmp_path, name, src):
    batching.per_row()  # AGAST #2806
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    path = work / "main.ritz"
    path.write_text(src)
    ll = work / "main.ll"
    return _emit(compiler, path, ll, work), ll, work


def _link(compiler, ll, work):
    exe = work / "main"
    cmd = ["clang", "-Wno-override-module", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        cmd.insert(1, str(RITZ_START))
    return fast_link.clang(cmd, cwd=work, capture_output=True, text=True), exe


def _batch_build(compiler, path, work):
    """batching.run's `build`: compile and link a batch the way `_run` does a row."""
    ll = work / "main.ll"
    comp = _emit(compiler, path, ll, work)
    if comp.returncode != 0 or not ll.exists():
        return False, comp.stdout + comp.stderr, None
    link, exe = _link(compiler, ll, work)
    return link.returncode == 0, link.stderr, exe


def _batch_compile(compiler, path, work):
    comp = _emit(compiler, path, work / "main.ll", work)
    return comp.returncode, comp.stdout + comp.stderr


def _run(compiler, tmp_path, name, src):
    got = batching.run(compiler, src, _batch_build, compile=_batch_compile)  # #2806: None unless batched
    if got is not None:
        return got
    comp, ll, work = _compile(compiler, tmp_path, name, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused {name}:\n{src}\n{out[-2000:]}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, f"{compiler}: {name} would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _located(text):
    """`text` without its `^`, and where the `^` was as `line:col`."""
    before = text[:text.index("^")]
    line = before.count("\n") + 1
    return text.replace("^", "", 1), f"{line}:{len(before) - before.rfind(chr(10))}"


def _assert_refused(compiler, tmp_path, name, marked, message):
    src, where = _located(marked)
    got = batching.refused(compiler, src, _batch_compile, at=tuple(map(int, where.split(":"))))
    if got is not None:  # AGAST #2806: this row's diagnostics from its chunk's batch
        out, where = got
    else:
        comp, ll, _ = _compile(compiler, tmp_path, name, src)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"{compiler} accepted {name}:\n{src}"
        assert not ll.exists()
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, message) in found, f"{compiler}: {name}, wanted {where}:\n{src}\n{out[-2000:]}"


def _main(body, entry):
    return f"{body}\npub fn main() -> i32\n{entry}"


CALL_F = "    var c = C { x: 3 }\n    0\n"
CALL_T = "    0\n"


def _ids(table):
    return sorted(table)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ref", _ids(REFS))
@pytest.mark.parametrize("site", _ids(SLOTS))
def test_reference_into_a_by_value_slot(tmp_path, compiler, site, ref):
    body = SLOTS[site].replace("{R}", REFS[ref])
    _assert_refused(compiler, tmp_path, f"{site}_{ref}", COPY + _main(body, CALL_F), REF_INTO_VALUE)


def _shape_params():
    for shape in _ids(SHAPES):
        for compiler in COMPILERS:
            gap = SHAPE_GAPS.get(shape) if compiler != "ritz0" else None
            marks = [pytest.mark.xfail(strict=True, reason=f"AGAST #{gap}")] if gap else []
            yield pytest.param(shape, compiler, marks=marks)


@pytest.mark.parametrize("shape,compiler", list(_shape_params()))
def test_every_shape_of_reference_is_refused(tmp_path, compiler, shape):
    _assert_refused(compiler, tmp_path, shape, COPY + _main(SHAPES[shape], CALL_F), REF_INTO_VALUE)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(ADDR_SLOTS))
def test_address_of_into_a_by_value_slot(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, COPY + _main(ADDR_SLOTS[site], CALL_F), ADDR_INTO_VALUE)


def _read_params():
    for site in _ids(READS):
        for ref in _ids(REFS):
            for compiler in COMPILERS:
                gap = READ_GAPS.get(site) if compiler != "ritz0" else None
                marks = [pytest.mark.xfail(strict=True, reason=f"AGAST #{gap}")] if gap else []
                yield pytest.param(site, ref, compiler, marks=marks)


@pytest.mark.parametrize("site,ref,compiler", list(_read_params()))
def test_copy_type_reads_through_a_reference(tmp_path, compiler, site, ref):
    body, want = READS[site]
    arg = "@&c" if ref == "mutable" else "@c"
    entry = f"    var c = C {{ x: 3 }}\n    f({arg})\n"
    src = COPY + _main(body.replace("{R}", REFS[ref]), entry)
    assert _run(compiler, tmp_path, f"{site}_{ref}", src) == want


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ref", _ids(TS))
@pytest.mark.parametrize("site", _ids(MOVES))
def test_move_out_of_a_reference(tmp_path, compiler, site, ref):
    body = MOVES[site].replace("{T}", TS[ref]).replace("{H}", HS[ref])
    _assert_refused(compiler, tmp_path, f"{site}_{ref}", MOVE + _main(body, CALL_T), MOVE_OUT_OF_REF)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(POINTER_MOVES))
def test_move_out_through_a_raw_pointer(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, MOVE + _main(POINTER_MOVES[site], CALL_T), MOVE_OUT_OF_REF)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(LENT_MOVES))
def test_move_out_of_a_lent_param(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, MOVE + _main(LENT_MOVES[site], CALL_T), MOVE_OUT_OF_REF)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(GENERIC_MOVES))
def test_move_out_is_judged_per_instance(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, MOVE + _main(GENERIC_MOVES[site], CALL_T), MOVE_OUT_OF_REF)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_generic_read_is_fine_at_a_copy_type(tmp_path, compiler):
    assert _run(compiler, tmp_path, "generic_copy", GENERIC_COPY) == 3


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ref", _ids(TS))
@pytest.mark.parametrize("site", _ids(NOT_MOVES))
def test_reads_that_leave_the_owner_alone(tmp_path, compiler, site, ref):
    body = NOT_MOVES[site].replace("{T}", TS[ref]).replace("{H}", HS[ref])
    amp = "@&" if ref == "mutable" else "@"
    arg = f"{amp}h" if "{H}" in NOT_MOVES[site] else f"{amp}h.t"
    entry = f"    var h = H {{ t: T {{ id: 4 }}, n: 4 }}\n    f({arg})\n"
    assert _run(compiler, tmp_path, f"{site}_{ref}", MOVE + _main(body, entry)) == 4


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ref", _ids(ES))
@pytest.mark.parametrize("site", _ids(MATCHES))
def test_a_match_through_a_reference_reads(tmp_path, compiler, site, ref):
    amp = "@&" if ref == "mutable" else "@"
    body = MATCHES[site].replace("{E}", ES[ref]).replace("{W}", WS[ref])
    arg = f"{amp}y" if site == "field" else f"{amp}y.e"
    entry = f"    var y = Y {{ e: E.V(T {{ id: 4 }}) }}\n    f({arg})\n"
    src = MOVE + "struct Y\n    e: E\n\n" + _main(body, entry)
    assert _run(compiler, tmp_path, f"{site}_{ref}", src) == 4


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", _ids(INT_CONTROLS))
def test_a_pointer_as_an_integer_is_not_this_rule(tmp_path, compiler, name):
    src, want = INT_CONTROLS[name]
    assert _run(compiler, tmp_path, name, src) == want


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_pointer_to_another_type_is_not_this_rule(tmp_path, compiler):
    """`*r` wouldn't help, so the error must not say it would."""
    src = COPY + "struct D\n    x: i32\n\nfn f(r: *D) -> i32\n    val(r)\n\npub fn main() -> i32\n    0\n"
    comp, _, _ = _compile(compiler, tmp_path, "another", src)
    assert REF_INTO_VALUE not in comp.stdout + comp.stderr


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_payload_is_judged_by_its_own_instance(tmp_path, compiler):
    comp, ll, _ = _compile(compiler, tmp_path, "two_instances", TWO_INSTANCES)
    assert comp.returncode == 0, (comp.stdout + comp.stderr)[-2000:]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_ptr_read_hands_the_caller_ownership(tmp_path, compiler):
    """5 read, and two drops: the one `eat` took and `t` itself."""
    assert _run(compiler, tmp_path, "ptr_read", PTR_READ) == 52
