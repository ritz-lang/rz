"""AGAST #2331, LARB R9: `*p` is a place, so `(*p)[i]` is element i, and means `p[i]`.

    fn f(p: *[3]i32) -> i32
        return (*p)[1]      # ritz0 "Cannot index type: [3 x i32]"

in every position: read, store, `+=`, `@`, `@&`, `.f`.  Writes through `@[N]T` are
§3.2's located error, as for `p[i]`.  It's also the only spelling one pointer level
further out, where `q[1]` is a raw buffer (`**`) or a located error (`@*`, #2440):

    fn f(q: @*[3]i32) -> i32
        return (*q)[1]      # ritz1 and selfhosted 0, SILENT

and the same over a Vec, `q: @*Vec<i32>` or `**Vec<i32>` (ritz0 failed at clang,
ritz1 and selfhosted read the wrong word).  One row per base kind and position:
each can go wrong on its own path.  `(*p)[i]` through one level of Vec, Span and
String is #2440's, in test_index_through_reference.py.
"""

import pytest

import ref_rules
import test_ritz1_for_header as for_header

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The parameter's type around `[3]T`, how main passes `a`, and whether a write
# reaches the array.  The `*`-out kinds hold `q: *[3]T = @a` and pass that.
KINDS = {
    "pointer": ("*", "@a", True),
    "reference": ("@", "@a", False),
    "mut_reference": ("@&", "@&a", True),
    "ptr_ptr": ("**", "@q", True),
    "ref_ptr": ("@*", "@q", True),
    "mut_ref_ptr": ("@&*", "@&q", True),
}

S = "struct S\n    x: i32\n    y: i32\n\n"

# Each position's body for `f`, what `f` returns, then what main returns of `a`.
# `a` is [10, 20, 30] (as `.y` for the struct rows); 20 back means the element.
POSITIONS = {
    "read": ("i32", "    return (*p)[1]\n", "f(ARG)"),
    "read_var": ("i32", "    return (*p)[i]\n", "f(ARG)"),
    "store": ("i32", "    (*p)[1] = 7\n    return 0\n", "f(ARG) + a[1] + 13"),
    "store_var": ("i32", "    (*p)[i] = 7\n    return 0\n", "f(ARG) + a[1] + 13"),
    "compound": ("i32", "    (*p)[1] += 7\n    return 0\n", "f(ARG) + a[1] - 7"),
    "address": ("i32", "    let e: *i32 = @(*p)[1]\n    return *e\n", "f(ARG)"),
    "mut_address": ("i32", "    let e: @&i32 = @&(*p)[1]\n    *e = 7\n    return 0\n", "f(ARG) + a[1] + 13"),
    "field": ("S", "    return (*p)[1].y\n", "f(ARG)"),
    "field_store": ("S", "    (*p)[1].y = 7\n    return 0\n", "f(ARG) + a[1].y + 13"),
    "field_address": ("S", "    let e: *i32 = @(*p)[1].y\n    return *e\n", "f(ARG)"),
}
WRITES = ("store", "store_var", "compound", "mut_address", "field_store")


def _program(kind: str, position: str) -> str:
    around, arg, _ = KINDS[kind]
    elem, body, ret = POSITIONS[position]
    if elem == "S":
        fill = "    var a: [3]S\n    a[0].y = 10\n    a[1].y = 20\n    a[2].y = 30\n"
    else:
        fill = "    var a: [3]i32 = [10, 20, 30]\n"
    if arg.endswith("q"):
        fill += f"    var q: *[3]{elem} = @a\n"
    return (S + f"fn f(p: {around}[3]{elem}, i: i32) -> i32\n{body}\n"
            + f"pub fn main() -> i32\n{fill}    return {ret.replace('ARG', arg + ', 1')}\n")


ROWS = [(k, p) for k in KINDS for p in POSITIONS if KINDS[k][2] or p not in WRITES]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind,position", ROWS)
def test_a_deref_index_is_element_i(run_with, kind, position, compiler):
    assert run_with(compiler, f"{kind}_{position}", _program(kind, position)) == 20


# §3.2: an `@[3]T` is read-only, at the place, whichever spelling reaches it.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("position", WRITES)
def test_a_write_through_a_shared_array_is_refused(compile_with, position, compiler):
    comp, _, _ = compile_with(compiler, f"shared_{position}", _program("reference", position))
    want = ref_rules.BORROW_THROUGH_SHARED if position == "mut_address" else ref_rules.WRITE_THROUGH_SHARED
    assert comp.returncode != 0
    assert want in comp.stdout + comp.stderr


# One level out over a Vec: `*q` is the Vec, `(*q).data` its buffer.
VEC_KINDS = {"ptr_ptr": ("**", "@p"), "ref_ptr": ("@*", "@p"), "mut_ref_ptr": ("@&*", "@&p")}
VEC_POSITIONS = {
    "read": ("    return (*q)[1]\n", "f(ARG)"),
    "store": ("    (*q)[1] = 7\n    return 0\n", "f(ARG) + *(v.data + 1) + 13"),
    "compound": ("    (*q)[1] += 7\n    return 0\n", "f(ARG) + *(v.data + 1) - 7"),
    "address": ("    let e: *i32 = @(*q)[1]\n    return *e\n", "f(ARG)"),
    # By hand: `(*q).data` is a `*i32`, so `+ 1` steps one i32 (ritz1 stepped a byte).
    "by_hand": ("    return *((*q).data + 1)\n", "f(ARG)"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("position", sorted(VEC_POSITIONS))
@pytest.mark.parametrize("kind", sorted(VEC_KINDS))
def test_a_deref_index_one_level_out_over_a_vec(run_with, kind, position, compiler):
    around, arg = VEC_KINDS[kind]
    body, ret = VEC_POSITIONS[position]
    program = (f"import ritzlib.gvec\n\nfn f(q: {around}Vec<i32>) -> i32\n{body}\n"
               "pub fn main() -> i32\n    var v: Vec<i32> = vec_new<i32>()\n"
               "    v.push(10)\n    v.push(20)\n    v.push(30)\n    var p: *Vec<i32> = @v\n"
               f"    return {ret.replace('ARG', arg)}\n")
    assert run_with(compiler, f"vec_{kind}_{position}", program) == 20
