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
migration diagnostic (see LANGUAGE_SPEC 3.2). ritz1 lexes `:&` as COLON AMP,
so it cannot tell the two spellings apart and accepts both. That looseness
already existed for free-function `r: &T` (#1301) and is tracked separately. It
is pinned below on the ritz0 side only.

Every runnable program returns 3 only if the receiver really is a mutable
borrow, meaning the write through `self` is visible in the caller. A fix that
parses the receiver but passes a copy returns 0, so it fails too. ritz0 is run
as the oracle.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _build_ritz1() -> None:
    """Bring RITZ1_BIN up to date. A stale ritz1 would test the old grammar (#1322)."""
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the self:& receiver tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


def _build_runtime_start() -> None:
    proc = subprocess.run(
        ["make", "-C", "runtime", RITZ_START.name],
        cwd=RITZ_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0 or not RITZ_START.exists():
        pytest.fail(
            f"could not build the runtime start object {RITZ_START}:\n"
            f"{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    _build_runtime_start()
    return RITZ1_BIN


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
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
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
    link = subprocess.run(link_cmd, cwd=tmp_path, capture_output=True, text=True)
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


@pytest.mark.integration
@pytest.mark.parametrize("receiver", ["self: &R", "self : & R"])
def test_ritz0_rejects_spaced_self_amp(tmp_path, receiver):
    """`: &R` is the removed legacy `&T` type, not the `:&` mutable-borrow form.

    Pins the oracle's answer to "does `self: &R` need the same treatment?" (no).
    """
    comp, _ = _compile("ritz0", tmp_path, "spaced", _program(receiver))
    assert comp.returncode != 0
    assert "Legacy `&T` reference syntax" in comp.stdout + comp.stderr
