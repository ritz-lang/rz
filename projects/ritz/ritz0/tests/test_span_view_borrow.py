"""LARB R57, AGAST #3472: a Span view is a borrow, and a move conflicts with one
(LANGUAGE_SPEC §13.5).

A `Span<T>` made from a local root, `v[a..b]` of a Vec or String in a `Span`
slot, or `@x` in one, is an `@` of that root for both of §13.5's rules:

- a loan to the end of its holder's block, so `v.push` beside it is refused;
- R2's "cannot return a reference to local", at a return or tail, directly or
  through a `Span` binding.

Moving a place joins what conflicts with a live `@` of an overlapping place
(R11a): `let p = @v` then `let w = v` is refused, as is moving `h.t` while
`@h.t` is held. Outside a Span slot `v[a..b]` is a copy (§7.8) and lends
nothing. A Span of a Span parameter views the caller's storage, so it returns.
A call's result held in a binding stays unchecked (R2's definite-case limit;
test_return_local_ref.py's `in_a_span`).

`Vec<i32>` is Copy until #2159 gives Vec a Drop, so the move rows use a
`Vec<T>` of a Drop `T`, which is move-only already.

AGAST #3473 gives ritz1 and ritz1_selfhosted the same rule, in Sema's checking
phase (ref_loan.ritz's loans and ref_value.ritz's return check), not in the
emitter.
"""

import pytest

from ref_rules import returns_local
import test_ritz1_for_header as for_header
from test_ref_into_value import COMPILERS, _assert_refused, _main

# A Vec needs the allocator linked in (for_header.UNITS).
compile_with = for_header.compile_with
run_with = for_header.run_with

pytestmark = [pytest.mark.integration, pytest.mark.batched]

TYPES = """\
import ritzlib.gvec
import ritzlib.span

struct T
    x: i32

impl Drop for T
    fn drop(self: @&T)
        self.x = 0

struct H
    t: T
    n: i32

fn three() -> Vec<i32>
    var v: Vec<i32> = vec_new<i32>()
    v.push(1)
    v.push(2)
    v.push(3)
    v
"""


def _held(here, held, verb):
    """move_checker._report's wording."""
    head = (f"cannot move out of `{here}`" if verb == "move"
            else f"cannot borrow `{here}` as {verb}")
    return f"{head} - `{held}` is already borrowed as immutable"


# A `^` marks where the error is reported.
REFUSED = {
    # The ruling's rows.
    "view_then_push": ("fn f()\n    var v = three()\n    let s: Span<i32> = v[0..2]\n"
                       "    ^v.push(4)\n", _held("v", "v", "mutable")),
    "return_a_vec_slice": ("fn f() -> Span<i32>\n    var v = three()\n    return ^v[0..3]\n",
                           returns_local("v")),
    "return_an_array_view": ("fn f() -> Span<i32>\n    var a: [3]i32 = [1, 2, 3]\n    return ^@a\n",
                             returns_local("a")),
    "move_a_borrowed_vec": ("fn f()\n    var v: Vec<T> = vec_new<T>()\n    let p = @v\n"
                            "    let w = ^v\n", _held("v", "v", "move")),
    # R2's binding hop: a Span `let` holding a view of a local.
    "return_a_held_view": ("fn f() -> Span<i32>\n    var v = three()\n"
                           "    let s: Span<i32> = v[0..2]\n    return ^s\n", returns_local("v")),
    # R11a: a field moved out under a loan of it.
    "move_a_borrowed_field": ("fn f()\n    let h = H { t: T { x: 1 }, n: 2 }\n    let p = @h.t\n"
                              "    let w = ^h.t\n", _held("h.t", "h.t", "move")),
}

# Each runs, and returns its value.
LEGAL = {
    # A Span's slice views the caller's storage, not the Span: `t` stays free.
    "a_span_param_resliced": ("fn g(s: Span<i32>) -> Span<i32>\n    var t: Span<i32> = s\n"
                              "    let u: Span<i32> = t[0..1]\n    t = s[u[0]..3]\n    return t[0..2]\n\n"
                              "fn f() -> i32\n    var v = three()\n    let s: Span<i32> = v[0..3]\n"
                              "    let t = g(s)\n    t[1]\n", 3),
    # Outside a Span slot a slice is a copy: nothing is lent.
    "a_copied_slice_then_push": ("fn f() -> i32\n    var v = three()\n    let c = v[0..2]\n"
                                 "    v.push(4)\n    c[1] + v[3]\n", 6),
    # A loan ends with its holder's block.
    "a_move_after_the_loan_ends": ("fn f() -> i32\n    var v: Vec<T> = vec_new<T>()\n"
                                   "    v.push(T { x: 5 })\n    var n: i64 = 0\n    if v.len() > 0\n        let p = @v\n"
                                   "        n = p.len()\n    let w = v\n    n as i32 + w.len() as i32\n", 2),
    # R11a: a move of a field the loan doesn't overlap.
    "a_disjoint_field_move": ("fn f() -> i32\n    let h = H { t: T { x: 4 }, n: 2 }\n    let p = @h.n\n"
                              "    let w = h.t\n    w.x + *p\n", 6),
}


def _params(table):
    for site in sorted(table):
        for compiler in COMPILERS:
            yield pytest.param(site, compiler, id=f"{site}-{compiler}")


@pytest.mark.parametrize("site,compiler", list(_params(REFUSED)))
def test_a_view_or_move_against_a_loan_is_refused(tmp_path, compiler, site):
    body, message = REFUSED[site]
    _assert_refused(compiler, tmp_path, site, _main(TYPES + body, "    0\n"), message)


@pytest.mark.parametrize("site,compiler", list(_params(LEGAL)))
def test_what_the_rule_allows_runs(run_with, compiler, site):
    body, want = LEGAL[site]
    assert run_with(compiler, site, _main(TYPES + body, "    f()\n")) == want
