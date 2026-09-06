#!/usr/bin/env python3
"""A statement-position match mixing arm value types must not build a phi.

AGAST #1321 (angelo font.ritz `ensure_cmap`). The shape:

    match self.file.get_table(TAG_CMAP)
        Some(data) =>
            match parse(data)
                Ok(cmap) => self.cmap = Some(cmap)
                Err(_) => pass
        None => pass

The assignment arm yields the assigned enum value; the `pass` arms yield
the dummy `i32 0`. Merging them built

    phi %"Option$CmapTable" [...], [0, %arm]

— an integer constant incoming into an enum-typed phi, invalid IR that
only clang/llvm parsing catches. Nobody consumes the match's value; when
arm types are irreconcilable the match is a statement and gets no phi.
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


def _verify_ir(tmp_path):
    return subprocess.run(
        [sys.executable, "-c",
         "import sys; import llvmlite.binding as llvm; "
         "llvm.parse_assembly(open(sys.argv[1]).read())",
         str(tmp_path / "unit.ll")],
        capture_output=True, text=True)


MIXED_TYPE_STATEMENT_MATCH = """\
struct Table
    id: i32

struct Holder
    slot: Option<Table>

fn get(n: i32) -> Option<Table>
    if n == 1
        Some(Table { id: 7 })
    else
        None

impl Holder
    fn fill(self:&, n: i32)
        match get(n)
            Some(t) => self.slot = Some(t)
            None => pass

fn main() -> i32
    var h = Holder { slot: None }
    h.fill(1)
    match h.slot
        Some(t) => t.id
        None => 0
"""


def test_mixed_type_statement_match_valid_ir(tmp_path):
    result = _compile(tmp_path, MIXED_TYPE_STATEMENT_MATCH)
    assert result.returncode == 0, (
        f"mixed-arm statement match failed to compile:\n{result.stderr}"
    )
    verify = _verify_ir(tmp_path)
    assert verify.returncode == 0, f"invalid IR: {verify.stderr}"


# The companion the statement-position fix above must NOT buy at the price of:
# the same irreconcilable-arm-type condition in *value* position. Suppressing
# the phi is right for a statement (nobody consumes the value); silently
# yielding `i32 0` for a `let` binding is a fail-open — an ill-typed program
# compiles clean and prints a wrong answer.
#
# main @ f336bae rejects this:
#     Compiler error: Type of #1 arg mismatch: i64 != %"struct...P"
# Losing that rejection loses type safety: ritz0's emitter IS the type check.
MIXED_TYPE_VALUE_MATCH = """\
struct P
    x: i64

enum Shape
    A(i64)
    B(i64)

fn main() -> i32
    let p: P = P { x: 99 }
    let s: Shape = A(5)
    let v: i64 = match s
        A(q) => p
        B(q) => 7
    return v as i32
"""


def test_mixed_type_value_match_is_rejected(tmp_path):
    """A value-position match with irreconcilable arm types must be rejected.

    It must NOT compile to a silent `i32 0`. Either diagnostic is acceptable
    here — what is not acceptable is returncode 0.
    """
    result = _compile(tmp_path, MIXED_TYPE_VALUE_MATCH)
    assert result.returncode != 0, (
        "ill-typed value-position match compiled clean — the arm-type "
        "mismatch guard silently yielded a dummy value instead of "
        "rejecting.\nstdout:\n" + result.stdout + "\nstderr:\n" + result.stderr
    )
