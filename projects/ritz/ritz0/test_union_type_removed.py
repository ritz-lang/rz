"""LARB R52 / AGAST #3409, #3411 (#1622): `A | B` isn't a type, a type isn't a pattern.

LANGUAGE_SPEC §3.8: an alias names one type.  ritz0 used to accept
`type V = i64 | bool` and lower it to `{ i8 tag, [N x i8] }`, tagged by LLVM
type (so `u64 as (i64 | u64)` got the i64 tag) and read back with an unchecked
`v as T`.  Both the union type and the type-name match pattern (`i64 =>`)
that took it apart are now located parse errors.  For a value of several
kinds, write an enum with a payload per kind.

`|` always ends a type.  ritz0's rows are parser-only and in-process.

ritz1 never had unions (#3411): its grammar already stopped at the same `|`
and pattern, as "unexpected '|'".  Its dropped-item report (ast_helpers.ritz,
union_type_at / type_pattern_at) now gives ritz0's words there, so each row
runs on ritz1 and ritz1_selfhosted too.  ritz1 lexes the primitive type names
as keywords, so `i64 =>` is told from a binding; a user type's name used as a
pattern (`Point =>`) is a binding on all three.  ritz1 has no closures, so
`|x: i32| x` stays "unexpected '|'" there.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
import ritz_ast as rast
from parser import parse, ParseError

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

UNION_MSG = ("`A | B` isn't a type: declare an enum with a payload per kind "
             "(LANGUAGE_SPEC §3.8)")
PATTERN_MSG = "a type isn't a pattern"

_ARM = "fn f(x: i64) -> i64\n    match x\n        {} => 1\n        _ => 0\n"

# name -> (source, line, column) of the `|`.
UNIONS = {
    # test_level24.ritz's alias (the file went with #3409).
    "alias": ("type X = i64 | bool\n", 1, 14),
    # Inline, in a parameter.
    "param": ("fn f(x: i64 | bool) -> i64\n    0\n", 1, 13),
    # Under a fn type's undelimited return: still the alias's `|`.
    "fn_type_return": ("type F = fn() -> i64 | bool\n", 1, 22),
    # The other type positions, each a different path in ritz1's grammar.
    "return_type": ("fn f() -> i64 | bool\n    0\n", 1, 15),
    "let_annotation": ("fn f() -> i64\n    let v: i64 | bool = 0\n    0\n", 2, 16),
    "struct_field": ("struct S\n    v: *u8 | i64\n", 2, 12),
    "generic_arg": ("struct B<T>\n    v: T\nfn f(b: B<i64 | bool>) -> i64\n    0\n", 3, 15),
    "user_types": ("struct P\n    v: i64\nstruct Q\n    v: i64\ntype X = P | Q\n", 5, 12),
}

# name -> (source, line, column) of the pattern.
TYPE_PATTERNS = {
    "i64": (_ARM.format("i64"), 3, 9),
    "bool": (_ARM.format("bool"), 3, 9),
    "ptr": (_ARM.format("*u8"), 3, 9),
    "amp": (_ARM.format("&i32"), 3, 9),
    # R52a: a type in a payload is a type, not a binding.
    "payload": ("enum E\n    A(i64)\n    B\nfn f(e: E) -> i64\n    match e\n"
                "        A(i64) => 1\n        _ => 0\n", 6, 11),
}

REFUSED = {**{k: (s, UNION_MSG, ln, col) for k, (s, ln, col) in UNIONS.items()},
           **{f"pattern_{k}": (s, PATTERN_MSG, ln, col)
              for k, (s, ln, col) in TYPE_PATTERNS.items()}}

# Not refused anywhere: `|` after a cast is a bitwise or (R52a, §7.5), and a
# bare IDENT pattern is a binding even when it names a type.
KEPT = {
    "cast_then_or": "fn f(x: i64) -> u64\n    x as u64 | 1\n",
    "or_of_casts": "fn f(x: i64) -> u64\n    let y: u64 = x as u64 | x as u64\n    y\n",
    "binding_named_like_a_type": ("struct Point\n    v: i64\nfn f(x: i64) -> i64\n"
                                  "    match x\n        Point => Point\n"),
}


# ---------------------------------------------------------------------------
# ritz0: in-process parser
# ---------------------------------------------------------------------------

def _refusal(src: str) -> ParseError:
    with pytest.raises(ParseError) as info:
        parse(src)
    return info.value


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz0_refuses_at_the_spot(name):
    src, message, line, column = REFUSED[name]
    err = _refusal(src)
    assert err.message == message
    assert (err.span.line, err.span.column) == (line, column)


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(KEPT))
def test_ritz0_keeps(name):
    parse(KEPT[name])


@pytest.mark.unit
def test_cast_then_bitwise_or_is_an_expression():
    """`|` ends a cast's target type too: `x as u64 | 1` is a bitwise or."""
    module = parse(KEPT["cast_then_or"])
    expr = module.items[0].body.expr
    assert isinstance(expr, rast.BinOp) and expr.op == "|"
    assert isinstance(expr.left, rast.Cast)


# ---------------------------------------------------------------------------
# ritz1 and ritz1_selfhosted (#3411): a compile that stops at the parse
# ---------------------------------------------------------------------------

def _ritz1(request, compiler, tmp_path, source):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    return proc.stdout + proc.stderr, ll


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz1_refuses_at_the_spot(request, tmp_path, compiler, name):
    source, message, line, col = REFUSED[name]
    out, ll = _ritz1(request, compiler, tmp_path, source)
    assert not ll.exists(), f"{compiler} wrote IR for {name}:\n{out[-800:]}"
    want = rf"^error: \S*/unit\.ritz:{line}:{col}: {re.escape(message)}$"
    assert len(re.findall(want, out, re.M)) == 1, f"{compiler}, {name}:\n{out[-800:]}"
    assert "unexpected" not in out, f"{compiler}, {name}:\n{out[-800:]}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(KEPT))
def test_ritz1_keeps(request, tmp_path, compiler, name):
    out, ll = _ritz1(request, compiler, tmp_path, KEPT[name])
    assert ll.exists() and "error" not in out, f"{compiler}, {name}:\n{out[-800:]}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_ritz1_closure_pipe_is_not_a_union(request, tmp_path, compiler):
    """ritz1 has no closures: `|x: i32|` is refused as one (#3471), not a union."""
    out, ll = _ritz1(request, compiler, tmp_path,
                     "fn main() -> i32\n    let g = |x: i32| x + 1\n    0\n")
    assert not ll.exists(), out[-800:]
    assert UNION_MSG not in out and "closures aren't supported" in out, f"{compiler}:\n{out[-800:]}"
