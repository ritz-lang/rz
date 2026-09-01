#!/usr/bin/env python3
"""Qualified enum-variant handling in the ritz0 emitter (AGAST #1284).

Background
----------
``./rz build lexis`` died with a bare Python traceback::

    ValueError: Unknown variant Dir in enum Tag

The reported hypothesis was that enum *resolution* had picked the wrong type —
two enums in scope, the lookup taking a global match rather than the
scrutinee's declared type.  It had not.  ``lib/dom/tag.ritz`` genuinely matched
on nine ``Tag`` variants (``Dir``, ``Frame``, ``Frameset``, ``Listing``,
``Marquee``, ``Noembed``, ``Noframes``, ``Plaintext``, ``Xmp``) that the enum
never declared.  Resolution was correct; the source was invalid.

Two defects fall out of that, and this module pins both.

1. **Qualified variant construction was emitted as a method call.**
   ``Color.Named(payload)`` parses to a :class:`rast.MethodCall`, and
   ``_emit_method_call`` decided whether the receiver was a *type* by asking
   ``name in self.struct_types`` — it never consulted ``self.enum_types``.  An
   enum receiver therefore fell through to the "emit the receiver and inspect
   its LLVM type" fallback, which tried to evaluate the bare identifier
   ``Color`` as a value and raised ``Unknown identifier: Color``.

   It only ever surfaced in positions where the expected enum type was *not*
   already threaded through.  ``_emit_expr_with_expected_enum`` special-cases a
   function's tail expression, so ``fn f() -> Color`` returning
   ``Color.Named(x)`` directly was fine; the same expression as the tail of an
   ``if``/``else`` branch was not, because ``_emit_if`` does not propagate the
   expected enum into its arms.  That is exactly the shape ``tag_from_name``
   uses, so the bug hid behind the invalid-source failure above until the enum
   was completed.

2. **The invalid-source diagnostic had no source location.**  An undeclared
   variant is a legitimate user error, but it escaped as an unhandled
   ``ValueError`` from deep inside the emitter with a Python traceback and no
   ``file:line:column``.  ``type_checker._check_pattern`` has the information to
   catch this earlier but silently ignores it, and ``--check-types`` is off by
   default — so the emitter is the only line of defence and must report like
   one.
"""

import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"


def _compile(tmp_path: Path, source: str) -> subprocess.CompletedProcess:
    """Compile a standalone Ritz source, returning the completed process.

    ``--no-runtime`` keeps these free of any ``RITZ_PATH``/ritzlib dependency:
    the sources below import nothing, so the emitter is the only thing under
    test.
    """
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll"), "--no-runtime"],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# 1. Qualified enum-variant construction
# ---------------------------------------------------------------------------

# The reduced shape of `tag_from_name`: a qualified variant *with a payload*
# built in the tail of an if/else arm, where no expected-enum context reaches
# the expression. `Color.Red` in the other arm covers the payload-free case.
IF_ELSE_PAYLOAD = """\
enum Color
    Red
    Named(*u8)

fn pick(n: i32) -> Color
    if n == 0
        Color.Red
    else
        Color.Named(c"blue")

fn main() -> i32
    match pick(1)
        Color.Red => 0
        Color.Named(s) => 1
"""


def test_qualified_variant_with_payload_in_if_branch(tmp_path):
    """`Enum.Variant(payload)` as an if/else tail must compile.

    This is the exact construct `lexis`'s `tag_from_name` is built from. Before
    the fix it raised `ValueError: Unknown identifier: Color`, because the
    receiver `Color` was not recognised as a type name and was evaluated as a
    value instead.
    """
    result = _compile(tmp_path, IF_ELSE_PAYLOAD)
    assert result.returncode == 0, (
        "qualified enum-variant construction in an if/else branch failed to "
        f"compile:\n{result.stderr}"
    )


def test_qualified_variant_construction_is_not_a_method_call(tmp_path):
    """The failure must not resurface as the identifier error specifically.

    Asserted separately from the return code so a regression names the actual
    mechanism — an enum receiver being evaluated as a value — rather than just
    reporting a non-zero exit.
    """
    result = _compile(tmp_path, IF_ELSE_PAYLOAD)
    assert "Unknown identifier: Color" not in result.stderr, (
        "enum receiver was evaluated as a value instead of being recognised "
        f"as a type name:\n{result.stderr}"
    )


def test_qualified_variant_still_resolves_against_its_own_enum(tmp_path):
    """A qualifier must select *its* enum, not merely the first variant match.

    Two enums here share the variant name `Named`, with different payload
    arities. If the qualifier were ignored — the failure mode originally
    hypothesised for this bug — the wrong constructor would be selected and the
    payload would not typecheck. This guards the fix against being implemented
    as an unqualified `variant_to_enum` lookup.
    """
    source = """\
enum Color
    Red
    Named(*u8)

enum Shape
    Round
    Named(i32)

fn colour() -> Color
    if 1 == 1
        Color.Named(c"blue")
    else
        Color.Red

fn shape() -> Shape
    if 1 == 1
        Shape.Named(7)
    else
        Shape.Round

fn main() -> i32
    match colour()
        Color.Named(s) => 0
        Color.Red => 1
"""
    result = _compile(tmp_path, source)
    assert result.returncode == 0, (
        "a variant name shared by two enums must resolve via its qualifier:\n"
        f"{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 2. Located diagnostic for an undeclared variant
# ---------------------------------------------------------------------------

# `Blue` is never declared. This is the reduced form of the original lexis
# failure: a match arm naming a variant its enum does not have.
UNDECLARED_VARIANT = """\
enum Color
    Red
    Green

fn main() -> i32
    let c = Color.Red
    match c
        Color.Red => 0
        Color.Green => 1
        Color.Blue => 2
"""


def test_undeclared_variant_in_match_is_rejected(tmp_path):
    """Matching on a variant the enum does not declare must fail the build."""
    result = _compile(tmp_path, UNDECLARED_VARIANT)
    assert result.returncode != 0, (
        "a match arm naming an undeclared variant compiled successfully"
    )


def test_undeclared_variant_names_variant_and_enum(tmp_path):
    """The message must still identify both halves of the mismatch."""
    result = _compile(tmp_path, UNDECLARED_VARIANT)
    assert "Blue" in result.stderr and "Color" in result.stderr, (
        f"diagnostic named neither the variant nor the enum:\n{result.stderr}"
    )


def test_undeclared_variant_reports_source_location(tmp_path):
    """The diagnostic must carry `file:line:column`, not a bare ValueError.

    `Color.Blue` sits on line 10 of the source above. Pinning the line number
    (rather than merely looking for a colon) is what actually proves the span
    is the offending pattern's own, and not some unrelated node's.
    """
    result = _compile(tmp_path, UNDECLARED_VARIANT)
    assert "unit.ritz:10:" in result.stderr, (
        "expected a `file:line:column` location pointing at the bad pattern, "
        f"got:\n{result.stderr}"
    )


def test_undeclared_variant_does_not_emit_a_python_traceback(tmp_path):
    """A user error must be reported as a diagnostic, not an emitter crash.

    The original bug surfaced as an unhandled `ValueError` unwinding through
    `emitter_llvmlite.py`. A raw traceback is not a compiler diagnostic, so the
    absence of one is part of the contract.
    """
    result = _compile(tmp_path, UNDECLARED_VARIANT)
    assert "Traceback (most recent call last)" not in result.stderr, (
        f"undeclared variant crashed the emitter instead of reporting:\n{result.stderr}"
    )
