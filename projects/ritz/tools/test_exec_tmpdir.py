"""tools/exec_tmpdir.py: the gate and smoke run binaries from an exec-able
temp dir even when /tmp is mounted noexec (AGAST #3704).

A room can't mount a noexec tmpfs, so the probe's "can't run it" path is
driven by an injected exec function that raises EACCES as a noexec mount
does -- plus, where the host has one (/dev/shm, /run/user/<uid> or a noexec
/tmp), a real noexec mount this user can write to.  Hosts with none (a GitHub
runner's are /sys and /proc, which it can't write) skip those two tests.

Run: python3 -m pytest projects/ritz/tools/test_exec_tmpdir.py -q
"""

from __future__ import annotations

import errno
import io
import os
import stat
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


# Where to look first: mounts a user can normally write to.  On bangerang
# /dev/shm and /tmp are both noexec; on a GitHub runner the first noexec mount
# in the table is /sys/fs/pstore, which the runner user can't even stat into.
PREFERRED_MOUNTS = ("/dev/shm", f"/run/user/{os.getuid()}", "/tmp")


def _preferred_first(points: list[str]) -> list[str]:
    rank = {p: i for i, p in enumerate(PREFERRED_MOUNTS)}
    return sorted(points, key=lambda p: rank.get(p, len(rank)))


def _can_write_in(d: Path) -> bool:
    """Really create (and remove) a dir in `d`: os.access and is_dir() can't be
    trusted on /sys and friends, and Path.is_dir() raises EACCES on 3.12."""
    try:
        with tempfile.TemporaryDirectory(prefix="noexec_find_", dir=d):
            pass
    except OSError:
        return False
    return True


def writable_noexec_mount(mounts: str | os.PathLike = "/proc/mounts") -> Path | None:
    """A dir on a rw,noexec mount this process can write to, else None.
    Never raises: an unreadable mount table or mount point is just skipped."""
    try:
        lines = Path(mounts).read_text().splitlines()
    except OSError:
        return None
    points = []
    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            continue
        opts = parts[3].split(",")
        if "noexec" in opts and "rw" in opts:
            points.append(parts[1])
    for point in _preferred_first(points):
        for cand in (Path(point) / str(os.getuid()), Path(point)):
            if _can_write_in(cand):
                return cand
    return None


@pytest.fixture
def noexec_mount() -> Path:
    mnt = writable_noexec_mount()
    if mnt is None:
        pytest.skip("no writable noexec mount on this host (none in /proc/mounts "
                    "that this user can create a dir in); the stub-based probe "
                    "tests cover the logic")
    return mnt


@pytest.fixture
def clean_tempfile(monkeypatch):
    """ensure_exec_tmpdir resets tempfile's cache; put the real one back."""
    monkeypatch.setattr(tempfile, "tempdir", None)
    yield
    tempfile.tempdir = None


# ---- probe ---------------------------------------------------------------

@pytest.mark.integration
def test_probe_passes_in_an_exec_able_dir(tmp_path):
    assert exec_tmpdir.probe(tmp_path) is None


@pytest.mark.integration
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


@pytest.mark.integration
def test_probe_leaves_nothing_behind(tmp_path):
    exec_tmpdir.probe(tmp_path)
    exec_tmpdir.probe(tmp_path, noexec_exec)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.integration
def test_probe_fails_on_a_real_noexec_mount(noexec_mount):
    mnt = noexec_mount
    why = exec_tmpdir.probe(mnt)
    assert why is not None and str(mnt) in why


# ---- finding a real noexec mount (AGAST #3743) -----------------------------

@pytest.fixture
def py312_is_dir(monkeypatch):
    """Path.is_dir() as on CI's Python 3.12: EACCES propagates (3.14 swallows it)."""
    def is_dir(self):
        try:
            return stat.S_ISDIR(os.stat(self).st_mode)
        except (FileNotFoundError, NotADirectoryError):
            return False
    monkeypatch.setattr(Path, "is_dir", is_dir)


def mount_table(tmp_path, *entries) -> Path:
    """A /proc/mounts listing (mount point, options) pairs."""
    table = tmp_path / "mounts"
    table.write_text("".join(f"fake {mp} tmpfs {opts} 0 0\n" for mp, opts in entries))
    return table


