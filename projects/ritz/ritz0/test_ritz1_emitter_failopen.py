"""Regression tests for AGAST #1369 — ritz1 must FAIL when its emitter cannot
emit an expression, instead of writing the error into the IR as a comment and
carrying on.

ritz1's emitter had no error-reporting mechanism at all. When it met something
it could not lower, it wrote a comment into the output and substituted a
value:

    ; ERROR: unknown identifier 'double'
    %.1 = add i64 0, 0

then carried on and exited 0. The caller then does `call i64 %.1(...)` on a
null pointer. So `ritz1 prog.ritz` reports success, build.py prints its tick,
and the program segfaults at run time — a compiler that knows it has failed
and says nothing.

There were 20 such sites (unknown identifier, unknown variable, unhandled
EXPR_MEMBER, cannot take address, struct literal not in var initializer
context, the simd/x86 intrinsic arity checks, ...). The assignment case is
worse than the value case: `; ERROR: unknown variable 'x'` emits the comment
and then simply DROPS THE STORE, so the program runs to completion with a
stale value and no diagnostic anywhere.

Found by clearing tier5_async_57_fn_ptr's compile failure (#1367). Underneath
it sat this: ritz1 cannot take the address of a function, and rather than say
so it emitted 0 and produced a segfaulting binary. Fixing #1367 did not cause
that — it removed the compile error that had been masking it.

A corpus sweep at the time measured 5 of 66 ritz1-compilable examples emitting
at least one `; ERROR` comment into their IR: 44_csv, 50_http, 57_fn_ptr,
61_true_async, 72_raii. Four were already on an allowlist for other reasons;
57_fn_ptr was the one that had just become reachable.

What is asserted here is only the honesty property — that ritz1 refuses —
NOT that ritz1 can compile these programs. Function pointers remain
unimplemented in ritz1; the point is that "unimplemented" must exit non-zero.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"


def _build_ritz1() -> None:
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
            "could not build ritz1 for the emitter fail-open tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    _build_ritz1()
    return RITZ1_BIN


# A function used as a value. ritz1 cannot lower this; ritz0 can, and returns
# 10, which is what makes the silent-zero substitution a WRONG ANSWER rather
# than merely an unsupported one.
FN_POINTER = """\
fn double(x: i32) -> i32
    return x * 2

fn apply(f: fn(i32) -> i32, v: i32) -> i32
    return f(v)

fn main() -> i32
    return apply(double, 5) as i32
"""

# Assignment to a name that does not exist. The old behaviour emitted the
# comment and dropped the store, so the program ran to completion.
UNKNOWN_VARIABLE = """\
fn main() -> i32
    no_such_variable = 7
    return 0
"""

UNEMITTABLE = {
    "fn_pointer": FN_POINTER,
    "unknown_variable": UNKNOWN_VARIABLE,
}


def _compile(compiler: str, tmp_path: Path, name: str, program: str):
    src = tmp_path / f"{name}_{compiler}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    cmd = (
        ["python3", str(RITZ0), str(src), "-o", str(ll)]
        if compiler == "ritz0"
        else [str(RITZ1_BIN), str(src), "-o", str(ll)]
    )
    proc = subprocess.run(
        cmd, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300
    )
    return proc, ll


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(UNEMITTABLE))
def test_ritz1_rejects_what_it_cannot_emit(ritz1_bin, tmp_path, name):
    """AGAST #1369: a non-zero exit, not a tick and a broken binary."""
    proc, _ = _compile("ritz1", tmp_path, name, UNEMITTABLE[name])
    assert proc.returncode != 0, (
        f"ritz1 exited 0 for a program it cannot emit ({name}).\n"
        f"stdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(UNEMITTABLE))
def test_ritz1_says_what_went_wrong(ritz1_bin, tmp_path, name):
    """The refusal must be visible to the user, not buried in the IR.

    Exiting non-zero silently would satisfy the test above and still leave a
    caller unable to tell a compiler bug from a bad program.
    """
    proc, _ = _compile("ritz1", tmp_path, name, UNEMITTABLE[name])
    combined = proc.stdout + proc.stderr
    assert "rror" in combined, (
        f"ritz1 failed for {name} without printing a diagnostic.\n"
        f"stdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(UNEMITTABLE))
def test_ritz1_does_not_leave_a_usable_output_file(ritz1_bin, tmp_path, name):
    """A failed compile must not leave IR behind for a build system to link.

    build.py runs the compiler and then links whatever is at -o. If a failing
    compile still writes the file, a downstream step can pick up the very IR
    the compiler just disowned.
    """
    proc, ll = _compile("ritz1", tmp_path, name, UNEMITTABLE[name])
    assert proc.returncode != 0  # precondition; asserted properly above
    assert not ll.exists() or "; ERROR" not in ll.read_text(), (
        f"ritz1 failed for {name} but left IR containing its own error marker "
        f"at {ll} — a build system will happily link this."
    )


@pytest.mark.integration
def test_ritz0_compiles_the_function_pointer_case(tmp_path):
    """The oracle, and the reason the silent zero was a wrong ANSWER.

    ritz0 lowers this correctly. If ritz1 is ever taught function pointers,
    this test stays true and the ones above must then be re-pointed at a
    construct ritz1 still cannot emit — they assert honesty, not incapacity.
    """
    proc, ll = _compile("ritz0", tmp_path, "fn_pointer", FN_POINTER)
    assert proc.returncode == 0 and ll.exists(), (
        f"ritz0 failed to compile the function-pointer case:\n{proc.stderr[-2000:]}"
    )
