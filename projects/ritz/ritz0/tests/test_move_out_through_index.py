#!/usr/bin/env python3
"""AGAST #2444: nothing moves out of an element through a pointer or reference.

LARB R9 rule 1: `p[i]` on a `*T`, `@T` or `@&T` whose T is a Vec or Span means
`(*p)[i]`, and reading it by value copies: "for a move-only type that's 'cannot
move out of a reference' (R1)".  R1 gives raw pointers no exception, so `*T` is
judged like `@T` and `@&T`.  A by-value `self` on the element is the same read.

    fn f(p: @Vec<T>) -> T
        return (*p)[1]      # ritz1 and selfhosted accepted it: two owners of one T

What isn't a move stays legal: a copy element (`i32`), a scalar read through a
nested index (AGAST #2159 made `Vec` move-only, so an element of `Vec<Vec<i32>>`
is no longer a copy), a pointer element, a copy field of the element, a
borrowing receiver, `@p[i]`.

A Vec or Span of a Drop type is refused today on ritz0, in gvec.ritz's generic
bodies, and on ritz1 in span.ritz's (#2159's question): so the refusals assert the
`line:col` of this program's own error, and the controls that no such error is
reported at the marked place.  Arrays behind a pointer are #2330's.

The cases are table rows (test_table_rows.py, AGAST #3889), one test per
compiler, not a parametrised matrix.  Each row keeps the id its parametrised
test had, less the compiler and `test_`: `test_an_element_does_not_move_out[
let-Vec-pointer-ritz1]` is `an_element_does_not_move_out[let-Vec-pointer]` on
ritz1.  The refusals are compiled a chunk at a time and each must report
exactly MOVE_OUT_OF_REF at its `^`; the controls and copies are compiled on
their own (an absence or a clean compile is not a batch's to vouch for), and
every failing row is named.
"""

import re

import pytest

from ref_rules import MOVE_OUT_OF_REF
from test_ref_into_value import COMPILERS, MOVE, _compile, _located, _main
from test_table_rows import assert_refusals

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

# No Drop in sight: every read is a copy, and each compiles.
COPIES = {
    "scalar": "fn f(p: {P}Vec<i32>) -> i32\n    let w: i32 = p[1]\n    w\n",
    "vec_of_vecs": "fn f(p: {P}Vec<Vec<i32>>) -> i32\n    let w: i32 = p[1][1]\n    w\n",
    "deref_vec_of_vecs": "fn f(p: {P}Vec<Vec<i32>>) -> i32\n    let w: i32 = (*p)[1][1]\n    w\n",
}


def _src(base, body):
    return BASES[base] + MOVE + _main(body, "    0\n")


def _fill(body, kind, base="Vec"):
    return body.replace("{P}", KINDS[kind]).replace("{B}", base)


# ---- the rows: {old id less `test_` and the compiler: ...} --------------------

# Refused with MOVE_OUT_OF_REF, exactly, at the `^`: (marked program, message).
REFUSALS = {
    **{f"an_element_does_not_move_out[{site}-{base}-{kind}]":
       (_src(base, _fill(MOVES[site], kind, base)), MOVE_OUT_OF_REF)
       for site in sorted(MOVES) for base in sorted(BASES) for kind in sorted(KINDS)},
    **{f"an_element_does_not_move_out_of_a_lent_param[{site}-{base}]":
       (_src(base, LENT_MOVES[site].replace("{B}", base)), MOVE_OUT_OF_REF)
       for site in sorted(LENT_MOVES) for base in sorted(BASES)},
    **{f"a_by_value_self_does_not_move_out_through_a_deref[{kind}]":
       (_src("Vec", _fill(DEREF_RECEIVER, kind)), MOVE_OUT_OF_REF) for kind in sorted(KINDS)},
}

# No MOVE_OUT_OF_REF reported on the `^`'s line: marked programs.
LEFT_ALONE = {f"what_leaves_the_element_alone[{site}-{base}-{kind}]": _src(base, _fill(NOT_MOVES[site], kind, base))
              for site in sorted(NOT_MOVES) for base in sorted(BASES) for kind in sorted(KINDS)}

# Compile cleanly: programs.
COPY_READS = {f"a_copy_element_reads[{site}-{kind}]":
              "import ritzlib.gvec\n\n" + _main(_fill(COPIES[site], kind), "    0\n")
              for site in sorted(COPIES) for kind in sorted(KINDS)}


@pytest.mark.parametrize("compiler", COMPILERS)
def test_every_refusal(tmp_path, compiler):
    assert_refusals(compiler, tmp_path, REFUSALS)


def _wrong_alone(compiler, tmp_path, k, name, marked):
    """Why row `name` fails compiled on its own, or None."""
    if name in LEFT_ALONE:
        src, where = _located(marked)
        comp, _, _ = _compile(compiler, tmp_path, f"row{k}", src)
        out = comp.stdout + comp.stderr
        found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
        line = where.split(":")[0]
        if [f for f in found if f[0].split(":")[0] == line and f[1] == MOVE_OUT_OF_REF]:
            return f"reported a move out at line {line}:\n{out[-600:]}"
        return None
    comp, ll, _ = _compile(compiler, tmp_path, f"row{k}", marked)
    if comp.returncode == 0 and ll.exists():
        return None
    return f"wanted it to compile, got:\n{(comp.stdout + comp.stderr)[-600:]}"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_what_is_no_move_out(tmp_path, compiler):
    """The controls and the copy reads, each compiled on its own."""
    table = {**LEFT_ALONE, **COPY_READS}
    failures = [f"{name}: {why}" for k, (name, marked) in enumerate(table.items())
                for why in [_wrong_alone(compiler, tmp_path, k, name, marked)] if why]
    assert not failures, f"{compiler}: {len(failures)} of {len(table)} rows failed:\n" + "\n".join(failures)
