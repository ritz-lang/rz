"""AGAST #4531: the syscall/kernel ABI layer is converted or deliberately exempt."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize("name", ["sys.ritz", "net.ritz", "uring.ritz"])
def test_abi_module_has_no_unexempted_raw_pointer_parameters(name):
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / name]))
    assert summary["raw-ptr-param"]["violations"] == 0, name
    assert summary["exempt-malformed"]["violations"] == 0, name
