#!/usr/bin/env python3
"""Match on a method-call scrutinee must dispatch on the value's enum type
(AGAST #1321).

`_emit_match` classified the scrutinee with `_get_enum_name_from_expr`, which
leans on `_infer_ritz_type` — and method calls resolved through the UFCS
fallback (`v.pop()` -> `vec_pop$i32`) have no inferable receiver-declared
type, so classification failed. The match then fell through:

* to `_emit_integer_match` when the arms looked integer-ish — variant
  patterns like `Some(x)` then bind nothing and the arm body dies with the
  red herring `Unknown identifier: x` (angelo hinting/interpreter.ritz,
  `match self.stack.pop()`), or
* to `NotImplementedError: Match on type %"Result$u16_StrView" not yet
  supported` (angelo font.ritz, `match reader.read_u16()`).

But the *emitted value* already knows: its LLVM type is the enum's identified
struct, and `enum_types` is keyed by the same name. The fix falls back to the
identified struct name before giving up.
"""

import os
import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"
RITZ_ROOT = RITZ0.parent.parent


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll")],
        capture_output=True,
        text=True,
        env=env,
    )


# The font.ritz shape: the receiver is bound from a static method call
# (`var reader = Reader.new(...)`), which `_infer_ritz_type` cannot type, so
# the match scrutinee `reader.read_u16()` has no source-level enum
# classification — only the emitted value's identified struct type.
MATCH_ON_METHOD_RESULT = """\
struct Reader
    pos: i32

impl Reader
    fn new(p: i32) -> Reader
        return Reader { pos: p }

    fn read_u16(self:& Reader) -> Result<u16, StrView>
        if self.pos >= 0
            return Ok(7)
        return Err("eof")

fn main() -> i32
    var reader = Reader.new(1)
    match reader.read_u16()
        Ok(n) => (n as i32) - 7
        Err(_) => 1
"""


def test_match_on_method_call_result(tmp_path):
    """`match reader.read_u16()` must dispatch on Result$u16_StrView."""
    result = _compile(tmp_path, MATCH_ON_METHOD_RESULT)
    assert result.returncode == 0, (
        f"match on method-call result failed to compile:\n{result.stderr}"
    )
