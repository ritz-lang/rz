"""AGAST #1814 (FIX step 0): ritz0 and ritz1 must agree on struct layout for
every primitive field type and every array element type.

THE DEFECT

ritz1's `emit_field_llvm_type` array-element ladder knew only i32 / i64 /
i8 / u8 / ptr / struct, so `a: [4]u16` was declared `[4 x i64]` while ritz1's
own `get_struct_size_by_name` sized it 8 bytes:

    struct S { a: [4]u16, b: i64 }
    ritz0:  {[4 x i16], i64}   sizeof = 16
    ritz1:  {[4 x i64], i64}   sizeof = 16   <- 40-byte type, 16-byte malloc

so `malloc(sizeof(S))` then `p.b = ...` stored past the block, and code built
by the two compilers disagreed on the layout. Separately, scalar `bool` fields
were sized 8 (declared i1), and `f32` fields 8 in BOTH compilers (declared
float) — ritz0's size table had no f32 entry and fell back to (8, 8).

THE ORACLE

* LLVM type body: ritz0's `%T = type {...}` line (typed pointers normalised
  to `ptr`), so ritz1 emits the same layout ritz0-built code expects.
* sizeof: the natural-alignment (x86_64 DataLayout) size of that body,
  computed here, so neither compiler's own size table is trusted.
"""

import re
import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import _run, ritz1_bin  # noqa: F401

# (ritz spelling, LLVM spelling, size, align) for every primitive.
PRIMS = [
    ("i8", "i8", 1, 1),
    ("u8", "i8", 1, 1),
    ("i16", "i16", 2, 2),
    ("u16", "i16", 2, 2),
    ("i32", "i32", 4, 4),
    ("u32", "i32", 4, 4),
    ("i64", "i64", 8, 8),
    ("u64", "i64", 8, 8),
    ("f32", "float", 4, 4),
    ("f64", "double", 8, 8),
    ("bool", "i1", 1, 1),
    ("*u8", "ptr", 8, 8),
]
LLVM_SIZE = {llvm: (size, align) for _, llvm, size, align in PRIMS}

# Each field type is tested as a scalar and as a 3-element array, followed
# by a u8 (exposes a too-large size for the first field) and an i64 (exposes
# a too-small alignment / padding).
CASES = []
for _ritz, _llvm, _, _ in PRIMS:
    CASES.append((_ritz, f"{{{_llvm}, i8, i64}}"))
    CASES.append((f"[3]{_ritz}", f"{{[3 x {_llvm}], i8, i64}}"))


def _case_id(field: str) -> str:
    return field.replace("[3]", "arr3_").replace("*", "ptr_")


def _program(field: str) -> str:
    return f"""\
struct S
    a: {field}
    b: u8
    c: i64

pub fn main() -> i32
    return sizeof(S) as i32
"""


def _layout(body: str) -> tuple[int, int]:
    """(size, align) of an LLVM struct body like `{[3 x i16], i8, i64}`."""
    fields = [f.strip() for f in body.strip()[1:-1].split(",")]
    off, max_align = 0, 1
    for f in fields:
        m = re.fullmatch(r"\[(\d+) x (\S+)\]", f)
        if m:
            esize, align = LLVM_SIZE[m.group(2)]
            size = esize * int(m.group(1))
        else:
            size, align = LLVM_SIZE[f]
        off = (off + align - 1) // align * align + size
        max_align = max(max_align, align)
    return (off + max_align - 1) // max_align * max_align, max_align


def _struct_body(ll_text: str) -> str:
    """The `%S = type {...}` body, with typed pointers spelled `ptr`."""
    m = re.search(r'^%(?:S|"struct\.[^"]*\.S") = type (\{.*\})$', ll_text, re.M)
    assert m, "no `%S = type` line in the emitted IR"
    return re.sub(r"[A-Za-z0-9_%.\"]+\*+", "ptr", m.group(1))


def _compile_and_measure(compiler, tmp_path, field):
    name = _case_id(field)
    rc = _run(compiler, tmp_path, name, _program(field))
    body = _struct_body((tmp_path / f"{name}_{compiler}.ll").read_text())
    return body, rc


