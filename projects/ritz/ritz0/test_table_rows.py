"""A matrix of small programs as one table per compiler (AGAST #3519, #3453 F1).

A helper with its own tests, as test_ritz1_for_header.py is: a `test_` module
so tools/check_liveness.py counts it as test code.  Import it as
`import test_table_rows as table_rows`.

A parametrised matrix pays pytest's per-test cost once per row: collection,
xdist dispatch and reporting, and under `batched` a record-mode replay of
every sibling.  2,070 rows of test_index_through_reference.py and
test_slice_through_reference.py were 99 CPU-s.  A table pays it once per
chunk.  The rows are data, each chunk's rows compile as one program per
compiler (batching.run_rows / refuse_rows, so the leaning checks of AGAST
#2867 still hold), and every row is asserted by name.

**A batch only ever passes a row.**  A row the batch can't answer, or answers
wrong, is compiled on its own, and that answer is the row's: a failure is
always the row's own compile, as `batched` promised.  It names the row (the
id the parametrised test had, less its compiler), what it wanted and what
it got, and the test goes on to the rest of the chunk, so one broken rule
lists every row it breaks.

    @case(box=sorted(BOXES), kind=sorted(KINDS))    # id: the_first_element[Vec-pointer]
    def the_first_element(box, kind):
        return Run(program, 20)

    TABLE = cases(globals())    # every @case in the module, in source order

The kwargs' order is the id's: list them as the old decorators read bottom-up.
"""

from __future__ import annotations

import itertools
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

import batching
import test_ritz1_for_header as for_header

ALL = ("ritz0", "ritz1", "ritz1_selfhosted")

# Rows per chunk: one compile of each chunk per compiler.  batching.CHUNK's 48 is
# for rows of one function; a table's rows share less, so a merge renames more.
CHUNK = 64


@dataclass(frozen=True)
class Run:
    """The program compiles, links and exits `want`."""
    program: str
    want: int


@dataclass(frozen=True)
class Refused:
    """The compiler refuses the program.

    `message` is in what it says (a tuple: every one of them is; None: any
    refusal will do); `located`, some diagnostic is at a `main.ritz:` line;
    `at`, (line, col) is where one is.
    """
    program: str
    message: str | tuple | None
    at: tuple | None = None
    located: bool = True


@dataclass(frozen=True)
class Row:
    id: str
    compilers: tuple
    spec: Run | Refused


def case(compilers=ALL, **grid):
    """Mark `fn(**params) -> Run | Refused` as a table's rows, one per point of `grid`."""
    def mark(fn):
        fn.table_case = (tuple(compilers), grid)
        return fn
    return mark


def _rows_of(name, fn):
    compilers, grid = fn.table_case
    base = name.lstrip("_")
    if not grid:
        yield Row(base, compilers, fn())
        return
    keys = list(grid)
    for values in itertools.product(*(grid[k] for k in keys)):
        params = dict(zip(keys, values))
        yield Row(f"{base}[{'-'.join(map(str, values))}]", compilers, fn(**params))


def cases(namespace: dict) -> list:
    """Every row of every `@case` function in `namespace`, in its order."""
    rows = [row for name, fn in namespace.items() if hasattr(fn, "table_case")
            for row in _rows_of(name, fn)]
    seen = set()
    for row in rows:
        assert row.id not in seen, f"two rows are {row.id}"
        seen.add(row.id)
    return rows


def for_compiler(rows, compiler) -> list:
    return [r for r in rows if compiler in r.compilers]


