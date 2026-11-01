"""Regression tests for AGAST #1600 / #1610: ritz1 must accept a bare unit
variant of a user enum used as a value (`let s: S = B`, `tab.state =
TabLoading`, `var c: Color = Green`).

ritz1's `emit_expr_ident` resolved an identifier against constants, locals,
globals and functions, then reported `unknown identifier 'B'`.  The qualified
`S.B` and a bare `B` in a match arm already worked; only the bare value did
not.  That blocked tempest (tab.ritz, document.ritz) and test_level34.
#1610 also hid a second bug there: a unit variant with call syntax, `Red()`,
fell through to a fn call and stored an i64 into the `%Color` slot.

Every runnable program's exit code encodes which variant arrived, so a fix
that builds *a* value with the wrong tag is caught, not just a compile
failure.  ritz0 is run as the oracle.

A name declared as a variant by two enums is ambiguous: ritz1 reports a
located error rather than guessing.  (ritz0 picks by expected type, else the
last-declared enum; ritz1 has no user-enum expected-type threading.  The rule
is open in AGAST #2039.)
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

ENUM_S = """\
enum S
    A
    B
    C
"""

# --- forms #1600 / #1610 rejected -------------------------------------------

# The ticket's repro, verbatim.
REPRO = """\
enum S
    A
    B
pub fn main() -> i32
    let s: S = B
    return 3
"""

# A match over the bare value must pick B's arm (2), not A's (1) or C's (3).
LET_THEN_MATCH = (
    ENUM_S
    + """\
pub fn main() -> i32
    let s: S = B
    match s
        A => 1
        B => 2
        C => 3
"""
)

# The last variant: a tag of 0 or 1 would both be wrong.
LAST_VARIANT = (
    ENUM_S
    + """\
pub fn main() -> i32
    let s: S = C
    match s
        A => 1
        B => 2
        C => 3
"""
)

# test_level34's shape: `var` + reassignment with another bare variant.
VAR_REASSIGNED = (
    ENUM_S
    + """\
pub fn main() -> i32
    var s: S = A
    s = C
    match s
        A => 1
        B => 2
        C => 3
"""
)

# tempest tab.ritz: assigning to a struct field of enum type.
FIELD_ASSIGN = (
    ENUM_S
    + """\
struct Tab
    id: i32
    state: S
pub fn main() -> i32
    var t: Tab = Tab { id: 7, state: A }
    t.state = B
    match t.state
        A => 1
        B => t.id
        C => 3
"""
)

# Through a pointer to the struct, as tempest's `tab.state = ...` on a *Tab.
FIELD_ASSIGN_VIA_PTR = (
    ENUM_S
    + """\
struct Tab
    id: i32
    state: S
fn set_loading(t: *Tab)
    t.state = C
pub fn main() -> i32
    var t: Tab = Tab { id: 7, state: A }
    set_loading(@t)
    match t.state
        A => 1
        B => 2
        C => 3
"""
)

# tempest document.ritz: `node_new(0, NodeDocument, Unknown)`.
CALL_ARG = (
    ENUM_S
    + """\
fn which(x: i32, s: S) -> i32
    match s
        A => x + 1
        B => x + 2
        C => x + 3
pub fn main() -> i32
    return which(10, B)
"""
)

RETURNED = (
    ENUM_S
    + """\
fn get() -> S
    return C
pub fn main() -> i32
    match get()
        A => 1
        B => 2
        C => 3
"""
)

# Compared with `==` / `!=` against a bare variant on either side.
COMPARED = (
    ENUM_S
    + """\
pub fn main() -> i32
    let s: S = B
    var r: i32 = 0
    if s == B
        r = r + 10
    if s != A
        r = r + 20
    if C == s
        r = r + 40
    return r
"""
)

# Untyped binding: the slot must take the enum's type from the variant.
UNTYPED_LET = (
    ENUM_S
    + """\
pub fn main() -> i32
    let s = C
    match s
        A => 1
        B => 2
        C => 3
"""
)

# #1610's hidden second bug: a unit variant with call syntax, `C()`, fell
# through to a fn call returning i64, stored into the %S slot (asm-fail).
CALL_SYNTAX = (
    ENUM_S
    + """\
pub fn main() -> i32
    var s: S = C()
    match s
        A => 1
        B => 2
        C => 3
"""
)

# Untyped, so the slot's type comes from the ctor alone.
CALL_SYNTAX_UNTYPED = (
    ENUM_S
    + """\
pub fn main() -> i32
    let s = B()
    match s
        A => 1
        B => 2
        C => 3
"""
)

BROKEN_FORMS = {
    "call_syntax": CALL_SYNTAX,
    "call_syntax_untyped": CALL_SYNTAX_UNTYPED,
    "repro": REPRO,
    "let_then_match": LET_THEN_MATCH,
    "last_variant": LAST_VARIANT,
    "var_reassigned": VAR_REASSIGNED,
    "field_assign": FIELD_ASSIGN,
    "field_assign_via_ptr": FIELD_ASSIGN_VIA_PTR,
    "call_arg": CALL_ARG,
    "returned": RETURNED,
    "compared": COMPARED,
    "untyped_let": UNTYPED_LET,
}

# --- forms that already worked, pinned against regression --------------------

# A local named like a variant still reads the local.  ritz1-only: ritz0
# itself crashes on it ("Unknown enum type: i32"), AGAST #2038.
LOCAL_SHADOWS_VARIANT = (
    ENUM_S
    + """\
