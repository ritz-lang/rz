#!/usr/bin/env python3
"""Static-style UFCS calls: `Type.method(args)` -> `type_method(args)` (AGAST #1321).

`_emit_method_call` resolves `String.from(x)` through the UFCS fallback to
`string_from(sv: StrView)`. The fallback then set::

    has_self_param = params and (params[0].name == 'self' or used_ufcs_fallback)

i.e. *any* UFCS-resolved function was assumed to take the receiver as its
first parameter — even when the call is static (`Type.method()`, no receiver
instance). The very next check rejects static calls with a self param, so
every static-style UFCS call died with::

    ValueError: Static method call Type.method() but method 'from' expects
    'self' parameter

angelo's discovery.ritz uses `String.from(...)` fourteen times; all were
concealed behind earlier compile failures in the same file.

The fix: `used_ufcs_fallback` only implies a receiver parameter when the call
actually has a receiver. Static calls emit their arguments plainly.
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


STRING_FROM_STATIC = """\
import ritzlib.string

fn main() -> i32
    let s = String.from("hello")
    return 0
"""


def test_string_from_static_ufcs(tmp_path):
    """`String.from("...")` must desugar to `string_from(...)` and compile."""
    result = _compile(tmp_path, STRING_FROM_STATIC)
    assert result.returncode == 0, (
        f"static-style UFCS call String.from failed:\n{result.stderr}"
    )


# Receiver-style UFCS must keep working: the first param is still treated as
# the receiver when there *is* a receiver instance.
RECEIVER_UFCS = """\
import ritzlib.string

fn main() -> i32
    var s = String.from("hi")
    let n = s.len()
    return (n - 2) as i32
"""


def test_receiver_ufcs_still_works(tmp_path):
    """`s.len()` -> `string_len(@s)` must be unaffected."""
    result = _compile(tmp_path, RECEIVER_UFCS)
    assert result.returncode == 0, (
        f"receiver-style UFCS call regressed:\n{result.stderr}"
    )
