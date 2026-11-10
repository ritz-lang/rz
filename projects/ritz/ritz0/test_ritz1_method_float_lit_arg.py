"""Regression tests for AGAST #2561: a literal passed to a method's float
param must be coerced to the param's width.

ritz1 emits a float literal as a `double` and an integer literal as an `i64`.
The free-call cascade (emit_expr_call) fptrunc's / sitofp's an arg into an
`f32` / `f64` param, but the instance-method arm of emit_expr_method had no
float arm at all: `a.lerp(b, 0.25)` emitted `call ... float %<double>` and
clang rejected it ("defined with type 'double' but expected 'float'").  Found
in angelo raster/bezier.ritz:151, `p1.lerp(p2, 0.25)`.

The ticket guessed an off-by-one at arg j > 0; measured, every position was
broken, the first included (`a.sc(0.5)`), for every self form.  The static
arm (`P.st(0.5)`) fptrunc'd a float literal but passed an integer literal
(`P.st(2)`) as an `i64` under `float`.

Covered: a literal at arg positions 1, 2 and 3 (counting self as 0); after an
i32, a by-value struct and another f32; `@P`, `@&P` and by-value `self`, and
a receiver that is itself an `@P` param; static methods; integer literals
into f32 and f64 (sitofp); an f32 local into an f64 param (fpext); and the
angelo shape (`lerp(self: @Pt, other: Pt, t: f32) -> Pt`).  Each program
returns 42 on success and a distinct small code per failed check.  ritz0 is
the oracle.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

PRELUDE = """\
struct P
    x: f32
    y: f32

impl P
    pub fn p1(self: @P, t: f32) -> f32
        self.x * t
    pub fn p2(self: @P, k: i32, t: f32) -> f32
        self.x * t + (k as f32)
    pub fn p3(self: @P, k: i32, o: P, t: f32) -> f32
        o.x * t + (k as f32)
    pub fn sp(self: @P, o: P, t: f32) -> f32
        o.x * t
    pub fn ff(self: @P, a: f32, t: f32) -> f32
        a * t
    pub fn mr(self: @&P, k: i32, t: f32) -> f32
        self.x * t + (k as f32)
    pub fn bv(self: P, k: i32, t: f32) -> f32
        self.x * t + (k as f32)
    pub fn d2(self: @P, k: i32, t: f64) -> f64
        t + (k as f64)
    pub fn st(k: i32, t: f32) -> f32
        t + (k as f32)
    pub fn ss(o: P, t: f32) -> f32
        o.x * t
    pub fn sd(k: i32, t: f64) -> f64
        t + (k as f64)

"""

# A float literal at positions 1, 2 and 3 (self is position 0).
POSITIONS = PRELUDE + """\
pub fn main() -> i32
    let a: P = P { x: 2.0, y: 1.0 }
    let b: P = P { x: 4.0, y: 1.0 }
    if a.p1(0.5) != 1.0
        return 1
    if a.p2(3, 0.5) != 4.0
        return 2
    if a.p3(3, b, 0.25) != 4.0
        return 3
    return 42
"""

# After an i32, a by-value struct and another f32 (both args literals).
AFTER = PRELUDE + """\
pub fn main() -> i32
    let a: P = P { x: 2.0, y: 1.0 }
    let b: P = P { x: 4.0, y: 1.0 }
    if a.p2(1, 0.5) != 2.0
        return 1
    if a.sp(b, 0.5) != 2.0
        return 2
    if a.ff(0.5, 0.25) != 0.125
        return 3
    return 42
"""

# `@P`, `@&P` and by-value `self`, and a receiver that is an `@P` param.
SELF_FORMS = PRELUDE + """\
fn via_ref(r: @P) -> f32
    r.p2(1, 0.5)

pub fn main() -> i32
    var a: P = P { x: 2.0, y: 1.0 }
    if a.p2(2, 0.5) != 3.0
        return 1
    if a.mr(2, 0.5) != 3.0
        return 2
    if a.bv(2, 0.5) != 3.0
        return 3
    if via_ref(@a) != 2.0
        return 4
    return 42
"""

# Static methods: a float literal after an i32 and after a struct, and an
# integer literal into f32 / f64 (sitofp).
STATIC = PRELUDE + """\
pub fn main() -> i32
    let b: P = P { x: 4.0, y: 1.0 }
    if P.st(1, 0.5) != 1.5
        return 1
    if P.ss(b, 0.25) != 1.0
        return 2
    if P.st(1, 2) != 3.0
        return 3
    if P.sd(1, 2) != 3.0
        return 4
    if P.sd(1, 0.5) != 1.5
        return 5
    return 42
"""

# An integer literal into an instance method's f32 / f64 param (sitofp), an
# f64 literal into an f64 param, and an f32 local into an f64 param (fpext).
CONVERSIONS = PRELUDE + """\
pub fn main() -> i32
    let a: P = P { x: 2.0, y: 1.0 }
    let h: f32 = 0.5
    if a.p2(1, 3) != 7.0
        return 1
    if a.p1(2) != 4.0
        return 2
    if a.d2(1, 2) != 3.0
        return 3
    if a.d2(1, 0.5) != 1.5
        return 4
    if a.d2(1, h) != 1.5
        return 5
    if a.p2(1, h) != 2.0
        return 6
    return 42
"""

# angelo raster/bezier.ritz:151 -- `p1.lerp(p2, 0.25)`, struct result.
LERP = """\
struct Pt
    x: f32
    y: f32

impl Pt
    pub fn new(x: f32, y: f32) -> Pt
        Pt { x: x, y: y }
    pub fn lerp(self: @Pt, other: Pt, t: f32) -> Pt
        Pt.new(self.x + (other.x - self.x) * t, self.y + (other.y - self.y) * t)

pub fn main() -> i32
    let p1: Pt = Pt.new(0.0, 0.0)
    let p2: Pt = Pt.new(8.0, 4.0)
    let q: Pt = p1.lerp(p2, 0.25)
    if q.x != 2.0
        return 1
    if q.y != 1.0
        return 2
    return 42
"""

CASES = {
    "positions": POSITIONS,
    "after": AFTER,
    "self_forms": SELF_FORMS,
    "static": STATIC,
    "conversions": CONVERSIONS,
    "lerp": LERP,
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, CASES[name]) == 42


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_method_float_lit_arg(ritz1_bin, tmp_path, name):
    """AGAST #2561. Before the fix: `call ... float %<double>` -> clang error."""
    assert _run("ritz1", tmp_path, name, CASES[name]) == 42
