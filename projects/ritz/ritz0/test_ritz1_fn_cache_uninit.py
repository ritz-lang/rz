"""Regression tests for AGAST #1663: ritz1's cache fingerprint must be defined.

`fn_cache.ritz:read_file_to_buf()` sized its buffer with `stat(path)` and then
read until it had `st_size` bytes.  When `read()` returned 0 (EOF) or an error
before that, it set `total = sz` and reported the *whole* buffer as read, so
the unread tail was uninitialised heap.  `compiler_fingerprint()` reads
`/proc/self/exe` through it, so the compiler hash stamped into every
sig file (and compared on every cache lookup) could hash garbage:

* valgrind: `stat("/proc/self/exe")` reports memcheck's size while `open` is
  redirected to the client binary, which is how the bug was found
  ("Conditional jump ... uninitialised" in `cache_fingerprint`, "write(buf)
  points to uninitialised byte(s)" in `write_sig_file`);
* natively: any file that shrinks between `stat` and `read` (a relink while
  ritz1 is running) hits the same path.

The fix stops at EOF and reports the byte count actually read, and fails the
read on error.

Separately, `monomorph.ritz` cloned FnDef/MatchArm/FieldInit/StructDef/
StructField nodes into literal-sized blocks; they now use `sizeof()` like the
Stmt/Expr clones fixed in #1649.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emitter.fn_cache import sig_path_for  # noqa: E402

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_SRC = RITZ_ROOT / "ritz1" / "src"
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

# A small program with a generic, so the monomorph clones run too.
SOURCE = """\
fn id<T>(x: T) -> T
    return x

pub fn main() -> i32
    return id<i32>(0)
"""

# Exit code valgrind reports for memcheck errors; distinct from ritz1's own.
VG_ERR = 97

# AST node types that monomorph clones; each must be sized with sizeof().
CLONED_TYPES = ("FnDef", "Param", "MatchArm", "FieldInit", "StructDef", "StructField")
LITERAL_ALLOC = re.compile(
    r"\bmalloc\(\s*\d+\s*\)\s+as\s+\*(" + "|".join(CLONED_TYPES) + r")\b"
)


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    """Build (or freshen) ritz1; a stale binary would test old code."""
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the fn_cache uninit tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )
    return RITZ1_BIN


@pytest.fixture
def valgrind() -> str:
    path = shutil.which("valgrind")
    if path is None:
        pytest.skip("valgrind not installed")
    return path


def _compile(cmd_prefix: list, ritz1: Path, tmp: Path) -> tuple:
    """Cold-compile SOURCE in `tmp`; return (process, parsed sig)."""
    src = tmp / "g.ritz"
    src.write_text(SOURCE)
    sig = sig_path_for(src, "ritz1")
    if sig.exists():
        sig.unlink()
    proc = subprocess.run(
        cmd_prefix + [str(ritz1), str(src), "-o", str(tmp / "g.ll")],
        capture_output=True,
        text=True,
        cwd=str(tmp),
        timeout=600,
    )
    data = json.loads(sig.read_text()) if sig.exists() else None
    return proc, data


@pytest.mark.integration
def test_ritz1_compile_is_valgrind_clean(ritz1_bin, valgrind, tmp_path):
    """No memcheck errors compiling a generic program (fingerprint + sig write)."""
    proc, _ = _compile(
        [valgrind, "-q", f"--error-exitcode={VG_ERR}"], ritz1_bin, tmp_path
    )
    assert "uninitialised" not in proc.stderr, proc.stderr[-4000:]
    assert proc.returncode != VG_ERR, proc.stderr[-4000:]
    assert proc.returncode == 0, proc.stderr[-4000:]


@pytest.mark.integration
def test_compiler_hash_independent_of_stat_size(ritz1_bin, valgrind, tmp_path):
    """The same binary must stamp the same compiler_hash, whatever stat() says.

    Under valgrind `stat("/proc/self/exe")` reports memcheck's size, not
    ritz1's.  The fingerprint must describe the bytes actually read.
    """
    native_dir = tmp_path / "native"
    vg_dir = tmp_path / "vg"
    native_dir.mkdir()
    vg_dir.mkdir()
    p1, native = _compile([], ritz1_bin, native_dir)
    p2, under_vg = _compile([valgrind, "-q"], ritz1_bin, vg_dir)
    assert native is not None, p1.stderr[-2000:]
    assert under_vg is not None, p2.stderr[-2000:]
    assert native["compiler_hash"] == under_vg["compiler_hash"]


@pytest.mark.unit
def test_monomorph_clones_sized_with_sizeof():
    """monomorph must allocate cloned AST nodes with sizeof(), not literals."""
    path = RITZ1_SRC / "monomorph.ritz"
    offenders = [
        f"{path.name}:{n}: {line.strip()}"
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if LITERAL_ALLOC.search(line)
    ]
    assert not offenders, "literal-sized AST clone (use sizeof):\n" + "\n".join(
        offenders
    )
