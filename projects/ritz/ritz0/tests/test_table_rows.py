"""A matrix of small programs as one table per compiler (AGAST #3518, #3519, #3566).

A helper with its own tests, as test_ritz1_for_header.py is: a `test_` module
so tools/check_liveness.py counts it as test code.  Import it as
`import test_table_rows as table_rows`.  It is the one table helper: #3566
folded #3518's test_row_table.py into it.

A parametrised matrix pays pytest's per-test cost once per row: collection,
xdist dispatch and reporting, and under `batched` a record-mode replay of
every sibling.  2,070 rows of test_index_through_reference.py and
test_slice_through_reference.py were 99 CPU-s.  A table pays it once per
test.  The rows are data, compiled as one program per compiler and chunk
(batching.run_rows / refuse_rows, so the leaning checks of AGAST #2867 still
hold), each run row in its own process, and every row is asserted by name.

**A batch only ever passes a row.**  A row the batch can't answer, or answers
wrong, is compiled on its own, and that answer is the row's: a failure is
always the row's own compile, as `batched` promised.  It names the row (the
id the parametrised test had, less its compiler), what it wanted and what
it got, and the test goes on to the rest of the rows, so one broken rule
lists every row it breaks (the first `SHOWN` with their detail, the rest by
name).  `RITZ_TEST_BATCH=0` compiles every row on its own.

Two ways in, one checker (`check`):

    @case(box=sorted(BOXES), kind=sorted(KINDS))    # id: the_first_element[Vec-pointer]
    def the_first_element(box, kind):
        return Run(program, 20)

    TABLE = cases(globals())    # every @case in the module, in source order

The kwargs' order is the id's: list them as the old decorators read bottom-up.
A grid with holes lists `Row(id, compilers, spec)`s instead.  `chunks` /
`chunk` cut a table into `test_every_row[<compiler>-<chunk>]` tests, and
`assert_rows(compiler, rows, build=, compile=, work=)` takes the build that
links what the rows need (`ritzlib_build`).

Or a dict per table, checked in one test per compiler with
test_ref_into_value.py's build unless `build=` / `compile=` say otherwise:

    assert_runs(compiler, tmp_path, {name: (program, exit code)}, gaps)
    assert_refusals(compiler, tmp_path, {name: (program with `^`, message)}, gaps)

A refusal's `^` is where its message must be reported, the whole message
unless it's a `Prefix`; a program without a `^` must report it, as a prefix,
somewhere in its own lines.

`gaps` maps a row id to the AGAST ticket it is a known gap of: such a row must
fail (a strict xfail), and one that passes fails the table until the entry is
dropped.
"""

from __future__ import annotations

import functools
import itertools
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

import batching
import test_ref_into_value as ref_into_value
import test_ritz1_for_header as for_header

ALL = ("ritz0", "ritz1", "ritz1_selfhosted")

SHOWN = 20  # failing rows reported with their detail; the rest are named

# Rows per chunk: one compile of each chunk per compiler.  batching.CHUNK's 48 is
# for rows of one function; a table's rows share less, so a merge renames more.
CHUNK = 64


@dataclass(frozen=True)
class Run:
    """The program compiles, links and exits `want`."""
    program: str
    want: int


class Prefix(str):
    """A `Refused` message that one diagnostic, at `at` if the row has one,
    starts with."""


class Whole(str):
    """A `Refused` message that one diagnostic, at `at` if the row has one, is."""


