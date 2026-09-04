#!/usr/bin/env python3
"""let/var with a generic enum annotation must resolve the specialization.

AGAST #1321, class 3 (angelo tests.ritz). The shape:

    var opt: Option<Foo> = Some(foo)

The let/var statement path handed the *raw* annotation name (`Option`) to
`_emit_enum_variant_with_type`, which only knows materialized
specializations (`Option$Foo`) -> `ValueError: Unknown enum type: Option`.
The assignment-statement path already resolved the name properly; this
pins the let/var path to the same behaviour.
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


GENERIC_ANNOTATED_LET = """\
struct Foo
    n: i32

fn main() -> i32
    var opt: Option<Foo> = Some(Foo { n: 3 })
    match opt
        Some(f) => f.n
        None => 0
"""


def test_var_with_generic_option_annotation(tmp_path):
    """`var opt: Option<Foo> = Some(...)` must compile."""
    result = _compile(tmp_path, GENERIC_ANNOTATED_LET)
    assert result.returncode == 0, (
        f"generic-annotated var binding failed to compile:\n{result.stderr}"
    )


# Guard: non-generic enum annotations took the same branch and worked; they
# must keep working unchanged.
PLAIN_ANNOTATED_LET = """\
enum Color
    Red
    Blue

fn main() -> i32
    var c: Color = Color.Blue
    match c
        Color.Red => 0
        Color.Blue => 1
"""


def test_var_with_plain_enum_annotation(tmp_path):
    result = _compile(tmp_path, PLAIN_ANNOTATED_LET)
    assert result.returncode == 0, (
        f"plain enum annotation guard case failed:\n{result.stderr}"
    )
