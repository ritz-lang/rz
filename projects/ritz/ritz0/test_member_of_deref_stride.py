"""AGAST #2450: a pointer field reached through a deref strides by its element.

`+` on a pointer takes its stride from the left operand's type.  On ritz1 a
member of a deref wasn't typed as the field's pointer there, so it stepped by
bytes and read garbage, silently:

    struct H / k: i64 / q: *i32
    let hp: *H = @h
    *(hp.q + 1)             # 20
    *((*hp).q + 1)          # ritz1 0: one byte in
    *((*(hp + 0)).q + 1)    # ritz1 0
    *((*(v.data)).data + 1) # ritz1 0, `v: Vec<Vec<i32>>`

#2440 fixed the same shape for `*(p[1].q + 1)`.  The table is every place x
every element width, read at a constant, read at a local index, and written.
"""

import pytest

import test_ritz1_for_header as for_header

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# Element type -> (is a struct, setup of `a: [3]T` holding 10, 20, 30).
WIDTHS = {
    "i8": False,
    "i32": False,
    "i64": False,
    "S": True,
}

# Place -> (the pointer field, how element 1 reads back without the place).
PLACES = {
    "deref": "(*hp).q",
    "deref_of_sum": "(*(hp + 0)).q",
    "deref_of_member": "(*(v.data)).data",
}


def _program(place: str, elem: str, body: str) -> str:
    struct = WIDTHS[elem]
    out = ("import ritzlib.gvec\n\n"
           "struct S\n    x: i32\n    y: i32\n\n"
           f"struct H\n    k: i64\n    q: *{elem}\n\n"
           "pub fn main() -> i32\n")
    if place == "deref_of_member":
        out += (f"    var w: Vec<{elem}> = vec_new<{elem}>()\n"
                f"    var v: Vec<Vec<{elem}>> = vec_new<Vec<{elem}>>()\n")
        for n in (10, 20, 30):
            out += (f"    w.push(S {{ x: {n + 1}, y: {n} }})\n" if struct
                    else f"    w.push({n})\n")
        out += "    v.push(w)\n"
    else:
        out += f"    var a: [3]{elem}\n"
        for i, n in enumerate((10, 20, 30)):
            out += (f"    a[{i}].x = {n + 1}\n    a[{i}].y = {n}\n" if struct
                    else f"    a[{i}] = {n}\n")
        out += "    var h: H\n    h.k = 0\n    h.q = @a[0]\n    let hp: *H = @h\n"
    return out + body


def _elem(place: str, elem: str, at: str) -> str:
    """Element `at` of the place, as an lvalue: `*(P + at)` or `(*(P + at)).y`."""
    ptr = f"*({PLACES[place]} + {at})"
    return f"({ptr}).y" if WIDTHS[elem] else ptr


def _back(place: str, elem: str) -> str:
    """Element 1 read back without the place under test."""
    base = "v[0][1]" if place == "deref_of_member" else "a[1]"
    return f"{base}.y" if WIDTHS[elem] else f"{base} as i32"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("elem", sorted(WIDTHS))
@pytest.mark.parametrize("place", sorted(PLACES))
def test_element_one_reads_twenty(run_with, place, elem, compiler):
    body = f"    return {_elem(place, elem, '1')} as i32\n"
    assert run_with(compiler, f"read_{place}_{elem}", _program(place, elem, body)) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("elem", sorted(WIDTHS))
@pytest.mark.parametrize("place", sorted(PLACES))
def test_a_local_index_reads_the_same(run_with, place, elem, compiler):
    body = f"    let i: i64 = 2\n    return {_elem(place, elem, 'i')} as i32\n"
    assert run_with(compiler, f"local_{place}_{elem}", _program(place, elem, body)) == 30


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("elem", sorted(WIDTHS))
@pytest.mark.parametrize("place", sorted(PLACES))
def test_a_store_lands_in_element_one(run_with, place, elem, compiler):
    body = f"    {_elem(place, elem, '1')} = 7\n    return {_back(place, elem)}\n"
    assert run_with(compiler, f"store_{place}_{elem}", _program(place, elem, body)) == 7
