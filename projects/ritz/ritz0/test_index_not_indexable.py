"""AGAST #2452: `[]` on a value that holds no elements is one located error.

    var sv: Vec<S> = ...      # S a plain struct
    sv[0][1]                  # sv[0] is one S: there is nothing to index

    var v: Vec<i32> = ...
    (*v)[1]                   # v is a Vec, not a pointer: there is nothing to deref

On origin/main cd81af88 ritz0 refused `sv[0][1]` with §7.8's located error, but
said "Cannot index type: i32" unlocated for `v[0][1]` on a `Vec<i32>`, and raised a
Python AttributeError or ValueError for `(*v)[1]`.  ritz1 and ritz1_selfhosted
failed at clang, said "unhandled EXPR_MEMBER", or compiled them.

Now each is one located error on all three, in the shape of #2440's NOT_A_BUFFER:
one string, said by ritz0 and ritz1 alike, at one place.

AGAST #2885 does the same for a `*x` outside a `[]` (`*n` on an i32, `*v = ...`,
`@*v` on a Vec value).

    an element with nothing to index    index_rules.needs_index, at the second `[`
                                        (§7.8's words; ritz1: struct_index.ritz)
    `*v` on a struct by value           array_rules.NOT_A_POINTER, at the `*`
                                        (ritz1: index_through.ritz)

ritz1 had no record of where a `[` is, so an index's errors named the start of its
base; the parser now keeps it (Expr.bracket).
"""

import pytest

import array_rules
import batching
import index_rules
import test_ritz1_for_header as for_header
from test_ritz1_for_header import _new

pytestmark = pytest.mark.batched

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The element is a struct without `Index`, or a scalar: §7.8's words (index_rules.py).
NEEDS_INDEX = index_rules.needs_index
NOT_A_POINTER = array_rules.NOT_A_POINTER

HEADER = """\
import ritzlib.gvec
import ritzlib.string

struct S
    x: i32
    y: i32

"""

STRUCTS = ("    var sv: Vec<S> = vec_new<S>()\n"
           "    sv.push(S { x: 1, y: 2 })\n    sv.push(S { x: 3, y: 20 })\n")

# Each body's first line is the offending one; `@` marks the column the error names:
# the `[` of the index that has nothing to index, as §7.8's errors are.
NOT_INDEXABLES = {
    "vec_element_read": ("S", STRUCTS, "    return sv[0]@[1].x\n"),
    "vec_element_store": ("S", STRUCTS, "    sv[0]@[1] = S { x: 0, y: 0 }\n    return 0\n"),
    "vec_scalar_element": ("i32", _new("i32", (10, 20, 30)), "    return v[0]@[1]\n"),
    "through_pointer": ("S", STRUCTS + "    let p: *Vec<S> = @sv\n", "    return p[0]@[1].x\n"),
    "array_element": ("S", "    var a: [2]S\n", "    return a[0]@[1].x\n"),
    "array_scalar_element": ("i32", "    var a: [3]i32 = [10, 20, 30]\n", "    return a[0]@[1]\n"),
    "struct_local": ("S", "    var s: S = S { x: 1, y: 2 }\n", "    return s@[1].x\n"),
    # AGAST #2886: a scalar local.  ritz0 said "Cannot index type: i32" unlocated;
    # ritz1 and ritz1_selfhosted compiled it.
    "scalar_local": ("i32", "    var n: i32 = 5\n", "    return n@[1]\n"),
    "scalar_local_store": ("i32", "    var n: i32 = 5\n", "    n@[1] = 7\n    return n\n"),
    "scalar_local_add": ("i32", "    var n: i32 = 5\n", "    n@[1] += 7\n    return n\n"),
}

# `@` marks the `*`.
NOT_POINTERS = {
    "vec_value_read": (_new("i32", (10, 20, 30)), "    return (@*v)[1]\n"),
    "vec_value_store": (_new("i32", (10, 20, 30)), "    (@*v)[1] = 7\n    return 0\n"),
    "string_value_read": ("    var v: String\n    v.data = vec_new<u8>()\n    v.data.push(10)\n",
                          "    return (@*v)[0] as i32\n"),
}


