#!/usr/bin/env python3
"""An `if` with no `else` has no value, so using one as a value is an error.

AGAST #1406.

THE DEFECT

`if` is an expression in ritz0, and `_emit_if` returns a phi node when both
arms produce a value. When there is no `else` there is nothing to merge, so it
returns `None` — which is correct, because the same function also serves
statement position, where there is no value to produce.

The caller in `_emit_expr` then did this:

    result = self._emit_if(expr)
    if result is not None:
        return result
    # If no value (shouldn't happen for well-formed if expressions), return 0
    return ir.Constant(self.i32, 0)

The comment says "shouldn't happen". It happens. The manufactured zero is
stored into the binding, the taken branch's value is discarded, and the
program compiles at exit 0 and returns the wrong answer:

    fn pick(c: i32) -> i32
        let x = if c == 1
            1
        return x                      # source says 1, program returns 0

WHY REJECTION RATHER THAN A ZERO PHI

The ticket forbids synthesising a zero (or undef) for the missing arm. That
would keep every one of these programs compiling and merely make the wrong
answer deliberate. `if c` with no `else` has no value on the path where `c` is
false; the only answer that cannot be silently wrong is to refuse it, at the
source location.

WHERE THE CHECK LIVES — AND WHY NOT IN `_emit_expr`

Versions 1–4 of this fix decided "value position" inside the emitter, from
the *expression's* point of view (`_emit_expr`, function tails, reachability).
Every one redded live code, each caught by a deeper gate than the last:

    v1  every procedure ending in a guard                    own probing
    v2  ritzlib/hashmap.ritz:210 (tail if/else, procedure)  bootstrap
    v3  tier1 91_loop_trailing_expr, tier2 15_cut            regression
    v4  angelo interpreter.ritz:295, tests.ritz:727          GitHub build-all
        — a statement-position `match` whose arm ends in an else-less `if`

The expression cannot know whether its value is consumed. The *statement*
can. So v5 checks at the four statements that consume a value — `let`, `var`,
assignment, `return` — and walks only that value's result paths: `if` arms,
block tails and `match` arm bodies. A `match` used as a statement is never
walked, so angelo's shape cannot be reached.

AGAST #1435 extends the walk into operand positions (operator operands, call
and method arguments, index, field base, cast, struct-literal fields, ...).
An operand's value is consumed no matter which statement holds it, so that
part of the walk runs from every statement and from a function's tail too.
It still never enters `Block.stmts` or a lambda/closure body.

The function-tail shape (a fn declaring `-> T` whose last statement is an
else-less `if`) is deliberately NOT covered; it is AGAST #1429, pinned below
so a change to it is made on purpose.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"


def _compile(tmp_path, source):
    """Compile a fragment. Returns (returncode, combined_output, ir_or_None)."""
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    out = tmp_path / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(out), "--no-runtime"],
        capture_output=True, text=True, env=env, timeout=300,
    )
    combined = proc.stdout + proc.stderr
    ir_text = out.read_text() if out.exists() else None
    return proc.returncode, combined, ir_text


def _run(tmp_path, source):
    """Build with the runtime and execute. Returns the program's exit code.

    `-nostdlib` matches build.py: ritz0 emits its own `_start`, and linking
    crt1 as well fails with a duplicate `_start`. That link failure also exits
    1, so the link is asserted separately rather than folded into the result.
    """
    src = tmp_path / "prog.ritz"
    src.write_text(source)
    ll = tmp_path / "prog.ll"
    exe = tmp_path / "prog"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(ll)],
        capture_output=True, text=True, env=env, timeout=300,
    )
    assert proc.returncode == 0, f"compile failed:\n{proc.stdout}{proc.stderr}"
    link = subprocess.run(
        ["clang", "-w", "-O0", "-nostdlib", str(ll), "-o", str(exe)],
        capture_output=True, text=True, timeout=300,
    )
    assert link.returncode == 0, f"link failed:\n{link.stderr}"
    return subprocess.run([str(exe)], timeout=60).returncode


# Every consuming statement, plus each result path the walk must follow. Each
# one compiled at exit 0 and returned 0 before the fix where the source says 1
# (the `assignment` case even discards the prior value 7).
VALUE_POSITIONS = {
    "let_inferred": (
        "fn pick(c: i32) -> i32\n"
        "    let x = if c == 1\n"
        "        1\n"
        "    return x\n"
    ),
    "let_annotated": (
        "fn pick(c: i32) -> i32\n"
        "    let x: i32 = if c == 1\n"
        "        1\n"
        "    return x\n"
    ),
    "var_initialiser": (
        "fn pick(c: i32) -> i32\n"
        "    var x = if c == 1\n"
        "        1\n"
        "    return x\n"
    ),
    "assignment": (
        "fn pick(c: i32) -> i32\n"
        "    var x: i32 = 7\n"
        "    x = if c == 1\n"
        "        1\n"
        "    return x\n"
    ),
    "return_value": (
        "fn pick(c: i32) -> i32\n"
        "    return if c == 1\n"
        "        1\n"
    ),
    # Result path: the then-arm's tail of an otherwise total if/else.
    "inside_if_arm": (
        "fn pick(c: i32, d: i32) -> i32\n"
        "    let x = if c == 1\n"
        "        if d == 1\n"
        "            1\n"
        "    else\n"
        "        2\n"
        "    return x\n"
    ),
    # Result path: an else-if chain that never reaches a final `else`.
    "open_else_if_chain": (
        "fn pick(c: i32) -> i32\n"
        "    let x = if c == 2\n"
        "        2\n"
        "    else if c == 1\n"
        "        1\n"
        "    return x\n"
    ),
    # Result path: a match arm's body, when the match itself is a value.
    "inside_match_arm": (
        "fn pick(c: i32) -> i32\n"
        "    let x = match c\n"
        "        1 =>\n"
        "            if c == 1\n"
        "                1\n"
        "        _ => 2\n"
        "    return x\n"
    ),
}


@pytest.mark.unit
@pytest.mark.parametrize("position", sorted(VALUE_POSITIONS))
def test_else_less_if_in_value_position_is_rejected(tmp_path, position):
    """The defect itself, at each position that reaches it."""
    rc, output, _ = _compile(tmp_path, VALUE_POSITIONS[position])
    assert rc != 0, (
        f"{position}: compiled at exit 0 — the taken branch is discarded and "
        f"the binding silently becomes 0"
    )
    assert re.search(r"no `else`", output), (
        f"{position}: rejected, but not for the missing else:\n{output}"
    )


@pytest.mark.unit
@pytest.mark.parametrize("position", sorted(VALUE_POSITIONS))
def test_rejection_never_manufactures_a_zero(tmp_path, position):
    """No IR may be written out that stores or returns a fabricated 0.

    This is the assertion that forbids the zero/undef-phi non-fix. Rejecting
    is not enough on its own if the emitter still writes the wrong module out
    alongside the error.
    """
    _, _, ir_text = _compile(tmp_path, VALUE_POSITIONS[position])
    if ir_text is None:
        return  # nothing emitted at all is the strongest possible pass
    pick = re.search(r'define [^\n]*@"pick"[^\n]*\n\{\n(.*?)\n\}', ir_text, re.S)
    if pick is None:
        return
    body = pick.group(1)
    for spelling in ("ret i32 0", "store i32 0"):
        assert spelling not in body, (
            f"{position}: emitted a fabricated zero (`{spelling}`):\n{body}"
        )


@pytest.mark.unit
def test_diagnostic_is_located_and_not_a_python_traceback(tmp_path):
    """`file:line:col:` — the same shape every other user error uses."""
    rc, output, _ = _compile(tmp_path, VALUE_POSITIONS["let_inferred"])
    assert rc != 0
    assert "Traceback (most recent call last)" not in output, (
        f"reported as a Python traceback:\n{output}"
    )
    assert re.search(r"unit\.ritz:2:\d+:", output), (
        f"diagnostic does not point at the `if` on line 2:\n{output}"
    )


@pytest.mark.unit
def test_diagnostic_points_at_the_inner_if_that_lacks_the_else(tmp_path):
    """In an open chain the outer `if` HAS an else; the inner one does not.

    Pointing at line 2 would send the reader to an `if` that is fine. The
    offending node is the `else if` on line 4.
    """
    rc, output, _ = _compile(tmp_path, VALUE_POSITIONS["open_else_if_chain"])
    assert rc != 0
    assert re.search(r"unit\.ritz:4:\d+:", output), (
        f"diagnostic does not point at the inner `if` on line 4:\n{output}"
    )


@pytest.mark.integration
def test_the_value_was_really_zero_before_and_is_one_after_adding_else(tmp_path):
    """End to end, on exit codes: the well-formed spelling returns the 1."""
    assert _run(tmp_path, (
        "fn pick(c: i32) -> i32\n"
        "    let x = if c == 1\n"
        "        1\n"
        "    else\n"
        "        0\n"
        "    return x\n"
        "fn main() -> i32\n"
        "    return pick(1)\n"
    )) == 1


# ---------------------------------------------------------------------------
# AGAST #1435: operand positions. An operand's value is always consumed —
# by the operator, the callee, the index, the cast — whatever statement the
# expression sits in. So the walk descends into operands from EVERY statement,
# including an `ExprStmt` and a function's tail, not only from the four
# consuming statements. It still never enters `Block.stmts` (each statement is
# checked on its own when emitted) or a lambda/closure body.
#
# Every entry compiled at exit 0 before the fix and used 0 for the `if`.
# ---------------------------------------------------------------------------

_ID = "fn id(v: i32) -> i32\n    return v\n"
_ID_P = "fn idp(p: *i32, v: i32)\n    *p = v\n"

OPERAND_POSITIONS = {
    "binop_right": (
        "fn pick(c: i32) -> i32\n"
        "    let x = 5 + if c == 1\n"
        "        1\n"
        "    return x\n"
    ),
    # `(if ...) + 5` does not parse; a unary wrapper puts the `if` on the
    # left operand's side regardless.
    "binop_left_in_return": (
        "fn pick(c: i32) -> i32\n"
        "    return (-(if c == 1\n"
        "        1\n"
        "    )) + 5\n"
    ),
    "unary_operand": (
        "fn pick(c: i32) -> i32\n"
        "    let x = -(if c == 1\n"
        "        1\n"
        "    )\n"
        "    return x\n"
    ),
    "call_argument": _ID + (
        "fn pick(c: i32) -> i32\n"
        "    return id(if c == 1\n"
        "        1\n"
        "    )\n"
    ),
    # The call is a statement, but its argument is still consumed.
    "call_argument_of_an_expr_stmt": _ID_P + (
        "fn pick(c: i32) -> i32\n"
        "    var r: i32 = 7\n"
        "    idp(@r, if c == 1\n"
        "        1\n"
        "    )\n"
        "    return r\n"
    ),
    # A procedure's tail is not a consuming statement (#1429's carve-out),
    # but an argument inside it is consumed.
    "call_argument_in_a_procedure_tail": _ID_P + (
        "fn g(p: *i32, c: i32)\n"
        "    idp(p, if c == 1\n"
        "        1\n"
        "    )\n"
    ),
    # Tail of a statement `if`'s arm: reached through the arm's block tail.
    "call_argument_in_a_statement_if_arm": _ID_P + (
        "fn g(p: *i32, c: i32, d: i32)\n"
        "    if d == 1\n"
        "        idp(p, if c == 1\n"
        "            1\n"
        "        )\n"
        "    *p = 3\n"
    ),
    "call_argument_in_a_while_body_tail": _ID_P + (
        "fn g(p: *i32, c: i32)\n"
        "    while *p < 10\n"
        "        idp(p, if c == 1\n"
        "            1\n"
        "        )\n"
    ),
    "method_call_argument": (
        "struct S\n"
        "    v: i32\n"
        "impl S\n"
        "    fn add(self:&, n: i32) -> i32\n"
        "        return self.v + n\n"
        "fn pick(s: *S, c: i32) -> i32\n"
        "    return s.add(if c == 1\n"
        "        1\n"
        "    )\n"
    ),
    "index": (
        "fn pick(a: *i32, c: i32) -> i32\n"
        "    return a[if c == 1\n"
        "        1\n"
        "    ]\n"
    ),
    "assignment_target_index": (
        "fn g(a: *i32, c: i32)\n"
        "    a[if c == 1\n"
        "        1\n"
        "    ] = 3\n"
    ),
    # `(if ...) as T` does not parse; the cast's operand is a BinOp holding
    # the `if`, so the walk must pass through Cast to reach it.
    "cast": (
        "fn pick(c: i32) -> i64\n"
        "    return (2 * if c == 1\n"
        "        1\n"
        "    ) as i64\n"
    ),
    "struct_literal_field": (
        "struct S\n"
        "    v: i32\n"
        "fn pick(c: i32) -> i32\n"
        "    let s = S { v: if c == 1\n"
        "        1\n"
        "    }\n"
        "    return s.v\n"
    ),
    "while_condition": (
        "fn g(c: i32)\n"
        "    while (if c == 1\n"
        "        true\n"
        "    )\n"
        "        pass\n"
    ),
    # Result path and operand compose: the `if` is an operand inside the
    # value arm of a total if/else.
    "operand_inside_a_value_arm": (
        "fn pick(c: i32, d: i32) -> i32\n"
        "    let x = if d == 1\n"
        "        5 + if c == 1\n"
        "            1\n"
        "    else\n"
        "        2\n"
        "    return x\n"
    ),
}


@pytest.mark.unit
@pytest.mark.parametrize("position", sorted(OPERAND_POSITIONS))
def test_else_less_if_in_an_operand_position_is_rejected(tmp_path, position):
    """AGAST #1435: the same zero, one level further in."""
    rc, output, _ = _compile(tmp_path, OPERAND_POSITIONS[position])
    assert rc != 0, (
        f"{position}: compiled at exit 0 — the `if` silently evaluates to 0"
    )
    assert re.search(r"no `else`", output), (
        f"{position}: rejected, but not for the missing else:\n{output}"
    )
    assert "Traceback (most recent call last)" not in output, output


