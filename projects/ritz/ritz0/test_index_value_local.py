"""AGAST #2442, LARB R9: an element of a Vec, Span or String value is a place.

#2440 made `p[i]` a place through a pointer or reference, "as on the value itself".
On the value itself it wasn't one:

    var v: Vec<i32> = ...10, 20, 30
    v[1] = 7                # ritz1 20: the store was lost
    v[1] += 2               # ritz1 20
    var v: Span<i32> = ...
    v[1] = 7                # ritz0 "Cannot index type", ritz1 20
    var v: Vec<Vec<i32>>
    v[1][1]                 # ritz1 -11: garbage

So `v[i]` on a local Vec, Span or String is `*(v.data + i)` (`v.ptr` for a Span,
`v.data.data` for a String), in every position: read, store, `+=`, `@`, `@&` and
`.f`, and as the base of another index, `v[i][j]`, which takes `p[i][j]` through a
pointer with it.

A method on an element is #2443, moving out through a reference #2444, and a slice
through a pointer #2448.
"""

import subprocess

import pytest

import test_ritz1_for_header as for_header
from test_index_through_reference import HEADER, KINDS, SCALARS, STRUCTS, _refused

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


def _main(setup: str, body: str) -> str:
    return f"{HEADER}pub fn main() -> i32\n{setup}{body}"


# Each returns element 1 (20), or the sum `add` wants (30).  `{e}` is the element type.
READS = {
    "read": ("    return v[1] as i32\n", 20),
    "add": ("    return (v[0] + v[1]) as i32\n", 30),
    "at": ("    let q: *{e} = @v[1]\n    return *q as i32\n", 20),
    "at_inferred": ("    let q = @v[1]\n    return *q as i32\n", 20),
    "at_next": ("    let q: *{e} = @v[0] + 1\n    return *q as i32\n", 20),
    "in_a_let": ("    let x: {e} = v[1]\n    return x as i32\n", 20),
    "index_is_a_local": ("    let i: i64 = 1\n    return v[i] as i32\n", 20),
}
# Each writes element 1, then reads it back without `[]`.
WRITES = {
    "store": ("    v[1] = 7\n", 7),
    "plus_equals": ("    v[1] += 2\n", 22),
    "minus_equals": ("    v[1] -= 2\n", 18),
    "at_mut": ("    let q: @&{e} = @&v[1]\n    *q = 7\n", 7),
    "at_store": ("    let q: *{e} = @v[1]\n    *q = 7\n", 7),
    "store_from_another": ("    v[1] = v[0] + v[2]\n", 40),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(READS))
@pytest.mark.parametrize("box", sorted(SCALARS))
def test_an_element_of_a_local_reads(run_with, box, op, compiler):
    _, elem, setup, _ = SCALARS[box]
    body, want = READS[op]
    assert run_with(compiler, op, _main(setup, body.replace("{e}", elem))) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(WRITES))
@pytest.mark.parametrize("box", sorted(SCALARS))
def test_a_write_lands_in_the_element_of_a_local(run_with, box, op, compiler):
    _, elem, setup, back = SCALARS[box]
    body, want = WRITES[op]
    program = _main(setup, body.replace("{e}", elem) + f"    return {back}\n")
    assert run_with(compiler, op, program) == want


# A wrong stride or width writes past element 1, or into the header.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("box", sorted(SCALARS))
def test_a_store_leaves_the_neighbours_and_the_header(run_with, box, compiler):
    _, _, setup, _ = SCALARS[box]
    first, last = {"Vec": ("*(v.data)", "*(v.data + 2)"),
                   "Span": ("a[0]", "a[2]"),
                   "String": ("*(v.data.data) as i32", "*(v.data.data + 2) as i32")}[box]
    length = "v.data.len" if box == "String" else "v.len"
    body = f"    v[1] = 7\n    return {first} + {last} + {length} as i32\n"
    assert run_with(compiler, "neighbours", _main(setup, body)) == 43


# A loop that writes every element: the store isn't a one-off of a constant index.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("box", ["Vec", "Span"])
def test_a_loop_writes_every_element(run_with, box, compiler):
    _, _, setup, _ = SCALARS[box]
    body = ("    var i: i64 = 0\n    while i < 3\n        v[i] = v[i] * 2 + 1\n        i += 1\n"
            "    return (v[0] + v[1] + v[2]) as i32\n")
    assert run_with(compiler, "loop", _main(setup, body)) == 123


