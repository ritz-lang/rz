#!/usr/bin/env python3
"""Indexing a struct through `Index`, `IndexMut` and `IndexSet` (LANGUAGE_SPEC §7.8,
LARB ruling R15, AGAST #1635).

A struct opts into `[]` by implementing up to three compiler-known traits, resolved
statically like `Drop`. `m[k]` is a place: shared uses go through `index`, mutable
ones through `index_mut`, and a plain `m[k] = v` through `index_set` (or
`index_mut` without one). `m[k] op= x` calls `index_mut` once. A struct with an
`index` method but no `impl Index` gets no `[]`.

ritz0 used to rewrite `m[k]` only for a local whose type was named `HashMapI64`,
and ritz1 emitted invalid IR for it.

Each row runs on ritz0, ritz1 and ritz1_selfhosted; refusals must report the same
`line:col: message` on all three, located at the `[`.

The runs and the refusals are each a table per compiler (AGAST #3889): runs
through test_table_rows, linking the ritzlib modules a row imports
(test_table_rows.ritzlib_build, not a `--no-cache` build.py package per
case); refusals through test_table_rows.assert_refusals.  A row keeps the id its
parametrised test had, less the compiler, and a failure names it.  The missing
key test checks stderr too, so it stays its own test.
"""

import subprocess

import pytest

import test_ritz1_for_header as for_header
import test_table_rows as table_rows
from index_rules import builtin_impl, needs_index, needs_index_mut, needs_writer
from ref_rules import WRITE_THROUGH_SHARED, lent_temp_escapes
from test_ref_into_value import COMPILERS
from test_table_rows import Row, Run, assert_refusals, ritzlib_build

pytestmark = pytest.mark.integration


# A grid of four cells whose keys are fixed: `index` and `index_mut`, no
# `index_set`. COUNT records every call, by trait, so a test can say which ran.
GRID = """\
struct Cell
    v: i32
    w: i32

struct Grid
    cells: [4]Cell

var READS: i32 = 0
var WRITES: i32 = 0
var SETS: i32 = 0

impl Index for Grid
    fn index(self: @Grid, key: i64) -> @Cell
        READS += 1
        @self.cells[key]

impl IndexMut for Grid
    fn index_mut(self: @&Grid, key: i64) -> @&Cell
        WRITES += 1
        @&self.cells[key]

"""

# A counter whose elements are i64s, with all three traits.
TALLY = """\
struct Tally
    n: [4]i64

var READS: i32 = 0
var WRITES: i32 = 0
var SETS: i32 = 0
var KEYS: i32 = 0

impl Index for Tally
    fn index(self: @Tally, key: i64) -> @i64
        READS += 1
        @self.n[key]

impl IndexMut for Tally
    fn index_mut(self: @&Tally, key: i64) -> @&i64
        WRITES += 1
        @&self.n[key]

impl IndexSet for Tally
    fn index_set(self: @&Tally, key: i64, value: i64)
        SETS += 1
        self.n[key] = value

fn key(k: i64) -> i64
    KEYS += 1
    k

"""


# An element holding a struct by value (`n[k].c.v`) and a pointer (`n[k].p.v`):
# a store through `p` writes outside `n` (AGAST #4160).
NEST = """\
struct Inner
    v: i32

struct Outer
    c: Inner
    p: *Inner

struct Nest
    cells: [2]Outer

impl Index for Nest
    fn index(self: @Nest, key: i64) -> @Outer
        @self.cells[key]

impl IndexMut for Nest
    fn index_mut(self: @&Nest, key: i64) -> @&Outer
        @&self.cells[key]

"""


# A generic pair with all three traits, each impl generic (AGAST #2847).
PAIR = """\
struct Pair<T>
    a: [2]T

var READS: i32 = 0
var WRITES: i32 = 0
var SETS: i32 = 0

impl<T> Index for Pair<T>
    fn index(self: @Pair<T>, key: i64) -> @T
        READS += 1
        @self.a[key]

impl<T> IndexMut for Pair<T>
    fn index_mut(self: @&Pair<T>, key: i64) -> @&T
        WRITES += 1
        @&self.a[key]

impl<T> IndexSet for Pair<T>
    fn index_set(self: @&Pair<T>, key: i64, value: T)
        SETS += 1
        self.a[key] = value

"""


