#!/usr/bin/env python3
"""Self-tests for the machine budget shared by task rooms and gates (AGAST #1811).

The gate's wall time doubled in a week because task rooms built and tested
unthrottled next to it on the same 12-core / 15 GB WSL VM. Decision (option b):
rooms run deprioritised (CPUWeight=20) under a memory cap, the gate runs at
CPUWeight=100 in its own slice. These tests hold the two scripts to that:

  * .claude/host-budget.sh writes the slices and a per-room drop-in, is
    idempotent, reloads systemd only when something changed, and can verify
    and remove what it wrote
  * the memory figures it installs fit 2 rooms + 1 gate in the VM with headroom
  * .claude/skills/rz-iterate/run-gate.sh starts the gate in ritz-gate.slice
    at CPUWeight=100, not in app.slice next to the rooms' parent

Nothing here touches the real systemd: `systemctl` and `systemd-run` are fakes
on PATH that record their arguments, and units are written to a temp dir.

Run with:
    python3 -m pytest projects/ritz/tools/test_host_budget.py -q
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BUDGET = REPO / ".claude" / "host-budget.sh"
RUN_GATE = REPO / ".claude" / "skills" / "rz-iterate" / "run-gate.sh"

ROOM = "ritz-task-4242"
GIB = 1024**3

# The VM (`free -b`: 16717213696 bytes RAM). The budget must leave this much
# for everything that is not a ritz room or the gate: the other ~10 Adele
# agents, the rz coordinator, the page cache and the WSL kernel.
VM_RAM = 16717213696
HEADROOM = 4 * GIB


def _fake_bin(tmp_path: Path) -> Path:
    """systemctl / systemd-run fakes that append their argv to calls.log."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    for name in ("systemctl", "systemd-run"):
        script = bin_dir / name
        # `systemctl --user is-active` must say "not running" for run-gate.sh.
        script.write_text(
            "#!/bin/sh\n"
            f'echo "{name} $*" >> "{log}"\n'
            'case "$*" in *is-active*) exit 3;; esac\n'
            "exit 0\n"
        )
        script.chmod(0o755)
    return bin_dir


