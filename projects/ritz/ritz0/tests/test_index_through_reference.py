"""AGAST #2440, LARB R9: `[]` sees through one level to anything indexable.

    p[i]    means (*p)[i] when p is a `*T`, `@T` or `@&T` and T is a Vec, Span or String

and it's a place in every position: read, store, `+=`, `@`, `@&` and `.f`.  Writes
follow §3.2, so `@T` refuses them.  `(*p)[i]` is the same place.

    fn f(p: *Vec<i32>) -> i32
        return p[1]         # ritz0 failed at clang, ritz1 112, selfhosted 160
    p[1] = 7                # through `*Vec<i32>`, ritz1 wrote the Vec's own header
    p[1] = 7                # through `@&Vec<i32>`, ritz1 lost the store

Around that rule, the two forms it isn't:

    `*T`, T not indexable       a raw buffer: `p[i]` is `*(p + i)`, stride T
    `@T`, `@&T`, T not indexable    a located error: a reference is one T, not a buffer

Arrays behind a pointer are #2330 and other bases (`h.r[i]`, `g[i]`, `f()[i]`) are
#2329.  A pointer as the pointee isn't indexable: one level, so `q: @*[3]i32` wants
`(*q)[1]`, which #2331 lowers.

AGAST #3519: the cases are one table (test_table_rows.py), not a parametrised
matrix.  Each `@case` below is what was a test function, and each of its rows
has the id that test's case had, less the compiler: `a_read_runs_right[Span-add-pointer]`
was `test_a_read_runs_right[Span-add-pointer-ritz0]`.  `test_every_row` checks
a chunk of rows per compiler and names each row that fails.
"""

import pytest

import batching
import test_table_rows as table_rows
import test_ritz1_for_header as for_header
from test_table_rows import Refused, Run, case
from test_ritz1_for_header import _new

# A `String`'s `string_new`/`String_drop` are linked from ritzlib/string, whose
# byte Vec (and its Drop) come from gvec (#2159), as test_slice_value_local's
# String rows already do.
STRING_UNITS = ("string", "strview", "hash")


def _string_objects(compiler, ritz1_bin) -> tuple:
    return for_header.library_objects(compiler, ritz1_bin, STRING_UNITS)

# The pointer's spelling and the operator that makes one.
KINDS = {"pointer": ("*", "@"), "reference": ("@", "@"), "mut_reference": ("@&", "@&")}
WRITABLE = ("pointer", "mut_reference")

SHARED_WRITE = "cannot write through an `@T`: make it `@&T`"
SHARED_BORROW = "cannot borrow through an `@T` as mutable: make it `@&T`"
NOT_A_BUFFER = "a reference is one value, not a buffer: `[]` needs an array, Vec, Span or String behind it"

HEADER = """\
import ritzlib.gvec
import ritzlib.span
import ritzlib.string

struct S
    x: i32
    y: i32

"""

# How `v` comes to hold 10, 20, 30, and how main reads element 1 back without `[]`.
SCALARS = {
    "Vec": ("Vec<i32>", "i32", _new("i32", (10, 20, 30)), "*(v.data + 1)"),
    "Span": ("Span<i32>", "i32",
             "    var a: [3]i32 = [10, 20, 30]\n"
             "    var v: Span<i32> = span_from_ptr<i32>(@a[0], 3)\n", "a[1]"),
    "String": ("String", "u8",
               "    var v: String = string_new()\n    v.data = vec_new<u8>()\n"
               "    v.data.push(10)\n    v.data.push(20)\n    v.data.push(30)\n",
               "*(v.data.data + 1) as i32"),
}

# Elements with a field: `x` and `y` differ, and `y` is at a non-zero offset.
STRUCTS = {
    "Vec": ("Vec<S>",
            "    var v: Vec<S> = vec_new<S>()\n"
            "    v.push(S { x: 1, y: 2 })\n    v.push(S { x: 3, y: 20 })\n",
            "(*(v.data + 1)).y"),
    "Span": ("Span<S>",
             "    var a: [2]S\n    a[0].x = 1\n    a[0].y = 2\n    a[1].x = 3\n    a[1].y = 20\n"
             "    var v: Span<S> = span_from_ptr<S>(@a[0], 2)\n",
             "a[1].y"),
}


def _program(spelled: str, ty: str, setup: str, addr: str, body: str, after: str) -> str:
    return (f"{HEADER}fn f(p: {spelled}{ty}) -> i32\n{body}\n"
            f"pub fn main() -> i32\n{setup}    let r: i32 = f({addr}v)\n{after}")


def _reads(spelled, ty, setup, addr, body):
    return _program(spelled, ty, setup, addr, body, "    return r\n")


def _writes(spelled, ty, setup, addr, body, back):
    return _program(spelled, ty, setup, addr, body + "    return 0\n", f"    return {back}\n")


def _refused(compile_with, compiler, name, program, message):
    """For the files that share this one's HEADER: `program` is refused, saying `message`."""
    batch = getattr(compile_with, "batch_compile", None)
    got = batching.refused(compiler, program, batch) if batch else None  # AGAST #2806
    if got is not None:
        out = got[0]  # the batch's diagnostics inside this row's own lines
    else:
        comp, _, _ = compile_with(compiler, name, program)
        assert comp.returncode != 0, f"{compiler} took {name}"
        out = comp.stdout + comp.stderr
    assert message in out, out[-1000:]
    assert "main.ritz:" in out, f"unlocated: {out[-1000:]}"


