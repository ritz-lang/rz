"""`@a` of an array, or of a Vec, fits a `Span<T>` slot (AGAST #3595).

LANGUAGE_SPEC §13: "A whole array is the same for a `Span<T>`: `@a` fits and
`a` doesn't", and a borrowed `Vec<T>` is a view of its elements too.  The
emitter has always built `Span { ptr, len }` from both; ritz0's typing pass
said `expected Span<u8>, got @[3]u8`.  Its element must still be the Span's,
and a value (not a reference) still doesn't fit.

The rows run the typing pass alone, in-process: no compile, no link.
"""

import pytest

import ritz_ast as rast
from type_checker import TypeChecker

from test_checker_corpus_gaps import types

pytestmark = pytest.mark.unit

# `{S}` is what `a` is, `{E}` the expression put in the Span slot.
SITES = {
    "argument": "fn g(b: Span<u8>) -> i64\n    b.len\n\nfn f(a: {S}) -> i64\n    g({E})\n",
    "let": "fn f(a: {S}) -> i64\n    let b: Span<u8> = {E}\n    b.len\n",
    "assign": "fn f(a: {S}, b: Span<u8>) -> i64\n    var c = b\n    c = {E}\n    c.len\n",
    "struct_literal": ("struct H\n    b: Span<u8>\n\nfn f(a: {S}) -> i64\n"
                       "    let h = H { b: {E} }\n    h.b.len\n"),
    "tail": "fn f(a: {S}) -> Span<u8>\n    {E}\n",
}


def _src(site: str, held: str, expr: str) -> str:
    return SITES[site].replace("{S}", held).replace("{E}", expr)


# What `a` is, and how it goes in.  For the tail, `a` is already the reference.
FITS = {
    "array_ref": ("[3]u8", "@a"),
    "array_mut_ref": ("[3]u8", "@&a"),
    "vec_ref": ("Vec<u8>", "@a"),
}


@pytest.mark.parametrize("site", sorted(SITES))
@pytest.mark.parametrize("shape", sorted(FITS))
def test_borrow_fits_span(site, shape):
    held, expr = FITS[shape]
    if site == "tail":
        held, expr = expr[:-1] + held, "a"     # `a: @[3]u8`, tail `a`
    assert types(_src(site, held, expr)) == []


@pytest.mark.parametrize("held, expr, says", [
    # A bare array is a value: `a` doesn't fit (the spec's own words).
    ("[3]u8", "a", "a value doesn't fit a reference slot"),
    # The element must be the Span's: no conversion (LARB R5, AGAST #2781).
    ("[3]i8", "@a", "an array only fits a slot of the same element type"),
    ("Vec<i32>", "@a", "expected Span<u8>, got @Vec<i32>"),
    # A Vec by value is not a borrow of one.
    ("Vec<u8>", "a", "expected Span<u8>, got Vec<u8>"),
    # Only a Vec is a view: another generic struct isn't.
    ("Box<u8>", "@a", "expected Span<u8>, got @Box<u8>"),
])
def test_still_refused(held, expr, says):
    errs = types(_src("argument", held, expr))
    assert any(says in e for e in errs), errs


def test_the_tickets_repro():
    src = ("fn n(b: Span<u8>) -> i64\n    b.len\n\n"
           "fn main() -> i32\n    var a: [3]u8 = [1, 2, 3]\n    (n(@a) - 3) as i32\n")
    assert types(src) == []


def test_generic_span_slot():
    # A generic slot `Span<T>`: T stands for whatever it is instantiated with.
    src = ("fn g<T>(b: Span<T>) -> i64\n    b.len\n\n"
           "fn f(a: [3]u8, v: Vec<u8>) -> i64\n    g(@a) + g(@v)\n")
    assert types(src) == []


def _named(name):
    return rast.NamedType(None, name, [])


@pytest.mark.parametrize("held, slot, fits", [
    # A generic instance's body (type_bodies) spells both `Name$T`.
    (_named("Vec$u8"), "Span$u8", True),
    (_named("Vec$i32"), "Span$u8", False),
    (rast.ArrayType(None, 3, _named("u8")), "Span$u8", True),
])
def test_monomorphised_spelling(held, slot, fits):
    ref = rast.RefType(None, held, False)
    assert TypeChecker()._types_compatible(ref, _named(slot)) is fits
