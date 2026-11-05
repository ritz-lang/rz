"""AGAST #2286: `@c` / `@&c` of a `:&` parameter is the borrow's pointer.

    fn h(p: *C) -> i32
        return p.x

    fn f(c:& C) -> i32
        return h(@c)        # ritz0 3, ritz1 88

A `c:& C` param's slot holds the borrow's pointer, so the address of that slot
is a pointer to the pointer. `@c` took it, and everything downstream read or
wrote the slot as if it were the referent, with no diagnostic. `*p = ...` through
it overwrote the borrow itself.

LocalVar.is_lent doesn't say which params these are: it's set on an integer,
whose slot IS the caller's variable, and not on `:& f64`, `:& bool` or `:& **C`,
whose slots hold a pointer like a struct's. holds_lent_ptr says it. `self` is
passed as a `ptr` however it's spelled, so every receiver that isn't declared as
a reference is one too, but `self: @C` keeps `@self` as the reference's address.

Every program exits 3 on success, and ritz0 is the oracle: each is checked on
both compilers. Where a program can, it writes through the address and reads the
caller's variable, so a pointer to a copy can't pass.
"""

import re

import pytest

from test_borrow_param_ref_field import _compile, _run

TYPES = """\
struct C
    x: i32
    y: i64

struct D
    a: i64
    b: i64

struct Big
    x: i32
    pad: [64]i64

struct H
    p: *C

struct R
    p: @&C

enum E
    One(i32)
    Nope

"""

MAIN_C = """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@c)
"""

# The caller's `x` starts at 1: only a write through the borrow makes it 3.
MAIN_WRITE = """
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    f(@c)
    return c.x
"""

MAIN_CALLER_KEEPS = """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    c.g()
    return c.x
"""

MAIN_SAME = """
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    return f(@c, @c)
"""

MAIN_BIG = """
pub fn main() -> i32
    var c: Big
    c.x = 3
    return f(@c)
"""

MAIN_ARRAY = """
pub fn main() -> i32
    var a: [2]i32 = [1, 3]
    return f(@a)
"""

MAIN_ARRAY_WRITE = """
pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@a)
    return a[1]
"""

MAIN_F64 = """
pub fn main() -> i32
    var n: f64 = 3.0
    return f(@n)
"""


GENERIC = """\
struct W<T>
    v: T

"""

MAIN_W = """
pub fn main() -> i32
    var w: W<i32> = W<i32> { v: 3 }
    return f(@w)
"""

# Named so that ritz1's name-based Vec paths see it. ritzlib's would need linking.
VEC = """\
struct Vec<T>
    data: *T
    len: i64

"""

MAIN_VEC = """
pub fn main() -> i32
    var d: [2]i32 = [1, 3]
    var v: Vec<i32>
    v.data = @d[0]
    v.len = 2
    return f(@v)
"""


# The caller's Res drops once, after `go` returns: 2 + 1.
DROP = """\
var G: i32 = 2

struct Res
    id: i32

impl Drop for Res
    fn drop(self:& Res)
        G = G + 1

"""

MAIN_DROP = """
fn go()
    var r: Res = Res { id: 3 }
    f(@r)

pub fn main() -> i32
    go()
    return G
"""


def _body(body: str, main: str = MAIN_C) -> str:
    return TYPES + body + main


READ_P = "    return p.x\n"

