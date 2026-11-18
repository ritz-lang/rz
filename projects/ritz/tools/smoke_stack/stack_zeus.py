"""stack, zeus on its own: SIGTERM/SIGINT/SIGKILL to zeus alone stops its
workers in 2 s; kill -9 of one worker: zeus respawns it in 2 s, and a SIGHUP
hot reload reaps it; a SIGHUP hot reload stops and replaces every worker;
zeus logs each line in one write(2).

Each check starts `zeus -f -w 2 nexus` with no valet or store in front of it
(zeus_alone) from the stack suite's StackCtx.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .harness import (
    START_TIMEOUT,
    Broken,
    CheckFailed,
    _pid_alive,
    log_tail,
    log_text,
    wait_path,
)

if TYPE_CHECKING:
    from .stack import StackCtx


def zeus_alone(ctx: StackCtx) -> tuple[subprocess.Popen, list[int]]:
    """zeus -f -w 2 nexus, no valet or store; returns zeus and its worker pids."""
    if ctx.sock.exists():
        ctx.sock.unlink()
    z = ctx.procs.start("stack-zeus-alone", [str(ctx.zeus), "-f", "-w", "2", "-s", str(ctx.sock),
                                             "-p", str(ctx.work / "zeus.pid"), str(ctx.nexus)],
                        ctx.work, env=ctx.store_env)
    wait_path(z, ctx.sock)
    deadline = time.monotonic() + START_TIMEOUT
    while True:
        log = log_text(z)
        pids = [int(m) for m in re.findall(r"zeus: spawned worker \d+ \(pid (\d+)\)", log)]
        if len(pids) == 2:
            return z, pids
        if time.monotonic() > deadline:
            ctx.procs.stop(z)
            # The tail alone hid the evidence in #3121: show every line
            # that mentions a spawn, torn or not.
            spawn = [ln for ln in log.splitlines() if "spawn" in ln]
            raise Broken(f"zeus never logged 2 spawned workers in {START_TIMEOUT:.0f} s; "
                         f"spawn lines: {spawn}; tail: {log_tail(z)}")
        time.sleep(0.1)


def _check_clean_shutdown(z: subprocess.Popen, pids: list[int], sig: int) -> None:
    # The workers' PDEATHSIG kills them whenever zeus exits, so
    # "gone" alone can't tell zeus's shutdown from zeus dying
    # of the signal: zeus must say it reaped each one.
    try:
        z.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        raise CheckFailed(f"{signal.Signals(sig).name}: zeus still running 2 s later")
    log = log_text(z)
    reaped = {int(m) for m in re.findall(r"zeus: reaped worker \d+ \(pid (\d+)\)", log)}
    if z.returncode != 0 or reaped != set(pids):
        raise CheckFailed(f"{signal.Signals(sig).name}: zeus exit {z.returncode}, reaped "
                          f"{sorted(reaped)} of {pids} (want exit 0, all reaped)")
    # nexus dies of SIGTERM; needing SIGKILL means the worker
    # inherited zeus's blocked signal mask across exec.
    if "ignored SIGTERM" in log:
        raise CheckFailed(f"{signal.Signals(sig).name}: a worker ignored zeus's SIGTERM: "
                          f"{log_tail(z, 4)}")


def workers_gone_after(ctx: StackCtx, sig: int) -> None:
    # Signal zeus alone, not its process group: a supervisor stops its
    # own workers. Before #2465 both nexus workers outlived a SIGTERM to
    # zeus (reparented to init, shm and all); only killpg hid it.
    z, pids = zeus_alone(ctx)
    try:
        os.kill(z.pid, sig)
        deadline = time.monotonic() + 2.0
        while (alive := [p for p in pids if _pid_alive(p)]) and time.monotonic() < deadline:
            time.sleep(0.05)
        if alive:
            raise CheckFailed(f"{signal.Signals(sig).name} to zeus: worker(s) {alive} of {pids} "
                              f"still running 2 s later")
        if sig != signal.SIGKILL:
            _check_clean_shutdown(z, pids, sig)
    finally:
        ctx.procs.stop(z, signal.SIGKILL)


def term_stops_workers(ctx: StackCtx) -> None:
    workers_gone_after(ctx, signal.SIGTERM)


def int_stops_workers(ctx: StackCtx) -> None:
    workers_gone_after(ctx, signal.SIGINT)


def kill9_stops_workers(ctx: StackCtx) -> None:
    # SIGKILL can't be handled: the workers' PR_SET_PDEATHSIG must stop them.
    workers_gone_after(ctx, signal.SIGKILL)


def respawns_killed_worker(ctx: StackCtx) -> None:
    # #3075: check_workers tested liveness with kill(pid, 0), which
    # succeeds on an unreaped zombie, so a crashed worker was never
    # respawned and its slot silently served nothing.
    z, pids = zeus_alone(ctx)
    try:
        os.kill(pids[0], signal.SIGKILL)
        pat = r"zeus: respawned worker \d+ \(pid (\d+)\)"
        deadline = time.monotonic() + 2.0
        while True:
            new = [int(m) for m in re.findall(pat, log_text(z))]
            if new or time.monotonic() > deadline:
                break
            time.sleep(0.05)
        if not new:
            raise CheckFailed(f"kill -9 worker {pids[0]}: zeus did not respawn it within 2 s: "
                              f"{log_tail(z, 4)}")
        if not _pid_alive(new[0]) or not _pid_alive(pids[1]):
            raise CheckFailed(f"respawned worker {new[0]} or untouched worker {pids[1]} "
                              f"not running")
        # Respawning means zeus reaped the corpse: no zombie left behind.
        if Path(f"/proc/{pids[0]}").exists():
            raise CheckFailed(f"killed worker {pids[0]} left unreaped (zombie)")
    finally:
        ctx.procs.stop(z, signal.SIGKILL)


def reload_reaps_dead_worker(ctx: StackCtx) -> None:
    # #3075: SIGHUP's per-worker exit wait used kill(pid, 0) too, so a
    # worker that had died spun the full 500 ms, then its slot took a
    # new pid and the corpse stayed a zombie for zeus's lifetime. SIGHUP
    # straight after the kill, before check_workers' next tick.
    z, pids = zeus_alone(ctx)
    try:
        os.kill(pids[0], signal.SIGKILL)
        os.kill(z.pid, signal.SIGHUP)
        deadline = time.monotonic() + 3.0
        while "zeus: hot reload complete" not in log_text(z):
            if time.monotonic() > deadline:
                raise CheckFailed(f"SIGHUP: no 'hot reload complete' in 3 s: {log_tail(z, 4)}")
            time.sleep(0.05)
        if Path(f"/proc/{pids[0]}").exists():
            raise CheckFailed(f"SIGHUP after kill -9 of worker {pids[0]}: hot reload left it "
                              f"unreaped (zombie)")
    finally:
        ctx.procs.stop(z, signal.SIGKILL)


def _children(pid: int) -> list[int]:
    """Every process whose parent is pid, zombies included."""
    kids = []
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            stat = (d / "stat").read_text()
        except OSError:
            continue
        if int(stat.rsplit(")", 1)[1].split()[1]) == pid:
            kids.append(int(d.name))
    return sorted(kids)


def reload_replaces_workers(ctx: StackCtx) -> None:
    # #3084: SIGHUP only set WORKER_STATE_STOPPING in each control block,
    # which nexus never reads, waited 500 ms and spawned the new worker on
    # the re-prepared shm anyway: 2 old + 2 new nexus children, the old
    # ones never signalled or reaped. After the reload zeus must have
    # exactly -w children, none of them an original worker.
    z, pids = zeus_alone(ctx)
    try:
        os.kill(z.pid, signal.SIGHUP)
        deadline = time.monotonic() + 5.0
        while "zeus: hot reload complete" not in log_text(z):
            if time.monotonic() > deadline:
                raise CheckFailed(f"SIGHUP: no 'hot reload complete' in 5 s: {log_tail(z, 4)}")
            time.sleep(0.05)
        kids = _children(z.pid)
        stale = sorted(set(kids) & set(pids))
        if len(kids) != 2 or stale:
            raise CheckFailed(f"SIGHUP: zeus has children {kids} after 'hot reload complete' "
                              f"(want 2, none of the originals {pids}; still there: {stale})")
    finally:
        ctx.procs.stop(z, signal.SIGKILL)


def zeus_writes_and_lines(z: subprocess.Popen) -> tuple[int, int]:
    """(write syscalls zeus has made, lines zeus has logged), read consistently."""
    while True:
        before = log_text(z)
        try:
            # The thread's own file: /proc/<pid>/io also folds in the
            # writes of every worker zeus has reaped.
            io = Path(f"/proc/{z.pid}/task/{z.pid}/io").read_text()
        except OSError as e:
            raise Broken(f"/proc/{z.pid}/task/{z.pid}/io unreadable (no task I/O accounting?): {e}")
        if log_text(z) == before:
            syscw = int(re.search(r"^syscw: (\d+)$", io, re.MULTILINE).group(1))  # type: ignore[union-attr]
            return syscw, sum(ln.startswith("zeus: ") for ln in before.splitlines())
        time.sleep(0.05)


def log_one_write_per_line(ctx: StackCtx) -> None:
    # #3121: zeus printed a line in pieces, one write(2) per fragment and
    # per digit ("spawned worker " "0" " (pid " "5" "6" ... ")\n"). Its
    # workers share that stdout, so a worker's line landing between two
    # pieces tore it and the "spawned worker N (pid P)" regexes above
    # never matched: zeus_int_stops_workers waited out its 10 s. With no
    # client connected, zeus's only write(2)s are its log lines, so
    # syscw (/proc/<pid>/io) must equal its line count: at startup, and
    # after a kill -9 makes it log a respawn.
    z, pids = zeus_alone(ctx)
    try:
        deadline = time.monotonic() + START_TIMEOUT
        while "zeus: entering event loop" not in log_text(z):
            if time.monotonic() > deadline:
                raise Broken(f"zeus never entered its event loop: {log_tail(z)}")
            time.sleep(0.05)
        writes, lines = zeus_writes_and_lines(z)
        if writes != lines:
            raise CheckFailed(f"startup: zeus made {writes} write(2)s for {lines} log lines "
                              f"(want one write per line)")
        os.kill(pids[0], signal.SIGKILL)
        deadline = time.monotonic() + 2.0
        while "zeus: respawned worker" not in log_text(z):
            if time.monotonic() > deadline:
                raise CheckFailed(f"kill -9 worker {pids[0]}: no respawn in 2 s: {log_tail(z, 4)}")
            time.sleep(0.05)
        writes, lines = zeus_writes_and_lines(z)
        if writes != lines:
            raise CheckFailed(f"respawn: zeus made {writes} write(2)s for {lines} log lines "
                              f"(want one write per line)")
    finally:
        ctx.procs.stop(z, signal.SIGKILL)


CHECKS = (("zeus_term_stops_workers", term_stops_workers),
          ("zeus_int_stops_workers", int_stops_workers),
          ("zeus_kill9_stops_workers", kill9_stops_workers),
          ("zeus_respawns_killed_worker", respawns_killed_worker),
          ("zeus_reload_reaps_dead_worker", reload_reaps_dead_worker),
          ("zeus_reload_replaces_workers", reload_replaces_workers),
          ("zeus_log_one_write_per_line", log_one_write_per_line))
