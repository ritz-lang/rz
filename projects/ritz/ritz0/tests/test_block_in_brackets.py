"""AGAST #3429 (LARB R46a, spec §2.2): no block can open inside ( [ {.

THE RULE

Inside `(`, `[` or `{` there is no layout, so no block can open there.  A
multi-line `if` (one whose body is an indented block) or any `match` inside
brackets is an error at the `if` / `match` keyword:

    a block can't open inside `(`: bind the `if`/`match` to a `let` first

naming the innermost open bracket.  One-line `if c then a else b` inside
brackets stays legal, and so does a block `if` / `match` outside brackets
(`let t = match n` ..., `x = 5 + if c` + block).

Before R46a, ritz0 parsed `take(match n` + arms + `)` and pinned it
(test_return_expected_enum.py `call_arg_arm`, LANGUAGE_SPEC's #1435 example).
Those now bind the value to a `let` first.

THE FIX

The parser maps each `if` / `match` token to the innermost bracket open
around it, once, from the token list (`_enclosing_brackets`).  Spans key the
map because the token list is rewritten while parsing (`>>` splits,
continuation relayouts), but those rewrites never touch a bracket or a
keyword.  `parse_if` checks it only for the block form, after the condition,
so `then` / `else` one-liners are unaffected; `parse_match` always checks.

THE TESTS

Parse-level (no compile): `if` and `match` in each bracket kind, with the
exact message and line:col; the innermost bracket is the one named.
Controls: one-liners in each bracket kind, block forms outside brackets
(including after a bracket that closed on the same line).  Two compiles go through
the CLI: the located error, and a one-line `if` inside parens that runs.
"""

import os
from pathlib import Path

import pytest

from parser import ParseError, parse
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]


def _msg(bracket):
    return f"a block can't open inside `{bracket}`: bind the `if`/`match` to a `let` first"


# name -> (source, bracket, line, column of the `if` / `match`)
REFUSED = {
    "if_in_paren": ("""\
fn id(v: i32) -> i32
    v

fn f(c: i32) -> i32
    id(if c == 1
        1
    else
        2
    )
""", "(", 5, 8),
    "if_in_bracket": ("""\
fn f(a: *i32, c: i32) -> i32
    a[if c == 1
        0
    else
        1
    ]
""", "[", 2, 7),
    "if_in_brace": ("""\
struct S
    v: i32

fn f(c: i32) -> i32
    let s = S { v: if c == 1
        1
    else
        2
    }
    s.v
""", "{", 5, 20),
    "match_in_paren": ("""\
fn id(v: i32) -> i32
    v

fn f(n: i32) -> i32
    id(match n
        1 => 10
        _ => 20
    )
""", "(", 5, 8),
    "match_in_bracket": ("""\
fn f(n: i32) -> i32
    let a: [2]i32 = [match n
        1 => 10
        _ => 20
    , 3]
    a[0]
""", "[", 2, 22),
    "match_in_brace": ("""\
struct S
    v: i32

fn f(n: i32) -> i32
    let s = S { v: match n
        1 => 10
        _ => 20
    }
    s.v
""", "{", 5, 20),
    # The innermost bracket is the one named: `[` inside `(`.
    "innermost_bracket_named": ("""\
fn id(v: i32) -> i32
    v

fn f(a: *i32, c: i32) -> i32
    id(a[if c == 1
        0
    else
        1
    ])
""", "[", 5, 10),
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_block_inside_brackets_is_refused_at_the_keyword(name):
    source, bracket, line, col = REFUSED[name]
    with pytest.raises(ParseError) as info:
        parse(source)
    err = info.value
    assert _msg(bracket) in str(err), str(err)
    assert (err.span.line, err.span.column) == (line, col), (
        f"{name}: located at {err.span.line}:{err.span.column}, want {line}:{col}"
    )


ACCEPTED = {
    "one_line_if_in_paren": """\
fn id(v: i32) -> i32
    v

fn f(c: i32) -> i32
    id(if c == 1 then 1 else 2)
""",
    "one_line_if_in_bracket": """\
fn f(a: *i32, c: i32) -> i32
    a[if c == 1 then 0 else 1]
""",
    "one_line_if_in_brace": """\
struct S
    v: i32

fn f(c: i32) -> i32
    let s = S { v: if c == 1 then 1 else 2 }
    s.v
""",
    # Outside brackets, after a bracket that closed on the same line.
    "block_if_after_closed_paren": """\
fn id(v: i32) -> i32
    v

fn f(c: i32) -> i32
    let x = id(1) + if c == 1
        1
    else
        2
    x
""",
    "let_match": """\
fn f(n: i32) -> i32
    let t = match n
        1 => 10
        _ => 20
    t
""",
    # Brackets inside the block are fine: the block isn't inside them.
    "brackets_inside_a_block": """\
fn id(v: i32) -> i32
    v

fn f(n: i32) -> i32
    let t = match n
        1 => id(if n == 1 then 10 else 11)
        _ => id(20)
    t
""",
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_one_liners_and_blocks_outside_brackets_still_parse(name):
    parse(ACCEPTED[name])


def _compile(tmp_path, source, *extra):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(tmp_path / "unit.ll"), *extra],
                     env=env, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr


@pytest.mark.integration
def test_the_cli_reports_the_error_located(tmp_path):
    rc, out = _compile(tmp_path, REFUSED["match_in_paren"][0], "--no-runtime")
    assert rc != 0
    assert "unit.ritz:5:8" in out, out
    assert _msg("(") in out, out
    assert "Traceback (most recent call last)" not in out, out


@pytest.mark.integration
def test_one_line_if_in_parens_still_compiles(tmp_path):
    rc, out = _compile(tmp_path, ACCEPTED["one_line_if_in_paren"], "--no-runtime")
    assert rc == 0, out
