"""tools/exec_tmpdir.py: the gate and smoke run binaries from an exec-able
temp dir even when /tmp is mounted noexec (AGAST #3704).

A room can't mount a noexec tmpfs, so the probe's "can't run it" path is
driven by an injected exec function that raises EACCES as a noexec mount
does -- plus, where the host has one (/run/user/<uid> on many systemd hosts),
a real writable noexec mount.

Run: python3 -m pytest projects/ritz/tools/test_exec_tmpdir.py -q
"""

from __future__ import annotations

import errno
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import exec_tmpdir  # noqa: E402

pytestmark = pytest.mark.unit


def noexec_exec(path: str) -> int:
    """What posix_spawn does to a file on a noexec mount."""
    raise PermissionError(errno.EACCES, "Permission denied", path)


def noexec_in(bad: Path):
    """An exec_fn under which only files in `bad` can't run."""
    def run(path: str) -> int:
        if Path(path).parent == bad:
            noexec_exec(path)
        return exec_tmpdir._exec(path)
    return run


def writable_noexec_mount() -> Path | None:
    try:
        lines = Path("/proc/mounts").read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        parts = line.split()
        if len(parts) < 4 or "noexec" not in parts[3].split(",") or "rw" not in parts[3].split(","):
            continue
        for cand in (Path(parts[1]) / str(os.getuid()), Path(parts[1])):
            if cand.is_dir() and os.access(cand, os.W_OK | os.X_OK):
                return cand
    return None


@pytest.fixture
def clean_tempfile(monkeypatch):
    """ensure_exec_tmpdir resets tempfile's cache; put the real one back."""
    monkeypatch.setattr(tempfile, "tempdir", None)
    yield
    tempfile.tempdir = None


# ---- probe ---------------------------------------------------------------

def test_probe_passes_in_an_exec_able_dir(tmp_path):
    assert exec_tmpdir.probe(tmp_path) is None


def test_probe_really_runs_the_file(tmp_path):
    seen = []

    def run(path):
        seen.append((path, os.access(path, os.X_OK), Path(path).read_text()))
        return exec_tmpdir._exec(path)

    assert exec_tmpdir.probe(tmp_path, run) is None
    (path, executable, text), = seen
    assert Path(path).parent == tmp_path and executable and text.startswith("#!/bin/sh")


def test_probe_reports_a_noexec_dir_by_name(tmp_path):
    why = exec_tmpdir.probe(tmp_path, noexec_exec)
    assert why is not None and str(tmp_path) in why and "noexec" in why


def test_probe_fails_when_the_probe_exits_nonzero(tmp_path):
    why = exec_tmpdir.probe(tmp_path, lambda p: 126)
    assert why is not None and "126" in why


def test_probe_fails_on_an_unwritable_dir(tmp_path):
    missing = tmp_path / "no-such-dir"
    why = exec_tmpdir.probe(missing)
    assert why is not None and str(missing) in why


def test_probe_leaves_nothing_behind(tmp_path):
    exec_tmpdir.probe(tmp_path)
    exec_tmpdir.probe(tmp_path, noexec_exec)
    assert list(tmp_path.iterdir()) == []


def test_probe_fails_on_a_real_noexec_mount():
    mnt = writable_noexec_mount()
    if mnt is None:
        pytest.skip("no writable noexec mount on this host")
    why = exec_tmpdir.probe(mnt)
    assert why is not None and str(mnt) in why


# ---- ensure_exec_tmpdir --------------------------------------------------

def test_ensure_changes_nothing_when_tmp_runs_binaries(tmp_path, monkeypatch,
                                                      clean_tempfile):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    out = io.StringIO()
    got = exec_tmpdir.ensure_exec_tmpdir(fallback=tmp_path / "fb", out=out)
    assert got is None and os.environ["TMPDIR"] == str(tmp_path) and out.getvalue() == ""
    assert not (tmp_path / "fb").exists()


def test_ensure_switches_tmpdir_to_the_fallback(tmp_path, monkeypatch, clean_tempfile):
    bad = tmp_path / "noexec-tmp"
    bad.mkdir()
    fb = tmp_path / "cache" / "exec-tmp"
    monkeypatch.setenv("TMPDIR", str(bad))
    out = io.StringIO()
    got = exec_tmpdir.ensure_exec_tmpdir(fallback=fb, exec_fn=noexec_in(bad), out=out)
    assert got == fb and fb.is_dir()
    # Children inherit it, and this process's tempfile uses it from now on.
    assert os.environ["TMPDIR"] == str(fb)
    assert tempfile.gettempdir() == str(fb)
    assert str(bad) in out.getvalue() and str(fb) in out.getvalue()


def test_ensure_raises_setup_error_when_the_fallback_fails_too(tmp_path, monkeypatch,
                                                               clean_tempfile):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    fb = tmp_path / "fb"
    with pytest.raises(exec_tmpdir.SetupError) as e:
        exec_tmpdir.ensure_exec_tmpdir(fallback=fb, exec_fn=noexec_exec, out=io.StringIO())
    assert str(tmp_path) in str(e.value) and str(fb) in str(e.value)
    assert os.environ["TMPDIR"] == str(tmp_path)


def test_default_fallback_is_under_the_user_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert exec_tmpdir.default_fallback() == tmp_path / "ritz" / "exec-tmp"


# ---- CLI: what run-gate.sh calls ------------------------------------------

def cli(*args):
    return subprocess.run([str(HERE / "exec_tmpdir.py"), *args], check=False,
                          capture_output=True, text=True, timeout=60)


def test_cli_probe_exit_0_in_an_exec_able_dir(tmp_path):
    p = cli("probe", str(tmp_path))
    assert p.returncode == 0, p.stdout + p.stderr


def test_cli_probe_is_a_setup_error_naming_the_dir(tmp_path):
    missing = tmp_path / "gone"
    p = cli("probe", str(missing))
    assert p.returncode == exec_tmpdir.EXIT_SETUP
    assert p.stdout.startswith("SETUP ERROR") and str(missing) in p.stdout


def test_cli_probe_on_a_real_noexec_mount():
    mnt = writable_noexec_mount()
    if mnt is None:
        pytest.skip("no writable noexec mount on this host")
    p = cli("probe", str(mnt))
    assert p.returncode == exec_tmpdir.EXIT_SETUP and str(mnt) in p.stdout


# ---- wiring ---------------------------------------------------------------

def test_smoke_and_matrix_use_the_one_helper():
    """Both entry points call ensure_exec_tmpdir; neither has its own probe."""
    for name in ("smoke.py", "run_regression_matrix.py"):
        src = (HERE / name).read_text()
        assert "exec_tmpdir.ensure_exec_tmpdir(" in src, name
        assert "chmod" not in src, f"{name} grew its own exec probe"

