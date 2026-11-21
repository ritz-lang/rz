"""Regression tests for AGAST #2100: binding a user-enum payload out of
Option / Result in ritz1.

`Some(x)` over `Option<Opt>` and `Err(e)` over `Result<T, ArgError>` (Opt /
ArgError user enums) bound the payload as an i64: `val(x)` passed an i64
where `%Opt` was expected (clang rejects the IR), and `match e` read the
wrong tag.  Construction was already right (#1466); the bind side must load
the payload as the enum aggregate, just as it does for a struct payload
(#1515, #1667).

Every program exits 42 under ritz0 (the oracle) and must under ritz1.
"""

import pytest

from test_ritz1_qualified_variant_ctor import _run

EXPECTED = 42

OPT = """\
import ritzlib.option

enum Opt
    Vacant
    Holds(i32)

fn val(o: Opt) -> i32
    match o
        Holds(v) => v
        Vacant => 100
"""

ARGERROR = """\
import ritzlib.result

enum ArgError
    Missing(i64)
    Bad
"""

PROGRAMS = {
    # The ticket's first repro, verbatim.
    "some_opt_call": OPT
    + """
fn unwrap(o: Option<Opt>) -> i32
    match o
        Some(x) => val(x)
        None => 0

pub fn main() -> i32
    let o: Option<Opt> = Some(Holds(42))
    return unwrap(o)
""",
    # The bound payload matched in place, and a unit variant inside Some.
    "some_opt_nested_match": OPT
    + """
fn inner(o: Option<Opt>) -> i32
    match o
        Some(x) => match x
            Holds(v) => v
            Vacant => 2
        None => 0

pub fn main() -> i32
    let a: Option<Opt> = Some(Opt.Holds(40))
    let b: Option<Opt> = Some(Opt.Vacant)
    let c: Option<Opt> = None
    return inner(a) + inner(b) + inner(c)
""",
    # The ticket's Result repro: `Err(e) => match e`.
    "err_nested_match": ARGERROR
    + """
fn f() -> Result<i64, ArgError>
    return Err(Missing(42))

pub fn main() -> i32
    match f()
        Ok(n) => return 1
        Err(e) => match e
            Missing(n) => return n as i32
            Bad => return 2
""",
    # `Err(e) => code(e)`: the payload passed by value.
    "err_call": ARGERROR
    + """
fn code(e: ArgError) -> i32
    match e
        Missing(n) => n as i32
        Bad => 2

fn f(x: i64) -> Result<i64, ArgError>
    if x == 0
        return Err(ArgError.Missing(40))
    if x < 0
        return Err(ArgError.Bad)
    return Ok(x)

fn get(r: Result<i64, ArgError>) -> i32
    match r
        Ok(n) => n as i32
        Err(e) => code(e)

pub fn main() -> i32
    return get(f(0)) + get(f(0 - 1)) + (get(f(7)) - 7)
""",
    # A user enum on the Ok side, an i64 on the Err side.
    "ok_opt": OPT
    + """
import ritzlib.result

fn mk(x: i64) -> Result<Opt, i64>
    if x < 0
        return Err(x)
    return Ok(Opt.Holds(x as i32))

fn get(r: Result<Opt, i64>) -> i32
    match r
        Ok(o) => val(o)
        Err(n) => (0 - n) as i32

pub fn main() -> i32
    return get(mk(40)) + get(mk(0 - 2))
""",
    # User enums on both sides of a Result.
    "ok_and_err_enums": OPT
    + ARGERROR.replace("import ritzlib.result\n", "")
    + """
import ritzlib.result

fn code(e: ArgError) -> i32
    match e
        Missing(n) => n as i32
        Bad => 2

fn mk(x: i32) -> Result<Opt, ArgError>
    if x < 0
        return Err(ArgError.Missing(2))
    return Ok(Opt.Holds(x))

fn get(r: Result<Opt, ArgError>) -> i32
    match r
        Ok(o) => val(o)
        Err(e) => code(e)

pub fn main() -> i32
    return get(mk(40)) + get(mk(0 - 1))
""",
    # A struct on the Ok side, a user enum on the Err side (#1667's lookup
    # of E after a struct T).
    "struct_ok_enum_err": ARGERROR
    + """
struct Pt
    x: i64
    y: i64

fn code(e: ArgError) -> i64
    match e
        Missing(n) => n
        Bad => 2

fn mk(x: i64) -> Result<Pt, ArgError>
    if x == 0
        return Err(Missing(30))
    return Ok(Pt { x: x, y: 2 })

fn get(r: Result<Pt, ArgError>) -> i64
    match r
        Ok(p) => p.x + p.y
        Err(e) => code(e)

pub fn main() -> i32
    return (get(mk(10)) + get(mk(0))) as i32
""",
    # The binding is an `Opt` local: it initialises a typed `var`.
    "bound_local_copied": OPT
    + """
fn copy(o: Option<Opt>) -> i32
    var r: i32 = 0
    match o
        Some(x) =>
            var y: Opt = x
            r = val(y)
        None => r = 1
    return r

pub fn main() -> i32
    return copy(Some(Opt.Holds(40))) + 2
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_binds_enum_payload(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
