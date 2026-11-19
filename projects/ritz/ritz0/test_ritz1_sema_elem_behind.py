"""AGAST #4290: an element behind a pointer to an array, typed by Sema's one typer.

THE CHANGE

#4259 made sema_elem_ty (sema_type.ritz) Sema's one `x[i]` element typer:
SemaVar.index_elem plus its N-D shape, a row of an N-D array, the leaf of a
full-rank index.  Three readers of an array's element still kept their own:

- ref_check's rs_behind typed `*p` of a `*[N]T` from RsNote.arr_elem, which a
  plane pointer `*[N][M]T` (#2570) never had: `(*p)[i]` of one was untyped.
  It reads index_elem and the shape now, as sema_elem_ty does, and rs_ty's
  `p[i]` reads it too, so `@p[i]` / `@(*p)[i]` of a plane is a row (an `@`
  to an array), not "one value".  RsNote.arr_elem is gone.
- ref_ty_in indexed a `*[N][M]T` plane's row (#4259) but not a 1-D `*[N]T`'s
  element, nor an `@[N][M]T` plane's row (the emitter's LocalVar image keeps
  a plane's shape only for a `*`; Sema's ref_behind takes SemaVar's): so
  `let s = p[i]` of a Drop element behind `p: @[N]D` or `*[N]D` moved it out
  of a reference unrefused, and `(*p)[i][j].f = v` through an `@[N][M]S` was
  no write through an `@T`.
- the slot rules' sema_named_elem / sema_index_slot kept their own array
  branches; they take sema_arr_elem's element now (sx_arr_slot), with their
  diagnostics as they were (test_ritz1_sema_literal_slot.py,
  test_ritz1_sema_narrowing.py).

THE TESTS

Both ritz1 compilers, each against ritz0's verdict on the same program: the
moves ritz0 refuses, the plane writes it refuses, and rows of a plane it lets
index.  Lowering an index through an `@` / `@&` plane is the emitter's
(AGAST #4313).
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

MOVES = """\
struct D
    n: i32

impl Drop for D
    fn drop(self:&)
        self.n = 0

fn plane_deref(p: *[2][3]D) -> i32
    let s = (*p)[1][2]
    s.n

fn plane_idx(p: *[2][3]D) -> i32
    let s = p[1][2]
    s.n

fn one_ref(p: @[3]D) -> i32
    let s = p[1]
    s.n

fn one_deref(p: @[3]D) -> i32
    let s = (*p)[1]
    s.n

fn one_ptr(p: *[3]D) -> i32
    let s = p[1]
    s.n

fn one_local(a: [3]D) -> i32
    let q: @[3]D = @a
    let s = q[2]
    s.n

fn main() -> i32
    0
"""

MOVE_OUT = "cannot move out of a reference"

# ritz0 refuses each (`Ownership error: main.ritz:L:C: cannot move ...`).
MOVES_WANTED = [("9:14", MOVE_OUT), ("13:13", MOVE_OUT), ("17:13", MOVE_OUT),
                ("21:14", MOVE_OUT), ("25:13", MOVE_OUT), ("30:13", MOVE_OUT)]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_drop_element_behind_an_array_pointer_is_not_moved_out(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_elem_behind_moves", MOVES)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == MOVES_WANTED, f"{compiler}:\n{out}"


PLANE_WRITE = """\
struct D
    n: i32

fn plane_store(p: @[2][3]D)
    (*p)[1][2].n = 4

fn one_store(p: @[3]D)
    (*p)[1].n = 4

fn main() -> i32
    0
"""

READ_ONLY = "cannot write through an `@T`: make it `@&T`"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_write_through_an_at_plane_is_refused(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_elem_behind_write", PLANE_WRITE)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == [("5:6", READ_ONLY), ("8:6", READ_ONLY)], f"{compiler}:\n{out}"


# Controls: a row of a plane behind a pointer is an array, which indexes, and
# a Drop element read in place (its field, a method on it) moves nothing.
# ritz0 accepts all of it.  (Indexing through an `@[N][M]T` / `@&[N][M]T`
# plane is Sema-clean now, but ritz1's emitter doesn't lower it yet.)
ROWS = """\
struct D
    n: i32

impl D
    fn get(self: @D) -> i32
        self.n

impl Drop for D
    fn drop(self:&)
        self.n = 0

fn plane_row(p: *[2][3]i32) -> i32
    let r = @(*p)[1]
    let m = @&(*p)[0]
    m[1] = 2
    r[2] + m[1]

fn in_place(q: @[3]D, w: *[2][3]D) -> i32
    q[1].n + (*q)[2].get() + (*w)[1][2].get() + (*w)[0][1].n

fn main() -> i32
    var g: [2][3]i32
    g[1][2] = 7
    plane_row(@g) - 9
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_row_behind_a_plane_pointer_indexes(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_elem_behind_rows", ROWS)
    assert comp.returncode == 0 and ll.exists(), f"{compiler}:\n{comp.stdout + comp.stderr}"


# A row of an `@&[N][M]T` plane, `@p[i]` or `@(*p)[i]`, is an `@` to an array,
# which indexes (ritz0 accepts it): Sema no longer calls it one value.  What
# ritz1's emitter says of lowering it is its own business.
AT_PLANE_ROWS = """\
fn idx_row(p: @&[2][3]i32) -> i32
    let r = @p[1]
    r[2]

fn deref_row(p: @&[2][3]i32) -> i32
    let r = @&(*p)[1]
    r[2]

fn main() -> i32
    0
"""

NOT_A_BUFFER = "a reference is one value, not a buffer"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_row_of_an_at_plane_is_not_one_value(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, _, _ = _compile(compiler, tmp_path, "sema_elem_behind_at_rows", AT_PLANE_ROWS)
    out = comp.stdout + comp.stderr
    assert NOT_A_BUFFER not in out, f"{compiler}:\n{out}"


# A `self: @&D` method on an element behind an `@` pointer to an array is a
# write through the `@T`, a 1-D one's or a plane's, by `p[i]` or `(*p)[i]`:
# rs_ty types each receiver now, so each is refused, as ritz0 refuses each.
RECEIVERS = """\
struct D
    n: i32

impl D
    fn bump(self: @&D)
        self.n = self.n + 1

fn one(p: @[3]D)
    p[1].bump()

fn one_deref(p: @[3]D)
    (*p)[1].bump()

fn plane_deref(p: @[2][3]D)
    (*p)[1][2].bump()

fn plane_idx(p: @[2][3]D)
    p[1][2].bump()

fn main() -> i32
    0
"""

AT_INTO_MUT = "an `@T` doesn't fit an `@&T` slot: make it `@&T`"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_mut_receiver_behind_an_at_array_pointer_is_refused(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_elem_behind_receivers", RECEIVERS)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == [("9:5", AT_INTO_MUT), ("12:6", AT_INTO_MUT), ("15:6", AT_INTO_MUT),
                     ("18:5", AT_INTO_MUT)], f"{compiler}:\n{out}"
