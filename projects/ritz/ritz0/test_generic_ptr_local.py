#!/usr/bin/env python3
"""A `let p: *T` local in a generic fn points at the argument type (AGAST #1551).

monomorph's `clone_stmt` substituted T in a local's type name only for a
by-value struct local.  A `let p: *T` kept the name "T" and the TYPE_STRUCT
pointee the parser gives any bare name, so after `second<u8>` the local
pointed at a struct `T` that does not exist:

- `p + 1` had no element size and was refused (#1451 fails closed);
- `*p` loaded and `*p = v` stored a `%T`, IR clang rejects;
- `let p: *Box<T>` kept "Box$T", so `p + 1` and `p.v` were refused too.

Parameters of the same types were always right: `clone_params_with_suffix`
concretizes a bare `*T` and substitutes `*Box<T>`'s name.  The local now
gets the same treatment.  `@T` / `@&T` locals go through `var_ref` (#2308)
and were already right; they are pinned here so both paths stay in step.

Every row runs on ritz0, ritz1 and ritz1_selfhosted, and all three must exit
with the row's value: ritz0's answer, by running the linked binary.
"""

import pytest
from test_ref_into_value import COMPILERS, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

LB = "struct LB\n    start: i64\n    length: i64\n\n"
BOX = "struct Box<T>\n    v: T\n\n"

# Elements 1, 10, 20: element 1 (10) is only reached by a stride of exactly
# one element; 8 bytes on a [3]u8 reads past the end, 1 byte on an [3]i32
# reads the middle of element 0.
SECOND = """\
fn second<T>(x: *T) -> T
    let p: *T = x
    let q: *T = p + 1
    return *q

"""


def _fill(elem):
    return f"    var arr: [3]{elem}\n    arr[0] = 1\n    arr[1] = 10\n    arr[2] = 20\n"


SECOND_BOX = (
    BOX
    + """\
fn second_box<T>(x: *Box<T>) -> T
    let p: *Box<T> = x
    let q: *Box<T> = p + 1
    return q.v

"""
)


def _box_main(t):
    return (
        "fn main() -> i32\n"
        f"    var arr: [3]Box<{t}>\n"
        "    arr[0].v = 1\n    arr[1].v = 10\n    arr[2].v = 20\n"
        f"    return second_box<{t}>(@arr[0]) as i32\n"
    )


# A `*T` local read and written without arithmetic: a wrong width loads or
# stores a neighbour's bytes, or a `%T` clang refuses.
DEREF = """\
fn first<T>(x: *T) -> T
    let p: *T = x
    return *p

fn main() -> i32
    var arr: [3]u8
    arr[0] = 3
    arr[1] = 10
    return first<u8>(@arr[0]) as i32
"""

STORE = """\
fn put<T>(x: *T, v: T)
    let p: *T = x
    *p = v

fn main() -> i32
    var arr: [3]u8
    arr[0] = 1
    arr[1] = 2
    arr[2] = 4
    put<u8>(@arr[1], 10)
    return arr[0] as i32 + arr[1] as i32 + arr[2] as i32
"""

# `*T` at T = `[2]i32` points at that array, recorded as a written
# `*[2]i32` local is, so `*p` copies the whole row.
DEREF_ARRAY = """\
fn first<T>(x: *T) -> T
    let p: *T = x
    return *p

fn main() -> i32
    var arr: [2][2]i32
    arr[0][0] = 1
    arr[0][1] = 2
    arr[1][0] = 5
    arr[1][1] = 6
    let a: [2]i32 = first<[2]i32>(@arr[0])
    return a[0] + a[1]
"""


def _ref(t):
    return (
        "fn get<T>(x: *T) -> T\n    let r: @T = x\n    return *r\n\n"
        "fn main() -> i32\n" + _fill(t) + f"    return get<{t}>(@arr[1]) as i32\n"
    )


def _mut_ref(t):
    # A store wider than T clobbers arr[2]: the sum is 31 only if it is not.
    return (
        "fn put<T>(x: *T, v: T)\n    let r: @&T = x\n    *r = v\n\n"
        "fn main() -> i32\n" + _fill(t) + f"    put<{t}>(@arr[1], 10)\n"
        "    return arr[0] as i32 + arr[1] as i32 + arr[2] as i32\n"
    )


REF_BOX = (
    BOX
    + """\
fn get<T>(x: *Box<T>) -> T
    let r: @Box<T> = x
    return r.v

fn main() -> i32
    var b: Box<i32>
    b.v = 7
    return get<i32>(@b)
"""
)

ROWS = {
    "ptr_u8": (
        SECOND
        + "fn main() -> i32\n"
        + _fill("u8")
        + "    return second<u8>(@arr[0]) as i32\n",
        10,
    ),
    "ptr_i32": (
        SECOND
        + "fn main() -> i32\n"
        + _fill("i32")
        + "    return second<i32>(@arr[0])\n",
        10,
    ),
    "ptr_struct": (
        LB + SECOND + "fn main() -> i32\n    var arr: [3]LB\n"
        "    arr[0].start = 0\n    arr[1].start = 10\n    arr[2].start = 20\n"
        "    let v: LB = second<LB>(@arr[0])\n    return v.start as i32\n",
        10,
    ),
    "ptr_deref_u8": (DEREF, 3),
    "ptr_store_u8": (STORE, 15),
    "ptr_deref_array": (DEREF_ARRAY, 3),
    "box_ptr_u8": (SECOND_BOX + _box_main("u8"), 10),
    "box_ptr_i32": (SECOND_BOX + _box_main("i32"), 10),
    "ref_u8": (_ref("u8"), 10),
    "mut_ref_u8": (_mut_ref("u8"), 31),
    "ref_box_i32": (REF_BOX, 7),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_generic_ptr_local_matches_ritz0(compiler, tmp_path, name):
    src, want = ROWS[name]
    assert _run(compiler, tmp_path, name, src) == want
