"""AGAST #2928 / #2597: pointer minus pointer.

    let s: *u8 = c"abcd"
    let p: *u8 = s + 3
    (p - s) as i32          # 3

ritz0 lowered `p - s` on two pointers to `sub i8* %p, %s`, which clang
rejects (`invalid operand type for instruction`); #2597 was the same on two
`*E` struct pointers (`sub %struct.E*`).  ritz1 and ritz1_selfhosted gave
the distance.

LANGUAGE_SPEC §7.1 "Pointer difference": `q - p` on two pointers to the same
`T` is the distance in elements of `T`, an i64 — the inverse of `p + n`, so
`(p + n) - p == n`.  Each row checks a pointee size that the others don't:
1 byte (no scaling), 4 bytes, a struct, and a negative distance.
"""

import pytest
from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

PROGRAMS = {
    # the ticket's repro: no scaling at stride 1
    "u8": """\
pub fn main() -> i32
    let s: *u8 = c"abcd"
    let p: *u8 = s + 3
    if (p - s) as i32 != 3
        return 1
    0
""",
    # 4-byte elements: the distance is in elements, not bytes
    "i32": """\
pub fn main() -> i32
    var a: [8]i32
    let s: *i32 = @a[0]
    let p: *i32 = s + 5
    let d: i64 = p - s
    if d != 5
        return 1
    0
""",
    # #2597: two `*E` struct pointers
    "struct": """\
struct E
    a: i64
    b: i32

pub fn main() -> i32
    var es: [4]E
    let p: *E = @es[0]
    let q: *E = p + 3
    if q - p != 3
        return 1
    0
""",
    # the earlier pointer on the left: a negative distance
    "negative": """\
pub fn main() -> i32
    var a: [8]i64
    let s: *i64 = @a[1]
    let p: *i64 = s + 6
    if s - p != -6
        return 1
    0
""",
    # an inferred `let` holds a count, so `+ 1` is one, not sizeof(i32)
    "inferred": """\
pub fn main() -> i32
    var a: [8]i32
    let s: *i32 = @a[0]
    let p: *i32 = s + 5
    let d = p - s
    if d + 1 != 6
        return 1
    0
""",
    # reference parameters, which ritz1 may hold as `ptr`, not i64
    "refs": """\
fn dist(q: @i32, p: @i32) -> i64
    q - p

pub fn main() -> i32
    var a: [8]i32
    if dist(@a[6], @a[2]) != 4
        return 1
    0
""",
    # an `@&` operand, which ritz1 holds as `ptr`, not i64 (#1754)
    "mut_ref": """\
fn back(q: @&i32) -> i64
    q - (q - 3)

pub fn main() -> i32
    var a: [8]i32
    if back(@&a[5]) != 3
        return 1
    0
""",
    # `*u8` and `*i8` are one LLVM type, `i8*`: ritz0 gives their distance
    "signedness": """\
pub fn main() -> i32
    let p: *u8 = c"abcd"
    let s: *i8 = p as *i8
    if (p + 3) - s != 3
        return 1
    if s - (p + 1) != -1
        return 2
    0
""",
    # the distance used in place: `+ 1` adds one, and it indexes as a count
    "in_place": """\
pub fn main() -> i32
    var a: [8]i32
    a[3] = 7
    let s: *i32 = @a[0]
    let p: *i32 = s + 2
    if (p - s) + 1 != 3
        return 1
    if *(s + (p - s) + 1) != 7
        return 2
    0
""",
    # a struct field holding the pointer, and a padded struct (16 bytes)
    "field": """\
struct E
    a: i64
    b: i32

struct Cur
    start: *E
    at: *E

pub fn main() -> i32
    var es: [4]E
    let c = Cur { start: @es[0], at: @es[2] }
    if c.at - c.start != 2
        return 1
    0
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_pointer_difference_counts_elements(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, f"ptrdiff_{name}", PROGRAMS[name]) == 0


# Two pointee types have no common element to count in (#2957): ritz0 refuses
# it, located, and ritz1 counted in the left's elements.  The type is the one
# LLVM sees, so `*u8 - *i8` above is one type, and a reference operand is
# refused as its pointer is.
MIXED = {
    "ptr": ("""\
pub fn main() -> i32
    var a: [8]i32
    let s: *u8 = c"abcd"
    let p: *i32 = @a[0]
    let d: i64 = ^p - s
    0
""", "`i32*` and `i8*`"),
    "refs": ("""\
fn dist(q: @i32, p: @u8) -> i64
    ^q - p

pub fn main() -> i32
    0
""", "`i32*` and `i8*`"),
    "mut_ref": ("""\
fn back(q: @&i32, p: *i64) -> i64
    ^q + 1 - p

pub fn main() -> i32
    0
""", "`i32*` and `i64*`"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(MIXED))
def test_pointer_difference_of_two_types_is_refused(tmp_path, compiler, name):
    src, types = MIXED[name]
    _assert_refused(
        compiler,
        tmp_path,
        f"ptrdiff_mixed_{name}",
        src,
        f"pointer difference needs two pointers to the same type, got {types}",
    )
