"""AGAST #1603: ritz1 must scale `@arr[i] + n` by the element size.

THE DEFECT

`ptr_arith_elem_size` (ritz1/src/emitter_core.ritz) decides whether the left
operand of `+`/`-` is a pointer, and with what stride, by its AST shape. It
knew identifiers, member accesses and left-associated chains of those — but
not an address-of. `@arr[0] + 2` classified as "not a pointer" and lowered to
a raw `add i64 <addr>, 2`: a BYTE offset. For `[4]i32` that lands half-way
into element 0 instead of on element 2. No crash, a silently wrong value.

`let q: *i32 = @arr[0]` then `q + 2` was always right, because `q` is an
identifier with a recorded pointee. Only the inline address-of was missed.
test_level15::test_slice_subslice does exactly `make_slice_i32(@arr[0] + 3, 4)`.

Each program returns 42 only when the computed address is the intended
element; any other stride reads a neighbour or a split element and returns a
different code. ritz0 is the oracle, and must itself say 42.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

# The ticket's repro, as a main.
REPRO = """\
pub fn main() -> i32
    var arr: [4]i32
    arr[0] = 0
    arr[1] = 0
    arr[2] = 42
    arr[3] = 0
    let p: *i32 = @arr[0] + 2
    return *p
"""

I8 = """\
pub fn main() -> i32
    var arr: [4]i8
    arr[0] = 1
    arr[1] = 2
    arr[2] = 42
    arr[3] = 4
    let p: *i8 = @arr[0] + 2
    return *p as i32
"""

U16 = """\
pub fn main() -> i32
    var arr: [4]u16
    arr[0] = 1
    arr[1] = 2
    arr[2] = 3
    arr[3] = 42
    let p: *u16 = @arr[1] + 2
    return *p as i32
"""

I64 = """\
pub fn main() -> i32
    var arr: [4]i64
    arr[0] = 1
    arr[1] = 2
    arr[2] = 3
    arr[3] = 42
    let p: *i64 = @arr[0] + 3
    return *p as i32
"""

# 16-byte struct element: a byte offset of 1 lands inside element 0.
STRUCT = """\
struct LB
    start: i64
    fin: i64

pub fn main() -> i32
    var arr: [3]LB
    arr[0].start = 10
    arr[0].fin = 11
    arr[1].start = 42
    arr[1].fin = 21
    arr[2].start = 30
    arr[2].fin = 31
    let q: *LB = @arr[0] + 1
    return q.start as i32
"""

# `-` strides the same way: from element 3 back two lands on element 1.
SUB = """\
pub fn main() -> i32
    var arr: [4]i32
    arr[0] = 0
    arr[1] = 42
    arr[2] = 0
    arr[3] = 0
    let p: *i32 = @arr[3] - 2
    return *p
"""

# A left-associated chain whose spine bottoms out in an address-of.
CHAIN = """\
pub fn main() -> i32
    var arr: [4]i32
    arr[0] = 0
    arr[1] = 0
    arr[2] = 42
    arr[3] = 0
    let p: *i32 = @arr[0] + 3 - 1
    return *p
"""

# Indexing through a pointer rather than an array local: same stride.
PTR_INDEX = """\
pub fn main() -> i32
    var arr: [4]i32
    arr[0] = 0
    arr[1] = 0
    arr[2] = 0
    arr[3] = 42
    let base: *i32 = @arr[0]
    let p: *i32 = @base[1] + 2
    return *p
"""

# A GLOBAL `[N]T` array.
GLOBAL = """\
var g_arr: [4]i32

pub fn main() -> i32
    g_arr[0] = 0
    g_arr[1] = 0
    g_arr[2] = 42
    g_arr[3] = 0
    let p: *i32 = @g_arr[0] + 2
    return *p
"""

# The test_level15 shape: the sum is passed straight to a call.
CALL_ARG = """\
fn at(p: *i32, i: i64) -> i32
    return p[i]

pub fn main() -> i32
    var arr: [10]i32 = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    if at(@arr[0] + 3, 0) != 3
        return 1
    if at(@arr[0] + 3, 3) != 6
        return 2
    return 42
"""

CASES = {
    "repro": REPRO,
    "i8": I8,
    "u16": U16,
    "i64": I64,
    "struct": STRUCT,
    "sub": SUB,
    "chain": CHAIN,
    "ptr_index": PTR_INDEX,
    "global": GLOBAL,
    "call_arg": CALL_ARG,
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_addr_of_ptr_arith_ritz1_matches_ritz0(ritz1_bin, tmp_path, name):  # noqa: F811
    program = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == 42, "oracle moved"
    assert _run("ritz1", tmp_path, name, program) == 42
