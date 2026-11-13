#!/usr/bin/env python3
"""A reference to a local doesn't leave its fn (LANGUAGE_SPEC §13.5, LARB ruling
R2, AGAST #2340).

A **local root** is a by-value local or param, reached with no pointer or
reference on the path. At `return` or a tail, through `if` and `match` arms, it's
an error to return:

(a) `@x`, `@&x`, `@x.f` or `@x[i]` of a local root, as `@T`, `@&T` or `*T`;
(b) a local reference binding initialised from (a), over any number of hops;
(c) a call returning `@U` or `@&U` given a reference to a local root with pointee
    `U`. Raw `*U` returns are exempt.

This is a check for the definite case. A `var` stops being definite once it's
written or has its address taken, or inside a loop it was declared outside: the
loop can reach a later write first.

Each row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must report
the same `line:col: message`.

Whether an `@x` held in a `*T` counts as a borrow is #2371's, and a reference to
another type is #2367's and #2368's. Nothing here decides those.
"""

import pytest

from ref_rules import returns_local
from test_ref_into_value import COMPILERS, _assert_refused, _ids, _main, _run

pytestmark = pytest.mark.integration

TYPES = """\
struct C
    x: i32

struct W
    c: C
    a: [2]i32

struct H
    p: *C
    r: @C

struct Node
    next: *Node
    x: i32

enum E
    V(C)
    N

impl C
    fn me(self: @C) -> @C
        self
    fn mine(self: @&C) -> @&C
        self
    fn other(self: @C, o: @C) -> @C
        o
    fn raw(self: @C) -> *C
        self as *C

fn id(r: @&C) -> @&C
    r

fn sid(r: @C) -> @C
    r

fn iid(n: @i32) -> @i32
    n

fn aid(a: @[2]i32) -> @[2]i32
    a

fn pid(r: *C) -> @C
    r

fn rawid(r: @C) -> *C
    r as *C

fn lend(c:& C) -> @&C
    @&c

fn first(r: @C, n: @i32) -> @C
    r

fn second(n: @i32, r: @C) -> @C
    r

fn gid<T>(r: @T) -> @T
    r

var G: C
var GA: [2]C
var GR: @C = null

"""

C1 = "    var c = C { x: 1 }\n"

# (a), with the local root each row names.
ADDRESSES = {
    "shared": ("fn f() -> @C\n" + C1 + "    return ^@c\n", "c"),
    "mutable": ("fn f() -> @&C\n" + C1 + "    return ^@&c\n", "c"),
    "pointer": ("fn f() -> *C\n" + C1 + "    return ^@c\n", "c"),
    "mutable_pointer": ("fn f() -> *C\n" + C1 + "    return ^@&c\n", "c"),
    "let": ("fn f() -> @C\n    let c = C { x: 1 }\n    return ^@c\n", "c"),
    "by_value_param": ("fn f(c: C) -> @C\n    return ^@c\n", "c"),
    "scalar": ("fn f() -> @i32\n    var n: i32 = 1\n    return ^@n\n", "n"),
    "scalar_pointer": ("fn f() -> *i32\n    var n: i32 = 1\n    return ^@n\n", "n"),
    "scalar_param": ("fn f(n: i32) -> *i32\n    return ^@n\n", "n"),
    "field": ("fn f(w: W) -> @C\n    return ^@w.c\n", "w"),
    "nested_field": ("fn f(w: W) -> @i32\n    return ^@w.c.x\n", "w"),
    "element": ("fn f() -> @i32\n    var a: [2]i32 = [1, 2]\n    return ^@a[1]\n", "a"),
    "element_of_a_param": ("fn f(a: [2]i32) -> *i32\n    return ^@a[0]\n", "a"),
    "element_of_a_field": ("fn f(w: W) -> *i32\n    return ^@w.a[1]\n", "w"),
    "field_of_an_element": ("fn f() -> *i32\n    var a: [1]C = [C { x: 1 }]\n    return ^@a[0].x\n", "a"),
    "whole_array": ("fn f() -> *i32\n    var a: [2]i32 = [1, 2]\n    return ^@a\n", "a"),
    "a_pointer_local": ("fn f(p: *C) -> **C\n    return ^@p\n", "p"),
    "a_reference_param": ("fn f(r: @C) -> @C\n    return ^@r\n", "r"),
    "a_reference_self": ("impl C\n    fn g(self: @C) -> @C\n        return ^@self\n", "self"),
    "self_by_value": ("impl C\n    fn g(self) -> @C\n        return ^@self\n", "self"),
    "self_by_value_typed": ("impl C\n    fn g(self: C) -> @C\n        return ^@self\n", "self"),
    "self_by_value_field": ("impl C\n    fn g(self) -> @i32\n        return ^@self.x\n", "self"),
    "self_by_value_field_tail": ("impl C\n    fn g(self) -> @i32\n        ^@self.x\n", "self"),
    "pattern_binding": ("fn f(e: E) -> @C\n    match e\n        V(c) => return ^@c\n        N => return null\n", "c"),
    "loop_binding": ("fn f(a: [2]C) -> @C\n    for c in a\n        return ^@c\n    null\n", "c"),
    "grouped": ("fn f() -> @C\n" + C1 + "    return (^@c)\n", "c"),
    "method": ("impl C\n    fn g(self: @C, d: C) -> @C\n        return ^@d\n", "d"),
    "generic_instance": ("fn g<T>(v: T) -> @T\n    return ^@v\n\nfn f() -> i32\n    g<C>(C { x: 1 })\n    0\n", "v"),
}

