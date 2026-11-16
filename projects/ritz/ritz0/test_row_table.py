"""A matrix of rows as one test per compiler (AGAST #3518, #3520, #3453 F1).

A parametrised matrix pays pytest's per-case cost (collection, xdist dispatch,
reporting) for every row, on every gate.  Here a table of rows is one test:
the rows are compiled `batching.CHUNK` at a time as one program per compiler
(`batching.run_rows` / `refuse_rows`), each run row in its own process, and
every row is asserted.  A failure names its rows: case id, what it wanted and
what it got (the first `SHOWN` with their detail, the rest by name).

As with `pytest.mark.batched`, a batch can only pass a row: a row the batch
has no answer for, or answers wrongly, is compiled on its own, and only that
answer can fail it.  `RITZ_TEST_BATCH=0` compiles every row on its own.

A refusal row's `^` is where its message must be reported: the whole message,
unless it's a `Prefix`.  A program without a `^` must report its message, as a
prefix, somewhere in its own lines.

`gaps` maps a row to the AGAST ticket it is a known gap of: such a row must
fail (a strict xfail), and passing fails the table until the entry is dropped.

The tests below check the failures name their rows, and only those: a row
that exits wrong or doesn't build, a gap that has started to pass, a refusal
somewhere else or none at all must each come back by name.
"""

from __future__ import annotations

import re

import pytest

import batching
from test_ref_into_value import _batch_build, _batch_compile, _compile, _run

SHOWN = 20  # failing rows reported with their detail; the rest are named


class Prefix(str):
    """A refusal row's message that the diagnostic only has to start with."""


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
    if not failures:
        return
    rest = [f.split(":", 1)[0] for f in failures[SHOWN:]]
    tail = f"\n...and {len(rest)} more: {', '.join(rest)}" if rest else ""
    raise AssertionError(f"{compiler}: {len(failures)} of {total} rows failed:\n"
                         + "\n".join(failures[:SHOWN]) + tail)


def _chunked(answer, programs, tmp_path):
    """`answer(chunk, work)` over `programs`, `batching.CHUNK` rows at a time;
    all None when batching is off."""
    answers = [None] * len(programs)
    if batching.enabled():
        for start in range(0, len(programs), batching.CHUNK):
            chunk = programs[start:start + batching.CHUNK]
            answers[start:start + len(chunk)] = answer(chunk, tmp_path / f"batch{start}")
    return answers


def assert_runs(compiler, tmp_path, rows, gaps=None):
    """Every row of `rows` ({name: (program, exit code)}) exits as it says."""
    gaps = gaps or {}
    names = list(rows)
    answers = _chunked(lambda chunk, work: batching.run_rows(compiler, chunk, _batch_build, work,
                                                             compile=_batch_compile),
                       [rows[n][0] for n in names], tmp_path)
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


def _caret(marked):
    """`marked` without its `^`, and the `^`'s `line:col` (None without one)."""
    if "^" not in marked:
        return marked, None
    before = marked[:marked.index("^")]
    line = before.count("\n") + 1
    return marked.replace("^", "", 1), f"{line}:{len(before) - before.rfind(chr(10))}"


def _refused_as(out, where, message):
    """Whether `out` reports `message` at `where`: the whole message, unless
    it's a `Prefix`; anywhere, as a prefix, when `where` is None."""
    whole = where is not None and not isinstance(message, Prefix)
    return any((at == where or where is None) and (text == message if whole else text.startswith(message))
               for at, text in re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out))


def _refused_alone(compiler, tmp_path, k, src, where, message):
    """None if the row compiled on its own is refused as it says, else what it got."""
    comp, ll, _ = _compile(compiler, tmp_path, f"row{k}", src)
    out = comp.stdout + comp.stderr
    if comp.returncode == 0 or ll.exists():
        return "accepted"
    return None if _refused_as(out, where, message) else out[-600:]


