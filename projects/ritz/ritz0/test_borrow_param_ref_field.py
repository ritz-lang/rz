"""A reference to a `name:& T` parameter stored in a field, and what a by-value
field copies (AGAST #1302, #2250, #2279, #2337).

    fn mk(c:& C) -> R
        var r: R
        r.ch = @&c

`c` is an alias of the caller's place, so it has type `C` all through the body and
a `C` never fits a reference field (LANGUAGE_SPEC §13.4, LARB ruling R1). The
reference is written, `@&c` for an `@&T` or `:&` field and `@c` for a `*T` one, and
gives the caller's address. The move checker agrees: that isn't a move out of the
parameter, so a Drop type can be stored this way. A by-value field copies. A bare
`c` in a reference field is refused, as test_value_into_ref.py has it at each slot.

The ticket's other error was a tempest source bug: lib/document.ritz dereferenced
`vec_get`'s result, which is a `T` now. `./rz build tempest` still fails on other
tickets (#2221, #1858, #2222), so that file is compiled on its own here.

Every program returns 3 on success, and writes through the stored reference
after it was stored, so a pointer to a temporary copy can't pass.

ritz1 binds `n:& i32` as an `i32` local whose slot is the caller's pointer, and
leaves `c:& C` a local that reads as the pointer, so #2250 and #2279 hold it to
ritz0 on every by-value path: stores into a field or an element, `return`, a tail,
`let`/`var` with or without a type, a by-value argument and an array-literal
element. A whole `a:& [N]T` copies into a field or a local. A move-only referent
is rejected at each. RITZ1_GAPS lists what's still open.

`@x` doesn't fit a `:&` param (#2339), so one is only ever given `@&x` here.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import batching

import fast_link

from array_rules import ELEMENT_MISMATCH
from ref_rules import REF_INTO_VALUE, REF_TO_OTHER_TYPE, VALUE_INTO_MUT_REF, VALUE_INTO_SHARED_REF
from ritz0_inproc import run_ritz0
from test_ref_into_value import COMPILERS, _assert_refused

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

TYPES = """\
struct C
    x: i32
    y: i64

struct R
    n: i32
    ch:& C

struct P
    ch: *C

struct A
    ch: @&C
"""

MAIN_R = """\
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var r: R = mk(@&c)
    r.ch.x = r.ch.x + 2
    return c.x
"""

STORES = {
    "assign": TYPES + """
fn mk(c:& C) -> R
    var r: R
    r.ch = @&c
    return r
""" + MAIN_R,
    "assign_ptr_field": TYPES + """
fn mk(c:& C) -> P
    var p: P
    p.ch = @c
    return p

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var p: P = mk(@&c)
    p.ch.x = p.ch.x + 2
    return c.x
""",
    "assign_at_amp_field": TYPES + """
fn mk(c:& C) -> A
    var a: A
    a.ch = @&c
    return a

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var a: A = mk(@&c)
    a.ch.x = a.ch.x + 2
    return c.x
""",
    "assign_through_pointer": TYPES + """
fn fill(r: *R, c:& C)
    r.ch = @&c

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var r: R
    fill(@r, @&c)
    r.ch.x = r.ch.x + 2
    return c.x
""",
    "literal": TYPES + """
fn mk(c:& C) -> R
    return R { n: 1, ch: @&c }
""" + MAIN_R,
    "literal_ptr_field": TYPES + """
fn mk(c:& C) -> P
    return P { ch: @c }

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var p: P = mk(@&c)
    p.ch.x = p.ch.x + 2
    return c.x
""",
    # A generic struct's field type comes from its arguments.
    "literal_generic_struct": """\
struct C
    x: i32

struct G<T>
    p: *T

fn mk(c:& C) -> G<C>
    return G<C> { p: @c }

pub fn main() -> i32
    var c: C = C { x: 1 }
    var g: G<C> = mk(@&c)
    g.p.x = g.p.x + 2
    return c.x
""",
    # The referent is an integer, and `@n` is the caller's address of it.
    "assign_primitive": """\
struct Q
    p: *i32

fn mk(n:& i32) -> Q
    var q: Q
    q.p = @n
    return q

pub fn main() -> i32
    var n: i32 = 1
    var q: Q = mk(@&n)
    *q.p = 3
    return n
""",
    "literal_primitive": """\
struct Q
    p: *i32

fn mk(n:& i32) -> Q
    return Q { p: @n }

pub fn main() -> i32
    var n: i32 = 1
    var q: Q = mk(@&n)
    *q.p = 3
    return n
""",
}

# AGAST #2250: the other ways to reach a `*T` field of a primitive.
PRIMITIVE = """\
struct Q
    p: *i32

struct O
    q: Q

struct QA
    a: [2]Q

struct G<T>
    p: *T

struct RI
    p:& i32

struct AI
    p: @&i32
"""

MAIN_FILL_Q = """
pub fn main() -> i32
    var n: i32 = 1
    var q: Q
    fill(@q, @&n)
    *q.p = 3
    return n
"""

STORES.update({
    "nested_primitive": PRIMITIVE + """
fn mk(n:& i32) -> O
    var o: O
    o.q.p = @n
    return o

pub fn main() -> i32
    var n: i32 = 1
    var o: O = mk(@&n)
    *o.q.p = 3
    return n
""",
    "nested_literal_primitive": PRIMITIVE + """
fn mk(n:& i32) -> O
    var o: O
    o.q = Q { p: @n }
    return o

pub fn main() -> i32
    var n: i32 = 1
    var o: O = mk(@&n)
    *o.q.p = 3
    return n
""",
    "through_pointer_primitive": PRIMITIVE + """
fn fill(q: *Q, n:& i32)
    q.p = @n
""" + MAIN_FILL_Q,
    "through_explicit_deref_primitive": PRIMITIVE + """
fn fill(q: *Q, n:& i32)
    (*q).p = @n
""" + MAIN_FILL_Q,
    "through_borrow_primitive": PRIMITIVE + """
fn fill(q:& Q, n:& i32)
    q.p = @n
""" + MAIN_FILL_Q.replace("fill(@q", "fill(@&q"),
    "array_element_field_primitive": PRIMITIVE + """
fn fill(a: *QA, n:& i32)
    a.a[1].p = @n

pub fn main() -> i32
    var n: i32 = 1
    var a: QA
    fill(@a, @&n)
    *a.a[1].p = 3
    return n
""",
    "local_array_element_field_primitive": PRIMITIVE + """
fn run(n:& i32)
    var a: [2]Q
    a[1].p = @n
    *a[1].p = 3

pub fn main() -> i32
    var n: i32 = 1
    run(@&n)
    return n
""",
    "global_field_primitive": PRIMITIVE + """
var GQ: Q

fn fill(n:& i32)
    GQ.p = @n

pub fn main() -> i32
    var n: i32 = 1
    fill(@&n)
    *GQ.p = 3
    return n
""",
    # A `:&` or `@&` field of a primitive lowers to a `*T` field.
    "borrow_field_primitive": PRIMITIVE + """
fn mk(n:& i32) -> RI
    var r: RI
    r.p = @&n
    return r

pub fn main() -> i32
    var n: i32 = 1
    var r: RI = mk(@&n)
    *r.p = 3
    return n
""",
    "borrow_field_literal_primitive": PRIMITIVE + """
fn mk(n:& i32) -> RI
    return RI { p: @&n }

pub fn main() -> i32
    var n: i32 = 1
    var r: RI = mk(@&n)
    *r.p = 3
    return n
""",
    "at_amp_field_primitive": PRIMITIVE + """
fn mk(n:& i32) -> AI
    var a: AI
    a.p = @&n
    return a

pub fn main() -> i32
    var n: i32 = 1
    var a: AI = mk(@&n)
    *a.p = 3
    return n
""",
    # A generic field's pointee comes from its arguments.
    "generic_struct_primitive": PRIMITIVE + """
fn mk(n:& i32) -> G<i32>
    return G<i32> { p: @n }

pub fn main() -> i32
    var n: i32 = 1
    var g: G<i32> = mk(@&n)
    *g.p = 3
    return n
""",
    "generic_fn_primitive": PRIMITIVE + """
fn mk<T>(n:& T) -> G<T>
    return G<T> { p: @n }

pub fn main() -> i32
    var n: i32 = 1
    var g: G<i32> = mk<i32>(@&n)
    *g.p = 3
    return n
""",
    # Each width takes the same path. Sign doesn't matter here: `*i32` and
    # `u32` are the same LLVM pointee.
    "width_u8": """\
struct Q
    p: *u8

fn mk(n:& u8) -> Q
    var q: Q
    q.p = @n
    return q

