"""AGAST #4539, #4644: elf.ritz has no raw *T parameter and no exemption.

#4539 left 7 exemptions (ELF image / .strtab / callback ABI).  #4644 deleted
the private read_u16/u32/u64 copies (ritzlib.endian's span readers replace
them), `starts_with` (StrView's does it) and find_test_functions' unused
callback pointers.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_elf_module_has_no_raw_pointer_parameters():
    """AGAST #4644: no raw *T parameter is left, so nothing is exempt."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "elf.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