@pytest.mark.unit
def test_layout_helper_matches_known_answers():
    """The size oracle itself: the ticket's repro and the padding cases."""
    assert _layout("{[4 x i16], i64}") == (16, 8)
    assert _layout("{float, i8, i64}") == (16, 8)
    assert _layout("{[3 x i1], i8, i64}") == (16, 8)
    assert _layout("{[3 x double], i8, i64}") == (40, 8)


@pytest.mark.integration
@pytest.mark.parametrize("field,expected", CASES, ids=[_case_id(c[0]) for c in CASES])
def test_ritz0_layout_and_sizeof(tmp_path, field, expected):
    """ritz0 is the layout oracle; its sizeof must match that layout."""
    body, rc = _compile_and_measure("ritz0", tmp_path, field)
    assert body == expected
    assert rc == _layout(expected)[0], f"ritz0 sizeof(S) for a: {field}"


@pytest.mark.integration
@pytest.mark.parametrize("field,expected", CASES, ids=[_case_id(c[0]) for c in CASES])
def test_ritz1_layout_and_sizeof_match_ritz0(ritz1_bin, tmp_path, field, expected):
    """ritz1 declares the same `%S` as ritz0 and sizes it like LLVM does."""
    body, rc = _compile_and_measure("ritz1", tmp_path, field)
    assert body == expected, f"ritz1 declares a: {field} as {body}"
    assert rc == _layout(expected)[0], f"ritz1 sizeof(S) for a: {field}"


# The ticket's repro plus its consequence: a block of sizeof(S) bytes must
# hold every field. With `[4 x i64]` the store to `p.b` landed at offset 32
# of a 16-byte block — exactly where `mem[4]`, the guard word, lives.
BLOCK_REPRO = """\
struct S
    a: [4]u16
    b: i64

pub fn main() -> i32
    if sizeof(S) != 16
        return 1
    var mem: [5]i64
    mem[4] = 77
    let p: *S = @mem[0] as *S
    p.b = 0x1122334455667788
    p.a[0] = 1
    p.a[3] = 0xBEEF
    if mem[4] != 77
        return 2
    if p.b != 0x1122334455667788
        return 3
    if p.a[3] != 0xBEEF
        return 4
    if p.a[0] != 1
        return 5
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_struct_with_u16_array_fits_its_sizeof(ritz1_bin, tmp_path, compiler):
    assert _run(compiler, tmp_path, "block_repro", BLOCK_REPRO) == 42


# Element access through every member-array lowering path, per element type:
# a direct local struct (`s.a[i]`), a `*S` local (`p.a[i]`), a `*S` param and
# `@s.a[i]` handed to a callee. Each slot is written with a distinct value
# whose top bit is set where the type is narrower than 64 bits, so a wrong
# stride (neighbour clobbered), a wrong store width (`b`/`c` clobbered) or a
# zext/sext mix-up returns a code other than 42.
#   (element type, v0, v1, v2) — v2 is read back through `@s.a[2]`.
ELEM_VALUES = [
    ("u8", "1", "200", "0x7F"),
    ("i8", "1", "-2", "-128"),
    ("u16", "1", "65534", "0x8001"),
    ("i16", "1", "-2", "-32768"),
    ("u32", "1", "0xFFFFFFFE", "0x80000001"),
    ("i32", "1", "-2", "-2147483648"),
    ("u64", "1", "0x7FFFFFFFFFFFFFFE", "3"),
    ("i64", "1", "-2", "-3"),
]


def _elem_program(t: str, v0: str, v1: str, v2: str) -> str:
    return f"""\
struct S
    a: [3]{t}
    b: u8
    c: i64

fn put(p: *{t}, v: {t}) -> void
    *p = v

# Widened in the callee: ritz0 sign-extends a narrow unsigned CALL result
# before comparing (a separate ritz0 bug), which is not what this tests.
fn get(p: *{t}) -> i64
    let v: {t} = *p
    v as i64

fn via_param(q: *S) -> i32
    if q.a[1] != {v1}
        return 20
    q.a[0] = {v0}
    return 0

