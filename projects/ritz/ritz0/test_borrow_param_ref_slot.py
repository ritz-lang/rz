"""A reference to a `name:& T` parameter, written out, in every reference slot.

    fn go(c:& C)
        let p: @&C = @&c    # p refers to the caller's `C`

    fn id(c:& C) -> @&C
        return @&c          # and so does the result

`c` is an alias of the caller's place, so it has type `C` in the whole body and
a `C` never fits a reference slot (LANGUAGE_SPEC §13.4, LARB ruling R1, AGAST
#2337). The reference is written, `@&c` for an `@&T` and `@c` for an `@T` or
`*T`, and these hold it to what #2249 asked of the slot: the caller's address,
in every position a value reaches one from: `let`, `var`, `return`, a tail, `=`,
a cast, an `if`/`match` arm of any of those, and an element of an array or tuple
literal.

Every program returns 3 on success and writes through the reference after it
was bound, or reads through it after the referent changed, so a pointer to a
temporary copy can't pass.

test_value_into_ref.py has the refusals of the bare form at each slot. What's
here is a shape that table doesn't have. `@x` doesn't fit an `@&T` or a `:&`
(#2339), so an `@&T` slot or `:&` param is only ever given `@&c`, an `@&T` value
or a place.
"""

import re

import pytest

from ref_rules import REF_TO_OTHER_TYPE, VALUE_INTO_MUT_REF, VALUE_INTO_SHARED_REF
from test_borrow_param_ref_field import _compile, _run
from test_ref_into_value import COMPILERS, _assert_refused

# None of these needs a `:&` to fail. #2309 lists each, and is closing.
ELEMENT_GAP = "AGAST #2369: `a[0].x` through an `@&C` or `@C` element is `unhandled EXPR_MEMBER` on ritz1"
IF_VALUE_GAP = "AGAST #2369: ritz1 doesn't parse an `if` value after `=` or in a struct literal"
# No ticket has these.
PAYLOAD_GAP = "AGAST #2369: `p.x = 3` on a reference payload is `unhandled EXPR_MEMBER` on ritz1, without a `:&` too"
CAST_GAP = ("AGAST #2370: a value cast to a reference isn't refused: ritz1 runs it, and ritz0 reports "
            "`cannot store` at the later `p.x = 3`")

TYPES = """\
struct C
    x: i32
    y: i64

"""

# Calls `go`, which writes through the reference, then reads the caller's `c`.
GO = """
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    go(@&c)
    return c.x
"""
GO_K = GO.replace("go(@&c)", "go(@&c, 0)")

# `id` hands the reference back, and the caller writes through it.
ID = """
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: SLOT = id(@&c)
    p.x = 3
    return c.x
"""
ID_K = ID.replace("id(@&c)", "id(@&c, 0)")

# Reads through a shared reference, after the referent changed.
READ = """
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    return go(@&c)
"""
READ_ID = """
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: @C = id(@&c)
    c.x = 3
    return p.x
"""

