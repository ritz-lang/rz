"""tools/sweep_pytest_tmp.py ages out stale pytest basetemps (AGAST #4274).

2026-11-19, bangerang: /tmp (a tmpfs, 1,048,576 inodes) filled up with 29
old /tmp/pytest-of-aaron/pytest-N dirs of 110-145k files each; every mktemp
then failed and gates broke.  pytest's own retention (keep 3) never removed
them: a run killed outright leaves its .lock for 3 days, and a dir a test
left with no read bit stops pytest's rm.  The sweep removes pytest-* dirs
older than --max-age-hours, mode-000 dirs and all, but never one whose .lock
names a live process.

Run: python3 -m pytest projects/ritz/tools/test_sweep_pytest_tmp.py -q
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import sweep_pytest_tmp as sweep

pytestmark = pytest.mark.unit

HOUR = 3600
NOW = 1_800_000_000.0


def _basetemp(root: Path, name: str, age_h: float, lock_pid: int | None = None) -> Path:
    """A pytest-N dir as pytest leaves it, last touched age_h hours before NOW."""
    d = root / name
    (d / "test_a0").mkdir(parents=True)
    (d / "test_a0" / "out.txt").write_text("x")
    t = NOW - age_h * HOUR
    if lock_pid is not None:
        (d / ".lock").write_text(str(lock_pid))
        os.utime(d / ".lock", (t, t))
    os.utime(d, (t, t))
    return d


def _dead_pid() -> int:
    """A PID no process has: above the kernel's pid_max."""
    return int(Path("/proc/sys/kernel/pid_max").read_text()) + 1


def _alive(pid: int) -> bool:
    return pid == os.getpid()


def test_only_dirs_older_than_the_limit_are_stale(tmp_path):
    old = _basetemp(tmp_path, "pytest-1", 5)
    _basetemp(tmp_path, "pytest-2", 1)
    assert sweep.find_stale(tmp_path, 3 * HOUR, now=NOW, alive=_alive) == [old]


def test_a_live_lock_keeps_an_old_dir_and_a_dead_one_does_not(tmp_path):
    _basetemp(tmp_path, "pytest-1", 5, lock_pid=os.getpid())
    dead = _basetemp(tmp_path, "pytest-2", 5, lock_pid=_dead_pid())
    assert sweep.find_stale(tmp_path, 3 * HOUR, now=NOW, alive=_alive) == [dead]


def test_a_fresh_lock_keeps_a_dir_whose_own_mtime_is_old(tmp_path):
    # A long session: pytest-N was made hours ago, its .lock touched since.
    d = _basetemp(tmp_path, "pytest-1", 5, lock_pid=_dead_pid())
    os.utime(d / ".lock", (NOW, NOW))
    os.utime(d, (NOW - 5 * HOUR, NOW - 5 * HOUR))
    assert sweep.find_stale(tmp_path, 3 * HOUR, now=NOW, alive=_alive) == []


def test_a_future_mtime_is_stale_not_forever_fresh(tmp_path):
    # bangerang, #4274: gate-queue tests set mtimes into the future, and
    # pytest-4530 (83k inodes, idle 1h+) looked recent to every age sweep.
    # A dir or .lock dated over a minute ahead counts as stale.
    d1 = _basetemp(tmp_path, "pytest-1", -2)
    d2 = _basetemp(tmp_path, "pytest-2", 5, lock_pid=_dead_pid())
    os.utime(d2 / ".lock", (NOW + 7 * 24 * HOUR,) * 2)
    os.utime(d2, (NOW - 5 * HOUR,) * 2)
    _basetemp(tmp_path, "pytest-3", -0.01)  # 36 s ahead: clock skew, kept
    assert sweep.find_stale(tmp_path, 3 * HOUR, now=NOW, alive=_alive) == [d1, d2]


def test_future_mtimes_inside_a_dir_do_not_keep_it(tmp_path):
    d = _basetemp(tmp_path, "pytest-1", 5)
    os.utime(d / "test_a0" / "out.txt", (NOW + 24 * HOUR,) * 2)
    os.utime(d / "test_a0", (NOW + 24 * HOUR,) * 2)
    os.utime(d, (NOW - 5 * HOUR,) * 2)
    assert sweep.find_stale(tmp_path, 3 * HOUR, now=NOW, alive=_alive) == [d]


