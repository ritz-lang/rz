"""AGAST #2249: a `name:& T` parameter landing in a reference slot.

    fn go(c:& C)
        let p: @&C = c      # p was a copy of `C`, or `cannot store %C to %C**`

    fn id(c:& C) -> @&C
        return c            # `ret %C %x` from a fn returning `%C*`: invalid IR

A `:&` parameter reads as its referent, so a slot that holds a reference has to
take the borrow's pointer instead. #1302 did that for fields. This does it for
every other slot, in every position a value reaches one from: `let`, `var`,
`return`, a tail, `=`, a cast, an `if`/`match` arm of any of those, and an
element of an array or tuple literal.

Every program returns 3 on success and writes through the reference after it
was bound, or reads through it after the referent changed, so a pointer to a
temporary copy can't pass.

`*i32` isn't here: `n:& i32` into a `*T` of a scalar is #2280's, which hasn't
decided between taking the pointer and rejecting it. BOTH_GAPS in
test_borrow_param_ref_field.py pins that.
"""

import re

import pytest

from test_borrow_param_ref_field import _compile, _run

CLOSED_GAP = "AGAST #2309: ritz1 can't take a `:&` into a reference from here"
NOT_CHECKED_GAP = "AGAST #2310: ritz1 doesn't hold a reference to a `:&` param to these rules"
NO_TUPLES_GAP = "AGAST #1526: ritz1 has no tuples"
BY_VALUE_ARM_GAP = "AGAST #2288: ritz1 can't read a `:&` by value in an arm"

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

# Each takes the slot's spelling, `@&C` or `*C`.
WRITABLE = {
    "let": "fn go(c:& C)\n    let p: SLOT = c\n    p.x = 3\n" + GO,
    "var": "fn go(c:& C)\n    var p: SLOT = c\n    p.x = 3\n" + GO,
    "grouped": "fn go(c:& C)\n    let p: SLOT = (c)\n    p.x = 3\n" + GO,
    "cast": "fn go(c:& C)\n    let p: SLOT = c as SLOT\n    p.x = 3\n" + GO,
    "assign": """\
fn go(c:& C)
    var d: C = C { x: 9, y: 0 }
    var p: SLOT = @&d
    p = c
    p.x = 3
""" + GO,
    "assign_in_arm": """\
fn go(c:& C, k: i32)
    var d: C = C { x: 9, y: 0 }
    var p: SLOT = @&d
    match k
        0 => p = c
        _ => pass
    p.x = 3
""" + GO_K,
    "assign_from_if": """\
fn go(c:& C, k: i32)
    var d: C = C { x: 9, y: 0 }
    var p: SLOT = @&d
    p = if k == 0
        c
    else
        c
    p.x = 3
""" + GO_K,
    "return": "fn id(c:& C) -> SLOT\n    return c\n" + ID,
    "return_grouped": "fn id(c:& C) -> SLOT\n    return (c)\n" + ID,
    "tail": "fn id(c:& C) -> SLOT\n    c\n" + ID,
    "return_in_if": """\
fn id(c:& C) -> SLOT
    if c.y == 0
        return c
    return c
""" + ID,
    "return_in_arm": """\
fn id(c:& C, k: i32) -> SLOT
    match k
        0 => return c
        _ => return c
""" + ID_K,
    "tail_if": """\
fn id(c:& C, k: i32) -> SLOT
    if k == 0
        c
    else
        c
""" + ID_K,
    "tail_match": """\
fn id(c:& C, k: i32) -> SLOT
    match k
        0 => c
        _ => c
""" + ID_K,
    "let_if": """\
fn go(c:& C, k: i32)
    let p: SLOT = if k == 0
        c
    else
        c
    p.x = 3
""" + GO_K,
    "let_match": """\
fn go(c:& C, k: i32)
    let p: SLOT = match k
        0 => c
        _ => c
    p.x = 3
""" + GO_K,
    "let_match_block": """\
fn go(c:& C, k: i32)
    let p: SLOT = match k
        0 =>
            let q: i32 = 1
            c
        _ => c
    p.x = 3
""" + GO_K,
    "arm_beside_a_borrow": """\
fn go(c:& C, k: i32)
    var d: C = C { x: 9, y: 0 }
    let p: SLOT = if k == 0
        c
    else
        @&d
    p.x = 3
""" + GO_K,
    "array_literal": "fn go(c:& C)\n    var a: [1]SLOT = [c]\n    a[0].x = 3\n" + GO,
    "array_fill": "fn go(c:& C)\n    var a: [2]SLOT = [c; 2]\n    a[1].x = 3\n" + GO,
    "array_store": "fn go(c:& C)\n    var a: [1]SLOT\n    a[0] = c\n    a[0].x = 3\n" + GO,
    "tuple": "fn go(c:& C)\n    let t: (SLOT, i32) = (c, 1)\n    t.0.x = 3\n" + GO,
    "tuple_return": """\
fn id(c:& C) -> (SLOT, i32)
    return (c, 1)

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let t: (SLOT, i32) = id(@&c)
    t.0.x = 3
    return c.x
""",
    "argument": "fn g(p: SLOT)\n    p.x = 3\n\nfn go(c:& C)\n    g(c)\n" + GO,
    "through_a_chain": """\
fn inner(c:& C) -> SLOT
    return c

fn id(c:& C) -> SLOT
    return inner(c)
""" + ID,
    "self_return": """\
impl C
    fn me(self:& C) -> SLOT
        return self

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: SLOT = c.me()
    p.x = 3
    return c.x
""",
    "bare_self_return": """\
impl C
    fn me(self:&) -> SLOT
        return self

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: SLOT = c.me()
    p.x = 3
    return c.x
""",
    "self_let": """\
impl C
    fn me(self:& C)
        let p: SLOT = self
        p.x = 3

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    c.me()
    return c.x
""",
}


