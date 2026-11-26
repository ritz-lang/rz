"""AGAST #2516: an error inside an imported generic's instance names that module.

    import ritzlib.span
    # T implements Drop
    fn f(p: @Span<T>) -> i32
        let x: T = p.get(0)
        return 0

instantiates `impl<T> Span<T>`'s `get` (a method is specialised only once
called: AGAST #3617), and `get`'s `return *(self.ptr + idx)` moves a T out of
a pointer.  ritz0 reports it at `.../ritzlib/span.ritz` column 16, on `get`'s
`return *(self.ptr + idx)` (the line is derived from the source, not pinned, so
an edit above it does not look like a regression — AGAST #4554); ritz1 and
ritz1_selfhosted printed `main.ritz:92:12`, a line main.ritz doesn't have,
because ref_check located every error in the driver's input file.

Whether a Span of a Drop T should be refused at all is #2159's question; this
only pins where the refusal points.  A user module (`cell.ritz`, written beside
main.ritz) is checked as well as ritzlib, so the rule isn't "ritzlib paths",
and so is an error inside a generic impl's method (#2913), whose instance
ritz1 located in main.ritz because impl methods carried no def_file.

AGAST #4844: such an error is followed by where the instance was
instantiated, one `<file>:<line>:<col>: note:` line per step, innermost
first, down to the first non-generic body: `p.get()` in main.ritz, and in
`user_module` first `cell_get<T>(self)` in cell.ritz's `Cell<T>.get`, and
`v.get(0)` for ritzlib's `Vec<T>.get` (gvec.ritz) on a move-only T.  An instance several places name reports the first, with
"(and N more)" (`ritzlib_vec`); an error in a non-generic body gets no note
(`main_method`, `plain_fn`).  Every error class carries them: the move
checker's, a slot rule's (`slot_rule`) and the emitter's (`emit_match`).
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
from ritz0_inproc import run_ritz0
from test_ref_into_value import COMPILERS, RITZ1_BUILD, RITZ_ROOT

pytestmark = pytest.mark.integration

DROP_T = """\
struct T
    id: i32

impl Drop for T
    fn drop(self: @&T)
        self.id = 0
"""

# A Span-shaped generic: the impl's `get` instantiates `cell_get<T>` at line 5.
CELL = """\
pub struct Cell<T>
    ptr: *T

pub fn cell_get<T>(c: *Cell<T>) -> T
    return *(c.ptr + 0)

impl<T> Cell<T>
    pub fn get(self: *Cell<T>) -> T
        return cell_get<T>(self)
"""

# AGAST #2913: the move is in the generic impl's own method, at 6:16.
CELL_METHOD = """\
pub struct Cell<T>
    ptr: *T

impl<T> Cell<T>
    pub fn get(self: *Cell<T>) -> T
        return *(self.ptr + 0)
"""

# The same method's file names binder_check's refusal at 8:13, which it judges
# for an imported generic impl only once the method has a def_file.
CELL_BINDER = """\
pub const K: i32 = 3

pub struct Cell<T>
    ptr: *T

impl<T> Cell<T>
    pub fn get(self: *Cell<T>) -> i32
        let K: i32 = 1
        K
"""

# The `@S` receiver's push wants `@&Vec`: an error at 8:9 in main.ritz's own method.
METHOD = """\
import ritzlib.gvec

struct S
    v: Vec<u8>

impl S
    fn add(self: @S)
        self.v.push(3 as u8)
"""

# AGAST #4844: two calls make one instance, Vec<T>.get, reported at the first.
VEC_GET = f"""import ritzlib.gvec

{DROP_T}
fn f(v: @Vec<T>) -> i32
    let x: T = v.get(0)
    return 0

fn g(v: @Vec<T>) -> i32
    let y: T = v.get(1)
    return 0
"""

# A non-generic body's own refusal: no instance, so no note.
PLAIN = f"""{DROP_T}
fn f(p: *T) -> i32
    let x: T = *p
    return 0
"""

# Every error class carries the notes, not only the move checker's: a slot
# rule the typing pass judges per instance (§13.2), and a match the emitter
# finds non-exhaustive while lowering the instance.
SLOT = """struct C
    x: i32

