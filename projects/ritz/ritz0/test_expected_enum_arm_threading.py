#!/usr/bin/env python3
"""Expected-enum threading through control-flow tails (AGAST #1321).

`_emit_expr_with_expected_enum` forces an unqualified variant constructor
(`Some(x)`) to the enum the context demands. It was only applied to a
function's tail expression *directly*: if the tail was an `if` or a `match`,
the expectation was dropped and every variant constructor in the arm tails
fell back to the global `variant_to_enum` map — which points at whichever
specialization was registered last.

angelo's font.ritz shape: a function returning `Option<GlyphOutline>` whose
tail is a match over a `Result`, with `Some(outline)` inside an inner match
arm. With another `Option<Glyph>` in scope, `Some` resolved to
`Option$Glyph` and construction died with::

    cannot store %"...GlyphOutline" to %"...Glyph"*: mismatching types

The fix threads the expectation through if/match arm tails and block tails,
clearing it at statement boundaries so nested statements do not inherit it.
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


# Two Option payload types. `use_b` sits between `pick` and `main`, so `Option$B`
# is the later registration and the global `Some` binding points at it — module-level type collection means the
# global `Some` binding cannot be trusted inside `pick`; only the expectation
# from `pick`'s return type can pick `Option$A`.
NESTED_ARM_VARIANT = """\
struct A
    x: i32

struct B
    y: i32

fn pick(n: i32) -> Option<A>
    match n
        1 =>
            match n + 1
                2 => Some(A { x: 1 })
                _ => None
        _ => None

fn use_b(n: i32) -> Option<B>
    if n == 1
        return Some(B { y: 2 })
    return None

fn main() -> i32
    match pick(1)
        Some(a) => a.x - 1
        None => 7
"""


def test_variant_in_nested_match_arm_uses_expected_enum(tmp_path):
    """`Some(A{..})` two match levels below the fn tail must build Option$A."""
    result = _compile(tmp_path, NESTED_ARM_VARIANT)
    assert result.returncode == 0, (
        f"variant constructor in nested match arm failed to compile:\n"
        f"{result.stderr}"
    )


# The same shape through an `if` tail instead of a match.
IF_TAIL_VARIANT = """\
struct A
    x: i32

struct B
    y: i32

fn pick(n: i32) -> Option<A>
    if n == 1
        Some(A { x: 1 })
    else
        None

fn use_b(n: i32) -> Option<B>
    if n == 1
        return Some(B { y: 2 })
    return None

fn main() -> i32
    match pick(1)
        Some(a) => a.x - 1
        None => 7
"""


def test_variant_in_if_tail_uses_expected_enum(tmp_path):
    """`Some(A{..})` in an if/else tail must build Option$A."""
    result = _compile(tmp_path, IF_TAIL_VARIANT)
    assert result.returncode == 0, (
        f"variant constructor in if tail failed to compile:\n{result.stderr}"
    )

# Assignment in a match arm goes through `_emit_assign_expr`, not
# `AssignStmt` — the latter already resolved the variant against the target's
# enum, the former did not (font.ritz: `Ok(cmap) => self.cmap = Some(cmap)`).
ASSIGN_IN_ARM = """\
struct A
    x: i32

struct B
    y: i32

struct Holder
    slot: Option<A>

fn fill(h:& Holder, n: i32)
    match n
        1 => h.slot = Some(A { x: 1 })
        _ => h.slot = None

fn use_b(n: i32) -> Option<B>
    if n == 1
        return Some(B { y: 2 })
    return None

fn main() -> i32
    var h = Holder { slot: None }
    fill(@&h, 1)
    match h.slot
        Some(a) => a.x - 1
        None => 7
"""


def test_variant_assigned_in_match_arm_uses_target_enum(tmp_path):
    """`h.slot = Some(A{..})` as an arm body must build the target's enum."""
    result = _compile(tmp_path, ASSIGN_IN_ARM)
    assert result.returncode == 0, (
        f"variant assignment in match arm failed to compile:\n{result.stderr}"
    )
