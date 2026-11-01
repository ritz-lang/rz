"""AGAST #1975: ritz1 types an unannotated `let s = p[a..b]` over a bare
`*T` as a pointer carrying T, not as a T scalar.

THE DEFECT

get_expr_type (EXPR_INDEX on a TYPE_PTR base) returned the recorded
pointee for the integer widths without the `e.right.kind != EXPR_RANGE`
guard #1973 gave the f32/f64 arm, so a range over a `*u32` was typed u32.
And emit_var_decl never narrowed `let s = p[a..b]` at all: `s` stayed the
parser's i64 default with no pointee, so `s[i]` strode by bytes.

ritz0 rejects slicing a bare pointer, so these programs are checked
against a fixed exit code (as test_ritz1_ptr_range_stride.py does).
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run

# Each case: element type, array literal, expected s[0] and s[1] where
# s = p[2..4].  Values exceed the next-smaller width so a byte / narrower
# stride or load reads something else.
CASES = [
    ("u8", "[1, 2, 3, 4, 5]", "3", "4"),
    ("i8", "[1, 2, -3, 100, 5]", "-3", "100"),
    ("u16", "[1, 2, 300, 400, 5]", "300", "400"),
    ("i16", "[1, 2, -300, 400, 5]", "-300", "400"),
    ("u32", "[1, 2, 70000, 80000, 5]", "70000", "80000"),
    ("i32", "[1, 2, -70000, 80000, 5]", "-70000", "80000"),
    ("u64", "[1, 2, 0x100000000, 0x200000000, 5]", "0x100000000", "0x200000000"),
    ("i64", "[1, 2, -5000000000, 6000000000, 5]", "-5000000000", "6000000000"),
    ("f32", "[1.0, 2.0, 3.5, -4.25, 5.0]", "3.5", "-4.25"),
    ("f64", "[1.0, 2.0, 3.5, -4.25, 5.0]", "3.5", "-4.25"),
]

# The inferred `let s` is read (s[0], s[1]), written through (s[1] = ..),
# re-sliced (`let u = s[1..2]`), and passed where a `*T` is expected.  A
# local, a parameter and a global base are each sliced.
PROG = """\
var g: *{elem} = null

fn at(q: *{elem}, i: i64) -> {elem}
    q[i]

fn second(p: *{elem}) -> {elem}
    let s = p[2..4]
    s[1]

pub fn main() -> i32
    var a: [5]{elem} = {lit}
    let p: *{elem} = @a as *{elem}
    let s = p[2..4]
    let x0: {elem} = {v0}
    let x1: {elem} = {v1}
    if s[0] != x0
        return 1
    if s[1] != x1
        return 2
    if second(p) != x1
        return 3
    g = p
    let t = g[2..4]
    if t[0] != x0
        return 4
    if t[1] != x1
        return 5
    let u = s[1..2]
    if u[0] != x1
        return 6
    if at(s, 1) != x1
        return 7
    s[1] = x0
    if a[3] != x0
        return 8
    if a[4] != {lit5}
        return 9
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("elem,lit,v0,v1", CASES, ids=[c[0] for c in CASES])
def test_inferred_ptr_range_let_keeps_pointee(ritz1_bin, tmp_path, elem, lit, v0, v1):
    lit5 = "5.0" if elem.startswith("f") else "5"
    src = PROG.format(elem=elem, lit=lit, v0=v0, v1=v1, lit5=lit5)
    assert _run("ritz1", tmp_path, f"pri_{elem}", src) == 42


# The ticket's repro.
REPRO = """\
pub fn main() -> i32
    var a: [4]u32 = [10, 20, 30, 40]
    let p: *u32 = @a as *u32
    let s = p[2..4]
    if s[1] != 40
        return 1
    return 42
"""


@pytest.mark.integration
def test_ticket_repro(ritz1_bin, tmp_path):
    assert _run("ritz1", tmp_path, "pri_repro", REPRO) == 42


# A range and an inferred range `let` compare equal to the pointer they
# alias (regression guard; compares are i64 whatever get_expr_type says).
CMP = """\
pub fn main() -> i32
    var a: [4]{elem} = [1, 2, 3, 4]
    let p: *{elem} = @a as *{elem}
    if p[2..4] != p + 2
        return 1
    let s = p[2..4]
    if s != p + 2
        return 2
    if s + 1 != @a[3]
        return 3
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("elem", ["i8", "i16", "u16", "i32", "u32", "i64", "u64"])
def test_ptr_range_types_as_pointer(ritz1_bin, tmp_path, elem):
    assert _run("ritz1", tmp_path, f"pri_cmp_{elem}", CMP.format(elem=elem)) == 42


# The range's own type: a pointer carrying the base's pointee.  `*(p[2..4])`
# derefs it at the element's width.  Typed as the element (or u8 for
# f32/f64), the deref fell to the i64 default and read 8 bytes.  Local,
# param and global bases, every width (f32 / f64 since AGAST #2022).
DEREF = """\
var g: *{elem} = null

fn first(p: *{elem}) -> {elem}
    *(p[2..4])

pub fn main() -> i32
    var a: [5]{elem} = {lit}
    let p: *{elem} = @a as *{elem}
    let x0: {elem} = {v0}
    if *(p[2..4]) != x0
        return 1
    if first(p) != x0
        return 2
    g = p
    if *(g[2..4]) != x0
        return 3
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("elem,lit,v0,v1", CASES, ids=[c[0] for c in CASES])
def test_deref_ptr_range_loads_element(ritz1_bin, tmp_path, elem, lit, v0, v1):
    src = DEREF.format(elem=elem, lit=lit, v0=v0)
    assert _run("ritz1", tmp_path, f"pri_deref_{elem}", src) == 42