# `@c` and `@&c` of a struct, into every kind of slot.
STRUCT = {
    "let_ptr": _body("fn f(c:& C) -> i32\n    let p: *C = @c\n" + READ_P),
    "let_ref": _body("fn f(c:& C) -> i32\n    let p: @C = @c\n" + READ_P),
    "let_mut_ref": _body("fn f(c:& C) -> i32\n    let p: @&C = @&c\n" + READ_P),
    "let_mut_into_ptr": _body("fn f(c:& C) -> i32\n    let p: *C = @&c\n" + READ_P),
    "let_untyped": _body("fn f(c:& C) -> i32\n    let p = @c\n" + READ_P),
    "let_untyped_mut": _body("fn f(c:& C) -> i32\n    let p = @&c\n" + READ_P),
    "var_ptr": _body("fn f(c:& C) -> i32\n    var p: *C = @c\n" + READ_P),
    "assign_ptr": _body("fn f(c:& C) -> i32\n    var p: *C = null\n    p = @c\n" + READ_P),
    "write_through_ptr": _body("fn f(c:& C)\n    let p: *C = @c\n    p.x = 3\n", MAIN_WRITE),
    "write_through_mut": _body("fn f(c:& C)\n    let p: @&C = @&c\n    p.x = 3\n", MAIN_WRITE),
    "write_through_untyped": _body("fn f(c:& C)\n    let p = @c\n    p.x = 3\n", MAIN_WRITE),
    "same_pointer": _body("""\
fn f(c:& C, o: *C) -> i32
    let p: *C = @c
    if p == o
        return 3
    return 0
""", MAIN_SAME),
    "same_address_as_integer": _body("""\
fn f(c:& C, o: *C) -> i32
    if (@c as i64) == (o as i64)
        return 3
    return 0
""", MAIN_SAME),
    "pointer_arithmetic": _body("""\
fn f(c:& C, o: *C) -> i32
    let q: *C = @c + 1
    if q == o + 1
        return 3
    return 0
""", MAIN_SAME),
    "pointer_to_pointer": _body("""\
fn f(c:& C) -> i32
    var p: *C = @c
    let q: **C = @p
    return (*q).x
"""),
    "if_arm": _body("""\
fn f(c:& C) -> i32
    let p: *C = if c.x == 3
        @c
    else
        @c
    return p.x
"""),
    "field_assign": _body("fn f(c:& C) -> i32\n    var h: H\n    h.p = @c\n    return h.p.x\n"),
    "field_literal": _body("fn f(c:& C) -> i32\n    let h: H = H { p: @c }\n    return h.p.x\n"),
    "field_reference": _body("fn f(c:& C) -> i32\n    let r: R = R { p: @&c }\n    return r.p.x\n"),
    "return_ptr": _body("""\
fn g(c:& C) -> *C
    return @c

fn f(c:& C) -> i32
    let p: *C = g(@c)
    return p.x
"""),
    "return_ref": _body("""\
fn g(c:& C) -> @C
    return @c

fn f(c:& C) -> i32
    let p: @C = g(@c)
    return p.x
"""),
    "return_mut_ref": _body("""\
fn g(c:& C) -> @&C
    return @&c

fn f(c:& C) -> i32
    let p: @&C = g(@&c)
    return p.x
"""),
    "tail_ptr": _body("""\
fn g(c:& C) -> *C
    @c

fn f(c:& C) -> i32
    let p: *C = g(@c)
    return p.x
"""),
    "tail_mut_ref": _body("""\
fn g(c:& C) -> @&C
    @&c

fn f(c:& C) -> i32
    let p: @&C = g(@&c)
    return p.x
"""),
    "deref": _body("fn f(c:& C) -> i32\n    let d: C = *@c\n    return d.x\n"),
    "lent_on": _body("""\
fn k(p: *C) -> i32
    return p.x

fn h(d:& C) -> i32
    return k(@d)

fn f(c:& C) -> i32
    return h(@c)
"""),
    "generic_struct": _body("""\
fn h<T>(p:& T) -> *T
    return @p

fn f(c:& C) -> i32
    let p: *C = h<C>(@c)
    return p.x
"""),
    "generic_struct_type": TYPES + GENERIC + """\
fn k(p: *W<i32>) -> i32
    return p.v

fn f(c:& W<i32>) -> i32
    return k(@c)
""" + MAIN_W,
    "generic_fn_over_generic_struct": TYPES + GENERIC + """\
fn k<T>(p: *W<T>) -> T
    return p.v

fn f<T>(c:& W<T>) -> T
    return k<T>(@c)

pub fn main() -> i32
    var w: W<i32> = W<i32> { v: 3 }
    return f<i32>(@w)
""",
    "generic_struct_deref": TYPES + GENERIC + """\
fn f(c:& W<i32>) -> i32
    let d: W<i32> = *@c
    return d.v
""" + MAIN_W,
    "generic_struct_untyped": TYPES + GENERIC + """\
fn f(c:& W<i32>) -> i32
    let p = @c
    return p.v
""" + MAIN_W,
    "for_vec": VEC + """\
fn f(v:& Vec<i32>) -> i32
    var t: i32 = 0
    for x in @v
        t = t + x
    return t - 1
""" + MAIN_VEC,
    "match": TYPES + """\
fn f(e:& E) -> i32
    match @e
        E.One(v) => return v
        E.Nope => return 0
    return 0

pub fn main() -> i32
    var e: E = E.One(3)
    return f(@e)
""",
}

