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
elements (a strict xfail citing #1526, ritz1's missing tuple literals).
AGAST #2168 added moves out of a field, closed for ritz1; ritz0's by AGAST
#2171. AGAST #2174 added a match owning its scrutinee, with payload
bindings owning the payload, closed for ritz1; ritz0's by AGAST #2177.
AGAST #2173 added assigning a move-only field (the old value drops),
closed for both. AGAST #2257 added bindings and temporaries from a method
call, whose temporaries ritz0 drops and ritz1 doesn't yet (#2262). AGAST
#2243 added bindings from a field, which ritz1 already got right. AGAST
#2244 added moves out of a tuple element, closed for ritz0; ritz1 has no
tuples to move out of yet (#1526).
AGAST #2261 closed ritz0's double evaluation of a method receiver, which
dropped two values for one call.
A new gap goes in as a strict xfail, so the room that closes it has to flip
it.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
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
        ORDER = ORDER * 10 + self.id

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

# ritz1's array literals don't move their elements.
ARRAY_ELEMENT_GAP = {"ritz1": 2266, "ritz1_selfhosted": 2266}

# Unannotated bindings ritz1 can't type yet.
BINDING_TYPE_GAP = {"ritz1": 2267, "ritz1_selfhosted": 2267}

# A value moved out through a reference: what that means is #2227's question.
THROUGH_REFERENCE_GAP = {c: 2227 for c in COMPILERS}

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

# ritz1 has no tuples yet.
NO_TUPLES = {"ritz1": 1526, "ritz1_selfhosted": 1526}


def tuple_gap(ticket):
    """A ritz0 gap in something ritz1 can't compile either (#1526)."""
    return {"ritz0": ticket, **NO_TUPLES}

# Method temporaries ritz1 doesn't drop yet.
METHOD_TEMP_GAP = {"ritz1": 2262, "ritz1_selfhosted": 2262}

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
""", 3, {"ritz1": 2242, "ritz1_selfhosted": 2242}),

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
        Empty => 0
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
""", 2, METHOD_TEMP_GAP),

    # So does a literal of fields nobody takes (it leaked on ritz0 before).
    "field_element_array_temporary": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    [h.t]
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, ARRAY_ELEMENT_GAP),

    "field_element_tuple_temporary": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    (h.t, 1)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {"ritz1": 1526, "ritz1_selfhosted": 1526}),

    "field_element_array_binding": (SLOT + FIELDS + """\
fn f() -> i32
    var h = Holder { t: make(1), n: 0 }
    var a: [1]Tracked = [h.t]
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, ARRAY_ELEMENT_GAP),

    "field_binding_pointer_member": (SLOT + FIELDS + """\
fn f() -> i32
    var t = make(1)
    var r = Refs { p: @t, n: 0 }
    var y = r.p
    return y.id - 1

pub fn main() -> i32
    f()
    return DROPS
""", 1, BINDING_TYPE_GAP),

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
""", 1, BINDING_TYPE_GAP),

    # Neighbours #2243 doesn't reach: `x` stays unknown, so a copy.
    "field_binding_of_array_element": (SLOT + FIELDS + """\
fn f() -> i32
    var a: [1]Tracked = [make(1)]
    var x = a[0]
    consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {"ritz0": 2268, "ritz1": 2268, "ritz1_selfhosted": 2268}),

    "field_binding_of_global": (SLOT + FIELDS + """\
var GLOBAL: Holder

fn f() -> i32
    GLOBAL = make_holder(1)
    var x = GLOBAL.t
    consume(x)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, {"ritz0": 2269}),

    # `var x = r.t` through `@T` copies the referent, so its owner and `x`'s new
    # owner both drop it. #2243 only removes the third drop, `x`'s own.
    "field_binding_through_reference": (SLOT + FIELDS + """\
fn g(r: @Holder) -> i32
    var x = r.t
    return consume(x)

fn f() -> i32
    var h = make_holder(1)
    g(@h)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 1, THROUGH_REFERENCE_GAP),

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
""", 1, METHOD_TEMP_GAP),

    "method_temp_field": (METHODS + """\
fn f() -> i32
    var i = Tracked.new(1).id
    return i

pub fn main() -> i32
    f()
    return DROPS
""", 1, METHOD_TEMP_GAP),

    "method_temp_lent_argument": (METHODS + """\
fn f() -> i32
    var s = Sink { n: 0 }
    return s.look(Tracked.new(1))

pub fn main() -> i32
    f()
    return DROPS
""", 1, METHOD_TEMP_GAP),

    # One evaluation, so one value to drop (AGAST #2261).
    "method_temp_receiver": (METHODS + """\
fn f() -> i32
    return Tracked.new(1).peek()

pub fn main() -> i32
    f()
    return DROPS
""", 1, METHOD_TEMP_GAP),

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
    var i = 0
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
    var i = 0
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
""", 12, {"ritz1": 1526, "ritz1_selfhosted": 1526}),

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

    # Lent to an `@T` parameter, the temporary is still nobody's: it drops
    # once the `let` statement ends. inner = 1 * 10 + 2.
    "temporary_lent": ("""\
