"""AGAST #3501: ritz1's Sema types locals and expressions itself (#1816 step 2).

THE CHANGE

#3462 gave ritz1 a `Sema` pass that knew local names and fn resolution only.
Every check still to move onto it reads types the emitter computes
mid-lowering (get_expr_type, LocalVar).  Sema now binds each local with its
declared type (params, `let` / `var` annotations, else the initialiser's
type), and `sema_expr_ty` / `sema_expr_type` (ritz1/src/sema_type.ritz) type
an expression from the AST and that scope: literals, names (local, global,
const), calls (through a local's `fn(..) -> T` or the resolved fn), the
comparison and logical operators, `not` / `-` / `@`, casts, member access on a
struct or a pointer to one, and arithmetic whose operands agree.  Anything
else is TYPE_UNKNOWN (-1): Sema doesn't guess.

THE TESTS

`RITZ1_SEMA_PROBE` (ritz1/src/sema_probe.ritz) turns on a test-only probe:
Sema records its answer for each expression it walks, and emit_expr compares
it with get_expr_type and bool_kind on the same node.

- One program pins Sema's answer shape by shape (`RITZ1_SEMA_PROBE=dump`
  prints them), including the ones it must leave unknown and a block's local
  going out of scope.
- The matrix corpus (ritz0/test/*.ritz) compiles with the probe on and no
  expression may disagree.  A floor on the compared count keeps a typer that
  answers "unknown" to everything from passing.  The probe changes no IR (the
  commit compared 457 files with it on and off).

AGAST #3810 folded deref_field's receiver typing in: `*p` of a struct
pointer, a struct element `a[i]`, a method's result, `E.V(..)`, a `:& S` param
as its S, and the `for`, `V(x)` and `let (a, b)` bindings over them.  Where
the emitter's get_expr_type has no answer for `*p`, `a[i]` or `x.m()` it
says i64; the probe takes that as lenient for a struct or pointer.

AGAST #3502 moved bool_check onto Sema, judging with sema_bool_kind.  The probe
also compares that with the emitter's bool_kind on every expression: both sure
and different is a mismatch; one sure and the other not is a `bk-gap`, a place
where a bool report would read differently (or not at all).  The corpus holds
the gaps to a ceiling, so a change can close them but not open new ones.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from test_ref_into_value import RITZ1_BUILD, RITZ_ROOT, _compile

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

# TYPE_* (ritz1/src/ast.ritz) and EXPR_* kinds, for reading the table below.
UNKNOWN, I32, I64, U8, BOOL, PTR, U16 = -1, 1, 2, 3, 4, 5, 9
STRUCT, ARRAY, REF, MUT_REF = 100, 101, 102, 103
E_INT, E_IDENT, E_BINARY, E_UNARY, E_CALL, E_CAST, E_MEMBER, E_NIL = 1, 4, 5, 6, 7, 8, 10, 3
E_INDEX, E_METHOD = 9, 12

SHAPES = """\
const K: i32 = 7
var g: *i32 = null

struct P
    x: i32
    flag: bool
    next: *P

fn small(n: i64) -> u8
    n as u8

fn take(b:& i32) -> i32
    b

fn add(a: i64) -> i32
    a as i32

fn main() -> i32
    let n: i32 = 3
    let b: bool = n < K
    let c = b and true
    var p: P = P { x: 1, flag: false, next: null }
    let q: *P = @p
    let h: fn(i64) -> i32 = add
    let arr: [4]i32 = [1, 2, 3, 4]
    var wide: u16 = 2
    if c
        let add: fn(i64) -> u8 = small
        let f: bool = q.flag
        if add(1) == 1 and f == false
            wide = 3
    let w: u16 = wide + 1
    var s: i32 = q.x + p.next.x * 0
    let t: u8 = small(4)
    let v: i32 = h(2) + add(1)
    let r: i64 = arr[1] as i64
    let m: i32 = take(@&s)
    for k in 0..2
        let z: i32 = k as i32
    let y: i32 = match n
        other => other + 1
    if g != null
        return 1
    w as i32 + s - s + v - v + t as i32 - t as i32 + m - m + y - y + r as i32 - r as i32

struct Q
    v: i32

impl Q
    fn me(self: @Q) -> @Q
        self

enum E
    A(Q)
    B

fn borrow(x:& Q) -> i32
    x.v

fn tup() -> (Q, i32)
    (Q { v: 1 }, 2)

fn recv(pp: *Q) -> i32
    let d = *pp
    let e = E.A(d)
    let m = d.me()
    let (a, n) = tup()
    var qs: [2]Q
    qs[0] = d
    qs[1] = d
    var t: i32 = 0
    for y in qs
        t = t + y.v
    let z = qs[0]
    let r: i32 = match e
        E.A(w) => w.v
        E.B => 0
    d.v + m.v + a.v + n + t + z.v + r

enum F
    One(i32)
    Two(i32, i32)

fn ctor() -> i32
    let o = One(3)
    let w = Two(3, 4)
    let a: i32 = match o
        One(v) => v
        Two(x, y) => x + y
    let b: i32 = match w
        One(v) => v * 2
        Two(x, y) => x - y
    a + b