# Where the value lands: a tail, or an arm of one, in its own scope.
LANDINGS = {
    "tail": ("fn f() -> @C\n" + C1 + "    ^@c\n", "c"),
    "if_arm": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    if b > 0\n        ^@c\n    else\n        p\n", "c"),
    "else_arm": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    if b > 0\n        p\n    else\n        ^@c\n", "c"),
    "match_arm": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    match b\n        0 => ^@c\n        _ => p\n", "c"),
    "return_if": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    return if b > 0\n        ^@c\n    else\n        p\n", "c"),
    "return_match": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    return match b\n        0 => ^@c\n        _ => p\n", "c"),
    "nested_arm": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    if b > 0\n        if b > 1\n            ^@c\n"
                   "        else\n            p\n    else\n        p\n", "c"),
    "arm_own_local": ("fn f(b: i32, p: @C) -> @C\n    if b > 0\n        var d = C { x: 1 }\n        ^@d\n"
                      "    else\n        p\n", "d"),
    "arm_return": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    match b\n        0 => return ^@c\n        _ => return p\n", "c"),
    "early_return": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    if b > 0\n        return ^@c\n    p\n", "c"),
    "return_in_a_loop": ("fn f(b: i32) -> @C\n" + C1 + "    while b > 0\n        return ^@c\n    null\n", "c"),
    "tail_of_a_method": ("impl C\n    fn g(self: @C) -> @C\n" + "    " + C1 + "        ^@c\n", "c"),
}