# Each takes the slot's spelling, `@&C` or `*C`, and ADDR the `@&` or `@` that
# makes one.
WRITABLE = {
    "let": "fn go(c:& C)\n    let p: SLOT = ADDRc\n    p.x = 3\n" + GO,
    "var": "fn go(c:& C)\n    var p: SLOT = ADDRc\n    p.x = 3\n" + GO,
    "grouped": "fn go(c:& C)\n    let p: SLOT = (ADDRc)\n    p.x = 3\n" + GO,
    "cast": "fn go(c:& C)\n    let p: SLOT = ADDRc as SLOT\n    p.x = 3\n" + GO,
    "assign": """\
fn go(c:& C)
    var d: C = C { x: 9, y: 0 }
    var p: SLOT = ADDRd
    p = ADDRc
    p.x = 3
""" + GO,
    "assign_in_arm": """\
fn go(c:& C, k: i32)
    var d: C = C { x: 9, y: 0 }
    var p: SLOT = ADDRd
    match k
        0 => p = ADDRc
        _ => pass
    p.x = 3
""" + GO_K,
    "assign_from_if": """\
fn go(c:& C, k: i32)
    var d: C = C { x: 9, y: 0 }
    var p: SLOT = ADDRd
    p = if k == 0
        ADDRc
    else
        ADDRc
    p.x = 3
""" + GO_K,
    "return": "fn id(c:& C) -> SLOT\n    return ADDRc\n" + ID,
    "return_grouped": "fn id(c:& C) -> SLOT\n    return (ADDRc)\n" + ID,
    "tail": "fn id(c:& C) -> SLOT\n    ADDRc\n" + ID,
    "return_in_if": """\
fn id(c:& C) -> SLOT
    if c.y == 0
        return ADDRc
    return ADDRc
""" + ID,
    "return_in_arm": """\
fn id(c:& C, k: i32) -> SLOT
    match k
        0 => return ADDRc
        _ => return ADDRc
""" + ID_K,
    "tail_if": """\
fn id(c:& C, k: i32) -> SLOT
    if k == 0
        ADDRc
    else
        ADDRc
""" + ID_K,
    "tail_match": """\
fn id(c:& C, k: i32) -> SLOT
    match k
        0 => ADDRc
        _ => ADDRc
""" + ID_K,
    "let_if": """\
fn go(c:& C, k: i32)
    let p: SLOT = if k == 0
        ADDRc
    else
        ADDRc
    p.x = 3
""" + GO_K,
    "let_match": """\
fn go(c:& C, k: i32)
    let p: SLOT = match k
        0 => ADDRc
        _ => ADDRc
    p.x = 3
""" + GO_K,
    "let_match_block": """\
fn go(c:& C, k: i32)
    let p: SLOT = match k
        0 =>
            let q: i32 = 1
            ADDRc
        _ => ADDRc
    p.x = 3
""" + GO_K,
    "arm_beside_a_borrow": """\
fn go(c:& C, k: i32)
    var d: C = C { x: 9, y: 0 }
    let p: SLOT = if k == 0
        ADDRc
    else
        ADDRd
    p.x = 3
""" + GO_K,
    "array_literal": "fn go(c:& C)\n    var a: [1]SLOT = [ADDRc]\n    a[0].x = 3\n" + GO,
    "array_fill": "fn go(c:& C)\n    var a: [2]SLOT = [ADDRc; 2]\n    a[1].x = 3\n" + GO,
    "array_store": "fn go(c:& C)\n    var a: [1]SLOT\n    a[0] = ADDRc\n    a[0].x = 3\n" + GO,
    "tuple": "fn go(c:& C)\n    let t: (SLOT, i32) = (ADDRc, 1)\n    t.0.x = 3\n" + GO,
    "tuple_return": """\
fn id(c:& C) -> (SLOT, i32)
    return (ADDRc, 1)

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let t: (SLOT, i32) = id(@&c)
    t.0.x = 3
    return c.x
""",
    "argument": "fn g(p: SLOT)\n    p.x = 3\n\nfn go(c:& C)\n    g(ADDRc)\n" + GO,
    "through_a_chain": """\
fn inner(c:& C) -> SLOT
    return ADDRc

fn id(c:& C) -> SLOT
    return inner(c)
""" + ID,
    "self_return": """\
impl C
    fn me(self:& C) -> SLOT
        return ADDRself

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: SLOT = c.me()
    p.x = 3
    return c.x
""",
    "bare_self_return": """\
impl C
    fn me(self:&) -> SLOT
        return ADDRself

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: SLOT = c.me()
    p.x = 3
    return c.x
""",
    "self_let": """\
impl C
    fn me(self:& C)
        let p: SLOT = ADDRself
        p.x = 3

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    c.me()
    return c.x
""",
}


def _generic(slot: str, addr: str) -> dict:
    """The generic forms, whose slot is spelled with `T`."""
    generic_slot = slot.replace("C", "T")
    return {
        "generic_return": f"""\
fn id<T>(c:& T) -> {generic_slot}
    return {addr}c

pub fn main() -> i32
    var c: C = C {{ x: 1, y: 0 }}
    let p: {slot} = id<C>(@&c)
    p.x = 3
    return c.x
""",
        "generic_let": f"""\
fn id<T>(c:& T) -> {generic_slot}
    let p: {generic_slot} = {addr}c
    return p

pub fn main() -> i32
    var c: C = C {{ x: 1, y: 0 }}
    let p: {slot} = id<C>(@&c)
    p.x = 3
    return c.x
""",
    }


