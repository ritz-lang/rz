#!/usr/bin/env python3
"""`?` on a method call whose receiver was bound from a static method call.

AGAST #1321, class 1 (the cmap/hmtx/loca trio in angelo). The shape:

    var reader = Reader.new(data)
    let v = reader.read_u16()?

`Reader.new(...)` is a static method call; `_infer_ritz_type` had no case
for it, so the binding recorded no Ritz type for `reader`. When `?` later
asked `_get_enum_name_from_expr` about `reader.read_u16()`, the receiver's
type was unknown, method resolution failed, and the emitter raised
`Try operator requires a Result type, got expression: MethodCall`.

The fixture avoids ritzlib so it compiles with --no-runtime.
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


TRY_ON_STATIC_BOUND_RECEIVER = """\
struct Reader
    pos: i32

impl Reader
    fn new(start: i32) -> Reader
        Reader { pos: start }

    fn read_u16(self: @&Reader) -> Result<u16, i32>
        self.pos = self.pos + 2
        Ok(7 as u16)

fn parse() -> Result<u16, i32>
    var reader = Reader.new(0)
    let a = reader.read_u16()?
    let b = reader.read_u16()?
    Ok(a + b)

fn main() -> i32
    match parse()
        Ok(v) => v as i32
        Err(e) => e
"""


def test_try_on_receiver_bound_from_static_method(tmp_path):
    """`reader.read_u16()?` must compile when reader came from Reader.new()."""
    result = _compile(tmp_path, TRY_ON_STATIC_BOUND_RECEIVER)
    assert result.returncode == 0, (
        "`?` on method call with static-method-bound receiver failed:\n"
        f"{result.stderr}"
    )


# Guard: the same shape with an explicitly annotated binding already worked;
# it must keep working (pins that the fix extends inference rather than
# rerouting the annotated path).
TRY_ON_ANNOTATED_RECEIVER = """\
struct Reader
    pos: i32

impl Reader
    fn new(start: i32) -> Reader
        Reader { pos: start }

    fn read_u16(self: @&Reader) -> Result<u16, i32>
        self.pos = self.pos + 2
        Ok(7 as u16)

fn parse() -> Result<u16, i32>
    var reader: Reader = Reader.new(0)
    let a = reader.read_u16()?
    Ok(a)

fn main() -> i32
    match parse()
        Ok(v) => v as i32
        Err(e) => e
"""


def test_try_on_annotated_receiver_still_works(tmp_path):
    result = _compile(tmp_path, TRY_ON_ANNOTATED_RECEIVER)
    assert result.returncode == 0, (
        f"annotated-receiver guard case failed:\n{result.stderr}"
    )
