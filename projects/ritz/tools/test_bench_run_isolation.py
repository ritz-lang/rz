"""bench/run.sh must not collide with another room's run on one host (AGAST #3201).

Up to eight rooms share a host, each with its own worktree.  Before #3201,
bench/run.sh

  * bound fixed ports 9001-9004 and 7777, so two rooms benching at once
    fought over them (and SO_REUSEPORT let one serve the other's requests);
  * aborted in its orphan guard whenever ANY worktree ran a
    valet/nexus/zeus/mausoleum binary (e.g. mausoleum's concurrent_test.sh);
  * ran `pkill -9 -f 'projects/(valet|...)/build/'` on exit, killing every
    room's servers.

The rules checked here:

  * ports default to free ones the kernel hands out, and BENCH_PORT_* env
    vars override them;
  * the orphan guard only counts processes whose executable lives under THIS
    worktree's projects/<server>/build/;
  * cleanup kills only the PIDs the run recorded, plus their descendants
    (zeus's nexus workers), and nothing chosen by a name pattern.

None of this needs wrk or a built server: `--dry-run` reports the ports, the
guard's verdict and what cleanup would kill, and starts nothing.  The tests
only ever signal processes they started themselves.
"""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUN_SH = REPO / "bench" / "run.sh"
SOCK_DIR_REL = Path("projects/ritz/tools/sock_dir.sh")  # run.sh sources it
SERVERS = ("valet", "nexus", "zeus", "mausoleum")
LOOP = "for _ in $(seq 300); do sleep 1; done"
PORT_VARS = (
    "PORT_DIRECT",
    "PORT_STATIC",
    "PORT_PROXY",
    "PORT_PROXY_DB",
    "PORT_MAUSOLEUM",
)


def _env(**extra):
    env = {k: v for k, v in os.environ.items() if not k.startswith("BENCH_PORT_")}
    env.update(extra)
    return env


