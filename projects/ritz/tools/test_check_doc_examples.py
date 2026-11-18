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

import re
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


# ---------------------------------------------------------------------------
# expect-runtime-error (AGAST #1869): the block compiles, RUNS, exits
# non-zero, and its stderr contains the declared text.
# ---------------------------------------------------------------------------

FAILING_ASSERT = (
    "[[test]]\n"
    "fn test_sum() -> i32\n"
    "    let got: i32 = 1 + 2\n"
    "    assert got == 4\n"
    "    0\n"
    "\n"
    "fn main() -> i32\n"
    "    test_sum()\n"
)


@pytest.mark.unit
def test_bare_expect_runtime_error_is_rejected(tmp_path):
    doc = write(tmp_path, "```ritz expect-runtime-error\nfn main() -> i32\n    0\n```\n")
    with pytest.raises(C.FenceError, match="must name"):
        C.extract_blocks(doc)


@pytest.mark.unit
@pytest.mark.parametrize("other", ['expect-error="x"', 'no-compile="a long enough reason"', "body"])
def test_expect_runtime_error_excludes_other_modes(tmp_path, other):
    doc = write(tmp_path, f'```ritz expect-runtime-error="x" {other}\nfn main() -> i32\n    0\n```\n')
    with pytest.raises(C.FenceError):
        C.extract_blocks(doc)


@pytest.mark.unit
def test_expect_runtime_error_decodes_newline_escapes(tmp_path):
    doc = write(tmp_path, '```ritz expect-runtime-error="a\\nb \\\\n"\nfn main() -> i32\n    0\n```\n')
    (block,) = C.extract_blocks(doc)
    assert block.expect_runtime_error == "a\nb \\n"


@pytest.mark.integration
def test_expect_runtime_error_passes_when_stderr_matches(tmp_path):
    doc = write(
        tmp_path,
        '```ritz expect-runtime-error="left:  3\\n  right: 4"\n' + FAILING_ASSERT + "```\n",
    )
    report = C.run([doc], jobs=2, verbose=False)
    assert report.failures == [], [r.detail for r in report.failures]
    assert len(report.compiled) == 1


@pytest.mark.integration
def test_expect_runtime_error_fails_when_stderr_differs(tmp_path):
    doc = write(
        tmp_path,
        '```ritz expect-runtime-error="left:  5"\n' + FAILING_ASSERT + "```\n",
    )
    report = C.run([doc], jobs=2, verbose=False)
    assert len(report.failures) == 1
    assert "not with the declared stderr" in report.failures[0].detail


@pytest.mark.integration
def test_expect_runtime_error_fails_when_the_program_succeeds(tmp_path):
    doc = write(
        tmp_path,
        '```ritz expect-runtime-error="anything"\n'
        "fn main() -> i32\n"
        "    0\n"
        "```\n",
    )
    report = C.run([doc], jobs=2, verbose=False)
    assert len(report.failures) == 1
    assert "exited 0" in report.failures[0].detail


@pytest.mark.integration
def test_expect_runtime_error_fails_when_it_does_not_compile(tmp_path):
    doc = write(
        tmp_path,
        '```ritz expect-runtime-error="anything"\n'
        "fn main() -> i32\n"
        "    let mut s = 1\n"
        "```\n",
    )
    report = C.run([doc], jobs=2, verbose=False)
    assert len(report.failures) == 1
    assert "did not compile" in report.failures[0].detail


# ---------------------------------------------------------------------------
# Emitted IR is parsed (AGAST #1358 follow-up 1). For seven months the
# documented `token.kind == TokenKind.Ident` idiom compiled to .ll with exit 0
# while the .ll held `icmp eq` on a struct, which clang's parser rejects. A
# gate that stops at "ritz0 exited 0" cannot see that. ritz0 no longer emits
# that IR, so a stub compiler stands in for the February one.
# ---------------------------------------------------------------------------

# Verbatim shape of the IR main @ f336bae emitted for the STYLE.md block.
INVALID_IR = """\
%"enum.TokenKind" = type { i8 }

define i32 @main() {
entry:
  %a = insertvalue %"enum.TokenKind" undef, i8 0, 0
  %b = insertvalue %"enum.TokenKind" undef, i8 1, 0
  %eq = icmp eq %"enum.TokenKind" %a, %b
  ret i32 0
}
"""

