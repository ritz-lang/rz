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
`(*q)[1]`, and that form is #2331's.
"""

import pytest

import test_ritz1_for_header as for_header
from test_ritz1_for_header import _new

compile_with = for_header.compile_with
run_with = for_header.run_with

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

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
               "    var v: String\n    v.data = vec_new<u8>()\n"
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


# Each returns element 1, or the sum `add` wants.  `{e}` is the element type.
SCALAR_READS = {
    "read": "    return p[1] as i32\n",
    "add": "    return (p[0] + p[1]) as i32\n",
    "at": "    let q: *{e} = @p[1]\n    return *q as i32\n",
    "at_next": "    let q: *{e} = @p[0] + 1\n    return *q as i32\n",
    "at_inferred": "    let q = @p[1]\n    return *q as i32\n",
    "deref_form": "    return (*p)[1] as i32\n",
}
SCALAR_WRITES = {
    "store": ("    p[1] = 7\n", 7),
    "plus_equals": ("    p[1] += 2\n", 22),
    "at_mut": ("    let q: @&{e} = @&p[1]\n    *q = 7\n", 7),
    "deref_form_store": ("    (*p)[1] = 7\n", 7),
    "deref_form_plus_equals": ("    (*p)[1] += 2\n", 22),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("op", sorted(SCALAR_READS))
@pytest.mark.parametrize("box", sorted(SCALARS))
def test_a_read_runs_right(run_with, box, op, kind, compiler):
    ty, elem, setup, _ = SCALARS[box]
    spelled, addr = KINDS[kind]
    want = 30 if op == "add" else 20
    body = SCALAR_READS[op].replace("{e}", elem)
    assert run_with(compiler, op, _reads(spelled, ty, setup, addr, body)) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", WRITABLE)
@pytest.mark.parametrize("op", sorted(SCALAR_WRITES))
@pytest.mark.parametrize("box", sorted(SCALARS))
def test_a_write_lands_in_the_element(run_with, box, op, kind, compiler):
    ty, elem, setup, back = SCALARS[box]
    spelled, addr = KINDS[kind]
    body, want = SCALAR_WRITES[op]
    program = _writes(spelled, ty, setup, addr, body.replace("{e}", elem), back)
    assert run_with(compiler, op, program) == want


# Neighbours keep their values: a wrong stride or width writes past element 1.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", WRITABLE)
@pytest.mark.parametrize("box", sorted(SCALARS))
def test_a_store_leaves_the_neighbours_and_the_header(run_with, box, kind, compiler):
    ty, _, setup, _ = SCALARS[box]
    spelled, addr = KINDS[kind]
    first, last = {"Vec": ("*(v.data)", "*(v.data + 2)"),
                   "Span": ("a[0]", "a[2]"),
                   "String": ("*(v.data.data) as i32", "*(v.data.data + 2) as i32")}[box]
    length = "v.data.len" if box == "String" else "v.len"
    after = f"    return {first} + {last} + {length} as i32\n"
    assert run_with(compiler, "neighbours", _program(
        spelled, ty, setup, addr, "    p[1] = 7\n    return 0\n", after)) == 43


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("op", sorted(STRUCT_READS))
@pytest.mark.parametrize("box", sorted(STRUCTS))
def test_a_field_of_an_element_reads(run_with, box, op, kind, compiler):
    ty, setup, _ = STRUCTS[box]
    spelled, addr = KINDS[kind]
    assert run_with(compiler, op, _reads(spelled, ty, setup, addr, STRUCT_READS[op])) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", WRITABLE)
@pytest.mark.parametrize("op", sorted(STRUCT_WRITES))
@pytest.mark.parametrize("box", sorted(STRUCTS))
def test_a_field_of_an_element_writes(run_with, box, op, kind, compiler):
    ty, setup, back = STRUCTS[box]
    spelled, addr = KINDS[kind]
    body, want = STRUCT_WRITES[op]
    assert run_with(compiler, op, _writes(spelled, ty, setup, addr, body, back)) == want


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


def _refused(compile_with, compiler, name, program, message):
    comp, _, _ = compile_with(compiler, name, program)
    assert comp.returncode != 0, f"{compiler} took {name}"
    out = comp.stdout + comp.stderr
    assert message in out, out[-1000:]
    assert "main.ritz:" in out, f"unlocated: {out[-1000:]}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(SHARED_REFUSALS))
@pytest.mark.parametrize("box", sorted(SCALARS))
def test_a_shared_reference_refuses_a_write(compile_with, box, op, compiler):
    ty, elem, setup, _ = SCALARS[box]
    body, message = SHARED_REFUSALS[op]
    program = _reads("@", ty, setup, "@", body.replace("{e}", elem) + "    return 0\n")
    _refused(compile_with, compiler, op, program, message)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("op", sorted(SHARED_FIELD_REFUSALS))
@pytest.mark.parametrize("box", sorted(STRUCTS))
def test_a_shared_reference_refuses_a_field_write(compile_with, box, op, compiler):
    ty, setup, _ = STRUCTS[box]
    body, message = SHARED_FIELD_REFUSALS[op]
    _refused(compile_with, compiler, op, _reads("@", ty, setup, "@", body + "    return 0\n"), message)


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", WRITABLE)
@pytest.mark.parametrize("ty", sorted(ELEMENTS))
def test_every_element_type_at_its_own_width(run_with, ty, kind, compiler):
    fill, other = ELEMENTS[ty]
    spelled, addr = KINDS[kind]
    program = f"""\
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
"""
    assert run_with(compiler, ty, program) == 0


# A float element straight into arithmetic and a comparison: its type picks the op.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("ty", ["f32", "f64"])
def test_a_float_element_in_an_expression(run_with, ty, kind, compiler):
    spelled, addr = KINDS[kind]
    program = f"""\
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
"""
    assert run_with(compiler, "float", program) == 4


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("name", sorted(FIELD_READS))
def test_a_field_keeps_its_own_type(run_with, name, kind, compiler):
    spelled, addr = KINDS[kind]
    program = f"""\
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
"""
    assert run_with(compiler, name, program) == 0


# A byte above 127 keeps its value when it widens: `*(p + i)`'s sign, not i8's.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("ty", ["Vec<u8>", "String"])
def test_an_unsigned_byte_widens_without_its_sign(run_with, ty, kind, compiler):
    spelled, addr = KINDS[kind]
    setup = (_new("u8", (1, 200)) if ty == "Vec<u8>" else
             "    var v: String\n    v.data = vec_new<u8>()\n    v.data.push(1)\n    v.data.push(200)\n")
    body = "    if p[1] as i64 != 200\n        return 1\n    if p[1] < 100\n        return 2\n    return 0\n"
    assert run_with(compiler, "byte", _reads(spelled, ty, setup, addr, body)) == 0


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(HOLDERS))
def test_every_way_of_holding_it(run_with, name, compiler):
    program = (f"{HEADER}fn id(x: i32) -> i32\n    return x\n\n"
               f"pub fn main() -> i32\n{_new('i32', (10, 20, 30))}{HOLDERS[name]}")
    assert run_with(compiler, name, program) == 20


# An alias is the type it names, behind a pointer or as the pointer.
ALIASES = "type IntVec = Vec<i32>\ntype Row = [3]i32\ntype VecRef = @Vec<i32>\ntype IntRef = @i32\ntype Num = i32\n\n"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_an_alias_of_a_vec_sees_through(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = (f"{HEADER}{ALIASES}fn f(p: {spelled}IntVec) -> i32\n    return p[1]\n\n"
               f"pub fn main() -> i32\n{_new('i32', (10, 20, 30))}    return f({addr}v)\n")
    assert run_with(compiler, "alias", program) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_an_alias_of_an_array_indexes(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = (f"{HEADER}{ALIASES}fn f(p: {spelled}Row) -> i32\n    return p[1]\n\n"
               f"pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n    return f({addr}a)\n")
    assert run_with(compiler, "alias", program) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_alias_of_a_reference_to_a_vec_sees_through(run_with, compiler):
    program = (f"{HEADER}{ALIASES}fn f(p: VecRef) -> i32\n    return p[1]\n\n"
               f"pub fn main() -> i32\n{_new('i32', (10, 20, 30))}    return f(@v)\n")
    assert run_with(compiler, "alias", program) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("param", ["p: IntRef", "p: @Num", "p: @&Num"])
def test_an_alias_of_a_scalar_is_not_a_buffer(compile_with, param, compiler):
    program = f"{HEADER}{ALIASES}fn f({param}) -> i32\n    return p[1]\n\npub fn main() -> i32\n    return 0\n"
    _refused(compile_with, compiler, "alias", program, NOT_A_BUFFER)


# A generic body sees the instantiated pointee.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", WRITABLE)
def test_a_generic_fn(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = f"""\
{HEADER}fn swap_ends<T>(p: {spelled}Vec<T>)
    let t: T = p[0]
    p[0] = p[2]
    p[2] = t