# (b).
BINDINGS = {
    "let": ("fn f() -> @C\n" + C1 + "    let r = @c\n    return ^r\n", "c"),
    "let_mutable": ("fn f() -> @&C\n" + C1 + "    let r = @&c\n    return ^r\n", "c"),
    "annotated": ("fn f() -> @C\n" + C1 + "    let r: @C = @c\n    return ^r\n", "c"),
    "pointer": ("fn f() -> *C\n" + C1 + "    let r: *C = @c\n    return ^r\n", "c"),
    "pointer_to_a_pointer": ("fn f(p: *C) -> **C\n    let r: **C = @p\n    return ^r\n", "p"),
    "by_value_param": ("fn f(c: C) -> @C\n    let r = @c\n    return ^r\n", "c"),
    "self_by_value": ("impl C\n    fn g(self) -> @C\n        let r = @self\n        return ^r\n", "self"),
    "field": ("fn f(w: W) -> @C\n    let r = @w.c\n    return ^r\n", "w"),
    "element": ("fn f() -> *i32\n    var a: [2]i32 = [1, 2]\n    let r: *i32 = @a[0]\n    return ^r\n", "a"),
    "two_hops": ("fn f() -> @C\n" + C1 + "    let r = @c\n    let q = r\n    return ^q\n", "c"),
    "three_hops": ("fn f() -> @C\n" + C1 + "    let r = @c\n    let q = r\n    let p = q\n    return ^p\n", "c"),
    "tail": ("fn f() -> @C\n" + C1 + "    let r = @c\n    ^r\n", "c"),
    "if_arm": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    let r = @c\n    if b > 0\n        ^r\n    else\n        p\n", "c"),
    "match_arm": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    let r = @c\n    match b\n        0 => ^r\n        _ => p\n", "c"),
    "a_var": ("fn f() -> @C\n" + C1 + "    var r = @c\n    return ^r\n", "c"),
    "a_var_hop": ("fn f() -> @C\n" + C1 + "    var r = @c\n    var q = r\n    return ^q\n", "c"),
    # A hop holds the value it was given, whatever happens to where it came from.
    "copied_before_the_write": ("fn f(p: @C) -> @C\n" + C1 + "    var r = @c\n    let q = r\n    r = p\n    return ^q\n", "c"),
    "var_read_in_a_loop": ("fn f(b: i32) -> @C\n" + C1 + "    var r = @c\n    var n: i32 = 0\n    while n < b\n"
                           "        n = n + r.x\n    return ^r\n", "c"),
    "let_in_a_loop": ("fn f(b: i32) -> @C\n" + C1 + "    while b > 0\n        let r = @c\n        return ^r\n    null\n", "c"),
    "var_of_the_loop": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    while b > 0\n        var r = @c\n"
                        "        if b > 1\n            return ^r\n        r = p\n    null\n", "c"),
    # The same name in the arm before is out of scope here (#2395): `r` is this
    # arm's, so it's judged.  ritz1 left a name bound twice in a fn unjudged.
    "a_name_bound_in_the_arm_before": ("fn f(b: i32, p: @C) -> @C\n    if b > 0\n        let r = @G\n"
                                       "        p\n    else\n        var d = C { x: 1 }\n        let r = @d\n"
                                       "        ^r\n", "d"),
    "let_with_its_address_taken": ("fn f() -> @C\n" + C1 + "    let r = @c\n    let q = @r\n    return ^r\n", "c"),
}

# (c).
CALLS = {
    "mutable": ("fn f() -> @&C\n" + C1 + "    return ^id(@&c)\n", "c"),
    "shared": ("fn f() -> @C\n" + C1 + "    return ^sid(@c)\n", "c"),
    "by_value_param": ("fn f(c: C) -> @C\n    return ^sid(@c)\n", "c"),
    "scalar": ("fn f() -> @i32\n    var n: i32 = 1\n    return ^iid(@n)\n", "n"),
    "field": ("fn f(w: W) -> @C\n    return ^sid(@w.c)\n", "w"),
    "scalar_field": ("fn f(w: W) -> @i32\n    return ^iid(@w.c.x)\n", "w"),
    "element": ("fn f() -> @i32\n    var a: [2]i32 = [1, 2]\n    return ^iid(@a[0])\n", "a"),
    "array": ("fn f() -> @[2]i32\n    var a: [2]i32 = [1, 2]\n    return ^aid(@a)\n", "a"),
    "second_argument": ("fn f(n: @i32) -> @C\n" + C1 + "    return ^second(n, @c)\n", "c"),
    "a_binding": ("fn f() -> @C\n" + C1 + "    let r = @c\n    return ^sid(r)\n", "c"),
    "a_hop": ("fn f() -> @C\n" + C1 + "    let r = @c\n    let q = r\n    return ^sid(q)\n", "c"),
    "into_a_pointer": ("fn f() -> @C\n" + C1 + "    return ^pid(@c)\n", "c"),
    "lent": ("fn f() -> @&C\n" + C1 + "    return ^lend(c)\n", "c"),
    "lent_field": ("fn f(w: W) -> @&C\n    return ^lend(w.c)\n", "w"),
    "receiver": ("fn f() -> @C\n" + C1 + "    return ^c.me()\n", "c"),
    "mutable_receiver": ("fn f() -> @&C\n" + C1 + "    return ^c.mine()\n", "c"),
    "receiver_param": ("fn f(c: C) -> @C\n    return ^c.me()\n", "c"),
    "receiver_field": ("fn f(w: W) -> @C\n    return ^w.c.me()\n", "w"),
    "receiver_binding": ("fn f() -> @C\n" + C1 + "    let r = @c\n    return ^r.me()\n", "c"),
    "method_argument": ("fn f(p: @C) -> @C\n" + C1 + "    return ^p.other(@c)\n", "c"),
    "tail": ("fn f() -> @C\n" + C1 + "    ^sid(@c)\n", "c"),
    "if_arm": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    if b > 0\n        ^sid(@c)\n    else\n        p\n", "c"),
    "match_arm": ("fn f(b: i32, p: @C) -> @C\n" + C1 + "    match b\n        0 => ^sid(@c)\n        _ => p\n", "c"),
    "into_a_pointer_return": ("fn f() -> *C\n" + C1 + "    return ^sid(@c)\n", "c"),
    "generic_instance": ("fn f() -> @C\n" + C1 + "    return ^gid<C>(@c)\n", "c"),
}

