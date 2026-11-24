"""Pin gvec.ritz and argspec.ritz against docs/STANDARD.md's S-IMPL-1 rule.

AGAST #4537.  The `vec_*` free functions whose first parameter is a Vec<T>,
and the argspec parser's arg_*/argspec_*/parsed_* accessors whose first
parameter is a same-file struct, now live in `impl` blocks as methods.  The
constructors (vec_new, vec_with_cap, vec_new_in, vec_with_cap_in,
argspec_new) stay free by design.

The two files were the whole remaining tree-wide free-fn-method count
(23 + 15 = 38), so this pin also asserts the rule is clear across the tree.
A method and its old free-fn twin would count twice, so the twin is gone.

Kept in its own file: #4551 is splitting tools/test_standard_report.py, and
this pin belongs to #4537.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent


def test_gvec_has_no_free_fns_taking_its_own_type():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "gvec.ritz"]))
    assert summary["free-fn-method"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}


def test_argspec_has_no_free_fns_taking_its_own_type():
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib" / "argspec.ritz"]))
    assert summary["free-fn-method"] == {"violations": 0, "exempt": 0}
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}


def test_free_fn_method_is_clear_across_ritzlib():
    """The 38 counted ritzlib sites were exactly these two files; none remain.

    ritzlib is the standard report's default scope, and 23 + 15 = 38 was its
    whole free-fn-method count at 60b73372.
    """
    summary = summarise(scan_tree([RITZ_ROOT / "ritzlib"]))
    assert summary["free-fn-method"]["violations"] == 0
    # 14 are deliberate, documented exemptions (span.ritz 11, sys.ritz 2,
    # time.ritz's sleep(d: Duration), AGAST #4637).
    assert summary["free-fn-method"]["exempt"] == 14
    assert summary["exempt-malformed"] == {"violations": 0, "exempt": 0}