def _generic(slot: str) -> dict:
    """The generic forms, whose slot is spelled with `T`."""
    generic_slot = slot.replace("C", "T")
    return {
        "generic_return": f"""\
fn id<T>(c:& T) -> {generic_slot}
    return c

pub fn main() -> i32
    var c: C = C {{ x: 1, y: 0 }}
    let p: {slot} = id<C>(@&c)
    p.x = 3
    return c.x
""",
        "generic_let": f"""\
fn id<T>(c:& T) -> {generic_slot}
    let p: {generic_slot} = c
    return p

pub fn main() -> i32
    var c: C = C {{ x: 1, y: 0 }}
    let p: {slot} = id<C>(@&c)
    p.x = 3
    return c.x
""",
    }


PROGRAMS = {}
for slot_name, slot in (("mut", "@&C"), ("ptr", "*C")):
    for shape, program in {**WRITABLE, **_generic(slot)}.items():
        PROGRAMS[f"{shape}_{slot_name}"] = TYPES + program.replace("SLOT", slot)

SCALAR_MAIN = """
pub fn main() -> i32
    var n: i32 = 1
    CALL
    return n
"""

PROGRAMS.update({
    # `@T` can't write, so these change the referent and read through it.
    "let_ref": TYPES + "fn go(c:& C) -> i32\n    let p: @C = c\n    c.x = 3\n    return p.x\n" + READ,
    "var_ref": TYPES + "fn go(c:& C) -> i32\n    var p: @C = c\n    c.x = 3\n    return p.x\n" + READ,
    "assign_ref": TYPES + """\
fn go(c:& C) -> i32
    var d: C = C { x: 9, y: 0 }
    var p: @C = @d
    p = c
    c.x = 3
    return p.x
""" + READ,
    "return_ref": TYPES + "fn id(c:& C) -> @C\n    return c\n" + READ_ID,
    "tail_ref": TYPES + "fn id(c:& C) -> @C\n    c\n" + READ_ID,
    "field_from_if": TYPES + """\
struct A
    ch: @&C

fn go(c:& C, k: i32)
    var a: A
    a.ch = if k == 0
        c
    else
        c
    a.ch.x = 3
""" + GO_K,
    "literal_field_from_if": TYPES + """\
struct A
    ch: @&C

fn go(c:& C, k: i32)
    let a: A = A { ch: if k == 0
        c
    else
        c
    }
    a.ch.x = 3
""" + GO_K,
    "global": TYPES + "var G: *C\n\nfn go(c:& C)\n    G = c\n    G.x = 3\n" + GO,
    "through_pointer": TYPES + """\
fn go(c:& C)
    var d: C = C { x: 9, y: 0 }
    var p: *C = @&d
    var pp: **C = @&p
    *pp = c
    p.x = 3
""" + GO,
    "alias": TYPES + """\
type CR = @&C

fn id(c:& C) -> CR
    return c

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    let p: CR = id(@&c)
    p.x = 3
    return c.x
""",
    # A reference to a scalar: not #2280, which is `*i32`.
    "scalar_let": "fn f(n:& i32)\n    let p: @&i32 = n\n    *p = 3\n"
                  + SCALAR_MAIN.replace("CALL", "f(@&n)"),
    "scalar_var": "fn f(n:& i32)\n    var p: @&i32 = n\n    *p = 3\n"
                  + SCALAR_MAIN.replace("CALL", "f(@&n)"),
    "scalar_shared_let": """\
fn f(n:& i32) -> i32
    let p: @i32 = n
    n = 3
    return *p

pub fn main() -> i32
    var n: i32 = 1
    return f(@&n)
""",
    "scalar_return": "fn f(n:& i32) -> @&i32\n    return n\n"
                     + SCALAR_MAIN.replace("CALL", "let p: @&i32 = f(@&n)\n    *p = 3"),
    "scalar_tail": "fn f(n:& i32) -> @&i32\n    n\n"
                   + SCALAR_MAIN.replace("CALL", "let p: @&i32 = f(@&n)\n    *p = 3"),
    "scalar_generic_return": "fn id<T>(c:& T) -> @&T\n    return c\n"
                             + SCALAR_MAIN.replace("CALL", "let p: @&i32 = id<i32>(@&n)\n    *p = 3"),
    "scalar_argument": "fn g(p: @&i32)\n    *p = 3\n\nfn f(n:& i32)\n    g(n)\n"
                       + SCALAR_MAIN.replace("CALL", "f(@&n)"),
    "float_let": """\
fn f(n:& f64)
    let p: @&f64 = n
    *p = 3.0

pub fn main() -> i32
    var n: f64 = 1.0
    f(@&n)
    return n as i32
""",
    "bool_let": """\
fn f(n:& bool)
    let p: @&bool = n
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
    let p: @&[2]i32 = a
    *p = [1, 3]

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
""",
    "array_return": """\
fn f(a:& [2]i32) -> @&[2]i32
    return a

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    let p: @&[2]i32 = f(@&a)
    *p = [1, 3]
    return a[1]
""",
    # `h` reads as a `*C`, so a `@&*C` holds the borrow and a `*C` holds `h`.
    "pointer_referent_let": TYPES + """\
fn go(h:& *C, d: *C)
    let p: @&*C = h
    *p = d

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    var q: *C = @&c
    go(@&q, @&d)
    return q.x
""",
    "pointer_referent_return": TYPES + """\
fn go(h:& *C) -> @&*C
    return h

pub fn main() -> i32
    var c: C = C { x: 1, y: 0 }
    var d: C = C { x: 3, y: 0 }
    var q: *C = @&c
    let p: @&*C = go(@&q)
    *p = @&d
    return q.x
""",
})

