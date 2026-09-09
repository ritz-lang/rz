#!/usr/bin/env python3
"""A store whose value does not match its destination must be a located
diagnostic.

AGAST #1384.

#1366 fixed this for *call arguments* by wrapping `_emit_call`. It did not
cover stores, and stores are where the workspace's remaining anonymous
diagnostics actually come from:

    projects/http     Compiler error: cannot store %"struct...StrView"
                      to i8**: mismatching types
    projects/tempest  TypeError: cannot store %"struct...IpcChannel"
                      to %"struct...IpcChannel"**: mismatching types

Neither names a file, a line, or the variable being assigned. `tempest`'s
arrives as a bare Python traceback — llvmlite's `IRBuilder.store` exception
unwinding all the way out of the compiler.

This is the same cost #1366 documented: an error that names nothing gets
misfiled. `72_raii` sat on the known-failure allowlist for months labelled
"verified genuine compiler debt" on the strength of an anonymous message, and
turned out to be three ordinary source bugs.

WHAT THESE TESTS PIN

The diagnostic's *shape*, not the compiler's capability. If ritz0 later
learns to coerce a StrView into a `*u8` slot, these tests must still pass —
whatever it continues to reject, it must reject with a location. The control
(`test_a_correct_store_still_compiles`) is what stops "convert every
TypeError" from passing by rejecting everything.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"

# file:line:column: — the format EmitError shares with TypeError,
# OwnershipError and NameError.
LOCATION = re.compile(r"[\w./-]+\.ritz:\d+:\d+:")


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


# A StrView assigned into a `*u8` variable. This is `projects/http`'s shape.
VAR_ASSIGN = """\
fn main() -> i32
    var p: *u8 = c"a"
    p = "hello"
    return 0
"""

# The same mismatch through a struct field rather than a local. Field stores
# go through a different `builder.store` call site, so one test does not
# cover the other.
FIELD_ASSIGN = """\
struct Holder
    p: *u8

fn main() -> i32
    var h: Holder
    h.p = "hello"
    return 0
"""

# Both of the above, spelled correctly. Must keep compiling.
CORRECT = """\
struct Holder
    p: *u8

fn main() -> i32
    var h: Holder
    h.p = c"hello"
    var q: *u8 = c"a"
    q = c"b"
    return 0
"""


@pytest.mark.unit
@pytest.mark.parametrize("name,source", [
    ("var_assign.ritz", VAR_ASSIGN),
    ("field_assign.ritz", FIELD_ASSIGN),
])
def test_store_mismatch_is_rejected(tmp_path, name, source):
    """Both shapes are user errors and must fail the compile."""
    r = _compile(tmp_path, name, source)
    assert r.returncode != 0, (
        f"{name} should not compile:\n{r.stdout}\n{r.stderr}")


@pytest.mark.unit
@pytest.mark.parametrize("name,source", [
    ("var_assign.ritz", VAR_ASSIGN),
    ("field_assign.ritz", FIELD_ASSIGN),
])
def test_store_mismatch_names_a_source_location(tmp_path, name, source):
    """The regression: `cannot store X to Y` with no file and no line."""
    r = _compile(tmp_path, name, source)
    assert LOCATION.search(r.stderr), (
        f"{name}: diagnostic has no file:line:column\n{r.stderr}")
    assert name in r.stderr, (
        f"{name}: diagnostic does not name the file\n{r.stderr}")


@pytest.mark.unit
@pytest.mark.parametrize("name,source", [
    ("var_assign.ritz", VAR_ASSIGN),
    ("field_assign.ritz", FIELD_ASSIGN),
])
def test_store_mismatch_is_not_a_python_traceback(tmp_path, name, source):
    """A user error must not arrive with a Python stack attached.

    This is the half that made `tempest` unreadable: llvmlite's exception
    unwound through eleven frames of emitter internals, and the actionable
    line was the last one.
    """
    r = _compile(tmp_path, name, source)
    assert "Traceback (most recent call last)" not in r.stderr, (
        f"{name}: user error escaped as a traceback\n{r.stderr}")
    assert "llvmlite/ir/builder.py" not in r.stderr, (
        f"{name}: diagnostic leaks llvmlite internals\n{r.stderr}")


@pytest.mark.unit
def test_a_correct_store_still_compiles(tmp_path):
    """The control.

    Without this, a 'fix' that converts every TypeError in the emitter into
    a user-facing error passes the tests above while rejecting valid
    programs. `_convert_type` legitimately reshapes values on the way into a
    store, and those cases must keep working.
    """
    r = _compile(tmp_path, "correct.ritz", CORRECT)
    assert r.returncode == 0, (
        f"a correct program stopped compiling:\n{r.stdout}\n{r.stderr}")


@pytest.mark.unit
def test_diagnostic_still_reports_the_type_conflict(tmp_path):
    """Locating it must not throw away what llvmlite knew.

    The types are the only part of the old message that was any use; the fix
    adds a location, it does not replace the content.
    """
    r = _compile(tmp_path, "var_assign.ritz", VAR_ASSIGN)
    assert "cannot store" in r.stderr, (
        f"the type conflict was dropped from the message\n{r.stderr}")
