#!/usr/bin/env python3
"""Integer match with mixed value/void arms must not build a phi over
`ir.Undefined` (AGAST #1321).

A `?` that unwraps a `Result<(), E>` yields the unit value — represented in
the emitter as `ir.Undefined`. angelo's hinting interpreter dispatches
opcodes with a statement-position integer match whose arms mix value tails
(`self.pop()?` -> i32) with *block arms ending in an assignment statement* —
a block with no tail expression, which `_emit_block_expr` reports as
`ir.Undefined`::

    match opcode
        instructions.POP => self.pop()?
        instructions.SRP0 =>
            let p = self.pop()? as u16
            self.gs.rp0 = p

`_emit_integer_match` built a merge phi from every non-terminated arm value,
including the `Undefined`s, and module serialization then crashed with::

    AttributeError: '_Undefined' object has no attribute 'get_reference'

A match with a void arm is a statement, not a value: when any live arm yields
`Undefined` the phi must be skipped.
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


MIXED_ARMS = """\
struct Gs
    rp0: i32

fn maybe(n: i32) -> Result<i32, i32>
    if n > 0
        return Ok(n)
    return Err(0 - n)

fn act(gs:& Gs, n: i32) -> Result<(), i32>
    match n
        1 => maybe(n)?
        2 =>
            let p = maybe(n)?
            gs.rp0 = p
        _ => pass
    Ok(())

fn main() -> i32
    var gs = Gs { rp0: 0 }
    match act(@&gs, 2)
        Ok(_) => 0
        Err(e) => e
"""


def test_integer_match_with_mixed_void_and_value_arms(tmp_path):
    """Statement-position match mixing unit-? and value arms must compile."""
    result = _compile(tmp_path, MIXED_ARMS)
    assert result.returncode == 0, (
        f"integer match with mixed void/value arms failed to compile:\n"
        f"{result.stderr}"
    )
