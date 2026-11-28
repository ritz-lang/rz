"""LARB R66 step 1, generic half (AGAST #4231): `impl<T> Vec<T>` and
`impl<T> Option<T>` in ritzlib.

THE CHANGE

ritzlib.gvec holds `impl<T> Vec<T>`, ritzlib.option `impl<T> Option<T>`: each
method a one-line `pub` wrapper of its free fn, as #3495 did for `impl String`
(test_ritzlib_impl_wrappers.py). #3495 had to leave these two out: both
compilers specialised every method of a generic impl at every instance, so the
wrappers linked malloc into -nostdlib importers and move-checked
`Vec<MoveOnly>`'s `pop` though nothing popped. #3617 specialises a method only
where a call names it.

THE RITZ1 HALF

ritz1 names a method on EVERY instance when it can't type the call's receiver
(#3617: nothing reachable is missed). It typed a local, a param and a field
chain. Once ritzlib has `impl<T> Vec<T>`, one untyped `x.push(..)` / `x.get(..)`
specialised Vec's `push` / `get` at every Vec instance: a -nostdlib program with
a `push` of its own linked `vec_grow` and `realloc`, and `arr[0].get(0)` beside
a `Vec<Res>` was refused "cannot move out of a reference" in `vec_get<Res>`.
ritz1 now also types `*p`, `a[i]` of a `[N]S` local (or of a Vec<Vec<T>>), a
call's result (plain fn, or `vec_new<i32>()`) and a method's
(`a.slice(0, 1).get(0)`). ritz0 types these through its type checker already.

THE TESTS

  * Option's impl holds exactly the methods listed here, each `pub`, each a
    single `return option_<method><T>(...)` of its own free fn.
  * Vec's impl holds its operations' bodies directly.  AGAST #4537 moved
    every `vec_*` free fn into `impl<T> Vec<T>` and deleted it, so the
    wrapper premise of #4231 is gone for Vec (as #4533 did for String):
    each method is `pub`, takes `self`, and no `vec_*` twin remains.
    `push_bytes` keeps the raw `(data, len)` print-sink protocol shape.
  * every wrapper's name, by method syntax, runs right on each compiler.
  * each receiver shape above, beside a `Vec<Res>` / `Option<Res>` whose
    `get` / `unwrap_or` would be refused, compiles and runs.
  * a -nostdlib program importing ritzlib.gvec whose untyped receivers call
    a `push` of its own references no malloc, realloc or vec_grow.

Method syntax on a Vec or Option reaches only these wrappers: the UFCS tables
that also reached the free fns were deleted by #3496 (ritz0) and #3497 (ritz1).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import test_table_rows as table_rows
from ritz0_inproc import run_ritz0
from test_ritzlib_impl_wrappers import _body_text, _impl_methods
from test_table_rows import Row, Run

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
RITZLIB = RITZ_ROOT / "ritzlib"
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ("ritz0", "ritz1", "ritz1_selfhosted")

# Every operation `impl<T> Vec<T>` declares, each holding its body (AGAST
# #4537).  A method and its old free-fn twin would be two spellings of one
# API, so the twins are gone.
VEC_METHODS = {
    "deinit", "valid", "len", "cap", "is_empty", "grow", "ensure_cap", "push",
    "pop", "get", "get_ptr", "set", "clear", "first", "last", "as_ptr",
    "slice", "clone", "push_bytes", "push_span", "push_view", "swap", "replace",
    "find_lines", "as_view",
}
# The operations that were free fns at 60b73372, whose names the twin check
# below looks for.  Two methods spell a differently named twin: the manual
# release that was `vec_drop` (the Drop impl owns `drop`, #3614) and the Span
# form of `vec_push_bytes`, which `push_bytes` keeps for the print sink.
VEC_FREE_TWINS = {
    "drop", "valid", "len", "cap", "is_empty", "grow", "ensure_cap", "push",
    "pop", "get", "get_ptr", "set", "clear", "first", "last", "as_ptr",
    "slice", "clone", "push_bytes", "push_view", "swap", "find_lines",
}
VEC_TWIN_OF = {"deinit": "drop", "push_span": "push_bytes"}
OPTION_METHODS = {"is_some", "is_none", "unwrap_or"}

# Methods whose raw (data, len) shape is the print-sink protocol.
PROTOCOL_METHODS = {"push_bytes"}


@pytest.mark.unit
@pytest.mark.parametrize("path,type_name,prefix,want", [
    ("option.ritz", "Option", "option", OPTION_METHODS),
], ids=["Option"])
def test_impl_wraps_each_free_fn(path, type_name, prefix, want):
    path = RITZLIB / path
    methods = _impl_methods(path, type_name)
    assert set(methods) == want, (
        f"impl<T> {type_name}<T>: missing {sorted(want - set(methods))}, "
        f"unexpected {sorted(set(methods) - want)}")
    for name, fn in sorted(methods.items()):
        assert fn.is_pub, f"{type_name}.{name} must be `pub` (#3418)"
        params = [p.name for p in fn.params]
        assert params and params[0] == "self", f"{type_name}.{name} takes self"
        if name in PROTOCOL_METHODS:
            # The print-sink protocol (LANGUAGE_SPEC §2.6): the compiler emits
            # `sink.push_bytes(data: *T, len: i64)`, so the wrapper cannot
            # forward the Span the free fn now takes.
            assert params == ["self", "data", "len"], (
                f"{type_name}.{name}: params {params!r}, want the protocol form")
            continue
        call = f"{prefix}_{name}<T>({', '.join(params)})"
        want_body = f"return {call}" if fn.ret_type is not None else call
        body = _body_text(path, fn)
        assert body == want_body, f"{type_name}.{name}: body {body!r}, want {want_body!r}"


@pytest.mark.unit
def test_impl_vec_holds_each_method():
    """AGAST #4537: `impl<T> Vec<T>` owns the bodies, and the vec_* twins
    (one free fn per operation at 60b73372) are gone from the file."""
    path = RITZLIB / "gvec.ritz"
    methods = _impl_methods(path, "Vec")
    assert set(methods) == VEC_METHODS, (
        f"impl<T> Vec<T>: missing {sorted(VEC_METHODS - set(methods))}, "
        f"unexpected {sorted(set(methods) - VEC_METHODS)}")
    for name, fn in sorted(methods.items()):
        assert fn.is_pub, f"Vec.{name} must be `pub` (#3418)"
        params = [p.name for p in fn.params]
        assert params and params[0] == "self", f"Vec.{name} takes self"
        if name in PROTOCOL_METHODS:
            assert params == ["self", "data", "len"], (
                f"Vec.{name}: params {params!r}, want the print-sink protocol")
            continue
        body = _body_text(path, fn)
        twin = VEC_TWIN_OF.get(name, name)
        if twin in VEC_FREE_TWINS:
            assert not re.search(rf"\bvec_{re.escape(twin)}\s*(<[^<>]*>)?\s*\(", body), (
                f"Vec.{name} forwards to vec_{twin}, not its own body: {body!r}")
    src = path.read_text()
    for name in sorted(VEC_FREE_TWINS):
        assert re.search(rf"^pub fn vec_{re.escape(name)}\b", src, re.M) is None, (
            f"vec_{name} is still a free fn beside Vec.{name} (AGAST #4537)")


# A move-only type: `Vec<Res>.get` / `Option<Res>.unwrap_or` move a Res out of
# a reference, which every compiler refuses at an instance it specialises.
MOVE_ONLY = """\
import ritzlib.gvec
import ritzlib.option
import ritzlib.hashmap
import ritzlib.memory