def _program(prelude, body):
    return f"{prelude}pub fn main() -> i32\n{body}"


# name -> (prelude, main's body). Each exits 0 when the rule holds; a non-zero
# exit is the line of the check that failed.
RUNS = {
    # A read by value copies through `index`.
    "read": (TALLY, """\
    var t: Tally
    t.n[2] = 7
    let v: i64 = t[2]
    if v != 7
        return 1
    if READS != 1 or WRITES != 0
        return 2
    0
"""),
    # `m[k] = v` uses `index_set` when there is one.
    "assign_set": (TALLY, """\
    var t: Tally
    t[1] = 9
    if t.n[1] != 9
        return 1
    if SETS != 1 or WRITES != 0 or READS != 0
        return 2
    0
"""),
    # Without `IndexSet`, `m[k] = v` stores through `index_mut`.
    "assign_mut": (GRID, """\
    var g: Grid
    g[1] = Cell { v: 3, w: 4 }
    if g.cells[1].v != 3 or g.cells[1].w != 4
        return 1
    if WRITES != 1 or READS != 0
        return 2
    0
"""),
    # `m[k] op= x` calls `index_mut` once, evaluates the key once, and never
    # `index` or `index_set`.
    "compound": (TALLY, """\
    var t: Tally
    t.n[3] = 10
    t[key(3)] += 5
    if t.n[3] != 15
        return 1
    if WRITES != 1 or READS != 0 or SETS != 0
        return 2
    if KEYS != 1
        return 3
    t[key(3)] -= 1
    if t.n[3] != 14 or WRITES != 2 or KEYS != 2
        return 4
    0
"""),
    # A user-written `m[k] = m[k] + 1` is a read and a store.
    "spelled_out": (TALLY, """\
    var t: Tally
    t.n[0] = 1
    t[0] = t[0] + 1
    if t.n[0] != 2
        return 1
    if READS != 1 or SETS != 1 or WRITES != 0
        return 2
    0
"""),
    # `.f` on a read goes through `index`; a field store through `index_mut`.
    "field": (GRID, """\
    var g: Grid
    g[2].v = 6
    if WRITES != 1
        return 1
    let v: i32 = g[2].v
    if v != 6 or READS != 1
        return 2
    0
"""),
    # A store through a pointer field of an element writes outside the struct,
    # so a loan of another element doesn't stand in its way (AGAST #4160).
    "field_store_through_pointer": (NEST, """\
    var x: Inner
    x.v = 0
    var n: Nest
    n.cells[0].p = @x
    n.cells[1].c.v = 0   # read below; `var` leaves it uninitialised
    let p: @Outer = @n[1]
    n[0].p.v = 4
    if x.v != 4 or p.c.v != 0
        return 1
    0
"""),
    # A struct element read by value is a copy through `index`.
    "read_struct": (GRID, """\
    var g: Grid
    g.cells[1].v = 5
    g.cells[1].w = 6
    let c: Cell = g[1]
    if c.v != 5 or c.w != 6
        return 1
    if READS != 1 or WRITES != 0
        return 2
    0
"""),
    # The base can be a field: `h.t[k]`.
    "field_base": (TALLY + """\
struct Holder
    pad: i64
    t: Tally

""", """\
    var h: Holder
    h.t[2] = 3
    h.t[2] += 4
    if h.t[2] != 7 or h.t.n[2] != 7
        return 1
    if SETS != 1 or WRITES != 1 or READS != 1
        return 2
    0
"""),
    # `@m[k]` is `index`, `@&m[k]` is `index_mut`. Each borrow is in its own fn:
    # `[k]` is an index step, so the two would overlap (R11a).
    "address": (TALLY + """\
fn shared() -> i64
    var t: Tally
    t.n[1] = 4
    let p: @i64 = @t[1]
    *p

fn mutable() -> i64
    var t: Tally
    let q: @&i64 = @&t[2]
    *q = 8
    t.n[2]

""", """\
    if shared() != 4 or READS != 1 or WRITES != 0
        return 1
    if mutable() != 8 or WRITES != 1 or READS != 1
        return 2
    0
"""),
    # `[]` sees through one level of `@`, `@&` and `*`.
    "through": (TALLY + """\
fn get(t: @Tally) -> i64
    t[1]

fn put(t: @&Tally)
    t[1] = 5

fn bump(t: *Tally)
    t[1] += 1

""", """\
    var t: Tally
    put(@&t)
    bump(@t)
    if get(@t) != 6
        return 1
    if SETS != 1 or WRITES != 1 or READS != 1
        return 2
    0
"""),
    # R11a: a read of `t[k]` beside a shared loan of `t[_]` borrows nothing.
    "loan_then_read": (TALLY, """\
    var t: Tally
    t.n[1] = 4
    t.n[2] = 3
    let p: @i64 = @t[1]
    let v: i64 = t[2]
    if *p + v != 7
        return 1
    0
"""),
    # AGAST #2847: a generic impl is found for each instantiation, by value
    # and through a reference.
    "generic": (PAIR + """\
fn bump(p: @&Pair<i32>)
    p[0] += 2

""", """\
    var p: Pair<i64>
    p[1] = 7
    p[1] += 3
    let v: i64 = p[1]
    if v != 10 or p.a[1] != 10
        return 1
    if SETS != 1 or WRITES != 1 or READS != 1
        return 2
    var q: Pair<i32>
    q.a[0] = 1
    bump(@&q)
    if q[0] != 3
        return 3
    0
"""),
    # AGAST #2847: the base is any expression of the struct's type: a call
    # result, a global, `(*p)`.
    "call_base": (TALLY + """\
var STORE: Tally

fn mk() -> *Tally
    @STORE

""", """\
    mk()[2] = 6
    mk()[2] += 1
    let v: i64 = mk()[2]
    if v != 7 or STORE.n[2] != 7
        return 1
    if SETS != 1 or WRITES != 1 or READS != 1
        return 2
    0
"""),
    "global_base": (TALLY + "var G: Tally\n\n", """\
    G[1] = 5
    G[1] += 2
    let v: i64 = G[1]
    if v != 7 or G.n[1] != 7
        return 1
    if SETS != 1 or WRITES != 1 or READS != 1
        return 2
    0
"""),
    "deref_base": (TALLY + """\
fn work(p: *Tally) -> i64
    (*p)[1] = 5
    (*p)[1] += 2
    (*p)[1]

""", """\
    var t: Tally
    if work(@t) != 7 or t.n[1] != 7
        return 1
    if SETS != 1 or WRITES != 1 or READS != 1
        return 2
    0
"""),
}


