#!/usr/bin/env python3
"""ritz1 rejects implicit narrowing exactly where ritz0 does (AGAST #1364, #1446).

#1364 decided (option b) that `let n: i32 = big()`, with `big() -> i64`, is a
compile error and the programmer writes `big() as i32`. #1393 implemented that
in ritz0 with a "provably lossless" exemption (constants that fit, `e & K`
masks, if/match of those). ritz1 kept compiling the narrowing silently, so the
two compilers disagreed about which programs are valid -- and the regression
suite could not see it, because it only feeds ritz1 programs ritz0 accepts.

This test is the differential the regression suite lacks: it feeds BOTH
compilers every case in ritz0's own tables (test_implicit_narrowing.py, the
single source of truth for the rule) and requires the same verdict. Taking
the tables from that file, rather than copying them, means a future change to
the rule cannot silently skip ritz1.
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RITZ_ROOT = HERE.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

_spec = importlib.util.spec_from_file_location(
    "_ritz0_narrowing_rule", HERE / "test_implicit_narrowing.py")
RULE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RULE)

# ritz1's grammar has no `if c then a else b` EXPRESSION, so these cases cannot
# reach the narrowing check at all. They are not skipped silently: the test
# below requires ritz1 to reject them with a parse error, so the day ritz1
# learns the construct this list goes red and the cases join the parity run.
RITZ1_CANNOT_PARSE = {"if_bounded_by_comparison", "if_constant_arms"}


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    """Bring RITZ1_BIN up to date; a stale binary would test the old emitter."""
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"], cwd=RITZ_ROOT, env=env,
        capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(f"could not build ritz1:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}")
    return RITZ1_BIN


def _ritz1(ritz1_bin, tmp_path, body):
    src = tmp_path / "unit.ritz"
    src.write_text(RULE.PRELUDE + body)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [str(ritz1_bin), str(src), "-o", str(tmp_path / "unit.ll")],
        cwd=tmp_path, capture_output=True, text=True, env=env, timeout=300)


def _parity_cases(table):
    return sorted(name for name in table if name not in RITZ1_CANNOT_PARSE)


@pytest.mark.integration
@pytest.mark.parametrize("name", _parity_cases(RULE.REJECTED))
def test_ritz1_rejects_what_ritz0_rejects(ritz1_bin, tmp_path, name):
    stmt = RULE.REJECTED[name]
    r = _ritz1(ritz1_bin, tmp_path, RULE._fn(stmt))
    assert r.returncode != 0, (
        f"{name}: ritz1 compiled `{stmt.splitlines()[0]}`, which ritz0 rejects "
        f"as an unprovable implicit narrowing")
    assert "implicit narrowing:" in r.stderr, (
        f"{name}: ritz1 rejected it, but not with the narrowing diagnostic:\n"
        f"{r.stderr[-1500:]}")


@pytest.mark.integration
@pytest.mark.parametrize("name", _parity_cases(RULE.ACCEPTED))
def test_ritz1_accepts_what_ritz0_accepts(ritz1_bin, tmp_path, name):
    """The load-bearing controls: without them, rejecting everything passes."""
    stmt = RULE.ACCEPTED[name]
    r = _ritz1(ritz1_bin, tmp_path, RULE._fn(stmt))
    assert r.returncode == 0, (
        f"{name}: ritz1 rejected `{stmt.splitlines()[0]}`, which ritz0 accepts:\n"
        f"{r.stderr[-1500:]}")
    assert "implicit narrowing" not in r.stderr


@pytest.mark.integration
def test_ritz1_diagnostic_names_both_types_suggests_as_and_is_located(ritz1_bin, tmp_path):
    r = _ritz1(ritz1_bin, tmp_path, RULE._fn("let n: i32 = big()"))
    assert r.returncode != 0
    err = r.stderr
    assert "`n`" in err, err[-1500:]
    assert "`i32`" in err and "`i64`" in err, err[-1500:]
    assert "as i32" in err, err[-1500:]
    assert f"unit.ritz:{RULE.PRELUDE_LINES + 2}:" in err, err[-1500:]


@pytest.mark.integration
def test_ritz1_rejection_writes_no_output(ritz1_bin, tmp_path):
    """A diagnostic that still leaves a .ll behind lets a build link it anyway."""
    r = _ritz1(ritz1_bin, tmp_path, RULE._fn("let n: i32 = big()"))
    assert r.returncode != 0
    assert not (tmp_path / "unit.ll").exists()


# Shapes ritz0's tables do not cover but ritz1 reaches by a different route:
# its unified i64 value model means the narrowing is decided from Ritz types,
# not from LLVM register widths, so each source of a type gets a case.
RITZ1_EXTRA_REJECTED = {
    "i64_param":          ("let n: i32 = w", "x: i32, o: Order, w: i64"),
    "i64_annotated_local": ("let a: i64 = five()\n    let n: u16 = a", None),
    "u64_call_into_u32":  ("let n: u32 = five() as u64", None),
    "binary_wider_right": ("let n: i32 = x + five()", None),
    "unary_neg_of_i64":   ("let n: i32 = 0 - five()", None),
    # ritz0's table has the negative mask on the RIGHT only; a mask is
    # accepted from either side, so the guard is checked on both.
    "negative_mask_on_left": ("let n: i8 = (0 - 1) & big()", None),
    # The literal arms adopt the i16 arm's type, which is wider than i8.
    "match_i16_arm_into_i8": ("let n: i8 = match o\n"
                              "        Gray => w\n"
                              "        RGB => 1\n"
                              "        BGR => 2", "x: i32, o: Order, w: i16"),
}
RITZ1_EXTRA_ACCEPTED = {
    # An UNANNOTATED local: ritz1 records it as i64 whatever its initialiser,
    # and ritz0 infers i32 here. A check that trusted ritz1's default would
    # reject valid code -- the false positive this guards against.
    "unannotated_local_of_i32": ("let a = x\n    let n: i32 = a", None),
    "literal_operand_adopts":   ("let n: i32 = x + 1", None),
    "comparison_is_bool":       ("let n: bool = five() > 3", None),
    "same_width_param":         ("let n: i32 = x", None),
    "i8_into_i32":              ("let n: i32 = 5 as i8", None),
    # Found by the matrix (test_issue_symbol_lookup_scaling): a literal match
    # arm takes the type of the other arms in ritz0, it is not an i64.  Both
    # orders, because a fold that met the literals first once got this wrong.
    "match_literal_arm_adopts": ("let n: i32 = match o\n"
                                 "        Gray => x\n"
                                 "        RGB => 0\n"
                                 "        BGR => 1", None),
    "match_literal_arms_first": ("let n: i32 = match o\n"
                                 "        Gray => 0\n"
                                 "        RGB => 1\n"
                                 "        BGR => x", None),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_EXTRA_REJECTED))
def test_ritz1_extra_shapes_rejected_by_both(ritz1_bin, tmp_path, name):
    stmt, params = RITZ1_EXTRA_REJECTED[name]
    body = RULE._fn(stmt, params) if params else RULE._fn(stmt)
    r0 = RULE._compile(tmp_path, body)
    assert r0.returncode != 0 and "implicit narrowing:" in r0.stderr, (
        f"{name}: ritz0 is the oracle and accepted it -- fix the case:\n{r0.stderr[-800:]}")
    r1 = _ritz1(ritz1_bin, tmp_path, body)
    assert r1.returncode != 0 and "implicit narrowing:" in r1.stderr, (
        f"{name}: ritz1 did not reject `{stmt}`:\n{r1.stderr[-1500:]}")


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_EXTRA_ACCEPTED))
def test_ritz1_extra_shapes_accepted_by_both(ritz1_bin, tmp_path, name):
    stmt, params = RITZ1_EXTRA_ACCEPTED[name]
    body = RULE._fn(stmt, params) if params else RULE._fn(stmt)
    r0 = RULE._compile(tmp_path, body)
    assert r0.returncode == 0, (
        f"{name}: ritz0 is the oracle and rejected it -- fix the case:\n{r0.stderr[-800:]}")
    r1 = _ritz1(ritz1_bin, tmp_path, body)
    assert r1.returncode == 0, f"{name}: ritz1 rejected `{stmt}`:\n{r1.stderr[-1500:]}"


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(RITZ1_CANNOT_PARSE))
def test_ritz1_still_cannot_parse_if_expressions(ritz1_bin, tmp_path, name):
    table = RULE.REJECTED if name in RULE.REJECTED else RULE.ACCEPTED
    r = _ritz1(ritz1_bin, tmp_path, RULE._fn(table[name]))
    assert r.returncode != 0 and "implicit narrowing" not in r.stderr, (
        f"{name}: ritz1 now gets past the parser -- remove it from "
        f"RITZ1_CANNOT_PARSE so it joins the parity run:\n{r.stderr[-800:]}")
