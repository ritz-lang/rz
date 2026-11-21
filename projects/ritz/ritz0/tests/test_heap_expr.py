"""AGAST #3934: `heap <expr>` allocates its value and is a `*T`, on every
compiler.

THE DEFECT

`heap` is a keyword in ritz0 (tokens.py; parser.parse_prefix makes a
HeapExpr): `heap e` mallocs one `T`, stores `e` there and is the `*T`.
STDLIB_REFERENCE.md (then ritzlib.heap, now ritzlib.box) shows `var p = heap 42`.  ritz1's grammar
had no `heap`, so it lexed as an identifier and stopped at the operand:
`4:18: error: unexpected '42'` (check-doc-examples under ritz1, #3928).

THE FIX

`heap` is a keyword in ritz1 too (a module path segment still, so
`import mm.heap` resolves as in ritz0), and
`heap <unary>` binds like the other prefixes.  It is lowered as a call to
a compiler-made generic, `fn __heap<T>(v: T) -> *T` (malloc(sizeof(T)),
store, return), so T comes from generic inference as `f(e)`'s would.

Every row runs on ritz0, ritz1 and ritz1_selfhosted and reads the value back
through the pointer, so an allocation that merely compiles but stores the
wrong width or the wrong value still fails.
"""

import pytest

import test_table_rows as table_rows
from test_ref_into_value import _compile
from test_table_rows import Run

pytestmark = pytest.mark.integration

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

POINT = """\
struct Point
    x: i64
    y: i64

fn point_new(x: i64, y: i64) -> Point
    return Point { x: x, y: y }

"""

PROGRAMS = {
    # The ticket's repro: STDLIB_REFERENCE.md's `heap`-keyword block (in the
    # ritzlib.box section since #3916 folded ritzlib.heap into box), which
    # imports only ritzlib.box (malloc arrives through its plain import).
    "stdlib_reference": ("""\
import ritzlib.box

fn heap_vs_box() -> i64
    var p = heap 42
    var q = box_new<i64>(42)
    *p + box_get<i64>(@q)

pub fn main() -> i32
    heap_vs_box() as i32
""", 84),
    "int_literal": ("""\
import ritzlib.memory

pub fn main() -> i32
    let p = heap 42
    let v: i64 = *p
    free(p as *u8)
    v as i32
""", 42),
    "write_through": ("""\
import ritzlib.memory

pub fn main() -> i32
    let p = heap 10
    *p = *p + 33
    let v = *p
    free(p as *u8)
    v as i32
""", 43),
    "struct_call": (POINT + """\
import ritzlib.memory

pub fn main() -> i32
    let p = heap point_new(3, 4)
    let v = p.x * 10 + p.y
    free(p as *u8)
    v as i32
""", 34),
    "struct_mutate": (POINT + """\
import ritzlib.memory

pub fn main() -> i32
    let p = heap point_new(1, 2)
    p.x = 5
    p.y = 6
    let v = p.x * 10 + p.y
    free(p as *u8)
    v as i32
""", 56),
    "grouped_binary": ("""\
import ritzlib.memory

pub fn main() -> i32
    let x = 10
    let y = 20
    let p = heap (x + y)
    let v = *p
    free(p as *u8)
    v as i32
""", 30),
    # A narrow T: the slot is an i32, so a store or load at i64 width would
    # read the neighbour's bytes.
    "i32_local": ("""\
import ritzlib.memory

pub fn main() -> i32
    let a: i32 = 7
    let p = heap a
    let q = heap (a + a)
    let v: i32 = *p * 10 + *q
    free(p as *u8)
    free(q as *u8)
    v
""", 84),
    # Two allocations are two blocks: writing one leaves the other alone.
    "distinct_blocks": ("""\
import ritzlib.memory

pub fn main() -> i32
    let p = heap 1
    let q = heap 2
    *p = 40
    let v = *p + *q
    free(p as *u8)
    free(q as *u8)
    v as i32
""", 42),
}


# One table per compiler (AGAST #4418): each case used to launch `build.py`
# for its own package, paying a Python start and a cold build cache.  As rows,
# every ritzlib module a chunk imports is compiled once per process per
# compiler and linked onto the batch (test_table_rows.ritzlib_build, #3906);
# a row that fails is still compiled again on its own and named.
RUNS = [table_rows.Row(f"heap_expr[{name}]", table_rows.ALL, Run(*PROGRAMS[name]))
        for name in sorted(PROGRAMS)]


@pytest.mark.parametrize("compiler", COMPILERS)
def test_heap_expr(ritz1_bin, tmp_path, compiler):
    table_rows.assert_ritzlib_rows(compiler, RUNS, ritz1_bin, tmp_path)


# Without ritzlib.memory there is no malloc (ritz0) and no `__heap_new`
# (ritz1): refused in ritz0's words, not as a call the input never wrote.
NO_MEMORY = """\
pub fn main() -> i32
    let p = heap 42
    *p as i32
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_heap_without_memory_is_refused(tmp_path, compiler):
    comp, ll, _ = _compile(compiler, tmp_path, "no_memory", NO_MEMORY)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), out
    assert "heap requires ritzlib.memory (malloc not found)" in out, out
    assert "__heap_new" not in out, out