def _build_and_run(ritz1_bin, compiler, tmp_path, src):
    """Compile `src`, link the ritzlib modules it imports (as build.py would, each
    compiled once per process), and run it."""
    work = tmp_path / compiler
    work.mkdir()
    (work / "main.ritz").write_text(src)
    ok, output, exe = ritzlib_build(ritz1_bin)(compiler, work / "main.ritz", work)
    assert ok, f"{compiler} failed to build:\n{output[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60, check=False)


# The spec's example: ritzlib's HashMapI64 at K = V = i64.
HASHMAP = _program("import ritzlib.hashmap\n\n", """\
    var m: HashMapI64 = hashmap_i64_new()
    m[1] = 10
    m[1] += 5
    m[2] = 1
    if m.len() != 2
        return 1
    let p: @i64 = @m[1]
    let v: i64 = *p - 15
    v as i32
""")

# Every run is a row exiting 0 under its old id, less the compiler; the hashmap
# row links the ritzlib modules it imports (ritzlib_build).
RUN_TABLE = [
    *(Row(f"struct_index_runs[{name}]", table_rows.ALL, Run(_program(*RUNS[name]), 0)) for name in sorted(RUNS)),
    Row("hashmap_implements_all_three", table_rows.ALL, Run(HASHMAP, 0)),
]


