#!/usr/bin/env python3
"""An array literal's length must be its slot's `N` (LANGUAGE_SPEC §3.3, LARB
ruling R42, AGAST #3315 / #3382).

`let a: [3]i64 = [1, 2]` used to zero-fill `a[2]`, and `[7; 2]` into a `[3]i64`
did the same: C's footgun (R20). Both are now an error at the literal, and so is
a longer one. `[0; N]` says the zero-fill out loud.

Every row runs on ritz0, ritz1 and ritz1_selfhosted (AGAST #3383). Before
#3383, ritz1 zero-filled or truncated a literal in a `let`, `var`, `const` or
struct literal, and refused one in the other slots only by accident ("unlowerable
expression", unlocated). ritz1 has no aggregate global initializer and no N-D
`const`, so it refuses those rows twice: this error, then that one.
"""

import pytest

from array_rules import literal_length
from test_ref_into_value import COMPILERS, _assert_refused, _ids, _main, _run

# AGAST #2806: each test's rows share one compile (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

PRELUDE = """\
pub fn memset(dest: *u8, c: u8, n: i64) -> *u8
    var i: i64 = 0
    while i < n
        *(dest + i) = c
        i = i + 1
    dest

struct R
    n: i32

"""

# Every slot §3.3 lists; `{L}` is a `[3]i64`-bound literal, `^` its start.
SLOTS = {
    "argument": "fn g(b: [3]i64) -> i32\n    0\n\nfn f() -> i32\n    g(^{L})\n",
    "method_argument": ("impl R\n    fn g(self: *R, b: [3]i64) -> i32\n        0\n\n"
                        "fn f(r: *R) -> i32\n    r.g(^{L})\n"),
    "let": "fn f() -> i32\n    let b: [3]i64 = ^{L}\n    0\n",
    "var": "fn f() -> i32\n    var b: [3]i64 = ^{L}\n    0\n",
    "assign": "fn f() -> i32\n    var b: [3]i64 = [0; 3]\n    b = ^{L}\n    0\n",
    "store_through": "fn f(p: *[3]i64) -> i32\n    *p = ^{L}\n    0\n",
    "global": "var G: [3]i64 = ^{L}\n\nfn f() -> i32\n    0\n",
    "const": "const G: [3]i64 = ^{L}\n\nfn f() -> i32\n    0\n",
    "global_assign": "var G: [3]i64\n\nfn f() -> i32\n    G = ^{L}\n    0\n",
    "field": "struct H\n    b: [3]i64\n\nfn f(h: *H) -> i32\n    h.b = ^{L}\n    0\n",
    "struct_literal": ("struct H\n    b: [3]i64\n\n"
                       "fn f() -> i32\n    var h: H = H { b: ^{L} }\n    0\n"),
    "return": "fn f() -> [3]i64\n    return ^{L}\n",
    "tail": "fn f() -> [3]i64\n    ^{L}\n",
    "element": "fn f() -> i32\n    var m: [1][3]i64 = [ ^{L}]\n    0\n",
}

# List and fill, shorter and longer: each is its own branch of the rule.
LITERALS = {
    "short_list": ("[1, 2]", 2),
    "long_list": ("[1, 2, 3, 4]", 4),
    "short_fill": ("[7; 2]", 2),
    "long_fill": ("[7; 4]", 4),
    "empty": ("[]", 0),
}


@pytest.mark.parametrize("slot", _ids(SLOTS))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_slot_refuses_a_short_literal(tmp_path, compiler, slot):
    src = PRELUDE + SLOTS[slot].replace("{L}", "[1, 2]")
    _assert_refused(compiler, tmp_path, slot, _main(src, "    0\n"), literal_length(2, "[3]i64"))


@pytest.mark.parametrize("literal", _ids(LITERALS))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_literal_of_the_wrong_length_is_refused(tmp_path, compiler, literal):
    text, n = LITERALS[literal]
    src = PRELUDE + SLOTS["let"].replace("{L}", text)
    _assert_refused(compiler, tmp_path, literal, _main(src, "    0\n"), literal_length(n, "[3]i64"))


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_inner_literal_is_judged_against_its_row(tmp_path, compiler):
    src = PRELUDE + "fn f() -> i32\n    var m: [2][3]i64 = [ [1, 2, 3], ^[4, 5]]\n    0\n"
    _assert_refused(compiler, tmp_path, "inner", _main(src, "    0\n"), literal_length(2, "[3]i64"))


@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_inner_literal_of_a_const_is_judged_against_its_row(tmp_path, compiler):
    src = PRELUDE + "const M: [2][3]i64 = [ [1, 2, 3], ^[4, 5]]\n\nfn f() -> i32\n    0\n"
    _assert_refused(compiler, tmp_path, "const_inner", _main(src, "    0\n"), literal_length(2, "[3]i64"))