enum G
    Some(i32)
    Nada

fn slot() -> i32
    let s = Some(4)
    match s
        Some(v) => v
        Nada => 0

fn elems(pb: *u8, bs: [2]bool) -> i32
    var m: [2][3]i32
    var cube: [2][2][3]i32
    let a: i32 = m[1][2] + cube[1][0][2]
    let c: u8 = pb[3]
    let f: bool = bs[1]
    let r = @cube[1]
    if f
        return 1
    a + c as i32
"""

# (line, col, expr kind, Sema's type kind[, name]): what the dump must say.
WANTED = [
    (10, 5, E_IDENT, I64),             # the param n: i64
    (10, 5, E_CAST, U8),               # n as u8
    (19, 18, E_INT, I64),              # 3
    (20, 19, E_BINARY, BOOL),          # n < K
    (20, 19, E_IDENT, I32),            # n: i32
    (20, 23, E_IDENT, I32),            # const K: i32
    (21, 13, E_BINARY, BOOL),          # b and true
    (21, 19, E_INT, BOOL),             # true
    (23, 17, E_UNARY, PTR, "P"),       # @p, a pointer to P
    (23, 18, E_IDENT, STRUCT, "P"),    # p: P
    (25, 24, E_INT, I64),
    (27, 8, E_IDENT, BOOL),            # c, typed off its initialiser
    (29, 23, E_MEMBER, BOOL),          # q.flag through q: *P
    (30, 12, E_CALL, U8),              # add(1): the block's local add, -> u8
    (32, 18, E_BINARY, U16),           # wide + 1: the literal takes u16
    (33, 18, E_MEMBER, I32),           # q.x
    (33, 24, E_MEMBER, I32),           # p.next.x, through the *P field
    (33, 24, E_MEMBER, PTR, "P"),      # p.next
    (34, 17, E_CALL, U8),              # small(4)
    (35, 18, E_CALL, I32),             # h(2) through h: fn(i64) -> i32
    (35, 25, E_CALL, I32),             # add(1) after the block: the fn, -> i32
    (36, 18, E_CAST, I64),             # arr[1] as i64
    (36, 18, E_IDENT, ARRAY),          # arr
    (37, 18, E_CALL, I32),             # take(..)
    (37, 23, E_UNARY, MUT_REF),        # @&s
    (39, 22, E_CAST, I32),             # k as i32
    (40, 24, E_IDENT, I32),            # the scrutinee n
    (42, 8, E_IDENT, PTR),             # global g: *i32
    (42, 13, E_NIL, PTR),              # null
    # A receiver's shapes, which deref_field typed on its own until #3810:
    (58, 5, E_IDENT, STRUCT, "Q"),    # x:& Q reads as a Q
    (64, 13, E_UNARY, STRUCT, "Q"),   # *pp
    (65, 13, E_METHOD, STRUCT, "E"),  # E.A(d) builds an E
    (66, 13, E_IDENT, STRUCT, "Q"),   # d, an inferred `let` of *pp
    (66, 13, E_METHOD, REF, "Q"),     # d.me(): its `-> @Q`
    (73, 17, E_IDENT, STRUCT, "Q"),   # y, an element of qs: [2]Q
    (74, 13, E_INDEX, STRUCT, "Q"),   # qs[0]
    (76, 19, E_IDENT, STRUCT, "Q"),   # w, E.A's payload
    (78, 11, E_IDENT, REF, "Q"),      # m
    (78, 17, E_IDENT, STRUCT, "Q"),   # a, the tuple's first field
    (78, 23, E_IDENT, I32),           # n, its second
    (78, 31, E_IDENT, STRUCT, "Q"),   # z, an inferred `let` of qs[0]
    # A user-enum variant ctor call builds its enum (AGAST #3995), so an
    # inferred `let` of one is the enum and its match arms bind typed:
    (85, 13, E_CALL, STRUCT, "F"),    # One(3)
    (86, 13, E_CALL, STRUCT, "F"),    # Two(3, 4), a multi-field variant
    (87, 24, E_IDENT, STRUCT, "F"),   # o, an inferred `let` of One(3)
    (88, 19, E_IDENT, I32),           # v, One's payload
    (89, 22, E_IDENT, I32),           # x, Two's first field
    (89, 26, E_IDENT, I32),           # y, its second
    (90, 24, E_IDENT, STRUCT, "F"),   # w
    (92, 22, E_IDENT, I32),           # x, bound off w
    # One element typer, `x[i]` of anything indexable (AGAST #3943, #4259):
    # a scalar element, and an N-D array's row (one dimension fewer) and leaf.
    (36, 18, E_INDEX, I32),           # arr[1]
    (108, 18, E_INDEX, I32),          # m[1][2]
    (108, 28, E_INDEX, I32),          # cube[1][0][2]
    (109, 17, E_INDEX, U8),           # pb[3] through a *u8
    (110, 19, E_INDEX, BOOL),         # bs[1]
    (111, 14, E_INDEX, ARRAY),        # cube[1], a [2][3]i32 plane
]

# Shapes Sema leaves unknown: a `for` variable over a range, a catch-all arm binding and a
# scalar `:&` param (take's `b`, line 13: `*b` is how it is read and written).
UNKNOWN_AT = [
    (39, 22, E_IDENT),                 # k
    (41, 18, E_IDENT),                 # other
    (13, 5, E_IDENT),                  # b
    # A user enum's `Some(4)` (or Ok / Err / None) is the builtin's unless
    # the slot names the user enum (users_variant_wins): no slot-free type.
    (100, 13, E_CALL),                 # Some(4)
]

DUMP = re.compile(r"^sema-type: (\d+):(\d+) e(\d+) (-?\d+)(?: (\S+))?$", re.M)
SUMMARY = re.compile(r"sema-probe: (\d+) compared, (\d+) mismatched, (\d+) lenient, "
                     r"(\d+) unknown, (\d+) bool-gap, (\d+) bk-gap")


def _probe_env(value):
    return dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ1_SEMA_PROBE=value)


@pytest.mark.parametrize("compiler", COMPILERS)
def test_sema_types_each_shape(request, tmp_path, compiler, monkeypatch):
    request.getfixturevalue("ritz1_bin")
    monkeypatch.setenv("RITZ1_SEMA_PROBE", "dump")
    comp, ll, _ = _compile(compiler, tmp_path, "shapes", SHAPES)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused it:\n{out}"
    seen = {}
    for line, col, kind, ty, name in DUMP.findall(out):
        seen.setdefault((int(line), int(col), int(kind)), set()).add((int(ty), name))
    for want in WANTED:
        at, ty = want[:3], want[3]
        name = want[4] if len(want) > 4 else None
        got = seen.get(at, set())
        assert any(t == ty and (name is None or n == name) for t, n in got), \
            f"{compiler}: {at} wanted {ty} {name or ''}, got {sorted(got)}\n{out}"
    for at in UNKNOWN_AT:
        assert seen.get(at) == {(UNKNOWN, "")}, f"{compiler}: {at} wanted unknown, got {seen.get(at)}"
    summary = SUMMARY.search(out)
    assert summary and summary.group(2) == "0", f"{compiler}:\n{out}"


# Floor on compared expressions over the corpus (19,000+ at #3501).  A typer
# that answered unknown everywhere would compare none and disagree with nothing.
CORPUS_FLOOR = 15000

# Ceiling on bk-gaps over the corpus: 154 at #3502, 42 at #3768 (which typed
# const array elements, `-> *T` / `-> @T` pointees, `**T` chains, `*@a[i]`,
# array fields through `*p` and nameless tuples; test_ritz1_sema_bk_gap.py),
# 40 at #3024 (a nameless tuple's `*T` / `[N]T` element: `*q`, `b[i]`).
# 29 at #3810, which types a receiver's `*p`, struct `a[i]`, method results
# and the `for` / arm / tuple bindings over them (a field through a generic
# Deref).  What's left: a struct match payload's field,
# `(*(@x)).f` where the emitter is the unsure side, and `K[i]` of a const
# array of structs, which the emitter's get_expr_type guesses is an i64 (a
# guess that refused good programs when Sema copied it).  28 at #3974, which
# types `c?` as its Ok / Some struct.  28 still at #3995, which types a
# user-enum ctor call `One(3)` as its enum (Sema and get_expr_type both) and
# untyped test_issue_struct_enum_variants' lets again: 41 without it.  30 at
# #4248, whose fs Err payload became the user enum Errno: Sema leaves a
# Result payload binding of user-enum type untyped (`Err(e) => errno_code(e)`
# in the two corpus files reading fs's Err; #4265 types it).  23 at
# #3943 / #4259, whose one element typer (sema_elem_ty) types `x[i]`'s scalars
# and bool_check's sbk_index falls back on it: an index through a Vec or Span
# a field, call or method holds.  Lower it as they go.
BK_GAP_CEILING = 23


@pytest.mark.parametrize("compiler", COMPILERS)
def test_sema_types_agree_with_the_emitter_on_the_matrix_corpus(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    env = _probe_env("1")
    compared = 0
    bk_gaps = 0
    mismatches = []
    unsummarised = []
    for src in sorted((RITZ_ROOT / "ritz0" / "test").glob("*.ritz")):
        comp = subprocess.run([str(binary), str(src), "-o", str(tmp_path / "out.ll")],
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
        out = comp.stdout + comp.stderr
        mismatches += [ln for ln in out.splitlines() if ln.startswith("sema-probe: mismatch")]
        summary = SUMMARY.search(out)
        if summary:
            compared += int(summary.group(1))
            bk_gaps += int(summary.group(6))
        elif comp.returncode == 0:
            unsummarised.append(src.name)
    assert not mismatches, f"{compiler}: Sema and the emitter disagree:\n" + "\n".join(mismatches)
    assert not unsummarised, f"{compiler}: compiled without a probe summary: {unsummarised}"
    assert compared >= CORPUS_FLOOR, f"{compiler}: only {compared} expressions compared"
    assert bk_gaps <= BK_GAP_CEILING, f"{compiler}: {bk_gaps} bool-kind gaps, more than {BK_GAP_CEILING}"