VALID_IR = "define i32 @main() {\nentry:\n  ret i32 0\n}\n"


def _stub_compiler(tmp_path: Path, monkeypatch, ir: str) -> None:
    """Point the checker at a 'compiler' that exits 0 and writes `ir`."""
    canned = tmp_path / "canned.ll"
    canned.write_text(ir)
    stub = tmp_path / "stub_ritz0.py"
    stub.write_text(
        "import shutil, sys\n"
        f"shutil.copy({str(canned)!r}, sys.argv[sys.argv.index('-o') + 1])\n"
    )
    monkeypatch.setattr(C, "RITZ0", stub)


@pytest.mark.unit
def test_verify_ir_rejects_icmp_on_a_struct(tmp_path):
    ll = tmp_path / "bad.ll"
    ll.write_text(INVALID_IR)
    problem = C.verify_ir(ll)
    assert problem is not None and "icmp" in problem


@pytest.mark.unit
def test_verify_ir_runs_the_verifier_not_just_the_parser(tmp_path):
    """Parses fine, but %x does not dominate its use. clang rejects it as a
    broken module, so the gate must too."""
    ll = tmp_path / "undominated.ll"
    ll.write_text(
        "define i32 @f() {\n"
        "entry:\n  br label %use\n"
        "use:\n  ret i32 %x\n"
        "def:\n  %x = add i32 1, 1\n  br label %use\n"
        "}\n"
    )
    problem = C.verify_ir(ll)
    assert problem is not None and "dominate" in problem


@pytest.mark.unit
def test_verify_ir_accepts_valid_ir(tmp_path):
    ll = tmp_path / "good.ll"
    ll.write_text(VALID_IR)
    assert C.verify_ir(ll) is None


@pytest.mark.integration
def test_block_whose_ir_does_not_parse_fails(tmp_path, monkeypatch):
    _stub_compiler(tmp_path, monkeypatch, INVALID_IR)
    doc = write(tmp_path, "```ritz\nfn main() -> i32\n    0\n```\n")
    report = C.run([doc], jobs=2, verbose=False)
    assert len(report.failures) == 1, report.results
    assert "invalid IR" in report.failures[0].detail


@pytest.mark.integration
def test_expect_runtime_error_block_with_invalid_ir_names_the_ir(tmp_path, monkeypatch):
    """Fails at the IR check, not at clang with a red-herring link error."""
    _stub_compiler(tmp_path, monkeypatch, INVALID_IR)
    doc = write(tmp_path, '```ritz expect-runtime-error="x"\nfn main() -> i32\n    0\n```\n')
    report = C.run([doc], jobs=2, verbose=False)
    assert len(report.failures) == 1
    assert "invalid IR" in report.failures[0].detail


@pytest.mark.integration
def test_block_whose_ir_parses_passes_with_stub(tmp_path, monkeypatch):
    """Control: the stub itself is not what fails the block above."""
    _stub_compiler(tmp_path, monkeypatch, VALID_IR)
    doc = write(tmp_path, "```ritz\nfn main() -> i32\n    0\n```\n")
    report = C.run([doc], jobs=2, verbose=False)
    assert report.failures == [], [r.detail for r in report.failures]


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


# ---------------------------------------------------------------------------
# --compiler ritz1 / ritz1_selfhosted (AGAST #3928).
#
# The gate checked docs with ritz0 alone, so an example ritz1 refuses passed
# it.  These run against a FAKE ritz1 binary: `make tools-unit` runs before
# CI's ritz1 build, and a fake pins each behaviour (refuse, crash, accept,
# bad IR) independently of which ritz1 bugs are open today.
# ---------------------------------------------------------------------------

# A main that writes "boom" to stderr and returns 3, linked against
# runtime/ritz_start.x86_64.ll: ritz1 emits no `_start` of its own.
RUNTIME_ERROR_IR = """\
@msg = private constant [4 x i8] c"boom"

define i32 @main(i32 %argc, ptr %argv) {
entry:
  %r = call i64 asm sideeffect "syscall", "={rax},{rax},{rdi},{rsi},{rdx},~{rcx},~{r11},~{memory}"(i64 1, i64 2, ptr @msg, i64 4)
  ret i32 3
}
"""

