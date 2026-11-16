"""AGAST #1577: a variant constructor passed as a call argument is built at
the CALLEE's parameter type, not at the enum an enclosing typed `let` or
`return` expects.

THE DEFECT

`let v: Option<i64> = Some(g(Some(20 as i32)) + g(None))` with
`g(o: Option<i32>)`: the let sets `_expected_enum_name = Option$i64` for its
initialiser, and every call-argument path except a plain call's *bare* ctor
argument emitted the argument under it. The inner `Some`/`None` came out as
`%Option$i64` and ritz0 refused the call ("argument 1 of `g` has the wrong
type"). Leaking paths: impl-method arguments, static `Type.method`
arguments, and a ctor in an `if` tail of a plain call's argument.

THE FIX

`_emit_value_arg` emits each by-value argument with the expected enum set
from its parameter: the parameter's enum when it is one, else none at all,
and restores the outer expectation afterwards. All three call paths use it.

Each case is its own program so a broken path names itself; the same cases
run on ritz0, ritz1 and ritz1_selfhosted as [[test]] fns in
ritz0/test/test_variant_arg_param_hint.ritz.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

G = """\
fn g(o: Option<i32>) -> i64
    let r: i64 = match o
        Some(v) => v as i64 * 2
        None => 1
    return r

fn opt(v: Option<i64>) -> i32
    let r: i32 = match v
        Some(x) => x as i32
        None => 99
    return r
"""

ACC = """\
struct Acc
    base: i64

impl Acc
    fn m(self: @Acc, o: Option<i32>) -> i64
        let r: i64 = match o
            Some(v) => self.base + v as i64
            None => 1
        return r

    fn mk(o: Option<i32>) -> i64
        let b: i64 = match o
            Some(v) => v as i64 * 2
            None => 1
        return b
"""

CASES = {
    # The ticket repro.
    "let_plain": G + """
pub fn main() -> i32
    let v: Option<i64> = Some(g(Some(20 as i32)) + g(None))
    return opt(v)
""",
    "return_plain": G + """
fn h() -> Option<i64>
    return Some(g(Some(20 as i32)) + g(None))

pub fn main() -> i32
    return opt(h())
""",
    "let_plain_if_tail": G + """
pub fn main() -> i32
    let c: i32 = 1
    let v: Option<i64> = Some(g(if c == 1 then Some(20 as i32) else None) + g(None))
    return opt(v)
""",
    "let_method": G + ACC + """
pub fn main() -> i32
    let a: Acc = Acc { base: 0 }
    let v: Option<i64> = Some(a.m(Some(40 as i32)) + a.m(None))
    return opt(v)
""",
    "return_method": G + ACC + """
fn h(a: @Acc) -> Option<i64>
    return Some(a.m(Some(40 as i32)) + a.m(None))

pub fn main() -> i32
    let a: Acc = Acc { base: 0 }
    return opt(h(@a))
""",
    "let_static_method": G + ACC + """
pub fn main() -> i32
    let v: Option<i64> = Some(Acc.mk(Some(20 as i32)) + Acc.mk(None))
    return opt(v)
""",
    # The let's expectation is back for the tails after the condition's
    # call argument.
    "let_restored_after_arg": G + """
pub fn main() -> i32
    let c: i32 = 1
    let v: Option<i64> = if g(if c == 1 then Some(20 as i32) else None) == 40 then Some(41) else None
    return opt(v)
""",
    "let_user_enum": """\
enum Crate<T>
    Packed(T)
    Bare

fn cg(b: Crate<i32>) -> i64
    let r: i64 = match b
        Packed(v) => v as i64 * 2
        Bare => 1
    return r

pub fn main() -> i32
    let v: Crate<i64> = Packed(cg(Packed(20 as i32)) + cg(Bare))
    let r: i32 = match v
        Packed(x) => x as i32
        Bare => 99
    return r
""",
    "let_nested_two_deep": G + """
fn k(o: Option<i64>) -> i32
    let r: i32 = match o
        Some(v) => v as i32
        None => 0
    return r

pub fn main() -> i32
    let v: Option<i64> = Some(g(Some(k(Some(20 as i64)))) + g(None))
    return opt(v)
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_variant_arg_takes_param_type(tmp_path, name):
    assert _run("ritz0", tmp_path, name, CASES[name]) == 41


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_variant_arg_takes_param_type(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, CASES[name]) == 41
