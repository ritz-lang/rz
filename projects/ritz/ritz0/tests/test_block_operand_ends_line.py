"""AGAST #3435 (spec §2.2): the line after a block `if` / `match` operand is a new statement.

THE DEFECT (found in #3429, LARB R46a)

    let x = 5 + if c == 1
        1
    else
        2
    -x                     # ritz0: `let x = (5 + if … else 2) - x`, no tail

The `if`'s block ends in a DEDENT with no NEWLINE after it, so the enclosing
Pratt loop (parser.py `parse_expr`) found the next line's `-` straight after
the operand and read it as infix: two statements became one.  With `*p = x`
as the next line it was `… * p = x` ("Expected expression, got EQ").  A bare
`let x = if …` was fine: `parse_expr` returns a block operand that starts the
expression without entering the loop.  The defect needs the block to be an
operand of something: `5 + if`, `-if`, `5 + 2 * if`.

ritz1 had the same defect after a `match` operand (its grammar's operator
tails, grammars/ritz1.grammar `or_tail` … `cast_tail`): `y = 5 + match c` …
then `-y` was `y = 5 + match … - y`.  It refuses a block `if` operand, and has
no statement form ending in a block operand, so the line it swallowed was the
only way it took one.

THE RULE (§2.2)

A line that doesn't end in an operator ends the statement.  A block's last
line ends in no operator, so once an operand's block has ended (its DEDENT
consumed), the statement ends.

THE FIX

ritz0: the infix loop stops when the token before it is a DEDENT.  ritz1:
each operator tail first tries `block_ended`, which matches nothing when
the previous token is a DEDENT and ends the tail there.

THE TESTS

Parse rows (ritz0, no compile): `-x` and `*p = x` after an `if` and a `match`
operand, each two statements; the unary (`-if`) and nested (`5 + 2 * if`)
operand shapes, which leave the loop at different depths; and every infix
token at the start of the next line, which is now its own statement (refused
there, or a statement of its own), never part of the `let`.  The infix rows
are checked against the parser's precedence table, so a new operator gets one.
ritz0 runs the `match` and `if` shapes, and so do ritz1 and ritz1_selfhosted
since #4553 (`if`) and #4049 (`match`, in every statement form).
"""

import pytest
import ritz_ast as rast
from lexer import Lexer
from parser import ParseError, Parser, parse
from test_ref_into_value import _run


def _body(src):
    return parse(src).items[0].body


IF_OPERAND = """\
fn g(p: *i32, c: i32) -> i32
    let x = 5 + if c == 1
        1
    else
        2
"""

MATCH_OPERAND = """\
fn g(p: *i32, c: i32) -> i32
    let x = 5 + match c
        1 => 1
        _ => 2
"""

OPERANDS = {"if": (IF_OPERAND, rast.If), "match": (MATCH_OPERAND, rast.Match)}


def _assert_let_is_five_plus_block(let, block_type):
    assert isinstance(let, rast.LetStmt), let
    assert isinstance(let.value, rast.BinOp) and let.value.op == "+", let.value
    assert isinstance(let.value.right, block_type), let.value


# --- `-` and `*`: the next line is a statement of its own --------------------

@pytest.mark.unit
@pytest.mark.parametrize("kind", sorted(OPERANDS))
def test_minus_line_after_block_operand_is_the_tail(kind):
    src, block_type = OPERANDS[kind]
    body = _body(src + "    -x\n")
    assert len(body.stmts) == 1, body.stmts
    _assert_let_is_five_plus_block(body.stmts[0], block_type)
    assert isinstance(body.expr, rast.UnaryOp) and body.expr.op == "-", body.expr
    assert isinstance(body.expr.operand, rast.Ident) and body.expr.operand.name == "x"


@pytest.mark.unit
@pytest.mark.parametrize("kind", sorted(OPERANDS))
def test_star_line_after_block_operand_is_a_store(kind):
    src, block_type = OPERANDS[kind]
    body = _body(src + "    *p = x\n    x\n")
    assert len(body.stmts) == 2, body.stmts
    _assert_let_is_five_plus_block(body.stmts[0], block_type)
    store = body.stmts[1]
    assert isinstance(store, rast.AssignStmt), store
    assert isinstance(store.target, rast.UnaryOp) and store.target.op == "*", store.target


@pytest.mark.unit
def test_unary_block_operand_ends_the_statement():
    # `-if …`: the loop is entered with the UnaryOp as `left`.
    body = _body("""\
fn g(c: i32) -> i32
    let x = -if c == 1
        1
    else
        2
    -x
""")
    let = body.stmts[0]
    assert isinstance(let.value, rast.UnaryOp) and isinstance(let.value.operand, rast.If)
    assert isinstance(body.expr, rast.UnaryOp) and body.expr.op == "-", body.expr


@pytest.mark.unit
def test_nested_block_operand_ends_the_statement():
    # `5 + 2 * if …`: the inner loop gives up on `-` by precedence and the
    # outer one, a frame further out, must stop too.
    body = _body("""\
fn g(c: i32) -> i32
    let x = 5 + 2 * if c == 1
        1
    else
        2
    -x
""")
    let = body.stmts[0]
    assert isinstance(let.value, rast.BinOp) and let.value.op == "+", let.value
    mul = let.value.right
    assert isinstance(mul, rast.BinOp) and mul.op == "*" and isinstance(mul.right, rast.If)
    assert isinstance(body.expr, rast.UnaryOp) and body.expr.op == "-", body.expr


