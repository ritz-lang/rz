"""Free counts for the ownership model in LANGUAGE_SPEC §13 (AGAST #2156, #1854).

#1854 decided the model (option (a)): a type is move-only iff it implements
`Drop` or contains a move-only field; every other type copies. The compiler
drops an owned binding at the end of its block, before `return`, on
`break`/`continue` and before reassigning it, in reverse declaration order,
and never drops a moved-from binding.

Every program below uses one instrumented `Drop` type, `Tracked`, whose
`drop` bumps a global counter (`DROPS`) and appends its id to a second one
(`ORDER`). The program's exit status encodes the counts it observed. The
expected statuses come from the spec, not from what a compiler does today.

The first gaps these programs exposed are closed: ritz0's by AGAST #2157,
ritz1 / ritz1_selfhosted's by AGAST #2158 (ritz1/src/ownership.ritz). AGAST
#2161 added enum payloads, array and tuple elements, temporaries and moves
inside loops, closed for ritz0; ritz1's by AGAST #2165, except tuple
elements (#1526, ritz1's missing tuple literals: #2956 added tuple
types and literals, and #3005 typed a tuple with no tuple type, closing
most of those rows; the rest cite their own tickets).
AGAST #2168 added moves out of a field, closed for ritz1; ritz0's by AGAST
#2171. AGAST #2174 added a match owning its scrutinee, with payload
bindings owning the payload, closed for ritz1; ritz0's by AGAST #2177.
AGAST #2173 added assigning a move-only field (the old value drops),
closed for both. AGAST #2257 added bindings and temporaries from a method
call; ritz1 drops their temporaries since #2262. AGAST
#2243 added bindings from a field, which ritz1 already got right. AGAST
#2244 added moves out of a tuple element, closed for ritz0; for ritz1 by
#2956 / #3005, except the rows citing their own tickets.
AGAST #2261 closed ritz0's double evaluation of a method receiver, which
dropped two values for one call.
AGAST #2242 closed moves out of a nested field for ritz1, and AGAST #2319
the 31-path cap it had per binding.
AGAST #2266 closed ritz1's array literals: an element moves in, a literal
nobody takes drops its elements, and an unannotated literal of a struct is
`[N]T`.
A new gap goes in as a gap ticket on its row, a strict xfail: the table's
test fails if the row passes, so the room that closes it has to flip it.

AGAST #2159 turned the model on the standard library's two owning types:
`Vec<T>` and `String` now implement `Drop`, so they are move-only and every
manual `vec_drop` / `string_drop` call on an owned binding is gone. Their
free counts are pinned separately (`VEC_CASES`, through an instrumented
Allocator) because they need ritzlib linked; the last of those rows is a
match arm `found = path`, an assignment *expression* that used to escape the
move checker and drop the payload twice.

Each table is one test per compiler that asserts every row and names each
failing one (`row <name>: ...`); see "the harness" below (AGAST #3521).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link

from ref_rules import (ADDR_INTO_VALUE, MOVE_OUT_OF_REF, REF_INTO_VALUE, lent_temp_escapes,
                       move_out_of_global)
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]
RITZ1S = ("ritz1", "ritz1_selfhosted")

PRELUDE = """\
trait Drop
    fn drop(self: @&Self)

var DROPS: i32 = 0
var ORDER: i32 = 0

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        DROPS = DROPS + 1
        ORDER = ORDER *% 10 +% self.id  # wraps by request (R63)

# Move-only without a Drop impl of its own: it has a Tracked field.
struct Holder
    t: Tracked
    n: i32

# No Drop anywhere inside: copies.
struct Plain
    x: i32
    y: i32

fn make(id: i32) -> Tracked
    return Tracked { id: id }

# A by-value parameter of a move-only type takes ownership.
fn consume(t: Tracked) -> i32
    return t.id

"""

# A move-only enum, for the match cases (AGAST #2174, #2177).
SLOT = """\
enum Slot
    Full(Tracked)
    Empty

"""

# A by-value parameter of a move-only enum: it drops the enum (AGAST #4602).
EAT_SLOT = """\
fn eat(s: Slot) -> i32
    return 0

"""

# A move-only enum carrying a move-only enum (AGAST #3329).
NESTED_SLOT = """\
enum Nest
    Has(Slot)
    Nil

fn take_slot(s: Slot) -> i32
    return 0

"""

# A tag-only enum that is move-only by its Drop impl, as a payload (#3329).
DROP_FLAG = """\
enum Flag
    A
    B

impl Drop for Flag
    fn drop(self: @&Flag)
        DROPS = DROPS + 1

enum Flagged
    Has(Flag)
    Nil

fn take_flag(f: Flag) -> i32
    return 0

"""

# Methods that build a value, for the method-call cases (AGAST #2257).
METHODS = """\
impl Tracked
    fn new(id: i32) -> Tracked
        return Tracked { id: id }

    fn again(self: @Tracked) -> Tracked
        return Tracked { id: self.id }

    fn peek(self: @Tracked) -> i32
        return self.id

struct Sink
    n: i32

impl Sink
    fn look(self: @Sink, t: @Tracked) -> i32
        return t.id

"""

# Callees taking a lent `Tracked`, for `@<call>` arguments (AGAST #3050).
LENT = """\
fn look(t: @Tracked) -> i32
    return t.id

fn set(t: @&Tracked)
    t.id = 7

fn both(t: @Tracked, n: i32) -> i32
    return DROPS

"""

# Callees that hand back what they were lent (AGAST #3215).
LENT_ESCAPE = """\
fn id(t: @Tracked) -> @Tracked
    return t

struct Pick
    n: i32

impl Pick
    fn pick(self: @Pick, t: @Tracked) -> @Tracked
        return t

struct Wrap
    p: *Tracked

impl Wrap
    fn of(t: @&Tracked) -> Wrap
        return Wrap { p: t }

"""

# Shapes a binding from a field can take (AGAST #2243).
FIELDS = """\
struct Pair
    t: Tracked
    s: Tracked

struct Deep
    p: Pair
    u: Tracked

struct Refs
    p: *Tracked
    n: i32

struct Gen<A>
    v: A

struct Slotted
    e: Slot
    s: Tracked

impl Tracked
    fn burn(self: Tracked) -> i32
        return self.id

    fn again(self: @Tracked) -> Tracked
        return Tracked { id: self.id }

fn make_holder(id: i32) -> Holder
    return Holder { t: make(id), n: 0 }

"""


# Shapes a move out of a tuple element can take (AGAST #2244).
TUPLES = """\
struct WithPair
    pair: (Tracked, Tracked)
    u: Tracked

struct InElement
    t: Tracked
    s: Tracked

impl Tracked
    fn burn(self: Tracked) -> i32
        return self.id

    fn again(self: @Tracked) -> Tracked
        return Tracked { id: self.id }

    fn peek(self: @Tracked) -> i32
        return self.id

fn look(t: @Tracked) -> i32
    return t.id

fn make_pair(a: i32, b: i32) -> (Tracked, Tracked)
    return (make(a), make(b))

fn make_mixed(a: i32) -> (Tracked, i32)
    return (make(a), 5)

"""

# Tuple rows ritz1 still misses since it types every tuple (AGAST #3005): a
# pointer or array element (#3024).  #3031's discarded tuple temporary has no
# effect (LARB R64, AGAST #3491), so its rows bind the tuple instead.
TUPLE_PTR_ELEM = {"ritz1": 3024, "ritz1_selfhosted": 3024}

# name -> (program body, expected exit status, {compiler: gap ticket}).
# Where a helper returns `DROPS * 10`, the tens digit is the count at that
# point inside the helper and the units digit the count once it has returned.
# Two levels of struct (AGAST #2232).
NESTED = """\
struct Inner2
    t: Tracked
    u: Tracked
    n: i32

struct Outer2
    w: Inner2

"""

# AGAST #2242: a third level, and what moves or rebuilds its parts.
NESTED3 = NESTED + """\
struct D3
    a: Outer2
    z: Tracked

enum Pick
    A
    B

fn eat_w(i: Inner2) -> i32
    return i.n

fn eat_o(o: Outer2) -> i32
    return 0

fn mk_w(a: i32, b: i32) -> Inner2
    return Inner2 { t: make(a), u: make(b), n: 3 }

"""

V3 = "    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }\n"
D3 = ("    var d = D3 { a: Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }, "
      "z: make(4) }\n")


def nested_order(lines, decl=V3):
    """`f(1)` runs `lines` after `decl`; the program exits with ORDER."""
    return (NESTED3 + "fn f(c: i32)\n" + decl + lines
            + "\npub fn main() -> i32\n    f(1)\n    return ORDER\n")


# A value that can leave the statement it is stored by.
FALLIBLE = """\
fn make_or_err(c: i32) -> Result<Tracked, i32>
    if c == 1
        return Err(9)
    return Ok(make(5))

"""

# Bindings initialised from `?` (AGAST #2264). Not `open`: a user fn of that
# name is ritz0's builtin syscall (#3243).
TRY_MAKE = """\
fn try_make(id: i32) -> Result<Tracked, i32>
    if id == 0
        return Err(9)
    return Ok(make(id))

fn try_some(id: i32) -> Option<Tracked>
    return Some(make(id))

impl Tracked
    fn try_new(id: i32) -> Result<Tracked, i32>
        return Ok(make(id))

"""


# AGAST #2319: more movable paths than an i32 has bits (ritz1 used to track
# 31 and move the whole binding past them).  `Wide` has `n` Tracked fields;
# f(c) builds one and runs `lines`, `calls` runs f, and the program exits
# with DROPS.
def wide(n, lines, calls="    f(1)\n"):
    return ("struct Wide\n" + "".join(f"    f{i}: Tracked\n" for i in range(n))
            + "\nfn f(c: i32)\n    var w = Wide { "
            + ", ".join(f"f{i}: make(1)" for i in range(n)) + " }\n" + lines
            + "\npub fn main() -> i32\n" + calls + "    return DROPS\n")


WIDE_N = (NESTED3 + "struct WideN\n" + "".join(f"    g{i}: Inner2\n" for i in range(12))
          + "\nfn f()\n    var w = WideN { "
          + ", ".join(f"g{i}: mk_w(1, 1)" for i in range(12)) + " }\n")

CASES = {
    # AGAST #2243: a binding from a field has the field's type, so it moves.
    # Each `consume` or rebinding below dropped a value twice on ritz0.
    "field_binding_moves_into_call": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_let": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    let x = h.t
    consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_moves_to_binding": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    var y = x
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_unmoved_drops_once": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_sibling_still_drops": (SLOT + FIELDS + """\
fn f() -> i32
    var p = Pair { t: make(1), s: make(2) }
    var x = p.t
    consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "field_binding_nested": (SLOT + FIELDS + """\
fn f() -> i32
    var d = Deep { p: Pair { t: make(1), s: make(2) }, u: make(3) }
    var x = d.p.t
    consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 3, {}),

    "field_binding_part_of_a_field_binding": (SLOT + FIELDS + """\
fn f() -> i32
    var d = Deep { p: Pair { t: make(1), s: make(2) }, u: make(3) }
    var x = d.p
    var y = x.t
    consume(y)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 3, {}),

    "field_binding_moved_on_the_path_taken": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    if h.n == 0
        consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_moved_on_the_path_not_taken": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    if h.n == 1
        consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_field_assigned_back": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    h.t = make(2)
    consume(h.t)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "field_binding_assigned_after_move": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    consume(x)
    x = make(2)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "field_binding_by_value_receiver": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    x.burn()
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_from_temporary": (SLOT + FIELDS + """\
fn f() -> i32
    var x = make_holder(1).t
    consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_matched": (SLOT + FIELDS + """\
