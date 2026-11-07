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
#2398's, in test_member_through_levels.py.
"""

import pytest

from ref_rules import MOVE_OUT_OF_REF
from test_ref_into_value import COMPILERS, _assert_refused, _run

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
    # UFCS: a standalone function taking the receiver, `s` rather than `self`.
    "ufcs_shared_ptr_read": ("struct String\n    n: i32\n\nfn string_size(s: @String) -> i32\n    s.n\n\n"
                             "fn g(p: @*String) -> i32\n    p.size()\n\n"
                             "pub fn main() -> i32\n    var s = String { n: 3 }\n    var q: *String = @&s\n    g(@q)\n", 3),
    "ufcs_ptr_ptr_store": ("struct String\n    n: i32\n\nfn string_put(s: @&String, v: i32)\n    s.n = v\n\n"
                           "fn g(p: **String)\n    p.put(3)\n\n"
                           "pub fn main() -> i32\n    var s = String { n: 1 }\n    var q: *String = @&s\n    g(@&q)\n    s.n\n", 3),
}

# A receiver that doesn't lead to `self`'s type: `s` is a `*u8`, so `p` and `h.s`
# are the pointer it gets, and nothing past them.
OTHER_POINTER = """\
struct String
    n: i32

struct H
    s: *String

fn string_first(s: *u8) -> i32
    *s as i32

fn g(p: *String) -> i32
    p.first()

"""

HOLDERS |= {
    "ufcs_self_of_another_pointer_type": (OTHER_POINTER + "pub fn main() -> i32\n    var s = String { n: 3 }\n"
                                          "    var q: *String = @&s\n    g(q)\n", 3),
    "ufcs_field_of_another_pointer_type": (OTHER_POINTER + "pub fn main() -> i32\n    var s = String { n: 3 }\n"
                                           "    var h = H { s: @&s }\n    h.s.first()\n", 3),
}

HOLDERS |= {
    "ufcs_other_pointer_type_behind_a_reference": (
        OTHER_POINTER + "fn r(p: @*String) -> i32\n    p.first()\n\npub fn main() -> i32\n"
        "    var s = String { n: 3 }\n    var q: *String = @&s\n    r(@q)\n", 3),
    "ufcs_other_pointer_type_behind_a_pointer": (
        OTHER_POINTER + "fn r(p: **String) -> i32\n    p.first()\n\npub fn main() -> i32\n"
        "    var s = String { n: 3 }\n    var q: *String = @&s\n    r(@&q)\n", 3),
    "ufcs_other_pointer_type_in_a_ptr_ptr_field": (
        OTHER_POINTER + "struct D\n    s: **String\n\npub fn main() -> i32\n"
        "    var s = String { n: 3 }\n    var q: *String = @&s\n    var d = D { s: @&q }\n    d.s.first()\n", 3),
}

# A by-value `self` that isn't what the pointers end at: `*Vec<u8>` converts to a
# `Span<u8>`, it doesn't load to one.
HOLDERS["ufcs_by_value_self_is_a_conversion"] = (
    "struct Vec<T>\n    data: *T\n    len: i64\n    cap: i64\n\n"
    "fn vec_total(s: Span<u8>) -> i32\n    s.len as i32\n\n"
    "fn g(p: *Vec<u8>) -> i32\n    p.total()\n\n"
    "pub fn main() -> i32\n    var b: [3]u8 = [1, 2, 3]\n"
    "    var v = Vec<u8> { data: @&b[0], len: 3, cap: 3 }\n    g(@&v)\n", 3)

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
}


# ritz0 has none. All of ritz1's refuse, except #2316's, #2401's and #2402's.
RITZ1_GAPS = {f"{level}.{name}": gap for level in LEVELS
              for name, gap in (("chained_method", 2295), ("chained_store", 2295), ("chained_field", 2404))}
RITZ1_GAPS |= dict.fromkeys(("field_shared_ptr_read", "field_mut_ptr_store", "global_shared_ptr_read",
                             "returned_shared_ptr_store", "returned_ptr_ptr_read", "returned_ptr_ptr_store",
                             "returned_is_called_once", "shared_to_shared_read", "mut_to_mut_store",
                             "ptr_to_mut_store"), 2399)
RITZ1_GAPS |= dict.fromkeys(("global_ptr_ptr_read", "global_ptr_ptr_store", "element_ptr_ptr_store",
                             "element_of_a_pointer_store", "index_is_evaluated_once", "one_level_returned",
                             "deref_leaves_a_pointer_to_a_pointer", "self_is_a_ptr_ptr",
                             "self_is_a_shared_ptr", "ufcs_by_value_self_is_a_conversion"), 2404)
RITZ1_GAPS["ptr_ptr"] = 2402

GAPS = {"ritz0": {}, "ritz1": RITZ1_GAPS, "ritz1_selfhosted": RITZ1_GAPS}


def _params(table):
    for row in table:
        for compiler in COMPILERS:
            gap = GAPS[compiler].get(row)
            marks = [pytest.mark.xfail(strict=True, reason=f"AGAST #{gap}")] if gap else []
            yield pytest.param(row, compiler, marks=marks, id=f"{row}-{compiler}")


@pytest.mark.parametrize("row,compiler", list(_params(ROWS)))
def test_receiver_through_levels(tmp_path, compiler, row):
    src, want = ROWS[row]
    assert _run(compiler, tmp_path, row.replace(".", "_"), src) == want


@pytest.mark.parametrize("row,compiler", list(_params(HOLDERS)))
def test_receiver_through_what_holds_it(tmp_path, compiler, row):
    src, want = HOLDERS[row]
    assert _run(compiler, tmp_path, row, src) == want


@pytest.mark.parametrize("row,compiler", list(_params(MOVES)))
def test_a_move_only_self_stays_behind_the_level(tmp_path, compiler, row):
    fn, arg = MOVES[row]
    src = (f"{RESOURCE}{fn}\npub fn main() -> i32\n    var r = R {{ id: 1 }}\n"
           f"    var q: *R = @&r\n    g({arg})\n")
    _assert_refused(compiler, tmp_path, row, src, MOVE_OUT_OF_REF)
