"""Regression tests for AGAST #1505 — ritz1 must load a struct by value
through a deref whose pointee struct is known statically, not `load i64`.

ritz1's OP_DEREF arm named the pointee struct only for a bare parameter
(`*p`, `p: *D`) and otherwise fell back silently to `load i64`. clang then
rejected the IR as soon as the value met a struct slot ("'%.N' defined with
type 'i64' but expected '%D'"). Shapes that failed:

* `*(p + i)` (pointer arithmetic keeps the pointer's type)
* `*q` for a let-local `q: *D` (its pointee is recorded as TYPE_I64)
* `*(h.items + i)` for a `*D` struct field (example 21_ls), including nested
  `w.h.items`
* `*v` for a `v: @D` reference param (ritzunit's `arr[i].name = *name`)

The same resolution fixes two companion sites, because without them the
struct load gives valid IR that steps or stores the wrong type:

* pointer-arithmetic stride: a let-local `*D` stepped by 8 instead of
  sizeof(D), and a nested `w.h.items` field by 1
* `*dst = *src` deref stores: stored the struct as `i64`

Every runnable program returns 7 only when the right element was read in
full (fields a + b = 3 + 4), so a wrong stride or a truncated copy returns
something else. ritz0 is run as the oracle.

A deref whose pointee is a struct that ritz1 still cannot name is now a
located error rather than a silent i64 load.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

EXPECTED = 7


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date; make's dependency graph decides the work.

    A stale ritz1 would assert against the old emitter (see AGAST #1322).
    """
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the deref-struct tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    proc = subprocess.run(
        ["make", "-C", "runtime", RITZ_START.name],
        cwd=RITZ_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0 or not RITZ_START.exists():
        pytest.fail(
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    _build_runtime_start()
    return RITZ1_BIN


STRUCT_D = """\
struct D
    a: i64
    b: i64

"""

# --- the load shapes #1505 rejected -----------------------------------------

# The ticket's repro, verbatim (reads only `a`, so it returns 7 directly).
PTR_ADD = STRUCT_D + """\
fn get(p: *D, i: i64) -> i64
    let d: D = *(p + i)
    return d.a

pub fn main() -> i32
    var arr: [2]D
    arr[1].a = 7
    return get(@arr[0], 1) as i32
"""

LET_LOCAL = STRUCT_D + """\
pub fn main() -> i32
    var arr: [2]D
    arr[1].a = 3
    arr[1].b = 4
    let q: *D = @arr[1]
    let d: D = *q
    return (d.a + d.b) as i32
"""

# Stride: a let-local `*D` stepped by 8 (pointee recorded as i64), landing
# mid-element 0 and reading a = 0, b = 0.
LET_LOCAL_PTR_ADD = STRUCT_D + """\
pub fn main() -> i32
    var arr: [2]D
    arr[1].a = 3
    arr[1].b = 4
    let q: *D = @arr[0]
    let d: D = *(q + 1)
    return (d.a + d.b) as i32
"""

# A left-associated chain on a let-local: `(q + i) - 1`.
LET_LOCAL_SUB_CHAIN = STRUCT_D + """\
fn get(p: *D, i: i64) -> i64
    let q: *D = p
    let d: D = *(q + i - 1)
    return d.a + d.b

pub fn main() -> i32
    var arr: [3]D
    arr[1].a = 3
    arr[1].b = 4
    return get(@arr[0], 2) as i32
"""

# 21_ls sort_entries: `*(entries.entries + i)` through a struct-pointer
# param's `*D` field; also the bare `*h.items`.
FIELD_PTR = STRUCT_D + """\
struct H
    items: *D
    n: i64

fn get(h: *H, i: i64) -> i64
    let d: D = *(h.items + i)
    let e: D = *h.items
    return d.a + d.b + e.a

pub fn main() -> i32
    var arr: [2]D
    arr[0].a = 1
    arr[1].a = 2
    arr[1].b = 4
    var h: H
    h.items = @arr[0]
    h.n = 2
    return get(@h, 1) as i32
"""

# Nested receiver: the old stride for `w.h.items + i` was 1.
NESTED_FIELD_PTR = STRUCT_D + """\
struct H
    items: *D
    n: i64

struct W
    h: H

fn get(w: *W, i: i64) -> i64
    let d: D = *(w.h.items + i)
    return d.a + d.b

pub fn main() -> i32
    var arr: [2]D
    arr[1].a = 3
    arr[1].b = 4
    var w: W
    w.h.items = @arr[0]
    return get(@w, 1) as i32
"""

REF_PARAM = STRUCT_D + """\
fn sum(v: @D) -> i64
    let t: D = *v
    return t.a + t.b

pub fn main() -> i32
    var d: D
    d.a = 3
    d.b = 4
    return sum(@d) as i32
"""

# ritzunit json_reporter: `g_json_results[i].name = *name`, `name: @StrView`.
RITZUNIT_SHAPE = STRUCT_D + """\
struct Rec
    d: D
    n: i64

var g_recs: [4]Rec

fn put(v: @D, i: i64)
    g_recs[i].d = *v

pub fn main() -> i32
    var d: D
    d.a = 3
    d.b = 4
    put(@d, 2)
    return (g_recs[2].d.a + g_recs[2].d.b) as i32
"""

# Mixed-width fields: the struct load must use the %D layout, not 8 bytes.
NARROW_FIELDS = """\
struct D
    a: i32
    b: u8

fn get(p: *D, i: i64) -> i64
    let d: D = *(p + i)
    return (d.a as i64) + (d.b as i64)

pub fn main() -> i32
    var arr: [2]D
    arr[1].a = 3
    arr[1].b = 4
    return get(@arr[0], 1) as i32
"""

# --- the deref-store companion ----------------------------------------------

# 21_ls: `*(entries.entries + j + 1) = *other`.  Three fields, so a copy
# that moved only the first 8 bytes would leave c = 0 (the old i64
# load/store pair did exactly that when it compiled).
DEREF_STORE = """\
struct E
    a: i64
    b: i64
    c: i32

struct L
    items: *E

fn shift(l: *L, j: i64)
    let other: *E = l.items + j
    *(l.items + j + 1) = *other

pub fn main() -> i32
    var arr: [3]E
    arr[0].a = 1
    arr[0].b = 2
    arr[0].c = 4
    var l: L
    l.items = @arr[0]
    shift(@l, 0)
    return (arr[1].a + arr[1].b + (arr[1].c as i64)) as i32
"""

# `*dst = *src` with let-local pointers on both sides.
DEREF_STORE_LET = STRUCT_D + """\
pub fn main() -> i32
    var s: D
    s.a = 3
    s.b = 4
    var t: D
    let src: *D = @s
    let dst: *D = @t
    *dst = *src
    return (t.a + t.b) as i32
"""

LOCAL_INDEX_STORE = STRUCT_D + """\
pub fn main() -> i32
    var d: D
    d.a = 3
    d.b = 4
    let v: *D = @d
    var arr: [4]D
    arr[2] = *v
    return (arr[2].a + arr[2].b) as i32
"""

BROKEN_FORMS = {
    "ptr_add": PTR_ADD,
    "let_local": LET_LOCAL,
    "let_local_ptr_add": LET_LOCAL_PTR_ADD,
    "let_local_sub_chain": LET_LOCAL_SUB_CHAIN,
    "field_ptr": FIELD_PTR,
    "nested_field_ptr": NESTED_FIELD_PTR,
    "ref_param": REF_PARAM,
    "ritzunit_shape": RITZUNIT_SHAPE,
    "narrow_fields": NARROW_FIELDS,
    "deref_store": DEREF_STORE,
    "deref_store_let": DEREF_STORE_LET,
    "local_index_store": LOCAL_INDEX_STORE,
}

# --- forms that already worked, pinned against regression -------------------

PARAM_DEREF = STRUCT_D + """\
fn sum(p: *D) -> i64
    let d: D = *p
    return d.a + d.b

pub fn main() -> i32
    var d: D
    d.a = 3
    d.b = 4
    return sum(@d) as i32
"""

# Primitive pointees keep their width-specific loads and strides.
PRIMITIVE_PTRS = """\
pub fn main() -> i32
    var buf: [4]i32
    buf[2] = 3
    var bytes: [4]u8
    bytes[3] = 4
    let p: *i32 = @buf[0]
    let q: *u8 = @bytes[0]
    return *(p + 2) + (*(q + 3) as i32)
"""

# The parser leaves the previous param's struct name on a following
# primitive pointer param (`d: *D, out: *i64` gives `out` type_name "D").
# Only a recorded TYPE_STRUCT pointee may be trusted, or `*out = 3` becomes
# `store %D` — the shape that broke ritz1's self-host (lexer_match_from's
# `best_priority: *i64` after `lex: *Lexer`).
STALE_PARAM_NAME = STRUCT_D + """\
fn put(d: *D, out: *i64, cnt: *i32)
    *out = 3
    *cnt = 4
    let x: i64 = *(out + 0)
    *out = x + 0

pub fn main() -> i32
    var d: D
    var o: i64 = 0
    var c: i32 = 0
    put(@d, @o, @c)
    return (o as i32) + c
"""

STALE_LET_NAME = STRUCT_D + """\
pub fn main() -> i32
    var d: D
    var o: i64 = 0
    let dp: *D = @d
    let op: *i64 = @o
    *op = 7
    let x: i64 = *op
    return x as i32
"""

# A bare `*p` on a tagged-enum pointer loads `%Option$i32` — not a StructDef,
# so the resolver must keep the old unverified trust for this path
# (ritz0/test/test_issue_option_return.ritz, ritzlib's option_is_none).
OPTION_PARAM_DEREF = """\
import ritzlib.option

fn get(p: *Option<i32>) -> i32
    let o: Option<i32> = *p
    match o
        Some(v) => v
        None => 1

fn is_none(p: *Option<i32>) -> i32
    match *p
        Some(_) => 0
        None => 1

pub fn main() -> i32
    let a: Option<i32> = Some(7)
    let b: Option<i32> = None
    return get(@a) + is_none(@a) + (is_none(@b) - 1)
"""

WORKING_FORMS = {
    "param_deref": PARAM_DEREF,
    "option_param_deref": OPTION_PARAM_DEREF,
    "primitive_ptrs": PRIMITIVE_PTRS,
    "stale_param_name": STALE_PARAM_NAME,
    "stale_let_name": STALE_LET_NAME,
}

# A global `*D` records no pointee struct name (follow-up ticket), so ritz1
# cannot name the struct `*(g_p + 1)` loads.  It must say so at the deref's
# position instead of emitting `load i64`.
UNRESOLVED_GLOBAL_PTR = STRUCT_D + """\
var g_p: *D = null

pub fn main() -> i32
    var arr: [2]D
    arr[1].a = 3
    arr[1].b = 4
    g_p = @arr[0]
    let d: D = *(g_p + 1)
    return (d.a + d.b) as i32
"""


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
    proc = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    return proc, ll


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n"
        f"{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


ALL_RUNNABLE = {**BROKEN_FORMS, **WORKING_FORMS}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL_RUNNABLE[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BROKEN_FORMS))
def test_ritz1_deref_loads_struct(ritz1_bin, tmp_path, name):
    """AGAST #1505. Before the fix: clang rejects `load i64` into a %D slot."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_forms(ritz1_bin, tmp_path, name):
    """Param `*p`, primitive pointees and stale-named `*i64` params are unchanged."""
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == EXPECTED


@pytest.mark.integration
def test_ritz1_repro_ir_loads_struct(ritz1_bin, tmp_path):
    """The repro's deref is a `load %D`, the stride sizeof(D) = 16."""
    comp, ll = _compile("ritz1", tmp_path, "ptr_add_ir", PTR_ADD)
    assert comp.returncode == 0, comp.stderr[-2000:]
    ir = ll.read_text()
    get_body = ir.split("@get(", 1)[1].split("\n}", 1)[0]
    assert "= load %D, ptr" in get_body
    assert re.search(r"= mul i64 %\.\d+, 16\n", get_body), get_body


@pytest.mark.integration
def test_ritz1_unresolved_struct_deref_is_located_error(ritz1_bin, tmp_path):
    """No silent `load i64`: an unnameable struct pointee is a located error."""
    comp, ll = _compile("ritz1", tmp_path, "glob_ptr", UNRESOLVED_GLOBAL_PTR)
    out = comp.stderr + comp.stdout
    assert comp.returncode != 0
    # Line 12, column 16 is the `*` of `*(g_p + 1)`.
    assert "12:16: error: ritz1 cannot emit: " in out, out[-2000:]
    assert "cannot determine the struct type loaded by this '*' deref" in out
    assert not ll.exists()


# `*(p + 1)` over a tagged enum: the deref resolves `%Option$i32`, but a
# tagged enum has no StructDef size, so the stride must NOT come from
# get_struct_size_by_name (it answers 8; the enum is 33 bytes).  ritz1 may
# refuse the stride (AGAST #1451's fail-closed error) — it must never run
# and return the wrong element.
OPTION_PTR_ARITH = """\
import ritzlib.option

struct Two
    x: Option<i32>
    y: Option<i32>

fn get(p: *Option<i32>, i: i64) -> i32
    let o: Option<i32> = *(p + i)
    match o
        Some(v) => v
        None => 1

pub fn main() -> i32
    var t: Two
    t.x = Some(1)
    t.y = Some(7)
    return get(@t.x, 1)
"""


@pytest.mark.integration
def test_ritz1_tagged_enum_ptr_arith_never_miscompiles(ritz1_bin, tmp_path):
    """Refusing is fine; a wrong stride that runs and reads garbage is not."""
    comp, ll = _compile("ritz1", tmp_path, "opt_arith", OPTION_PTR_ARITH)
    if comp.returncode != 0:
        assert "element size of pointee unknown" in comp.stderr + comp.stdout
        return
    assert _run("ritz1", tmp_path, "opt_arith", OPTION_PTR_ARITH) == EXPECTED