# The argument cascades: each param kind, free fn and method.
ARGUMENTS = {
    "ptr": _body("fn h(p: *C) -> i32\n    return p.x\n\nfn f(c:& C) -> i32\n    return h(@c)\n"),
    "ref": _body("fn h(p: @C) -> i32\n    return p.x\n\nfn f(c:& C) -> i32\n    return h(@c)\n"),
    "mut_ref": _body("fn h(p: @&C) -> i32\n    return p.x\n\nfn f(c:& C) -> i32\n    return h(@&c)\n"),
    "mut_into_ptr": _body("fn h(p: *C) -> i32\n    return p.x\n\nfn f(c:& C) -> i32\n    return h(@&c)\n"),
    "borrow": _body("fn h(p:& C) -> i32\n    return p.x\n\nfn f(c:& C) -> i32\n    return h(@c)\n"),
    "mut_into_borrow": _body("fn h(p:& C) -> i32\n    return p.x\n\nfn f(c:& C) -> i32\n    return h(@&c)\n"),
    # lexis's shape: `peek(@t)` with `fn peek(t: CssTokenizer)`.
    "by_value": _body("fn h(p: C) -> i32\n    return p.x\n\nfn f(c:& C) -> i32\n    return h(@c)\n"),
    "by_value_byval": _body("fn h(p: Big) -> i32\n    return p.x\n\nfn f(c:& Big) -> i32\n    return h(@c)\n",
                            MAIN_BIG),
    "by_value_is_a_copy": _body("""\
fn h(p: C) -> i32
    p.x = 9
    return 0

fn f(c:& C) -> i32
    h(@c)
    return c.x
"""),
    "mut_into_by_value": _body("fn h(p: C) -> i32\n    return p.x\n\nfn f(c:& C) -> i32\n    return h(@&c)\n"),
    "mut_into_by_value_byval": _body("fn h(p: Big) -> i32\n    return p.x\n\nfn f(c:& Big) -> i32\n    return h(@&c)\n",
                                     MAIN_BIG),
    "method_by_value": _body("""\
impl C
    fn g(self: @C, p: C) -> i32
        return p.x

fn f(c:& C) -> i32
    return c.g(@c)
"""),
    "addr_receiver": _body("""\
impl C
    fn g(self: @C) -> i32
        return self.x

fn f(c:& C) -> i32
    return (@c).g()
"""),
    "method_ptr": _body("""\
impl C
    fn g(self: @C, p: *C) -> i32
        return p.x

fn f(c:& C) -> i32
    return c.g(@c)
"""),
    "method_mut_ref": _body("""\
impl C
    fn g(self: @C, p: @&C) -> i32
        return p.x

fn f(c:& C) -> i32
    return c.g(@&c)
"""),
}