pub fn main() -> i32
    let B: i32 = 9
    return B
"""
)

QUALIFIED = (
    ENUM_S
    + """\
pub fn main() -> i32
    let s: S = S.B
    match s
        A => 1
        B => 2
        C => 3
"""
)

WORKING_FORMS = {
    "qualified": QUALIFIED,
}

# --- errors -------------------------------------------------------------------

# `B` is a variant of both S and T.
AMBIGUOUS = """\
enum S
    A
    B
enum T
    B
    C
pub fn main() -> i32
    let s: S = B
    return 3
"""

UNKNOWN_NAME = (
    ENUM_S
    + """\
pub fn main() -> i32
    let s: S = D
    return 3
"""
)


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
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


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    comp, ll, _ = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(1, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link ({name}):\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


EXPECTED = {
    "call_syntax": 3,
    "call_syntax_untyped": 2,
    "repro": 3,
    "let_then_match": 2,
    "last_variant": 3,
    "var_reassigned": 3,
    "field_assign": 7,
    "field_assign_via_ptr": 3,
    "call_arg": 12,
    "returned": 3,
    "compared": 30,
    "untyped_let": 3,
    "qualified": 2,
}

ALL_RUNNABLE = {**BROKEN_FORMS, **WORKING_FORMS}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL_RUNNABLE[name]) == EXPECTED[name]


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz1_matches_ritz0(tmp_path, name):
    assert _run("ritz1", tmp_path, name, ALL_RUNNABLE[name]) == EXPECTED[name]


@pytest.mark.integration
def test_ritz1_local_shadows_variant(tmp_path):
    """`let B: i32 = 9` reads the local, not S.B (which is tag 1)."""
    assert _run("ritz1", tmp_path, "shadow", LOCAL_SHADOWS_VARIANT) == 9


@pytest.mark.integration
def test_ritz1_ambiguous_variant_is_located_error(tmp_path):
    """`B` names a variant of S and of T: an error at the use, naming both."""
    comp, ll, src = _compile("ritz1", tmp_path, "ambiguous", AMBIGUOUS)
    assert comp.returncode != 0, "ritz1 accepted an ambiguous bare variant"
    assert not ll.exists(), "ritz1 wrote output despite the error"
    err = comp.stderr
    # file:line:col of the `B` in `let s: S = B` (line 8, column 16).
    assert re.search(rf"{re.escape(src.name)}:8:16:", err), err
    assert "ambiguous" in err and "'B'" in err, err
    assert "S" in err and "T" in err, err


@pytest.mark.integration
def test_ritz1_unknown_name_still_errors(tmp_path):
    """A name that is no variant, local, global, const or fn stays an error."""
    comp, ll, _ = _compile("ritz1", tmp_path, "unknown", UNKNOWN_NAME)
    assert comp.returncode != 0
    assert "unknown identifier 'D'" in comp.stderr, comp.stderr


# A payload variant used bare has no value without its payload: still an
# error, as in ritz0 ("Unknown identifier"), not a tag-only %E.
PAYLOAD_VARIANT_BARE = """\
enum E
    Empty
    Holds(i32)
pub fn main() -> i32
    let e: E = Holds
    return 3
"""


@pytest.mark.integration
def test_ritz1_bare_payload_variant_is_error(tmp_path):
    comp, ll, _ = _compile("ritz1", tmp_path, "payload_bare", PAYLOAD_VARIANT_BARE)
    assert comp.returncode != 0, "ritz1 built a payload variant with no payload"
    assert "unknown identifier 'Holds'" in comp.stderr, comp.stderr


# tempest's shape: tab.ritz imports ipc.ritz, which imports tab.ritz back, so
# ritz1 parses tab.ritz twice and records its enum twice.  One enum recorded
# twice is not two enums: the bare variant must still resolve.
CYCLE_TAB = """\
import cyc_ipc { ipc_id }

pub enum TabState
    TabIdle
    TabLoading
    TabError

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
        TabError => 3
    return r + ipc_id()
"""

CYCLE_IPC = """\
import cyc_tab { Tab }

pub fn ipc_id() -> i32
    return 2
"""


@pytest.mark.integration
def test_ritz1_variant_of_enum_recorded_twice_via_import_cycle(tmp_path):
    (tmp_path / "cyc_ipc.ritz").write_text(CYCLE_IPC)
    (tmp_path / "cyc_tab.ritz").write_text(CYCLE_TAB)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path}:{RITZ_ROOT}")
    lls = []
    for stem in ("cyc_ipc", "cyc_tab"):
        ll = tmp_path / f"{stem}.ll"
        comp = subprocess.run(
            [str(RITZ1_BIN), str(tmp_path / f"{stem}.ritz"), "-o", str(ll)],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert comp.returncode == 0, f"ritz1 failed on {stem}:\n{comp.stderr[-2000:]}"
        lls.append(str(ll))
    exe = tmp_path / "cyc"
    link = subprocess.run(
        ["clang", str(RITZ_START), *lls, "-o", str(exe), "-nostdlib"],
        capture_output=True,
        text=True,
    )
    assert link.returncode == 0, link.stderr[-2000:]
    assert subprocess.run([str(exe)], timeout=60).returncode == 22
