"""Regression tests for AGAST #2068: a user impl method returning f32 / f64,
used as an arithmetic operand, must be typed at its return width.

`Pt { x: 0.5 as f32 }.scale(2.0 as f32) + 0.5` made ritz1 emit
`fadd double %<float>, ...` -- clang rejects it.  get_expr_type's EXPR_METHOD
arm only knew float intrinsics (`x.ceil()`) and fell back to TYPE_I64 for a
user method, so binop_float_width computed the add at the literal's `double`.

Receivers covered: struct literal (the ticket), local, pointer local,
global, field, call result (`mk(v).scale(f)`, which also needed AGAST
#2073's struct-typed spill), `self`, and a static method.  Each program is
instantiated for f64 and f32 and returns 3 on success.  ritz0 is the oracle.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# `T` is the float type.  `Pt.scale` is shared by every program.
PRELUDE = """\
struct Pt
    x: T

impl Pt
    fn scale(self: @Pt, f: T) -> T
        self.x * f

    # A bare `1.0` tail in an f32 fn: fptrunc'd since AGAST #2074.
    fn unit() -> T
        1.0

"""

# The ticket's repro: an rvalue struct-literal receiver.  0.5 * 2 + 0.5 +
# 1.5 = 3.
STRUCT_LIT = """\
pub fn main() -> i32
    var b: T = Pt { x: 0.5 as T }.scale(2.0 as T) + 0.5
    b = b + 1.5
    return b as i32
"""

# The method call on the right of the literal, and in a product.
LIT_LEFT = """\
pub fn main() -> i32
    let b: T = 0.5 + 1.0 * Pt { x: 1.25 as T }.scale(2.0 as T)
    return b as i32
"""

# A local and a pointer-local receiver, both operands of one add.
LOCAL_RECV = """\
pub fn main() -> i32
    let p: Pt = Pt { x: 0.5 as T }
    let q: *Pt = @p
    let b: T = p.scale(2.0 as T) + q.scale(3.0 as T) + 0.5
    return b as i32
"""

# A global receiver.
GLOBAL_RECV = """\
var g: Pt

pub fn main() -> i32
    g.x = 0.75 as T
    let b: T = g.scale(2.0 as T) + 1.5
    return b as i32
"""

# A field receiver.
FIELD_RECV = """\
struct Box
    p: Pt

pub fn main() -> i32
    let bx: Box = Box { p: Pt { x: 1.25 as T } }
    let b: T = bx.p.scale(2.0 as T) + 0.5
    return b as i32
"""

# A call-result receiver (AGAST #2073): 0.75 * 2 + 1.5 = 3.
CALL_RECV = """\
fn mk(v: T) -> Pt
    Pt { x: v }

pub fn main() -> i32
    let b: T = mk(0.75 as T).scale(2.0 as T) + 1.5
    return b as i32
"""

# `self.scale(...) + 0.5` inside a method: 1.25 * 2 + 0.5 = 3.
SELF_RECV = """\
struct Q
    x: T

impl Q
    fn scale(self: @Q, f: T) -> T
        self.x * f

    fn twice_plus(self: @Q) -> T
        self.scale(2.0 as T) + 0.5

pub fn main() -> i32
    let q: Q = Q { x: 1.25 as T }
    return q.twice_plus() as i32
"""

# A static method: 1 + 1 + 0.5 + 0.5 = 3.
STATIC = """\
pub fn main() -> i32
    let b: T = Pt.unit() + Pt.unit() + 0.5
    return (b + 0.5) as i32
"""

PROGRAMS = {
    "struct_lit": STRUCT_LIT,
    "lit_left": LIT_LEFT,
    "local_recv": LOCAL_RECV,
    "global_recv": GLOBAL_RECV,
    "field_recv": FIELD_RECV,
    "call_recv": CALL_RECV,
    "self_recv": SELF_RECV,
    "static": STATIC,
}

CASES = {
    f"{name}_{ty}": (PRELUDE + prog).replace("T", ty)
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
def test_ritz1_method_float_arith(ritz1_bin, tmp_path, name):
    """AGAST #2068. Before the fix: `fadd double %<float>` -> clang error."""
    assert _run("ritz1", tmp_path, name, CASES[name]) == 3
