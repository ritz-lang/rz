#!/usr/bin/env python3
"""`==` on struct operands must be a located diagnostic, not invalid IR.

AGAST #1321 (angelo hinting/instructions.ritz):

    assert instruction_name(0x40) == "NPUSHB"

Both sides are StrView structs. The emitter emitted `icmp eq %StrView`,
which LLVM rejects at link time ("icmp requires integer operands") — a
red herring pointing at generated IR instead of the source. Zero corpus
usage: `==` is not defined for aggregates; the user needs `strview_eq`
(or a field-wise comparison). The diagnostic must say so and point at
the source line.
"""

import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
    )


STRVIEW_EQ_WITH_EQEQ = """\
fn name() -> StrView
    "NPUSHB"

fn main() -> i32
    if name() == "NPUSHB"
        0
    else
        1
"""


def test_struct_eq_is_located_diagnostic(tmp_path):
    result = _compile(tmp_path, STRVIEW_EQ_WITH_EQEQ)
    err = result.stderr
    assert result.returncode != 0, "== on StrView unexpectedly compiled"
    # Must be a user-facing located error, not an LLVM crash
    assert "unit.ritz:5" in err, (
        f"diagnostic does not point at the comparison's line:\n{err}"
    )
    assert "==" in err and "StrView" in err, (
        f"diagnostic does not name the operator and type:\n{err}"
    )
    assert "strview_eq" in err, (
        f"diagnostic does not suggest strview_eq:\n{err}"
    )


# Guard: integer and pointer == comparisons keep working.
SCALAR_EQ = """\
fn main() -> i32
    let a = 3
    let b = 3
    if a == b
        0
    else
        1
"""


def test_scalar_eq_still_works(tmp_path):
    result = _compile(tmp_path, SCALAR_EQ)
    assert result.returncode == 0, f"scalar == broke:\n{result.stderr}"