def test_symlinks_and_other_names_are_left_alone(tmp_path):
    target = _basetemp(tmp_path, "keepme", 9)
    (tmp_path / "pytest-current").symlink_to(target)
    os.utime(tmp_path / "pytest-current", (NOW - 9 * HOUR,) * 2, follow_symlinks=False)
    (tmp_path / "pytest-9.txt").write_text("not a dir")
    assert sweep.find_stale(tmp_path, 3 * HOUR, now=NOW, alive=_alive) == []


def test_a_missing_root_has_nothing_stale(tmp_path):
    assert sweep.find_stale(tmp_path / "nope", 3 * HOUR, now=NOW, alive=_alive) == []


def test_remove_clears_mode_000_dirs(tmp_path):
    d = _basetemp(tmp_path, "pytest-1", 5)
    deep = d / "test_a0" / "noread" / "inner"
    deep.mkdir(parents=True)
    (deep / "f").write_text("x")
    (d / "test_a0" / "ro.txt").write_text("x")
    (d / "test_a0" / "ro.txt").chmod(0)
    deep.chmod(0)
    (d / "test_a0" / "noread").chmod(0)
    (d / "test_a0").chmod(0o500)
    sweep.remove(d)
    assert not d.exists()


def test_remove_does_not_follow_a_symlink_out(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep").write_text("x")
    outside.chmod(0o500)
    d = _basetemp(tmp_path, "pytest-1", 5)
    (d / "link").symlink_to(outside)
    sweep.remove(d)
    assert not d.exists()
    assert (outside / "keep").exists() and (outside.stat().st_mode & 0o777) == 0o500
    outside.chmod(0o700)


def test_main_dry_run_lists_only_stale_dirs_and_removes_nothing(tmp_path):
    old = _basetemp(tmp_path, "pytest-1", 5)
    new = _basetemp(tmp_path, "pytest-2", 1)
    ahead = _basetemp(tmp_path, "pytest-3", -48)
    out = io.StringIO()
    rc = sweep.main(["--root", str(tmp_path), "--dry-run"], now=NOW, out=out)
    assert rc == 0
    lines = out.getvalue().splitlines()
    assert lines[0] == f"would remove {old} (5.0h old)"
    assert lines[1] == f"would remove {ahead} (mtime in the future)"
    assert str(new) not in out.getvalue()
    assert lines[-1] == f"{tmp_path}: 2 stale of 3, 0 removed (dry run)"
    assert old.exists() and new.exists() and ahead.exists()


def test_main_removes_stale_dirs(tmp_path):
    old = _basetemp(tmp_path, "pytest-1", 5)
    old.chmod(0o500)
    new = _basetemp(tmp_path, "pytest-2", 1)
    out = io.StringIO()
    assert (
        sweep.main(["--root", str(tmp_path), "--max-age-hours", "2"], now=NOW, out=out)
        == 0
    )
    assert not old.exists() and new.exists()
    assert out.getvalue().splitlines()[-1] == f"{tmp_path}: 1 stale of 2, 1 removed"


def test_main_default_root_is_pytests_own(monkeypatch, tmp_path):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(tempfile, "tempdir", None)  # tempfile caches its dir
    monkeypatch.setattr(sweep, "_user", lambda: "someone")
    assert sweep.default_root() == tmp_path / "pytest-of-someone"


def test_install_copies_itself_and_enables_a_user_timer(tmp_path):
    calls = []
    sweep.install(tmp_path, max_age_hours=3, run=calls.append)
    script = tmp_path / ".local" / "libexec" / "rz-pytest-sweep.py"
    assert script.read_bytes() == Path(sweep.__file__).read_bytes()
    units = tmp_path / ".config" / "systemd" / "user"
    service = (units / "rz-pytest-sweep.service").read_text()
    timer = (units / "rz-pytest-sweep.timer").read_text()
    # The installed copy, not this checkout (a worktree can be removed).
    assert f"ExecStart=/usr/bin/env python3 {script} --max-age-hours 3" in service
    assert "Type=oneshot" in service
    assert "OnUnitActiveSec=" in timer and "WantedBy=timers.target" in timer
    assert calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", "rz-pytest-sweep.timer"],
    ]
