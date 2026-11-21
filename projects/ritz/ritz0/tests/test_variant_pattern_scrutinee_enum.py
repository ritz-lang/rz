"""An unqualified variant pattern is the scrutinee's enum's (AGAST #3556).

nexus declares `enum SlugVerdict` with a unit variant `Ok`.  Beside it, the
typing pass read every `Ok(v)` pattern, over a `Result` too, as
`SlugVerdict.Ok`: the last enum registered with a variant of that name.  That
variant has no payload, so `v` was never bound and each use was "undefined
variable: v", in nexus's own matches and in ritzlib/result.ritz's instances
alike.  The emitter takes the variant from the scrutinee's type, and so does
the typing pass now: the scrutinee's own enum, then a built-in Option /
Result, and only then whichever enum declares the name.
"""

import pytest
from parser import parse
from type_checker import TypeChecker

pytestmark = pytest.mark.unit

# Registered after the payload enums, so the bare name `Ok` maps to it.
VERDICT = """
enum Verdict
    Ok
    Bad

"""


def types(source: str) -> list:
    return [str(e) for e in TypeChecker().check(parse(source))]


def test_a_declared_enum_s_variant_binds_its_payload():
    src = "enum Res\n    Ok(i32)\n    Err(i32)\n\n" + VERDICT + (
        "fn f(r: Res) -> i32\n"
        "    match r\n"
        "        Ok(v) => v\n"
        "        Err(e) => e\n")
    assert types(src) == []


def test_a_builtin_result_s_variant_binds_its_payload():
    src = VERDICT + (
        "fn f(r: Result<i32, i64>) -> i32\n"
        "    match r\n"
        "        Ok(v) => v\n"
        "        Err(_) => 0\n")
    assert types(src) == []


def test_the_payload_is_the_scrutinee_s_type():
    # Bound, and at the Result's T: an i64 is no StrView.
    src = VERDICT + (
        "fn f(r: Result<i64, i32>) -> i32\n"
        "    match r\n"
        "        Ok(v) =>\n"
        "            let s: StrView = v\n"
        "            0\n"
        "        Err(_) => 0\n")
    errors = types(src)
    assert len(errors) == 1 and "StrView" in errors[0] and "i64" in errors[0], errors


def test_the_unit_variant_still_matches_its_own_enum():
    src = VERDICT + (
        "fn f(v: Verdict) -> i32\n"
        "    match v\n"
        "        Ok => 1\n"
        "        Bad => 0\n")
    assert types(src) == []
