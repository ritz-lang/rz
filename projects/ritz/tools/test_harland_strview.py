"""Harland's UEFI binaries share ritzlib's StrView (AGAST #4601, from #1885).

The kernel took ritzlib.strview's StrView in #1885, but the UEFI loader
(boot/src/main.ritz) and HWINV (inventory/src/main.ritz) kept a private
`struct StrView { ptr, len }`: ritzlib.strview imported ritzlib.memory
(malloc), which they can't link. ritzlib.strview is heap-free now (BARE in
tools/ritzlib_layers.py), so no harland binary declares its own, and the
loader's `prints` wrapper over serial_write is gone with it.

These read harland's source. Runs in `make tools-unit`.
"""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HARLAND = Path(__file__).resolve().parents[2] / "harland"

# Every harland source tree that once carried a private StrView.
TREES = ["kernel/src", "boot/src", "inventory/src", "boot_abi/src"]

STRUCT = re.compile(r"^\s*(?:pub\s+)?struct\s+StrView\b")
PRINTS = re.compile(r"^\s*(?:pub\s+)?fn\s+prints\s*\(")
IMPORT = re.compile(r"^\s*(?:pub\s+)?import\s+ritzlib\.strview\b")


def hits(pattern, trees):
    """'path:line: text' for each line of a .ritz file under trees matching pattern."""
    out = []
    for tree in trees:
        for path in sorted((HARLAND / tree).rglob("*.ritz")):
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.match(line):
                    out.append(f"{path.relative_to(HARLAND)}:{n}: {line.strip()}")
    return out


@pytest.mark.parametrize("tree", TREES)
def test_no_private_strview(tree):
    assert hits(STRUCT, [tree]) == []


def test_loader_has_no_prints_wrapper():
    assert hits(PRINTS, ["boot/src", "boot_abi/src"]) == []


@pytest.mark.parametrize("tree", ["boot/src", "inventory/src"])
def test_uefi_binary_imports_ritzlib_strview(tree):
    assert hits(IMPORT, [tree]) != []
