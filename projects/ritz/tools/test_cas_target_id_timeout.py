"""cas.target_id's `clang --version` probe is bounded (AGAST #4148).

It ran as `with Popen(...) as proc: proc.communicate(timeout=30)`. On a
timeout, Popen.__exit__ ran before the `except` and wait()ed for the hung
clang with no bound, so the timeout never took effect and a wedged clang
hung every build. A fake `clang` on PATH that sleeps must now give up
within the bound.
"""

import importlib
import os
import sys
import time
from pathlib import Path

import pytest

PKG_DIR = Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))

cas = importlib.import_module("cas")


def _fake_clang(tmp_path: Path, monkeypatch, body: str) -> None:
    clang = tmp_path / "clang"
    clang.write_text("#!/bin/sh\n" + body + "\n")
    clang.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setattr(cas, "_TARGET", None)


@pytest.mark.unit
def test_hung_clang_version_gives_up_within_the_bound(tmp_path, monkeypatch):
    # `sleep` without exec: a grandchild holds stdout open after the
    # shell is killed, so the fix must not read the pipe to EOF either.
    _fake_clang(tmp_path, monkeypatch, "sleep 10")
    monkeypatch.setattr(cas, "CLANG_VERSION_TIMEOUT", 0.3)
    start = time.monotonic()
    tid = cas.target_id()
    elapsed = time.monotonic() - start
    assert elapsed < 5, f"target_id() took {elapsed:.1f}s past a 0.3s bound"
    assert tid.endswith("/clang-missing"), tid


@pytest.mark.unit
def test_clang_version_first_line_is_the_target(tmp_path, monkeypatch):
    _fake_clang(tmp_path, monkeypatch, "echo 'fake clang 99.0'; echo second")
    assert cas.target_id().endswith("/fake clang 99.0")