@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(RUN_TABLE),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(RUN_TABLE)])
def test_every_run(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_rows(compiler, table_rows.chunk(RUN_TABLE, compiler, chunk),
                           build=ritzlib_build(ritz1_bin),
                           compile=for_header.batch_compile(ritz1_bin), work=tmp_path)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_missing_key_ends_the_program(ritz1_bin, tmp_path, compiler):
    """`index` must not return for a missing key: HashMapI64 exits with a message."""
    src = _program("import ritzlib.hashmap\n\n", """\
    var m: HashMapI64 = hashmap_i64_new()
    m[1] = 10
    let v: i64 = m[999]
    0
""")
    run = _build_and_run(ritz1_bin, compiler, tmp_path, src)
    assert run.returncode == 101
    assert b"HashMapI64: key not found: 999" in run.stderr


# `^` is where the error lands: the `[`.
POINT = "struct Point\n    x: i32\n\n"
LOOKUP = """\
struct Lookup
    n: [2]i64

impl Index for Lookup
    fn index(self: @Lookup, key: i64) -> @i64
        @self.n[key]

"""
LOOKUP_SET = LOOKUP + """\
impl IndexSet for Lookup
    fn index_set(self: @&Lookup, key: i64, value: i64)
        self.n[key] = value

"""

REFUSALS = {
    # No trait at all: every use names `Index`.
    "read_no_impl": (POINT, "    var p: Point\n    let v: i32 = p^[0]\n    0\n",
                     needs_index("Point")),
    "assign_no_impl": (POINT, "    var p: Point\n    p^[0] = 1\n    0\n",
                       needs_index("Point")),
    # A method named `index` is not an `impl Index` (R15: a trait, not a name).
    "method_named_index": (
        "struct Named\n    n: [2]i64\n\n"
        "impl Named\n    fn index(self: @Named, key: i64) -> @i64\n        @self.n[key]\n\n",
        "    var p: Named\n    let v: i64 = p^[0]\n    0\n", needs_index("Named")),
    "assign_index_only": (LOOKUP, "    var m: Lookup\n    m^[0] = 1\n    0\n",
                          needs_writer("Lookup", ["Index"])),
    "mut_addr_index_set": (LOOKUP_SET, "    var m: Lookup\n    let r: @&i64 = @&m^[0]\n    0\n",
                           needs_index_mut("@&m[k]", "Lookup", ["Index", "IndexSet"])),
    "compound_index_set": (LOOKUP_SET, "    var m: Lookup\n    m^[0] += 1\n    0\n",
                           needs_index_mut("m[k] op= x", "Lookup", ["Index", "IndexSet"])),
    # Writes follow §3.2: an `@M` refuses them, whichever trait would write.
    "write_through_shared": (LOOKUP_SET + "fn put(p: @Lookup)\n    ^p[0] = 1\n\n",
                             "    0\n", WRITE_THROUGH_SHARED),
    "field_store_index_only": (
        "struct C\n    v: i32\n\nstruct Box1\n    c: C\n\n"
        "impl Index for Box1\n    fn index(self: @Box1, key: i64) -> @C\n        @self.c\n\n",
        "    var b: Box1\n    b^[0].v = 1\n    0\n",
        needs_index_mut("m[k].f = x", "Box1", ["Index"])),
    # AGAST #2847: at the `[` itself, whatever comes between it and the base.
    "spaced_read": (POINT, "    var p: Point\n    let v: i32 = p ^[0]\n    0\n",
                    needs_index("Point")),
    "spaced_assign": (LOOKUP, "    var m: Lookup\n    m ^[0] = 1\n    0\n",
                      needs_writer("Lookup", ["Index"])),
    "spaced_field_assign": (LOOKUP + "struct Holder\n    m: Lookup\n\n",
                            "    var h: Holder\n    h.m ^[0] = 1\n    0\n",
                            needs_writer("Lookup", ["Index"])),
    # AGAST #2847: any base expression, as on ritz0.
    "call_base": (POINT + "fn mk() -> Point\n    Point { x: 1 }\n\n",
                  "    let v: i32 = mk()^[0]\n    0\n", needs_index("Point")),
    # A by-value call's result is a temporary, which `index` would lend
    # (Aaron's ruling on AGAST #3215).
    "call_base_temporary": (TALLY + "fn mk() -> Tally\n    var t: Tally\n    t\n\n",
                            "    let v: i64 = ^mk()[2]\n    0\n", lent_temp_escapes("@mk()")),
    "global_base": (LOOKUP + "var G: Lookup\n\n", "    G^[0] = 1\n    0\n",
                    needs_writer("Lookup", ["Index"])),
    "deref_base": (LOOKUP + "fn put(p: *Lookup)\n    (*p)^[0] += 1\n\n", "    0\n",
                   needs_index_mut("m[k] op= x", "Lookup", ["Index"])),
    # AGAST #2847: a generic impl counts, and only the traits it implements.
    "generic_index_only": (
        "struct Only<T>\n    a: [2]T\n\n"
        "impl<T> Index for Only<T>\n    fn index(self: @Only<T>, key: i64) -> @T\n        @self.a[key]\n\n",
        "    var m: Only<i64>\n    let v: i64 = m[0]\n    m^[0] = v\n    0\n",
        needs_writer("Only<i64>", ["Index"])),
    # AGAST #4924: two type arguments are spelled `, `-separated.
    "generic_two_params_index_only": (
        "struct Two<A, B>\n    a: [2]A\n    b: B\n\n"
        "impl<A, B> Index for Two<A, B>\n    fn index(self: @Two<A, B>, key: i64) -> @A\n        @self.a[key]\n\n",
        "    var m: Two<i64, i32>\n    let v: i64 = m[0]\n    m^[0] = v\n    0\n",
        needs_writer("Two<i64, i32>", ["Index"])),
    # R11a: `@t[1]` is a loan of `t[_]` once it's an `index` call, so a store
    # into another element of `t` overlaps it.
    "loan_then_store": (TALLY, "    var t: Tally\n    let p: @i64 = @t[1]\n    ^t[2] = 5\n"
                        "    return *p as i32\n",
                        "cannot assign to `t[_]` - `t[_]` is already borrowed as immutable"),
    "loan_then_borrow_mut": (TALLY, "    var t: Tally\n    let p: @i64 = @t[1]\n"
                             "    let q: @&i64 = ^@&t[2]\n    return (*p + *q) as i32\n",
                             "cannot borrow `t[_]` as mutable - `t[_]` is already borrowed as immutable"),
    "mut_loan_then_compound": (TALLY, "    var t: Tally\n    let q: @&i64 = @&t[1]\n    ^t[2] += 1\n"
                               "    return *q as i32\n",
                               "cannot assign to `t[_]` - `t[_]` is already borrowed as mutable"),
    # AGAST #4160: `g[2].v = 5` stores through `index_mut`, so it is a write of
    # `g[_].v`, as `a[2].v = 5` is of an array's; ritz0 and ritz1 saw none.
    "loan_then_field_store": (GRID, "    var g: Grid\n    let p: @Cell = @g[1]\n    ^g[2].v = 5\n"
                              "    return p.v\n",
                              "cannot assign to `g[_].v` - `g[_]` is already borrowed as immutable"),
    "mut_loan_then_field_compound": (GRID, "    var g: Grid\n    let q: @&Cell = @&g[1]\n"
                                     "    ^g[2].v += 1\n    return q.v\n",
                                     "cannot assign to `g[_].v` - `g[_]` is already borrowed as mutable"),
    "loan_then_nested_field_store": (
        NEST, "    var n: Nest\n    let p: @Outer = @n[1]\n    ^n[0].c.v = 5\n    return p.c.v\n",
        "cannot assign to `n[_].c.v` - `n[_]` is already borrowed as immutable"),
}


def _builtin_opt_in(trait):
    return ("import ritzlib.string\n\nimpl " + trait + " for ^String\n"
            "    fn index(self: @String, key: i64) -> @u8\n"
            "        @self.data.data[key]\n\n"
            "pub fn main() -> i32\n    0\n")


# Each refusal's whole message at its `^`, as `_assert_refused` wanted it.
REFUSAL_TABLE = {
    **{f"struct_index_refusals[{name}]": (_program(prelude, body), message)
       for name, (prelude, body, message) in sorted(REFUSALS.items())},
    **{f"built_in_types_cannot_opt_in[{trait}]": (_builtin_opt_in(trait), builtin_impl(trait, "String"))
       for trait in ["Index", "IndexMut", "IndexSet"]},
}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_refusal(ritz1_bin, tmp_path, compiler):
    assert_refusals(compiler, tmp_path, REFUSAL_TABLE)