# None of these lands in a reference, so all of them still read the referent.
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
    # The name in the slot is a new binding, not the parameter.
    "shadowed": TYPES + """\
fn go(c:& C) -> @C
    let c: *C = @&G
    return c

var G: C

pub fn main() -> i32
    var c: C = C { x: 9, y: 0 }
    G.x = 3
    let p: @C = go(@&c)
    return p.x
""",
    # A `let` takes the name out of the emitter's locals, a `var` replaces it.
    "shadowed_by_var": TYPES + """\
fn go(c:& C) -> @C
    var c: *C = @&G
    return c

var G: C

pub fn main() -> i32
    var c: C = C { x: 9, y: 0 }
    G.x = 3
    let p: @C = go(@&c)
    return p.x
""",
    "shadowed_in_arm": TYPES + """\
fn go(c:& C, k: i32) -> *C
    if k == 0
        let c: *C = @&G
        c
    else
        c

var G: C

pub fn main() -> i32
    var c: C = C { x: 9, y: 0 }
    G.x = 3
    let p: *C = go(@&c, 0)
    return p.x
""",
    # `h` reads as the `*C` the slot wants.
    "pointer_referent": TYPES + """\
fn go(h:& *C) -> *C
    let p: *C = h
    return p

pub fn main() -> i32
    var c: C = C { x: 3, y: 0 }
    var q: *C = @&c
    let p: *C = go(@&q)
    return p.x
""",
}

