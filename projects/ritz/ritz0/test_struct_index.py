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
"""

import os
import subprocess

import pytest

from index_rules import builtin_impl, needs_index, needs_index_mut, needs_writer
from ref_rules import WRITE_THROUGH_SHARED
from test_ref_into_value import COMPILERS, RITZ_ROOT, _assert_refused, _run

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
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_struct_index_runs(tmp_path, compiler, name):
    prelude, body = RUNS[name]
    assert _run(compiler, tmp_path, name, _program(prelude, body)) == 0


def _build_and_run(compiler, tmp_path, name, src):
    """Build `src` as a package, which links the ritzlib modules it imports, and run it."""
    pkg = tmp_path / f"{name}_{compiler}"
    (pkg / "src").mkdir(parents=True)
    (pkg / "src" / "main.ritz").write_text(src)
    (pkg / "ritz.toml").write_text(f'[package]\nname = "{name}"\nversion = "0.1.0"\n\n'
                                   '[build]\ntarget = "x86_64-linux"\n')
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(["python3", str(RITZ_ROOT / "build.py"), "build", str(pkg),
                           "--no-cache", "--compiler", compiler],
                          cwd=RITZ_ROOT, env=env, capture_output=True, text=True, timeout=600)
    exe = pkg / "build" / "debug" / name
    assert proc.returncode == 0 and exe.exists(), \
        f"{compiler} failed to build {name}:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_hashmap_implements_all_three(tmp_path, compiler):
    """The spec's example: ritzlib's HashMapI64 at K = V = i64."""
    src = _program("import ritzlib.hashmap\n\n", """\
    var m: HashMapI64 = hashmap_i64_new()
    m[1] = 10
    m[1] += 5
    m[2] = 1
    if hashmap_i64_len(@m) != 2
        return 1
    let p: @i64 = @m[1]
    let v: i64 = *p - 15
    v as i32
""")
    assert _build_and_run(compiler, tmp_path, "hashmap", src).returncode == 0


@pytest.mark.parametrize("compiler", COMPILERS)
def test_missing_key_ends_the_program(tmp_path, compiler):
    """`index` must not return for a missing key: HashMapI64 exits with a message."""
    src = _program("import ritzlib.hashmap\n\n", """\
    var m: HashMapI64 = hashmap_i64_new()
    m[1] = 10
    let v: i64 = m[999]
    0
""")
    run = _build_and_run(compiler, tmp_path, "missing", src)
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
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSALS))
def test_struct_index_refusals(tmp_path, compiler, name):
    prelude, body, message = REFUSALS[name]
    _assert_refused(compiler, tmp_path, name, _program(prelude, body), message)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("trait", ["Index", "IndexMut", "IndexSet"])
def test_built_in_types_cannot_opt_in(tmp_path, compiler, trait):
    src = ("import ritzlib.string\n\nimpl " + trait + " for ^String\n"
           "    fn index(self: @String, key: i64) -> @u8\n"
           "        @self.data.data[key]\n\n"
           "pub fn main() -> i32\n    0\n")
    _assert_refused(compiler, tmp_path, trait, src, builtin_impl(trait, "String"))