def _located(compile_with, compiler, name, setup, body, message, mark="@"):
    marked = body.splitlines()[0]
    column = 1 + marked.index(mark)
    line = 1 + (HEADER + "pub fn main() -> i32\n" + setup).count("\n")
    program = f"{HEADER}pub fn main() -> i32\n{setup}{body.replace(mark, '', 1)}"
    batch = getattr(compile_with, "batch_compile", None)
    got = batching.refused(compiler, program, batch) if batch else None  # AGAST #2806
    if got is not None:
        out = got[0]
    else:
        comp, _, _ = compile_with(compiler, name, program)
        assert comp.returncode != 0, f"{compiler} took {name}"
        out = comp.stdout + comp.stderr
    assert message in out, out[-1000:]
    assert f"main.ritz:{line}:{column}:" in out, out[-1000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_INDEXABLES))
def test_an_element_that_holds_nothing_is_not_indexable(compile_with, name, compiler):
    elem, setup, body = NOT_INDEXABLES[name]
    _located(compile_with, compiler, name, setup, body, NEEDS_INDEX(elem))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_POINTERS))
def test_a_value_is_not_a_pointer(compile_with, name, compiler):
    setup, body = NOT_POINTERS[name]
    _located(compile_with, compiler, name, setup, body, NOT_A_POINTER)