fn peek(t: @Tracked) -> i32
    return t.id

fn f() -> i32
    let n = peek(make(2))
    return DROPS * 10 + n

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 13, {}),

    # A `return` statement's temporary drops after the value is evaluated
    # (DROPS is still 0 there), before the function returns. inner = 2.
    "temporary_in_return": ("""\
fn peek(t: @Tracked) -> i32
    return t.id

fn f() -> i32
    return peek(make(2)) + DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner * 10 + DROPS
""", 21, {}),

    # Moving an outer binding inside a loop is fine when every path back to
    # the loop head assigns it again: consume drops ids 0, 1 and 2, the
    # scope end drops id 3.
    "loop_move_reassigned": ("""\
fn f()
    var t = make(0)
    var i = 0
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
""", 142, {"ritz1": 2242, "ritz1_selfhosted": 2242}),

    # Only that field moves: v.w's other fields still drop...
    "nested_field_move_rest_dropped": (NESTED + """\
fn f()
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)

pub fn main() -> i32
    f()
    return ORDER
""", 12, {"ritz1": 2242, "ritz1_selfhosted": 2242}),

    # ...and stay usable.
    "nested_field_move_sibling_readable": (NESTED + """\
fn f() -> i32
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    return v.w.n

pub fn main() -> i32
    return f()
""", 3, {"ritz1": 2242, "ritz1_selfhosted": 2242}),

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
    var i = 0
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
    var i = 0
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
    var i = 1
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

    # AGAST #2177 from here on (ritz1's cases from #2174, now shared).
    # A match moves its scrutinee (ritz0's rule), and the match
    # owns it.  A payload binding takes the payload and drops at the end of
    # its arm unless moved; an arm that binds nothing drops the scrutinee.
    # Each tens digit is the count inside f, before its `return`.
    "match_stmt_payload_drops": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Full(t) => t.id
        _ => 0
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 11, {}),

    "match_stmt_unbound_arm_drops": (SLOT + """\
fn f() -> i32
    var s = Slot.Full(make(1))
    match s
        Empty => 1
        _ => 2
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
        Full(_) => 1
        Empty => 2
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
        _ => 0
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
        Empty => 1
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
        Full(t) => t.id
        _ => 0
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
        Full(t) => t.id
        _ => 0
    match full(2)
        Empty => 1
        _ => 2
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
        Some(t) => t.id
        None => 0
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
            Full(t) => t.id
            _ => 0
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
        Full(t) => 1
        _ => 0
    return DROPS * 10

pub fn main() -> i32
    let inner = f()
    return inner + DROPS
""", 1, {}),

    # AGAST #2244: the ticket's program. The tuple's drop skips the element.
    "tuple_element_moved": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    "tuple_element_moved_let": (TUPLES + SLOT + """\
fn f()
    let p = (make(1), 2)
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    "tuple_element_sibling_still_drops": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    # The moved element drops in `consume`, then the rest, in order.
    "tuple_element_sibling_order": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2), make(3))
    consume(p.1)

pub fn main() -> i32
    f()
    return ORDER
""", 213, NO_TUPLES),

    "tuple_element_both_moved": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    consume(p.0)
    consume(p.1)

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_element_binding": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    var x = p.0
    consume(x)

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    # The binding owns it now, and drops it.
    "tuple_element_binding_unmoved": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    var x = p.0

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    "tuple_element_param": (TUPLES + SLOT + """\
fn g(p: (Tracked, Tracked)) -> i32
    return consume(p.1)

fn f()
    g(make_pair(1, 2))

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_element_from_call": (TUPLES + SLOT + """\
fn f()
    var p = make_pair(1, 2)
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

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
""", 1, NO_TUPLES),

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
""", 1, NO_TUPLES),

    "tuple_element_returned": (TUPLES + SLOT + """\
fn g() -> Tracked
    var p = (make(1), make(2))
    return p.0

fn f()
    consume(g())

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_element_tail": (TUPLES + SLOT + """\
fn g() -> Tracked
    var p = (make(1), make(2))
    p.1

fn f()
    consume(g())

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    # Reassigning drops what is left of the old value; the new one is whole.
    "tuple_reassigned_after_element_move": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    consume(p.0)
    p = (make(3), make(4))

pub fn main() -> i32
    f()
    return DROPS
""", 4, NO_TUPLES),

    # A path through a tuple.
    "tuple_element_in_field": (TUPLES + SLOT + """\
fn f()
    var v = WithPair { pair: (make(1), make(2)), u: make(3) }
    consume(v.pair.0)

pub fn main() -> i32
    f()
    return DROPS
""", 3, NO_TUPLES),

    "tuple_element_in_field_binding": (TUPLES + SLOT + """\
fn f()
    var v = WithPair { pair: (make(1), make(2)), u: make(3) }
    var x = v.pair.1
    consume(x)

pub fn main() -> i32
    f()
    return DROPS
""", 3, NO_TUPLES),

    "tuple_in_field_whole_after_element_is_part": (TUPLES + SLOT + """\
fn f()
    var v = WithPair { pair: (make(1), make(2)), u: make(3) }
    consume(v.pair.0)
    consume(v.u)

pub fn main() -> i32
    f()
    return DROPS
""", 3, NO_TUPLES),

    # A path through a tuple into a struct.
    "tuple_field_of_an_element": (TUPLES + SLOT + """\
fn f()
    var p = (InElement { t: make(1), s: make(2) }, 7)
    consume(p.0.t)

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_in_tuple": (TUPLES + SLOT + """\
fn f()
    var p = ((make(1), make(2)), make(3))
    consume((p.0).1)

pub fn main() -> i32
    f()
    return DROPS
""", 3, NO_TUPLES),

    # What the element's type feeds.
    "tuple_element_by_value_receiver": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    p.0.burn()

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_element_method_temporary": (TUPLES + SLOT + """\
fn f() -> i32
    var p = (make(1), 2)
    p.0.again()
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_element_match": (TUPLES + SLOT + """\
fn f()
    var p = (Slot.Full(make(1)), make(2))
    match p.0
        Full(t) => consume(t)
        _ => 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_element_match_wildcard": (TUPLES + SLOT + """\
fn f()
    var p = (Slot.Full(make(1)), make(2))
    match p.0
        _ => 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_element_of_temporary": (TUPLES + SLOT + """\
fn f()
    consume(make_mixed(1).0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    "tuple_element_of_temporary_binding": (TUPLES + SLOT + """\
fn f()
    var x = make_mixed(1).0

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    "tuple_element_into_literal": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), make(2))
    var q = (p.0, 3)

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    "tuple_element_into_literal_temporary": (TUPLES + SLOT + """\
fn f() -> i32
    var p = (make(1), make(2))
    (p.0, 3)
    return 0

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

    # Lending an element takes its address, which moves nothing.
    "tuple_element_lent": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    look(@p.0)
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    "tuple_element_lending_receiver": (TUPLES + SLOT + """\
fn g(p: (Tracked, i32)) -> i32
    return p.0.peek()

fn f()
    g((make(1), 2))

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

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
""", 1, NO_TUPLES),

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
""", 1, NO_TUPLES),

    "tuple_element_for": (TUPLES + SLOT + """\
fn f()
    var p = ([make(1), make(2)], 3)
    for v in p.0
        consume(v)

pub fn main() -> i32
    f()
    return DROPS
""", 2, NO_TUPLES),

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
""", 6, NO_TUPLES),

    "tuple_element_before_break": (TUPLES + SLOT + """\
fn f()
    while true
        var p = (make(1), 2)
        consume(p.0)
        break

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

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
""", 2, NO_TUPLES),

    "tuple_element_alias": (TUPLES + SLOT + """\
type Mixed = (Tracked, i32)

fn g(p: Mixed) -> i32
    return consume(p.0)

fn f()
    g((make(1), 2))

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    # The emitter types the binding through the alias, so `x` drops it.
    "tuple_element_alias_binding": (TUPLES + SLOT + """\
type Mixed = (Tracked, i32)

fn f()
    var p: Mixed = (make(1), 2)
    var x = p.0

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),

    # What a move through a reference means is #2227's question.
    "tuple_element_through_reference": (TUPLES + SLOT + """\
fn g(r: @(Tracked, i64)) -> i32
    var x = r.0
    return consume(x)

fn f()
    var p = (make(1), 2)
    g(@p)

pub fn main() -> i32
    f()
    return DROPS
""", 1, THROUGH_REFERENCE_GAP),

    # Gaps next to #2244.
    "tuple_destructure_moved": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    let (a, b) = p
    consume(a)

pub fn main() -> i32
    f()
    return DROPS
""", 1, tuple_gap(2282)),

    "tuple_destructure_call": (TUPLES + SLOT + """\
fn f()
    let (a, b) = make_pair(1, 2)

pub fn main() -> i32
    f()
    return DROPS
""", 2, tuple_gap(2282)),

    "tuple_element_assigned_back": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    consume(p.0)
    p.0 = make(3)

pub fn main() -> i32
    f()
    return DROPS
""", 2, tuple_gap(2283)),

    "tuple_element_assigned_drops_old": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    p.0 = make(3)

pub fn main() -> i32
    f()
    return DROPS
""", 2, tuple_gap(2283)),

    "tuple_element_in_generic_field": (TUPLES + SLOT + """\
struct GenPair<A>
    pair: (A, i32)

fn f()
    var g = GenPair<Tracked> { pair: (make(1), 2) }
    consume(g.pair.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, tuple_gap(2285)),

    # A binding from an element has the element's type, signedness included.
    "tuple_element_keeps_its_signedness": ("""\
pub fn main() -> i32
    var p: (u8, i32) = (200 as u8, 1)
    var x = p.0
    if x > 100
        return 1
    return 0
""", 1, NO_TUPLES),

    "tuple_copy_element_read": (TUPLES + SLOT + """\
fn f()
    var p = (make(1), 2)
    var n = p.1
    consume(p.0)

pub fn main() -> i32
    f()
    return DROPS
""", 1, NO_TUPLES),
}

