"""AGAST #2039: a bare variant name that two or more user enums declare is a
located error in every value position, in ritz0 and in ritz1, whatever the
expected type.

    enum S          enum T
        A               B
        B               C

    let s: S = B    # error: ambiguous enum variant 'B': declared by enum 'S'
    let x = B       #        and enum 'T'; qualify it, e.g. 'S.B'

Before this, ritz0 took `let s: S = B` as S.B through the expected type and
`let x = B` as T.B, the last-declared enum, silently; ritz1 (#1600) already
rejected both.  The user chose to be strict (option a): it can be relaxed to
expected-type disambiguation later without breaking code, but not the reverse.
The call forms `B()` / `Holds(x)` were last-declared-wins in BOTH compilers;
they are now the same error.

The diagnostic names the two alphabetically-first declaring enums, so ritz0
(which registers imported enums first) and ritz1 (own module first) print the
same text for a cross-module clash.

Match arms are the exception, in both compilers: a bare `B =>` arm resolves
against the scrutinee's enum, which is known, so it is not ambiguous and stays
legal (`match_arms_resolve_by_scrutinee` pins this).

Controls: a variant only one enum declares stays legal next to an ambiguous
one; the qualified form compiles; a local named like the variant shadows it
(#2038); and one enum recorded twice through an import cycle is one enum.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"
COMPILERS = ("ritz0", "ritz1")

# Lines 1-12.  B is ambiguous (S, T); so is Holds (E, F).  A, C, Empty and
# Other each have one declarer.
HEADER = """\
enum S
    A
    B
enum T
    B
    C
enum E
    Empty
    Holds(i32)
enum F
    Holds(i32)
    Other
"""

MSG_B = "ambiguous enum variant 'B': declared by enum 'S' and enum 'T'; qualify it, e.g. 'S.B'"
MSG_HOLDS = (
    "ambiguous enum variant 'Holds': declared by enum 'E' and enum 'F'; "
    "qualify it, e.g. 'E.Holds'"
)

# name -> (body after HEADER, line, column of the offending name, message)
AMBIGUOUS = {
    "typed_let": (
        """\
pub fn main() -> i32
    let s: S = B
    return 3
""",
        14,
        16,
        MSG_B,
    ),
    "untyped_let": (
        """\
pub fn main() -> i32
    let x = B
    return 3
""",
        14,
        13,
        MSG_B,
    ),
    "typed_var": (
        """\
pub fn main() -> i32
    var s: S = B
    return 3
""",
        14,
        16,
        MSG_B,
    ),
    "assignment": (
        """\
pub fn main() -> i32
    var s: S = S.A
    s = B
    return 3
""",
        15,
        9,
        MSG_B,
    ),
    "struct_field": (
        """\
struct P
    s: S
pub fn main() -> i32
    let p: P = P { s: B }
    return 3
""",
        16,
        23,
        MSG_B,
    ),
    "argument": (
        """\
fn f(s: S) -> i32
    return 1
pub fn main() -> i32
    return f(B)
""",
        16,
        14,
        MSG_B,
    ),
    "return": (
        """\
fn g() -> S
    return B
pub fn main() -> i32
    return 3
""",
        14,
        12,
        MSG_B,
    ),
    "eq_right": (
        """\
pub fn main() -> i32
    let s: S = S.A
    if s == B
        return 1
    return 3
""",
        15,
        13,
        MSG_B,
    ),
    "eq_left": (
        """\
pub fn main() -> i32
    let s: S = S.A
    if B == s
        return 1
    return 3
""",
        15,
        8,
        MSG_B,
    ),
    "unit_ctor_typed": (
        """\
pub fn main() -> i32
    let s: S = B()
    return 3
""",
        14,
        16,
        MSG_B,
    ),
    "unit_ctor_untyped": (
        """\
pub fn main() -> i32
    let s = B()
    return 3
""",
        14,
        13,
        MSG_B,
    ),
    "payload_ctor_typed": (
        """\
pub fn main() -> i32
    let e: E = Holds(4)
    return 3
""",
        14,
        16,
        MSG_HOLDS,
    ),
    "payload_ctor_untyped": (
        """\
