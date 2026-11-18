"""Tests for check_unused_imports.py (AGAST #3458, LARB review/5 harland F4).

The rule: a brace-imported name the file never mentions outside imports,
comments and strings is an error, unless the allowlist names it; an
allowlist entry that is no longer an unused import is an error too, so the
list only shrinks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_unused_imports import main, unused_imports  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
KERNEL = REPO / "projects" / "harland" / "kernel"
ALLOW = KERNEL / "unused_imports.allow"


def names(src: str) -> list[str]:
    return [n for (_, _, n) in unused_imports(src)]


class TestRule:
    def test_unused_and_used(self):
        src = "import io { outb, inb }\nfn f() -> i32\n    outb(1, 2)\n    0\n"
        assert names(src) == ["inb"]

    def test_comment_and_string_mentions_do_not_count(self):
        src = 'import io { inb }\n# inb is not called\nfn f() -> *u8\n    c"inb"\n'
        assert names(src) == ["inb"]

    def test_multiline_brace_list(self):
        src = "import sched.mod {\n    A, B,\n    C\n}\nfn f() -> u32\n    B\n"
        assert names(src) == ["A", "C"]

    def test_alias_binds_the_alias(self):
        src = "import io { inb as read_port }\nfn f() -> u8\n    read_port(1)\n"
        assert names(src) == []

    def test_asm_operand_counts_as_use(self):
        src = "import mm.vmm { PML4 }\nfn f() -> i32\n    asm x86_64:\n        movq {PML4}, %rax\n    0\n"
        assert names(src) == []

    def test_bare_import_unchecked(self):
        assert names("import io\nfn f() -> i32\n    0\n") == []


class TestAllowlist:
    @pytest.fixture
    def tree(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "a.ritz").write_text("import io { inb, outb }\nfn f() -> i32\n    outb(1, 2)\n")
        return tmp_path

    def test_unlisted_unused_is_red(self, tree):
        assert main([str(tree / "src")]) == 1

    def test_listed_unused_is_green(self, tree):
        (tree / "allow").write_text("# comment\nsrc/a.ritz inb\n")
        assert main(["--allow", str(tree / "allow"), str(tree / "src")]) == 0

    def test_stale_entry_is_red(self, tree, capsys):
        (tree / "allow").write_text("src/a.ritz inb\nsrc/a.ritz outb\n")
        assert main(["--allow", str(tree / "allow"), str(tree / "src")]) == 1
        assert "stale" in capsys.readouterr().out


class TestHarlandKernel:
    def test_main_ritz_has_no_unused_imports(self):
        assert unused_imports((KERNEL / "src" / "main.ritz").read_text()) == []

    def test_planted_unused_import_in_main_is_red(self, tmp_path):
        planted = tmp_path / "main.ritz"
        planted.write_text("import io { cpu_pause }\n" + (KERNEL / "src" / "main.ritz").read_text())
        assert main([str(planted)]) == 1

    def test_main_ritz_is_not_allowlisted(self):
        assert "src/main.ritz" not in ALLOW.read_text()

    def test_kernel_tree_clean_against_allowlist(self, capsys):
        rc = main(["--allow", str(ALLOW), str(KERNEL / "src")])
        assert rc == 0, capsys.readouterr().out


def test_kernel_asm_pause_only_in_io_ritz():
    """LARB review/5 harland F5: spin loops call io.cpu_pause(); the `pause`
    instruction is written once, in io.ritz."""
    import re

    hits = [
        f"{p.relative_to(KERNEL)}:{i}"
        for p in sorted((KERNEL / "src").rglob("*.ritz"))
        for i, line in enumerate(p.read_text().splitlines(), 1)
        if re.fullmatch(r"\s*pause\s*", line)
    ]
    assert len(hits) == 1 and hits[0].startswith("src/io.ritz:"), hits
