"""AGAST #2064: ritz1 lowers a struct-literal field of type u64.

THE DEFECT

emit_struct_lit_field_store (ritz1/src/emitter_expr.ritz) picked the store
type for each field from a list of scalar kinds. The list had TYPE_I64 but
not TYPE_U64, so `S { a: 3 }` with `a: u64` fell through to "ritz1 cannot
emit: struct literal field of this type is not lowered". Every other integer
width, signed or unsigned, was handled.

THE FIX

u64 is stored like i64: the value is already an i64 register, so it needs no
trunc.

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# The ticket's reproducer.
TICKET = """\
struct S
    a: u64

pub fn main() -> i32
    let s: S = S { a: 3 }
    return s.a as i32
"""

# A value with the top bit set must round-trip unchanged (no sign games).
HIGH_BIT = """\
struct S
    a: u64

pub fn main() -> i32
    let s: S = S { a: 0x8000000000000005 }
    if s.a >> 63 != 1
        return 1
    return (s.a & 0xff) as i32
"""

# u64 between narrower fields: field indices and widths must line up.
MIXED = """\
struct M
    x: u8
    a: u64
    y: i32
    b: u64

pub fn main() -> i32
    let m: M = M { b: 40, y: -1, a: 1000000000000, x: 2 }
    if m.a != 1000000000000
        return 1
    if m.y != -1
        return 2
    return (m.b + m.x as u64) as i32
"""

# The literal as a call argument and as a return value (other lowering paths
# that share the field-store loop), with a u64 local as the initialiser.
RVALUE = """\
struct S
    a: u64
    b: u64

fn make(v: u64) -> S
    return S { a: v, b: v + 1 }

fn sum(s: S) -> u64
    return s.a + s.b

pub fn main() -> i32
    let v: u64 = 20
    return sum(make(v)) as i32 + sum(S { a: 0, b: 1 }) as i32
"""

CASES = {
    "ticket": (TICKET, 3),
    "high_bit": (HIGH_BIT, 5),
    "mixed": (MIXED, 42),
    "rvalue": (RVALUE, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    program, want = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1_struct_lit_u64_field(ritz1_bin, tmp_path, name):
    """ritz1 refused a u64 struct-literal field (#2064)."""
    program, want = CASES[name]
    assert _run("ritz1", tmp_path, name, program) == want
