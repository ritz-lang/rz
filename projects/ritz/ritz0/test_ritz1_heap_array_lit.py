"""AGAST #3986: `heap [a, b]`, an array-literal operand, on ritz1.

ritz1 lowers `heap e` to ritzlib.memory's `__heap_new<T>(value: T) -> *T`
(ast_helpers.expr_heap); ritz0 mallocs the `[N]E` inline (_emit_heap_expr).
ritz1 refused `heap [P { .. }, P { .. }]` for three reasons, each pinned here
on its own, then together (test_heap_padded_size.py's `array` rows are the
padded-size canary):

- generic_infer bound no T from an array literal.  It now binds the `[N]E`
  ritz0 does (gi_array_lit_type): for `heap`, and since AGAST #4159 for an
  ordinary call's argument too, as ritz0 has since #3554 (`call_*`).  Since
  AGAST #4178 a nested literal binds `[N][M]E` (`call_nested`), and a by-value
  `[N][M]E` param takes a nested literal or fill.
- The instance's `let p: *T` at T = `[N]S` names S (monomorph, #2832), and
  the let bound any named `*X` as a `*S` struct pointer, so `*p = value`
  refused the array: "a whole array is not a value here".  `instance_store`.
- `-> *T` at T = `[N]E` recorded no `*[N]E` return (ret_ptr_array), so the
  caller's `let p = f<[N]E>(..)` was a `*arrN_E` struct pointer: `p[i]` had
  no element size and `p[i].f` was "unhandled EXPR_MEMBER".  `ret_ptr`.
  generic_infer typed no such `p[i]` either, so `size(p[0])` bound no T
  (AGAST #4182, `call_ptr_index`).
"""

import pytest
from test_borrow_param_ref_field import _compile
from test_ritz1_builtin_struct_shadow import _run_pkg
from test_ritz1_for_iterable import SELFHOSTED_BIN

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

HEAD = """\
import ritzlib.memory

struct P
    a: u8
    b: i64
    c: u8

fn put<T>(value: T) -> *T
    let p: *T = malloc(sizeof(T)) as *T
    *p = value
    p

fn size<T>(value: T) -> i64
    sizeof(T) as i64

fn corner(m: [2][2]i64) -> i64
    m[1][0]

"""

# name: main's body; each returns 0 when the heap block holds the value.
PROGRAMS = {
    # A by-value `[2]P` stored through the instance's `*T`.
    "instance_store": (
        "    let a: [2]P = [P { a: 1, b: 2, c: 3 }, P { a: 4, b: 55, c: 6 }]\n"
        "    let p = put<[2]P>(a)\n"
        "    if p[0].c != 3 or p[1].b != 55 or p[1].c != 6\n"
        "        return 1\n"
        "    0\n"
    ),
    # A scalar array: the store always worked; the result's `p[i]` didn't.
    "ret_ptr": (
        "    let a: [3]i32 = [5, 6, 7]\n"
        "    let p = put<[3]i32>(a)\n"
        "    p[1] = p[1] + 10\n"
        "    if p[0] != 5 or p[1] != 16 or p[2] != 7\n"
        "        return 1\n"
        "    0\n"
    ),
    # `heap` of a literal of structs: T is `[2]P`.
    "heap_structs": (
        "    let p = heap [P { a: 1, b: 2, c: 3 }, P { a: 4, b: 55, c: 6 }]\n"
        "    p[1].c = 9\n"
        "    if p[0].c != 3 or p[1].b != 55 or p[1].c != 9\n"
        "        return 1\n"
        "    0\n"
    ),
    # Integer literals are i64s, as ritz0's `heap 42` is a *i64: `[3]i64`.
    "heap_ints": (
        "    let p = heap [5, 6, 70000000000]\n"
        "    if p[0] != 5 or p[1] != 6 or p[2] != 70000000000\n"
        "        return 1\n"
        "    0\n"
    ),
    # AGAST #4159: an ordinary call's literal binds T as `heap`'s does.
    "call_put": (
        "    let p = put([5, 6])\n"
        "    if p[0] != 5 or p[1] != 6\n"
        "        return 1\n"
        "    0\n"
    ),
    # E is the first element's type, as ritz0's: `[2]i32` (8 bytes) from an
    # i32 first, `[2]i64` (16) from a literal first.
    "call_first_elem": (
        "    let x: i32 = 3\n"
        "    if size([x, 5]) != 8 or size([5, x]) != 16\n"
        "        return 1\n"
        "    0\n"
    ),
    # AGAST #4178: a nested literal is `[2][2]i64` (32 bytes), inferred or
    # written, as ritz0's ArrayLit rule recurses into the first element.
    "call_nested": (
        "    if size([ [1, 2], [3, 4] ]) != 32\n"
        "        return 1\n"
        "    if size<[2][2]i64>([ [1, 2], [3, 4] ]) != 32\n"
        "        return 2\n"
        "    let x: i32 = 3\n"
        "    if size([ [x, 5], [6, 7], [8, 9] ]) != 24\n"
        "        return 3\n"
        "    if corner([ [1, 2], [x as i64, 4] ]) != 3 or corner([ [7; 2]; 2]) != 7\n"
        "        return 4\n"
        "    0\n"
    ),
    # AGAST #4182: `p[i]` of a `-> *T` at T = `[N]E` is an E, so it binds a
    # T of its own, written (`put<[2]i32>`) or inferred (`put([x, 5])`).
    "call_ptr_index": (
        "    let x: i32 = 3\n"
        "    let p = put<[2]i32>([x, 5])\n"
        "    if p[1] != 5 or size(p[0]) != 4\n"
        "        return 1\n"
        "    let q = put([x, 5])\n"
        "    if q[0] != 3 or size(q[1]) != 4\n"
        "        return 2\n"
        "    let r = put<[2]P>([P { a: 1, b: 2, c: 3 }, P { a: 4, b: 5, c: 6 }])\n"
        "    if r[1].b != 5 or size(r[1]) != 24\n"
        "        return 3\n"
        "    0\n"
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_heap_array_holds_its_elements(tmp_path, compiler, name):
    program = HEAD + "pub fn main() -> i32\n" + PROGRAMS[name]
    assert _run_pkg(compiler, tmp_path, name, program) == 0

