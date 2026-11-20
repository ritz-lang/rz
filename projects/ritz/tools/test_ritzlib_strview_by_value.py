"""ritzlib takes a read-only StrView by value, not through a pointer (#2414).

Aaron's ruling (2026-11-06, goal 5: ritzlib APIs take slices and structs,
not pointers): a ritzlib function that only reads a StrView declares it
`StrView`, and its callers pass `x`, not `@x`. A StrView is `{ptr, len}`:
ritz0, ritz1 and ritz1_selfhosted all pass it as a first-class LLVM
aggregate, which x86-64 lowers to two registers, so by value costs no copy
through memory.

`@StrView` is an immutable borrow, so every one is read-only and none may
stay. `*StrView` and `:& StrView` are allowed only where listed below with
the reason; a new one has to be added here, reason and all.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RITZLIB = Path(__file__).resolve().parent.parent / "ritzlib"

# (file relative to ritzlib, function, param) -> why it is not by value
ALLOWED = {
    ("strview.ritz", "strview_split_once", "before"): "output param: written",
    ("strview.ritz", "strview_split_once", "after"): "output param: written",
    ("os/env.ritz", "env_get_p", "name"): (
        "the pointer form of env_get by design; by value it would be env_get"
    ),
    # A trait impl's signature is the trait's: Hash and Eq take `@Self`, so
    # a generic HashMap can call them on any K (#1858).
    ("hash.ritz", "hash", "self"): "impl Hash for StrView: the trait's @Self",
    ("hash.ritz", "equals", "self"): "impl Eq for StrView: the trait's @Self",
    ("hash.ritz", "equals", "other"): "impl Eq for StrView: the trait's @Self",
    # Display/Debug declare `self: @Self` (LARB #4016), so the StrView impls
    # must spell it `@StrView`; the value is still only read (#4294).
    ("fmt/display.ritz", "show", "self"): "impl Display for StrView: the trait's @Self",
    ("fmt/display.ritz", "show_debug", "self"): "impl Debug for StrView: the trait's @Self",
}

FN_RE = re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\(([^)]*)\)")
PARAM_RE = re.compile(r"(\w+)\s*:\s*(@&|@|\*|&)?\s*StrView\b")


def strview_pointer_params(root: Path):
    """Yield (relpath, fn, param, sigil, lineno) for each pointer-to-StrView param."""
    for path in sorted(root.rglob("*.ritz")):
        if "tests" in path.relative_to(root).parts:
            continue
        rel = path.relative_to(root).as_posix()
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            m = FN_RE.match(line)
            if not m:
                continue
            # `name:& T` is spelled with the sigil glued to the colon.
            params = m.group(2).replace(":&", ": &")
            for pm in PARAM_RE.finditer(params):
                if pm.group(2):
                    yield rel, m.group(1), pm.group(1), pm.group(2), lineno


@pytest.mark.unit
def test_ritzlib_has_no_pointer_strview_param_outside_allowlist():
    found = list(strview_pointer_params(RITZLIB))
    bad = [
        f"ritzlib/{rel}:{ln}: {fn}({p}: {sig}StrView)"
        for rel, fn, p, sig, ln in found
        if (rel, fn, p) not in ALLOWED
    ]
    assert not bad, "read-only StrView params must be by value (#2414):\n" + "\n".join(bad)


@pytest.mark.unit
def test_allowlist_has_no_stale_entries():
    present = {(rel, fn, p) for rel, fn, p, _, _ in strview_pointer_params(RITZLIB)}
    stale = sorted(set(ALLOWED) - present)
    assert not stale, f"allowlisted params no longer exist; drop them: {stale}"


# tome and spire took the same rewrite (#3155): their lib/ and test/ trees.
PROJECTS = RITZLIB.parent.parent
PACKAGES = ("tome", "spire")

# (package-relative file, function, param) -> why it is not by value
PACKAGE_ALLOWED = {
    ("spire", "test/support/test_utils.ritz", "response_find_header", "out"): (
        "output param: the header value is written through it"
    ),
    ("tome", "lib/commands.ritz", "ctx_write_bulk_array", "items"): (
        "an array of `count` views (LRANGE/SMEMBERS/HKEYS... replies, #4210), not one view"
    ),
}


def package_pointer_params():
    """Yield (pkg, relpath, fn, param, sigil, lineno) over tome's and spire's sources."""
    for pkg in PACKAGES:
        root = PROJECTS / pkg
        for sub in ("lib", "test"):
            for rel, fn, p, sig, ln in strview_pointer_params(root / sub):
                yield pkg, f"{sub}/{rel}", fn, p, sig, ln


@pytest.mark.unit
def test_packages_have_no_pointer_strview_param_outside_allowlist():
    # A moved package would otherwise scan nothing and pass.
    for pkg in PACKAGES:
        assert (PROJECTS / pkg / "lib").is_dir(), f"projects/{pkg}/lib is gone"
    found = list(package_pointer_params())
    bad = [
        f"projects/{pkg}/{rel}:{ln}: {fn}({p}: {sig}StrView)"
        for pkg, rel, fn, p, sig, ln in found
        if (pkg, rel, fn, p) not in PACKAGE_ALLOWED
    ]
    assert not bad, "read-only StrView params must be by value (#3155):\n" + "\n".join(bad)


@pytest.mark.unit
def test_package_allowlist_has_no_stale_entries():
    present = {(pkg, rel, fn, p) for pkg, rel, fn, p, _, _ in package_pointer_params()}
    stale = sorted(set(PACKAGE_ALLOWED) - present)
    assert not stale, f"allowlisted params no longer exist; drop them: {stale}"


@pytest.mark.unit
def test_scanner_sees_each_pointer_spelling(tmp_path):
    (tmp_path / "m.ritz").write_text(
        "pub fn a(s: @StrView) -> i64\n"
        "fn b(x: i64, s: *StrView)\n"
        "fn c(out:& StrView)\n"
        "    fn d(self: @StrView) -> i64\n"
        "fn e(s: StrView, t: @String)\n"
    )
    got = {(fn, sig) for _, fn, _, sig, _ in strview_pointer_params(tmp_path)}
    assert got == {("a", "@"), ("b", "*"), ("c", "&"), ("d", "@")}
