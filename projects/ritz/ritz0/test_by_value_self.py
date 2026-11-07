#!/usr/bin/env python3
"""A by-value `self` is a by-value parameter named `self` (LANGUAGE_SPEC §5.4, LARB
ruling R10, AGAST #2393).

A bare `self` and `self: T` are one thing: the method has its own storage, and
nothing it does to `self` reaches the caller. What the caller's receiver holds is
read when the receiver is evaluated, before the arguments. `self:& T` is the
caller's place, and stays a distinct mode.

Each row of ROWS is spelled three ways, as a bare `self`, as `self: T` and as a
plain `s: T` param, and all of them have to give the row's answer on ritz0, ritz1
and ritz1_selfhosted: the plain param is what `self` can't drift from.
"""

import os
import re
import subprocess

import pytest

from ref_rules import DROP_BY_VALUE
from test_ref_into_value import COMPILERS, RITZ1_BUILD, RITZ_ROOT, RITZ_START, _compile, _run

pytestmark = pytest.mark.integration

TYPES = """\
struct C
    x: i32
    y: i64

struct W
    c: C

struct Big
    a: [40]i64
    x: i32

struct Holder
    b: Big

enum E
    V(i32)
    N

enum Level
    Low
    High

var G: C
var GB: Big
var drops: i32

fn bump(c: @&C) -> i32
    c.x = 9
    5

fn bump_big(b: @&Big) -> i32
    b.x = 9
    5

fn poke(p: *C) -> i32
    p.x = 9
    5

fn repoint(p: @&*C) -> i32
    *p = @G
    5

fn make() -> C
    C { x: 4, y: 0 }

"""

C1 = "var c = C { x: 1, y: 2 }\n    "
B1 = "var b: Big\n    b.x = 1\n    b.a[3] = 1\n    "

# name: (type, extra params, the body, the receiver, its arguments, what main does
# around `{call}`, the answer). `{s}` is the receiver's name in the body.
ROWS = {
    "field_write_stays": ("C", "", "{s}.x = 9\n{s}.x", "c", "", C1 + "let r = {call}\n    c.x * 10 + r", 19),
    "field_write_is_seen_inside": ("C", "", "{s}.x = 9\n{s}.x", "c", "", C1 + "{call}", 9),
    "whole_write_stays": ("C", "", "{s} = C { x: 7, y: 0 }\n{s}.x", "c", "", C1 + "let r = {call}\n    c.x * 10 + r", 17),
    "address_write_stays": ("C", "", "let p: @&C = @&{s}\np.x = 9\n{s}.x", "c", "",
                            C1 + "let r = {call}\n    c.x * 10 + r", 19),
    "pointer_write_stays": ("C", "", "poke(@{s})\n{s}.x", "c", "", C1 + "let r = {call}\n    c.x * 10 + r", 19),
    "returned_copy": ("C", "", "{s}.x = 9\n{s}", "c", "", C1 + "let d = {call}\n    c.x * 10 + d.x", 19),
    "returned_copy_explicit": ("C", "", "{s}.x = 9\nreturn {s}", "c", "", C1 + "let d = {call}\n    c.x * 10 + d.x", 19),
    "write_through_an_argument": ("C", ", q: @&C", "q.x = 9\n{s}.x", "c", "@&c", C1 + "{call}", 1),
    "write_through_an_argument_lands": ("C", ", q: @&C", "q.x = 9\n{s}.x", "c", "@&c", C1 + "{call}\n    c.x", 9),
    "write_by_an_argument_expression": ("C", ", n: i32", "{s}.x", "c", "bump(@&c)", C1 + "{call}", 1),
    "write_to_a_global": ("C", "", "G.x = 9\n{s}.x", "G", "", "G.x = 1\n    {call}", 1),
    "receiver_behind_a_pointer": ("C", "", "{s}.x = 9\n{s}.x", "*p", "",
                                  C1 + "let p: *C = @c\n    {call}\n    c.x", 1),
    "receiver_pointer_read_before_the_arguments": ("C", ", n: i32", "{s}.x", "*p", "repoint(@&p)",
                                                   C1 + "G.x = 7\n    var p: *C = @c\n    {call}", 1),
    "receiver_behind_a_reference": ("C", "", "{s}.x = 9\n{s}.x", "*p", "",
                                    C1 + "let p: @&C = @&c\n    {call}\n    c.x", 1),
    "receiver_is_a_field": ("C", "", "{s}.x = 9\n{s}.x", "w.c", "",
                            "var w = W { c: C { x: 1, y: 2 } }\n    {call}\n    w.c.x", 1),
    "receiver_is_an_element": ("C", "", "{s}.x = 9\n{s}.x", "a[1]", "",
                               "var a: [2]C\n    a[1].x = 1\n    {call}\n    a[1].x", 1),
    "receiver_is_a_call": ("C", "", "{s}.x = {s}.x + 1\n{s}.x", "make()", "", "{call}", 5),
    "receiver_is_a_literal": ("C", "", "{s}.x = {s}.x + 1\n{s}.x", "C { x: 2, y: 0 }", "", "{call}", 3),
    # Past the sret threshold it goes `byval`: a different path, and the same answer.
    "big_field_write_stays": ("Big", "", "{s}.x = 9\n{s}.a[3] = 9\n{s}.x + {s}.a[3] as i32", "b", "",
                              B1 + "let r = {call}\n    b.x + b.a[3] as i32 + r", 20),
    "big_returned_copy": ("Big", "", "{s}.x = 9\n{s}", "b", "", B1 + "let d = {call}\n    b.x * 10 + d.x", 19),
    "big_write_through_an_argument": ("Big", ", q: @&Big", "q.x = 9\n{s}.x", "b", "@&b", B1 + "{call}", 1),
    "big_write_by_an_argument_expression": ("Big", ", n: i32", "{s}.x", "b", "bump_big(@&b)", B1 + "{call}", 1),
    "big_write_to_a_global": ("Big", "", "GB.x = 9\n{s}.x", "GB", "", "GB.x = 1\n    {call}", 1),
    "big_receiver_is_a_field": ("Big", "", "{s}.x = 9\n{s}.x", "h.b", "",
                                "var h: Holder\n    h.b.x = 1\n    {call}\n    h.b.x", 1),
    "tagged_enum_write_stays": ("E", "", "{s} = E.N\n0", "e", "",
                                "var e = E.V(3)\n    {call}\n    match e\n        E.V(n) => n\n        E.N => 0", 3),
    "plain_enum_write_stays": ("Level", "", "{s} = Level.High\n0", "l", "",
                               "var l = Level.Low\n    {call}\n    match l\n        Level.Low => 1\n"
                               "        Level.High => 2", 1),
}

