"""AGAST #2335: a place passed to a `name:& T` parameter is borrowed.

LARB ruling R1, exception 2: `f(x)` into `fn f(n:& T)` means `f(@&x)`, for every
T, pointers included. It's the language's only implicit borrow.

    fn f(n:& i32)
        n = 3

    var n: i32 = 1
    f(n)                # n is 3

- PLACES. A local, a param, a field, an element or a deref. ritz1 read the value
  and took the integer for the pointer (exit -11), or passed `%C` as an i64 and
  clang refused it. ritz0 refused a `*U` referent, which ritz1 took by value.
- RVALUES. There's nothing for the caller to observe, so `f(1 + 2)` and `f(g())`
  are refused, in the same words at the same place on each compiler. ritz0
  spilled a struct rvalue to a temporary and dropped the write.
- `let`. The place must be mutable. A `let` that holds a `*U` is refused into a
  `:& *U`: that's its own storage. It's still fine into a `:& U`, which takes
  the pointer it holds.
- FIT. A place of another type is refused. `i32` into `:& i64` would have become
  an 8-byte store over a 4-byte place, so neighbours check the width.
- POINTER FAMILY. The ruling's `:&` row keeps `m` and `p`: an `@&T` or `*T` isn't
  a place of `T`, so it passes as the pointer it is. `@x` doesn't fit (#2339).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link

from ref_rules import REF_TO_OTHER_TYPE
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

C = "struct C\n    x: i32\n    y: i64\n\n"
GOOD = "    var c1: C = C { x: 1, y: 0 }\n    var c3: C = C { x: 3, y: 0 }\n"
GENERIC_WRITER = "fn w<T>(r:& T, v: T)\n    r = v\n\n"

# name: (T, writer, initial value, read of `{}`, extra writer arguments, setup,
# how an element gets its start: ritz1 stores no whole struct or array there)
REFERENTS = {
    "int": ("i32", "fn w(r:& i32)\n    r = 3\n", "1", "{}", "", "", "a[1] = 1"),
    "struct": ("C", "fn w(r:& C)\n    r.x = 3\n", "C { x: 1, y: 0 }", "{}.x", "", "", "a[1].x = 1"),
    "array": ("[2]i32", "fn w(r:& [2]i32)\n    r[1] = 3\n", "[1, 1]", "{}[1]", "", "", "a[1][1] = 1"),
    "pointer": ("*C", "fn w(r:& *C, d: *C)\n    r = d\n", "@c1", "{}.x", ", @c3", GOOD, "a[1] = @c1"),
    # AGAST #2994: the callee reads and writes it, and a `bool` local's slot is
    # wider than the `bool` it holds.
    "bool": ("bool", "fn w(r:& bool)\n    r = not r\n", "false", "({} as i32) * 3", "", "", "a[1] = false"),
}


def _table() -> dict:
    """Each program writes through the borrow and returns what the owner sees."""
    programs = {}
    for name, (t, w, init, read, extra, setup, start) in REFERENTS.items():
        def rd(place):
            return read.format(place)

        # The writer's extra argument is built where `c3` is in scope.
        go_extra = ", d" if extra else ""
        go_param = ", d: *C" if extra else ""
        head = C + w + "\n"
        main = f"pub fn main() -> i32\n{setup}"
        programs[f"{name}_local"] = (
            head + main + f"    var v: {t} = {init}\n    w(v{extra})\n    return {rd('v')}\n")
        programs[f"{name}_grouped"] = (
            head + main + f"    var v: {t} = {init}\n    w((v){extra})\n    return {rd('v')}\n")
        programs[f"{name}_by_value_param"] = (
            head + f"fn go(v: {t}{go_param}) -> i32\n    w(v{go_extra})\n    return {rd('v')}\n\n"
            + main + f"    var v: {t} = {init}\n    return go(v{extra})\n")
        programs[f"{name}_borrow_param"] = (
            head + f"fn go(v:& {t}{go_param})\n    w(v{go_extra})\n\n"
            + main + f"    var v: {t} = {init}\n    go(v{extra})\n    return {rd('v')}\n")
        programs[f"{name}_field"] = (
            head + f"struct H\n    a: i64\n    f: {t}\n    b: i64\n\n"
            + main + f"    var h: H\n    h.f = {init}\n    w(h.f{extra})\n    return {rd('h.f')}\n")
        programs[f"{name}_element"] = (
            head + main + f"    var a: [3]{t}\n    {start}\n    w(a[1]{extra})\n"
            f"    return {rd('a[1]')}\n")
        programs[f"{name}_deref_pointer"] = (
            head + main + f"    var v: {t} = {init}\n    let p: *{t} = @v\n    w(*p{extra})\n"
            f"    return {rd('v')}\n")
        programs[f"{name}_deref_reference"] = (
            head + f"fn go(p: @&{t}{go_param})\n    w(*p{go_extra})\n\n"
            + main + f"    var v: {t} = {init}\n    go(@&v{extra})\n    return {rd('v')}\n")
        programs[f"{name}_field_through_pointer"] = (
            head + f"struct H\n    a: i64\n    f: {t}\n\n"
            f"fn go(p: *H{go_param})\n    w(p.f{go_extra})\n\n"
            + main + f"    var h: H\n    h.f = {init}\n    go(@h{extra})\n    return {rd('h.f')}\n")
        programs[f"{name}_field_through_reference"] = (
            head + f"struct H\n    a: i64\n    f: {t}\n\n"
            f"fn go(p: @&H{go_param})\n    w(p.f{go_extra})\n\n"
            + main + f"    var h: H\n    h.f = {init}\n    go(@&h{extra})\n    return {rd('h.f')}\n")
        programs[f"{name}_field_through_borrow"] = (
            head + f"struct H\n    a: i64\n    f: {t}\n\n"
            f"fn go(p:& H{go_param})\n    w(p.f{go_extra})\n\n"
            + main + f"    var h: H\n    h.f = {init}\n    go(h{extra})\n    return {rd('h.f')}\n")
        programs[f"{name}_global"] = (
            head + f"var g: {t}\n\n" + main + f"    {start.replace('a[1]', 'g')}\n    w(g{extra})\n"
            f"    return {rd('g')}\n")
    return programs


TABLE = _table()
# name -> AGAST ticket, for a row ritz1 can't run yet (strict xfail).
TABLE_GAPS = {}

# The same borrow through each way of calling.
INT_WRITER = "fn w(r:& i32)\n    r = 3\n\n"
S = "struct S\n    v: i32\n\n"
ROUTES = {
    "second_argument": "fn w(k: i32, r:& i32)\n    r = 3\n\n"
                       "pub fn main() -> i32\n    var n: i32 = 1\n    w(0, n)\n    return n\n",
    "two_borrows": "fn w(a:& i32, b:& i32)\n    a = 1\n    b = 2\n\n"
                   "pub fn main() -> i32\n    var m: i32 = 0\n    var n: i32 = 0\n"
                   "    w(m, n)\n    return m + n\n",
    "method": S + "impl S\n    fn put(self: @&S, r:& i32)\n        r = 3\n\n"
                  "pub fn main() -> i32\n    var s: S = S { v: 0 }\n    var n: i32 = 1\n"
                  "    s.put(n)\n    return n\n",
    "method_struct": C + S + "impl S\n    fn put(self: @&S, r:& C)\n        r.x = 3\n\n"
                  "pub fn main() -> i32\n    var s: S = S { v: 0 }\n"
                  "    var c: C = C { x: 1, y: 0 }\n    s.put(c)\n    return c.x\n",
    "method_pointer": C + S + "impl S\n    fn put(self: @&S, r:& *C, d: *C)\n        r = d\n\n"
                  "pub fn main() -> i32\n    var s: S = S { v: 0 }\n" + GOOD +
                  "    var p: *C = @c1\n    s.put(p, @c3)\n    return p.x\n",
    "method_on_a_global": S + "impl S\n    fn put(self: @&S, r:& i32)\n        r = 3\n\n"
                          "var g: S\n\n"
                          "pub fn main() -> i32\n    var n: i32 = 1\n    g.put(n)\n    return n\n",
    "static_method": S + "impl S\n    fn put(r:& i32)\n        r = 3\n\n"
                  "pub fn main() -> i32\n    var n: i32 = 1\n    S.put(n)\n    return n\n",
    "static_method_struct": C + S + "impl S\n    fn put(r:& C)\n        r.x = 3\n\n"
                  "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n    S.put(c)\n"
                  "    return c.x\n",
    "generic_int": "fn w<T>(r:& T, v: T)\n    r = v\n\n"
                   "pub fn main() -> i32\n    var n: i32 = 1\n    w<i32>(n, 3)\n    return n\n",
    "generic_struct": C + "fn id<T>(r:& T) -> @&T\n    return @&r\n\n"
                      "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n"
                      "    let p: @&C = id<C>(c)\n    p.x = 3\n    return c.x\n",
    "generic_pointer": C + GENERIC_WRITER + "pub fn main() -> i32\n" + GOOD +
                       "    var p: *C = @c1\n    w<*C>(p, @c3)\n    return p.x\n",
    "generic_pointer_explicit": C + GENERIC_WRITER + "pub fn main() -> i32\n" + GOOD +
                                "    var p: *C = @c1\n    w<*C>(@&p, @c3)\n    return p.x\n",
    "generic_pointer_to_int": GENERIC_WRITER + "pub fn main() -> i32\n    var a: i32 = 1\n"
                              "    var b: i32 = 3\n    var p: *i32 = @a\n    w<*i32>(p, @b)\n"
                              "    return *p\n",
    "generic_pointer_to_byte": GENERIC_WRITER + "pub fn main() -> i32\n    var a: u8 = 1\n"
                               "    var b: u8 = 3\n    var p: *u8 = @a\n    w<*u8>(p, @b)\n"
                               "    return *p as i32\n",
    # The space is #2355: ritz1 won't close `w<*B<i32>>`.
    "generic_pointer_to_generic": "struct B<T>\n    v: T\n\n" + GENERIC_WRITER +
                                  "pub fn main() -> i32\n    var b1: B<i32> = B<i32> { v: 1 }\n"
                                  "    var b3: B<i32> = B<i32> { v: 3 }\n    var p: *B<i32> = @b1\n"
                                  "    w<*B<i32> >(p, @b3)\n    return p.v\n",
    "generic_pointer_to_float": GENERIC_WRITER + "pub fn main() -> i32\n    var a: f64 = 1.0\n"
                                "    var b: f64 = 3.0\n    var p: *f64 = @a\n    w<*f64>(p, @b)\n    return *p as i32\n",
    "generic_pointer_to_pointer": C + GENERIC_WRITER + "pub fn main() -> i32\n" + GOOD +
                                  "    var p: *C = @c1\n    var q: *C = @c3\n    var pp: **C = @p\n"
                                  "    var qq: **C = @q\n    w<**C>(pp, qq)\n    return (*pp).x\n",
    # A borrow of `pp` writes `pp`, and leaves the `p` it points at alone.
    "generic_pointer_to_pointer_owner": C + GENERIC_WRITER + "pub fn main() -> i32\n" + GOOD +
                                        "    var p: *C = @c1\n    var q: *C = @c3\n"
                                        "    var pp: **C = @p\n    var qq: **C = @q\n"
                                        "    w<**C>(pp, qq)\n    return p.x + 2\n",
    "generic_pointer_second_param": C + "fn w<U, T>(u: U, r:& T, v: T)\n    r = v\n\n"
                                    "pub fn main() -> i32\n" + GOOD + "    var p: *C = @c1\n"
                                    "    w<i32, *C>(0, p, @c3)\n    return p.x\n",
    "generic_pointer_element": C + GENERIC_WRITER + "pub fn main() -> i32\n" + GOOD +
                               "    var a: [2]*C = [@c1, @c1]\n    w<*C>(a[1], @c3)\n"
                               "    return a[1].x\n",
    "generic_pointer_field": C + "struct H\n    p: *C\n\n" + GENERIC_WRITER +
                             "pub fn main() -> i32\n" + GOOD + "    var h: H = H { p: @c1 }\n"
                             "    w<*C>(h.p, @c3)\n    return h.p.x\n",
    "generic_pointer_pass_on": C + GENERIC_WRITER + "fn go<T>(h:& T, v: T)\n    w<T>(h, v)\n\n"
                               "pub fn main() -> i32\n" + GOOD + "    var p: *C = @c1\n"
                               "    go<*C>(p, @c3)\n    return p.x\n",
    "generic_pointer_read": C + "fn g<T>(r:& T) -> T\n    return r\n\n"
                            "pub fn main() -> i32\n" + GOOD + "    var p: *C = @c3\n"
                            "    let q: *C = g<*C>(p)\n    return q.x\n",
    "generic_pointer_read_field": C + "fn g<T>(r:& T) -> i32\n    return r.x\n\n"
                                  "pub fn main() -> i32\n" + GOOD + "    var p: *C = @c3\n"
                                  "    return g<*C>(p)\n",
    "generic_pointer_read_deref": "fn g<T>(r:& T) -> i32\n    return *r\n\n"
                                  "pub fn main() -> i32\n    var a: i32 = 3\n    var p: *i32 = @a\n"
                                  "    return g<*i32>(p)\n",
    # Already right; they clone through the same code, so they stay right.
    "generic_pointer_returned": C + "fn id<T>(r:& T) -> @&T\n    return @&r\n\n"
                                "pub fn main() -> i32\n" + GOOD + "    var p: *C = @c1\n"
                                "    let q: @&*C = id<*C>(p)\n    *q = @c3\n    return p.x\n",
    "generic_pointer_named_reference": C + "fn w<T>(r: @&T, v: T)\n    *r = v\n\n"
                                       "pub fn main() -> i32\n" + GOOD + "    var p: *C = @c1\n"
                                       "    w<*C>(@&p, @c3)\n    return p.x\n",
    # At a T that's no pointer, `@&T` holds no pointer to record.
    "generic_reference_from_pointer": C + "fn g<T>(p: @&T)\n    p.x = 3\n\n"
                                      "fn go(h:& *C)\n    g<C>(h)\n\n"
                                      "pub fn main() -> i32\n" + GOOD + "    var p: *C = @c1\n"
                                      "    go(p)\n    return c1.x\n",
    "generic_reference_from_int_pointer": "fn g<T>(p: @&T)\n    *p = 3\n\n"
                                          "fn go(h:& *i32)\n    g<i32>(h)\n\n"
                                          "pub fn main() -> i32\n    var a: i32 = 1\n"
                                          "    var p: *i32 = @a\n    go(p)\n    return a\n",
    "generic_caller": INT_WRITER + "fn go<T>(v: T) -> T\n    var x: T = v\n    w(x)\n    return x\n\n"
                      "pub fn main() -> i32\n    return go<i32>(1)\n",
    "index_evaluated_once": INT_WRITER + "var calls: i32 = 0\n\nfn next() -> i64\n"
                            "    calls = calls + 1\n    return 1\n\n"
                            "pub fn main() -> i32\n    var a: [3]i32 = [1, 1, 1]\n    w(a[next()])\n"
                            "    return a[1] + calls - 1\n",
    "nested_array": "fn w(a:& [2][3]i32)\n    a[1][2] = 3\n\n"
                    "pub fn main() -> i32\n    var a: [2][3]i32\n    a[1][2] = 1\n    w(a)\n"
                    "    return a[1][2]\n",
    "element_of_a_field": INT_WRITER + "struct H\n    a: i64\n    f: [3]i32\n\n"
                          "pub fn main() -> i32\n    var h: H\n    h.f[1] = 1\n    w(h.f[1])\n"
                          "    return h.f[1]\n",
    "field_of_an_element": INT_WRITER + C + "pub fn main() -> i32\n    var a: [2]C\n"
                           "    a[1].x = 1\n    w(a[1].x)\n    return a[1].x\n",
    "element_through_pointer": INT_WRITER + "pub fn main() -> i32\n"
                               "    var a: [3]i32 = [1, 1, 1]\n    let p: *i32 = @a[0]\n"
                               "    w(p[1])\n    return a[1]\n",
    "deref_of_arithmetic": INT_WRITER + "pub fn main() -> i32\n"
                           "    var a: [3]i32 = [1, 1, 1]\n    let p: *i32 = @a[0]\n"
                           "    w(*(p + 1))\n    return a[1]\n",
    "in_a_loop": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 0\n"
                 "    for i in 0..3\n        w(n)\n    return n\n",
    "deref_of_a_borrow": INT_WRITER + C + "fn go(c:& C)\n    w((*c).x)\n\n"
                         "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n    go(c)\n"
                         "    return c.x\n",
    "whole_deref_of_a_borrow": C + "fn w(r:& C)\n    r.x = 3\n\nfn go(c:& C)\n    w(*c)\n\n"
                               "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n    go(c)\n"
                               "    return c.x\n",
    "pointer_pass_on": C + "fn g(m:& *C, d: *C)\n    m = d\n\n"
                       "fn go(h:& *C, d: *C)\n    g(h, d)\n\n"
                       "pub fn main() -> i32\n" + GOOD +
                       "    var p: *C = @c1\n    go(p, @c3)\n    return p.x\n",
    "pointer_method_result": INT_WRITER + C + "impl C\n    fn px(self: @&C) -> *i32\n"
                             "        return @self.x\n\n"
                             "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n    w(c.px())\n"
                             "    return c.x\n",
    "reference_method_result": INT_WRITER + C + "impl C\n    fn px(self: @&C) -> @&i32\n"
                               "        return @&self.x\n\n"
                               "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n    w(c.px())\n"
                               "    return c.x\n",
    "self_field": INT_WRITER + C + "impl C\n    fn go(self: @&C)\n        w(self.x)\n\n"
                  "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n    c.go()\n    return c.x\n",
    "generic_struct_type": "struct B<T>\n    v: T\n\nfn w(r:& B<i32>)\n    r.v = 3\n\n"
                           "pub fn main() -> i32\n    var b: B<i32> = B<i32> { v: 1 }\n    w(b)\n"
                           "    return b.v\n",
    # AGAST #2994: the callee's `b` is a `bool` in a condition, a loop, an
    # operand and a by-value argument.
    "bool_conditions": "fn id(x: bool) -> bool\n    return x\n\n"
                       "fn w(b:& bool) -> i32\n    var n: i32 = 0\n    while not b\n"
                       "        b = true\n    if b\n        n = n + 1\n    if b and id(b)\n"
                       "        n = n + 1\n    return n\n\n"
                       "pub fn main() -> i32\n    var b: bool = false\n    let n: i32 = w(b)\n"
                       "    return n + (b as i32)\n",
    "aliased_type": "type N = i32\n\nfn w(r:& N)\n    r = 3\n\n"
                    "pub fn main() -> i32\n    var n: i32 = 1\n    w(n)\n    return n\n",
}


# ritz1's callee, not the call, and not generic: `:& **C` and `:& *f64` don't
# bind as their referent either.
ROUTE_GAPS = {
    "generic_pointer_to_float": "AGAST #2086: `r = v` in a `:& *f64` writes nothing",
    "generic_pointer_to_pointer": "AGAST #2086: `r = v` in a `:& **C` writes nothing",
}


def _neighbours(t: str, writer: str) -> str:
    """A write through `:& T` leaves the elements either side alone."""
    return writer + f"""
