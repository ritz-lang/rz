"""Regression tests for AGAST #1608 (and #1661): struct literals and array
literals nested inside other literals, under ritz1.

    let r: Rect = Rect { origin: Point { x: 1, y: 2 }, w: 3 }        # #1661
    let a: [2]Point = [Point { x: 1, y: 2 }, Point { x: 3, y: 4 }]   # #1608
    var b: Buffer = Buffer { data: [1, 2, 3, 4], len: 4 }            # #1608

All three compile under ritz0. When #1608 was filed ritz1 rejected all three
with "struct literal not in var initializer context", which made every fn in
ritz0/test/test_level12.ritz compile-fail. By the time it was picked up:

  * the nested field (#1661) was already written in place, by #1655. The
    `nested_field` cases are guards that keep it that way.
  * `[Point { .. }, ..]` produced invalid IR: the typed-array `let` path
    stored each element as an i64 into an `[N x %Point]` slot.
  * an array literal as an array FIELD (`Buffer { data: [..] }`) was
    refused ("struct literal field of this type is not lowered").

The fix is one helper, emit_array_lit_into, which writes a `[a, b, ..]`
literal into typed storage in place. Both the `let` and the struct-field
paths call it. A struct-literal element is written into its slot with
emit_struct_lit_to_alloca. Any other struct-valued element (a local or a call
result) is stored as the declared `%T` aggregate.

Each program returns 42 when correct and a distinct small code naming the
failed check otherwise. ritz0 is the oracle. Every case runs the program:
a misplaced store only shows up at runtime.
"""

import os
import re
import subprocess

import pytest

from test_ritz1_builtin_struct_shadow import (  # noqa: F401
    RITZ1_BIN,
    RITZ_ROOT,
    _run,
    ritz1_bin,
)

EXPECTED = 42

PRELUDE = """\
struct Point
    x: i32
    y: i32

struct Rect
    origin: Point
    w: i32

struct Holder
    d: Point

# Mixed widths so a store at the wrong width clobbers a neighbour.
struct M
    a: u8
    b: i64
    c: i32

struct Buffer
    data: [4]i32
    len: i32

struct Bytes
    pre: u8
    data: [4]u8
    post: u8

struct Poly
    n: i32
    pts: [3]Point
    tag: i32

fn mkp(x: i32, y: i32) -> Point
    Point { x: x, y: y }

"""

