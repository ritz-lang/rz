"""AGAST #3654: memory is sized by the padded LLVM alloc size, not the field sum.

THE DEFECT

ritz0's `_emit_heap_expr` sized `heap <value>`'s malloc with
`_type_size_bytes`, which sums field sizes and ignores padding.  For

    struct P
        a: u8
        b: i64
        c: u8

`heap P { .. }` emitted `malloc(i64 10)` and then stored the 24-byte `%P`
into it: a 14-byte heap overflow.  ritzlib's malloc hands a 10-byte request a
16-byte block whose neighbour's 16-byte header follows, so the store's tail
overwrote that header.  Each program below frees a block so the `heap` value
reuses it, then checks the next block's header is unchanged: a deterministic
canary, no ASan needed.

The same family, fixed here too:
- `_sizeof_type` (the memset size of a large scalar array fill) measured an
  `i1` as `1 // 8 == 0` bytes, so `[false; 100]` memset nothing and the bools
  stayed uninitialised.  It now measures by `_abi_size_align`.
- AGAST #3655: `_ritz_type_size_and_align`'s fallback for a synthesized
  built-in generic struct returned `(_type_size_bytes, 8)`: unpadded, with the
  alignment hardcoded.  It now returns `_abi_size_align`.  The only such
  struct today is `Span<T>`, `{ ptr, i64 }`, where the two agree, so that
  case is pinned by a unit test with a padded body.

AGAST #3664: `heap W<P> { .. }`, a generic literal directly under `heap`,
crashed with "Unknown struct: W": the monomorphizer's instantiation walk never
entered `heap`.  The `generic_lit*` cases pin it, parenthesised and nested.

AGAST #3934: ritz1 lowers `heap e` to ritzlib.memory's `__heap_new<T>`,
which mallocs `sizeof(T)`.  The block canary runs on all three compilers;
the malloc-size read of the IR is ritz0's (ritz1's size is sizeof's).  The
padded structs ritzlib's generic containers hold (Box<T>, Vec<T>, sized by
`sizeof(T)`), and the bool fills, run on all three.
"""

import re

import llvmlite.binding as llvm
import pytest
from llvmlite import ir

import ritz_ast as rast
import test_ritz1_for_header as for_header
import test_table_rows as table_rows
from emitter_llvmlite import LLVMEmitter
from test_borrow_param_ref_field import _compile
from test_table_rows import Row, Run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# The three rules below are tables (AGAST #4418): each row used to launch its
# own `build.py` package, paying a Python start and a cold build cache.  As
# rows of one table per rule, every ritzlib module a chunk imports is compiled
# once per process per compiler (#3906); a failing row is compiled again alone
# and named.  `xdist_group` keeps the three tables on one worker so they share
# those objects.
pytestmark = pytest.mark.xdist_group("heap_padded_size")

HEAD = """\
import ritzlib.memory
import ritzlib.box
import ritzlib.gvec

struct P
    a: u8
    b: i64
    c: u8

struct O
    x: u8
    inner: P

struct W<T>
    tag: u8
    v: T

# The 16-byte block header ritzlib's malloc puts before every block.
fn hdr(q: *u8) -> i64
    let h: *i64 = (q as i64 - 16) as *i64
    h[0]

"""

