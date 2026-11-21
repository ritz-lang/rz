"""Regression tests for AGAST #2074: a float-literal return value in an f32 fn
must be fptrunc'd to `float`.

`fn one() -> f32` with a bare `1.0` tail made ritz1 emit
`%.1 = fadd double 0.0, 1.0` then `ret float %.1` -- clang rejects it.  A
float literal is always a `double` in ritz1's IR; the implicit tail return
(emit_fn / emit_impl_method) and the explicit `return` (emit_return) emitted
the value at the fn's return width without converting it.

Return sites covered: free fn, static method and instance method, each as an
implicit tail and as `return`; plus a literal-only expression tail
(`0.5 + 2.5`), a negated literal, and integer literals (sitofp'd).  Each program is instantiated for f64
(the control) and f32 and returns 3 on success.  ritz0 is the oracle.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# `T` is the float type.
FREE_TAIL = """\
fn three() -> T
    3.0

pub fn main() -> i32
    return three() as i32
"""

FREE_RETURN = """\
fn three(x: i32) -> T
    if x > 0
        return 3.0
    return 1.0

pub fn main() -> i32
    return three(1) as i32
"""

STATIC_TAIL = """\
struct Pt
    x: T

impl Pt
    fn three() -> T
        3.0

pub fn main() -> i32
    return Pt.three() as i32
"""

STATIC_RETURN = """\
struct Pt
    x: T

impl Pt
    fn three() -> T
        return 3.0

pub fn main() -> i32
    return Pt.three() as i32
"""

INSTANCE_TAIL = """\
struct Pt
    x: T

impl Pt
    fn three(self: @Pt) -> T
        3.0

pub fn main() -> i32
    let p: Pt = Pt { x: 0.5 as T }
    return p.three() as i32
"""

INSTANCE_RETURN = """\
struct Pt
    x: T

impl Pt
    fn three(self: @Pt) -> T
        return 3.0

pub fn main() -> i32
    let p: Pt = Pt { x: 0.5 as T }
    return p.three() as i32
"""

# A tail that is arithmetic on literals only: still a `double` value.
LIT_ARITH_TAIL = """\
fn three() -> T
    0.5 + 2.5

pub fn main() -> i32
    return three() as i32
"""

# A negated literal, returned and added: -1.0 + 4 = 3.
NEG_RETURN = """\
fn neg() -> T
    return -1.0

pub fn main() -> i32
    let b: T = neg() + 4.0
    return b as i32
"""

# Integer literals, tail and `return`: sitofp'd to the float return type.
# 3 + 4 - 4 = 3.
INT_LIT = """\
fn three() -> T
    3

fn four() -> T
    return 4

pub fn main() -> i32
    return (three() + four()) as i32 - 4
"""

PROGRAMS = {
    "free_tail": FREE_TAIL,
    "free_return": FREE_RETURN,
    "static_tail": STATIC_TAIL,
    "static_return": STATIC_RETURN,
    "instance_tail": INSTANCE_TAIL,
    "instance_return": INSTANCE_RETURN,
    "lit_arith_tail": LIT_ARITH_TAIL,
    "neg_return": NEG_RETURN,
    "int_lit": INT_LIT,
}

CASES = {
    f"{name}_{ty}": prog.replace("T", ty)
    for name, prog in PROGRAMS.items()
    for ty in ("f64", "f32")
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, CASES[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_float_lit_return(ritz1_bin, tmp_path, name):
    """AGAST #2074. Before the fix: `ret float %<double>` -> clang error."""
    assert _run("ritz1", tmp_path, name, CASES[name]) == 3
