"""AGAST #2448: `p[lo..hi]` through a pointer or reference slices what's behind it.

R9 rule 2 (projects/larb/review/4/rulings-2026-11.md): `p[i]` means `(*p)[i]` when
`p` is a `*T`, `@T` or `@&T` and T is an array, Vec, Span or String.  Rule 6 keeps
`p[lo..hi]` refused "as on a plain array": a slice through a reference does what
the plain value does.  A Vec, Span or String slices (LANGUAGE_SPEC §3.4,
test_slice_value_local.py); an array doesn't.

Before this, ritz1 refused the slice at the index ("a slice through a pointer or
reference isn't lowered by ritz1", #2440's stopgap), and ritz0 ran the Span form
but refused the Vec form ("Type of #1 arg mismatch": vec_slice$T takes the
reference and was handed the Vec).

So on all three compilers `p[lo..hi]` and `(*p)[lo..hi]` are `(*p)[lo..hi]`: a
Vec or String slice is a copy, a Span slice a view into the same elements.
"""

import pytest

from test_index_through_reference import HEADER, KINDS, _refused
import test_slice_value_local as value_local
from test_slice_value_local import BOXES, RANGES, WRITES_THROUGH

# The by-value table's fixtures: it links ritzlib/string for a String slice.
compile_with = value_local.compile_with
run_with = value_local.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# What `p` points at, by box: the type spelled in `f`'s parameter.
TYPES = {"Vec": "Vec<i32>", "Span": "Span<i32>", "String": "String"}

# `p[..]`, and the same place spelled as the deref.
FORMS = {"index": "p", "deref": "(*p)"}


def _program(box, kind, rng, body, form="index", tail=""):
    """`f` slices `v` through `p`; main builds `v`, and `tail` reads it after."""
    setup, _, _ = BOXES[box]
    spelled, addr = KINDS[kind]
    return (f"{HEADER}fn f(p: {spelled}{TYPES[box]}) -> i32\n"
            f"    let t = {FORMS[form]}[{rng}]\n{body}\n"
            f"pub fn main() -> i32\n{setup}    let r: i32 = f({addr}v)\n"
            f"    return r{tail}\n")


def _length_of(box):
    return BOXES[box][2]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(FORMS))
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_first_element(run_with, box, kind, rng, form, compiler):
    spelled, _, _ = RANGES[rng]
    program = _program(box, kind, spelled, "    return t[0] as i32\n", form)
    assert run_with(compiler, "t0", program) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_last_element(run_with, box, kind, rng, compiler):
    spelled, length, last = RANGES[rng]
    program = _program(box, kind, spelled, f"    return t[{length - 1}] as i32\n")
    assert run_with(compiler, "last", program) == last


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_sum(run_with, box, kind, rng, compiler):
    spelled, length, last = RANGES[rng]
    terms = " + ".join(f"t[{i}]" for i in range(length))
    program = _program(box, kind, spelled, f"    return ({terms}) as i32\n")
    assert run_with(compiler, "sum", program) == sum(range(20, last + 1, 10))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(FORMS))
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_length(run_with, box, kind, rng, form, compiler):
    spelled, length, _ = RANGES[rng]
    program = _program(box, kind, spelled, f"    return {_length_of(box)} as i32\n", form)
    assert run_with(compiler, "len", program) == length


# `t[0] = 7` lands in `t`, and in `v` for a Span only: a Vec or String slice is a
# copy, a Span slice a view.  `t` is f's own local, so it's writable whatever `p` is.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_a_write_through_the_slice(run_with, box, kind, rng, compiler):
    spelled, _, _ = RANGES[rng]
    _, back, _ = BOXES[box]
    program = _program(box, kind, spelled, "    t[0] = 7\n    return (t[0] as i32) * 100\n",
                       tail=f" + {back}")
    want = 707 if WRITES_THROUGH[box] else 720
    assert run_with(compiler, "write", program) == want % 256


# The slice leaves `v` and `p` as they were: `v` still has its 4 elements after.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_pointee_is_left_alone(run_with, box, kind, compiler):
    length_of = _length_of(box).replace("t.", "p.")
    body = f"    return ({length_of} as i32) * 10 + {_length_of(box)} as i32\n"
    assert run_with(compiler, "pointee", _program(box, kind, "1..3", body)) == 42


# The slice is a Vec, Span or String local, so it slices again by value.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_a_slice_of_the_slice(run_with, box, kind, compiler):
    length_of = _length_of(box).replace("t.", "u.")
    body = f"    let u = t[1..=2]\n    return (u[1] as i32) + {length_of} as i32\n"
    assert run_with(compiler, "twice", _program(box, kind, "1..4", body)) == 42


# A String has no `len` field: the same located refusal as on the value.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_the_len_field_of_a_string_slice_is_refused(compile_with, kind, compiler):
    program = _program("String", kind, "1..3", "    return t.len as i32\n")
    _refused(compile_with, compiler, "string_len", program,
             "Unknown field 'len' in struct 'String'")


