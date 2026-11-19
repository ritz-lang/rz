#!/usr/bin/env python3
"""Age out stale pytest basetemps: <tmp>/pytest-of-$USER/pytest-* (AGAST #4274).

2026-11-19, bangerang: /tmp is a tmpfs of 1,048,576 inodes, and 29 old
pytest-N dirs of 110-145k files each used ~1.0M of them.  Every mktemp then
failed with ENOSPC; a train gate, a room gate and the host room broke.
pytest keeps the last 3 basetemps, but it skips one whose .lock is under 3
days old (a run killed outright never drops its lock), and its rm stops at a
dir a test left with no read bit.  So the dirs piled up.

This sweep removes every pytest-* dir under the root that

  * is a real dir (pytest-current and other symlinks are left to pytest),
  * was last touched (the dir or its .lock) more than --max-age-hours ago,
    or is dated over a minute in the future (tests set future mtimes),
  * and whose .lock, if any, names no live process (a long session is kept),

making each one removable first (chmod u+rwx on every dir, symlinks never
followed), as `rm -rf` alone can't descend into a mode-000 dir.

Every host runs it from a user timer; install it once per host with

    python3 projects/ritz/tools/sweep_pytest_tmp.py --install

which copies this file to ~/.local/libexec/rz-pytest-sweep.py (so the timer
outlives any worktree), writes rz-pytest-sweep.{service,timer} under
~/.config/systemd/user and enables the timer (every 30 min).  Re-run it to
update.  `--dry-run` lists what would go.  Stdlib only.
"""

from __future__ import annotations

import argparse
import getpass
import math
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

DEFAULT_MAX_AGE_HOURS = 3.0
UNIT = "rz-pytest-sweep"
TIMER_INTERVAL = "30min"
# An mtime further ahead than this is a test's doing, not clock skew.
FUTURE_SLACK_S = 60.0


def _user() -> str:
    return getpass.getuser()


def default_root() -> Path:
    """Where pytest puts basetemps: <tempfile's dir>/pytest-of-<user>."""
    return Path(tempfile.gettempdir()) / f"pytest-of-{_user()}"


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # someone else's process: alive
    except (OverflowError, ValueError):
        return False
    return True


def _lock(d: Path) -> tuple[float, int | None] | None:
    """(mtime, pid or None) of d/.lock, or None when there is none."""
    lock = d / ".lock"
    try:
        mtime = lock.lstat().st_mtime
    except OSError:
        return None
    try:
        pid = int(lock.read_text().strip())
    except (OSError, ValueError):
        pid = None
    return mtime, pid


def age_of(d: Path, now: float) -> float:
    """Seconds since d or its .lock was last touched; inf when either is
    dated over FUTURE_SLACK_S ahead.  Gate-queue tests set mtimes into the
    future, and on bangerang a basetemp holding them looked fresh to every
    age sweep for good (pytest-4530, 83k inodes, AGAST #4274).  Only d and
    its .lock count: pytest writes both at the session's start, and the
    files a test leaves inside say nothing about whether a run is live."""
    times = [d.lstat().st_mtime]
    lk = _lock(d)
    if lk:
        times.append(lk[0])
    if max(times) > now + FUTURE_SLACK_S:
        return math.inf
    return now - max(times)


def find_stale(
    root: Path,
    max_age_s: float,
    *,
    now: float | None = None,
    alive: Callable[[int], bool] = pid_alive,
) -> list[Path]:
    """The pytest-* dirs under root this sweep would remove, sorted."""
    now = time.time() if now is None else now
    try:
        entries = sorted(root.iterdir())
    except OSError:
        return []
    stale = []
    for d in entries:
        if not d.name.startswith("pytest-"):
            continue
        try:
            if not stat.S_ISDIR(d.lstat().st_mode):
                continue
            if age_of(d, now) <= max_age_s:
                continue
        except OSError:
            continue
        lk = _lock(d)
        if lk and lk[1] is not None and alive(lk[1]):
            continue
        stale.append(d)
    return stale


