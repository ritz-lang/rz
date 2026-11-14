"""AGAST #2390: two array elements ritz1 typed wrong, both caught by clang.

    var a: [2]StrView
    a[0] = "ab"             # stored a %Span$u8 where %StrView is expected

    struct W<T>
        a: [2]T
    var w: W<i32>           # %W$i32 = type {[2 x %T]}: an unsized alloca

A bare `"..."` is a %Span$u8 (#98), layout-equal to %StrView (#168); every
other StrView slot rebuilds it, an array element didn't.  Monomorphisation
substituted `x: T` and `p: *T` and `a: [N]*T` but not `a: [N]T`.

Each holder is also walked by `for`, which these two blocked (#2375).  ritz0
ran all of it already: its rows pin that the three compilers agree.

Each program returns 0, or the number of the first check that failed.
"""

from pathlib import Path

import pytest

from test_borrow_param_ref_field import _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

RITZ_ROOT = Path(__file__).resolve().parent.parent
SELFHOSTED_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1_selfhosted"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

MAIN = "pub fn main() -> i32\n"


@pytest.fixture
def run_with(ritz1_bin, tmp_path):
    """_run, by compiler name.  The gate builds ritz1_selfhosted before pytest."""
    bins = {"ritz0": None, "ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}

    def go(compiler, name, program):
        return _run("ritz0" if compiler == "ritz0" else "ritz1", bins[compiler],
                    tmp_path, name, program)
    return go


def _ind(body: str, n: int = 4) -> str:
    return "".join(" " * n + line + "\n" for line in body.splitlines())


# Walk a [3]StrView holder: lengths 2, 3, 1 in order, and the bytes of the
# middle one, so a store that kept the pointer but dropped the length (or
# swapped the pair) fails.
def _walk_strs(it: str) -> str:
    return _ind(f"var n: i64 = 0\nvar i: i32 = 0\nfor v in {it}\n"
                f"    if i == 0 and v.len != 2\n        return 1\n"
                f"    if i == 1 and v.len != 3\n        return 2\n"
                f"    if i == 2 and v.len != 1\n        return 3\n"
                f"    if i == 1 and *(v.ptr + 2) != 122\n        return 4\n"
                f"    n = n + v.len\n    i = i + 1\nif n != 6\n    return 5\nreturn 0\n")


def _fill_strs(place: str) -> str:
    return _ind(f'{place}[0] = "ab"\n{place}[1] = "xyz"\n{place}[2] = "q"\n')


# The canaries either side of the array show up a wrong stride or size.
_H = "struct H\n    lo: i64\n    a: [3]StrView\n    hi: i64\n\n"
_CANARIES = _ind("if h.lo != 11 or h.hi != 22\n    return 9\n")

STRVIEW_STORES = {
    # The ticket's own shape: an element of an [N]StrView local.
    "local": MAIN + "    var a: [3]StrView\n" + _fill_strs("a") + _walk_strs("a"),
    "global": "var g: [3]StrView\n\n" + MAIN + _fill_strs("g") + _walk_strs("g"),
    "field": (_H + MAIN + "    var h: H\n    h.lo = 11\n    h.hi = 22\n"
              + _fill_strs("h.a") + _CANARIES + _walk_strs("h.a")),
    # A field of a field, and a field through a pointer: emit_assign's
    # `x.f[i] = v`, where the local-field path above doesn't reach.
    "nested_field": (_H + "struct O\n    k: i32\n    h: H\n\n" + MAIN
                     + "    var o: O\n    o.h.lo = 11\n    o.h.hi = 22\n" + _fill_strs("o.h.a")
                     + _ind("if o.h.lo != 11 or o.h.hi != 22\n    return 9\n") + _walk_strs("o.h.a")),
    "ptr_field": (_H + MAIN + "    var h: H\n    h.lo = 11\n    h.hi = 22\n    let p: *H = @h\n"
                  + _fill_strs("p.a") + _CANARIES + _walk_strs("h.a")),
    # Through a `:&` param: stored as `*p = v` at the element (#2440).
    "lent_param": ("fn put(a:& [3]StrView)\n" + _fill_strs("a") + "\n" + MAIN
                   + "    var a: [3]StrView\n    put(a)\n" + _walk_strs("a")),
    # A whole StrView through a pointer: the deref store shares the rule.
    "deref": (MAIN + '    var s: StrView = "q"\n    let p: *StrView = @s\n    *p = "abc"\n'
              + _ind("if s.len != 3\n    return 1\nif *(s.ptr + 2) != 99\n    return 2\n"
                     "return 0\n")),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("holder", sorted(STRVIEW_STORES))
def test_a_string_literal_stores_into_a_strview_element(run_with, compiler, holder):
    assert run_with(compiler, f"sv_{holder}", STRVIEW_STORES[holder]) == 0


def _generic(arg: str, fill: tuple, check: str, prelude: str = "") -> str:
    """W<arg> holds `a: [3]T` between canaries; fill it, check each element
    with `check` (an expression over `v` and `i`), and walk it with `for`."""
    body = (f"var w: W<{arg}>\nw.lo = 11\nw.hi = 22\n"
            + "".join(f"w.a[{i}] = {v}\n" for i, v in enumerate(fill))
            + "if w.lo != 11 or w.hi != 22\n    return 9\n"
            + f"var i: i32 = 0\nfor v in w.a\n    if not ({check})\n        return 1 + i\n"
            + "    i = i + 1\nif i != 3\n    return 8\nreturn 0\n")
    return (prelude + "struct W<T>\n    lo: i64\n    a: [3]T\n    hi: i64\n\n"
            + MAIN + _ind(body))


_P = "struct P\n    x: i32\n    y: i64\n\n"
_BOX = "struct Box<T>\n    v: T\n\n"
_TARGETS = "var t0: i32 = 5\nvar t1: i32 = 6\nvar t2: i32 = 7\n\n"

GENERIC_FIELDS = {
    "i32": _generic("i32", ("-70000", "-70001", "-70002"), "v == -70000 - i"),
    # A narrow element: a stride of 8 shows up in the canaries and the walk.
    "u8": _generic("u8", ("200", "201", "202"), "v as i32 == 200 + i"),
    "f64": _generic("f64", ("1.5", "2.5", "3.5"), "v == 1.5 + i as f64"),
    "bool": _generic("bool", ("true", "false", "true"), "v == (i != 1)"),
    # A struct argument.
    "struct": _generic("P", ("P { x: 1, y: 10 }", "P { x: 2, y: 20 }", "P { x: 3, y: 30 }"),
                       "v.x == i + 1 and v.y == (i as i64 + 1) * 10", _P),
    # The two halves of the ticket together: a "..." into a T = StrView element.
    "strview": _generic("StrView", ('"ab"', '"xyz"', '"abcd"'), "v.len == 2 + i as i64"),
    # A pointer argument: `[3]*i32`.
    "ptr": _generic("*i32", ("@t0", "@t1", "@t2"), "*v == 5 + i", _TARGETS),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("arg", sorted(GENERIC_FIELDS))
def test_a_generic_array_field_takes_its_argument(run_with, compiler, arg):
    assert run_with(compiler, f"gen_{arg}", GENERIC_FIELDS[arg]) == 0


# T reached through a generic element, and T one of two parameters.
GENERIC_SHAPES = {
    "box_elem": (_BOX + "struct W<T>\n    lo: i64\n    a: [2]Box<T>\n    hi: i64\n\n" + MAIN
                 + _ind("var w: W<i32>\nw.lo = 11\nw.hi = 22\nw.a[0].v = 4\nw.a[1].v = 5\n"
                        "if w.lo != 11 or w.hi != 22\n    return 9\n"
                        "var n: i32 = 0\nfor b in w.a\n    n = n * 10 + b.v\n"
                        "if n != 45\n    return 1\nreturn 0\n")),
    "two_params": ("struct KV<K, V>\n    k: K\n    a: [2]V\n    hi: i64\n\n" + MAIN
                   + _ind("var w: KV<i64, u16>\nw.k = 11\nw.hi = 22\nw.a[0] = 40000\nw.a[1] = 40001\n"
                          "if w.k != 11 or w.hi != 22\n    return 9\n"
                          "var n: i64 = 0\nfor v in w.a\n    n = n + v as i64\n"
                          "if n != 80001\n    return 1\nreturn 0\n")),
}


def _shape_rows():
    for shape in sorted(GENERIC_SHAPES):
        for compiler in COMPILERS:
            marks = ()
            if shape == "box_elem" and compiler == "ritz0":
                marks = pytest.mark.xfail(strict=True, reason="AGAST #3080: ritz0 crashes on it")
            yield pytest.param(shape, compiler, marks=marks, id=f"{shape}-{compiler}")


@pytest.mark.parametrize(("shape", "compiler"), list(_shape_rows()))
def test_a_generic_array_field_shape(run_with, compiler, shape):
    assert run_with(compiler, f"shape_{shape}", GENERIC_SHAPES[shape]) == 0
