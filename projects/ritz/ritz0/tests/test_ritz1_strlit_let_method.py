"""AGAST #3267: a method on an untyped `let` of a string literal dispatches to
`StrView`'s method when the module has no `Span<u8>` one, as ritz0 does.

THE DEFECT

ritz0 binds `let h = "0123456789abcdef"` as a `StrView` and lowers
`h.get(i)` to `StrView_get`.  ritz1 lowers the literal to the layout-equal
`%Span$u8`, so the method looked for a Span helper.  With only
`ritzlib.strview` imported (cryptosec test_tls13_kdf.ritz:89-95 and
test_tls13_record.ritz) there is none, and the call fell through to the bare
`Type_method` mangling: `call i64 @Span$u8_get(...)`, declared, never
defined, and every test in both files failed at link.

THE FIX

`ufcs_fn_def` falls back to the `strview_*` helper for a `Span$u8` receiver
with no Span method of its own, and passes it by value as it does a
`StrView` receiver.  A module that imports `ritzlib.span` still gets
`span_get$u8` (the `span_imported` row).

ritz0 is the oracle: it is one of the compilers each row runs under.
"""

import pytest

from test_ritz1_move_param import _run

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# name -> (program, expected exit status)
FORMS = {
    # The ticket's shape: strview only, `hex_chars.get(i)`.  'a' + 'f' - 140.
    "get": ("""\
import ritzlib.strview

fn main() -> i32
    let hex_chars = "0123456789abcdef"
    let b: u8 = 0xaf
    let hi: u8 = hex_chars.get((b >> 4) as i64)
    let lo: u8 = hex_chars.get((b & 0x0f) as i64)
    (hi as i32) + (lo as i32) - 140
""", 59),
    # A StrView-returning method chains: `slice` is StrView's, not the
    # Span `{ ptr + lo, hi - lo }` builtin, and its `.get` resolves too.
    "slice_get": ("""\
import ritzlib.strview

fn main() -> i32
    let h = "0123456789abcdef"
    h.slice(10, 16).get(2) as i32
""", 99),
    # Control: with ritzlib.span in scope the Span helper still wins.
    "span_imported": ("""\
import ritzlib.span
import ritzlib.strview

fn main() -> i32
    let h = "0123456789abcdef"
    h.get(11) as i32
""", 98),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(FORMS))
def test_strlit_let_method(request, tmp_path, compiler, name):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    program, expected = FORMS[name]
    rc = _run(compiler, tmp_path, program)
    assert rc == expected, f"{compiler} {name}: exit {rc}, expected {expected}"
