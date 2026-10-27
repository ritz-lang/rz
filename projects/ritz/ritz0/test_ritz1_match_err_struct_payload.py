"""AGAST #1667 (dup #1670): ritz1 binds `Err(e)`'s struct payload at its real type.

THE DEFECT

#1515 taught emit_match_arm_body (ritz1/src/emitter_match.ritz) to bind a
carrier payload (`Ok(s)`, `Some(p)`) at its struct type, but the Err side of
`Result<T, E>` still fell back to `alloca i64` / TYPE_I64. With a struct `E`,
`Err(e) => fail(e)` handed an i64 to a fn taking `%E`, and clang rejected the
IR ("'%.N' defined with type 'i64' but expected '%ArgError'"); `e.code` failed
with "unhandled EXPR_MEMBER". This was the next blocker for
examples/tier2_stdlib/77_args (`sum_item`'s `match arg_parse_i64(item)`).

THE FIX

E is the trailing `$`-bounded component(s) of the mangled `Result$T$E` name:
the shortest `$`-suffix naming a concrete struct (`Result$i64$ArgError` ->
`ArgError`, `Result$i32$Box$i64` -> `Box$i64`). When it names one, `Err(e)`
binds a copy of the payload as an `alloca %E` struct local, as Ok does.

A second blocker on the same path: argspec's `arg_parse_i64` is a match
whose arms are bare ctors (`Some(n) => Ok(n)`, `None => Err(..)`), and its
merge phi was typed i64. emit_match_arm_body now types the phi with the
enum the ctor built (resolve_enum_ctx).

Oracle: ritz0 builds and runs every program with the same exit code.
"""

import pytest

from test_ritz1_builtin_struct_shadow import _run_pkg

# #1670 repro, the shape of 77_args `sum_item`: ritzlib.argspec's
# `arg_parse_i64` -> Result<i64, ArgError>, Err payload handed to a fn.
ARGSPEC_ERR = """\
import ritzlib.sys
import ritzlib.io
import ritzlib.option
import ritzlib.result
import ritzlib.strview
import ritzlib.span
import ritzlib.gvec
import ritzlib.argspec

fn fail(e: ArgError) -> i64
    return e.text.len + 100

fn parse(item: StrView) -> i64
    match arg_parse_i64(item)
        Ok(n) => n
        Err(e) => fail(e)

pub fn main() -> i32
    if parse("12") != 12
        return 1
    if parse("abcd") != 104
        return 2
    return 42
"""

# The other cases moved to ritz0/test/test_diff_match_err_struct_payload.ritz (AGAST #1805), where the
# regression matrix runs them under all three compilers.  This one stays:
# the matrix links ritzlib built by ritz0 into every cell, so its ritz1 cell
# would not be the all-ritz1 build this test checks.
PKG_CASES = {
    "argspec_err": (ARGSPEC_ERR, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz0_oracle_pkg(tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz1_match_err_struct_payload(ritz1_bin, tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want
