#!/usr/bin/env python3
"""The expect-error differential: ritz1 rejects what ritz0 rejects, where ritz0 does.

Self-hosting goal #3 is "ritz1 rejects everything ritz0 rejects, with the same
diagnostics".  Until this file, nothing checked the general claim.  The two
named cases had their own differentials -- test_ritz1_implicit_narrowing.py
(#1446 narrowing) and test_if_expression_requires_else.py (#1406/#1429
else-less if) -- but scripts/regression.sh and the matrix feed ritz1 only
programs ritz0 ACCEPTS.  A program ritz0 rejects and ritz1 accepts was
invisible unless someone wrote a dedicated differential.

This file is the corpus: (program, expected diagnostic) rows compiled by
ritz0, ritz1 and ritz1_selfhosted, with parity asserted on the verdict and
the diagnostic's ``unit.ritz:line:col``.

WHAT "PARITY" MEANS HERE (AGAST #3928)

The verdict must be identical: every compiler refuses every row.  The
diagnostic must point at the same ``line:col`` as ritz0.  The WORDING is
allowed to differ for the ritz1 family -- its front end is not ritz0's and
#3928 already decided a ritz1 refusal is judged by meaning, not by ritz0's
sentence.  A non-gap row still pins a rule token (``implicit narrowing:``,
``no `else` ``) so a rejection for an unrelated reason cannot pass; a known
gap pins only "refused, with a located diagnostic", exactly #3928's floor.

This is deliberately NOT the doc-example rule: tools/check_doc_examples.py
judges expect-error fences in prose, where ritz1 has no reason to reproduce a
parser message.  Here the rule being differentialled is ritz0's own, and the
position is the part that must agree.

KNOWN GAPS

Seeding found a real disagreement, which is this gate doing its job: for 14
of the 16 else-less-if shapes ritz1 (and ritz1_selfhosted, which agrees with
ritz1) refuses at a parser position rather than at ritz0's value position.
They are pinned as ``gap=4543`` rows -- the verdict and the rule still have
to hold; the position mismatch is the ticket.  The pin is strict: if the
ritz1 family starts pointing where ritz0 does, this file fails until the gap
entry is dropped (see ``_row_failures``).  The rest of that ticket tracks the
fix; do not relax it by deleting the row.

ADDING A RULE

Every new reject rule adds rows here.  The narrowing and else-less-if tables
are imported from their single sources of truth, and the coverage tests below
fail when a row appears there and is not in this corpus, so a rule change
cannot silently skip the parity run.  Measure the expected ``line:col`` with
ritz0 (the oracle) on the row's program and record it in the row; the ritz1
family must match it.

Wiring: this file is under ritz0/tests/, so the gate's "ritz0 unit tests"
step runs it.  It needs no ritz1 build of its own: ``ritz1_bin`` is the
session's binary and ``ritz1_selfhosted`` is built by the gate's bootstrap
step.  ``scripts/test-regression-reject-parity.sh`` proves the test goes red on an
injected divergence (``RITZ_REJECT_PARITY_INJECT``) and is itself picked up by
the "Regression harness self-tests" gate step.
"""

import importlib.util
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]          # projects/ritz/ritz0
RITZ_ROOT = HERE.parent                             # projects/ritz
POSITION_RE = re.compile(r"unit\.ritz:(\d+):(\d+):")
COMPILERS = ("ritz0", "ritz1", "ritz1_selfhosted")
CRASH = "Traceback (most recent call last)"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The single sources of truth for the two rules the ticket names.
NARROWING = _load("_reject_parity_narrowing", HERE / "tests" / "test_implicit_narrowing.py")
ELSE = _load("_reject_parity_else", HERE / "tests" / "test_if_expression_requires_else.py")


@dataclass(frozen=True)
class Row:
    """One expect-error row.

    ``message`` is the rule token every refusal must mention (None: #3928's
    floor, "a located refusal", for a known gap).  ``at`` is ritz0's
    ``(line, col)``, the parity target.  ``oracle_message`` is what ritz0
    itself must say (defaults to ``message``).  ``gap`` names the AGAST ticket
    for a documented position disagreement.
    """

    program: str
    message: str | None
    at: tuple[int, int]
    oracle_message: str | None = None
    gap: int | None = None