pub fn main() -> i32
    var s: S
    s.b = 7
    s.c = 99
    s.a[0] = {v0}
    s.a[1] = {v1}
    s.a[2] = {v2}
    if s.b != 7
        return 1
    if s.c != 99
        return 2
    if s.a[0] != {v0}
        return 3
    if s.a[1] != {v1}
        return 4
    if s.a[2] != {v2}
        return 5
    let p: *S = @s
    p.a[0] = {v1}
    if s.a[0] != {v1}
        return 6
    if p.a[1] != {v1}
        return 7
    if via_param(@s) != 0
        return 8
    if s.a[0] != {v0}
        return 9
    put(@s.a[2], {v1})
    if s.a[2] != {v1}
        return 10
    if get(@s.a[1]) != {v1}
        return 11
    if s.b != 7
        return 12
    if s.c != 99
        return 13
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("t,v0,v1,v2", ELEM_VALUES, ids=[e[0] for e in ELEM_VALUES])
def test_member_array_element_access(ritz1_bin, tmp_path, compiler, t, v0, v1, v2):
    assert _run(compiler, tmp_path, f"elem_{t}", _elem_program(t, v0, v1, v2)) == 42


BOOL_ELEMS = """\
struct S
    a: [3]bool
    b: u8
    c: i64

fn via_param(q: *S) -> i32
    if q.a[1]
        return 20
    q.a[1] = true
    return 0

pub fn main() -> i32
    var s: S
    s.b = 7
    s.c = 99
    s.a[0] = true
    s.a[1] = false
    s.a[2] = 3 > 2
    if s.b != 7
        return 1
    if s.c != 99
        return 2
    if not s.a[0]
        return 3
    if s.a[1]
        return 4
    if not s.a[2]
        return 5
    if via_param(@s) != 0
        return 6
    if not s.a[1]
        return 7
    let p: *S = @s
    p.a[0] = false
    if s.a[0]
        return 8
    if s.b != 7
        return 9
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_member_bool_array_element_access(ritz1_bin, tmp_path, compiler):
    assert _run(compiler, tmp_path, "elem_bool", BOOL_ELEMS) == 42


# Nested structs are aligned to their most-aligned field, not to 8 (LLVM
# natural alignment). `{%In, i8}` with `In = {i8, i16}` is 6 bytes, not 16.
NESTED = """\
struct In
    x: u8
    y: u16

struct S
    i: In
    b: u8

struct T
    arr: [3]In
    b: u8

struct W
    b: u8
    w: S
    f: f32

pub fn main() -> i32
    if sizeof(In) != 4
        return 1
    if sizeof(S) != 6
        return 2
    if sizeof(T) != 14
        return 3
    if sizeof(W) != 12
        return 4
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_nested_struct_sizeof_uses_natural_alignment(ritz1_bin, tmp_path, compiler):
    assert _run(compiler, tmp_path, "nested", NESTED) == 42


# ritz1 has no f32 element value model; indexing a `[N x float]` field must be
# a counted compile error, never an 8-byte stride over 4-byte slots.
F32_INDEX = {
    "read": "    return s.a[1] as i32\n",
    "write": "    s.a[1] = 1.5\n    return 0\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("op", sorted(F32_INDEX))
def test_ritz1_f32_member_array_index_fails_closed(ritz1_bin, tmp_path, op):
    src = tmp_path / f"f32_{op}.ritz"
    src.write_text(
        "struct S\n    a: [3]f32\n    c: i64\n\npub fn main() -> i32\n"
        "    var s: S\n" + F32_INDEX[op]
    )
    proc = subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(tmp_path / f"f32_{op}.ll")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 0
    assert "[N]f32 struct field" in proc.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("prim", [p[0] for p in PRIMS if not p[0].startswith("*")])
def test_sizeof_primitive(ritz1_bin, tmp_path, compiler, prim):
    """`sizeof(T)` for each primitive is its LLVM store size (bool/f32 were 8)."""
    prog = f"pub fn main() -> i32\n    return sizeof({prim}) as i32\n"
    expected = next(size for name, _, size, _ in PRIMS if name == prim)
    assert _run(compiler, tmp_path, f"sizeof_{prim}", prog) == expected
