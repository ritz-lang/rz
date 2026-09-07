#!/usr/bin/env python3
"""A call whose arguments do not match its callee must be a located diagnostic.

AGAST #1366.

Both of these are *user* errors — the program is wrong — but ritz0 reported
them by letting a Python exception unwind out of the emitter:

    TypeError: Type of #1 arg mismatch: %"struct.ritz_module_1.StrView" != i8*
    ValueError: Function 'two' called with 1 args but defined with 2 params

The first is llvmlite's `CallInstr` exception printed verbatim. It names no
file, no line, and no callee, and it spells the types in LLVM's syntax rather
than the `*u8` / `StrView` the programmer wrote. The second at least names the
function, but still arrives with a Python traceback attached and no location.

This cost real time: `47_lisp` and `51_loadtest` sat on the known-failure
allowlist for months misfiled as "unmigrated async". Locating them by reading
the source picked the wrong call site twice; what actually worked was patching
`_emit_call` to print `fname`, which a user cannot do to their own compiler.

The contrast that proves the point is inside the same batch — `52_uring`'s
error DID name its function, and was fixed in one step.

These tests assert the diagnostic's *shape*, not the compiler's capability:
they must keep passing if ritz0 later learns to coerce these calls, so long as
whatever it still rejects, it rejects with a location.
"""

import os
import subprocess
import sys
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"


def _compile(tmp_path, name, source):
    src = tmp_path / name
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )


# `prints` takes a StrView; `p` is a *u8. This is the exact shape that
# 47_lisp (two sites) and 51_loadtest hit.
TYPE_MISMATCH = """\
import ritzlib.io

fn main() -> i32
    let p: *u8 = c"hello"
    prints(p)
    return 0
"""

ARITY_MISMATCH = """\
fn two(a: i64, b: i64) -> i64
    return a + b

fn main() -> i32
    return two(1) as i32
"""


def test_argument_type_mismatch_is_located(tmp_path):
    """The call site's file:line must appear — this is the whole ticket."""
    r = _compile(tmp_path, "tm.ritz", TYPE_MISMATCH)
    assert r.returncode != 0, "prints(*u8) unexpectedly compiled"
    assert "tm.ritz:5" in r.stderr, (
        f"diagnostic does not point at the call site (line 5):\n{r.stderr[-2000:]}"
    )


def test_argument_type_mismatch_names_the_callee(tmp_path):
    """Naming the function is what turns a hunt into a one-step fix."""
    r = _compile(tmp_path, "tm.ritz", TYPE_MISMATCH)
    assert "prints" in r.stderr, (
        f"diagnostic does not name the callee:\n{r.stderr[-2000:]}"
    )


def test_argument_type_mismatch_has_no_python_traceback(tmp_path):
    """A user error must not surface as an emitter stack trace.

    This is the assertion that would have failed before #1366: llvmlite's
    TypeError escaped with the full llvmlite/emitter frame stack attached.
    """
    r = _compile(tmp_path, "tm.ritz", TYPE_MISMATCH)
    assert "Traceback (most recent call last)" not in r.stderr, (
        f"user error escaped as a Python traceback:\n{r.stderr[-3000:]}"
    )
    assert "llvmlite/ir/instructions.py" not in r.stderr, (
        f"diagnostic leaks llvmlite internals:\n{r.stderr[-3000:]}"
    )


def test_arity_mismatch_is_located(tmp_path):
    """Arity errors already named the function; they still had no location."""
    r = _compile(tmp_path, "arity.ritz", ARITY_MISMATCH)
    assert r.returncode != 0, "two(1) unexpectedly compiled"
    assert "arity.ritz:5" in r.stderr, (
        f"arity diagnostic does not point at the call site:\n{r.stderr[-2000:]}"
    )
    assert "two" in r.stderr, (
        f"arity diagnostic does not name the callee:\n{r.stderr[-2000:]}"
    )


def test_arity_mismatch_has_no_python_traceback(tmp_path):
    r = _compile(tmp_path, "arity.ritz", ARITY_MISMATCH)
    assert "Traceback (most recent call last)" not in r.stderr, (
        f"user error escaped as a Python traceback:\n{r.stderr[-3000:]}"
    )


def test_a_correct_call_still_compiles(tmp_path):
    """The guard must not reject calls that were always fine.

    Without this, wrapping every call in a try/except that converts TypeError
    could be made to 'pass' by rejecting everything.
    """
    r = _compile(tmp_path, "ok.ritz", """\
fn two(a: i64, b: i64) -> i64
    return a + b

fn main() -> i32
    return two(1, 2) as i32
""")
    assert r.returncode == 0, f"a well-typed call was rejected:\n{r.stderr[-2000:]}"
