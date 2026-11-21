#!/usr/bin/env python3
"""A reference type argument has a spelling of its own (AGAST #2384).

ritz0 mangles `@T` as `ref_T` and `@&T` as `refmut_T` (monomorph.py
mangle_type_name).  ritz1 spelled both as nothing, so `Option<@&A>` and
`Option<@&B>` were one `%Option$` with the 144-byte fallback payload, and
`Some(r)` stored a `ptr` as an i64: invalid IR.  Each row runs on ritz0, ritz1
and ritz1_selfhosted.  Whether `Some(r)` of an `@T` is refused there is
test_at_into_mut.py's.
"""

import re

import pytest

from test_ref_into_value import COMPILERS, _compile, _ids, _main, _run

pytestmark = pytest.mark.integration

TYPES = """\
struct A
    x: i32

struct B
    x: i64
    y: i64
    z: i64

"""

# Each is the fns, then `main`'s body; main must exit with the value given.
RUNS = {
    # Written through the bound payload.
    "option_mutable": ("fn f(r: @&A) -> Option<@&A>\n    Some(r)\n",
                       "    var a = A { x: 1 }\n    match f(@&a)\n        Some(m) => m.x = 5\n"
                       "        None => pass\n    a.x\n", 5),
    # A second referent with another layout: its own type, read at B.
    "distinct_referents": ("fn f(r: @&A) -> Option<@&A>\n    Some(r)\n\n"
                           "fn g(r: @&B) -> Option<@&B>\n    Some(r)\n",
                           "    var a = A { x: 1 }\n    var b = B { x: 1, y: 2, z: 7 }\n"
                           "    var t: i32 = 0\n    match f(@&a)\n        Some(m) => t = m.x\n"
                           "        None => pass\n    match g(@&b)\n"
                           "        Some(m) => t = t + m.z as i32\n        None => pass\n    t\n", 8),
    "option_shared": ("fn f(r: @A) -> Option<@A>\n    Some(r)\n",
                      "    var a = A { x: 6 }\n    match f(@a)\n        Some(m) => m.x\n"
                      "        None => 0\n", 6),
    "result": ("fn f(r: @&A) -> Result<@&A, i32>\n    Ok(r)\n",
               "    var a = A { x: 4 }\n    match f(@&a)\n        Ok(m) => m.x\n        Err(e) => e\n", 4),
    # The referent is generic: its own argument follows the `refmut_` one.
    "generic_referent": ("struct W<T>\n    v: T\n\nfn f(r: @&W<i64>) -> Option<@&W<i64>>\n    Some(r)\n",
                         "    var w = W<i64> { v: 3 }\n    match f(@&w)\n        Some(m) => m.v as i32\n"
                         "        None => 0\n", 3),
    # A generic struct's field: monomorph substitutes T as `@&A`.
    "generic_struct": ("struct W<T>\n    v: T\n",
                       "    var a = A { x: 1 }\n    let w = W<@&A> { v: @&a }\n    w.v.x = 9\n    a.x\n", 9),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(RUNS))
def test_a_reference_type_argument_runs(tmp_path, compiler, site):
    fns, body, want = RUNS[site]
    assert _run(compiler, tmp_path, site, _main(TYPES + fns, body)) == want


@pytest.mark.parametrize("compiler", COMPILERS)
def test_each_reference_argument_is_its_own_pointer_sized_type(tmp_path, compiler):
    fns = ("fn f(r: @&A) -> Option<@&A>\n    Some(r)\n\nfn g(r: @&B) -> Option<@&B>\n    Some(r)\n\n"
           "fn h(r: @A) -> Option<@A>\n    Some(r)\n")
    comp, ll, _ = _compile(compiler, tmp_path, "layout", _main(TYPES + fns, "    0\n"))
    assert comp.returncode == 0, comp.stdout + comp.stderr
    ir = ll.read_text()
    for name in ("Option$refmut_A", "Option$refmut_B", "Option$ref_A"):
        found = re.search(r'%"?' + re.escape(name) + r'"? = type \{\s*i8, \[7 x i8\], \[8 x i8\]\s*\}', ir)
        assert found, f"{compiler}: no 8-byte-payload %{name}"
