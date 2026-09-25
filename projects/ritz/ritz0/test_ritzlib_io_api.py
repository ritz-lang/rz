#!/usr/bin/env python3
"""Pin the public API shape of ritzlib/io.ritz (AGAST #1469).

io is the bottom rung of the idiomatic-ritzlib ladder (io -> str/strview/string
-> fs/buf/env/process -> json -> net; #1472 and #1474 build on it).  The rule
it establishes, following ritzlib/argspec.ritz (#1448):

* a String is taken as `@String` (a borrow), never as a raw `*String` --
  matching every other String API (string_len(s: @String), ...);
* the only raw pointers in io's public surface are the four `*_cstr`
  functions, which exist for C-string interop and say so in their doc
  comment, pointing callers at prints/println(StrView) instead.

Neither ritz0 nor ritz1 distinguishes `@String` from `*String` at a call site
(both lower to the same pointer and both accept `@s` for either), so a
compile-and-run test cannot tell the two signatures apart.  The contract is
the declared signature itself, so that is what this test reads -- through
ritz0's own parser, not a regex.
"""

from pathlib import Path

import pytest

import ritz_ast as rast
from lexer import tokenize
from parser import Parser

RITZ_ROOT = Path(__file__).resolve().parent.parent
IO_RITZ = RITZ_ROOT / "ritzlib" / "io.ritz"

STRING_PRINTERS = ("print_string", "eprint_string", "println_string", "eprintln_string")
# Each _cstr fn -> the StrView function its doc comment must point callers at.
CSTR_INTEROP = {
    "prints_cstr": "prints",
    "eprints_cstr": "eprints",
    "println_cstr": "println",
    "eprintln_cstr": "eprintln",
}


def _pub_fns():
    """Parse io.ritz and return {name: FnDef} for every `pub fn`."""
    module = Parser(tokenize(IO_RITZ.read_text())).parse_module()
    return {
        item.name: item
        for item in module.items
        if isinstance(item, rast.FnDef) and item.is_pub
    }


def _mentions_raw_pointer(ty) -> bool:
    """True if `ty` is, or contains, a raw `*T` pointer."""
    if isinstance(ty, rast.PtrType):
        return True
    if isinstance(ty, rast.RefType):
        return _mentions_raw_pointer(ty.inner)
    if isinstance(ty, rast.NamedType):
        return any(_mentions_raw_pointer(a) for a in ty.args)
    return False


def _doc_comment(fn_name: str) -> str:
    """The contiguous `#` comment block directly above `pub fn <fn_name>(`."""
    lines = IO_RITZ.read_text().splitlines()
    idx = next(i for i, l in enumerate(lines) if l.startswith(f"pub fn {fn_name}("))
    block = []
    i = idx - 1
    while i >= 0 and lines[i].startswith("#"):
        block.append(lines[i])
        i -= 1
    return "\n".join(reversed(block))


@pytest.mark.unit
@pytest.mark.parametrize("name", STRING_PRINTERS)
def test_string_printers_take_a_string_borrow(name):
    fns = _pub_fns()
    assert name in fns, f"{name} missing from ritzlib/io.ritz"
    params = fns[name].params
    assert len(params) == 1
    ty = params[0].type
    assert isinstance(ty, rast.RefType) and not ty.mutable, (
        f"{name} must take `s: @String`, got {ty!r}"
    )
    assert isinstance(ty.inner, rast.NamedType) and ty.inner.name == "String"


@pytest.mark.unit
def test_only_cstr_interop_fns_take_raw_pointers():
    offenders = sorted(
        name
        for name, fn in _pub_fns().items()
        if name not in CSTR_INTEROP
        and any(_mentions_raw_pointer(p.type) for p in fn.params)
    )
    assert offenders == [], f"raw-pointer params outside the _cstr interop fns: {offenders}"


@pytest.mark.unit
@pytest.mark.parametrize("name", CSTR_INTEROP)
def test_cstr_fns_are_kept_and_documented_as_c_interop(name):
    fns = _pub_fns()
    assert name in fns, f"{name} must stay (deletion is out of scope for #1469)"
    doc = _doc_comment(name)
    assert "C interop" in doc, f"{name} doc comment must mark it as C interop:\n{doc}"
    target = CSTR_INTEROP[name]
    assert target in fns, f"{target} (the StrView alternative) missing from io.ritz"
    preferred = f"{target}(StrView)"
    assert f"prefer {preferred}" in doc, f"{name} doc comment must say 'prefer {preferred}':\n{doc}"