@pytest.mark.unit
@pytest.mark.parametrize("shape", [
    "binop_left", "binop_right", "unary", "call_arg", "call_func",
    "method_receiver", "method_arg", "index_base", "index_index",
    "field_base", "cast", "struct_field", "array_elem", "tuple_elem",
    "grouped", "try", "interp", "match_scrutinee", "match_guard",
    "if_cond", "return_expr", "assign_expr_value", "slice_start",
])
def test_walker_reaches_every_operand_node(shape):
    """Direct AST check for positions the parser cannot produce from source.

    `(if c / 1).v` and `(if c / 1) as T` do not parse, so Field base and
    Cast have no source-level test; this builds the tree by hand. Every
    shape wraps the offender in a NON-consuming position (an expression
    statement), so only the operand walk can find it.
    """
    import ritz_ast as rast
    from emitter_llvmlite import LLVMEmitter

    S = None  # spans are irrelevant to the walk

    x = rast.Ident(S, "x")
    bad = rast.If(S, rast.BoolLit(S, True), rast.Block(S, [], rast.IntLit(S, 1)), None)
    def arm(body, guard=None):
        return rast.MatchArm(S, rast.WildcardPattern(S), guard, body)
    tree = {
        "binop_left": rast.BinOp(S, "+", bad, x),
        "binop_right": rast.BinOp(S, "+", x, bad),
        "unary": rast.UnaryOp(S, "-", bad),
        "call_arg": rast.Call(S, x, [x, bad]),
        "call_func": rast.Call(S, bad, []),
        "method_receiver": rast.MethodCall(S, bad, "m", []),
        "method_arg": rast.MethodCall(S, x, "m", [bad]),
        "index_base": rast.Index(S, bad, x),
        "index_index": rast.Index(S, x, bad),
        "field_base": rast.Field(S, bad, "v"),
        "cast": rast.Cast(S, bad, rast.NamedType(S, "i64")),
        "struct_field": rast.StructLit(S, "S", [("v", bad)]),
        "array_elem": rast.ArrayLit(S, [x, bad]),
        "tuple_elem": rast.TupleLit(S, [bad]),
        "grouped": rast.Call(S, x, [rast.Grouped(S, bad)]),
        "try": rast.TryOp(S, bad),
        "interp": rast.InterpString(S, ["", ""], [bad]),
        "match_scrutinee": rast.Match(S, bad, [arm(x)]),
        "match_guard": rast.Match(S, x, [arm(x, bad)]),
        "if_cond": rast.If(S, bad, rast.Block(S, [], None), None),
        "return_expr": rast.ReturnExpr(S, bad),
        "assign_expr_value": rast.AssignExpr(S, x, bad),
        "slice_start": rast.SliceExpr(S, x, bad, None),
    }[shape]
    found = LLVMEmitter._find_valueless_if(tree, consumed=False)
    assert found is bad, f"{shape}: operand walk did not reach the `if`"


