#!/usr/bin/env python3
"""Nested variant patterns must be rejected with a located diagnostic (AGAST #1321).

ritz0 supports one level of variant pattern. `Ok(Simple(x))` parses — the
inner `Simple(x)` becomes a `VariantPattern` in the outer pattern's fields —
but the match binder only binds `IdentPattern` fields, so the nested pattern
silently bound nothing and the arm body failed with the red herring::

    ValueError: Unknown identifier: x

(angelo's font.ritz hit exactly this: `Ok(Simple(outline))` reported
`Unknown identifier: outline`, pointing nowhere near the actual construct.
Nested patterns have zero corpus usage, so the next person to write one gets
the same misdirection unless the compiler names the construct.)

The deliverable is the diagnostic itself: name the unsupported construct and
point at the pattern's own file:line.
"""

import os
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


# The reduced font.ritz `glyph_outline_with_depth` shape: matching through a
# Result into an inner enum in one pattern.
NESTED_VARIANT_PATTERN = """\
enum Shape
    Simple(i32)
    Empty

enum Res
    Ok(Shape)
    Err(i32)

fn get() -> Res
    return Res.Ok(Shape.Simple(3))

fn main() -> i32
    match get()
        Ok(Simple(x)) => x
        Ok(Empty) => 1
        Err(e) => e
"""


def test_nested_variant_pattern_diagnostic(tmp_path):
    """`Ok(Simple(x))` must name the construct and its location, not the binder."""
    result = _compile(tmp_path, NESTED_VARIANT_PATTERN)
    assert result.returncode != 0, "nested variant pattern unexpectedly compiled"
    err = result.stderr
    assert "Unknown identifier" not in err, (
        f"nested pattern still reported the red-herring binder error:\n{err}"
    )
    # Must name the construct...
    assert "nested" in err.lower() and "pattern" in err.lower(), (
        f"diagnostic does not name the nested-pattern construct:\n{err}"
    )
    # ...and locate it: file and line 14 (the `Ok(Simple(x))` arm).
    assert "unit.ritz" in err and ":14" in err, (
        f"diagnostic does not point at the pattern's file:line:\n{err}"
    )
