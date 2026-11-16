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

AGAST #3519: one table (test_table_rows.py), as in test_index_through_reference.py.
Each row has the id its parametrised test had, less the compiler.
"""

import pytest

import test_table_rows as table_rows
import test_ritz1_for_header as for_header
import test_slice_value_local as value_local
from deref_rules import no_field
from test_table_rows import Refused, Run, case
from test_index_through_reference import HEADER, KINDS
from test_slice_value_local import BOXES, RANGES, WRITES_THROUGH

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


@case(box=sorted(BOXES), kind=sorted(KINDS), rng=sorted(RANGES), form=sorted(FORMS))
def the_first_element(box, kind, rng, form):
    spelled, _, _ = RANGES[rng]
    return Run(_program(box, kind, spelled, "    return t[0] as i32\n", form), 20)


@case(box=sorted(BOXES), kind=sorted(KINDS), rng=sorted(RANGES))
def the_last_element(box, kind, rng):
    spelled, length, last = RANGES[rng]
    return Run(_program(box, kind, spelled, f"    return t[{length - 1}] as i32\n"), last)


@case(box=sorted(BOXES), kind=sorted(KINDS), rng=sorted(RANGES))
def the_sum(box, kind, rng):
    spelled, length, last = RANGES[rng]
    terms = " + ".join(f"t[{i}]" for i in range(length))
    return Run(_program(box, kind, spelled, f"    return ({terms}) as i32\n"),
               sum(range(20, last + 1, 10)))


@case(box=sorted(BOXES), kind=sorted(KINDS), rng=sorted(RANGES), form=sorted(FORMS))
def the_length(box, kind, rng, form):
    spelled, length, _ = RANGES[rng]
    return Run(_program(box, kind, spelled, f"    return {_length_of(box)} as i32\n", form), length)


# `t[0] = 7` lands in `t`, and in `v` for a Span only: a Vec or String slice is a
# copy, a Span slice a view.  `t` is f's own local, so it's writable whatever `p` is.
@case(box=sorted(BOXES), kind=sorted(KINDS), rng=sorted(RANGES))
def a_write_through_the_slice(box, kind, rng):
    spelled, _, _ = RANGES[rng]
    _, back, _ = BOXES[box]
    program = _program(box, kind, spelled, "    t[0] = 7\n    return (t[0] as i32) * 100\n",
                       tail=f" + {back}")
    return Run(program, (707 if WRITES_THROUGH[box] else 720) % 256)


# The slice leaves `v` and `p` as they were: `v` still has its 4 elements after.
@case(box=sorted(BOXES), kind=sorted(KINDS))
def the_pointee_is_left_alone(box, kind):
    length_of = _length_of(box).replace("t.", "p.")
    body = f"    return ({length_of} as i32) * 10 + {_length_of(box)} as i32\n"
    return Run(_program(box, kind, "1..3", body), 42)


# The slice is a Vec, Span or String local, so it slices again by value.
@case(box=sorted(BOXES), kind=sorted(KINDS))
def a_slice_of_the_slice(box, kind):
    length_of = _length_of(box).replace("t.", "u.")
    body = f"    let u = t[1..=2]\n    return (u[1] as i32) + {length_of} as i32\n"
    return Run(_program(box, kind, "1..4", body), 42)


# A String has no `len` field: the same located refusal as on the value.
@case(kind=sorted(KINDS))
def the_len_field_of_a_string_slice_is_refused(kind):
    return Refused(_program("String", kind, "1..3", "    return t.len as i32\n"),
                   no_field("String", "len"))  # §7.7 rule 5(a)


# #2440's pin: a Span sliced through a pointer, read through `t[0]`.
@case(kind=sorted(KINDS))
def a_span_slice_returned_by_value(kind):
    spelled, addr = KINDS[kind]
    return Run(f"{HEADER}fn f(p: {spelled}Span<i32>) -> Span<i32>\n    return p[1..3]\n\n"
               "pub fn main() -> i32\n"
               "    var a: [4]i32 = [10, 20, 30, 40]\n"
               "    var v: Span<i32> = span_from_ptr<i32>(@a[0], 4)\n"
               f"    let t = f({addr}v)\n    return (t[1] + t.len) as i32\n", 32)


# A pointer bound by `let`, annotated or not, slices the same: `let p = @v` is an
# `@T` (R9).  v[1..3] is 20, 30.
LETS = {"shared": "let p = @v", "mut": "let p = @&v",
        "annotated_shared": "let p: @{ty} = @v", "annotated_pointer": "let p: *{ty} = @v"}


@case(box=sorted(BOXES), bind=sorted(LETS))
def a_pointer_bound_by_let(box, bind):
    setup, _, length_of = BOXES[box]
    spelled = LETS[bind]
    return Run(f"{HEADER}pub fn main() -> i32\n{setup}"
               f"    {spelled.format(ty=TYPES[box])}\n    let t = p[1..3]\n"
               f"    return (t[1] as i32) + {length_of} as i32\n", 32)


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


@case(kind=sorted(KINDS), form=sorted(FORMS))
def a_span_of_bytes_needs_no_import(kind, form):
    spelled, addr = KINDS[kind]
    return Run(NO_IMPORT.format(spelled=spelled, addr=addr, base=FORMS[form]), (32 * 10 + 7) % 256)


# Into a Span slot a Vec slice is a view of what `p` points at, as on the value
# (#2501): t[1] is v[2], 30.  ritz1 refused it, located.
INTO_SPAN = (f"{HEADER}fn f(p: {{spelled}}Vec<i32>) -> i32\n"
             "    let t: Span<i32> = {base}[1..3]\n    return (t[1] + t.len) as i32\n\n"
             f"pub fn main() -> i32\n{BOXES['Vec'][0]}    return f({{addr}}v)\n")


@case(kind=sorted(KINDS), form=sorted(FORMS))
def a_vec_slice_into_a_span_is_a_view(kind, form):
    spelled, addr = KINDS[kind]
    return Run(INTO_SPAN.format(spelled=spelled, addr=addr, base=FORMS[form]), 32)


# An array doesn't slice, so neither does a pointer to one (R9 rule 6).  ritz0
# says so located too (#2521, test_slice_only_three.py): its row was its own test.
ARRAY = (f"{HEADER}fn f(p: *[4]i32) -> i32\n    let t = p[1..3]\n    return 0\n\n"
         "pub fn main() -> i32\n    var a: [4]i32 = [10, 20, 30, 40]\n    return f(@a)\n")


@case(compilers=("ritz1", "ritz1_selfhosted"))
def a_slice_through_a_pointer_to_an_array_is_refused():
    return Refused(ARRAY, "a pointer to an array can't be sliced")


@case(compilers=("ritz0",))
def ritz0_refuses_a_slice_through_a_pointer_to_an_array():
    return Refused(ARRAY, "a pointer to an array can't be sliced")


# One level (R9 rule 5): `pp[lo..hi]` on a `**Vec` isn't the Vec's slice.  All
# three refuse it, located (#2521, test_slice_only_three.py).
DOUBLE = (f"{HEADER}fn f(pp: **Vec<i32>) -> i32\n    let t = pp[1..3]\n    return t[0]\n\n"
          f"pub fn main() -> i32\n{BOXES['Vec'][0]}    var p: *Vec<i32> = @v\n    return f(@p)\n")


@case(compilers=("ritz0",))
def ritz0_does_not_slice_two_levels_down():
    return Refused(DOUBLE, None, located=False)


TABLE = table_rows.cases(globals())


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(TABLE),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(TABLE)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    # A String slice links ritzlib/string, as test_slice_value_local.py's `run_with` does.
    def strings(compiler):
        return value_local._string_objects(compiler, ritz1_bin)

    table_rows.assert_rows(compiler, table_rows.chunk(TABLE, compiler, chunk),
                           build=for_header.batch_build(ritz1_bin, strings),
                           compile=for_header.batch_compile(ritz1_bin), work=tmp_path)
