#!/usr/bin/env python3
"""An unannotated `let a = [5, 6, 7]` / `let a = [5; 3]` is a `[N]T` (AGAST #3014).

ritz0 types an array literal or fill by its first element: an untyped int
literal is `i64`, `true`/`false` is `bool`, a float literal `f64`, and a typed
value keeps its own type (`[x, x]` with `x: i32` is `[2]i32`). ritz1 did that
only for a struct element (#2266, #2976). A scalar one kept the parser's
default i64 slot, which held the address of a shadow `[N x i64]` alloca, so
`a[2]` read garbage (0) and nothing reported an error.

Each row runs on ritz0, ritz1 and ritz1_selfhosted and must return ritz0's
result on all three. The struct-element rows are #2266's and #2976's own tests
(test_array_fill_move_only.py's `untyped_let`), unchanged.

ritz0 refuses to index a nested `[ [1, 2], [3, 4]]` ("Cannot index type"), so
there is no nested row: no reference result to pin.
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = pytest.mark.integration

ROWS = {
    # The ticket's two programs: an untyped int literal element is i64.
    "int_literal": ("""\
pub fn main() -> i32
    let a = [5, 6, 7]
    return a[2] as i32
""", 7),
    "int_fill": ("""\
pub fn main() -> i32
    let a = [5; 3]
    return a[2] as i32
""", 5),
    # A `var` is the same slot, written through and read back.
    "var_literal_store": ("""\
pub fn main() -> i32
    var a = [5, 6, 7]
    a[1] = 10
    return (a[1] + a[2]) as i32
""", 17),
    # A typed value keeps its width: `[2]i32`, `[4]u8`.
    "i32_value_literal": ("""\
pub fn main() -> i32
    let x: i32 = 9
    let a = [x, x]
    return a[1]
""", 9),
    "u8_value_fill": ("""\
pub fn main() -> i32
    let x: u8 = 200
    let a = [x; 4]
    return a[3] as i32 - 190
""", 10),
    # The first element decides: `[4, x]` is `[2]i64`, as on ritz0.
    "first_element_decides": ("""\
pub fn main() -> i32
    let x: i32 = 3
    let a = [4, x]
    return (a[0] + a[1]) as i32
""", 7),
    "f64_literal": ("""\
pub fn main() -> i32
    let a = [1.5, 2.5]
    return (a[0] + a[1]) as i32
""", 4),
    "f64_fill": ("""\
pub fn main() -> i32
    let a = [2.5; 2]
    return (a[0] + a[1]) as i32
""", 5),
    "bool_literal": ("""\
pub fn main() -> i32
    let a = [false, true]
    if a[1] and not a[0]
        return 3
    return 4
""", 3),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(ROWS))
def test_untyped_scalar_array_let_is_typed(tmp_path, compiler, site):
    src, want = ROWS[site]
    assert _run(compiler, tmp_path, site, src) == want


# A literal or fill with no `[N]T` slot reached emit_expr's shadow `[N x i64]`,
# whose ADDRESS became the value: each of these ran to a wrong answer or a
# segfault on ritz1.  ritz1 now refuses them at the `[` (`^`), until #3029
# gives them a slot; ritz0's result is pinned beside, for that ticket to flip.
NO_SLOT = {
    "option_payload": ("""\
pub fn main() -> i32
    var o: Option<[2]u8> = Some(^[4, 3])
    match o
        Some(a) => return a[1] as i32
        None => return 9
    0
""", 3),
    "enum_payload_fill": ("""\
enum Pay
    V([2]u8)
    N

pub fn main() -> i32
    var e: Pay = V(^[3; 2])
    match e
        V(a) => return a[1] as i32
        N => return 9
    0
""", 3),
    "pointer_elements": ("""\
pub fn main() -> i32
    var x: i32 = 4
    let a = ^[@x, @x]
    return *a[1]
""", 4),
}

NO_SLOT_MESSAGE = ("ritz1 cannot build this array literal here: it has no `[N]T` slot "
                   "(give it one, e.g. `let a: [2]u8 = [..]`)")


@pytest.mark.parametrize("site", sorted(NO_SLOT))
def test_no_slot_literal_runs_on_ritz0(tmp_path, site):
    src, want = NO_SLOT[site]
    assert _run("ritz0", tmp_path, site, src.replace("^", "")) == want


@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("site", sorted(NO_SLOT))
def test_no_slot_literal_is_refused_on_ritz1(tmp_path, compiler, site):
    _assert_refused(compiler, tmp_path, site, NO_SLOT[site][0], NO_SLOT_MESSAGE)