pub fn main() -> i32
    var n: u8 = 1
    var q: Q = mk(@&n)
    *q.p = 3
    return n as i32
""",
    "width_i16": """\
struct Q
    p: *i16

fn mk(n:& i16) -> Q
    return Q { p: @n }

pub fn main() -> i32
    var n: i16 = 1
    var q: Q = mk(@&n)
    *q.p = 3
    return n as i32
""",
    "width_i64": """\
struct Q
    p: *i64

fn mk(n:& i64) -> Q
    return Q { p: @n }

pub fn main() -> i32
    var n: i64 = 1
    var q: Q = mk(@&n)
    *q.p = 3
    return n as i32
""",
    # Another sign is another type (#2368): `as` says so.
    "sign_cast": """\
struct Q
    p: *i32

fn mk(n:& u32) -> Q
    return Q { p: @n as *i32 }

pub fn main() -> i32
    var n: u32 = 1
    var q: Q = mk(@&n)
    *q.p = 3
    return n as i32
""",
    # A method binds its params on a path of its own.
    "method_param_primitive": PRIMITIVE + """
impl O
    fn keep(self: @O, n:& i32) -> Q
        return Q { p: @n }

pub fn main() -> i32
    var o: O
    var n: i32 = 1
    var q: Q = o.keep(@&n)
    *q.p = 3
    return n
""",
    # `@n` of a float or of `self` is the pointer ritz1 already holds.
    "float_pointer_field": """\
struct Q
    p: *f64

fn mk(n:& f64) -> Q
    var q: Q
    q.p = @n
    return q

pub fn main() -> i32
    var n: f64 = 1.0
    var q: Q = mk(@&n)
    *q.p = 3.0
    return n as i32
""",
    "self_pointer_field": TYPES + """
impl C
    fn keep(self:& C) -> P
        return P { ch: @self }

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var p: P = c.keep()
    p.ch.x = 3
    return c.x
""",
})

# A large literal is built in place, on a path of its own (#1741). ritz0 only:
# clang lowers ritz1's copy of it to a `memset` call, and -nostdlib has none.
LARGE_LITERAL = """\
struct C
    x: i32

struct L
    ch:& C
    pad: [8192]u8

fn fill(l: *L, c:& C)
    *l = L { ch: @&c, pad: [0; 8192] }

pub fn main() -> i32
    var c: C = C { x: 1 }
    var l: L
    fill(@l, @&c)
    l.ch.x = l.ch.x + 2
    return c.x
"""

# Each slot holds what it's given: a value of its own type, as it is.
CONTROLS = {
    # `c` has type `*C`: that pointer is what the field holds, not the address
    # of the caller's pointer variable.
    "referent_is_a_pointer": TYPES + """
fn mk(c:& *C) -> P
    var p: P
    p.ch = c
    return p

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var q: *C = @c
    var p: P = mk(@&q)
    p.ch.x = p.ch.x + 2
    return c.x
""",
    # The same with an integer pointee, a pointer being as wide as an `i64`.
    "referent_is_a_pointer_of_the_same_width": """\
struct Q
    p: *i64

fn mk(n:& *i64) -> Q
    var q: Q
    q.p = n
    return q

pub fn main() -> i32
    var n: i64 = 1
    var m: *i64 = @n
    var q: Q = mk(@&m)
    *q.p = 3
    return n as i32
""",
    # Locals are reused from one function to the next: `@m` is `m`'s own address,
    # not what `m` holds, whatever the last function's `n` was.
    "plain_param_after_a_borrow": """\
struct Q
    p: *i32

fn peek(n:& i32) -> i32
    return n

fn mk(m: i32) -> i32
    var q: Q
    q.p = @m
    return *q.p

pub fn main() -> i32
    var n: i32 = 3
    return mk(peek(@&n))
""",
    # A by-value field copies: the write lands in the copy.
    "by_value_field_copies": TYPES + """
struct V
    c: C

fn mk(c:& C) -> V
    var v: V
    v.c = c
    return v

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V = mk(@&c)
    v.c.x = 9
    return c.x
""",
    "by_value_literal_copies": TYPES + """
struct V
    c: C

fn mk(c:& C) -> V
    return V { c: c }

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V = mk(@&c)
    v.c.x = 9
    return c.x
""",
    # An integer field reads the referent, by either route.
    "integer_field_copies": """\
struct I
    n: i32

fn mk(n:& i32) -> I
    var v: I
    v.n = n
    return v

pub fn main() -> i32
    var n: i32 = 3
    var v: I = mk(@&n)
    v.n = 9
    return n
""",
    "integer_literal_copies": """\
struct I
    n: i32

fn mk(n:& i32) -> I
    return I { n: n }

pub fn main() -> i32
    var n: i32 = 3
    var v: I = mk(@&n)
    v.n = 9
    return n
""",
    "generic_integer_field_copies": """\
struct GV<T>
    v: T

fn mk(n:& i32) -> GV<i32>
    return GV<i32> { v: n }

pub fn main() -> i32
    var n: i32 = 3
    var g: GV<i32> = mk(@&n)
    g.v = 9
    return n
""",
}

# AGAST #2250: every by-value slot takes a copy of the referent. Each program
# changes the original afterwards, or the copy, and then reads the other, so a
# stored pointer can't pass.
LARGE = """\
struct B
    x: i32
    pad: [64]i64

"""

ENUM = """\
enum E
    Nope
    Full(i32)

"""

ARRAY_H = """\
struct H
    a: [2]i32

"""

DROP_COUNT = """\
var DROPS: i32 = 0

struct Counted
    h: i32

impl Drop for Counted
    fn drop(self: @&Counted)
        DROPS = DROPS + 1

"""

BY_VALUE = TYPES + """
struct V
    c: C

struct O
    v: V

struct VA
    a: [2]C

struct GV<T>
    v: T

enum E
    A
    B(i32)

struct HE
    e: E
"""

MAIN_V = """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V = mk(@&c)
    c.x = 9
    return v.c.x
"""

MAIN_O = """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var o: O = mk(@&c)
    c.x = 9
    return o.v.c.x
"""

MAIN_FILL_V = """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V
    fill(@v, @&c)
    c.x = 9
    return v.c.x
"""

MAIN_E = """
pub fn main() -> i32
    var e: E = E.B(3)
    var h: HE = mk(@&e)
    e = E.A
    match h.e
        E.B(n) => return n
        E.A => return 0
"""

CONTROLS.update({
    "by_value_field_reads_the_copy": BY_VALUE + """
fn mk(c:& C) -> V
    var v: V
    v.c = c
    return v
""" + MAIN_V,
    "by_value_literal_reads_the_copy": BY_VALUE + """
fn mk(c:& C) -> V
    return V { c: c }
""" + MAIN_V,
    "by_value_nested": BY_VALUE + """
fn mk(c:& C) -> O
    var o: O
    o.v.c = c
    return o
""" + MAIN_O,
    "by_value_nested_literal": BY_VALUE + """
fn mk(c:& C) -> O
    var o: O
    o.v = V { c: c }
    return o
""" + MAIN_O,
    "by_value_through_pointer": BY_VALUE + """
fn fill(v: *V, c:& C)
    v.c = c
""" + MAIN_FILL_V,
    "by_value_through_borrow": BY_VALUE + """
fn fill(v:& V, c:& C)
    v.c = c
""" + MAIN_FILL_V.replace("fill(@v", "fill(@&v"),
    "by_value_global_field": BY_VALUE + """
var GV0: V

fn fill(c:& C)
    GV0.c = c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    fill(@&c)
    c.x = 9
    return GV0.c.x
""",
    "by_value_generic_struct": BY_VALUE + """
fn mk(c:& C) -> GV<C>
    return GV<C> { v: c }

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var g: GV<C> = mk(@&c)
    c.x = 9
    return g.v.x
""",
    "by_value_generic_struct_assign": BY_VALUE + """
fn mk(c:& C) -> GV<C>
    var g: GV<C>
    g.v = c
    return g

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var g: GV<C> = mk(@&c)
    c.x = 9
    return g.v.x
""",
    "by_value_generic_fn": BY_VALUE + """
fn mk<T>(c:& T) -> GV<T>
    return GV<T> { v: c }

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var g: GV<C> = mk<C>(@&c)
    c.x = 9
    return g.v.x
""",
    "by_value_enum_field": BY_VALUE + """
fn mk(e:& E) -> HE
    var h: HE
    h.e = e
    return h
""" + MAIN_E,
    "by_value_enum_literal": BY_VALUE + """
fn mk(e:& E) -> HE
    return HE { e: e }
""" + MAIN_E,
    "by_value_self": BY_VALUE + """
