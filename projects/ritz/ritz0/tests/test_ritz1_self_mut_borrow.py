"""Regression tests for AGAST #1522: ritz1 must accept the `self:& R` and bare
`self:&` mutable-borrow receivers in an impl method.

ritz0 accepts it. ritz1's grammar had `IDENT COLON AMP type_spec` in `param`,
added by #1301 for free-function `name:& T` borrows, but no SELF version of
it. `type_spec` cannot start with `&`, so `self:& R` matched no `param`
alternative. The whole impl block failed to parse and ritz1 exited 1 with
`cannot parse item starting at 'impl R'`. angelo writes 68 methods this way,
so every angelo module cascaded.

The bare receiver `self:&` (type taken from the impl block) failed for the
same reason and is fixed alongside it.

The spaced spelling `self: &R` is NOT a valid form. ritz0 lexes `:&` as one
COLON_AMP token, so `: &R` is the removed legacy `&T` reference type and gets a
migration diagnostic (see LANGUAGE_SPEC 3.2). ritz1 lexed `:&` as COLON AMP
and accepted both spellings, for `self` and for free-function `r: &T` (#1301),
until AGAST #1565 gave it the same COLON_AMP token.  SPACED_LEGACY pins both
compilers' refusal.

Every runnable program returns 3 only if the receiver really is a mutable
borrow, meaning the write through `self` is visible in the caller. A fix that
parses the receiver but passes a copy returns 0, so it fails too. ritz0 is run
as the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _program(receiver: str) -> str:
    """The ticket's repro, with the receiver spelling substituted."""
    return f"""\
struct R
    pos: i64

impl R
    fn seek({receiver}, p: i64)
        self.pos = p

pub fn main() -> i32
    var r: R = R {{ pos: 0 }}
    r.seek(3)
    return r.pos as i32
"""


# --- forms that #1522 rejects -------------------------------------------------

BROKEN_FORMS = {
    # The ticket's repro: angelo's spelling.
    "self_colon_amp": _program("self:& R"),
    # Bare `self:&`, with the type taken from the impl block (170 uses in
    # angelo, prism and lexis). ritz0 accepts it. ritz1 rejected it for the
    # same reason: nothing in `param` allowed SELF COLON AMP.
    "bare_self_colon_amp": _program("self:&"),
    # `self:& R` as the only parameter, plus a second method that reads through
    # the same receiver form, so both a void and a value-returning method with
    # the new receiver get emitted.
    "self_only_param_and_getter": """\
struct R
    pos: i64

impl R
    fn bump(self:& R)
        self.pos = self.pos + 1

    fn get(self:& R) -> i64
        return self.pos

pub fn main() -> i32
    var r: R = R { pos: 0 }
    r.bump()
    r.bump()
    r.bump()
    return r.get() as i32
""",
}

# --- receiver forms that already worked, pinned against regression -----------

