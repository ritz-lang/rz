"""LARB review/5 ritzlib F2-F4 stay fixed (AGAST #3452).

- F2: ritzlib has one integer formatter, fmt.ritz. hashmap's missing-key
  message hand-rolled an eighth `% 10` digit loop after #1856 consolidated
  the other seven. No ritzlib file but fmt.ritz (tests aside) may contain
  `% 10`. The ticket's `git grep '% 10'` also matched `% 1000` in timer.ritz
  (one fractional digit) and net.ritz (ms to us), which format nothing, so
  the check wants `% 10` with no digit after it.
- F3: ptr.ritz claimed "container code" reads elements with ptr_read, but no
  ritzlib container imports it; and it copied byte by byte instead of memcpy.
- F4: the constant-time compare took two (*u8, len) pairs; it is now
  `ct_eq(a: StrView, b: StrView) -> bool`, and `ct_bytes_eq` is gone.

Read in-process rather than via `git grep`: a unit test starts no processes
(AGAST #1805).
"""

from __future__ import annotations

import re
from pathlib import Path

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZLIB = RITZ_ROOT / "ritzlib"
PROJECTS = RITZ_ROOT.parent

SKIP_PARTS = {"build", ".git", "node_modules", "__pycache__", "archive"}


def _files(root: Path, pattern: str):
    for path in sorted(root.rglob(pattern)):
        rel = path.relative_to(root)
        if SKIP_PARTS.intersection(rel.parts) or not path.is_file():
            continue
        yield path


def test_no_digit_loop_outside_fmt():
    """`git grep -nE '% 10([^0-9]|$)' ritzlib -- ':!*fmt/digits.ritz' ':!*test*'` is empty."""
    digit_loop = re.compile(r"% 10(?![0-9])")
    offenders = []
    for path in _files(RITZLIB, "*"):
        rel = str(path.relative_to(RITZLIB))
        if rel == "fmt/digits.ritz" or "test" in rel:
            continue
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if digit_loop.search(line):
                offenders.append(f"{rel}:{n}: {line.strip()}")
    assert offenders == [], "format integers through ritzlib.fmt.digits:\n" + "\n".join(offenders)


def test_ptr_header_makes_no_container_claim_unless_true():
    text = (RITZLIB / "ptr.ritz").read_text()
    importers = [p for p in _files(RITZLIB, "*.ritz")
                 if re.search(r"^\s*import\s+ritzlib\.ptr\b", p.read_text(), re.M)]
    if not importers:
        assert "Container code" not in text and "container code" not in text


def test_ptr_read_copies_with_memcpy():
    text = (RITZLIB / "ptr.ritz").read_text()
    assert "memcpy" in text
    # No per-byte loop: no `while`/`for` at all in a one-function module.
    assert not re.search(r"^\s*(while|for)\b", text, re.M)


def test_ct_bytes_eq_is_gone():
    """`git grep -n ct_bytes_eq` over live code and docs is empty.

    projects/larb holds review records, which quote the old name as
    history; they are not scanned."""
    offenders = []
    for root in (RITZ_ROOT, PROJECTS / "tome"):
        for path in _files(root, "*"):
            if path.suffix not in {".ritz", ".md", ".py"} or path == Path(__file__):
                continue
            if "ct_bytes_eq" in path.read_text(errors="replace"):
                offenders.append(str(path.relative_to(PROJECTS)))
    assert offenders == []


def test_ct_eq_takes_strviews():
    text = (RITZLIB / "ct.ritz").read_text()
    assert re.search(r"^pub fn ct_eq\(a: StrView, b: StrView\) -> bool$", text, re.M)