# Each returns element 1, or the sum `add` wants.  `{e}` is the element type.
SCALAR_READS = {
    "read": "    return p[1] as i32\n",
    "add": "    return (p[0] + p[1]) as i32\n",
    "at": "    let q: *{e} = @p[1]\n    return *q as i32\n",
    "at_next": "    let q: *{e} = @p[0] + 1\n    return *q as i32\n",
    # `as *{e}` keeps the binding untyped while naming the place's type; ritz1
    # otherwise reads the move-only Vec out of the reference to infer it (#2159).
    "at_inferred": "    let q = @p[1] as *{e}\n    return *q as i32\n",
    "deref_form": "    return (*p)[1] as i32\n",
}
SCALAR_WRITES = {
    "store": ("    p[1] = 7\n", 7),
    "plus_equals": ("    p[1] += 2\n", 22),
    "at_mut": ("    let q: @&{e} = @&p[1]\n    *q = 7\n", 7),
    "deref_form_store": ("    (*p)[1] = 7\n", 7),
    "deref_form_plus_equals": ("    (*p)[1] += 2\n", 22),
}


@case(box=sorted(SCALARS), op=sorted(SCALAR_READS), kind=sorted(KINDS))
def a_read_runs_right(box, op, kind):
    ty, elem, setup, _ = SCALARS[box]
    spelled, addr = KINDS[kind]
    body = SCALAR_READS[op].replace("{e}", elem)
    return Run(_reads(spelled, ty, setup, addr, body), 30 if op == "add" else 20)


@case(box=sorted(SCALARS), op=sorted(SCALAR_WRITES), kind=WRITABLE)
def a_write_lands_in_the_element(box, op, kind):
    ty, elem, setup, back = SCALARS[box]
    spelled, addr = KINDS[kind]
    body, want = SCALAR_WRITES[op]
    return Run(_writes(spelled, ty, setup, addr, body.replace("{e}", elem), back), want)


# Neighbours keep their values: a wrong stride or width writes past element 1.
@case(box=sorted(SCALARS), kind=WRITABLE)
def a_store_leaves_the_neighbours_and_the_header(box, kind):
    ty, _, setup, _ = SCALARS[box]
    spelled, addr = KINDS[kind]
    first, last = {"Vec": ("*(v.data)", "*(v.data + 2)"),
                   "Span": ("a[0]", "a[2]"),
                   "String": ("*(v.data.data) as i32", "*(v.data.data + 2) as i32")}[box]
    length = "v.data.len" if box == "String" else "v.len"
    after = f"    return {first} + {last} + {length} as i32\n"
    return Run(_program(spelled, ty, setup, addr, "    p[1] = 7\n    return 0\n", after), 43)


# Every position, for an element with a field.
STRUCT_READS = {
    "field": "    return p[1].y\n",
    "at_field": "    let q: *i32 = @p[1].y\n    return *q\n",
    "whole": "    let s: S = p[1]\n    return s.y\n",
    "at_whole": "    let q: *S = @p[1]\n    return q.y\n",
    "field_in_sum": "    return p[1].y + p[0].y - 2\n",
    "deref_form_field": "    return (*p)[1].y\n",
}
STRUCT_WRITES = {
    "field": ("    p[1].y = 7\n", 7),
    "plus_equals": ("    p[1].y += 2\n", 22),
    "at_mut_field": ("    let q: @&i32 = @&p[1].y\n    *q = 7\n", 7),
    "whole": ("    p[1] = S { x: 5, y: 7 }\n", 7),
    "deref_form_field": ("    (*p)[1].y = 7\n", 7),
}


@case(box=sorted(STRUCTS), op=sorted(STRUCT_READS), kind=sorted(KINDS))
def a_field_of_an_element_reads(box, op, kind):
    ty, setup, _ = STRUCTS[box]
    spelled, addr = KINDS[kind]
    return Run(_reads(spelled, ty, setup, addr, STRUCT_READS[op]), 20)


@case(box=sorted(STRUCTS), op=sorted(STRUCT_WRITES), kind=WRITABLE)
def a_field_of_an_element_writes(box, op, kind):
    ty, setup, back = STRUCTS[box]
    spelled, addr = KINDS[kind]
    body, want = STRUCT_WRITES[op]
    return Run(_writes(spelled, ty, setup, addr, body, back), want)


# §3.2: an `@T` on the way to the place refuses a write, at the statement or the `@&`.
SHARED_REFUSALS = {
    "store": ("    p[1] = 7\n", SHARED_WRITE),
    "plus_equals": ("    p[1] += 2\n", SHARED_WRITE),
    "at_mut": ("    let q: @&{e} = @&p[1]\n    *q = 7\n", SHARED_BORROW),
    "deref_form": ("    (*p)[1] = 7\n", SHARED_WRITE),
}
SHARED_FIELD_REFUSALS = {
    "field": ("    p[1].y = 7\n", SHARED_WRITE),
    "plus_equals": ("    p[1].y += 2\n", SHARED_WRITE),
    "at_mut": ("    let q: @&i32 = @&p[1].y\n    *q = 7\n", SHARED_BORROW),
}


@case(box=sorted(SCALARS), op=sorted(SHARED_REFUSALS))
def a_shared_reference_refuses_a_write(box, op):
    ty, elem, setup, _ = SCALARS[box]
    body, message = SHARED_REFUSALS[op]
    return Refused(_reads("@", ty, setup, "@", body.replace("{e}", elem) + "    return 0\n"), message)


