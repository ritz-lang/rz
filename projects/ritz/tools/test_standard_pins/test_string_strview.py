"""Pin String/StrView APIs to their impls (AGAST #4533)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent


def test_string_and_strview_modules_have_no_free_fn_methods():
    """AGAST #4533: String/StrView APIs live on their impls, not free fns."""
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "string.ritz",
                                   RITZ_ROOT / "ritzlib" / "strview.ritz"]))
    assert summary["free-fn-method"] == {"violations": 0, "exempt": 0}


C_STRING_WORDS = ("C string ABI", "C-string ABI", "NUL-terminated")


def test_string_strview_gvec_io_str_name_no_c_string_exemption():
    """AGAST #4688: every NUL-terminated *u8 API lives in ritzlib.cstr.

    No exemption reason in str/io/string/strview/gvec says "C string ABI" or
    "NUL-terminated", and the raw-pointer shapes that remain are the counts
    below (ritzlib raw-ptr-param 140 -> 124, null-return 11 -> 9, sentinel-return
    5 -> 4).
    """
    for name in ("str", "io", "string", "strview", "gvec"):
        for line in (RITZ_ROOT / "ritzlib" / f"{name}.ritz").read_text().splitlines():
            if "standard-exempt" in line:
                assert not any(w in line for w in C_STRING_WORDS), f"{name}.ritz: {line}"
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / f"{n}.ritz"
                                   for n in ("string", "strview", "gvec")]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 6}
    assert summary["null-return"] == {"violations": 0, "exempt": 1}
    assert summary["sentinel-return"] == {"violations": 0, "exempt": 0}
    tree = summarise(scan_tree([RITZ_ROOT / "ritzlib"]))
    assert tree["raw-ptr-param"] == {"violations": 0, "exempt": 124}
    assert tree["null-return"] == {"violations": 0, "exempt": 9}
    assert tree["sentinel-return"] == {"violations": 0, "exempt": 3}