impl C
    fn wrap(self:& C) -> V
        return V { c: self }

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V = c.wrap()
    c.x = 9
    return v.c.x
""",
    "by_value_method_param": BY_VALUE + """
impl O
    fn wrap(self: @O, c:& C) -> V
        return V { c: c }

pub fn main() -> i32
    var o: O
    var c: C = C { x: 3, y: 0 }
    var v: V = o.wrap(@&c)
    c.x = 9
    return v.c.x
""",
    "by_value_strview": """\
import ritzlib.strview

struct HS
    s: StrView

fn mk(v:& StrView) -> HS
    return HS { s: v }

pub fn main() -> i32
    var v: StrView = "abc"
    var h: HS = mk(@&v)
    return h.s.len as i32
""",
    "by_value_deref_store": BY_VALUE + """
fn fill(p: *C, c:& C)
    *p = c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = C { x: 0, y: 0 }
    fill(@d, @&c)
    c.x = 9
    return d.x
""",
    "by_value_local_assign": BY_VALUE + """
fn f(c:& C) -> i32
    var d: C = C { x: 0, y: 0 }
    d = c
    c.x = 9
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_field_array_element": BY_VALUE + """
fn fill(a: *VA, c:& C)
    a.a[1] = c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var a: VA
    fill(@a, @&c)
    c.x = 9
    return a.a[1].x
""",
    "by_value_nested_array_element": BY_VALUE + """
struct OV
    va: VA

fn fill(o: *OV, c:& C)
    o.va.a[1] = c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var o: OV
    fill(@o, @&c)
    c.x = 9
    return o.va.a[1].x
""",
    "by_value_local_field_array_element": BY_VALUE + """
fn run(c:& C) -> i32
    var a: VA
    a.a[1] = c
    c.x = 9
    return a.a[1].x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return run(@&c)
""",
    "by_value_local_array_element": BY_VALUE + """
fn run(c:& C) -> i32
    var a: [2]C
    a[1] = c
    c.x = 9
    return a[1].x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return run(@&c)
""",
    "by_value_pointer_element": BY_VALUE + """
fn fill(p: *C, c:& C)
    p[1] = c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var a: [2]C
    fill(@a[0], @&c)
    c.x = 9
    return a[1].x
""",
    "by_value_global_array_element": BY_VALUE + """
var GA: [2]C

fn fill(c:& C)
    GA[1] = c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    fill(@&c)
    c.x = 9
    return GA[1].x
""",
})

# An integer isn't a pointer, of any pointee (#2281). `^` is where the reference
# goes: bare, each is a value in a reference field. Written out, each is R1's
# "pointees must be the same type" (#2325).
MISMATCHED = """\
struct S
    x: i32

struct G<T>
    p: *T

struct W
    p: *i64

struct F
    p: *f32

struct B
    p: *bool

struct T
    p: *S
"""

ENTRY = """
pub fn main() -> i32
    return 0
"""

MISMATCHES = {
    "width": MISMATCHED + """
fn mk(n:& i32) -> W
    var w: W
    w.p = ^n
    return w
""" + ENTRY,
    # A `**i64` holds pointers, which are as wide as `n`.
    "pointer_of_the_same_width": MISMATCHED + """
struct PP
    p: **i64

fn mk(n:& i64) -> PP
    return PP { p: ^n }
""" + ENTRY,
    "float_of_the_same_width": MISMATCHED + """
fn mk(n:& i32) -> F
    return F { p: ^n }
""" + ENTRY,
    "bool_of_the_same_width": MISMATCHED + """
fn mk(n:& u8) -> B
    return B { p: ^n }
""" + ENTRY,
    "struct_of_the_same_width": MISMATCHED + """
fn mk(n:& i32) -> T
    return T { p: ^n }
""" + ENTRY,
    "generic_float": MISMATCHED + """
fn mk(n:& i32) -> G<f32>
    return G<f32> { p: ^n }
""" + ENTRY,
    "generic_bool": MISMATCHED + """
fn mk(n:& u8) -> G<bool>
    return G<bool> { p: ^n }
""" + ENTRY,
    # Exactly the same type, not the same width (#2368).
    "sign_differs": MISMATCHED + """
struct Q
    p: *i32

fn mk(n:& u32) -> Q
    return Q { p: ^n }
""" + ENTRY,
    "sign_differs_store": MISMATCHED + """
struct Q
    p: *i32

fn mk(n:& u32) -> Q
    var q: Q
    q.p = ^n
    return q
""" + ENTRY,
}
# test_value_into_ref.py's lent_field_other_pointee is this, bare.
MISMATCHES_BARE = sorted(set(MISMATCHES) - {"width", "sign_differs", "sign_differs_store"})
POINTER_TO_POINTER_GAP = "AGAST #2370: ritz1 takes a bare `n:& i64` into a `**i64`; ritz0 refuses it, and `*i64` is refused"
WRITTEN_POINTER_TO_POINTER_GAP = "AGAST #2528: ritz1 judges nothing into a `**T` field, so `@n` of an `i64` into a `**i64` compiles"

# AGAST #2250: known gaps next to it, each pinned by its own ticket below.
CONTROLS.update({
    "by_value_float_field": """\
struct F
    f: f64

fn mk(n:& f64) -> F
    var v: F
    v.f = n
    return v

pub fn main() -> i32
    var n: f64 = 3.0
    var v: F = mk(@&n)
    return v.f as i32
""",
    "by_value_float_literal": """\
struct F
    f: f64

fn mk(n:& f64) -> F
    return F { f: n }

pub fn main() -> i32
    var n: f64 = 3.0
    var v: F = mk(@&n)
    return v.f as i32
""",
    "by_value_bool_field": """\
struct B
    b: bool

fn mk(n:& bool) -> B
    var v: B
    v.b = n
    return v

pub fn main() -> i32
    var n: bool = true
    var v: B = mk(@&n)
    if v.b
        return 3
    return 0
""",
    "by_value_bool_literal": """\
struct B
    b: bool

fn mk(n:& bool) -> B
    return B { b: n }

pub fn main() -> i32
    var n: bool = true
    var v: B = mk(@&n)
    if v.b
        return 3
    return 0
""",
    "by_value_from_at_amp_param": BY_VALUE + """
fn mk(c: @&C) -> V
    var v: V
    v.c = c
    return v

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V = mk(@&c)
    return v.c.x
""",
    "by_value_from_pointer_param": BY_VALUE + """
fn mk(c: *C) -> V
    return V { c: c }

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: V = mk(@c)
    return v.c.x
""",
    "by_value_let": BY_VALUE + """
fn f(c:& C) -> i32
    let d: C = c
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_argument": BY_VALUE + """
fn g(c: C) -> i32
    return c.x

fn f(c:& C) -> i32
    return g(c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_return": BY_VALUE + """
fn f(c:& C) -> C
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c)
    return d.x
""",
    "by_value_array_referent": """\
struct H
    a: [2]i32

fn mk(a:& [2]i32) -> H
    var h: H
    h.a = a
    return h

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var h: H = mk(@&a)
    return h.a[1]
""",
    # AGAST #2279: the reads that aren't stores.  Every one is a by-value slot.
    "by_value_var": BY_VALUE + """
fn f(c:& C) -> i32
    var d: C = c
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_untyped_let": BY_VALUE + """
fn f(c:& C) -> i32
    let d = c
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    # An unannotated binding is a copy as well: it used to alias the referent,
    # so the write below reached the caller.
    "by_value_untyped_var_copies": BY_VALUE + """
fn f(c:& C) -> i32
    var d = c
    d.x = 9
    return c.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_var_copies": BY_VALUE + """
fn f(c:& C) -> i32
    var d: C = c
    c.x = 9
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_argument_copies": BY_VALUE + """
fn g(c: C) -> i32
    var d: C = c
    d.x = 9
    return d.x

fn f(c:& C) -> i32
    g(c)
    return c.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_second_argument": BY_VALUE + """
fn g(a: i32, c: C) -> i32
    return a + c.x

fn f(c:& C) -> i32
    return g(0, c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_method_argument": BY_VALUE + """
struct M
    k: i32

impl M
    fn take(self: @M, c: C) -> i32
        return c.x

fn f(m: @M, c:& C) -> i32
    return m.take(c)

pub fn main() -> i32
    var m: M = M { k: 0 }
    var c: C = C { x: 3, y: 0 }
    return f(@m, @&c)
""",
    "by_value_static_method_argument": BY_VALUE + """
impl C
    fn take(c: C) -> i32
        return c.x

fn f(c:& C) -> i32
    return C.take(c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_generic_argument": BY_VALUE + """
fn g<T>(c: T) -> T
    return c

fn f(c:& C) -> C
    return g<C>(c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c)
    return d.x
""",
    "by_value_tail": BY_VALUE + """
fn f(c:& C) -> C
    c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c)
    return d.x
""",
    "by_value_return_in_branch": BY_VALUE + """
fn f(c:& C, k: i32) -> C
    if k == 0
        return c
    return C { x: 0, y: 0 }

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c, 0)
    return d.x
