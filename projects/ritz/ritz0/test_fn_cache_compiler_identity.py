#!/usr/bin/env python3
"""Compiler identity must be part of ritz1's file-level cache key (AGAST #1279).

Background
----------
``ritz1`` keeps a per-source ``<src>.ritz.sig`` next to every input file.  Two
things live in it that let a rebuild skip work entirely:

* ``source_hash`` — used to prove the source text has not changed, and
* ``module_ir``  — a verbatim snapshot of the last emitted ``.ll``.

``check_source_unchanged()`` consults both.  It used to gate reuse on the
source hash and the ``.ll`` mtime *only*, which says nothing about **which
compiler** produced the cached IR.  Rebuilding ritz1 therefore left every
``.ritz.sig`` advertising IR from the compiler that had just been replaced,
and ritz1 served it:

* path (a) — a ``.ll`` newer than the source was reused as-is, and
* path (b) — a ``.ll`` that make had *just deleted* was re-materialised by
  splicing ``module_ir`` back out of the sig.

Path (b) is the damaging one: it defeats the orchestrator's own invalidation.
``ritz1/Makefile`` correctly lists ``$(RITZ1)`` as a prerequisite of every
``build/%_sh.ll``, so make re-invokes ritz1 when the binary changes — and
ritz1 then declined to regenerate, printing ``Skipped (unchanged)`` moments
before clang rejected IR from a compiler that no longer existed.

The observable damage was a bootstrap gate that answered from leftover build
state rather than from the commit under test, in both directions: incremental
runs failed with ``PHI node entries do not match predecessors`` on a tree
whose emitter bug was already fixed, and a separate branch reported a
``ritz1_selfhosted 0/50`` "NUL-byte miscompilation" that did not reproduce
from clean.  Both were artefacts of the stale cache, not compiler defects.

These tests pin the fix: the sig records a ``compiler_hash`` and *both* reuse
paths refuse to fire unless it matches the running binary.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1 = RITZ_ROOT / "ritz1" / "build" / "ritz1"

# This suite is about the behaviour of a compiled artifact, so build it rather
# than skip.  It used to carry a module-level `skipif(not RITZ1.exists())`,
# evaluated at COLLECTION time — before any fixture can run — which meant CI's
# bootstrap job (unit tests at step 6, ritz1 built at step 7) skipped all 10
# tests on every run since #1279 landed.  A suite about cache staleness,
# silently disabled by a staleness-shaped condition, in the one environment
# that is supposed to be authoritative (AGAST #1327).
#
# Mirroring #1322's fix for test_ritz1_parse_errors.py: always invoke make.
# An up-to-date `make -C ritz1 ritz1` is a ~9ms no-op, so the warm case costs
# nothing, and we additionally stop trusting a binary that is merely *present*
# but stale.


@pytest.fixture(scope="module", autouse=True)
def _ritz1_built():
    """Build (or freshen) the ritz1 binary; fail loudly rather than skip.

    A skipped test is indistinguishable from a passing one in aggregate
    output — "reported success while asserting nothing" is the exact failure
    family #1301/#1322/#1327 are about.
    """
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1.exists():
        pytest.fail(
            "could not build ritz1 for the cache-identity tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )

# Deliberately import-free: these tests exercise the cache, not the language,
# and a standalone source keeps the compile fast and RITZ_PATH-independent.
SOURCE = "fn main() -> i32\n    0\n"

# A recognisable payload we can plant in `module_ir` to prove whether the
# splice path fired.  It is not valid LLVM IR — it never needs to be, because
# nothing downstream of these tests runs clang on it, and using invalid IR
# makes an accidental *real* reuse impossible to mistake for success.
SENTINEL_IR = "; STALE-IR-FROM-A-DIFFERENT-COMPILER\n"


def _compile(compiler: Path, src: Path, out: Path) -> subprocess.CompletedProcess:
    """Run a ritz1 binary over `src`, returning the completed process."""
    return subprocess.run(
        [str(compiler), str(src), "-o", str(out)],
        capture_output=True,
        text=True,
        cwd=str(src.parent),
    )


def _sig_path(src: Path) -> Path:
    """`.ritz.sig` lives beside the source, with the extension replaced."""
    return src.with_suffix(".ritz.sig")


@pytest.fixture
def project(tmp_path):
    """A compiled-once source tree: (src, out, sig) with the cache warm."""
    src = tmp_path / "unit.ritz"
    src.write_text(SOURCE)
    out = tmp_path / "unit.ll"

    result = _compile(RITZ1, src, out)
    assert result.returncode == 0, f"initial compile failed: {result.stderr}"
    assert out.exists(), "initial compile produced no .ll"

    sig = _sig_path(src)
    assert sig.exists(), f"initial compile wrote no sig at {sig}"
    return src, out, sig


def _read_sig(sig: Path) -> dict:
    return json.loads(sig.read_text())


def _write_sig(sig: Path, data: dict) -> None:
    sig.write_text(json.dumps(data, indent=2) + "\n")


class TestSigRecordsCompilerIdentity:
    """The written sig must attribute its cached IR to a specific binary."""

    def test_sig_has_compiler_hash(self, project):
        _, _, sig = project
        data = _read_sig(sig)
        assert "compiler_hash" in data, (
            "sig has no compiler_hash — cached IR is unattributable and the "
            "reuse check below has nothing to compare against"
        )

    def test_compiler_hash_is_not_the_unknown_sentinel(self, project):
        """0 means 'compiler unknown' and must never match; a real run is not 0."""
        _, _, sig = project
        assert _read_sig(sig)["compiler_hash"] != "0" * 16

    def test_compiler_hash_is_stable_across_runs_of_one_binary(self, project, tmp_path):
        """Same binary, same fingerprint — otherwise the cache never hits."""
        src, _, sig = project
        first = _read_sig(sig)["compiler_hash"]

        other_src = tmp_path / "other.ritz"
        other_src.write_text(SOURCE)
        result = _compile(RITZ1, other_src, tmp_path / "other.ll")
        assert result.returncode == 0, result.stderr

        assert _read_sig(_sig_path(other_src))["compiler_hash"] == first


class TestFastPathHonoursCompilerIdentity:
    """Reuse when the compiler matches; refuse when it does not."""

    def test_matching_compiler_still_reuses(self, project):
        """The fast path is worth keeping — it must not be disabled wholesale."""
        src, out, _ = project
        result = _compile(RITZ1, src, out)
        assert result.returncode == 0, result.stderr
        assert "Skipped (unchanged)" in result.stdout, (
            "same compiler + unchanged source should still hit the fast path; "
            f"got: {result.stdout!r}"
        )

    def test_path_a_declines_when_compiler_hash_differs(self, project):
        """Path (a): `.ll` newer than source is NOT enough to justify reuse."""
        src, out, sig = project

        # Leave the .ll in place and newer than the source, so the mtime test
        # that used to be the entire gate passes. Only the compiler identity
        # differs.
        os.utime(out, (out.stat().st_atime, src.stat().st_mtime + 10))

        data = _read_sig(sig)
        data["compiler_hash"] = "deadbeefdeadbeef"
        _write_sig(sig, data)

        result = _compile(RITZ1, src, out)
        assert result.returncode == 0, result.stderr
        assert "Skipped (unchanged)" not in result.stdout, (
            "reused a .ll attributed to a different compiler"
        )

    def test_path_b_declines_when_compiler_hash_differs(self, project):
        """Path (b) — the splice — is the one that resurrects deleted output.

        Fixing only path (a) would leave this hole open, and it is the more
        damaging of the two: it hands back IR for an output file the build
        orchestrator has explicitly removed.
        """
        src, out, sig = project

        data = _read_sig(sig)
        data["module_ir"] = SENTINEL_IR
        data["compiler_hash"] = "deadbeefdeadbeef"
        _write_sig(sig, data)

        # Removing the .ll is exactly what `make` does before re-invoking the
        # compiler, so this is the real-world trigger, not a contrived one.
        out.unlink()

        result = _compile(RITZ1, src, out)
        assert result.returncode == 0, result.stderr
        assert "Skipped (unchanged)" not in result.stdout, (
            "spliced cached IR from a foreign compiler into a deleted output"
        )
        assert SENTINEL_IR not in out.read_text(), (
            "foreign compiler's cached IR reached the output .ll"
        )

    def test_path_b_splices_when_compiler_hash_matches(self, project):
        """Guard against the fix degenerating into 'never reuse anything'.

        If this ever fails while the two `declines` tests pass, the gate has
        been made unconditional and no-op rebuilds are back to ~12m30s.
        """
        src, out, sig = project

        data = _read_sig(sig)
        data["module_ir"] = SENTINEL_IR   # compiler_hash left untouched/valid
        _write_sig(sig, data)
        out.unlink()

        result = _compile(RITZ1, src, out)
        assert result.returncode == 0, result.stderr
        assert "Skipped (unchanged)" in result.stdout, (
            f"splice path stopped firing for a matching compiler: {result.stdout!r}"
        )
        assert out.read_text() == SENTINEL_IR

    def test_absent_compiler_hash_is_treated_as_unknown(self, project):
        """ritz0 writes the same `.ritz.sig` path and omits this field.

        Two compilers sharing one sig file must never consume each other's
        cached IR, so a missing field has to fail closed rather than being
        read as 'no compiler constraint'.
        """
        src, out, sig = project

        data = _read_sig(sig)
        data.pop("compiler_hash", None)
        _write_sig(sig, data)

        result = _compile(RITZ1, src, out)
        assert result.returncode == 0, result.stderr
        assert "Skipped (unchanged)" not in result.stdout


class TestAgainstARealDifferentBinary:
    """The end-to-end shape of the bug: rebuild the compiler, then rebuild."""

    def test_modified_compiler_binary_declines_to_reuse(self, project, tmp_path):
        """A genuinely different ritz1 must not inherit the previous one's cache.

        This is the regression that made `make matrix-full` answer from
        leftover build state: after ritz1 itself was rebuilt, every
        `build/%_sh.ll` was skipped rather than regenerated.

        We fabricate the "rebuilt compiler" by appending padding to a copy of
        the binary — trailing bytes past the ELF image are ignored by the
        loader, so the copy still runs, but its content fingerprint differs
        exactly as a real rebuild's would.
        """
        src, out, _ = project

        rebuilt = tmp_path / "ritz1_rebuilt"
        shutil.copy2(RITZ1, rebuilt)
        with rebuilt.open("ab") as fh:
            fh.write(b"\0" * 4096)
        rebuilt.chmod(0o755)

        # Sanity: the stand-in is a working compiler, not a corpse. If this
        # assertion fires the test below proves nothing.
        probe_src = tmp_path / "probe.ritz"
        probe_src.write_text(SOURCE)
        probe = _compile(rebuilt, probe_src, tmp_path / "probe.ll")
        assert probe.returncode == 0, f"padded binary does not run: {probe.stderr}"

        result = _compile(rebuilt, src, out)
        assert result.returncode == 0, result.stderr
        assert "Skipped (unchanged)" not in result.stdout, (
            "a rebuilt ritz1 reused the previous compiler's cached output — "
            "this is the defect that made the bootstrap gate report stale "
            "pass/fail results (AGAST #1279)"
        )

    def test_rebuilt_compiler_rewrites_the_sig_attribution(self, project, tmp_path):
        """After the forced recompile, the sig must name the *new* compiler."""
        src, out, sig = project
        original_hash = _read_sig(sig)["compiler_hash"]

        rebuilt = tmp_path / "ritz1_rebuilt"
        shutil.copy2(RITZ1, rebuilt)
        with rebuilt.open("ab") as fh:
            fh.write(b"\0" * 8192)
        rebuilt.chmod(0o755)

        result = _compile(rebuilt, src, out)
        assert result.returncode == 0, result.stderr

        assert _read_sig(sig)["compiler_hash"] != original_hash, (
            "sig still attributes its cached IR to the superseded compiler, "
            "so the next run would face the same stale-cache decision"
        )