@case(box=sorted(STRUCTS), op=sorted(SHARED_FIELD_REFUSALS))
def a_shared_reference_refuses_a_field_write(box, op):
    ty, setup, _ = STRUCTS[box]
    body, message = SHARED_FIELD_REFUSALS[op]
    return Refused(_reads("@", ty, setup, "@", body + "    return 0\n"), message)


# The element's own width, sign and float-ness, through every kind.  A Span over a
# local array builds each type on every compiler (#2412 keeps `push` off some).
ELEMENTS = {
    "i8": ("-2", "-3"), "u8": ("200", "201"),
    "i16": ("-300", "-301"), "u16": ("40000", "40001"),
    "i32": ("-70000", "-70001"), "u32": ("3000000000", "3000000001"),
    "i64": ("-5000000000", "-5000000001"), "u64": ("5000000000", "5000000001"),
    "f32": ("1.5", "2.5"), "f64": ("1.5", "2.5"),
    "bool": ("true", "false"),
}


@case(ty=sorted(ELEMENTS), kind=WRITABLE)
def every_element_type_at_its_own_width(ty, kind):
    fill, other = ELEMENTS[ty]
    spelled, addr = KINDS[kind]
    return Run(f"""\
{HEADER}fn get(p: {spelled}Span<{ty}>, i: i64) -> {ty}
    return p[i]

fn put(p: {spelled}Span<{ty}>, i: i64, x: {ty})
    p[i] = x

pub fn main() -> i32
    var a: [3]{ty}
    a[0] = {fill}
    a[1] = {fill}
    a[2] = {fill}
    var v: Span<{ty}> = span_from_ptr<{ty}>(@a[0], 3)
    if get({addr}v, 1) != {fill}
        return 1
    put({addr}v, 1, {other})
    if a[1] != {other}
        return 2
    if a[0] != {fill} or a[2] != {fill}
        return 3
    if get({addr}v, 1) != {other}
        return 4
    return 0
""", 0)


# A float element straight into arithmetic and a comparison: its type picks the op.
@case(ty=["f32", "f64"], kind=sorted(KINDS))
def a_float_element_in_an_expression(ty, kind):
    spelled, addr = KINDS[kind]
    return Run(f"""\
{HEADER}fn f(p: {spelled}Span<{ty}>) -> i32
    if p[1] * 2.0 != 5.0
        return 1
    let d: {ty} = p[1] + 1.5
    if d != 4.0
        return 2
    if p[1] < 2.0
        return 3
    return (p[1] + p[0]) as i32

pub fn main() -> i32
    var a: [2]{ty}
    a[0] = 1.5
    a[1] = 2.5
    var v: Span<{ty}> = span_from_ptr<{ty}>(@a[0], 2)
    return f({addr}v)
""", 4)


# A field's own type, through an element: width, sign, float-ness and pointer stride.
FIELDS = """\
enum K
    Red
    Blue

struct Inner
    x: i32
    y: i32

struct W
    f: f64
    u: u8
    n: Inner
    q: *i32
    k: K

"""
FIELD_READS = {
    "float": "    if p[1].f * 2.0 != 5.0\n        return 1\n    return 0\n",
    "unsigned_byte": "    if p[1].u as i64 != 200\n        return 1\n    return 0\n",
    "nested_struct": "    return p[1].n.y - 7\n",
    "pointer_stride": "    return *(p[1].q + 1) - 20\n",
    "inferred_struct": "    let n = p[1].n\n    return n.y - 7\n",
    "enum": "    if p[1].k == K.Blue\n        return 0\n    return 1\n",
}


@case(name=sorted(FIELD_READS), kind=sorted(KINDS))
def a_field_keeps_its_own_type(name, kind):
    spelled, addr = KINDS[kind]
    return Run(f"""\
{HEADER}{FIELDS}fn f(p: {spelled}Span<W>) -> i32
{FIELD_READS[name]}
pub fn main() -> i32
    var b: [2]i32 = [10, 20]
    var a: [2]W
    a[1].f = 2.5
    a[1].u = 200
    a[1].n.y = 7
    a[1].q = @b[0]
    a[1].k = K.Blue
    var v: Span<W> = span_from_ptr<W>(@a[0], 2)
    return f({addr}v)
""", 0)


# A byte above 127 keeps its value when it widens: `*(p + i)`'s sign, not i8's.
@case(ty=["Vec<u8>", "String"], kind=sorted(KINDS))
def an_unsigned_byte_widens_without_its_sign(ty, kind):
    spelled, addr = KINDS[kind]
    setup = (_new("u8", (1, 200)) if ty == "Vec<u8>" else
             "    var v: String = string_new()\n    v.data = vec_new<u8>()\n    v.data.push(1)\n    v.data.push(200)\n")
    body = "    if p[1] as i64 != 200\n        return 1\n    if p[1] < 100\n        return 2\n    return 0\n"
    return Run(_reads(spelled, ty, setup, addr, body), 0)


