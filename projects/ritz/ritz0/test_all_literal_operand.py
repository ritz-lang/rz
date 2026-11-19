#!/usr/bin/env python3
"""An all-literal subexpression is one literal of its value (AGAST #4082).

LARB R21 (#3112) types an untyped literal operand from its sibling, so with
`w: i32`, `w ^ 1` is an i32 xor. A BinOp / UnaryOp whose operands are ALL
literals has no typed sibling of its own, so it was computed at i64 and widened
the expression around it into an implicit-narrowing error (#1393, #1444):

    let a: i32 = w ^ (0 - 1)     # rejected: initialiser is i64
    let b: i32 = v & ~63         # rejected
    g4 = g4 - (1 << 26)          # rejected (g4: u32)

The rule pinned here: such a subexpression is a constant. It is folded with
the i64 semantics it had (`const_eval.fold_literal_i64`) and then is exactly
the literal of that value, so R21 gives it the sibling's width when the value
fits. #1396's `>>` / `/` / `%` hazard is why the FOLD stays at i64 (exact
arithmetic, refused if any step leaves i64): folding `(1 << 40) >> 38` at the
slot's 32 bits would give 0, not 4. A folded value that doesn't fit the
sibling keeps today's i64 path rather than becoming an error.

Rows are sized to the rule's parts (docs/TESTING.md), not a cross product:
  * acceptance, one row per slot route the ticket names (let, assign) and per
    operator form (BinOp, UnaryOp), asserted on IR shape, since "it compiles"
    alone could pass by widening and truncating;
  * the fold's own semantics (`fold_literal_i64`) as unit rows;
  * one run whose exit code pins the values the hazard could change.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from const_eval import fold_literal_i64
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.integration


def _compile(tmp_path, source, name="unit"):
    src = tmp_path / f"{name}.ritz"
    src.write_text(source)
    out = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(out), "--no-runtime"],
                     env=env, timeout=300)
    return proc, out


def _body(ir_text, fn_name):
    """A function's instruction lines, debug metadata stripped."""
    m = re.search(r'define [^\n]*@"%s"[^\n]*\n\{\n(.*?)\n\}' % re.escape(fn_name),
                  ir_text, re.S)
    assert m, f"function {fn_name} not found in IR"
    lines = []
    for line in m.group(1).splitlines():
        line = re.sub(r",?\s*!dbg.*$", "", line).strip()
        if line and "llvm.dbg" not in line:
            lines.append(line)
    return lines


# The ticket's rows, one fn each, so each is its own assertion.
TICKET_ROWS = """\
fn let_binop(w: i32) -> i32
    let a: i32 = w ^ (0 - 1)
    return a

fn let_unary(v: i32) -> i32
    let b: i32 = v & ~63
    return b

fn assign_shift(g: u32) -> u32
    var g4: u32 = g
    g4 = g4 - (1 << 26)
    return g4

fn nested_left(w: i32) -> i32
    let c: i32 = (0 - 1 - 1) ^ w
    return c

fn arg_slot(v: i32) -> i32
    return let_unary((v + 63) & ~63)
"""


@pytest.mark.unit
def test_the_ticket_rows_compile_at_the_sibling_width(tmp_path):
    """Accepted, and computed at the operand's width: no i64, no trunc."""
    proc, out = _compile(tmp_path, TICKET_ROWS)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ir_text = out.read_text()
    for fn in ("let_binop", "let_unary", "assign_shift", "nested_left", "arg_slot"):
        body = _body(ir_text, fn)
        wide = [l for l in body if re.search(r"\bi64\b|\btrunc\b", l)]
        assert not wide, f"{fn}: the all-literal operand was computed in i64: {wide}"


@pytest.mark.unit
def test_a_folded_value_that_does_not_fit_keeps_the_old_path(tmp_path):
    """`x + (1 << 40)` with x: u32 is not an error: it widens, as it did."""
    proc, out = _compile(tmp_path, (
        "fn f(x: u32) -> i64\n"
        "    let big: i64 = x + (1 << 40)\n"
        "    return big\n"
    ))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert any("add i64" in l for l in _body(out.read_text(), "f"))


