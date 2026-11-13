"""AGAST #2516: an error inside an imported generic's instance names that module.

    import ritzlib.span
    # T implements Drop
    fn f(p: @Span<T>) -> i32
        return 0

instantiates span.ritz's `span_get<T>`, whose `return *(s.ptr + idx)` moves a T
out of a pointer.  ritz0 reports it at `.../ritzlib/span.ritz:91:12`; ritz1 and
ritz1_selfhosted printed `main.ritz:91:12`, a line main.ritz doesn't have,
because ref_check located every error in the driver's input file.

Whether a Span of a Drop T should be refused at all is #2159's question; this
only pins where the refusal points.  A user module (`cell.ritz`, written beside
main.ritz) is checked as well as ritzlib, so the rule isn't "ritzlib paths",
and so is an error inside a generic impl's method (#2913), whose instance
ritz1 located in main.ritz because impl methods carried no def_file.
"""

import os
import re
import subprocess

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

MOVE_OUT = "cannot move out of a reference"

CASES = {
    # (main.ritz, extra files, the file the error belongs to, line:col, message)
    "ritzlib_span": (
        f"import ritzlib.span\n\n{DROP_T}\nfn f(p: @Span<T>) -> i32\n    return 0\n",
        {},
        str(RITZ_ROOT / "ritzlib" / "span.ritz"),
        "91:12",
        MOVE_OUT,
    ),
    "user_module": (
        f"import cell\n\n{DROP_T}\nfn f(p: @Cell<T>) -> i32\n    return 0\n",
        {"cell.ritz": CELL},
        "cell.ritz",
        "5:12",
        MOVE_OUT,
    ),
    "user_method": (
        f"import cell\n\n{DROP_T}\nfn f(p: @Cell<T>) -> i32\n    return 0\n",
        {"cell.ritz": CELL_METHOD},
        "cell.ritz",
        "6:16",
        MOVE_OUT,
    ),
    "user_method_binder": (
        "import cell\n\nfn f(p: *Cell<i32>) -> i32\n    return p.get()\n",
        {"cell.ritz": CELL_BINDER},
        "cell.ritz",
        "8:13",
        "a local can't take the name of a const: 'K'",
    ),
    "main_method": (
        METHOD,
        {},
        "main.ritz",
        "8:9",
        "an `@T` doesn't fit an `@&T` slot",
    ),
}

ENTRY = "\npub fn main() -> i32\n    0\n"
LOC = re.compile(r"(\S+\.ritz):(\d+:\d+): (?:error: )?(.*)")


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(CASES))
def test_instance_error_names_its_module(compiler, case, tmp_path):
    main, extra, owner, where, message = CASES[case]
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
