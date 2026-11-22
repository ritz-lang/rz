"""Arithmetic in a wider integer slot is computed in the slot's type (AGAST #3225).

    fn f(x: u32) -> i64
        let big: i64 = x * 1000     # an i64 multiply: 5_000_000 gives 5_000_000_000

Aaron's ruling, on R21's consequence (#3112): "silent widening is ok, just not
silent wrapping." When an integer arithmetic expression (`+ - * / % <<`, unary
`-`) is used directly in a slot of a WIDER integer type (a typed let/var, `=`,
`+=`, return, argument, field, element), each operand is widened to the slot's
type first, by its own signedness, and the operation runs there. Recursively:
`x * y + 1` widens x and y. `& | ^` are followed too: they can't wrap, so all
they change is that a wrapping operand below them no longer wraps.

Where there's no wider slot R21 stands: `var n = m + 1` is a u32 and wraps (the
control rows), as does an operand under `>>`, `~`, a call or an `as`, which
consume their operand at its own type. Overflow there is #3197's question.

Each `main` returns 3 when the row holds. On all three compilers.
"""

import pytest

from test_ref_into_value import COMPILERS, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

MAX = "4294967295"


def _f(sig, body, call):
    """`fn f<sig>` with `body`, and a `main` returning 3 when `f(<call>)` does."""
    return f"fn f{sig}\n{body}\npub fn main() -> i32\n    f({call})\n"


def _is(var, want):
    """Return 3 when `var == want`, else 4."""
    return f"    if {var} == {want}\n        return 3\n    return 4\n"


