"""AGAST #3387 (LARB R46, spec §2.2): a continuation line may be indented deeper.

THE DEFECT (#2193)

    let h = (a or b) and
            c and d          # ritz0: Expected expression, got INDENT

    not (a or
         b)                  # same error

The lexer pushed an indent level for the deeper line and emitted INDENT (and
later a DEDENT), which no expression can start with.  #2954 had allowed only
a SAME-indent continuation, because the Pratt loop skips NEWLINE alone.

THE RULE (R46)

After a line ending in a binary operator or `as`, the next line opens and
closes no block: it emits no INDENT / DEDENT.  It must be indented at least
as far as the statement's first line; shallower is an error at that line.
Inside ( [ { indentation is ignored altogether.

THE FIX

The lexer can't tell a binary `>` / `>>` from a generic list's close
(`fn f() -> Vec<T>` then its body), so the parser decides: when its Pratt
loop has consumed an infix operator and finds a layout token after the line
break, it re-derives the layout with that line marked as a continuation
(`lexer.relayout`), which also refuses a shallower one.  The lexer defers
its "Unindent does not match" (a marked INDENT) for the same reason.

NOT DONE HERE: R46's "inside ( [ { indentation is ignored altogether".
ritz0 parses a block `if` / `match` inside call parens and pins it
(test_return_expected_enum.py `call_arg_arm`, LANGUAGE_SPEC's #1435
example), which needs layout there; R46 doesn't say which wins, so it is
asked rather than decided.  The #2193 paren repro is an operator
continuation and works through the rule above.

THE TESTS

Parse-level rows (no compile) separate the code paths: deeper, shallower
than the statement (refused, located), shallower than an earlier
continuation but not than the statement (accepted), a bad unindent with no
operator (still refused), `as`, an `if` condition followed by its block, a
two-level dedent after a continuation, a generic `>` ending a header,
#2954's same-indent form, and the speculative-parse undo.  One
row compiles and runs both #2193 repros under ritz0.
"""

import pytest

import lexer
import ritz_ast as rast
from lexer import Lexer, LexerError
from parser import ParseError, Parser, parse


def _fn(mod, name):
    return next(i for i in mod.items if getattr(i, "name", None) == name)


# --- the two #2193 repros -------------------------------------------------

REPRO_AND = """\
fn f(a: bool, b: bool, c: bool, d: bool) -> bool
    let h = (a or b) and
            c and d
    h
"""

REPRO_NOT = """\
fn g(a: bool, b: bool) -> bool
    not (a or
         b)
"""


def test_repro_deeper_after_operator_parses():
    fn = _fn(parse(REPRO_AND), "f")
    let = fn.body.stmts[0]
    # `(a or b) and c and d`: one `let`, then the tail `h`.
    assert isinstance(let.value, rast.BinOp) and let.value.op == "and"
    assert len(fn.body.stmts) == 1
    assert isinstance(fn.body.expr, rast.Ident)


def test_repro_deeper_inside_parens_parses():
    fn = _fn(parse(REPRO_NOT), "g")
    assert isinstance(fn.body.expr, rast.UnaryOp)


# --- R46's rule -----------------------------------------------------------

def test_shallower_than_statement_is_refused_at_that_line():
    src = """\
fn f(a: i32, b: i32) -> bool
    if true
        let t = a == 0 and
    b == 0
        return t
    false
"""
    with pytest.raises((LexerError, ParseError)) as e:
        parse(src, "c.ritz")
    msg = str(e.value)
    assert "c.ritz:4:" in msg, msg
    assert "continuation" in msg, msg


def test_bad_unindent_without_operator_still_refused():
    # Line 4 is between levels and no operator ends line 3: the lexer's
    # deferred error is raised at it, as before.
    src = "fn f() -> i32\n    if true\n        g()\n      h()\n    0\n"
    with pytest.raises(LexerError) as e:
        parse(src, "c.ritz")
    assert "c.ritz:4:" in str(e.value)
    assert "Unindent does not match" in str(e.value)


