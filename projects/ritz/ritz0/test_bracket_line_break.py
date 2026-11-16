"""AGAST #3426 (spec §2.2): inside ( [ { a line break is no token at all.

THE RULE

"Inside `(`, `[` or `{` line breaks and indentation are ignored altogether."
So an expression may break anywhere inside brackets, before an operator too:

    (a
        + b)

LARB R46a (#3429) still holds: no block opens inside brackets, and an `if`
there whose line ends before its `then`, other than after an operator, is
refused at the `if` (ritz1's lexer rule, #3388).

THE DEFECT

ritz0's lexer emitted NEWLINE (and INDENT / DEDENT) at bracket depth > 0, and
the parser skipped them only at chosen points (after `(`, `,`, an operator).
A break before an operator ended the expression: "Expected RPAREN, got
NEWLINE".  And a deeper break inside a bracketed one-line `if` condition was
laid out ("Expected item").

THE FIX

The lexer tracks bracket depth and, inside brackets, consumes a line break
and the next line's indentation as whitespace (ritz1's lexer does the same).
`relayout` re-derives layout from NEWLINE positions, so it emits none inside
brackets either.  The R46a "then on a later line" refusal, which used to
fall out of the NEWLINE, is now an explicit parser check (`parse_if`).

THE TESTS

Parse-level only (no compile).  The ticket's two repros; a break before an
operator in each bracket kind; the lexer emits no layout token inside
brackets and `relayout` agrees with it; and the R46a refusals that depended
on the old NEWLINE.
"""

import pytest

import ritz_ast as rast
from lexer import relayout, tokenize
from parser import ParseError, parse
from tokens import TokenType

LAYOUT = (TokenType.NEWLINE, TokenType.INDENT, TokenType.DEDENT)

# name -> source that must parse
ACCEPTED = {
    # The ticket's first repro.
    "break_before_op_in_paren": """\
fn f(a: i32, b: i32) -> i32
    (a
        + b)
""",
    # The ticket's second repro: a deeper break inside a bracketed one-line
    # `if` condition.
    "break_in_bracketed_if_condition": """\
fn take(x: i32) -> i32
    x

fn g(c: i32) -> i32
    take(if take(
            c) == 1 then 0 else 9)
""",
    "break_before_op_in_bracket": """\
fn f(a: *i32, i: i32) -> i32
    a[i
        - 1]
""",
    "break_before_op_in_brace": """\
struct S
    v: i32

fn f(a: i32, b: i32) -> i32
    let s = S { v: a
        * b }
    s.v
""",
    # A shallower line inside brackets is no DEDENT: the block goes on.
    "shallower_line_in_paren": """\
fn f(a: i32, b: i32) -> i32
    let x = (a
+ b)
    x
""",
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_a_line_break_inside_brackets_is_ignored(name):
    parse(ACCEPTED[name])


@pytest.mark.unit
def test_break_before_operator_parses_as_the_one_line_form():
    module = parse(ACCEPTED["break_before_op_in_paren"])
    tail = module.items[0].body.expr
    assert isinstance(tail, rast.BinOp) and tail.op == "+", tail


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(ACCEPTED))
def test_the_lexer_emits_no_layout_inside_brackets(name):
    tokens = tokenize(ACCEPTED[name])
    depth = 0
    for tok in tokens:
        if tok.type in (TokenType.LPAREN, TokenType.LBRACKET, TokenType.LBRACE):
            depth += 1
        elif tok.type in (TokenType.RPAREN, TokenType.RBRACKET, TokenType.RBRACE):
            depth -= 1
        elif depth > 0:
            assert tok.type not in LAYOUT, (name, tok)
    # relayout re-derives exactly the lexer's layout (pinned more widely by
    # test_deeper_continuation.py).
    assert relayout(tokens, set()) == tokens


def _msg(bracket):
    return f"a block can't open inside `{bracket}`: bind the `if`/`match` to a `let` first"


_TAKE = "fn take(x: i32) -> i32\n    x\n\n"

# name -> (source, bracket, line, column of the `if`)
REFUSED = {
    # `then` on the line after the condition: refused, as ritz1 does.
    "then_on_next_line": (_TAKE + """\
fn g(c: i32) -> i32
    take(if c == 1
        then 0 else 9)
""", "(", 5, 10),
    # A break before an operator in the condition: the condition's line
    # ended without an operator (ritz1's rule).
    "break_before_op_in_condition": (_TAKE + """\
fn g(c: i32) -> i32
    take(if c
        == 1 then 0 else 9)
""", "(", 5, 10),
    # The innermost `if`'s bracket is named.
    "then_on_next_line_innermost": (_TAKE + """\
fn g(a: *i32, c: i32) -> i32
    take(a[if c == 1
        then 0 else 1])
""", "[", 5, 12),
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_an_if_broken_before_then_is_refused(name):
    source, bracket, line, col = REFUSED[name]
    with pytest.raises(ParseError) as info:
        parse(source)
    err = info.value
    assert _msg(bracket) in str(err), str(err)
    assert (err.span.line, err.span.column) == (line, col), (
        f"{name}: located at {err.span.line}:{err.span.column}, want {line}:{col}")


# Breaks inside the condition that R46a allows: after an operator, or inside
# a bracket of the condition's own.
CONDITION_OK = {
    "after_operator": _TAKE + """\
fn g(c: i32) -> i32
    take(if c ==
        1 then 0 else 9)
""",
    "inside_a_nested_bracket": _TAKE + """\
fn g(c: i32) -> i32
    take(if take(c
        + 1) == 1 then 0 else 9)
""",
}


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(CONDITION_OK))
def test_an_if_condition_may_break_after_an_operator_or_deeper(name):
    parse(CONDITION_OK[name])