def chunks(rows, compilers=ALL, size=CHUNK) -> list:
    """(compiler, chunk index) for each chunk: a pytest parametrisation."""
    return [(c, i) for c in compilers for i in range(-(-len(for_compiler(rows, c)) // size))]


def chunk(rows, compiler, index, size=CHUNK) -> list:
    return for_compiler(rows, compiler)[index * size:(index + 1) * size]


# ---- checking ---------------------------------------------------------------

def _tail(text: str, n: int = 800) -> str:
    return text[-n:].rstrip()


def _alone_dir(work: Path, row: Row) -> Path:
    alone = work / "alone"
    alone.mkdir(parents=True, exist_ok=True)
    here = alone / f"{sum(1 for _ in alone.iterdir())}-{re.sub(r'\W+', '_', row.id)[:80]}"
    here.mkdir()
    return here


def _run_alone(compiler, row, build, work) -> str | None:
    """None if `row` runs right compiled on its own, else what went wrong."""
    want = row.spec.want
    here = _alone_dir(work, row)
    src = here / "main.ritz"
    src.write_text(row.spec.program)
    ok, output, exe = build(compiler, src, here)
    if not ok:
        return f"want exit {want}, but it didn't compile and link:\n{_tail(output)}"
    try:
        got = subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode
    except subprocess.TimeoutExpired:
        return f"want exit {want}, but it ran past 60 s"
    return None if got == want else f"want exit {want}, got {got}"


def _refusal_wrong(spec: Refused, out: str, at: str | None) -> str | None:
    """What a refusal's diagnostics `out` lack, or None.  `at` is "line:col" to find."""
    wanted = (spec.message,) if isinstance(spec.message, str) else spec.message or ()
    missing = [m for m in wanted if m not in out]
    if missing:
        return f"want {' and '.join(map(repr, missing))}, got:\n{_tail(out)}"
    if spec.located and "main.ritz:" not in out:
        return f"want it located, got:\n{_tail(out)}"
    if at is not None and f"main.ritz:{at}:" not in out:
        return f"want it at main.ritz:{at}:, got:\n{_tail(out)}"
    return None


def _refused_alone(compiler, row, compile, work) -> str | None:
    spec = row.spec
    here = _alone_dir(work, row)
    src = here / "main.ritz"
    src.write_text(spec.program)
    code, out = compile(compiler, src, here)
    if code == 0:
        return f"want it refused ({spec.message!r}), but it compiled"
    return _refusal_wrong(spec, out, "{}:{}".format(*spec.at) if spec.at else None)


def check(compiler, rows, *, build, compile, work: Path) -> list:
    """One line per row of `rows` that fails on `compiler`: "<compiler> <id>: <why>".

    `build` and `compile` are batching.run_rows's: `build(compiler, src, work) ->
    (ok, output, exe)` compiles and links, `compile(compiler, src, work) ->
    (rc, output)` only compiles, its module in `work/main.ll`.
    """
    failures = []
    runs = [r for r in rows if isinstance(r.spec, Run)]
    refusals = [r for r in rows if isinstance(r.spec, Refused)]
    if runs:
        got = batching.run_rows(compiler, [r.spec.program for r in runs], build, work / "run",
                                compile=compile)
        for row, code in zip(runs, got):
            if code != row.spec.want:
                why = _run_alone(compiler, row, build, work)
                if why:
                    failures.append(f"{compiler} {row.id}: {why}")
    if refusals:
        programs = [batching._insert_mark(r.spec.program, r.spec.at) if r.spec.at else r.spec.program
                    for r in refusals]
        got = batching.refuse_rows(compiler, programs, compile, work / "refuse")
        for row, answer in zip(refusals, got):
            if (answer is not None and (row.spec.at is None or answer[1] is not None)
                    and _refusal_wrong(row.spec, answer[0], answer[1]) is None):
                continue
            why = _refused_alone(compiler, row, compile, work)
            if why:
                failures.append(f"{compiler} {row.id}: {why}")
    return failures


def assert_rows(compiler, rows, **kwargs) -> None:
    """`check`, as one assertion listing every failing row."""
    failures = check(compiler, rows, **kwargs)
    assert not failures, f"{len(failures)} of {len(rows)} rows failed:\n" + "\n".join(failures)


# ---- its own tests: a failing row says which, and only it fails ------------
#
# ritz1 only: the checker is the same for every compiler, and ritz1's compile is
# the cheap one.
GOOD = "pub fn main() -> i32\n    return 7\n"
WRONG = "pub fn main() -> i32\n    return 8\n"
BAD = "pub fn main() -> i32\n    let x: i32 = true\n    return 0\n"


@case(n=[1, 2], word=["a", "b"])
def _ids(n, word):
    return Run(GOOD, 7)


@case(compilers=("ritz0",))
def _only_ritz0():
    return Run(GOOD, 7)


@pytest.mark.unit
def test_a_row_id_is_the_old_parametrised_id():
    # The kwargs' order is the old bottom-up decorator order; the compiler isn't in it.
    rows = cases({"_ids": _ids, "_only_ritz0": _only_ritz0})
    assert [r.id for r in rows] == ["ids[1-a]", "ids[1-b]", "ids[2-a]", "ids[2-b]", "only_ritz0"]
    assert [r.compilers for r in rows][-1] == ("ritz0",)
    assert [r.id for r in for_compiler(rows, "ritz1")] == ["ids[1-a]", "ids[1-b]", "ids[2-a]", "ids[2-b]"]


def _check(ritz1_bin, tmp_path, rows):
    return check("ritz1", rows, build=for_header.batch_build(ritz1_bin),
                            compile=for_header.batch_compile(ritz1_bin), work=tmp_path)


@pytest.mark.integration
def test_a_wrong_exit_code_names_its_row_and_no_other(ritz1_bin, tmp_path):
    rows = [Row("right", ALL, Run(GOOD, 7)),
            Row("wrong", ALL, Run(WRONG, 7))]
    failures = _check(ritz1_bin, tmp_path, rows)
    assert len(failures) == 1, failures
    assert failures[0].startswith("ritz1 wrong: want exit 7, got 8"), failures


@pytest.mark.integration
def test_a_refusal_row_names_itself_when_it_compiles_or_says_the_wrong_thing(ritz1_bin, tmp_path):
    rows = [Row("refused", ALL, Refused(BAD, "cannot use bool as an integer")),
            Row("compiles", ALL, Refused(GOOD, "anything")),
            Row("other_words", ALL, Refused(BAD, "no such message")),
            Row("elsewhere", ALL, Refused(BAD, None, at=(1, 1)))]
    failures = _check(ritz1_bin, tmp_path, rows)
    assert [f.split(":")[0] for f in failures] == ["ritz1 compiles", "ritz1 other_words",
                                                   "ritz1 elsewhere"], failures
    assert "compiled" in failures[0]
    assert "no such message" in failures[1]
    assert "main.ritz:1:1:" in failures[2]


@pytest.mark.integration
def test_a_refusal_row_with_several_messages_wants_every_one(ritz1_bin, tmp_path):
    # AGAST #3517: a tuple is every one of its messages, and a row missing one names it.
    rows = [Row("both", ALL, Refused(BAD, ("cannot use bool", "as an integer"))),
            Row("one_missing", ALL, Refused(BAD, ("cannot use bool", "no such message")))]
    failures = _check(ritz1_bin, tmp_path, rows)
    assert [f.split(":")[0] for f in failures] == ["ritz1 one_missing"], failures
    assert "no such message" in failures[0] and "cannot use bool'" not in failures[0]
