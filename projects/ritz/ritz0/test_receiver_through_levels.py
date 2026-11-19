#!/usr/bin/env python3
"""A method gets the struct, however many pointers its receiver is behind (AGAST #2397).

`p.set(3)` with `p: @*C` means `C.set`. ritz0 found the method from the pointee
and then handed it the slot holding the `*C`: `_convert_type` bitcasts one
pointer to another, so nothing complained, the write overwrote the pointer and a
read returned what lay past it.

`self` decides how far to go: a method taking `self: **C` wants the pointer.

Each row says what the program must exit with, worked out from what it means.
No compiler is the oracle: `GAPS` lists who's wrong or refuses, and each is a
strict xfail citing its ticket. Levels past one extra (`***C`, `@**C`) are
in test_member_through_levels.py (#2398).
"""

import pytest

from ref_rules import MOVE_OUT_OF_REF
from test_ref_into_value import COMPILERS
from test_table_rows import assert_refusals, assert_runs

pytestmark = pytest.mark.integration

TYPES = """\
struct C
    x: i32
    y: i32

struct B<T>
    v: T

trait Tr
    fn tget(self: @Self) -> i32
    fn tset(self: @&Self, v: i32)

impl Tr for C
    fn tget(self: @C) -> i32
        self.y
    fn tset(self: @&C, v: i32)
        self.x = v

impl<T> B<T>
    fn gget(self: @B<T>) -> T
        self.v
    fn gset(self: @&B<T>, v: T)
        self.v = v

impl C
    fn get(self: @C) -> i32
        self.x
    fn set(self: @&C, v: i32)
        self.x = v
    fn val(self: C) -> i32
        self.x
    fn lget(self:& C) -> i32
        self.x
    fn lset(self:& C, v: i32)
        self.x = v
    fn bget(self:&) -> i32
        self.x
    fn bset(self:&, v: i32)
        self.x = v
    fn pget(self: *C) -> i32
        self.x
    fn pset(self: *C, v: i32)
        self.x = v

"""

# Only for the rows that chain.
CHAIN = """\
impl C
    fn me(self: @&C) -> @&C
        self
    fn mp(self: *C) -> *C
        self

"""

MAKE_C = "    var c = C { x: 1, y: 7 }\n"
MAKE_Q = MAKE_C + "    var q: *C = @&c\n"
MAKE_R = MAKE_Q + "    var r: **C = @&q\n"

# name: (param, argument, what `main` sets up).
LEVELS = {
    "shared_ptr": ("p: @*C", "@q", MAKE_Q),
    "mut_ptr": ("p: @&*C", "@&q", MAKE_Q),
    "ptr_ptr": ("p: **C", "@&q", MAKE_Q),
    "lent_ptr_ptr": ("p:& **C", "r", MAKE_R),
    # One level: what the rows above must not have moved.
    "lent_ptr": ("p:& *C", "q", MAKE_Q),
    "ptr": ("p: *C", "q", MAKE_Q),
    "mut": ("p: @&C", "@&c", MAKE_C),
    "lent": ("p:& C", "c", MAKE_C),
}

# name: (the call, exit code).
READS = {
    "shared_self": ("p.get()", 1),
    "by_value_self": ("p.val()", 1),
    "lent_self": ("p.lget()", 1),
    "bare_lent_self": ("p.bget()", 1),
    "pointer_self": ("p.pget()", 1),
    "trait": ("p.tget()", 7),
    "chained_field": ("p.mp().y", 7),
    "chained_method": ("p.mp().get()", 1),
}

# `c` must end up { x: 3, y: 7 }.
WRITES = {
    "mut_self": "p.set(3)",
    "lent_self_store": "p.lset(3)",
    "bare_lent_self_store": "p.bset(3)",
    "pointer_self_store": "p.pset(3)",
    "trait_store": "p.tset(3)",
    "chained_store": "p.me().set(3)",
    "reads_itself_for_an_argument": "p.set(p.get() + 2)",
}


def _level_rows():
    for level, (param, arg, make) in LEVELS.items():
        for name, (call, want) in READS.items():
            types = TYPES + CHAIN if name.startswith("chained") else TYPES
            yield (f"{level}.{name}",
                   f"{types}fn g({param}) -> i32\n    {call}\n\n"
                   f"pub fn main() -> i32\n{make}    g({arg})\n", want)
        for name, call in WRITES.items():
            types = TYPES + CHAIN if name.startswith("chained") else TYPES
            yield (f"{level}.{name}",
                   f"{types}fn g({param})\n    {call}\n\n"
                   f"pub fn main() -> i32\n{make}    g({arg})\n    c.x * 10 + c.y\n", 37)