# A referent of the wrong type. A return used to reach clang as invalid IR, and
# a binding silently kept the `C`, which only a read of a `D` field exposed.
D = "struct D\n    a: i32\n\n"
ANOTHER_POINTEE = {
    "return": TYPES + D + "fn f(c:& C) -> @D\n    return c\n",
    "tail": TYPES + D + "fn f(c:& C) -> @D\n    c\n",
    "return_ptr": TYPES + D + "fn f(c:& C) -> *D\n    return c\n",
    "let": TYPES + D + "fn f(c:& C) -> i32\n    let p: @D = c\n    return 0\n",
    "var": TYPES + D + "fn f(c:& C) -> i32\n    var p: @&D = c\n    return 0\n",
    "assign": TYPES + D + "fn f(c:& C, p: @&D)\n    var q: @&D = p\n    q = c\n",
    "arm": TYPES + D + """\
fn f(c:& C, d: @D, k: i32) -> @D
    if k == 0
        c
    else
        d
""",
    "scalar": "fn f(n:& i32) -> @i64\n    return n\n",
    "move_only": """\
struct D
    a: i32

struct T
    id: i32

impl Drop for T
    fn drop(self: @&T)
        self.id = 0

fn f(t:& T) -> @D
    return t
""",
}

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

# A reborrow isn't a move: `t` stays the caller's, and is dropped once, there.
MOVE_ONLY = {}
for slot_name, slot in (("mut", "@&T"), ("ref", "@T"), ("ptr", "*T")):
    returned = DROP_MAIN.replace("return BODY", f"let p: {slot} = id(@&t)\n    return p.id")
    MOVE_ONLY.update({
        f"let_{slot_name}": DROP + f"fn f(t:& T) -> i32\n    let p: {slot} = t\n    return p.id\n"
                            + DROP_MAIN.replace("BODY", "f(@&t)"),
        f"var_{slot_name}": DROP + f"fn f(t:& T) -> i32\n    var p: {slot} = t\n    return p.id\n"
                            + DROP_MAIN.replace("BODY", "f(@&t)"),
        f"assign_{slot_name}": DROP + f"""\
fn f(t:& T) -> i32
    var p: {slot}
    p = t
    return p.id
""" + DROP_MAIN.replace("BODY", "f(@&t)"),
        f"return_{slot_name}": DROP + f"fn id(t:& T) -> {slot}\n    return t\n" + returned,
        f"tail_{slot_name}": DROP + f"fn id(t:& T) -> {slot}\n    t\n" + returned,
        f"tail_if_{slot_name}": DROP + f"""\
fn id(t:& T) -> {slot}
    if t.id == 3
        t
    else
        t
""" + returned,
        f"let_match_{slot_name}": DROP + f"""\
fn f(t:& T, k: i32) -> i32
    let p: {slot} = match k
        0 => t
        _ => t
    return p.id
""" + DROP_MAIN.replace("BODY", "f(@&t, 0)"),
        f"return_in_arm_{slot_name}": DROP + f"""\
fn id(t:& T, k: i32) -> {slot}
    match k
        0 => return t
        _ => return t
""" + DROP_MAIN.replace("return BODY", f"let p: {slot} = id(@&t, 0)\n    return p.id"),
        f"array_store_{slot_name}": DROP + f"""\
fn f(t:& T) -> i32
    var a: [1]{slot}
    a[0] = t
    return a[0].id
""" + DROP_MAIN.replace("BODY", "f(@&t)"),
        f"array_literal_{slot_name}": DROP + f"""\
fn f(t:& T) -> i32
    var a: [1]{slot} = [t]
    return a[0].id
""" + DROP_MAIN.replace("BODY", "f(@&t)"),
    })

# A by-value slot is still a move out of what the caller lent.
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

# §13.5's first rule is checked, and `let p: @&C = c` is `let p = @&c` spelled
# without the `@&`. These were only stopped by the store failing.
BORROW_CONFLICTS = {
    "two_mut_lets": ("""\
fn go(c:& C)
    let p: @&C = c
    let q: @&C = c
    p.x = 2
    q.x = 3
""", "cannot borrow `c` as mutable - already borrowed as mutable"),
    "mut_var_then_mut_let": ("""\
fn go(c:& C)
    var p: @&C = c
    let q: @&C = c
    q.x = 3
""", "cannot borrow `c` as mutable - already borrowed as mutable"),
    "mut_then_explicit": ("""\
fn go(c:& C)
    let p: @&C = c
    let q = @&c
    q.x = 3
""", "cannot borrow `c` as mutable - already borrowed as mutable"),
    "shared_then_mut": ("""\
fn go(c:& C)
    let p: @C = c
    let q: @&C = c
    q.x = 3
""", "cannot borrow `c` as mutable - already borrowed as immutable"),
    "mut_then_shared": ("""\
fn go(c:& C)
    let p: @&C = c
    let q: @C = c
    p.x = 3
""", "cannot borrow `c` as immutable - already borrowed as mutable"),
    "from_an_arm": ("""\
fn go(c:& C, k: i32)
    let p: @&C = if k == 0
        c
    else
        c
    let q: @&C = c
    q.x = 3
""", "cannot borrow `c` as mutable - already borrowed as mutable"),
}

