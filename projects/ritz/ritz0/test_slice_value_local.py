"""AGAST #2451: a slice of a Vec, Span or String local is a Vec, Span or String.

ritz1 lowered `v[lo..hi]` to a bare address held in an `i64`, so the slice lost
its type and its length:

    var v: Vec<i32> = ...10, 20, 30
    let t = v[1..3]
    t[1]                # ritz1 0, want 30: the untyped address indexed by bytes
    t.len               # ritz1 "unhandled EXPR_MEMBER", unlocated

and ritz0 refused the Vec case unless the program happened to instantiate
`vec_slice<T>` itself.  ritz1 had no `v[lo..=hi]` at all.

It's ritz0's lowering on all three compilers: a Vec slice is `vec_slice<T>`, a
copy; a String slice is `string_slice`, a copy; a Span slice is a view into the
same elements.  So a write through `t` lands in `v` for a Span only.  `lo..=hi`
is `lo..hi + 1`.  A String has no `len` field (`t.data.len` is its length), so
`t.len` is a located refusal, the same on all three.

Through a pointer or reference it's #2448.
"""

import functools
import subprocess
import tempfile
from pathlib import Path

import pytest

import batching
import fast_link

import test_ritz1_for_header as for_header
from test_index_through_reference import HEADER, _refused

compile_with = for_header.compile_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# A String slice calls string_slice, which neither compiler emits into main.ll:
# it's linked from ritzlib/string, as a program would, with what string needs.
STRING_UNITS = ("string", "strview", "hash")


@functools.lru_cache(maxsize=None)
def _string_objects(compiler, ritz1_bin) -> tuple:
    work = Path(tempfile.mkdtemp(prefix=f"slice_string_{compiler}_"))
    objects = []
    for unit in STRING_UNITS:
        ll = work / f"{unit}.ll"
        comp = for_header._emit(compiler, ritz1_bin, for_header.RITZ_ROOT / "ritzlib" / f"{unit}.ritz", ll)
        assert comp.returncode == 0, comp.stdout + comp.stderr
        obj = work / f"{unit}.o"
        fast_link.clang(["clang", "-w", "-c", str(ll), "-o", str(obj)], check=True)
        objects.append(str(obj))
    return tuple(objects)


@pytest.fixture
def run_with(ritz1_bin, compile_with):
    def strings(compiler):
        return _string_objects(compiler, ritz1_bin)

    def go(compiler, name, program):
        got = batching.run(compiler, program, for_header.batch_build(ritz1_bin, strings))  # #2806
        if got is not None:
            return got
        comp, ll, work = compile_with(compiler, name, program)
        assert comp.returncode == 0 and ll.exists(), (
            f"{compiler} failed on {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}")
        link, exe = for_header._link(compiler, ritz1_bin, ll, work, strings(compiler))
        assert link.returncode == 0, f"{name} would not link:\n{link.stderr[-2000:]}"
        return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    return go

# `v` holds 10, 20, 30, 40.  `back` reads v's element 1 without `[]`, and `length`
# is t's element count spelled for the box.
BOXES = {
    "Vec": ("    var v: Vec<i32> = vec_new<i32>()\n"
            "    v.push(10)\n    v.push(20)\n    v.push(30)\n    v.push(40)\n",
            "*(v.data + 1)", "t.len"),
    "Span": ("    var a: [4]i32 = [10, 20, 30, 40]\n"
             "    var v: Span<i32> = span_from_ptr<i32>(@a[0], 4)\n",
             "a[1]", "t.len"),
    "String": ("    var v: String\n    v.data = vec_new<u8>()\n"
               "    v.data.push(10)\n    v.data.push(20)\n    v.data.push(30)\n    v.data.push(40)\n",
               "*(v.data.data + 1) as i32", "t.data.len"),
}

# Both spellings of elements 1 and 2, and 1..3 of the same: an off-by-one in `..=`
# changes the length and the last element.
RANGES = {"exclusive": ("1..3", 2, 30), "inclusive": ("1..=2", 2, 30),
          "inclusive_to_the_end": ("1..=3", 3, 40), "exclusive_to_the_end": ("1..4", 3, 40)}

# A view writes through to `v`; a copy doesn't.
WRITES_THROUGH = {"Vec": False, "Span": True, "String": False}


