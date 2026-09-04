#!/usr/bin/env python3
"""Result<(), E> must mangle to one stable name regardless of where it's written.

AGAST #1321: `_type_to_name_suffix` fell through to `str(ty)` for tuple
types, embedding the *source span* in the mangled name. Two functions both
returning `Result<(), StrView>` produced two distinct enum type names, and
a call/ret across them emitted invalid IR:

    ret %"Result$TupleType(span=...:127:53, ...)_StrView" %".11"
    (function declared %"Result$TupleType(span=...:103:58, ...)_StrView")
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


# Two fns declare Result<(), i32> at different source locations; one calls
# the other and forwards with `?`, so the two names must unify.
TWO_UNIT_RESULTS = """\
fn inner(n: i32) -> Result<(), i32>
    if n < 0
        return Err(n)
    Ok(())

fn outer(n: i32) -> Result<(), i32>
    inner(n)?
    Ok(())

fn main() -> i32
    match outer(1)
        Ok(_) => 0
        Err(e) => e
"""


def test_unit_result_single_mangled_name(tmp_path):
    result = _compile(tmp_path, TWO_UNIT_RESULTS)
    assert result.returncode == 0, (
        f"Result<(), E> at two spans failed to compile:\n{result.stderr}"
    )
    ll = (tmp_path / "unit.ll").read_text()
    assert "TupleType(span=" not in ll, (
        "mangled name still embeds the tuple's source span"
    )
    assert 'Result$unit_i32' in ll, (
        "expected the canonical Result$unit_i32 name in the IR"
    )