@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_slots_alias_is_named_as_its_array(tmp_path, compiler):
    src = PRELUDE + "type Row = [3]i64\n\nfn f() -> i32\n    let b: Row = ^[1, 2]\n    0\n"
    _assert_refused(compiler, tmp_path, "alias", _main(src, "    0\n"), literal_length(2, "[3]i64"))


@pytest.mark.parametrize("compiler", COMPILERS)
def test_one_element_is_singular(tmp_path, compiler):
    src = PRELUDE + "fn f() -> i32\n    let b: [3]u8 = ^[1]\n    0\n"
    _assert_refused(compiler, tmp_path, "one", _main(src, "    0\n"), literal_length(1, "[3]u8"))
    assert literal_length(1, "[3]u8") == "an array literal of 1 element for a `[3]u8`"


# Was `test_array_literal_shorter_than_declared` in
# test/test_issue_slice_generic_siblings.ritz, which pinned the zero-fill.
@pytest.mark.parametrize("compiler", COMPILERS)
def test_the_old_zero_fill_corpus_row_is_refused(tmp_path, compiler):
    src = PRELUDE + "fn f() -> i32\n    let buf: [4]u8 = ^[1, 2]\n    0\n"
    _assert_refused(compiler, tmp_path, "corpus", _main(src, "    0\n"),
                    "an array literal of 2 elements for a `[4]u8`")


# The length fits: these still compile, and the values land.
FITS = {
    "list": "fn f() -> i32\n    let b: [3]i64 = [1, 2, 3]\n    b[2] as i32\n",
    "fill": "fn f() -> i32\n    let b: [3]i64 = [3; 3]\n    b[2] as i32\n",
    "untyped": "fn f() -> i32\n    let b = [1, 2, 3]\n    b[2] as i32\n",
    "const": "const G: [3]i64 = [1, 2, 3]\n\nfn f() -> i32\n    G[2] as i32\n",
    "nested": "fn f() -> i32\n    var m: [2][3]i64 = [ [0; 3], [1, 2, 3]]\n    m[1][2] as i32\n",
}


@pytest.mark.parametrize("name", _ids(FITS))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_literal_of_the_slots_length_fits(tmp_path, compiler, name):
    assert _run(compiler, tmp_path, name, _main(PRELUDE + FITS[name], "    f()\n")) == 3


# AGAST #3642: `*q = [..]` through a plane pointer `q = @&x[0]` (#2570) is
# judged against the plane's shape `[2][3]i64`, not its flat count 6. ritz1
# refused the good store, unlocated, and R42 never saw a wrong one.
PLANE = ("fn f() -> i32\n    var x: [2][2][3]i64 = [ [ [0; 3]; 2]; 2]\n    let q = @&x[0]\n"
         "    *q = {L}\n    x[0][1][2] as i32 - x[1][1][2] as i32\n")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_plane_store_through_a_pointer_fits(tmp_path, compiler):
    src = PRELUDE + PLANE.replace("{L}", "[ [1, 2, 3], [4, 5, 6]]")
    assert _run(compiler, tmp_path, "plane", _main(src, "    f()\n")) == 6



# The literal is built whole before it lands, so it reads the old plane; and a
# whole `[2][3]i64` local is copied through a plane pointer too.
PLANE_ALIAS = """\
fn swap(x: *[2][2][3]i64)
    let q = @&x[0]
    *q = [ [q[1][0], q[1][1], q[1][2]], [q[0][0], q[0][1], q[0][2]]]

fn fill(x: *[2][2][3]i64)
    var y: [2][3]i64 = [ [7; 3], [8; 3]]
    let r = @&x[1]
    *r = y

fn f() -> i32
    var x: [2][2][3]i64 = [ [ [1, 2, 3], [4, 5, 6]], [ [0; 3]; 2]]
    swap(@&x)
    fill(@&x)
    (x[0][1][2] * 10 + x[0][0][0] + x[1][1][0]) as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_plane_store_reads_the_old_plane(tmp_path, compiler):
    assert _run(compiler, tmp_path, "plane_alias", _main(PRELUDE + PLANE_ALIAS, "    f()\n")) == 42

PLANE_WRONG = {
    "outer": ("^[ [1, 2, 3]]", 1, "[2][3]i64"),
    "inner": ("[ [1, 2, 3], ^[4, 5]]", 2, "[3]i64"),
}


@pytest.mark.parametrize("which", _ids(PLANE_WRONG))
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_plane_store_of_the_wrong_length_is_refused(tmp_path, compiler, which):
    text, n, slot = PLANE_WRONG[which]
    src = PRELUDE + PLANE.replace("{L}", text)
    _assert_refused(compiler, tmp_path, which, _main(src, "    0\n"), literal_length(n, slot))