# name -> (program body, binding named in the diagnostic, {compiler: gap}).
USE_AFTER_MOVE = {
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

    # AGAST #2232: the ticket's program. ritz1 rejects it too, naming `v.w`.
    "nested_field_moved_twice": (NESTED + """\
fn f() -> i32
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    consume(v.w.t)
    return 0

pub fn main() -> i32
    return f()
""", "v.w.t", {"ritz1": 2242, "ritz1_selfhosted": 2242}),

    # A partly moved parent can't be used whole.
    "parent_after_nested_field_move": (NESTED + """\
fn eat(i: Inner2) -> i32
    return i.n

pub fn main() -> i32
    var v = Outer2 { w: Inner2 { t: make(1), u: make(2), n: 3 } }
    consume(v.w.t)
    eat(v.w)
    return 0
""", "v.w.t", {"ritz1": 2242, "ritz1_selfhosted": 2242}),

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
""", "d.p.t", {"ritz1": 2242, "ritz1_selfhosted": 2242}),

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
        Full(t) => consume(t) + consume(t)
        _ => 0
    return 0
""", "t", {}),

    "tuple_element_after_move": (TUPLES + """\
pub fn main() -> i32
    var p = (make(1), 2)
    return consume(p.0) + consume(p.0)
""", "p.0", NO_TUPLES),

    "tuple_element_binding_after_move": (TUPLES + """\
pub fn main() -> i32
    var p = (make(1), 2)
    var x = p.0
    return consume(x) + consume(x)
""", "x", NO_TUPLES),

    "tuple_after_element_move": (TUPLES + """\
pub fn main() -> i32
    var p = (make(1), 2)
    consume(p.0)
    var q = p
    return 0
""", "p.0", NO_TUPLES),

    "tuple_in_field_after_element_move": (TUPLES + """\
pub fn main() -> i32
    var v = WithPair { pair: (make(1), make(2)), u: make(3) }
    consume(v.pair.0)
    var q = v.pair
    return 0
""", "v.pair.0", NO_TUPLES),
}


