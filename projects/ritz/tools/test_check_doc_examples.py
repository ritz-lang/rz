#!/usr/bin/env python3
"""Tests for the documentation example checker (AGAST #1311).

The checker's whole value is that it FAILS on bad documentation. A checker
that silently passes everything is worth less than nothing, because it
occupies the slot where a real check would go — that is exactly the defect
this task exists to fix. So the tests below are weighted toward the
negative cases: malformed fences, unlabelled opt-outs, `expect-error`
blocks that started compiling, and real pre-RERITZ syntax.

Run with:  cd projects/ritz && python -m pytest tools/test_check_doc_examples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_doc_examples as C  # noqa: E402


def write(tmp_path: Path, text: str, name: str = "DOC.md") -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extracts_only_ritz_blocks(tmp_path):
    doc = write(
        tmp_path,
        "intro\n"
        "```ritz\n"
        "fn main() -> i32\n"
        "    return 0\n"
        "```\n"
        "```bash\n"
        "make test\n"
        "```\n"
        "```\n"
        "plain\n"
        "```\n",
    )
    blocks = C.extract_blocks(doc)
    assert len(blocks) == 1
    assert blocks[0].line == 2
    assert blocks[0].code.startswith("fn main()")


@pytest.mark.unit
def test_extracts_indented_fence_inside_list_item(tmp_path):
    doc = write(
        tmp_path,
        "- an example:\n"
        "\n"
        "  ```ritz\n"
        "  fn main() -> i32\n"
        "      return 0\n"
        "  ```\n",
    )
    (block,) = C.extract_blocks(doc)
    # The fence's own indentation must be stripped, or every indented
    # example would fail on a bogus INDENT at line 1.
    assert block.code == "fn main() -> i32\n    return 0"


@pytest.mark.unit
def test_ritz_fence_nested_in_longer_outer_fence_is_not_extracted(tmp_path):
    """Documenting the checker requires showing ```ritz fences verbatim."""
    doc = write(
        tmp_path,
        "````\n"
        "```ritz no-compile=\"this is documentation of the fence syntax\"\n"
        "whatever\n"
        "```\n"
        "````\n",
    )
    assert C.extract_blocks(doc) == []


@pytest.mark.unit
def test_unterminated_fence_is_an_error(tmp_path):
    doc = write(tmp_path, "```ritz\nfn main() -> i32\n    return 0\n")
    with pytest.raises(C.FenceError, match="unterminated"):
        C.extract_blocks(doc)


# ---------------------------------------------------------------------------
# Fence info-string parsing — the opt-out discipline
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("info", ["ritz body", "ritz,body"])
def test_body_attribute_accepts_both_separators(tmp_path, info):
    doc = write(tmp_path, f"```{info}\nlet x = 1\n```\n")
    (block,) = C.extract_blocks(doc)
    assert block.mode == "body"


@pytest.mark.unit
def test_unknown_attribute_is_rejected(tmp_path):
    """A typo must not silently degrade an assertion into a plain compile."""
    doc = write(tmp_path, '```ritz expect-eror="oops"\nlet x = 1\n```\n')
    with pytest.raises(C.FenceError, match="unknown fence attribute"):
        C.extract_blocks(doc)


@pytest.mark.unit
def test_no_compile_without_a_reason_is_rejected(tmp_path):
    doc = write(tmp_path, "```ritz no-compile\nsomething\n```\n")
    with pytest.raises(C.FenceError, match="requires a reason"):
        C.extract_blocks(doc)


@pytest.mark.unit
@pytest.mark.parametrize("reason", ["", "fragment", "TODO", "n/a"])
def test_no_compile_with_a_shrug_for_a_reason_is_rejected(tmp_path, reason):
    doc = write(tmp_path, f'```ritz no-compile="{reason}"\nsomething\n```\n')
    with pytest.raises(C.FenceError, match="requires a reason"):
        C.extract_blocks(doc)


@pytest.mark.unit
def test_no_compile_with_a_real_reason_is_accepted_and_reported(tmp_path):
    reason = "pseudo-code sketch of the not-yet-implemented trait system"
    doc = write(tmp_path, f'```ritz no-compile="{reason}"\ntrait Show\n```\n')
    (block,) = C.extract_blocks(doc)
    assert block.no_compile_reason == reason


@pytest.mark.unit
def test_bare_expect_error_is_rejected(tmp_path):
    """`expect-error` alone asserts only that *something* went wrong."""
    doc = write(tmp_path, "```ritz expect-error\nlet mut x = 1\n```\n")
    with pytest.raises(C.FenceError, match="must name the diagnostic"):
        C.extract_blocks(doc)


