"""Regression tests for AGAST #2105: `?` over a Result / Option whose Ok / Some
payload is a user enum, in ritz1.

`let o = mk()?` with `mk() -> Result<Opt, E>` (Opt a user enum) unwrapped the
payload as an i64: the try emission (emitter_expr.ritz) only recognised a
struct payload, and so did the untyped-let typing (emitter_stmt.ritz), so
`val(o)` passed an i64 where `%Opt` was expected and clang rejected the IR.
#2100 fixed the same gap on the match-bind side; the try path must load the
payload as the enum aggregate too.

Every program exits 42 under ritz0 (the oracle) and must under ritz1.
"""

import pytest

from test_ritz1_qualified_variant_ctor import _run

EXPECTED = 42

OPT = """\
enum Opt
    Vacant
    Holds(i32)

fn val(o: Opt) -> i32
    match o
        Holds(v) => v
        Vacant => 100
"""

RESULT_OPT = (
    "import ritzlib.result\n\n"
    + OPT
    + """
fn mk(n: i32) -> Result<Opt, i64>
    if n < 0
        return Err(7)
    return Ok(Holds(n))
"""
)

OPTION_OPT = (
    "import ritzlib.option\n\n"
    + OPT
    + """
fn mk(n: i32) -> Option<Opt>
    if n < 0
        return None
    return Some(Holds(n))
"""
)

PROGRAMS = {
    # The ticket's repro, verbatim.
    "result_untyped_let": "import ritzlib.result\n\n"
    + OPT
    + """
fn mk() -> Result<Opt, i64>
    return Ok(Holds(42))

fn g() -> Result<i32, i64>
    let o = mk()?
    return Ok(val(o))

pub fn main() -> i32
    match g()
        Ok(n) => n
        Err(e) => 1
""",
    # The ticket's `Option<Opt>?` variant, untyped let.
    "option_untyped_let": OPTION_OPT
    + """
fn g() -> Option<i32>
    let o = mk(42)?
    return Some(val(o))

pub fn main() -> i32
    match g()
        Some(n) => n
        None => 1
""",
    # Annotated let: the slot type is given, so only the try load is tested.
    "result_typed_let": RESULT_OPT
    + """
fn g() -> Result<i32, i64>
    let o: Opt = mk(40)?
    return Ok(val(o) + 2)

pub fn main() -> i32
    match g()
        Ok(n) => n
        Err(e) => 1
""",
    # `?` straight into a by-value enum argument: no let at all.
    "option_try_as_arg": OPTION_OPT
    + """
fn g() -> Option<i32>
    return Some(val(mk(42)?))

pub fn main() -> i32
    match g()
        Some(n) => n
        None => 1
""",
    # The unwrapped enum matched by value, a unit variant, and the Err /
    # None short-circuit still propagating.
    "result_match_and_propagate": "import ritzlib.result\n\n"
    + OPT
    + """
fn mk(k: i32) -> Result<Opt, i64>
    if k == 0
        # Qualified: a bare `Ok(Vacant)` is a separate ctor bug (#2144).
        return Ok(Opt.Vacant)
    if k == 1
        return Ok(Holds(30))
    return Err(10)

fn pick(o: Opt) -> i32
    match o
        Holds(v) => v
        Vacant => 2

fn g(k: i32) -> Result<i32, i64>
    let o = mk(k)?
    return Ok(pick(o))

pub fn main() -> i32
    var total: i32 = 0
    match g(0)
        Ok(n) => total = total + n
        Err(e) => total = total + 100
    match g(1)
        Ok(n) => total = total + n
        Err(e) => total = total + 100
    match g(2)
        Ok(n) => total = total + 100
        Err(e) => total = total + e as i32
    return total
""",
    "option_none_propagates": OPTION_OPT
    + """
fn g(n: i32) -> Option<i32>
    let o = mk(n)?
    return Some(val(o))

pub fn main() -> i32
    var total: i32 = 0
    match g(-1)
        Some(n) => total = total + 100
        None => total = total + 2
    match g(40)
        Some(n) => total = total + n
        None => total = total + 100
    return total
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_try_unwraps_enum_payload(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