def _main(setup: str, rng: str, body: str) -> str:
    return f"{HEADER}pub fn main() -> i32\n{setup}    let t = v[{rng}]\n{body}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_first_element_of_a_slice(run_with, box, rng, compiler):
    setup, _, _ = BOXES[box]
    spelled, _, _ = RANGES[rng]
    assert run_with(compiler, "t0", _main(setup, spelled, "    return t[0] as i32\n")) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_last_element_of_a_slice(run_with, box, rng, compiler):
    setup, _, _ = BOXES[box]
    spelled, length, last = RANGES[rng]
    body = f"    return t[{length - 1}] as i32\n"
    assert run_with(compiler, "last", _main(setup, spelled, body)) == last


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_sum_of_a_slice(run_with, box, rng, compiler):
    setup, _, _ = BOXES[box]
    spelled, length, last = RANGES[rng]
    terms = " + ".join(f"t[{i}]" for i in range(length))
    body = f"    return ({terms}) as i32\n"
    assert run_with(compiler, "sum", _main(setup, spelled, body)) == sum(range(20, last + 1, 10))


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_the_length_of_a_slice(run_with, box, rng, compiler):
    setup, _, length_of = BOXES[box]
    spelled, length, _ = RANGES[rng]
    body = f"    return {length_of} as i32\n"
    assert run_with(compiler, "len", _main(setup, spelled, body)) == length


# A String's length is `t.data.len`: `t.len` names no field, on all three.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
def test_the_len_field_of_a_string_slice_is_refused(compile_with, rng, compiler):
    setup, _, _ = BOXES["String"]
    spelled, _, _ = RANGES[rng]
    program = _main(setup, spelled, "    return t.len as i32\n")
    _refused(compile_with, compiler, "string_len", program,
             "Unknown field 'len' in struct 'String'")


# `t[0] = 7` lands in t; in v too for a Span, a view, and not for a Vec or a String,
# copies.  The `let` holds the header: the elements are behind its pointer.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("rng", sorted(RANGES))
@pytest.mark.parametrize("box", sorted(BOXES))
def test_a_write_through_a_slice(run_with, box, rng, compiler):
    setup, back, _ = BOXES[box]
    spelled, _, _ = RANGES[rng]
    body = f"    t[0] = 7\n    return (t[0] as i32) * 100 + {back}\n"
    want = 707 if WRITES_THROUGH[box] else 720
    assert run_with(compiler, "write", _main(setup, spelled, body)) == want % 256


# The slice leaves its neighbours alone: a write to t[1] doesn't reach v[1] or
# v[3], or t[0].
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("box", sorted(BOXES))
def test_a_write_to_a_slice_keeps_its_neighbours(run_with, box, compiler):
    setup, back, _ = BOXES[box]
    last = back.replace("1", "3")
    body = f"    t[1] = 7\n    return (t[0] as i32) + {back} + {last}\n"
    # t[1] is v[2] in a view: v[1] and v[3] are untouched either way.
    assert run_with(compiler, "neighbours", _main(setup, "1..3", body)) == 20 + 20 + 40



# A slice is a Vec, Span or String local like any other, so it slices again:
# v[1..4] is 20, 30, 40 and its [1..=2] is 30, 40.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("box", sorted(BOXES))
def test_a_slice_of_a_slice(run_with, box, compiler):
    setup, _, length_of = BOXES[box]
    body = f"    let u = t[1..=2]\n    return (u[1] as i32) + {length_of.replace('t.', 'u.')} as i32\n"
    assert run_with(compiler, "twice", _main(setup, "1..4", body)) == 42

