#!/usr/bin/env python3
"""A `:& T` param at T = `@&U` borrows the `@&U` place (AGAST #2354).

`fn w<T>(r:& T, v: T)` called as `w<@&C>(p, @&c3)` with `var p: @&C` points
`p` at `c3`: ritz0 gives 3.  ritz1 refused it ("this place doesn't hold what the
`:&` parameter borrows"): an `@&U` local was no place of a `:& *U`, generic or
written, though a `*U` one was.  And T substituted as `*C`, so `v: T` took a
shared `@c3`, which the #2339 ruling refuses into an `@&T` slot.

Neither `*C` nor `@&C` is the other's misfit at a `:&` slot: ritz0 takes both
ways round (`pointer_type_arg`, `pointer_place`).  An `@C` place stays refused
(`shared_place`).  Each row runs on ritz0, ritz1 and ritz1_selfhosted.
"""

import re

import pytest

from ref_rules import ADDR_INTO_MUT
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _ids, _located, _main, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

TYPES = """\
struct C
    x: i32
    y: i64

fn w<T>(r:& T, v: T)
    r = v

"""

C13 = "    var c1: C = C { x: 1, y: 0 }\n    var c3: C = C { x: 3, y: 0 }\n"

# Each is the extra fns, then `main`'s body; main must exit with the value given.
RUNS = {
    # The ticket's program.
    "ticket": ("", C13 + "    var p: @&C = @&c1\n    w<@&C>(p, @&c3)\n    p.x\n", 3),
    # The place is an `@&C`, T the pointer: one borrow, as on ritz0.
    "pointer_type_arg": ("", C13 + "    var p: @&C = @&c1\n    w<*C>(p, @c3)\n    p.x\n", 3),
    # And the other way round: a `*C` place, T the reference.
    "pointer_place": ("", C13 + "    var p: *C = @c1\n    w<@&C>(p, @&c3)\n    p.x\n", 3),
    # `v: T` is an `@&C`, so an `@&C` local goes in as one.
    "reference_value": ("", C13 + "    var p: @&C = @&c1\n    var q: @&C = @&c3\n    w<@&C>(p, q)\n    p.x\n", 3),
    "scalar_referent": ("", "    var a: i32 = 1\n    var b: i32 = 3\n    var p: @&i32 = @&a\n"
                            "    w<@&i32>(p, @&b)\n    *p\n", 3),
    # Read and written through the borrow: it's `p`, not a copy of it.
    "read_through": ("fn g<T>(r:& T) -> T\n    r\n",
                     "    var c1: C = C { x: 7, y: 0 }\n    var p: @&C = @&c1\n    let q = g<@&C>(p)\n    q.x\n", 7),
    "write_through": ("fn g<T>(r:& T)\n    r.x = 9\n",
                      "    var c1: C = C { x: 7, y: 0 }\n    var p: @&C = @&c1\n    g<@&C>(p)\n    c1.x\n", 9),
    # The same borrow, written out: no generics at all.
    "written_reference": ("fn wr(r:& @&C, v: @&C)\n    r = v\n",
                          C13 + "    var p: @&C = @&c1\n    wr(p, @&c3)\n    p.x\n", 3),
    "written_pointer": ("fn wp(r:& *C, v: *C)\n    r = v\n",
                        C13 + "    var p: @&C = @&c1\n    wp(p, @c3)\n    p.x\n", 3),
    # A by-value `v: T` at T = `@&C` writes through: it's the `@&C` it says.
    "by_value_write": ("fn set<T>(v: T)\n    v.x = 4\n",
                       "    var c1: C = C { x: 5, y: 0 }\n    set<@&C>(@&c1)\n    c1.x\n", 4),
    # At T = `@&*C` it stays as it was: monomorph has no `@&*C` param to make
    # of it, and an `@&C` one refused `@&p` ("a reference to one pointer type").
    "reference_to_pointer": ("fn setp<T>(v: T, q: *C)\n    *v = q\n",
                             C13 + "    var p: *C = @c1\n    setp<@&*C>(@&p, @c3)\n    p.x\n", 3),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(RUNS))
def test_a_reference_type_argument_borrows(tmp_path, compiler, site):
    fns, body, want = RUNS[site]
    assert _run(compiler, tmp_path, site, _main(TYPES + fns, body)) == want


# `^` marks where the error lands.
REFUSED = {
    # #2339: `@x` is shared, and `v: T` at T = `@&C` is an `@&T` slot.
    "shared_into_value": (C13 + "    var p: @&C = @&c1\n    w<@&C>(p, ^@c3)\n    p.x\n", ADDR_INTO_MUT),
    "shared_into_scalar": ("    var a: i32 = 1\n    var b: i32 = 3\n    var p: @&i32 = @&a\n"
                           "    w<@&i32>(p, ^@b)\n    *p\n", ADDR_INTO_MUT),
    # An `@C` place can't be borrowed as mutable, at T = `@C` (the ticket's
    # `w<@C>`) or at T = `@&C`.
    "shared_place": (C13 + "    var p: @C = @c1\n    w<@C>(^p, @c3)\n    p.x\n",
                     "argument 1 of `w` has the wrong type: a `:&` parameter can't borrow through an `@T`, which is read-only"),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("site", _ids(REFUSED))
def test_a_reference_type_argument_refuses(tmp_path, compiler, site):
    body, message = REFUSED[site]
    _assert_refused(compiler, tmp_path, site, _main(TYPES, body), message)


# An `@&C` param is no place to borrow: ritz0 gives it no storage, and says so
# in LLVM's words, so only the prefix is shared.  test_bare_place_borrow.py's
# `reference_for_pointer` is the same without generics.
REFERENCE_PARAM = TYPES + "fn go(r: @&C, v: @&C) -> i32\n    w<@&C>(^r, v)\n    r.x\n\n"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_reference_param_is_no_place(tmp_path, compiler):
    src, where = _located(_main(REFERENCE_PARAM, C13 + "    go(@&c1, @&c3)\n"))
    comp, ll, _ = _compile(compiler, tmp_path, "reference_param", src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0 and not ll.exists(), f"{compiler} accepted it"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert any(at == where and msg.startswith("argument 1 of `w` has the wrong type") for at, msg in found), out
