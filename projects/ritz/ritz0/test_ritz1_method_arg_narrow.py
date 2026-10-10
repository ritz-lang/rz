"""AGAST #1607 (+ duplicates #1580, #1581): ritz1 instance-method calls.

THE DEFECT

emit_expr_method's fallback `Type_method` path (ritz1/src/emitter_expr_call.ritz)
evaluated every argument into an i64 register and passed it straight through
under the declared param type:

    %.8 = add i64 0, 5
    call void @P_set(ptr %.1, i32 %.8)      ; clang: '%.8' defined as i64

The free-fn and UFCS paths trunc integer args to the param width; this one did
not, for every receiver form (local, pointer local, field). #1580 is the same
bug through a by-value `self`.

The void half (#1581): the call's return type came from a table with no
TYPE_VOID arm, so a void method was called as `%.5 = call i64 @Box_nv(...)`
against `define ... void @Box_nv`. clang accepts that with opaque pointers,
but the call type doesn't match the callee: UB, and a register is bound to a
value that doesn't exist. The fix emits `call void` and binds no register.

Oracle: ritz0 compiles every program, and both binaries return the same exit
code. The void cases also check the IR directly, since clang accepts the bug.
"""

import re

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

# The #1607 ticket repro: an i32 param through a `self:& P` receiver.
MUT_REF_I32 = """\
struct P
    v: i32

impl P
    fn set(self:& P, x: i32)
        self.v = x

pub fn main() -> i32
    var p: P = P { v: 0 }
    p.set(5)
    if p.v != 5
        return 1
    return 42
"""

# The #1580 repro: by-value self, i32 param, i32 result.
BY_VALUE_I32 = """\
struct Box
    v: i64

impl Box
    fn wi(self, n: i32) -> i32
        n

pub fn main() -> i32
    let b: Box = Box { v: 7 }
    return b.wi(5)
"""

# i8 / i16 / i32 / u8 / u16 / u32 params, mixed with i64 ones so a narrowed
# arg's position matters. Negative values check that the trunc keeps the
# low bits (ritz0 compares the final result).
WIDTHS = """\
struct W
    acc: i64

impl W
    fn a8(self, x: i8, y: i64) -> i64
        x as i64 + y

    fn a16(self, y: i64, x: i16) -> i64
        x as i64 + y

    fn a32(self, x: i32, y: i32) -> i64
        x as i64 * 10 + y as i64

    fn au8(self, x: u8) -> i64
        x as i64

    fn au16(self, x: u16) -> i64
        x as i64

    fn au32(self, x: u32) -> i64
        x as i64

pub fn main() -> i32
    let w: W = W { acc: 0 }
    var r: i64 = 0
    r = r + w.a8(0 - 3, 10)
    r = r + w.a16(20, 0 - 5)
    r = r + w.a32(4, 2)
    r = r + w.au8(200)
    r = r + w.au16(300)
    r = r + w.au32(70000)
    if r != 7 + 15 + 42 + 200 + 300 + 70000
        return 1
    return 42
"""

# Receiver forms that reach the Type_method fallback: a local, a field and a
# nested field. Pointer-typed receivers (`pp: *P`, `q: *P`) are left out:
# the fallback passes the pointer's slot, not the pointer (AGAST #1692).
RECEIVER_FORMS = """\
struct P
    v: i32

impl P
    fn put(self:& P, x: i32, y: i16)
        self.v = x + y as i32

struct O
    p: P

struct OO
    o: O

pub fn main() -> i32
    var p: P = P { v: 0 }
    p.put(1, 2)
    if p.v != 3
        return 1
    var o: O = O { p: P { v: 0 } }
    o.p.put(10, 1)
    if o.p.v != 11
        return 3
    var oo: OO = OO { o: O { p: P { v: 0 } } }
    oo.o.p.put(20, 2)
    if oo.o.p.v != 22
        return 4
    return 42
"""

# The #1581 repro, in both spellings: `-> void` and no return type.
VOID_METHODS = """\
struct Box
    v: i64

impl Box
    fn nv(self, c: i64) -> void
        if c > 0
            let q: i64 = 1

    fn nn(self:& Box, c: i32)
        self.v = c as i64

pub fn main() -> i32
    var b: Box = Box { v: 7 }
    b.nv(1)
    b.nn(42)
    return b.v as i32
"""

# Bool params take i1: a literal, a comparison, a bool-returning call, and a
# bool identifier (already i1 per bool_reg_is_i1, so it must not be trunc'd).
BOOL_PARAM = """\
struct B
    v: i64

impl B
    fn yes(self) -> bool
        true

    fn pick(self, c: bool, a: i64, b: i64) -> i64
        if c
            return a
        b

pub fn main() -> i32
    let b: B = B { v: 3 }
    var r: i64 = b.pick(true, 10, 1)
    r = r + b.pick(b.v > 5, 100, 2)
    r = r + b.pick(b.yes(), 30, 3)
    let flag: bool = true
    r = r + b.pick(flag, 1, 50)
    return r as i32
"""

# The void half on its own: i64 args only, so clang accepts the old IR and
# only the IR check below can see the `call i64`.
VOID_I64_ONLY = """\
struct Box
    v: i64

impl Box
    fn nv(self, c: i64) -> void
        if c > 0
            let q: i64 = 1

    fn nn(self:& Box, c: i64)
        self.v = c

pub fn main() -> i32
    var b: Box = Box { v: 7 }
    b.nv(1)
    b.nn(42)
    return b.v as i32
"""

CASES = [
    ("mut_ref_i32", MUT_REF_I32),
    ("by_value_i32", BY_VALUE_I32),
    ("widths", WIDTHS),
    ("receiver_forms", RECEIVER_FORMS),
    ("void_methods", VOID_METHODS),
    ("bool_param", BOOL_PARAM),
    ("void_i64_only", VOID_I64_ONLY),
]


@pytest.mark.integration
@pytest.mark.parametrize("name,program", CASES, ids=[c[0] for c in CASES])
def test_method_args_match_ritz0(ritz1_bin, tmp_path, name, program):  # noqa: F811
    expected = _run("ritz0", tmp_path, name, program)
    got = _run("ritz1", tmp_path, name, program)
    assert got == expected, f"{name}: ritz1 exit {got}, ritz0 exit {expected}"


@pytest.mark.integration
def test_void_method_called_as_void(ritz1_bin, tmp_path):  # noqa: F811
    """clang accepts `call i64` to a void define, so check the IR itself."""
    _run("ritz1", tmp_path, "void_ir", VOID_I64_ONLY)
    ll = (tmp_path / "void_ir_ritz1.ll").read_text()
    for m in ("Box_nv", "Box_nn"):
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
    fn pick(self, c: bool, a: i64) -> i64
        if c
            return a
        0

pub fn main() -> i32
    let b: B = B { v: 3 }
    return b.pick(FLAG, 42) as i32
"""


@pytest.mark.integration
def test_bool_global_arg_not_retruncated(ritz1_bin, tmp_path):  # noqa: F811
    assert _run("ritz1", tmp_path, "bool_global", BOOL_GLOBAL) == 42