@pytest.fixture
def locked(tmp_path):
    """Dirs as the runner user sees /sys/fs/pstore (0750 root): 0o000 and 0o500."""
    if os.getuid() == 0:
        pytest.skip("root ignores directory permissions")
    made = []

    def make(name, mode):
        d = tmp_path / name
        d.mkdir()
        d.chmod(mode)
        made.append(d)
        return d
    yield make
    for d in made:
        d.chmod(0o700)


def test_discovery_skips_an_unsearchable_noexec_mount(tmp_path, locked, py312_is_dir):
    """The CI failure: stat'ing /sys/fs/pstore/<uid> raised during setup."""
    pstore = locked("pstore", 0o000)
    table = mount_table(tmp_path, (pstore, "rw,nosuid,nodev,noexec,relatime"))
    assert writable_noexec_mount(table) is None


def test_discovery_skips_a_read_only_noexec_mount(tmp_path, locked, py312_is_dir):
    ro = locked("ro", 0o500)
    table = mount_table(tmp_path, (ro, "rw,nosuid,nodev,noexec"))
    assert writable_noexec_mount(table) is None


def test_discovery_moves_past_unwritable_mounts_to_a_writable_one(tmp_path, locked,
                                                                  py312_is_dir):
    ok = tmp_path / "ok"
    ok.mkdir()
    table = mount_table(tmp_path, (locked("pstore", 0o000), "rw,noexec"),
                        (locked("ro", 0o500), "rw,noexec"), (ok, "rw,noexec"))
    assert writable_noexec_mount(table) == ok
    assert list(ok.iterdir()) == []


def test_discovery_wants_rw_and_noexec(tmp_path):
    exec_ok, ro = tmp_path / "exec", tmp_path / "ro"
    exec_ok.mkdir()
    ro.mkdir()
    table = mount_table(tmp_path, (exec_ok, "rw,nosuid"), (ro, "ro,noexec"))
    assert writable_noexec_mount(table) is None


def test_discovery_without_a_mount_table_is_none(tmp_path):
    assert writable_noexec_mount(tmp_path / "no-mounts") is None


def test_discovery_tries_dev_shm_and_tmp_before_sys():
    got = _preferred_first(["/sys/fs/pstore", "/tmp", "/proc", "/dev/shm"])
    assert got[:2] == ["/dev/shm", "/tmp"]


# ---- ensure_exec_tmpdir --------------------------------------------------

@pytest.mark.integration
def test_ensure_changes_nothing_when_tmp_runs_binaries(tmp_path, monkeypatch,
                                                      clean_tempfile):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    out = io.StringIO()
    got = exec_tmpdir.ensure_exec_tmpdir(fallback=tmp_path / "fb", out=out)
    assert got is None and os.environ["TMPDIR"] == str(tmp_path) and out.getvalue() == ""
    assert not (tmp_path / "fb").exists()


@pytest.mark.integration
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


@pytest.mark.integration
def test_cli_probe_exit_0_in_an_exec_able_dir(tmp_path):
    p = cli("probe", str(tmp_path))
    assert p.returncode == 0, p.stdout + p.stderr


@pytest.mark.integration
def test_cli_probe_is_a_setup_error_naming_the_dir(tmp_path):
    missing = tmp_path / "gone"
    p = cli("probe", str(missing))
    assert p.returncode == exec_tmpdir.EXIT_SETUP
    assert p.stdout.startswith("SETUP ERROR") and str(missing) in p.stdout


@pytest.mark.integration
def test_cli_probe_on_a_real_noexec_mount(noexec_mount):
    mnt = noexec_mount
    p = cli("probe", str(mnt))
    assert p.returncode == exec_tmpdir.EXIT_SETUP and str(mnt) in p.stdout


# ---- wiring ---------------------------------------------------------------

def test_smoke_and_matrix_use_the_one_helper():
    """Every entry point that runs built binaries calls ensure_exec_tmpdir;
    none has its own probe."""
    for name in ("smoke.py", "run_regression_matrix.py", "ritz1_unit.py"):
        src = (HERE / name).read_text()
        assert "exec_tmpdir.ensure_exec_tmpdir(" in src, name
        assert "chmod" not in src, f"{name} grew its own exec probe"

