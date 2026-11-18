"""AGAST #3509: ritz1 resolves `.` through Deref / DerefMut on Sema (#1816).

THE CHANGE

R17 (LANGUAGE_SPEC §7.7, AGAST #3015): `s.f` reaches through a struct that
implements `Deref` / `DerefMut`.  ritz1 rewrote each statement into
`(*S_deref(@s)).f` as the emitter reached it (df_rewrite_stmt in emit_fn,
emit_impl_method, emit_stmt and the match-arm lowering), kept the calls it made
in a side table find_call_fn asked, and checked the impls (df_check_impls) at
the top of emit_module.  Now Sema's walk resolves each statement before any
other check reads it, each call it makes carries its annotation
(Expr.deref_step: the method and the place it lends, which ref_check reads),
and the emitter only lowers it.  deref_impls_check runs first in sema_check_module.

Sema left some bindings untyped (AGAST #3501's scope): a `for` variable, a
match-arm or tuple binding, an inferred `let`, a `:&` param.  The emitter typed
them, so deref_field noted what `.` on each saw (SemaVar.recv).  AGAST #3810
folded those shapes into sema_expr_ty and has sema_walk bind each typed;
deref_field reads sema_expr_ty alone.

The rule's own words are test_ritz1_box_field.py's, on all three compilers.
The commit compared every file of ritz0/test, ritzlib, examples and ritz1/src,
the inline programs of the Deref / fn-field tests and the rows below, plain
and --test-table, against the pre-move compiler: the same IR for each
accepted program, the same located Deref error for each refusal.

THE TESTS

- A Deref error now stops the compile before emission: the unsupported
  `for` iterable after it, an error only the emitter reports, is no longer
  printed.  Red on the base.
- REACH: one row per kind of receiver the emitter typed and Sema had to learn
  to (each row's note, removed alone, turns that row red).
- The emitter rewrites nothing: no df_rewrite_* left, and emitter_core no
  longer imports deref_field (#1816's layering): find_call_fn finds a step's
  `S_deref` by its symbol, and ref_check reads the annotation's place.
"""

import re
from pathlib import Path

import pytest

from test_ref_into_value import _compile
from test_table_rows import assert_runs

RITZ_ROOT = Path(__file__).resolve().parent.parent
SRC = RITZ_ROOT / "ritz1" / "src"
COMPILERS = ["ritz1", "ritz1_selfhosted"]

STOPS_BEFORE_EMIT = """\
struct Ro<T>
    ptr: *T

impl<T> Deref for Ro<T>
    fn deref(self: @Ro<T>) -> @T
        @*self.ptr

struct Lone
    n: i64

impl DerefMut for Lone
    fn deref_mut(self: @&Lone) -> @&Lone
        self

struct H
    k: i64

fn main() -> i32
    var h: H
    h.k = 1
    var r: Ro<H>
    r.ptr = @h
    r.k = 11
    var q: i32 = 3
    for x in q
        h.k = 2
    0
"""

