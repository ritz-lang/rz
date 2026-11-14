#!/usr/bin/env python3
"""Self-tests for tools/smoke_stack.py, the stack smoke gate (AGAST #2456).

The gate's value is in the properties that would make it say "fine" when the
stack is broken, so those are what these pin, without starting any server:

  * strict xfail: an excused check that passes is XPASS and fails the run;
    a broken precondition is FAIL even under an xfail; an XFAILS entry no
    check ran under is reported, so a rename cannot leave a dead excuse;
  * every xfail cites an AGAST ticket;
  * binaries are chosen by target, not by name: the harland ELFs (ritzutils
    cat.elf, rzsh.elf) are out, rzsh.linux and the servers are in;
  * every process it starts is killed by process group, children included,
    and a CLI that hangs is killed at its timeout.

The live checks themselves run in main.yml's build-all job; their wiring is
pinned by test_ci_e2e.py.

Run with:
    python3 -m pytest projects/ritz/tools/test_smoke_stack.py -q
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import smoke_stack as ss  # noqa: E402


def reporter(xfails: dict[str, str] | None = None) -> ss.Reporter:
    return ss.Reporter(xfails or {}, out=io.StringIO())


# --- strict xfail ------------------------------------------------------------

@pytest.mark.unit
def test_pass_and_fail_without_xfail():
    r = reporter()
    assert r.run("a", lambda: None) == ss.PASS
    assert r.exit_code() == 0

    def bad():
        raise ss.CheckFailed("wrong")
    assert r.run("b", bad) == ss.FAIL
    assert r.exit_code() == 1


@pytest.mark.unit
def test_xfail_that_fails_is_green():
    r = reporter({"a": "#1 known"})

    def bad():
        raise ss.CheckFailed("still broken")
    assert r.run("a", bad) == ss.XFAIL
    assert r.exit_code() == 0
    assert "#1 known" in r.out.getvalue() and "still broken" in r.out.getvalue()


@pytest.mark.unit
def test_xfail_that_passes_fails_the_run():
    r = reporter({"a": "#1 known"})
    assert r.run("a", lambda: None) == ss.XPASS
    assert r.exit_code() == 1


@pytest.mark.unit
def test_broken_precondition_is_never_excused():
    r = reporter({"a": "#1 known"})

    def no_binary():
        raise ss.Broken("missing binary")
    assert r.run("a", no_binary) == ss.FAIL
    assert r.exit_code() == 1


@pytest.mark.unit
def test_harness_crash_is_a_named_fail_even_under_xfail():
    r = reporter({"a": "#1 known"})
    assert r.run("a", lambda: {}["missing"]) == ss.FAIL
    assert "KeyError" in r.results[-1].detail


@pytest.mark.unit
def test_skip_does_not_fail_the_run():
    r = reporter()
    r.skip("a", "port taken")
    assert r.exit_code() == 0


@pytest.mark.unit
def test_unused_xfail_is_reported_only_for_suites_that_ran():
    r = reporter({"tome.uring.ping": "#1", "valet.gone": "#2", "help:x/y": "#3"})
    r.run("tome.uring.ping", lambda: (_ for _ in ()).throw(ss.CheckFailed("x")))
    assert r.unused_xfails({"tome", "valet"}) == ["valet.gone"]
    assert r.unused_xfails({"tome", "help"}) == ["help:x/y"]
    assert r.unused_xfails({"tome"}) == []


@pytest.mark.unit
def test_every_xfail_cites_a_ticket():
    for check, reason in ss.XFAILS.items():
        assert re.match(r"#\d{3,}\b", reason), f"{check}: {reason!r} cites no AGAST ticket"


@pytest.mark.unit
def test_every_xfail_belongs_to_a_suite():
    for check in ss.XFAILS:
        assert ss._suite_of(check) in ss.SUITES, check


@pytest.mark.unit
def test_child_tickets_each_have_a_check():
    """#2456's acceptance: every child ticket's repro is one of its checks.
    A fixed child drops out of this set in the change that deletes its last
    XFAILS entry (#2457, #2458, #2459, #2460, #2461: their checks are plain
    passing checks now; #2460's one remaining failure, sage running JS, is
    #2787's)."""
    cited = {m for reason in ss.XFAILS.values() for m in re.findall(r"#(\d+)", reason)}
    assert {"2787"} <= cited


# --- binaries by target --------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("target,target_os,linux", [
    ("", "", True),
    ("x86_64-unknown-linux-gnu", "linux", True),
    ("", "linux", True),
    ("x86_64-unknown-none", "harland", False),
    ("x86_64-none-elf", "", False),          # harland kernel: no target_os at all
    ("x86_64-unknown-uefi", "", False),      # bootx64
    ("", "harland", False),
])
def test_targets_linux(target, target_os, linux):
    assert ss.targets_linux(target, target_os) is linux


@pytest.mark.unit
def test_linux_bins_selects_by_target_not_name():
    bins, known = ss.linux_bins()
    ids = {b.check for b in bins}
    assert "help:rzsh/rzsh.linux" in ids
    assert "help:rzsh/rzsh" not in ids              # harland rzsh.elf
    assert not any(c.startswith("help:ritzutils/") for c in ids)  # harland cat.elf
    assert not any(c.startswith(("help:harland/", "help:indium/", "help:prism/")) for c in ids)
    for server in ("valet/valet", "zeus/zeus", "nexus/nexus", "tome/tome-server",
                   "tome/tome-cli", "mausoleum/mausoleum", "mausoleum/wiki-seed"):
        assert f"help:{server}" in ids
    assert all(not str(b.path).endswith(".elf") for b in bins)
    assert set(known) >= {"lexis", "tempest"}