FAKE_RITZ1 = {
    # Refuses everything with a located diagnostic in ritz1's own words.
    "refuse": "import sys\nsys.stderr.write(sys.argv[1] + ':2:5: error: unexpected thing\\n')\nsys.exit(1)\n",
    # Dies on a signal: a crash is not a refusal.
    "crash": "import os, signal\nos.kill(os.getpid(), signal.SIGSEGV)\n",
    # Exits 1 and says nothing.
    "silent": "import sys\nsys.exit(1)\n",
}


def _fake_ritz1(tmp_path: Path, monkeypatch, mode: str, ir: str = VALID_IR,
                name: str = "ritz1") -> Path:
    """Install an executable stand-in for ritz1 (or ritz1_selfhosted)."""
    fake = tmp_path / f"fake_{name}"
    if mode == "accept":
        canned = tmp_path / f"canned_{name}.ll"
        canned.write_text(ir)
        body = ("import shutil, sys\n"
                f"shutil.copy({str(canned)!r}, sys.argv[sys.argv.index('-o') + 1])\n")
    else:
        body = FAKE_RITZ1[mode]
    fake.write_text(f"#!{sys.executable}\n{body}")
    fake.chmod(0o755)
    monkeypatch.setitem(C.COMPILERS, name, (fake, "make it"))
    return fake


GOOD = "```ritz\nfn main() -> i32\n    return 0\n```\n"


@pytest.mark.integration
def test_planted_example_ritz0_accepts_and_ritz1_refuses_fails_the_gate(tmp_path, monkeypatch):
    """The acceptance case: green under ritz0, red under ritz1."""
    doc = write(tmp_path, GOOD)
    _fake_ritz1(tmp_path, monkeypatch, "refuse")
    assert C.main([str(doc)]) == 0
    assert C.main(["--compiler", "ritz1", str(doc)]) == 1


@pytest.mark.unit
def test_ritz1_selfhosted_is_checked_with_its_own_binary(tmp_path, monkeypatch):
    """ritz1 passing must not stand in for ritz1_selfhosted."""
    doc = write(tmp_path, GOOD)
    _fake_ritz1(tmp_path, monkeypatch, "accept", name="ritz1")
    _fake_ritz1(tmp_path, monkeypatch, "refuse", name="ritz1_selfhosted")
    assert C.main(["--compiler", "ritz1", str(doc)]) == 0
    assert C.main(["--compiler", "ritz1_selfhosted", str(doc)]) == 1


@pytest.mark.unit
def test_ritz1_gets_the_ritz_root_as_its_import_path(tmp_path):
    cmd = C.compile_cmd("ritz1", tmp_path / "a.ritz", tmp_path / "a.ll")
    assert cmd[0] == str(C.COMPILERS["ritz1"][0])
    assert cmd[-2:] == ["-I", str(C.RITZ_ROOT)]