ARRAYS = {
    "let_ref_store": _body("fn f(a:& [2]i32)\n    let p: *[2]i32 = @a\n    *p = [1, 3]\n", MAIN_ARRAY_WRITE),
    "let_mut_ref_store": _body("fn f(a:& [2]i32)\n    let p: @&[2]i32 = @&a\n    *p = [1, 3]\n", MAIN_ARRAY_WRITE),
    "let_ptr_read": _body("""\
fn f(a:& [2]i32) -> i32
    let p: *[2]i32 = @a
    let b: [2]i32 = *p
    return b[1]
""", MAIN_ARRAY),
    "let_ref_read": _body("""\
fn f(a:& [2]i32) -> i32
    let p: @[2]i32 = @a
    let b: [2]i32 = *p
    return b[1]
""", MAIN_ARRAY),
    "untyped_read": _body("""\
fn f(a:& [2]i32) -> i32
    let p = @a
    let b: [2]i32 = *p
    return b[1]
""", MAIN_ARRAY),
    "deref": _body("fn f(a:& [2]i32) -> i32\n    let b: [2]i32 = *@a\n    return b[1]\n", MAIN_ARRAY),
    "argument_ptr": _body("""\
fn g(p: *[2]i32) -> i32
    let b: [2]i32 = *p
    return b[1]

fn f(a:& [2]i32) -> i32
    return g(@a)
""", MAIN_ARRAY),
    "argument_ref": _body("""\
fn g(p: @[2]i32) -> i32
    let b: [2]i32 = *p
    return b[1]

fn f(a:& [2]i32) -> i32
    return g(@a)
""", MAIN_ARRAY),
    "argument_mut_ref": _body("""\
fn g(p: @&[2]i32) -> i32
    let b: [2]i32 = *p
    return b[1]

fn f(a:& [2]i32) -> i32
    return g(@&a)
""", MAIN_ARRAY),
    "argument_borrow": _body("""\
fn g(p:& [2]i32) -> i32
    let b: [2]i32 = p
    return b[1]

fn f(a:& [2]i32) -> i32
    return g(@a)
""", MAIN_ARRAY),
    "argument_mut_into_borrow": _body("""\
fn g(p:& [2]i32) -> i32
    let b: [2]i32 = p
    return b[1]

fn f(a:& [2]i32) -> i32
    return g(@&a)
""", MAIN_ARRAY),
    "argument_by_value": _body("fn g(p: [2]i32) -> i32\n    return p[1]\n\nfn f(a:& [2]i32) -> i32\n    return g(@a)\n",
                               MAIN_ARRAY),
    "return_ptr": _body("""\
fn g(a:& [2]i32) -> *[2]i32
    return @a

fn f(a:& [2]i32) -> i32
    let p: *[2]i32 = g(@a)
    let b: [2]i32 = *p
    return b[1]
""", MAIN_ARRAY),
    "struct_elements": _body("""\
fn g(p: *[2]C) -> i32
    let b: [2]C = *p
    return b[1].x

fn f(a:& [2]C) -> i32
    return g(@a)
""", """
pub fn main() -> i32
    var a: [2]C
    a[1].x = 3
    return f(@a)
"""),
    "for": _body("""\
fn f(a:& [2]i32) -> i32
    var t: i32 = 0
    for x in @a
        t = t + x
    return t - 1
""", MAIN_ARRAY),
    "span": "import ritzlib.span\n" + _body("""\
fn g(p: Span<i32>) -> i32
    return p[1]

fn f(a:& [2]i32) -> i32
    return g(@a)
""", MAIN_ARRAY),
}