SPELLINGS = {
    "bare": ("impl {t}\n    fn g(self{extra}) -> {ret}\n{body}\n", "self", "{recv}.g({args})"),
    "typed": ("impl {t}\n    fn g(self: {t}{extra}) -> {ret}\n{body}\n", "self", "{recv}.g({args})"),
    "plain": ("fn g(s: {t}{extra}) -> {ret}\n{body}\n", "s", "g({recv}{comma}{args})"),
}


# A plain param's gaps, which are nothing to do with `self`: the receiver forms pass.
PLAIN_GAPS = {"write_to_a_global": 2446, "big_write_to_a_global": 2446, "receiver_is_an_element": 2446}


def _source(spelling, row):
    ty, extra, body, recv, args, main, _ = row
    template, name, call = SPELLINGS[spelling]
    indent = " " * (4 if spelling == "plain" else 8)
    lines = body.replace("{s}", name).split("\n")
    ret = ty if lines[-1].endswith(f" {name}") or lines[-1] == name else "i32"
    fn = template.format(t=ty, extra=extra, ret=ret, body="\n".join(indent + line for line in lines))
    if spelling != "plain" and recv.startswith("*"):
        recv = recv[1:]   # `p.g()` reads through p, as `*p` does for a plain param (§13.3).
    if spelling != "plain" and recv.startswith("C {"):
        recv = f"({recv})"
    call = call.format(recv=recv, args=args, comma=", " if args else "")
    return f"{TYPES}{fn}\npub fn main() -> i32\n    {main.replace('{call}', call)}\n"


def _table():
    for name in sorted(ROWS):
        for spelling in sorted(SPELLINGS):
            for compiler in COMPILERS:
                marks = []
                if spelling == "plain" and name in PLAIN_GAPS and compiler != "ritz0":
                    marks = [pytest.mark.xfail(strict=True, reason=f"#{PLAIN_GAPS[name]}")]
                yield pytest.param(name, spelling, compiler, marks=marks, id=f"{name}-{spelling}-{compiler}")


@pytest.mark.parametrize("name,spelling,compiler", list(_table()))
def test_self_is_a_by_value_param(name, spelling, compiler, tmp_path):
    assert _run(compiler, tmp_path, name, _source(spelling, ROWS[name])) == ROWS[name][-1]


METHOD = "impl C\n    fn g(self) -> i32\n        self.x = 9\n        self.x\n\n"

# Every way to name the call. `c.g()` and `C_g(c)` mean the same thing (R10).
CALLS = {
    "mangled": ("C_g(c)", 19),
    "in_a_method": ("c.h()", 19),
}
MANGLED_GAP = 2447


