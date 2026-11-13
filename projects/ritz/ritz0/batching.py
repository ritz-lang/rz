"""One compile for a matrix's rows, per compiler (AGAST #2806).

A ritz0 pytest matrix row compiles, links and runs one small program.  The
compile and link are most of a row's cost (docs/TESTING.md, "What a ritz0
pytest case costs"), so a batched test file pays them once per CHUNK rows:

* **Run rows.** Each row's program is merged into one: its `main` becomes
  `fn __row<i>() -> i32`, and the merged `main(argc, argv)` returns row i's
  answer when started with i extra arguments.  One compile and one link; each
  row then runs in its own process, so a crash or a stray global in one row
  is that row's alone.
* **Refusal rows.** All three compilers report every error in a file, so the
  rows' programs are merged the same way and compiled once; each row is given
  the diagnostics that land inside its own lines, and the spot its own
  marker moved to.

Names that two rows define differently (`f`, `g`, `H`, an enum's variants, a
method of a shared type) are renamed per row, `f` -> `f__r3`, everywhere in
that row outside strings and comments; an item every row spells the same is
emitted once under its own name.  A row's diagnostics come back with the
suffixes taken off.

**A batch can only pass a row, never fail it.**  The harness function
(`_run`, `_assert_refused`, ...) asks `run()` / `refused()` first; `None`
means "no batched answer" and the harness compiles the row on its own, as it
always did.  A batch that fails to compile is split: rows with an error
inside their own lines drop out, a failure nobody owns halves the batch.  And
if a test fails on a batched answer, conftest's `pytest_pyfunc_call` runs it
again with batching off, so every failure, and its message, is the row's own
per-row compile.  `RITZ_TEST_BATCH=0` turns batching off.

How the harness learns the other rows: on its first call in a batched test,
the helper runs each sibling test in the chunk (same function, same
`compiler` parameter) in *record* mode, where the harness call raises
`_Recorded` carrying the program instead of compiling it.  The answers go to
a file under the session's shared basetemp, under a lock, so each chunk is
compiled once per session whichever xdist worker asks first.  A row's answer
is keyed by its test's node id and the hash of its program: a test whose
live program differs from the recorded one gets no batched answer.

A test file opts in with `pytestmark = [..., pytest.mark.batched]`.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

CHUNK = int(os.environ.get("RITZ_TEST_BATCH_CHUNK", "48"))
MARK = "\x01"  # stands in for a refusal row's `^` while its program is merged

_HEADER = re.compile(
    r"(?:pub\s+)?(?:extern\s+)?(fn|struct|enum|union|trait|type|const|var|let|static)\s+([A-Za-z_]\w*)")
_IMPL = re.compile(r"impl\b(?:\s*<[^>]*>)?\s+(?:([A-Za-z_]\w*)(?:<[^>]*>)?\s+for\s+)?([A-Za-z_]\w*)")
_METHOD = re.compile(r"^[ \t]+(?:pub\s+)?fn\s+([A-Za-z_]\w*)", re.MULTILINE)
_VARIANT = re.compile(r"^[ \t]+([A-Za-z_]\w*)\s*(?:\(.*\))?\s*(?:#.*)?$")
_MAIN = re.compile(r"(?:pub\s+)?fn\s+main\s*\(\s*\)\s*->\s*i32\s*")
# Strings, chars and comments are copied as they are; words are renamed.
_TOKENS = re.compile(r'(?P<s>[cb]?"(?:\\.|[^"\\\n])*")|(?P<c>\'(?:\\.|[^\'\\\n])+\')'
                     r'|(?P<k>#[^\n]*)|(?P<w>[A-Za-z_]\w*)')
_SUFFIX = re.compile(r"\b([A-Za-z_]\w*?)__r\d+\b")
_ROW_FN = "__row{}"


# ---- merge: pure text -------------------------------------------------------

@dataclass
class _Item:
    text: str           # the item, attributes and leading comments included, "\n"-terminated
    kind: str           # "import", "main", "impl", "item"
    names: tuple = ()   # top-level names it defines
    target: str = ""    # an impl's type
    methods: tuple = ()  # an impl's method names


@dataclass
class Merged:
    text: str
    ok: list            # per row: whether it is in the program
    regions: list       # per row: (first line, last line), 1-based, or None
    marks: list = field(default_factory=list)  # per row: "line:col" of its MARK, or None


def _split(program: str) -> list:
    """Top-level items: a column-0 line and the indented or blank lines after it."""
    items, cur, lead = [], None, []
    for line in program.splitlines(keepends=True):
        if not line.endswith("\n"):
            line += "\n"
        top = line[0] not in " \t\n"
        if top and line.startswith(("#", "[[")):
            if cur is not None:
                items.append(cur)
                cur = None
            lead.append(line)
        elif top:
            if cur is not None:
                items.append(cur)
            cur, lead = lead + [line], []
        elif cur is not None:
            cur.append(line)
        else:
            lead.append(line)
    if cur is not None:
        items.append(cur)
    out = []
    for lines in items:
        while lines and not lines[-1].strip():
            lines.pop()
        while lines and not lines[0].strip():
            lines.pop(0)
        out.append(_classify("".join(lines)))
    return out


def _classify(text: str) -> _Item:
    head = next(ln for ln in text.splitlines() if ln[:1] not in ("#", "[") and ln.strip())
    if head.startswith("import "):
        return _Item(text, "import")
    if _MAIN.fullmatch(head):
        return _Item(text, "main")
    if head.startswith("impl"):
        m = _IMPL.match(head)
        return _Item(text, "impl", target=m.group(2) if m else "",
                     methods=tuple(_METHOD.findall(text)))
    m = _HEADER.match(head)
    if not m:
        return _Item(text, "item")
    names = [m.group(2)]
    if m.group(1) == "enum":
        body = text.splitlines()[text.splitlines().index(head) + 1:]
        depth = min((len(ln) - len(ln.lstrip()) for ln in body if ln.strip()), default=0)
        names += [v.group(1) for ln in body if ln.strip() and len(ln) - len(ln.lstrip()) == depth
                  for v in [_VARIANT.match(ln)] if v]
    return _Item(text, "item", names=tuple(names))


def _words(text: str) -> set:
    return {m.group("w") for m in _TOKENS.finditer(text) if m.group("w")}


def _rename(text: str, names: dict) -> str:
    if not names:
        return text
    return _TOKENS.sub(lambda m: names.get(m.group("w"), m.group("w")) if m.group("w") else m.group(0),
                       text)


def merge(programs: list) -> Merged:
    """One program answering for every row of `programs` (see the module doc)."""
    rows = [_split(p) for p in programs]
    ok = [sum(it.kind == "main" for it in items) == 1 for items in rows]
    rows = [items if good else [] for items, good in zip(rows, ok)]

    def defs(it):
        return [("", n) for n in it.names] + [(it.target, m) for m in it.methods]

    # An item spelled the same by every row that has it is emitted once, unless it
    # defines or uses a name that is renamed.  Grow the renamed set to a fixpoint.
    unshared: set = set()  # texts that are emitted per row
    while True:
        counts: dict = {}
        for items in rows:
            for it in items:
                if it.kind in ("import", "main"):
                    continue
                for key in defs(it):
                    counts.setdefault(key, set()).add(
                        it.text if it.text not in unshared and MARK not in it.text else id(it))
        clashing = {key for key, texts in counts.items() if len(texts) > 1}
        renamed = {name for _, name in clashing}
        grew = False
        for items in rows:
            for it in items:
                if it.kind in ("import", "main") or it.text in unshared:
                    continue
                if MARK in it.text or (_words(it.text) & renamed):
                    unshared.add(it.text)
                    grew = True
        if not grew:
            break

    imports, shared, seen = [], [], set()
    for items in rows:
        for it in items:
            if it.kind == "import":
                for line in it.text.splitlines():
                    if line.startswith("import ") and line not in imports:
                        imports.append(line)
            elif it.kind != "main" and it.text not in unshared and MARK not in it.text \
                    and it.text not in seen:
                seen.add(it.text)
                shared.append(it.text)

    out = [*imports, ""] if imports else []
    for text in shared:
        out += [*text.rstrip("\n").split("\n"), ""]
    regions, marks = [], []
    for i, items in enumerate(rows):
        if not items:
            regions.append(None)
            marks.append(None)
            continue
        names = {n: f"{n}__r{i}" for it in items if it.kind not in ("import", "main")
                 and (it.text in unshared or MARK in it.text)
                 for _, n in defs(it) if n in renamed}
        start = len(out) + 1
        for it in items:
            if it.kind == "import" or (it.kind != "main" and it.text not in unshared
                                       and MARK not in it.text):
                continue
            text = _rename(it.text, names)
            if it.kind == "main":
                lines = text.splitlines()
                at = next(j for j, ln in enumerate(lines) if _MAIN.fullmatch(ln))
                lines[at] = f"fn {_ROW_FN.format(i)}() -> i32"
                text = "\n".join(lines)
            out += [*text.rstrip("\n").split("\n"), ""]
        regions.append((start, len(out) - 1))
        marks.append(None)
    out.append("pub fn main(argc: i32, argv: **u8) -> i32")
    for i, good in enumerate(ok):
        if good:
            out += [f"    if argc == {i + 1}", f"        return {_ROW_FN.format(i)}()"]
    out += ["    0", ""]

    # Each MARK is in its own row's lines: note where, then take it out.
    for i, region in enumerate(regions):
        if region is None:
            continue
        for n in range(region[0] - 1, region[1]):
            col = out[n].find(MARK)
            if col >= 0:
                if marks[i] is None:
                    marks[i] = f"{n + 1}:{col + 1}"
                out[n] = out[n].replace(MARK, "")
    return Merged("\n".join(out), ok, regions, marks)


def row_of(merged: Merged, line: int):
    """Which row's lines `line` is in, or None (shared items, imports, `main`)."""
    for i, region in enumerate(merged.regions):
        if region and region[0] <= line <= region[1]:
            return i
    return None


