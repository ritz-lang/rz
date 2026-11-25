"""AGAST #4688: ritzlib/cstr.ritz, the one C-interop module, pinned down-only.

Every NUL-terminated *u8 API lives here and nowhere else in ritzlib: strlen,
streq, strneq, strview_from_cstr, string_from_cstr, eprints_cstr,
eprintln_cstr.  All share one exemption reason, "ritzlib.cstr IS the C-string
boundary".  The pin is a ceiling of (violations, violations + exempt) per
counting rule (standard_report.ratchet_breaches); a rule not listed is pinned
at zero.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import ratchet_breaches, scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent
CSTR = RITZ_ROOT / "ritzlib" / "cstr.ritz"

PINS = {}
REASON = "ritzlib.cstr IS the C-string boundary"


def test_cstr_c_shapes_only_go_down():
    assert ratchet_breaches(summarise(scan_tree([CSTR])), PINS) == []


def test_cstr_raw_pointer_counts():
    summary = summarise(scan_tree([CSTR]))
    assert summary["raw-ptr-param"] == {"violations": 0, "exempt": 9}
    assert summary["ptr-len-param"] == {"violations": 0, "exempt": 1}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}


def test_cstr_has_one_exemption_reason():
    exempts = [l for l in CSTR.read_text().splitlines() if "standard-exempt" in l]
    assert exempts and all(l.endswith(REASON) for l in exempts), exempts


def test_no_other_ritzlib_module_defines_a_c_string_api():
    names = ("strlen", "streq", "strneq", "strcmp", "strcpy", "strcat", "strchr",
             "strstr", "atoi", "eprints_cstr", "eprintln_cstr", "string_from_cstr",
             "strview_from_cstr", "push_cstr", "eq_cstr", "from_cstr",
             "starts_with_cstr", "as_cstr_unchecked")
    for f in (RITZ_ROOT / "ritzlib").rglob("*.ritz"):
        if f == CSTR or "tests" in f.parts:
            continue
        for line in f.read_text().splitlines():
            code = line.split("#")[0].strip()
            for n in names:
                assert not code.startswith((f"pub fn {n}(", f"fn {n}(")), f"{f.name}: {code}"