# What rule 1 doesn't touch.
NO_CONFLICT = {
    "two_shared": TYPES + """\
fn go(c:& C) -> i32
    let p: @C = c
    let q: @C = c
    return p.x + q.x

pub fn main() -> i32
    var c: C = C { x: 1, y: 1 }
    return go(@&c) + 1
""",
    # A raw pointer isn't a borrow, as `let p: *C = @&c` is not when spelled
    # `let p: *C = c`: nothing tracks it.
    "two_raw_pointers": TYPES + """\
fn go(c:& C)
    let p: *C = c
    let q: *C = c
    p.x = 2
    q.x = p.x + 1
""" + GO,
    "raw_pointer_then_mut_reference": TYPES + """\
fn go(c:& C)
    let p: *C = c
    let q: @&C = c
    q.x = 2
    p.x = q.x + 1
""" + GO,
    "write_beside_a_shared_reference": TYPES + """\
fn go(c:& C) -> i32
    let p: @C = c
    c.x = 3
    return p.x
""" + READ,
    "lent_on_while_bound": TYPES + """\
fn g(p: @&C)
    p.x = 3

fn go(c:& C)
    let p: @&C = c
    g(c)
""" + GO,
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_reference_slot_takes_the_borrow(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, PROGRAMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BY_VALUE))
def test_ritz0_by_value_slot_still_reads_the_referent(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, BY_VALUE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MOVE_ONLY))
def test_ritz0_reborrow_of_a_move_only_referent_drops_once(tmp_path, name):
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
@pytest.mark.parametrize("name", sorted(ANOTHER_POINTEE))
def test_ritz0_reference_to_another_type_is_located_and_refused(tmp_path, name):
    program = ANOTHER_POINTEE[name] + """
pub fn main() -> i32
    return 0
"""
    comp, ll, _ = _compile("ritz0", None, tmp_path, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0
    assert not ll.exists()
    assert re.search(r"main\.ritz:\d+:\d+.*a `[cnt]:&` parameter can't", out), out[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BORROW_CONFLICTS))
def test_ritz0_reborrow_binding_counts_as_a_borrow(tmp_path, name):
    body, message = BORROW_CONFLICTS[name]
    entry = GO_K if "k: i32" in body else GO
    comp, ll, _ = _compile("ritz0", None, tmp_path, name, TYPES + body + entry)
    assert comp.returncode != 0
    assert message in comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NO_CONFLICT))
def test_ritz0_reborrow_conflicts_only_with_a_borrow(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, NO_CONFLICT[name]) == 3


def _gaps(names, reason):
    return dict.fromkeys(names, reason)


def _both(*shapes):
    return [f"{shape}_{slot}" for shape in shapes for slot in ("mut", "ptr")]


RITZ1_GAPS = {
    **_gaps(_both("arm_beside_a_borrow", "array_fill", "array_literal", "array_store",
                  "assign_from_if", "let_if", "let_match", "let_match_block",
                  "tail_if", "tail_match")
            + ["assign_in_arm_mut", "assign_mut", "bare_self_return_mut",
               "field_from_if", "global", "literal_field_from_if", "return_in_arm_mut",
               "self_return_mut", "through_a_chain_mut"], CLOSED_GAP),
    **_gaps(_both("tuple", "tuple_return"), NO_TUPLES_GAP),
}

RITZ1_MOVE_ONLY_GAPS = _gaps(
    [f"{shape}_{slot}" for shape in ("array_literal", "array_store", "let_match", "tail_if")
     for slot in ("mut", "ref", "ptr")] + ["assign_mut", "return_in_arm_mut"], CLOSED_GAP)

RITZ1_BY_VALUE_GAPS = {"if_arm": BY_VALUE_ARM_GAP}


