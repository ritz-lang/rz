"""A closure with no expected type is a located error, not a traceback (AGAST #3302).

`let g = |x| x + 1` gives `_emit_closure` no `fn(...)` type to build the
closure from.  It raised a bare `ValueError`, so ritz0 printed a Python
traceback with no file:line:col.  It is now an `EmitError` at the closure's `|`.

Whether a closure whose params are all typed should infer its own type is
#1829 / #3301, not this test's business: the row here has an untyped param.
ritz1 has no closures at all (#1531, #1623); it refuses this source with a
parse error at the same `|`.
"""

import os
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.integration
def test_untyped_closure_is_located_error(tmp_path):
    src = tmp_path / "closure.ritz"
    src.write_text("fn main() -> i32\n    let g = |x| x + 1\n    0\n")
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = run_ritz0([str(src), "-o", str(tmp_path / "closure.ll")],
                     cwd=tmp_path, env=env, timeout=300)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0
    assert "Traceback" not in out, out
    # Line 2, column 13: the closure's opening `|`.
    assert f"{src}:2:13: Cannot infer closure type" in out, out