@pytest.mark.unit
@pytest.mark.parametrize("shape", ["expr_stmt_if", "block_stmts", "lambda", "closure"])
def test_walker_does_not_flag_unconsumed_positions(shape):
    """Statement `if`, `Block.stmts`, lambda and closure bodies stay unwalked."""
    import ritz_ast as rast
    from emitter_llvmlite import LLVMEmitter

    S = None  # spans are irrelevant to the walk

    bad = rast.If(S, rast.BoolLit(S, True), rast.Block(S, [], rast.IntLit(S, 1)), None)
    def call_of(e):
        return rast.Call(S, rast.Ident(S, "f"), [e])
    tree = {
        "expr_stmt_if": bad,
        "block_stmts": call_of(rast.Block(S, 
            [rast.ExprStmt(S, call_of(bad))], rast.IntLit(S, 1))),
        "lambda": call_of(rast.Lambda(S, [], None, call_of(bad))),
        "closure": call_of(rast.Closure(S, [], call_of(bad))),
    }[shape]
    assert LLVMEmitter._find_valueless_if(tree, consumed=False) is None


@pytest.mark.unit
def test_operand_diagnostic_points_at_the_if(tmp_path):
    """Line 2 holds `5 + if ...`; the `if` itself is the located node."""
    rc, output, _ = _compile(tmp_path, OPERAND_POSITIONS["binop_right"])
    assert rc != 0
    assert re.search(r"unit\.ritz:2:\d+:", output), output