# The local doesn't have to be declared with its type: a Span a plain function
# returned, or a by-value Span parameter, slices the same way.
SHAPES = {
    "returned_by_a_call": ("fn ms(a: *i32) -> Span<i32>\n    return span_from_ptr<i32>(a, 4)\n\n",
                           "    var a: [4]i32 = [10, 20, 30, 40]\n    var v = ms(@a[0])\n"
                           "    let t = v[1..=2]\n    return (t[1] + t.len) as i32\n"),
    "a_parameter": ("fn tail(v: Span<i32>) -> i32\n    let t = v[1..3]\n    return (t[1] + t.len) as i32\n\n",
                    "    var a: [4]i32 = [10, 20, 30, 40]\n"
                    "    return tail(span_from_ptr<i32>(@a[0], 4))\n"),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_a_span_slices_however_it_was_bound(run_with, shape, compiler):
    before, body = SHAPES[shape]
    program = f"{HEADER}{before}pub fn main() -> i32\n{body}"
    assert run_with(compiler, shape, program) == 32


# AGAST #2501: a Vec slice into a Span slot is a view of the Vec, not
# vec_slice's copy (ritz0's _emit_vec_span_slice, LANGUAGE_SPEC §3.4):
# `Span$T { ptr: v.data + lo, len: hi - lo }`.  ritz1 refused it, located
# ("this slice ... isn't lowered by ritz1"); before #2451, unlocated.
VEC_SETUP = BOXES["Vec"][0]
COUNTER = "var g_calls: i32 = 0\n\nfn idx() -> i64\n    g_calls += 1\n    return 1\n\n"


def _into_span(rng: str, body: str, before: str = "") -> str:
    return (f"{HEADER}{before}pub fn main() -> i32\n{VEC_SETUP}"
            f"    let t: Span<i32> = v[{rng}]\n{body}")


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_vec_slice_into_a_span_reads_the_vec(run_with, compiler):
    program = _into_span("1..3", "    return (t[1] + t.len) as i32\n")
    assert run_with(compiler, "into_span", program) == 32


# A view, so a write through `t` lands in `v` (a copy's wouldn't: 720).
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_write_through_a_vec_slice_into_a_span_lands_in_the_vec(run_with, compiler):
    body = "    t[0] = 7\n    return (t[0] as i32) * 100 + *(v.data + 1)\n"
    assert run_with(compiler, "into_span_write", _into_span("1..3", body)) == 707 % 256


# The Vec can be a by-value field: `b.data[1..3]` is the same view.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_vec_field_slice_into_a_span_reads_the_vec(run_with, compiler):
    program = (f"{HEADER}struct B\n    data: Vec<i32>\n\npub fn main() -> i32\n{VEC_SETUP}"
               "    let b = B { data: v }\n    let t: Span<i32> = b.data[1..3]\n"
               "    return (t[1] + t.len) as i32\n")
    assert run_with(compiler, "field_into_span", program) == 32


# `lo` appears in both fields, and is evaluated once: idx() runs one time.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_call_in_the_low_bound_of_a_vec_view_runs_once(run_with, compiler):
    body = "    return (t[0] + t.len * 10) as i32 + g_calls * 100\n"  # 20 + 2 * 10 + 1 * 100
    program = _into_span("idx()..3", body, COUNTER)
    assert run_with(compiler, "into_span_once", program) == (20 + 20 + 100) % 256


# A call inside the bound isn't the bound itself, so it can't be shared: ritz1
# refuses rather than run it twice.  ritz0 emits the bound once and takes it.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_a_call_inside_the_low_bound_of_a_vec_view_is_refused_on_ritz1(compile_with, compiler):
    program = _into_span("idx() + 0..3", "    return t.len as i32\n", COUNTER)
    _refused(compile_with, compiler, "into_span_nested", program,
             "this slice of a Vec, Span or String isn't lowered by ritz1")


# A struct that isn't one of the three has no slice.  ritz1 read it as an address.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_a_slice_of_another_struct_is_refused_on_ritz1(compile_with, compiler):
    program = (f"{HEADER}pub fn main() -> i32\n    var v = S {{ x: 1, y: 2 }}\n"
               "    let t = v[0..1]\n    return 0\n")
    _refused(compile_with, compiler, "struct", program,
             "a struct can't be sliced (only String, Vec and Span can)")


# A Span<u8> needs no import, and then there's no span_slice: ritz1 builds the
# view itself, `Span$u8 { ptr: v.ptr + lo, len: hi - lo }`, as ritz0 does.
# The Span is a parameter: `let v: Span<u8> = @a` is #2502 on ritz1.
NO_IMPORT = """\
fn idx() -> i64
    return 1

fn f(v: Span<u8>) -> i32
    let lo: i64 = 1
{body}
pub fn main() -> i32
    var a: [4]u8 = [10, 20, 30, 40]
    let r: i32 = f(@a)
    return r * 100 + a[1] as i32
"""
NO_IMPORT_ROWS = {
    "t1": ("    let t = v[1..3]\n    return t[1] as i32\n", 30 * 100 + 20),
    "len": ("    let t = v[1..=3]\n    return t.len as i32\n", 3 * 100 + 20),
    "a_name": ("    let t = v[lo..=2]\n    return (t[1] as i32) + t.len as i32\n", 32 * 100 + 20),
    "write": ("    let t = v[1..3]\n    t[0] = 7\n    return 0\n", 7),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(NO_IMPORT_ROWS))
def test_a_span_slice_needs_no_import(run_with, row, compiler):
    body, want = NO_IMPORT_ROWS[row]
    assert run_with(compiler, row, NO_IMPORT.format(body=body)) == want % 256


# There `lo` is read twice, so ritz1 takes a literal or a name only.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_a_call_in_the_bound_needs_span_slice_on_ritz1(compile_with, compiler):
    program = NO_IMPORT.format(body="    let t = v[idx()..3]\n    return t.len as i32\n")
    _refused(compile_with, compiler, "call", program,
             "this slice of a Vec, Span or String isn't lowered by ritz1")


@pytest.mark.integration
def test_a_call_in_the_bound_is_read_once_on_ritz0(run_with):
    program = NO_IMPORT.format(body="    let t = v[idx()..3]\n    return t.len as i32\n")
    assert run_with("ritz0", "call", program) == (200 + 20) % 256