ROWS = {name: (src, want) for name, src, want in _level_rows()}


def _main(body, top="", make=MAKE_Q):
    return f"{TYPES}{top}pub fn main() -> i32\n{make}{body}"


PP_FIELD = "struct F\n    pp: **C\n\n"
COPIED = "impl C\n    fn plus(self: C, n: i32) -> i32\n        self.x + n\n\n"
MAKE_B = "    var b = B<i32> { v: 1 }\n    var q: *B<i32> = @&b\n"

# A receiver's kind of method that isn't on `C`, and what holds it. name: (source, exit code).
HOLDERS = {
    "generic_shared_ptr_read": (_main("    g(@q)\n", "fn g(p: @*B<i32>) -> i32\n    p.gget()\n\n", MAKE_B), 1),
    "generic_shared_ptr_store": (_main("    g(@q)\n    b.v\n", "fn g(p: @*B<i32>)\n    p.gset(3)\n\n", MAKE_B), 3),
    "generic_mut_ptr_store": (_main("    g(@&q)\n    b.v\n", "fn g(p: @&*B<i32>)\n    p.gset(3)\n\n", MAKE_B), 3),
    "generic_ptr_ptr_read": (_main("    g(@&q)\n", "fn g(p: **B<i32>) -> i32\n    p.gget()\n\n", MAKE_B), 1),
    "generic_ptr_ptr_store": (_main("    g(@&q)\n    b.v\n", "fn g(p: **B<i32>)\n    p.gset(3)\n\n", MAKE_B), 3),
    "generic_ptr_store": (_main("    g(q)\n    b.v\n", "fn g(p: *B<i32>)\n    p.gset(3)\n\n", MAKE_B), 3),
    "type_arg_is_the_pointer": (_main("    h<*C>(@q)\n", "fn h<T>(p: @T) -> i32\n    p.get()\n\n"), 1),
    "type_arg_is_the_pointer_trait": (_main("    h<*C>(@q)\n", "fn h<T>(p: @T) -> i32\n    p.tget()\n\n"), 7),
    "let_shared_ptr_read": (_main("    let p: @*C = @q\n    p.get()\n"), 1),
    "let_shared_ptr_store": (_main("    let p: @*C = @q\n    p.set(3)\n    c.x\n"), 3),
    "var_shared_ptr_store": (_main("    var p: @*C = @q\n    p.set(3)\n    c.x\n"), 3),
    "let_mut_ptr_store": (_main("    let p: @&*C = @&q\n    p.set(3)\n    c.x\n"), 3),
    "let_ptr_ptr_store": (_main("    let p: **C = @&q\n    p.set(3)\n    c.x\n"), 3),
    "var_ptr_ptr_read": (_main("    var p: **C = @&q\n    p.get()\n"), 1),
    "inferred_shared_read": (_main("    let p = @q\n    p.get()\n"), 1),
    "inferred_mut_store": (_main("    var p = @&q\n    p.set(3)\n    c.x\n"), 3),
    "field_ptr_ptr_read": (_main("    var h = F { pp: @&q }\n    h.pp.get()\n", PP_FIELD), 1),
    "field_ptr_ptr_trait": (_main("    var h = F { pp: @&q }\n    h.pp.tget()\n", PP_FIELD), 7),
    "field_through_a_pointer": (_main("    var h = F { pp: @&q }\n    var e: *F = @&h\n    e.pp.set(3)\n    c.x\n", PP_FIELD), 3),
    "field_shared_ptr_read": (_main("    var h = F { p: @q }\n    h.p.get()\n", "struct F\n    p: @*C\n\n"), 1),
    "field_mut_ptr_store": (_main("    var h = F { p: @&q }\n    h.p.set(3)\n    c.x\n", "struct F\n    p: @&*C\n\n"), 3),
    "global_ptr_ptr_read": (_main("    G = @&q\n    G.get()\n", "var G: **C = null\n\n"), 1),
    "global_ptr_ptr_store": (_main("    G = @&q\n    G.set(3)\n    c.x\n", "var G: **C = null\n\n"), 3),
    "global_shared_ptr_read": (_main("    G = @q\n    G.get()\n", "var G: @*C = null\n\n"), 1),
    # An `@C` / `@&C` global holds the `ptr` to its struct (#3093).
    "global_shared_read": (_main("    G = @c\n    G.get()\n", "var G: @C = null\n\n"), 1),
    "global_mut_store": (_main("    G = @&c\n    G.set(3)\n    c.x\n", "var G: @&C = null\n\n"), 3),
    # `G = @&c` stored the `ptr` into the global's i64 (#2399).
    "global_ptr_of_an_address_store": (_main("    G = @&c\n    G.set(3)\n    c.x\n", "var G: *C = null\n\n"), 3),
    "element_ptr_ptr_store": (_main("    var a: [1]**C = [@&q]\n    a[0].set(3)\n    c.x\n"), 3),
    "element_of_a_pointer_store": (_main("    var r: **C = @&q\n    g(@&r)\n    c.x\n", "fn g(a: ***C)\n    a[0].set(3)\n\n"), 3),
    "returned_shared_ptr_store": (_main("    h(@q).set(3)\n    c.x\n", "fn h(p: @*C) -> @*C\n    p\n\n"), 3),
    "returned_ptr_ptr_read": (_main("    h(@&q).get()\n", "fn h(p: **C) -> **C\n    p\n\n"), 1),
    "returned_ptr_ptr_store": (_main("    h(@&q).set(3)\n    c.x\n", "fn h(p: **C) -> **C\n    p\n\n"), 3),
    "deref_leaves_a_pointer_to_a_pointer": (_main("    var r: **C = @&q\n    g(@&r)\n    c.x\n", "fn g(p: ***C)\n    (*p).set(3)\n\n"), 3),
    "shared_to_shared_read": (_main("    var r: @C = q\n    g(@r)\n", "fn g(p: @@C) -> i32\n    p.get()\n\n"), 1),
    "mut_to_mut_store": (_main("    var r: @&C = q\n    g(@&r)\n    c.x\n", "fn g(p: @&@&C)\n    p.set(3)\n\n"), 3),
    "ptr_to_mut_store": (_main("    var r: @&C = q\n    g(@&r)\n    c.x\n", "fn g(p: *@&C)\n    p.set(3)\n\n"), 3),
    # What a `.` receiver has always done: the rows above must not have moved it.
    "one_level_local": (_main("    q.set(3)\n    c.x\n"), 3),
    "one_level_element": (_main("    var a: [1]*C = [q]\n    a[0].set(3)\n    c.x\n"), 3),
    "one_level_returned": (_main("    h(q).set(3)\n    c.x\n", "fn h(p: *C) -> *C\n    p\n\n"), 3),
    "one_deref_of_a_pointer_to_a_pointer": (_main("    g(@&q)\n    c.x\n", "fn g(p: **C)\n    (*p).set(3)\n\n"), 3),
    # The receiver is evaluated once, and before the arguments.
    "returned_is_called_once": (_main("    h(@&q).set(3)\n    c.x * 10 + N\n",
                                      "var N: i32 = 0\n\nfn h(p: **C) -> **C\n    N += 1\n    p\n\n"), 31),
    "index_is_evaluated_once": (_main("    var a: [1]**C = [@&q]\n    a[i()].set(3)\n    c.x * 10 + N\n",
                                      "var N: i32 = 0\n\nfn i() -> i32\n    N += 1\n    0\n\n"), 31),
    "receiver_is_read_before_the_arguments": (_main(
        "    var e = C { x: 5, y: 6 }\n    g(@&q, @&e)\n    c.x * 10 + e.x\n",
        "fn aim(p: **C, e: *C) -> i32\n    *p = e\n    3\n\nfn g(p: **C, e: *C)\n    p.set(aim(p, e))\n\n"), 35),
    # A by-value `self` is its copy from before the arguments ran.
    "by_value_self_is_read_before_the_arguments": (_main("    g(q)\n", COPIED + "fn bump(p: *C) -> i32\n    p.x = 5\n    0\n\n"
                                                         "fn g(p: *C) -> i32\n    p.plus(bump(p))\n\n"), 1),
    "by_value_self_is_read_before_the_arguments_two_levels": (_main("    g(@&q)\n", COPIED + "fn bump(p: **C) -> i32\n    p.x = 5\n    0\n\n"
                                                                    "fn g(p: **C) -> i32\n    p.plus(bump(p))\n\n"), 1),
}