# AGAST #2885: the same `*x` outside a `[]`.  ritz0 raised an unlocated Python
# ValueError ("Cannot dereference non-pointer") from each of its three deref sites
# (a read, a `*x = ...` store, an `@*x`); ritz1 and ritz1_selfhosted compiled them.
# `^` marks the `*`.
INT = "    var n: i32 = 5\n"
VEC = _new("i32", (10, 20, 30))
BARE_DEREFS = {
    "int_read": (INT, "    return ^*n\n"),
    "int_store": (INT, "    ^*n = 7\n    return n\n"),
    "vec_read": (VEC, "    let w: Vec<i32> = ^*v\n    return w[0]\n"),
    "vec_store": (VEC, "    ^*v = vec_new<i32>()\n    return 0\n"),
    "vec_address": (VEC, "    let p: *Vec<i32> = @^*v\n    return (*p)[0]\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(BARE_DEREFS))
def test_a_bare_deref_of_a_value_is_not_a_pointer(compile_with, name, compiler):
    setup, body = BARE_DEREFS[name]
    _located(compile_with, compiler, name, setup, body, NOT_A_POINTER, mark="^")


# The legal neighbour: `*p` of a pointer to an int, read and stored.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_bare_deref_of_a_pointer_still_runs(run_with, compiler):
    program = f"{HEADER}pub fn main() -> i32\n{INT}    let p: *i32 = @n\n    *p = *p + 10\n    return n\n"
    assert run_with(compiler, "int_pointer", program) == 15


# `*h` of an integer borrow reads as the caller's int (#2045): it isn't a value.
# ritz1 compiles it, then loads through the int (#2971).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_bare_deref_of_a_borrow_is_not_refused(compile_with, compiler):
    program = (f"{HEADER}fn f(h:& i32) -> i32\n    return *h + 1\n\n"
               f"pub fn main() -> i32\n{INT}    return f(@&n)\n")
    comp, _, _ = compile_with(compiler, "int_borrow", program)
    assert comp.returncode == 0, (comp.stdout + comp.stderr)[-1000:]


# The legal neighbours: an element that is indexable, and a field of a struct element.
LEGAL = {
    "vec_of_vec": (_new("i32", (10, 20, 30)) +
                   "    var vv: Vec<Vec<i32>> = vec_new<Vec<i32>>()\n    vv.push(v)\n",
                   "    return vv[0][1]\n", 20),
    "vec_element_field": (STRUCTS, "    return sv[1].y\n", 20),
    "array_of_arrays": ("    var g: [2][3]i32\n    g[1][2] = 20\n", "    return g[1][2]\n", 20),
    # A `*[3]i32` element indexes the array, not a raw buffer of arrays (#2968).
    "array_pointer_element": ("    var g: [2][3]i32\n    g[0][1] = 20\n    var pg: [1]*[3]i32\n"
                              "    pg[0] = @g[0]\n", "    return pg[0][1]\n", 20),
    "deref_of_pointer": (_new("i32", (10, 20, 30)) + "    let p: *Vec<i32> = @v\n",
                         "    return (*p)[1]\n", 20),
    "deref_of_inferred_ref": (_new("i32", (10, 20, 30)) + "    let p = @v\n",
                              "    return (*p)[1]\n", 20),
}

# An element that's a pointer is a raw buffer: `pv[0][1]` is `*(pv[0] + 1)`.
POINTERS = ("    var a: [2]S\n    a[1].x = 20\n    var pv: Vec<*S> = vec_new<*S>()\n"
            "    pv.push(@a[0])\n")
POINTER_ELEMENT = "    let s: S = pv[0][1]\n    return s.x\n"

# AGAST #2887: each place `pv[0][1]` is, element 1 of the buffer `pv[0]` points at.
# ritz1 took the element for an i64 (clang refused it), and `.x` was "unhandled
# EXPR_MEMBER".  `pv[0]` is evaluated once (`pv[i()][1]` calls `i` once).
# ritz0 refused `.f =` and `+=` on it, read `@` as the wrong place, and evaluated
# `pv[i]` twice (#2968).
RAW_ELEMENTS = {
    "copy": POINTER_ELEMENT,
    "field": "    return pv[0][1].x\n",
    "field_store": "    pv[0][1].y = 7\n    return a[1].y + 13\n",
    "store": "    pv[0][1] = S { x: 5, y: 15 }\n    return a[1].x + a[1].y\n",
    "field_add": "    pv[0][1].x += 1\n    return a[1].x - 1\n",
    "address": "    let q: *S = @pv[0][1]\n    return q.x\n",
    "index_once": "    let s: S = pv[once(@n)][1]\n    return s.x + n - 1\n",
}
ONCE = "fn once(n: *i32) -> i64\n    *n = *n + 1\n    0\n\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RAW_ELEMENTS))
def test_an_element_that_is_a_pointer_indexes_raw(run_with, name, compiler):
    program = (f"{HEADER}{ONCE}pub fn main() -> i32\n    var n: i32 = 0\n"
               f"{POINTERS}{RAW_ELEMENTS[name]}")
    assert run_with(compiler, name, program) == 20


# Whatever ritz1 makes of it, it isn't this rule's error.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_element_that_is_a_pointer_is_not_refused(compile_with, compiler):
    program = f"{HEADER}pub fn main() -> i32\n{POINTERS}{POINTER_ELEMENT}"
    comp, _, _ = compile_with(compiler, "pointer_element", program)
    assert NEEDS_INDEX("S") not in comp.stdout + comp.stderr


# ritz1 reads garbage through a `*[N]T` element, silently (#2995).
def _legal_cases():
    for name in sorted(LEGAL):
        for c in COMPILERS:
            marks = [pytest.mark.xfail(strict=True, reason="#2995")] \
                if name == "array_pointer_element" and c != "ritz0" else []
            yield pytest.param(name, c, marks=marks, id=f"{name}-{c}")


@pytest.mark.integration
@pytest.mark.parametrize("name,compiler", list(_legal_cases()))
def test_the_legal_neighbours_still_run(run_with, name, compiler):
    setup, body, want = LEGAL[name]
    assert run_with(compiler, name, f"{HEADER}pub fn main() -> i32\n{setup}{body}") == want


# A `h:& T` borrow (#2045) reads as its referent, but `*h` is still a deref of the
# pointer underneath, so `(*h)[i]` indexes the Vec.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_borrow_derefs_to_its_vec(run_with, compiler):
    program = (f"{HEADER}fn f(h:& Vec<i32>) -> i32\n    return (*h)[1]\n\n"
               f"pub fn main() -> i32\n{_new('i32', (10, 20, 30))}    return f(@&v)\n")
    assert run_with(compiler, "borrow", program) == 20


# An element that implements `Index` (§7.8) isn't one of these: `lv[0][1]` reads
# through it, as `*lv[0].index(1)` (#2884).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_element_with_index_reads_through_it(run_with, compiler):
    program = f"""\
{HEADER}struct L
    n: [2]i64

impl Index for L
    fn index(self: @L, key: i64) -> @i64
        @self.n[key]

pub fn main() -> i32
    var l: L
    l.n[0] = 10
    l.n[1] = 20
    var lv: Vec<L> = vec_new<L>()
    lv.push(l)
    return lv[0][1] as i32
"""
    assert run_with(compiler, "index_element", program) == 20
