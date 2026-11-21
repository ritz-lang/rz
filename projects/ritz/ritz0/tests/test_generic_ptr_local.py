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

AGAST #3662: at T = `*U` a `let p: *T` is a `**U` local (the `ptr_arg_*`,
`ptr_store_ptr_*`, `ptr_field_*` and `ptr_second_ptr_*` rows).

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


# AGAST #3662: `*T` at T = `*U` is a `**U` local, recorded as a written one
# is (TYPE_PTR_PTR, U's depth-packed inner slot), as `x: *T` is for a param.
# It was a `*` with a TYPE_PTR pointee, which ref_check refused at `return *p`
# ("a value doesn't fit a reference slot").  Both elements point at n, so a
# stride or width error reads a pointer's other half, not 9.
def _ptr_arg(decl, t, setup, ret):
    return (
        f"fn first<T>(x: *T) -> T\n    let p: {decl} = x\n    return *p\n\n"
        "fn main() -> i32\n" + setup + f"    var arr: [2]{t}\n"
        "    arr[0] = @n\n    arr[1] = @n\n"
        f"    let q: {t} = first<{t}>(@arr[0])\n    return {ret}\n"
    )


S = "struct S\n    a: i32\n    b: i32\n\n"
N_I32 = "    var n: i32 = 9\n"
N_S = "    var n: S\n    n.a = 4\n    n.b = 9\n"
N_PU8 = "    var c: u8 = 9\n    var n: *u8 = @c\n"

# A store through the local writes the whole pointer, not a T-wide part of it.
# `(*p).b` reads S's field through the `*S` the local points at.
PTR_ARG_FIELD = (
    S
    + """\
fn getb<T>(x: *T) -> i32
    let p: *T = x
    return (*p).b

fn main() -> i32
    var n: S
    n.a = 4
    n.b = 9
    var arr: [2]*S
    arr[0] = @n
    arr[1] = @n
    return getb<*S>(@arr[0])
"""
)

PTR_ARG_STORE = """\
fn put<T>(x: *T, v: T)
    let p: *T = x
    *p = v

fn main() -> i32
    var a: i32 = 2
    var b: i32 = 9
    var arr: [2]*i32
    arr[0] = @a
    arr[1] = @a
    put<*i32>(@arr[0], @b)
    return *arr[0] * 10 + *arr[1]
"""


# AGAST #3663: a `*[3]T` local's element is the argument type.  It stayed a
# struct `T`, so `p[1]` was refused as "a whole struct element".
def _ptr_array(kw, t, ret):
    return (
        f"fn second<T>(x: *[3]T) -> T\n    {kw} p: *[3]T = x\n    return p[1]\n\n"
        f"fn main() -> i32\n    var arr: [3]{t}\n" + ret
    )


PA_SCALAR = "    arr[0] = 1\n    arr[1] = 10\n    arr[2] = 20\n"
PA_U8 = PA_SCALAR + "    return second<u8>(@arr) as i32\n"
PA_I64 = PA_SCALAR + "    return second<i64>(@arr) as i32\n"
PA_LB = (
    "    arr[0].start = 1\n    arr[1].start = 10\n    arr[2].start = 20\n"
    "    let v: LB = second<LB>(@arr)\n    return v.start as i32\n"
)

# `*[3]*T`'s element points at T (#2378): `*p[1]` loads a T, not a `%T`.
PA_PTR = """\
fn second<T>(x: *[3]*T) -> T
    let p: *[3]*T = x
    return *p[1]

fn main() -> i32
    var a: u8 = 1
    var b: u8 = 10
    var arr: [3]*u8
    arr[0] = @a
    arr[1] = @b
    arr[2] = @a
    return second<u8>(@arr) as i32
"""

# AGAST #3686: at T = `***u8` the argument spelled "" past two levels, so
# `first<***u8>` became `first$`, a procedure: "`first` returns nothing".
# `deep`'s `****p` reaches the leaf through the `****u8` local, so it reads
# #3662's depth packing (`inner + extra * PTR_DEPTH_UNIT`) in
# ptr_local_take_ptr_arg; recorded as a `**u8` it loads a pointer as the u8.
PTR_ARG_PTR3 = """\
fn first<T>(x: *T) -> T
    let p: *T = x
    return *p

fn deep<T>(x: *T) -> i32
    let p: *T = x
    return ****p as i32

fn main() -> i32
    var c: u8 = 9
    var m: *u8 = @c
    var n: **u8 = @m
    var arr: [2]***u8
    arr[0] = @n
    arr[1] = @n
    let q: ***u8 = first<***u8>(@arr[0])
    return ***q as i32 * 10 + deep<***u8>(@arr[1])
"""

ROWS = {
    "ptr_array_ptr_u8": (PA_PTR, 10),
    "ptr_array_let_u8": (_ptr_array("let", "u8", PA_U8), 10),
    "ptr_array_var_u8": (_ptr_array("var", "u8", PA_U8), 10),
    "ptr_array_let_i64": (_ptr_array("let", "i64", PA_I64), 10),
    "ptr_array_var_i64": (_ptr_array("var", "i64", PA_I64), 10),
    "ptr_array_let_struct": (LB + _ptr_array("let", "LB", PA_LB), 10),
    "ptr_array_var_struct": (LB + _ptr_array("var", "LB", PA_LB), 10),
    "ptr_arg_ptr_i32": (S + _ptr_arg("*T", "*i32", N_I32, "*q"), 9),
    "ptr_arg_ptr_struct": (S + _ptr_arg("*T", "*S", N_S, "q.b"), 9),
    "ptr_arg_ptr_ptr_u8": (_ptr_arg("*T", "**u8", N_PU8, "**q as i32"), 9),
    "ptr_arg_ptr3_u8": (PTR_ARG_PTR3, 99),
    "ref_ptr_i32": (_ptr_arg("@T", "*i32", N_I32, "*q"), 9),
    "mut_ref_ptr_i32": (_ptr_arg("@&T", "*i32", N_I32, "*q"), 9),
    "ref_ptr_struct": (S + _ptr_arg("@T", "*S", N_S, "q.b"), 9),
    "ptr_store_ptr_i32": (PTR_ARG_STORE, 92),
    "ptr_field_ptr_struct": (PTR_ARG_FIELD, 9),
    # `p + 1` strides one pointer: element 1 is the only one pointing at 9.
    "ptr_second_ptr_i32": (
        SECOND + "fn main() -> i32\n    var a: i32 = 2\n    var n: i32 = 9\n"
        "    var arr: [3]*i32\n    arr[0] = @a\n    arr[1] = @n\n    arr[2] = @a\n"
        "    return *second<*i32>(@arr[0])\n",
        9,
    ),
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