STRUCT_READS = {
    "field": ("    return v[1].y\n", 20),
    "at_field": ("    let q: *i32 = @v[1].y\n    return *q\n", 20),
    "whole": ("    let s: S = v[1]\n    return s.y\n", 20),
    "at_whole": ("    let q: *S = @v[1]\n    return q.y\n", 20),
    "field_in_sum": ("    return v[1].y + v[0].y - 2\n", 20),
}
STRUCT_WRITES = {
    "field": ("    v[1].y = 7\n", 7),
    "plus_equals": ("    v[1].y += 2\n", 22),
    "at_mut_field": ("    let q: @&i32 = @&v[1].y\n    *q = 7\n", 7),
    "whole": ("    v[1] = S { x: 5, y: 7 }\n", 7),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(STRUCT_READS))
@pytest.mark.parametrize("box", sorted(STRUCTS))
def test_a_field_of_an_element_of_a_local_reads(run_with, box, op, compiler):
    _, setup, _ = STRUCTS[box]
    body, want = STRUCT_READS[op]
    assert run_with(compiler, op, _main(setup, body)) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(STRUCT_WRITES))
@pytest.mark.parametrize("box", sorted(STRUCTS))
def test_a_field_of_an_element_of_a_local_writes(run_with, box, op, compiler):
    _, setup, back = STRUCTS[box]
    body, want = STRUCT_WRITES[op]
    # `x` is kept, or 5 after a whole store: read back without `[]`.
    x_back = back.replace(".y", ".x") + (" - 2" if op == "whole" else "")
    program = _main(setup, body + f"    return {back} + {x_back} - 3\n")
    assert run_with(compiler, op, program) == want


# `v[1][1]`: the base of the outer index is itself an element.
VECS = """\
    var v: Vec<Vec<i32>> = vec_new<Vec<i32>>()
    var a: Vec<i32> = vec_new<i32>()
    var b: Vec<i32> = vec_new<i32>()
    a.push(1)
    a.push(2)
    b.push(10)
    b.push(20)
    vec_push<Vec<i32>>(@&v, a)
    vec_push<Vec<i32>>(@&v, b)
"""
# Element (1, 1) of `v`, read back without `[]`: `v[1]` is a copy of `b`'s header,
# so the two share a buffer.  (`*((*(v.data + 1)).data + 1)` would be #2450's.)
VECS_BACK = "*(b.data + 1)"
NESTED_READS = {
    "read": ("    return v[1][1]\n", 20),
    "add": ("    return v[0][1] + v[1][1]\n", 22),
    "at": ("    let q: *i32 = @v[1][1]\n    return *q\n", 20),
    "len": ("    return v[1].len as i32 + v[1][0]\n", 12),
}
NESTED_WRITES = {
    "store": ("    v[1][1] = 7\n", 7),
    "plus_equals": ("    v[1][1] += 2\n", 22),
    "at_mut": ("    let q: @&i32 = @&v[1][1]\n    *q = 7\n", 7),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(NESTED_READS))
def test_an_element_of_an_element_reads(run_with, op, compiler):
    body, want = NESTED_READS[op]
    assert run_with(compiler, op, _main(VECS, body)) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(NESTED_WRITES))
def test_an_element_of_an_element_writes(run_with, op, compiler):
    body, want = NESTED_WRITES[op]
    program = _main(VECS, body + f"    return {VECS_BACK} + *(a.data + 1) - 2\n")
    assert run_with(compiler, op, program) == want