PROGRAMS = {}
for slot_name, slot, addr in (("mut", "@&C", "@&"), ("ptr", "*C", "@")):
    for shape, program in {**WRITABLE, **_generic(slot, addr)}.items():
        PROGRAMS[f"{shape}_{slot_name}"] = TYPES + program.replace("SLOT", slot).replace("ADDR", addr)

SCALAR_MAIN = """
pub fn main() -> i32
    var n: i32 = 1
    CALL
    return n
"""

PROGRAMS.update({
    # `@T` can't write, so these change the referent and read through it. Not
    # by its name, which the `@T` borrows (§13.5, #2438), but through a `*T`.
    "let_ref": TYPES + "fn go(c:& C) -> i32\n    let w: *C = @c\n    let p: @C = @c\n    w.x = 3\n"
               "    return p.x\n" + READ,
    "var_ref": TYPES + "fn go(c:& C) -> i32\n    let w: *C = @c\n    var p: @C = @c\n    w.x = 3\n"
               "    return p.x\n" + READ,
    "assign_ref": TYPES + """\
fn go(c:& C) -> i32
    var d: C = C { x: 9, y: 0 }
    var p: @C = @d
    p = @c
    c.x = 3
    return p.x
""" + READ,
    "return_ref": TYPES + "fn id(c:& C) -> @C\n    return @c\n" + READ_ID,
    "tail_ref": TYPES + "fn id(c:& C) -> @C\n    @c\n" + READ_ID,
    "field_from_if": TYPES + """\
struct A
    ch: @&C

fn go(c:& C, k: i32)
    var a: A
    a.ch = if k == 0
        @&c
    else
        @&c
    a.ch.x = 3
""" + GO_K,
    "literal_field_from_if": TYPES + """\
struct A
    ch: @&C

fn go(c:& C, k: i32)
    let a: A = A { ch: if k == 0
        @&c
    else
        @&c
    }
    a.ch.x = 3
""" + GO_K,
    "global": TYPES + "var G: *C\n\nfn go(c:& C)\n    G = @c\n    G.x = 3\n" + GO,
    "through_pointer": TYPES + """\
fn go(c:& C)
    var d: C = C { x: 9, y: 0 }
    var p: *C = @d
    var pp: **C = @p
    *pp = @c
    p.x = 3
""" + GO,
    "alias": TYPES + """\
type CR = @&C

fn id(c:& C) -> CR
    return @&c

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: CR = id(@&c)
    p.x = 3
    return c.x
""",
    # A reference to a scalar.
    "scalar_let": "fn f(n:& i32)\n    let p: @&i32 = @&n\n    *p = 3\n"
                  + SCALAR_MAIN.replace("CALL", "f(@&n)"),
    "scalar_var": "fn f(n:& i32)\n    var p: @&i32 = @&n\n    *p = 3\n"
                  + SCALAR_MAIN.replace("CALL", "f(@&n)"),
    "scalar_shared_let": """\
fn f(n:& i32) -> i32
    let w: *i32 = @n
    let p: @i32 = @n
    *w = 3
    return *p

pub fn main() -> i32
    var n: i32 = 1
    return f(@&n)
""",
    "scalar_return": "fn f(n:& i32) -> @&i32\n    return @&n\n"
                     + SCALAR_MAIN.replace("CALL", "let p: @&i32 = f(@&n)\n    *p = 3"),
    "scalar_tail": "fn f(n:& i32) -> @&i32\n    @&n\n"
                   + SCALAR_MAIN.replace("CALL", "let p: @&i32 = f(@&n)\n    *p = 3"),
    "scalar_generic_return": "fn id<T>(c:& T) -> @&T\n    return @&c\n"
                             + SCALAR_MAIN.replace("CALL", "let p: @&i32 = id<i32>(@&n)\n    *p = 3"),
    "scalar_argument": "fn g(p: @&i32)\n    *p = 3\n\nfn f(n:& i32)\n    g(@&n)\n"
                       + SCALAR_MAIN.replace("CALL", "f(@&n)"),
    "float_let": """\
fn f(n:& f64)
    let p: @&f64 = @&n
    *p = 3.0

pub fn main() -> i32
    var n: f64 = 1.0
    f(@&n)
    return n as i32
""",
    "bool_let": """\
fn f(n:& bool)
    let p: @&bool = @&n
    *p = true

pub fn main() -> i32
    var n: bool = false
    f(@&n)
    if n
        return 3
    return 0
""",
    "array_let": """\
fn f(a:& [2]i32)
    let p: @&[2]i32 = @&a
    *p = [1, 3]

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
""",
    "array_return": """\
fn f(a:& [2]i32) -> @&[2]i32
    return @&a

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    let p: @&[2]i32 = f(@&a)
    *p = [1, 3]
    return a[1]
""",
    # `h` has type `*C`, so `@&h` is the `@&*C`: the caller's pointer variable.
    "pointer_referent_let": TYPES + """\
fn go(h:& *C, d: *C)
    let p: @&*C = @&h
    *p = d

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    var q: *C = @c
    go(@&q, @d)
    return q.x
""",
    "pointer_referent_return": TYPES + """\
fn go(h:& *C) -> @&*C
    return @&h

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    var q: *C = @c
    let p: @&*C = go(@&q)
    *p = @d
    return q.x
""",
})

