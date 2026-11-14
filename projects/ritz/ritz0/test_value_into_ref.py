#!/usr/bin/env python3
"""A value doesn't fit a reference slot (LANGUAGE_SPEC §13.4, LARB ruling R1,
AGAST #2337).

`name:& T` is an alias of the caller's place, so `c` has type `T` in the whole
body, and a `T` never fits an `@T`, `@&T` or `*T`, whatever the binding. A
reference is written: `@c` or `@&c`, which give the caller's address. The one
implicit borrow left is a place into a `:&` parameter.

Each row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must report
the same `line:col: message`.

`@x` doesn't fit `@&T` or `:&` (#2339), so an `@&T` slot is only ever given `@&c`.
"""

import pytest

from ref_rules import REF_TO_OTHER_POINTER, REF_TO_OTHER_TYPE, VALUE_INTO_MUT_REF, VALUE_INTO_SHARED_REF
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _ids, _main, _run

pytestmark = pytest.mark.integration

TYPES = """\
struct C
    x: i32

struct W
    r: {S}

struct K
    n: i32

enum E
    V({S})
    N

impl K
    fn take(self: @K, p: {S}) -> i32
        self.n

fn g(p: {S}) -> i32
    0

"""

SLOT_TYPES = {"shared": "@C", "mutable": "@&C", "pointer": "*C"}
MESSAGE = {"shared": VALUE_INTO_SHARED_REF, "mutable": VALUE_INTO_MUT_REF,
           "pointer": VALUE_INTO_SHARED_REF}
ADDR = {"shared": "@c", "mutable": "@&c", "pointer": "@c"}

# What `c` is. A by-value param is a `let`, so it has no `@&c`: the refusals
# don't need one.
BINDINGS = {"lent": "c:& C", "value": "c: C"}

# `^` marks where the error lands; `{S}` is the slot's type and `{B}` binds `c`.
SITES = {
    "argument": "fn f({B}) -> i32\n    g(^c)\n",
    "method_argument": "fn f({B}, k: K) -> i32\n    k.take(^c)\n",
    "let": "fn f({B}) -> i32\n    let p: {S} = ^c\n    0\n",
    "var": "fn f({B}) -> i32\n    var p: {S} = ^c\n    0\n",
    "assign": "fn f({B}, q: {S}) -> i32\n    var p: {S} = q\n    p = ^c\n    0\n",
    "field_assign": "fn f({B}, q: {S}) -> i32\n    var w = W { r: q }\n    w.r = ^c\n    0\n",
    "return": "fn f({B}) -> {S}\n    return ^c\n",
    "tail": "fn f({B}) -> {S}\n    ^c\n",
    "field": "fn f({B}) -> i32\n    let w = W { r: ^c }\n    0\n",
    "element": "fn f({B}) -> i32\n    let a: [1]{S} = [^c]\n    0\n",
    "fill": "fn f({B}) -> i32\n    let a: [2]{S} = [^c; 2]\n    0\n",
    "element_store": "fn f({B}, q: {S}) -> i32\n    var a: [1]{S} = [q]\n    a[0] = ^c\n    0\n",
    "payload": "fn f({B}) -> i32\n    let e: E = E.V(^c)\n    0\n",
    "if_arm": "fn f({B}, b: i32) -> {S}\n    if b > 0\n        ^c\n    else\n        c\n",
    "match_arm": "fn f({B}, b: i32) -> {S}\n    match b\n        0 => ^c\n        _ => c\n",
    "return_in_an_arm": "fn f({B}, b: i32) -> {S}\n    match b\n        0 => return ^c\n        _ => return c\n",
    "value_arm": "fn f({B}, b: i32) -> i32\n    let p: {S} = if b > 0\n        ^c\n    else\n        c\n    0\n",
}