# Referents is_lent doesn't cover, whose slots hold a pointer all the same.
OTHER_REFERENTS = {
    "f64_let": _body("fn f(n:& f64) -> i32\n    let p: *f64 = @n\n    return *p as i32\n", MAIN_F64),
    "f64_mut_let": _body("fn f(n:& f64) -> i32\n    let p: @&f64 = @&n\n    return *p as i32\n", MAIN_F64),
    "f64_argument": _body("fn h(p: *f64) -> i32\n    return *p as i32\n\nfn f(n:& f64) -> i32\n    return h(@n)\n",
                          MAIN_F64),
    "f64_deref": _body("fn f(n:& f64) -> i32\n    return (*@n) as i32\n", MAIN_F64),
    "f64_write": _body("fn f(n:& f64)\n    let p: *f64 = @n\n    *p = 3.0\n", """
pub fn main() -> i32
    var n: f64 = 1.0
    f(@n)
    return n as i32
"""),
    "f32_let": _body("fn f(n:& f32) -> i32\n    let p: *f32 = @n\n    return *p as i32\n", """
pub fn main() -> i32
    var n: f32 = 3.0
    return f(@n)
"""),
    "bool_let": _body("""\
fn f(n:& bool) -> i32
    let p: *bool = @n
    if *p
        return 3
    return 0
""", """
pub fn main() -> i32
    var n: bool = true
    return f(@n)
"""),
    "bool_write": _body("fn f(n:& bool)\n    let p: *bool = @n\n    *p = true\n", """
pub fn main() -> i32
    var n: bool = false
    f(@n)
    if n
        return 3
    return 0
"""),
    "pointer_to_pointer_referent": _body("fn f(h:& **C) -> i32\n    let p: ***C = @h\n    return (**p).x\n", """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var p: *C = @c
    var q: **C = @p
    return f(@q)
"""),
    # `h:& **C` names `C` as well, and `@h` is no `*C`.
    "pointer_to_pointer_deref": _body("fn f(h:& **C) -> i32\n    let q: **C = *@h\n    return (**q).x\n", """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var p: *C = @c
    var q: **C = @p
    return f(@q)
"""),
    "pointer_to_pointer_untyped": _body("fn f(h:& **C) -> i32\n    let p = @h\n    let q: **C = *p\n    return (**q).x\n", """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var p: *C = @c
    var q: **C = @p
    return f(@q)
"""),
    "reference_referent_deref": _body("fn f(h:& @C) -> i32\n    let q: @C = *@h\n    return q.x\n", """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var p: @C = @c
    return f(@p)
"""),
    "pointer_to_float_referent": _body("fn f(h:& *f64) -> i32\n    let p: **f64 = @h\n    return **p as i32\n", """
pub fn main() -> i32
    var n: f64 = 3.0
    var p: *f64 = @n
    return f(@p)
"""),
    "generic_f64": _body("""\
fn h<T>(p:& T) -> *T
    return @p

fn f() -> i32
    var n: f64 = 3.0
    let p: *f64 = h<f64>(@n)
    return *p as i32
""", "\npub fn main() -> i32\n    return f()\n"),
}

SELF = {
    "typed": _body("""\
fn h(p: *C) -> i32
    return p.x

impl C
    fn g(self:& C) -> i32
        return h(@self)

fn f(c:& C) -> i32
    return c.g()
"""),
    "bare": _body("""\
fn h(p: *C) -> i32
    return p.x

impl C
    fn g(self:&) -> i32
        return h(@self)

fn f(c:& C) -> i32
    return c.g()
"""),
    "by_value_argument": _body("""\
fn h(p: C) -> i32
    return p.x

impl C
    fn g(self:&) -> i32
        return h(@self)

fn f(c:& C) -> i32
    return c.g()
"""),
    "by_value": _body("""\
fn h(p: *C) -> i32
    return p.x

impl C
    fn g(self: C) -> i32
        return h(@self)

fn f(c:& C) -> i32
    return c.g()
"""),
    "bare_by_value": _body("""\
fn h(p: *C) -> i32
    return p.x

impl C
    fn g(self) -> i32
        return h(@self)

fn f(c:& C) -> i32
    return c.g()
"""),
    # A free fn may name a param `self`, and it binds like any other.
    "free_fn": _body("""\
fn h(p: *C) -> i32
    return p.x

fn f(self:& C) -> i32
    return h(@self)
"""),
    "generic_typed": TYPES + GENERIC + """\
fn k(p: *W<i32>) -> i32
    return p.v

impl<T> W<T>
    fn g(self:& W<T>) -> i32
        return k(@self)

pub fn main() -> i32
    var w: W<i32> = W<i32> { v: 3 }
    return w.g()
""",
    "generic_bare": TYPES + GENERIC + """\
fn k(p: *W<i32>) -> i32
    return p.v

impl<T> W<T>
    fn g(self:&) -> i32
        return k(@self)

pub fn main() -> i32
    var w: W<i32> = W<i32> { v: 3 }
    return w.g()
""",
    "generic_by_value": TYPES + GENERIC + """\
fn k(p: *W<i32>) -> i32
    return p.v

impl<T> W<T>
    fn g(self: W<T>) -> i32
        return k(@self)

pub fn main() -> i32
    var w: W<i32> = W<i32> { v: 3 }
    return w.g()
""",
    # A by-value receiver is the callee's own: the caller's `x` stays 3.
    "by_value_field_write": _body("""\
impl C
    fn g(self: C)
        self.x = 9
""", MAIN_CALLER_KEEPS),
    "by_value_address_write": _body("""\
impl C
    fn g(self: C)
        let p: *C = @self
        p.x = 9
""", MAIN_CALLER_KEEPS),
    "let": _body("""\
impl C
    fn g(self:&) -> i32
        let p = @self
        return p.x

fn f(c:& C) -> i32
    return c.g()
"""),
    "write": _body("""\
impl C
    fn g(self:&)
        let p: *C = @self
        p.x = 3

fn f(c:& C)
    c.g()
""", MAIN_WRITE),
}