# `self` is the pointer, so nothing comes off it.
KEEPS_THE_POINTER = """\
struct C
    x: i32

impl C
    fn swap(self: **C, n: *C)
        *self = n
    fn rd(self: **C) -> i32
        self.x
    fn sh(self: @*C) -> i32
        self.x

"""

HOLDERS |= {
    "self_is_a_ptr_ptr": (KEEPS_THE_POINTER + "pub fn main() -> i32\n    var c = C { x: 1 }\n    var e = C { x: 3 }\n"
                          "    var q: *C = @&c\n    var r: **C = @&q\n    r.swap(@&e)\n    q.x * 10 + r.rd()\n", 33),
    "self_is_a_shared_ptr": (KEEPS_THE_POINTER + "fn g(p: @*C) -> i32\n    p.sh()\n\n"
                             "pub fn main() -> i32\n    var c = C { x: 3 }\n    var q: *C = @&c\n    g(@q)\n", 3),
    # The `**C` a global or an array element holds is that `self` (#2404).
    "self_is_a_global_ptr_ptr": (KEEPS_THE_POINTER + "var G: **C = null\n\npub fn main() -> i32\n    var c = C { x: 1 }\n"
                                 "    var e = C { x: 3 }\n    var q: *C = @&c\n    G = @&q\n    G.swap(@&e)\n    q.x * 10 + G.rd()\n", 33),
    "self_is_an_element_ptr_ptr": (KEEPS_THE_POINTER + "pub fn main() -> i32\n    var c = C { x: 1 }\n    var e = C { x: 3 }\n"
                                   "    var q: *C = @&c\n    var a: [1]**C = [@&q]\n    a[0].swap(@&e)\n    q.x * 10 + a[0].rd()\n", 33),
}

