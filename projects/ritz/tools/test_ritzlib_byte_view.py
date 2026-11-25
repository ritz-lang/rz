"""AGAST #1930: ritzlib has exactly one byte-view type.

These are structural checks, because the properties are invisible to a
behavioural test: every compiler silently coerces an i32 return to bool, and
two same-layout `struct StrView` declarations link without complaint. So the
matrix test (ritz0/test/test_byte_view_dedup.ritz) pins the semantics, and
this file pins the shape:

* one `struct StrView` in ritzlib (string.ritz used to declare its own);
* string_eq / string_eq_string / string_eq_strview all return bool;
* the string_push_strview alias (== string_push_str) is gone, callers too;
* Span<u8>'s byte operations delegate to strview, so ritz-metrics finds no
  duplicate window shared between span.ritz and strview.ritz.
"""

import json
import re
import subprocess
from pathlib import Path

import pytest

RITZ_DIR = Path(__file__).resolve().parent.parent
RITZLIB = RITZ_DIR / "ritzlib"
REPO_ROOT = RITZ_DIR.parent.parent
METRICS = REPO_ROOT / "projects" / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"


def _ritzlib_sources():
    return sorted(RITZLIB.glob("*.ritz"))


@pytest.mark.unit
def test_exactly_one_struct_strview_in_ritzlib():
    decl = re.compile(r"^\s*(pub\s+)?struct\s+StrView\b", re.M)
    owners = [p.name for p in _ritzlib_sources() if decl.search(p.read_text())]
    assert owners == ["strview.ritz"], owners


@pytest.mark.unit
@pytest.mark.parametrize("method", ["eq", "eq_string", "eq_strview"])
def test_string_eq_family_returns_bool(method):
    src = (RITZLIB / "string.ritz").read_text()
    m = re.search(rf"^\s+pub fn {method}\([^)]*\)\s*->\s*(\w+)", src, re.M)
    assert m, f"String.{method} not found in string.ritz"
    assert m.group(1) == "bool", f"String.{method} returns {m.group(1)}"


# AGAST #1943: the rest of the predicate family follows string_eq to bool.
# Since #4533 the String/StrView predicates are impl methods; since #4684
# Span<u8>'s are methods of span.ritz's Bytes trait (`impl Bytes for Span<u8>`).
PREDICATE_METHODS = {
    "string.ritz": [
        "eq", "eq_string", "eq_strview", "is_empty",
        "starts_with", "starts_with_string", "ends_with",
        "ends_with_string", "contains", "contains_string",
    ],
    "strview.ritz": [
        "is_empty", "eq", "starts_with",
        "ends_with", "contains",
    ],
    "span.ritz": ["is_empty", "eq", "contains", "starts_with", "ends_with"],
}


@pytest.mark.unit
@pytest.mark.parametrize(
    "fname,method", [(f, m) for f, ms in PREDICATE_METHODS.items() for m in ms]
)
def test_predicate_methods_return_bool(fname, method):
    src = (RITZLIB / fname).read_text()
    m = re.search(rf"^\s+(?:pub )?fn {method}\([^)]*\)\s*->\s*(\w+)", src, re.M)
    assert m, f"method {method} not found in {fname}"
    assert m.group(1) == "bool", f"{fname} {method} returns {m.group(1)}"


def _method_body(src, method):
    """The indented body of the first `fn method` in `src`, or None."""
    lines = src.splitlines()
    for i, line in enumerate(lines):
        m = re.match(rf"^(\s+)(?:pub )?fn {method}\(", line)
        if not m:
            continue
        indent = len(m.group(1))
        body = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                break
            body.append(nxt)
        return "\n".join(body)
    return None


@pytest.mark.unit
def test_predicate_bodies_return_no_int_literals():
    """A bool predicate saying `return 1` compiles (silent coercion) but is the
    i32 shape in disguise; pin the bodies too."""
    bad = []
    for fname, methods in PREDICATE_METHODS.items():
        src = (RITZLIB / fname).read_text()
        for meth in methods:
            body = _method_body(src, meth)
            assert body is not None, f"{fname}: method {meth} not found"
            for line in body.splitlines():
                if re.match(r"\s*return\s+[01]\b", line):
                    bad.append(f"{fname}:{meth}: {line.strip()}")
    assert bad == [], bad


@pytest.mark.integration
def test_no_int_comparisons_against_predicates():
    """Callers must not compare a (now bool) predicate against 1 / 0."""
    meth = [m for ms in PREDICATE_METHODS.values() for m in ms]
    meth_pat = "|".join(re.escape(x) for x in meth)
    pat = re.compile(
        rf"\.(?:{meth_pat})\("
        rf"[^()]*(\([^()]*\)[^()]*)*\)\s*[!=]=\s*[01]\b")
    tracked = subprocess.run(
        ["git", "ls-files", "*.ritz"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    hits = [
        f"{rel}:{i}"
        for rel in tracked
        for i, line in enumerate(
            (REPO_ROOT / rel).read_text(errors="replace").splitlines(), 1
        )
        if pat.search(line)
    ]
    assert hits == [], hits


@pytest.mark.integration
def test_string_push_strview_alias_gone_with_callers():
    tracked = subprocess.run(
        ["git", "ls-files", "*.ritz"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    hits = [
        f"{rel}:{i}"
        for rel in tracked
        for i, line in enumerate(
            (REPO_ROOT / rel).read_text(errors="replace").splitlines(), 1
        )
        if re.search(r"\bstring_push_strview\b|\.push_strview\(", line)
    ]
    assert hits == [], hits


@pytest.mark.integration
def test_no_span_strview_duplicate_clusters(tmp_path):
    out = tmp_path / "m.json"
    subprocess.run(
        [
            "python3",
            str(METRICS),
            str(RITZLIB / "span.ritz"),
            str(RITZLIB / "strview.ritz"),
            "--json",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    clusters = json.loads(out.read_text())["duplicates"]
    shared = [
        c
        for c in clusters
        if any("span.ritz" in loc[0] for loc in c["locations"])
        and any("strview.ritz" in loc[0] for loc in c["locations"])
    ]
    assert shared == [], shared
