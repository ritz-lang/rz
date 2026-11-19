"""Shared harness: outcomes, the Reporter, process groups and I/O helpers.

Every suite module imports from here; nothing here knows about a suite.
"""

from __future__ import annotations

import http.client
import os
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PROJECTS = REPO / "projects"

IO_TIMEOUT = 1.5      # a server that has not answered in this long is not going to
START_TIMEOUT = 10.0  # a server that is not listening after this long is broken
CMD_TIMEOUT = 8.0     # bound on any one CLI invocation
WRK = shutil.which("wrk")  # stack.wrk_index's load generator (#2464)


# --------------------------------------------------------------------------
# Outcomes
# --------------------------------------------------------------------------

class CheckFailed(Exception):
    """The behaviour under test is wrong. An xfail may excuse it."""


class Broken(Exception):
    """A precondition failed (missing binary, server never listened). Never
    excused by an xfail: it is not the bug the xfail names."""


PASS, FAIL, XFAIL, XPASS, SKIP = "PASS", "FAIL", "XFAIL", "XPASS", "SKIP"


@dataclass
class Result:
    check: str
    outcome: str
    detail: str = ""


@dataclass
class Reporter:
    xfails: dict[str, str]
    results: list[Result] = field(default_factory=list)
    out: object = sys.stdout

    def record(self, check: str, ok: bool, detail: str = "", broken: bool = False) -> str:
        reason = self.xfails.get(check)
        if broken:
            outcome = FAIL
        elif ok:
            outcome = XPASS if reason else PASS
        else:
            outcome = XFAIL if reason else FAIL
        self.results.append(Result(check, outcome, detail))
        line = f"{outcome:5}  {check}"
        if outcome == XFAIL:
            line += f"  [{reason}]  got: {detail}"
        elif outcome == XPASS:
            line += f"  [{reason}]  now PASSES: delete its XFAILS entry (strict xpass)"
        elif outcome == FAIL:
            line += f"  {'BROKEN: ' if broken else ''}{detail}"
        elif detail:
            line += f"  {detail}"
        print(line, file=self.out, flush=True)
        return outcome

    def run(self, check: str, fn: Callable[[], str | None]) -> str:
        try:
            detail = fn() or ""
        except CheckFailed as e:
            return self.record(check, False, str(e))
        except Broken as e:
            return self.record(check, False, str(e), broken=True)
        except Exception as e:  # noqa: BLE001 -- a harness crash is a FAIL, named
            return self.record(check, False, f"{type(e).__name__}: {e}", broken=True)
        return self.record(check, True, detail)

    def skip(self, check: str, why: str) -> None:
        self.results.append(Result(check, SKIP, why))
        print(f"{SKIP:5}  {check}  {why}", file=self.out, flush=True)

    def broken(self, check: str, why: str) -> None:
        self.record(check, False, why, broken=True)

    def exit_code(self) -> int:
        return 1 if any(r.outcome in (FAIL, XPASS) for r in self.results) else 0

    def unused_xfails(self, selected: set[str] | None) -> list[str]:
        """XFAILS entries no check ran under. A renamed check must not leave
        an excuse behind that silently matches nothing."""
        ran = {r.check for r in self.results}
        return sorted(k for k in self.xfails
                      if k not in ran and (selected is None or _suite_of(k) in selected))

    def summary(self) -> str:
        counts = {o: sum(r.outcome == o for r in self.results)
                  for o in (PASS, XFAIL, SKIP, XPASS, FAIL)}
        return "  ".join(f"{n} {o.lower()}" for o, n in counts.items())


def _suite_of(check: str) -> str:
    return "help" if check.startswith("help:") else check.split(".", 1)[0]


# --------------------------------------------------------------------------
# Processes: own session each, killed by group, verified dead
# --------------------------------------------------------------------------

