#!/usr/bin/env python3
"""AGAST #2444: nothing moves out of an element through a pointer or reference.

LARB R9 rule 1: `p[i]` on a `*T`, `@T` or `@&T` whose T is a Vec or Span means
`(*p)[i]`, and reading it by value copies: "for a move-only type that's 'cannot
move out of a reference' (R1)".  R1 gives raw pointers no exception, so `*T` is
judged like `@T` and `@&T`.  A by-value `self` on the element is the same read.

    fn f(p: @Vec<T>) -> T
        return (*p)[1]      # ritz1 and selfhosted accepted it: two owners of one T

What isn't a move stays legal: a copy element (`Vec<i32>`, `Vec<Vec<i32>>`: a Vec
has no Drop, so it's a copy, and the ticket's own example is one), a pointer
element, a copy field of the element, a borrowing receiver, `@p[i]`.

A Vec or Span of a Drop type is refused today on ritz0, in gvec.ritz's generic
bodies, and on ritz1 in span.ritz's (#2159's question): so the refusals assert the
`line:col` of this program's own error, and the controls that no such error is
reported at the marked place.  Arrays behind a pointer are #2330's.
"""

import re

import pytest

from ref_rules import MOVE_OUT_OF_REF
from test_ref_into_value import COMPILERS, MOVE, _assert_refused, _compile, _located, _main

pytestmark = pytest.mark.integration

KINDS = {"pointer": "*", "reference": "@", "mut_reference": "@&"}
BASES = {"Vec": "import ritzlib.gvec\n", "Span": "import ritzlib.span\n"}

# `{P}` is the pointer type, over `{B}<T>`, or `{B}<H>` for MOVE's holder of a T.
MOVES = {
    "let": "fn f(p: {P}{B}<T>) -> i32\n    let w: T = ^p[1]\n    0\n",
    "var": "fn f(p: {P}{B}<T>) -> i32\n    var w = ^p[1]\n    0\n",
    "argument": "fn f(p: {P}{B}<T>) -> i32\n    eat(^p[1])\n",
    "return": "fn f(p: {P}{B}<T>) -> T\n    return ^p[1]\n",
    "deref_let": "fn f(p: {P}{B}<T>) -> i32\n    let w: T = (^*p)[1]\n    0\n",
    "deref_var": "fn f(p: {P}{B}<T>) -> i32\n    var w = (^*p)[1]\n    0\n",
    "deref_argument": "fn f(p: {P}{B}<T>) -> i32\n    eat((^*p)[1])\n",
    "deref_return": "fn f(p: {P}{B}<T>) -> T\n    return (^*p)[1]\n",
    "receiver": "fn f(p: {P}{B}<T>) -> i32\n    ^p[1].burn()\n",
    "deref_receiver": "fn f(p: {P}{B}<T>) -> i32\n    (^*p)[1].burn()\n",
    "field": "fn f(p: {P}{B}<H>) -> i32\n    eat(^p[1].t)\n",
    "deref_field": "fn f(p: {P}{B}<H>) -> i32\n    eat((^*p)[1].t)\n",
    "field_receiver": "fn f(p: {P}{B}<H>) -> i32\n    ^p[1].t.burn()\n",
}

# A `name:& T` param is a reference too (R1), with no `*` to write.
LENT_MOVES = {
    "lent": "fn f(v:& {B}<T>) -> i32\n    eat(^v[1])\n",
    "lent_receiver": "fn f(v:& {B}<T>) -> i32\n    ^v[1].burn()\n",
    "lent_field": "fn f(v:& {B}<H>) -> i32\n    eat(^v[1].t)\n",
}