""",
    "by_value_return_generic": BY_VALUE + """
fn id<T>(c:& T) -> T
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = id<C>(@&c)
    return d.x
""",
    "by_value_return_from_method": BY_VALUE + """
struct M
    k: i32

impl M
    fn pick(self: @M, c:& C) -> C
        return c

pub fn main() -> i32
    var m: M = M { k: 0 }
    var c: C = C { x: 3, y: 0 }
    var d: C = m.pick(@&c)
    return d.x
""",
    "by_value_tail_from_method": BY_VALUE + """
struct M
    k: i32

impl M
    fn pick(self: @M, c:& C) -> C
        c

pub fn main() -> i32
    var m: M = M { k: 0 }
    var c: C = C { x: 3, y: 0 }
    var d: C = m.pick(@&c)
    return d.x
""",
    # Too big for a register: these take the sret and byval paths.
    "by_value_large_return": LARGE + """
fn f(b:& B) -> B
    return b

pub fn main() -> i32
    var b: B
    b.x = 3
    var d: B = f(@&b)
    return d.x
""",
    "by_value_large_tail": LARGE + """
fn f(b:& B) -> B
    b

pub fn main() -> i32
    var b: B
    b.x = 3
    var d: B = f(@&b)
    return d.x
""",
    "by_value_large_let": LARGE + """
fn f(b:& B) -> i32
    let d: B = b
    return d.x

pub fn main() -> i32
    var b: B
    b.x = 3
    return f(@&b)
""",
    "by_value_large_argument": LARGE + """
fn g(b: B) -> i32
    return b.x

fn f(b:& B) -> i32
    return g(b)

pub fn main() -> i32
    var b: B
    b.x = 3
    return f(@&b)
""",
    "by_value_enum_return": ENUM + """
fn f(e:& E) -> E
    return e

pub fn main() -> i32
    var e: E = E.Full(3)
    var d: E = f(@&e)
    return match d
        Full(n) => n
        Nope => 0
""",
    "by_value_enum_let": ENUM + """
fn f(e:& E) -> i32
    let d: E = e
    return match d
        Full(n) => n
        Nope => 0

pub fn main() -> i32
    var e: E = E.Full(3)
    return f(@&e)
""",
    "by_value_enum_argument": ENUM + """
fn g(e: E) -> i32
    return match e
        Full(n) => n
        Nope => 0

fn f(e:& E) -> i32
    return g(e)

pub fn main() -> i32
    var e: E = E.Full(3)
    return f(@&e)
""",
    "by_value_array_literal_element": BY_VALUE + """
fn f(c:& C) -> i32
    let a: [2]C = [c, c]
    return a[1].x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    # An integer `:&` already reads as its value: nothing to copy.
    "integer_untyped_let": """\
fn f(n:& i32) -> i32
    let m = n
    return m

pub fn main() -> i32
    var n: i32 = 3
    return f(@&n)
""",
    "integer_untyped_var_copies": """\
fn f(n:& i32) -> i32
    var m = n
    m = 9
    return n

pub fn main() -> i32
    var n: i32 = 3
    return f(@&n)
""",
    # The referent is read before the fn's own locals drop, and they still do.
    "return_drops_locals": BY_VALUE + DROP_COUNT + """
fn f(c:& C) -> C
    var r: Counted = Counted { h: 1 }
    return c

pub fn main() -> i32
    var c: C = C { x: 2, y: 0 }
    var d: C = f(@&c)
    return d.x + DROPS
""",
    "tail_drops_locals": BY_VALUE + DROP_COUNT + """
fn f(c:& C) -> C
    var r: Counted = Counted { h: 1 }
    c

pub fn main() -> i32
    var c: C = C { x: 2, y: 0 }
    var d: C = f(@&c)
    return d.x + DROPS
""",
    "large_return_drops_locals": LARGE + DROP_COUNT + """
fn f(b:& B) -> B
    var r: Counted = Counted { h: 1 }
    return b

pub fn main() -> i32
    var b: B
    b.x = 2
    var d: B = f(@&b)
    return d.x + DROPS
""",
    # A written reference is the caller's address: writes through it reach them.
    "let_reference_keeps_the_borrow": BY_VALUE + """
fn f(c:& C) -> i32
    let p: @C = @c
    return p.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "reborrow_keeps_the_borrow": BY_VALUE + """
fn g(c:& C)
    c.x = 3

fn f(c:& C)
    g(c)

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    f(@&c)
    return c.x
""",
    "reference_argument_keeps_the_borrow": BY_VALUE + """
fn g(c: @&C)
    c.x = 3

fn f(c:& C)
    g(@&c)

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    f(@&c)
    return c.x
""",
    "pointer_argument_keeps_the_borrow": BY_VALUE + """
fn g(c: *C)
    c.x = 3

fn f(c:& C)
    g(@c)

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    f(@&c)
    return c.x
""",
    # A whole-array referent copies, at every element kind and destination.
    "array_referent_literal": ARRAY_H + """
fn mk(a:& [2]i32) -> H
    return H { a: a }

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var h: H = mk(@&a)
    return h.a[1]
""",
    "array_referent_through_pointer": ARRAY_H + """
fn fill(h: *H, a:& [2]i32)
    h.a = a

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var h: H
    fill(@h, @&a)
    return h.a[1]
""",
    "array_referent_nested_field": ARRAY_H + """
struct O
    h: H

fn fill(o: *O, a:& [2]i32)
    o.h.a = a

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var o: O
    fill(@o, @&a)
    return o.h.a[1]
""",
    "array_referent_method_param": ARRAY_H + """
impl H
    fn set(self: @&H, a:& [2]i32)
        self.a = a

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var h: H
    h.set(@&a)
    return h.a[1]
""",
    "array_referent_let": """\
fn f(a:& [2]i32) -> i32
    let b: [2]i32 = a
    return b[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
    "array_referent_untyped_let": """\
fn f(a:& [2]i32) -> i32
    let b = a
    return b[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
    "array_referent_assign": """\
fn f(a:& [2]i32) -> i32
    var b: [2]i32 = [0, 0]
    b = a
    return b[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
    # The write lands in the copy: reading `a` again still gives 3.
    "array_referent_copies": """\
fn f(a:& [2]i32) -> i32
    var b: [2]i32 = a
    b[1] = 9
    let c: [2]i32 = a
    return c[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
    "array_referent_untyped_copies": """\
fn f(a:& [2]i32) -> i32
    var b = a
    b[1] = 9
    let c: [2]i32 = a
    return c[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
    "array_referent_of_structs": BY_VALUE + """
fn mk(a:& [2]C) -> VA
    var h: VA
    h.a = a
    return h

pub fn main() -> i32
    var a: [2]C
    a[1].x = 3
    var h: VA = mk(@&a)
    return h.a[1].x
""",
    "array_referent_of_bytes": """\
struct H
    a: [2]u8

fn fill(h: *H, a:& [2]u8)
    h.a = a

pub fn main() -> i32
    var a: [2]u8 = [1, 3]
    var h: H
    fill(@h, @&a)
    return h.a[1] as i32
""",
    "array_referent_large": """\
struct H
    a: [64]i64

fn fill(h: *H, a:& [64]i64)
    h.a = a

pub fn main() -> i32
    var a: [64]i64
    a[63] = 3
    var h: H
    fill(@h, @&a)
    return h.a[63] as i32
""",
    "array_referent_generic": ARRAY_H + """
fn fill<T>(h: *H, a:& [2]T)
    h.a = a

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var h: H
    fill<i32>(@h, @&a)
    return h.a[1]
""",
    "array_referent_generic_structs": BY_VALUE + """
fn fill<T>(h: *VA, a:& [2]T)
    h.a = a

pub fn main() -> i32
    var a: [2]C
    a[1].x = 3
    var h: VA
    fill<C>(@h, @&a)
    return h.a[1].x
""",
    "array_reborrow_keeps_the_borrow": """\
fn g(a:& [2]i32) -> i32
    return 3

fn f(a:& [2]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
})

# Reads ritz1 doesn't do yet, each held to ritz0's answer by a strict xfail.
CONTROLS.update({
    "address_of_borrow_let": BY_VALUE + """
fn f(c:& C) -> i32
    let p: *C = @c
    return p.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "address_of_borrow_argument": BY_VALUE + """
fn h(p: *C) -> i32
    return p.x

fn f(c:& C) -> i32
    return h(@c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "mut_address_of_borrow": BY_VALUE + """
fn f(c:& C) -> i32
    let p: @&C = @&c
    return p.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_if_arm": BY_VALUE + """
fn f(c:& C, k: i32) -> i32
    let d: C = if k == 0
        c
    else
        c
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c, 0)
""",
    "by_value_if_tail": BY_VALUE + """
fn f(c:& C, k: i32) -> C
    if k == 0
        c
    else
        c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c, 0)
    return d.x
""",
    "by_value_match_arm": BY_VALUE + """
fn f(c:& C, k: i32) -> C
    return match k
        0 => c
        _ => c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c, 0)
    return d.x
