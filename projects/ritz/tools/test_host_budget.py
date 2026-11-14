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
  * per host (AGAST #2998): ~/.config/rz/host.env (.claude/host-env.sh) sets
    the rooms slice's MemoryHigh/MemoryMax and run-gate.sh's slot count; with
    no file both scripts behave byte for byte as before.  The slot tests run
    real gates (a systemd-run fake that executes the unit) against temp dirs

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
    # Never read the real ~/.config/rz/host.env (huburght has one, AGAST
    # #2998): every test starts as a host with no config file.
    env["RZ_HOST_ENV"] = str(tmp_path / "host.env")
    env.pop("RZ_GATE_SLOTS", None)
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
# per-host config: ~/.config/rz/host.env (AGAST #2998)
# --------------------------------------------------------------------------

# What host-budget.sh wrote before #2998, byte for byte. omegalisk, toffee,
# starbux and chungus have no host.env and must keep getting exactly this.
GOLDEN_ROOMS_SLICE = """\
# Installed by .claude/host-budget.sh (AGAST #1811). Do not edit by hand.
[Unit]
Description=ritz task rooms: deprioritised, memory-capped

[Slice]
CPUWeight=20
MemoryHigh=7G
MemoryMax=8G
"""
GOLDEN_GATE_SLICE = """\
# Installed by .claude/host-budget.sh (AGAST #1811). Do not edit by hand.
[Unit]
Description=ritz verification gate (run-gate.sh): full CPU weight, no memory cap

[Slice]
CPUWeight=100
"""
GOLDEN_DROPIN = f"""\
# Installed by .claude/host-budget.sh (AGAST #1811). Do not edit by hand.
# Removed on reap with: .claude/host-budget.sh --remove {ROOM}
[Service]
Slice=ritz-rooms.slice
MemoryHigh=3500M
MemoryMax=5G
OOMPolicy=continue
"""

# huburght: 6 rooms on 47 GiB (rz-iterate SKILL.md "Hosts").
HUBURGHT_ENV = """\
# rz per-host budget (AGAST #2998)
RZ_ROOMS_MEMORY_HIGH=28G
RZ_ROOMS_MEMORY_MAX=32G

RZ_GATE_SLOTS=2
"""


def _host_env(tmp_path: Path, text: str) -> None:
    (tmp_path / "host.env").write_text(text)


@pytest.mark.unit
def test_no_config_writes_todays_files_byte_for_byte(tmp_path):
    env = _env(tmp_path)
    assert not Path(env["RZ_HOST_ENV"]).exists()
    r = _budget(tmp_path, env, ROOM)
    assert r.returncode == 0, r.stderr
    rooms, gate, dropin = _paths(tmp_path)
    assert rooms.read_bytes() == GOLDEN_ROOMS_SLICE.encode()
    assert gate.read_bytes() == GOLDEN_GATE_SLICE.encode()
    assert dropin.read_bytes() == GOLDEN_DROPIN.encode()


@pytest.mark.unit
def test_config_sets_the_rooms_slice_memory(tmp_path):
    env = _env(tmp_path)
    _host_env(tmp_path, HUBURGHT_ENV)
    r = _budget(tmp_path, env, ROOM)
    assert r.returncode == 0, r.stderr
    rooms, gate, dropin = _paths(tmp_path)
    assert rooms.read_text() == GOLDEN_ROOMS_SLICE.replace(
        "MemoryHigh=7G\nMemoryMax=8G", "MemoryHigh=28G\nMemoryMax=32G"
    )
    # Per-room caps and the gate slice are not per-host.
    assert gate.read_text() == GOLDEN_GATE_SLICE
    assert dropin.read_text() == GOLDEN_DROPIN


@pytest.mark.unit
def test_config_with_one_key_keeps_the_other_default(tmp_path):
    env = _env(tmp_path)
    _host_env(tmp_path, "RZ_ROOMS_MEMORY_MAX=12G\n")
    assert _budget(tmp_path, env, ROOM).returncode == 0
    rp = _props(_paths(tmp_path)[0])
    assert (rp["MemoryHigh"], rp["MemoryMax"]) == ("7G", "12G")


@pytest.mark.unit
def test_verify_reports_the_values_in_effect(tmp_path):
    env = _env(tmp_path)
    assert _budget(tmp_path, env, ROOM).returncode == 0
    r = _budget(tmp_path, env, "--verify", ROOM)
    assert r.returncode == 0, r.stderr
    assert "MemoryHigh=7G MemoryMax=8G" in r.stdout
    assert "gate slots=1" in r.stdout
    assert "no host config" in r.stdout

    _host_env(tmp_path, HUBURGHT_ENV)
    # The installed slice is now stale against the host's config.
    r = _budget(tmp_path, env, "--verify", ROOM)
    assert r.returncode != 0
    assert "ritz-rooms.slice" in r.stderr

    assert _budget(tmp_path, env, ROOM).returncode == 0
    r = _budget(tmp_path, env, "--verify", ROOM)
    assert r.returncode == 0, r.stderr
    assert "MemoryHigh=28G MemoryMax=32G" in r.stdout
    assert "gate slots=2" in r.stdout
    assert env["RZ_HOST_ENV"] in r.stdout


@pytest.mark.unit
@pytest.mark.parametrize(
    "text",
    [
        "RZ_ROOMS_MEMORY_MAX=lots\n",  # not a size
        "RZ_ROOMS_MEMORY_MAX=$(touch pwned)\n",  # parsed, never sourced
        "RZ_ROOM_MEMORY_MAX=32G\n",  # typo'd key: an error, not ignored
        "RZ_ROOMS_MEMORY_HIGH=40G\nRZ_ROOMS_MEMORY_MAX=32G\n",  # high > max
        "RZ_ROOMS_MEMORY_HIGH=9G\n",  # high > default max 8G
        "RZ_GATE_SLOTS=0\n",
    ],
)
def test_bad_config_is_refused_and_writes_nothing(tmp_path, text):
    env = _env(tmp_path)
    _host_env(tmp_path, text)
    r = _budget(tmp_path, env, ROOM)
    assert r.returncode != 0
    assert "host.env" in r.stderr
    assert not (tmp_path / "units").exists()
    assert not (tmp_path / "pwned").exists()
    assert _budget(tmp_path, env, "--verify", ROOM).returncode != 0


@pytest.mark.unit
def test_remove_works_despite_a_bad_config(tmp_path):
    """Reaping a room must not depend on the host's config parsing."""
    env = _env(tmp_path)
    assert _budget(tmp_path, env, ROOM).returncode == 0
    _host_env(tmp_path, "RZ_GATE_SLOTS=many\n")
    r = _budget(tmp_path, env, "--remove", ROOM)
    assert r.returncode == 0, r.stderr
    assert not _paths(tmp_path)[2].exists()


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


def _git_worktree(tmp_path: Path) -> Path:
    wt = tmp_path / "wt"
    wt.mkdir()
    git = ["git", "-C", str(wt), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    return wt


# A systemd-run that really starts the unit's command (detached, in its own
# session), so the slot locks inside run-gate.sh are exercised for real.
_RUNNING_SYSTEMD_RUN = """\
#!/usr/bin/env python3
import os, subprocess, sys
args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write("systemd-run " + " ".join(args) + "\\n")
env, cwd, i = dict(os.environ), None, 0
while args[i].startswith("--"):
    a = args[i]
    if a.startswith("--setenv="):
        k, v = a[len("--setenv="):].split("=", 1)
        env[k] = v
    elif a.startswith("--working-directory="):
        cwd = a.split("=", 1)[1]
    i += 1
p = subprocess.Popen(args[i:], cwd=cwd, env=env, start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
with open(os.environ["FAKE_PIDS"], "a") as f:
    f.write(f"{p.pid}\\n")
"""


def _start_gates(tmp_path: Path, env: dict[str, str], n: int) -> list[Path]:
    """Start n gates whose command blocks until tmp_path/release exists."""
    wt = _git_worktree(tmp_path)
    fake = tmp_path / "bin" / "systemd-run"
    fake.write_text(_RUNNING_SYSTEMD_RUN)
    env["FAKE_LOG"] = str(tmp_path / "calls.log")
    env["FAKE_PIDS"] = str(tmp_path / "pids")
    env["RZ_GATE_DIR"] = str(tmp_path / "gates")
    release = tmp_path / "release"
    env["RZ_GATE_CMD"] = f'while [ ! -e "{release}" ]; do sleep 0.1; done'
    logs = []
    for k in range(n):
        r = subprocess.run(
            ["bash", str(RUN_GATE), str(wt), f"t2998-{k}"],
            env=env,
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr
        logs.append(Path(r.stdout.strip()))
    return logs


def _running(logs: list[Path], want: int) -> int:
    """Gates holding a slot, once the count has settled (or reached want+1)."""
    import time

    # Generous for a loaded gate runner; a passing run returns in ~2 s.
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        n = sum("SLOT=" in p.read_text() for p in logs)
        if n > want:
            return n
        if n == want:
            time.sleep(1.5)  # long enough for an extra gate to slip in
            return sum("SLOT=" in p.read_text() for p in logs)
        time.sleep(0.1)
    return sum("SLOT=" in p.read_text() for p in logs)


def _kill_gates(tmp_path: Path) -> None:
    import signal

    (tmp_path / "release").touch()
    pids = tmp_path / "pids"
    for pid in pids.read_text().split() if pids.exists() else []:
        try:
            os.killpg(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


@pytest.mark.unit
@pytest.mark.parametrize(
    "host_env, env_slots, slots",
    [
        (None, None, 1),  # no config: one gate per host, as before
        (HUBURGHT_ENV, None, 2),  # host.env's RZ_GATE_SLOTS
        (HUBURGHT_ENV, "1", 1),  # an explicit RZ_GATE_SLOTS still wins
    ],
    ids=["default", "host-env", "env-wins"],
)
def test_run_gate_runs_the_configured_number_of_gates(
    tmp_path, host_env, env_slots, slots
):
    env = _env(tmp_path)
    if host_env is not None:
        _host_env(tmp_path, host_env)
    if env_slots is not None:
        env["RZ_GATE_SLOTS"] = env_slots
    try:
        logs = _start_gates(tmp_path, env, slots + 1)
        assert _running(logs, slots) == slots
        waiting = [p for p in logs if "SLOT=" not in p.read_text()]
        assert len(waiting) == 1 and "WAITING" in waiting[0].read_text()
    finally:
        _kill_gates(tmp_path)


@pytest.mark.unit
@pytest.mark.parametrize("text", ["RZ_GATE_SLOTS=0\n", "RZ_GATE_SLOTS=two\n"])
def test_run_gate_refuses_a_bad_config(tmp_path, text):
    wt = _git_worktree(tmp_path)
    env = _env(tmp_path)
    env["RZ_GATE_DIR"] = str(tmp_path / "gates")
    _host_env(tmp_path, text)
    r = subprocess.run(
        ["bash", str(RUN_GATE), str(wt), "t2998"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "host.env" in r.stderr
    assert not any(c.startswith("systemd-run ") for c in _calls(tmp_path))