# `p[1][1]` through a pointer or reference: #2440's NESTED rows, and their stores.
THROUGH = """\
fn f(p: {spelled}Vec<Vec<i32>>) -> i32
{body}
pub fn main() -> i32
{vecs}    let r: i32 = f({addr}v)
    return r + {back}
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_an_element_of_an_element_through_a_pointer_reads(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = HEADER + THROUGH.format(spelled=spelled, addr=addr, vecs=VECS, back=0,
                                      body="    return p[1][1] + p[0][0] - 1\n")
    assert run_with(compiler, "nested", program) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", ("pointer", "mut_reference"))
def test_an_element_of_an_element_through_a_pointer_writes(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = HEADER + THROUGH.format(spelled=spelled, addr=addr, vecs=VECS, back=VECS_BACK,
                                      body="    p[1][1] += 2\n    return 0\n")
    assert run_with(compiler, "nested", program) == 22


# A by-value parameter is a local of its own: its elements are the caller's buffer,
# which a Vec shares, so a store through it lands where the caller looks.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("box", ["Vec", "Span"])
def test_a_by_value_parameter_indexes(run_with, box, compiler):
    ty, _, setup, back = SCALARS[box]
    program = (f"{HEADER}fn f(v: {ty}) -> i32\n    v[2] = 9\n    return v[1]\n\n"
               f"pub fn main() -> i32\n{setup}    let r: i32 = f(v)\n"
               f"    return r + {back.replace('1', '2')}\n")
    assert run_with(compiler, "param", program) == 29


# An array of Vecs is #2329's base, `a[1][1]`; a Vec in a field is `h.v[1]`, also
# #2329's.  Neither is this rule's, and each keeps working as it did.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_array_still_indexes_as_an_array(run_with, compiler):
    body = "    var a: [3]i32 = [10, 20, 30]\n    a[1] = 7\n    a[2] += 2\n    return a[1] + a[2]\n"
    assert run_with(compiler, "array", _main("", body)) == 39


# A store checks its value against the element, not the Vec, as through a pointer.
SLOTS = {
    "too_wide": ("Vec<u8>", "v[1] = 300", "`300` does not fit in `u8`"),
    "too_wide_string": ("String", "v[1] = 300", "`300` does not fit in `u8`"),
    "too_wide_span": ("Span<i8>", "v[1] = 200", "`200` does not fit in `i8`"),
    "bool_into_int": ("Vec<i32>", "v[1] = true", "cannot use bool as an integer"),
    "int_into_bool": ("Vec<bool>", "v[1] = 1", "cannot use an integer as bool"),
    "string_into_int": ("Vec<i32>", 'v[1] = "abc"', "a string literal does not fit"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SLOTS))
def test_a_store_fits_the_element(compile_with, name, compiler):
    ty, stmt, message = SLOTS[name]
    program = f"{HEADER}fn f(v: {ty})\n    {stmt}\n\npub fn main() -> i32\n    return 0\n"
    _refused(compile_with, compiler, name, program, message)


# A condition sees the element: an element of a `Span<bool>` is a bool, and of a
# `Vec<i32>` isn't.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_bool_element_is_a_condition(run_with, compiler):
    setup = ("    var a: [2]bool\n    a[0] = false\n    a[1] = true\n"
             "    var v: Span<bool> = span_from_ptr<bool>(@a[0], 2)\n")
    assert run_with(compiler, "cond", _main(setup, "    if v[1]\n        return 5\n    return 6\n")) == 5


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_int_element_is_not_a_condition(compile_with, compiler):
    program = f"{HEADER}fn f(v: Vec<i32>) -> i32\n    if v[1]\n        return 1\n    return 0\n\npub fn main() -> i32\n    return 0\n"
    _refused(compile_with, compiler, "cond", program, "if condition must be bool")


# A slice of the value keeps its own lowering: `v[1..3]` isn't an element.  The
# slice itself is test_slice_value_local.py's (#2451).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_slice_of_a_span_is_not_an_element(run_with, compiler):
    _, _, setup, _ = SCALARS["Span"]
    body = "    let t = v[1..3]\n    return t[0] as i32\n"
    assert run_with(compiler, "slice", _main(setup, body)) == 20


# An element that points at a Vec: `[]` sees through it, one level, as through a
# `*Vec` local.  ritz1 segfaulted on the store and ritz0 raised a ValueError.
PTRS = """\
type VP = *Vec<i32>

pub fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(10)
    v.push(20)
    var w: Vec<VP> = vec_new<VP>()
    vec_push<VP>(@&w, @v)
{body}"""
PTRS_ROWS = {
    "read": ("    return w[0][1]\n", 20),
    "store": ("    w[0][1] = 7\n    return *(v.data + 1)\n", 7),
    "plus_equals": ("    w[0][1] += 2\n    return *(v.data + 1)\n", 22),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(PTRS_ROWS))
def test_an_element_that_points_at_a_vec_indexes(run_with, op, compiler):
    body, want = PTRS_ROWS[op]
    assert run_with(compiler, op, HEADER + PTRS.format(body=body)) == want



# Not places, and not taken as one.  Loud on all three, but not located: #2452.
# `(*v)[1]` derefs a value: under a looser guard ritz1 read element 1 from it.
NOT_PLACES = {
    "deref_of_a_value": (SCALARS["Vec"][2], "    return (*v)[1]\n"),
    "element_not_indexable": (STRUCTS["Vec"][1], "    return v[1][1]\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_PLACES))
def test_not_a_place_is_not_taken(compile_with, name, compiler):
    setup, body = NOT_PLACES[name]
    comp, ll, work = compile_with(compiler, name, _main(setup, body))
    if comp.returncode == 0:
        link = subprocess.run(["clang", "-w", "-c", str(ll), "-o", str(work / "main.o")],
                              capture_output=True, text=True)
        assert link.returncode != 0, f"{compiler} took {name}"


# A Span this module never declared, the bare `{ ptr, i64 }` of `as_bytes()`, keeps
# the read it had: there's no `.ptr` field to name.  (ritz0 failed to compile this
# matrix test, test_issue_strview_as_bytes, on #2442's first cut.)
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_undeclared_span_still_reads(run_with, compiler):
    program = ("import ritzlib.strview\n\npub fn main() -> i32\n    let s: StrView = \"ABC\"\n"
               "    let bytes = s.as_bytes()\n    return (bytes[1] - bytes[0]) as i32 + 6\n")
    assert run_with(compiler, "as_bytes", program) == 7
