"""AGAST #1375: a free-fn parameter named `self` keeps its annotated type in ritz1.

THE DEFECT

    fn c_get(self: @C) -> i64
        return self.value

ritz1: `unhandled EXPR_MEMBER`, exit 1. Rename the parameter to `me` and it
builds. `self` is the SELF token, not an IDENT, so a `self: T` param goes through
the grammar's param_self alternatives. Their action threw the parsed type away
and recorded TYPE_STRUCT with no name, because emit_impl_method takes an impl
receiver's type from the impl block. A free fn has no impl block, so its `self`
had no type and every `self.field` failed: read, assignment, and `@self.field`
("cannot take address").

THE FIX (ritz1/src/ast_helpers.ritz, no grammar change)

param_self rebuilds the type it was given from the tokens type_spec consumed and
the parser state type_spec left behind. That produces the same Param the
`IDENT COLON type_spec` alternative builds for any other name. impl_block_new
then resets each method's `self` to the old receiver form, so impl methods are
unchanged.

ORACLE

Every program is compiled three ways and all three exit codes must agree:
ritz0 on the `self` spelling, ritz1 on the `self` spelling, and ritz1 with
`self` renamed to `me`. The `me` twin shows the name is the only difference.
"""

import re

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

# The ticket's repro.
REPRO = """\
struct C
    value: i64

fn c_get(self: @C) -> i64
    return self.value

pub fn main() -> i32
    var c: C = C { value: 7 }
    return c_get(@c) as i32
"""

# The receiver forms the examples use (61_true_async: `*T` and `@self.inner`;
# 72_raii: `@T` and `@&T` with `+=`), plus the `self:& T` mutable-borrow
# spelling and `**T`.
RECEIVERS = """\
struct C
    value: i64

struct W
    inner: C
    n: i64

fn c_get(self: @C) -> i64
    return self.value

fn c_bump(self: @&C)
    self.value += 1

fn c_bump2(self:& C)
    self.value = self.value + 2

fn c_ptr(self: *C) -> i64
    self.value = self.value + 10
    return self.value

fn w_go(self: *W) -> i64
    return c_ptr(@self.inner) + self.n

fn c_pp(self: **C) -> i64
    let q: *C = *self
    return q.value

pub fn main() -> i32
    var c: C = C { value: 7 }
    c_bump(@&c)
    c_bump2(@&c)
    var d: C = C { value: 0 }
    var w: W = W { inner: d, n: 100 }
    w.inner.value = 1
    var pc: *C = @c
    if c_pp(@pc) != 10
        return 1
    return (c_get(@c) + w_go(@w)) as i32
"""

# The other type_spec forms: by-value struct, primitive, primitive pointer,
# type alias, generic struct (by reference and by value), and `**T`, both
# stepped with pointer arithmetic and indexed (`self[i]` on a `**u8` only
# loads a pointer if the param is TYPE_PTR_PTR, not TYPE_PTR).
OTHER_TYPES = """\
struct C
    value: i64

struct D
    a: i64
    b: i64

struct Box<T>
    v: T

type Num = i64

fn by_val(self: C) -> i64
    return self.value * 2

fn prim(self: i64) -> i64
    return self + 1

fn prim_ptr(self: *i64) -> i64
    return *self + 3

fn aliased(self: Num) -> i64
    return self * 5

fn boxed(self: @Box<i64>) -> i64
    return self.v

fn boxv(self: Box<i64>) -> i64
    return self.v + 1

fn d_pp(self: **D) -> i64
    let q: *D = *(self + 1)
    return q.b

fn pick(self: **u8, i: i64) -> i64
    let s: *u8 = self[i]
    return *(s + 1) as i64

pub fn main() -> i32
    let c: C = C { value: 4 }
    var x: i64 = 6
    var b: Box<i64> = Box<i64> { v: 9 }
    var d1: D = D { a: 1, b: 2 }
    var d2: D = D { a: 3, b: 40 }
    var arr: [2]*D
    arr[0] = @d1
    arr[1] = @d2
    var bytes: [4]u8
    bytes[0] = 3
    bytes[1] = 30
    var ps: [2]*u8
    ps[0] = @bytes[0]
    ps[1] = @bytes[0]
    if by_val(c) != 8
        return 1
    if prim(10) != 11
        return 2
    if prim_ptr(@x) != 9
        return 3
    if aliased(2) != 10
        return 4
    if boxed(@b) != 9
        return 5
    if boxv(b) != 10
        return 6
    if d_pp(@arr[0]) != 40
        return 7
    if pick(@ps[0], 1) != 30
        return 8
    return 42
"""

# Control: impl receivers in every spelling. param_self now records the
# annotation, so impl_block_new has to reset these. They must behave as before.
# (Generic impl receivers are left out: ritz1 does not yet emit generic impl
# methods at all, #1520.)
IMPL_CONTROL = """\
struct P
    x: i64
    y: i64

impl P
    fn sum(self) -> i64
        self.x + self.y

    fn get_x(self: @P) -> i64
        return self.x

    fn set_y(self: @&P, v: i64)
        self.y = v

    fn bump_x(self:& P)
        self.x = self.x + 1

    fn twice(self: P) -> i64
        return self.x * 2

pub fn main() -> i32
    var p: P = P { x: 3, y: 4 }
    p.set_y(10)
    p.bump_x()
    if p.get_x() != 4
        return 1
    if p.twice() != 8
        return 2
    return p.sum() as i32
"""

CASES = {
    "repro": REPRO,
    "receivers": RECEIVERS,
    "other_types": OTHER_TYPES,
    "impl_control": IMPL_CONTROL,
}


def _rename_self(program: str) -> str:
    return re.sub(r"\bself\b", "me", program)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_self_param_matches_ritz0_and_renamed_twin(ritz1_bin, tmp_path, name):  # noqa: F811
    program = CASES[name]
    oracle = _run("ritz0", tmp_path, name, program)
    got = _run("ritz1", tmp_path, name, program)
    assert got == oracle, f"ritz1 exit {got} != ritz0 exit {oracle} for {name}"
    if name != "impl_control":  # impl receivers must be spelled `self`
        twin = _run("ritz1", tmp_path, f"{name}_me", _rename_self(program))
        assert twin == got, f"`me` twin exits {twin}, `self` exits {got}"
