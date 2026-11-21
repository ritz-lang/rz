#!/usr/bin/env python3
"""A warm sig must not hide an import that no longer resolves (AGAST #1355, #2203).

#1355: after a compile with ``RITZ_PATH`` set wrote the sig, the same compile
with ``RITZ_PATH`` unset (or pointing nowhere) took the "Skipped … (unchanged)"
fast path and exited 0, though ``import ritzlib.io`` can no longer resolve.
#2020 fixed it by putting ``RITZ_PATH`` in the compile-mode key
(``ritz0._compile_mode``'s ``'ritz_path'`` entry); this pins that down.
``test_fast_path_compile_mode.py`` covers a switch between two valid roots;
here the new root cannot resolve the import at all.

Each compile is one forked ritz0 (``run_ritz0``) against a private
``RITZ_CACHE_DIR``, so the sig under test is this test's alone.
"""

import os
from pathlib import Path

import pytest

from emitter.fn_cache import sig_path_for
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
NOT_FOUND = "Cannot find module: ritzlib.io"


def _ritz0(src: Path, cache: Path, ritz_path):
    """Compile ``src``; ``ritz_path`` None means RITZ_PATH unset."""
    env = dict(os.environ)
    env.pop("RITZ_PATH", None)
    if ritz_path is not None:
        env["RITZ_PATH"] = str(ritz_path)
    env["RITZ_CACHE_DIR"] = str(cache)
    return run_ritz0(
        [str(src), "-o", str(src.with_suffix(".ll"))],
        cwd=str(src.parent),
        env=env,
        timeout=300,
    )


def _sig(src: Path, cache: Path) -> Path:
    old = os.environ.get("RITZ_CACHE_DIR")
    os.environ["RITZ_CACHE_DIR"] = str(cache)
    try:
        return sig_path_for(str(src))
    finally:
        if old is None:
            del os.environ["RITZ_CACHE_DIR"]
        else:
            os.environ["RITZ_CACHE_DIR"] = old


def _expect(proc, code: int, step: str):
    out = proc.stdout + proc.stderr
    assert proc.returncode == code, (
        f"step {step}: exit {proc.returncode}, want {code}:\n{out}"
    )
    if code == 1:
        assert NOT_FOUND in out, f"step {step}: missing {NOT_FOUND!r}:\n{out}"


@pytest.mark.integration
def test_unresolvable_ritz_path_after_warm_sig_fails(tmp_path):
    """Steps A-D of #1355: the sig must not turn a failing compile into exit 0."""
    cache = tmp_path / "cache"
    src = tmp_path / "main.ritz"
    src.write_text("import ritzlib.io\n\nfn main() -> i32\n    0\n")
    sig = _sig(src, cache)

    _expect(_ritz0(src, cache, None), 1, "A (cold, unset)")
    _expect(_ritz0(src, cache, RITZ_ROOT), 0, "B (cold, valid root)")
    assert sig.exists(), f"step B wrote no sig at {sig}"
    _expect(_ritz0(src, cache, None), 1, "C (warm, unset)")
    _expect(_ritz0(src, cache, "/tmp/nope"), 1, "C (warm, /tmp/nope)")
    sig.unlink()
    _expect(_ritz0(src, cache, None), 1, "D (sig removed, unset)")


@pytest.mark.integration
def test_unresolvable_ritz_path_through_warm_local_import_fails(tmp_path):
    """main imports a local ``a`` whose sig is warm; ``a`` imports ritzlib.io."""
    cache = tmp_path / "cache"
    a = tmp_path / "a.ritz"
    a.write_text("import ritzlib.io\n\npub fn a_val() -> i32\n    0\n")
    main = tmp_path / "main.ritz"
    main.write_text("import a\n\nfn main() -> i32\n    a_val()\n")

    _expect(_ritz0(a, cache, RITZ_ROOT), 0, "warm a")
    _expect(_ritz0(main, cache, RITZ_ROOT), 0, "warm main")
    assert _sig(a, cache).exists() and _sig(main, cache).exists()
    _expect(_ritz0(main, cache, None), 1, "main, unset")