class Procs:
    def __init__(self, logdir: Path):
        self.logdir = logdir
        self.live: dict[int, tuple[str, subprocess.Popen]] = {}
        self.started_pgids: set[int] = set()
        self._n = 0

    def start(self, name: str, argv: list[str], cwd: Path, stdin=subprocess.DEVNULL,
              env: dict[str, str] | None = None) -> subprocess.Popen:
        """Start `argv` in its own session; `env` is added to ours."""
        self._n += 1
        log = self.logdir / f"{self._n:02d}-{name}.log"
        with open(log, "wb") as fh:  # the child keeps its own copy of the fd
            p = subprocess.Popen(argv, cwd=cwd, stdin=stdin, stdout=fh, stderr=subprocess.STDOUT,
                                 start_new_session=True, env={**os.environ, **env} if env else None)
        p.log = log  # type: ignore[attr-defined]
        p.label = name  # type: ignore[attr-defined]
        self.live[p.pid] = (name, p)
        self.started_pgids.add(p.pid)
        return p

    def stop(self, p: subprocess.Popen, sig: int = signal.SIGTERM, grace: float = 3.0) -> None:
        """Signal the whole group (zeus's workers too), escalate to SIGKILL."""
        for s in (sig, signal.SIGKILL):
            try:
                os.killpg(p.pid, s)
            except ProcessLookupError:
                break
            try:
                p.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                continue
            if s == signal.SIGKILL or not _group_alive(p.pid):
                break
        try:
            os.killpg(p.pid, signal.SIGKILL)  # stragglers in the group
        except ProcessLookupError:
            pass
        try:
            p.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
        self.live.pop(p.pid, None)

    def kill_all(self) -> None:
        for _name, p in list(self.live.values()):
            self.stop(p, signal.SIGKILL, grace=2.0)

    def survivors(self) -> list[int]:
        return sorted(g for g in self.started_pgids if _group_alive(g))


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    # A zombie leader we have not reaped still answers; check /proc for any
    # member that is not a zombie.
    try:
        for pid in os.listdir("/proc"):
            if not pid.isdigit():
                continue
            try:
                stat = Path(f"/proc/{pid}/stat").read_text()
            except OSError:
                continue
            fields = stat.rsplit(")", 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != "Z":
                return True
    except OSError:
        return True
    return False


def _pid_alive(pid: int) -> bool:
    """True if pid exists and is not a zombie."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return stat.rsplit(")", 1)[1].split()[0] != "Z"


def log_tail(p: subprocess.Popen, n: int = 6) -> str:
    try:
        lines = Path(p.log).read_text(errors="replace").splitlines()  # type: ignore[attr-defined]
    except OSError:
        return "(no log)"
    return " | ".join(lines[-n:])


def log_text(p: subprocess.Popen) -> str:
    """Everything `p` has logged so far."""
    return Path(p.log).read_text(errors="replace")  # type: ignore[attr-defined]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_listening(p: subprocess.Popen, port: int, timeout: float = START_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if p.poll() is not None:
            raise Broken(f"{p.label} exited {p.returncode} before listening on {port}: {log_tail(p)}")  # type: ignore[attr-defined]
        if port_in_use(port):
            time.sleep(0.15)
            if p.poll() is None:
                return
            raise Broken(f"{p.label} exited {p.returncode} just after {port} answered: {log_tail(p)}")  # type: ignore[attr-defined]
        time.sleep(0.05)
    raise Broken(f"{p.label} not listening on {port} after {timeout}s: {log_tail(p)}")  # type: ignore[attr-defined]


def wait_path(p: subprocess.Popen, path: Path, timeout: float = START_TIMEOUT) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if p.poll() is not None:
            raise Broken(f"{p.label} exited {p.returncode} before creating {path.name}: {log_tail(p)}")  # type: ignore[attr-defined]
        if path.exists():
            return
        time.sleep(0.05)
    raise Broken(f"{p.label} never created {path.name}: {log_tail(p)}")  # type: ignore[attr-defined]


SUN_PATH_MAX = 107  # sockaddr_un.sun_path is 108 bytes, NUL included


def unix_socket_path(path: Path) -> Path:
    """path, if bind() can take it; else Broken naming its length.

    An over-long path makes the server's bind() fail, which a harness only
    sees as a socket that never appears, START_TIMEOUT later (#4100)."""
    n = len(os.fsencode(path))
    if n > SUN_PATH_MAX:
        raise Broken(f"unix socket path too long: {n} bytes > {SUN_PATH_MAX} (sun_path): {path}")
    return path


def short_sock_dir(name: str = "zeus.sock", prefix: str = "smoke_") -> Path:
    """A fresh dir for unix sockets where <dir>/name fits sun_path. The
    caller removes it.

    The first of $TMPDIR, $XDG_RUNTIME_DIR, /tmp ($SOCK_DIR_LAST, for tests)
    that is absolute, short enough, and where mkdtemp succeeds. A gate's
    TMPDIR sits deep in its worktree and left zeus.sock ~10 bytes of headroom
    (#4100); a full /tmp failed every gate on bangerang (#4274). Same order
    as tools/sock_dir.sh (#4282); Broken, naming each candidate, if none."""
    why = []
    for cand in (os.environ.get("TMPDIR", ""), os.environ.get("XDG_RUNTIME_DIR", ""),
                 os.environ.get("SOCK_DIR_LAST", "/tmp")):
        if not cand.startswith("/"):
            if cand:
                why.append(f"{cand} (relative)")
            continue
        cand = cand.rstrip("/") or "/"
        # <cand>/<prefix>XXXXXXXX/<name>, as mkdtemp names it
        if len(os.fsencode(cand)) + 1 + len(prefix) + 8 + 1 + len(os.fsencode(name)) > SUN_PATH_MAX:
            why.append(f"{cand} (too long)")
            continue
        try:
            return Path(tempfile.mkdtemp(prefix=prefix, dir=cand))
        except OSError as e:
            why.append(f"{cand} ({e.strerror or e})")
    raise Broken(f"no socket dir for {name}: {'; '.join(why)}")


def run_cmd(argv: list[str], cwd: Path, stdin: bytes | None = None,
            timeout: float = CMD_TIMEOUT, split_stderr: bool = False) -> subprocess.CompletedProcess:
    """A short-lived CLI. Own session; its group is killed on timeout AND on
    any other way out (a SIGTERM to the gate lands here as SystemExit).
    stderr is folded into stdout unless split_stderr."""
    p = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE if split_stderr else subprocess.STDOUT,
                         start_new_session=True)
    try:
        out, err = p.communicate(stdin, timeout=timeout)
        return subprocess.CompletedProcess(argv, p.returncode, out or b"", err or b"")
    except subprocess.TimeoutExpired:
        _killpg(p.pid)
        out, err = p.communicate()
        return subprocess.CompletedProcess(argv, 124, out or b"", err or b"")
    finally:
        _killpg(p.pid)  # background children of a CLI that exited, or an interrupted wait
        if p.poll() is None:
            p.wait()


def _killpg(pgid: int) -> None:
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def short(b: bytes | str, n: int = 160) -> str:
    s = b.decode(errors="replace") if isinstance(b, bytes) else b
    s = s.replace("\r", "\\r").replace("\n", "\\n")
    return s if len(s) <= n else s[:n] + "..."


def binary(rel: str) -> Path:
    p = PROJECTS / rel
    if not (p.is_file() and os.access(p, os.X_OK)):
        raise Broken(f"missing binary projects/{rel} (run ./rz build --all first)")
    return p


def http_req(port: int, method: str, path: str, body: bytes | None = None,
             headers: dict | None = None, tls: bool = False, timeout: float = 5.0):
    if tls:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        c = http.client.HTTPSConnection("127.0.0.1", port, timeout=timeout, context=ctx)
    else:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        c.request(method, path, body=body, headers=headers or {})
        resp = c.getresponse()
        data = resp.read()
        version = c.sock.version() if tls and c.sock else None
        return resp.status, dict(resp.getheaders()), data, version
    finally:
        c.close()