pub fn main() -> i32
{_new('i32', (10, 20, 30))}    swap_ends<i32>({addr}v)
    return *(v.data) + *(v.data + 2) / 10
"""
    assert run_with(compiler, "generic", program) == 31


# A store runs its index once.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_store_runs_its_index_once(run_with, compiler):
    program = f"""\
{HEADER}var G: i64 = 0

fn next() -> i64
    G = G + 1
    return G

fn f(p: *Vec<i32>)
    p[next()] = 7

pub fn main() -> i32
{_new('i32', (10, 20, 30))}    f(@v)
    return *(v.data + 1) + G as i32
"""
    assert run_with(compiler, "once", program) == 8


# What isn't a pointer or reference to a Vec isn't this rule's, though it names one.
NOT_THROUGH = {
    "array_of_vecs": ("    var a: [2]Vec<i32>\n    a[0] = vec_new<i32>()\n    a[1] = vec_new<i32>()\n"
                      "    vec_push<i32>(@&a[1], 1)\n    vec_push<i32>(@&a[1], 2)\n"
                      "    return a[1].len as i32\n", 2),
    "the_vec_itself": (_new("i32", (10, 20, 30)) + "    return v[1] / 10\n", 2),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_THROUGH))
def test_a_value_is_not_seen_through(run_with, name, compiler):
    body, want = NOT_THROUGH[name]
    assert run_with(compiler, name, f"{HEADER}pub fn main() -> i32\n{body}") == want


# ritz0's checker, which is off by default, has the element too.
@pytest.mark.integration
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("box", sorted(SCALARS))
def test_the_type_checker_sees_the_element(tmp_path, box, kind):
    ty, elem, setup, _ = SCALARS[box]
    spelled, addr = KINDS[kind]
    src = tmp_path / "main.ritz"
    src.write_text(_reads(spelled, ty, setup, addr, f"    let e: {elem} = p[1]\n    return e as i32\n"))
    comp = for_header.ritz0_inproc.run_ritz0([str(src), "--check-types", "-o", str(tmp_path / "main.ll")],
                                             cwd=tmp_path, env=for_header.ENV, timeout=300)
    assert comp.returncode == 0, comp.stdout + comp.stderr


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
                "    var a: [2]Vec<i32>\n    a[0] = vec_new<i32>()\n    a[1] = vec_new<i32>()\n"
                "    vec_push<i32>(@&a[1], 1)\n    vec_push<i32>(@&a[1], 2)\n    return f(@a[0])\n", 2),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RAW))
def test_a_raw_buffer_stays_one(run_with, name, compiler):
    decl, body, want = RAW[name]
    program = f"{HEADER}{decl}\npub fn main() -> i32\n{body}"
    assert run_with(compiler, name, program) == want


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(NOT_BUFFERS))
def test_a_reference_is_not_a_buffer(compile_with, name, compiler):
    params, body = NOT_BUFFERS[name]
    program = f"{HEADER}fn f({params}) -> i32\n{body}\npub fn main() -> i32\n    return 0\n"
    comp, _, _ = compile_with(compiler, name, program)
    assert comp.returncode != 0, f"{compiler} took {name}"
    out = comp.stdout + comp.stderr
    assert NOT_A_BUFFER in out, out[-1000:]
    # At the index's own base, the same place on all three.
    first_line = body.splitlines()[0]
    column = 1 + min(first_line.index(n) for n in ("p[", "q[") if n in first_line)
    assert f"main.ritz:10:{column}:" in out, out[-1000:]


# A write through `@T` is §3.2's first, on all three, whatever is behind it.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_write_through_a_shared_scalar_is_section_3_2s(compile_with, compiler):
    program = f"{HEADER}fn f(p: @i32) -> i32\n    p[1] = 7\n    return 0\n\npub fn main() -> i32\n    return 0\n"
    _refused(compile_with, compiler, "shared", program, SHARED_WRITE)


# `let p = @x` is an `@T` too.  An annotated `*T` takes the same `@x` and stays raw.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_inferred_reference_is_not_a_buffer(compile_with, compiler):
    program = (f"{HEADER}pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
               "    let p = @a[0]\n    return p[1]\n")
    comp, _, _ = compile_with(compiler, "inferred", program)
    assert comp.returncode != 0
    assert NOT_A_BUFFER in comp.stdout + comp.stderr
    assert "main.ritz:" in comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_annotated_pointer_takes_the_same_address_and_is_raw(run_with, compiler):
    program = (f"{HEADER}pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
               "    let p: *i32 = @a[0]\n    return p[1]\n")
    assert run_with(compiler, "annotated", program) == 20


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("init", ["@a", "@&a"])
def test_an_inferred_reference_to_an_array_indexes(run_with, init, compiler):
    program = (f"{HEADER}pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
               f"    let p = {init}\n    return p[1]\n")
    assert run_with(compiler, "array", program) == 20


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SLOTS))
def test_a_store_fits_the_element(compile_with, name, compiler):
    ty, stmt, message = SLOTS[name]
    program = f"{HEADER}fn f(p: {ty})\n    {stmt}\n\npub fn main() -> i32\n    return 0\n"
    _refused(compile_with, compiler, name, program, message)


# A condition sees the element too: the element of a `*Vec<bool>` is a bool.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_bool_element_is_a_condition(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    program = f"""\
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
"""
    assert run_with(compiler, "cond", program) == 5


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("place", ["p[1]", "(*p)[1]"])
def test_an_int_element_is_not_a_condition(compile_with, place, compiler):
    program = f"{HEADER}fn f(p: *Vec<i32>) -> i32\n    if {place}\n        return 1\n    return 0\n\npub fn main() -> i32\n    return 0\n"
    _refused(compile_with, compiler, "cond", program, "if condition must be bool")


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
            "    var v: Vec<*S> = vec_new<*S>()\n    vec_push<*S>(@&v, @s0)\n    vec_push<*S>(@&v, @s1)\n"
            "{tail}")
ARRAYS = ("    var v: Vec<A> = vec_new<A>()\n    var e: A\n    e.a[1] = 20\n"
          "    vec_push<A>(@&v, e)\n    vec_push<A>(@&v, e)\n{tail}")
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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("name", sorted(INSIDE))
def test_inside_an_element_reads(run_with, name, kind, compiler):
    spelled, addr = KINDS[kind]
    assert run_with(compiler, name, _inside(spelled, addr, INSIDE[name])) == INSIDE[name][4]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", WRITABLE)
@pytest.mark.parametrize("name", sorted(INSIDE_WRITES))
def test_inside_an_element_writes(run_with, name, kind, compiler):
    spelled, addr = KINDS[kind]
    assert run_with(compiler, name, _inside(spelled, addr, INSIDE_WRITES[name])) == INSIDE_WRITES[name][4]


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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_slice_through_a_pointer(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    assert run_with(compiler, "slice", HEADER + SLICE.format(spelled=spelled, addr=addr)) == 20


# One level out, `(*q)[1]` is the form R9 points at: not this error, and #2331's to lower.
ONE_LEVEL_OUT = [pytest.param(c, marks=pytest.mark.xfail(strict=True, reason="#2331"))
                 for c in ("ritz1", "ritz1_selfhosted")]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", *ONE_LEVEL_OUT])
def test_one_level_out_is_the_deref_form(run_with, compiler):
    program = """\