# `c` is a `C`, so a by-value slot copies it.
BY_VALUE = {
    "let": TYPES + """\
fn go(c:& C) -> i32
    let d: C = c
    c.x = 9
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return go(@&c)
""",
    "untyped_let": TYPES + """\
fn go(c:& C) -> i32
    let d = c
    c.x = 9
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return go(@&c)
""",
    "return": TYPES + """\
fn id(c:& C) -> C
    return c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    let d: C = id(@&c)
    c.x = 9
    return d.x
""",
    "if_arm": TYPES + """\
fn go(c:& C, k: i32) -> i32
    let d: C = if k == 0
        c
    else
        c
    c.x = 9
    return d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return go(@&c, 0)
""",
    # `h` has type `*C`, which is what the slot holds.
    "pointer_referent": TYPES + """\
fn go(h:& *C) -> *C
    let p: *C = h
    return p

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var q: *C = @c
    let p: *C = go(@&q)
    return p.x
""",
}

# A reference to the wrong type. `^` is where the reference goes, and the row's
# last item the `@` or `@&` the slot asks for. Bare, it's a value in a reference
# slot, whatever the types. Written out, it's R1's "pointees must be the same
# type" (#2325): exactly the same, not the same width (#2368).
D = "struct D\n    a: i32\n\n"
ANOTHER_POINTEE = {
    "return": (TYPES + D + "fn f(c:& C) -> @D\n    return ^c\n", "@"),
    "tail": (TYPES + D + "fn f(c:& C) -> @D\n    ^c\n", "@"),
    "return_ptr": (TYPES + D + "fn f(c:& C) -> *D\n    return ^c\n", "@"),
    "let": (TYPES + D + "fn f(c:& C) -> i32\n    let p: @D = ^c\n    return 0\n", "@"),
    "var": (TYPES + D + "fn f(c:& C) -> i32\n    var p: @&D = ^c\n    return 0\n", "@&"),
    "assign": (TYPES + D + "fn f(c:& C, p: @&D)\n    var q: @&D = p\n    q = ^c\n", "@&"),
    "arm": (TYPES + D + """\
fn f(c:& C, d: @D, k: i32) -> @D
    if k == 0
        ^c
    else
        d
""", "@"),
    "scalar": ("fn f(n:& i32) -> @i64\n    return ^n\n", "@"),
    "move_only": ("""\
struct D
    a: i32

struct T
    id: i32

impl Drop for T
    fn drop(self: @&T)
        self.id = 0

fn f(t:& T) -> @D
    return ^t
""", "@"),
}
# test_value_into_ref.py's lent_other_struct and lent_other_scalar are these, bare.
ANOTHER_POINTEE_BARE = sorted(set(ANOTHER_POINTEE) - {"return", "scalar"})

MESSAGE = {"@": VALUE_INTO_SHARED_REF, "@&": VALUE_INTO_MUT_REF}

DROP = """\
var DROPS: i32 = 0

struct T
    id: i32

impl Drop for T
    fn drop(self: @&T)
        DROPS = DROPS + 1

"""
DROP_MAIN = """
fn run() -> i32
    var t: T = T { id: 3 }
    return BODY

pub fn main() -> i32
    let id: i32 = run()
    return id * DROPS
"""

