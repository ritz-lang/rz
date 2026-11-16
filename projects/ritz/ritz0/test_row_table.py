"""A matrix of rows as one test per compiler (AGAST #3518, #3453 F1).

A parametrised matrix pays pytest's per-case cost (collection, xdist dispatch,
reporting) for every row, on every gate.  Here a table of rows is one test:
the rows are compiled `batching.CHUNK` at a time as one program per compiler
(`batching.run_rows`), each row runs in its own process, and every row is
asserted.  A failure names its rows: case id, what it wanted and what it got.

As with `pytest.mark.batched`, a batch can only pass a row: a row the batch
has no answer for, or answers wrongly, is compiled and run on its own, and
only that answer can fail it.

`gaps` maps a row to the AGAST ticket it is a known gap of: such a row must
fail (a strict xfail), and passing fails the table until the entry is dropped.

The tests below check the failures name their rows, and only those: a row
that exits wrong, a gap that has started to pass, or a refusal somewhere
else must each come back by name.
"""

from __future__ import annotations

import pytest

import batching
from test_ref_into_value import _assert_refused, _batch_build, _batch_compile, _run


def _alone(compiler, tmp_path, k, src):
    """The row's exit code compiled on its own, or why it has none."""
    try:
        return _run(compiler, tmp_path, f"row{k}", src)
    except AssertionError as exc:
        return f"no exit code: {str(exc)[-600:]}"


def _verdict(name, ok, got, want, gaps):
    gap = gaps.get(name)
    if gap and ok:
        return f"{name}: passes, but is listed as a gap of AGAST #{gap}: drop the entry"
    if not gap and not ok:
        return f"{name}: wanted {want}, got {got}"
    return None


def _assert_none(compiler, failures, total):
    assert not failures, (f"{compiler}: {len(failures)} of {total} rows failed:\n"
                          + "\n".join(failures))


def assert_runs(compiler, tmp_path, rows, gaps=None):
    """Every row of `rows` ({name: (program, exit code)}) exits as it says."""
    gaps = gaps or {}
    names = list(rows)
    programs = [rows[n][0] for n in names]
    answers = [None] * len(names)
    if batching.enabled():
        for start in range(0, len(names), batching.CHUNK):
            chunk = programs[start:start + batching.CHUNK]
            answers[start:start + len(chunk)] = batching.run_rows(
                compiler, chunk, _batch_build, tmp_path / f"batch{start}", compile=_batch_compile)
    failures = []
    for k, (name, got) in enumerate(zip(names, answers)):
        src, want = rows[name]
        if got != want:
            got = _alone(compiler, tmp_path, k, src)
        bad = _verdict(name, got == want, f"exit {got}" if isinstance(got, int) else got,
                       f"exit {want}", gaps)
        if bad:
            failures.append(bad)
    _assert_none(compiler, failures, len(names))


def assert_refusals(compiler, tmp_path, rows, gaps=None):
    """Every row of `rows` ({name: (program with `^` at the spot, message)}) is refused there."""
    gaps = gaps or {}
    failures = []
    for k, (name, (marked, message)) in enumerate(rows.items()):
        try:
            _assert_refused(compiler, tmp_path, f"row{k}", marked, message)
            ok, got = True, "refused"
        except AssertionError as exc:
            ok, got = False, str(exc)[-600:]
        bad = _verdict(name, ok, got, f"`{message}` at its `^`", gaps)
        if bad:
            failures.append(bad)
    _assert_none(compiler, failures, len(rows))


# ---- the harness's own tests ------------------------------------------------

MAIN = "pub fn main() -> i32\n    {}\n"


def _failure(call):
    with pytest.raises(AssertionError) as exc:
        call()
    return str(exc.value)


@pytest.mark.integration
def test_a_run_table_names_each_failing_row(tmp_path):
    rows = {"right": (MAIN.format(3), 3), "wrong": (MAIN.format(4), 5),
            "gap_that_passes": (MAIN.format(6), 6), "gap_that_fails": (MAIN.format(7), 8)}
    gaps = {"gap_that_passes": 101, "gap_that_fails": 102}
    got = _failure(lambda: assert_runs("ritz1", tmp_path, rows, gaps))
    assert "2 of 4 rows failed" in got
    assert "wrong: wanted exit 5, got exit 4" in got
    assert "gap_that_passes: passes, but is listed as a gap of AGAST #101" in got
    assert "right" not in got and "gap_that_fails" not in got


@pytest.mark.integration
def test_a_refusal_table_names_each_failing_row(tmp_path):
    shared = "struct C\n    x: i32\n\nfn g(p: @C)\n    {}p.x = 3\n\n" + MAIN.format(0)
    message = "cannot write through an `@T`: make it `@&T`"
    rows = {"refused_there": (shared.format("^"), message),
            "refused_elsewhere": (shared.format("") + "    ^0\n", message)}
    got = _failure(lambda: assert_refusals("ritz1", tmp_path, rows))
    assert "1 of 2 rows failed" in got
    assert "refused_elsewhere: wanted" in got and "refused_there" not in got