# Stays legal, and runs. (fn, the call, what main returns.)
ALLOWED = {
    # The caller's value must outlive the result (R2 confirms #2249's half).
    "lent_mutable": ("fn g(c:& C) -> @&C\n    return @&c\n", "let r = g(c)\n    r.x = 4", 4),
    "lent_shared": ("fn g(c:& C) -> @C\n    return @c\n", "let r = g(c)\n    c.x = r.x + 3", 4),
    "lent_pointer": ("fn g(c:& C) -> *C\n    return @c\n", "let r = g(c)\n    r.x = 5", 5),
    "lent_tail": ("fn g(c:& C) -> @&C\n    @&c\n", "let r = g(c)\n    r.x = 6", 6),
    "lent_through_a_binding": ("fn g(c:& C) -> @&C\n    let p: @&C = @&c\n    return p\n", "let r = g(c)\n    r.x = 7", 7),
    "lent_field": ("fn g(w:& W) -> @&i32\n    return @&w.c.x\n",
                   "var w = W { c: c, a: [0, 0] }\n    *g(w) = 8\n    c.x = w.c.x", 8),
    "lent_element": ("fn g(a:& [2]i32) -> @&i32\n    return @&a[1]\n",
                     "var a: [2]i32 = [1, 2]\n    *g(a) = 9\n    c.x = a[1]", 9),
    "lent_scalar": ("fn g(n:& i32) -> @&i32\n    return @&n\n",
                    "var n: i32 = 1\n    *g(n) = 3\n    c.x = n", 3),
    "lent_pointer_param": ("fn g(p:& *C) -> @&*C\n    return @&p\n",
                           "var p: *C = @c\n    let q = g(p)\n    c.x = 2", 2),
    "lent_float": ("fn g(n:& f64) -> @&f64\n    return @&n\n",
                   "var n: f64 = 1.0\n    let q = g(n)\n    c.x = 5", 5),
    "lent_self": ("impl C\n    fn g(self:&) -> @&C\n        return @&self\n", "let r: @&C = c.g()\n    r.x = 2", 2),
    "lent_passed_on": ("fn g(c:& C) -> @&C\n    return id(@&c)\n", "let r = g(c)\n    r.x = 3", 3),
    # AGAST #2391: a `-> @&T` call result or `self: @&T` is a `ptr` at the return.
    "lent_passed_on_tail": ("fn g(c:& C) -> @&C\n    id(@&c)\n", "let r = g(c)\n    r.x = 4", 4),
    "mutable_param_passed_on": ("fn g(r: @&C) -> @&C\n    return id(r)\n", "let r = g(@&c)\n    r.x = 5", 5),
    "mutable_self": ("impl C\n    fn g(self: @&C) -> @&C\n        return self\n", "let r: @&C = c.g()\n    r.x = 6", 6),
    "mutable_self_method": ("fn g(c:& C) -> @&C\n    return c.mine()\n", "let r = g(c)\n    r.x = 7", 7),
    "shared_param": ("fn g(r: @C) -> @C\n    return r\n", "let r = g(@c)\n    c.x = r.x + 1", 2),
    "mutable_param": ("fn g(r: @&C) -> @&C\n    return r\n", "let r = g(@&c)\n    r.x = 7", 7),
    "pointer_param": ("fn g(r: *C) -> *C\n    return r\n", "let r = g(@c)\n    r.x = 5", 5),
    "param_copied": ("fn g(r: @&C) -> @&C\n    let q = r\n    return q\n", "let r = g(@&c)\n    r.x = 6", 6),
    "param_passed_on": ("fn g(r: @C) -> @C\n    return sid(r)\n", "let r = g(@c)\n    c.x = r.x + 2", 3),
    # A pointer or reference on the path: what's behind it isn't the fn's.
    "through_a_pointer": ("fn g(p: *C) -> *i32\n    return @p.x\n", "*g(@c) = 3", 3),
    "through_a_reference": ("fn g(p: @&C) -> @&i32\n    return @&p.x\n", "*g(@&c) = 4", 4),
    "through_a_pointer_field": ("fn g(h: H) -> *i32\n    return @h.p.x\n",
                                "*g(H { p: @c, r: null }) = 5", 5),
    "through_a_reference_field": ("fn g(h: H) -> @C\n    return h.r\n",
                                  "let r = g(H { p: null, r: @c })\n    c.x = r.x + 5", 6),
    "pointer_element": ("fn g(p: *i32) -> *i32\n    return @p[1]\n",
                        "var a: [2]i32 = [1, 2]\n    *g(@a[0]) = 7\n    c.x = a[1]", 7),
    "deref": ("fn g(p: *C) -> *C\n    return @*p\n", "let r = g(@c)\n    r.x = 8", 8),
    "pointer_in_an_array": ("fn g(a: [1]*C) -> *i32\n    return @a[0].x\n",
                            "var a: [1]*C = [@c]\n    *g(a) = 9\n    c.x = c.x", 9),
    "binding_through_a_pointer": ("fn g(p: *C) -> *i32\n    let q: *i32 = @p.x\n    return q\n", "*g(@c) = 3", 3),
    "global": ("fn g() -> @C\n    return @G\n", "let r = g()\n    c.x = r.x + 4", 4),
    "global_mutable": ("fn g() -> *C\n    return @G\n", "let r = g()\n    r.x = 5\n    c.x = G.x", 5),
    "global_field": ("fn g() -> *i32\n    return @G.x\n", "*g() = 6\n    c.x = G.x", 6),
    "global_element": ("fn g() -> *C\n    return @GA[1]\n", "let r = g()\n    r.x = 7\n    c.x = GA[1].x", 7),
    "global_binding": ("fn g() -> *C\n    let r = @G\n    return r\n", "let r = g()\n    r.x = 8\n    c.x = G.x", 8),
    "global_through_a_call": ("fn g() -> @C\n    return sid(@G)\n", "let r = g()\n    c.x = r.x + 9", 9),
    "null": ("fn g() -> *C\n    return null\n", "c.x = 2\n    g()", 2),
    # (c) is type-directed: `store_get(@key)` looks a key up, it doesn't hand it back.
    "another_pointee": ("fn g(r: @C) -> @C\n    var key: i32 = 3\n    return first(r, @key)\n", "let r = g(@c)\n    c.x = r.x + 1", 2),
    "another_pointee_lent": ("fn t(n:& i32, r: @C) -> @C\n    r\n\nfn g(r: @C) -> @C\n    var key: i32 = 3\n"
                             "    return t(key, r)\n", "let r = g(@c)\n    c.x = r.x + 2", 3),
    "another_pointee_argument": ("impl C\n    fn with(self: @C, n: @i32) -> @C\n        self\n\n"
                                 "fn g(r: @C) -> @C\n    var key: i32 = 3\n    return r.with(@key)\n",
                                 "let r = g(@c)\n    c.x = r.x + 3", 4),
    "another_pointee_receiver": ("struct K\n    n: i32\n\nimpl K\n    fn pick(self: @K, r: @C) -> @C\n        r\n\n"
                                 "fn g(r: @C) -> @C\n    var k = K { n: 1 }\n    return k.pick(r)\n",
                                 "let r = g(@c)\n    c.x = r.x + 4", 5),
    "a_pointer_argument": ("fn g(r: *C) -> @C\n    return pid(r)\n", "let r = g(@c)\n    c.x = r.x + 5", 6),
    "a_raw_return": ("fn g() -> *C\n    var d = C { x: 1 }\n    rawid(@d)\n    return @G\n", "let r = g()\n    c.x = r.x + 1", 1),
    # A `var` that may hold something else isn't definite.
    "var_written_first": ("fn g(p: @C) -> @C\n    var d = C { x: 1 }\n    var r = @d\n    r = p\n    return r\n",
                          "let r = g(@c)\n    c.x = r.x + 3", 4),
    "var_written_in_an_arm": ("fn g(p: @C, b: i32) -> @C\n    var d = C { x: 1 }\n    var r = @d\n    if b > 0\n"
                              "        r = p\n    return r\n", "let r = g(@c, 1)\n    c.x = r.x + 4", 5),
    "var_written_in_a_loop": ("fn g(n: *Node) -> *Node\n    var head = Node { next: n, x: 0 }\n"
                              "    var cur: *Node = @head\n    while cur.next != null\n"
                              "        cur = cur.next\n    return cur\n",
                              "var n = Node { next: null, x: 5 }\n    let r = g(@n)\n    c.x = r.x", 5),
    "var_returned_before_a_loops_write": ("fn g(n: *Node) -> *Node\n    var head = Node { next: n, x: 0 }\n"
                                          "    var cur: *Node = @head\n    while true\n"
                                          "        if cur.x > 0\n            return cur\n"
                                          "        cur = cur.next\n    null\n",
                                          "var n = Node { next: null, x: 6 }\n    let r = g(@n)\n    c.x = r.x", 6),
    "var_address_taken": ("fn s(q: *@C, to: @C)\n    *q = to\n\nfn g(p: @C) -> @C\n    var d = C { x: 1 }\n"
                          "    var r = @d\n    s(@r, p)\n    return r\n", "let r = g(@c)\n    c.x = r.x + 5", 6),
    "var_address_taken_mutably": ("fn s(q: @&@C, to: @C)\n    *q = to\n\nfn g(p: @C) -> @C\n    var d = C { x: 1 }\n"
                                  "    var r = @d\n    s(@&r, p)\n    return r\n", "let r = g(@c)\n    c.x = r.x + 6", 7),
    "var_lent": ("fn s(q:& *C, to: *C)\n    q = to\n\nfn g(p: *C) -> *C\n    var d = C { x: 1 }\n"
                 "    var r: *C = @d\n    s(r, p)\n    return r\n", "let r = g(@c)\n    c.x = r.x + 7", 8),
    "a_value_read_through": ("fn g() -> i32\n    var d = C { x: 1 }\n    let r = @d\n    return r.x\n", "c.x = g()", 1),
    "a_copy_returned": ("fn g() -> C\n    var d = C { x: 2 }\n    let r = @d\n    return *r\n", "let r = g()\n    c.x = r.x", 2),
    # A pointer as an integer is a different question: the slot isn't a reference.
    "an_integer_return": ("fn g() -> i64\n    var d = C { x: 1 }\n    return @d\n", "c.x = (g() - g()) as i32 + 3", 3),
}