# What the value is, rather than where it lands. `^` as above.
OTHER_SHAPES = {
    "scalar_lent_let": ("fn f(n:& i32) -> i32\n    let p: @i32 = ^n\n    0\n", VALUE_INTO_SHARED_REF),
    "scalar_lent_return": ("fn f(n:& i32) -> @&i32\n    return ^n\n", VALUE_INTO_MUT_REF),
    "scalar_lent_pointer": ("fn f(n:& i32) -> *i32\n    return ^n\n", VALUE_INTO_SHARED_REF),
    "scalar_lent_argument": ("fn g(p: @i32) -> i32\n    0\n\nfn f(n:& i32) -> i32\n    g(^n)\n",
                             VALUE_INTO_SHARED_REF),
    "scalar_value_argument": ("fn g(p: @i32) -> i32\n    0\n\nfn f(n: i32) -> i32\n    g(^n)\n",
                              VALUE_INTO_SHARED_REF),
    "scalar_value_pointer": ("fn g(p: *i32) -> i32\n    0\n\nfn f(n: i32) -> i32\n    g(^n)\n",
                             VALUE_INTO_SHARED_REF),
    "array_lent_let": ("fn f(a:& [2]i32) -> i32\n    let p: @[2]i32 = ^a\n    0\n", VALUE_INTO_SHARED_REF),
    "array_lent_return": ("fn f(a:& [2]i32) -> @&[2]i32\n    return ^a\n", VALUE_INTO_MUT_REF),
    # #2325: `h` has type `*U`, and a `T` doesn't fit `@T` at T = `*U`.
    "pointer_lent_let": ("struct C\n    x: i32\n\nfn f(h:& *C) -> i32\n    let p: @&*C = ^h\n    0\n",
                         VALUE_INTO_MUT_REF),
    "pointer_lent_return": ("struct C\n    x: i32\n\nfn f(h:& *C) -> @&*C\n    return ^h\n",
                            VALUE_INTO_MUT_REF),
    "pointer_lent_argument": ("struct C\n    x: i32\n\nfn g(p: @&*C) -> i32\n    0\n\n"
                              "fn f(h:& *C) -> i32\n    g(^h)\n", VALUE_INTO_MUT_REF),
    # Nothing to compare: another type in a reference is the same mistake.
    "lent_other_struct": ("struct C\n    x: i32\n\nstruct D\n    a: i32\n\n"
                          "fn f(c:& C) -> @D\n    return ^c\n", VALUE_INTO_SHARED_REF),
    "value_other_struct": ("struct C\n    x: i32\n\nstruct D\n    a: i32\n\n"
                           "fn f(c: C) -> @&D\n    return ^c\n", VALUE_INTO_MUT_REF),
    "lent_other_scalar": ("fn f(n:& i32) -> @i64\n    return ^n\n", VALUE_INTO_SHARED_REF),
    "same_width_scalar": ("fn f(n:& u32) -> @&i32\n    return ^n\n", VALUE_INTO_MUT_REF),
    "integer_into_reference": ("fn f(n: i64) -> @i32\n    return ^n\n", VALUE_INTO_SHARED_REF),
    # #2281: the integer used to become the pointer.
    "lent_field_other_pointee": ("struct W\n    p: *i64\n\nfn f(n:& i32) -> i32\n    var w: W\n"
                                 "    w.p = ^n\n    0\n", VALUE_INTO_SHARED_REF),
    "lent_pointer_other_struct": ("struct C\n    x: i32\n\nstruct D\n    a: i32\n\nstruct W\n    p: *D\n\n"
                                  "fn f(c:& C) -> i32\n    let w = W { p: ^c }\n    0\n", VALUE_INTO_SHARED_REF),
    # #2313: no `:&` involved, and it was invalid IR.
    "local_returned": ("struct T\n    id: i32\n\nfn f(k: i32) -> @T\n    let t: T = T { id: 3 }\n    return ^t\n",
                       VALUE_INTO_SHARED_REF),
    "local_tail": ("struct T\n    id: i32\n\nfn f(k: i32) -> @T\n    let t: T = T { id: 3 }\n    ^t\n",
                   VALUE_INTO_SHARED_REF),
    # An rvalue has no `@`, and doesn't borrow itself.
    "call_result": ("struct C\n    x: i32\n\nfn mk() -> C\n    C { x: 1 }\n\nfn g(p: @C) -> i32\n    0\n\n"
                    "fn f() -> i32\n    g(^mk())\n", VALUE_INTO_SHARED_REF),
    "string_into_strview_ref": ("fn g(p: @StrView) -> i32\n    0\n\nfn f() -> i32\n    g(^\"hi\")\n",
                                VALUE_INTO_SHARED_REF),
    "string_into_strview_ptr": ("fn g(p: *StrView) -> i32\n    0\n\nfn f() -> i32\n    g(^\"hi\")\n",
                                VALUE_INTO_SHARED_REF),
    "strview_into_ref": ("fn g(p: @StrView) -> i32\n    0\n\nfn f(s: StrView) -> i32\n    g(^s)\n",
                         VALUE_INTO_SHARED_REF),
    # A move-only referent gets this error too, not "cannot move out".
    "move_only_lent": ("struct R\n    h: i32\n\nimpl Drop for R\n    fn drop(self: @&R)\n        self.h = 0\n\n"
                       "fn f(r:& R) -> @&R\n    return ^r\n", VALUE_INTO_MUT_REF),
    "move_only_argument": ("struct R\n    h: i32\n\nimpl Drop for R\n    fn drop(self: @&R)\n        self.h = 0\n\n"
                           "fn g(p: @R) -> i32\n    0\n\nfn f(r: R) -> i32\n    g(^r)\n", VALUE_INTO_SHARED_REF),
    "scalar_element": ("fn f(n:& i32) -> i32\n    let a: [1]*i32 = [^n]\n    0\n", VALUE_INTO_SHARED_REF),
    "scalar_field": ("struct W\n    p: *i32\n\nfn f(n: i32) -> i32\n    let w = W { p: ^n }\n    0\n",
                     VALUE_INTO_SHARED_REF),
    "scalar_payload": ("enum E\n    V(*i32)\n    N\n\nfn f(n: i32) -> i32\n    let e: E = E.V(^n)\n    0\n",
                       VALUE_INTO_SHARED_REF),
    "mutable_scalar_field": ("struct W\n    p: @&i32\n\nfn f(n:& i32) -> i32\n    let w = W { p: ^n }\n    0\n",
                             VALUE_INTO_MUT_REF),
    # #2325 case 2: `@&h` is an `@&*C`, and a `*D` can't be stored through it.
    "other_pointer_let": ("struct C\n    x: i32\n\nstruct D\n    a: i32\n\n"
                          "fn f(h:& *C) -> i32\n    let p: @&*D = ^@&h\n    0\n", REF_TO_OTHER_POINTER),
    "other_pointer_argument": ("struct C\n    x: i32\n\nstruct D\n    a: i32\n\nfn g(p: @&*D) -> i32\n    0\n\n"
                               "fn f(h:& *C) -> i32\n    g(^@&h)\n", REF_TO_OTHER_POINTER),
    "other_scalar_pointer": ("fn f(h:& *i32) -> i32\n    let p: @&*i64 = ^@&h\n    0\n", REF_TO_OTHER_POINTER),
    # #2364: a scalar pointee has no name to compare, so each place that keeps
    # the pointee of a pointee is a row: the slot (a param, a return, an
    # assigned local) and the referent (a plain local, a field, a reference).
    "other_scalar_pointer_argument": ("fn g(p: @&*i64) -> i32\n    0\n\nfn f(h:& *i32) -> i32\n    g(^@&h)\n",
                                      REF_TO_OTHER_POINTER),
    "other_scalar_pointer_sign": ("fn f(h:& *u32) -> @&*i32\n    return ^@&h\n", REF_TO_OTHER_POINTER),
    "other_scalar_pointer_assign": ("fn f(h:& *i32, d: @&*i64) -> i32\n    var p: @&*i64 = d\n    p = ^@&h\n    0\n",
                                    REF_TO_OTHER_POINTER),
    "other_scalar_pointer_local": ("fn f() -> i32\n    var q: *i32 = null\n    let p: @&*i64 = ^@&q\n    0\n",
                                   REF_TO_OTHER_POINTER),
    "other_scalar_pointer_field": ("struct V\n    q: *i32\n\nfn f(v:& V) -> i32\n    let p: @&*i64 = ^@&v.q\n    0\n",
                                   REF_TO_OTHER_POINTER),
    "other_scalar_pointer_reference": ("fn f(h: @&*i32) -> i32\n    let p: @&*i64 = ^h\n    0\n",
                                       REF_TO_OTHER_POINTER),
    "other_scalar_pointer_declared": ("fn f(h:& *i32) -> i32\n    let q: @&*i32 = @&h\n    let p: @&*i64 = ^q\n    0\n",
                                      REF_TO_OTHER_POINTER),
    "other_scalar_pointer_shared": ("fn f(h:& *i32) -> i32\n    let p: @*i64 = ^@h\n    0\n", REF_TO_OTHER_POINTER),
    # #3160: `@&q` of a reference `q: @&i32` refers to an `@&i32`, a `*i32`:
    # another U is "a reference to one type", as it is to ritz0.
    "other_reference_pointee": ("fn f(q: @&i32) -> i32\n    let p: @&*i64 = ^@&q\n    0\n", REF_TO_OTHER_TYPE),
    "other_reference_pointee_shared": ("fn f(q: @i32) -> i32\n    let p: @*i64 = ^@q\n    0\n", REF_TO_OTHER_TYPE),
    "other_reference_struct": ("struct C\n    x: i32\n\nstruct D\n    a: i32\n\n"
                               "fn f(q: @&C) -> i32\n    let p: @&*D = ^@&q\n    0\n", REF_TO_OTHER_TYPE),
    # A generic instance keeps U's name, scalar or not, and its kind.
    "other_scalar_pointer_generic": ("fn g<T>(p: @&*T) -> i32\n    0\n\nfn f(h:& *i32) -> i32\n    g<i64>(^@&h)\n",
                                     REF_TO_OTHER_POINTER),
    "other_scalar_pointer_generic_whole": ("fn g<T>(p: @&T) -> i32\n    0\n\nfn f(h:& *i32) -> i32\n"
                                           "    g<*i64>(^@&h)\n", REF_TO_OTHER_POINTER),
    "struct_pointer_into_scalar": ("struct C\n    x: i32\n\nfn f(h:& *C) -> i32\n    let p: @&*i32 = ^@&h\n    0\n",
                                   REF_TO_OTHER_POINTER),
    # A temporary has nothing to borrow, whatever its drop would have been.
    "move_only_temporary": ("struct R\n    h: i32\n\nimpl Drop for R\n    fn drop(self: @&R)\n        self.h = 0\n\n"
                            "fn mk() -> R\n    R { h: 1 }\n\nfn g(p: @R) -> i32\n    0\n\n"
                            "fn f() -> i32\n    g(^mk())\n", VALUE_INTO_SHARED_REF),
    # A pattern's payload is judged: the scrutinee names its instance.
    "pattern_payload": ("import ritzlib.option\n\nstruct C\n    x: i32\n\nfn rd(p: @C) -> i32\n    p.x\n\n"
                        "fn mk() -> Option<C>\n    Some(C { x: 3 })\n\n"
                        "fn f() -> i32\n    match mk()\n        Some(o) => rd(^o)\n        None => 0\n",
                        VALUE_INTO_SHARED_REF),
    # A generic struct's instance keeps the `&` of its field, however many
    # params it has.
    "generic_mutable_field": ("struct C\n    x: i32\n\nstruct W<T>\n    r: @&T\n\n"
                              "fn f(c:& C) -> i32\n    let w = W<C> { r: ^c }\n    0\n", VALUE_INTO_MUT_REF),
    "generic_mutable_field_two_params": ("struct C\n    x: i32\n\nstruct W<T, U>\n    r: @&T\n    u: U\n\n"
                                         "fn f(c:& C) -> i32\n    let w = W<C, i32> { r: ^c, u: 0 }\n    0\n",
                                         VALUE_INTO_MUT_REF),
    "generic_instance": ("struct C\n    x: i32\n\nfn g<T>(v: T) -> @T\n    return ^v\n\n"
                         "fn f(c: C) -> i32\n    g<C>(c)\n    0\n", VALUE_INTO_SHARED_REF),
    "array_into_span": ("import ritzlib.span\n\nfn g(s: Span<i32>) -> i32\n    0\n\nfn f(a: [2]i32) -> i32\n    g(^a)\n",
                        VALUE_INTO_SHARED_REF),
}

