#!/usr/bin/env python3
"""A match payload that points to a struct reaches its fields (AGAST #2436).

`Some(v)` over a typed local `o: Option<*Pair>` bound `v` as a bare i64, so
`v.a` and `(*v).a` were "unhandled EXPR_MEMBER" on ritz1.  ritz0 ran them.  The
binding now records the struct it points to, for Option, Result and a user
enum's `*T` / `@T` / `@&T` variant, reads and stores alike.  #3047 adds
`**T`, which binds as a `let pp: **Pair` does.

Each row's exit code is worked out from the program: p is Pair { a: 2, b: 3 }.
"""

import pytest
from test_ref_into_value import COMPILERS, _assert_refused, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

HEAD = """\
struct Pair
    a: i32
    b: i32

impl Pair
    fn sum(self: @Pair) -> i32
        self.a + self.b

enum E
    P(*Pair)
    S(@Pair)
    M(@&Pair)
    PP(**Pair)
    N

pub fn main() -> i32
    var p = Pair { a: 2, b: 3 }
    let q: *Pair = @&p
    var r: *Pair = q
"""

# name: (the rest of main, exit code).
ROWS = {
    # Option<*T>: the ticket's shape, its deref spelling, a store, a method.
    "option_read": (
        "let o: Option<*Pair> = Some(q)\nmatch o\n    Some(v) => v.a + v.b\n    _ => 50",
        5,
    ),
    "option_deref_read": (
        "let o: Option<*Pair> = Some(q)\nmatch o\n    Some(v) => (*v).b\n    _ => 50",
        3,
    ),
    "option_store": (
        "let o: Option<*Pair> = Some(q)\nmatch o\n    Some(v) => v.a = 7\n    _ => 0\np.a",
        7,
    ),
    "option_deref_store": (
        "let o: Option<*Pair> = Some(q)\nmatch o\n    Some(v) => (*v).b = 9\n    _ => 0\np.b",
        9,
    ),
    "option_method": (
        "let o: Option<*Pair> = Some(q)\nmatch o\n    Some(v) => v.sum()\n    _ => 50",
        5,
    ),
    # Control: a pointer to a scalar has no fields and keeps its i64 binding.
    "option_int_pointer": (
        "var n: i32 = 4\nlet pn: *i32 = @&n\nlet o: Option<*i32> = Some(pn)\nmatch o\n    Some(v) => *v\n    _ => 50",
        4,
    ),
    # Result: each side carries its own argument.
    "result_ok": (
        "let o: Result<*Pair, i32> = Ok(q)\nmatch o\n    Ok(v) => v.b\n    Err(e) => 50",
        3,
    ),
    "result_err": (
        "let o: Result<i32, *Pair> = Err(q)\nmatch o\n    Ok(v) => 50\n    Err(e) => e.a",
        2,
    ),
    # A user enum declares the payload itself.
    "enum_read": (
        "let e: E = E.P(q)\nmatch e\n    E.P(v) => v.a + v.b\n    _ => 50",
        5,
    ),
    "enum_deref_read": (
        "let e: E = E.P(q)\nmatch e\n    E.P(v) => (*v).a\n    _ => 50",
        2,
    ),
    "enum_store": (
        "let e: E = E.P(q)\nmatch e\n    E.P(v) => v.b = 8\n    _ => 0\np.b",
        8,
    ),
    "enum_shared_read": (
        "let e: E = E.S(@p)\nmatch e\n    E.S(v) => v.b\n    _ => 50",
        3,
    ),
    # Built from `q`; enum_mut_ref_value builds it from an `@&Pair` value.
    "enum_mut_store": (
        "let e: E = E.M(q)\nmatch e\n    E.M(v) => v.a = 6\n    _ => 0\np.a",
        6,
    ),
    # Built from an `@&Pair` / `@Pair` value: ritz1 stored the ptr as an i64 (#3046)
    # and gave `Option<@&Pair>` no payload type (#2384) until #2384.
    "enum_mut_ref_value": (
        "let e: E = E.M(@&p)\nmatch e\n    E.M(v) => v.a = 6\n    _ => 0\np.a",
        6,
    ),
    "option_shared_read": (
        "let o: Option<@Pair> = Some(@p)\nmatch o\n    Some(v) => v.b\n    _ => 50",
        3,
    ),
    "option_mut_store": (
        "let o: Option<@&Pair> = Some(@&p)\nmatch o\n    Some(v) => v.a = 4\n    _ => 0\np.a",
        4,
    ),
    # AGAST #3047: two levels.  `v` is a `**Pair`; `(*v)` is the `*Pair`.
    "option_ptr_ptr_read": (
        "let o: Option<**Pair> = Some(@&r)\nmatch o\n    Some(v) => (*v).b\n    _ => 50",
        3,
    ),
    "option_ptr_ptr_local": (
        "let pp: **Pair = @&r\nlet o: Option<**Pair> = Some(pp)\nmatch o\n    Some(v) => (**v).a\n    _ => 50",
        2,
    ),
    "option_ptr_ptr_store": (
        "let o: Option<**Pair> = Some(@&r)\nmatch o\n    Some(v) => (*v).a = 7\n    _ => 0\np.a",
        7,
    ),
    "result_ptr_ptr_ok": (
        "let o: Result<**Pair, i32> = Ok(@&r)\nmatch o\n    Ok(v) => (**v).b\n    Err(e) => 50",
        3,
    ),
    "result_ptr_ptr_err": (
        "let o: Result<i32, **Pair> = Err(@&r)\nmatch o\n    Ok(v) => 50\n    Err(e) => (*e).a",
        2,
    ),
    "enum_ptr_ptr_read": (
        "let e: E = E.PP(@&r)\nmatch e\n    E.PP(v) => (*v).a + (**v).b\n    _ => 50",
        5,
    ),
    # The binding's pointee is the `*Pair`, not the Pair: `**v` copies a Pair
    # and `*v = ...` retargets r.
    "option_ptr_ptr_copy": (
        "let o: Option<**Pair> = Some(@&r)\nmatch o\n    Some(v) =>\n        let x: Pair = **v\n        x.a * 10 + x.b\n    _ => 50",
        23,
    ),
    "enum_ptr_ptr_retarget": (
        "var p2 = Pair { a: 6, b: 7 }\nlet e: E = E.PP(@&r)\nmatch e\n    E.PP(v) => *v = @&p2\n    _ => 0\nr.a",
        6,
    ),
    "enum_ptr_ptr_store": (
        "let e: E = E.PP(@&r)\nmatch e\n    E.PP(v) => (**v).b = 8\n    _ => 0\np.b",
        8,
    ),
    # AGAST #3114: a `**Pair` reaches a field through `let w = *v` (w is the
    # `*Pair`), `(*v)[0]` (index the `*Pair`) and `v[0]` (index the `**Pair`),
    # for a typed local and for a `Some(v)` payload alike.
    "ptr_ptr_local_let_deref": (
        "let v: **Pair = @&r\nlet w = *v\nw.b",
        3,
    ),
    "ptr_ptr_local_deref_index": (
        "let v: **Pair = @&r\n(*v)[0].a",
        2,
    ),
    "ptr_ptr_local_index": (
        "let v: **Pair = @&r\nv[0].a + v[0].b",
        5,
    ),
    "option_ptr_ptr_let_deref": (
        "let o: Option<**Pair> = Some(@&r)\nmatch o\n    Some(v) =>\n        let w = *v\n        w.b\n    _ => 50",
        3,
    ),
    "option_ptr_ptr_deref_index": (
        "let o: Option<**Pair> = Some(@&r)\nmatch o\n    Some(v) => (*v)[0].a\n    _ => 50",
        2,
    ),
    "option_ptr_ptr_index": (
        "let o: Option<**Pair> = Some(@&r)\nmatch o\n    Some(v) => v[0].a + v[0].b\n    _ => 50",
        5,
    ),
}

# ritz1 and ritz1_selfhosted only; ritz0 runs every row.
GAPS = {}


def _program(rest):
    return HEAD + "".join(f"    {line}\n" for line in rest.split("\n"))


def _cases():
    for row in sorted(ROWS):
        for compiler in COMPILERS:
            marks = []
            if row in GAPS and compiler != "ritz0":
                marks = [pytest.mark.xfail(strict=True, reason=GAPS[row])]
            yield pytest.param(row, compiler, marks=marks, id=f"{row}-{compiler}")


@pytest.mark.parametrize("row,compiler", _cases())
def test_pointer_payload_member(tmp_path, compiler, row):
    rest, want = ROWS[row]
    assert _run(compiler, tmp_path, row, _program(rest)) == want


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_at_payload_stays_read_only(tmp_path, compiler):
    """`E.S(v)` over `S(@Pair)` binds an `@Pair`, not a `*Pair`: a write is refused."""
    marked = _program(
        "let e: E = E.S(@p)\nmatch e\n    E.S(v) => ^v.a = 6\n    _ => 0\np.a"
    )
    _assert_refused(
        compiler,
        tmp_path,
        "at_payload_store",
        marked,
        "cannot write through an `@T`: make it `@&T`",
    )