@pytest.mark.unit
def test_a_missing_ritz1_binary_is_an_error_not_a_skip(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(C.COMPILERS, "ritz1", (tmp_path / "nope", "make -C x ritz1-bootstrap"))
    doc = write(tmp_path, GOOD)
    assert C.main(["--compiler", "ritz1", str(doc)]) == 1
    assert "ritz1-bootstrap" in capsys.readouterr().err


@pytest.mark.unit
def test_ritz1_invalid_ir_fails_and_names_ritz1(tmp_path, monkeypatch):
    doc = write(tmp_path, GOOD)
    _fake_ritz1(tmp_path, monkeypatch, "accept", ir=INVALID_IR)
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1")
    assert len(report.failures) == 1
    assert report.failures[0].detail.startswith("ritz1 exited 0 but emitted invalid IR")


EXPECT_ERR = '```ritz body expect-error="Expected IDENT, got MUT"\nlet mut s = 1\n```\n'


@pytest.mark.unit
def test_ritz1_refusing_an_expect_error_block_in_its_own_words_passes(tmp_path, monkeypatch):
    """ritz0's diagnostic text is not ritz1's; the refusal is what's held."""
    doc = write(tmp_path, EXPECT_ERR)
    _fake_ritz1(tmp_path, monkeypatch, "refuse")
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1")
    assert report.failures == [], [r.detail for r in report.failures]


@pytest.mark.unit
def test_ritz1_compiling_an_expect_error_block_fails(tmp_path, monkeypatch):
    doc = write(tmp_path, EXPECT_ERR)
    _fake_ritz1(tmp_path, monkeypatch, "accept")
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1")
    assert len(report.failures) == 1
    assert "COMPILED" in report.failures[0].detail


@pytest.mark.unit
@pytest.mark.parametrize("mode", ["crash", "silent"])
def test_ritz1_crashing_or_silent_on_an_expect_error_block_fails(tmp_path, monkeypatch, mode):
    doc = write(tmp_path, EXPECT_ERR)
    _fake_ritz1(tmp_path, monkeypatch, mode)
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1")
    assert len(report.failures) == 1
    assert "not a refusal" in report.failures[0].detail


@pytest.mark.unit
@pytest.mark.parametrize("pos, ok", [("2:5", True), ("4:13", False)])
def test_ritz1_must_point_at_a_pinned_position(tmp_path, monkeypatch, pos, ok):
    """The fake reports :2:5:; a fence pinning another place fails."""
    doc = write(tmp_path, f'```ritz expect-error=".ritz:{pos}: whatever ritz0 says"\nfn f()\n```\n')
    _fake_ritz1(tmp_path, monkeypatch, "refuse")
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1")
    assert (report.failures == []) is ok, [r.detail for r in report.failures]


@pytest.mark.integration
def test_ritz1_expect_runtime_error_links_the_runtime_start(tmp_path, monkeypatch):
    """ritz1's IR has no `_start`.  Without the runtime, ld enters at `main`
    and returning from it segfaults: still non-zero, still "boom", so the
    exit status (main's 3, via the runtime's exit syscall) is what tells."""
    doc = write(tmp_path, '```ritz expect-runtime-error="boom"\nfn main() -> i32\n    3\n```\n')
    _fake_ritz1(tmp_path, monkeypatch, "accept", ir=RUNTIME_ERROR_IR)
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1")
    assert report.failures == [], [r.detail for r in report.failures]
    assert report.results[0].detail.endswith("(exit 3)"), report.results[0].detail


# KNOWN_FAILURES: each entry names an open ticket and is held to its claim.


def _known_for(doc: Path, reason: str = "#1: tracked") -> dict:
    (block,) = C.extract_blocks(doc)
    return {("ritz1", doc.name, block.digest): reason}


@pytest.mark.unit
def test_a_known_failure_is_reported_with_its_ticket_and_does_not_fail(tmp_path, monkeypatch):
    doc = write(tmp_path, GOOD)
    _fake_ritz1(tmp_path, monkeypatch, "refuse")
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1", known=_known_for(doc))
    assert report.failures == []
    assert [r.known for r in report.known] == ["#1: tracked"]


@pytest.mark.unit
def test_a_known_failure_is_per_compiler(tmp_path, monkeypatch):
    """An entry for ritz1 does not excuse ritz1_selfhosted."""
    doc = write(tmp_path, GOOD)
    _fake_ritz1(tmp_path, monkeypatch, "refuse", name="ritz1_selfhosted")
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1_selfhosted",
                   known=_known_for(doc))
    assert len(report.failures) == 1


@pytest.mark.unit
def test_a_known_failure_that_now_passes_fails_the_run(tmp_path, monkeypatch):
    doc = write(tmp_path, GOOD)
    _fake_ritz1(tmp_path, monkeypatch, "accept")
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1", known=_known_for(doc))
    assert len(report.failures) == 1
    assert "now passes" in report.failures[0].detail


@pytest.mark.unit
def test_a_known_failure_matching_no_block_fails_the_run(tmp_path, monkeypatch):
    """An edited block gets a new digest, so its old entry is stale."""
    doc = write(tmp_path, GOOD)
    known = _known_for(doc)
    doc.write_text(GOOD.replace("return 0", "return 1"))
    _fake_ritz1(tmp_path, monkeypatch, "refuse")
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1", known=known)
    details = [r.detail for r in report.failures]
    assert len(details) == 2, details  # the edited block, and the stale entry
    assert any("matches no block" in d for d in details)


