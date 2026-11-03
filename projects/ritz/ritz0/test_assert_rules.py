"""AGAST #1869: where `assert` may appear (LANGUAGE_SPEC §17.1, §19.2).

`assert` is legal in a `[[test]]` fn and in a `[[test_helper]]` fn, and
nowhere else. Both compilers enforce it with the same located diagnostic:

    t.ritz:<line>:<col>: assert is only allowed in [[test]] and
    [[test_helper]] functions, not in '<fn>'

Before #1869 ritz0 raised a bare ValueError (a Python traceback naming the
removed `@test` syntax) and ritz1 accepted the assert in any fn.

What a failing assert *prints* is runtime behaviour and is checked on all
three compilers by the matrix: ritz0/test/test_assert_operands.ritz.
"""

import pytest

from test_attr_validation import COMPILERS, _assert_located_error, _ir, _need

pytestmark = pytest.mark.integration

PLAIN_FN = """\
fn main() -> i32
    assert 1 == 1
    return 0
"""

HELPER_IN_PLAIN_CALLER = """\
fn check(x: i64) -> i64
    let y: i64 = x + 1
    assert y > x
    y

[[test]]
fn test_it() -> i32
    check(1)
    0

fn main() -> i32
    0
"""

HELPER_OK = """\
[[test_helper]]
fn expect_pos(x: i64)
    assert x > 0, "positive"

[[test_helper]]
fn expect_pair(a: i64, b: i64)
    expect_pos(a)
    assert a == b

[[test]]
fn test_it() -> i32
    expect_pair(1, 1)
    assert 1 + 1 == 2
    0

fn main() -> i32
    0
"""

RULE = "assert is only allowed in [[test]] and [[test_helper]] functions"


@pytest.mark.parametrize("compiler", COMPILERS)
def test_assert_in_plain_fn_is_a_located_error(request, tmp_path, compiler):
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, PLAIN_FN, 2, 5, RULE, "not in 'main'")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_assert_in_unmarked_helper_names_the_helper(request, tmp_path, compiler):
    # Being called from a test is not enough: the helper must say so.
    _need(compiler, request)
    _assert_located_error(compiler, tmp_path, HELPER_IN_PLAIN_CALLER, 3, 5, RULE,
                          "not in 'check'")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_diagnostic_no_longer_names_removed_at_test(request, tmp_path, compiler):
    from test_attr_validation import _compile

    _need(compiler, request)
    proc, _ = _compile(compiler, tmp_path, PLAIN_FN)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "@test" not in out, out
    assert "Traceback" not in out, out


@pytest.mark.parametrize("compiler", COMPILERS)
def test_assert_in_test_helper_compiles(request, tmp_path, compiler):
    _need(compiler, request)
    ir_text = _ir(compiler, tmp_path, HELPER_OK)
    # Helpers read the call site the [[test]] fn records.
    assert "__ritz_assert_site_line" in ir_text