# However a local comes to hold the pointer, and whatever the index is.
HOLDERS = {
    "let_pointer": "    let p: *Vec<i32> = @v\n    return p[1]\n",
    "let_reference": "    let p: @Vec<i32> = @v\n    return p[1]\n",
    "let_mut_reference": "    let p: @&Vec<i32> = @&v\n    return p[1]\n",
    "var_pointer": "    var p: *Vec<i32> = @v\n    return p[1]\n",
    "inferred_at": "    let p = @v\n    return p[1]\n",
    "inferred_at_mut": "    let p = @&v\n    return p[1]\n",
    "i32_index": "    let p: *Vec<i32> = @v\n    let i: i32 = 1\n    return p[i]\n",
    "i64_index": "    let p: *Vec<i32> = @v\n    let i: i64 = 1\n    return p[i]\n",
    "u8_index": "    let p: *Vec<i32> = @v\n    let i: u8 = 1\n    return p[i]\n",
    "expression_index": "    let p: *Vec<i32> = @v\n    let i: i64 = 3\n    return p[i - 2]\n",
    "element_index": "    let p: *Vec<i32> = @v\n    v.push(1)\n    return p[p[3]]\n",
    "in_a_condition": "    let p: *Vec<i32> = @v\n    if p[1] == 20\n        return p[1]\n    return 0\n",
    "as_an_argument": "    let p: *Vec<i32> = @v\n    return id(p[1])\n",
    "tail": "    let p: *Vec<i32> = @v\n    p[1]\n",
}


@case(name=sorted(HOLDERS))
def every_way_of_holding_it(name):
    return Run(f"{HEADER}fn id(x: i32) -> i32\n    return x\n\n"
               f"pub fn main() -> i32\n{_new('i32', (10, 20, 30))}{HOLDERS[name]}", 20)


# An alias is the type it names, behind a pointer or as the pointer.
ALIASES = "type IntVec = Vec<i32>\ntype Row = [3]i32\ntype VecRef = @Vec<i32>\ntype IntRef = @i32\ntype Num = i32\n\n"


@case(kind=sorted(KINDS))
def an_alias_of_a_vec_sees_through(kind):
    spelled, addr = KINDS[kind]
    return Run(f"{HEADER}{ALIASES}fn f(p: {spelled}IntVec) -> i32\n    return p[1]\n\n"
               f"pub fn main() -> i32\n{_new('i32', (10, 20, 30))}    return f({addr}v)\n", 20)


@case(kind=sorted(KINDS))
def an_alias_of_an_array_indexes(kind):
    spelled, addr = KINDS[kind]
    return Run(f"{HEADER}{ALIASES}fn f(p: {spelled}Row) -> i32\n    return p[1]\n\n"
               f"pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n    return f({addr}a)\n", 20)


@case()
def an_alias_of_a_reference_to_a_vec_sees_through():
    return Run(f"{HEADER}{ALIASES}fn f(p: VecRef) -> i32\n    return p[1]\n\n"
               f"pub fn main() -> i32\n{_new('i32', (10, 20, 30))}    return f(@v)\n", 20)


@case(param=["p: IntRef", "p: @Num", "p: @&Num"])
def an_alias_of_a_scalar_is_not_a_buffer(param):
    return Refused(f"{HEADER}{ALIASES}fn f({param}) -> i32\n    return p[1]\n\n"
                   "pub fn main() -> i32\n    return 0\n", NOT_A_BUFFER)


# A generic body sees the instantiated pointee.
@case(kind=WRITABLE)
def a_generic_fn(kind):
    spelled, addr = KINDS[kind]
    return Run(f"""\
{HEADER}fn swap_ends<T>(p: {spelled}Vec<T>)
    let t: T = p[0]
    p[0] = p[2]
    p[2] = t

pub fn main() -> i32
{_new('i32', (10, 20, 30))}    swap_ends<i32>({addr}v)
    return *(v.data) + *(v.data + 2) / 10
""", 31)


# A store runs its index once.
@case()
def a_store_runs_its_index_once():
    return Run(f"""\
{HEADER}var G: i64 = 0

fn next() -> i64
    G = G + 1
    return G

fn f(p: *Vec<i32>)
    p[next()] = 7

pub fn main() -> i32
{_new('i32', (10, 20, 30))}    f(@v)
    return *(v.data + 1) + G as i32
""", 8)


# What isn't a pointer or reference to a Vec isn't this rule's, though it names one.
NOT_THROUGH = {
    "array_of_vecs": ("    var a: [2]Vec<i32> = [Vec<i32> { data: null, len: 0, cap: 0 }, Vec<i32> { data: null, len: 0, cap: 0 }]\n    a[0] = vec_new<i32>()\n    a[1] = vec_new<i32>()\n"
                      "    a[1].push(1)\n    a[1].push(2)\n"
                      "    return a[1].len as i32\n", 2),
    "the_vec_itself": (_new("i32", (10, 20, 30)) + "    return v[1] / 10\n", 2),
}


@case(name=sorted(NOT_THROUGH))
def a_value_is_not_seen_through(name):
    body, want = NOT_THROUGH[name]
    return Run(f"{HEADER}pub fn main() -> i32\n{body}", want)


# A raw buffer stays one: `*T` with T not indexable, at stride T.
RAW = {
    "scalar_read": ("fn f(p: *i32) -> i32\n    return p[1]\n",
                    "    var a: [3]i32 = [10, 20, 30]\n    return f(@a[0])\n", 20),
    "scalar_store": ("fn f(p: *i32)\n    p[1] = 7\n",
                     "    var a: [3]i32 = [10, 20, 30]\n    f(@a[0])\n    return a[1]\n", 7),
    "struct_field": ("fn f(p: *S) -> i32\n    return p[1].y\n",
                     "    var a: [2]S\n    a[1].y = 20\n    return f(@a[0])\n", 20),
    "strview_is_a_struct_here": (
        "fn f(p: *StrView) -> i32\n    return p[1].len as i32\n",
        "    var a: [2]StrView\n    a[1].len = 3\n    return f(@a[0])\n", 3),
    # Walking rows of Vecs is `p + i`: `p[i]` is an element of the first (R9).
    "vec_row": ("fn f(p: *Vec<i32>) -> i32\n    return (p + 1).len as i32\n",
                "    var a: [2]Vec<i32> = [Vec<i32> { data: null, len: 0, cap: 0 }, Vec<i32> { data: null, len: 0, cap: 0 }]\n    a[0] = vec_new<i32>()\n    a[1] = vec_new<i32>()\n"
                "    a[1].push(1)\n    a[1].push(2)\n    return f(@a[0])\n", 2),
}


