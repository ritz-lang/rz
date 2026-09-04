#!/usr/bin/env python3
"""Inferred binding types must not leak between functions (AGAST #1321).

`_emit_function_body` clears `locals` and `params` per function but never
`ritz_types`. A name bound in one function leaves its inferred Ritz type
behind; if a *later* function reuses the name and inference fails for the
new binding, method dispatch consults the stale entry and resolves against
the wrong type.

The angelo shape (tests.ritz): `let metrics = font.metrics()` (FontMetrics)
in one test function, then `let metrics = font.glyph_metrics(0)`
(Option<GlyphMetrics>, inference misses) in a later one ->
`No method 'is_some' found for type 'FontMetrics'`.
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


# `x` is an A in first(). In second(), `x` is a B, but bound from an
# if/else expression, which type inference does not resolve — so the stale
# `A` entry from first() is what method dispatch sees.
STALE_BINDING_ACROSS_FUNCTIONS = """\
struct A
    n: i32

impl A
    fn only_a(self: @A) -> i32
        return self.n

struct B
    m: i32

impl B
    fn only_b(self: @B) -> i32
        return self.m

fn first() -> i32
    let x = A { n: 1 }
    x.only_a()

fn second(flag: i32) -> i32
    let x = match flag
        1 => B { m: 2 }
        _ => B { m: 3 }
    x.only_b()

fn main() -> i32
    return first() + second(1)
"""


def test_binding_type_does_not_leak_across_functions(tmp_path):
    result = _compile(tmp_path, STALE_BINDING_ACROSS_FUNCTIONS)
    assert result.returncode == 0, (
        f"stale cross-function binding type broke dispatch:\n{result.stderr}"
    )
