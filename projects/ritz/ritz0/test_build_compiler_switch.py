"""`build.py build --compiler X` must relink a binary another compiler produced.

AGAST #1360: `<pkg>/build/debug/<bin>` was not keyed on the compiler that
built it. Building with ritz1 and then with ritz0 (no clean) left ritz1's
binary in place while printing `🔨 ... ✓`, and vice versa: whichever compiler
ran first won. The per-compiler object caches (.ritz-cache, .ritz-cache-ritz1)
were already partitioned; the linked output was not.

#1382's provenance manifest (`build/<profile>/<name>.manifest.json`) records
the compiler name and hash, which closes this. tools/test_build_binary_provenance.py
covers it only by REWRITING the manifest's compiler field. These tests run the
real switch, end to end, with both real compilers, in both directions.

The two compilers are told apart by the binary's bytes: ritz0 and ritz1 emit
different IR for the same source, so their linked binaries differ. The
`distinct` fixture asserts that precondition. If ritz1 ever reaches byte
parity with ritz0 on this fixture, it fails loudly instead of letting the
switch tests pass for the wrong reason. Swap the fixture then.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[1]
BUILD_PY = RITZ_ROOT / "build.py"
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
EXAMPLE = RITZ_ROOT / "examples" / "tier1_basics" / "02_exitcode"
BIN_NAME = "exitcode"


def _build_ritz1() -> None:
    """Bring ritz1 up to date rather than skipping without it (AGAST #1327)."""
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", "ritz1", "ritz1"],
        cwd=RITZ_ROOT, env=env, capture_output=True, text=True, timeout=1800,
    )
    if proc.returncode != 0 or not RITZ1_BIN.exists():
        pytest.fail(
            "could not build ritz1 for the compiler-switch tests:\n"
            f"{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_built() -> None:
    _build_ritz1()


@pytest.fixture
def pkg(tmp_path, ritz1_built):
    dst = tmp_path / "pkg"
    shutil.copytree(EXAMPLE, dst, ignore=shutil.ignore_patterns("build", BIN_NAME))
    return dst


def binary(pkg: Path) -> Path:
    return pkg / "build" / "debug" / BIN_NAME


def manifest(pkg: Path) -> dict:
    return json.loads((pkg / "build" / "debug" / f"{BIN_NAME}.manifest.json").read_text())


def build(pkg: Path, compiler: str) -> str:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    r = subprocess.run(
        [sys.executable, str(BUILD_PY), "build", str(pkg), "--compiler", compiler],
        capture_output=True, text=True, cwd=RITZ_ROOT, env=env, timeout=600,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(pkg: Path) -> None:
    shutil.rmtree(pkg / "build", ignore_errors=True)


def run_exit(pkg: Path) -> int:
    return subprocess.run([str(binary(pkg))], timeout=30).returncode


@pytest.fixture
def distinct(pkg):
    """Clean-build reference hashes per compiler, and the precondition that they differ."""
    ref = {}
    for compiler in ("ritz0", "ritz1"):
        clean(pkg)
        build(pkg, compiler)
        assert run_exit(pkg) == 42, f"{compiler} miscompiled the fixture"
        ref[compiler] = sha(binary(pkg))
    assert ref["ritz0"] != ref["ritz1"], (
        "ritz0 and ritz1 now link byte-identical binaries for this fixture, so "
        "these tests can no longer tell which compiler built the output. "
        "Pick a fixture where they differ (see module docstring)."
    )
    clean(pkg)
    return ref


@pytest.mark.integration
@pytest.mark.parametrize("first,second", [("ritz1", "ritz0"), ("ritz0", "ritz1")])
def test_switching_compiler_relinks_build_debug(pkg, distinct, first, second):
    """The ticket's repro: steps A->B (ritz1 then ritz0) and C->D (ritz0 then ritz1)."""
    build(pkg, first)
    assert sha(binary(pkg)) == distinct[first]

    out = build(pkg, second)  # no clean in between
    assert sha(binary(pkg)) == distinct[second], (
        f"--compiler {second} left {first}'s binary in build/debug:\n{out}"
    )
    assert "up to date" not in out


@pytest.mark.integration
def test_switching_back_relinks_again(pkg, distinct):
    """ritz0 -> ritz1 -> ritz0: the stamp tracks the LAST compiler, not the first."""
    for compiler in ("ritz0", "ritz1", "ritz0"):
        build(pkg, compiler)
        assert sha(binary(pkg)) == distinct[compiler], f"after --compiler {compiler}"


@pytest.mark.integration
def test_manifest_records_the_last_compiler(pkg, distinct):
    """The stamp next to the binary names whichever compiler linked it most recently."""
    for compiler in ("ritz1", "ritz0", "ritz1"):
        build(pkg, compiler)
        assert manifest(pkg)["compiler"] == compiler


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_same_compiler_rebuild_stays_up_to_date(pkg, distinct, compiler):
    """Control: keying on the compiler must not disable the fast path."""
    build(pkg, compiler)
    out = build(pkg, compiler)
    assert "up to date" in out, out
    assert sha(binary(pkg)) == distinct[compiler]