@case(name=sorted(RAW))
def a_raw_buffer_stays_one(name):
    decl, body, want = RAW[name]
    return Run(f"{HEADER}{decl}\npub fn main() -> i32\n{body}", want)


# A reference is one T: every way of reaching past it, and the same words from all three.
NOT_BUFFERS = {
    "at_scalar": ("p: @i32", "    return p[1]\n"),
    "at_mut_scalar": ("p: @&i32", "    return p[1]\n"),
    "at_mut_scalar_store": ("p: @&i32", "    p[1] = 7\n    return 0\n"),
    "at_mut_plus_equals": ("p: @&i32", "    p[1] += 2\n    return 0\n"),
    "at_scalar_address": ("p: @i32", "    let q: *i32 = @p[1]\n    return *q\n"),
    "at_mut_address": ("p: @&i32", "    let q: @&i32 = @&p[1]\n    *q = 7\n    return 0\n"),
    "at_scalar_zero": ("p: @i32", "    return p[0]\n"),
    "at_scalar_slice": ("p: @i32", "    let q = p[0..1]\n    return 0\n"),
    "at_struct_field": ("p: @S", "    return p[1].x\n"),
    "at_mut_struct_field": ("p: @&S", "    return p[1].x\n"),
    "at_mut_struct_store": ("p: @&S", "    p[1].x = 7\n    return 0\n"),
    "at_struct_address": ("p: @S", "    let q: *i32 = @p[1].x\n    return *q\n"),
    "at_struct_whole": ("p: @S", "    let s: S = p[1]\n    return s.x\n"),
    "at_pointer_to_array": ("q: @*[3]i32", "    return q[1]\n"),
    "at_mut_pointer_to_array": ("q: @&*[3]i32", "    return q[1]\n"),
    "at_pointer": ("q: @*i32", "    let r: *i32 = q[1]\n    return 0\n"),
    "at_pointer_to_vec": ("q: @*Vec<i32>", "    return q[1]\n"),
    "at_strview": ("p: @StrView", "    return p[1] as i32\n"),
}


@case(name=sorted(NOT_BUFFERS))
def a_reference_is_not_a_buffer(name):
    params, body = NOT_BUFFERS[name]
    # At the index's own base, the same place on all three: line 10 is f's first.
    first_line = body.splitlines()[0]
    column = 1 + min(first_line.index(n) for n in ("p[", "q[") if n in first_line)
    return Refused(f"{HEADER}fn f({params}) -> i32\n{body}\npub fn main() -> i32\n    return 0\n",
                   NOT_A_BUFFER, at=(10, column))


# A write through `@T` is §3.2's first, on all three, whatever is behind it.
@case()
def a_write_through_a_shared_scalar_is_section_3_2s():
    return Refused(f"{HEADER}fn f(p: @i32) -> i32\n    p[1] = 7\n    return 0\n\n"
                   "pub fn main() -> i32\n    return 0\n", SHARED_WRITE)


# `let p = @x` is an `@T` too, and `let p = @&x` an `@&T` (#2445: ritz0 read past
# it, 20; ritz1 failed at clang, later compiled it silently).  Both are refused
# at the `p[1]`, and so is a copy of either.  An annotated `*T` takes the same
# address and stays raw.
@case(copied=[False, True], addr=["@", "@&"])
def an_inferred_reference_is_not_a_buffer(copied, addr):
    program = (f"{HEADER}pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
               f"    let p = {addr}a[0]\n" + ("    let q = p\n    return q[1]\n" if copied
                                                 else "    return p[1]\n"))
    # At the `p[1]` (or `q[1]`), on the line it's on.
    return Refused(program, NOT_A_BUFFER, at=(len(HEADER.splitlines()) + 4 + copied, 12))


@case(addr=["@", "@&"])
def an_annotated_pointer_takes_the_same_address_and_is_raw(addr):
    return Run(f"{HEADER}pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
               f"    let p: *i32 = {addr}a[0]\n    return p[1]\n", 20)


@case(init=["@a", "@&a"])
def an_inferred_reference_to_an_array_indexes(init):
    return Run(f"{HEADER}pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
               f"    let p = {init}\n    return p[1]\n", 20)


# A store checks its value against the element, not the Vec.
SLOTS = {
    "too_wide": ("*Vec<u8>", "p[1] = 300", "`300` does not fit in `u8`"),
    "too_wide_through_a_reference": ("@&Vec<u8>", "p[1] = 300", "`300` does not fit in `u8`"),
    "too_wide_deref_form": ("*Vec<u8>", "(*p)[1] = 300", "`300` does not fit in `u8`"),
    "too_wide_string": ("*String", "p[1] = 300", "`300` does not fit in `u8`"),
    "too_wide_span": ("@&Span<i8>", "p[1] = 200", "`200` does not fit in `i8`"),
    "bool_into_int": ("*Vec<i32>", "p[1] = true", "cannot use bool as an integer"),
    "bool_into_int_deref_form": ("*Vec<i32>", "(*p)[1] = true", "cannot use bool as an integer"),
    "int_into_bool": ("*Vec<bool>", "p[1] = 1", "cannot use an integer as bool"),
    "int_into_bool_reference": ("@&Span<bool>", "p[1] = 1", "cannot use an integer as bool"),
    "string_into_int": ("*Vec<i32>", 'p[1] = "abc"', "a string literal does not fit"),
}