""",
    "by_value_match_tail": BY_VALUE + """
fn f(c:& C, k: i32) -> C
    match k
        0 => c
        _ => c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c, 0)
    return d.x
""",
    "by_value_variant_payload": BY_VALUE + """
enum W
    Nil
    Held(C)

fn f(c:& C) -> i32
    let w: W = W.Held(c)
    return match w
        Held(d) => d.x
        Nil => 0

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_bare_variant_payload": BY_VALUE + """
enum W
    Nil
    Held(C)

fn f(c:& C) -> i32
    let w: W = Held(c)
    return match w
        Held(d) => d.x
        Nil => 0

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_some_payload": "import ritzlib.option\n\n" + BY_VALUE + """
fn f(c:& C) -> Option<C>
    return Some(c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var o: Option<C> = f(@&c)
    return match o
        Some(d) => d.x
        None => 0
""",
    "by_value_array_fill": BY_VALUE + """
fn f(c:& C) -> i32
    let a: [2]C = [c; 2]
    return a[1].x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "by_value_cast": BY_VALUE + """
fn f(c:& C) -> i32
    let d: C = c as C
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    # AGAST #2288: the payload's declared type decides, for each variant.
    "by_value_ok_payload": "import ritzlib.result\n\n" + BY_VALUE + """
fn f(c:& C) -> Result<C, i32>
    return Ok(c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var r: Result<C, i32> = f(@&c)
    return match r
        Ok(d) => d.x
        Err(e) => e
""",
    "by_value_err_payload": "import ritzlib.result\n\n" + BY_VALUE + """
fn f(c:& C) -> Result<i32, C>
    return Err(c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var r: Result<i32, C> = f(@&c)
    return match r
        Ok(n) => n
        Err(d) => d.x
""",
    # A `*C` payload keeps the pointer: the write through it reaches `c`.
    "pointer_payload_keeps_pointer": BY_VALUE + """
enum W
    Nil
    Held(*C)

fn f(c:& C) -> W
    return W.Held(@c)

fn set(p: *C)
    p.x = 3

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let w: W = f(@&c)
    match w
        Held(p) => set(p)
        Nil => pass
    return c.x
""",
    # The arm is a copy: a write to it leaves the caller's `c` alone.
    "by_value_if_arm_copies": BY_VALUE + """
fn f(c:& C, k: i32) -> i32
    var d: C = if k == 0
        c
    else
        C { x: 1, y: 0 }
    d.x = 9
    return c.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c, 0)
""",
    # A literal arm types the phi first.
    "by_value_match_arm_after_literal": BY_VALUE + """
fn f(c:& C, k: i32) -> C
    return match k
        0 => C { x: 1, y: 0 }
        _ => c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c, 1)
    return d.x
""",
    "match_borrow_scrutinee": ENUM + """
fn f(e:& E) -> i32
    match e
        Full(n) => return n
        Nope => return 0

pub fn main() -> i32
    var e: E = E.Full(3)
    return f(@&e)
""",
    "match_borrow_scrutinee_value": ENUM + """
fn f(e:& E) -> i32
    return match e
        Full(n) => n
        Nope => 0

pub fn main() -> i32
    var e: E = E.Full(3)
    return f(@&e)
""",
    "array_borrow_index": """\
fn f(a:& [2]i32) -> i32
    return a[1]

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
    "array_borrow_index_store": """\
fn f(a:& [2]i32)
    a[1] = 3

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
""",
    "array_borrow_reference_argument": """\
fn g(a: @[2]i32) -> i32
    return 3

fn f(a:& [2]i32) -> i32
    return g(@a)

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
    "array_referent_argument": """\
fn g(a: [2]i32) -> i32
    return a[1]

fn f(a:& [2]i32) -> i32
    return g(a)

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@&a)
""",
    "array_referent_return": """\
fn f(a:& [2]i32) -> [2]i32
    return a

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var b: [2]i32 = f(@&a)
    return b[1]
""",
    "array_referent_deref_store": """\
fn f(p: *[2]i32, a:& [2]i32)
    *p = a

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var b: [2]i32 = [0, 0]
    f(@b, @&a)
    return b[1]
""",
    "array_referent_global": """\
var G: [2]i32

fn f(a:& [2]i32)
    G = a

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    f(@&a)
    return G[1]
""",
    # No borrow: [4]i32, because a first 8 bytes that hold the answer hide this.
    "plain_array_argument": """\
fn g(a: [4]i32) -> i32
    return a[3]

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    return g(a)
""",
    "plain_array_deref_store": """\
fn s(p: *[4]i32)
    var a: [4]i32 = [0, 0, 0, 3]
    *p = a

pub fn main() -> i32
    var b: [4]i32 = [0, 0, 0, 0]
    s(@b)
    return b[3]
""",
    "plain_array_global_store": """\
var G: [4]i32

pub fn main() -> i32
    var a: [4]i32 = [0, 0, 0, 3]
    G = a
    return G[3]
""",
    "generic_struct_array_field": """\
struct G<T>
    a: [2]T

fn fill(g: *G<i32>, a:& [2]i32)
    g.a = a

pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    var g: G<i32>
    fill(@g, @&a)
    return g.a[1]
""",
})

# ritz0 reads these by value.  ritz1 loaded the local's slot as the struct and
# returned garbage, silently.  Until they compile they must not compile wrong.
USED_TO_RETURN_GARBAGE = {
    "return_from_reference": BY_VALUE + """
fn f(c: @C) -> C
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@c)
    return d.x
""",
    "return_from_mut_reference": BY_VALUE + """
fn f(c: @&C) -> C
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@&c)
    return d.x
""",
    "return_from_pointer": BY_VALUE + """
fn f(c: *C) -> C
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@c)
    return d.x
""",
    "tail_from_reference": BY_VALUE + """
fn f(c: @C) -> C
    c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@c)
    return d.x
""",
    "tail_from_pointer": BY_VALUE + """
fn f(c: *C) -> C
    c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = f(@c)
    return d.x
""",
    "return_from_borrowed_pointer": BY_VALUE + """
fn f(p:& *C) -> C
    return p

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var q: *C = @c
    var d: C = f(@&q)
    return d.x
""",
    "return_self_by_value": BY_VALUE + """
impl C
    fn me(self: C) -> C
        return self

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = c.me()
    return d.x
""",
    "return_bare_self": BY_VALUE + """
impl C
    fn me(self) -> C
        return self

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: C = c.me()
    return d.x
""",
}
CONTROLS.update(USED_TO_RETURN_GARBAGE)
# A by-value `self` is a by-value param (#2393): it reads as `s: C` does.
for _name in ("return_self_by_value", "return_bare_self"):
    USED_TO_RETURN_GARBAGE.pop(_name)

RES = """\
struct Res
    h: i32

impl Drop for Res
    fn drop(self: @&Res)
        self.h = 0

struct H
    r:& Res

struct V
    r: Res
"""

# A reference to a Drop type moves nothing and drops nothing.
DROP_STORES = {
    "assign": RES + """
fn mk(t:& Res) -> H
    var h: H
    h.r = @&t
    return h

pub fn main() -> i32
    var r: Res = Res { h: 1 }
    var h: H = mk(@&r)
    h.r.h = 3
    return r.h
""",
    "literal": RES + """
fn mk(t:& Res) -> H
    return H { r: @&t }

pub fn main() -> i32
    var r: Res = Res { h: 1 }
    var h: H = mk(@&r)
    h.r.h = 3
    return r.h
""",
}

DROP_STORES.update({
    # AGAST #2279: only a by-value slot moves.
    "let_reference": RES + """
fn f(t:& Res) -> i32
    let p: @Res = @t
    return p.h

pub fn main() -> i32
    var r: Res = Res { h: 3 }
    return f(@&r)
""",
    "let_pointer": RES + """
fn f(t:& Res) -> i32
    let p: *Res = @t
    return p.h

