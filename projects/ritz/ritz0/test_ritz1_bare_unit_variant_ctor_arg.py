"""Regression tests for AGAST #2144: a tagged-enum constructor (`Ok` / `Some` /
`Err`) whose argument is a bare unit variant of a user enum, in ritz1.

`Ok(Vacant)` with `Vacant` a unit variant of `enum Opt` stored the payload as
an i64 (`store i64 %.3`) while the value was the `%Opt` aggregate, so clang
rejected the IR. The qualified `Ok(Opt.Vacant)` and the payload form
`Ok(Holds(1))` already took the aggregate-store path (#1466); the bare ident
did not.

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
        Vacant => 42
"""

PROGRAMS = {
    # The ticket's repro, verbatim.
    "result_ok_vacant": "import ritzlib.result\n\n"
    + OPT
    + """
fn mk() -> Result<Opt, i64>
    return Ok(Vacant)

pub fn main() -> i32
    match mk()
        Ok(o) => val(o)
        Err(e) => 1
""",
    # The ticket's Option<Opt> variant.
    "option_some_vacant": "import ritzlib.option\n\n"
    + OPT
    + """
fn mk() -> Option<Opt>
    return Some(Vacant)

pub fn main() -> i32
    match mk()
        Some(o) => val(o)
        None => 1
""",
    # A typed let initialised from the bare ctor (not a return).
    "option_let_some_vacant": "import ritzlib.option\n\n"
    + OPT
    + """
pub fn main() -> i32
    let o: Option<Opt> = Some(Vacant)
    match o
        Some(x) => val(x)
        None => 1
""",
    # Err payload of user-enum type.
    "result_err_vacant": "import ritzlib.result\n\n"
    + OPT
    + """
fn mk() -> Result<i64, Opt>
    return Err(Vacant)

pub fn main() -> i32
    match mk()
        Ok(n) => 1
        Err(e) => val(e)
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz0_is_the_oracle(tmp_path, name):
    assert _run("ritz0", tmp_path, name, PROGRAMS[name]) == EXPECTED


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_ritz1_bare_unit_variant_ctor_arg(ritz1_bin, tmp_path, name):
    assert _run("ritz1", tmp_path, name, PROGRAMS[name]) == EXPECTED