@pytest.mark.unit
@pytest.mark.parametrize("src, want", [
    ("0 - 1", -1),
    ("~63", -64),
    ("1 << 26", 1 << 26),
    ("(0 - 7) / 2", -3),            # sdiv truncates toward zero
    ("(0 - 7) % 2", -1),            # srem takes the dividend's sign
    ("(1 << 40) >> 38", 4),         # the #1396 hazard: not 0
    ("(0 - 64) >> 3", -8),          # an i64 `>>` is arithmetic
    ("-(2 + 3)", -5),
])
def test_fold_is_the_i64_value(src, want):
    assert fold_literal_i64(_expr(src)) == want


@pytest.mark.unit
@pytest.mark.parametrize("src", [
    "7",                            # a plain literal is already one
    "-7",
    "(1 << 63) >> 60",              # an intermediate leaves i64: i64 says -8
    "9223372036854775807 + 1",
    "1 / 0",
    "1 << 64",
    "1 << (0 - 1)",
    "1 < 2",                        # a compare is a bool, not an integer
    "x + 1",
    "!1",
])
def test_fold_refuses(src):
    assert fold_literal_i64(_expr(src)) is None


def _expr(src):
    """Parse `src` as one expression (as test_const_eval.py does)."""
    from lexer import Lexer
    from parser import Parser
    return Parser(list(Lexer(src, "test").tokenize())).parse_expr()


@pytest.mark.unit
def test_folded_operands_give_the_same_answers(tmp_path):
    """Each check fails with its own exit code; 0 is all right.

    `x / (4 - 2)` on a u32 above 2**31 is an unsigned divide, and so is the
    `>>` of `(x + (2 - 1))`: once the folded side is a u32, `_int_shape` must
    not read it as an i64 and make the sum signed (an `ashr`).
    """
    src = tmp_path / "rt.ritz"
    src.write_text(
        "fn divu(x: u32) -> u32\n"
        "    let q: u32 = x / (4 - 2)\n"
        "    return q\n"
        "\n"
        "fn shr(x: u32) -> u32\n"
        "    let r: u32 = (x + (2 - 1)) >> 1\n"
        "    let l: u32 = ((2 - 1) + x) >> 1\n"
        "    return r + l\n"
        "\n"
        "fn hazard(x: i32) -> i32\n"
        "    let r: i32 = x + ((1 << 40) >> 38)\n"
        "    return r\n"
        "\n"
        "fn neg(x: i32) -> i32\n"
        "    let r: i32 = x + (0 - 7) / 2\n"
        "    return r\n"
        "\n"
        "fn overflowing(x: i32) -> i64\n"
        "    let r: i64 = x + ((1 << 63) >> 60)\n"
        "    return r\n"
        "\n"
        "fn flip(w: i32) -> i32\n"
        "    var v: i32 = w\n"
        "    v = v ^ (0 - 1)\n"
        "    return v\n"
        "\n"
        "fn main() -> i32\n"
        "    if divu(4000000000 as u32) != 2000000000 as u32\n"
        "        return 1\n"
        "    if shr(4294967294 as u32) != 4294967294 as u32\n"
        "        return 6\n"
        "    if hazard(10) != 14\n"
        "        return 2\n"
        "    if neg(10) != 7\n"
        "        return 3\n"
        "    if overflowing(10) != 2\n"
        "        return 4\n"
        "    if flip(5) != -6\n"
        "        return 5\n"
        "    return 0\n"
    )
    ll, exe = tmp_path / "rt.ll", tmp_path / "rt"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    build = run_ritz0([str(src), "-o", str(ll)], env=env, timeout=300)
    assert build.returncode == 0, build.stdout + build.stderr
    link = fast_link.clang(["clang", str(ll), "-o", str(exe), "-nostdlib"],
                           capture_output=True, text=True, timeout=300)
    assert link.returncode == 0, link.stderr
    run = subprocess.run([str(exe)], capture_output=True, timeout=60)
    assert run.returncode == 0, f"check {run.returncode} gave a wrong answer"