@pytest.mark.unit
def test_help_xfails_name_real_binaries():
    ids = {b.check for b in ss.linux_bins()[0]}
    stale = [c for c in ss.XFAILS if c.startswith("help:") and c not in ids]
    assert not stale, f"help xfails for binaries that are not Linux [[bin]]s: {stale}"


# --- the stack's own store (AGAST #3065) ---------------------------------------

@pytest.mark.unit
def test_start_adds_env_to_the_inherited_environment(tmp_path, monkeypatch):
    # zeus gets MAUSOLEUM_PORT this way and passes it on to nexus.
    monkeypatch.setenv("SMOKE_INHERITED", "kept")
    procs = ss.Procs(tmp_path)
    p = procs.start("env", ["sh", "-c", 'echo "$SMOKE_INHERITED $SMOKE_ADDED"'], tmp_path,
                    env={"SMOKE_ADDED": "added"})
    p.wait(timeout=5)
    assert Path(p.log).read_text().strip() == "kept added"


@pytest.mark.unit
def test_every_zeus_the_stack_starts_gets_the_store_env():
    # A zeus started without it runs nexus workers that dial 127.0.0.1:7777,
    # i.e. some other stack's mausoleum (zeus_alone did, #3065).
    import ast
    tree = ast.parse(Path(ss.__file__).read_text())
    zeus_starts = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "start"
        and len(n.args) >= 2 and isinstance(n.args[1], ast.List)
        and any(isinstance(e, ast.Call) and ast.unparse(e) == "str(zeus)" for e in n.args[1].elts)
    ]
    assert len(zeus_starts) >= 2
    missing = [n.lineno for n in zeus_starts if not any(k.arg == "env" for k in n.keywords)]
    assert not missing, f"zeus started without env= at smoke_stack.py lines {missing}"


# --- process hygiene -----------------------------------------------------------

@pytest.mark.unit
def test_stop_kills_the_whole_group(tmp_path):
    procs = ss.Procs(tmp_path)
    # A parent that ignores SIGTERM and a background child: the zeus shape.
    p = procs.start("tree", ["sh", "-c", "trap '' TERM; sleep 60 & sleep 60"], tmp_path)
    time.sleep(0.2)
    procs.stop(p, grace=0.5)
    assert procs.survivors() == []


@pytest.mark.unit
def test_kill_all_leaves_nothing(tmp_path):
    procs = ss.Procs(tmp_path)
    for i in range(3):
        procs.start(f"s{i}", ["sh", "-c", "sleep 60 & sleep 60"], tmp_path)
    time.sleep(0.2)
    procs.kill_all()
    assert procs.survivors() == []


@pytest.mark.unit
def test_run_cmd_times_out_and_kills_the_group(tmp_path):
    marker = tmp_path / "child.pid"
    t = time.monotonic()
    res = ss.run_cmd(["sh", "-c", f"sleep 60 & echo $! > {marker}; wait"], tmp_path, timeout=0.5)
    assert res.returncode == 124
    assert time.monotonic() - t < 5
    pid = int(marker.read_text())
    time.sleep(0.1)
    alive = subprocess.run(["kill", "-0", str(pid)], capture_output=True).returncode == 0
    assert not alive, "the hung command's child survived its timeout"


@pytest.mark.unit
def test_run_cmd_interrupted_kills_the_group(tmp_path):
    """A SIGTERM to the gate arrives as an exception inside communicate();
    the CLI it was waiting on must not outlive it."""
    import signal

    class Interrupted(Exception):
        pass

    def boom(*_):
        raise Interrupted
    marker = tmp_path / "child.pid"
    old = signal.signal(signal.SIGALRM, boom)
    signal.setitimer(signal.ITIMER_REAL, 0.5)
    try:
        with pytest.raises(Interrupted):
            ss.run_cmd(["sh", "-c", f"echo $$ > {marker}; sleep 60"], tmp_path, timeout=30)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    pid = int(marker.read_text())
    time.sleep(0.1)
    alive = subprocess.run(["kill", "-0", str(pid)], capture_output=True).returncode == 0
    assert not alive, "the interrupted command survived"


@pytest.mark.unit
def test_wait_listening_rejects_a_process_that_dies(tmp_path):
    procs = ss.Procs(tmp_path)
    p = procs.start("dies", ["sh", "-c", "echo bind failed; exit 3"], tmp_path)
    with pytest.raises(ss.Broken, match="exited 3"):
        ss.wait_listening(p, ss.free_port(), timeout=3)
    procs.kill_all()


@pytest.mark.unit
def test_resp_exchange_reset_is_a_check_failure_not_a_crash():
    port = ss.free_port()  # nothing listens: connection refused
    with pytest.raises(ss.CheckFailed, match="ConnectionRefused"):
        ss.resp_exchange(port, ss.resp_cmd("PING"), b"+PONG\r\n")


@pytest.mark.unit
def test_resp_encoding():
    assert ss.resp_cmd("SET", "k", "vv") == b"*3\r\n$3\r\nSET\r\n$1\r\nk\r\n$2\r\nvv\r\n"


@pytest.mark.unit
def test_unknown_suite_is_an_error_exit_1(capsys):
    assert ss.main(["nope"]) == 1
    assert "unknown suite" in capsys.readouterr().err
