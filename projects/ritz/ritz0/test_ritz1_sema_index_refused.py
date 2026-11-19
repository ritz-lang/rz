"""AGAST #3893: ritz1's index refusals run on Sema, before emission (#1816).

THE CHANGE

index_through.ritz refused, mid-lowering on EmitterState, what has nothing to
index or no pointer to follow (LANGUAGE_SPEC §7.8, LARB R9):

- index_refused's reference arm: `p[i]` with `p` an `@T` / `@&T` (an inferred
  `let p = @x` too, #2445 / #3079) whose T is no array, Vec, Span or String;
- element_refused: `x[i][j]` with `x[i]` a scalar or a struct without `Index`;
- deref_value_refused: `*v` with `v` a struct or sized scalar by value (and
  now as a `.`'s or method's receiver, `(*v).f`, where the emitter said only
  "cannot emit"; ritz0 says NOT_A_POINTER there too);
- deref_pointee_refused: `(*p)[i]` with `p` a `*T` to such a T;
- through_whole_array_refused: `p[i] = b` with `p` a `*[N]T` and `b` an array.

They are semantic checks, so they run from sema_walk now (index_refuse.ritz),
in the same words at the same places, and the emitter only lowers.  Its
scalar_local_refused went too: index_scalar_check (#3755) already refuses that
on Sema.  through_slice_refused stays: "isn't lowered by ritz1" is a lowering
limit, like frame_limit's, not a rule of the language.

THE TESTS

One program, both ritz1 compilers: each refusal, a `:&` integer's `*h` and a
bare `self:&`'s `*self` (no value: not refused), a scalar element of a
`*[N]T` and of a local `[N]T` indexed again, then a fn whose frame is over the stack, frame_limit's
error, which stays on the emitter: it is no longer printed.  Before the move
it was, and the receivers' errors were "cannot emit".  The rules' own rows are
test_index_through_reference.py's, test_index_not_indexable.py's,
test_ritz1_array_pointer_index.py's and test_ritz1_scalar_index.py's.
"""

import re

import pytest

from test_ref_into_value import _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

PROGRAM = """\
import ritzlib.gvec

struct S
    x: i32

impl S
    fn get(self: @S) -> i32
        self.x

    fn copy(self:&) -> S
        *self

fn not_buffer(p: @i32) -> i32
    return p[1]

fn inferred_ref() -> i32
    var x: i32 = 3
    let p = @x
    p[0]

fn element(v: *Vec<i32>, w: [3]u8) -> i32
    let a: i32 = v[0][1]
    w[0][1] as i32

fn deref_value(s: S, n: i32) -> S
    let a: i32 = *n
    *s

fn deref_pointee(p: *u8, q: *i32) -> i32
    let a: i32 = (*p)[0] as i32
    (*q)[0]

fn whole(p: *[3]i32, b: [3]i32)
    p[0] = b

fn store_ref(p: @&i32)
    p[0] = 1

fn receiver(s: S) -> i32
    (*s).x

fn method(s: S) -> i32
    (*s).get()

fn lent(h:& i32) -> i32
    *h = 4
    *h

fn view(p: *[3]i32) -> i32
    p[0][1]

fn local() -> i32
    var a: [3]i32
    a[0][1]

fn big() -> i32
    var big: [16777216]u8
    big[0] = 1
    big[0] as i32

fn main() -> i32
    0
"""

NOT_A_BUFFER = "a reference is one value, not a buffer: `[]` needs an array, Vec, Span or String behind it"
NOT_A_POINTER = "`*x` needs `x` to be a pointer or a reference: this one is a value"


def _needs_index(ty):
    return f"`{ty}` can't be indexed: it doesn't implement `Index` (§7.8)"


WANTED = [
    ("14:12", NOT_A_BUFFER),
    ("19:5", NOT_A_BUFFER),
    ("22:22", _needs_index("i32")),
    ("23:9", _needs_index("u8")),
    ("26:18", NOT_A_POINTER),
    ("27:5", NOT_A_POINTER),
    ("30:22", _needs_index("u8")),
    ("31:9", _needs_index("i32")),
    ("34:5", "`p[i]` is one element of the array behind `p`, not the whole array: `*p = a` stores the array"),
    ("37:5", NOT_A_BUFFER),
    ("40:6", NOT_A_POINTER),
    ("43:6", NOT_A_POINTER),
    ("50:9", _needs_index("i32")),
    ("54:9", _needs_index("i32")),
]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_index_refusals_stop_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_index_refused", PROGRAM)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    assert "stack frame" not in out, f"{compiler}: the emitter ran:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): error: (.*)", out)
    assert found == WANTED, f"{compiler}:\n{out}"


# A pointer to an N-D array is a plane pointer (#2570): `p[i]` is a row, so
# `p[i][j]` indexes it.  It has no `p#` view, as a `*[N]T` has, and isn't refused.
PLANE = """\
fn put(p: *[2][3]i32, r: [3]i32) -> i32
    p[1][2]

fn get(q:& *[2][3]i32) -> i32
    q[1][2]

fn main() -> i32
    var g: [2][3]i32
    var r: [3]i32 = [1, 2, 3]
    let p: *[2][3]i32 = @g
    var pp: *[2][3]i32 = @g
    put(p, r) + get(@&pp)
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_plane_pointer_indexes_a_row(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_index_plane", PLANE)
    assert comp.returncode == 0 and ll.exists(), f"{compiler}:\n{comp.stdout + comp.stderr}"
