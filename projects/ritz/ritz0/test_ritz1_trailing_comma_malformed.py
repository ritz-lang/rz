"""AGAST #1452 — ritz1 accepts ONE trailing comma in fn params and call args,
and nothing looser.

The accepting side lives in the regression matrix
(ritz0/test/test_issue_trailing_comma_{params,args}.ritz). This file pins the
rejecting side. The first version of the fix let `args` itself end in a comma,
which `LBRACKET args COMMA RBRACKET` (the #1507 array alternative) then
extended to `[1, 2,,]`. test_ritz1_array_trailing_comma caught that, so the
trailing comma now lives in `call_args`, used only at call sites, and `args`
is unchanged. The forms below are the call and param versions of the same
mistake, and ritz0 (the oracle) rejects each of them as well.
"""

import pytest

from test_ritz1_array_trailing_comma import _compile, ritz1_bin  # noqa: F401

MALFORMED_FORMS = {
    "call_double_trailing_comma": """\
fn add(a: i32, b: i32) -> i32
    return a + b

pub fn main() -> i32
    return add(1, 2,,)
""",
    "call_double_comma": """\
fn add(a: i32, b: i32) -> i32
    return a + b

pub fn main() -> i32
    return add(1,,2)
""",
    "call_comma_only": """\
fn zero() -> i32
    return 0

pub fn main() -> i32
    return zero(,)
""",
    "params_double_trailing_comma": """\
fn add(a: i32, b: i32,,) -> i32
    return a + b

pub fn main() -> i32
    return add(1, 2)
""",
    "params_comma_only": """\
fn zero(,) -> i32
    return 0

pub fn main() -> i32
    return zero()
""",
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED_FORMS))
def test_ritz0_rejects_malformed_commas(tmp_path, name):
    """The oracle agrees each form is malformed."""
    comp, _ = _compile("ritz0", tmp_path, name, MALFORMED_FORMS[name])
    assert comp.returncode != 0, f"ritz0 accepted malformed {name!r}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(MALFORMED_FORMS))
def test_ritz1_rejects_malformed_commas(ritz1_bin, tmp_path, name):
    """Only one trailing comma after at least one param/arg is legal."""
    comp, ll = _compile("ritz1", tmp_path, name, MALFORMED_FORMS[name])
    assert comp.returncode != 0, (
        f"ritz1 accepted malformed {name!r}:\n{comp.stdout[-1000:]}"
    )
    assert not ll.exists(), f"ritz1 wrote an artifact for malformed {name!r}"