struct Res
    h: i32

impl Drop for Res
    fn drop(self: @&Res)
        self.h = 0

fn mk() -> Vec<i32>
    var v: Vec<i32> = vec_new<i32>()
    v.push(5)
    return v

fn mko() -> Option<i32>
    return Some(6)

fn one<T>(x: T) -> Vec<T>
    var v: Vec<T> = vec_new<T>()
    v.push(x)
    return v

"""

# Each body, beside a Vec<Res> and an Option<Res>, names `get` / `pop` /
# `unwrap_or` through one receiver shape ritz1 couldn't type.
SHAPES = {
    "index_of_array_local": ("""\
    var arr: [2]Vec<i32> = [Vec<i32> { data: null, len: 0, cap: 0 }, Vec<i32> { data: null, len: 0, cap: 0 }]
    arr[0] = mk()
    return arr[0].get(0) + arr[0].pop()
""", 10),
    "call_result": ("""\
    return mk().get(0) + mko().unwrap_or(0)
""", 11),
    "generic_call_result": ("""\
    return one<i32>(12).get(0)
""", 12),
    "deref_of_pointer": ("""\
    var v: Vec<i32> = mk()
    let p: *Vec<i32> = @v
    return (*p).get(0) + (*p).first() + 3
""", 13),
    "method_result": ("""\
    var v: Vec<i32> = mk()
    return v.slice(0, 1).get(0) + v.slice(0, 1).last() + 4
""", 14),
}


# A global receiver (AGAST #4774): `g.m()` / `(*gp).m()`, where `g` is a
# struct global by value or `gp` one behind a pointer.  binder_check's
# `(*g_binder_map).get(k).unwrap_or(0)` was untyped, so once diag imported
# ritzlib.fs (a move-only Result<DirIter, Errno>) ritz1 refused its own source.
GLOBALS = """\
struct Box2
    a: i32
    b: i32

impl Box2
    fn first(self: @Box2) -> Option<i32>
        return Some(self.a)

var g_box: Box2 = Box2 { a: 0, b: 0 }
var g_boxp: *Box2 = null
var g_mapp: *HashMap<i64, i64> = null

"""

GLOBAL_SHAPES = {
    "global": ("""\
    g_box = Box2 { a: 7, b: 1 }
    return g_box.first().unwrap_or(0) + 8