# `^` marks a place that must not be reported.
NOT_MOVES = {
    "copy_field": "fn f(p: {P}{B}<T>) -> i32\n    ^p[1].id\n",
    "deref_copy_field": "fn f(p: {P}{B}<T>) -> i32\n    (^*p)[1].id\n",
    "lent_receiver": "fn f(p: {P}{B}<T>) -> i32\n    ^p[1].look()\n",
    "borrow": "fn f(p: {P}{B}<T>) -> i32\n    let q: @T = ^@p[1]\n    q.id\n",
    "pointer_element": "fn f(p: {P}{B}<*T>) -> i32\n    let q: *T = ^p[1]\n    q.id\n",
    "deref_pointer_element": "fn f(p: {P}{B}<*T>) -> i32\n    let q: *T = (^*p)[1]\n    q.id\n",
    "holder_copy_field": "fn f(p: {P}{B}<H>) -> i32\n    ^p[1].t.id\n",
    # A slice isn't an element: #2448 refuses it through a pointer, in its own words.
    "slice": "fn f(p: {P}{B}<T>) -> i32\n    let s = ^p[0..1]\n    0\n",
    "deref_slice": "fn f(p: {P}{B}<T>) -> i32\n    let s = (^*p)[0..1]\n    0\n",
}

# A by-value `self` through a deref, with no `[]`: R9's `(*p).m()` (#2175), the
# same receiver check as `(*p)[i].m()`.
DEREF_RECEIVER = "fn f(r: {P}T) -> i32\n    (^*r).burn()\n"

# No Drop in sight: every element is a copy, and each compiles.
COPIES = {
    "scalar": "fn f(p: {P}Vec<i32>) -> i32\n    let w: i32 = p[1]\n    w\n",
    "vec_of_vecs": "fn f(p: {P}Vec<Vec<i32>>) -> i32\n    let w: Vec<i32> = p[1]\n    0\n",
    "deref_vec_of_vecs": "fn f(p: {P}Vec<Vec<i32>>) -> i32\n    let w: Vec<i32> = (*p)[1]\n    0\n",
}


def _src(base, body):
    return BASES[base] + MOVE + _main(body, "    0\n")


def _fill(body, kind, base="Vec"):
    return body.replace("{P}", KINDS[kind]).replace("{B}", base)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("site", sorted(MOVES))
def test_an_element_does_not_move_out(tmp_path, compiler, kind, base, site):
    body = _fill(MOVES[site], kind, base)
    _assert_refused(compiler, tmp_path, f"{site}_{base}_{kind}", _src(base, body), MOVE_OUT_OF_REF)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("site", sorted(LENT_MOVES))
def test_an_element_does_not_move_out_of_a_lent_param(tmp_path, compiler, base, site):
    body = LENT_MOVES[site].replace("{B}", base)
    _assert_refused(compiler, tmp_path, f"{site}_{base}", _src(base, body), MOVE_OUT_OF_REF)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
def test_a_by_value_self_does_not_move_out_through_a_deref(tmp_path, compiler, kind):
    _assert_refused(compiler, tmp_path, f"deref_self_{kind}",
                    _src("Vec", _fill(DEREF_RECEIVER, kind)), MOVE_OUT_OF_REF)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("base", sorted(BASES))
@pytest.mark.parametrize("site", sorted(NOT_MOVES))
def test_what_leaves_the_element_alone(tmp_path, compiler, kind, base, site):
    src, where = _located(_src(base, _fill(NOT_MOVES[site], kind, base)))
    comp, _, _ = _compile(compiler, tmp_path, f"{site}_{base}_{kind}", src)
    out = comp.stdout + comp.stderr
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    line = where.split(":")[0]
    assert not [f for f in found if f[0].split(":")[0] == line and f[1] == MOVE_OUT_OF_REF], \
        f"{compiler}: {site} reported a move out at line {line}:\n{src}\n{out[-2000:]}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("kind", sorted(KINDS))
@pytest.mark.parametrize("site", sorted(COPIES))
def test_a_copy_element_reads(tmp_path, compiler, kind, site):
    src = "import ritzlib.gvec\n\n" + _main(_fill(COPIES[site], kind), "    0\n")
    comp, ll, _ = _compile(compiler, tmp_path, f"{site}_{kind}", src)
    assert comp.returncode == 0 and ll.exists(), (comp.stdout + comp.stderr)[-2000:]