# Right before #2286, and they have to stay right: each slot here is not a
# pointer to the referent, so reading it would be a new bug.
CONTROLS = {
    # An integer's slot IS the caller's variable.
    "int_let": _body("fn f(n:& i32) -> i32\n    let p: *i32 = @n\n    return *p\n", """
pub fn main() -> i32
    var n: i32 = 3
    return f(@n)
"""),
    "int_mut_let": _body("fn f(n:& i32) -> i32\n    let p: @&i32 = @&n\n    return *p\n", """
pub fn main() -> i32
    var n: i32 = 3
    return f(@n)
"""),
    "int_write": _body("fn f(n:& i32)\n    let p: *i32 = @n\n    *p = 3\n", """
pub fn main() -> i32
    var n: i32 = 1
    f(@n)
    return n
"""),
    "int_argument": _body("fn h(p: *i32) -> i32\n    return *p\n\nfn f(n:& i32) -> i32\n    return h(@n)\n", """
pub fn main() -> i32
    var n: i32 = 3
    return f(@n)
"""),
    "int_deref": _body("fn f(n:& i32) -> i32\n    return *@n\n", """
pub fn main() -> i32
    var n: i32 = 3
    return f(@n)
"""),
    "u8_let": _body("fn f(n:& u8) -> i32\n    let p: *u8 = @n\n    return *p as i32\n", """
pub fn main() -> i32
    var n: u8 = 3
    return f(@n)
"""),
    "i64_let": _body("fn f(n:& i64) -> i64\n    let p: *i64 = @n\n    return *p\n", """
pub fn main() -> i32
    var n: i64 = 3
    return f(@n) as i32
"""),
    "generic_int": _body("""\
fn h<T>(p:& T) -> *T
    return @p

fn f() -> i32
    var n: i32 = 3
    let p: *i32 = h<i32>(@n)
    return *p
""", "\npub fn main() -> i32\n    return f()\n"),
    # `p:& *T`'s slot is the caller's pointer variable: `@h` is a `**T`.
    "pointer_referent": _body("fn f(h:& *C) -> i32\n    let p: **C = @h\n    return (*p).x\n", """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var p: *C = @c
    return f(@p)
"""),
    "pointer_to_int_referent": _body("fn f(h:& *i32) -> i32\n    let p: **i32 = @h\n    return **p\n", """
pub fn main() -> i32
    var n: i32 = 3
    var p: *i32 = @n
    return f(@p)
"""),
    # Not borrows: `@x` is the address of x's own slot.
    "local": _body("""\
fn h(p: *C) -> i32
    return p.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return h(@c)
""", ""),
    "by_value_param": _body("""\
fn h(p: *C) -> i32
    return p.x

fn f(c: C) -> i32
    return h(@c)
""", """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(c)
"""),
    "pointer_param": _body("fn h(p: **C) -> i32\n    return (*p).x\n\nfn f(c: *C) -> i32\n    return h(@c)\n"),
    "self_ref": _body("""\
fn h(p: **C) -> i32
    return (*p).x

impl C
    fn g(self: @C) -> i32
        return h(@self)

fn f(c:& C) -> i32
    return c.g()
"""),
    "self_mut_ref": _body("""\
fn h(p: **C) -> i32
    return (*p).x

impl C
    fn g(self: @&C) -> i32
        return h(@self)

fn f(c:& C) -> i32
    return c.g()
"""),
    # `self:& T` and `self: @&T` were one Param until #2286 told them apart.
    "self_free_fn_mut_ref": _body("""\
fn h(p: **C) -> i32
    return (*p).x

fn f(self: @&C) -> i32
    return h(@self)
""", """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@&c)
"""),
    # Taking the address of a move-only referent lends it on: nothing drops.
    "move_only_pointer": DROP + """\
fn h(r: *Res) -> i32
    return r.id

fn f(t:& Res) -> i32
    return h(@t)
""" + MAIN_DROP,
    "move_only_deref_field": DROP + """\
fn f(t:& Res) -> i32
    return (*@t).id
""" + MAIN_DROP,
    # A local that shadows the param is that local, not the borrow.
    "shadowed_by_struct": _body("""\
fn h(p: *C) -> i32
    return p.x

fn f(c:& C) -> i32
    var d: C = C { x: 3, y: 0 }
    if d.x == 3
        var c: C = C { x: 3, y: 0 }
        return h(@c)
    return 0
""", MAIN_C.replace("x: 3", "x: 1")),
    "shadowed_by_pointer": _body("""\
fn h(p: **C) -> i32
    return (*p).x

fn f(c:& C) -> i32
    var e: C = C { x: 3, y: 0 }
    let c: *C = @e
    return h(@c)
""", MAIN_C.replace("x: 3", "x: 1")),
    # The field and the parenthesised forms never went through the slot.
    "field_address": _body("fn f(c:& C) -> i32\n    let p: *i32 = @c.x\n    return *p\n"),
    "parenthesised_field": _body("fn f(c:& C) -> i32\n    return (@c).x\n"),
}

