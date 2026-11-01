#!/usr/bin/env python3
"""A warm-sig recompile must emit the same IR as a cold one (AGAST #2019).

ritz0's per-function IR cache (``emitter/fn_cache.py``) records each source
fn's token hash and emitted IR in a ``.sig``.  On the next compile every fn
whose hash still matches is a "hit": ``emit_llvmlite`` tells the emitter to
skip that fn's body, then ``_splice_cached_ir`` swaps the resulting
``declare`` back for the cached ``define``.

The hits only ever took effect on fns the async transform synthesizes.
Ordinary source fns carry ``source_file``, so ``_should_emit_body`` emits
them regardless.  An ``async fn add_one`` becomes a synthesized constructor
named ``add_one``, the same name as the source fn, so it was the only hit
honoured.  Its body was skipped, and the splice regex (which wants the
declare line to end at ``)``) never matched the ``... "no-builtins"`` declare
the emitter writes.  The warm compile therefore only *declared* ``@add_one``
while defining ``@add_one_poll``, and the object failed to link with
``undefined reference to add_one``.  build.py's machine-wide CAS (#1808) then
kept that bad object for every worktree building the same key.

Each test runs ritz0 as a subprocess (no in-process compile cache) against a
private ``RITZ_CACHE_DIR``, so "cold" really is cold and "warm" really is warm.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZ0 = RITZ0_DIR / "ritz0.py"
EXAMPLE_62 = (
    RITZ_ROOT / "examples" / "tier5_async" / "62_async_compiler" / "src" / "main.ritz"
)

# `define <ret> @"name"(` / `declare <ret> @"name"(`
_DEFINE_RE = re.compile(r'^define\s[^@]*@"?([^"(\s]+)"?\(', re.MULTILINE)
_DECLARE_RE = re.compile(r'^declare\s[^@]*@"?([^"(\s]+)"?\(', re.MULTILINE)


def _compile(src: Path, out: Path, cache_dir: Path) -> None:
    env = dict(os.environ)
    env["RITZ_PATH"] = str(RITZ_ROOT)
    env["RITZ_CACHE_DIR"] = str(cache_dir)
    proc = subprocess.run(
        [sys.executable, str(RITZ0), str(src), "-o", str(out), "--no-runtime"],
        capture_output=True,
        text=True,
        cwd=str(src.parent),
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, f"ritz0 failed:\n{proc.stdout}\n{proc.stderr}"
    assert "Skipped" not in proc.stdout, (
        f"{out.name} is a fresh output path; ritz0 must compile, not skip:\n{proc.stdout}"
    )


def _defined(ir: str) -> set:
    return set(_DEFINE_RE.findall(ir))


def _declared(ir: str) -> set:
    return set(_DECLARE_RE.findall(ir))


@pytest.fixture
def example_62(tmp_path) -> Path:
    """62's main.ritz in a private directory (its sig is keyed on realpath)."""
    src = tmp_path / "src" / "main.ritz"
    src.parent.mkdir()
    shutil.copy(EXAMPLE_62, src)
    return src


@pytest.fixture
def cache_dir(tmp_path) -> Path:
    return tmp_path / "sigcache"


@pytest.mark.integration
def test_cold_compile_defines_async_constructor(example_62, cache_dir, tmp_path):
    """Baseline: a cold compile defines both halves of `async fn add_one`."""
    out = tmp_path / "cold.ll"
    _compile(example_62, out, cache_dir)
    defined = _defined(out.read_text())
    assert "add_one" in defined
    assert "add_one_poll" in defined


@pytest.mark.integration
def test_warm_sig_recompile_is_byte_identical_to_cold(example_62, cache_dir, tmp_path):
    """The #2019 repro: compile, then compile again into a new output file."""
    cold = tmp_path / "cold.ll"
    warm = tmp_path / "warm.ll"
    _compile(example_62, cold, cache_dir)
    _compile(example_62, warm, cache_dir)

    cold_ir, warm_ir = cold.read_text(), warm.read_text()
    assert "add_one" in _defined(cold_ir)
    assert "add_one" in _defined(warm_ir), (
        "warm-sig recompile only declares the async constructor @add_one"
    )
    assert warm_ir == cold_ir, "warm-sig recompile IR differs from the cold compile"


@pytest.mark.integration
def test_repeated_warm_recompiles_stay_identical(example_62, cache_dir, tmp_path):
    """A sig rewritten by a warm compile must not poison the next one either."""
    outs = [tmp_path / f"build{i}.ll" for i in range(3)]
    for out in outs:
        _compile(example_62, out, cache_dir)
    irs = [o.read_text() for o in outs]
    assert irs[1] == irs[0]
    assert irs[2] == irs[0]


@pytest.mark.integration
def test_warm_recompile_defines_every_async_constructor(
    example_62, cache_dir, tmp_path
):
    """Every `X_poll` this module defines comes with its constructor `X` defined.

    This is the scan used to find the poisoned CAS objects: a defined poll fn
    with a merely declared constructor is exactly the #2019 link failure.
    """
    _compile(example_62, tmp_path / "cold.ll", cache_dir)
    warm = tmp_path / "warm.ll"
    _compile(example_62, warm, cache_dir)
    ir = warm.read_text()
    defined, declared = _defined(ir), _declared(ir)
    polls = {n[: -len("_poll")] for n in defined if n.endswith("_poll")}
    assert polls, "62 should define async poll fns"
    missing = sorted(c for c in polls if c not in defined and c in declared)
    assert not missing, f"async constructors only declared on warm recompile: {missing}"
