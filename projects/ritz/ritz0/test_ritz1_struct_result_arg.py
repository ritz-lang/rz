"""AGAST #2413: ritz1 passes a struct-returning method call straight into a
by-value struct param of a method.

THE DEFECT

    r.add(S.mk(5))      # add(self:&, s: S), mk(a: i32) -> S

The method-call argument cascade (emit_expr_method, emitter_expr_call.ritz)
boxes a scalar into a single-field "newtype" struct param when
get_expr_type calls the argument an integer. get_expr_type has no struct arm
for EXPR_METHOD, so it reported `S.mk(5)` (a `%S` register) as i64 and the
box wrote `store i64 %.7, ptr %.8`, which clang rejects. ritz1 exited 0.

WHICH FORMS WERE BROKEN (measured on 46d1f96e)

Producer x consumer x size, 27 programs, all run by ritz0 with exit 6:

  * broken: an instance-method consumer (`r.add(...)`) fed by a static
    method (`S.mk(5)`) or an instance method (`q.me()`), for an 8-byte
    struct (fits i64) and a 32-byte one (doesn't).
  * already fine: a free-fn producer (`mk(5)`): get_expr_type's EXPR_CALL
    arm reports TYPE_STRUCT, so it was never boxed.
  * already fine: a free-fn consumer (`f(...)`) and a static-method
    consumer (`R.take(...)`). Neither path has the generic newtype box.
  * already fine: a struct of SRET_MIN_BYTES or more. Its param is byval,
    and the box branch skips byval params.

THE FIX

The box guard treats a call or method call whose callee returns a struct
(call_result_struct_name) as already being the aggregate, as it already does
for a struct literal and for `*r`. get_expr_type is left alone.

The NEWTYPE row is a control: a method returning i64 into a single-field
struct param must still be boxed. A guard that skipped every method call
would break it.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import itertools

import pytest

from test_ritz1_builtin_struct_shadow import _run

# 8 bytes: classified as an integer-sized aggregate.
SMALL = """\
struct S
    a: i32
    b: f32
"""
SMALL_INIT = "S { a: a, b: 1.0 }"

# 32 bytes: too big for an i64, below the byval threshold.
BIG = """\
struct S
    a: i32
    b: i64
    c: i64
    d: i64
"""
BIG_INIT = "S { a: a, b: 2, c: 3, d: 4 }"

# 280 bytes: at least SRET_MIN_BYTES, so returned via sret and passed byval.
HUGE = "struct S\n    a: i32\n" + "".join(f"    p{i}: i64\n" for i in range(34))
HUGE_INIT = "S { a: a, " + ", ".join(f"p{i}: {i}" for i in range(34)) + " }"

SIZES = {
    "small": (SMALL, SMALL_INIT),
    "big": (BIG, BIG_INIT),
    "huge": (HUGE, HUGE_INIT),
}

PRODUCERS = {
    "static_method": "S.mk(5)",
    "free_fn": "mk(5)",
    "instance_method": "q.me()",
}

# Each consumer adds s.a (5) to 1, so every program exits 6.
CONSUMERS = {
    "method": "    r.add({arg})\n    return r.n\n",
    "free_fn": "    return f({arg}) + 1\n",
    "static_method": "    return R.take({arg}) + 1\n",
}

# The four rows that produced invalid IR before the fix.
WAS_BROKEN = {
    (size, prod, "method")
    for size in ("small", "big")
    for prod in ("static_method", "instance_method")
}


def _program(size: str, producer: str, consumer: str) -> str:
    struct, init = SIZES[size]
    me_init = init.replace("a: a", "a: self.a + 1", 1)
    return (
        struct
        + f"""
impl S
    pub fn mk(a: i32) -> S
        {init}
    pub fn me(self:&) -> S
        {me_init}

fn mk(a: i32) -> S
    {init}

struct R
    n: i32

impl R
    pub fn add(self:&, s: S)
        self.n = self.n + s.a
    pub fn take(s: S) -> i32
        s.a

fn f(s: S) -> i32
    s.a

pub fn main() -> i32
    var r = R {{ n: 1 }}
    var q = S.mk(4)
"""
        + CONSUMERS[consumer].format(arg=PRODUCERS[producer])
    )


MATRIX = [
    pytest.param(
        size,
        prod,
        cons,
        id=f"{size}-{prod}-into-{cons}"
        + ("-was_broken" if (size, prod, cons) in WAS_BROKEN else ""),
    )
    for size, prod, cons in itertools.product(SIZES, PRODUCERS, CONSUMERS)
]


@pytest.mark.integration
@pytest.mark.parametrize("size,producer,consumer", MATRIX)
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_struct_result_as_by_value_arg(tmp_path, compiler, size, producer, consumer):
    name = f"sra_{size}_{producer}_{consumer}"
    assert _run(compiler, tmp_path, name, _program(size, producer, consumer)) == 6


# Control: a scalar-returning method (`q.get()`, i64) into a single-field
# struct param is still boxed. Scalar only, so a guard that is off fails the
# matrix rows and not this one.
NEWTYPE = """\
struct M
    v: i64

struct Q
    k: i64

impl Q
    pub fn get(self) -> i64
        self.k

struct R
    n: i64

impl R
    pub fn add(self:&, m: M)
        self.n = self.n + m.v

pub fn main() -> i32
    var r = R { n: 1 }
    let q = Q { k: 4 }
    r.add(q.get())
    return r.n as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_scalar_method_result_still_boxed_into_newtype(tmp_path, compiler):
    assert _run(compiler, tmp_path, "sra_newtype", NEWTYPE) == 5