# ---------------------------------------------------------------------------
# Controls. Every one of these is green BEFORE the fix and must stay green.
# ---------------------------------------------------------------------------

@pytest.mark.integration
def test_statement_match_whose_arm_ends_in_an_else_less_if_still_runs(tmp_path):
    """Verbatim shape of angelo hinting/interpreter.ritz:295 — v4's undoing.

    The match is a statement; nothing consumes its arms' values, so the
    else-less `if` closing an arm is an ordinary guard. v4 rejected it from
    inside `_emit_expr` and turned GitHub's build-all red. angelo is outside
    the regression corpus, so ci-local could not see it; this test can.
    """
    assert _run(tmp_path, (
        "fn g(p: *i32, c: i32)\n"
        "    match c\n"
        "        1 =>\n"
        "            if c == 1\n"
        "                *p = 1\n"
        "        _ => *p = 2\n"
        "fn main() -> i32\n"
        "    var v: i32 = 0\n"
        "    g(@v, 1)\n"
        "    return v\n"
    )) == 1


@pytest.mark.integration
def test_else_ful_if_as_operand_and_argument_still_runs(tmp_path):
    """#1435 control: the total forms in operand position keep their value."""
    assert _run(tmp_path, (
        "fn id(v: i32) -> i32\n"
        "    return v\n"
        "fn main() -> i32\n"
        "    let c: i32 = 1\n"
        "    let x = 5 + if c == 1\n"
        "        1\n"
        "    else\n"
        "        0\n"
        "    return x + id(if c == 1\n"
        "        10\n"
        "    else\n"
        "        0\n"
        "    )\n"
    )) == 16