def _env(tmp_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = f"{_fake_bin(tmp_path)}:{env['PATH']}"
    env["RZ_SYSTEMD_USER_DIR"] = str(tmp_path / "units")
    return env


def _budget(tmp_path: Path, env: dict[str, str], *args: str):
    return subprocess.run(
        ["bash", str(BUDGET), *args],
        env=env,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )


def _calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "calls.log"
    return log.read_text().splitlines() if log.exists() else []


def _props(path: Path) -> dict[str, str]:
    """key=value pairs of a unit file (last wins, like systemd)."""
    out = {}
    for line in path.read_text().splitlines():
        m = re.match(r"^([A-Za-z]+)=(.*)$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def _bytes(value: str) -> int:
    m = re.fullmatch(r"(\d+)([KMG]?)", value)
    assert m, f"unexpected size {value!r}"
    return int(m.group(1)) * {"": 1, "K": 1024, "M": 1024**2, "G": GIB}[m.group(2)]


def _paths(tmp_path: Path, room: str = ROOM):
    units = tmp_path / "units"
    return (
        units / "ritz-rooms.slice",
        units / "ritz-gate.slice",
        units / f"adele-agent@{room}.service.d" / "50-ritz-host-budget.conf",
    )


# --------------------------------------------------------------------------
# host-budget.sh
# --------------------------------------------------------------------------


@pytest.mark.unit
def test_install_writes_slices_and_room_dropin(tmp_path):
    env = _env(tmp_path)
    r = _budget(tmp_path, env, ROOM)
    assert r.returncode == 0, r.stderr
    rooms, gate, dropin = _paths(tmp_path)

    rp = _props(rooms)
    assert rp["CPUWeight"] == "20"
    assert "MemoryMax" in rp and "MemoryHigh" in rp

    assert _props(gate)["CPUWeight"] == "100"

    dp = _props(dropin)
    assert dp["Slice"] == "ritz-rooms.slice"
    assert "MemoryMax" in dp and "MemoryHigh" in dp
    # systemd's default OOMPolicy=stop would kill the whole room (agent and
    # all) when the kernel OOM-kills one runaway compiler inside the cap.
    assert dp["OOMPolicy"] == "continue"


@pytest.mark.unit
def test_install_reloads_systemd(tmp_path):
    env = _env(tmp_path)
    assert _budget(tmp_path, env, ROOM).returncode == 0
    assert "systemctl --user daemon-reload" in _calls(tmp_path)


@pytest.mark.unit
def test_install_is_idempotent(tmp_path):
    env = _env(tmp_path)
    assert _budget(tmp_path, env, ROOM).returncode == 0
    before = {p: p.read_text() for p in _paths(tmp_path)}
    (tmp_path / "calls.log").unlink()

    r = _budget(tmp_path, env, ROOM)
    assert r.returncode == 0, r.stderr
    assert {p: p.read_text() for p in _paths(tmp_path)} == before
    # Nothing changed, so nothing to reload.
    assert "systemctl --user daemon-reload" not in _calls(tmp_path)


@pytest.mark.unit
def test_install_repairs_a_stale_dropin(tmp_path):
    env = _env(tmp_path)
    assert _budget(tmp_path, env, ROOM).returncode == 0
    dropin = _paths(tmp_path)[2]
    good = dropin.read_text()
    dropin.write_text("[Service]\nCPUWeight=100\n")
    (tmp_path / "calls.log").unlink()

    assert _budget(tmp_path, env, ROOM).returncode == 0
    assert dropin.read_text() == good
    assert "systemctl --user daemon-reload" in _calls(tmp_path)


@pytest.mark.unit
def test_verify(tmp_path):
    env = _env(tmp_path)
    assert _budget(tmp_path, env, "--verify", ROOM).returncode != 0
    assert _budget(tmp_path, env, ROOM).returncode == 0
    r = _budget(tmp_path, env, "--verify", ROOM)
    assert r.returncode == 0, r.stderr
    # --verify writes nothing and reloads nothing.
    assert _calls(tmp_path).count("systemctl --user daemon-reload") == 1


@pytest.mark.unit
def test_verify_rejects_a_stale_dropin(tmp_path):
    env = _env(tmp_path)
    assert _budget(tmp_path, env, ROOM).returncode == 0
    _paths(tmp_path)[2].write_text("[Service]\n")
    assert _budget(tmp_path, env, "--verify", ROOM).returncode != 0


@pytest.mark.unit
def test_remove_drops_only_the_room(tmp_path):
    env = _env(tmp_path)
    assert _budget(tmp_path, env, ROOM).returncode == 0
    assert _budget(tmp_path, env, "ritz-task-7").returncode == 0
    r = _budget(tmp_path, env, "--remove", ROOM)
    assert r.returncode == 0, r.stderr

    rooms, gate, dropin = _paths(tmp_path)
    assert not dropin.exists() and not dropin.parent.exists()
    assert rooms.exists() and gate.exists()
    assert _paths(tmp_path, "ritz-task-7")[2].exists()
    # Removing twice (reap retried) is fine.
    assert _budget(tmp_path, env, "--remove", ROOM).returncode == 0


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["", "../etc", "a/b", "x@y", "-rf", "a b"])
def test_rejects_unsafe_room_names(tmp_path, bad):
    env = _env(tmp_path)
    r = _budget(tmp_path, env, bad)
    assert r.returncode != 0
    assert not (tmp_path / "units").exists() or not any(
        (tmp_path / "units").glob("adele-agent@*")
    )


@pytest.mark.unit
def test_budget_fits_two_rooms_and_a_gate(tmp_path):
    """The installed caps, plus the gate's measured peak, leave headroom."""
    env = _env(tmp_path)
    assert _budget(tmp_path, env, ROOM).returncode == 0
    rooms, _gate, dropin = _paths(tmp_path)
    rp, dp = _props(rooms), _props(dropin)

    room_high, room_max = _bytes(dp["MemoryHigh"]), _bytes(dp["MemoryMax"])
    slice_high, slice_max = _bytes(rp["MemoryHigh"]), _bytes(rp["MemoryMax"])
    assert room_high < room_max
    assert slice_high < slice_max
    # Two rooms at their soft limit fit under the slice's soft limit, so the
    # slice only throttles when both are also over their own.
    assert 2 * room_high <= slice_high
    # One room alone can use its full cap.
    assert room_max <= slice_max

    gate_peak = int(
        re.search(r"^GATE_PEAK_MB=(\d+)", BUDGET.read_text(), re.M).group(1)
    )
    assert gate_peak > 0
    assert slice_max + gate_peak * 1024**2 + HEADROOM <= VM_RAM


# --------------------------------------------------------------------------
# run-gate.sh
# --------------------------------------------------------------------------


@pytest.mark.unit
def test_run_gate_starts_in_the_gate_slice(tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    git = ["git", "-C", str(wt), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], check=True)

    env = _env(tmp_path)
    env["RZ_GATE_DIR"] = str(tmp_path / "gates")
    r = subprocess.run(
        ["bash", str(RUN_GATE), str(wt), "t1811"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr

    runs = [c for c in _calls(tmp_path) if c.startswith("systemd-run ")]
    assert len(runs) == 1, _calls(tmp_path)
    argv = runs[0].split()
    assert "--slice=ritz-gate.slice" in argv
    assert "--property=CPUWeight=100" in argv
