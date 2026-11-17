"""AGAST #3504: ritz1's let_check runs on Sema, before emission (#1816).

THE CHANGE

let_check.ritz (`let` immutability, AGAST #2028 / #2032 / #2403, and a struct
of another type, AGAST #2293 / #3293 / #3294 / #3347) was five `pub fn
*check*(s: *EmitterState, ..)` calls made mid-lowering.  It now takes
`sm: *Sema` and runs from sema_walk.ritz at each place the emitter called it,
reading Sema's lexical scope: SemaVar.is_let marks a `let` and a
`for x in <iterable>` element, and SemaVar.let_* records each local as the
emitter's LocalVar did.  The emitter no longer skips a refused `return c` /
tail: it never sees a refused program.

The diagnostics are the rule's own tables (test_let_immutability.py through
test_ritz1_let_immutability.py, test_receiver_short_of_self.py, ...),
unchanged; the commit compared every file of ritz0/test, ritzlib, examples and
ritz1/src, plain and --test-table, against the pre-move compiler: the same IR,
and the same words for each refusal.

THE TESTS

One program, both ritz1 compilers.  It has a let_check error at each place
the walk calls into let_check (a statement's write and `@&`, an expression
arm, a receiver lent to `self: **C`, a call's and a method's struct argument,
a store, a declaration, a `return`, a fn's tail and a method's), in source
order.  An emitter-side error after them (a literal that doesn't fit its
slot, literal_slot) is no longer printed: before the move it was.  A fn's tail
expression is the fn's value, not a statement, but an `@&` of a `let` in it
is refused as anywhere else (AGAST #3804: the emitter never let-checked it).
ritz1 reports an `@&` at the `@`; ritz0 at its operand, two columns on.
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

PROGRAM = """\
struct Pt
    x: i64
    y: i64

struct D
    x: i64

struct C
    x: i32

impl C
    fn rd(self: **C) -> i32
        self.x

impl Pt
    fn take(self: @Pt, d: D) -> i64
        d.x

fn pt_x(p: *Pt) -> i64
    p.x

fn want_d(d: D) -> i64
    d.x

fn ret_d(p: Pt) -> D
    if p.x == 0
        return p
    p

fn tail_borrow() -> i64
    let t = Pt { x: 1, y: 2 }
    pt_x(@&t)

fn main() -> i32
    let p = Pt { x: 1, y: 2 }
    let o: Option<i64> = Some(3)
    let n = match o
        Some(v) => pt_x(@&p)
        None => 0
    var c = C { x: 3 }
    let q: *C = @&c
    q.rd()
    want_d(p)
    p.take(p)
    var d: D = D { x: 1 }
    d = p
    let e: D = p
    p.x = 5
    var m: u8 = 300
    0

impl D
    fn tail_m(self: *D) -> i64
        let t = Pt { x: 1, y: 2 }
        pt_x(@&t)
"""

WANTED = [
    ("27:9", "the fn is declared `-> D` but its return value is a `Pt`"),
    ("28:5", "the fn is declared `-> D` but its return value is a `Pt`"),
    ("32:10", "cannot borrow `let` binding `t` as mutable; declare it `var`"),
    ("38:25", "cannot borrow `let` binding `p` as mutable; declare it `var`"),
    ("42:5", "cannot borrow `let` binding `q` as mutable; declare it `var`"),
    ("43:12", "parameter `d` is declared `D` but its argument is a `Pt`"),
    ("44:12", "parameter `d` is declared `D` but its argument is a `Pt`"),
    ("46:5", "`d` is declared `D` but the value assigned is a `Pt`"),
    ("47:5", "`e` is declared `D` but its initialiser is a `Pt`"),
    ("48:5", "cannot assign through `let` binding `p`; declare it `var`"),
    ("55:14", "cannot borrow `let` binding `t` as mutable; declare it `var`"),
]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_let_errors_stop_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_let", PROGRAM)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == WANTED, f"{compiler}:\n{out}"


# Untyped bindings Sema's typer leaves unknown and the emitter typed anyway: a
# method's result, an array element, an `if` arm's value, an array literal, `unwrap()`, a field of an element.  Each is
# a struct `let`, so a write through it, a lend of it and a store of it as
# another struct are refused, as before the move.
UNTYPED = """\
struct Pt
    x: i64
    y: i64