RESOURCE = """\
struct R
    id: i32

impl Drop for R
    fn drop(self: @&R)
        pass

impl R
    fn burn(self: R) -> i32
        self.id

"""

# A by-value `self` copies through a level, so a move-only one can't.
MOVES = {
    "shared_ptr": ("fn g(p: @*R) -> i32\n    ^p.burn()\n", "@q"),
    "mut_ptr": ("fn g(p: @&*R) -> i32\n    ^p.burn()\n", "@&q"),
    "ptr_ptr": ("fn g(p: **R) -> i32\n    ^p.burn()\n", "@&q"),
    "ptr": ("fn g(p: *R) -> i32\n    ^p.burn()\n", "q"),
    "lent_ptr_ptr": ("fn k(p:& **R) -> i32\n    ^p.burn()\n\nfn g(p: **R) -> i32\n    k(p)\n", "@&q"),
    "ptr_ptr_field": ("struct F\n    pp: **R\n\nfn g(p: **R) -> i32\n    let h = F { pp: p }\n    ^h.pp.burn()\n", "@&q"),
}


# ritz0 has none. All of ritz1's refuse, except #2316's and #2401's.
# (`self_is_a_ptr_ptr` and `self_is_a_shared_ptr` run since #3071 lowered a
# `self` at the levels it declares.)
# (`chained_field` ran once #2391 returned a `-> @&T` call result as a `ptr`;
# `chained_method`, through `mp() -> *C`, once #2883 named a `*S` link's impl;
# `one_level_returned`, `h(q).set(3)`, once #2946 named a `*S` free call's.)
# `chained_store` (#2295) runs since #3015 made an `@S` / `@&S` call result a place.
# #2399's rows run since it lowered `@@C`, `@*S` fields and `-> @*S` / `**S` calls.
# The global, element and `(*p)` rows and `global_shared_ptr_read` run since
# #2404 (and the UFCS rows, until LARB R66 deleted UFCS, #3496/#3497).
RITZ1_GAPS = {}

GAPS = {"ritz0": {}, "ritz1": RITZ1_GAPS, "ritz1_selfhosted": RITZ1_GAPS}


# AGAST #3518: each table is one test per compiler, a row per case (test_table_rows.py).
@pytest.mark.parametrize("compiler", COMPILERS)
def test_receiver_through_levels(tmp_path, compiler):
    assert_runs(compiler, tmp_path, ROWS, GAPS[compiler])


@pytest.mark.parametrize("compiler", COMPILERS)
def test_receiver_through_what_holds_it(tmp_path, compiler):
    assert_runs(compiler, tmp_path, HOLDERS, GAPS[compiler])


# A by-value `self` copies through a level, so a move-only one can't.
# name: (program, message).
REFUSALS = {
    row: ((f"{RESOURCE}{fn}\npub fn main() -> i32\n    var r = R {{ id: 1 }}\n"
           f"    var q: *R = @&r\n    g({arg})\n"), MOVE_OUT_OF_REF)
    for row, (fn, arg) in MOVES.items()
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_move_only_self_stays_behind_the_level(tmp_path, compiler):
    assert_refusals(compiler, tmp_path, REFUSALS, GAPS[compiler])