def unrename(text: str) -> str:
    """A row's diagnostics in its own names."""
    return _SUFFIX.sub(r"\1", text)


def _located(output: str, filename: str):
    """(line, text) for each output line located in `filename`."""
    pat = re.compile(rf"(?:^|[\s/]){re.escape(filename)}:(\d+):\d+")
    for text in output.splitlines():
        m = pat.search(text)
        if m:
            yield int(m.group(1)), text


# ---- runners ----------------------------------------------------------------

def run_rows(compiler: str, programs: list, build, work: Path, filename: str = "main.ritz") -> list:
    """Each row's exit code, or None where the batch has no answer for it.

    `build(compiler, src, work) -> (ok, output, exe)` compiles and links the
    program at `src` into `work` the way the harness would.
    """
    answers = [None] * len(programs)
    counter = [0]

    def solve(idx):
        if not idx:
            return
        merged = merge([programs[i] for i in idx])
        live = [i for i, good in zip(idx, merged.ok) if good]
        if not live:
            return
        counter[0] += 1
        here = work / f"b{counter[0]}"
        here.mkdir(parents=True)
        src = here / filename
        src.write_text(merged.text)
        try:
            good, output, exe = build(compiler, src, here)
        except Exception as exc:  # noqa: BLE001 - a harness assert, a timeout: nobody's in particular
            good, output, exe = False, str(exc), None
        if not good:
            owners = {idx[r] for line, _ in _located(output, filename)
                      for r in [row_of(merged, line)] if r is not None}
            if owners:
                return solve([i for i in live if i not in owners])
            if len(live) > 1:
                half = len(live) // 2
                solve(live[:half])
                solve(live[half:])
            return
        for k, i in enumerate(idx):
            if not merged.ok[k]:
                continue
            try:
                code = subprocess.run([str(exe), *["-"] * k], capture_output=True,
                                      timeout=60, check=False).returncode
            except subprocess.TimeoutExpired:
                continue
            if code >= 0:
                answers[i] = code

    solve(list(range(len(programs))))
    return answers


