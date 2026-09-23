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

    if.then:
      br label %"if.end"              # EMPTY — the 1 is never materialised
    if.end:
      ret i32 0                       # folded to zero, no phi, no store of 1

WHY REJECTION RATHER THAN A ZERO PHI

The ticket forbids the tempting fix of synthesising a zero (or undef) for the
missing arm. That would keep every one of these programs compiling and merely
make the wrong answer deliberate. `if c` with no `else` has no value on the
path where `c` is false; there is no value to name, so the program is asking
for something that does not exist. The only answer that cannot be silently
wrong is to refuse it, at the source location.

WHY THE STATEMENT-POSITION CONTROLS ARE LOAD-BEARING

An else-less `if` used as a *statement* is ordinary, correct, extremely common
code, and it also reaches `_emit_if` and also gets `None` back. The difference
is the route: statement position is dispatched at `_emit_stmt`'s `ExprStmt`
branch straight to `_emit_if`, bypassing `_emit_expr` entirely. A fix that
rejects in `_emit_if` would red the entire corpus. The controls below fail if
anyone moves the check there.
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


# The value positions an else-less `if` can reach: the ones that BIND the
# result. Every one compiled clean and evaluated to 0 before the fix.
#
# A function tail (`fn pick(c: i32) -> i32` ending in an else-less `if`) looks
# like a fourth, and was listed here at first — but the corpus builds on that
# shape and rejecting it reds two examples. It is a missing return value, a
# different defect, and it has its own test below:
# test_declared_return_type_tailing_a_valueless_if_is_unchanged.
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


@pytest.mark.unit
@pytest.mark.parametrize("position", sorted(VALUE_POSITIONS))
def test_rejection_never_manufactures_a_zero(tmp_path, position):
    """No IR may be emitted that stores or returns a fabricated 0.

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
    # None of these sources contains a legitimate zero, so any zero here
    # is manufactured. Both spellings matter: `let`/implicit-return fold it
    # into the `ret`, while `var` stores it into the binding's slot.
    for spelling in ("ret i32 0", "store i32 0"):
        assert spelling not in body, (
            f"{position}: emitted a fabricated zero (`{spelling}`):\n{body}"
        )


@pytest.mark.unit
def test_diagnostic_is_located_and_not_a_python_traceback(tmp_path):
    """`file:line:col:` — the same shape every other user error uses.

    An unlocated error in a 3000-line file is only marginally better than a
    wrong answer, and a raw traceback reads as a compiler crash rather than
    as something the author can fix.
    """
    rc, output, _ = _compile(tmp_path, VALUE_POSITIONS["let_inferred"])
    assert rc != 0
    assert "Traceback (most recent call last)" not in output, (
        f"reported as a Python traceback:\n{output}"
    )
    assert re.search(r"unit\.ritz:\d+:\d+:", output), (
        f"diagnostic carries no source location:\n{output}"
    )
    assert re.search(r"else", output, re.I), (
        f"diagnostic does not say what is missing:\n{output}"
    )


# ---------------------------------------------------------------------------
# Controls. Every one of these is green BEFORE the fix and must stay green.
# ---------------------------------------------------------------------------

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