# Written out: what the error tells you to do. Each writes through or reads the
# caller's value after the reference was made, so a copy can't pass.
EXPLICIT = {
    "let": ("fn go(c:& C)\n    let p: @&C = @&c\n    p.x = 3\n",
            "    var c = C { x: 1 }\n    go(c)\n    c.x\n", 3),
    "var": ("fn go(c:& C)\n    var p: @&C = @&c\n    p.x = 3\n",
            "    var c = C { x: 1 }\n    go(c)\n    c.x\n", 3),
    "return": ("fn id(c:& C) -> @&C\n    return @&c\n",
               "    var c = C { x: 1 }\n    let r = id(c)\n    r.x = 3\n    c.x\n", 3),
    "tail": ("fn id(c:& C) -> @&C\n    @&c\n",
             "    var c = C { x: 1 }\n    let r = id(c)\n    r.x = 3\n    c.x\n", 3),
    "shared_read": ("fn rd(p: @C) -> i32\n    p.x\n\nfn go(c:& C) -> i32\n    c.x = 3\n    rd(@c)\n",
                    "    var c = C { x: 1 }\n    go(c)\n", 3),
    "pass_on": ("fn wr(p: @&C)\n    p.x = 3\n\nfn go(c:& C)\n    wr(@&c)\n",
                "    var c = C { x: 1 }\n    go(c)\n    c.x\n", 3),
    "pointer": ("fn wr(p: *C)\n    p.x = 3\n\nfn go(c:& C)\n    wr(@c)\n",
                "    var c = C { x: 1 }\n    go(c)\n    c.x\n", 3),
    "field": ("struct W\n    r: @&C\n\nfn go(c:& C)\n    let w = W { r: @&c }\n    w.r.x = 3\n",
              "    var c = C { x: 1 }\n    go(c)\n    c.x\n", 3),
    "assign": ("fn go(c:& C, d: @&C)\n    var p: @&C = d\n    p = @&c\n    p.x = 3\n",
               "    var c = C { x: 1 }\n    var d = C { x: 1 }\n    go(c, @&d)\n    c.x\n", 3),
    "scalar": ("fn go(n:& i32)\n    let p: @&i32 = @&n\n    *p = 3\n",
               "    var n: i32 = 1\n    go(n)\n    n\n", 3),
    "scalar_return": ("fn id(n:& i32) -> @&i32\n    return @&n\n",
                      "    var n: i32 = 1\n    let p = id(n)\n    *p = 3\n    n\n", 3),
    # A `:&` param into a `:&` param is the one implicit borrow.
    "lent_on": ("fn wr(c:& C)\n    c.x = 3\n\nfn go(c:& C)\n    wr(c)\n",
                "    var c = C { x: 1 }\n    go(c)\n    c.x\n", 3),
    "pointer_param_lent_on": ("fn wr(h:& *C, d: *C)\n    h = d\n\nfn go(h:& *C, d: *C)\n    wr(h, d)\n",
                              "    var c = C { x: 3 }\n    var d = C { x: 1 }\n    var p: *C = @d\n"
                              "    go(p, @c)\n    p.x\n", 3),
    "pointer_param_borrowed": ("fn go(h:& *C, d: *C)\n    let p: @&*C = @&h\n    *p = d\n",
                               "    var c = C { x: 3 }\n    var d = C { x: 1 }\n    var p: *C = @d\n"
                               "    go(p, @c)\n    p.x\n", 3),
    # #2364: the same `*U`, with a scalar U, still fits.
    "scalar_pointer_param_borrowed": ("fn go(h:& *i32, d: *i32)\n    let p: @&*i32 = @&h\n    *p = d\n",
                                      "    var n: i32 = 3\n    var m: i32 = 1\n    var p: *i32 = @m\n"
                                      "    go(p, @n)\n    *p\n", 3),
    # #3160: `@&q` of a reference to the same U still fits.
    "reference_pointee_borrowed": ("fn go(q: @&i32)\n    let p: @&*i32 = @&q\n    **p = 3\n",
                                   "    var n: i32 = 1\n    go(@&n)\n    n\n", 3),
    # An un-annotated copy records no U, and isn't judged for it.
    "scalar_pointer_untyped_copy": ("fn go(h:& *i32, d: *i32)\n    let r = @&h\n    let p: @&*i32 = r\n    *p = d\n",
                                    "    var n: i32 = 3\n    var m: i32 = 1\n    var p: *i32 = @m\n"
                                    "    go(p, @n)\n    *p\n", 3),
    "plain_pointer_lent": ("fn wr(h:& *C, d: *C)\n    h = d\n",
                           "    var c = C { x: 3 }\n    var d = C { x: 1 }\n    var p: *C = @d\n"
                           "    wr(p, @c)\n    p.x\n", 3),
    "array_span": ("fn sum(s: Span<i32>) -> i32\n    s[0] + s[1]\n",
                   "    var a: [2]i32 = [1, 2]\n    sum(@a)\n", 3),
    "reference_assigned": ("fn go(d: @&C, e: @&C)\n    var p: @&C = d\n    p = e\n    p.x = 3\n",
                           "    var c = C { x: 1 }\n    var d = C { x: 1 }\n    go(@&d, @&c)\n    c.x\n", 3),
    "scalar_reference_assigned": ("fn go(d: @&i32, e: @&i32)\n    var p: @&i32 = d\n    p = e\n    *p = 3\n",
                                  "    var c: i32 = 1\n    var d: i32 = 1\n    go(@&d, @&c)\n    c\n", 3),
    # A `*T` local takes an `@&T`, as it did.
    "reference_into_a_pointer_local": ("fn wr(p: *C)\n    p.x = 3\n\nfn go(d: @&C)\n    var p: *C = null\n    p = d\n    wr(p)\n",
                                       "    var c = C { x: 1 }\n    go(@&c)\n    c.x\n", 3),
    # `null` is no value of a type, and stays what it was.
    "null_into_a_reference": ("", "    let p: @C = null\n    3\n", 3),
}