struct D
    x: i64

struct H
    p: Pt
    ps: [2]Pt

impl H
    fn get(self: @H) -> Pt
        self.p

fn bump(p:& Pt)
    p.x = 1

fn main() -> i32
    var h = H { p: Pt { x: 1, y: 2 }, ps: [Pt { x: 1, y: 2 }, Pt { x: 1, y: 2 }] }
    let a = h.get()
    a.x = 4
    let b = h.ps[0]
    bump(b)
    let n = 3
    let c = if n == 3
        Pt { x: 1, y: 2 }
    else
        Pt { x: 3, y: 2 }
    let d: D = c
    var g: [2]Pt
    let e = g[1]
    e.y = 2
    let f = [1, 2]
    f[0] = 3
    let o: Option<Pt> = Some(Pt { x: 1, y: 2 })
    let u = o.unwrap()
    u.x = 3
    var hs: [2]H
    let w = hs[0].p
    w.y = 1
    0
"""

UNTYPED_WANTED = [
    ("22:5", "cannot assign through `let` binding `a`; declare it `var`"),
    ("24:10", "cannot borrow `let` binding `b` as mutable; declare it `var`"),
    ("30:5", "`d` is declared `D` but its initialiser is a `Pt`"),
    ("33:5", "cannot assign through `let` binding `e`; declare it `var`"),
    ("35:5", "cannot assign through `let` binding `f`; declare it `var`"),
    ("38:5", "cannot assign through `let` binding `u`; declare it `var`"),
    ("41:5", "cannot assign through `let` binding `w`; declare it `var`"),
]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_untyped_lets_are_typed_as_the_emitter_typed_them(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_let_untyped", UNTYPED)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == UNTYPED_WANTED, f"{compiler}:\n{out}"


# Where Sema can't type a binding (a method's `*Pt` result, whose pointee it
# doesn't record) let_check stays quiet: lending what that `let` holds to a
# `:& Pt` is legal, and the emitter accepted it.  A guess would refuse it.
UNKNOWN_KIND = """\
struct Pt
    x: i64
    y: i64

struct H
    p: Pt

impl H
    fn at(self: *H) -> *Pt
        @&self.p

fn bump(p:& Pt)
    p.x = 7

fn main() -> i32
    var h = H { p: Pt { x: 1, y: 2 } }
    let q = h.at()
    bump(q)
    h.p.x as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_untyped_let_sema_cannot_type_is_not_refused(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_let_unknown", UNKNOWN_KIND)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"


# A `for x in` element is a `let` (AGAST #2389) over a Vec field too: Sema
# names its element through the Vec's buffer, as the emitter indexed it.
VEC_FIELD = """\
import ritzlib.gvec

struct S
    a: i32
    b: i32

struct H
    v: Vec<S>

pub fn main() -> i32
    var h = H { v: vec_new<S>() }
    for x in h.v
        x.a = 5
    return 0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_element_of_a_vec_field_is_a_let(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_let_vec_field", VEC_FIELD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == [("13:9", "cannot assign through `let` binding `x`; declare it `var`")], out


# `sizeof(f(d))` sizes f's result and never lowers the call, so the emitter
# never paired its argument with f's param: a `D` there was accepted, and
# Sema doesn't judge it either (as call_check mutes it, AGAST #3503).
SIZEOF_ARG = """\
struct C
    x: i32

struct D
    x: i32

fn f(c: C) -> i32
    c.x

fn main() -> i32
    let d: D = D { x: 1 }
    let n: i64 = sizeof(f(d))
    n as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_struct_argument_inside_sizeof_is_not_judged(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_let_sizeof", SIZEOF_ARG)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"


# A method call there: the emitter can't size it, and says only that.
SIZEOF_METHOD = """\
struct C
    x: i32

struct D
    x: i32

impl C
    fn take(self: *C, o: C) -> i32
        o.x

fn main() -> i32
    let d: D = D { x: 1 }
    var c: C = C { x: 2 }
    let n: i64 = sizeof(c.take(d))
    n as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_method_argument_inside_sizeof_is_not_judged(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_let_sizeof_m", SIZEOF_METHOD)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted it:\n{out}"
    assert "is declared `C`" not in out, out
    assert "sizeof: cannot determine the type of this expression" in out, out