WORKING_FORMS = {
    "self_at_amp": _program("self: @&R"),
    # Read-only receivers. Bare `self` is a const borrow in ritz0, so a write
    # through it does not reach the caller; only reads are pinned here.
    "bare_self_read": """\
struct R
    pos: i64

impl R
    fn get(self) -> i64
        return self.pos

pub fn main() -> i32
    var r: R = R { pos: 3 }
    return r.get() as i32
""",
    # The #1301 alternative this fix mirrors: a free-function `name:& T` borrow.
    "free_fn_colon_amp": """\
struct R
    pos: i64

fn seek(r:& R, p: i64)
    r.pos = p

pub fn main() -> i32
    var r: R = R { pos: 0 }
    seek(@&r, 3)
    return r.pos as i32
""",
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        comp = run_ritz0([str(src), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll)]
        comp = subprocess.run(
            cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
        )
    return comp, ll


def _run(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    """Compile `program` with `compiler`, link it, run it, return the exit code."""
    comp, ll = _compile(compiler, tmp_path, name, program)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n"
        f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )

    exe = tmp_path / f"{name}_{compiler}"
    link_cmd = ["clang", str(ll), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = fast_link.clang(link_cmd, cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, (
        f"{compiler} emitted IR that would not link for {name}:\n{link.stderr[-2000:]}"
    )
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


ALL_RUNNABLE = {**BROKEN_FORMS, **WORKING_FORMS}


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ALL_RUNNABLE))
def test_ritz0_is_the_oracle(tmp_path, name):
    """The reference answer. If this changes, the oracle moved, not ritz1."""
    assert _run("ritz0", tmp_path, name, ALL_RUNNABLE[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(BROKEN_FORMS))
def test_ritz1_accepts_self_mut_borrow_receiver(ritz1_bin, tmp_path, name):
    """AGAST #1522. Before the fix each of these was a ritz1 parse error (exit 1)."""
    assert _run("ritz1", tmp_path, name, BROKEN_FORMS[name]) == 3


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(WORKING_FORMS))
def test_ritz1_already_working_receiver_forms(ritz1_bin, tmp_path, name):
    """Receiver and borrow forms that parsed before the fix must still work."""
    assert _run("ritz1", tmp_path, name, WORKING_FORMS[name]) == 3


@pytest.mark.integration
def test_ritz1_rejects_self_double_amp(ritz1_bin, tmp_path):
    """The new alternative accepts one `&`, nothing looser."""
    comp, ll = _compile("ritz1", tmp_path, "double_amp", _program("self:&& R"))
    assert comp.returncode != 0, f"ritz1 accepted `self:&& R`:\n{comp.stdout[-1000:]}"
    assert not ll.exists(), "ritz1 wrote an artifact for `self:&& R`"


# --- the spaced spelling is the removed legacy `&T` type (AGAST #1565) --------

_LEGACY_AMP = "Legacy `&T` reference syntax is no longer supported"
_LEGACY_AMP_MUT = "Legacy `&mut T` syntax is no longer supported"

# Each row is refused, by both compilers, with ritz0's migration diagnostic.
# One row per grammar position that took `COLON AMP` before the fix (a self
# receiver, a free-fn param, a struct field) plus a `let`, whose `: &T` never
# parsed but had no diagnostic, and `&mut T`, which ritz0 words differently.
SPACED_LEGACY = {
    "self_amp": (_program("self: &R"), _LEGACY_AMP),
    "self_spaced_amp": (_program("self : & R"), _LEGACY_AMP),
    "param_amp": (WORKING_FORMS["free_fn_colon_amp"].replace("r:& R", "r: &R"), _LEGACY_AMP),
    "param_amp_mut": (
        WORKING_FORMS["free_fn_colon_amp"].replace("r:& R", "r: &mut R"),
        _LEGACY_AMP_MUT,
    ),
    "field_amp": (
        "struct C\n    x: i32\nstruct R\n    ch: &C\n"
        "pub fn main() -> i32\n    return 3\n",
        _LEGACY_AMP,
    ),
    "let_amp": (
        "struct R\n    pos: i64\npub fn main() -> i32\n"
        "    var r: R = R { pos: 3 }\n    let q: &R = @r\n    return q.pos as i32\n",
        _LEGACY_AMP,
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("name", sorted(SPACED_LEGACY))
def test_rejects_spaced_legacy_amp(request, tmp_path, compiler, name):
    """`: &R` is the removed legacy `&T` type, not the `:&` mutable-borrow form.

    ritz0 lexes `:&` as one COLON_AMP token, so with a space between them the
    `&` starts a type.  ritz1 lexed COLON AMP either way and took `r: &R` and
    `self: &R` as borrows (AGAST #1565).  The `:&` spellings stay accepted:
    BROKEN_FORMS / WORKING_FORMS above run them.
    """
    if compiler == "ritz1":
        request.getfixturevalue("ritz1_bin")
    program, message = SPACED_LEGACY[name]
    comp, ll = _compile(compiler, tmp_path, name, program)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted {name}:\n{out[-1000:]}"
    assert message in out, f"{compiler} refused {name} without the legacy diagnostic:\n{out[-2000:]}"
    if compiler == "ritz1":
        assert not ll.exists(), f"ritz1 wrote an artifact for {name}"
