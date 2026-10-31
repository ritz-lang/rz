"""AGAST #1942: one read-all-fd loop in ritzlib; GrowBuf docs match GrowBuf.

Structural checks, like test_ritzlib_byte_view.py: two copies of the same
sys_read loop behave identically, so no behavioural test can tell that one of
them exists. The behaviour itself is pinned by the examples that read stdin
through the surviving owner (12_tac, 13_sort, 14_uniq, 78_buf).

* vec_read_all_fd (gvec.ritz) is the only read-all-fd function in ritzlib.
  buf.ritz's GrowBuf copy is gone and no tracked .ritz file still calls it.
* buf.ritz no longer calls GrowBuf a "type alias for Vec<u8>" or says it is
  "backed by Vec<u8>": it is its own struct, with an `impl Drop` Vec<u8>
  does not have, and the two do not convert implicitly.
"""

import re
import subprocess
from pathlib import Path

import pytest

RITZ_DIR = Path(__file__).resolve().parent.parent
RITZLIB = RITZ_DIR / "ritzlib"
REPO_ROOT = RITZ_DIR.parent.parent
BUF = RITZLIB / "buf.ritz"
STDLIB_REF = RITZ_DIR / "docs" / "STDLIB_REFERENCE.md"


def _tracked_ritz():
    out = subprocess.run(
        ["git", "ls-files", "*.ritz"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [REPO_ROOT / rel for rel in out]


@pytest.mark.unit
def test_exactly_one_read_all_fd_in_ritzlib():
    decl = re.compile(r"^\s*(?:pub\s+)?fn\s+(\w*read_all_fd)\b", re.M)
    owners = sorted(
        f"{p.name}:{name}"
        for p in RITZLIB.glob("*.ritz")
        for name in decl.findall(p.read_text())
    )
    assert owners == ["gvec.ritz:vec_read_all_fd"], owners


@pytest.mark.unit
def test_no_caller_of_deleted_growbuf_read_all_fd():
    # `read_all_fd(` not preceded by an identifier char (so not
    # vec_read_all_fd) and not by `fn ` (a definition is the other test's job).
    call = re.compile(r"(?<![\w.])(?<!fn )read_all_fd\s*\(")
    hits = [
        f"{p.relative_to(REPO_ROOT)}:{i}"
        for p in _tracked_ritz()
        for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1)
        if call.search(line.split("#", 1)[0])
    ]
    assert hits == [], hits


@pytest.mark.unit
def test_stdlib_reference_lists_no_growbuf_read_all_fd():
    assert "`read_all_fd`" not in STDLIB_REF.read_text()


@pytest.mark.unit
def test_growbuf_is_its_own_struct():
    src = BUF.read_text()
    assert re.search(r"^struct GrowBuf\b", src, re.M)
    assert re.search(r"^impl Drop for GrowBuf\b", src, re.M)


@pytest.mark.unit
@pytest.mark.parametrize(
    "claim",
    [r"alias\s+for\s+Vec<u8>", r"backed\s+by\s+Vec<u8>"],
)
def test_buf_docs_do_not_claim_growbuf_is_vec(claim):
    hits = [
        f"buf.ritz:{i}: {line.strip()}"
        for i, line in enumerate(BUF.read_text().splitlines(), 1)
        if re.search(claim, line, re.I)
    ]
    assert hits == [], hits