@case(name=sorted(SLOTS))
def a_store_fits_the_element(name):
    ty, stmt, message = SLOTS[name]
    return Refused(f"{HEADER}fn f(p: {ty})\n    {stmt}\n\npub fn main() -> i32\n    return 0\n", message)


# A condition sees the element too: the element of a `*Vec<bool>` is a bool.
@case(kind=sorted(KINDS))
def a_bool_element_is_a_condition(kind):
    spelled, addr = KINDS[kind]
    return Run(f"""\
{HEADER}fn f(p: {spelled}Span<bool>) -> i32
    if p[1]
        return 5
    return 6

pub fn main() -> i32
    var a: [2]bool
    a[0] = false
    a[1] = true
    var v: Span<bool> = span_from_ptr<bool>(@a[0], 2)
    return f({addr}v)
""", 5)


@case(place=["p[1]", "(*p)[1]"])
def an_int_element_is_not_a_condition(place):
    return Refused(f"{HEADER}fn f(p: *Vec<i32>) -> i32\n    if {place}\n        return 1\n    return 0\n\n"
                   "pub fn main() -> i32\n    return 0\n", "if condition must be bool")


# A pointer element, and an array inside an element.
A_ELEMENT = """\
struct A
    n: i32
    a: [3]i32

impl A
    fn get1(self: @A) -> i32
        return self.a[1]

"""
POINTERS = ("    var s0: S = S {{ x: 1, y: 2 }}\n    var s1: S = S {{ x: 3, y: 20 }}\n"
            "    var v: Vec<*S> = vec_new<*S>()\n    v.push(@s0)\n    v.push(@s1)\n"
            "{tail}")
ARRAYS = ("    var v: Vec<A> = vec_new<A>()\n    var e: A\n    e.a[1] = 20\n"
          "    v.push(e)\n    v.push(e)\n{tail}")
INSIDE = {
    "pointer_element_field": ("Vec<*S>", POINTERS, "    return p[1].y\n", "    return f({a}v)\n", 20),
    "pointer_element": ("Vec<*S>", POINTERS, "    let q: *S = p[1]\n    return q.y\n",
                        "    return f({a}v)\n", 20),
    "array_in_element": ("Vec<A>", ARRAYS, "    return p[1].a[1]\n", "    return f({a}v)\n", 20),
}
INSIDE_WRITES = {
    "pointer_element_field": ("Vec<*S>", POINTERS, "    p[1].y = 7\n    return 0\n",
                              "    f({a}v)\n    return s1.y\n", 7),
    "array_in_element": ("Vec<A>", ARRAYS, "    p[1].a[1] = 7\n    return 0\n",
                         "    f({a}v)\n    return (*(v.data + 1)).a[1]\n", 7),
}


def _inside(spelled, addr, row):
    ty, setup, body, tail, _ = row
    return (f"{HEADER}{A_ELEMENT}fn f(p: {spelled}{ty}) -> i32\n{body}\n"
            f"pub fn main() -> i32\n{setup.format(tail=tail.format(a=addr))}")


@case(name=sorted(INSIDE), kind=sorted(KINDS))
def inside_an_element_reads(name, kind):
    spelled, addr = KINDS[kind]
    return Run(_inside(spelled, addr, INSIDE[name]), INSIDE[name][4])


@case(name=sorted(INSIDE_WRITES), kind=WRITABLE)
def inside_an_element_writes(name, kind):
    spelled, addr = KINDS[kind]
    return Run(_inside(spelled, addr, INSIDE_WRITES[name]), INSIDE_WRITES[name][4])


# A range isn't an element: `p[lo..hi]` slices what `p` points at, on all three
# (#2448; the table is test_slice_through_reference.py).  ritz1 read garbage here,
# then refused it.
SLICE = """\
fn f(p: {spelled}Span<i32>) -> i32
    let t = p[1..3]
    return t[0]

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    var v: Span<i32> = span_from_ptr<i32>(@a[0], 3)
    return f({addr}v)
"""


@case(kind=sorted(KINDS))
def a_slice_through_a_pointer(kind):
    spelled, addr = KINDS[kind]
    return Run(HEADER + SLICE.format(spelled=spelled, addr=addr), 20)


# One level out, `(*q)[1]` is the form R9 points at: not this error (#2331).
@case()
def one_level_out_is_the_deref_form():
    return Run("""\
fn f(q: @*[3]i32) -> i32
    return (*q)[1]

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    let p: *[3]i32 = @a
    return f(@p)
""", 20)


# AGAST #2557: `let p = *q` copies that `*[3]i32` out, so p is a pointer and
# indexes, a store included.  ritz0 kept q's reference type for `*q`, and refused
# `p[1]` as one value.  ritz1's side of a `@*[N]T` param is #2331's.
@case(compilers=("ritz0",), ref=["@", "@&"])
def one_level_out_copied_is_the_pointer(ref):
    return Run(f"""\
fn f(q: {ref}*[3]i32) -> i32
    let p = *q
    p[2] = 4
    return p[1] + p[2]

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    var p: *[3]i32 = @a
    return f({ref}p) + a[2]
""", 28)


