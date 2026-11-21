"""AGAST #1733: ritz1 static method calls `T.m(...)` narrow int / bool args.

THE DEFECT

The static-method arm of emit_expr_method (ritz1/src/emitter_expr_call.ritz)
evaluated every argument into an i64 register and passed it under the
declared param type, narrowing only f64 -> f32:

    %.2 = add i64 0, 42
    %.3 = call %P @P_make(i32 %.2)      ; clang: '%.2' defined as i64

The direct-call and instance-method (#1607) paths trunc integer args to the
param width, and bool args to i1 (unless the value is already i1, e.g. a bool
global's load). The static arm now does the same.

The result half (#1739's addendum to this ticket) landed with #1962; the
RESULT cases here keep both halves pinned together.

Oracle: ritz0 compiles every program, and both binaries return the same exit
code. The void case also checks the IR, since clang accepts `call i64` to a
void define.
"""

import re

import pytest

from test_ritz1_builtin_struct_shadow import _run

# The ticket's first repro: an i32 literal into an i32 param, struct result.
REPRO_MAKE = """\
struct P
    x: i64
impl P
    fn make(n: i32) -> P
        return P { x: n as i64 }
pub fn main() -> i32
    var p: P = P.make(42)
    return p.x as i32
"""

# The ticket's second repro: an i32 result compared, then returned from an
# i32 fn; its i32 arg is narrowed too.
REPRO_OF = """\
struct S
    v: i32
impl S
    fn of(n: i32) -> i32
        return n + 1
pub fn main() -> i32
    if S.of(3) != 4
        return 1
    return S.of(3)
"""

# i8 / i16 / i32 / u8 / u16 / u32 params mixed with i64 ones so a narrowed
# arg's position matters; args are literals, negated literals, i64 locals and
# narrow locals. Negative values check that the trunc keeps the low bits.
PARAM_WIDTHS = """\
struct W
    acc: i64

impl W
    fn a8(x: i8, y: i64) -> i64
        x as i64 + y

    fn a16(y: i64, x: i16) -> i64
        x as i64 + y

    fn a32(x: i32, y: i32) -> i64
        x as i64 * 10 + y as i64

    fn au8(x: u8) -> i64
        x as i64

    fn au16(x: u16) -> i64
        x as i64

    fn au32(x: u32) -> i64
        x as i64

pub fn main() -> i32
    var r: i64 = 0
    let big: i64 = 4
    let small: i32 = 2
    r = r + W.a8(0 - 3, 10)
    r = r + W.a16(20, 0 - 5)
    r = r + W.a32(big as i32, small)
    r = r + W.au8(200)
    r = r + W.au16(300)
    r = r + W.au32(70000)
    if r != 7 + 15 + 42 + 200 + 300 + 70000
        return 1
    return 42
"""

# Narrow results of every width, used in a comparison, in arithmetic and
# returned straight from an i32 fn.
RESULT_WIDTHS = """\
struct R
    v: i64

impl R
    fn r8(n: i8) -> i8
        n

    fn r16(n: i16) -> i16
        n

    fn r32(n: i32) -> i32
        n

    fn ru8(n: u8) -> u8
        n

    fn ru16(n: u16) -> u16
        n

    fn ru32(n: u32) -> u32
        n

pub fn main() -> i32
    if R.r8(0 - 7) != 0 - 7
        return 1
    if R.r16(0 - 300) != 0 - 300
        return 2
    if R.r32(0 - 70000) != 0 - 70000
        return 3
    if R.ru8(250) != 250
        return 4
    if R.ru16(60000) != 60000
        return 5
    if R.ru32(4000000000) != 4000000000
        return 6
    let sum: i64 = R.r8(1) as i64 + R.r16(2) as i64 + R.ru32(3) as i64
    if sum != 6
        return 7
    return R.r32(42)
"""

# Bool params take i1: a literal, a comparison, a bool-returning static call
# and a bool local. A bool result is used as a condition and compared.
BOOL_PARAM_RESULT = """\
struct B
    v: i64

impl B
    fn yes() -> bool
        true

    fn flip(c: bool) -> bool
        if c
            return false
        true

    fn pick(c: bool, a: i64, b: i64) -> i64
        if c
            return a
        b

pub fn main() -> i32
    let v: i64 = 3
    var r: i64 = B.pick(true, 10, 1)
    r = r + B.pick(v > 5, 100, 2)
    r = r + B.pick(B.yes(), 30, 3)
    let flag: bool = true
    r = r + B.pick(flag, 1, 50)
    if B.flip(flag)
        return 1
    if B.flip(false) != true
        return 2
    return r as i32
"""

# A void static method, in both spellings: `-> void` and no return type.
VOID_STATIC = """\
var G: i64 = 0

struct V
    v: i64

impl V
    fn nv(c: i32) -> void
        G = G + c as i64

    fn nn(c: i16)
        G = G + c as i64

pub fn main() -> i32
    V.nv(40)
    V.nn(2)
    return G as i32
"""

CASES = [
    ("repro_make", REPRO_MAKE),
    ("repro_of", REPRO_OF),
    ("param_widths", PARAM_WIDTHS),
    ("result_widths", RESULT_WIDTHS),
    ("bool_param_result", BOOL_PARAM_RESULT),
    ("void_static", VOID_STATIC),
]


@pytest.mark.integration
@pytest.mark.parametrize("name,program", CASES, ids=[c[0] for c in CASES])
def test_static_method_args_match_ritz0(ritz1_bin, tmp_path, name, program):
    expected = _run("ritz0", tmp_path, name, program)
    got = _run("ritz1", tmp_path, name, program)
    assert got == expected, f"{name}: ritz1 exit {got}, ritz0 exit {expected}"


@pytest.mark.integration
def test_void_static_method_called_as_void(ritz1_bin, tmp_path):
    """clang accepts `call i64` to a void define, so check the IR itself."""
    _run("ritz1", tmp_path, "void_ir", VOID_STATIC)
    ll = (tmp_path / "void_ir_ritz1.ll").read_text()
    for m in ("V_nv", "V_nn"):
        calls = re.findall(rf"^\s*(.*\bcall\b.*@{m}\()", ll, re.M)
        assert calls, f"no call to @{m} in ritz1 IR"
        for c in calls:
            assert re.match(r"call void @", c), f"@{m} called as non-void: {c}"


# A bool global loads as i1 (bool_reg_is_i1), so it must reach the call
# without a second trunc. ritz0 rejects bool global initializers, so this case
# has no oracle and asserts the exit code directly.
BOOL_GLOBAL = """\
var FLAG: bool = true

struct B
    v: i64

impl B
    fn pick(c: bool, a: i64) -> i64
        if c
            return a
        0

pub fn main() -> i32
    return B.pick(FLAG, 42) as i32
"""


@pytest.mark.integration
def test_bool_global_arg_not_retruncated(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "bool_global", BOOL_GLOBAL) == 42