def refuse_rows(compiler: str, programs: list, compile, work: Path, filename: str = "main.ritz") -> list:
    """Per row, (its diagnostics, where its MARK landed) or None.

    `compile(compiler, src, work) -> (returncode, output)`.  A row is answered
    only if the batch was refused and some diagnostic lands in its lines.

    ritz1 reports every error in a file, and so does ritz0's checker, but
    ritz0's emitter stops at its first.  So the rows answered are taken out
    and the rest compiled again, for as long as a round answers more than
    one row: a round that answers one is no cheaper than that row alone.
    """
    answers = [None] * len(programs)
    left = list(range(len(programs)))
    for n in range(len(programs)):
        merged = merge([programs[i] for i in left])
        here = work / f"r{n}"
        here.mkdir(parents=True)
        src = here / filename
        src.write_text(merged.text)
        try:
            code, output = compile(compiler, src, here)
        except Exception:  # noqa: BLE001 - no answer; the rows compile alone
            break
        if code == 0:
            break
        mine: dict = {}
        for line, text in _located(output, filename):
            r = row_of(merged, line)
            if r is not None:
                mine.setdefault(r, []).append(unrename(text))
        for r, lines in mine.items():
            answers[left[r]] = ("\n".join(lines) + "\n", merged.marks[r])
        left = [i for k, i in enumerate(left) if k not in mine and merged.ok[k]]
        if len(mine) < 2 or len(left) < 2:
            break
    return answers