# `p[1][1]`: the base is itself an element (#2442).  Its stores are in
# test_index_value_local.py.
NESTED = """\
fn f(p: {spelled}Vec<Vec<i32>>) -> i32
    return p[1][1]

pub fn main() -> i32
    var v: Vec<Vec<i32>> = vec_new<Vec<i32>>()
    var a: Vec<i32> = vec_new<i32>()
    var b: Vec<i32> = vec_new<i32>()
    b.push(10)
    b.push(20)
    v.push(a)
    v.push(b)
    return f({addr}v)
"""


@case(kind=sorted(KINDS))
def an_element_that_is_a_vec_indexes(kind):
    spelled, addr = KINDS[kind]
    return Run(HEADER + NESTED.format(spelled=spelled, addr=addr), 20)


# A method on an element (#2443): the element is the receiver.
@case(kind=sorted(KINDS))
def a_method_on_an_element(kind):
    spelled, addr = KINDS[kind]
    row = ("Vec<A>", ARRAYS, "    return p[1].get1()\n", "    return f({a}v)\n", 20)
    return Run(_inside(spelled, addr, row), 20)


# The element is the receiver, in place: `self: @M` reads it, `self: @&M` writes it,
# `self: M` takes a copy.  `y` is at a non-zero offset, so a receiver at the wrong
# address reads `x`.
M_ELEMENT = """\
struct M
    x: i32
    y: i32

impl M
    fn gety(self: @M) -> i32
        return self.y
    fn sety(self: @&M, v: i32)
        self.y = v
    fn sum(self: M) -> i32
        return self.x + self.y

"""
M_HOLDERS = {
    "Vec": ("Vec<M>",
            "    var v: Vec<M> = vec_new<M>()\n"
            "    v.push(M { x: 1, y: 2 })\n    v.push(M { x: 3, y: 20 })\n",
            "(*(v.data + 1)).y"),
    "Span": ("Span<M>",
             "    var a: [2]M\n    a[0].x = 1\n    a[0].y = 2\n    a[1].x = 3\n    a[1].y = 20\n"
             "    var v: Span<M> = span_from_ptr<M>(@a[0], 2)\n",
             "a[1].y"),
    "Vec_of_pointers": ("Vec<*M>",
                        "    var m0: M = M { x: 1, y: 2 }\n    var m1: M = M { x: 3, y: 20 }\n"
                        "    var v: Vec<*M> = vec_new<*M>()\n    v.push(@m0)\n"
                        "    v.push(@m1)\n",
                        "m1.y"),
}
# A call through `(*p)[1]` and `p[1]`, and what f returns.
M_READS = {
    "read": ("    return p[1].gety()\n", 20),
    "read_deref": ("    return (*p)[1].gety()\n", 20),
    "by_value": ("    return p[1].sum()\n", 23),
    "in_expression": ("    return p[1].gety() + p[0].gety()\n", 22),
}
M_WRITES = {
    "write": "    p[1].sety(7)\n    return 0\n",
    "write_deref": "    (*p)[1].sety(7)\n    return 0\n",
}


def _m_program(spelled, holder, addr, body, after):
    ty, setup, back = M_HOLDERS[holder]
    return (f"{HEADER}{M_ELEMENT}fn f(p: {spelled}{ty}) -> i32\n{body}\n"
            f"pub fn main() -> i32\n{setup}    let r: i32 = f({addr}v)\n"
            + after.format(back=back))


@case(name=sorted(M_READS), holder=sorted(M_HOLDERS), kind=sorted(KINDS))
def a_method_reads_its_element(name, holder, kind):
    spelled, addr = KINDS[kind]
    body, want = M_READS[name]
    return Run(_m_program(spelled, holder, addr, body, "    return r\n"), want)


@case(name=sorted(M_WRITES), holder=sorted(M_HOLDERS), kind=WRITABLE)
def a_mutating_method_writes_its_element(name, holder, kind):
    spelled, addr = KINDS[kind]
    return Run(_m_program(spelled, holder, addr, M_WRITES[name], "    return {back}\n"), 7)


# Through an `@T`, a `self: @&M` method is a mutable borrow of the element, as
# `q.sety(7)` is on `q: @M`: refused at the receiver, the same place on all three.
# An element that's a `*M` is the pointer's business, and `self: @M` only reads.
SHARED_INTO_MUT = "an `@T` doesn't fit an `@&T` slot: make it `@&T`"
SHARED_RECEIVERS = {"element": ("p[1].sety(7)", 5), "element_deref": ("(*p)[1].sety(7)", 6)}


@case(name=sorted(SHARED_RECEIVERS), holder=["Span", "Vec"])
def a_shared_reference_refuses_a_mutating_method(name, holder):
    call, col = SHARED_RECEIVERS[name]
    program = _m_program("@", holder, "@", f"    {call}\n    return 0\n", "    return r\n")
    line = program.splitlines().index(f"    {call}") + 1
    return Refused(program, SHARED_INTO_MUT, at=(line, col))


SHARED_LEGAL = {
    "pointer_element": ("Vec_of_pointers", "    p[1].sety(7)\n    return 0\n", "    return {back}\n", 7),
    "pointer_element_deref": ("Vec_of_pointers", "    (*p)[1].sety(7)\n    return 0\n",
                              "    return {back}\n", 7),
    "reading_method": ("Vec", "    return p[1].gety()\n", "    return r\n", 20),
}


