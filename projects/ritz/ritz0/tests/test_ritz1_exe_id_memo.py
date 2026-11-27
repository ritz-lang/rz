#!/usr/bin/env python3
"""ritz1 hashes its own binary once per build of ritz1, not per run (AGAST #4851).

Background
----------
Every ritz1 run stamps or checks its sig cache with ``cache_fingerprint()``,
which starts from ``compiler_fingerprint()``: a content hash of
``/proc/self/exe`` (AGAST #1279).  Hashing all of the binary on every
invocation cost ~42M Ir per compile (#4850), more than compiling a small file,
and ``rz build`` runs ritz1 once per module.

The fix memoizes the content hash in the cache directory, keyed by the
binary's stat identity::

    <cache root>/<compiler>/exe-id/<st_dev hex16>-<st_ino hex16>
    "ritz1-exe-id-v1 <size> <mtime s> <mtime ns> <ctime s> <ctime ns> <hash hex16>\\n"

A relink makes a new inode, so the memo misses and the binary is hashed again:
a byte-identical relink still keeps the sig cache warm (same content hash),
and a changed binary never inherits the old one's hash.  An in-place rewrite
keeps the inode but moves ctime, which userspace cannot set back, so it misses
too.  The memo is written only when the binary's ctime is over a second old,
so a rewrite in the same clock tick as the hash cannot alias it.

These tests pin: the memo is written and then used; a corrupt memo is a miss
(rehash), never a match; an in-place change misses; an unreadable binary
yields "unknown" (no reuse) even with a memo present.
"""