EXPLICIT_HEAD = "import ritzlib.span\n\nstruct C\n    x: i32\n\n"

# Each of these is a slot this rule reaches and ritz1 can't compile for a reason
# with no reference in it. The row is refused, just not at this location.
SITE_GAPS = {}
SHAPE_GAPS = {}
EXPLICIT_GAPS = {}


def _source(site, slot, binding):
    head = TYPES.replace("{S}", SLOT_TYPES[slot])
    return _main(head + SITES[site].replace("{S}", SLOT_TYPES[slot]).replace("{B}", BINDINGS[binding]),
                 "    0\n")


def _params(table, gaps):
    for name in _ids(table):
        for compiler in COMPILERS:
            marks = []
            if compiler != "ritz0" and name in gaps:
                marks.append(pytest.mark.xfail(strict=True, reason=f"AGAST #{gaps[name]}"))
            yield pytest.param(name, compiler, marks=marks, id=f"{name}-{compiler}")


@pytest.mark.parametrize("site,compiler", list(_params(SITES, SITE_GAPS)))
@pytest.mark.parametrize("slot", _ids(SLOT_TYPES))
@pytest.mark.parametrize("binding", _ids(BINDINGS))
def test_a_value_never_fits_a_reference_slot(tmp_path, compiler, site, slot, binding):
    _assert_refused(compiler, tmp_path, f"{site}_{slot}_{binding}",
                    _source(site, slot, binding), MESSAGE[slot])


