#!/usr/bin/env python3
"""`build.py run` gives every source file its own output path (AGAST #2252).

It used to link `<dir>/main.ritz` to projects/ritz/build/main whatever <dir>
was, so any two sources with the same stem shared one binary and one
manifest: running a second `main.ritz` relinked over the first, and two at
once raced on the file (#2251 saw exactly that). The output directory is now
derived from the source's resolved path, `build/run/<digest>/<stem>`, and the
binary keeps the source's stem as its name.

These need no xdist group: each build gets its own source directory (so its
own output path) and its own build cache through RITZ_BUILD_CACHE_DIR, and
session CAS stores are already private (conftest.py).
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
BUILD_PY = RITZ_ROOT / "build.py"

_spec = importlib.util.spec_from_file_location("ritz_build_2252", BUILD_PY)
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


@pytest.mark.unit
def test_same_stem_in_different_directories_gets_different_outputs(tmp_path):
    a = build.run_output_dir(tmp_path / "a" / "main.ritz")
    b = build.run_output_dir(tmp_path / "b" / "main.ritz")
    assert a != b
    assert a.parent == b.parent == RITZ_ROOT / "build" / "run"


@pytest.mark.unit
def test_the_output_follows_the_file_not_how_it_was_spelled(tmp_path, monkeypatch):
    src = tmp_path / "d" / "main.ritz"
    monkeypatch.chdir(tmp_path)
    assert build.run_output_dir(Path("d/main.ritz")) == build.run_output_dir(src)
    assert build.run_output_dir(Path("d/../d/main.ritz")) == build.run_output_dir(src)


def _run(src: Path, cache: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT), RITZ_BUILD_CACHE_DIR=str(cache))
    return subprocess.run(
        [sys.executable, str(BUILD_PY), "run", str(src)],
        cwd=src.parent, env=env, capture_output=True, text=True, timeout=300,
    )


@pytest.mark.integration
def test_two_mains_keep_their_own_binaries(tmp_path):
    first = tmp_path / "first" / "main.ritz"
    second = tmp_path / "second" / "main.ritz"
    for src, code in ((first, 3), (second, 4)):
        src.parent.mkdir()
        src.write_text(f"fn main() -> i32\n    {code}\n")
    cache = tmp_path / "cache"

    for src, code in ((first, 3), (second, 4)):
        result = _run(src, cache)
        assert result.returncode == code, result.stderr + result.stdout

    # Both binaries are still there, each where its own source says.
    for src in (first, second):
        binary = build.run_output_dir(src) / "main"
        assert binary.is_file(), f"{binary} missing"
        assert (binary.parent / "main.manifest.json").is_file()

    # Building `second` left `first`'s binary alone, so it is still up to date.
    again = _run(first, cache)
    assert again.returncode == 3, again.stderr + again.stdout
    assert "= main up to date" in again.stdout, again.stdout
    assert "🔨" not in again.stdout, again.stdout