def _calls():
    for name in sorted(CALLS):
        for compiler in COMPILERS:
            marks = []
            if name == "mangled" and compiler != "ritz0":
                marks = [pytest.mark.xfail(strict=True, reason=f"#{MANGLED_GAP}: ritz1 can't name a method so")]
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.parametrize("name,compiler", list(_calls()))
def test_every_spelling_of_the_call(name, compiler, tmp_path):
    call, want = CALLS[name]
    src = (TYPES + METHOD.replace("impl C\n", "impl C\n    fn h(self) -> i32\n        self.g()\n\n")
           + f"pub fn main() -> i32\n    {C1}let r = {call}\n    c.x * 10 + r\n")
    assert _run(compiler, tmp_path, name, src) == want


# The caller's place, and it stays one: these are what a by-value `self` isn't.
LENT = {
    "bare": ("self:&", "c.g()", 9),
    "typed": ("self:& C", "c.g()", 9),
    "mutable_reference": ("self: @&C", "c.g()", 9),
    "pointer": ("self: *C", "c.g()", 9),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LENT))
def test_a_lent_self_is_the_callers_place(name, compiler, tmp_path):
    receiver, call, want = LENT[name]
    src = (f"{TYPES}impl C\n    fn g({receiver}) -> i32\n        self.x = 9\n        0\n\n"
           f"pub fn main() -> i32\n    {C1}{call}\n    c.x\n")
    assert _run(compiler, tmp_path, name, src) == want


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("receiver", ["self", "self: T"])
def test_a_move_only_self_is_dropped_once(receiver, compiler, tmp_path):
    src = f"""\
var drops: i32

struct T
    x: i32

impl Drop for T
    fn drop(self:&)
        drops = drops + 1

impl T
    fn burn({receiver}) -> i32
        self.x = self.x + 1
        self.x

fn run() -> i32
    let t = T {{ x: 1 }}
    t.burn()

pub fn main() -> i32
    let r = run()
    drops * 10 + r
"""
    assert _run(compiler, tmp_path, "drop_once", src) == 12


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_move_only_self_drops_what_the_method_wrote(compiler, tmp_path):
    src = """\
var seen: i32

struct T
    x: i32

impl Drop for T
    fn drop(self:&)
        seen = self.x

impl T
    fn burn(self)
        self.x = 7

fn run()
    let t = T { x: 1 }
    t.burn()

pub fn main() -> i32
    run()
    seen
"""
    assert _run(compiler, tmp_path, "drop_sees_the_write", src) == 7


MOVE_ONLY = """\
var drops: i32

struct T
    x: i32

struct H
    t: T

impl Drop for T
    fn drop(self:&)
        drops = drops + 1

impl T
    fn burn(self) -> i32
        self.x
    fn keep(self) -> T
        self
    fn peek(self:&) -> i32
        self.x

fn make() -> T
    T { x: 1 }

"""

CHAIN_GAP = 2295

# How many times the value drops, whichever way the receiver gets there.
DROPS = {
    "binding": ("let t = T { x: 1 }\n    t.burn()\n    0\n", 1),
    "literal": ("(T { x: 1 }).burn()\n    0\n", 1),
    "call_result": ("make().burn()\n    0\n", 1),
    "field": ("var h = H { t: T { x: 1 } }\n    h.t.burn()\n    0\n", 1),
    "handed_back": ("let t = T { x: 1 }\n    let u = t.keep()\n    u.x\n    0\n", 1),
    "handed_back_and_burned": ("let t = T { x: 1 }\n    t.keep().burn()\n    0\n", 1),
    "lent_first": ("var t = T { x: 1 }\n    t.peek()\n    t.burn()\n    0\n", 1),
    "lent_only": ("var t = T { x: 1 }\n    t.peek()\n    0\n", 1),
    "in_an_arm_only": ("let t = T { x: 1 }\n    if drops == 0\n        t.burn()\n    0\n", 1),
    "in_the_arm_not_taken": ("let t = T { x: 1 }\n    if drops == 1\n        t.burn()\n    0\n", 1),
}