import errno
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Every test runs a compiler process (AGAST #1805).
pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1 = RITZ_ROOT / "ritz1" / "build" / "ritz1"

SOURCE = "fn main() -> i32\n    0\n"
TAG = "ritz1-exe-id-v1"
# A hash no real binary is expected to produce, planted to prove a memo hit.
FAKE = "0123456789abcdef"


@pytest.fixture(scope="module", autouse=True)
def _ritz1_built(ritz1_bin):
    """Every test here needs an up-to-date ritz1: conftest's session build (#1804)."""


@pytest.fixture(scope="module")
def aged_ritz1(tmp_path_factory, _ritz1_built) -> Path:
    """A private copy of ritz1 whose ctime is old enough to be memoized.

    Named "ritz1" so its cache namespace is the one these tests read.  The
    copy makes a fresh ctime, so wait (once per module) until it is over a
    second in the past, the memo's write rule.
    """
    path = tmp_path_factory.mktemp("aged") / "ritz1"
    shutil.copy2(RITZ1, path)
    path.chmod(0o755)
    wait = os.stat(path).st_ctime + 2.05 - time.time()
    if wait > 0:
        time.sleep(wait)
    return path


def _copy(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "ritz1"
    shutil.copy2(src, dst)
    dst.chmod(0o755)
    return dst


def _memo_path(cache: Path, binary: Path) -> Path:
    st = os.stat(binary)
    return cache / "ritz1" / "exe-id" / f"{st.st_dev:016x}-{st.st_ino:016x}"


def _memo_prefix(binary: Path) -> str:
    """The record for `binary`'s current stat, up to the hash."""
    st = os.stat(binary)
    return (
        f"{TAG} {st.st_size} {st.st_mtime_ns // 10**9} {st.st_mtime_ns % 10**9} "
        f"{st.st_ctime_ns // 10**9} {st.st_ctime_ns % 10**9} "
    )


def _memo_line(binary: Path, hash16: str) -> str:
    return f"{_memo_prefix(binary)}{hash16}\n"


def _plant(cache: Path, binary: Path, text: str) -> Path:
    memo = _memo_path(cache, binary)
    memo.parent.mkdir(parents=True, exist_ok=True)
    memo.write_text(text)
    return memo


def _open_for_rewrite(binary: Path, timeout: float = 10.0):
    """Open `binary` "r+b", waiting out ETXTBSY from a just-reaped exec (#4901).

    `subprocess.run` has reaped the ritz1 child, but the kernel lifts the
    exec's deny-write only when the child's last `mm` reference drops: a
    `/proc/<pid>` reader (a CI resource sampler) can hold it past `wait()`,
    so the open briefly fails "Text file busy".  Retry on that errno only,
    bounded; anything else, or a holder that never lets go, still fails.
    """
    deadline = time.monotonic() + timeout
    while True:
        try:
            return binary.open("r+b")
        except OSError as e:
            if e.errno != errno.ETXTBSY or time.monotonic() >= deadline:
                raise
            time.sleep(0.01)


def _compile(binary: Path, work: Path, cache: Path, name: str = "unit") -> subprocess.CompletedProcess:
    src = work / f"{name}.ritz"
    src.write_text(SOURCE)
    env = dict(os.environ, RITZ_CACHE_DIR=str(cache))
    return subprocess.run(
        [str(binary), str(src), "-o", str(work / f"{name}.ll")],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(work),
        env=env,
    )


def _compiler_hash(binary: Path, work: Path, cache: Path, name: str = "unit") -> str:
    """The `compiler_hash` a cold compile of a fixed source stamps its sig with.

    The source and its directory are the same for every call with one `work`,
    so this differs between two calls only when the binary's fingerprint
    (memoized or computed) does.
    """
    import json

    from emitter.fn_cache import sig_path_for

    old = os.environ.get("RITZ_CACHE_DIR")
    os.environ["RITZ_CACHE_DIR"] = str(cache)
    try:
        sig = sig_path_for(work / f"{name}.ritz", "ritz1")
    finally:
        if old is None:
            del os.environ["RITZ_CACHE_DIR"]
        else:
            os.environ["RITZ_CACHE_DIR"] = old
    if sig.exists():
        sig.unlink()
    r = _compile(binary, work, cache, name)
    assert r.returncode == 0, r.stderr
    return json.loads(sig.read_text())["compiler_hash"]


class TestMemoIsWrittenAndUsed:
    def test_first_run_writes_the_memo(self, aged_ritz1, tmp_path):
        cache = tmp_path / "cache"
        r = _compile(aged_ritz1, tmp_path, cache)
        assert r.returncode == 0, r.stderr
        memo = _memo_path(cache, aged_ritz1)
        assert memo.exists(), "no exe-id memo written for an aged binary"
        text = memo.read_text()
        assert text.startswith(_memo_prefix(aged_ritz1)), text
        h = text.rstrip("\n").rsplit(" ", 1)[1]
        assert len(h) == 16 and h != "0" * 16 and int(h, 16) != 0

    def test_memo_hit_gives_the_same_fingerprint_as_hashing(self, aged_ritz1, tmp_path):
        """Round trip: the memoized hash reproduces the computed one."""
        cache = tmp_path / "cache"
        computed = _compiler_hash(aged_ritz1, tmp_path, cache)
        assert _memo_path(cache, aged_ritz1).exists()
        assert _compiler_hash(aged_ritz1, tmp_path, cache) == computed

    def test_a_matching_memo_is_used(self, aged_ritz1, tmp_path):
        """A planted memo with a fake hash changes the fingerprint: it is read."""
        cache = tmp_path / "cache"
        real = _compiler_hash(aged_ritz1, tmp_path, cache)
        _plant(cache, aged_ritz1, _memo_line(aged_ritz1, FAKE))
        assert _compiler_hash(aged_ritz1, tmp_path, cache) != real

    def test_fresh_binary_is_not_memoized(self, tmp_path):
        """ctime within the last second: hashed, but the memo is not written."""
        fresh = _copy(RITZ1, tmp_path / "fresh")
        cache = tmp_path / "cache"
        r = _compile(fresh, tmp_path, cache)
        assert r.returncode == 0, r.stderr
        assert not _memo_path(cache, fresh).exists()


class TestCorruptMemoIsAMiss:
    """Anything but an exact, well-formed match is rehashed and rewritten."""

    @pytest.mark.parametrize(
        "variant",
        [
            "empty",
            "torn",          # the hash cut short (a torn write)
            "non_hex",       # hash of the right length, not hex
            "zero",          # 0 is "unknown", never a real value
            "wrong_tag",
            "wrong_size",
            "wrong_ctime",
            "trailing",      # extra bytes after the newline
            "no_newline",    # right length, last byte not the newline
        ],
    )
    def test_corrupt_memo(self, aged_ritz1, tmp_path, variant):
        cache = tmp_path / "cache"
        real = _compiler_hash(aged_ritz1, tmp_path, cache)
        good = _memo_line(aged_ritz1, FAKE)
        st = os.stat(aged_ritz1)
        text = {
            "empty": "",
            "torn": good[:-6],
            "non_hex": good.replace(FAKE, "0123456789abcdeg"),
            "zero": good.replace(FAKE, "0" * 16),
            "wrong_tag": good.replace(TAG, "ritz1-exe-id-v0"),
            "wrong_size": good.replace(f" {st.st_size} ", f" {st.st_size + 1} ", 1),
            "wrong_ctime": good.replace(
                f" {st.st_ctime_ns // 10**9} ", f" {st.st_ctime_ns // 10**9 - 1} ", 1
            ),
            "trailing": good + "x",
            "no_newline": good[:-1] + "x",
        }[variant]
        memo = _plant(cache, aged_ritz1, text)
        assert _compiler_hash(aged_ritz1, tmp_path, cache) == real, (
            f"a {variant} memo was taken as a match"
        )
        # ...and the miss rewrote it with the real record.
        assert memo.read_text().startswith(_memo_prefix(aged_ritz1))
        assert FAKE not in memo.read_text()


class TestChangedBinaryMisses:
    def test_in_place_rewrite_with_mtime_restored_misses(self, aged_ritz1, tmp_path):
        """Same inode, same size, mtime put back: only ctime tells. It must.

        A memo planted for the binary before the rewrite must not apply
        after it; the fingerprint is the rewritten content's.
        """
        binary = _copy(aged_ritz1, tmp_path / "bin")
        cache = tmp_path / "cache"
        work = tmp_path / "w"
        work.mkdir()
        # Make the copy differ from aged_ritz1 by padding past the ELF image.
        with binary.open("ab") as fh:
            fh.write(b"\0" * 64)
        padded = _compiler_hash(binary, work, cache)
        _plant(cache, binary, _memo_line(binary, FAKE))
        assert _compiler_hash(binary, work, cache) != padded   # memo in use
        before = os.stat(binary)
        # Rewrite the trailing padding in place, then restore mtime.
        with _open_for_rewrite(binary) as fh:
            fh.seek(-64, os.SEEK_END)
            fh.write(b"\1" * 64)
        os.utime(binary, ns=(before.st_atime_ns, before.st_mtime_ns))
        after = os.stat(binary)
        assert (after.st_ino, after.st_size, after.st_mtime_ns) == (
            before.st_ino, before.st_size, before.st_mtime_ns)
        rewritten = _compiler_hash(binary, work, cache)   # stale memo present
        _memo_path(cache, binary).unlink(missing_ok=True)
        truth = _compiler_hash(binary, work, cache)       # no memo: hashed
        assert rewritten == truth, "the pre-rewrite memo stood in for the new bytes"
        assert truth != padded

    def test_unreadable_binary_is_unknown_even_with_a_memo(self, aged_ritz1, tmp_path):
        """Execute-only: /proc/self/exe can't be opened, so no fingerprint.

        A memo for its exact stat identity is present and must not stand in:
        an unreadable binary fails closed (#1279), so nothing is reused.
        """
        if os.geteuid() == 0:
            pytest.skip("root reads an execute-only file")
        binary = _copy(aged_ritz1, tmp_path / "xo")
        binary.chmod(0o111)
        cache = tmp_path / "cache"
        _plant(cache, binary, _memo_line(binary, FAKE))
        first = _compile(binary, tmp_path, cache)
        assert first.returncode == 0, first.stderr
        second = _compile(binary, tmp_path, cache)
        assert second.returncode == 0, second.stderr
        assert "Skipped (unchanged)" not in second.stdout, (
            "an unreadable compiler reused cached IR"
        )
