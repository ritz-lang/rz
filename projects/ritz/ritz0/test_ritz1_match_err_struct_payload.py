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

from test_ritz1_builtin_struct_shadow import _run, _run_pkg, ritz1_bin  # noqa: F401

# Err carries a struct; the binding is passed by value to a fn and every
# field must survive the copy (a truncated i64-sized copy loses `b`/`c`).
ERR_STRUCT_TO_FN = """\
import ritzlib.result

struct Oops
    a: i64
    b: i64
    c: i64

fn fail(e: Oops) -> i64
    return e.a + e.b * 10 + e.c * 100

fn mk(bad: i64) -> Result<i64, Oops>
    if bad != 0
        let e = Oops { a: 1, b: 2, c: 3 }
        return Err(e)
    return Ok(7)

pub fn main() -> i32
    let r1: i64 = match mk(1)
        Ok(n) => n
        Err(e) => fail(e)
    let r2: i64 = match mk(0)
        Ok(n) => n
        Err(e) => fail(e)
    if r1 != 321
        return 1
    if r2 != 7
        return 2
    return 42
"""

# Field access straight off the Err binding.
ERR_STRUCT_MEMBER = """\
import ritzlib.result

struct Oops
    code: i64
    extra: i64

fn mk() -> Result<i32, Oops>
    let e = Oops { code: 40, extra: 2 }
    return Err(e)

pub fn main() -> i32
    let x: i64 = match mk()
        Ok(v) => v as i64
        Err(e) => e.code + e.extra
    return x as i32
"""

# Both sides carry (different) structs; exercise both arms.
BOTH_STRUCT = """\
import ritzlib.result

struct Point
    x: i64
    y: i64

struct Oops
    a: i64
    b: i64
    c: i64

fn ok_val(p: Point) -> i64
    return p.x + p.y * 10

fn err_val(e: Oops) -> i64
    return e.a + e.b * 10 + e.c * 100

fn mk(bad: i64) -> Result<Point, Oops>
    if bad != 0
        let e = Oops { a: 5, b: 6, c: 7 }
        return Err(e)
    let p = Point { x: 3, y: 4 }
    return Ok(p)

fn pick(bad: i64) -> i64
    match mk(bad)
        Ok(p) => ok_val(p)
        Err(e) => err_val(e)

pub fn main() -> i32
    if pick(0) != 43
        return 1
    if pick(1) != 765
        return 2
    return 42
"""

# Ok carries a struct, Err a scalar: the Err side stays i64 (no regression).
OK_STRUCT = """\
import ritzlib.result

struct Point
    x: i64
    y: i64

fn ok_val(p: Point) -> i64
    return p.x + p.y * 10

fn mk(bad: i64) -> Result<Point, i64>
    if bad != 0
        return Err(9)
    let p = Point { x: 3, y: 4 }
    return Ok(p)

fn pick(bad: i64) -> i64
    match mk(bad)
        Ok(p) => ok_val(p)
        Err(e) => e

pub fn main() -> i32
    if pick(0) != 43
        return 1
    if pick(1) != 9
        return 2
    return 42
"""

# E is itself a generic instance: `Result<i32, Box<i64>>` mangles as
# `Result$i32$Box$i64`, so E is the two-component suffix `Box$i64`.
ERR_NESTED_GENERIC = """\
import ritzlib.result

struct Box<T>
    v: T

fn mk(x: i64) -> Result<i32, Box<i64>>
    var b: Box<i64>
    b.v = x
    return Err(b)

pub fn main() -> i32
    match mk(40)
        Ok(v) => v
        Err(b) => (b.v + 2) as i32
"""

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

# The match itself yields Result values (`Some(n) => Ok(n)` / `None =>
# Err(..)`), as argspec's `arg_parse_i64` does: the merge phi must be typed
# `%Result$i64$Oops`, not i64 (clang: "'%.N' defined with type
# '%"Result$i64$ArgError"' but expected 'i64'").
CTOR_ARMS = """\
import ritzlib.option
import ritzlib.result

struct Oops
    a: i64
    b: i64

fn oops(a: i64) -> Oops
    return Oops { a: a, b: 2 }

fn opt(x: i64) -> Option<i64>
    if x > 0
        return Some(x)
    return None

fn conv(x: i64) -> Result<i64, Oops>
    match opt(x)
        Some(n) => Ok(n)
        None => Err(oops(30))

fn get(x: i64) -> i64
    match conv(x)
        Ok(n) => n
        Err(e) => e.a + e.b

pub fn main() -> i32
    if get(7) != 7
        return 1
    if get(0) != 32
        return 2
    return 42
"""

PKG_CASES = {
    "ctor_arms": (CTOR_ARMS, 42),
    "err_struct_to_fn": (ERR_STRUCT_TO_FN, 42),
    "err_struct_member": (ERR_STRUCT_MEMBER, 42),
    "both_struct": (BOTH_STRUCT, 42),
    "ok_struct": (OK_STRUCT, 42),
    "err_nested_generic": (ERR_NESTED_GENERIC, 42),
    "argspec_err": (ARGSPEC_ERR, 42),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz0_oracle_pkg(tmp_path, name):
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz0", tmp_path, name, program) == want


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PKG_CASES))
def test_ritz1_match_err_struct_payload(ritz1_bin, tmp_path, name):  # noqa: F811
    program, want = PKG_CASES[name]
    assert _run_pkg("ritz1", tmp_path, name, program) == want