@pytest.mark.unit
def test_else_less_if_statement_inside_an_argument_arm_compiles(tmp_path):
    """#1435 control: the operand walk never enters `Block.stmts`.

    The argument is a total if/else; inside its then-arm an else-less `if`
    is a statement, and the arm's value is the tail `1`.
    """
    rc, output, _ = _compile(tmp_path, (
        "fn id(v: i32) -> i32\n"
        "    return v\n"
        "fn pick(c: i32, d: i32) -> i32\n"
        "    var r: i32 = 0\n"
        "    return id(if c == 1\n"
        "        if d == 1\n"
        "            r = 5\n"
        "        1\n"
        "    else\n"
        "        2\n"
        "    )\n"
    ))
    assert rc == 0, f"walked into a block's statements:\n{output}"


@pytest.mark.unit
def test_statement_if_whose_condition_is_a_call_still_compiles(tmp_path):
    """#1435 control: walking a statement `if` must not flag the `if` itself."""
    rc, output, _ = _compile(tmp_path, (
        "fn id(v: i32) -> i32\n"
        "    return v\n"
        "fn g(p: *i32, c: i32)\n"
        "    if id(c) == 1\n"
        "        *p = id(1)\n"
        "    *p = 2\n"
    ))
    assert rc == 0, f"rejected a statement if with calls in it:\n{output}"


