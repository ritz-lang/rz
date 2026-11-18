#!/usr/bin/env python3
"""projects/valet/test/run_all.sh runs every valet shell suite (AGAST #1403).

run_all.sh named 3 (later 4) of valet's test_*.sh suites by hand; the other
eleven ran nowhere or only in main.yml. It now runs every test_*.sh in its
directory except those listed in its EXCLUDED table with a reason, and
`--list` prints what it would run and skip.

A suite wired into run_all.sh is only coverage if it starts the valet under
test ($VALET, not a ./valet symlink that may not exist) and exits non-zero
when that valet is broken. The orphaned suites did neither: three of them
printed responses and always exited 0.

Run with:
    python3 -m pytest projects/ritz/tools/test_valet_run_all.py -q
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TEST_DIR = REPO / "projects/valet/test"
RUN_ALL = TEST_DIR / "run_all.sh"

# The suites that ran nowhere before #1403 (main.yml gates the others).
ORPHANED = [
    "test_dirlist.sh",
    "test_etag.sh",
    "test_range.sh",
    "test_middleware.sh",
    "test_json_builder.sh",
]

# A valet that records it was started and never listens.
STUB = """#!/bin/sh
echo started >> "$STUB_LOG"
exit 1
"""


def _list() -> tuple[set[str], dict[str, str]]:
    r = subprocess.run(
        ["bash", str(RUN_ALL), "--list"], capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0, r.stdout + r.stderr
    run: set[str] = set()
    skip: dict[str, str] = {}
    for line in r.stdout.splitlines():
        kind, _, rest = line.partition(" ")
        name, _, reason = rest.partition(" ")
        if kind == "run":
            run.add(name)
        elif kind == "skip":
            skip[name] = reason.strip()
        else:
            pytest.fail(f"unexpected --list line: {line!r}")
    return run, skip


def test_list_covers_every_suite_and_explains_each_skip():
    run, skip = _list()
    on_disk = {p.name for p in TEST_DIR.glob("test_*.sh")}
    assert run | set(skip) == on_disk
    assert not run & set(skip)
    assert all(skip.values()), f"a skipped suite has no reason: {skip}"
    for name in ORPHANED:
        assert name in run, f"{name} is still not run by run_all.sh"


def _fake_dir(tmp_path: Path, suites: dict[str, int]) -> tuple[Path, Path]:
    """A copy of run_all.sh beside fake suites that log their name and exit."""
    d = tmp_path / "test"
    d.mkdir()
    shutil.copy(RUN_ALL, d / "run_all.sh")
    shutil.copy(TEST_DIR / "lib_ports.sh", d / "lib_ports.sh")
    ran = tmp_path / "ran.log"
    for name, rc in suites.items():
        (d / name).write_text(f'#!/bin/bash\necho {name} >> "{ran}"\nexit {rc}\n')
    valet = tmp_path / "valet"
    valet.write_text("#!/bin/sh\nexit 0\n")
    valet.chmod(0o755)
    return d, valet


def _run_fake(tmp_path, suites):
    d, valet = _fake_dir(tmp_path, suites)
    r = subprocess.run(
        ["bash", str(d / "run_all.sh")],
        env=dict(os.environ, VALET=str(valet)),
        capture_output=True,
        text=True,
        timeout=30,
    )
    ran_log = tmp_path / "ran.log"
    ran = ran_log.read_text().split() if ran_log.exists() else []
    return r, ran


def test_runner_runs_every_discovered_suite_past_a_failure(tmp_path):
    """The first suite passing must not abort the run (`((PASSED++))` under
    set -e did), nor a failing one; the exit status is the verdict."""
    r, ran = _run_fake(
        tmp_path, {"test_a.sh": 0, "test_b.sh": 1, "test_c.sh": 0}
    )
    out = r.stdout + r.stderr
    assert sorted(ran) == ["test_a.sh", "test_b.sh", "test_c.sh"], out
    assert r.returncode == 1, out
    assert "Passed: \x1b[0;32m2" in out and "Failed: \x1b[0;31m1" in out, out


def test_runner_exits_0_when_every_suite_passes(tmp_path):
    r, ran = _run_fake(tmp_path, {"test_a.sh": 0, "test_b.sh": 0})
    assert sorted(ran) == ["test_a.sh", "test_b.sh"]
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("script", ORPHANED)
def test_orphaned_suite_fails_against_a_broken_valet(script, tmp_path):
    """Each suite starts $VALET (the stub logs it) and exits 1 when it never
    answers, rather than printing the failure and exiting 0."""
    stub = tmp_path / "stub"
    stub.write_text(STUB)
    stub.chmod(0o755)
    log = tmp_path / "stub.log"
    r = subprocess.run(
        ["bash", str(TEST_DIR / script)],
        env=dict(os.environ, VALET=str(stub), STUB_LOG=str(log)),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    out = r.stdout + r.stderr
    assert log.exists(), f"{script} did not start $VALET:\n{out}"
    assert r.returncode == 1, out