# A reference isn't a move: `t` stays the caller's, and is dropped once, there.
MOVE_ONLY = {}
for slot_name, slot, addr in (("mut", "@&T", "@&"), ("ref", "@T", "@"), ("ptr", "*T", "@")):
    returned = DROP_MAIN.replace("return BODY", f"let p: {slot} = id(@&t)\n    return p.id")
    MOVE_ONLY.update({
        f"let_{slot_name}": DROP + f"fn f(t:& T) -> i32\n    let p: {slot} = {addr}t\n    return p.id\n"
                            + DROP_MAIN.replace("BODY", "f(@&t)"),
        f"var_{slot_name}": DROP + f"fn f(t:& T) -> i32\n    var p: {slot} = {addr}t\n    return p.id\n"
                            + DROP_MAIN.replace("BODY", "f(@&t)"),
        f"assign_{slot_name}": DROP + f"""\
fn f(t:& T) -> i32
    var p: {slot}
    p = {addr}t
    return p.id
""" + DROP_MAIN.replace("BODY", "f(@&t)"),
        f"return_{slot_name}": DROP + f"fn id(t:& T) -> {slot}\n    return {addr}t\n" + returned,
        f"tail_{slot_name}": DROP + f"fn id(t:& T) -> {slot}\n    {addr}t\n" + returned,
        f"tail_if_{slot_name}": DROP + f"""\
fn id(t:& T) -> {slot}
    if t.id == 3
        {addr}t
    else
        {addr}t
""" + returned,
        f"let_match_{slot_name}": DROP + f"""\
fn f(t:& T, k: i32) -> i32
    let p: {slot} = match k
        0 => {addr}t
        _ => {addr}t
    return p.id
""" + DROP_MAIN.replace("BODY", "f(@&t, 0)"),
        f"return_in_arm_{slot_name}": DROP + f"""\
fn id(t:& T, k: i32) -> {slot}
    match k
        0 => return {addr}t
        _ => return {addr}t
""" + DROP_MAIN.replace("return BODY", f"let p: {slot} = id(@&t, 0)\n    return p.id"),
        f"array_store_{slot_name}": DROP + f"""\
fn f(t:& T) -> i32
    var a: [1]{slot}
    a[0] = {addr}t
    return a[0].id
""" + DROP_MAIN.replace("BODY", "f(@&t)"),
        f"array_literal_{slot_name}": DROP + f"""\
fn f(t:& T) -> i32
    var a: [1]{slot} = [{addr}t]
    return a[0].id
""" + DROP_MAIN.replace("BODY", "f(@&t)"),
    })

# A by-value slot is a move out of the caller's place.
MOVE_OUT = {
    "return": "fn f(t:& T) -> T\n    return t\n",
    "tail": "fn f(t:& T) -> T\n    t\n",
    "var": "fn f(t:& T) -> i32\n    var u: T = t\n    return u.id\n",
    "untyped_var": "fn f(t:& T) -> i32\n    var u = t\n    return u.id\n",
    "if_arm": """\
fn f(t:& T, k: i32) -> T
    if k == 0
        t
    else
        t
""",
    "assign": "fn f(t:& T, u:= T) -> i32\n    var v: T = u\n    v = t\n    return v.id\n",
    "array_literal": "fn f(t:& T) -> i32\n    var a: [1]T = [t]\n    return a[0].id\n",
}

