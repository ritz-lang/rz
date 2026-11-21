#!/usr/bin/env python3
"""AGAST #4467: `?` on a `Result` needs the enclosing fn's `Result` to share `E`.

LANGUAGE_SPEC §14.2: "the enclosing function must return the same carrier: a
`Result` with the same `E` for a `Result` operand".  Until this ticket ritz0's
`_emit_try_op` only asked whether the enclosing fn returned *any* registered
enum (`fn_ret_type_name not in self.enum_types`), so:

  * `parse(x)?` in an `Option<i32>` fn compiled and emitted the `Err` as
    `None` — a silent conversion, the failure disappearing;
  * the same `?` in a `Shade` fn crashed with
    `InternalError: Enum Shade has no data buffer`;
  * a `Result<i32, u8>` operand in a `Result<i32, i32>` fn compiled and
    rebuilt the `Err` at the wrong width.

ritz1 (#4455) mirrored the weak rule: it accepted the Result operand in every
enum-returning fn.  Both now require a `Result` return whose `E` matches.

THE RULE (recorded on the ticket and in the commit)

"the same `E`" is canonical type-name equality after alias resolution: the two
error types must spell the same mangled name (`u8`, `CodeA`, `Option$i32`,
`Pair$u8_i32`), which is how the rest of the compiler already decides type
identity.  Type aliases resolve to their targets first, so `type Alias = u8`
in one signature matches `u8` in the other.  Layout equality is *not* the
rule: two distinct names with identical layout are different `E`s.

HOW THE ROWS ARE ORGANIZED

Each `REFUSED` row must exit non-zero, write no `.ll`, and print the pinned
message at the operand's `line:col` (`^`).  Each `MATCHES` row is a legitimate
`?` that must keep compiling and running (exit 3).  All three compilers are
checked, and they must agree on the message, so a message that embedded a
mangled type name would have to agree across ritz0's and ritz1's spelling;
the different-`E` message therefore names no type.
"""

import pytest

from test_ref_into_value import COMPILERS, _assert_refused, _run

pytestmark = [pytest.mark.integration, pytest.mark.batched]

PRELUDE = """\
import ritzlib.result
import ritzlib.option

struct CodeA
    n: i32

struct CodeB
    n: i32

type Alias = u8

fn parse(x: i32) -> Result<i32, i32>
    if x > 0
        return Ok(x)
    return Err(1)

fn parse_u8(x: i32) -> Result<i32, u8>
    if x > 0
        return Ok(x)
    return Err(1)

fn parse_alias(x: i32) -> Result<i32, Alias>
    if x > 0
        return Ok(x)
    return Err(1)

fn parse_a(x: i32) -> Result<i32, CodeA>
    if x > 0
        return Ok(x)
    return Err(CodeA { n: 1 })

"""

# ritz0's message for a Result operand whose enclosing fn returns something
# else; #4455 pinned it for a scalar return, these rows add an Option and a
# user enum (both of which used to get past the check).
NOT_RESULT = "Try operator used in function not returning Result type (got "
DIFFERENT_E = (
    "Try operator on a Result used in a function returning a Result with a"
    " different error type"
)

REFUSED = {
    # The silent Err -> None conversion: used to compile on both compilers.
    "result_in_option_fn": (
        "fn twice(x: i32) -> Option<i32>\n"
        "    let v = ^parse(x)?\n"
        "    Some(v + v)\n",
        NOT_RESULT + "Option$i32)",
    ),
    # Used to be ritz0's InternalError; must be a located refusal instead.
    "result_in_user_enum_fn": (
        "enum Shade\n"
        "    Dark\n"
        "    Light\n"
        "\n"
        "fn go(x: i32) -> Shade\n"
        "    let v = ^parse(x)?\n"
        "    Shade.Dark\n",
        NOT_RESULT + "Shade)",
    ),
    # Same carrier, different E spelling (both scalars).
    "different_e_scalar": (
        "fn go(x: i32) -> Result<i32, i32>\n"
        "    let v = ^parse_u8(x)?\n"
        "    Ok(v)\n",
        DIFFERENT_E,
    ),
    # Same carrier, same layout, different named E: name equality, not layout.
    "different_e_struct": (
        "fn go(x: i32) -> Result<i32, CodeB>\n"
        "    let v = ^parse_a(x)?\n"
        "    Ok(v)\n",
        DIFFERENT_E,
    ),
}

MATCHES = {
    # The baseline same-E `?`.
    "same_e": (
        "fn twice(x: i32) -> Result<i32, i32>\n"
        "    let v = parse(x)?\n"
        "    Ok(v + v)\n"
        "\n"
        "fn main() -> i32\n"
        "    match twice(3)\n"
        "        Ok(v) => v - 3\n"
        "        Err(e) => 2\n"
    ),
    # An alias on the operand's side resolves to the target: same E.
    "same_e_alias": (
        "fn twice(x: i32) -> Result<i32, u8>\n"
        "    let v = parse_alias(x)?\n"
        "    Ok((v + v) as u8)\n"
        "\n"
        "fn main() -> i32\n"
        "    match twice(3)\n"
        "        Ok(v) => (v as i32) - 3\n"
        "        Err(e) => 2\n"
    ),
    # Only `E` is constrained: the Ok payload may differ (i32 -> u8 here).
    "different_ok_same_e": (
        "fn twice(x: i32) -> Result<u8, u8>\n"
        "    let v = parse_u8(x)?\n"
        "    Ok((v + v) as u8)\n"
        "\n"
        "fn main() -> i32\n"
        "    match twice(3)\n"
        "        Ok(v) => (v as i32) - 3\n"
        "        Err(e) => 2\n"
    ),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(REFUSED))
def test_try_with_a_different_error_type_is_refused(tmp_path, compiler, row):
    body, message = REFUSED[row]
    _assert_refused(compiler, tmp_path, row, PRELUDE + body, message)


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("row", sorted(MATCHES))
def test_try_with_the_same_error_type_compiles_and_runs(tmp_path, compiler, row):
    assert _run(compiler, tmp_path, row, PRELUDE + MATCHES[row]) == 3