# #2440's pin: a Span sliced through a pointer, read through `t[0]`.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_span_slice_returned_by_value(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = (f"{HEADER}fn f(p: {spelled}Span<i32>) -> Span<i32>\n    return p[1..3]\n\n"
               "pub fn main() -> i32\n"
               "    var a: [4]i32 = [10, 20, 30, 40]\n"
               "    var v: Span<i32> = span_from_ptr<i32>(@a[0], 4)\n"
               f"    let t = f({addr}v)\n    return (t[1] + t.len) as i32\n")
    assert run_with(compiler, "returned", program) == 32


# A pointer bound by `let`, annotated or not, slices the same: `let p = @v` is an
# `@T` (R9).  v[1..3] is 20, 30.
LETS = {"shared": "let p = @v", "mut": "let p = @&v",
        "annotated_shared": "let p: @{ty} = @v", "annotated_pointer": "let p: *{ty} = @v"}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("bind", sorted(LETS))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_a_pointer_bound_by_let(run_with, box, bind, compiler):
    setup, _, length_of = BOXES[box]
    spelled = LETS[bind]
    program = (f"{HEADER}pub fn main() -> i32\n{setup}"
               f"    {spelled.format(ty=TYPES[box])}\n    let t = p[1..3]\n"
               f"    return (t[1] as i32) + {length_of} as i32\n")
    assert run_with(compiler, bind, program) == 32


# A Span<u8> needs no import, and then ritz1 builds the view itself, as on the value
# (test_slice_value_local.py): through `p` it's `p.ptr + lo`.
NO_IMPORT = """\
fn f(p: {spelled}Span<u8>) -> i32
    let t = {base}[1..=2]
    t[0] = 7
    return (t[1] as i32) + t.len as i32

fn g(v: Span<u8>) -> i32
    return f({addr}v)

pub fn main() -> i32
    var a: [4]u8 = [10, 20, 30, 40]
    let r: i32 = g(@a)
    return r * 10 + a[1] as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("form", sorted(FORMS))
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_span_of_bytes_needs_no_import(run_with, kind, form, compiler):
    spelled, addr = KINDS[kind]
    program = NO_IMPORT.format(spelled=spelled, addr=addr, base=FORMS[form])
    assert run_with(compiler, "no_import", program) == (32 * 10 + 7) % 256


# Into a Span slot a Vec slice is a view on ritz0, and refused by ritz1, located,
# as on the value (#2501).
INTO_SPAN = (f"{HEADER}fn f(p: {{spelled}}Vec<i32>) -> i32\n"
             "    let t: Span<i32> = p[1..3]\n    return (t[1] + t.len) as i32\n\n"
             f"pub fn main() -> i32\n{BOXES['Vec'][0]}    return f({{addr}}v)\n")


@pytest.mark.integration
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_vec_slice_into_a_span_is_a_view_on_ritz0(run_with, kind):
    spelled, addr = KINDS[kind]
    assert run_with("ritz0", "into_span", INTO_SPAN.format(spelled=spelled, addr=addr)) == 32


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_vec_slice_into_a_span_is_refused_on_ritz1(compile_with, kind, compiler):
    spelled, addr = KINDS[kind]
    _refused(compile_with, compiler, "into_span", INTO_SPAN.format(spelled=spelled, addr=addr),
             "this slice of a Vec, Span or String isn't lowered by ritz1")


# An array doesn't slice, so neither does a pointer to one (R9 rule 6).  ritz0's
# refusal is unlocated: #2521.
ARRAY = (f"{HEADER}fn f(p: *[4]i32) -> i32\n    let t = p[1..3]\n    return 0\n\n"
         "pub fn main() -> i32\n    var a: [4]i32 = [10, 20, 30, 40]\n    return f(@a)\n")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_a_slice_through_a_pointer_to_an_array_is_refused(compile_with, compiler):
    _refused(compile_with, compiler, "array", ARRAY, "a pointer to an array can't be sliced")


@pytest.mark.integration
def test_ritz0_refuses_a_slice_through_a_pointer_to_an_array(compile_with):
    comp, _, _ = compile_with("ritz0", "array", ARRAY)
    assert comp.returncode != 0
    assert "Only String, Vec and Span types support slicing" in comp.stdout + comp.stderr


# One level (R9 rule 5): `pp[lo..hi]` on a `**Vec` isn't the Vec's slice.  ritz0
# refuses it, unlocated; ritz1 reads garbage.  Both are #2521's.
DOUBLE = (f"{HEADER}fn f(pp: **Vec<i32>) -> i32\n    let t = pp[1..3]\n    return t[0]\n\n"
          f"pub fn main() -> i32\n{BOXES['Vec'][0]}    var p: *Vec<i32> = @v\n    return f(@p)\n")


@pytest.mark.integration
def test_ritz0_does_not_slice_two_levels_down(compile_with):
    comp, _, _ = compile_with("ritz0", "double", DOUBLE)
    assert comp.returncode != 0