def test_shallower_than_earlier_continuation_is_accepted():
    # Line 4 is shallower than line 3 but as deep as the statement (line 2).
    src = """\
fn f(a: i32, b: i32, c: i32) -> i32
    let s = a +
                b +
        c
    s
"""
    fn = _fn(parse(src), "f")
    assert len(fn.body.stmts) == 1 and isinstance(fn.body.expr, rast.Ident)


def test_as_continuation_deeper():
    src = "fn f(x: i32) -> i64\n    x as\n        i64\n"
    assert isinstance(_fn(parse(src), "f").body.expr, rast.Cast)


def test_if_condition_continued_then_block():
    # The continuation is no block; the line after it, deeper than the `if`,
    # is the `if`'s block.
    src = """\
fn f(a: bool, b: bool) -> i32
    if a and
            b
        return 1
    0
"""
    fn = _fn(parse(src), "f")
    stmt = fn.body.stmts[0]
    iff = getattr(stmt, "expr", stmt)
    assert isinstance(iff, rast.If)
    assert isinstance(iff.cond, rast.BinOp) and iff.cond.op == "and"
    assert isinstance(fn.body.expr, rast.IntLit)


def test_two_level_dedent_after_continuation():
    src = """\
fn f(a: i32) -> i32
    if a > 0
        let t = a +
                1
        return t
    0

fn g() -> i32
    1
"""
    mod = parse(src)
    assert isinstance(_fn(mod, "f").body.expr, rast.IntLit)
    assert isinstance(_fn(mod, "g").body.expr, rast.IntLit)


def test_generic_close_ending_a_header_still_opens_its_block():
    # `>` / `>>` here end a type, not an operator: the body is a block.
    src = """\
struct Box<T>
    v: T

fn f(b: Box<Box<i32>>) -> Box<Box<i32>>
    b
"""
    mod = parse(src)
    assert isinstance(_fn(mod, "f").body.expr, rast.Ident)


def test_same_indent_continuation_unchanged():
    # AGAST #2954.
    src = "fn f(a: i32, b: i32) -> bool\n    a == 0 and\n    b == 0\n"
    e = _fn(parse(src), "f").body.expr
    assert isinstance(e, rast.BinOp) and e.op == "and"


def test_relayout_without_continuations_is_the_lexers_layout():
    # relayout re-derives exactly what the lexer emitted when no line is a
    # continuation: one layout algorithm, two places, kept in step.
    src = REPRO_AND + "\n" + REPRO_NOT + "\nstruct S<T>\n    v: [4]T\n    w: i32\n"
    toks = Lexer(src, "c.ritz").tokenize()
    assert lexer.relayout(toks, set()) == toks


def test_speculative_reset_undoes_a_relayout():
    # A relayout is a token-list rewrite like a `>>` split: _reset undoes it.
    toks = Lexer("x = a +\n        b\n", "c.ritz").tokenize()
    p = Parser(list(toks))
    p._advance()  # x
    p._advance()  # =
    mark = p._mark()
    p.parse_expr()
    assert p.tokens != toks and p._continuations
    p._reset(mark)
    assert p.tokens == toks and not p._continuations


# --- runs -------------------------------------------------------------------

RUN = """\
fn f(a: bool, b: bool, c: bool, d: bool) -> bool
    let h = (a or b) and
            c and d
    h

fn g(a: bool, b: bool) -> bool
    not (a or
         b)

pub fn main() -> i32
    if not f(true, false, true, true) or f(false, false, true, true)
        return 1
    if g(true, false) or not g(false, false)
        return 2
    42
"""


@pytest.mark.integration
@pytest.mark.batched
def test_both_2193_repros_run(tmp_path):
    from test_ritz1_builtin_struct_shadow import _run
    assert _run("ritz0", tmp_path, "deeper_cont", RUN) == 42