# ---- the pytest side --------------------------------------------------------

class _Recorded(BaseException):
    """Raised by a harness call in record mode; carries the call."""

    def __init__(self, call):
        super().__init__()
        self.call = call


@dataclass
class _Context:
    item: object
    mode: str = "batch"      # "batch" or "record"
    calls: int = 0
    used: bool = False       # a batched answer was handed out


_active: _Context | None = None


def enabled() -> bool:
    return os.environ.get("RITZ_TEST_BATCH", "1") != "0"


def _digest(*parts) -> str:
    return hashlib.sha256("\0".join(map(str, parts)).encode()).hexdigest()[:20]


def _ask(kind, compiler, program, filename, at, worker):
    """The batched answer for the live test's first harness call, or None."""
    ctx = _active
    if ctx is None:
        return None
    marked = _insert_mark(program, at) if at else program
    if ctx.mode == "record":
        raise _Recorded((kind, compiler, marked, filename))
    n, ctx.calls = ctx.calls, ctx.calls + 1
    if n:
        return None
    answers = _chunk(ctx.item, kind, compiler, filename, worker)
    got = answers.get(ctx.item.nodeid)
    if not got or got[0] != _digest(marked) or got[1] is None:
        log = os.environ.get("RITZ_TEST_BATCH_LOG")
        if log:
            why = "unrecorded" if not got else "changed" if got[0] != _digest(marked) else "unanswered"
            with open(log, "a") as fh:
                fh.write(f"{os.getpid()} miss {why} {ctx.item.nodeid}\n")
        return None
    ctx.used = True
    return got[1]


def per_row() -> None:
    """Call first in a harness's per-row compile: while siblings are being
    recorded it ends the recording, and that row is left out of the batch."""
    if _active is not None and _active.mode == "record":
        raise _Recorded(None)


def run(compiler: str, program: str, build, filename: str = "main.ritz"):
    """Row's exit code from its chunk's batch, or None: compile it yourself.

    `build(compiler, src: Path, work: Path) -> (ok, output, exe)`.
    """
    return _ask("run", compiler, program, filename, None, build)


def refused(compiler: str, program: str, compile, at=None, filename: str = "main.ritz"):
    """(row's diagnostics, "line:col" of `at` in the batch), or None.

    `at` is the (line, col), 1-based, the row expects its diagnostic at; the
    "line:col" handed back is the same spot in the batch's text, to look for
    in the diagnostics instead.  `compile(compiler, src, work) -> (rc, output)`.
    """
    got = _ask("refused", compiler, program, filename, at, compile)
    return tuple(got) if got else None


def _insert_mark(program: str, at) -> str:
    line, col = at
    lines = program.split("\n")
    lines[line - 1] = lines[line - 1][:col - 1] + MARK + lines[line - 1][col - 1:]
    return "\n".join(lines)


_groups: dict = {}  # id(session) -> {key: [items]}


def _sibling_key(it):
    spec = getattr(it, "callspec", None)
    return (it.parent.nodeid, getattr(it, "originalname", it.name),
            spec.params.get("compiler") if spec else None)


def _groups_of(items) -> dict:
    groups: dict = {}
    for it in items:
        if it.get_closest_marker("batched") is not None and it.get_closest_marker("xfail") is None:
            groups.setdefault(_sibling_key(it), []).append(it)
    return groups


def assign_groups(items) -> None:
    """Put each chunk in its own `xdist_group`: one worker runs a chunk's rows.

    Under `--dist loadgroup` a chunk then compiles once on the worker that has
    it, while the other workers get on with other chunks; spread over workers,
    the rows of one chunk would queue on its lock instead.
    """
    if not enabled():
        return
    for group in _groups_of(items).values():
        for at in range(0, len(group), CHUNK):
            name = f"batch-{_digest(group[at].nodeid, CHUNK)[:10]}"
            for it in group[at:at + CHUNK]:
                it.add_marker(pytest.mark.xdist_group(name))


def _siblings(item) -> list:
    """The tests that batch with `item`: same function, same `compiler`, no xfail mark."""
    groups = _groups.get(id(item.session))
    if groups is None:
        groups = _groups[id(item.session)] = _groups_of(item.session.items)
    return groups.get(_sibling_key(item), [])


