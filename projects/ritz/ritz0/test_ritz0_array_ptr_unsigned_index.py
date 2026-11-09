"""AGAST #2541: `q[i]` on a `q: *[N]u8` widened the element with sext in ritz0.

    var x: [3]u8
    x[1] = 201
    var q: *[3]u8 = @x
    if q[1] != 201      # ritz0: sext i8 -> -55, so this was true
        return 1

_infer_unsigned_expr's Index arm asked whether `*[3]u8`'s pointee was unsigned,
and an array isn't, so every read through a pointer to an unsigned array was
signed: compares, casts, `/` and `>>`.  ritz1 was already right; the matrix runs
all three compilers so they stay in agreement.

Each element has its top bit set, so a sext changes the value.  Every check has
its own exit code.
"""

import pytest

from test_ritz1_array_ptr_element import COMPILERS, run_with  # noqa: F401  (fixture)

# element type -> (a value with its top bit set, that value // 2 == value >> 1)
TYPES = {
    "u8": ("201", "100"),
    "u16": ("40001", "20000"),
    "u32": ("3000000001", "1500000000"),
}

# Every way to get a name for the element read `{e}`, in main.
_FILL = "    var x: [3]{t}\n    x[0] = 1\n    x[1] = {v}\n    x[2] = 2\n"

# source -> (the name `{e}` that's indexed, declarations before main, setup in main)
SOURCES = {
    # The ticket's program.
    "local": ("q", "", "    var q: *[3]{t} = @x\n"),
    # A copy of the pointer: `let p = q`.
    "let_copy": ("p", "", "    var q: *[3]{t} = @x\n    let p = q\n"),
    # Out through a `**[3]T`: `let p = *r`.
    "let_deref": (
        "p",
        "",
        "    var q: *[3]{t} = @x\n    let r: **[3]{t} = @q\n    let p = *r\n",
    ),
    "global": ("g", "var g: *[3]{t}\n\n", "    g = @x\n"),
    # A struct field: `h.p[1]`.
    "field": (
        "h.p",
        "struct H\n    n: i64\n    p: *[3]{t}\n\n",
        "    var h: H\n    h.p = @x\n",
    ),
    # A parameter: `fn f(q: *[3]T)`, called as `f(@x)`.
    "param": ("q", None, None),
}

_CHECKS = """\
    if {e}[1] != {v}
        return 1
    if {e}[1] < {e}[0]
        return 2
    if ({e}[1] as i64) != {v}
        return 3
    if {e}[1] / 2 != {h}
        return 4
    if {e}[1] >> 1 != {h}
        return 5
    let n: i64 = {e}[1] as i64
    if n <= 0
        return 6
    return 0
"""


def _program(source: str, ty: str) -> str:
    v, h = TYPES[ty]
    name, pre, setup = SOURCES[source]
    checks = _CHECKS.format(e=name, v=v, h=h)
    if source == "param":
        return (
            f"fn f(q: *[3]{ty}) -> i32\n" + checks + "\n"
            "pub fn main() -> i32\n" + _FILL.format(t=ty, v=v) + "    return f(@x)\n"
        )
    return (
        pre.format(t=ty)
        + "pub fn main() -> i32\n"
        + _FILL.format(t=ty, v=v)
        + setup.format(t=ty)
        + checks
    )


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("ty", sorted(TYPES))
@pytest.mark.parametrize("source", sorted(SOURCES))
def test_unsigned_element_through_array_pointer(run_with, source, ty, compiler):
    assert run_with(compiler, f"{source}_{ty}", _program(source, ty)) == 0


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_signed_control(run_with, compiler):
    """i8 through the same pointer still sign-extends: -55 stays -55."""
    program = (
        "pub fn main() -> i32\n    var x: [3]i8\n    x[1] = -55\n"
        "    var q: *[3]i8 = @x\n    let p = q\n"
        "    if q[1] != -55\n        return 1\n"
        "    if p[1] >= 0\n        return 2\n"
        "    if (q[1] as i64) != -55\n        return 3\n"
        "    return 0\n"
    )
    assert run_with(compiler, "signed_control", program) == 0