@pytest.mark.unit
def test_expect_error_and_no_compile_are_mutually_exclusive(tmp_path):
    doc = write(
        tmp_path,
        '```ritz expect-error="got MUT" no-compile="it is awkward to compile"\n'
        "let mut x = 1\n"
        "```\n",
    )
    with pytest.raises(C.FenceError, match="cannot be both"):
        C.extract_blocks(doc)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_body_blocks_are_wrapped_and_indented(tmp_path):
    doc = write(tmp_path, "```ritz body\nlet x = 1\n\nlet y = 2\n```\n")
    (block,) = C.extract_blocks(doc)
    rendered = C.render(block)
    assert rendered.splitlines()[0].startswith("fn ")
    assert "    let x = 1" in rendered
    assert "    let y = 2" in rendered
    assert rendered.rstrip().endswith("return 0")
    # Blank lines stay blank rather than becoming trailing-whitespace lines.
    assert "\n\n" in rendered


# ---------------------------------------------------------------------------
# Compiling — the part that has to actually catch the bug
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_good_block_passes(tmp_path):
    doc = write(tmp_path, "```ritz\nfn main() -> i32\n    return 0\n```\n")
    report = C.run([doc], jobs=2, verbose=False)
    assert report.failures == []
    assert len(report.compiled) == 1


@pytest.mark.integration
@pytest.mark.parametrize(
    "snippet",
    [
        "let mut s = 1",  # `mut` is not a Ritz keyword; `var` is
        "let r: &i64 = @x",  # legacy `&T` reference type
        "let p = &x",  # legacy `&x` address-of
        'let s = String::from("hello")',  # `::` path syntax
    ],
    ids=["let-mut", "amp-type", "amp-address-of", "colon-colon"],
)
def test_pre_reritz_syntax_fails(tmp_path, snippet):
    """The four constructs measured in AGAST #1311, verbatim.

    If any of these starts passing, either the compiler grew the syntax
    back or this checker stopped compiling anything. Both are worth a
    red build.
    """
    doc = write(tmp_path, f"```ritz body\nvar x: i64 = 1\n{snippet}\n```\n")
    report = C.run([doc], jobs=2, verbose=False)
    assert len(report.failures) == 1, report.failures


@pytest.mark.integration
def test_expect_error_block_passes_when_it_fails_as_declared(tmp_path):
    doc = write(
        tmp_path,
        '```ritz body expect-error="Expected IDENT, got MUT"\n'
        "let mut s = 1\n"
        "```\n",
    )
    report = C.run([doc], jobs=2, verbose=False)
    assert report.failures == []


@pytest.mark.integration
def test_expect_error_block_fails_when_the_diagnostic_changed(tmp_path):
    """A stale claim about *which* error you get is still a stale doc."""
    doc = write(
        tmp_path,
        '```ritz body expect-error="Expected SEMICOLON, got MUT"\n'
        "let mut s = 1\n"
        "```\n",
    )
    report = C.run([doc], jobs=2, verbose=False)
    assert len(report.failures) == 1
    assert "not with the declared diagnostic" in report.failures[0].detail


@pytest.mark.integration
def test_expect_error_block_fails_when_the_block_starts_compiling(tmp_path):
    doc = write(
        tmp_path,
        '```ritz expect-error="this will never happen"\n'
        "fn main() -> i32\n"
        "    return 0\n"
        "```\n",
    )
    report = C.run([doc], jobs=2, verbose=False)
    assert len(report.failures) == 1
    assert "COMPILED" in report.failures[0].detail


@pytest.mark.integration
def test_no_compile_block_is_skipped_but_counted(tmp_path):
    doc = write(
        tmp_path,
        '```ritz no-compile="illustrative pseudo-code, not real Ritz"\n'
        "this is not ritz at all !!!\n"
        "```\n",
    )
    report = C.run([doc], jobs=2, verbose=False)
    assert report.failures == []
    assert len(report.skips) == 1
    assert report.skips[0].detail.startswith("illustrative")


@pytest.mark.integration
def test_missing_document_is_an_error():
    assert C.main(["does/not/exist.md"]) == 1


@pytest.mark.integration
def test_main_returns_nonzero_on_a_broken_block(tmp_path):
    doc = write(tmp_path, "```ritz body\nlet mut s = 1\n```\n")
    assert C.main([str(doc)]) == 1


@pytest.mark.integration
def test_main_returns_zero_on_a_good_document(tmp_path):
    doc = write(tmp_path, "```ritz\nfn main() -> i32\n    return 0\n```\n")
    assert C.main([str(doc)]) == 0


@pytest.mark.unit
def test_compiler_identity_names_the_reference_compiler():
    """A green run must say what it was green against."""
    identity = C.compiler_identity()
    assert "ritz0" in identity
