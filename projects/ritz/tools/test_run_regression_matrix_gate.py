"""Tests for the matrix gate's exit code (AGAST #1372).

`make matrix-full` is the compiler gate this repo cites in almost every commit
message: "matrix-full 53/53 x 3". It could not fail. run_regression_matrix.py's
main() ended in an unconditional `return 0`, so the process exited 0 no matter
how many cells were red. The Makefile target just runs the script, and CI's
"Bootstrap chain + regression matrix" step just runs the target, so nothing
between the failure and the green check mark ever looked at a status.

It was found by making it fail: #1369 turned ritz1's silent
`; ERROR ... add i64 0, 0` substitution into a hard compile error, which took
test_issue_float_coercion from pass to compile-fail under ritz1 and
ritz1_selfhosted. The summary printed

    ritz0                53/53
    ritz1                52/53
    ritz1_selfhosted     52/53

and the command exited 0.

The classification mirrors `rz`'s gate_outcome (rz:135), deliberately, because
that is the discipline the workspace already settled on for build/test sweeps:

  hard  — failed and NOT expected. Fails the gate.
  known — failed and listed in EXPECTED_FAILURES. Advisory, printed with its
          AGAST reference so it stays visible.
  xpass — listed in EXPECTED_FAILURES but PASSED. Also fails the gate.

The xpass half is the part that keeps the list from rotting. scripts/regression.sh
carried the same check for years as a warn() that changed nothing, and two
entries sat on its allowlist blaming the async framework for what was really a
syntax migration (#1365). A list that cannot go red is a list nobody edits.
"""

import importlib.util
from pathlib import Path

import pytest

MATRIX = Path(__file__).resolve().parent / "run_regression_matrix.py"


def _load():
    spec = importlib.util.spec_from_file_location("_matrix", MATRIX)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


matrix = _load()


def _results(**kw):
    """Build a results dict: name -> (status, code, info)."""
    return {name: (status, 0 if status == "pass" else 1, "") for name, status in kw.items()}


@pytest.mark.unit
def test_all_passing_is_green():
    hard, known, xpass = matrix.matrix_outcome(
        "ritz1", _results(a="pass", b="pass"), {}
    )
    assert (hard, known, xpass) == ([], [], [])


@pytest.mark.unit
def test_an_unexpected_failure_is_hard():
    """The case that was silently exiting 0."""
    hard, known, xpass = matrix.matrix_outcome(
        "ritz1", _results(a="pass", b="compile-fail"), {}
    )
    assert hard == ["b"]
    assert known == [] and xpass == []


@pytest.mark.unit
def test_an_expected_failure_is_advisory_not_hard():
    hard, known, xpass = matrix.matrix_outcome(
        "ritz1", _results(a="pass", b="compile-fail"), {("ritz1", "b"): "AGAST #1370"}
    )
    assert hard == []
    assert known == ["b"]
    assert xpass == []


@pytest.mark.unit
def test_expected_failure_is_per_compiler():
    """An entry for ritz1 must not excuse ritz1_selfhosted.

    ritz1 and its self-compiled twin disagreeing is a self-hosting bug, and
    regression.sh's allowlist header says such a divergence must go red rather
    than be recorded. Keying the excuse by (compiler, test) keeps that true
    here: excusing one does not excuse the other.
    """
    expected = {("ritz1", "b"): "AGAST #1370"}
    hard, _, _ = matrix.matrix_outcome("ritz1_selfhosted", _results(b="compile-fail"), expected)
    assert hard == ["b"], "a ritz1 excuse leaked into ritz1_selfhosted"


@pytest.mark.unit
def test_an_expected_failure_that_passes_is_xpass():
    """Strict-xpass: the entry must be deleted, and until it is, the gate is red."""
    hard, known, xpass = matrix.matrix_outcome(
        "ritz1", _results(b="pass"), {("ritz1", "b"): "AGAST #1370"}
    )
    assert xpass == ["b"]
    assert hard == [] and known == []


@pytest.mark.unit
def test_xpass_for_a_test_that_did_not_run_is_not_reported():
    """Filtering with --tests must not turn every unselected entry into an xpass."""
    hard, known, xpass = matrix.matrix_outcome(
        "ritz1", _results(a="pass"), {("ritz1", "not_selected"): "AGAST #1370"}
    )
    assert (hard, known, xpass) == ([], [], [])


@pytest.mark.unit
def test_exit_code_is_nonzero_for_hard_and_xpass_only():
    assert matrix.matrix_exit_code({"ritz1": ([], [], [])}) == 0
    assert matrix.matrix_exit_code({"ritz1": (["b"], [], [])}) != 0
    assert matrix.matrix_exit_code({"ritz1": ([], ["b"], [])}) == 0, (
        "a known failure is advisory and must not fail the gate"
    )
    assert matrix.matrix_exit_code({"ritz1": ([], [], ["b"])}) != 0, (
        "an expected failure that starts passing must fail the gate"
    )
    assert matrix.matrix_exit_code(
        {"ritz0": ([], [], []), "ritz1": (["b"], [], [])}
    ) != 0, "a failure in any compiler must fail the gate"


@pytest.mark.unit
def test_every_expected_failure_entry_names_an_agast_task():
    """Same rule rz.toml enforces for [ci.known_failing.*].

    An excuse without a ticket is an excuse nobody will ever revisit.
    """
    for key, reason in matrix.EXPECTED_FAILURES.items():
        assert "AGAST #" in reason, f"{key} has no AGAST reference: {reason!r}"


@pytest.mark.unit
def test_every_expected_failure_entry_names_a_real_test_and_compiler():
    """Guards the other rot direction: an entry for a test that no longer
    exists, or for a compiler name with a typo, would sit here forever
    excusing nothing while looking like diligence."""
    valid_compilers = {"ritz0", "ritz1", "ritz1_selfhosted"}
    for compiler, test_name in matrix.EXPECTED_FAILURES:
        assert compiler in valid_compilers, f"unknown compiler {compiler!r}"
        assert test_name in matrix.TESTS, (
            f"{test_name!r} is excused but is not in TESTS, so it never runs"
        )