def _drops():
    for name in sorted(DROPS):
        for compiler in COMPILERS:
            marks = []
            if name == "handed_back_and_burned" and compiler != "ritz0":
                marks = [pytest.mark.xfail(strict=True, reason=f"#{CHAIN_GAP}: no receiver type for `t.keep().burn()`")]
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.parametrize("name,compiler", list(_drops()))
def test_a_move_only_receiver_drops_once(name, compiler, tmp_path):
    body, want = DROPS[name]
    src = f"{MOVE_ONLY}fn run() -> i32\n    {body}\npub fn main() -> i32\n    run()\n    drops\n"
    assert _run(compiler, tmp_path, name, src) == want


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_receiver_taken_by_value_is_moved(compiler, tmp_path):
    src = f"{MOVE_ONLY}pub fn main() -> i32\n    let t = T {{ x: 1 }}\n    t.burn()\n    t.burn()\n"
    comp, ll, _ = _compile(compiler, tmp_path, "used_after_the_move", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it"
    line = src.count("\n")
    assert re.search(rf"main\.ritz:{line}:5: (error: )?use of moved value: `t` \(moved at .*main\.ritz:{line - 1}:5\)", out), out


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("receiver", ["self", "self: T"])
def test_drop_is_refused_a_by_value_self(receiver, compiler, tmp_path):
    src = (f"struct T\n    x: i32\n\nimpl Drop for T\n    fn drop({receiver})\n        self.x = 1\n\n"
           "pub fn main() -> i32\n    let t = T { x: 1 }\n    0\n")
    comp, ll, _ = _compile(compiler, tmp_path, "drop_by_value", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it"
    assert re.search(rf"main\.ritz:5:(\d+: )?(error: )?{re.escape(DROP_BY_VALUE)}|main\.ritz:5: {re.escape(DROP_BY_VALUE)}", out), out


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("receiver", ["self:&", "self:& T", "self: @&T", "self: *T"])
def test_drop_takes_any_lent_self(receiver, compiler, tmp_path):
    src = (f"var drops: i32\n\nstruct T\n    x: i32\n\nimpl Drop for T\n    fn drop({receiver})\n"
           "        drops = drops + 1\n\nfn run()\n    let t = T { x: 1 }\n\npub fn main() -> i32\n"
           "    run()\n    drops\n")
    assert _run(compiler, tmp_path, "drop_lent", src) == 1


GENERIC = ("struct W<T>\n    v: T\n\nimpl<T> W<T>\n    fn rd(self, q: @&W<T>) -> i32\n        q.v = q.v + 1\n"
           "        self.v as i32\n\npub fn main() -> i32\n    var a = W<i32> { v: 1 }\n    a.rd(@&a)\n")


@pytest.mark.parametrize("compiler", [
    "ritz0", *(pytest.param(c, marks=pytest.mark.xfail(strict=True, reason="#2318: a generic impl's `self`"))
               for c in COMPILERS[1:])])
def test_a_generic_impl_copies_too(compiler, tmp_path):
    """ritz1 refuses this outright, so its `self` can't be the caller's place unseen."""
    assert _run(compiler, tmp_path, "generic", GENERIC) == 1


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_type_is_not_a_receiver(compiler, tmp_path):
    src = f"{TYPES}{METHOD}pub fn main() -> i32\n    {C1}C.g(c)\n"
    comp, ll, _ = _compile(compiler, tmp_path, "through_a_type", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it"
    assert re.search(r"[Ss]tatic method call Type\.method\(\) but .*expects .*self.* parameter", out), out


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_free_fn_self_is_a_by_value_param(compiler, tmp_path):
    src = (f"{TYPES}fn g(self: C) -> i32\n    self.x = 9\n    self.x\n\n"
           "fn f(c:& C) -> i32\n    g(c)\n\n"
           f"pub fn main() -> i32\n    {C1}let r = f(c)\n    c.x * 10 + r\n")
    assert _run(compiler, tmp_path, "free_fn", src) == 19


IMPORTED = """\
pub struct S
    x: i32
    y: i64

pub struct L
    a: [40]i64
    x: i32

impl S
    pub fn w(self) -> i32
        self.x = 9
        self.x

impl L
    pub fn w(self, n: i32) -> i32
        self.x = 9
        self.x + n
"""


@pytest.mark.parametrize("compiler", COMPILERS[1:])
def test_an_imported_method_is_declared_as_it_is_defined(compiler, tmp_path):
    """Each module compiled alone, as a package is: the `declare` has to match."""
    binary = RITZ1_BUILD / compiler
    (tmp_path / "lib.ritz").write_text(IMPORTED)
    (tmp_path / "main.ritz").write_text(
        "import lib\n\npub fn main() -> i32\n    var s = S { x: 1, y: 2 }\n    var l: L\n    l.x = 1\n"
        "    s.w() + l.w(1) + s.x + l.x\n")
    env = {**os.environ, "RITZ_PATH": f"{RITZ_ROOT}:{tmp_path}"}
    for name in ("main", "lib"):
        built = subprocess.run([str(binary), f"{name}.ritz", "-o", f"{name}.ll"], cwd=tmp_path, env=env,
                               capture_output=True, text=True)
        assert built.returncode == 0, built.stderr
    link = subprocess.run(["clang", "-Wno-override-module", str(RITZ_START), "main.ll", "lib.ll", "-o", "m",
                           "-nostdlib", "-no-pie"], cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr
    assert subprocess.run([str(tmp_path / "m")]).returncode == 21
    # A `ptr` here links and runs too: the call's own attributes decide. It's still wrong.
    assert re.search(r"declare i32 @L_w\(ptr byval\(%L\)", (tmp_path / "main.ll").read_text())