""", 15),
    "deref_of_global_pointer": ("""\
    var local: Box2 = Box2 { a: 9, b: 2 }
    g_boxp = @local
    return (*g_boxp).first().unwrap_or(0) + 7
""", 16),
    # AGAST #4916: `(*gp).get(k).unwrap_or(..)` through a pointer to a
    # 2-type-param generic (HashMap<K, V>) is a Method receiver whose type
    # method_ret_at gave up on (tp.next != null), so unwrap_or specialised
    # at every Option/Result instance an import names instead of just
    # Option<i64>.
    "deref_of_global_hashmap_pointer": ("""\
    var local: HashMap<i64, i64> = hashmap_with_cap<i64, i64>(4)
    local.insert(42, 99)
    g_mapp = @local
    return ((*g_mapp).get(42).unwrap_or(0) + 7) as i32
""", 106),
}


def _shape_program(body: str, prelude: str = "") -> str:
    return (MOVE_ONLY + prelude + "pub fn main() -> i32\n"
            "    var mo: Vec<Res> = vec_new<Res>()\n"
            "    let om: Option<Res> = None\n"
            "    if mo.len != 0\n"
            "        return 1\n" + body)


# Every wrapper's name, by method syntax.
EVERY_METHOD = """\
import ritzlib.gvec
import ritzlib.option

pub fn main() -> i32
    var v: Vec<i32> = vec_new<i32>()
    v.push(1)
    v.push(2)
    v.push(3)
    v.set(0, 7)
    v.swap(1, 2)
    var t: i64 = v.len() + v.cap() / v.cap()
    if v.is_empty()
        return 1
    t = t + (v.get(0) + v.first() + v.last() + *v.get_ptr(1) + *v.as_ptr()) as i64
    let s: Vec<i32> = v.slice(1, 3)
    let c: Vec<i32> = v.clone()
    t = t + s.len() + c.len() + v.pop() as i64
    v.clear()
    let o: Option<i32> = Some(4)
    let n: Option<i32> = None
    if o.is_none() or n.is_some()
        return 2
    t = t + (o.unwrap_or(0) + n.unwrap_or(9)) as i64
    return (t + v.len()) as i32
"""
# v [7, 3, 2]: len 3 + cap/cap 1; get 7 + first 7 + last 2 + [1] 3 + [0] 7;
# slice 2 + clone 3 + pop 2; unwrap_or 4 + 9; len 0 after clear
EVERY_METHOD_EXIT = 4 + 26 + 7 + 13

ROWS = ([Row(f"receiver[{name}]", COMPILERS, Run(_shape_program(body), code))
         for name, (body, code) in SHAPES.items()]
        + [Row(f"receiver[{name}]", COMPILERS, Run(_shape_program(body, GLOBALS), code))
           for name, (body, code) in GLOBAL_SHAPES.items()]
        + [Row("every_method", COMPILERS, Run(EVERY_METHOD, EVERY_METHOD_EXIT))])


@pytest.mark.integration
@pytest.mark.parametrize("compiler,chunk", table_rows.chunks(ROWS, COMPILERS),
                         ids=[f"{c}-{i}" for c, i in table_rows.chunks(ROWS, COMPILERS)])
def test_every_row(ritz1_bin, tmp_path, compiler, chunk):
    table_rows.assert_ritzlib_rows(compiler, table_rows.chunk(ROWS, compiler, chunk),
                                   ritz1_bin, tmp_path)


# A -nostdlib program: its own `push`, called through receivers ritz1 couldn't
# type, and a Vec<u8> it only names. No call reaches Vec's `push`.
NOSTDLIB = """\
import ritzlib.gvec

struct Buf
    n: i32

impl Buf
    fn push(self: *Buf, x: i32)
        self.n = self.n + x

struct Holder
    raw: Vec<u8>

var g_buf: Buf

fn bp() -> *Buf
    return @g_buf

pub fn main() -> i32
    var h: Holder = Holder { raw: Vec<u8> { data: null, len: 0, cap: 0 } }
    h.raw.len = 0
    var bufs: [2]Buf
    bp().push(4)
    bufs[0].push(1)
    (*bp()).push(2)
    return g_buf.n + h.raw.len as i32
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_untyped_receiver_links_no_malloc(ritz1_bin, tmp_path, compiler):
    src = tmp_path / "main.ritz"
    src.write_text(NOSTDLIB)
    ll = tmp_path / "main.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        proc = subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
    assert proc.returncode == 0 and ll.exists(), (proc.stdout + proc.stderr)[-2000:]
    # A reference, not a declaration: ritz0 declares ritzlib.memory's externs.
    used = [line for line in ll.read_text().splitlines()
            if not line.startswith("declare")
            and re.search(r'@"?(malloc|realloc|vec_grow\$\w+|vec_push\$\w+)"?\(', line)]
    assert not used, f"{compiler} references Vec's push path:\n" + "\n".join(used[:5])