# name: (malloc size class, statements that heap-allocate `p`, a check that
# `p` holds what was stored, the padded size ritz0 must malloc).  The value
# reuses block `a`, the size class an unpadded size picks; `b` follows it.
HEAPS = {
    # 10 unpadded, 24 padded: `c` (90) lands on b's header.
    "struct": (
        16,
        "    let p = heap P { a: 1, b: 2, c: 90 }\n",
        "p.a == 1 and p.b == 2 and p.c == 90",
        24,
    ),
    # 11 unpadded, 32 padded: `inner.b` (77) lands on b's header.
    "nested": (
        16,
        "    let p = heap O { x: 1, inner: P { a: 2, b: 77, c: 3 } }\n",
        "p.x == 1 and p.inner.b == 77 and p.inner.c == 3",
        32,
    ),
    # A generic instance of a padded struct: 11 unpadded, 32 padded.
    "generic": (
        16,
        (
            "    let w = W<P> { tag: 1, v: P { a: 2, b: 77, c: 3 } }\n"
            "    let p = heap w\n"
        ),
        "p.tag == 1 and p.v.b == 77 and p.v.c == 3",
        32,
    ),
    # AGAST #3664: the generic literal directly under `heap`.  The
    # monomorphizer's instantiation walk never entered `heap`, so `W<P>` was
    # never instantiated and the emitter raised "Unknown struct: W".
    "generic_lit": (
        16,
        "    let p = heap W<P> { tag: 1, v: P { a: 2, b: 77, c: 3 } }\n",
        "p.tag == 1 and p.v.b == 77 and p.v.c == 3",
        32,
    ),
    "generic_lit_paren": (
        16,
        "    let p = heap (W<P> { tag: 1, v: P { a: 2, b: 77, c: 3 } })\n",
        "p.tag == 1 and p.v.b == 77 and p.v.c == 3",
        32,
    ),
    # {u8, W<P>}: 12 unpadded, 40 padded; W<P> is instantiated only here.
    "generic_lit_nested": (
        16,
        (
            "    let p = heap W<W<P>> { tag: 1, v: W<P> { tag: 2,"
            " v: P { a: 4, b: 77, c: 5 } } }\n"
        ),
        "p.tag == 1 and p.v.tag == 2 and p.v.v.b == 77 and p.v.v.c == 5",
        40,
    ),
    # An array of padded structs: 20 unpadded, 48 padded: the second
    # element's `b` (55) lands on b's header (offset 32).
    "array": (
        32,
        "    let p = heap [P { a: 1, b: 2, c: 3 }, P { a: 4, b: 55, c: 6 }]\n",
        "p[0].c == 3 and p[1].b == 55 and p[1].c == 6",
        48,
    ),
}


def _heap_program(name):
    size, alloc, check, _ = HEAPS[name]
    return HEAD + (
        "pub fn main() -> i32\n"
        f"    let a: *u8 = malloc({size})\n"
        f"    let b: *u8 = malloc({size})\n"
        "    free(a)\n"
        "    let before = hdr(b)\n"
        f"{alloc}"
        "    if hdr(b) != before\n"
        "        return 1\n"
        f"    if not ({check})\n"
        "        return 2\n"
        "    0\n"
    )


# x86-64 Linux, as clang writes it (test_byval_exact_size.py's oracle, #1744).
X86_64_DATA_LAYOUT = (
    "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-i128:128-f80:128-n8:16:32:64-S128"
)


def _malloc_sizes(text):
    """Each `heap` malloc's size in bytes, a `gep (T* null, 1)` folded by LLVM."""
    td = llvm.create_target_data(X86_64_DATA_LAYOUT)
    sizes = []
    for arg in re.findall(
        r'%"heap_ptr[.\d]*" = call i8\* @"malloc"\(i64 (.*)\), !dbg', text
    ):
        if arg.isdigit():
            sizes.append(int(arg))
            continue
        gep = re.fullmatch(
            r"ptrtoint \((.+)\* getelementptr \(\1, \1\* null, i32 1\) to i64\)", arg
        )
        assert gep, f"unexpected malloc size: {arg}"
        probe = llvm.parse_assembly(
            text + f"\n@__probe = external global {gep.group(1)}\n"
        )
        sizes.append(
            td.get_abi_size(probe.get_global_variable("__probe").global_value_type)
        )
    return sizes


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(HEAPS))
def test_ritz0_heap_mallocs_the_padded_size(tmp_path, name):
    comp, ll, _ = _compile("ritz0", None, tmp_path, name, _heap_program(name))
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    assert _malloc_sizes(ll.read_text()) == [HEAPS[name][3]]


# HEAPS rows ritz1 can't build yet, each with its ticket (none today: the
# `array` row was AGAST #3986, test_ritz1_heap_array_lit.py).
RITZ1_HEAP_GAPS: dict[str, int] = {}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_heap_store_stays_in_its_block(ritz1_bin, tmp_path, compiler):
    rows = [Row(f"heap_store_stays_in_its_block[{name}]", (compiler,),
                Run(_heap_program(name), 0))
            for name in sorted(HEAPS)]
    gaps = ({} if compiler == "ritz0" else
            {f"heap_store_stays_in_its_block[{name}]": ticket
             for name, ticket in RITZ1_HEAP_GAPS.items()})
    table_rows.assert_rows(
        compiler, rows, build=table_rows.ritzlib_build(ritz1_bin),
        compile=for_header.batch_compile(ritz1_bin), work=tmp_path, gaps=gaps)


