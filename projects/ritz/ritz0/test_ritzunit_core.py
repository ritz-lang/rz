"""AGAST #2072: a crashing test child does not dump core unless `--core`.

The kernel runs the core handler before the runner sees SIGSEGV. With a piped
core_pattern (apport, systemd-coredump) the dump can outlast a test's `-t`
deadline; the runner's SIGKILL then interrupts it and the crash reads as a
timeout. ritzunit's child therefore sets PR_SET_DUMPABLE 0 and RLIMIT_CORE 0
before running the test. `--core` keeps the runner's own settings, for
debugging a crash from its core file.

The probe tests report their child's state in their exit code, so they hold
on any core_pattern. The core-file tests need a plain (non-pipe) pattern.
"""

import json
import resource
import subprocess
import sys
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(RITZ0_DIR))

import test_ritzunit_harness as harness

package = harness.package
_binary = harness._binary

pytestmark = pytest.mark.integration

# Each probe fails with an exit code that names what its child saw:
#   probe_dumpable:   10 + prctl(PR_GET_DUMPABLE)
#   probe_core_limit: 20 if RLIMIT_CORE's soft limit is 0, else 21
PROBES = """\
import ritzlib.sys

[[test]]
fn probe_dumpable() -> i32
    10 + syscall2(157, 3, 0) as i32

[[test]]
fn probe_core_limit() -> i32
    var lim: [2]i64
    lim[0] = -1
    syscall2(97, 4, @lim[0] as i64)
    if lim[0] == 0
        return 20
    21
"""

CRASHER = """\
[[test]]
fn crashes() -> i32
    # A load from address 0 the optimiser cannot see (AGAST #1917).
    asm x86_64:
        movl 0, %eax
    0
"""


def _core_pattern() -> str:
    try:
        return Path("/proc/sys/kernel/core_pattern").read_text().strip()
    except OSError:
        return ""


def _allow_cores():
    """preexec_fn: raise RLIMIT_CORE's soft limit to its hard limit."""
    _soft, hard = resource.getrlimit(resource.RLIMIT_CORE)
    resource.setrlimit(resource.RLIMIT_CORE, (hard, hard))


def _cores_possible() -> bool:
    _soft, hard = resource.getrlimit(resource.RLIMIT_CORE)
    return hard != 0


def _run(exe: str, cwd: Path, *args: str) -> dict:
    proc = subprocess.run([exe, "--json", *args], check=False, capture_output=True, timeout=60,
                          cwd=cwd, preexec_fn=_allow_cores)
    return json.loads(proc.stdout)


def _exit_codes(report: dict) -> dict:
    return {t["name"]: t["exit_code"] for t in report["tests"]}


@pytest.mark.skipif(not _cores_possible(), reason="hard RLIMIT_CORE is 0")
@pytest.mark.parametrize("jobs", ["1", "2"])
@pytest.mark.parametrize("probe,expected", [("probe_dumpable", 10), ("probe_core_limit", 20)])
def test_child_disables_core(package, tmp_path, jobs, probe, expected):
    """PR_SET_DUMPABLE 0 (probe_dumpable) and RLIMIT_CORE 0 (probe_core_limit)."""
    exe = _binary(package(PROBES), tmp_path)
    assert _exit_codes(_run(exe, tmp_path, "-j", jobs, "-f", probe)) == {probe: expected}


@pytest.mark.skipif(not _cores_possible(), reason="hard RLIMIT_CORE is 0")
def test_core_flag_keeps_the_runners_settings(package, tmp_path):
    exe = _binary(package(PROBES), tmp_path)
    codes = _exit_codes(_run(exe, tmp_path, "--core"))
    assert codes == {"probe_dumpable": 11, "probe_core_limit": 21}


def test_crash_under_a_short_timeout_is_a_crash(package, tmp_path):
    exe = _binary(package(CRASHER), tmp_path)
    report = _run(exe, tmp_path, "-t", "300")
    (test,) = report["tests"]
    assert test["status"] == "crash", report
    assert test["signal"] == 11, report


def _crash_in(exe: str, cwd: Path, *args: str) -> list:
    """Run the crasher in an empty `cwd`; the core files it left there."""
    cwd.mkdir()
    report = _run(exe, cwd, *args)
    assert report["tests"][0]["status"] == "crash", report
    return sorted(p.name for p in cwd.iterdir() if p.name.startswith("core"))


cores_land_in_cwd = pytest.mark.skipif(
    _core_pattern().startswith("|") or "/" in _core_pattern() or not _cores_possible(),
    reason="core_pattern is a pipe or a path, or cores are disabled")


@cores_land_in_cwd
def test_crash_leaves_no_core_file(package, tmp_path):
    exe = _binary(package(CRASHER), tmp_path)
    assert _crash_in(exe, tmp_path / "run") == []


@cores_land_in_cwd
def test_core_flag_dumps_core(package, tmp_path):
    exe = _binary(package(CRASHER), tmp_path)
    assert _crash_in(exe, tmp_path / "run", "--core") != []