@pytest.mark.unit
def test_digest_ignores_position_but_not_content_or_fence(tmp_path):
    a = C.extract_blocks(write(tmp_path, GOOD, "A.md"))[0]
    b = C.extract_blocks(write(tmp_path, "prose\n\n" + GOOD, "B.md"))[0]
    c = C.extract_blocks(write(tmp_path, GOOD.replace("```ritz\n", "```ritz items\n"), "C.md"))[0]
    assert a.line != b.line and a.digest == b.digest
    assert a.digest != c.digest


@pytest.mark.unit
def test_every_real_known_failure_names_a_ticket_and_a_ritz1_compiler():
    for (compiler, doc, digest), reason in C.KNOWN_FAILURES.items():
        assert compiler in ("ritz1", "ritz1_selfhosted"), (compiler, doc, digest)
        assert C.TICKET_RE.match(reason), (doc, digest, reason)
        assert (C.RITZ_ROOT / "docs" / doc).is_file(), doc
        assert re.fullmatch(r"[0-9a-f]{12}", digest), digest


# KNOWN_FAILURES lives in tools/doc_known_failures/<ticket>.txt (AGAST #3963):
# fixing a ticket deletes its own file, so two doc-bug fixes never touch the
# same hunk.


def _kf_dir(tmp_path: Path, files: dict[str, str]) -> Path:
    d = tmp_path / "kf"
    d.mkdir()
    for name, text in files.items():
        (d / name).write_text(text)
    return d


@pytest.mark.unit
def test_known_failures_load_one_entry_per_line_reason_prefixed_by_the_files_ticket(tmp_path):
    d = _kf_dir(tmp_path, {
        "3929.txt": "# LANGUAGE_SPEC.md:246\n"
                    "ritz1 LANGUAGE_SPEC.md 065c93f07ee5 float literal exponents don't lex\n"
                    "\n"
                    "ritz1_selfhosted  LANGUAGE_SPEC.md  065c93f07ee5  float literal exponents don't lex\n",
        "1295.txt": "ritz1 STDLIB_REFERENCE.md 014099d52fe2 multi-field enum variants\n",
    })
    assert C.load_known_failures(d) == {
        ("ritz1", "LANGUAGE_SPEC.md", "065c93f07ee5"): "#3929: float literal exponents don't lex",
        ("ritz1_selfhosted", "LANGUAGE_SPEC.md", "065c93f07ee5"):
            "#3929: float literal exponents don't lex",
        ("ritz1", "STDLIB_REFERENCE.md", "014099d52fe2"): "#1295: multi-field enum variants",
    }


@pytest.mark.unit
@pytest.mark.parametrize("files, needle", [
    ({"3929.txt": "ritz1 LANGUAGE_SPEC.md 065c93f07ee5\n"}, "3929.txt:1"),  # no reason
    ({"3929.txt": "ritz1 LANGUAGE_SPEC.md 065c93f07EE5 why\n"}, "3929.txt:1"),  # bad digest
    ({"3929.txt": "ritz0 LANGUAGE_SPEC.md 065c93f07ee5 why\n"}, "3929.txt:1"),  # not ritz1
    ({"floats.txt": "ritz1 LANGUAGE_SPEC.md 065c93f07ee5 why\n"}, "floats.txt"),  # no ticket
    ({"1.txt": "ritz1 A.md 065c93f07ee5 why\n",
      "2.txt": "ritz1 A.md 065c93f07ee5 why\n"}, "2.txt:1"),  # listed twice
])
def test_known_failures_refuse_a_malformed_entry_naming_its_file_and_line(tmp_path, files, needle):
    with pytest.raises(ValueError, match=re.escape(needle)):
        C.load_known_failures(_kf_dir(tmp_path, files))


@pytest.mark.unit
def test_a_known_failure_that_now_passes_names_the_file_to_delete_it_from(tmp_path, monkeypatch):
    doc = write(tmp_path, GOOD)
    _fake_ritz1(tmp_path, monkeypatch, "accept")
    report = C.run([doc], jobs=1, verbose=False, compiler="ritz1",
                   known=_known_for(doc, "#3929: floats"))
    assert "tools/doc_known_failures/3929.txt" in report.failures[0].detail


