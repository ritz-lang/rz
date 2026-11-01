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
@pytest.mark.parametrize("fn", ["string_eq", "string_eq_string", "string_eq_strview"])
def test_string_eq_family_returns_bool(fn):
    src = (RITZLIB / "string.ritz").read_text()
    m = re.search(rf"^pub fn {fn}\([^)]*\)\s*->\s*(\w+)", src, re.M)
    assert m, f"{fn} not found in string.ritz"
    assert m.group(1) == "bool", f"{fn} returns {m.group(1)}"


# AGAST #1943: the rest of the predicate family follows string_eq to bool.
PREDICATES = {
    "string.ritz": [
        "string_eq_cstr",
        "string_is_empty",
        "string_starts_with",
        "string_starts_with_string",
        "string_ends_with",
        "string_ends_with_string",
        "string_contains",
        "string_contains_string",
    ],
    "strview.ritz": [
        "strview_is_empty",
        "strview_eq",
        "strview_eq_cstr",
        "strview_starts_with",
        "strview_starts_with_cstr",
        "strview_ends_with",
        "strview_contains",
    ],
    "span.ritz": [
        "span_is_empty",
        "span_eq",
        "span_eq_cstr",
        "span_contains",
        "span_starts_with",
        "span_ends_with",
    ],
}

# impl-block methods that wrap the predicates above.
PREDICATE_METHODS = {
    "strview.ritz": ["is_empty", "starts_with", "ends_with", "contains", "eq", "eq_cstr"],
    "span.ritz": ["is_empty"],
}


@pytest.mark.unit
@pytest.mark.parametrize(
    "fname,fn", [(f, fn) for f, fns in PREDICATES.items() for fn in fns]
)
def test_predicate_family_returns_bool(fname, fn):
    src = (RITZLIB / fname).read_text()
    m = re.search(rf"^pub fn {fn}(<\w+>)?\([^)]*\)\s*->\s*(\w+)", src, re.M)
    assert m, f"{fn} not found in {fname}"
    assert m.group(2) == "bool", f"{fn} returns {m.group(2)}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "fname,method", [(f, m) for f, ms in PREDICATE_METHODS.items() for m in ms]
)
def test_predicate_methods_return_bool(fname, method):
    src = (RITZLIB / fname).read_text()
    m = re.search(rf"^\s+fn {method}\([^)]*\)\s*->\s*(\w+)", src, re.M)
    assert m, f"method {method} not found in {fname}"
    assert m.group(1) == "bool", f"{fname} {method} returns {m.group(1)}"


@pytest.mark.unit
def test_predicate_bodies_return_no_int_literals():
    """A bool predicate saying `return 1` compiles (silent coercion) but is the
    i32 shape in disguise; pin the bodies too."""
    bad = []
    for fname, fns in PREDICATES.items():
        src = (RITZLIB / fname).read_text()
        for fn in fns:
            m = re.search(rf"^pub fn {fn}\b.*?\n(?=\S)", src + "\n#", re.M | re.S)
            assert m, fn
            for line in m.group(0).splitlines():
                if re.match(r"\s*return\s+[01]\b", line):
                    bad.append(f"{fname}:{fn}: {line.strip()}")
    assert bad == [], bad


@pytest.mark.unit
def test_no_int_comparisons_against_predicates():
    """Callers must not compare a (now bool) predicate against 1 / 0."""
    names = "|".join(fn for fns in PREDICATES.values() for fn in fns)
    pat = re.compile(rf"\b({names})(<\w+>)?\([^()]*(\([^()]*\)[^()]*)*\)\s*[!=]=\s*[01]\b")
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


@pytest.mark.unit
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


@pytest.mark.unit
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