# Ritzlib's generic containers of a padded struct, on every compiler.
CONTAINERS = {
    # box_new mallocs sizeof(P): an unpadded 10 would reuse `a` (class 16)
    # and the store would land on b's header.
    "box": (
        "    let a: *u8 = malloc(16)\n"
        "    let b: *u8 = malloc(16)\n"
        "    free(a)\n"
        "    let before = hdr(b)\n"
        "    let bx = box_new<P>(P { a: 1, b: 2, c: 90 })\n"
        "    if hdr(b) != before\n"
        "        return 1\n"
        "    let q = bx.get()\n"
        "    if q.a != 1 or q.b != 2 or q.c != 90\n"
        "        return 2\n"
        "    0\n"
    ),
    # Vec<P> strides by sizeof(P) through a grow: every element round-trips.
    "vec": (
        "    var v: Vec<P> = vec_new<P>()\n"
        "    for i in 0..20\n"
        "        vec_push<P>(@&v, P { a: i as u8, b: i * 1000, c: (i + 100) as u8 })\n"
        "    for i in 0..20\n"
        "        let q = vec_get<P>(@v, i)\n"
        "        if q.a != i as u8 or q.b != i * 1000 or q.c != (i + 100) as u8\n"
        "            return (i + 1) as i32\n"
        "    0\n"
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_container_of_padded_struct(ritz1_bin, tmp_path, compiler):
    rows = [Row(f"container_of_padded_struct[{name}]", (compiler,),
                Run(HEAD + "pub fn main() -> i32\n" + CONTAINERS[name], 0))
            for name in sorted(CONTAINERS)]
    table_rows.assert_rows(
        compiler, rows, build=table_rows.ritzlib_build(ritz1_bin),
        compile=for_header.batch_compile(ritz1_bin), work=tmp_path)


# A large bool fill: memset by the element's alloc size (1), not `1 // 8`.
# `dirty` leaves 7s on the stack the fill's slot reuses.
BOOL_FILL = """\
fn dirty() -> i32
    var junk: [400]u8 = [7; 400]
    junk[399] as i32 + junk[0] as i32

fn count(f: bool) -> i32
    var a: [100]bool = [f; 100]
    var n: i32 = 0
    for i in 0..100
        if a[i]
            n = n + 1
    n

fn falses() -> i32
    var a: [100]bool = [false; 100]
    let b = [false; 100]
    var n: i32 = 0
    for i in 0..100
        if a[i]
            n = n + 1
        if b[i]
            n = n + 1
    n

fn trues() -> i32
    var a: [100]bool = [true; 100]
    let b = [true; 100]
    var n: i32 = 0
    for i in 0..100
        if a[i]
            n = n + 1
        if b[i]
            n = n + 1
    n

pub fn main() -> i32
    dirty()
    if falses() != 0
        return 1
    dirty()
    if trues() != 200
        return 2
    0
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_large_bool_fill_sets_every_element(ritz1_bin, tmp_path, compiler):
    table_rows.assert_rows(
        compiler, [Row("large_bool_fill_sets_every_element", (compiler,), Run(BOOL_FILL, 0))],
        build=table_rows.ritzlib_build(ritz1_bin),
        compile=for_header.batch_compile(ritz1_bin), work=tmp_path)


@pytest.mark.integration
def test_ritz0_bool_fill_memsets_its_length(tmp_path):
    comp, ll, _ = _compile("ritz0", None, tmp_path, "bool_fill", BOOL_FILL)
    assert comp.returncode == 0, comp.stdout + comp.stderr
    counts = re.findall(
        r'call void @"llvm\.memset\.p0i8\.i64"\(i8\* %"[^"]*", i8 \S+, i64 (\d+)',
        ll.read_text(),
    )
    # falses' and trues' two fills each (`[f; 100]` isn't constant: a loop).
    assert counts == ["100", "100", "100", "100"]


# AGAST #3655: the synthesized built-in generic struct fallback.
@pytest.mark.unit
@pytest.mark.parametrize(
    "body, expected",
    [
        ((ir.IntType(8), ir.IntType(64)), (16, 8)),
        ((ir.IntType(8), ir.IntType(16)), (4, 2)),
        ((ir.PointerType(ir.IntType(8)), ir.IntType(64)), (16, 8)),  # Span<T>'s shape
    ],
    ids=["i8_i64", "i8_i16", "span"],
)
def test_synthesized_generic_struct_size_is_padded(body, expected):
    em = LLVMEmitter()
    em.module = ir.Module(name="t", context=ir.Context())  # emit() sets it
    ty = rast.NamedType(None, "Span", [rast.NamedType(None, "u8", [])])
    name = em._get_specialized_type_name(ty)
    st = em.module.context.get_identified_type(name)
    st.set_body(*body)
    em.struct_types[name] = st
    assert em._ritz_type_size_and_align(ty) == expected