pub fn main() -> i32
    var a: [3]{t} = [1, 1, 1]
    w(a[1])
    if (a[0] as i32) != 1
        return 41
    if (a[2] as i32) != 1
        return 42
    return a[1] as i32
"""


WIDTHS = {t: _neighbours(t, f"fn w(r:& {t})\n    r = 3\n")
          for t in ("i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64")}
# A `bool` is no integer, so it gets its own neighbours (AGAST #2994).
WIDTHS["bool"] = """fn w(r:& bool)
    r = not r

pub fn main() -> i32
    var a: [3]bool = [true, false, true]
    w(a[1])
    if not a[0]
        return 41
    if not a[2]
        return 42
    return (a[1] as i32) * 3
"""

# The ruling's `:&` row: what isn't a place of `T` passes as the pointer it is.
POINTER_FAMILY = {
    "pointer_local": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                     "    let p: *i32 = @n\n    w(p)\n    return n\n",
    "pointer_let_struct": C + "fn w(r:& C)\n    r.x = 3\n\n"
                          "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n"
                          "    let p: *C = @c\n    w(p)\n    return c.x\n",
    "reference_param": INT_WRITER + "fn go(p: @&i32)\n    w(p)\n\n"
                       "pub fn main() -> i32\n    var n: i32 = 1\n    go(@&n)\n    return n\n",
    "pointer_param": INT_WRITER + "fn go(p: *i32)\n    w(p)\n\n"
                     "pub fn main() -> i32\n    var n: i32 = 1\n    go(@n)\n    return n\n",
    "pointer_field": INT_WRITER + "struct H\n    p: *i32\n\n"
                     "pub fn main() -> i32\n    var n: i32 = 1\n    var h: H\n    h.p = @n\n"
                     "    w(h.p)\n    return n\n",
    "pointer_element": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                       "    var a: [2]*i32\n    a[1] = @n\n    w(a[1])\n    return n\n",
    "pointer_call": INT_WRITER + "fn id(p: *i32) -> *i32\n    return p\n\n"
                    "pub fn main() -> i32\n    var n: i32 = 1\n    w(id(@n))\n    return n\n",
    "reference_call": INT_WRITER + "fn id(p: @&i32) -> @&i32\n    return p\n\n"
                      "pub fn main() -> i32\n    var n: i32 = 1\n    w(id(@&n))\n    return n\n",
    "pointer_arithmetic": INT_WRITER + "pub fn main() -> i32\n    var a: [3]i32 = [1, 1, 1]\n"
                          "    let p: *i32 = @a[0]\n    w(p + 1)\n    return a[1]\n",
    "pointer_cast": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                    "    let q: *u8 = @n as *u8\n    w(q as *i32)\n    return n\n",
    "pointer_to_pointer": C + "fn w(r:& *C, d: *C)\n    r = d\n\n"
                          "pub fn main() -> i32\n" + GOOD +
                          "    var p: *C = @c1\n    let pp: **C = @p\n    w(pp, @c3)\n    return p.x\n",
    "bool_pointer": "fn w(r:& bool)\n    r = true\n\npub fn main() -> i32\n"
                    "    var b: bool = false\n    let p: *bool = @b\n    w(p)\n"
                    "    return (b as i32) * 3\n",
    "explicit_mut": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n    w(@&n)\n    return n\n",
    "explicit_pointer_referent": C + "fn w(r:& *C, d: *C)\n    r = d\n\n"
                                 "pub fn main() -> i32\n" + GOOD +
                                 "    var p: *C = @c1\n    w(@&p, @c3)\n    return p.x\n",
    "let_pointer_passes_what_it_holds": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                                        "    let p: *i32 = @n\n    w(p)\n    return n\n",
    "let_struct_through_pointer": INT_WRITER + C + "pub fn main() -> i32\n"
                                  "    var c: C = C { x: 1, y: 0 }\n    let p: *C = @c\n"
                                  "    w(p.x)\n    return c.x\n",
}

RVALUE = "needs a place to borrow"
RVALUES = {
    "sum": (INT_WRITER, "w(1 + 2)"),
    "literal": (INT_WRITER, "w(3)"),
    "cast": (INT_WRITER, "w(v as i32)"),
    "call": ("fn g() -> i32\n    return 1\n\n" + INT_WRITER, "w(g())"),
    "if_value": (INT_WRITER, "w(if v > 0 then v else 2)"),
    "struct_call": (C + "fn g() -> C\n    return C { x: 1, y: 0 }\n\n"
                    "fn w(r:& C)\n    r.x = 3\n\n", "w(g())"),
    "struct_literal": (C + "fn w(r:& C)\n    r.x = 3\n\n", "w(C { x: 1, y: 0 })"),
    "field_of_a_call": (C + "fn g() -> C\n    return C { x: 1, y: 0 }\n\n" + INT_WRITER, "w(g().x)"),
    "method_result": (S + "impl S\n    fn get(self: @S) -> i32\n        return 1\n\n" + INT_WRITER,
                      "var s: S = S { v: 0 }\n    w(s.get())"),
    "method_result_on_a_global": (S + "impl S\n    fn get(self: @S) -> i32\n        return 1\n\n"
                                  "var g: S\n\n" + INT_WRITER, "w(g.get())"),
    "array_literal": ("fn w(r:& [2]i32)\n    r[1] = 3\n\n", "w([1, 2])"),
    "pointer_call": (C + "fn g(p: *C) -> *C\n    return p\n\nfn w(r:& *C)\n    r = null\n\n",
                     "w(g(null))"),
    "null": (INT_WRITER, "w(null)"),
    "bool_literal": ("fn w(r:& bool)\n    r = true\n\n", "w(true)"),
    "c_string": ("fn w(r:& u8)\n    r = 3\n\n", 'w(c"x")'),
    "const": ("const K: i32 = 1\n\n" + INT_WRITER, "w(K)"),
    # A slice makes a value, so nothing reached through one is a place.
    "slice": (INT_WRITER, "var a: [4]i32\n    w(a[0..2])"),
    "element_of_a_slice": (INT_WRITER, "var a: [4]i32\n    w(a[0..2][0])"),
}
RVALUE_METHODS = {
    "method": (S + "impl S\n    fn put(self: @&S, r:& i32)\n        r = 3\n\n",
               "var s: S = S { v: 0 }\n    s.put(1 + 2)"),
    "method_on_a_global": (S + "impl S\n    fn put(self: @&S, r:& i32)\n        r = 3\n\n"
                           "var g: S\n\n", "g.put(1 + 2)"),
    "static_method": (S + "impl S\n    fn put(r:& i32)\n        r = 3\n\n", "S.put(1 + 2)"),
    "generic": ("fn w<T>(r:& T)\n    r = r\n\n", "w<i32>(1 + 2)"),
}

SHARED = "can't borrow through an `@T`"
SHARED_PLACES = {
    "field": (INT_WRITER + C, "fn go(r: @C)\n    w(r.x)\n\n"),
    "deref": (INT_WRITER, "fn go(r: @i32)\n    w(*r)\n\n"),
    "bare": (INT_WRITER, "fn go(r: @i32)\n    w(r)\n\n"),
    "bare_array": ("fn w(r:& [2]i32)\n    r[1] = 3\n\n",
                   "fn go()\n    var a: [2]i32 = [1, 3]\n    let p: @[2]i32 = @a\n    w(p)\n\n"),
    "element": (INT_WRITER, "fn go(r: @[2]i32)\n    w((*r)[1])\n\n"),
    "field_of_a_field": (INT_WRITER + C + "struct H\n    c: C\n\n",
                         "fn go(r: @H)\n    w(r.c.x)\n\n"),
    "typed_let": (INT_WRITER + C, "fn go(c:& C)\n    let r: @C = @c\n    w(r.x)\n\n"),
    "call_result": (INT_WRITER + "fn id(r: @i32) -> @i32\n    return r\n\n",
                    "fn go(r: @i32)\n    w(id(r))\n\n"),
    # `let p = @x` is an `@T` with no annotation to say so.
    "inferred_array": ("fn w(r:& [2]i32)\n    r[1] = 3\n\n",
                       "fn go()\n    var a: [2]i32 = [1, 3]\n    let p = @a\n    w(p)\n\n"),
    "inferred_copy": ("fn w(r:& [2]i32)\n    r[1] = 3\n\n",
                      "fn go()\n    var a: [2]i32 = [1, 3]\n    let p = @a\n    let q = p\n    w(q)\n\n"),
    "inferred_struct": ("fn w(r:& C)\n    r.x = 3\n\n" + C,
                        "fn go()\n    var c: C = C { x: 1, y: 0 }\n    let p = @c\n    w(p)\n\n"),
    "inferred_field": (INT_WRITER + C,
                       "fn go()\n    var c: C = C { x: 1, y: 0 }\n    let p = @c\n    w(p.x)\n\n"),
    "inferred_struct_copy": (INT_WRITER + C,
                             "fn go()\n    var c: C = C { x: 1, y: 0 }\n    let p = @c\n    let q = p\n    w(q.x)\n\n"),
    "inferred_scalar": (INT_WRITER, "fn go()\n    var n: i32 = 1\n    let p = @n\n    w(p)\n\n"),
    "inferred_scalar_deref": (INT_WRITER, "fn go()\n    var n: i32 = 1\n    let p = @n\n    w(*p)\n\n"),
    "inferred_scalar_copy": (INT_WRITER, "fn go()\n    var n: i32 = 1\n    let p = @n\n    let q = p\n    w(*q)\n\n"),
    "inferred_copy_of_a_param": (INT_WRITER + C, "fn go(r: @C)\n    let q = r\n    w(q.x)\n\n"),
    "inferred_copy_of_a_scalar_param": (INT_WRITER, "fn go(r: @i32)\n    let q = r\n    w(q)\n\n"),
    "inferred_deref_of_a_copied_param": (INT_WRITER, "fn go(r: @i32)\n    let q = r\n    w(*q)\n\n"),
    "inferred_struct_deref": ("fn w(r:& C)\n    r.x = 3\n\n" + C,
                              "fn go()\n    var c: C = C { x: 1, y: 0 }\n    let p = @c\n    w(*p)\n\n"),
    "inferred_element": (INT_WRITER + C, "fn go()\n    var a: [2]C\n    let p = @a[1]\n    w(p.x)\n\n"),
}
# An un-annotated `@&` local is an `@&T`, a scalar one too (#2352). All legal under R1.
INFERRED_MUT = {
    "mut_scalar": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                  "    let p = @&n\n    w(p)\n    return n\n",
    "mut_scalar_deref": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                        "    let p = @&n\n    w(*p)\n    return n\n",
    "mut_copy": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                "    let p = @&n\n    let q = p\n    w(*q)\n    return n\n",
    "mut_copy_bare": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                     "    let p = @&n\n    let q = p\n    w(q)\n    return n\n",
    "mut_var": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
               "    var p = @&n\n    w(*p)\n    return n\n",
}
# A nearer `@&T` or `*T` is what the place is reached through.
NOT_SHARED = {
    "inferred_mut_field": INT_WRITER + C + "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n"
                          "    let p = @&c\n    w(p.x)\n    return c.x\n",
    "inferred_mut_struct_deref": "fn w(r:& C)\n    r.x = 3\n\n" + C + "pub fn main() -> i32\n"
                                 "    var c: C = C { x: 1, y: 0 }\n    let p = @&c\n    w(*p)\n    return c.x\n",
    "inferred_mut_array": "fn w(r:& [2]i32)\n    r[1] = 3\n\n"
                          "pub fn main() -> i32\n    var a: [2]i32 = [1, 2]\n"
                          "    let p = @&a\n    w(p)\n    return a[1]\n",
    "raw_pointer_from_an_at": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n"
                              "    let p: *i32 = @n\n    w(p)\n    return n\n",
    "pointer_in_a_shared_struct": INT_WRITER + "struct H\n    p: *i32\n\n"
                                  "fn go(r: @H)\n    w(*r.p)\n\n"
                                  "pub fn main() -> i32\n    var n: i32 = 1\n    var h: H\n"
                                  "    h.p = @n\n    go(@h)\n    return n\n",
    "field_through_that_pointer": INT_WRITER + C + "struct H\n    p: *C\n\n"
                                  "fn go(r: @H)\n    w(r.p.x)\n\n"
                                  "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n    var h: H\n"
                                  "    h.p = @c\n    go(@h)\n    return c.x\n",
}

LET_PLACES = {
    "int": (INT_WRITER, "let n: i32 = 1\n    w(n)", "n"),
    "struct": (C + "fn w(r:& C)\n    r.x = 3\n\n", "let c: C = C { x: 1, y: 0 }\n    w(c)", "c"),
    "array": ("fn w(r:& [2]i32)\n    r[1] = 3\n\n", "let a: [2]i32 = [1, 1]\n    w(a)", "a"),
    "pointer": (C + "fn w(r:& *C)\n    r = null\n\n", "let p: *C = null\n    w(p)", "p"),
    "field": (INT_WRITER + C, "let c: C = C { x: 1, y: 0 }\n    w(c.x)", "c"),
    "element": (INT_WRITER, "let a: [2]i32 = [1, 1]\n    w(a[1])", "a"),
    "generic": ("fn w<T>(r:& T)\n    r = r\n\n", "let n: i32 = 1\n    w<i32>(n)", "n"),
    "static_method": (S + "impl S\n    fn put(r:& i32)\n        r = 3\n\n",
                      "let n: i32 = 1\n    S.put(n)", "n"),
    "method": (S + "impl S\n    fn put(self: @&S, r:& i32)\n        r = 3\n\n",
               "var s: S = S { v: 0 }\n    let n: i32 = 1\n    s.put(n)", "n"),
    "method_on_a_global": (S + "impl S\n    fn put(self: @&S, r:& i32)\n        r = 3\n\n"
                           "var g: S\n\n", "let n: i32 = 1\n    g.put(n)", "n"),
}

MISFITS = {
    "wider": (INT_WRITER.replace("i32", "i64"), "var n: i32 = 1\n    w(n)"),
    "narrower": (INT_WRITER, "var n: i64 = 1\n    w(n)"),
    "field": (INT_WRITER.replace("i32", "i64") + C, "var c: C = C { x: 1, y: 0 }\n    w(c.x)"),
    "element": (INT_WRITER.replace("i32", "i64"), "var a: [2]i32 = [1, 1]\n    w(a[1])"),
    "deref": (INT_WRITER.replace("i32", "i64"), "var n: i32 = 1\n    let p: *i32 = @n\n    w(*p)"),
    "float": (INT_WRITER.replace("i32", "i64"), "var f: f64 = 1.0\n    w(f)"),
    "struct": (C + "struct D\n    a: i32\n\nfn w(r:& C)\n    r.x = 3\n\n",
               "var d: D = D { a: 1 }\n    w(d)"),
    "struct_for_int": (C + INT_WRITER, "var c: C = C { x: 1, y: 0 }\n    w(c)"),
    "int_for_struct": (C + "fn w(r:& C)\n    r.x = 3\n\n", "var n: i32 = 1\n    w(n)"),
    "pointee": (C + "struct D\n    a: i32\n\nfn w(r:& *C)\n    r = null\n\n",
                "var p: *D = null\n    w(p)"),
    "int_for_pointer": (C + "fn w(r:& *C)\n    r = null\n\n", "var n: i64 = 1\n    w(n)"),
    "generic_pointee": (C + "struct D\n    a: i32\n\n" + GENERIC_WRITER,
                        "var d: D = D { a: 1 }\n    var p: *D = @d\n    w<*C>(p, null)"),
    "generic_pointee_width": (GENERIC_WRITER, "var n: i32 = 1\n    var p: *i32 = @n\n    w<*i64>(p, null)"),
    # A copy of the param would take the write: it has no storage to borrow.
    "reference_for_pointer": (C + "fn w(r:& *C)\n    r = null\n\nfn go(r: @&C)\n    w(r)\n\n",
                              "v = 2"),
    # Exactly the same type, not the same width (Aaron's ruling on #2368): one
    # sign for another is refused too, though LLVM spells both alike (#2530).
    "sign": (INT_WRITER, "var n: u32 = 1\n    w(n)"),
    "array_sign": ("fn w(a:& [2]i32)\n    a[1] = 3\n\n", "var a: [2]u32 = [1, 2]\n    w(a)"),
    "element_sign": (INT_WRITER, "var a: [2]u32 = [1, 1]\n    w(a[1])"),
    "pointee_sign": ("fn w(r:& *i32)\n    r = null\n\n", "var p: *u32 = null\n    w(p)"),
    "generic_sign": (GENERIC_WRITER, "var n: u32 = 1\n    w<i32>(n, 3)"),
    # AGAST #2994: a `bool` local fits `:& bool`, and still no byte, either
    # sign, nor the `i64` its slot is kept as.
    "u8_for_bool": ("fn w(r:& bool)\n    r = true\n\n", "var n: u8 = 1\n    w(n)"),
    "i8_for_bool": ("fn w(r:& bool)\n    r = true\n\n", "var n: i8 = 1\n    w(n)"),
    "bool_for_u8": ("fn w(r:& u8)\n    r = 3\n\n", "var b: bool = false\n    w(b)"),
    "bool_for_i64": (INT_WRITER.replace("i32", "i64"), "var b: bool = false\n    w(b)"),
}
# ritz0's method paths convert what they're given, so these need their own check.
METHOD_MISFITS = {
    "method": (S + "impl S\n    fn put(self: @&S, r:& i64)\n        r = 3\n\n",
               "var s: S = S { v: 0 }\n    s.put(v)", 2),
    "method_on_a_global": (S + "impl S\n    fn put(self: @&S, r:& i64)\n        r = 3\n\n"
                           "var g: S\n\n", "g.put(v)", 2),
    "static_method": (S + "impl S\n    fn put(r:& i64)\n        r = 3\n\n", "S.put(v)", 1),
    # `v` is an `i32`; #2530's sign, on each of ritz0's method paths.
    "method_sign": (S + "impl S\n    fn put(self: @&S, r:& u32)\n        r = 3\n\n",
                    "var s: S = S { v: 0 }\n    s.put(v)", 2),
    "static_method_sign": (S + "impl S\n    fn put(r:& u32)\n        r = 3\n\n", "S.put(v)", 1),
}

DROPS = """\
struct R
    n: i32