fn g<T>(r: *T) -> T
    return r

fn f(r: *C) -> C
    g<C>(r)
"""

MATCH = """enum E
    A
    B

fn g<T>(x: T, e: E) -> i32
    match e
        E.A => 1

fn f() -> i32
    g<i32>(1, E.A)
"""

MOVE_OUT = "cannot move out of a reference"

# Each case pins the owning file, the column and the message.  The *line* is
# derived from the source at run time by finding `marker` (a unique substring
# of the offending line), so an edit above the site in span.ritz/string.ritz
# shifts both the compiler's report and the expectation together instead of
# redding the gate with a stale pin that looks like a regression (AGAST #4554).
#
# `notes` is the instantiation chain the error is followed by, innermost first
# (AGAST #4844): each (file, marker, column, tail), located as the error is;
# `tail` is what follows "instantiated here", "(and N more)" for a deduped one.
#
# (main.ritz, extra files, the file the error belongs to, marker, column, message, notes)
CASES = {
    "ritzlib_span": (
        f"import ritzlib.span\n\n{DROP_T}\nfn f(p: @Span<T>) -> i32\n    let x: T = p.get(0)\n    return 0\n",
        {},
        str(RITZ_ROOT / "ritzlib" / "span.ritz"),
        "return *(self.ptr + idx)",
        16,
        MOVE_OUT,
        [("main.ritz", "p.get(0)", 16, "")],
    ),
    "user_module": (
        f"import cell\n\n{DROP_T}\nfn f(p: @Cell<T>) -> i32\n    let x: T = p.get()\n    return 0\n",
        {"cell.ritz": CELL},
        "cell.ritz",
        "return *(c.ptr + 0)",
        12,
        MOVE_OUT,
        [
            ("cell.ritz", "return cell_get<T>(self)", 16, ""),
            ("main.ritz", "p.get()", 16, ""),
        ],
    ),
    "user_method": (
        f"import cell\n\n{DROP_T}\nfn f(p: @Cell<T>) -> i32\n    let x: T = p.get()\n    return 0\n",
        {"cell.ritz": CELL_METHOD},
        "cell.ritz",
        "return *(self.ptr + 0)",
        16,
        MOVE_OUT,
        [("main.ritz", "p.get()", 16, "")],
    ),
    "user_method_binder": (
        "import cell\n\nfn f(p: *Cell<i32>) -> i32\n    return p.get()\n",
        {"cell.ritz": CELL_BINDER},
        "cell.ritz",
        "let K: i32 = 1",
        13,
        "a local can't take the name of a const: 'K'",
        None,  # judged on the template, not an instance: notes or none
    ),
    "main_method": (
        METHOD,
        {},
        "main.ritz",
        "self.v.push(3 as u8)",
        9,
        "an `@T` doesn't fit an `@&T` slot",
        [],
    ),
    "ritzlib_vec": (
        VEC_GET,
        {},
        str(RITZ_ROOT / "ritzlib" / "gvec.ritz"),
        "return *(self.data + idx)",
        16,
        MOVE_OUT,
        [("main.ritz", "v.get(0)", 16, " (and 1 more)")],
    ),
    "slot_rule": (
        SLOT,
        {},
        "main.ritz",
        "    return r",
        12,
        "a reference or pointer doesn't fit a by-value slot",
        [("main.ritz", "g<C>(r)", 5, "")],
    ),
    "emit_match": (
        MATCH,
        {},
        "main.ritz",
        "    match e",
        5,
        "non-exhaustive match: missing B",
        [("main.ritz", "g<i32>(1, E.A)", 5, "")],
    ),
    "plain_fn": (
        PLAIN,
        {},
        "main.ritz",
        "let x: T = *p",
        16,
        MOVE_OUT,
        [],
    ),
}

ENTRY = "\npub fn main() -> i32\n    0\n"
LOC = re.compile(r"(\S+\.ritz):(\d+:\d+): (?:error: )?(.*)")
PASS = re.compile(r"^[A-Z]\w* error: ")
NOTE = re.compile(r"(\S+\.ritz):(\d+:\d+): note: `[^`]+` instantiated here(.*)$")


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(CASES))
def test_instance_error_names_its_module(compiler, case, tmp_path):
    main, extra, owner, marker, column, message, notes = CASES[case]
    where = _where(_source(main, extra, owner), marker, column)
    work = tmp_path / f"{case}_{compiler}"
    work.mkdir()
    for name, text in extra.items():
        (work / name).write_text(text)
    path = work / "main.ritz"
    path.write_text(main + ENTRY)
    ll = work / "main.ll"
    comp = _emit(compiler, path, ll, work)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {case}:\n{out[-2000:]}"
    found = [(f, w) for f, w, m in LOC.findall(out) if m.startswith(message)]
    assert found, f"{compiler}: {case} gave no located `{message}`:\n{out[-2000:]}"
    owner_path = owner if os.path.isabs(owner) else str(work / owner)
    # ritz0 also reports gvec.ritz's own refusals (#2159): judge the one at `where`.
    at = [f for f, w in found if w == where]
    assert at, f"{compiler}: {case}, wanted {where}, got {found}"
    wrong = [f for f in at if not _same_file(f, owner_path, work)]
    assert not wrong, f"{compiler}: {case}, wanted {owner}:{where}, got {wrong}"
    if owner != "main.ritz":
        blamed = [(f, w) for f, w in found if _same_file(f, str(path), work)]
        assert not blamed, f"{compiler}: {case} blamed main.ritz: {blamed}"
    if notes is not None:
        _assert_notes(
            compiler,
            case,
            out,
            owner_path,
            where,
            message,
            [_note_at(main, extra, n) for n in notes],
            work,
        )


def _note_at(main, extra, note):
    """(file, `line:col`, tail) a `notes` entry names."""
    file, marker, column, tail = note
    return file, _where(_source(main, extra, file), marker, column), tail


def _assert_notes(compiler, case, out, owner_path, where, message, want, work):
    """The error at `owner_path:where` is followed by `want`'s note lines,
    in order, and no others (AGAST #4844)."""
    # ritz0 heads the first line with its pass ("Compiler error: ").
    lines = [PASS.sub("", line) for line in out.splitlines()]
    starts = [
        i
        for i, line in enumerate(lines)
        if (m := LOC.match(line))
        and m.group(2) == where
        and m.group(3).startswith(message)
        and _same_file(m.group(1), owner_path, work)
    ]
    assert starts, f"{compiler}: {case} no error at {where}:\n{out[-2000:]}"
    got = []
    for line in lines[starts[0] + 1 :]:
        m = NOTE.match(line)
        if m is None:
            break
        got.append((m.group(1), m.group(2), m.group(3)))
    assert len(got) == len(want), (
        f"{compiler}: {case} notes {got}, wanted {want}:\n{out[-2000:]}"
    )
    for (gf, gw, gt), (wf, ww, wt) in zip(got, want):
        wanted = wf if os.path.isabs(wf) else str(work / wf)
        assert _same_file(gf, wanted, work) and gw == ww and gt == wt, (
            f"{compiler}: {case} note {gf}:{gw}{gt}, wanted {wf}:{ww}{wt}"
        )


def _source(main, extra, owner):
    """The text the error site lives in: main+ENTRY, a sibling module, or disk."""
    if os.path.isabs(owner):
        return Path(owner).read_text()
    if owner in extra:
        return extra[owner]
    assert owner == "main.ritz", owner
    return main + ENTRY


def _where(source, marker, column):
    """`line:col` for the one line containing `marker`, derived from the source."""
    hits = [n for n, line in enumerate(source.splitlines(), 1) if marker in line]
    assert len(hits) == 1, f"marker {marker!r} must name one line, found at {hits}"
    return f"{hits[0]}:{column}"


def _emit(compiler, path, ll, work):
    # A sibling module resolves through RITZ_PATH, as ritzlib does.
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{work}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run(
        [str(binary), str(path), "-o", str(ll)],
        check=False,
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _same_file(printed, want, work):
    """`printed` names `want`, read relative to `work` (ritz1 prints paths as given)."""
    full = printed if os.path.isabs(printed) else os.path.join(work, printed)
    return os.path.realpath(full) == os.path.realpath(want)