@dataclass(frozen=True)
class Refused:
    """The compiler refuses the program.

    `message` is in what it says (a tuple: every one of them is; None: any
    refusal will do; a `Prefix` or a `Whole`: one `main.ritz:` diagnostic, at
    `at` if there is one, starts with it or is it); `located`, some diagnostic
    is at a `main.ritz:` line; `at`, (line, col) is where one is.
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


def _chunked(rows, compiler, size) -> list:
    """`compiler`'s rows cut into chunks of `size`, of one import set each if
    that takes no more chunks (AGAST #3906).

    batching.run_rows compiles alone, as well, each row whose imports differ
    from its batch's: it could lean on a module only a sibling imports (#2867).
    A chunk mixing import sets pays that for every row of all but the widest.
    A chunk more is a batch build more, and a test more, which costs more than
    a few rows alone (test_slice_through_reference.py's 6), so where one set a
    chunk takes more chunks, the rows are cut in source order as they were.
    Sets come in order of first appearance, each in its rows' source order.
    """
    mine = for_compiler(rows, compiler)
    by_imports = {}
    for row in mine:
        by_imports.setdefault(frozenset(batching._imports(row.spec.program)), []).append(row)
    grouped = [group[i:i + size] for group in by_imports.values() for i in range(0, len(group), size)]
    in_order = [mine[i:i + size] for i in range(0, len(mine), size)]
    return grouped if len(grouped) <= len(in_order) else in_order


def chunks(rows, compilers=ALL, size=CHUNK) -> list:
    """(compiler, chunk index) for each chunk: a pytest parametrisation."""
    return [(c, i) for c in compilers for i in range(len(_chunked(rows, c, size)))]


def chunk(rows, compiler, index, size=CHUNK) -> list:
    return _chunked(rows, compiler, size)[index]


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


_DIAGNOSTIC = re.compile(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)")


def _said_wrong(message, out: str, at: str | None) -> str | None:
    """Why no diagnostic in `out`, at `at` if not None, is the `Whole`
    `message` (starts with it, a `Prefix`), or None."""
    whole = isinstance(message, Whole)
    if any(where == at or at is None for where, text in _DIAGNOSTIC.findall(out)
           if (text == message if whole else text.startswith(message))):
        return None
    how = "a diagnostic" if whole else "a diagnostic starting"
    return f"want {how} {str(message)!r} at {f'main.ritz:{at}' if at else 'any line'}, got:\n{_tail(out)}"


def _refusal_wrong(spec: Refused, out: str, at: str | None) -> str | None:
    """What a refusal's diagnostics `out` lack, or None.  `at` is "line:col" to find."""
    if isinstance(spec.message, (Prefix, Whole)):
        return _said_wrong(spec.message, out, at)
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


def _batched(rows, size, answer) -> list:
    """`answer(chunk, index)` over `rows`, `size` (None: all) at a time; all
    None when batching is off (RITZ_TEST_BATCH=0, AGAST #3901)."""
    if not batching.enabled():
        return [None] * len(rows)
    size = size or len(rows) or 1
    got = []
    for index, start in enumerate(range(0, len(rows), size)):
        got += answer(rows[start:start + size], index)
    return got


def _verdict(compiler, row, why, gaps) -> str | None:
    """The row's failure line, or None: a gap must fail, any other row pass."""
    gap = gaps.get(row.id)
    if gap and why is None:
        return f"{compiler} {row.id}: passes, but is listed as a gap of AGAST #{gap}: drop the entry"
    if not gap and why:
        return f"{compiler} {row.id}: {why}"
    return None


def _failures(compiler, rows, *, build, compile, work: Path, gaps=None, size=None) -> list:
    """(row id, failure line) for each row of `rows` failing on `compiler`, in order."""
    gaps = gaps or {}
    runs = [k for k, r in enumerate(rows) if isinstance(r.spec, Run)]
    refusals = [k for k, r in enumerate(rows) if isinstance(r.spec, Refused)]
    whys = {}
    answers = _batched(runs, size, lambda part, i: batching.run_rows(
        compiler, [rows[k].spec.program for k in part], build, work / "run" / str(i), compile=compile))
    for k, code in zip(runs, answers):
        row = rows[k]
        whys[k] = None if code == row.spec.want else _run_alone(compiler, row, build, work)
    answers = _batched(refusals, size, lambda part, i: batching.refuse_rows(
        compiler, [batching._insert_mark(rows[k].spec.program, rows[k].spec.at) if rows[k].spec.at
                   else rows[k].spec.program for k in part], compile, work / "refuse" / str(i)))
    for k, answer in zip(refusals, answers):
        row = rows[k]
        if (answer is not None and (row.spec.at is None or answer[1] is not None)
                and _refusal_wrong(row.spec, answer[0], answer[1]) is None):
            whys[k] = None
        else:
            whys[k] = _refused_alone(compiler, row, compile, work)
    return [(rows[k].id, bad) for k in sorted(whys)
            for bad in [_verdict(compiler, rows[k], whys[k], gaps)] if bad]


def check(compiler, rows, *, build, compile, work: Path, gaps=None, size=None) -> list:
    """One line per row of `rows` that fails on `compiler`: "<compiler> <id>: <why>".

    `build` and `compile` are batching.run_rows's: `build(compiler, src, work) ->
    (ok, output, exe)` compiles and links, `compile(compiler, src, work) ->
    (rc, output)` only compiles, its module in `work/main.ll`.  `gaps` is
    {row id: AGAST ticket} of rows that must fail; `size` batches the rows
    that many at a time (None: all in one).

    Under RITZ_TEST_BATCH=0 (batching.enabled() false) nothing is batched: the
    batch answers None for every row, so each is compiled alone (AGAST #3901).
    """
    return [bad for _, bad in _failures(compiler, rows, build=build, compile=compile, work=work,
                                        gaps=gaps, size=size)]


def _assert_none(compiler, failures, total) -> None:
    """Fail naming every failing row: the first `SHOWN` with their detail."""
    if not failures:
        return
    rest = [rid for rid, _ in failures[SHOWN:]]
    tail = f"\n...and {len(rest)} more: {', '.join(rest)}" if rest else ""
    raise AssertionError(f"{compiler}: {len(failures)} of {total} rows failed:\n"
                         + "\n".join(bad for _, bad in failures[:SHOWN]) + tail)


def assert_rows(compiler, rows, **kwargs) -> None:
    """`check`, as one assertion listing every failing row."""
    _assert_none(compiler, _failures(compiler, rows, **kwargs), len(rows))


# ---- a table as a dict, one test per compiler (AGAST #3518) ----------------

def _caret(marked: str):
    """`marked` without its `^`, and the `^`'s (line, col) (None without one)."""
    if "^" not in marked:
        return marked, None
    before = marked[:marked.index("^")]
    return marked.replace("^", "", 1), (before.count("\n") + 1, len(before) - before.rfind("\n"))


def _refusal(marked, message) -> Refused:
    """A dict row's `Refused`: the whole message (or a `Prefix`) at its `^`;
    without a `^`, the message as a prefix on some line of its own."""
    program, at = _caret(marked)
    if isinstance(message, str) and not isinstance(message, (Prefix, Whole)):
        message = Whole(message) if at else Prefix(message)
    return Refused(program, message, at=at)


def _assert_table(compiler, tmp_path, table, gaps, build, compile) -> None:
    assert_rows(compiler, table, build=build or ref_into_value._batch_build,
                compile=compile or ref_into_value._batch_compile, work=tmp_path, gaps=gaps,
                size=batching.CHUNK)


def assert_runs(compiler, tmp_path, rows, gaps=None, *, build=None, compile=None) -> None:
    """Every row of `rows` ({name: (program, exit code)}) exits as it says on
    `compiler`; `build` / `compile` default to test_ref_into_value.py's."""
    _assert_table(compiler, tmp_path, [Row(n, (compiler,), Run(*rows[n])) for n in rows],
                  gaps, build, compile)


def assert_refusals(compiler, tmp_path, rows, gaps=None, *, build=None, compile=None) -> None:
    """Every row of `rows` ({name: (program with `^` at the spot, message)})
    is refused there on `compiler` (see `_refusal`)."""
    _assert_table(compiler, tmp_path, [Row(n, (compiler,), _refusal(*rows[n])) for n in rows],
                  gaps, build, compile)


# ---- rows that import ritzlib (AGAST #3906) ---------------------------------
#
# One way to link what a chunk's rows import, for every table: each ritzlib
# module they import, transitively, compiled once per process per compiler
# (for_header.library_objects) and linked onto for_header's batch build.  The
# other way #3889 grew, each chunk a build.py package of its own, paid a python
# start and a cold build cache, every module compiled again, per chunk.

# A nested module (`ritzlib.fmt.digits`) is its path under ritzlib/
# (`fmt/digits`), the form for_header.UNITS uses; `pub import` re-exports
# count (AGAST #201: ritzlib.fmt is an umbrella of them).
_IMPORT = re.compile(r"^(?:pub\s+)?import ritzlib\.([\w.]+)", re.MULTILINE)


def _imports(text: str) -> list:
    return [m.replace(".", "/") for m in _IMPORT.findall(text)]


@functools.cache
def _closure(roots: tuple) -> tuple:
    """`roots` and every ritzlib module they import, transitively."""
    seen, todo = set(), list(roots)
    while todo:
        unit = todo.pop()
        if unit not in seen:
            seen.add(unit)
            todo += _imports((for_header.RITZ_ROOT / "ritzlib" / f"{unit}.ritz").read_text())
    return tuple(sorted(seen))


def ritzlib_build(ritz1_bin):
    """`check`'s `build`: compile the program and link every ritzlib module it
    imports, transitively, as build.py links a package's."""
    def build(compiler, src, work):
        roots = tuple(sorted(set(_imports(src.read_text()))))
        units = tuple(u for u in _closure(roots) if u not in for_header.UNITS)
        return for_header.batch_build(
            ritz1_bin, lambda c: for_header.library_objects(c, ritz1_bin, units))(compiler, src, work)
    return build


def assert_ritzlib_rows(compiler, rows, ritz1_bin, work: Path) -> None:
    """`assert_rows` for rows that import ritzlib."""
    assert_rows(compiler, rows, build=ritzlib_build(ritz1_bin),
                compile=for_header.batch_compile(ritz1_bin), work=work)


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


# ---- RITZ_TEST_BATCH=0: every row is compiled alone (AGAST #3901) ----------
#
# docs/TESTING.md promises RITZ_TEST_BATCH=0 turns batching off, so that "every
# row passes compiled alone" can be checked.  check() calls batching.run_rows /
# refuse_rows itself, so it has to ask batching.enabled() too.  These stub the
# compiler: what's under test is which path a row takes, not ritz1.

def _stub_check(monkeypatch, tmp_path, rows, batch):
    """check() on stubs; returns (failures, programs compiled alone, batch calls)."""
    monkeypatch.setenv("RITZ_TEST_BATCH", batch)
    batched = []
    monkeypatch.setattr(batching, "run_rows",
                        lambda c, programs, *a, **k: batched.append("run") or [7] * len(programs))
    monkeypatch.setattr(batching, "refuse_rows",
                        lambda c, programs, *a, **k: batched.append("refuse")
                        or [("main.ritz:1:1: error: nope", "1:1")] * len(programs))
    alone = []

    def build(compiler, src, work):
        alone.append(src.read_text())
        return True, "", Path("/bin/false" if src.read_text() == WRONG else "/bin/true")

    def compile(compiler, src, work):
        alone.append(src.read_text())
        return 1, "main.ritz:1:1: error: nope"

    failures = check("ritz1", rows, build=build, compile=compile, work=tmp_path)
    return failures, alone, batched


_STUB_ROWS = [Row("runs", ALL, Run(GOOD, 0)),
              Row("wrong", ALL, Run(WRONG, 0)),
              Row("refused", ALL, Refused(BAD, "nope"))]


@pytest.mark.integration    # runs /bin/true and /bin/false
def test_with_batching_off_every_row_is_compiled_alone(monkeypatch, tmp_path):
    failures, alone, batched = _stub_check(monkeypatch, tmp_path, _STUB_ROWS, "0")
    assert batched == [], "RITZ_TEST_BATCH=0 must not batch a row"
    assert alone == [GOOD, WRONG, BAD]
    # A row compiled alone is still asserted, by name: /bin/false exits 1.
    assert failures == ["ritz1 wrong: want exit 0, got 1"], failures


@pytest.mark.unit
def test_with_batching_on_a_row_the_batch_passes_is_not_compiled_again(monkeypatch, tmp_path):
    # The batch's stub answers exit 7 and the refusal every row wants: a Run
    # wanting 7 is the batch's, the refusal is the batch's, nothing goes alone.
    rows = [Row("runs", ALL, Run(GOOD, 7)), Row("refused", ALL, Refused(BAD, "nope"))]
    failures, alone, batched = _stub_check(monkeypatch, tmp_path, rows, "1")
    assert batched == ["run", "refuse"]
    assert alone == [] and failures == []



@pytest.mark.unit
def test_a_table_is_batched_size_rows_at_a_time(monkeypatch, tmp_path):
    # assert_runs / assert_refusals batch batching.CHUNK rows a compile, as #3518's did.
    sizes = []
    monkeypatch.setenv("RITZ_TEST_BATCH", "1")
    monkeypatch.setattr(batching, "run_rows", lambda c, programs, *a, **k: sizes.append(len(programs))
                        or [7] * len(programs))
    rows = [Row(f"r{i}", ALL, Run(GOOD, 7)) for i in range(5)]
    assert check("ritz1", rows, build=None, compile=None, work=tmp_path, size=2) == []
    assert sizes == [2, 2, 1]


@pytest.mark.integration    # runs /bin/true and /bin/false
def test_a_dict_table_builds_with_the_build_it_is_given(monkeypatch, tmp_path):
    # `build=` / `compile=` replace test_ref_into_value's: a String row links ritzlib.
    monkeypatch.setenv("RITZ_TEST_BATCH", "0")
    built = []

    def build(compiler, src, work):
        built.append((compiler, src.read_text()))
        return True, "", Path("/bin/true")

    def compile(compiler, src, work):
        built.append((compiler, src.read_text()))
        return 1, "main.ritz:2:18: error: nope"

    assert_runs("ritz0", tmp_path / "runs", {"runs": (GOOD, 0)}, build=build, compile=compile)
    assert_refusals("ritz0", tmp_path / "refusals", {"refused": (BAD.replace("true", "^true"), "nope")},
                    build=build, compile=compile)
    assert built == [("ritz0", GOOD), ("ritz0", BAD)]


@pytest.mark.unit
def test_a_refusal_row_wants_it_located_unless_told_not_to(monkeypatch, tmp_path):
    monkeypatch.setenv("RITZ_TEST_BATCH", "0")
    rows = [Row("located", ALL, Refused(BAD, "nope")),
            Row("anywhere", ALL, Refused(BAD, "nope", located=False))]
    failures = check("ritz1", rows, build=None, compile=lambda c, src, work: (1, "error: nope"),
                     work=tmp_path)
    assert [f.split(":")[0] for f in failures] == ["ritz1 located"], failures
    assert "want it located" in failures[0]

# ---- a chunk is rows of one import set, if that costs no chunk (AGAST #3906) --
#
# batching.run_rows compiles alone, as well, every row whose imports differ
# from its batch's (a row could lean on a module only a sibling imports,
# #2867).  A chunk mixing import sets paid that for each of them:
# test_deref_index's were 5.7-6.0 CPU-s, 3.7 grouped.  A chunk more, though,
# is a batch build more per compiler, dearer than a few rows alone:
# test_slice_through_reference's 6 rows apart cost CPU-s, not saved them.

def _imports_row(rid, imports):
    return Row(rid, ALL, Run("".join(f"import ritzlib.{m}\n" for m in imports) + "\n" + GOOD, 7))


def _chunk_ids(rows, size):
    """Each compiler's chunks of `rows`, as row ids."""
    got = {compiler: [[r.id for r in chunk(rows, compiler, i, size=size)]
                      for c, i in chunks(rows, size=size) if c == compiler] for compiler in ALL}
    assert len(set(map(repr, got.values()))) == 1, got   # every compiler has every row
    return got["ritz1"]


@pytest.mark.unit
def test_a_chunk_holds_rows_of_one_import_set_and_every_row_once():
    rows = [_imports_row("a1", ["gvec"]), _imports_row("n1", []), _imports_row("a2", ["gvec"]),
            _imports_row("b1", ["gvec", "str"]), _imports_row("n2", []), _imports_row("a3", ["gvec"]),
            _imports_row("b2", ["str", "gvec"]), _imports_row("a4", ["gvec"])]
    # By first appearance, each set in source order and cut at `size`; an
    # import set is the lines, not their order.
    got = _chunk_ids(rows, 2)
    assert got == [["a1", "a2"], ["a3", "a4"], ["n1", "n2"], ["b1", "b2"]], got


@pytest.mark.unit
def test_rows_chunk_in_source_order_where_one_set_a_chunk_takes_more_chunks():
    # Apart, a1-a3 and n1 are 3 chunks of 2; in order, 2.  The test count stays.
    rows = [_imports_row("a1", ["gvec"]), _imports_row("a2", ["gvec"]), _imports_row("a3", ["gvec"]),
            _imports_row("n1", [])]
    got = _chunk_ids(rows, 2)
    assert got == [["a1", "a2"], ["a3", "n1"]], got


# ---- a table whose rows import ritzlib: `ritzlib_build` (AGAST #3906) ------
#
# One way to link what a row imports: every ritzlib module it imports,
# transitively, compiled once per process per compiler and linked onto
# for_header's batch build.  #3889's other way, a build.py package per chunk,
# paid a python and a cold build cache of every module per chunk.

HASHMAP = """\
import ritzlib.hashmap

pub fn main() -> i32
    var m = hashmap_i64_new()
    m.insert(3, 40)
    m.insert(5, 2)
    return (m.get(3) + m.get(5)) as i32
"""


@pytest.mark.integration
def test_a_row_links_every_ritzlib_module_it_imports(ritz1_bin, tmp_path):
    # ritzlib.hashmap is beyond the allocator's units, and its `impl Drop`
    # method is not `pub`: ritz0 has to compile it as a library module.
    rows = [Row("hashmap", ALL, Run(HASHMAP, 42))]
    for compiler in ALL:
        assert_ritzlib_rows(compiler, rows, ritz1_bin, tmp_path / compiler)


# ---- a dict table: rows named, gaps strict, refusals where `^` is (#3518) --
#
# Through test_ref_into_value.py's build, as `assert_runs` / `assert_refusals`
# are called; ritz1 only, as above.

MAIN = "pub fn main() -> i32\n    {}\n"
# Same `f` spelled differently per row: the batch renames it, and each row
# still answers for itself.
F = "fn f() -> i32\n    return {}\n\n" + MAIN.format("return f()")
REFUSED = MAIN.format("let x: i32 = ^true\n    return 0")


def _failure(call):
    with pytest.raises(AssertionError) as exc:
        call()
    return str(exc.value)


def _named(failure):
    """The rows a table's failure names, with their detail or past it."""
    detailed = re.findall(r"^ritz1 (\w+): ", failure, re.MULTILINE)
    past = re.search(r"\.\.\.and \d+ more: (.*)$", failure)
    return detailed + (past.group(1).split(", ") if past else [])


@pytest.mark.integration
def test_a_run_table_names_each_failing_row(tmp_path):
    rows = {"right": (MAIN.format(3), 3), "wrong": (MAIN.format(4), 5),
            "gap_that_passes": (MAIN.format(6), 6), "gap_that_fails": (MAIN.format(7), 8),
            "f3": (F.format(3), 3), "f4": (F.format(4), 3), "unbuilt": (REFUSED.replace("^", ""), 0)}
    gaps = {"gap_that_passes": 101, "gap_that_fails": 102}
    got = _failure(lambda: assert_runs("ritz1", tmp_path, rows, gaps))
    assert got.startswith("ritz1: 4 of 7 rows failed"), got
    assert _named(got) == ["wrong", "gap_that_passes", "f4", "unbuilt"], got
    assert "ritz1 wrong: want exit 5, got 4" in got
    assert "ritz1 f4: want exit 3, got 4" in got
    assert "ritz1 unbuilt: want exit 0, but it didn't compile and link" in got
    assert "ritz1 gap_that_passes: passes, but is listed as a gap of AGAST #101" in got


@pytest.mark.integration
def test_a_refusal_table_names_each_failing_row(tmp_path):
    shared = "struct C\n    x: i32\n\nfn g(p: @C)\n    {}p.x = 3\n\n" + MAIN.format(0)
    message = "cannot write through an `@T`: make it `@&T`"
    rows = {"refused_there": (shared.format("^"), message),
            "refused_elsewhere": (shared.format("") + "    ^0\n", message),
            "part_there": (shared.format("^"), message[:-1]),
            "prefix_there": (REFUSED, Prefix("")),
            "anywhere": (REFUSED.replace("^", ""), ""),
            "prefix_elsewhere": (REFUSED.replace("^true", "true^"), Prefix("")),
            "accepted": (MAIN.format(0), "")}
    got = _failure(lambda: assert_refusals("ritz1", tmp_path, rows))
    assert got.startswith("ritz1: 4 of 7 rows failed"), got
    assert _named(got) == ["refused_elsewhere", "part_there", "prefix_elsewhere", "accepted"], got
    assert f"ritz1 refused_elsewhere: want a diagnostic {message!r} at main.ritz:9:5" in got
    assert "ritz1 part_there: want a diagnostic " in got   # the whole message, unless a Prefix
    assert "ritz1 prefix_elsewhere: want a diagnostic starting '' at main.ritz:2:22" in got
    assert "ritz1 accepted: want it refused" in got


@pytest.mark.unit
def test_a_long_failure_names_the_rows_past_its_detail():
    failures = [(f"r{i}", f"ritz1 r{i}: want exit 0, got 1") for i in range(SHOWN + 2)]
    got = _failure(lambda: _assert_none("ritz1", failures, 30))
    assert got.startswith(f"ritz1: {SHOWN + 2} of 30 rows failed"), got
    assert f"ritz1 r{SHOWN - 1}: want exit 0" in got and f"ritz1 r{SHOWN}: want" not in got
    assert got.endswith(f"...and 2 more: r{SHOWN}, r{SHOWN + 1}")