# Every narrowing row in #1446's REJECTED table.  The statement is line 2 of
# the wrapper function, after the prelude, and starts at column 5 (`let`/`var`).
NARROWING_AT = (NARROWING.PRELUDE_LINES + 2, 5)

CORPUS: dict[str, Row] = {}
for _name, _stmt in NARROWING.REJECTED.items():
    CORPUS[f"narrowing/{_name}"] = Row(
        program=NARROWING.PRELUDE + NARROWING._fn(_stmt),
        message="implicit narrowing:",
        at=NARROWING_AT,
    )

# #1406/#1429/#1435's else-less-if shapes.  Positions measured with ritz0 at
# 0ae161b9.  All three compilers now agree on `line:col` for every row: the
# 14 rows whose ritz1-family refusal used to land elsewhere were AGAST #4543,
# fixed in ritz1's front end (it parses the else-less block `if` and Sema
# refuses it at the `if`, as ritz0 does).  Any new disagreement reintroduces a
# `gap` here.  A new entry without an entry in this table fails
# test_every_else_less_if_row_is_in_the_corpus below, which is the point.
ELSE_AT: dict[str, tuple[tuple[int, int], int | None]] = {
    "else/value/assignment": ((3, 9), None),
    "else/value/inside_if_arm": ((3, 9), None),
    "else/value/inside_match_arm": ((4, 13), None),
    "else/value/let_annotated": ((2, 18), None),
    "else/value/let_inferred": ((2, 13), None),
    "else/value/open_else_if_chain": ((4, 10), None),
    "else/value/return_value": ((2, 12), None),
    "else/value/var_initialiser": ((2, 13), None),
    "else/operand/binop_right": ((2, 17), None),
    "else/operand/binop_right_in_return": ((2, 16), None),
    "else/operand/operand_in_a_procedure_tail": ((2, 15), None),
    "else/operand/operand_in_a_statement_if_arm": ((3, 19), None),
    "else/operand/operand_in_a_while_body_tail": ((3, 19), None),
    "else/operand/operand_inside_a_value_arm": ((3, 13), None),
    "else/operand/operand_of_an_expr_stmt": ((2, 15), None),
    "else/operand/unary_operand": ((2, 14), None),
}
for _label, _table in (("value", ELSE.VALUE_POSITIONS), ("operand", ELSE.OPERAND_POSITIONS)):
    for _name, _program in _table.items():
        _rid = f"else/{_label}/{_name}"
        if _rid not in ELSE_AT:
            continue  # the coverage test names it
        _at, _gap = ELSE_AT[_rid]
        CORPUS[_rid] = Row(
            program=_program,
            # A gap row pins only ritz1's floor (#3928): its parser message
            # need not mention the rule it refused for.
            message=None if _gap else "no `else`",
            at=_at,
            oracle_message="no `else`",
            gap=_gap,
        )


def _first_diagnostic(output: str) -> tuple[int, int] | None:
    match = POSITION_RE.search(output)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _refusal_wrong(compiler: str, row: Row, returncode: int, output: str, *,
                   position: bool) -> str | None:
    """Why ``compiler`` does not satisfy ``row``, or None.

    ``position=False`` is a known-gap row: the verdict, a diagnostic and
    ritz0's rule token are still required; the position is not.
    """
    if returncode == 0:
        return f"{compiler} ACCEPTED it; ritz0 rejects it"
    if returncode < 0 or not output.strip() or CRASH in output:
        return (f"{compiler} refused without a diagnostic (exit {returncode}): "
                f"a crash, not a refusal")
    at = _first_diagnostic(output)
    if at is None:
        return f"{compiler}'s refusal is not located at unit.ritz:line:col"
    token = row.message
    if compiler == "ritz0":
        token = row.oracle_message or row.message
    if token is not None and token not in output:
        return f"{compiler}'s refusal does not mention {token!r}"
    if position and at != row.at:
        return (f"{compiler} points at unit.ritz:{at[0]}:{at[1]}, "
                f"ritz0 at unit.ritz:{row.at[0]}:{row.at[1]}")
    return None