def _params(programs, gaps):
    return [pytest.param(name, marks=[pytest.mark.xfail(strict=True, reason=gaps[name])]
                         if name in gaps else [])
            for name in sorted(programs)]


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(PROGRAMS, RITZ1_GAPS))
def test_ritz1_reference_slot_takes_the_borrow(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, PROGRAMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(BY_VALUE, RITZ1_BY_VALUE_GAPS))
def test_ritz1_by_value_slot_still_reads_the_referent(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, BY_VALUE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(MOVE_ONLY, RITZ1_MOVE_ONLY_GAPS))
def test_ritz1_reborrow_of_a_move_only_referent_drops_once(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, MOVE_ONLY[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(NO_CONFLICT))
def test_ritz1_reborrow_conflicts_only_with_a_borrow(ritz1_bin, tmp_path, name):
    assert _run("ritz1", ritz1_bin, tmp_path, name, NO_CONFLICT[name]) == 3


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason=NOT_CHECKED_GAP)
@pytest.mark.parametrize("name", sorted(set(BORROW_CONFLICTS) - {"mut_then_explicit"}))
def test_ritz1_reborrow_binding_counts_as_a_borrow(ritz1_bin, tmp_path, name):
    body, message = BORROW_CONFLICTS[name]
    entry = GO_K if "k: i32" in body else GO
    comp, _, _ = _compile("ritz1", ritz1_bin, tmp_path, name, TYPES + body + entry)
    assert comp.returncode != 0
    assert message in comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("name", _params(ANOTHER_POINTEE, _gaps(set(ANOTHER_POINTEE) - {"scalar"}, NOT_CHECKED_GAP)))
def test_ritz1_reference_to_another_type_is_refused(ritz1_bin, tmp_path, name):
    program = ANOTHER_POINTEE[name] + """
pub fn main() -> i32
    return 0
"""
    comp, _, _ = _compile("ritz1", ritz1_bin, tmp_path, name, program)
    assert comp.returncode != 0


# A variant payload is the one slot left: the constructors read their arguments
# before anything knows the payload's type.
VARIANT_GAPS = {
    "own_enum": TYPES + """\
enum E
    Full(@&C)
    Nope

fn go(c:& C)
    let e: E = E.Full(c)
    match e
        Full(p) => p.x = 3
        Nope => pass
""" + GO,
    "option": "import ritzlib.option\n" + TYPES + """\
fn go(c:& C)
    let o: Option<@&C> = Some(c)
    match o
        Some(p) => p.x = 3
        None => pass
""" + GO,
}


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2312: a variant payload reads the referent")
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(VARIANT_GAPS))
def test_variant_payload_takes_the_borrow(ritz1_bin, tmp_path, compiler, name):
    assert _run(compiler, ritz1_bin, tmp_path, name, VARIANT_GAPS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("slot", ["let a: @dyn Animal = c", "var a: @dyn Animal = c"])
def test_ritz0_reference_to_a_trait_object_is_located_and_refused(tmp_path, slot):
    """`@dyn Animal` is a `%dyn.Animal*`, so a `Dog` can't lend to it. `let` used
    to bind a `Dog` there, and a call through it raised a raw TypeError. What
    `dyn` should do at all is #1620's."""
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
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0
    assert not ll.exists()
    assert re.search(r"main\.ritz:\d+:\d+.*a `c:&` parameter can't", out), out[-2000:]


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2313: ritz0 writes `ret %T` from a `-> @T`")
@pytest.mark.parametrize("tail", ["return t", "t"])
def test_ritz0_by_value_local_returned_as_a_reference_is_refused(tmp_path, tail):
    """No `:&` here, so nothing lends: the value has no reference to give."""
    program = TYPES + f"""\
fn f() -> @C
    let t: C = C {{ x: 3, y: 0 }}
    {tail}

pub fn main() -> i32
    return f().x
"""
    comp, ll, _ = _compile("ritz0", None, tmp_path, "local_ret", program)
    assert comp.returncode != 0
    assert not ll.exists()


@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2311: `p[i]` through a `@&[N]T`")
def test_ritz0_index_through_a_reference_to_an_array(tmp_path):
    program = """\
fn f(a:& [2]i32)
    let p: @&[2]i32 = a
    p[1] = 3

pub fn main() -> i32
    var a: [2]i32 = [1, 1]
    f(@&a)
    return a[1]
"""
    assert _run("ritz0", None, tmp_path, "index", program) == 3


# `*c` says the value, so this is a by-value read landing in a reference, not a
# bare `:&`: whether that's a borrow or an error is #2227's, for every `*p`.
@pytest.mark.integration
@pytest.mark.xfail(strict=True, reason="AGAST #2227: is `*p` into a reference an implicit borrow?")
def test_ritz0_deref_into_a_reference(tmp_path):
    program = TYPES + "fn go(c:& C)\n    let p: @&C = *c\n    p.x = 3\n" + GO
    assert _run("ritz0", None, tmp_path, "deref", program) == 3
