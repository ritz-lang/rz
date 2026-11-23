"""Tests for check_unused_imports.py (AGAST #3458, #4174, LARB review/5 harland F4).

The rule: a brace-imported name the file never mentions outside imports,
comments and strings is an error. There is no allowlist: #3458 added one so
the pre-existing offenders could ratchet down, and #4174 burned it to zero
and deleted it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_unused_imports import main, unused_imports  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
KERNEL = REPO / "projects" / "harland" / "kernel"
# What the kernel and the UEFI loader both compile (AGAST #4578), and the loader.
ABI = REPO / "projects" / "harland" / "boot_abi" / "src"
BOOT_SRC = REPO / "projects" / "harland" / "boot" / "src"
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


class TestHarlandKernel:
    def test_main_ritz_has_no_unused_imports(self):
        assert unused_imports((KERNEL / "src" / "main.ritz").read_text()) == []

    def test_planted_unused_import_in_main_is_red(self, tmp_path):
        planted = tmp_path / "main.ritz"
        planted.write_text(
            "import io { cpu_pause }\n" + (KERNEL / "src" / "main.ritz").read_text()
        )
        assert main([str(planted)]) == 1

    def test_unused_import_allowlist_is_gone(self):
        """AGAST #4174: the list ratcheted to empty; keeping the file would
        let a new unused import be papered over again."""
        assert not ALLOW.exists(), f"{ALLOW} is empty and must be deleted"

    def test_kernel_tree_has_no_unused_imports(self, capsys):
        rc = main([str(KERNEL / "src")])
        assert rc == 0, capsys.readouterr().out

    def test_abi_and_loader_have_no_unused_imports(self, capsys):
        rc = main([str(ABI), str(BOOT_SRC)])
        assert rc == 0, capsys.readouterr().out


def test_asm_pause_only_in_abi_portio():
    """LARB review/5 harland F5: spin loops call cpu_pause(); the `pause`
    instruction is written once. Since AGAST #4578 that is boot_abi/src/portio.ritz,
    which the kernel (via io.ritz) and the UEFI loader share."""
    import re

    hits = [
        f"{p.relative_to(KERNEL.parent)}:{i}"
        for root in (KERNEL / "src", ABI, BOOT_SRC)
        for p in sorted(root.rglob("*.ritz"))
        for i, line in enumerate(p.read_text().splitlines(), 1)
        if re.fullmatch(r"\s*pause\s*", line)
    ]
    assert len(hits) == 1 and hits[0].startswith("boot_abi/src/portio.ritz:"), hits
