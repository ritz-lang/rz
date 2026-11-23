"""AGAST #4539: fmt/writer.ritz raw *T parameters are converted or exempt.

1 exemption: `Writer.write`, the signature the write/writeln builtins lower
to. `push_bytes` is a Span<u8> (AGAST #4555), so it is no longer a raw pair.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_fmt_writer_module_has_no_raw_pointer_parameters():
    """AGAST #4539: every raw *T parameter is converted or exempted with a reason."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "fmt" / "writer.ritz"]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 1}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
