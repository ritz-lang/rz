"""AGAST #2169: ritz1 must copy a whole array value at the array's real type.

THE DEFECT

Two places in ritz1 treated a whole `[N]T` value as an i64:

1. `a = [x, y]` (whole-array assignment from a literal) emitted
   `store i64 %lit, ptr %a` with %lit an `[N x T]` aggregate -- clang rejects
   the module for any struct element type.
2. An unannotated `var b = a` of an array typed b as i64 and copied 8 bytes
   (`load i64, ptr %a`): a silent miscompile for any array over 8 bytes.

Each program returns 42 only when every element arrived intact and the copy
is independent of its source.  ritz0 is the oracle.
"""

import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run

# `[3]i64` (24 bytes) copied by an unannotated var: every element must come
# across, and writing the copy must leave the source alone.
I64_UNANNOTATED_COPY = """\
pub fn main() -> i32
    var a: [3]i64 = [10, 20, 30]
    var b = a
    b[0] = 1
    if a[0] != 10
        return 1
    if b[1] != 20
        return 2
    if b[2] != 30
        return 3
    if b[0] != 1
        return 4
    return 42
"""

# `let` takes the same path as `var`.
I64_UNANNOTATED_LET = """\
pub fn main() -> i32
    var a: [3]i64 = [10, 20, 30]
    let b = a
    a[2] = 0
    if b[0] != 10
        return 1
    if b[2] != 30
        return 2
    return 42
"""

# Whole-array assignment from a literal, scalar elements.
I64_LITERAL_ASSIGN = """\
pub fn main() -> i32
    var a: [3]i64 = [1, 2, 3]
    a = [7, 8, 9]
    if a[0] != 7
        return 1
    if a[1] != 8
        return 2
    if a[2] != 9
        return 3
    return 42
"""

# Narrow elements: the literal is built at the element width.
I32_LITERAL_ASSIGN = """\
pub fn main() -> i32
    var a: [4]i32 = [1, 2, 3, 4]
    a = [5, 6, 7, 8]
    var b = a
    if b[0] + b[1] + b[2] + b[3] != 26
        return 1
    return 42
"""

# Struct elements (no drop glue): literal assignment and unannotated copy.
STRUCT_ELEMS = """\
struct Pt
    x: i64
    y: i64

pub fn main() -> i32
    var a: [2]Pt = [Pt { x: 1, y: 2 }, Pt { x: 3, y: 4 }]
    a = [Pt { x: 5, y: 6 }, Pt { x: 7, y: 8 }]
    var b = a
    b[0].x = 100
    if a[0].x != 5
        return 1
    if b[1].y != 8
        return 2
    if a[1].x != 7
        return 3
    return 42
"""

# The annotated and assignment forms copied 8 bytes too (`load i64`): they
# only looked right for arrays of at most 8 bytes.
I64_ANNOTATED_AND_ASSIGN = """\
pub fn main() -> i32
    var a: [3]i64 = [10, 20, 30]
    var d: [3]i64 = a
    var c: [3]i64 = [4, 5, 6]
    a = c
    if d[2] != 30
        return 1
    if a[2] != 6
        return 2
    c[1] = 0
    if a[1] != 5
        return 3
    return 42
"""

# `a = [v; N]` fills in place; `a = [a[1], a[0]]` reads every element before
# writing any (a swap, as in ritz0).
FILL_AND_SWAP = """\
pub fn main() -> i32
    var a: [2]i64 = [1, 2]
    a = [a[1], a[0]]
    if a[0] != 2
        return 1
    if a[1] != 1
        return 2
    a = [9; 2]
    if a[0] + a[1] != 18
        return 3
    return 42
"""

# `*p` for `p: *[N]T` copies the pointee.
DEREF_SOURCE = """\
fn get(p: *[3]i64) -> i64
    var b: [3]i64 = *p
    return b[0] + b[1] + b[2]

pub fn main() -> i32
    var a: [3]i64 = [10, 12, 20]
    return get(@a) as i32
"""

CASES = {
    "i64_annotated_and_assign": I64_ANNOTATED_AND_ASSIGN,
    "fill_and_swap": FILL_AND_SWAP,
    "deref_source": DEREF_SOURCE,
    "i64_unannotated_copy": I64_UNANNOTATED_COPY,
    "i64_unannotated_let": I64_UNANNOTATED_LET,
    "i64_literal_assign": I64_LITERAL_ASSIGN,
    "i32_literal_assign": I32_LITERAL_ASSIGN,
    "struct_elems": STRUCT_ELEMS,
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CASES))
def test_array_value_copy_ritz1_matches_ritz0(ritz1_bin, tmp_path, name):
    program = CASES[name]
    assert _run("ritz0", tmp_path, name, program) == 42
    assert _run("ritz1", tmp_path, name, program) == 42


@pytest.mark.integration
def test_array_length_mismatch_fails_closed(ritz1_bin, tmp_path):
    """A literal of the wrong length is rejected, not stored short."""
    src = tmp_path / "bad.ritz"
    src.write_text(
        "pub fn main() -> i32\n"
        "    var a: [3]i64 = [1, 2, 3]\n"
        "    a = [1, 2]\n"
        "    return 0\n"
    )
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(tmp_path / "bad.ll")],
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert "array literal length does not match" in proc.stderr