var drops: i32 = 0

impl Drop for R
    fn drop(self: @&R)
        drops = drops + 1

fn w(r:& R)
    r.n = 3

pub fn main() -> i32
    var r: R = R { n: 1 }
    w(r)
    w(r)
    return r.n
"""

DROP_COUNT = DROPS.replace(
    "pub fn main() -> i32\n    var r: R = R { n: 1 }\n    w(r)\n    w(r)\n    return r.n\n",
    "fn go()\n    var r: R = R { n: 1 }\n    w(r)\n    w(r)\n\n"
    "pub fn main() -> i32\n    go()\n    return drops + 2\n")

IMMUTABLE = "cannot borrow `n` as mutable - `n` is already borrowed as immutable"
ALIASED = {
    "shared": (INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n    let p = @n\n"
               "    w(n)\n    return *p\n", IMMUTABLE),
    "method": (S + "impl S\n    fn put(self: @&S, r:& i32)\n        r = 3\n\n"
               "pub fn main() -> i32\n    var s: S = S { v: 0 }\n    var n: i32 = 1\n"
               "    let p = @n\n    s.put(n)\n    return *p\n", IMMUTABLE),
    "twice": ("fn w(a:& i32, b:& i32)\n    a = 1\n\n"
              "pub fn main() -> i32\n    var n: i32 = 1\n    w(n, n)\n    return n\n",
              "cannot borrow `n` as mutable - `n` is already borrowed as mutable"),
}
NOT_ALIASED = {
    "shared_pointer": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n    var p: *i32 = @n\n"
                      "    let q = @p\n    w(p)\n    return n\n",
    "after_the_call": INT_WRITER + "pub fn main() -> i32\n    var n: i32 = 1\n    w(n)\n    w(n)\n"
                      "    return n\n",
}


def _compile(compiler, tmp_path, name, src):
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    path = work / "main.ritz"
    path.write_text(src)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300), ll, work
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    proc = subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc, ll, work


def _run(compiler, tmp_path, name, src):
    comp, ll, work = _compile(compiler, tmp_path, name, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused {name}:\n{src}\n{out[-2000:]}"
    exe = work / "main"
    cmd = ["clang", "-Wno-override-module", str(ll), "-o", str(exe), "-nostdlib", "-no-pie"]
    if compiler != "ritz0":
        cmd.insert(1, str(RITZ_START))
    link = fast_link.clang(cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: {name} would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _error(compiler, tmp_path, name, src):
    """`line:col: message` of the located error `compiler` refuses `src` with."""
    comp, ll, _ = _compile(compiler, tmp_path, name, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name}:\n{src}"
    assert not ll.exists()
    found = re.search(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert found, f"{compiler}: {name} has no location:\n{out[-2000:]}"
    return f"{found.group(1)}: {found.group(2).strip()}"


def _main(setup, body):
    return setup + "pub fn main() -> i32\n    var v: i32 = 1\n    " + body + "\n    return 0\n"


def _table_params():
    for name in sorted(TABLE):
        for compiler in COMPILERS:
            reason = TABLE_GAPS.get(name) if compiler != "ritz0" else None
            marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.parametrize("name,compiler", list(_table_params()))
def test_a_place_is_borrowed(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, TABLE[name]) == 3


def _route_params():
    for name in sorted(ROUTES):
        for compiler in COMPILERS:
            reason = ROUTE_GAPS.get(name) if compiler != "ritz0" else None
            marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.parametrize("name,compiler", list(_route_params()))
def test_each_way_of_calling_borrows(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, ROUTES[name]) == 3


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("t", sorted(WIDTHS))
def test_a_borrow_writes_its_width(tmp_path, compiler, t):
    assert _run(compiler, tmp_path, t, WIDTHS[t]) == 3


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(POINTER_FAMILY))
def test_a_pointer_passes_as_the_pointer_it_is(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, POINTER_FAMILY[name]) == 3


@pytest.mark.parametrize("name", sorted(RVALUES))
def test_an_rvalue_is_refused_alike(tmp_path, name):
    setup, body = RVALUES[name]
    src = _main(setup, body)
    errors = {c: _error(c, tmp_path, name, src) for c in COMPILERS}
    assert RVALUE in errors["ritz0"], errors
    assert len(set(errors.values())) == 1, errors


@pytest.mark.parametrize("name", sorted(RVALUE_METHODS))
def test_an_rvalue_is_refused_on_each_way_of_calling(tmp_path, name):
    setup, body = RVALUE_METHODS[name]
    src = _main(setup, body)
    errors = {c: _error(c, tmp_path, name, src) for c in COMPILERS}
    assert RVALUE in errors["ritz0"], errors
    assert len(set(errors.values())) == 1, errors


@pytest.mark.parametrize("name", sorted(LET_PLACES))
def test_a_let_place_is_refused_alike(tmp_path, name):
    setup, body, binding = LET_PLACES[name]
    src = _main(setup, body)
    errors = {c: _error(c, tmp_path, name, src) for c in COMPILERS}
    assert f"cannot borrow `let` binding `{binding}` as mutable" in errors["ritz0"], errors
    assert len(set(errors.values())) == 1, errors


@pytest.mark.parametrize("name", sorted(SHARED_PLACES))
def test_a_place_behind_an_at_t_is_refused_alike(tmp_path, name):
    setup, go = SHARED_PLACES[name]
    src = setup + go + "pub fn main() -> i32\n    return 0\n"
    errors = {c: _error(c, tmp_path, name, src) for c in COMPILERS}
    assert SHARED in errors["ritz0"], errors
    assert len(set(errors.values())) == 1, errors


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INFERRED_MUT))
def test_an_inferred_mutable_reference_passes(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, INFERRED_MUT[name]) == 3


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_var_holding_an_at_t_is_refused(tmp_path, compiler):
    src = (INT_WRITER + C + "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n"
           "    var p = @c\n    w(p.x)\n    return c.x\n")
    assert SHARED in _error(compiler, tmp_path, "var_at", src)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_SHARED))
def test_a_nearer_pointer_makes_the_place_writable(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, NOT_SHARED[name]) == 3


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(MISFITS))
def test_a_place_of_another_type_is_refused(tmp_path, compiler, name):
    setup, body = MISFITS[name]
    error = _error(compiler, tmp_path, name, _main(setup, body))
    assert re.search(r"argument 1 of `w` has the wrong type", error), error


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(METHOD_MISFITS))
def test_a_method_place_of_another_type_is_refused(tmp_path, compiler, name):
    setup, body, argno = METHOD_MISFITS[name]
    error = _error(compiler, tmp_path, name, _main(setup, body))
    assert f"argument {argno} of `put` has the wrong type" in error, error


# A reference to another type, refused on all three since #2368 (it was #2348's
# on ritz1), and no temporary.
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_explicit_borrow_of_another_type_is_no_temporary(tmp_path, compiler):
    src = INT_WRITER + "pub fn main() -> i32\n    var n: i64 = 1\n    w(@&n)\n    return 0\n"
    error = _error(compiler, tmp_path, "explicit", src)
    assert REF_TO_OTHER_TYPE in error and "temporary" not in error, error


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_borrow_does_not_move(tmp_path, compiler):
    assert _run(compiler, tmp_path, "drops", DROPS) == 3


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_borrowed_value_drops_once(tmp_path, compiler):
    assert _run(compiler, tmp_path, "drop_count", DROP_COUNT) == 3


# §13.5 on all three compilers, at one place (#2438).
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ALIASED))
def test_a_borrow_is_a_mutable_borrow_for_the_borrow_rules(tmp_path, compiler, name):
    src, needle = ALIASED[name]
    error = _error(compiler, tmp_path, name, src)
    assert needle in error, error
    if compiler != "ritz0":
        assert error == _error("ritz0", tmp_path, f"{name}_oracle", src)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_ALIASED))
def test_a_pointer_passed_on_borrows_nothing(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, NOT_ALIASED[name]) == 3


# AGAST #3079: an un-annotated `let p = @c` / `@&c` of a struct is an `@C` /
# `@&C`, and `let r = @q` of a `*T` an `@*T`, by its kind: not a `*C` / `**T`
# with a side flag.  Every use does what ritz0 does: an int is the exit code, a
# string the error.  Pointer arithmetic on it is ritz0's too: legal, as on a
# `*C` (R16 refuses an `@C` from a param or a call; #3106 asks LARB), and so is
# everything on an annotated `let p: *C = @c`.
CM = C + ("impl C\n    fn get(self: @C) -> i32\n        self.x\n"
          "    fn set(self: @&C)\n        self.x = 3\n\n"
          "fn rd(r: @C) -> i32\n    r.x\n\nfn rm(r: @&C)\n    r.x = 3\n\nfn rp(r: *C)\n    r.x = 3\n\n"
          "pub fn main() -> i32\n    var c: C = C { x: 1, y: 0 }\n")
PQ = ("enum E\n    A\n    B\n\npub fn main() -> i32\n    var n: i32 = 1\n    var m: i32 = 3\n    var q: *i32 = @n\n"
      "    var e: E = E.A\n    var qe: *E = @e\n    var a: [2]i32 = [1, 3]\n    var qa: *[2]i32 = @a\n")
WRITE_SHARED = "cannot write through an `@T`: make it `@&T`"
NOT_MUT = "an `@T` doesn't fit an `@&T` slot: make it `@&T`"
INFERRED_REFS = {
    "shared_read": (CM + "    let p = @c\n    return p.x + p.get() + rd(p)\n", 3),
    "shared_write": (CM + "    let p = @c\n    p.x = 3\n    return c.x\n", WRITE_SHARED),
    "shared_copy_write": (CM + "    let p = @c\n    let q = p\n    q.x = 3\n    return c.x\n", WRITE_SHARED),
    "shared_element_write": (CM + "    var a: [2]C\n    let p = @a[1]\n    p.x = 3\n    return 0\n", WRITE_SHARED),
    "shared_method": (CM + "    let p = @c\n    p.set()\n    return c.x\n", NOT_MUT),
    "shared_into_mut_ref": (CM + "    let p = @c\n    rm(p)\n    return c.x\n", NOT_MUT),
    "shared_into_raw": (CM + "    let p = @c\n    rp(p)\n    return c.x\n", 3),
    "shared_arith": (CM + "    var a: [2]C\n    a[1].x = 3\n    let p = @a[0]\n    let q = p + 1\n    return q.x\n", 3),
    "mut_write": (CM + "    let p = @&c\n    p.x = 3\n    return c.x\n", 3),
    "mut_method": (CM + "    let p = @&c\n    let q = p\n    q.set()\n    return c.x\n", 3),
    "mut_into_mut_ref": (CM + "    let p = @&c\n    rm(p)\n    return c.x\n", 3),
    "mut_arith": (CM + "    var a: [2]C\n    a[0].x = 3\n    let p = @&a[1]\n    let q = p\n    let r = q - 1\n    return r.x\n", 3),
    "scalar_arith": ("pub fn main() -> i32\n    var n: i32 = 1\n    let p = @n\n    let q = p + 1\n    return 3\n", 3),
    # `let r = @q` with `q: *T` is an `@*T`, of a scalar, an enum or an array.
    "pointer_shared_store": (PQ + "    let r = @q\n    *r = @m\n    return *q\n", WRITE_SHARED),
    "pointer_shared_copy_store": (PQ + "    let r = @q\n    let r2 = r\n    *r2 = @m\n    return *q\n", WRITE_SHARED),
    "pointer_shared_inner_store": (PQ + "    let r = @q\n    **r = 3\n    return n\n", 3),
    "pointer_mut_copy_store": (PQ + "    let r = @&q\n    let r2 = r\n    *r2 = @m\n    return *q\n", 3),
    "enum_pointer_shared_store": (PQ + "    var f: E = E.B\n    let r = @qe\n    *r = @f\n    return 3\n", WRITE_SHARED),
    "enum_pointer_inner_store": (PQ + "    let r = @qe\n    **r = E.B\n    return e as i32 + 2\n", 3),
    "array_pointer_shared_store": (PQ + "    var b: [2]i32 = [3, 3]\n    let r = @qa\n    *r = @b\n    return 0\n", WRITE_SHARED),
    "array_pointer_mut_store": (PQ + "    var b: [2]i32 = [3, 3]\n    let r = @&qa\n    *r = @b\n    return (*qa)[0]\n", 3),
    "annotated_raw": (CM + "    let p: *C = @c\n    p.x = 2\n    let q = p + 1\n    rp(p)\n    return c.x\n", 3),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(INFERRED_REFS))
def test_an_inferred_reference_is_its_kind(tmp_path, compiler, name):
    src, want = INFERRED_REFS[name]
    if isinstance(want, int):
        assert _run(compiler, tmp_path, name, src) == want
        return
    got = _error(compiler, tmp_path, name, src)
    assert want in got, got
    if compiler != "ritz0":
        assert got == _error("ritz0", tmp_path, name, src), "located where ritz0 says it"