def assert_refusals(compiler, tmp_path, rows, gaps=None):
    """Every row of `rows` ({name: (program with `^` at the spot, message)}) is refused there."""
    gaps = gaps or {}
    names = list(rows)
    answers = _chunked(lambda chunk, work: batching.refuse_rows(compiler, chunk, _batch_compile, work),
                       [rows[n][0].replace("^", batching.MARK, 1) for n in names], tmp_path)
    failures = []
    for k, (name, got) in enumerate(zip(names, answers)):
        marked, message = rows[name]
        src, where = _caret(marked)
        if got is not None and _refused_as(got[0], got[1] if where else None, message):
            miss = None
        else:
            miss = _refused_alone(compiler, tmp_path, k, src, where, message)
        bad = _verdict(name, miss is None, miss, f"`{message}` at {where or 'any line'}", gaps)
        if bad:
            failures.append(bad)
    _assert_none(compiler, failures, len(names))


# ---- the harness's own tests ------------------------------------------------

MAIN = "pub fn main() -> i32\n    {}\n"
# Same `f` spelled differently per row: the batch renames it, and each row
# still answers for itself.
F = "fn f() -> i32\n    return {}\n\n" + MAIN.format("return f()")
REFUSED = MAIN.format("let x: i32 = ^true\n    return 0")


def _failure(call):
    with pytest.raises(AssertionError) as exc:
        call()
    return str(exc.value)


@pytest.mark.integration
def test_a_run_table_names_each_failing_row(tmp_path):
    rows = {"right": (MAIN.format(3), 3), "wrong": (MAIN.format(4), 5),
            "gap_that_passes": (MAIN.format(6), 6), "gap_that_fails": (MAIN.format(7), 8),
            "f3": (F.format(3), 3), "f4": (F.format(4), 3), "unbuilt": (REFUSED.replace("^", ""), 0)}
    gaps = {"gap_that_passes": 101, "gap_that_fails": 102}
    got = _failure(lambda: assert_runs("ritz1", tmp_path, rows, gaps))
    assert "4 of 7 rows failed" in got
    assert "wrong: wanted exit 5, got exit 4" in got
    assert "f4: wanted exit 3, got exit 4" in got
    assert "unbuilt: wanted exit 0, got no exit code" in got
    assert "gap_that_passes: passes, but is listed as a gap of AGAST #101" in got
    assert "right" not in got and "gap_that_fails" not in got and "f3" not in got


@pytest.mark.integration
def test_a_refusal_table_names_each_failing_row(tmp_path):
    shared = "struct C\n    x: i32\n\nfn g(p: @C)\n    {}p.x = 3\n\n" + MAIN.format(0)
    message = "cannot write through an `@T`: make it `@&T`"
    rows = {"refused_there": (shared.format("^"), message),
            "refused_elsewhere": (shared.format("") + "    ^0\n", message),
            "prefix_there": (REFUSED, Prefix("")),
            "anywhere": (REFUSED.replace("^", ""), ""),
            "prefix_elsewhere": (REFUSED.replace("^true", "true^"), Prefix("")),
            "accepted": (MAIN.format(0), "")}
    got = _failure(lambda: assert_refusals("ritz1", tmp_path, rows))
    assert "3 of 6 rows failed" in got
    assert "refused_elsewhere: wanted" in got
    assert "prefix_elsewhere: wanted `` at 2:22" in got
    assert "accepted: wanted `` at any line, got accepted" in got
    assert "refused_there" not in got and "prefix_there" not in got and "anywhere:" not in got


def test_a_long_failure_names_the_rows_past_its_detail():
    failures = [f"r{i}: wanted exit 0, got exit 1" for i in range(SHOWN + 2)]
    got = _failure(lambda: _assert_none("ritz1", failures, 30))
    assert f"{SHOWN + 2} of 30 rows failed" in got
    assert got.endswith(f"...and 2 more: r{SHOWN}, r{SHOWN + 1}")