# ritz0 can't compile this one: ritzlib.span brings ritzlib's Vec, which clashes.
VEC_SPAN = "import ritzlib.span\n" + VEC + """\
fn g(p: Span<i32>) -> i32
    return p[1]

fn f(v:& Vec<i32>) -> i32
    return g(@v)
""" + MAIN_VEC

# `@c` is a `*C` now, so ritz1's rule for `@x` applies to it. ritz0 accepts this
# one for a local and a `:&` alike, and reinterprets the `C`.
WRONG_POINTEE = _body("""\
fn h(p: *D) -> i64
    return p.a

fn f(c:& C) -> i64
    return h(@c)
""", """
pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@c) as i32
""")

# ritz0 compiles these two and drops the value twice (#2227). ritz1 failed at
# clang before `*@t` could be typed, and reads `t` by value here as `t` itself.
MOVE_OUT = {
    "let": DROP + "fn f(t:& Res) -> i32\n    let d: Res = *@t\n    return d.id\n" + MAIN_DROP,
    "self": DROP + """\
impl Res
    fn g(self:& Res) -> i32
        let d: Res = *@self
        return d.id

fn f(t:& Res) -> i32
    return t.g()
""" + MAIN_DROP,
}

# `a:& [2]C` names `C` as well, but `@a` is no `*C`: reading it as one gets
# element 0, silently. Refused by both compilers.
MAIN_ELEMENTS = """
pub fn main() -> i32
    var a: [2]C
    a[0].x = 3
    return f(@a)
"""