@pytest.mark.unit
def test_the_real_list_is_the_checked_in_directory():
    assert C.KNOWN_FAILURES == C.load_known_failures(C.KNOWN_FAILURES_DIR)
    assert C.KNOWN_FAILURES_DIR == Path(C.__file__).parent / "doc_known_failures"


@pytest.mark.unit
def test_deleting_neighbouring_tickets_entries_cherry_picks_in_either_order(tmp_path):
    """The point of #3963: two doc-bug fixes, each deleting its own ticket's
    entries from the real list, land in either order without a conflict."""
    import shutil
    import subprocess

    def git(*args: str) -> str:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                               "-c", "commit.gpgsign=false", *args], cwd=tmp_path / "repo",
                              capture_output=True, text=True, check=True).stdout.strip()

    (tmp_path / "repo").mkdir()
    git("init", "-q", "-b", "base")
    shutil.copytree(C.KNOWN_FAILURES_DIR, tmp_path / "repo" / "kf")
    git("add", "-A")
    git("commit", "-qm", "base")
    first, second = sorted((tmp_path / "repo" / "kf").glob("*.txt"))[:2]  # neighbours
    fixes = []
    for f in (first, second):
        git("checkout", "-q", "-b", f"fix-{f.stem}", "base")
        git("rm", "-q", f"kf/{f.name}")
        git("commit", "-qm", f"fix {f.stem}")
        fixes.append(git("rev-parse", "HEAD"))
    for order in (fixes, fixes[::-1]):
        git("checkout", "-q", "-B", "train", "base")
        for sha in order:
            git("cherry-pick", sha)  # check=True: a conflict raises
        assert not first.exists() and not second.exists()
        assert C.load_known_failures(tmp_path / "repo" / "kf") == {
            k: v for k, v in C.KNOWN_FAILURES.items()
            if not v.startswith((f"#{first.stem}:", f"#{second.stem}:"))}


# The gate's wiring (AGAST #3928): main.yml's bootstrap job is what ci-local,
# every room gate and every train run.  Same shape as #3805's
# tools/test_ritzlib_tests_ritz1.py.

DOC_TARGET = "check-doc-examples-ritz1"


@pytest.mark.unit
def test_bootstrap_job_checks_doc_examples_under_ritz1_after_the_build():
    import ci_local

    steps = [s for s in ci_local.load_steps() if s.job == "bootstrap"]
    runs = [s.run.strip() for s in steps]
    assert f"make {DOC_TARGET}" in runs, runs
    assert steps[runs.index(f"make {DOC_TARGET}")].workdir == "projects/ritz"
    assert runs.index("make ritz1-bootstrap") < runs.index(f"make {DOC_TARGET}")
    assert "make check-doc-examples" in runs  # ritz0's run stays


@pytest.mark.unit
def test_doc_target_checks_the_same_docs_under_both_ritz1_compilers():
    import subprocess

    def dry(target: str) -> list[str]:
        out = subprocess.run(["make", "-n", "--no-print-directory", target], cwd=C.RITZ_ROOT,
                             capture_output=True, text=True, check=True).stdout
        return [ln for ln in out.splitlines() if "check_doc_examples.py" in ln]

    ritz1_runs = dry(DOC_TARGET)
    compilers = sorted(ln.split("--compiler", 1)[1].split()[0] for ln in ritz1_runs)
    assert compilers == ["ritz1", "ritz1_selfhosted"], ritz1_runs
    (ritz0_run,) = dry("check-doc-examples")
    docs = ritz0_run.split("check_doc_examples.py", 1)[1].split()
    for ln in ritz1_runs:
        assert ln.split()[-len(docs):] == docs, ln


@pytest.mark.unit
def test_doc_target_builds_both_compilers_first():
    makefile = (C.RITZ_ROOT / "Makefile").read_text()
    line = next(ln for ln in makefile.splitlines() if ln.startswith(f"{DOC_TARGET}:"))
    assert "ritz1-bootstrap" in line.split(":", 1)[1]
    assert f".PHONY: {DOC_TARGET}" in makefile