@case(name=sorted(SHARED_LEGAL))
def a_shared_reference_takes_what_does_not_write_its_element(name):
    holder, body, after, want = SHARED_LEGAL[name]
    return Run(_m_program("@", holder, "@", body, after), want)


# On the value itself: `v[1].m()` on a Vec or Span local.
@case(holder=sorted(M_HOLDERS))
def a_method_on_an_element_of_a_local(holder):
    _, setup, back = M_HOLDERS[holder]
    return Run(f"{HEADER}{M_ELEMENT}pub fn main() -> i32\n{setup}"
               f"    v[1].sety(v[1].gety() + 5)\n    return {back}\n", 25)


# An element that's a Vec: Vec's own methods (`len`, `get`) on it.  `get` needs
# `vec_get<i32>`, so each monomorphizer has to type the element as the receiver,
# or it's never instantiated: undefined `Vec$i32_get` at link (#2519).
VEC_METHODS = {"len": ("p[1].len() as i32", 2), "get": ("p[1].get(1)", 20)}


@case(method=sorted(VEC_METHODS), kind=sorted(KINDS))
def a_vec_method_on_an_element_that_is_a_vec(method, kind):
    spelled, addr = KINDS[kind]
    call, want = VEC_METHODS[method]
    return Run(HEADER + NESTED.replace("p[1][1]", call).format(spelled=spelled, addr=addr), want)


# The same on the local Vec itself: no reference in the way (#2519).
@case()
def a_vec_method_on_an_element_of_a_local_vec():
    return Run(HEADER + NESTED.replace("return f({addr}v)", "return v[1].get(1)").format(spelled="*"), 20)


# The other bases an element receiver is reached from (#2519): `(*p)[i]`, a
# field, and an un-annotated `let` of an element, which ritz0 types the same way.
# Batched, the rows share one compile and so one `vec_get$i32`; a row that never
# registers it is caught by its own compile, which needs an external `Vec$i32_get`
# the batch didn't (#2867), and then fails alone.
ELEMENT_RECEIVERS = {
    "deref_form": "fn f(p: *Vec<Vec<i32>>) -> i32\n    return (*p)[1].get(1)\n",
    # `Vec` is move-only (#2159), so the field is built in place and its element
    # is a borrowed receiver; a clone out of `p` would move its elements.
    "field": ("fn f(p: *Vec<Vec<i32>>) -> i32\n"
              "    var h: H = H { vv: vec_new<Vec<i32>>() }\n"
              "    h.vv.push(vec_new<i32>())\n    h.vv.push(vec_new<i32>())\n"
              "    h.vv[1].push(10)\n    h.vv[1].push(20)\n"
              "    return h.vv[1].get(1)\n"),
    "let_element": "fn f(p: *Vec<Vec<i32>>) -> i32\n    let w: *Vec<i32> = p.get_ptr(1)\n    return w.get(1)\n",
}


@case(form=sorted(ELEMENT_RECEIVERS))
def a_vec_method_on_an_element_reached_another_way(form):
    _, _, rest = NESTED.partition("pub fn main")
    return Run(HEADER + "struct H\n    vv: Vec<Vec<i32>>\n\n" + ELEMENT_RECEIVERS[form]
               + "\npub fn main" + rest.format(addr="@"), 20)


# Generic code meets its T when it's instantiated.
@case()
def a_generic_reference_is_refused_once_it_has_a_type():
    return Refused(f"""\
{HEADER}fn g<T>(p: @T) -> T
    return p[1]

pub fn main() -> i32
    var x: i32 = 1
    return g<i32>(@x)
""", NOT_A_BUFFER, located=False)


# The legal form beside the error: a whole array behind a reference.
@case()
def an_array_behind_a_reference_still_reads():
    return Run("""\
fn f(p: @[3]i32) -> i32
    return p[1]

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    return f(@a)
""", 20)


TABLE = table_rows.cases(globals())


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(TABLE),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(TABLE)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    def strings(compiler):
        return _string_objects(compiler, ritz1_bin)

    table_rows.assert_rows(compiler, table_rows.chunk(TABLE, compiler, chunk),
                           build=for_header.batch_build(ritz1_bin, strings),
                           compile=for_header.batch_compile(ritz1_bin), work=tmp_path)


# ritz0's checker, which is off by default, has the element too.  Its own flag, so
# its own loop: one row per box and kind, ids as the table's.
TYPE_CHECKED = [
    (f"the_type_checker_sees_the_element[{box}-{kind}]",
     _reads(KINDS[kind][0], SCALARS[box][0], SCALARS[box][2], KINDS[kind][1],
            f"    let e: {SCALARS[box][1]} = p[1]\n    return e as i32\n"))
    for box in sorted(SCALARS) for kind in sorted(KINDS)]
OUTSIDE_TABLE = [rid for rid, _ in TYPE_CHECKED]


@pytest.mark.integration
def test_the_type_checker_sees_the_element(tmp_path):
    failures = []
    for n, (rid, program) in enumerate(TYPE_CHECKED):
        here = tmp_path / str(n)
        here.mkdir()
        src = here / "main.ritz"
        src.write_text(program)
        comp = for_header.ritz0_inproc.run_ritz0([str(src), "-o", str(here / "main.ll")],
                                                 cwd=here, env=for_header.ENV, timeout=300)
        if comp.returncode != 0:
            failures.append(f"ritz0 {rid}:\n" + (comp.stdout + comp.stderr)[-800:])
    assert not failures, "\n".join(failures)