# ritz1 stores a nested `-> @C` result as a `C`, which clang refuses.
UNCHECKED_GAPS = {"a_call_of_a_call": 2394}

# Compiles, and that's all that's asked: §13.5 says these aren't checked, and most
# of them dangle. A row here that starts failing means the check has grown past
# what the ruling asks.
NOT_CHECKED = {
    "a_cast": "fn f() -> *C\n" + C1 + "    return (@c as *u8) as *C\n",
    "a_cast_binding": "fn f() -> *u8\n" + C1 + "    let p = @c as *u8\n    return p\n",
    "a_stored_reference": "fn f(h: @&H) -> *C\n" + C1 + "    h.p = @c\n    return h.p\n",
    "a_reference_in_a_field": "fn f() -> @C\n" + C1 + "    let h = H { p: null, r: @c }\n    return h.r\n",
    "a_reference_in_a_global": "fn f() -> @C\n" + C1 + "    GR = @c\n    return GR\n",
    "a_call_result_held": "fn f() -> @C\n" + C1 + "    let r = sid(@c)\n    return r\n",
    "a_call_of_a_call": "fn f() -> @C\n" + C1 + "    return sid(sid(@c))\n",
    "a_raw_call": "fn f() -> *C\n" + C1 + "    return rawid(@c)\n",
    "a_raw_method": "fn f() -> *C\n" + C1 + "    return c.raw()\n",
    "an_arm_held": "fn f(b: i32, p: @C) -> @C\n" + C1 + "    let r: @C = if b > 0\n        @c\n    else\n        p\n    return r\n",
    "assigned_not_initialised": "fn f() -> @C\n" + C1 + "    var r: @C = null\n    r = @c\n    return r\n",
    "behind_a_held_reference": "fn f(w: W) -> @i32\n    let r = @w.c\n    return @r.x\n",
    "a_pointer_as_an_integer": "fn f() -> *C\n" + C1 + "    let n: i64 = @c\n    return n\n",
    "a_fn_value": "fn f(g: fn(@C) -> @C) -> @C\n" + C1 + "    return g(@c)\n",
    "in_a_span": ("import ritzlib.span\n\nfn g(s: Span<i32>) -> Span<i32>\n    s\n\n"
                  "fn f() -> Span<i32>\n    var a: [2]i32 = [1, 2]\n    return g(@a)\n"),
    "in_an_option": "import ritzlib.option\n\nfn f() -> Option<@C>\n" + C1 + "    return Some(@c)\n",
}