pub fn main() -> i32
    var r: Res = Res { h: 3 }
    return f(@&r)
""",
    "reborrow": RES + """
fn g(t:& Res) -> i32
    return t.h

fn f(t:& Res) -> i32
    return g(t)

pub fn main() -> i32
    var r: Res = Res { h: 3 }
    return f(@&r)
""",
    "reference_argument": RES + """
fn g(t: @Res) -> i32
    return t.h

fn f(t:& Res) -> i32
    return g(@t)

pub fn main() -> i32
    var r: Res = Res { h: 3 }
    return f(@&r)
""",
})

# A by-value field of the same type really would take it from the caller.
MOVE_OUT = {
    "assign": RES + """
fn mk(t:& Res) -> V
    var v: V
    v.r = t
    return v

pub fn main() -> i32
    return 0
""",
    "literal": RES + """
fn mk(t:& Res) -> V
    return V { r: t }

pub fn main() -> i32
    return 0
""",
    # AGAST #2250: every slot ritz1 now loads a referent for.
    "nested": RES + """
struct O
    v: V

fn mk(t:& Res) -> O
    var o: O
    o.v.r = t
    return o

pub fn main() -> i32
    return 0
""",
    "through_pointer": RES + """
fn fill(v: *V, t:& Res)
    v.r = t

pub fn main() -> i32
    return 0
""",
    "deref_store": RES + """
fn fill(p: *Res, t:& Res)
    *p = t

pub fn main() -> i32
    return 0
""",
    "local_assign": RES + """
fn f(t:& Res)
    var r: Res = Res { h: 1 }
    r = t

pub fn main() -> i32
    return 0
""",
    "field_array_element": RES + """
struct AR
    a: [2]Res

fn fill(a: *AR, t:& Res)
    a.a[1] = t

pub fn main() -> i32
    return 0
""",
    "local_array_element": RES + """
fn f(t:& Res)
    var a: [2]Res
    a[1] = t

pub fn main() -> i32
    return 0
""",
    "pointer_element": RES + """
fn fill(p: *Res, t:& Res)
    p[1] = t

pub fn main() -> i32
    return 0
""",
    "global_array_element": RES + """
var GA: [2]Res

fn fill(t:& Res)
    GA[1] = t

pub fn main() -> i32
    return 0
""",
    # Move-only because of what it holds, not because of an impl of its own.
    "drop_field_inside": RES + """
struct W
    r: Res

struct HW
    w: W

fn mk(w:& W) -> HW
    return HW { w: w }

pub fn main() -> i32
    return 0
""",
    # AGAST #2279: the reads that aren't stores, as ritz0 rejects them.
    "return": RES + """
fn f(t:& Res) -> Res
    return t

pub fn main() -> i32
    return 0
""",
    "tail": RES + """
fn f(t:& Res) -> Res
    t

pub fn main() -> i32
    return 0
""",
    "let": RES + """
fn f(t:& Res)
    let d: Res = t

pub fn main() -> i32
    return 0
""",
    "var": RES + """
fn f(t:& Res)
    var d: Res = t

pub fn main() -> i32
    return 0
""",
    "untyped_let": RES + """
fn f(t:& Res)
    let d = t

pub fn main() -> i32
    return 0
""",
    "untyped_var": RES + """
fn f(t:& Res)
    var d = t

pub fn main() -> i32
    return 0
""",
    "argument": RES + """
fn g(t: Res) -> i32
    return t.h

fn f(t:& Res) -> i32
    return g(t)

pub fn main() -> i32
    return 0
""",
    "method_argument": RES + """
struct M
    k: i32

impl M
    fn take(self: @M, t: Res) -> i32
        return t.h

fn f(m: @M, t:& Res) -> i32
    return m.take(t)

pub fn main() -> i32
    return 0
""",
    "method_tail": RES + """
struct M
    k: i32

impl M
    fn pick(self: @M, t:& Res) -> Res
        t

pub fn main() -> i32
    return 0
""",
    "return_drop_field_inside": RES + """
struct W
    r: Res

fn f(w:& W) -> W
    return w

pub fn main() -> i32
    return 0
""",
    "array_literal_element": RES + """
fn f(t:& Res)
    let a: [1]Res = [t]

pub fn main() -> i32
    return 0
""",
    "array_referent_field": RES + """
struct HR
    a: [2]Res

fn f(h: *HR, a:& [2]Res)
    h.a = a

pub fn main() -> i32
    return 0
""",
    "array_referent_let": RES + """
fn f(a:& [2]Res)
    let b: [2]Res = a

pub fn main() -> i32
    return 0
""",
    "array_referent_untyped": RES + """
fn f(a:& [2]Res)
    var b = a

pub fn main() -> i32
    return 0
""",
    "if_arm": RES + """
fn f(t:& Res, k: i32) -> Res
    return if k == 0
        t
    else
        t

pub fn main() -> i32
    return 0
""",
    # AGAST #2288: the rest of the by-value reads #2279 left.
    "if_tail": RES + """
fn f(t:& Res, k: i32) -> Res
    if k == 0
        t
    else
        t

pub fn main() -> i32
    return 0
""",
    "match_arm": RES + """
fn f(t:& Res, k: i32) -> Res
    match k
        0 => t
        _ => t

pub fn main() -> i32
    return 0
""",
    "variant_payload": RES + """
enum W
    Nil
    Held(Res)

fn f(t:& Res) -> W
    return W.Held(t)

pub fn main() -> i32
    return 0
""",
    "some_payload": "import ritzlib.option\n\n" + RES + """
fn f(t:& Res) -> Option<Res>
    return Some(t)

pub fn main() -> i32
    return 0
""",
    "array_fill": RES + """
fn f(t:& Res)
    let a: [2]Res = [t; 2]

pub fn main() -> i32
    return 0
""",
    "cast": RES + """
fn f(t:& Res)
    let d: Res = t as Res

pub fn main() -> i32
    return 0
""",
    "array_return": RES + """
fn f(a:& [2]Res) -> [2]Res
    return a

pub fn main() -> i32
    return 0
""",
    "array_argument": RES + """
fn g(a: [2]Res) -> i32
    return 0

fn f(a:& [2]Res) -> i32
    return g(a)

pub fn main() -> i32
    return 0
""",
}


# AGAST #2288: ritz0 misses these two moves out of a borrow (AGAST #2948),
# so only ritz1 is held to the rule: `[t; 2]` and `t as Res` would hand the
# caller's move-only `Res` to a second owner.
RITZ0_MISSED_MOVE_OUT = {name: MOVE_OUT.pop(name) for name in ("array_fill", "cast")}


# A reference in a by-value slot: ritz0 read through it and ritz1 failed at clang
# or returned garbage. There's no implicit deref (§13.2, AGAST #2336).
NO_IMPLICIT_DEREF = {name: CONTROLS.pop(name) for name in (
    "by_value_from_at_amp_param", "by_value_from_pointer_param",
    "return_from_reference", "return_from_mut_reference", "return_from_pointer",
    "tail_from_reference", "tail_from_pointer", "return_from_borrowed_pointer",
)}
for _name in NO_IMPLICIT_DEREF:
    USED_TO_RETURN_GARBAGE.pop(_name, None)


# Keyed by program, across STORES, CONTROLS and MOVE_OUT.
RITZ1_GAPS = {
    "by_value_pointer_element": "AGAST #2277: `p[i] = v` with a struct value isn't lowered",
    "pointer_element": "AGAST #2277: `p[i] = v` with a struct value isn't lowered",
    "by_value_self": "AGAST #2278: ritz1 doesn't know a typed `self:& T` is a borrow",
    "by_value_float_field": "AGAST #1668: a `:&` float isn't auto-dereferenced",
    "by_value_float_literal": "AGAST #1668: a `:&` float isn't auto-dereferenced",
    "by_value_bool_field": "AGAST #1668: a `:&` bool isn't auto-dereferenced",
    "by_value_bool_literal": "AGAST #1668: a `:&` bool isn't auto-dereferenced",
    "match_borrow_scrutinee": "AGAST #2289: `match` on a `:&` enum spills the pointer",
    "match_borrow_scrutinee_value": "AGAST #2289: `match` on a `:&` enum spills the pointer",
    "array_referent_return": "AGAST #2302: ritz1 has no array return yet",
    "array_return": "AGAST #2302: ritz1 has no array return yet",
    "generic_struct_array_field": "AGAST #2292: a generic struct's `[N]T` field isn't substituted",
    "array_referent_literal": "AGAST #1748: a struct literal's array field takes only array literals",
}

# `@n` into a `*i32` that isn't a field: the caller's address, so the write
# through it reaches them.
POINTER_SLOTS = {
    "let": """\
