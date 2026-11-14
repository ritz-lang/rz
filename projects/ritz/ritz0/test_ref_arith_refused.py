"""AGAST #3037, LARB R16: `+`/`-` on a reference to a non-array is refused.

    fn f(p: @&i32) -> i32
        let q: *i32 = p + 1
        return *q          # 9 on ritz0, ritz1 and ritz1_selfhosted, silently

R9 rule 4 says a reference names one value.  `p + 1` names the next one, which
was never lent, and it escapes the loan check of §13.5 (R11a): a loan of `a[0]`
covers `a[0]`, and `p + 1` reaches `a[1]` without the checker seeing it.  So
`p + i`, `i + p`, `p - i`, `p += i`, `p -= i` and `p - q` are errors when `p`
(or either operand of `p - q`) is an `@T` / `@&T` and T is not an array.  The
cast keeps the step available and visible: `(p as *T) + 1`.  The row walk on
`@[N]T` / `@&[N]T` stays legal (§7.8, #2554, R18; test_ritz1_ref_array_arith).

The error sits where the compilers locate a binary operator: its expression's
start, as #2957's refusal in test_pointer_difference.py.
"""

import pytest
from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]


def _msg(op, ty):
    return (f"a reference is one value, not a buffer: `{op}` needs a `*T`; "
            f"write `(p as *{ty}) {op} 1`")


_S = "struct S\n    x: i32\n\n"
_MAIN = "pub fn main() -> i32\n    0\n"

# Each row separates a path: the operator (`+`, `-`, `-` of two pointers,
# compound), which operand is the reference, `@` vs `@&`, a scalar vs a struct
# T, and an untyped `let` (no slot type to steer the lowering).
REFUSED = {
    "add_mut_ref": ("fn f(p: @&i32) -> i32\n    let q: *i32 = ^p + 1\n    *q\n\n" + _MAIN, "+", "i32"),
    "add_ref": ("fn f(p: @i32) -> i32\n    let q: *i32 = ^p + 1\n    *q\n\n" + _MAIN, "+", "i32"),
    "int_plus_ref": ("fn f(p: @&i32) -> i32\n    let q: *i32 = ^1 + p\n    *q\n\n" + _MAIN, "+", "i32"),
    "sub_mut_ref": ("fn f(p: @&i32) -> i32\n    let q: *i32 = ^p - 1\n    *q\n\n" + _MAIN, "-", "i32"),
    "struct": (_S + "fn f(p: @&S) -> i32\n    let q: *S = ^p + 1\n    q.x\n\n" + _MAIN, "+", "S"),
    "untyped_let": ("fn f(p: @&i32) -> i32\n    let q = ^p + 1\n    *q\n\n" + _MAIN, "+", "i32"),
    "compound": ("fn f(r: @&i32) -> i32\n    var p: @&i32 = r\n    ^p += 1\n    *p\n\n" + _MAIN, "+", "i32"),
    "difference": ("fn d(q: @i32, p: @i32) -> i64\n    ^q - p\n\n" + _MAIN, "-", "i32"),
    # two pointee types, too: the reference is refused before the types are compared
    "difference_two_types": ("fn d(q: @i32, p: @u8) -> i64\n    ^q - p\n\n" + _MAIN, "-", "i32"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_reference_arithmetic_is_refused(tmp_path, compiler, name):
    src, op, ty = REFUSED[name]
    _assert_refused(compiler, tmp_path, f"refarith_{name}", src, _msg(op, ty))


# What stays legal: the cast, `*T` arithmetic, and the row walk.
ALLOWED = {
    "cast": """\
fn f(p: @&i32) -> i32
    let q: *i32 = (p as *i32) + 1
    *q

pub fn main() -> i32
    var a: [2]i32
    a[1] = 9
    if f(@&a[0]) != 9
        return 1
    0
""",
    "pointer": """\
fn f(p: *i32) -> i32
    let q: *i32 = p + 1
    *q

pub fn main() -> i32
    var a: [2]i32
    a[1] = 9
    if f(@a[0]) != 9
        return 1
    0
""",
    # the array T named by an alias is still an array
    "row_walk_alias": """\
type Row = [3]i32

fn f(q: @&Row) -> i32
    let r = q + 1
    r[1]

pub fn main() -> i32
    var x: [2][3]i32
    x[1][1] = 9
    if f(@&x[0]) != 9
        return 1
    0
""",
    "row_walk": """\
fn f(q: @&[3]i32) -> i32
    let r = q + 1
    r[1]

pub fn main() -> i32
    var x: [2][3]i32
    x[1][1] = 9
    if f(@&x[0]) != 9
        return 1
    0
""",
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ALLOWED))
def test_pointer_arithmetic_stays_legal(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, f"refarith_ok_{name}", ALLOWED[name]) == 0