NOT_THE_ELEMENT = {
    "deref": _body("fn f(a:& [2]C) -> i32\n    let d: C = *@a\n    return d.x\n", MAIN_ELEMENTS),
    "untyped_field": _body("fn f(a:& [2]C) -> i32\n    let p = @a\n    return p.x\n", MAIN_ELEMENTS),
}

GROUPS = {"struct": STRUCT, "argument": ARGUMENTS, "array": ARRAYS,
          "referent": OTHER_REFERENTS, "self": SELF, "control": CONTROLS}

ALL = {f"{group}_{name}": source
       for group, programs in GROUPS.items()
       for name, source in programs.items()}

# Still open on ritz1, each held to ritz0's answer by a strict xfail.
RITZ1_GAPS = {
    "array_deref": "AGAST #2305: `*@a` isn't a whole-array source, for a local either",
    "array_untyped_read": "AGAST #2304: `let p = @b` doesn't record the pointee array",
    "array_for": "AGAST #2314: `for x in @a` runs zero iterations",
    "struct_for_vec": "AGAST #2314: `for x in @v` runs zero iterations",
    "self_by_value_field_write": "AGAST #2316: a by-value `self` isn't a copy",
    "self_by_value_address_write": "AGAST #2316: a by-value `self` isn't a copy",
    "self_generic_bare": "AGAST #2318: bare `self:&` in a generic impl doesn't compile",
    "self_generic_by_value": "AGAST #2318: `self: W<T>` in a generic impl doesn't compile",
    "argument_mut_into_by_value": "AGAST #2317: `h(@&x)` into a by-value param fails at clang",
    "argument_mut_into_by_value_byval": "AGAST #2317: `h(@&x)` into a by-value param fails at clang",
    "argument_method_by_value": "AGAST #2317: `c.g(@x)` into a by-value method param fails at clang",
    "argument_addr_receiver": "AGAST #2317: `(@c).g()` has no receiver type, for a local either",
    "control_move_only_deref_field": "AGAST #2317: `(*@t).id` is unhandled, as `(@c).g()` is",
}


def _ritz1_params() -> list:
    return [pytest.param(name, marks=[pytest.mark.xfail(strict=True, reason=RITZ1_GAPS[name])]
                         if name in RITZ1_GAPS else [])
            for name in sorted(ALL)]


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL))
def test_ritz0_address_of_borrow(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, ALL[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _ritz1_params())
def test_ritz1_address_of_borrow(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, ALL[name]) == 3


@pytest.mark.integration
def test_ritz1_vec_into_a_span(ritz1_bin, tmp_path):
    assert _run("ritz1", ritz1_bin, tmp_path, "vec_span", VEC_SPAN) == 3


@pytest.mark.integration
def test_ritz1_refuses_a_borrow_of_another_type(ritz1_bin, tmp_path):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, "wrong", WRONG_POINTEE)
    assert comp.returncode != 0
    assert not ll.exists()
    assert "argument 1 of `h` has the wrong type: D* != C*" in comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MOVE_OUT))
def test_ritz1_deref_of_the_address_is_still_a_move_out(ritz1_bin, tmp_path, name):
    comp, ll, _ = _compile("ritz1", ritz1_bin, tmp_path, name, MOVE_OUT[name])
    assert comp.returncode != 0
    assert not ll.exists()
    assert re.search(r"main\.ritz:\d+:\d+: error: cannot move out of borrowed parameter `(t|self)`",
                     comp.stdout + comp.stderr), comp.stdout + comp.stderr


# ritz1 leaves `deref` to clang, which is why this isn't a check on the compile.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(NOT_THE_ELEMENT))
def test_address_of_a_borrowed_array_is_not_its_element(ritz1_bin, tmp_path, name, compiler):
    with pytest.raises(AssertionError, match=f"(failed on|would not link).*{name}|{name}.*would not link"):
        _run(compiler, ritz1_bin, tmp_path, name, NOT_THE_ELEMENT[name])
