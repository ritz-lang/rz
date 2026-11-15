"""AGAST #2230: a typed closure parameter's type stops at the closing `|`.

`|x: i32| x + 1` is valid per the `Closure` docstring in ritz_ast.py, but
the param's type was parsed with the full `parse_type`, whose union rule
(`A | B`) read the closing `|` as a union operator: `i32 | x` became a
`UnionType` and the parse then failed with "Expected PIPE, got PLUS".

A closure param's type is now parsed without the union operator, at the top
level and in a `fn(...) -> T` return type (the only undelimited place a
type nests).  Rows are parser-only and in-process, one per code path.
Past the parser the annotation is still ignored (AGAST #3301).
"""

import pytest
import ritz_ast as rast
from parser import parse


def _closure(expr_src: str) -> rast.Closure:
    """Parse `let g = <expr_src>` inside a fn and return the closure."""
    module = parse(f"fn main() -> i32\n    let g = {expr_src}\n    0\n")
    value = module.items[0].body.stmts[0].value
    assert isinstance(value, rast.Closure)
    return value


@pytest.mark.parametrize("src, param_types, body_op", [
    # The ticket's repro: a named type, then a binary body.
    ("|x: i32| x + 1", [rast.NamedType], "+"),
    # The second param's type also stops at the closing `|`.
    ("|a: i32, b: i32| a + b", [rast.NamedType, rast.NamedType], "+"),
    # Prefix types reach the same primary: pointer and array.
    ("|p: *i32| p + 1", [rast.PtrType], "+"),
    ("|a: [4]i32| a[0] + 1", [rast.ArrayType], "+"),
    # A fn type's return type is undelimited, so it must not take the `|`.
    ("|f: fn(i32) -> i32| f(1) + 1", [rast.FnType], "+"),
    # ...and so must one under a prefix, which threads the rule through.
    ("|fs: [2]fn(i32) -> i32| fs[0](1) + 1", [rast.ArrayType], "+"),
])
def test_typed_closure_param_stops_at_pipe(src, param_types, body_op):
    closure = _closure(src)
    assert [type(p.type) for p in closure.params] == param_types
    assert isinstance(closure.body, rast.BinOp) and closure.body.op == body_op


def test_fn_typed_param_return_type_is_not_a_union():
    (param,) = _closure("|f: fn(i32) -> i32| f(1) + 1").params
    assert isinstance(param.type.ret, rast.NamedType)


def test_untyped_closure_body_keeps_bitwise_or():
    closure = _closure("|x| x | 1")
    assert closure.params[0].type is None
    assert isinstance(closure.body, rast.BinOp) and closure.body.op == "|"


def test_union_type_alias_still_parses():
    (alias,) = parse("type X = i64 | bool\n").items
    assert isinstance(alias.target, rast.UnionType)
    assert [v.name for v in alias.target.variants] == ["i64", "bool"]
