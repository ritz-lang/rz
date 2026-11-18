"""AGAST #3986: `heap [a, b]`, an array-literal operand, on ritz1.

ritz1 lowers `heap e` to ritzlib.memory's `__heap_new<T>(value: T) -> *T`
(ast_helpers.expr_heap); ritz0 mallocs the `[N]E` inline (_emit_heap_expr).
ritz1 refused `heap [P { .. }, P { .. }]` for three reasons, each pinned here
on its own, then together (test_heap_padded_size.py's `array` rows are the
padded-size canary):

- generic_infer bound no T from an array literal.  For `heap` it now binds
  the `[N]E` ritz0 allocates (gi_heap_array_lit).  An ordinary call still
  binds none on ritz1, where ritz0 binds one since #3554: `refused` pins
  that gap (AGAST #4159).
- The instance's `let p: *T` at T = `[N]S` names S (monomorph, #2832), and
  the let bound any named `*X` as a `*S` struct pointer, so `*p = value`
  refused the array: "a whole array is not a value here".  `instance_store`.
- `-> *T` at T = `[N]E` recorded no `*[N]E` return (ret_ptr_array), so the
  caller's `let p = f<[N]E>(..)` was a `*arrN_E` struct pointer: `p[i]` had
  no element size and `p[i].f` was "unhandled EXPR_MEMBER".  `ret_ptr`.
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
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_heap_array_holds_its_elements(tmp_path, compiler, name):
    program = HEAD + "pub fn main() -> i32\n" + PROGRAMS[name]
    assert _run_pkg(compiler, tmp_path, name, program) == 0


# An ordinary call's array literal binds no T on ritz1 yet; ritz0 binds one
# since #3554.  Strict, so closing the gap flips these red (AGAST #4159).
REFUSED = HEAD + "pub fn main() -> i32\n    let p = put([1, 2])\n    0\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_ritz1_array_literal_binds_no_t_outside_heap(tmp_path, ritz1_bin, compiler):
    binary = {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}[compiler]
    comp, _, _ = _compile(compiler, binary, tmp_path, "refused", REFUSED)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert "can't infer `T` for `put`" in out, out