class _RecordingRequest:
    """`request` for a sibling being recorded: a marker it applies voids the row."""

    def __init__(self, real):
        self._real = real
        self.marked = False

    def applymarker(self, marker):
        self.marked = True

    def __getattr__(self, name):
        return getattr(self._real, name)


def _record(sibling, ctx):
    """What harness call `sibling` makes first, or None if it makes none we can batch."""
    kwargs, request = {}, None
    params = sibling.callspec.params if hasattr(sibling, "callspec") else {}
    fixtures = sibling._fixtureinfo.name2fixturedefs
    for name in sibling._fixtureinfo.argnames:
        if name in params:
            defs = fixtures.get(name) or ()
            if defs and getattr(defs[-1].func, "__name__", "") != "get_direct_param_fixture_func":
                return None  # an indirect parameter: its value is a fixture's, not ours to make
            kwargs[name] = params[name]
        elif name == "request":
            kwargs[name] = request = _RecordingRequest(ctx.item._request)
        elif name in ctx.item.funcargs:
            kwargs[name] = ctx.item.funcargs[name]
        else:
            return None
    ctx.mode = "record"
    try:
        sibling.obj(**kwargs)
    except _Recorded as rec:
        return None if request is not None and request.marked else rec.call
    except BaseException:  # noqa: BLE001 - skip, xfail, assert: not batchable
        return None
    finally:
        ctx.mode = "batch"
    return None


def _shared_dir(item) -> Path:
    base = item.config._tmp_path_factory.getbasetemp()
    root = base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base
    path = root / "ritz-batches"
    path.mkdir(exist_ok=True)
    return path


@contextlib.contextmanager
def _locked(path: Path):
    with open(path, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


_answers: dict = {}  # chunk key -> answers, this process's copy


def _chunk(item, kind, compiler, filename, worker) -> dict:
    """{nodeid: [digest, answer]} for `item`'s chunk, computed once per session."""
    sibs = _siblings(item)
    if item not in sibs:
        return {}
    at = sibs.index(item) // CHUNK * CHUNK
    chunk = sibs[at:at + CHUNK]
    key = _digest(chunk[0].nodeid, kind, compiler, filename, CHUNK)
    if key in _answers:
        return _answers[key]
    shared = _shared_dir(item)
    answers_path = shared / f"{key}.json"
    with _locked(shared / f"{key}.lock"):
        if answers_path.exists():
            _answers[key] = json.loads(answers_path.read_text())
            return _answers[key]
        t0 = time.monotonic()
        ctx = _active
        rows = []
        for sib in chunk:
            call = _record(sib, ctx)
            if call and call[0] == kind and call[1] == compiler and call[3] == filename:
                rows.append((sib.nodeid, call[2]))
        work = shared / key
        programs = [p for _, p in rows]
        if kind == "run":
            got = run_rows(compiler, programs, worker, work, filename)
        else:
            got = refuse_rows(compiler, programs, worker, work, filename)
        answers = {nid: [_digest(p), g] for (nid, p), g in zip(rows, got)}
        log = os.environ.get("RITZ_TEST_BATCH_LOG")
        if log:
            with open(log, "a") as fh:
                fh.write(f"{os.getpid()} {kind} {compiler} {chunk[0].nodeid} chunk={len(chunk)} "
                         f"rows={len(rows)} answered={sum(g is not None for g in got)} "
                         f"secs={time.monotonic() - t0:.2f}\n")
        tmp = answers_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(answers))
        tmp.replace(answers_path)
        _answers[key] = answers
        return answers


def pyfunc_call(item):
    """conftest's `pytest_pyfunc_call` for a `batched` test; None for any other.

    Runs the test with batching on; if it fails on a batched answer, runs it
    again with batching off, so a failure is always the row's own.
    """
    global _active
    if item.get_closest_marker("batched") is None or not enabled():
        return None
    if item.get_closest_marker("xfail") is not None:
        return None
    args = {name: item.funcargs[name] for name in item._fixtureinfo.argnames}
    ctx = _active = _Context(item)
    try:
        item.obj(**args)
        return True
    except (pytest.skip.Exception, pytest.xfail.Exception):
        raise
    except Exception:
        if not ctx.used:
            raise
    finally:
        _active = None
    log = os.environ.get("RITZ_TEST_BATCH_LOG")
    if log:
        with open(log, "a") as fh:
            fh.write(f"{os.getpid()} retry {item.nodeid}\n")
    tmp = item.funcargs.get("tmp_path")
    if isinstance(tmp, Path):
        for child in tmp.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    item.obj(**args)
    return True