@pytest.mark.unit
def test_statement_match_arm_guard_in_a_method_still_compiles(tmp_path):
    """angelo tests.ritz:727's variant: the match is a method body's tail."""
    rc, output, _ = _compile(tmp_path, (
        "struct S\n"
        "    v: i32\n"
        "impl S\n"
        "    fn step(self:&, c: i32)\n"
        "        match c\n"
        "            1 =>\n"
        "                if self.v == 0\n"
        "                    self.v = 1\n"
        "            _ => pass\n"
    ))
    assert rc == 0, f"rejected a statement match whose arm ends in a guard:\n{output}"


@pytest.mark.unit
def test_else_less_if_nested_in_a_statement_block_of_a_value_arm_compiles(tmp_path):
    """The walk follows block TAILS only, never a block's statements.

    Here the else-less `if` is a statement inside the then-arm, and the arm's
    value is its tail `1`. Walking `Block.stmts` would reject this.
    """
    rc, output, _ = _compile(tmp_path, (
        "fn pick(c: i32, d: i32) -> i32\n"
        "    var r: i32 = 0\n"
        "    let x = if c == 1\n"
        "        if d == 1\n"
        "            r = 5\n"
        "        1\n"
        "    else\n"
        "        2\n"
        "    return x + r\n"
    ))
    assert rc == 0, f"rejected an else-less if statement inside a value arm:\n{output}"


@pytest.mark.unit
def test_else_ful_if_in_value_position_still_compiles(tmp_path):
    """The form that was always correct: both arms, so there is a phi."""
    rc, output, ir_text = _compile(tmp_path, (
        "fn pick(c: i32) -> i32\n"
        "    let x = if c == 1\n"
        "        1\n"
        "    else\n"
        "        2\n"
        "    return x\n"
    ))
    assert rc == 0, f"rejected a well-formed if-expression:\n{output}"
    assert "phi " in ir_text, f"no phi node merging the arms:\n{ir_text}"