def _row_failures(rid: str, row: Row, results: dict[str, tuple[int, str]]) -> list[str]:
    """Every reason ``results`` ({compiler: (rc, output)}) fails ``row``."""
    failures = []
    for compiler in COMPILERS:
        returncode, output = results[compiler]
        # A gap excuses only the ritz1 family's position.  The verdict is
        # never excused: ritz1 accepting a row is always a failure.
        wrong = _refusal_wrong(compiler, row, returncode, output,
                               position=row.gap is None or compiler == "ritz0")
        if wrong:
            failures.append(f"{rid}: {wrong}")
    if row.gap:
        # The two self-compiled twins must still agree with each other; a
        # divergence between them is a self-hosting bug the gap does not
        # cover (regression.sh Stage 5's invariant, one compiler earlier).
        at1 = _first_diagnostic(results["ritz1"][1])
        at2 = _first_diagnostic(results["ritz1_selfhosted"][1])
        if at1 is not None and at2 is not None and at1 != at2:
            failures.append(
                f"{rid}: ritz1 points at unit.ritz:{at1[0]}:{at1[1]}, "
                f"ritz1_selfhosted at unit.ritz:{at2[0]}:{at2[1]}")
        # Strict pin: the entry must go when the gap closes.
        if all(_first_diagnostic(results[c][1]) == row.at
               for c in ("ritz1", "ritz1_selfhosted")):
            failures.append(
                f"{rid}: passes, but is listed as a gap of AGAST #{row.gap}: "
                f"drop the entry")
    return failures


def _compile_all(row: Row, rid: str, work: Path, binaries: dict[str, Path], run0):
    """Compile one row with all three compilers; {name: (rc, stdout+stderr)}."""
    here = work / re.sub(r"\W+", "_", rid)[:80]
    here.mkdir(parents=True, exist_ok=True)
    src = here / "unit.ritz"
    src.write_text(row.program)
    ll = here / "unit.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    ritz0 = run0([str(src), "-o", str(ll), "--no-runtime"],
                 cwd=here, env=env, timeout=300)
    results = {"ritz0": (ritz0.returncode, ritz0.stdout + ritz0.stderr)}
    for name in ("ritz1", "ritz1_selfhosted"):
        proc = subprocess.run(
            [str(binaries[name]), str(src), "-o", str(ll)],
            cwd=here, capture_output=True, text=True, env=env, timeout=300,
            check=False)
        results[name] = (proc.returncode, proc.stdout + proc.stderr)
    return results


def _injection_failures(spec: str) -> list[str]:
    """Synthetic divergence for scripts/test-regression-reject-parity.sh (no compilers).

    ``spec`` is a comma-separated list of ``<compiler>:accept|position``.  It
    feeds the same ``_row_failures`` the real run uses, so the test goes red
    exactly where a real disagreement would.  The self-test does not need a
    ritz1 build, which is why the harness self-tests step (before bootstrap)
    can run it.
    """
    failures = []
    real = [(rid, row) for rid, row in CORPUS.items() if row.gap is None]
    entries = [entry for entry in spec.split(",") if entry]
    if not entries:
        pytest.fail(f"empty RITZ_REJECT_PARITY_INJECT={spec!r}")
    for entry in entries:
        compiler, _, mode = entry.partition(":")
        if compiler not in COMPILERS or mode not in ("accept", "position"):
            pytest.fail(f"bad RITZ_REJECT_PARITY_INJECT entry {entry!r}; "
                        f"want <compiler>:accept|position")
        for rid, row in real[:2]:
            line, col = row.at
            good = f"unit.ritz:{line}:{col}: {row.oracle_message or row.message}\n"
            results = {name: (1, good) for name in COMPILERS}
            if mode == "accept":
                results[compiler] = (0, "")
            else:
                results[compiler] = (
                    1, f"unit.ritz:{line}:{col + 1}: {row.message}\n")
            failures += _row_failures(rid, row, results)
    if not failures:
        pytest.fail(f"RITZ_REJECT_PARITY_INJECT={spec!r} produced no "
                    f"disagreement: the injection self-test is broken")
    return failures