def _wrap(body):
    return _main(TYPES + body, "    0\n")


def _rows(*tables):
    for prefix, table, gaps in tables:
        for site in _ids(table):
            for compiler in COMPILERS:
                row = (f"{prefix}_{site}", table[site], compiler)
                if site in gaps and compiler != "ritz0":
                    mark = pytest.mark.xfail(strict=True, reason=f"#{gaps[site]}")
                    yield pytest.param(*row, marks=mark, id=f"{row[0]}-{compiler}")
                else:
                    yield pytest.param(*row, id=f"{row[0]}-{compiler}")


@pytest.mark.parametrize("site,row,compiler", list(_rows(("address", ADDRESSES, {}),
                                                         ("landing", LANDINGS, {}),
                                                         ("binding", BINDINGS, {}),
                                                         ("call", CALLS, {}))))
def test_a_reference_to_a_local_is_refused(tmp_path, compiler, site, row):
    body, root = row
    _assert_refused(compiler, tmp_path, site, _wrap(body), returns_local(root))


@pytest.mark.parametrize("site,row,compiler", list(_rows(("", ALLOWED, {}))))
def test_what_outlives_the_fn_still_runs(tmp_path, compiler, site, row):
    fn, call, want = row
    src = _main(TYPES + fn, f"    var c = C {{ x: 1 }}\n    {call}\n    c.x\n")
    assert _run(compiler, tmp_path, site, src) == want


@pytest.mark.parametrize("site,row,compiler", list(_rows(("", NOT_CHECKED, UNCHECKED_GAPS))))
def test_what_the_spec_leaves_unchecked_compiles(tmp_path, compiler, site, row):
    assert _run(compiler, tmp_path, site, _wrap(row)) == 0


@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_types_compile_on_their_own(tmp_path, compiler):
    """Or every row above fails for them, and not for what it names."""
    assert _run(compiler, tmp_path, "types", _wrap("")) == 0