@pytest.mark.unit
def test_else_less_if_as_a_statement_still_compiles(tmp_path):
    """The overwhelmingly common case, and the one a careless fix breaks.

    Statement position also gets `None` back from `_emit_if`. It is correct
    there. If this goes red, the check has been put in `_emit_if` instead of
    at the value-position caller.
    """
    rc, output, ir_text = _compile(tmp_path, (
        "fn pick(c: i32) -> i32\n"
        "    var r: i32 = 0\n"
        "    if c == 1\n"
        "        r = 1\n"
        "    return r\n"
    ))
    assert rc == 0, f"rejected an else-less if used as a statement:\n{output}"
    assert "if.then" in ir_text
    assert "phi " not in ir_text, "a statement-position if must not emit a phi"


@pytest.mark.unit
def test_else_less_if_statement_containing_a_return_still_compiles(tmp_path):
    """Early-return guards are else-less ifs whose arm terminates."""
    rc, output, _ = _compile(tmp_path, (
        "fn pick(c: i32) -> i32\n"
        "    if c == 1\n"
        "        return 1\n"
        "    return 2\n"
    ))
    assert rc == 0, f"rejected an early-return guard:\n{output}"


@pytest.mark.unit
def test_procedure_whose_tail_is_an_else_less_if_still_compiles(tmp_path):
    """A procedure's trailing expression runs for effect, so it needs no value.

    The parser puts a block's last `if` into `body.expr` rather than
    `body.stmts`, so a procedure ending in an ordinary guard arrives at the
    same place a value-position `if` does. Only this site knows whether the
    value is wanted — the same distinction AGAST #1321 had to make for a
    trailing `match`.

    The first version of the #1406 fix rejected this, which would have redded
    every procedure in the corpus that ends in a guard.
    """
    rc, output, _ = _compile(tmp_path, (
        "fn g(p: *i32, c: i32)\n"
        "    if c == 1\n"
        "        *p = 1\n"
    ))
    assert rc == 0, (
        f"rejected a procedure ending in an else-less if statement:\n{output}"
    )


@pytest.mark.unit
def test_procedure_whose_tail_is_an_if_else_of_assignments_still_compiles(tmp_path):
    """Verbatim shape of `ritzlib/hashmap.ritz:210`.

    An if/else whose arms are assignments, as the last thing in a procedure.
    There is no phi — the arms produce nothing to merge — but nothing wants a
    value either.

    The second version of the #1406 fix carved out only *else-less* trailing
    ifs in procedures, so this compiled clean through pytest and then took
    the bootstrap red at `FATAL: ritzlib hashmap compile failed`. pytest is
    not the corpus.
    """
    rc, output, _ = _compile(tmp_path, (
        "struct E\n"
        "    state: i64\n"
        "    value: i64\n"
        "fn ins(e: *E, value: i64)\n"
        "    if e.state == 1\n"
        "        e.value = value\n"
        "    else\n"
        "        e.state = 1\n"
        "        e.value = value\n"
    ))
    assert rc == 0, (
        f"rejected a procedure ending in an if/else of assignments:\n{output}"
    )


@pytest.mark.unit
def test_declared_return_type_tailing_a_valueless_if_is_unchanged(tmp_path):
    """Scope boundary, pinned deliberately: this is NOT #1406's defect.

    A function that declares `-> i64` and whose tail is an else-less `if`
    with no value returns an implicit zero. That is a missing return value,
    and it is arguably its own defect — but it is a *different* one, it
    exists in the corpus today, and `examples/tier1_basics/91_loop_trailing_expr`
    is built on it:

        fn f_nested(n: i64) -> i64
            var i: i64 = 0
            if n > 0
                while i < n
                    i = i + 1

    The third version of the #1406 fix rejected this and redded that example
    plus `tier2_stdlib_15_cut`. Widening a fix until the corpus goes red is a
    scope increase wearing a bug fix's clothes, so the behaviour is preserved
    here and tracked on its own ticket. If a later change makes this an error
    ON PURPOSE, this test should be replaced — not deleted quietly.
    """
    rc, output, _ = _compile(tmp_path, (
        "fn f_nested(n: i64) -> i64\n"
        "    var i: i64 = 0\n"
        "    if n > 0\n"
        "        while i < n\n"
        "            i = i + 1\n"
    ))
    assert rc == 0, (
        "a declared-return fn tailing a valueless if is out of #1406's scope "
        f"and must still compile:\n{output}"
    )


