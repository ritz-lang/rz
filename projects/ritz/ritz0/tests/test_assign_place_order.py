"""AGAST #1740: `place = v` evaluates the place, then `v`, on every compiler.

§13.6 (LARB R61): "The place is evaluated before the value: `a[i] = v`
evaluates `a`, then `i`, then `v`, left to right as everywhere else."  R61
measured index places only.  Member and deref places split the compilers:

    lp(@s).x = r()           ritz0 ran r() first; ritz1 lp() first
    *li(@x) = r()            both ran r() first
    g[idx(1)] = rin()        both ran rin() first (`*g.index_mut(k) = v`)
    ps[idx(0)].inn.v = r()   ritz0 ran r(), then idx() TWICE

so `bump_o(p, @o).big = *p` exited 7 on ritz0 and 8 on ritz1.  Every place
form now runs its calls first, once each, left to right, then the value.
AGAST #3665 widened §13.6 to say so for every place.

Each program records its calls as decimal digits in `seq`: 1 for a call in
the place, 3 for an `index_mut` / `deref_mut` the place runs, 2 for the
value, 4 for `index_set`.  The expected `seq` is the order §13.6 gives.
"""

import pytest

from test_ritz1_array_pointer_index import COMPILERS, run_with  # noqa: F401 (fixture)

pytestmark = pytest.mark.batched

_DECLS = """\
var seq: i32 = 0

struct In
    v: i32

struct S
    x: i32
    arr: [3]i32
    inn: In

impl S
    fn me(self: *S) -> *S
        seq = seq * 10 + 1
        return self

fn lp(p: *S) -> *S
    seq = seq * 10 + 1
    return p

fn li(p: *i32) -> *i32
    seq = seq * 10 + 1
    return p

fn la(p: *[3]i32) -> *[3]i32
    seq = seq * 10 + 1
    return p

fn idx(i: i64) -> i64
    seq = seq * 10 + 1
    return i

fn r() -> i32
    seq = seq * 10 + 2
    return 5

fn rin() -> In
    seq = seq * 10 + 2
    return In { v: 5 }

struct Grid
    cells: [2]In

impl Index for Grid
    fn index(self: @Grid, key: i64) -> @In
        @self.cells[key]

impl IndexMut for Grid
    fn index_mut(self: @&Grid, key: i64) -> @&In
        seq = seq * 10 + 3
        @&self.cells[key]

struct Keyed
    cells: [2]In

impl Index for Keyed
    fn index(self: @Keyed, key: i64) -> @In
        @self.cells[key]

impl IndexSet for Keyed
    fn index_set(self: @&Keyed, key: i64, value: In)
        seq = seq * 10 + 4
        self.cells[key] = value

struct W
    inn: In

impl Deref for W
    fn deref(self: @W) -> @In
        @self.inn

impl DerefMut for W
    fn deref_mut(self: @&W) -> @&In
        seq = seq * 10 + 3
        @&self.inn

fn rs() -> S
    seq = seq * 10 + 2
    var t: S
    t.x = 5
    return t

pub fn main() -> i32
    var s: S
    var x: i32 = 0
    var a: [3]i32
    var ps: [2]*S = [@s, @s]
    var g: Grid
    var w: W
    var kd: Keyed
    let o: Option<i32> = Some(1)
"""

# name: (statement, expected seq, the slot it wrote, which must read 5)
CASES = {
    # A field of a call's `*S`: the ticket's `bump_o(p, @o).big = *p`.
    "member_of_call": ("lp(@s).x = r()", 12, "s.x"),
    "member_of_method": ("s.me().x = r()", 12, "s.x"),
    "nested_member_of_call": ("lp(@s).inn.v = r()", 12, "s.inn.v"),
    "struct_member_of_call": ("lp(@s).inn = rin()", 12, "s.inn.v"),
    # A field of an element: the index's call once, then the value.
    "member_of_element": ("ps[idx(0)].x = r()", 12, "s.x"),
    "nested_member_of_element": ("ps[idx(0)].inn.v = r()", 12, "s.inn.v"),
    # Through a call's pointer.
    "deref_call": ("*li(@x) = r()", 12, "x"),
    "deref_struct_call": ("*lp(@s) = rs()", 12, "s.x"),
    # Through `IndexMut` / `DerefMut` (§7.7, §7.8), which record a 3: the
    # index, then `index_mut` / `deref_mut`, then the value.
    "index_mut_element": ("g[idx(1)] = rin()", 132, "g.cells[1].v"),
    "index_mut_member": ("g[idx(1)].v = r()", 132, "g.cells[1].v"),
    "deref_mut_member": ("w.v = r()", 32, "w.inn.v"),
    # `index_set(@&m, k, v)` takes `v` as an argument, so it runs last (4).
    "index_set_element": ("kd[idx(1)] = rin()", 124, "kd.cells[1].v"),
    # An assignment as a match arm's value: ritz0 lowers it apart.
    "arm_member_of_call": ("match o\n        Some(v) => lp(@s).x = r()\n        None => s.x = 0",
                           12, "s.x"),
    "arm_deref_call": ("match o\n        Some(v) => *li(@x) = r()\n        None => x = 0", 12, "x"),
    # Index places (R61 already): guards that the member and deref fixes
    # leave them alone.
    "call_index": ("la(@a)[1] = r()", 12, "a[1]"),
    "index_call": ("a[idx(1)] = r()", 12, "a[1]"),
    "member_of_call_index_call": ("lp(@s).arr[idx(1)] = r()", 112, "s.arr[1]"),
}


def _program(stmt: str, slot: str) -> str:
    # 10 when the slot holds 5 (the store landed); seq rides on top, mod 256.
    return (_DECLS + f"    {stmt}\n    if {slot} != 5\n        return 1\n"
            "    return seq % 256\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_place_is_evaluated_before_the_value(run_with, name, compiler):  # noqa: F811
    stmt, want, slot = CASES[name]
    got = run_with(compiler, name, _program(stmt, slot))
    assert got != 1, f"{stmt!r} did not store 5 into {slot}"
    assert got == want % 256, (
        f"{stmt!r}: calls ran in order {got}, §13.6 says {want} "
        "(1 = a call in the place, 3 = index_mut / deref_mut, 2 = the value)")