@pytest.mark.integration
def test_ritz1_family_rejects_where_ritz0_rejects(request, tmp_path):
    """Every corpus row is refused by all three compilers at ritz0's position."""
    inject = os.environ.get("RITZ_REJECT_PARITY_INJECT")
    if inject:
        failures = _injection_failures(inject)
    else:
        # Resolved lazily so the injected self-test does not build ritz1.
        binaries = {
            "ritz1": request.getfixturevalue("ritz1_bin"),
            "ritz1_selfhosted": request.getfixturevalue("ritz1_selfhosted"),
        }
        run0 = request.getfixturevalue("run_ritz0")
        failures = []
        for rid, row in CORPUS.items():
            failures += _row_failures(
                rid, row, _compile_all(row, rid, tmp_path, binaries, run0))
    if failures:
        shown = "\n".join(failures[:20])
        rest = failures[20:]
        tail = f"\n...and {len(rest)} more:\n" + "\n".join(rest) if rest else ""
        raise AssertionError(
            f"reject parity: {len(failures)} failure(s) over {len(CORPUS)} rows\n"
            + shown + tail)


def test_the_checker_notices_a_disagreement():
    """The always-on mutation check: a disagreement is reported, not absorbed."""
    rid, row = next((rid, row) for rid, row in CORPUS.items() if row.gap is None)
    line, col = row.at
    token = row.oracle_message or row.message
    good = {name: (1, f"unit.ritz:{line}:{col}: {token}\n") for name in COMPILERS}
    assert _row_failures(rid, row, good) == []

    accepted = dict(good)
    accepted["ritz1"] = (0, "")
    assert _row_failures(rid, row, accepted), "an acceptance was not reported"

    moved = dict(good)
    moved["ritz1_selfhosted"] = (1, f"unit.ritz:{line}:{col + 1}: {token}\n")
    assert _row_failures(rid, row, moved), "a moved diagnostic was not reported"

    crashed = dict(good)
    crashed["ritz1"] = (-11, "")
    assert _row_failures(rid, row, crashed), "a crash was not reported"


def test_a_bad_injection_is_an_error():
    """A malformed RITZ_REJECT_PARITY_INJECT fails loudly, not vacuously."""
    with pytest.raises(pytest.fail.Exception, match="bad RITZ_REJECT_PARITY_INJECT"):
        _injection_failures("nonsense")


def test_every_rejected_narrowing_row_is_in_the_corpus():
    """A new #1446 rejection cannot skip the parity run."""
    missing = sorted(f"narrowing/{name}" for name in NARROWING.REJECTED
                     if f"narrowing/{name}" not in CORPUS)
    assert not missing, (
        "these rows are in test_implicit_narrowing.REJECTED but not in the "
        f"parity corpus: {missing}")


def test_every_else_less_if_row_is_in_the_corpus():
    """A new #1406/#1435 shape cannot skip the parity run."""
    wanted = [f"else/{label}/{name}"
              for label, table in (("value", ELSE.VALUE_POSITIONS),
                                   ("operand", ELSE.OPERAND_POSITIONS))
              for name in table]
    missing = sorted(rid for rid in wanted if rid not in CORPUS)
    assert not missing, (
        "these else-less-if shapes are in test_if_expression_requires_else "
        f"but not in the parity corpus (measure ritz0's line:col and add them "
        f"to ELSE_AT): {missing}")


def test_every_else_position_is_a_known_shape():
    """ELSE_AT must not accumulate entries for rows that no longer exist."""
    wanted = {f"else/{label}/{name}"
              for label, table in (("value", ELSE.VALUE_POSITIONS),
                                   ("operand", ELSE.OPERAND_POSITIONS))
              for name in table}
    stale = sorted(rid for rid in ELSE_AT if rid not in wanted)
    assert not stale, f"ELSE_AT names rows that no longer exist: {stale}"