@pytest.mark.unit
def test_valueless_tail_if_in_a_pointer_returning_fn_emits_valid_ir(tmp_path):
    """The implicit zero must be CONVERTED to the return type, not typed at it.

    `ir.Constant(ptr_type, 0)` prints as `ret %"struct.E"* 0`, which clang
    rejects: "integer constant must have integer type". The zero has to go
    through `_convert_type`, which is what the pre-#1406 path did.

    Verbatim shape of `ritz1/src/ast_helpers.ritz`. The fourth version of the
    #1406 fix got this wrong and built a ritz1 that could not compile itself
    — after 862 pytest tests, 199/199 doc blocks and Stages 1-3 all passed.
    Only the self-hosting bootstrap in Stage 4 could see it, which is the
    argument for the differential suite existing at all.
    """
    rc, output, ir_text = _compile(tmp_path, (
        "struct E\n"
        "    v: i64\n"
        "fn touch(e: *E, c: i64) -> *E\n"
        "    if c == 1\n"
        "        e.v = 1\n"
    ))
    assert rc == 0, f"pointer-returning fn with a valueless tail if:\n{output}"
    assert ir_text is not None
    assert not re.search(r'ret %"[^"]+"\* 0', ir_text), (
        "emitted `ret %struct* 0` — an integer constant typed as a pointer, "
        f"which clang rejects:\n{ir_text}"
    )


@pytest.mark.unit
def test_if_whose_arms_both_return_still_compiles(tmp_path):
    """Both arms terminate, so the merge point is unreachable.

    `_emit_if` returns `None` here too — not because there is no value, but
    because control never arrives anywhere that could want one. There is
    nothing to diagnose: the `if` is total and every path has already
    returned.

    This is the shape `docs/STYLE.md` teaches, and the first version of the
    #1406 fix rejected it, which the doc-example gate caught at 195/197. It
    is the reason the check is conditioned on the merge point being
    reachable rather than merely on the absence of a phi.
    """
    rc, output, _ = _compile(tmp_path, (
        "fn example(x: i32) -> i32\n"
        "    if x > 0\n"
        "        let result: i32 = x * 2\n"
        "        return result\n"
        "    else\n"
        "        return 0\n"
    ))
    assert rc == 0, f"rejected an if whose arms both return:\n{output}"


@pytest.mark.unit
def test_else_less_if_whose_arm_returns_still_compiles(tmp_path):
    """The guard shape, as a function's whole body.

    The `then` arm returns; the implicit fall-through path does not, so the
    function is missing a return — but that is a different diagnostic's job,
    not #1406's. What matters here is that it is not rejected AS a
    value-position if-expression.
    """
    rc, output, _ = _compile(tmp_path, (
        "fn example(x: i32) -> i32\n"
        "    if x > 0\n"
        "        return 1\n"
        "    return 0\n"
    ))
    assert rc == 0, f"rejected an early-return guard:\n{output}"


@pytest.mark.unit
def test_else_if_chain_terminating_in_else_still_compiles(tmp_path):
    """A chain is nested ifs; only the innermost `else` makes it total."""
    rc, output, ir_text = _compile(tmp_path, (
        "fn pick(c: i32) -> i32\n"
        "    let x = if c == 1\n"
        "        1\n"
        "    else if c == 2\n"
        "        2\n"
        "    else\n"
        "        3\n"
        "    return x\n"
    ))
    assert rc == 0, f"rejected a total if/else-if/else chain:\n{output}"
    assert "phi " in ir_text