pub fn main() -> i32
    let e = Holds(4)
    return 3
""",
        14,
        13,
        MSG_HOLDS,
    ),
    "payload_ctor_argument": (
        """\
fn f(e: E) -> i32
    return 1
pub fn main() -> i32
    return f(Holds(4))
""",
        16,
        14,
        MSG_HOLDS,
    ),
}

# name -> (body after HEADER, exit code).  Each runs, and the exit code says
# which variant arrived.
LEGAL = {
    # A, C, Empty, Other have one declarer each: still legal bare.
    "unique_variants": (
        """\
fn tag_s(s: S) -> i32
    match s
        A => 1
        B => 2
fn tag_t(t: T) -> i32
    match t
        B => 10
        C => 20
pub fn main() -> i32
    let s: S = A
    let t = C
    let e: E = Empty
    var r: i32 = tag_s(s) + tag_t(t)
    match e
        Empty => r = r + 100
        Holds(v) => r = r + v
    return r
""",
        121,
    ),
    # The qualified form of an ambiguous name compiles.
    "qualified": (
        """\
pub fn main() -> i32
    let s: S = S.B
    let t: T = T.B
    let a: i32 = match s
        A => 1
        B => 2
    let b: i32 = match t
        B => 10
        C => 20
    return a + b
""",
        12,
    ),
    # Bare arms resolve by the scrutinee's enum in both compilers, so `B =>`
    # is S.B (tag 1) against an S and T.B (tag 0) against a T: 2 + 10.
    "match_arms_resolve_by_scrutinee": (
        """\
pub fn main() -> i32
    let s: S = S.B
    let t: T = T.B
    let a: i32 = match s
        A => 1
        B => 2
    let b: i32 = match t
        B => 10
        C => 20
    return a + b
""",
        12,
    ),
    # A payload arm, likewise: `Holds(v)` against an E binds E's payload.
    "payload_arm_resolves_by_scrutinee": (
        """\
fn mk() -> E
    let e: E = Empty
    return e
pub fn main() -> i32
    let e: E = mk()
    match e
        Empty => return 7
        Holds(v) => return v
""",
        7,
    ),
    # Two specializations of one generic enum, Option$i64 and Option$i32
    # (test_unambiguous_forms_still_compile adds the import),
    # both declare Some / None, but they are not user enums: bare Some /
    # None still resolve by the expected type (ritz0's first sweep for #2039
    # flagged ~100 such sites in ritzlib, mausoleum and angelo).
    "generic_specializations_not_ambiguous": (
        """\
fn wide(f: i32) -> Option<i64>
    if f == 1
        return Some(40)
    return None
fn narrow(f: i32) -> Option<i32>
    if f == 1
        return Some(2)
    return None
pub fn main() -> i32
    var r: i32 = 0
    match wide(1)
        Some(v) => r = r + v as i32
        None => r = r + 100
    match narrow(1)
        Some(v) => r = r + v
        None => r = r + 100
    match narrow(0)
        Some(v) => r = r + 50
        None => r = r + 1
    return r
""",
        43,
    ),
    # A local named like the ambiguous variant is the local (#2038).
    "local_shadows_ambiguous": (
        """\
pub fn main() -> i32
    let B: i32 = 9
    return B