RUNS = {
    # The ruling's example: an i64 multiply, not a u32 one widened.
    "let_mul": _f("(x: u32) -> i32", "    let big: i64 = x * 1000\n" + _is("big", 5000000000), 5000000),
    "var_mul": _f("(x: u32) -> i32", "    var big: i64 = x * 1000\n" + _is("big", 5000000000), 5000000),
    # Signed operands sign-extend: -2147483648 - 1 is -2147483649.
    "signed": _f("(k: i32) -> i32", "    let w: i64 = k - 1\n" + _is("w", -2147483649), -2147483648),
    # Unsigned operands zero-extend, and the subtraction runs in the slot: 1 - 2 is -1.
    "unsigned_minus": _f("(m: u32) -> i32", "    let w: i64 = m - 2\n" + _is("w", -1), 1),
    # Recursively: both x and y are widened before `x * y`.
    "nested": _f("(x: u32, y: u32) -> i32", "    let w: i64 = x * y + 1\n" + _is("w", 4294967297), "65536, 65536"),
    # `/` runs in the slot too, on the un-wrapped sum.
    "divide": _f("(m: u32, o: u32) -> i32", "    let w: i64 = (m + o) / 2\n" + _is("w", 2147483648), f"{MAX}, 1"),
    # ... at the slot's signedness: (1 - 5) / 2 is -2 in an i64.
    "divide_signed": _f("(m: u32, o: u32) -> i32", "    let w: i64 = (m - o) / 2\n" + _is("w", -2), "1, 5"),
    # ... and in a narrower slot, 200 * 200 / 3 in a u16.
    "divide_u16": _f("(a: u8, b: u8) -> i32", "    let w: u16 = (a * b) / 3\n" + _is("w", 13333), "200, 200"),
    "divide_argument": ("fn g(v: i64) -> i32\n" + _is("v", 2147483648)
                        + f"\nfn f(m: u32, o: u32) -> i32\n    g((m + o) / 2)\n\npub fn main() -> i32\n    f({MAX}, 1)\n"),
    # `<<` widens its left operand; the count has no say.
    "shift": _f("(x: u32) -> i32", "    let w: i64 = x << 20\n" + _is("w", 5242880000), 5000),
    # Unary `-`: -(-2147483648) is 2147483648 in an i64.
    "negate": _f("(k: i32) -> i32", "    let w: i64 = -k\n" + _is("w", 2147483648), -2147483648),
    # A wider slot that isn't 64 bits: 200 * 200 in a u16.
    "u16_slot": _f("(a: u8, b: u8) -> i32", "    let w: u16 = a * b\n" + _is("w", 40000), "200, 200"),
    # Bitwise ops are followed: the sum below `|` doesn't wrap. (The literal is
    # still R21's: it takes m's type and must fit a u32.)
    "through_or": _f("(m: u32) -> i32", "    let w: i64 = (m + 1) | 1\n" + _is("w", 4294967297), MAX),
    # Each slot kind.
    "return": ("fn g(x: u32) -> i64\n    return x * 1000\n\nfn f(x: u32) -> i32\n    let w = g(x)\n"
               + _is("w", 5000000000) + "\npub fn main() -> i32\n    f(5000000)\n"),
    "tail": ("fn g(x: u32) -> i64\n    x * 1000\n\nfn f(x: u32) -> i32\n    let w = g(x)\n"
             + _is("w", 5000000000) + "\npub fn main() -> i32\n    f(5000000)\n"),
    "argument": ("fn g(v: i64) -> i32\n" + _is("v", 5000000000)
                 + "\nfn f(x: u32) -> i32\n    g(x * 1000)\n\npub fn main() -> i32\n    f(5000000)\n"),
    "assign": _f("(x: u32) -> i32", "    var w: i64 = 0\n    w = x * 1000\n" + _is("w", 5000000000), 5000000),
    "compound": _f("(x: u32) -> i32", "    var w: i64 = 1\n    w += x * 1000\n" + _is("w", 5000000001), 5000000),
    "field": ("struct S\n    v: i64\n\nfn f(x: u32) -> i32\n    let s = S { v: x * 1000 }\n"
              + _is("s.v", 5000000000) + "\npub fn main() -> i32\n    f(5000000)\n"),
    "field_assign": ("struct S\n    v: i64\n\nfn f(x: u32) -> i32\n    var s = S { v: 0 }\n    s.v = x * 1000\n"
                     + _is("s.v", 5000000000) + "\npub fn main() -> i32\n    f(5000000)\n"),
    "element": _f("(x: u32) -> i32", "    let a: [2]i64 = [x * 1000, 0]\n" + _is("a[0]", 5000000000), 5000000),
    "element_assign": _f("(x: u32) -> i32", "    var a: [2]i64 = [0, 0]\n    a[1] = x * 1000\n"
                         + _is("a[1]", 5000000000), 5000000),
    # An arm's tail lands in the slot too.
    "arm": _f("(x: u32, c: bool) -> i32", "    let w: i64 = if c\n        x * 1000\n    else\n        0\n"
              + _is("w", 5000000000), "5000000, true"),
    # Controls: no wider slot, so R21 stands and the u32 wraps.  `+%` because
    # R63 stops a plain `+` that does; the typing under test is unchanged.
    "control_untyped": _f("(m: u32) -> i32", "    var n = m +% 1\n" + _is("n", 0), MAX),
    "control_same_width": _f("(m: u32) -> i32", "    let n: u32 = m +% 1\n" + _is("n", 0), MAX),
    "control_cast": _f("(m: u32) -> i32", "    let w: i64 = (m +% 1) as i64\n" + _is("w", 0), MAX),
    "control_tilde": _f("(m: u32) -> i32", "    let w: i64 = ~m\n" + _is("w", MAX), 0),
    # `~m` is a leaf of the sum that runs in the slot: 4294967295 + 1.
    "control_tilde_sum": _f("(m: u32) -> i32", "    let w: i64 = ~m + 1\n" + _is("w", 4294967296), 0),
    "control_shr": _f("(a: u8) -> i32", "    let w: i64 = (a << 4) >> 4\n" + _is("w", 8), 248),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_arithmetic_in_a_wider_slot_is_computed_in_the_slots_type(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, RUNS[name]) == 3