fn f() -> i32
    var b = Slotted { e: Slot.Full(make(1)), s: make(2) }
    var x = b.e
    match x
        Full(t) => consume(t)
        Empty => pass
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "field_binding_generic_field": (SLOT + FIELDS + """\
fn f() -> i32
    var g = Gen<Tracked> { v: make(1) }
    var x = g.v
    consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # A Copy-typed field stays a copy, and the owner keeps its field.
    "field_binding_copy_field_stays_a_copy": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.n
    var y = x
    var z = x
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_pointer_field_stays_a_copy": (SLOT + FIELDS + """\
fn f() -> i32
    var t = make(1)
    var r = Refs { p: @t, n: 0 }
    var x = r.p
    var y = x
    var z = x
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # #2243's types reach what the binding feeds: its method's unclaimed
    # result is a temporary (it wasn't on ritz0 before).
    "field_binding_method_temporary": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    x.again()
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    # So does a literal of fields nobody takes (it leaked on ritz0 before).
    "field_element_array_temporary": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    let a = [h.t]
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_element_tuple_temporary": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    let a = (h.t, 1)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_element_array_binding": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var a: [1]Tracked = [h.t]
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # A binding moves into a literal as a field does (AGAST #2266).
    "array_element_binding": (SLOT + FIELDS + """\
fn f() -> i32
    var t = make(1)
    var a: [1]Tracked = [t]
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # Unannotated, the literal is `[1]Tracked` (ritz1 gave it an i64 slot).
    "array_element_unannotated_binding": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var a = [h.t]
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # A temporary literal drops every element, in index order.
    "array_temporary_drops_each_element": (SLOT + FIELDS + """\
fn f() -> i32
    let a = [make(1), make(2)]
    return 0

pub fn main() -> i32
    f()
    return DROPS *% 100 +% ORDER
""", 212, {}),

    # A copy-typed struct literal gets its element type too, and copies.
    "array_unannotated_copy_elements": (SLOT + FIELDS + """\
fn f() -> i32
    var a = [Plain { x: 3, y: 4 }, Plain { x: 1, y: 2 }]
    var p = a[0]
    return a[0].x * 100 + a[1].y * 10 + p.y

pub fn main() -> i32
    return f() - 300
""", 24, {}),

    "field_binding_pointer_member": (SLOT + FIELDS + """\
fn f() -> i32
    var t = make(1)
    var r = Refs { p: @t, n: 0 }
    var y = r.p
    return y.id - 1

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "field_binding_from_try": (SLOT + FIELDS + """\
struct Res
    r: Result<Tracked, i32>

fn g() -> Result<i32, i32>
    var h = Res { r: Ok(make(1)) }
    var x = h.r?
    consume(x)
    return Ok(0)

fn f() -> i32
    g()
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # AGAST #2267: the carrier is a field down a chain, and an Option.
    "field_binding_from_try_nested_option": (SLOT + FIELDS + """\
struct ResOpt
    r: Option<Tracked>

struct Outer
    h: ResOpt
    n: i32

fn g() -> Option<i32>
    var o = Outer { h: ResOpt { r: Some(make(1)) }, n: 0 }
    var x = o.h.r?
    consume(x)
    return Some(0)

fn f() -> i32
    g()
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # AGAST #2264: a binding from `?` owns the unwrapped value. ritz0
    # dropped none of these: it typed no `?` initialiser, so leaked them.
    "try_binding_drops_at_scope_end": (TRY_MAKE + """\
fn g() -> Result<i32, i32>
    var t = try_make(1)?
    return Ok(0)

pub fn main() -> i32
    g()
    return DROPS
""", 1, {}),

    "try_binding_let": (TRY_MAKE + """\
fn g() -> Result<i32, i32>
    let t = try_make(1)?
    return Ok(0)

pub fn main() -> i32
    g()
    return DROPS
""", 1, {}),

    "try_binding_moves_to_binding": (TRY_MAKE + """\
fn g() -> Result<i32, i32>
    var t = try_make(1)?
    var u = t
    return Ok(0)

pub fn main() -> i32
    g()
    return DROPS
""", 1, {}),

    "try_binding_moves_into_call": (TRY_MAKE + """\
fn g() -> Result<i32, i32>
    var t = try_make(1)?
    return Ok(consume(t))

pub fn main() -> i32
    g()
    return DROPS
""", 1, {}),

    # Reverse declaration order on success (21); on `Err` only `a` exists (1).
    "try_binding_order_and_early_return": (TRY_MAKE + """\
fn g(c: i32) -> Result<i32, i32>
    var a = make(1)
    var t = try_make(c)?
    return Ok(0)

pub fn main() -> i32
    g(2)
    g(0)
    return ORDER
""", 211, {}),

    "try_binding_from_option": (TRY_MAKE + """\
fn g() -> Option<i32>
    var t = try_some(1)?
    return Some(0)

pub fn main() -> i32
    g()
    return DROPS
""", 1, {}),

    "try_binding_from_method": (TRY_MAKE + """\
fn g() -> Result<i32, i32>
    var t = Tracked.try_new(1)?
    var u = t
    return Ok(0)

pub fn main() -> i32
    g()
    return DROPS
""", 1, {}),

    # AGAST #2269 typed a binding from a module-level `var` (ritz0 saw only
    # locals, so `x` was a copy and dropped twice); LARB R34 (#3366) then
    # refused moving a move-only value out of one: GLOBAL_MOVE_OUT. A borrow
    # of the global's field is unaffected, and nothing drops.  LARB R60
    # refuses a value global of a Drop type, so GLOBAL is a pointer into a
    # static buffer (R71's migration shape).
    "borrow_of_global_field": (SLOT + FIELDS + """\
var GLOBAL: *Holder = null
var GLOBAL_STORE: [4]i64

fn see(t: @Tracked) -> i32
    return t.id

fn f() -> i32
    GLOBAL = @&GLOBAL_STORE as *Holder
    *GLOBAL = make_holder(1)
    var r = @(*GLOBAL).t
    see(@(*GLOBAL).t)
    return see(r)

pub fn main() -> i32
    f()
    return DROPS
""", 0, {}),

    # LARB R34 refuses only a move-only value: a copyable struct global copies
    # out by value as often as it's read (#3367).
    "copy_of_global_struct": (SLOT + FIELDS + """\
var PL: Plain

fn f() -> i32
    PL = Plain { x: 1, y: 2 }
    var a = PL
    var b = PL
    return a.x + b.y

pub fn main() -> i32
    return f() * 10 + DROPS
""", 30, {}),

    # LARB R34b: a by-value `match G.t` moves (GLOBAL_MOVE_OUT); `match @G.t`
    # lends it, reads the payload in place and drops nothing.  LARB R60: the
    # global is a pointer into a static buffer (R71's migration shape).
    "match_on_borrowed_global_field": (SLOT + FIELDS + """\
var SL: *Slotted = null
var SL_STORE: [8]i64

fn f() -> i32
    SL = @&SL_STORE as *Slotted
    *SL = Slotted { e: Slot.Full(make(4)), s: make(5) }
    match @(*SL).e
        Full(x) => x.id
        _ => 0

pub fn main() -> i32
    return f() * 10 + DROPS
""", 40, {}),

    # AGAST #2257: a binding from a method call has the method's return type,
    # so it moves. Each of these dropped one value twice on ritz0.
    "method_binding_moves_into_call": (METHODS + """\
fn f() -> i32
    var t = Tracked.new(1)
    consume(t)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "method_binding_moves_to_binding": (METHODS + """\
fn f() -> i32
    var t = Tracked.new(1)
    var u = t
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "method_binding_from_value_receiver": (METHODS + """\
fn f() -> i32
    var a = make(1)
    var t = a.again()
    consume(t)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    # AGAST #2257: a method's result nobody takes is a temporary (§13.6).
    "method_temp_statement": (METHODS + """\
fn f() -> i32
    Tracked.new(1)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "method_temp_field": (METHODS + """\
fn f() -> i32
    var i = Tracked.new(1).id
    return i

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # One evaluation, so one value to drop (AGAST #2261).
    "method_temp_receiver": (METHODS + """\
fn f() -> i32
    return Tracked.new(1).peek()

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # Lent to a method, the result is still nobody's: it drops after the
    # call (AGAST #3050).
    "method_temp_lent_arg": (METHODS + """\
fn f() -> i32
    var s = Sink { n: 0 }
    return s.look(@Tracked.new(1))

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # `@<call>` passed straight to a call lives until that call returns and
    # drops then, not at the statement's end (AGAST #2518, #3050): the
    # `DROPS` after the call already counts it.
    "lent_temp_fn_arg": (LENT + """\
fn f() -> i32
    return look(@make(1)) * 10 + DROPS

pub fn main() -> i32
    return f() * 10 + DROPS
""", 111, {}),

    "lent_temp_method_arg": (METHODS + LENT + """\
fn f() -> i32
    var s = Sink { n: 0 }
    return s.look(@make(2)) * 10 + DROPS

pub fn main() -> i32
    return f() * 10 + DROPS
""", 211, {}),

    # AGAST #4537: an owning argument to a method moves, even when another
    # type declares a same-named method that lends.  `Box.take` takes its
    # Tracked by value; `Poke.take` shares the name with a `*Tracked` param.
    # Read from the name-wide table alone, the argument looked lent, so the
    # caller dropped `t` after the callee had already dropped its parameter
    # (DROPS 2).  The receiver's own type decides.
    "method_arg_moves_past_a_lending_namesake": ("""\
struct Box
    n: i32

impl Box
    fn take(self: @&Box, t: Tracked) -> i32
        return t.id

struct Poke
    n: i32

impl Poke
    fn take(self: @&Poke, p: *Tracked) -> i32
        return 0

fn f() -> i32
    var b = Box { n: 0 }
    var t = make(1)
    return b.take(t)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # `@&`: the callee's write is what the drop sees (ORDER gets 7).
    "lent_temp_mut_arg": (LENT + """\
pub fn main() -> i32
    set(@&make(1))
    return ORDER * 10 + DROPS
""", 71, {}),

    # The inner call's temporary drops when the inner call returns, before
    # the outer call runs (`both` sees DROPS 1); the outer's after it.
    # The drop after the call adds blocks mid-expression: an `and`'s value,
    # an `if` expression's arm and a loop condition still join right.
    "lent_temp_in_and": (LENT + """\
pub fn main() -> i32
    let b = DROPS == 0 and look(@make(3)) == 3
    if b
        return 10 + DROPS
    return DROPS
""", 11, {}),

    "lent_temp_in_if_expr": (LENT + """\
pub fn main() -> i32
    let c: i32 = 1
    let zero: i32 = 0
    let v = if c == 1 then look(@make(3)) else zero
    return v * 10 + DROPS
""", 31, {}),

    "lent_temp_in_while_cond": (LENT + """\
pub fn main() -> i32
    var i: i32 = 0
    while i < 3 and look(@make(i)) >= 0
        i = i + 1
    return DROPS
""", 3, {}),

    "lent_temp_nested": (LENT + """\
pub fn main() -> i32
    let n = both(@make(1), look(@make(2)))
    return n * 100 + ORDER
""", 121, {}),

    # Lent from a local, the reference `id` returns outlives the call
    # (AGAST #3215's control): the local drops at the block's end.
    "lent_temp_bound_then_id": (LENT_ESCAPE + """\
pub fn main() -> i32
    let t = make(5)
    return id(@t).id * 10 + DROPS
""", 50, {}),

    "scope_end_let": ("""\
fn f()
    let t = make(1)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "scope_end_var": ("""\
fn f()
    var t = make(1)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # Dropped when the `if` body ends, not when f does.
    "nested_block_end": ("""\
fn f() -> i32
    if DROPS == 0
        var t = make(1)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # Once per call, on either path.
    "early_return": ("""\
fn f(x: i32) -> i32
    var t = make(1)
    if x > 0
        return 7
    return 9

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2, {}),

    # Iterations 0 and 1 drop at the end of the body; iteration 2 on `break`.
    "break": ("""\
fn f()
    var i: i32 = 0
    while i < 5
        var t = make(i)
        if i == 2
            break
        i = i + 1

pub fn main() -> i32
    f()
    return DROPS
""", 3, {}),

    # Four iterations, two of which leave by `continue`.
    "continue": ("""\
fn f()
    var i: i32 = 0
    while i < 4
        i = i + 1
        var t = make(i)
        if i % 2 == 0
            continue

pub fn main() -> i32
    f()
    return DROPS
""", 4, {}),

    # The old value is dropped by the assignment, the new one at scope end.
    "reassignment": ("""\
fn f() -> i32
    var t = make(1)
    t = make(2)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 12, {}),

    # consume() owns and drops it; f must not drop it again (ritz0: 12).
    "move_into_callee": ("""\
fn f() -> i32
    var t = make(1)
    consume(t)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # build() moves t out: not dropped there, dropped once by f's scope.
    "move_out_by_return": ("""\
fn build() -> Tracked
    var t = make(1)
    return t

fn f() -> i32
    var u = build()
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    # A `return` nested in a statement whose temporary is still pending, with
    # a binding declared after it. Innermost scope first, as Rust does: the
    # arm binding `t` (id 2) drops before the statement's temporary
    # `make(1)` (id 1), so ORDER is 21, not 12. LANGUAGE_SPEC §13.6
    # (AGAST #4304).
    "ret_before_pending_temp": (SLOT + """\
fn pick(id: i32) -> Slot
    Slot.Full(make(id + 1))

fn g() -> i32
    match pick(make(1).id)
        Full(t) =>
            return t.id
        _ =>
            pass
    return 0

pub fn main() -> i32
    g()
    return ORDER
""", 21, {}),

    # The other direction of the same rule: a temporary the `return` itself
    # creates is newer than a binding declared before it, so the temporary
    # (id 2) drops first, then the binding (id 1): ORDER 21. A `return` that
    # always dropped its bindings first would be 12 here (AGAST #4304).
    "ret_temp_after_binding": ("""\
fn f() -> i32
    let t = make(1)
    return make(2).id

pub fn main() -> i32
    f()
    return ORDER
""", 21, {}),

    # A `break` that leaves a statement whose temporary is still pending
    # drops that temporary too, innermost first: the arm binding `t` (id 2)
    # before the statement's `make(1)` (id 1), so DROPS is 2 and ORDER 21
    # (AGAST #4387; LANGUAGE_SPEC §13.6).
    "break_before_pending_temp": (SLOT + """\
fn pick(id: i32) -> Slot
    Slot.Full(make(id + 1))

fn f() -> i32
    var i: i32 = 0
    while i < 1
        i = i + 1
        match pick(make(1).id)
            Full(t) =>
                break
            _ =>
                pass
    return DROPS *% 100 +% ORDER

pub fn main() -> i32
    f()
    return DROPS *% 100 +% ORDER
""", 221, {}),

    # The same shape through `continue` (AGAST #4387).
    "continue_before_pending_temp": (SLOT + """\
fn pick(id: i32) -> Slot
    Slot.Full(make(id + 1))

fn f() -> i32
    var i: i32 = 0
    while i < 1
        i = i + 1
        match pick(make(1).id)
            Full(t) =>
                continue
            _ =>
                pass
    return DROPS *% 100 +% ORDER

pub fn main() -> i32
    f()
    return DROPS *% 100 +% ORDER
""", 221, {}),

    # A `defer` registered after the statement's temporary runs before it
    # drops, but the arm binding and the temporary still go innermost first:
    # the deferred `make(3)`, then `t` (id 2), then `make(1)` (id 1), so
    # ORDER is 321 (DROPS 3).  DROPS * 10 + ORDER / 100 keeps it small
    # (a process exit status is mod 256) while telling 33 from the 32 that
    # dropping the temporary before the defer would give (AGAST #4387).
    "defer_before_pending_temp": (SLOT + """\
fn pick(id: i32) -> Slot
    Slot.Full(make(id + 1))

fn f() -> i32
    var i: i32 = 0
    while i < 1
        i = i + 1
        match pick(make(1).id)
            Full(t) =>
                defer make(3)
                break
            _ =>
                pass
    return DROPS * 10 + ORDER / 100

pub fn main() -> i32
    f()
    return DROPS * 10 + ORDER / 100
""", 33, {}),

    # Plain copies: `a` stays usable after every copy, and nothing drops.
    "plain_struct_copy": ("""\
fn take(p: Plain) -> i32
    return p.x

fn f() -> i32
    let a = Plain { x: 3, y: 4 }
    let b = a
    let c = a
    return take(a) + take(a) + a.x + b.x + c.y

pub fn main() -> i32
    let n = f()
    return n + DROPS
""", 16, {}),

    # Reverse declaration order: 3, 2, 1.
    "drop_order": ("""\
fn f()
    var a = make(1)
    var b = make(2)
    var c = make(3)

pub fn main() -> i32
    f()
    return ORDER - 300
""", 21, {}),

    # Holder has no Drop impl; dropping it drops its Tracked field.
    "field_drop_glue": ("""\
fn f()
    var h = Holder { t: make(4), n: 1 }

pub fn main() -> i32
    f()
    return ORDER
""", 4, {}),

    # AGAST #2161 from here on. An enum drops the payload of the variant it
    # holds: f(1) holds Full(1) at scope end, f(0) only Empty.
    "enum_payload": ("""\
enum Slot
    Full(Tracked)
    Empty

fn f(full: i32)
    var s = Slot.Empty
    if full == 1
        s = Slot.Full(make(1))

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 1, {}),

    # The generic enum from ritzlib, instantiated at a move-only type.
    "option_payload": ("""\
import ritzlib.option

fn f()
    var o: Option<Tracked> = Some(make(1))
    var n: Option<Tracked> = None

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # Array elements drop in index order: 1, 2, 3.
    "array_elements": ("""\
fn f()
    var a: [3]Tracked = [make(1), make(2), make(3)]

pub fn main() -> i32
    f()
    return ORDER
""", 123, {}),

    # Tuple elements drop in order; the i32 in between is not dropped.
    "tuple_elements": ("""\
fn f()
    var t = (make(1), 5, make(2))

pub fn main() -> i32
    f()
    return ORDER
""", 12, {}),

    # A temporary nobody owns drops at the end of its statement: before
    # the `return`, so the helper already sees it.
    "temporary_statement": ("""\
fn f() -> i32
    make(1)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # Moving an outer binding inside a loop is fine when every path back to
    # the loop head assigns it again: consume drops ids 0, 1 and 2, the
    # scope end drops id 3.
    "loop_move_reassigned": ("""\
fn f()
    var t = make(0)
    var i: i32 = 0
    while i < 3
        consume(t)
        i = i + 1
        t = make(i)

pub fn main() -> i32
    f()
    return DROPS
""", 4, {}),

    # ...or when the path that moved it leaves the loop.
    "loop_move_then_break": ("""\
fn f()
    var t = make(1)
    while true
        consume(t)
        break

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # AGAST #2168 from here on.  Moving a field out moves only that field:
    # its new owner drops it, and the rest of the struct (nothing move-only
    # left in a Holder) drops with the binding, so t is dropped once.
    "field_move_return": ("""\
fn take() -> Tracked
    var h = Holder { t: make(4), n: 1 }
    return h.t

fn f() -> i32
    var u = take()
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    "field_move_binding": ("""\
fn f() -> i32
    var h = Holder { t: make(4), n: 1 }
    var u = h.t
    return DROPS * 10 + h.n

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 2, {}),

    # consume() drops t; h's drop must not drop it again.
    "field_move_into_callee": ("""\
fn f() -> i32
    var h = Holder { t: make(4), n: 1 }
    consume(h.t)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # A temporary whose move-only field is moved out isn't dropped too.
    "temporary_field_moved": ("""\
fn mk(id: i32) -> Holder
    return Holder { t: make(id), n: 0 }

fn f() -> i32
    var u = mk(3).t
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    # AGAST #2232: a move out of a nested field stops the binding dropping
    # it, so the one value drops once. It used to drop twice.
    "nested_field_moved": (NESTED + """\
struct Shell
    h: Holder

fn f()
    var v = Shell { h: Holder { t: make(1), n: 0 } }
    consume(v.h.t)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # Assigning it back makes the binding its owner again.
    "nested_field_assigned_back": (NESTED + """\
fn f()
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    v.w.t = make(4)

pub fn main() -> i32
    f()
    return ORDER
""", 142, {}),

    # Only that field moves: v.w's other fields still drop...
    "nested_field_move_rest_dropped": (NESTED + """\
fn f()
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)

pub fn main() -> i32
    f()
    return ORDER
""", 12, {}),

    # ...and stay usable.
    "nested_field_move_sibling_readable": (NESTED + """\
fn f() -> i32
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    return v.w.n

pub fn main() -> i32
    return f()
""", 3, {}),

    # AGAST #2242: a move on one path only.  ORDER is what the exit code
    # shows, mod 256, so 1256 reads 232.
    "nested_move_in_taken_if_arm": (nested_order("""\
    if c == 1
        consume(v.w.t)
"""), 12, {}),

    "nested_move_in_untaken_if_arm": (nested_order("""\
    if c == 2
        consume(v.w.t)
"""), 12, {}),

    "nested_move_of_each_part_in_if_arms": (nested_order("""\
    if c == 1
        consume(v.w.t)
    else
        consume(v.w.u)
"""), 12, {}),

    "nested_move_in_returning_if_arm": (nested_order("""\
    if c == 1
        consume(v.w.t)
        return
    consume(v.w.u)
"""), 12, {}),

    "nested_move_in_one_match_arm": (nested_order("""\
    var p = Pick.A
    match p
        Pick.A => consume(v.w.t)
        Pick.B => pass
"""), 12, {}),

    "nested_sibling_readable_after_if": (NESTED3 + """\
fn f(c: i32) -> i32
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    if c == 1
        consume(v.w.t)
    return v.w.n

pub fn main() -> i32
    return f(1)
""", 3, {}),

    "nested_move_from_by_value_param": (NESTED3 + """\
fn g(v: Outer2)
    consume(v.w.t)

fn f()
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    g(v)

pub fn main() -> i32
    f()
    return ORDER
""", 12, {}),

    # A match moves the path it reads, and only that: o.s.u still drops.
    "nested_match_scrutinee": (NESTED3 + """\
struct InSlot
    e: Slot
    u: Tracked

struct OutSlot
    s: InSlot

fn f()
    var o = OutSlot { s: InSlot { e: Slot.Full(make(1)), u: make(2) } }
    match o.s.e
        Slot.Full(t) => consume(t)
        Slot.Empty => pass

pub fn main() -> i32
    f()
    return ORDER
""".replace("struct InSlot", SLOT + "struct InSlot"), 12, {}),

    # Assigning a parent drops what is left of it: u, and not the moved t.
    "nested_parent_assigned_after_move": (nested_order("""\
    consume(v.w.t)
    v.w = mk_w(5, 6)
"""), 232, {}),

    # The assignment gives back every part of v.w, so t can move again.
    "nested_part_moves_again_after_parent_assigned": (nested_order("""\
    consume(v.w.t)
    v.w = mk_w(5, 6)
    consume(v.w.t)
"""), 232, {}),

    "nested_parent_assigned_after_maybe_move": (nested_order("""\
    if c == 1
        consume(v.w.t)
    v.w = mk_w(5, 6)
"""), 232, {}),

    "nested_parent_assigned_after_both_parts_moved": (nested_order("""\
    consume(v.w.t)
    consume(v.w.u)
    v.w = mk_w(5, 6)
"""), 232, {}),

    "nested_binding_assigned_after_move": (nested_order("""\
    consume(v.w.t)
    v = Outer2 { w: mk_w(5, 6) }
"""), 232, {}),

    # A sibling isn't moved, so it can be stored to: 2 drops as it is replaced.
    "nested_sibling_assigned_after_move": (nested_order("""\
    consume(v.w.t)
    v.w.u = make(5)
"""), 125, {}),

    "nested_scalar_assigned_after_move": (nested_order("""\
    consume(v.w.t)
    v.w.n = 5
"""), 12, {}),

    "nested_assigned_back_then_parent_moves": (nested_order("""\
    consume(v.w.t)
    v.w.t = make(5)
    eat_w(v.w)
"""), 152, {}),

    "nested_assigned_back_then_binding_moves": (nested_order("""\
    consume(v.w.t)
    v.w.t = make(5)
    eat_o(v)
"""), 152, {}),

    # The value moves v.w.t, so the store drops only v.w.u of the old v.w.
    "nested_value_moves_part_of_target": (nested_order("""\
    v.w = Inner2 { t: v.w.t, u: make(5), n: 3 }
"""), 215, {}),

    "nested_field_from_sibling": (nested_order("""\
    v.w.t = v.w.u
"""), 12, {}),

    # Several paths at different depths: what is left drops in declaration
    # order, depth first, whichever order the moves came in.
    "nested_deep_sibling_order": (nested_order("""\
    consume(d.a.w.u)
""", D3), 214, {}),

    "nested_moves_at_two_depths_order": (nested_order("""\
    consume(d.z)
    consume(d.a.w.t)
""", D3), 156, {}),

    "nested_middle_moved_order": (nested_order("""\
    eat_w(d.a.w)
""", D3), 124, {}),

    "nested_every_part_moved_order": (nested_order("""\
    consume(d.a.w.u)
    consume(d.a.w.t)
    consume(d.z)
""", D3), 214, {}),

    "nested_top_assigned_after_deep_move": (nested_order("""\
    consume(d.a.w.t)
    d.a = Outer2 { w: mk_w(5, 6) }
""", D3), 20, {}),

    "nested_middle_assigned_after_deep_move": (nested_order("""\
    consume(d.a.w.t)
    d.a.w = mk_w(5, 6)
""", D3), 20, {}),

    # Loops.  Moved and assigned back each time round: 1 5 then 5 2.
    "nested_loop_move_and_assign_back": (nested_order("""\
    var i = 0
    while i < 2
        consume(v.w.t)
        v.w.t = make(5)
        i = i + 1
"""), 16, {}),

    "nested_loop_binding_assigned_before_move": (nested_order("""\
    var i = 0
    while i < 2
        v = Outer2 { w: mk_w(5, 6) }
        consume(v.w.t)
        i = i + 1
"""), 216, {}),

    "nested_loop_read_sibling_until_move": (nested_order("""\
    var i = 0
    while i < 2
        if i == 1
            consume(v.w.t)
            break
        i = i + v.w.n
"""), 12, {}),

    # The store comes before the move in the source, but the move reaches it
    # round the loop: the second store must still make the field owned.
    "nested_loop_store_before_move": (nested_order("""\
    var i = 0
    while i < 2
        v.w.t = make(5)
        if i == 0
            consume(v.w.t)
        i = i + 1
"""), 16, {}),

    "field_loop_store_before_move": ("""\
fn f()
    var h = Holder { t: make(1), n: 0 }
    var i = 0
    while i < 2
        h.t = make(5)
        if i == 0
            consume(h.t)
        i = i + 1

pub fn main() -> i32
    f()
    return ORDER
""", 155, {}),

    # A field store owns the field once the value is stored, not before: a
    # `?` in the value leaves through the moved field, which must not drop.
    "field_store_value_returns_early": (FALLIBLE + """\
fn g(c: i32) -> Result<i32, i32>
    var h = Holder { t: make(1), n: 0 }
    consume(h.t)
    h.t = make_or_err(c)?
    return Ok(0)

pub fn main() -> i32
    g(1)
    return ORDER
""", 1, {}),

    "field_store_value_succeeds": (FALLIBLE + """\
fn g(c: i32) -> Result<i32, i32>
    var h = Holder { t: make(1), n: 0 }
    consume(h.t)
    h.t = make_or_err(c)?
    return Ok(0)

pub fn main() -> i32
    g(0)
    return ORDER
""", 15, {}),

    "nested_store_value_returns_early": (NESTED3 + FALLIBLE + """\
fn g(c: i32) -> Result<i32, i32>
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    v.w.t = make_or_err(c)?
    return Ok(0)

pub fn main() -> i32
    g(1)
    return ORDER
""", 12, {}),

    "nested_store_value_succeeds": (NESTED3 + FALLIBLE + """\
fn g(c: i32) -> Result<i32, i32>
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    v.w.t = make_or_err(c)?
    return Ok(0)

pub fn main() -> i32
    g(0)
    return ORDER
""", 152, {}),

    # More paths than ritz1 has bits: every part still drops once.
    "field_move_past_the_tracked_paths": (
        "struct Wide\n" + "".join(f"    f{i}: Tracked\n" for i in range(33)) + """
fn f()
    var w = Wide { """ + ", ".join(f"f{i}: make(1)" for i in range(33)) + """ }
    consume(w.f32)

pub fn main() -> i32
    f()
    return DROPS
""", 33, {}),

    "nested_move_past_the_tracked_paths": (NESTED3 +
        "struct WideN\n" + "".join(f"    g{i}: Inner2\n" for i in range(12)) + """
fn f()
    var w = WideN { """ + ", ".join(f"g{i}: mk_w(1, 1)" for i in range(12)) + """ }
    consume(w.g11.u)

pub fn main() -> i32
    f()
    return DROPS
""", 24, {}),

    # The path an i32's sign bit would hold.
    "wide_move_of_the_32nd_path": (wide(32, "    consume(w.f31)\n"), 32, {}),

    # Moved on one call's path only: 40 drops each call.
    "wide_move_in_one_if_arm": (wide(40, """\
    if c == 1
        consume(w.f39)
""", "    f(1)\n    f(0)\n"), 80, {}),

    # Paths in different words, moved apart.
    "wide_moves_far_apart": (wide(40, """\
    consume(w.f2)
    consume(w.f33)
    consume(w.f38)
"""), 40, {}),

    "wide_move_assigned_back": (wide(40, """\
    consume(w.f39)
    w.f39 = make(2)
"""), 41, {}),

    "wide_loop_move_and_assign_back": (wide(40, """\
    var i = 0
    while i < 2
        consume(w.f39)
        w.f39 = make(5)
        i = i + 1
"""), 42, {}),

    "wide_loop_move_then_break": (wide(40, """\
    while true
        consume(w.f39)
        break
"""), 40, {}),

    # The store drops what is left of the old w.g11 (its t), not its u.
    "wide_nested_parent_assigned_after_move": (WIDE_N + """\
    consume(w.g11.u)
    w.g11 = mk_w(1, 1)

pub fn main() -> i32
    f()
    return DROPS
""", 26, {}),

    # AGAST #2171 from here on (ritz1's cases from #2168, now shared).  A
    # struct with a field moved out still drops the others: consume drops 1,
    # p's scope end 2.
    "field_move_rest_dropped": ("""\
struct Two
    a: Tracked
    b: Tracked

fn f()
    var p = Two { a: make(1), b: make(2) }
    consume(p.a)

pub fn main() -> i32
    f()
    return ORDER
""", 12, {}),

    # Moved on one path only: the field drops on the other, once.
    "field_move_conditional": ("""\
fn f(x: i32)
    var h = Holder { t: make(1), n: 0 }
    if x > 0
        consume(h.t)

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 2, {}),

    # Assigning the field again re-owns it: 1 (consume), then 3 at scope end.
    "field_move_reassigned": ("""\
struct Two
    a: Tracked
    b: Tracked

fn f()
    var p = Two { a: make(1), b: make(2) }
    consume(p.a)
    p.a = make(3)

pub fn main() -> i32
    f()
    return ORDER
""", 132, {}),

    # Moved and re-assigned round a loop: consume drops 0, 1, 2; the end 3.
    "field_move_in_loop_reassigned": ("""\
fn f()
    var h = Holder { t: make(0), n: 0 }
    var i: i32 = 0
    while i < 3
        consume(h.t)
        i = i + 1
        h.t = make(i)

pub fn main() -> i32
    f()
    return DROPS
""", 4, {}),

    # A `return` drops what is left of a partly moved binding.
    "field_move_then_return": ("""\
struct Two
    a: Tracked
    b: Tracked

fn f(x: i32) -> i32
    var p = Two { a: make(1), b: make(2) }
    consume(p.b)
    if x > 0
        return 5
    return 6

pub fn main() -> i32
    f(1)
    return ORDER
""", 21, {}),

    # A by-value parameter owns its fields too: take() moves t out of h and
    # drops nothing; f's u drops it once.
    "field_move_from_param": ("""\
fn take(h: Holder) -> Tracked
    return h.t

fn f() -> i32
    var u = take(Holder { t: make(4), n: 1 })
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    # A binding declared inside a loop starts each iteration whole: the
    # field moved by iteration 0 doesn't stop iteration 1's h dropping its t:
    # consume drops id 0, iteration 1's scope end id 1.
    "field_move_fresh_each_iteration": ("""\
fn f()
    var i: i32 = 0
    while i < 2
        var h = Holder { t: make(i), n: 0 }
        if i == 0
            consume(h.t)
        i = i + 1

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    # AGAST #2173 from here on.  Assigning a move-only field drops its old
    # value (§13.6), as assigning a binding does: f's count after `h.t = ..`
    # is 1 (old t), h's scope end then drops the new one.
    "field_assign_drops_old": ("""\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    h.t = make(2)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 12, {}),

    # The new value is evaluated before the old one drops: make() sees
    # DROPS == 0, so the new id is 5 (6 if the old dropped first).
    "field_assign_value_first": ("""\
fn f()
    var h = Holder { t: make(1), n: 0 }
    h.t = make(DROPS + 5)

pub fn main() -> i32
    f()
    return ORDER
""", 15, {}),

    # The new value may read the old one; it is dropped after.
    "field_assign_reads_old": ("""\
fn f()
    var h = Holder { t: make(1), n: 0 }
    h.t = make(h.t.id + 1)

pub fn main() -> i32
    f()
    return ORDER
""", 12, {}),

    # The new value moves the old one: bump() drops it, the store doesn't.
    "field_assign_moves_old": ("""\
fn bump(t: Tracked) -> Tracked
    return make(t.id + 1)

fn f()
    var h = Holder { t: make(1), n: 0 }
    h.t = bump(h.t)

pub fn main() -> i32
    f()
    return ORDER
""", 12, {}),

    # Moved out on one path only: the old value drops on the other, so
    # each call drops two Tracked (consume's or the store's, then h's).
    "field_assign_after_conditional_move": ("""\
fn f(x: i32)
    var h = Holder { t: make(1), n: 0 }
    if x > 0
        consume(h.t)
    h.t = make(2)

pub fn main() -> i32
    f(1)
    f(0)
    return DROPS
""", 4, {}),

    # Each iteration's store drops the previous value; the end the last.
    "field_assign_in_loop": ("""\
fn f()
    var h = Holder { t: make(0), n: 0 }
    var i: i32 = 1
    while i < 4
        h.t = make(i)
        i = i + 1

pub fn main() -> i32
    f()
    return ORDER
""", 123, {}),

    # A copy field's store drops nothing.
    "field_assign_copy_field": ("""\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    h.n = 5
    return DROPS * 10 + h.n

pub fn main() -> i32
    let inner = f()
    return inner * 10 + DROPS
""", 51, {}),

    # A field of a field: `o.a.t = v` drops the old o.a.t (o owns it).
    "field_of_field_assign": ("""\
struct Outer
    a: Holder
    m: i32

fn f()
    var o = Outer { a: Holder { t: make(1), n: 0 }, m: 0 }
    o.a.t = make(2)

pub fn main() -> i32
    f()
    return ORDER
""", 12, {}),

    # Assigning a whole move-only field drops all of its old value.
    "field_assign_struct_field": ("""\
struct Outer
    a: Holder
    m: i32

fn f()
    var o = Outer { a: Holder { t: make(1), n: 0 }, m: 0 }
    o.a = Holder { t: make(2), n: 0 }

pub fn main() -> i32
    f()
    return ORDER
""", 12, {}),

    # A field of a type with its own drop: the old field drops at the
    # store; at the end Wrap's drop (9), then its field.
    "field_assign_in_drop_type": ("""\
struct Wrap
    t: Tracked

impl Drop for Wrap
    fn drop(self: @&Wrap)
        ORDER = ORDER * 10 + 9

fn f()
    var w = Wrap { t: make(1) }
    w.t = make(2)

pub fn main() -> i32
    f()
    return ORDER
""", 192, {}),

    # A by-value parameter owns its fields: the store drops the caller's.
    "field_assign_param": ("""\
fn f(h: Holder) -> i32
    h.t = make(2)
    return DROPS * 10

pub fn main() -> i32
    let inner = f(Holder { t: make(1), n: 0 })
    return inner + DROPS
""", 12, {}),

    # AGAST #4602: a bare-name arm binds the scrutinee itself (#4596), so
    # it takes it like a payload binding takes its payload: the binding
    # drops it once, at the end of its arm unless it moved on.
    "match_binding_arm_drops": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Empty => pass
        other => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    "match_binding_arm_into_call": (SLOT + EAT_SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Empty => pass
        other => eat(other)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    "match_binding_arm_returned": (SLOT + EAT_SLOT + """\
fn pick() -> Slot
    let s = Slot.Full(make(1))
    match s
        Empty => return Slot.Empty
        other => return other

pub fn main() -> i32
    let got = pick()
    let before = DROPS
    eat(got)
    return before * 10 + DROPS
""", 1, {}),

    # As a value: the arm's result is the binding, moved out once.
    "match_binding_arm_value": (SLOT + EAT_SLOT + """\
fn f() -> i32
    let s = Slot.Full(make(1))
    let n = match s
        Empty => 7
        other => eat(other)
    return DROPS * 10 + n

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # AGAST #2177 from here on (ritz1's cases from #2174, now shared).
    # A match moves its scrutinee (ritz0's rule), and the match
    # owns it.  A payload binding takes the payload and drops at the end of
    # its arm unless moved; an arm that binds nothing drops the scrutinee.
    # Each tens digit is the count inside f, before its `return`.
    "match_stmt_payload_drops": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Full(t) => pass
        _ => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    "match_stmt_unbound_arm_drops": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Empty => pass
        _ => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # `Full(_)` binds nothing either.
    "match_stmt_wildcard_payload_drops": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Full(_) => pass
        Empty => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # The payload moved on: dropped once, in consume.
    "match_stmt_payload_moved": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Full(t) => consume(t)
        _ => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # An arm that returns drops its payload binding at the `ret`, once.
    "match_stmt_payload_return": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Full(t) =>
            return DROPS * 10 + t.id
        _ =>
            pass
    return 99

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 2, {}),

    # Returning from an arm that binds nothing drops the scrutinee there.
    "match_stmt_unbound_arm_return": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Empty => pass
        _ =>
            return DROPS * 10
    return 99

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    # The expression form: the payload no longer leaks.
    "match_expr_payload_drops": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    let v = match s
        Full(t) => t.id
        _ => 0
    return DROPS * 10 + v

pub fn main() -> i32
    let inner = f()
    return inner + DROPS * 100
""", 111, {}),

    # The payload moved out as the arm's value: u owns it, dropped once.
    "match_expr_payload_moved_out": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    let u = match s
        Full(t) => t
        _ => make(2)
    return DROPS * 10 + u.id

pub fn main() -> i32
    let inner = f()
    return inner + DROPS * 100
""", 101, {}),

    # A move-only field as the scrutinee moves out of its struct.
    "match_field_scrutinee_drops": (SLOT + """\
struct Box2
    s: Slot
    n: i32

fn f() -> i32
    var b = Box2 { s: Slot.Full(make(1)), n: 1 }
    match b.s
        Full(t) => pass
        _ => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # A call's result as the scrutinee: the match owns it.
    "match_call_scrutinee_drops": (SLOT + """\
fn full(id: i32) -> Slot
    return Slot.Full(make(id))

fn f() -> i32
    match full(1)
        Full(t) => pass
        _ => pass
    match full(2)
        Empty => pass
        _ => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 22, {}),

    # Option<Tracked>: `Some(t)` owns the payload.
    "match_option_payload_drops": ("""\
import ritzlib.option

fn f() -> i32
    var o: Option<Tracked> = Some(make(1))
    match o
        Some(t) => pass
        None => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # A match in a loop: one drop per iteration, by whichever arm ran.
    "match_in_loop_drops": (SLOT + """\
fn f() -> i32
    for i in 0..4
        var s = Slot.Empty
        if i % 2 == 0
            s = Slot.Full(make(1))
        match s
            Full(t) => pass
            _ => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 22, {}),

    # A borrowed scrutinee (`match @s`) moves nothing; s drops once, at
    # its scope's end.
    "match_borrowed_scrutinee": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match @s
        Full(t) => pass
        _ => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    # AGAST #2178: the payload of a borrowed scrutinee reads and borrows;
    # only s drops it.
    "match_borrowed_scrutinee_reads_payload": (SLOT + LENT + """\
fn f() -> i32
    var s = Slot.Full(make(3))
    match @s
        Full(t) => DROPS = DROPS + t.id + look(@t) - 6
        _ => pass
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    # AGAST #3329: a lent move-only enum payload reads and borrows; only s
    # drops it.
    "match_borrowed_scrutinee_reads_enum_payload": (SLOT + NESTED_SLOT + """\
fn peek(s: @Slot) -> i32
    return 5

fn f() -> i32
    var s = Nest.Has(Slot.Full(make(1)))
    var r: i32 = 0
    match @s
        Has(x) => r = peek(@x)
        _ => r = 0
    return DROPS * 10 + r

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 6, {}),

    # AGAST #2178: a `let` from a match moves into consume, which drops it;
    # u's own drop is skipped.
    "let_from_match_moved": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    let u = match s
        Full(t) => t
        _ => make(2)
    consume(u)
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    # AGAST #2244: the ticket's program. The tuple's drop skips the element.
    "tuple_element_moved": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_moved_let": (TUPLES + SLOT + """\
fn f()
    let p = (make(1), 2)
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_sibling_still_drops": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    # The moved element drops in `consume`, then the rest, in order.
    "tuple_element_sibling_order": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2), make(3))
    consume(p.1)

pub fn main() -> i32
    f()
    return ORDER
""", 213, {}),

    "tuple_element_both_moved": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    consume(p.0)
    consume(p.1)

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_binding": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    var x = p.0
    consume(x)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # The binding owns it now, and drops it.
    "tuple_element_binding_unmoved": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    var x = p.0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_param": (TUPLES + SLOT + """\
fn g(p: (Tracked, Tracked)) -> i32
    return consume(p.1)

fn f()
    g(make_pair(1, 2))

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_from_call": (TUPLES + SLOT + """\
fn f()
    var p = make_pair(1, 2)
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_conditional_taken": (TUPLES + SLOT + """\
fn g(c: i32)
    var p = (make(1), 2)
    if c == 1
        consume(p.0)

fn f()
    g(1)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_conditional_not_taken": (TUPLES + SLOT + """\
fn g(c: i32)
    var p = (make(1), 2)
    if c == 1
        consume(p.0)

fn f()
    g(0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_returned": (TUPLES + SLOT + """\
fn g() -> Tracked
    var p = (make(1), make(2))
    return p.0

fn f()
    consume(g())

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_tail": (TUPLES + SLOT + """\
fn g() -> Tracked
    var p = (make(1), make(2))
    p.1

fn f()
    consume(g())

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    # Reassigning drops what is left of the old value; the new one is whole.
    "tuple_reassigned_after_element_move": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    consume(p.0)
    p = (make(3), make(4))

pub fn main() -> i32
    f()
    return DROPS
""", 4, {}),

    # A path through a tuple.
    "tuple_element_in_field": (TUPLES + SLOT + """\
fn f()
    var v = WithPair { pair: (make(1), make(2)), u: make(3) }
    consume(v.pair.0)

pub fn main() -> i32
    f()
    return DROPS
""", 3, {}),

    "tuple_element_in_field_binding": (TUPLES + SLOT + """\
fn f()
    var v = WithPair { pair: (make(1), make(2)), u: make(3) }
    var x = v.pair.1
    consume(x)

pub fn main() -> i32
    f()
    return DROPS
""", 3, {}),

    "tuple_in_field_whole_after_element_is_part": (TUPLES + SLOT + """\
fn f()
    var v = WithPair { pair: (make(1), make(2)), u: make(3) }
    consume(v.pair.0)
    consume(v.u)

pub fn main() -> i32
    f()
    return DROPS
""", 3, {}),

    # A path through a tuple into a struct.
    "tuple_field_of_an_element": (TUPLES + SLOT + """\
fn f()
    var p = (InElement { t: make(1), s: make(2) }, 7)
    consume(p.0.t)

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_in_tuple": (TUPLES + SLOT + """\
fn f()
    var p = ((make(1), make(2)), make(3))
    consume((p.0).1)

pub fn main() -> i32
    f()
    return DROPS
""", 3, {}),

    # What the element's type feeds.
    "tuple_element_by_value_receiver": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    p.0.burn()

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_method_temporary": (TUPLES + SLOT + """\
fn f() -> i32
    var p = (make(1), 2)
    p.0.again()
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_match": (TUPLES + SLOT + """\
fn f()
    var p = (Slot.Full(make(1)), make(2))
    match p.0
        Full(t) => consume(t)
        _ => pass

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_match_wildcard": (TUPLES + SLOT + """\
fn f()
    var p = (Slot.Full(make(1)), make(2))
    match p.0
        _ => pass

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_of_temporary": (TUPLES + SLOT + """\
fn f()
    consume(make_mixed(1).0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_of_temporary_binding": (TUPLES + SLOT + """\
fn f()
    var x = make_mixed(1).0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_into_literal": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    var q = (p.0, 3)

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_into_literal_temporary": (TUPLES + SLOT + """\
fn f() -> i32
    var p = (make(1), make(2))
    let a = (p.0, 3)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    # Lending an element takes its address, which moves nothing.
    "tuple_element_lent": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    look(@p.0)
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_lending_receiver": (TUPLES + SLOT + """\
fn g(p: (Tracked, i32)) -> i32
    return p.0.peek()

fn f()
    g((make(1), 2))

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # A reference element copies, so the value drops once, from `t`.
    "tuple_element_copy_reference": (TUPLES + SLOT + """\
fn f()
    var t = make(1)
    var p = (@t, 2)
    var x = p.0
    look(x)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),  # #3024 closed by #4656: `(@t, 2)` names its `@T` element,

    "tuple_element_try": (TUPLES + SLOT + """\
fn g(r: (Result<Tracked, i32>, i32)) -> Result<i32, i32>
    var x = r.0?
    return Ok(consume(x))

fn f()
    var r: Result<Tracked, i32> = Ok(make(1))
    g((r, 2))

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_for": (TUPLES + SLOT + """\
fn f()
    var p = ([make(1), make(2)], 3)
    for v in p.0
        consume(v)

pub fn main() -> i32
    f()
    return DROPS
""", 2, TUPLE_PTR_ELEM),

    "tuple_element_in_loop": (TUPLES + SLOT + """\
fn f()
    var i = 0
    while i < 3
        var p = (make(1), make(2))
        consume(p.0)
        i = i + 1

pub fn main() -> i32
    f()
    return DROPS
""", 6, {}),

    "tuple_element_before_break": (TUPLES + SLOT + """\
fn f()
    while true
        var p = (make(1), 2)
        consume(p.0)
        break

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    "tuple_element_before_return": (TUPLES + SLOT + """\
fn g() -> i32
    var p = (make(1), make(2))
    consume(p.0)
    return 0

fn f()
    g()

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    "tuple_element_alias": (TUPLES + SLOT + """\
type Mixed = (Tracked, i32)

fn g(p: Mixed) -> i32
    return consume(p.0)

fn f()
    g((make(1), 2))

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # The emitter types the binding through the alias, so `x` drops it.
    "tuple_element_alias_binding": (TUPLES + SLOT + """\
type Mixed = (Tracked, i32)

fn f()
    var p: Mixed = (make(1), 2)
    var x = p.0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # Gaps next to #2244.
    "tuple_destructure_moved": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    let (a, b) = p
    consume(a)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # AGAST #2282: the bindings own the elements, so each drops once.
    "tuple_destructure_kept": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    let (a, b) = p

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    # A struct source no longer destructures: a `(…)` pattern is tuples only
    # (LARB R67, test_tuple_pattern_tuples_only.py).

    "tuple_destructure_call": (TUPLES + SLOT + """\
fn f()
    let (a, b) = make_pair(1, 2)

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),

    # AGAST #3033: a name past the second (the tail) owns its element too.
    "tuple_destructure_call_three": (TUPLES + SLOT + """\
fn make_three() -> (Tracked, Tracked, Tracked)
    return (make(1), make(2), make(3))

fn f()
    let (a, b, c) = make_three()

pub fn main() -> i32
    f()
    return DROPS
""", 3, {}),

    "tuple_element_assigned_back": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    consume(p.0)
    p.0 = make(3)

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),  # ritz0 fixed by #2283

    "tuple_element_assigned_drops_old": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    p.0 = make(3)

pub fn main() -> i32
    f()
    return DROPS
""", 2, {}),  # ritz0 fixed by #2283

    "tuple_element_in_generic_field": (TUPLES + SLOT + """\
struct GenPair<A>
    pair: (A, i32)

fn f()
    var g = GenPair<Tracked> { pair: (make(1), 2) }
    consume(g.pair.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),  # ritz0 fixed by #2741 (was #2285); ritz1 by #2975

    # A binding from an element has the element's type, signedness included.
    "tuple_element_keeps_its_signedness": ("""\
pub fn main() -> i32
    var p: (u8, i32) = (200 as u8, 1)
    var x = p.0
    if x > 100
        return 1
    return 0
""", 1, {}),

    "tuple_copy_element_read": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    var n = p.1
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, {}),

    # AGAST #2240: what a `name:& T` param may still do with its referent.
    # The caller owns it, so it drops once, in the caller; each read here
    # that became a move would be a second drop. The rejected moves are in
    # THROUGH_REFERENCE.
    "borrowed_param_relent": (LENT + """\
fn g(t:& Tracked) -> i32
    set(@&t)
    let r: @Tracked = @t
    return look(@t) + r.id

fn f() -> i32
    var t = make(1)
    return g(@&t)

pub fn main() -> i32
    return f() * 10 + DROPS
""", 141, {}),

    "borrowed_param_field_reads": (LENT + """\
fn g(p:& Holder) -> i32
    set(@&p.t)
    let r: @Tracked = @p.t
    return look(@p.t) + r.id + p.t.id + p.n

fn f() -> i32
    var h = Holder { t: make(1), n: 1 }
    return g(@&h)

pub fn main() -> i32
    return f() * 10 + DROPS
""", 221, {}),

    "borrowed_param_match": (SLOT + """\
fn g(s:& Slot) -> i32
    match s
        Full(t) => return t.id
        Empty => return 0

fn f() -> i32
    var s = Slot.Full(make(4))
    return g(@&s)

pub fn main() -> i32
    return f() * 10 + DROPS
""", 41, {}),

    "borrowed_param_for": ("""\
fn g(a:& [2]Tracked) -> i32
    var n: i32 = 0
    for t in a
        n = n + t.id
    return n

fn f() -> i32
    var a: [2]Tracked = [make(1), make(2)]
    return g(@&a)

pub fn main() -> i32
    return f() * 10 + DROPS
""", 32, {}),
}

# name -> (program body, binding named in the diagnostic, {compiler: gap}).
# AGAST #2227's double drops: one value reached through a reference, and a second
# owner made of it. Each dropped twice or failed at clang, and is refused now.
BURN = """\
impl Tracked
    fn burn(self: Tracked) -> i32
        return self.id

"""

TAIL = """\

pub fn main() -> i32
    return 0
"""

THROUGH_REFERENCE = {
    "field_binding_through_reference": (SLOT + FIELDS + """\
fn g(r: @Holder) -> i32
    var x = r.t
    return consume(x)
""" + TAIL, MOVE_OUT_OF_REF, {}),
    "tuple_element_through_reference": (TUPLES + SLOT + """\
fn g(r: @(Tracked, i64)) -> i32
    var x = r.0
    return consume(x)
""" + TAIL, MOVE_OUT_OF_REF, {}),
    "address_of_into_by_value": ("fn g(t: Tracked) -> i32\n    return consume(@t)\n" + TAIL,
                                 ADDR_INTO_VALUE, {}),
    "deref_of_a_reference": ("fn g(r: @Tracked) -> i32\n    return consume(*r)\n" + TAIL,
                             MOVE_OUT_OF_REF, {}),
    "deref_of_a_pointer": ("fn g(p: *Tracked) -> i32\n    return consume(*p)\n" + TAIL,
                           MOVE_OUT_OF_REF, {}),
    "field_into_by_value": ("fn g(p: @Holder) -> i32\n    return consume(p.t)\n" + TAIL,
                            MOVE_OUT_OF_REF, {}),
    "reference_into_by_value": ("fn g(p: @Tracked) -> i32\n    return consume(p)\n" + TAIL,
                                REF_INTO_VALUE, {}),
    "reference_returned": ("fn g(p: @Tracked) -> Tracked\n    return p\n" + TAIL,
                           REF_INTO_VALUE, {}),
    "by_value_self": (BURN + "fn g(p: @Tracked) -> i32\n    return p.burn()\n" + TAIL,
                      MOVE_OUT_OF_REF, {}),
    # AGAST #2240: a `name:& T` param is lent too, bare or through a field.
    # ritz1 used to hand these to clang as invalid IR, and #2243's field
    # binding compiled and dropped the caller's value twice.
    "borrowed_param_into_call": ("fn g(t:& Tracked) -> i32\n    return consume(t)\n" + TAIL,
                                 MOVE_OUT_OF_REF, {}),
    "borrowed_param_binding": ("fn g(t:& Tracked) -> i32\n    var x = t\n    return consume(x)\n"
                               + TAIL, MOVE_OUT_OF_REF, {}),
    "borrowed_param_returned": ("fn g(t:& Tracked) -> Tracked\n    return t\n" + TAIL,
                                MOVE_OUT_OF_REF, {}),
    "borrowed_param_by_value_self": (BURN + "fn g(t:& Tracked) -> i32\n    return t.burn()\n"
                                     + TAIL, MOVE_OUT_OF_REF, {}),
    "borrowed_param_field_binding": ("""\
fn g(p:& Holder) -> i32
    var x = p.t
    return consume(x)

pub fn main() -> i32
    var h = Holder { t: make(1), n: 0 }
    g(@&h)
    return DROPS
""", MOVE_OUT_OF_REF, {}),
    "borrowed_param_field_into_call": ("fn g(p:& Holder) -> i32\n    return consume(p.t)\n"
                                       + TAIL, MOVE_OUT_OF_REF, {}),
    "borrowed_param_nested_field": (SLOT + FIELDS + """\
fn g(d:& Deep) -> Tracked
    return d.p.t
""" + TAIL, MOVE_OUT_OF_REF, {}),
}

# LARB R34 (#3366, spec §13.2): a move-only value can't be moved out of a
# global or a field of one. The global is never dropped and any function can
# read it, so nothing could track the move: #3280's two moves out of
# `GLOBAL.t` dropped one value twice. Refused at the path, with the borrow to
# write instead. #2269 had pinned the single moves as allowed.
# name -> (body, the moved path, the line of the first move, {compiler: gap}).
GLOBAL_HEAD = SLOT + FIELDS + """\
var GLOBAL: Holder

fn f() -> i32
    GLOBAL = make_holder(1)
"""

# ritz0 refuses it since #3366, ritz1 and ritz1_selfhosted since #3367.
GLOBAL_GAP = {}

GLOBAL_MOVE_OUT = {
    "two_moves_of_global_field": (GLOBAL_HEAD + """\
    var x = GLOBAL.t
    var y = GLOBAL.t
    return 0
""" + TAIL, "GLOBAL.t", "    var x = GLOBAL.t", GLOBAL_GAP),
    "one_move_of_global_field": (GLOBAL_HEAD + """\
    var x = GLOBAL.t
    return consume(x)
""" + TAIL, "GLOBAL.t", "    var x = GLOBAL.t", GLOBAL_GAP),
    "whole_global_binding": (GLOBAL_HEAD + """\
    var x = GLOBAL
    return 0
""" + TAIL, "GLOBAL", "    var x = GLOBAL", GLOBAL_GAP),
    "global_field_into_call": (GLOBAL_HEAD + """\
    return consume(GLOBAL.t)
""" + TAIL, "GLOBAL.t", "    return consume(GLOBAL.t)", GLOBAL_GAP),
    # #3367: the other by-value uses of §13.2, each its own path in ritz1's
    # ownership.ritz: a by-value `self`, `return`, a struct literal's field,
    # and a field two deep.
    "by_value_self_on_global_field": (GLOBAL_HEAD + """\
    return GLOBAL.t.burn()
""" + TAIL, "GLOBAL.t", "    return GLOBAL.t.burn()", GLOBAL_GAP),
    "global_field_returned": (GLOBAL_HEAD + """\
    return 0

fn g() -> Tracked
    return GLOBAL.t
""" + TAIL, "GLOBAL.t", "    return GLOBAL.t", GLOBAL_GAP),
    "global_field_into_struct_literal": (GLOBAL_HEAD + """\
    var h = Holder { t: GLOBAL.t, n: 0 }
    return 0
""" + TAIL, "GLOBAL.t", "    var h = Holder { t: GLOBAL.t, n: 0 }", GLOBAL_GAP),
    "nested_field_of_global": (SLOT + FIELDS + """\
var DEEP: Deep

fn f() -> Tracked
    return DEEP.p.t
""" + TAIL, "DEEP.p.t", "    return DEEP.p.t", GLOBAL_GAP),
    # A match by value owns its scrutinee, as ritz0's does: `match @SL.e` lends it.
    "match_on_global_field": (SLOT + FIELDS + """\
var SL: Slotted

fn f() -> i32
    match SL.e
        Full(x) => consume(x)
        _ => 0
""" + TAIL, "SL.e", "    match SL.e", GLOBAL_GAP),
}

# AGAST #2178: a match that owns nothing (`match @s`, a `name:& T` param, a
# place behind a pointer) binds a copy of the payload, which the scrutinee's
# owner still drops. Moving the copy out dropped it twice; it's refused now,
# at the use, on all three compilers (Rust's E0507).
# name -> (body, line of the use in the body, its column).
LENT_PAYLOAD_ROWS = {
    "borrowed_match_payload_into_call": (SLOT + """\
pub fn main() -> i32
    var s = Slot.Full(make(1))
    match @s
        Full(t) => consume(t)
        _ => pass
    return DROPS
""", 8, 28),
    "lent_param_match_payload_returned": (SLOT + """\
fn g(s:& Slot) -> Tracked
    match s
        Full(t) => return t
        _ => return make(0)
""" + TAIL, 7, 27),
    "lent_param_match_payload_into_let": (SLOT + """\
fn g(s:& Slot) -> i32
    match s
        Full(t) =>
            let y = t
            return y.id
        _ => return 0
""" + TAIL, 8, 21),
    "pointer_match_payload_into_call": (SLOT + """\
fn g(p: *Slot) -> i32
    match *p
        Full(t) => return consume(t)
        _ => return 0
""" + TAIL, 7, 35),
    # A field of the payload copy is the owner's too (ritz1's ref_through).
    "lent_param_match_payload_field_into_call": ("""\
enum Boxed
    Has(Holder)
    Nil

fn g(b:& Boxed) -> i32
    match b
        Has(h) => return consume(h.t)
        _ => return 0
""" + TAIL, 7, 34),
    "lent_param_match_payload_by_value_self": (SLOT + BURN + """\
fn g(s:& Slot) -> i32
    match s
        Full(t) => return t.burn()
        _ => return 0
""" + TAIL, 11, 27),
    # AGAST #3329: a move-only *enum* payload is lent too, on ritz1 as well
    # (it binds through emit_struct_payload_bind like a struct one).
    "borrowed_match_enum_payload_into_call": (SLOT + NESTED_SLOT + """\
pub fn main() -> i32
    var s = Nest.Has(Slot.Full(make(1)))
    match @s
        Has(x) => take_slot(x)
        _ => pass
    return DROPS
""", 15, 29),
    # A tag-only enum with a Drop impl: move-only, but no aggregate payload.
    "lent_param_match_drop_enum_payload_into_call": (DROP_FLAG + """\
fn g(s:& Flagged) -> i32
    match s
        Has(f) => return take_flag(f)
        _ => return 0
""" + TAIL, 18, 36),
    # AGAST #4602: a bare-name arm under a match that owns nothing binds a
    # copy of the owner's enum, so it is lent like a payload binding.
    "pointer_match_binding_arm_into_call": (SLOT + EAT_SLOT + """\
fn g(p: *Slot) -> i32
    match *p
        Empty => return 0
        other => return eat(other)
""" + TAIL, 11, 29),
    "lent_param_match_binding_arm_returned": (SLOT + """\
fn g(s:& Slot) -> Slot
    match s
        Empty => return Slot.Empty
        other => return other
""" + TAIL, 8, 25),
}

# AGAST #3329: a nested payload pattern (`Has(Full(x))`) under a match that
# owns nothing. It isn't a Ritz pattern: a variant's payload pattern is a name
# or `_` (LARB R76, which closed #1291), so all three compilers refuse it at
# the inner pattern, ahead of any ownership question.
NESTED_LENT_PAYLOAD = SLOT + NESTED_SLOT + """\
pub fn main() -> i32
    var s = Nest.Has(Slot.Full(make(1)))
    match @s
        Has(Full(x)) => consume(x)
        _ => pass
    return DROPS
"""

# A call returning a reference (or a value holding one) can't take a lent
# temporary: the temporary drops as the call returns, so the result would
# point at a dropped value (Aaron's ruling on AGAST #3215). Located at the
# lent argument, on all three compilers.
LENT_ESCAPE_ROWS = {
    "lent_temp_returned_ref_read": ("""\
pub fn main() -> i32
    return id(@make(5)).id
""", "@make(5)", 2, 15),
    "lent_temp_returned_ref_let": ("""\
pub fn main() -> i32
    let r = id(@make(5))
    return 0
""", "@make(5)", 2, 16),
    "lent_temp_returned_ref_method": ("""\
pub fn main() -> i32
    var s = Pick { n: 0 }
    return s.pick(@make(1)).id
""", "@make(1)", 3, 19),
    # A static call, and a struct holding a pointer: `Wrap.of` returns one.
    "lent_temp_returned_ptr_struct": ("""\
pub fn main() -> i32
    let w = Wrap.of(@&make(2))
    return 0
""", "@&make(2)", 2, 21),
}


USE_AFTER_MOVE = {
    # AGAST #2282: destructuring moves the source and defines its bindings.
    "after_destructure_source": (TUPLES + """\
pub fn main() -> i32
    var p = (make(1), 2)
    let (a, b) = p
    return look(@p.0)
""", "p", {}),

    "after_destructure_binding": (TUPLES + """\
pub fn main() -> i32
    let (a, b) = make_pair(1, 2)
    consume(a)
    return a.id
""", "a", {}),

    "after_move_into_callee": ("""\
pub fn main() -> i32
    var t = make(1)
    consume(t)
    return t.id
""", "t", {}),

    "after_move_by_binding": ("""\
pub fn main() -> i32
    var t = make(1)
    var u = t
    return t.id
""", "t", {}),

    # An array literal takes its elements (AGAST #2266).
    "after_move_into_array_literal": ("""\
pub fn main() -> i32
    var t = make(1)
    let a = [t]
    return t.id
""", "t", {}),

    # Move-only through its field.
    "holder_after_move": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    var g = h
    return h.n
""", "h", {}),

    # AGAST #2161: the second iteration would use the value the first moved.
    "move_in_loop": ("""\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        consume(t)
        i = i + 1
    return 0
""", "t", {}),

    # A `continue` path also reaches the loop head with t moved.
    "move_in_loop_continue": ("""\
pub fn main() -> i32
    var t = make(1)
    var i = 0
    while i < 2
        i = i + 1
        if i == 1
            consume(t)
            continue
        t = make(2)
    return 0
""", "t", {}),

    # Moved on the path that breaks out, so not usable after the loop.
    "after_move_then_break": ("""\
pub fn main() -> i32
    var t = make(1)
    while true
        consume(t)
        break
    return t.id
""", "t", {}),

    # AGAST #2168: the field moved out can't be used again.
    "field_after_field_move": ("""\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
    var u = h.t
    return h.t.id
""", "h.t", {}),

    # AGAST #2232: the ticket's program.
    "nested_field_moved_twice": (NESTED + """\
fn f() -> i32
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    consume(v.w.t)
    return 0

pub fn main() -> i32
    return f()
""", "v.w.t", {}),

    # A partly moved parent can't be used whole.
    "parent_after_nested_field_move": (NESTED + """\
fn eat(i: Inner2) -> i32
    return i.n

pub fn main() -> i32
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    eat(v.w)
    return 0
""", "v.w.t", {}),

    # AGAST #2242: a use overlapping a moved path, from any side.
    "nested_field_moved_in_if_arm": (NESTED3 + """\
fn f(c: i32) -> i32
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    if c == 1
        consume(v.w.t)
    return v.w.t.id

pub fn main() -> i32
    return f(1)
""", "v.w.t", {}),

    "nested_field_moved_in_loop": (nested_order("""\
    var i = 0
    while i < 2
        consume(v.w.t)
        i = i + 1
"""), "v.w.t", {}),

    # The first move is the one named, not the first field.
    "binding_after_two_nested_moves": (nested_order("""\
    consume(v.w.u)
    consume(v.w.t)
    eat_o(v)
"""), "v.w.u", {}),

    "parent_after_two_nested_moves": (nested_order("""\
    consume(v.w.u)
    consume(v.w.t)
    eat_w(v.w)
"""), "v.w.u", {}),

    "part_after_parent_move": (nested_order("""\
    eat_w(v.w)
    consume(v.w.t)
"""), "v.w", {}),

    "scalar_part_after_parent_move": (nested_order("""\
    eat_w(v.w)
    let n = v.w.n
"""), "v.w", {}),

    # A store into a moved parent doesn't make it an owner again.
    "store_into_moved_parent": (nested_order("""\
    eat_w(d.a.w)
    d.a.w.t = make(5)
""", D3), "d.a.w", {}),

    "scalar_store_into_moved_parent": (nested_order("""\
    eat_w(v.w)
    v.w.n = 5
"""), "v.w", {}),

    # The value is checked first: it moves what the store then writes into.
    "store_into_parent_its_value_moved": (NESTED3 + """\
fn from_w(i: Inner2) -> Tracked
    return make(i.n)

fn f()
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    v.w.t = from_w(v.w)

pub fn main() -> i32
    f()
    return ORDER
""", "v.w", {}),

    "store_into_binding_its_value_moved": ("""\
fn from_h(h: Holder) -> Tracked
    return make(h.n)

pub fn main() -> i32
    var h = Holder { t: make(1), n: 0 }
    h.t = from_h(h)
    return 0
""", "h", {}),

    # The first move is named at the top level too.
    "binding_after_two_field_moves": ("""\
struct TwoT
    a: Tracked
    b: Tracked

fn eat_two(x: TwoT) -> i32
    return 0

pub fn main() -> i32
    var h = TwoT { a: make(1), b: make(2) }
    consume(h.b)
    consume(h.a)
    eat_two(h)
    return 0
""", "h.b", {}),

    # AGAST #2173: `o.a.t = v` with o.a moved out is rejected (Rust's
    # E0382), so a field-of-field store never re-owns part of a moved field.
    "assign_into_moved_field": ("""\
struct Outer
    a: Holder
    m: i32

fn eat(h: Holder) -> i32
    return h.n

pub fn main() -> i32
    var o = Outer { a: Holder { t: make(1), n: 0 }, m: 0 }
    eat(o.a)
    o.a.t = make(2)
    return 0
""", "o.a", {}),

    # AGAST #2243: a binding from a field moves like any other, and the move
    # out of the field agrees with the field-move tracking.
    "field_binding_after_move": (SLOT + FIELDS + """\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    return consume(x) + consume(x)
""", "x", {}),

    "field_binding_nested_after_move": (SLOT + FIELDS + """\
pub fn main() -> i32
    var d = Deep { p: Pair { t: make(1), s: make(2) }, u: make(3) }
    var x = d.p.t
    return consume(x) + consume(x)
""", "x", {}),

    "field_after_field_binding": (SLOT + FIELDS + """\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    return consume(h.t)
""", "h.t", {}),

    "owner_after_field_binding": (SLOT + FIELDS + """\
pub fn main() -> i32
    var h = Holder { t: make(1), n: 0 }
    var x = h.t
    var y = h
    return 0
""", "h.t", {}),

    "parent_after_nested_field_binding": (SLOT + FIELDS + """\
pub fn main() -> i32
    var d = Deep { p: Pair { t: make(1), s: make(2) }, u: make(3) }
    var x = d.p.t
    var y = d.p
    return 0
""", "d.p.t", {}),

    # AGAST #2257: a binding from a method call moves like any other.
    "method_binding_after_move": (METHODS + """\
pub fn main() -> i32
    var t = Tracked.new(1)
    return consume(t) + consume(t)
""", "t", {}),

    # AGAST #2177: a payload binding owns the payload, so it moves once.
    "payload_after_move": (SLOT + """\
pub fn main() -> i32
    var s = Slot.Full(make(1))
    match s
        Full(t) =>
            let k = consume(t) + consume(t)
        _ => pass
    return 0
""", "t", {}),

    # AGAST #2178: a `let` from a match is typed by its arms, so it moves.
    "after_move_of_a_let_from_match": (SLOT + """\
pub fn main() -> i32
    var s = Slot.Full(make(1))
    let u = match s
        Full(t) => t
        _ => make(2)
    consume(u)
    return u.id
""", "u", {}),

    "tuple_element_after_move": (TUPLES + """\
pub fn main() -> i32
    var p = (make(1), 2)
    return consume(p.0) + consume(p.0)
""", "p.0", {}),

    "tuple_element_binding_after_move": (TUPLES + """\
pub fn main() -> i32
    var p = (make(1), 2)
    var x = p.0
    return consume(x) + consume(x)
""", "x", {}),

    "tuple_after_element_move": (TUPLES + """\
pub fn main() -> i32
    var p = (make(1), 2)
    consume(p.0)
    var q = p
    return 0
""", "p.0", {}),

    "tuple_in_field_after_element_move": (TUPLES + """\
pub fn main() -> i32
    var v = WithPair { pair: (make(1), make(2)), u: make(3) }
    consume(v.pair.0)
    var q = v.pair
    return 0
""", "v.pair.0", {}),
}


# ---- the harness: one test per table per compiler (AGAST #3521) -------------
#
# Each table is one test per compiler, not one per row: 846 collected tests
# cost more in xdist collection, dispatch and reporting than their compiles
# (#3453 F1).  Rows compile together through batching.run_rows /
# refuse_rows, a few dozen to a program.  A batch only passes a row: a row
# it has no answer for, or whose answer fails the row's check, is compiled
# on its own and checked again, so a failure is always the row's own, and
# the test's message names each failing row (`row <name>: ...`).
#
# A row with a gap ticket for this compiler is a strict xfail: it is run on
# its own, and the test fails if it passes, so the room that closes the gap
# has to flip it.  It is never batched: a row expected to fail would only
# split its batch.


def _gap_rows(table, compiler):
    """{name: gap ticket} of `table`'s rows this compiler is known to miss."""
    return {name: row[-1][compiler] for name, row in table.items()
            if isinstance(row[-1], dict) and compiler in row[-1]}


def _verdict(failures, gaps, passed, compiler):
    """Fail naming every row that failed, or that passed with a gap open."""
    msgs = [f"row {name}: {why}" for name, why in sorted(failures.items()) if name not in gaps]
    msgs += [f"row {name}: XPASS(strict) AGAST #{gaps[name]}: {compiler} passes it now; "
             f"drop the gap" for name in sorted(passed & set(gaps))]
    assert not msgs, f"{compiler}: {len(msgs)} row(s) failed:\n" + "\n".join(msgs)


def _check_table(compiler, tmp_path, table, program, check_batched, check_alone, kind,
                 at=lambda name: None):
    """Check every row of `table` on `compiler`; fail naming each row that fails.

    `program(name)` is the row's whole source.  `kind` is "run" or "refused".
    "run": `check_batched(name, exit code)` and `check_alone(name, workdir)`.
    "refused": `check_batched(name, diagnostics, "line:col" of its mark)` and
    `check_alone(name, workdir)`; `at(name)` is the (line, col) its mark goes
    at, or None.  Each returns None for a pass, else why it failed.
    """
    gaps = _gap_rows(table, compiler)
    names = sorted(table)
    batched = [n for n in names if n not in gaps]
    answers = {}
    if batching.enabled():
        for k in range(0, len(batched), batching.CHUNK):
            chunk = batched[k:k + batching.CHUNK]
            work = tmp_path / f"batch{k}"
            if kind == "run":
                got = batching.run_rows(compiler, [program(n) for n in chunk], _build, work,
                                        compile=_compile_only)
            else:
                got = batching.refuse_rows(compiler, [_marked(program(n), at(n)) for n in chunk],
                                           _compile_only, work)
            answers.update(zip(chunk, got))
    failures, passed = {}, set()
    for i, name in enumerate(names):
        got = answers.get(name)
        if got is not None:
            ok = check_batched(name, got) if kind == "run" else check_batched(name, *got)
            if ok is None:
                passed.add(name)
                continue
        work = tmp_path / f"row{i}"
        work.mkdir()
        why = check_alone(name, work)
        if why is None:
            passed.add(name)
        else:
            failures[name] = why
    _verdict(failures, gaps, passed, compiler)


def _marked(program, at):
    """`program` with batching's mark at (line, col), so the batch says where it went."""
    if at is None:
        return program
    line, col = at
    lines = program.split("\n")
    lines[line - 1] = lines[line - 1][:col - 1] + batching.MARK + lines[line - 1][col - 1:]
    return "\n".join(lines)


def _compile(compiler, src, ll, cwd):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=cwd, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300, check=False)


def _compile_only(compiler, src, work):
    """batching's `compile`: (returncode, output), the module in work/main.ll."""
    comp = _compile(compiler, src, work / "main.ll", work)
    return comp.returncode, comp.stdout + comp.stderr


def _build(compiler, src, work):
    """batching's `build`: (ok, output, exe) for the program at `src`."""
    ll, exe = work / "main.ll", work / "main"
    comp = _compile(compiler, src, ll, work)
    out = comp.stdout + comp.stderr
    if comp.returncode != 0 or not ll.exists():
        return False, out, None
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=work, capture_output=True, text=True)
    if link.returncode != 0:
        return False, out + link.stderr, None
    return True, out, exe


def _write(tmp_path, body):
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + body)
    return src


def _refusal(compiler, work, body):
    """(output, None) for `body` compiled alone if it was refused cleanly, else (None, why)."""
    comp = _compile(compiler, _write(work, body), work / "main.ll", work)
    out = comp.stdout + comp.stderr
    if comp.returncode == 0:
        return None, f"accepted it:\n{out[-1000:]}"
    if "Traceback" in out:
        return None, out[-2000:]
    return out, None


def _refused_table(compiler, tmp_path, table, body, wants, at=lambda name: None):
    """A refusal table: `wants(name, output, "line:col" or None)` is None or why not."""
    def alone(name, work):
        out, why = _refusal(compiler, work, body(name))
        if why is not None:
            return why
        loc = at(name)
        return wants(name, out, loc and f"{loc[0]}:{loc[1]}")

    _check_table(compiler, tmp_path, table, lambda n: PRELUDE + body(n),
                 lambda name, diag, mark: wants(name, diag, mark), alone, "refused", at)


def _ritz1(request, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_free_count(request, tmp_path, compiler):
    """Every CASES row runs and exits with the free count the spec gives it."""
    _ritz1(request, compiler)

    def check_code(name, rc):
        expected = CASES[name][1]
        return None if rc == expected else f"exit {rc}, spec says {expected}"

    def alone(name, work):
        good, out, exe = _build(compiler, _write(work, CASES[name][0]), work)
        if not good:
            return f"failed to compile or link:\n{out[-2000:]}"
        rc = subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode
        return check_code(name, rc)

    _check_table(compiler, tmp_path, CASES, lambda n: PRELUDE + CASES[n][0], check_code, alone,
                 "run")


def _has(message):
    return lambda out: None if message in out else f"no {message!r} in:\n{out[-2000:]}"


def _located_at(out, loc):
    """None if a diagnostic in `out` is at `loc` ("line:col"), else why not."""
    return None if f":{loc}:" in out else f"nothing at :{loc}: in:\n{out[-2000:]}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_second_owner_through_a_reference_rejected(request, tmp_path, compiler):
    _ritz1(request, compiler)
    _refused_table(compiler, tmp_path, THROUGH_REFERENCE, lambda n: THROUGH_REFERENCE[n][0],
                   lambda name, out, loc: _has(THROUGH_REFERENCE[name][1])(out))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_move_out_of_a_non_owning_match_payload_rejected(request, tmp_path, compiler):
    _ritz1(request, compiler)

    def wants(name, out, loc):
        # Located at the use: its line in the body, after the prelude.
        return _has(MOVE_OUT_OF_REF)(out) or _located_at(out, loc)

    def at(name):
        _, line, col = LENT_PAYLOAD_ROWS[name]
        return PRELUDE.count("\n") + line, col

    _refused_table(compiler, tmp_path, LENT_PAYLOAD_ROWS, lambda n: LENT_PAYLOAD_ROWS[n][0],
                   wants, at)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_nested_payload_of_a_non_owning_match_still_refused(request, tmp_path, compiler):
    """R76: refused at the inner pattern, `Full` (line 15, column 13 of the body)."""
    _ritz1(request, compiler)
    out, why = _refusal(compiler, tmp_path, NESTED_LENT_PAYLOAD)
    assert why is None, f"{compiler} {why}"
    at = PRELUDE.count("\n") + 15
    message = ("a variant's payload pattern is a name or `_`: "
               "match the inner value in its own `match`")
    assert f":{at}:13: " in out and message in out, out[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_use_after_move_rejected(request, tmp_path, compiler):
    _ritz1(request, compiler)
    _refused_table(compiler, tmp_path, USE_AFTER_MOVE, lambda n: USE_AFTER_MOVE[n][0],
                   lambda name, out, loc: _has(f"use of moved value: `{USE_AFTER_MOVE[name][1]}`")(out))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_lent_temp_into_returned_reference_refused(request, tmp_path, compiler):
    _ritz1(request, compiler)

    def wants(name, out, loc):
        # Located at the lent argument: its line in the body, after the prelude.
        return _has(lent_temp_escapes(LENT_ESCAPE_ROWS[name][1]))(out) or _located_at(out, loc)

    def at(name):
        _, _, line, col = LENT_ESCAPE_ROWS[name]
        return PRELUDE.count("\n") + LENT_ESCAPE.count("\n") + line, col

    _refused_table(compiler, tmp_path, LENT_ESCAPE_ROWS,
                   lambda n: LENT_ESCAPE + LENT_ESCAPE_ROWS[n][0], wants, at)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_move_out_of_a_global_refused(request, tmp_path, compiler):
    _ritz1(request, compiler)

    def wants(name, out, loc):
        path = GLOBAL_MOVE_OUT[name][1]
        # Located at the path: its line and column in the body, after the prelude.
        return _has(move_out_of_global(path.split(".")[0], path))(out) or _located_at(out, loc)

    def at(name):
        body, path, use, _ = GLOBAL_MOVE_OUT[name]
        return PRELUDE.count("\n") + body.splitlines().index(use) + 1, use.index(path) + 1

    _refused_table(compiler, tmp_path, GLOBAL_MOVE_OUT, lambda n: GLOBAL_MOVE_OUT[n][0], wants, at)


# ---------------------------------------------------------------------------
# Vec<T> and String drops (AGAST #2159).
#
# Enabling their Drop impls makes the compiler free the buffer: at block end,
# before return, when the value is reassigned, and in the callee that took it
# by value. The manual `vec_drop` / `string_drop` call sites go away with it
# (`test_no_manual_vec_or_string_drops`); a manual drop left in place is a
# free the compiler can repeat on the owning binding, and on a moved-from
# binding it frees a buffer the callee already freed.
#
# These rows count allocations and frees through an Allocator, as
# ritzlib/tests/test_allocator.ritz does: `live_bytes` returns to 0 only when
# every block the collection took was handed back exactly once, so a leak
# leaves it positive and a double free drives it negative.
# ---------------------------------------------------------------------------

VEC_PRELUDE = """\
import ritzlib.memory
import ritzlib.gvec
import ritzlib.string
import ritzlib.option

# An Arena behind a counting Allocator. ctx points at one of these.
struct CountingArena
    arena: Arena
    allocs: i64
    frees: i64
    live_bytes: i64

fn counting_alloc(ctx: *u8, len: i64) -> *u8
    let c: *CountingArena = ctx as *CountingArena
    let p: *u8 = c.arena.alloc(len)
    if p != null
        c.allocs += 1
        c.live_bytes += len
    return p

fn counting_free(ctx: *u8, p: *u8, len: i64) -> i32
    let c: *CountingArena = ctx as *CountingArena
    c.frees += 1
    c.live_bytes -= len
    return 0

fn counting_new(c: *CountingArena, size: i64) -> Allocator
    c.arena = arena_new(size)
    c.allocs = 0
    c.frees = 0
    c.live_bytes = 0
    return Allocator { ctx: c as *u8, alloc: counting_alloc, free: counting_free }

# Read after the value's scope has ended. 2/3/4 name the count that was wrong.
fn settle(c: @CountingArena, want_allocs: i64, want_frees: i64) -> i32
    if c.allocs != want_allocs
        return 2
    if c.frees != want_frees
        return 3
    if c.live_bytes != 0
        return 4
    return 0
"""

# Each body uses this boilerplate: an arena, then the scenario, then settle.
VEC_MAIN = """\

pub fn main() -> i32
    var c: CountingArena
    var a: Allocator = counting_new(@c, 65536)
    if build(@a) != {want}
        return 1
    return settle(@c, {allocs}, {frees})
"""


def _vec_case(body, want, allocs, frees):
    return VEC_PRELUDE + body + VEC_MAIN.format(want=want, allocs=allocs, frees=frees)


VEC_CASES = {
    # A Vec of bytes built with room for 8 stays at one allocation; the drop
    # at the end of `build` returns that block.
    "vec_scope_end": _vec_case("""\
fn build(a: *Allocator) -> i64
    var v: Vec<u8> = vec_with_cap_in<u8>(a, 8)
    v.push(1)
    return v.len()
""", 1, 1, 1),

    # `consume_vec` takes ownership: it drops the Vec, and the moved-from
    # binding in `build` is not dropped again. A copy-semantics compiler
    # drops both, so frees is 2 and live_bytes goes negative.
    "vec_move_into_callee": _vec_case("""\
fn consume_vec(v: Vec<u8>) -> i64
    return v.len()

fn build(a: *Allocator) -> i64
    var v: Vec<u8> = vec_with_cap_in<u8>(a, 8)
    v.push(7)
    return consume_vec(v)
""", 1, 1, 1),

    # Ownership moves out with the returned value; the caller's binding drops
    # it once, and the callee does not drop the moved-from local.
    "vec_return_from_fn": _vec_case("""\
fn make_vec(a: *Allocator) -> Vec<u8>
    var v: Vec<u8> = vec_with_cap_in<u8>(a, 8)
    v.push(3)
    return v

fn build(a: *Allocator) -> i64
    var got: Vec<u8> = make_vec(a)
    return got.len()
""", 1, 1, 1),

    # The old value is dropped before the new one is assigned; the new one is
    # dropped at block end. Two allocations, two frees.
    "vec_reassignment": _vec_case("""\
fn build(a: *Allocator) -> i64
    var v: Vec<u8> = vec_with_cap_in<u8>(a, 8)
    v = vec_with_cap_in<u8>(a, 16)
    return v.cap()
""", 16, 2, 2),

    # String owns its bytes through a Vec<u8>: one allocation, one free.
    "string_scope_end": _vec_case("""\
fn build(a: *Allocator) -> i64
    var s: String = string_with_cap_in(a, 10)
    s.push_str("hi")
    return s.len()
""", 2, 1, 1),

    # String moves into a callee like any other move-only type.
    "string_move_into_callee": _vec_case("""\
fn consume_string(s: String) -> i64
    return s.len()

fn build(a: *Allocator) -> i64
    var s: String = string_with_cap_in(a, 10)
    s.push_str("hi")
    return consume_string(s)
""", 2, 1, 1),

    # ...and moves out with a returned value.
    "string_return_from_fn": _vec_case("""\
fn make_string(a: *Allocator) -> String
    var s: String = string_with_cap_in(a, 10)
    s.push_str("ok")
    return s

fn build(a: *Allocator) -> i64
    var got: String = make_string(a)
    return got.len()
""", 2, 1, 1),

    # An arm body is an assignment expression (`found = path`), not an
    # assignment statement. The payload moves into `found`; the arm must not
    # drop `path` at its end too (AGAST #2159; the emitter clears the
    # moved-from binding's drop flag at the mark). Two allocations, two
    # frees.
    "string_match_arm_assignment": _vec_case("""\
fn pick(a: *Allocator) -> Option<String>
    return Some(string_with_cap_in(a, 8))

fn build(a: *Allocator) -> i64
    var found: String = string_with_cap_in(a, 16)
    match pick(a)
        Some(path) => found = path
        None => return -1
    return found.len()
""", 0, 2, 2),

    # `.unwrap()` hands the Some/Ok payload to the caller, so the carrier is
    # moved too. Borrowed, its scope-end drop and the payload binding would
    # both free the buffer (AGAST #2159, #4490).
    "string_unwrap_moves_carrier": _vec_case("""\
fn pick(a: *Allocator) -> Option<String>
    return Some(string_with_cap_in(a, 8))

fn build(a: *Allocator) -> i64
    var o: Option<String> = pick(a)
    let s: String = o.unwrap()
    return s.len()
""", 0, 1, 1),

    # `e?` consumes its carrier even as a statement: the Err payload moves
    # into the returned Err, and dropping the carrier at statement end on top
    # of that frees it twice (AGAST #2159; the Err payload is a String).
    "string_try_statement_moves_carrier": _vec_case("""\
fn inner(a: *Allocator) -> Result<i32, String>
    return Err(string_with_cap_in(a, 8))

fn outer(a: *Allocator) -> Result<i32, String>
    inner(a)?
    return Ok(0)

fn build(a: *Allocator) -> i64
    match outer(a)
        Ok(v) => return v as i64
        Err(e) => return e.len()
""", 0, 1, 1),
}

# Rows this compiler is known to miss, as {row: AGAST ticket}. A strict
# xfail, as in the main table: run alone, it must fail, and one that passes
# fails the test until the entry is dropped.
VEC_GAPS = {
}


def _build_pkg(compiler, tmp_path, name, program):
    """Build `program` as a package via build.py, which compiles and links
    every transitively imported module. Returns (CompletedProcess, exe)."""
    pkg = tmp_path / f"{name}_{compiler}"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text(program)
    (pkg / "ritz.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\n'
    )
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT),
               RITZ_BUILD_CACHE_DIR=str(pkg / ".build-cache"))
    proc = subprocess.run(
        ["python3", str(RITZ_ROOT / "build.py"), "build", str(pkg),
         "--compiler", compiler],
        cwd=RITZ_ROOT, env=env, capture_output=True, text=True, timeout=600,
    )
    return proc, pkg / "build" / "debug" / name


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_vec_string_free_count(request, tmp_path, compiler):
    """Vec<T> and String free their buffer exactly once (AGAST #2159)."""
    _ritz1(request, compiler)
    gaps = {name: row[compiler] for name, row in VEC_GAPS.items()
            if compiler in row}
    failures = []
    for name in sorted(VEC_CASES):
        proc, exe = _build_pkg(compiler, tmp_path, name, VEC_CASES[name])
        why = None
        if proc.returncode != 0 or not exe.exists():
            why = (f"failed to build:\n"
                   f"{proc.stdout[-1500:]}\n{proc.stderr[-1500:]}")
        else:
            rc = subprocess.run([str(exe)], capture_output=True, timeout=60,
                               check=False).returncode
            if rc != 0:
                why = (f"exit {rc} (1 wrong len, 2 alloc count, 3 free count, "
                       f"4 bytes left live)")
        if name in gaps:
            if why is None:
                failures.append(f"row {name}: XPASS(strict) AGAST #{gaps[name]}: "
                                f"{compiler} passes it now; drop the gap")
        elif why is not None:
            failures.append(f"row {name}: {why}")
    assert not failures, f"{compiler}: {len(failures)} row(s) failed:\n" + "\n".join(failures)


# The manual call that is now a use-after-move: `v` moved into `consume`, so
# `v.deinit()` would free the buffer `consume`'s drop already freed.
MOVE_THEN_MANUAL_DROP = """\
import ritzlib.gvec

fn consume(v: Vec<u8>) -> i64
    v.len()

pub fn main() -> i32
    var v: Vec<u8> = vec_new<u8>()
    consume(v)
    v.deinit()
    return 0
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_manual_drop_after_move_refused(request, tmp_path, compiler):
    """A manual drop on a moved-from Vec is refused, not silently doubled."""
    _ritz1(request, compiler)
    proc, _ = _build_pkg(compiler, tmp_path, "move_then_manual_drop",
                         MOVE_THEN_MANUAL_DROP)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted a manual drop after a move:\n{out[-2000:]}"
    # `@&v` is a borrow of a moved value: ritz0 says "use of moved value",
    # ritz1 "cannot borrow ... value has been moved". Both name `v`.
    assert "moved" in out and "`v`" in out, out[-3000:]


# Since AGAST #4537 neither `vec_drop` nor `string_drop` exists: both are
# `impl` methods (`Vec.deinit`, `String.deinit`) now. This tree-wide scan names
# any surviving call, which would not compile in any case. A `deinit()` on a
# place reached through a raw pointer (`vp.deinit()`) is the remaining manual
# API: the compiler never drops a value in raw memory (AGAST #2159).
MANUAL_DROP_CALL = re.compile(r"\b(vec_drop|string_drop)\s*(<[^<>]*>)?\s*\(")
BUILD_DIRS = {".ritz-cache", ".build-cache", "build", "target"}


@pytest.mark.unit
def test_no_manual_vec_or_string_drops():
    """No source in the tree calls vec_drop/string_drop by hand (AGAST #2159)."""
    offenders = []
    for path in sorted(RITZ_ROOT.rglob("*")):
        if path.suffix not in (".ritz", ".py"):
            continue
        rel = path.relative_to(RITZ_ROOT).as_posix()
        if BUILD_DIRS & set(path.relative_to(RITZ_ROOT).parts[:-1]):
            continue
        for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            if MANUAL_DROP_CALL.search(line):
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "manual String/Vec drops are now a double free; delete them "
        f"({len(offenders)} left):\n" + "\n".join(offenders)
    )