fn f(q: @*[3]i32) -> i32
    return (*q)[1]

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    let p: *[3]i32 = @a
    return f(@p)
"""
    assert run_with(compiler, "out", program) == 20


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
    vec_push<Vec<i32>>(@&v, a)
    vec_push<Vec<i32>>(@&v, b)
    return f({addr}v)
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_an_element_that_is_a_vec_indexes(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    assert run_with(compiler, "nested", HEADER + NESTED.format(spelled=spelled, addr=addr)) == 20


# A method on an element (#2443): the element is the receiver.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_method_on_an_element(run_with, kind, compiler):
    spelled, addr = KINDS[kind]
    row = ("Vec<A>", ARRAYS, "    return p[1].get1()\n", "    return f({a}v)\n", 20)
    assert run_with(compiler, "method", _inside(spelled, addr, row)) == 20


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
                        "    var v: Vec<*M> = vec_new<*M>()\n    vec_push<*M>(@&v, @m0)\n"
                        "    vec_push<*M>(@&v, @m1)\n",
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


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("holder", sorted(M_HOLDERS))
@pytest.mark.parametrize("name", sorted(M_READS))
def test_a_method_reads_its_element(run_with, name, holder, kind, compiler):
    spelled, addr = KINDS[kind]
    body, want = M_READS[name]
    program = _m_program(spelled, holder, addr, body, "    return r\n")
    assert run_with(compiler, f"m_{name}", program) == want


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", WRITABLE)
@pytest.mark.parametrize("holder", sorted(M_HOLDERS))
@pytest.mark.parametrize("name", sorted(M_WRITES))
def test_a_mutating_method_writes_its_element(run_with, name, holder, kind, compiler):
    spelled, addr = KINDS[kind]
    program = _m_program(spelled, holder, addr, M_WRITES[name], "    return {back}\n")
    assert run_with(compiler, f"m_{name}", program) == 7


# Through an `@T`, a `self: @&M` method is a mutable borrow of the element, as
# `q.sety(7)` is on `q: @M`: refused at the receiver, the same place on all three.
# An element that's a `*M` is the pointer's business, and `self: @M` only reads.
SHARED_INTO_MUT = "an `@T` doesn't fit an `@&T` slot: make it `@&T`"
SHARED_RECEIVERS = {"element": ("p[1].sety(7)", 5), "element_deref": ("(*p)[1].sety(7)", 6)}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("holder", ["Span", "Vec"])
@pytest.mark.parametrize("name", sorted(SHARED_RECEIVERS))
def test_a_shared_reference_refuses_a_mutating_method(compile_with, name, holder, compiler):
    call, col = SHARED_RECEIVERS[name]
    program = _m_program("@", holder, "@", f"    {call}\n    return 0\n", "    return r\n")
    line = program.splitlines().index(f"    {call}") + 1
    _refused(compile_with, compiler, name, program, SHARED_INTO_MUT)
    comp, _, _ = compile_with(compiler, name + "_at", program)
    assert f"main.ritz:{line}:{col}:" in comp.stdout + comp.stderr, (comp.stdout + comp.stderr)[-1000:]


SHARED_LEGAL = {
    "pointer_element": ("Vec_of_pointers", "    p[1].sety(7)\n    return 0\n", "    return {back}\n", 7),
    "pointer_element_deref": ("Vec_of_pointers", "    (*p)[1].sety(7)\n    return 0\n",
                              "    return {back}\n", 7),
    "reading_method": ("Vec", "    return p[1].gety()\n", "    return r\n", 20),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(SHARED_LEGAL))
def test_a_shared_reference_takes_what_does_not_write_its_element(run_with, name, compiler):
    holder, body, after, want = SHARED_LEGAL[name]
    assert run_with(compiler, name, _m_program("@", holder, "@", body, after)) == want


# On the value itself: `v[1].m()` on a Vec or Span local.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("holder", sorted(M_HOLDERS))
def test_a_method_on_an_element_of_a_local(run_with, holder, compiler):
    ty, setup, back = M_HOLDERS[holder]
    program = (f"{HEADER}{M_ELEMENT}pub fn main() -> i32\n{setup}"
               f"    v[1].sety(v[1].gety() + 5)\n    return {back}\n")
    assert run_with(compiler, "m_local", program) == 25


# An element that's a Vec: Vec's own methods (`len`, `get`) on it.  `get` needs
# `vec_get<i32>`, and neither monomorphizer types an element as a receiver, so it's
# never instantiated: undefined `Vec$i32_get` at link, on a local Vec too (#2519).
UNINSTANTIATED = pytest.mark.xfail(strict=True, reason="#2519")
VEC_METHODS = {"len": ("p[1].len() as i32", 2), "get": ("p[1].get(1)", 20)}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("method", sorted(VEC_METHODS))
def test_a_vec_method_on_an_element_that_is_a_vec(run_with, method, kind, compiler, request):
    if method == "get":
        request.applymarker(UNINSTANTIATED)
    spelled, addr = KINDS[kind]
    call, want = VEC_METHODS[method]
    program = HEADER + NESTED.replace("p[1][1]", call).format(spelled=spelled, addr=addr)
    assert run_with(compiler, f"vm_{method}", program) == want


# `let p = @&x` isn't recorded as a reference anywhere (#2445): ritz0 reads past it,
# and ritz1 fails at clang.
INFERRED_MUT = [pytest.param(c, marks=pytest.mark.xfail(strict=True, reason="#2445")) for c in COMPILERS]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", INFERRED_MUT)
def test_an_inferred_mut_reference_is_not_a_buffer(compile_with, compiler):
    program = (f"{HEADER}pub fn main() -> i32\n    var a: [3]i32 = [10, 20, 30]\n"
               "    let p = @&a[0]\n    return p[1]\n")
    comp, _, _ = compile_with(compiler, "inferred", program)
    assert NOT_A_BUFFER in comp.stdout + comp.stderr


# Generic code meets its T when it's instantiated.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_generic_reference_is_refused_once_it_has_a_type(compile_with, compiler):
    program = f"""\
{HEADER}fn g<T>(p: @T) -> T
    return p[1]

pub fn main() -> i32
    var x: i32 = 1
    return g<i32>(@x)
"""
    comp, _, _ = compile_with(compiler, "generic", program)
    assert comp.returncode != 0
    assert NOT_A_BUFFER in comp.stdout + comp.stderr


# The legal form beside the error: a whole array behind a reference.
@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_an_array_behind_a_reference_still_reads(run_with, compiler):
    program = """\
fn f(p: @[3]i32) -> i32
    return p[1]

pub fn main() -> i32
    var a: [3]i32 = [10, 20, 30]
    return f(@a)
"""
    assert run_with(compiler, "array", program) == 20
