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
from pathlib import Path

import pytest

from test_ritz1_builtin_struct_shadow import _run

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

fn get(p: *{t}) -> {t}
    *p

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


# AGAST #1954: a `[N x float]` field element reads and writes as a real
# `float` (it was a counted compile error, #1814 / #1890).  ritz0 is the oracle.
F32_INDEX = {
    "read": "    s.a[1] = 1.5\n    return (s.a[1] * 2.0) as i32 + 39\n",
    "write": "    s.a[1] = 1.5\n    s.a[0] = -2.0\n    s.a[2] = s.a[1] + s.a[0]\n"
    "    if s.a[2] != -0.5\n        return 1\n    return 42\n",
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("op", sorted(F32_INDEX))
def test_f32_member_array_index_runs(ritz1_bin, tmp_path, compiler, op):
    prog = (
        "struct S\n    a: [3]f32\n    c: i64\n\npub fn main() -> i32\n"
        "    var s: S\n" + F32_INDEX[op]
    )
    assert _run(compiler, tmp_path, f"f32_{op}", prog) == 42


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("prim", [p[0] for p in PRIMS if not p[0].startswith("*")])
def test_sizeof_primitive(ritz1_bin, tmp_path, compiler, prim):
    """`sizeof(T)` for each primitive is its LLVM store size (bool/f32 were 8)."""
    prog = f"pub fn main() -> i32\n    return sizeof({prim}) as i32\n"
    expected = next(size for name, _, size, _ in PRIMS if name == prim)
    assert _run(compiler, tmp_path, f"sizeof_{prim}", prog) == expected


# AGAST #1889: the two types.ritz rows the per-primitive tables above don't
# reach -- `usize` spelled as u64 (ty_from_name; `isize`/`usize` are aliases,
# #3464) and `@&T` carried as `ptr` in a signature (ty_value_llvm; i64 there
# makes the call operand mismatch its definition and the IR fails to link).
ALIASES_AND_MUT_REF = """\
struct P
    x: i32

fn pick(p: @&P) -> @&P
    p

pub fn main() -> i32
    var a: P
    a.x = 40
    let r: @&P = pick(@&a)
    r.x = r.x + 2
    if sizeof(usize) != 8 or sizeof(isize) != 8
        return 1
    let u: usize = 0
    let v: usize = u -% 1
    if v < u
        return 2
    a.x
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_usize_alias_and_mut_ref_signature(ritz1_bin, tmp_path, compiler):
    assert _run(compiler, tmp_path, "alias_mutref", ALIASES_AND_MUT_REF) == 42


# AGAST #1889 (#1814 FIX step 2): local / global `[3]T` arrays per element
# type, through the array-literal, array-fill, local index, global index and
# `*T` element paths -- the ones whose private type ladders were replaced by
# ritz1/src/types.ritz.  A wrong element width, stride or extension returns a
# code other than 42.
def _array_program(t: str, v0: str, v1: str, v2: str) -> str:
    return f"""\
var G: [3]{t}

fn second(p: *{t}) -> {t}
    *(p + 1)

pub fn main() -> i32
    var lit: [3]{t} = [{v0}, {v1}, {v2}]
    if lit[0] != {v0}
        return 1
    if lit[1] != {v1}
        return 2
    if lit[2] != {v2}
        return 3
    var fill: [3]{t} = [{v2}; 3]
    if fill[0] != {v2} or fill[2] != {v2}
        return 4
    G[0] = {v0}
    G[1] = {v1}
    G[2] = {v2}
    if G[1] != {v1}
        return 5
    if G[2] != {v2}
        return 6
    if G[0] != {v0}
        return 7
    if second(@lit[0]) != {v1}
        return 8
    if second(@G[0]) != {v1}
        return 9
    fill[1] = G[1]
    if fill[1] != {v1} or fill[0] != {v2}
        return 10
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("t,v0,v1,v2", ELEM_VALUES, ids=[e[0] for e in ELEM_VALUES])
def test_local_and_global_array_element_access(ritz1_bin, tmp_path, compiler, t, v0, v1, v2):
    assert _run(compiler, tmp_path, f"arr_{t}", _array_program(t, v0, v1, v2)) == 42


# AGAST #1889: ritz1 spells every primitive type fact in ONE module,
# ritz1/src/types.ritz.  These static checks keep the dozen-plus private
# copies (#1564, #1814, #1966, #2063 were each a copy that missed a type)
# from growing back.  They read the source; no compiler runs.
RITZ1_SRC = Path(__file__).resolve().parents[2] / "ritz1" / "src"
TYPES_RITZ = "types.ritz"

# The ladder functions types.ritz replaced.  None may be defined or called.
DELETED_LADDERS = [
    "emit_llvm_type",
    "array_elem_llvm",
    "field_array_elem_llvm",
    "local_array_elem_llvm",
    "global_array_elem_llvm",
    "const_array_elem_llvm",
    "ptr_field_elem_llvm",
    "narrow_type_name",
    "narrow_int_width",
    "narrow_is_unsigned",
    "int_prim_bits",
    "int_prim_signed",
    "prim_name_size",
]

# `<operand> ==/!= TypeKind.I16`: the kinds one operand is compared against.
_INT_KIND = re.compile(r"([\w.]+)\s*[!=]=\s*TypeKind\.([IU])(8|16|32|64)\b")
# A `match` or-pattern arm `TypeKind.I16 | TypeKind.U16 =>` (AGAST #4450) is
# the same rung: every alternative is compared against the one scrutinee.
_OR_ARM = re.compile(r"^\s*TypeKind\.\w+(?:\s*\|\s*TypeKind\.\w+)+\s*=>")
_ARM_KIND = re.compile(r"TypeKind\.([IU])(8|16|32|64)\b")


def _code_lines():
    """(file, lineno, code) for every ritz1 source line, comments stripped."""
    for path in sorted(RITZ1_SRC.glob("*.ritz")):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            code = re.sub(r'c?"(?:[^"\\]|\\.)*"', '""', line).split("#", 1)[0]
            if code.strip():
                yield path.name, n, code


@pytest.mark.unit
@pytest.mark.parametrize("name", DELETED_LADDERS)
def test_deleted_type_ladder_stays_deleted(name):
    hits = [f"{f}:{n}" for f, n, code in _code_lines() if re.search(rf"\b{name}\b", code)]
    assert not hits, f"{name} is replaced by types.ritz, still used at {hits}"


def _ladder_rungs():
    """Lines outside types.ritz that spell a primitive-type ladder rung:
    both signednesses of one width (`t == TypeKind.I16 or t == TypeKind.U16`,
    or the arm `TypeKind.I16 | TypeKind.U16 =>`) or a hand-rolled set of three
    or more integer kinds (`is_signed`), compared against ONE operand
    (`a == TypeKind.U64 and b == TypeKind.I64` is two facts)."""
    for f, n, code in _code_lines():
        if f in (TYPES_RITZ, "ast.ritz"):
            continue
        by_operand = {}
        for operand, sign, width in _INT_KIND.findall(code):
            by_operand.setdefault(operand, set()).add((sign, width))
        if _OR_ARM.match(code):
            for sign, width in _ARM_KIND.findall(code):
                by_operand.setdefault("<match scrutinee>", set()).add((sign, width))
        for kinds in by_operand.values():
            widths = [w for _, w in kinds]
            if len(kinds) >= 3 or len(widths) != len(set(widths)):
                yield f"{f}:{n}: {code.strip()}"
                break


@pytest.mark.unit
def test_no_inline_type_ladders_outside_types_ritz():
    rungs = list(_ladder_rungs())
    assert not rungs, (
        f"{len(rungs)} inline type ladder rung(s); ask types.ritz "
        "(ty_int_bits / ty_is_signed / ty_mem_llvm / ty_store_size) instead:\n"
        + "\n".join(rungs[:40])
    )


@pytest.mark.unit
def test_types_ritz_table_is_complete():
    """Every primitive kind has a row in each types.ritz function."""
    text = (RITZ1_SRC / TYPES_RITZ).read_text()
    for kind in ["I8", "U8", "I16", "U16", "I32", "U32", "I64", "U64"]:
        assert f"TypeKind.{kind}" in text
    for spelling in ['"float"', '"double"', '"i1"', '"ptr"']:
        assert spelling in text