# §13.5's first rule is checked, and `@c` and `@&c` of a `:&` count as those of
# any place. A `:&` argument is one too: as if written `@&c`.
BORROW_CONFLICTS = {
    "two_mut_lets": ("""\
fn go(c:& C)
    let p: @&C = @&c
    let q: @&C = @&c
    p.x = 2
    q.x = 3
""", "cannot borrow `c` as mutable - `c` is already borrowed as mutable"),
    "mut_var_then_mut_let": ("""\
fn go(c:& C)
    var p: @&C = @&c
    let q: @&C = @&c
    q.x = 3
""", "cannot borrow `c` as mutable - `c` is already borrowed as mutable"),
    "mut_then_untyped": ("""\
fn go(c:& C)
    let p: @&C = @&c
    let q = @&c
    q.x = 3
""", "cannot borrow `c` as mutable - `c` is already borrowed as mutable"),
    "shared_then_mut": ("""\
fn go(c:& C)
    let p: @C = @c
    let q: @&C = @&c
    q.x = 3
""", "cannot borrow `c` as mutable - `c` is already borrowed as immutable"),
    "mut_then_shared": ("""\
fn go(c:& C)
    let p: @&C = @&c
    let q: @C = @c
    p.x = 3
""", "cannot borrow `c` as immutable - `c` is already borrowed as mutable"),
    "from_an_arm": ("""\
fn go(c:& C, k: i32)
    let p: @&C = if k == 0
        @&c
    else
        @&c
    let q: @&C = @&c
    q.x = 3
""", "cannot borrow `c` as mutable - `c` is already borrowed as mutable"),
    "argument_while_bound": ("""\
fn g(p: @&C)
    p.x = 3

fn go(c:& C)
    let p: @&C = @&c
    g(@&c)
""", "cannot borrow `c` as mutable - `c` is already borrowed as mutable"),
    "lent_on_while_bound": ("""\
fn g(m:& C)
    m.x = 3

fn go(c:& C)
    let p: @&C = @&c
    g(c)
""", "cannot borrow `c` as mutable - `c` is already borrowed as mutable"),
    # A write into the place is a mutable borrow of it (LARB ruling R11, #2438).
    "write_beside_a_shared_reference": ("""\
fn go(c:& C)
    let p: @C = @c
    c.x = 3
""", "cannot assign to `c.x` - `c` is already borrowed as immutable"),
}

# What rule 1 doesn't touch.
NO_CONFLICT = {
    "two_shared": TYPES + """\
fn go(c:& C) -> i32
    let p: @C = @c
    let q: @C = @c
    return p.x + q.x

pub fn main() -> i32
    var c: C = C { x: 1, y: 1 }
    return go(@&c) + 1
""",
    "two_raw_pointers": TYPES + """\
fn go(c:& C)
    let p: *C = @c
    let q: *C = @c
    p.x = 2
    q.x = p.x + 1
""" + GO,
}


def _gaps(names, reason):
    return dict.fromkeys(names, reason)


def _both(*shapes):
    return [f"{shape}_{slot}" for shape in shapes for slot in ("mut", "ptr")]


RITZ1_GAPS = {
    **_gaps(["array_fill_mut", "array_literal_mut", "array_store_mut"], ELEMENT_GAP),
    **_gaps(_both("assign_from_if") + ["field_from_if", "literal_field_from_if"], IF_VALUE_GAP),
}

RITZ1_MOVE_ONLY_GAPS = {
    **_gaps(["array_literal_mut", "array_literal_ref", "array_store_mut", "array_store_ref"], ELEMENT_GAP),
}

RITZ1_BY_VALUE_GAPS = {}
RITZ0_NO_CONFLICT_GAPS = {}


def _params(programs, gaps):
    return [pytest.param(name, marks=[pytest.mark.xfail(strict=True, reason=gaps[name])]
                         if name in gaps else [])
            for name in sorted(programs)]


def _refused(comp, ll, message):
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out[-2000:]
    assert not ll.exists()
    assert re.search(r"main\.ritz:\d+:\d+: (error: )?" + re.escape(message), out), out[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_reference_slot_holds_the_written_reference(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, PROGRAMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BY_VALUE))
def test_ritz0_by_value_slot_copies(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, BY_VALUE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MOVE_ONLY))
def test_ritz0_reference_to_a_move_only_referent_drops_once(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, MOVE_ONLY[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MOVE_OUT))
def test_ritz0_by_value_slot_is_still_a_move_out(tmp_path, name):
    program = DROP + MOVE_OUT[name] + """
pub fn main() -> i32
    return 0
"""
    comp, ll, _ = _compile("ritz0", None, tmp_path, name, program)
    assert comp.returncode != 0
    assert "cannot move out of a reference" in comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", ANOTHER_POINTEE_BARE)
