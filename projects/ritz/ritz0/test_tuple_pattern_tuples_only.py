#!/usr/bin/env python3
"""A `(…)` pattern destructures tuples only (LARB R67, AGAST #3499).

    struct Bounds / x_min, y_min, x_max, y_max: i32
    let (_, y_min, _, y_max) = b      # ritz0 bound the fields in order

ritz0 bound a named struct's fields positionally, in declaration order: add a
field to `Bounds` and every `let (…)` of one silently rebinds (R19's
renumbering hazard).  With fewer names than fields it died with an unlocated
`ValueError`.  It is now a located refusal at the `(`:

    `Bounds` is a struct, not a tuple: read its fields

A generic struct is named without its type arguments.  Tuples still
destructure.  ritz1 is AGAST #3500, so only ritz0 runs here.
"""

import os
import re
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
from test_borrow_param_ref_field import _run

RITZ_ROOT = Path(__file__).resolve().parent.parent

_BOUNDS = ("struct Bounds\n    x_min: i32\n    y_min: i32\n"
           "    x_max: i32\n    y_max: i32\n\n")
_TRIPLE = "struct Triple\n    a: i32\n    b: i32\n    c: i32\n\n"
_PAIR = ("struct Pair<T>\n    x: T\n    y: T\n\n"
         "fn mk<T>(a: T, b: T) -> Pair<T>\n    Pair<T> { x: a, y: b }\n\n")


def _main(*lines, pre=""):
    return pre + "fn main() -> i32\n" + "".join(f"    {line}\n" for line in lines)


# Each row: the source and the struct the refusal names.  Every source has
# exactly one `let (`, the refused one.
REFUSED = {
    "local_all_names": (_main("let b = Bounds { x_min: 1, y_min: 2, x_max: 3, y_max: 4 }",
                              "let (p, q, r, s) = b", "q + s", pre=_BOUNDS), "Bounds"),
    # The ruling's 3 fields, 2 names: an unlocated ValueError before.
    "fewer_names_than_fields": (_main("let t = Triple { a: 1, b: 2, c: 3 }",
                                      "let (a, b) = t", "a + b", pre=_TRIPLE), "Triple"),
    "call_result": ("fn mk_t() -> Triple\n    Triple { a: 1, b: 2, c: 3 }\n\n"
                    + _main("let (a, b, c) = mk_t()", "a + b + c", pre=_TRIPLE), "Triple"),
    "generic_struct": (_main("let (a, b) = mk<i16>(1, 2)", "(a + b) as i32", pre=_PAIR),
                       "Pair"),
    # Specialised by monomorph before emission: the `(` must survive it.
    "in_generic_fn": (_PAIR + "fn sum<T>(a: T, b: T) -> T\n    let (u, v) = mk<T>(a, b)\n"
                      "    u + v\n\n" + _main("sum<i32>(1, 2)"), "Pair"),
}


def _paren(source):
    """1-based line and column of the refused pattern's `(`."""
    for line, text in enumerate(source.split("\n"), 1):
        if "let (" in text:
            return line, text.index("let (") + len("let ") + 1
    raise AssertionError("no `let (` in source")


def _ritz0(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return run_ritz0([str(src), "-o", str(tmp_path / "unit.ll")], cwd=tmp_path, env=env,
                     timeout=300)


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz0_refuses_a_tuple_pattern_on_a_struct(tmp_path, name):
    source, struct = REFUSED[name]
    proc = _ritz0(tmp_path, source)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"ritz0 accepted {name}"
    line, col = _paren(source)
    want = (rf"unit\.ritz:{line}:{col}: .*`{struct}` is a struct, not a tuple: "
            rf"read its fields$")
    assert len(re.findall(want, out, re.M)) == 1, out[-800:]
    assert "Traceback" not in out and "ValueError" not in out, out[-800:]
    assert not (tmp_path / "unit.ll").exists(), f"ritz0 wrote IR for {name}"


# Tuples still destructure.  Each returns the number of its first failed check.
KEPT = {
    "pair_from_fn": ("fn two() -> (i32, i64)\n    (3, -5000000000)\n\n"
                     + _main("let (a, b) = two()", "if a != 3", "    return 1",
                             "if b != -5000000000", "    return 2", "0")),
    # A tuple whose element is a struct: the element binds whole.
    "struct_element": ("fn two() -> (Triple, u8)\n    (Triple { a: 1, b: 2, c: 3 }, 200)\n\n"
                       + _main("let (t, k) = two()", "if t.c != 3", "    return 1",
                               "if k != 200", "    return 2", "0", pre=_TRIPLE)),
    "three_in_generic": ("fn tri<T>(a: T) -> (T, T, T)\n    (a, a + a, a + a + a)\n\n"
                         + _main("let (a, b, c) = tri<i16>(-300)", "if a + b + c != -1800",
                                 "    return 1", "0")),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(KEPT))
def test_ritz0_still_destructures_a_tuple(tmp_path, name):
    assert _run("ritz0", None, tmp_path, name, KEPT[name]) == 0