PROGRAMS = {
    # --- the ticket repros ---------------------------------------------------
    "ticket_1608": """\
pub fn main() -> i32
    let r: Rect = Rect { origin: Point { x: 1, y: 2 }, w: 3 }
    let a: [2]Point = [Point { x: 1, y: 2 }, Point { x: 3, y: 4 }]
    if r.origin.y + a[1].x != 5
        return 1
    42
""",
    "nested_field_1661": """\
pub fn main() -> i32
    let h: Holder = Holder { d: Point { x: 1, y: 2 } }
    if h.d.x != 1 or h.d.y != 2
        return 1
    42
""",
    "nested_field_tail_1661": """\
fn mk() -> Holder
    Holder { d: Point { x: 5, y: 6 } }

pub fn main() -> i32
    let h: Holder = mk()
    if h.d.x != 5 or h.d.y != 6
        return 1
    42
""",
    # --- an array literal of struct literals --------------------------------
    "array_of_struct_lits_let": """\
pub fn main() -> i32
    let a: [3]Point = [Point { x: 1, y: 2 }, Point { x: 3, y: 4 }, Point { y: 6, x: 5 }]
    if a[0].x != 1 or a[0].y != 2
        return 1
    if a[1].x != 3 or a[1].y != 4
        return 2
    if a[2].x != 5 or a[2].y != 6
        return 3
    42
""",
    "array_of_struct_lits_var_mutate": """\
pub fn main() -> i32
    var a: [2]Point = [Point { x: 1, y: 2 }, Point { x: 3, y: 4 }]
    a[1].y = 40
    if a[0].x != 1 or a[0].y != 2
        return 1
    if a[1].x != 3 or a[1].y != 40
        return 2
    42
""",
    "array_of_struct_lits_mixed_widths": """\
pub fn main() -> i32
    # `a` stays < 128: ritz0 sign-extends `arr[i].u8_field` (AGAST #1790).
    let a: [2]M = [M { a: 100, b: 5000000000, c: -7 }, M { c: 9, a: 1, b: -2 }]
    if a[0].a != 100 or a[0].b != 5000000000 or a[0].c != -7
        return 1
    if a[1].a != 1 or a[1].b != -2 or a[1].c != 9
        return 2
    42
""",
    "array_of_nested_struct_lits": """\
pub fn main() -> i32
    let a: [2]Rect = [Rect { origin: Point { x: 1, y: 2 }, w: 3 }, Rect { w: 6, origin: Point { x: 4, y: 5 } }]
    if a[0].origin.x != 1 or a[0].origin.y != 2 or a[0].w != 3
        return 1
    if a[1].origin.x != 4 or a[1].origin.y != 5 or a[1].w != 6
        return 2
    42
""",
    # Struct-valued elements that are NOT literals: a local and a call result.
    "array_of_struct_values": """\
pub fn main() -> i32
    let p: Point = Point { x: 7, y: 8 }
    let a: [3]Point = [p, mkp(9, 10), Point { x: 11, y: 12 }]
    if a[0].x != 7 or a[0].y != 8
        return 1
    if a[1].x != 9 or a[1].y != 10
        return 2
    if a[2].x != 11 or a[2].y != 12
        return 3
    42
""",
    # The scalar typed-array path still goes through the same helper.
    "array_of_scalars_unchanged": """\
pub fn main() -> i32
    let a: [4]u8 = [1, 2, 250, 4]
    let b: [3]i64 = [5000000000, -1, 3]
    if a[0] != 1 or a[2] != 250 or a[3] != 4
        return 1
    if b[0] != 5000000000 or b[1] != -1 or b[2] != 3
        return 2
    42
""",
    # --- an array literal as an array FIELD of a struct literal -------------
    "array_field_let": """\
pub fn main() -> i32
    var b: Buffer = Buffer { data: [1, 2, 3, 4], len: 4 }
    if b.len != 4
        return 1
    if b.data[0] != 1 or b.data[1] != 2 or b.data[2] != 3 or b.data[3] != 4
        return 2
    42
""",
    "array_field_narrow_neighbours": """\
pub fn main() -> i32
    var b: Bytes = Bytes { pre: 9, data: [1, 2, 3, 255], post: 7 }
    if b.pre != 9 or b.post != 7
        return 1
    if b.data[0] != 1 or b.data[3] != 255
        return 2
    42
""",
    "array_field_tail": """\
fn mk(k: i32) -> Buffer
    Buffer { len: 4, data: [k, k + 1, k + 2, k + 3] }

pub fn main() -> i32
    var b: Buffer = mk(10)
    if b.len != 4 or b.data[0] != 10 or b.data[3] != 13
        return 1
    42
""",
    "array_field_of_struct_lits": """\
pub fn main() -> i32
    var p: Poly = Poly { n: 3, pts: [Point { x: 1, y: 2 }, mkp(3, 4), Point { x: 5, y: 6 }], tag: 99 }
    if p.n != 3 or p.tag != 99
        return 1
    if p.pts[0].x != 1 or p.pts[0].y != 2
        return 2
    if p.pts[1].x != 3 or p.pts[1].y != 4
        return 3
    if p.pts[2].x != 5 or p.pts[2].y != 6
        return 4
    42
""",
    "array_field_of_struct_lits_return": """\
fn mk() -> Poly
    return Poly { tag: 5, pts: [Point { x: 1, y: 1 }, Point { x: 2, y: 2 }, Point { x: 3, y: 3 }], n: 3 }

pub fn main() -> i32
    var p: Poly = mk()
    if p.n != 3 or p.tag != 5
        return 1
    if p.pts[0].y + p.pts[1].y + p.pts[2].x != 6
        return 2
    42
""",
}


def _ritz1_ir(tmp_path, program: str) -> str:
    src = tmp_path / "shape.ritz"
    src.write_text(program)
    ll = tmp_path / "shape.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run(
        [str(RITZ1_BIN), str(src), "-o", str(ll)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert comp.returncode == 0, comp.stderr[-2000:]
    return ll.read_text()


@pytest.mark.integration
def test_ritz1_struct_lit_elements_written_in_place(ritz1_bin, tmp_path):  # noqa: F811
    """A struct-literal element or array-field element goes straight into its slot.

    Building it in a temp `alloca %Point` and copying it would also run
    correctly, so the runtime cases cannot see the difference. The temp is the
    cost: each one is another alloca, and in a loop body that grows the stack
    (#1685). Only the array's own storage may be allocated.
    """
    ir = _ritz1_ir(
        tmp_path,
        PRELUDE
        + """\
pub fn main() -> i32
    let a: [2]Point = [Point { x: 1, y: 2 }, Point { x: 3, y: 4 }]
    var p: Poly = Poly { n: 3, pts: [Point { x: 1, y: 2 }, Point { x: 3, y: 4 }, Point { x: 5, y: 6 }], tag: 9 }
    a[1].x + p.pts[2].y
""",
    )
    main_ir = ir[ir.index("define i32 @main") :]
    assert re.search(r"alloca %Point\b", main_ir) is None, main_ir


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, PRELUDE + PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_struct_lit_in_array(ritz1_bin, tmp_path, name):  # noqa: F811
    """ritz1 rejected or mis-stored literals nested in literals (#1608)."""
    assert _run("ritz1", tmp_path, name, PRELUDE + PROGRAMS[name]) == EXPECTED