@pytest.mark.parametrize("shape,compiler", list(_params(OTHER_SHAPES, SHAPE_GAPS)))
def test_every_shape_of_value_is_refused(tmp_path, compiler, shape):
    body, message = OTHER_SHAPES[shape]
    _assert_refused(compiler, tmp_path, shape, _main(body, "    0\n"), message)


@pytest.mark.parametrize("name,compiler", list(_params(EXPLICIT, EXPLICIT_GAPS)))
def test_the_written_reference_is_the_callers_address(tmp_path, compiler, name):
    body, entry, want = EXPLICIT[name]
    assert _run(compiler, tmp_path, name, _main(EXPLICIT_HEAD + body, entry)) == want


@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_hint_names_the_form_the_slot_takes(tmp_path, compiler):
    """A mutable slot asks for `@&x`, the others for `@x` (R1's table)."""
    assert "`@&x`" in VALUE_INTO_MUT_REF and "`@x`" in VALUE_INTO_SHARED_REF
    _assert_refused(compiler, tmp_path, "hint",
                    _main("fn f(n:& i32) -> @&i32\n    ^n\n", "    0\n"), VALUE_INTO_MUT_REF)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_receiver_taken_as_an_argument_is_not_a_slot(tmp_path, compiler):
    """`v.push(x)` is `vec_push(v, x)`: `x` doesn't land in the `@&Vec`."""
    src = _main("import ritzlib.gvec\n\nfn go() -> i32\n    var v: Vec<i32> = vec_new<i32>()\n"
                "    let x: i32 = 3\n    v.push(x)\n    vec_get<i32>(@v, 0)\n", "    go()\n")
    comp, ll, _ = _compile(compiler, tmp_path, "receiver", src)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr


@pytest.mark.parametrize("order", ["reference_last", "value_last"])
def test_a_pattern_binds_its_own_instances_payload(tmp_path, order):
    """`Some` belongs to every Option, and `variant_to_enum` holds the last one
    registered. `o` here is an `@C` whichever that is: read as the other
    instance's `D` it would be a value in a reference slot, and wrongly refused.
    ritz0's checker alone has this table."""
    other = "fn other() -> Option<D>\n    None\n\n"
    mine = "fn mk(c: @C) -> Option<@C>\n    Some(c)\n\n"
    body = ("import ritzlib.option\n\nstruct C\n    x: i32\n\nstruct D\n    a: i32\n\n"
            "fn rd(p: @C) -> i32\n    p.x\n\n"
            + (other + mine if order == "reference_last" else mine + other)
            + "fn go(c: @C) -> i32\n    other()\n    match mk(c)\n        Some(o) => rd(o)\n"
              "        None => 0\n")
    comp, ll, _ = _compile("ritz0", tmp_path, "pattern", _main(body, "    0\n"))
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr


def test_a_range_of_a_pointer_is_not_a_value_in_a_slot(tmp_path):
    """`p[1..3]` is a slice, not an element, so it's no `T` in a `*T`. ritz0
    doesn't slice a raw pointer at all, and nor does ritz1 (test_slice_only_three.py)."""
    src = _main("fn tail(p: *i32) -> *i32\n    p[1..3]\n", "    0\n")
    comp, _, _ = _compile("ritz0", tmp_path, "range", src)
    assert comp.returncode != 0
    assert "main.ritz:" in comp.stdout + comp.stderr
    assert "a pointer can't be sliced (only String, Vec and Span can)" in comp.stdout + comp.stderr