fn f(n:& i32)
    let p: *i32 = @n
    *p = 3

pub fn main() -> i32
    var n: i32 = 1
    f(@&n)
    return n
""",
    "var": """\
fn f(n:& i32)
    var p: *i32 = @n
    *p = 3

pub fn main() -> i32
    var n: i32 = 1
    f(@&n)
    return n
""",
    "alias": """\
type IP = *i32

fn f(n:& i32)
    let p: IP = @n
    *p = 3

pub fn main() -> i32
    var n: i32 = 1
    f(@&n)
    return n
""",
    "return": """\
fn f(n:& i32) -> *i32
    return @n

pub fn main() -> i32
    var n: i32 = 1
    let p: *i32 = f(@&n)
    *p = 3
    return n
""",
    "generic_return": """\
fn id<T>(n:& T) -> *T
    return @n

pub fn main() -> i32
    var n: i32 = 1
    let p: *i32 = id<i32>(@&n)
    *p = 3
    return n
""",
    "argument": """\
fn g(p: *i32)
    *p = 3

fn f(n:& i32)
    g(@n)

pub fn main() -> i32
    var n: i32 = 1
    f(@&n)
    return n
""",
    "array_element": """\
fn f(n:& i32)
    var a: [2]*i32
    a[1] = @n
    *a[1] = 3

pub fn main() -> i32
    var n: i32 = 1
    f(@&n)
    return n
""",
}


def _compile(compiler, ritz1_bin, tmp_path: Path, name: str, program: str):
    batching.per_row()  # AGAST #2806
    work = tmp_path / f"{name}_{compiler}"
    work.mkdir()
    src = work / "main.ritz"
    src.write_text(program)
    ll = work / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
    else:
        comp = subprocess.run([str(ritz1_bin), str(src), "-o", str(ll)], cwd=work,
                              env=env, capture_output=True, text=True, timeout=300)
    return comp, ll, work


def _batch_compile(ritz1_bin):
    """batching.run's `compile`: the compile alone, into `work/main.ll` (AGAST #2867)."""
    def compile(compiler, src, work):
        ll = work / "main.ll"
        env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
        if compiler == "ritz0":
            comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=env, timeout=300)
        else:
            comp = subprocess.run([str(ritz1_bin), str(src), "-o", str(ll)], cwd=work,
                                  env=env, capture_output=True, text=True, timeout=300, check=False)
        return comp.returncode, comp.stdout + comp.stderr
    return compile


def _batch_build(ritz1_bin):
    """batching.run's `build`: compile and link a batch the way `_run` does a row."""
    def build(compiler, src, work):
        ll = work / "main.ll"
        code, output = _batch_compile(ritz1_bin)(compiler, src, work)
        if code != 0 or not ll.exists():
            return False, output, None
        exe = work / "main"
        cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
        if compiler == "ritz1":
            cmd.insert(2, str(RITZ_START))
        link = fast_link.clang(cmd, cwd=work, capture_output=True, text=True)
        return link.returncode == 0, link.stderr, exe
    return build


def _run(compiler, ritz1_bin, tmp_path: Path, name: str, program: str) -> int:
    got = batching.run(compiler, program, _batch_build(ritz1_bin),  # AGAST #2806
                       compile=_batch_compile(ritz1_bin))  # #2867
    if got is not None:
        return got
    comp, ll, work = _compile(compiler, ritz1_bin, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed on {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
    exe = work / "main"
    cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(cmd, cwd=work, capture_output=True, text=True)
    assert link.returncode == 0, f"{name} would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(STORES))
def test_ritz0_ref_field_holds_the_written_reference(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, STORES[name]) == 3


@pytest.mark.integration
def test_ritz0_large_literal_holds_the_written_reference(tmp_path):
    assert _run("ritz0", None, tmp_path, "large", LARGE_LITERAL) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CONTROLS))
def test_ritz0_slot_holds_what_it_is_given(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, CONTROLS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(DROP_STORES))
def test_ritz0_reference_to_a_drop_type_is_not_a_move(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, DROP_STORES[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MOVE_OUT))
def test_ritz0_by_value_field_is_still_a_move_out(tmp_path, name):
    comp, _, _ = _compile("ritz0", None, tmp_path, name, MOVE_OUT[name])
    assert comp.returncode != 0
    assert "cannot move out of a reference" in comp.stdout + comp.stderr


@pytest.mark.integration
def test_tempest_document_compiles(tmp_path):
    tempest = RITZ_ROOT.parent / "tempest"
    ll = tmp_path / "document.ll"
    env = dict(os.environ, RITZ_PATH=f"{tempest.parent}:{tempest}")
    comp = run_ritz0(["lib/document.ritz", "--no-runtime", "--project-root", ".",
                      "-o", str(ll)], cwd=tempest, env=env, timeout=300)
    assert comp.returncode == 0 and ll.exists(), comp.stdout[-2000:] + comp.stderr[-2000:]


def _ritz1_params(programs: dict) -> list:
    """Every program, with ritz1's known gaps as strict xfails."""
    return [pytest.param(name, marks=[pytest.mark.xfail(strict=True, reason=RITZ1_GAPS[name])]
                         if name in RITZ1_GAPS else [])
            for name in sorted(programs)]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(NO_IMPLICIT_DEREF))
def test_a_reference_is_not_its_referent(ritz1_bin, tmp_path, name, compiler):
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, name, NO_IMPLICIT_DEREF[name])
    assert comp.returncode != 0
    assert not ll.exists()
    assert re.search(r"main\.ritz:\d+:\d+: (error: )?" + re.escape(REF_INTO_VALUE),
                     comp.stdout + comp.stderr), comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", _ritz1_params(STORES))
def test_ritz1_ref_field_holds_the_written_reference(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, STORES[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _ritz1_params(CONTROLS))
def test_ritz1_slot_holds_what_it_is_given(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, CONTROLS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(DROP_STORES))
def test_ritz1_reference_to_a_drop_type_is_not_a_move(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, DROP_STORES[name]) == 3


# Loading the referent would hand one value to two owners, so ritz1 has to
# refuse here where it used to leave the rejection to clang. The error names a
# line in the source, which clang's never could.
@pytest.mark.integration
@pytest.mark.parametrize("name", _ritz1_params(MOVE_OUT))
def test_ritz1_by_value_field_is_still_a_move_out(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, MOVE_OUT[name])
    assert comp.returncode != 0
    assert not ll.exists()
    assert re.search(r"main\.ritz:\d+:\d+: error: cannot move out of a reference",
                     comp.stdout + comp.stderr), comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ0_MISSED_MOVE_OUT))
def test_ritz1_refuses_a_move_out_ritz0_misses(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, RITZ0_MISSED_MOVE_OUT[name])
    assert comp.returncode != 0
    assert not ll.exists()
    assert re.search(r"main\.ritz:\d+:\d+: error: cannot move out of a reference",
                     comp.stdout + comp.stderr), comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(POINTER_SLOTS))
def test_pointer_slot_holds_the_written_reference(ritz1_bin, tmp_path, compiler, name):
    assert _run(compiler, ritz1_bin, tmp_path, name, POINTER_SLOTS[name]) == 3


def _mismatch_params():
    for name in MISMATCHES_BARE:
        for compiler in ("ritz0", "ritz1"):
            marks = ([pytest.mark.xfail(strict=True, reason=POINTER_TO_POINTER_GAP)]
                     if (name, compiler) == ("pointer_of_the_same_width", "ritz1") else [])
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.integration
@pytest.mark.parametrize("name,compiler", list(_mismatch_params()))
def test_a_value_into_a_field_of_another_pointee_is_refused(ritz1_bin, tmp_path, compiler, name):
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, name, MISMATCHES[name].replace("^", ""))
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out[-2000:]
    assert not ll.exists()
    assert re.search(r"main\.ritz:\d+:\d+: (error: )?" + re.escape(VALUE_INTO_SHARED_REF), out), out[-2000:]


def _written_mismatch_params():
    for name in sorted(MISMATCHES):
        for compiler in COMPILERS:
            marks = ([pytest.mark.xfail(strict=True, reason=WRITTEN_POINTER_TO_POINTER_GAP)]
                     if name == "pointer_of_the_same_width" and compiler != "ritz0" else [])
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.integration
@pytest.mark.parametrize("name,compiler", list(_written_mismatch_params()))
def test_a_written_reference_into_a_field_of_another_pointee_is_refused(tmp_path, compiler, name):
    _assert_refused(compiler, tmp_path, name, MISMATCHES[name].replace("^", "^@"), REF_TO_OTHER_TYPE)