def _run(script: Path, *args, **env):
    return subprocess.run(
        ["bash", str(script), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=_env(**env),
    )


def _ports(out: str) -> dict:
    """Parse the `[bench] dry-run: port NAME=N` lines."""
    return {m[1]: int(m[2]) for m in re.finditer(r"port (\w+)=(\d+)", out)}


def _would_kill(out: str) -> list:
    m = re.search(r"cleanup would kill:([ \d]*)$", out, re.MULTILINE)
    assert m, out
    return [int(p) for p in m[1].split()]


def _listed_pids(out: str) -> set:
    """Every pid run.sh names: the ABORT `(pids: ...)` list and the dry-run
    `cleanup would kill:` list, parsed as whole numbers.

    Never test `str(pid) in stderr`: stderr also carries 5-digit ports, so a
    4-digit pid substring-matches a port it has nothing to do with (#3736).
    """
    pids = set()
    for m in re.finditer(
        r"\(pids:([ \d]*)\)|cleanup would kill:([ \d]*)$", out, re.MULTILINE
    ):
        pids.update(int(p) for p in (m[1] or m[2] or "").split())
    return pids


@pytest.fixture
def worktrees(tmp_path):
    """Two fake worktrees, each with its own copy of bench/run.sh and the
    sock_dir.sh it sources (#4282)."""
    roots = []
    for name in ("room_a", "room_b"):
        root = tmp_path / name
        (root / "bench").mkdir(parents=True)
        shutil.copy(RUN_SH, root / "bench" / "run.sh")
        (root / SOCK_DIR_REL).parent.mkdir(parents=True)
        shutil.copy(REPO / SOCK_DIR_REL, root / SOCK_DIR_REL)
        roots.append(root)
    return roots


@pytest.fixture
def decoy(tmp_path):
    """Start a fake server binary in a worktree, the way another room would.

    The "binary" is a copy of bash at projects/<server>/build/debug/<server>
    (not sleep: on some hosts sleep is a multicall binary that dispatches on
    argv[0]), run by its relative path from the worktree, which is exactly
    what the old name regex matched.  A loop keeps bash from exec'ing away.
    Only processes started here are ever killed.
    """
    started = []

    def start(root: Path, server: str = "valet"):
        bin_dir = root / "projects" / server / "build" / "debug"
        bin_dir.mkdir(parents=True, exist_ok=True)
        binary = bin_dir / server
        shutil.copy(shutil.which("bash"), binary)
        proc = subprocess.Popen(
            [f"projects/{server}/build/debug/{server}", "-c", LOOP], cwd=root
        )
        started.append(proc)
        # Wait until the exec has happened, so /proc/PID/exe is the copy.
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                if os.readlink(f"/proc/{proc.pid}/exe").startswith(str(root)):
                    break
            except OSError:
                pass
            time.sleep(0.02)
        return proc

    yield start
    for proc in started:
        proc.kill()
        proc.wait()


# ── syntax and arguments ────────────────────────────────────────────────


@pytest.mark.integration
def test_script_parses():
    subprocess.run(["bash", "-n", str(RUN_SH)], check=True)


@pytest.mark.integration
def test_help_documents_port_overrides_and_dry_run():
    r = _run(RUN_SH, "--help")
    assert r.returncode == 0, r.stderr
    assert "--dry-run" in r.stdout
    assert "BENCH_PORT_" in r.stdout


@pytest.mark.integration
def test_bad_argument_exits_2():
    r = _run(RUN_SH, "--no-such-flag")
    assert r.returncode == 2
    assert "unknown arg" in r.stderr


@pytest.mark.integration
def test_non_numeric_port_override_is_rejected():
    r = _run(RUN_SH, "--dry-run", BENCH_PORT_DIRECT="ninety")
    assert r.returncode == 2
    assert "BENCH_PORT_DIRECT" in r.stderr


# ── ports ───────────────────────────────────────────────────────────────


def _ephemeral_range() -> range:
    """The kernel's ephemeral port range, where a bind to port 0 lands."""
    lo, hi = Path("/proc/sys/net/ipv4/ip_local_port_range").read_text().split()
    return range(int(lo), int(hi) + 1)


@pytest.mark.integration
def test_default_ports_are_kernel_picked_distinct_and_not_the_old_fixed_set():
    r = _run(RUN_SH, "--dry-run")
    assert r.returncode == 0, r.stderr
    ports = _ports(r.stderr)
    assert sorted(ports) == sorted(PORT_VARS), r.stderr
    assert len(set(ports.values())) == len(PORT_VARS)
    assert not set(ports.values()) & {9001, 9002, 9003, 9004, 7777}
    # Kernel-picked means inside the ephemeral range.  Never re-bind them to
    # check they are "still free": that is a TOCTOU race any other process
    # (another xdist worker, another room) can win between the pick and the
    # bind, failing with EADDRINUSE on unrelated commits (#4124).
    ephemeral = _ephemeral_range()
    assert all(p in ephemeral for p in ports.values()), (ports, ephemeral)


@pytest.mark.integration
def test_port_overrides_are_honoured():
    want = {v: 20101 + i for i, v in enumerate(PORT_VARS)}
    r = _run(
        RUN_SH, "--dry-run", **{f"BENCH_PORT_{k[5:]}": str(p) for k, p in want.items()}
    )
    assert r.returncode == 0, r.stderr
    assert _ports(r.stderr) == want


# ── orphan guard ────────────────────────────────────────────────────────


def test_listed_pids_reads_only_pid_lists_not_substrings():
    """A pid is "listed" only as a whole number in a pid list (AGAST #3736).

    CI pids are often 4 digits, and the dry-run stderr also prints 5-digit
    ephemeral ports: pid 3887 is a substring of port 38871 but is not
    listed.  A bare `str(pid) in stderr` mistook one for the other.
    """
    quiet = (
        "[bench] dry-run: port PORT_DIRECT=38871\n"
        "[bench] dry-run: no orphaned bench binaries under x/build\n"
        "[bench] dry-run: cleanup would kill: 13887\n"
    )
    assert 3887 not in _listed_pids(quiet)
    assert _listed_pids(quiet) == {13887}
    abort = (
        "[bench] ABORT: this worktree's bench binaries still running "
        "(pids: 38870 3887)\n"
        "[bench]        check they are yours, then:  kill -9 38870 3887\n"
    )
    assert _listed_pids(abort) == {38870, 3887}


@pytest.mark.integration
@pytest.mark.parametrize("server", SERVERS)
def test_guard_ignores_another_worktrees_server(worktrees, decoy, server):
    room_a, room_b = worktrees
    other = decoy(room_b, server)
    r = _run(room_a / "bench" / "run.sh", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert other.pid not in _listed_pids(r.stderr), r.stderr
    assert other.poll() is None


@pytest.mark.integration
def test_guard_still_aborts_on_this_worktrees_own_orphan(worktrees, decoy):
    room_a, _ = worktrees
    mine = decoy(room_a, "zeus")
    r = _run(room_a / "bench" / "run.sh", "--dry-run")
    assert r.returncode == 1, r.stderr
    assert "ABORT" in r.stderr and mine.pid in _listed_pids(r.stderr), r.stderr
    assert mine.poll() is None  # reported, never killed


# ── cleanup ─────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_cleanup_would_kill_nothing_it_did_not_start(worktrees, decoy):
    room_a, room_b = worktrees
    other = decoy(room_b, "valet")
    r = _run(room_a / "bench" / "run.sh", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert _would_kill(r.stderr) == []
    assert other.poll() is None


def test_cleanup_has_no_name_pattern_kill():
    code = "\n".join(line.split("#", 1)[0] for line in RUN_SH.read_text().splitlines())
    assert not re.search(r"\b(pkill|killall)\b", code)


@pytest.mark.integration
def test_pid_tree_covers_recorded_pid_and_descendants_only(decoy, worktrees):
    """pid_tree (what cleanup kills) is the recorded PID's whole subtree."""
    other = decoy(worktrees[1], "valet")
    text = RUN_SH.read_text()
    m = re.search(r"^pid_tree\(\) \{.*?^\}", text, re.DOTALL | re.MULTILINE)
    assert m, "bench/run.sh defines pid_tree()"
    parent = subprocess.Popen(["bash", "-c", "sleep 300 & sleep 300 & wait"])
    kids = []
    try:
        deadline = time.time() + 5
        while time.time() < deadline and len(kids) < 2:
            kids = subprocess.run(
                ["pgrep", "-P", str(parent.pid)],
                check=False,
                capture_output=True,
                text=True,
            ).stdout.split()
            time.sleep(0.02)
        r = subprocess.run(
            ["bash", "-c", m[0] + f"\npid_tree {parent.pid}"],
            capture_output=True,
            text=True,
            check=True,
        )
        got = {int(p) for p in r.stdout.split()}
        assert got == {parent.pid, *map(int, kids)}
        assert other.pid not in got
    finally:
        # Only the two sleeps this test started, by PID.
        for kid in kids:
            try:
                os.kill(int(kid), 9)
            except ProcessLookupError:
                pass
        parent.kill()
        parent.wait()