def _make_removable(d: Path) -> None:
    """chmod u+rwx d and every dir under it, never following a symlink."""
    try:
        st = d.lstat()
    except OSError:
        return
    if not stat.S_ISDIR(st.st_mode):
        return
    try:
        os.chmod(d, stat.S_IMODE(st.st_mode) | stat.S_IRWXU)
        children = list(os.scandir(d))
    except OSError:
        return
    for e in children:
        if e.is_dir(follow_symlinks=False):
            _make_removable(Path(e.path))


def remove(d: Path) -> None:
    """`chmod -R u+rwx d && rm -rf d`, without following symlinks out."""
    _make_removable(d)
    shutil.rmtree(d, ignore_errors=True)


def install(
    home: Path,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
    run: Callable[[list[str]], object] = lambda c: subprocess.run(c, check=True),
) -> None:
    """Install this script and its user timer under home, and enable it."""
    script = home / ".local" / "libexec" / f"{UNIT}.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(__file__, script)
    script.chmod(0o755)
    units = home / ".config" / "systemd" / "user"
    units.mkdir(parents=True, exist_ok=True)
    (units / f"{UNIT}.service").write_text(
        "# Installed by projects/ritz/tools/sweep_pytest_tmp.py --install (AGAST #4274).\n"
        "[Unit]\n"
        "Description=Age out stale pytest basetemps under /tmp/pytest-of-%u\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        "Nice=19\n"
        "IOSchedulingClass=idle\n"
        f"ExecStart=/usr/bin/env python3 {script} --max-age-hours {max_age_hours:g}\n"
    )
    (units / f"{UNIT}.timer").write_text(
        "# Installed by projects/ritz/tools/sweep_pytest_tmp.py --install (AGAST #4274).\n"
        "[Unit]\n"
        f"Description=Run {UNIT}.service every {TIMER_INTERVAL}\n\n"
        "[Timer]\n"
        "OnBootSec=5min\n"
        f"OnUnitActiveSec={TIMER_INTERVAL}\n"
        "Persistent=true\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )
    run(["systemctl", "--user", "daemon-reload"])
    run(["systemctl", "--user", "enable", "--now", f"{UNIT}.timer"])


def main(
    argv: list[str] | None = None, *, now: float | None = None, out: TextIO = sys.stdout
) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--root",
        type=Path,
        action="append",
        help="a pytest-of-<user> dir (repeatable; default: pytest's own)",
    )
    ap.add_argument("--max-age-hours", type=float, default=DEFAULT_MAX_AGE_HOURS)
    ap.add_argument("--dry-run", action="store_true", help="list, don't remove")
    ap.add_argument(
        "--install",
        action="store_true",
        help="install this script and a user timer that runs it",
    )
    args = ap.parse_args(argv)
    if args.install:
        install(Path.home(), args.max_age_hours)
        print(f"installed and enabled {UNIT}.timer", file=out)
        return 0
    now = time.time() if now is None else now
    for root in args.root or [default_root()]:
        try:
            total = sum(
                1
                for d in root.iterdir()
                if d.name.startswith("pytest-") and not d.is_symlink() and d.is_dir()
            )
        except OSError:
            total = 0
        stale = find_stale(root, args.max_age_hours * 3600, now=now)
        removed = 0
        for d in stale:
            if args.dry_run:
                age = age_of(d, now)
                why = (
                    "mtime in the future"
                    if math.isinf(age)
                    else f"{age / 3600:.1f}h old"
                )
                print(f"would remove {d} ({why})", file=out)
                continue
            remove(d)
            if not d.exists():
                removed += 1
            else:
                print(f"could not remove {d}", file=out)
        tail = " (dry run)" if args.dry_run else ""
        print(
            f"{root}: {len(stale)} stale of {total}, {removed} removed{tail}", file=out
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
