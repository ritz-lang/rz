"""LARB R52 / AGAST #3409 (#1622): `A | B` isn't a type, a type isn't a pattern.

LANGUAGE_SPEC §3.8: an alias names one type.  ritz0 used to accept
`type V = i64 | bool` and lower it to `{ i8 tag, [N x i8] }`, tagged by LLVM
type (so `u64 as (i64 | u64)` got the i64 tag) and read back with an unchecked
`v as T`.  Both the union type and the type-name match pattern (`i64 =>`)
that took it apart are now located parse errors.  For a value of several
kinds, write an enum with a payload per kind.

`|` always ends a type, so a typed closure param (`|x: i32| x + 1`, #2230)
needs no special rule.  Rows are parser-only and in-process.
"""

import pytest
import ritz_ast as rast
from parser import parse, ParseError

pytestmark = pytest.mark.unit

UNION_MSG = ("`A | B` isn't a type: declare an enum with a payload per kind "
             "(LANGUAGE_SPEC §3.8)")
PATTERN_MSG = "a type isn't a pattern"


def _refusal(src: str) -> ParseError:
    with pytest.raises(ParseError) as info:
        parse(src)
    return info.value


@pytest.mark.parametrize("src, line, column", [
    # test_level24.ritz's alias (the file went with #3409); error at the `|`.
    ("type X = i64 | bool\n", 1, 14),
    # Inline, in a parameter.
    ("fn f(x: i64 | bool) -> i64\n    0\n", 1, 13),
    # Under a fn type's undelimited return: still the alias's `|`.
    ("type F = fn() -> i64 | bool\n", 1, 22),
])
def test_union_type_refused_at_pipe(src, line, column):
    err = _refusal(src)
    assert err.message == UNION_MSG
    assert (err.span.line, err.span.column) == (line, column)


@pytest.mark.parametrize("pattern", ["i64", "bool", "*u8", "&i32"])
def test_type_pattern_refused_at_pattern(pattern):
    src = f"fn f(x: i64) -> i64\n    match x\n        {pattern} => 1\n        _ => 0\n"
    err = _refusal(src)
    assert err.message == PATTERN_MSG
    assert (err.span.line, err.span.column) == (3, 9)


def test_typed_closure_param_still_parses():
    module = parse("fn main() -> i32\n    let g = |x: i32| x + 1\n    0\n")
    closure = module.items[0].body.stmts[0].value
    assert isinstance(closure, rast.Closure)
    assert isinstance(closure.params[0].type, rast.NamedType)
    assert isinstance(closure.body, rast.BinOp) and closure.body.op == "+"


def test_cast_then_bitwise_or_is_an_expression():
    """`|` ends a cast's target type too: `x as u64 | 1` is a bitwise or."""
    module = parse("fn f(x: i64) -> u64\n    x as u64 | 1\n")
    expr = module.items[0].body.expr
    assert isinstance(expr, rast.BinOp) and expr.op == "|"
    assert isinstance(expr.left, rast.Cast)
