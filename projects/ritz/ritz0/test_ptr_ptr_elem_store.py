"""AGAST #3186 / #3185: loads / stores through an element of a `**T` that isn't an array.

    struct P
        f: **i32
    ...
        h.f = @a[0]          # a: [2]*i32
        *h.f[1] = 7          # #3186: `store i64` through the i32 pointer

    var q: **i32 = @a[0]
    q[1] = @&n               # #3185: `inttoptr i64 %n` on a `ptr`; clang refused

#3186: ritz1 resolved the width of `*X[i]` for an `[N]*T` array but not for
an index of a `**T` (field or local), so `*X[i] = v` stored all 8 bytes of
the i64 RHS into the 4-byte (or 1-byte) `n`, overwriting what sat next to it,
and `*X[i]` loaded 8 bytes.  `let p: *i32 = h.f[1]; *p = 7` was right.

#3185: the pointer-local arm of the index store narrowed `@&n` (already a
`ptr`) with inttoptr, as #3036 / #3170 fixed for arrays and fields.

Load and store rows: base (`**T` field / `**T` local) x pointee (i32 / u8,
the widths an i64 access overruns).  `m` sits beside `n`, so an over-wide
store changes the exit code even when it doesn't crash.  All three compilers
run each row.
"""

import pytest
from test_ref_into_value import COMPILERS, _run

# AGAST #2806: each test's rows share one compile per compiler (batching.py).
pytestmark = [pytest.mark.integration, pytest.mark.batched]

# base -> (declarations, setup, the `**T` expression)
BASES = {
    "field": ("struct P\n    f: **{t}\n\n", "    var h: P\n    h.f = @a[0]\n", "h.f"),
    "local": ("", "    var q: **{t} = @a[0]\n", "q"),
}


def _locals(t: str, setup: str, fill: str = "") -> str:
    """`m`, `n`, the `[2]*T` array (`fill` stores into it first: `a` is
    borrowed once the `**T` points at it), then the base's setup."""
    return f"    var m: {t} = 3\n    var n: {t} = 1\n    var a: [2]*{t}\n" + fill + setup.format(t=t)


def _wrap(decls: str, body: str) -> str:
    return f"{decls}fn f() -> i32\n{body}    return 0\n\npub fn main() -> i32\n    f()\n"


def _base_program(base: str, t: str, body: str) -> str:
    """`body` runs with `X` (the base's `**T`) pointing at `a`, `a[1] == @&n`."""
    decls, setup, x = BASES[base]
    return _wrap(decls.format(t=t), _locals(t, setup, "    a[1] = @&n\n") + body.format(x=x))


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("t", ["i32", "u8"])
@pytest.mark.parametrize("base", sorted(BASES))
def test_a_deref_load_through_a_ptr_ptr_element(tmp_path, compiler, base, t):
    """#3186, read side: `*X[1]` loads a T.  It loaded an i64 (`n` and `m`)."""
    src = _base_program(base, t, "    if *{x}[1] != 1\n        return 1\n")
    assert _run(compiler, tmp_path, f"load_{base}_{t}", src) == 0


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("t", ["i32", "u8"])
@pytest.mark.parametrize("base", sorted(BASES))
def test_a_deref_store_through_a_ptr_ptr_element(tmp_path, compiler, base, t):
    """#3186: `*X[1] = 7` stores a T: `n` changes, its neighbour `m` doesn't."""
    body = "    *{x}[1] = 7\n    if n != 7\n        return 2\n    if m != 3\n        return 4\n"
    assert _run(compiler, tmp_path, f"store_{base}_{t}", _base_program(base, t, body)) == 0


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("addr", ["@&n", "@n"])
def test_an_address_stored_through_a_ptr_ptr_local(tmp_path, compiler, addr):
    """#3185: `q[1] = @&n` with `q: **i32` stores the `ptr`, not inttoptr of it.
    Read back through the array, so only the index store is under test."""
    body = f"    q[1] = {addr}\n    if *a[1] != 1\n        return 1\n"
    src = _wrap("", _locals("i32", BASES["local"][1]) + body)
    assert _run(compiler, tmp_path, f"addr_{'mut' if '&' in addr else 'shared'}", src) == 0