def _params(table):
    out = []
    for name in sorted(table):
        gaps = table[name][-1]
        for compiler in COMPILERS:
            marks = []
            if compiler in gaps:
                marks.append(pytest.mark.xfail(
                    strict=True,
                    reason=f"AGAST #{gaps[compiler]}: {compiler} does not "
                           f"implement this part of LANGUAGE_SPEC §13 yet"))
            out.append(pytest.param(compiler, name, marks=marks,
                                    id=f"{compiler}-{name}"))
    return out


def _compile(compiler, src, ll, cwd):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll)], cwd=cwd, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=cwd, env=env,
                          capture_output=True, text=True, timeout=300)


def _write(tmp_path, body):
    src = tmp_path / "main.ritz"
    src.write_text(PRELUDE + body)
    return src


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", _params(CASES))
def test_free_count(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    body, expected, _ = CASES[name]
    src = _write(tmp_path, body)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / "main"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler != "ritz0":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-2000:]}"
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == expected, f"{compiler} {name}: exit {rc}, spec says {expected}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler,name", _params(USE_AFTER_MOVE))
def test_use_after_move_rejected(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    body, var, _ = USE_AFTER_MOVE[name]
    src = _write(tmp_path, body)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll, tmp_path)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted a use after move:\n{out[-1000:]}"
    assert "Traceback" not in out, out[-2000:]
    assert f"use of moved value: `{var}`" in out, out[-2000:]