# A by-value slot only copies a referent of its own type. Reading a `C` as a
# `D` would be a silent reinterpretation, so neither compiler may produce a
# program. ritz1 leaves the refusal to clang.
ANOTHER_STRUCT = TYPES + """
struct D
    a: i64
    b: i64

struct VD
    d: D

fn mk(c:& C) -> VD
    var v: VD
    v.d = c
    return v

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var v: VD = mk(@&c)
    return v.d.a as i32
"""

# Nor does a `:&` of a pointer to pointer hold a `C`.
POINTER_REFERENT = TYPES + """
struct V
    c: C

fn mk(c:& **C) -> V
    var v: V
    v.c = c
    return v

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var p: *C = @c
    var q: **C = @p
    var v: V = mk(@&q)
    return v.c.x
"""

# An array of `C` names `C` as well: the slot must not get its first element.
ARRAY_REFERENT = TYPES + """
struct V
    c: C

fn mk(c:& [2]C) -> V
    var v: V
    v.c = c
    return v

pub fn main() -> i32
    var a: [2]C
    a[0].x = 3
    var v: V = mk(@&a)
    return v.c.x
"""

# AGAST #2279: the same refusals where the read isn't a store.  `return` read the
# local's slot as the struct, so these used to compile and return garbage.
ANOTHER_D = TYPES + """
struct D
    a: i64
    b: i64
"""

REFUSED_READS = {
    "another_struct_return": ANOTHER_D + """
fn f(c:& C) -> D
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: D = f(@&c)
    return d.a as i32
""",
    "another_struct_tail": ANOTHER_D + """
fn f(c:& C) -> D
    c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var d: D = f(@&c)
    return d.a as i32
""",
    "another_struct_let": ANOTHER_D + """
fn f(c:& C) -> i32
    let d: D = c
    return d.a as i32

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "another_struct_argument": ANOTHER_D + """
fn g(d: D) -> i32
    return 3

fn f(c:& C) -> i32
    return g(c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    "pointer_referent_return": TYPES + """
fn f(c:& **C) -> C
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var p: *C = @c
    var q: **C = @p
    var d: C = f(@&q)
    return d.x
""",
    "pointer_pointer_return": TYPES + """
fn f(c: **C) -> C
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var p: *C = @c
    var q: **C = @p
    var d: C = f(q)
    return d.x
""",
    "array_referent_return": TYPES + """
fn mk(c:& [2]C) -> C
    return c

pub fn main() -> i32
    var a: [2]C
    a[0].x = 3
    var v: C = mk(@&a)
    return v.x
""",
    "array_referent_tail": TYPES + """
fn mk(c:& [2]C) -> C
    c

pub fn main() -> i32
    var a: [2]C
    a[0].x = 3
    var v: C = mk(@&a)
    return v.x
""",
    "array_referent_let": TYPES + """
fn mk(c:& [2]C) -> i32
    let d: C = c
    return d.x

pub fn main() -> i32
    var a: [2]C
    a[0].x = 3
    return mk(@&a)
""",
    "array_referent_argument": TYPES + """
fn g(c: C) -> i32
    return c.x

fn mk(c:& [2]C) -> i32
    return g(c)

pub fn main() -> i32
    var a: [2]C
    a[0].x = 3
    return mk(@&a)
""",
    # Monomorph rewrites a bare `T` pointee: `[2]T` has to stay an array.
    "generic_array_referent_return": TYPES + """
fn mk<T>(c:& [2]T) -> T
    return c

pub fn main() -> i32
    var a: [2]C
    a[0].x = 3
    var v: C = mk<C>(@&a)
    return v.x
""",
    "generic_array_referent_field": TYPES + """
struct V
    c: C

fn mk<T>(c:& [2]T) -> V
    var v: V
    v.c = c
    return v

pub fn main() -> i32
    var a: [2]C
    a[0].x = 3
    var v: V = mk<C>(@&a)
    return v.c.x
""",
    # A type isn't a receiver, however `self` is spelled.
    "static_call_of_self_method": TYPES + """
impl C
    fn get(self: C) -> i32
        return self.x

fn f(c:& C) -> i32
    return C.get(c)

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""",
    # Not a borrow at all: an array local isn't its first element either.
    "array_local_return": TYPES + """
fn f() -> C
    var a: [2]C
    a[0].x = 3
    return a

pub fn main() -> i32
    var d: C = f()
    return d.x
""",
}

# An array copy has to match in length and element type.  ritz0 misses the
# element type (#2090), so these are ritz1's alone, and ritz1 says why.
ARRAY_MISMATCH = {
    "length_field": ("""\
struct H
    a: [2]i32

fn mk(a:& [3]i32) -> H
    var h: H
    h.a = a
    return h

pub fn main() -> i32
    var a: [3]i32 = [1, 3, 5]
    var h: H = mk(@&a)
    return h.a[1]
""", "array length does not match"),
    "length_let": ("""\
fn f(a:& [3]i32) -> i32
    let b: [2]i32 = a
    return b[1]

pub fn main() -> i32
    var a: [3]i32 = [1, 3, 5]
    return f(@&a)
""", "array length does not match"),
    "element_field": ("""\
struct H
    a: [2]i32

fn mk(a:& [2]i64) -> H
    var h: H
    h.a = a
    return h

pub fn main() -> i32
    var a: [2]i64 = [1, 3]
    var h: H = mk(@&a)
    return h.a[1]
""", ELEMENT_MISMATCH),
    # A struct borrow isn't an array, whatever length it reads as.
    "struct_referent": (TYPES + """
fn f(c:& C) -> i32
    let b: [2]i32 = c
    return b[1]

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
""", "whole-array assignment to a local array from this value is not supported"),
    "element_let": ("""\
fn f(a:& [2]i64) -> i32
    let b: [2]i32 = a
    return b[1]

pub fn main() -> i32
    var a: [2]i64 = [1, 3]
    return f(@&a)
""", ELEMENT_MISMATCH),
}


REFUSED = {
    "another_struct": ANOTHER_STRUCT,
    "array_referent": ARRAY_REFERENT,
    "pointer_referent": POINTER_REFERENT,
    **REFUSED_READS,
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_by_value_slot_of_another_type_is_refused(ritz1_bin, tmp_path, compiler, name):
    comp, ll, work = _compile(compiler, ritz1_bin, tmp_path, name, REFUSED[name])
    if comp.returncode != 0:
        return
    link = subprocess.run(["clang", str(ll), "-o", str(work / "main"), "-nostdlib",
                           str(RITZ_START)], cwd=work, capture_output=True, text=True)
    assert link.returncode != 0
    assert re.search(r"defined with type|doesn't match function result type", link.stderr), link.stderr


# A written reference returned is the caller's address.
# test_borrow_param_ref_slot.py has the rest of #2249's slots.
RETURNS_THE_BORROW = {
    "pointer": TYPES + """
fn f(c:& C) -> *C
    return @c

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: *C = f(@&c)
    p.x = 3
    return c.x
""",
    "reference": TYPES + """
fn f(c:& C) -> @C
    return @c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    let p: @C = f(@&c)
    return p.x
""",
    "mut_reference": TYPES + """
fn f(c:& C) -> @&C
    return @&c

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: @&C = f(@&c)
    p.x = 3
    return c.x
""",
    "mut_reference_tail": TYPES + """
fn f(c:& C) -> @&C
    @&c

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: @&C = f(@&c)
    p.x = 3
    return c.x
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(RETURNS_THE_BORROW))
def test_returned_reference_is_the_callers_address(ritz1_bin, tmp_path, compiler, name):
    assert _run(compiler, ritz1_bin, tmp_path, name, RETURNS_THE_BORROW[name]) == 3


# The strict xfails say these aren't done; this says what they do meanwhile.
# Reverting the guard in emit_return turns them back into garbage, which an
# xfail can't see: a wrong exit code is the failure it expects.
@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(USED_TO_RETURN_GARBAGE))
def test_ritz1_refuses_what_it_used_to_miscompile(ritz1_bin, tmp_path, name):
    comp, ll, work = _compile("ritz1", ritz1_bin, tmp_path, name, USED_TO_RETURN_GARBAGE[name])
    if comp.returncode != 0:
        return
    link = subprocess.run(["clang", str(ll), "-o", str(work / "main"), "-nostdlib",
                           str(RITZ_START)], cwd=work, capture_output=True, text=True)
    assert link.returncode != 0
    assert "defined with type" in link.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ARRAY_MISMATCH))
def test_ritz1_array_referent_must_match_its_slot(ritz1_bin, tmp_path, name):
    program, message = ARRAY_MISMATCH[name]
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, program)
    assert comp.returncode != 0
    assert not ll.exists()
    assert message in comp.stdout + comp.stderr
