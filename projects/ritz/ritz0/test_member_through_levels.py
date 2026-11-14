#!/usr/bin/env python3
"""`.` goes through every level of pointer and reference to the struct (AGAST #2372).

`p.f` with `p: @*C` names `C`'s field, not a field laid over the `*C` that `p`
refers to. ritz1 took one level for everything, so a read returned whatever lay
past the pointer and a write overwrote the pointer. Nothing was reported.

Each row says what the program must exit with, worked out from what it means.
ritz0 isn't the oracle: `GAPS` lists where it's wrong or refuses, and each is a
strict xfail citing its ticket.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

TYPES = """\
struct C
    x: i32
    y: i32

struct W
    c: C
    pc: *C
    a: [2]i32

struct K
    b: i8
    l: i64
    f: bool
    d: f64

impl C
    fn get(self: @C) -> i32
        self.x
    fn set(self: @&C, v: i32)
        self.x = v

"""

MAKE_C = "    var c = C { x: 1, y: 7 }\n    var q: *C = @&c\n"
MAKE_W = ("    var d = C { x: 1, y: 7 }\n"
          "    var w = W { c: C { x: 1, y: 7 }, pc: @&d, a: [1, 2] }\n"
          "    var q: *W = @&w\n")
MAKE_K = "    var k = K { b: 1, l: 5, f: true, d: 2.0 }\n    var q: *K = @&k\n"

# name: (type with `{T}` for the struct, argument, what the argument needs).
# `p:& *T` isn't spelled like the others, so the whole param is here.
LEVELS = {
    "shared_ptr": ("p: @*{T}", "@q", ""),
    "mut_ptr": ("p: @&*{T}", "@&q", ""),
    "lent_ptr": ("p:& *{T}", "q", ""),
    "ptr_ptr": ("p: **{T}", "@&q", ""),
    "ptr_ptr_ptr": ("p: ***{T}", "@&r", "    var r: **{T} = @&q\n"),
    "shared_ptr_ptr": ("p: @**{T}", "@r", "    var r: **{T} = @&q\n"),
    "mut_ptr_ptr": ("p: @&**{T}", "@&r", "    var r: **{T} = @&q\n"),
    "lent_ptr_ptr": ("p:& **{T}", "r", "    var r: **{T} = @&q\n"),
    "shared_ptr_ptr_ptr": ("p: @***{T}", "@t", "    var r: **{T} = @&q\n    var t: ***{T} = @&r\n"),
}

# name: (body of `g`, its return type, what `main` ends with after `g`, exit code).
C_SHAPES = {
    "read": ("p.y", "i32", None, 7),
    "read_both": ("p.x + p.y", "i32", None, 8),
    "address_read": ("let a: @i32 = @p.y\n    *a", "i32", None, 7),
    "method_read": ("p.get()", "i32", None, 1),
    "store": ("p.x = 3", "", "c.x * 10 + c.y", 37),
    "store_second_field": ("p.y = 3", "", "c.x * 10 + c.y", 13),
    "compound": ("p.x += 2", "", "c.x * 10 + c.y", 37),
    "address_store": ("let a: @&i32 = @&p.x\n    *a = 3", "", "c.x * 10 + c.y", 37),
    "copy_read": ("let r = p\n    r.y", "i32", None, 7),
    "copy_store": ("var r = p\n    r.x = 3", "", "c.x * 10 + c.y", 37),
    "method_store": ("p.set(3)", "", "c.x * 10 + c.y", 37),
    "pointer_survives": ("p.x = 3", "", "q.y", 7),
}

W_SHAPES = {
    "nested_read": ("p.c.y", "i32", None, 7),
    "nested_store": ("p.c.x = 3", "", "w.c.x * 10 + w.c.y", 37),
    "nested_compound": ("p.c.x += 2", "", "w.c.x * 10 + w.c.y", 37),
    "nested_address": ("let a: @i32 = @p.c.y\n    *a", "i32", None, 7),
    "element_address": ("let a: @i32 = @p.a[1]\n    *a", "i32", None, 2),
    "array_compound": ("p.a[1] += 7", "", "w.a[1] + w.a[0]", 10),
    "for_over_field": ("var n: i32 = 0\n    for v in p.a\n        n += v\n    n", "i32", None, 3),
    "match_on_field": ("match p.c.y\n        7 => 3\n        _ => 1", "i32", None, 3),
    "nested_method_read": ("p.c.get()", "i32", None, 1),
    "nested_method_store": ("p.c.set(3)", "", "w.c.x", 3),
    "pointer_field_read": ("p.pc.y", "i32", None, 7),
    "pointer_field_store": ("p.pc.x = 3", "", "d.x * 10 + d.y", 37),
    "array_read": ("p.a[1]", "i32", None, 2),
    "array_store": ("p.a[1] = 9", "", "w.a[1] + w.a[0]", 10),
    "whole_field": ("p.c = C { x: 3, y: 4 }", "", "w.c.x * 10 + w.c.y", 34),
}

K_SHAPES = {
    "i8_store": ("p.b = 3", "", "k.b as i32 + k.l as i32", 8),
    "i64_store": ("p.l = 3", "", "k.b as i32 + k.l as i32", 4),
    "i64_read": ("p.l", "i64", None, 5),
    "bool_store": ("p.f = false", "", "if k.f\n        return 1\n    3", 3),
    "bool_read": ("if p.f\n        return 3\n    0", "i32", None, 3),
    "f64_store": ("p.d = 3.0", "", "k.d as i32", 3),
    "f64_read": ("p.d", "f64", None, 2),
}

def _program(level, struct, make, shape):
    """The source of one row. A `f64` or `i64` result leaves `main` as an i32."""
    param, arg, before = LEVELS[level]
    body, ret, after, _ = shape
    arrow = f" -> {ret}" if ret else ""
    fn = f"fn g({param.format(T=struct)}){arrow}\n    {body}\n"
    call = f"g({arg})"
    if ret in ("i64", "f64"):
        call += " as i32"
    tail = f"    {call}\n" if after is None else f"    {call}\n    {after}\n"
    return f"{TYPES}{fn}\npub fn main() -> i32\n{make}{before.format(T=struct)}{tail}"


def _rows():
    for level in LEVELS:
        for struct, make, shapes in (("C", MAKE_C, C_SHAPES), ("W", MAKE_W, W_SHAPES),
                                     ("K", MAKE_K, K_SHAPES)):
            for name, shape in shapes.items():
                yield f"{level}.{name}", _program(level, struct, make, shape), shape[3]


ROWS = {name: (src, want) for name, src, want in _rows()}


def _main(body, top="", make=MAKE_C):
    return f"{TYPES}{top}pub fn main() -> i32\n{make}{body}"


# Everything that isn't a parameter. name: (source, exit code).
HOLDERS = {
    "let_annotated_read": (_main("    let p: @*C = @q\n    p.y\n"), 7),
    "let_annotated_store": (_main("    let p: @*C = @q\n    p.x = 3\n    c.x\n"), 3),
    "var_annotated_store": (_main("    var p: @*C = @q\n    p.x = 3\n    c.x\n"), 3),
    "let_mut_annotated_store": (_main("    let p: @&*C = @&q\n    p.x = 3\n    c.x\n"), 3),
    "let_ptr_ptr_store": (_main("    let p: **C = @&q\n    p.x = 3\n    c.x\n"), 3),
    "let_shared_ptr_ptr_store": (_main("    var r: **C = @&q\n    let p: @**C = @r\n"
                                       "    p.x = 3\n    c.x\n"), 3),
    "inferred_read": (_main("    let p = @q\n    p.y\n"), 7),
    "inferred_store": (_main("    let p = @q\n    p.x = 3\n    c.x\n"), 3),
    "inferred_var_store": (_main("    var p = @q\n    p.x = 3\n    c.x\n"), 3),
    "inferred_mut_read": (_main("    let p = @&q\n    p.y\n"), 7),
    "inferred_mut_store": (_main("    let p = @&q\n    p.x = 3\n    c.x\n"), 3),
    "inferred_from_ptr_ptr": (_main("    var r: **C = @&q\n    let p = @r\n    p.y\n"), 7),
    "inferred_mut_replaces_the_pointer": (_main("    var e = C { x: 3, y: 4 }\n    let p = @&q\n    *p = @&e\n    q.x\n"), 3),
    "inferred_from_ptr_ptr_ptr": (_main("    var r: **C = @&q\n    var t: ***C = @&r\n    let p = @t\n    p.y\n"), 7),
    "let_annotated_deep": (_main("    var r: **C = @&q\n    var t: ***C = @&r\n    let p: @***C = @t\n    p.y\n"), 7),
    "copy_deep": (_main("    var r: **C = @&q\n    var t: ***C = @&r\n    g(@t)\n",
                        "fn g(p: @***C) -> i32\n    let v = p\n    v.y\n\n"), 7),
    "field_copied_through_levels": (_main("    var w = W { c: c, pc: q, a: [1, 2] }\n    var r: *W = @&w\n    g(@&r)\n",
                                          "fn g(p: **W) -> i32\n    let v = p.c\n    v.y\n\n"), 7),
    "field_borrowed_through_levels": (_main("    var w = W { c: c, pc: q, a: [1, 2] }\n    var r: *W = @&w\n    g(@&r)\n",
                                            "fn g(p: **W) -> i32\n    let v = @p.c\n    v.y\n\n"), 7),
    "field_of_a_ptr_ptr_field_copied": (_main("    var w = W { c: c, pc: q, a: [1, 2] }\n    var r: *W = @&w\n"
                                              "    var h = F { pp: @&r }\n    let v = h.pp.c\n    v.y\n",
                                              "struct F\n    pp: **W\n\n"), 7),
    "float_field_of_a_ptr_ptr_field": ("struct F\n    pp: **K\n\n" + TYPES.split("impl C")[0]
                                       + "pub fn main() -> i32\n" + MAKE_K
                                       + "    var h = F { pp: @&q }\n    let v = h.pp.d * 2.0\n    v as i32\n", 4),
    "inferred_method": (_main("    let p = @&q\n    p.set(3)\n    c.x\n"), 3),
    "field_ptr_ptr_read": (_main("    var h = F { pp: @&q }\n    h.pp.y\n", "struct F\n    pp: **C\n\n"), 7),
    "field_ptr_ptr_store": (_main("    var h = F { pp: @&q }\n    h.pp.x = 3\n    c.x\n",
                                  "struct F\n    pp: **C\n\n"), 3),
    "field_ptr_ptr_method": (_main("    var h = F { pp: @&q }\n    h.pp.set(3)\n    c.x\n",
                                   "struct F\n    pp: **C\n\n"), 3),
    "field_ptr_ptr_wide": ("struct F\n    pp: **K\n\n" + TYPES.split("impl C")[0]
                           + "pub fn main() -> i32\n" + MAKE_K
                           + "    var h = F { pp: @&q }\n    h.pp.l as i32\n", 5),
    "global_ptr_ptr_read": (_main("    var r: **C = @&q\n    G = r\n    G.y\n",
                                  "var G: **C = null\n\n"), 7),
    "global_ptr_ptr_store": (_main("    var r: **C = @&q\n    G = r\n    G.x = 3\n    c.x\n",
                                   "var G: **C = null\n\n"), 3),
    "global_ptr_ptr_ptr_read": (_main("    var r: **C = @&q\n    var t: ***C = @&r\n    G = t\n    G.y\n",
                                      "var G: ***C = null\n\n"), 7),
    "field_shared_ptr_read": (_main("    var h = F { p: @q }\n    h.p.y\n", "struct F\n    p: @*C\n\n"), 7),
    "field_mut_ptr_store": (_main("    var h = F { p: @&q }\n    h.p.x = 3\n    c.x\n",
                                  "struct F\n    p: @&*C\n\n"), 3),
    "ptr_to_shared_read": (_main("    var r: @C = q\n    g(@&r)\n", "fn g(p: *@C) -> i32\n    p.y\n\n"), 7),
    "ptr_to_mut_store": (_main("    var r: @&C = q\n    g(@&r)\n    c.x\n",
                               "fn g(p: *@&C)\n    p.x = 3\n\n"), 3),
    "shared_to_shared_read": (_main("    var r: @C = q\n    g(@r)\n", "fn g(p: @@C) -> i32\n    p.y\n\n"), 7),
    "shared_to_mut_read": (_main("    var r: @&C = q\n    g(@r)\n", "fn g(p: @@&C) -> i32\n    p.y\n\n"), 7),
    "mut_to_mut_store": (_main("    var r: @&C = q\n    g(@&r)\n    c.x\n",
                               "fn g(p: @&@&C)\n    p.x = 3\n\n"), 3),
    "global_shared_ptr_read": (_main("    G = @q\n    G.y\n", "var G: @*C = null\n\n"), 7),
    "returned_read": (_main("    h(@q).y\n", "fn h(p: @*C) -> @*C\n    p\n\n"), 7),
    "returned_ptr_ptr_read": (_main("    h(@&q).y\n", "fn h(p: **C) -> **C\n    p\n\n"), 7),
    "returned_store": (_main("    h(@q).x = 3\n    c.x\n", "fn h(p: @*C) -> @*C\n    p\n\n"), 3),
    "generic_read": (_main("    g<C>(@q)\n", "fn g<T>(p: @*B<T>) -> T\n    p.v\n\n"
                           "struct B<T>\n    v: T\n\n").replace("g<C>(@q)", "var b = B<i32> { v: 7 }\n"
                           "    var r: *B<i32> = @&b\n    g<i32>(@r) as i32"), 7),
    "generic_store": (_main("    x\n", "fn g<T>(p: @*B<T>, v: T)\n    p.v = v\n\n"
                            "struct B<T>\n    v: T\n\n").replace("    x\n", "    var b = B<i32> { v: 1 }\n"
                            "    var r: *B<i32> = @&b\n    g<i32>(@r, 3)\n    b.v\n"), 3),
    "tag_through_reference": ("import ritzlib.option\n\nfn g(p: @*Option<i32>) -> i32\n"
                              "    if p.is_some()\n        return 3\n    1\n\n"
                              "pub fn main() -> i32\n    var o: Option<i32> = Some(9)\n"
                              "    var q: *Option<i32> = @&o\n    g(@q)\n", 3),
    "tag_through_pointers": ("import ritzlib.option\n\nfn g(p: **Option<i32>) -> i32\n"
                             "    if p.is_none()\n        return 1\n    3\n\n"
                             "pub fn main() -> i32\n    var o: Option<i32> = Some(9)\n"
                             "    var q: *Option<i32> = @&o\n    g(@&q)\n", 3),
    # No level at all: a value isn't loaded through (#2398's control).
    "tag_of_a_value": ("import ritzlib.option\n\npub fn main() -> i32\n    var o: Option<i32> = Some(9)\n"
                       "    if o.is_some()\n        return 3\n    1\n", 3),
}

# `*` takes one level off; `.` takes the rest.
DEREFS = {
    "one_read": ("fn g(p: @*C) -> i32\n    (*p).y\n", "    g(@q)\n", 7),
    "one_store": ("fn g(p: @*C)\n    (*p).x = 3\n", "    g(@q)\n    c.x\n", 3),
    "both_read": ("fn g(p: @*C) -> i32\n    (**p).y\n", "    g(@q)\n", 7),
    "both_store": ("fn g(p: @*C)\n    (**p).x = 3\n", "    g(@q)\n    c.x\n", 3),
    "mut_one_store": ("fn g(p: @&*C)\n    (*p).x = 3\n", "    g(@&q)\n    c.x\n", 3),
    "ptr_ptr_one_store": ("fn g(p: **C)\n    (*p).x = 3\n", "    g(@&q)\n    c.x\n", 3),
    "ptr3_one_read": ("fn g(p: ***C) -> i32\n    (*p).y\n",
                      "    var r: **C = @&q\n    g(@&r)\n", 7),
    "ptr3_two_store": ("fn g(p: ***C)\n    (**p).x = 3\n",
                       "    var r: **C = @&q\n    g(@&r)\n    c.x\n", 3),
    "one_method_read": ("fn g(p: @*C) -> i32\n    (*p).get()\n", "    g(@q)\n", 1),
    "one_method_store": ("fn g(p: @&*C)\n    (*p).set(3)\n", "    g(@&q)\n    c.x\n", 3),
    "a_lent_pointer_reads_as_what_it_lends": ("fn g(p:& **C) -> i32\n    let s: **C = p\n    s.y\n",
                                              "    var r: **C = @&q\n    g(r)\n", 7),
    "a_lent_pointer_is_replaced": ("fn g(p:& **C, n: **C)\n    p = n\n",
                                   "    var e = C { x: 3, y: 4 }\n    var f: *C = @&e\n    var r: **C = @&q\n"
                                   "    var u: **C = @&f\n    g(r, u)\n    r.x\n", 3),
    "a_pointer_held": ("fn g(p: @*C) -> i32\n    let s: *C = *p\n    s.y\n", "    g(@q)\n", 7),
    "a_pointer_replaced": ("fn g(p: @&*C, n: *C)\n    *p = n\n",
                           "    var e = C { x: 3, y: 4 }\n    g(@&q, @&e)\n    q.x\n", 3),
}

# One level: what every other row must not have moved.
CONTROLS = {
    "pointer": ("fn g(p: *C)\n    p.x += 2\n", "    g(@&c)\n    c.x\n", 3),
    "shared": ("fn g(p: @C) -> i32\n    p.y\n", "    g(@c)\n", 7),
    "mutable": ("fn g(p: @&C)\n    p.x = 3\n", "    g(@&c)\n    c.x\n", 3),
    "lent": ("fn g(p:& C)\n    p.x = 3\n", "    g(c)\n    c.x\n", 3),
    "value": ("fn g(p: C) -> i32\n    p.y\n", "    g(c)\n", 7),
    "method_on_pointer": ("fn g(p: *C)\n    p.set(3)\n", "    g(@&c)\n    c.x\n", 3),
    "inferred_from_a_value": ("fn g()\n    pass\n", "    let p = @c\n    p.y\n", 7),
}

for _table, _prefix in ((DEREFS, "deref"), (CONTROLS, "control")):
    for _name, (_fn, _body, _want) in _table.items():
        _make = MAKE_C if _prefix == "deref" else "    var c = C { x: 1, y: 7 }\n"
        HOLDERS[f"{_prefix}.{_name}"] = (_main(_body, _fn + "\n", _make), _want)

# AGAST #2400: an un-annotated `let a = @p.f` / `@&p.f` of a scalar field holds
# what `let a: @T = @p.f` does, a pointer to the field's type.  ritz1 kept an
# i64 with no pointee: `*a = 3` stored the `ptr` as an i64 (clang refused the
# IR), and `*a` loaded 8 bytes of an i32.  `*(a + 1)` pins the pointee's width
# by its stride.  name: (g, main's body after `make`, make, exit code).
FIELD_REFS = {
    "store": ("fn g(p: *C)\n    let a = @&p.x\n    *a = 3\n", "    g(q)\n    c.x * 10 + c.y\n", MAKE_C, 37),
    "read": ("fn g(p: *C) -> i32\n    let a = @p.y\n    *a\n", "    g(q)\n", MAKE_C, 7),
    "stride": ("fn g(p: *C) -> i32\n    let a = @p.x\n    *(a + 1)\n", "    g(q)\n", MAKE_C, 7),
    "nested_store": ("fn g(p: *W)\n    let a = @&p.c.x\n    *a = 3\n", "    g(q)\n    w.c.x * 10 + w.c.y\n",
                     MAKE_W, 37),
    "i8_store": ("fn g(p: *K)\n    let a = @&p.b\n    *a = 3\n", "    g(q)\n    k.b as i32 + k.l as i32\n",
                 MAKE_K, 8),
    "bool_store": ("fn g(p: *K)\n    let a = @&p.f\n    *a = false\n", "    g(q)\n    if k.f\n        return 1\n    3\n",
                   MAKE_K, 3),
    "f64_read": ("fn g(p: *K) -> f64\n    let a = @p.d\n    *a\n", "    g(q) as i32\n", MAKE_K, 2),
    "of_a_local": ("fn g()\n    pass\n", "    let a = @&c.x\n    *a = 3\n    c.x * 10 + c.y\n", MAKE_C, 37),
}
for _name, (_fn, _body, _make, _want) in FIELD_REFS.items():
    HOLDERS[f"field_ref.{_name}"] = (_main(_body, _fn + "\n", _make), _want)


# ritz0 refused 189 of these with a raw ValueError past one extra level, on
# the store, address and method paths and through `***S` / `@**S` (#2398).
# It goes through every level now (§5.4), so every row runs on ritz0.

# ritz1 refuses these (#2399).
# `lent_ptr.copy_*` (`let r = p` of a `*S`) closed by #2596.
LOWERING_GAPS = {"returned_read", "returned_store",
                 "returned_ptr_ptr_read", "global_shared_ptr_read", "field_shared_ptr_read",
                 "field_mut_ptr_store", "ptr_to_shared_read", "ptr_to_mut_store",
                 "shared_to_shared_read", "shared_to_mut_read", "mut_to_mut_store"}


def _gap(row, compiler):
    if compiler == "ritz0":
        return None
    return 2399 if row in LOWERING_GAPS else None


def _params(table):
    for row in table:
        for compiler in COMPILERS:
            gap = _gap(row, compiler)
            marks = [pytest.mark.xfail(strict=True, reason=f"AGAST #{gap}")] if gap else []
            yield pytest.param(row, compiler, marks=marks, id=f"{row}-{compiler}")


@pytest.mark.parametrize("row,compiler", list(_params(ROWS)))
def test_member_through_levels(tmp_path, compiler, row):
    src, want = ROWS[row]
    assert _run(compiler, tmp_path, row.replace(".", "_"), src) == want


@pytest.mark.parametrize("row,compiler", list(_params(HOLDERS)))
def test_member_through_what_holds_it(tmp_path, compiler, row):
    src, want = HOLDERS[row]
    assert _run(compiler, tmp_path, row.replace(".", "_"), src) == want