def test_a_value_into_a_reference_to_another_type_is_refused(ritz1_bin, tmp_path, compiler, name):
    program, addr = ANOTHER_POINTEE[name]
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, name, program.replace("^", "") + """
pub fn main() -> i32
    return 0
""")
    _refused(comp, ll, MESSAGE[addr])


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ANOTHER_POINTEE))
def test_a_written_reference_to_another_type_is_refused(tmp_path, compiler, name):
    program, addr = ANOTHER_POINTEE[name]
    _assert_refused(compiler, tmp_path, name, program.replace("^", "^" + addr) + """
pub fn main() -> i32
    return 0
""", REF_TO_OTHER_TYPE)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BORROW_CONFLICTS))
def test_ritz0_written_reference_counts_as_a_borrow(tmp_path, name):
    body, message = BORROW_CONFLICTS[name]
    entry = GO_K if "k: i32" in body else GO
    comp, ll, _ = _compile("ritz0", None, tmp_path, name, TYPES + body + entry)
    assert comp.returncode != 0
    assert message in comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(NO_CONFLICT, RITZ0_NO_CONFLICT_GAPS))
def test_ritz0_conflicts_only_with_a_borrow(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, NO_CONFLICT[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(PROGRAMS, RITZ1_GAPS))
def test_ritz1_reference_slot_holds_the_written_reference(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, PROGRAMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(BY_VALUE, RITZ1_BY_VALUE_GAPS))
def test_ritz1_by_value_slot_copies(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, BY_VALUE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(MOVE_ONLY, RITZ1_MOVE_ONLY_GAPS))
def test_ritz1_reference_to_a_move_only_referent_drops_once(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, MOVE_ONLY[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NO_CONFLICT))
def test_ritz1_conflicts_only_with_a_borrow(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, NO_CONFLICT[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BORROW_CONFLICTS))
def test_ritz1_written_reference_counts_as_a_borrow(ritz1_bin, tmp_path, name):
    body, message = BORROW_CONFLICTS[name]
    entry = GO_K if "k: i32" in body else GO
    comp, _, _ = _compile("ritz1", ritz1_bin, tmp_path, name, TYPES + body + entry)
    assert comp.returncode != 0
    assert message in comp.stdout + comp.stderr


# AGAST #2950: an if / match's value has one LLVM type on ritz1.  An `@&c` arm
# is a `ptr` there and a `*C` one an i64, so an arm of each meets in one model;
# a `ptr` value leaves a `-> *C` fn as an i64; and a `*r` arm is the struct
# (READS in test_ref_into_value.py has the statement forms, this the value one).
ARM_MODELS = {
    "mixed_let_if": TYPES + """\
fn go(c:& C, q: *C, k: i32)
    let p: @&C = if k == 0
        @&c
    else
        q
    p.x = 3

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 1, y: 0 }
    go(@&c, @d, 0)
    go(@&c, @d, 1)
    return c.x * d.x - 6
""",
    "mixed_tail_match": TYPES + """\
fn pick(c:& C, q: *C, k: i32) -> @&C
    match k
        0 => q
        _ => @&c

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    let p: @&C = pick(@&c, @d, 0)
    let r: @&C = pick(@&c, @d, 1)
    return p.x * r.x
""",
    "mixed_tail_if": TYPES + """\
fn pick(c:& C, q: *C, k: i32) -> @&C
    if k == 0
        @&c
    else
        q

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    let p: @&C = pick(@&c, @d, 1)
    let r: @&C = pick(@&c, @d, 0)
    r.x = 1
    return p.x * r.x
""",
    "pointer_tail_if": TYPES + """\
fn raw(c:& C, k: i32) -> *C
    if k == 0
        @&c
    else
        @&c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    let q: *C = raw(@&c, 0)
    return q.x
""",
    "pointer_tail_match": TYPES + """\
fn raw(c:& C, k: i32) -> *C
    match k
        0 => @&c
        _ => @&c

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    let q: *C = raw(@&c, 1)
    return q.x
""",
    # AGAST #2960: an un-annotated `let` of an all-`@&x` if / match holds an
    # `@&C`, as `let p = @&c` does, so `p.x` reaches C.
    "untyped_let_if": TYPES + """\
fn go(c:& C, k: i32)
    let p = if k == 0
        @&c
    else
        @&c
    p.x = p.x + 1

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    go(@&c, 0)
    go(@&c, 1)
    return c.x
""",
    "untyped_let_match": TYPES + """\
fn go(c:& C, k: i32)
    let p = match k
        0 => @&c
        _ => @&c
    p.x = p.x + 1

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    go(@&c, 0)
    go(@&c, 1)
    return c.x
""",
    "untyped_let_if_locals": TYPES + """\
pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 1, y: 0 }
    let k: i32 = 1
    let p = if k == 0
        @&c
    else
        @&d
    p.x = 2
    return c.x + d.x
""",
    "untyped_let_if_field_and_ref": TYPES + """\
struct W
    c: C

fn go(w:& W, r: @&C, k: i32)
    let p = if k == 0
        @&w.c
    else
        r
    p.x = p.x + 1

pub fn main() -> i32
    var w: W = W { c: C { x: 1, y: 0 } }
    var d: C = C { x: 1, y: 0 }
    go(@&w, @&d, 0)
    go(@&w, @&d, 1)
    return w.c.x + d.x - 1
""",
    "deref_let_if": TYPES + """\
fn f(r: @C, k: i32) -> i32
    let d: C = if k == 0
        *r
    else
        *r
    d.x

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    return f(@c, 0)
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(ARM_MODELS))
def test_an_arm_value_takes_the_phi_model(ritz1_bin, tmp_path, compiler, name):
    assert _run(compiler, ritz1_bin, tmp_path, name, ARM_MODELS[name]) == 3


# A variant payload is a reference slot like any other.
VARIANTS = {
    "own_enum": TYPES + """\
enum E
    Full(@&C)
    Nope

fn go(c:& C)
    let e: E = E.Full(@&c)
    match e
        Full(p) => p.x = 3
        Nope => pass
""" + GO,
    "option": "import ritzlib.option\n" + TYPES + """\
fn go(c:& C)
    let o: Option<@&C> = Some(@&c)
    match o
        Some(p) => p.x = 3
        None => pass
""" + GO,
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", [
    "ritz0", pytest.param("ritz1", marks=pytest.mark.xfail(strict=True, reason=PAYLOAD_GAP))])
@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_variant_payload_holds_the_written_reference(ritz1_bin, tmp_path, compiler, name):
    assert _run(compiler, ritz1_bin, tmp_path, name, VARIANTS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("slot", ["let a: @dyn Animal = c", "var a: @dyn Animal = c"])
def test_ritz0_value_into_a_trait_object_reference_is_located_and_refused(tmp_path, slot):
    """`@dyn Animal` is a reference, so a `Dog` doesn't fit it. `let` used to bind
    a `Dog` there, and a call through it raised a raw TypeError. What `dyn` should
    do at all is #1620's."""
    program = f"""\
trait Animal
    fn speak(self: *Self) -> i32

struct Dog
    age: i32

impl Animal for Dog
    fn speak(self: *Self) -> i32
        return 3

fn go(c:& Dog) -> i32
    {slot}
    return 0

pub fn main() -> i32
    return 0
"""
    comp, ll, _ = _compile("ritz0", None, tmp_path, "dyn_slot", program)
    _refused(comp, ll, VALUE_INTO_SHARED_REF)


# AGAST #2311: ritz0 refused this ("cannot store i64 to [2 x i32]*") until #2330
# made its store stride T, as its read does (LARB R9).
@pytest.mark.integration
def test_ritz0_index_through_a_reference_to_an_array(tmp_path):
    program = """\
fn f(a:& [2]i32)
    let p: @&[2]i32 = @&a
    p[1] = 3

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
"""
    assert _run("ritz0", None, tmp_path, "index", program) == 3


# `*c` says the value, and a value doesn't fit a reference slot.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_deref_into_a_reference_is_refused(ritz1_bin, tmp_path, compiler):
    program = TYPES + "fn go(c:& C)\n    let p: @&C = *c\n    p.x = 3\n" + GO
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, "deref", program)
    _refused(comp, ll, VALUE_INTO_MUT_REF)


# A cast isn't a borrow either: `c as @&C` is the bare form with a type on it.
BARE_CASTS = {
    "mut": ("fn go(c:& C)\n    let p: @&C = c as @&C\n    p.x = 3\n", VALUE_INTO_MUT_REF),
    "ptr": ("fn go(c:& C)\n    let p: *C = c as *C\n    p.x = 3\n", VALUE_INTO_SHARED_REF),
}


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason=CAST_GAP)
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(BARE_CASTS))
def test_a_value_cast_to_a_reference_is_refused(ritz1_bin, tmp_path, compiler, name):
    body, message = BARE_CASTS[name]
    comp, ll, _ = _compile(compiler, ritz1_bin, tmp_path, name, TYPES + body + GO)
    _refused(comp, ll, message)