""",
        9,
    ),
}


def _compile(compiler, tmp_path, name, program, extra_path=None):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{extra_path or tmp_path}:{RITZ_ROOT}")
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        comp = subprocess.run(
            [str(RITZ1_BIN), str(src), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
    return comp, ll, src


def _link_run(compiler, tmp_path, name, lls):
    exe = tmp_path / f"{name}_{compiler}"
    cmd = ["clang", *map(str, lls), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        cmd.insert(1, str(RITZ_START))
    link = subprocess.run(cmd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _assert_located_error(compiler, comp, ll, src, line, col, msg):
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted it:\n{out[-2000:]}"
    assert not ll.exists(), f"{compiler} wrote output despite the error"
    # ritz0 prints the full path, ritz1 the name as given; both end in this.
    assert f"{src.name}:{line}:{col}: {msg}" in out, out[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(AMBIGUOUS))
def test_bare_ambiguous_variant_is_located_error(tmp_path, compiler, name):
    body, line, col, msg = AMBIGUOUS[name]
    comp, ll, src = _compile(compiler, tmp_path, name, HEADER + body)
    _assert_located_error(compiler, comp, ll, src, line, col, msg)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(LEGAL))
def test_unambiguous_forms_still_compile(tmp_path, compiler, name):
    body, expected = LEGAL[name]
    # Imports lead the file; the error tests' line numbers don't apply here.
    prelude = "import ritzlib.option\n" if "Option<" in body else ""
    comp, ll, _ = _compile(compiler, tmp_path, name, prelude + HEADER + body)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} rejected {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    assert _link_run(compiler, tmp_path, name, [ll]) == expected


# --- across modules -----------------------------------------------------------

# T lives in an imported module, S in the importer.  ritz0 registers the
# imported enum first and ritz1 the importer's own first; the message names
# the two declarers alphabetically, so both print 'S' then 'T'.
IMPORTED_T = """\
pub enum T
    B
    C

pub fn t_id() -> i32
    return 1
"""

IMPORTER = """\
import amb_t { T, t_id }

enum S
    A
    B

pub fn main() -> i32
    let x = B
    return t_id()
"""


# The importer's own enum sorts AFTER the imported one, so neither "own module
# first" nor "imports first" happens to give the alphabetical answer for both.
IMPORTER_U = IMPORTER.replace("enum S", "enum U")
MSG_B_TU = (
    "ambiguous enum variant 'B': declared by enum 'T' and enum 'U'; "
    "qualify it, e.g. 'T.B'"
)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize(
    "importer,msg", [(IMPORTER, MSG_B), (IMPORTER_U, MSG_B_TU)], ids=["own_S", "own_U"]
)
def test_ambiguity_across_an_import_names_both_alphabetically(
    tmp_path, compiler, importer, msg
):
    (tmp_path / "amb_t.ritz").write_text(IMPORTED_T)
    comp, ll, src = _compile(compiler, tmp_path, "importer", importer)
    _assert_located_error(compiler, comp, ll, src, 8, 13, msg)


# tempest's shape: cyc_tab imports cyc_ipc, which imports cyc_tab back, so
# TabState is recorded twice.  One enum recorded twice is not two enums.
CYCLE_TAB = """\
import cyc_ipc { ipc_id }

pub enum TabState
    TabIdle
    TabLoading

pub struct Tab
    id: i32
    state: TabState

pub fn tab_id(t: *Tab) -> i32
    return t.id

pub fn main() -> i32
    var t: Tab = Tab { id: 5, state: TabIdle }
    t.state = TabLoading
    let r: i32 = match t.state
        TabIdle => 1
        TabLoading => 20
    return r + ipc_id()
"""

CYCLE_IPC = """\
import cyc_tab { Tab }

pub fn ipc_id() -> i32
    return 2
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_enum_recorded_twice_via_import_cycle_is_not_ambiguous(tmp_path, compiler):
    (tmp_path / "cyc_ipc.ritz").write_text(CYCLE_IPC)
    (tmp_path / "cyc_tab.ritz").write_text(CYCLE_TAB)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    lls = []
    for stem in ("cyc_ipc", "cyc_tab"):
        src, ll = tmp_path / f"{stem}.ritz", tmp_path / f"{stem}_{compiler}.ll"
        if compiler == "ritz0":
            # ritz0 gives every module a _start unless told it is a library.
            lib = ["--no-runtime"] if stem == "cyc_ipc" else []
            comp = run_ritz0(
                [str(src), "-o", str(ll), *lib], cwd=tmp_path, env=env, timeout=300
            )
        else:
            comp = subprocess.run(
                [str(RITZ1_BIN), str(src), "-o", str(ll)],
                cwd=tmp_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
        assert comp.returncode == 0, (
            f"{compiler} failed on {stem}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
        )
        lls.append(ll)
    assert _link_run(compiler, tmp_path, "cyc", lls) == 22