# --- every infix token: never part of the `let` ------------------------------

INFIX_TEXTS = ["or", "||", "and", "&&", "|", "^", "&", "==", "!=", "<", ">", "<=", ">=",
               "<<", ">>", "+", "-", "*", "/", "%", "+%", "-%", "*%", "..", "..=", "as"]


@pytest.mark.unit
def test_infix_rows_cover_the_precedence_table():
    kinds = {Lexer(f"{t} x\n").tokenize()[0].type for t in INFIX_TEXTS}
    assert kinds == set(Parser.PRECEDENCE), set(Parser.PRECEDENCE) ^ kinds


@pytest.mark.unit
@pytest.mark.parametrize("op", INFIX_TEXTS)
def test_infix_at_line_start_after_if_operand_is_not_absorbed(op):
    src = IF_OPERAND + f"    {op} x\n    0\n"
    try:
        body = _body(src)
    except ParseError as e:
        assert e.span.line == 6, f"refused at {e.span}, not at the `{op}` line: {e}"
        return
    _assert_let_is_five_plus_block(body.stmts[0], rast.If)


# --- the programs run ---------------------------------------------------------

MATCH_PROGRAM = """\
fn g(p: *i64, c: i32) -> i64
    let x = 5 + match c
        1 => 1
        _ => 2
    *p = x
    -x

fn main() -> i32
    var v: i64 = 0
    if g(@&v, 2) != -7
        return 1
    if v != 7
        return 2
    if g(@&v, 1) != -6
        return 3
    0
"""

IF_PROGRAM = """\
fn g(p: *i64, c: i32) -> i64
    let x = 5 + if c == 1
        1
    else
        2
    *p = x
    -x

fn main() -> i32
    var v: i64 = 0
    if g(@&v, 2) != -7
        return 1
    if v != 7
        return 2
    if g(@&v, 1) != -6
        return 3
    0
"""


@pytest.mark.integration
@pytest.mark.batched
@pytest.mark.parametrize("name, program", [("match_operand", MATCH_PROGRAM), ("if_operand", IF_PROGRAM)])
def test_block_operand_then_store_and_tail_runs(tmp_path, name, program):
    assert _run("ritz0", tmp_path, name, program) == 0


# AGAST #4049: a block `match` operand in every statement form ritz1 has
# (let / var / assign / return / fn tail), nested under `*` and under unary
# `-`, and narrowed into a u8 slot through `+` (narrow_congs_fit).  ritz0
# always took these; ritz1 parsed the operand but no statement rule ended at
# its DEDENT, so it refused the line after it.
MATCH_OPERAND_FORMS = """\
fn let_form(c: i32) -> i32
    let x: i32 = 6 + match c
        1 => 1
        _ => 2
    x

fn var_assign_form(c: i32) -> i32
    var y: i32 = 10 + match c
        1 => 1
        _ => 2
    y = y * 2 + match c
        1 => 100
        _ => 200
    y

fn return_form(c: i32) -> i32
    return 100 + match c
        1 => 1
        _ => 2

fn tail_form(c: i32) -> i32
    1000 + 2 * match c
        1 => 1
        _ => 2

fn neg_form(c: i32) -> i32
    let x: i32 = -match c
        1 => c
        _ => c + 2
    x

fn byte_form(c: i32, a: u8, b: u8) -> u8
    let x: u8 = 6 + match c
        1 => a
        _ => b
    x

fn main() -> i32
    if let_form(1) != 7 or let_form(0) != 8
        return 1
    if var_assign_form(1) != 122 or var_assign_form(0) != 224
        return 2
    if return_form(1) != 101 or return_form(0) != 102
        return 3
    if tail_form(1) != 1002 or tail_form(0) != 1004
        return 4
    if neg_form(1) != -1 or neg_form(0) != -2
        return 5
    if (byte_form(1, 1, 2) as i32) != 7 or (byte_form(0, 1, 2) as i32) != 8
        return 6
    42
"""

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


@pytest.mark.integration
@pytest.mark.batched
@pytest.mark.parametrize("compiler", COMPILERS)
def test_match_operand_in_every_statement_form_runs(request, tmp_path, compiler):
    if compiler != "ritz0":
        request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, "match_operand_forms", MATCH_OPERAND_FORMS) == 42


# Before #3435 ritz1 took a block `match` operand only when the next line
# began with an operator, and then swallowed that line (`*p = x` read as
# `… * p = x`, `-x` as `… - x`).  Since #4049 it takes the operand and the
# next line is a statement of its own, so MATCH_PROGRAM's store and `-x`
# tail run as on ritz0: a swallowed line would not return 0.
@pytest.mark.integration
@pytest.mark.batched
@pytest.mark.parametrize("compiler", ["ritz1", "ritz1_selfhosted"])
def test_ritz1_match_operand_then_store_and_tail_runs(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    assert _run(compiler, tmp_path, "match_operand", MATCH_PROGRAM) == 0