STOPS_WANTED = [
    ("11:6", "`Lone` implements `DerefMut` without `Deref`"),
    ("23:7", "`r.k = …` needs `DerefMut`, and `Ro<H>` implements only `Deref`"),
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_deref_error_stops_the_compile_before_emission(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    comp, ll, _ = _compile(compiler, tmp_path, "sema_deref", STOPS_BEFORE_EMIT)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it:\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert found == STOPS_WANTED, f"{compiler}:\n{out}"


_BOX = ("struct Box<T>\n    ptr: *T\n\n"
        "impl<T> Deref for Box<T>\n    fn deref(self: @Box<T>) -> @T\n        @*self.ptr\n\n"
        "impl<T> DerefMut for Box<T>\n    fn deref_mut(self: @&Box<T>) -> @&T\n"
        "        @&*self.ptr\n\n")
_H = ("struct H\n    k: i64\n    f: fn(i64) -> i64\n\n"
      "impl H\n    fn get(self: @H) -> i64\n        self.k\n\n"
      "fn dbl(v: i64) -> i64\n    v * 2\n\n"
      "enum Opt\n    Some(Box<H>)\n    Non\n\n"
      "struct Pair\n    b: Box<H>\n    n: i32\n\n"
      "fn two(b: Box<H>) -> (Box<H>, i32)\n    (b, 1)\n\n")
_MAIN = ("pub fn main() -> i32\n    var h: H\n    h.k = 9\n    h.f = dbl\n"
         "    var b: Box<H>\n    b.ptr = @h\n")

# name -> (the fns before main, main's rest, what it returns).  Each `.` on the
# receiver reaches H's `k` (or `get`) through Box's Deref.
REACH = {
    # A `for` variable over an array: sema_bind_for over sema_elem_ty.
    "for_variable": ("", ("    var bs: [2]Box<H>\n    bs[0] = b\n    bs[1] = b\n    var t: i64 = 0\n"
                         "    for x in bs\n        t = t + x.k\n    t as i32\n"), 18),
    # A fn field called on a `for` variable (R41's rewrite, same typing).
    "fn_field_on_a_for_variable": ("", ("    var hs: [2]H\n    hs[0] = h\n    hs[1] = h\n    var t: i64 = 0\n"
                                       "    for y in hs\n        t = t + y.f(1)\n    t as i32\n"), 4),
    # A match arm's payload binding, the scrutinee an inferred `let` of `E.V(..)`:
    # sema_arm_payload_ty, and sema_expr_ty's `E.V(..)` for the `let`.
    "match_payload": ("", ("    let o = Opt.Some(b)\n    let r: i64 = match o\n"
                          "        Opt.Some(x) => x.k + x.get()\n        Opt.Non => 1\n    r as i32\n"), 18),
    # A payload binding read as an `if` value's arm, inside a match statement.
    "match_statement_payload": ("", ("    let o = Opt.Some(b)\n    var r: i64 = 0\n    match o\n"
                                    "        Opt.Some(x) =>\n            r = if x.k > 1\n                x.k\n"
                                    "            else\n                0\n        Opt.Non => r = 1\n    r as i32\n"), 9),
    # An `Option<Box<H>>`'s `Some(x)`: a tagged payload (sema_tagged_payload).
    "option_payload": ("fn mo(b: Box<H>) -> Option<Box<H>>\n    Some(b)\n\n",
                       ("    let o = mo(b)\n    let r: i64 = match o\n        Some(x) => x.k\n"
                       "        None => 1\n    r as i32\n"), 9),
    # A tuple binding: sema_bind_tuple.
    "tuple_binding": ("", "    let (c, n) = two(b)\n    (c.k as i32) + n\n", 10),
    # An inferred `let` of an element: sema_expr_ty's `a[i]` (sema_elem_ty).
    "inferred_element": ("", ("    var bs: [2]Box<H>\n    bs[0] = b\n    let c = bs[0]\n"
                             "    c.k as i32\n"), 9),
    # An inferred `let` of an element of a `@Vec<Box<H>>`: the Vec's element,
    # not the Vec (sema_elem_ty through a reference).
    "inferred_vec_element_through_reference": (
        ("struct Vec<T>\n    data: *T\n    len: i64\n    cap: i64\n\n"
        "fn g(v: @Vec<Box<H>>) -> i64\n    let c = v[0]\n    c.k\n\n"),
        ("    var arr: [1]Box<H>\n    arr[0] = b\n    var v: Vec<Box<H>>\n    v.data = @arr[0]\n"
        "    v.len = 1\n    v.cap = 1\n    g(@v) as i32\n"), 9),
    # `x:& Box<H>` reads as a Box (sema_bind_param): `x.k += 1` steps through deref_mut.
    "borrow_param": ("fn f(x:& Box<H>) -> i64\n    x.k += 1\n    x.k + x.get()\n\n",
                     "    f(b) as i32\n", 20),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_deref_reaches_each_receiver_the_emitter_typed(tmp_path, compiler):
    # One table test per compiler (docs/TESTING.md, "What a ritz0 pytest case
    # costs"): a failure still names its own row.
    rows = {name: ("import ritzlib.option\n\n" + _BOX + _H + before + _MAIN + body, wanted)
            for name, (before, body, wanted) in sorted(REACH.items())}
    assert_runs(compiler, tmp_path, rows)


@pytest.mark.unit
def test_the_emitter_rewrites_nothing():
    for f in sorted(SRC.glob("*.ritz")):
        text = f.read_text()
        assert "df_rewrite_" not in text, f"{f.name} still rewrites `.` through Deref"
        assert "df_check_impls" not in text, f"{f.name}: the impl check is deref_impls_check, on Sema"
    core = (SRC / "emitter_core.ritz").read_text()
    assert not re.search(r"^import deref_field\b", core, re.MULTILINE), \
        "emitter_core does not import deref_field (#1816)"


@pytest.mark.unit
def test_deref_field_types_its_receivers_with_sema_expr_ty():
    # AGAST #3810: `.`'s receiver is typed by sema_expr_ty, and sema_walk
    # binds the locals it used to leave untyped; deref_field keeps no typer
    # (df_ty) or notes (SemaVar.recv, df_note_*) of its own.
    df = (SRC / "deref_field.ritz").read_text()
    for name in ("fn df_ty(", "fn df_elem_ty(", "df_note_", "v.recv"):
        assert name not in df, f"deref_field.ritz still has {name}"
    sema = (SRC / "sema.ritz").read_text()
    assert not re.search(r"^\s+recv: \*SemaTy", sema, re.MULTILINE), "SemaVar.recv is gone"
    walk = (SRC / "sema_walk.ritz").read_text()
    assert "df_note_" not in walk, "sema_walk binds the types itself"
