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

PAYLOAD_ROWS (AGAST #3029) are the literals #3014 refused for having no slot:
an enum / Option payload, and an untyped `let` of pointers.

ritz0 refuses to index a nested `[ [1, 2], [3, 4]]` ("Cannot index type"), so
there is no nested row: no reference result to pin.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

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

# AGAST #3029: a literal or fill with no `[N]T` slot of its own reached
# emit_expr's shadow `[N x i64]`, whose ADDRESS became the value: each of these
# ran to a wrong answer or a segfault on ritz1, and #3014 refused them.  An
# enum or Option payload is built in the payload's own `[N]T`, and a pointer
# element types the `let` as `[N]*T`, T recorded so `*a[1]` loads T's width.
PAYLOAD_ROWS = {
    "option_payload": ("""\
pub fn main() -> i32
    var o: Option<[2]u8> = Some([4, 3])
    match o
        Some(a) => return a[1] as i32
        None => return 9
    0
""", 3),
    "option_payload_fill": ("""\
pub fn main() -> i32
    var o: Option<[3]i16> = Some([-300; 3])
    match o
        Some(a) => return (a[2] + 303) as i32
        None => return 9
    0
""", 3),
    # The ticket's program, and Err's payload (tag 1) at its `[2]i32`.
    "enum_payload": ("""\
enum Pay
    V([2]u8)
    N

pub fn main() -> i32
    var e: Pay = V([4, 3])
    match e
        V(a) => return a[1] as i32
        N => return 9
    0
""", 3),
    "enum_payload_fill": ("""\
enum Pay
    V([2]u8)
    N

pub fn main() -> i32
    var e: Pay = V([3; 2])
    match e
        V(a) => return a[1] as i32
        N => return 9
    0
""", 3),
    "result_err_payload": ("""\
pub fn main() -> i32
    var r: Result<i32, [2]i32> = Err([4, -3])
    match r
        Ok(v) => return 9
        Err(a) => return a[0] + a[1] + 2
    0
""", 3),
    # A struct element: emit_expr's #2266 branch returned the literal's address.
    "struct_element_payload": ("""\
struct C
    x: i32

enum Pay
    V([2]C)
    N

pub fn main() -> i32
    let c = C { x: 3 }
    var e: Pay = V([c, c])
    match e
        V(a) => return a[1].x
        N => return 9
    0
""", 3),
    # A payload returned, matched on the call, and passed as an argument.
    "payload_return_and_arg": ("""\
fn mk(n: u8) -> Option<[3]u8>
    if n > 0
        return Some([n, n, 7])
    None

fn take(o: Option<[2]i32>) -> i32
    match o
        Some(a) => a[0] + a[1]
        None => 0

pub fn main() -> i32
    var t: i32 = 0
    match mk(3)
        Some(a) => t = a[2] as i32 + a[0] as i32
        None => t = 50
    return t + take(Some([20, 1]))
""", 31),
    "pointer_elements": ("""\
pub fn main() -> i32
    var x: i32 = 4
    let a = [@x, @x]
    return *a[1]
""", 4),
    # The pointee's width: an i64 read of `*a[0]` is positive, and `*a[1]`
    # reads past y.
    "pointer_elements_signed": ("""\
pub fn main() -> i32
    var x: i32 = -1
    var y: i32 = 5
    let a = [@x, @y]
    if *a[0] < 0 and *a[1] == 5
        return 3
    return 4
""", 3),
    "pointer_fill": ("""\
pub fn main() -> i32
    var x: i16 = -3
    let a = [@x; 3]
    return (*a[2] + 7) as i32
""", 4),
    "struct_pointer_elements": ("""\
struct C
    x: i32

pub fn main() -> i32
    var c = C { x: 5 }
    let a = [@c, @c]
    return a[1].x
""", 5),
    # An `@&T` element is written through.
    "mut_ref_elements": ("""\
pub fn main() -> i32
    var x: i32 = 4
    let a = [@&x, @&x]
    *a[1] = 6
    return x
""", 6),
    "mut_ref_fill": ("""\
pub fn main() -> i32
    var x: i32 = 1
    let a = [@&x; 2]
    *a[1] = 7
    return x
""", 7),
}

ROWS.update(PAYLOAD_ROWS)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", sorted(ROWS))
def test_untyped_scalar_array_let_is_typed(tmp_path, compiler, site):
    src, want = ROWS[site]
    assert _run(compiler, tmp_path, site, src) == want
