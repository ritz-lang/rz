#!/usr/bin/env python3
"""smoke_stack.py -- start every server and CLI, talk to it for real (AGAST #2456).

Every package's [[test]] suite passed on 2026-11-08 while tome's default
io_uring server never replied, mausoleum lost its documents on restart,
nexus served a page on only every other request and several CLIs exited 0
having done nothing. No gate started a server and made a request. This one
does, after `./rz build --all`, using the debug binaries that step built:

  help      every [[bin]] that targets Linux runs `--help` and exits 0
  valet     GET /, a static file, a directory index, traversal -> 403, HTTPS
  tome      PING, SET/GET, INCR, a pipelined SET+GET and tome-cli, in the
            default io_uring mode AND in blocking mode (-b)
  mausoleum wiki-seed writes, restart on the same --data-dir, read back;
            wiki-seed exit codes; the encrypted protocol; the shell
  stack     valet -> zeus (2 workers) -> nexus + mausoleum: create a page,
            GET it 4 times, edit it, restart the whole stack, GET it again;
            100 keep-alive requests (the last says Connection: close);
            whole log lines; no mausoleum with 2 workers -> 503, not 404;
            MAUSOLEUM_PLAINTEXT=1 against a --no-encryption mausoleum, the
            handshake hint without it, a bad value -> refuse;
            SIGTERM/SIGINT/SIGKILL to zeus alone stops its workers in 2 s;
            kill -9 of one worker: zeus respawns it in 2 s, and a SIGHUP
            hot reload reaps it; zeus logs each line in one write(2)
  hollow    sage, goliath, rzrz and ritz-lsp must not report success for
            work they did not do
  rzsh      the Linux shell: echo, cd, $X, $?, >, |, external commands, EOF

What fails today is a STRICT xfail citing the child ticket that owns the
bug (XFAILS below). A check that starts passing fails the run (XPASS) until
its entry is deleted, so fixing a bug forces its xfail out, the same
strict-xpass rule as rz.toml [ci.known_failing.build]. A broken
precondition (a missing binary, a server that never listens) is a plain
FAIL even under an xfail: the xfail excuses the named bug, not a different
breakage that happens to make the same check red.

Every process is started in its own session and killed by process group
(zeus's nexus workers included) on exit, on failure and on SIGTERM/SIGINT.
The run checks afterwards that nothing it started survived. Ports come from
the kernel (bind to 0), mausoleum's too: nexus dials the port zeus passes
on as MAUSOLEUM_PORT (#3065), so a stack never shares mausoleum's default.

Run from anywhere, after `./rz build --all`:
    python3 projects/ritz/tools/smoke_stack.py            # everything
    python3 projects/ritz/tools/smoke_stack.py tome valet # some suites
    python3 projects/ritz/tools/smoke_stack.py --list     # check ids

CI runs it in main.yml's build-all job (so `make ci-local` and the room gate
run it too; ci_local parses the workflow). Exits 0 or 1 only: ci_local reads
3 as a SETUP ERROR, and a red run here is a regression.
"""

from __future__ import annotations

import argparse
import atexit
import http.client
import importlib.machinery
import importlib.util
import json
import os
import re
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROJECTS = REPO / "projects"

# Check id -> the ticket that owns its failure. Delete an entry in the same
# change that makes its check pass; the run fails (XPASS) until you do.
XFAILS: dict[str, str] = {
    # help: these exit non-zero for --help (run in a fresh temp cwd)
    "help:angelo/hello-world": "#2462 ignores --help and runs its demo: 'Failed to load font', exit 1",
    "help:angelo/render-demo": "#2462 ignores --help and runs its demo (font relative to cwd), exit 2",
    "help:larb/tools/ritz-stats/ritz-stats": "#2462 --help is read as a file name: 'Error reading file', exit 1",
    "help:mausoleum/concurrent_bench": "#2462 'Unknown argument: --help', exit 2",
    "help:nexus/nexus": "#2462 prints its usage and exits 1",
    "help:zeus/test_client": "#2462 prints its usage and exits 1",
    # hollow entry points (#2460 made the rest honest; sage still runs nothing)
    "hollow.sage_runs_js": "#2787 sage has no interpreter: `sage t.js` exits 1 'not implemented'",
}

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
        fh = open(log, "wb")
        p = subprocess.Popen(argv, cwd=cwd, stdin=stdin, stdout=fh, stderr=subprocess.STDOUT,
                             start_new_session=True, env={**os.environ, **env} if env else None)
        fh.close()
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


def log_tail(p: subprocess.Popen, n: int = 6) -> str:
    try:
        lines = Path(p.log).read_text(errors="replace").splitlines()  # type: ignore[attr-defined]
    except OSError:
        return "(no log)"
    return " | ".join(lines[-n:])


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


def run_cmd(argv: list[str], cwd: Path, stdin: bytes | None = None,
            timeout: float = CMD_TIMEOUT) -> subprocess.CompletedProcess:
    """A short-lived CLI. Own session; its group is killed on timeout AND on
    any other way out (a SIGTERM to the gate lands here as SystemExit)."""
    p = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out, _ = p.communicate(stdin, timeout=timeout)
        return subprocess.CompletedProcess(argv, p.returncode, out or b"", b"")
    except subprocess.TimeoutExpired:
        _killpg(p.pid)
        out, _ = p.communicate()
        return subprocess.CompletedProcess(argv, 124, out or b"", b"")
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


# --------------------------------------------------------------------------
# help: every Linux [[bin]] answers --help with exit 0
# --------------------------------------------------------------------------

def _load(name: str, path: Path):
    # `rz` has no .py suffix, so name the loader explicitly.
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def targets_linux(target: str, target_os: str) -> bool:
    """By target, never by name: harland ELFs (ritzutils cat.elf, rzsh.elf)
    and the UEFI loader segfault or refuse to exec on Linux."""
    if target_os and target_os != "linux":
        return False
    return not target or "linux" in target


@dataclass
class Bin:
    project: str   # rz project id, e.g. "mausoleum" or "larb/tools/ritz-stats"
    name: str
    path: Path

    @property
    def check(self) -> str:
        return f"help:{self.project}/{self.name}"


def linux_bins() -> tuple[list[Bin], dict[str, str]]:
    """Every buildable Linux [[bin]] in the workspace, from the same member
    discovery and binary planning `./rz build --all` uses, plus the
    {project: reason} of rz.toml [ci.known_failing.build] (those are not built)."""
    rz = _load("rz_cli_2456", REPO / "rz")
    if str(PROJECTS / "ritz") not in sys.path:
        sys.path.insert(0, str(PROJECTS / "ritz"))  # build.py imports cache, cas, ...
    build = _load("ritz_buildpy_2456", PROJECTS / "ritz" / "build.py")
    known = rz.known_failing_from_config("build")
    bins = []
    for project in rz.discover_projects():
        pkg = (PROJECTS / project).resolve()
        config = tomllib.loads((pkg / "ritz.toml").read_text())
        for b in build.plan_binaries(pkg, config).buildable:
            if not targets_linux(b.target, b.target_os):
                continue
            out = pkg / "build" / "debug" / (f"{b.name}.elf" if b.freestanding else b.name)
            bins.append(Bin(project, b.name, out))
    return bins, known


def suite_help(r: Reporter, tmp: Path) -> None:
    bins, known = linux_bins()
    if len(bins) < 20:
        r.broken("help:discovery", f"found only {len(bins)} Linux binaries (expected 20+): discovery is broken")
    for b in bins:
        if b.project in known:
            r.skip(b.check, f"package not built: rz.toml [ci.known_failing.build] {known[b.project][:60]}")
            continue

        def one(b=b):
            if not b.path.is_file():
                raise Broken(f"not built: {b.path.relative_to(REPO)}")
            cwd = tmp / "help" / b.project.replace("/", "_") / b.name
            cwd.mkdir(parents=True, exist_ok=True)  # some write files into cwd
            res = run_cmd([str(b.path), "--help"], cwd, timeout=5)
            if res.returncode != 0:
                raise CheckFailed(f"exit {res.returncode}: {short(res.stdout, 90)}")
        r.run(b.check, one)


# --------------------------------------------------------------------------
# valet
# --------------------------------------------------------------------------

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


def suite_valet(r: Reporter, procs: Procs, tmp: Path) -> None:
    try:
        valet = binary("valet/build/debug/valet")
    except Broken as e:
        r.broken("valet.start", str(e))
        return
    work = tmp / "valet"
    (work / "public" / "sub").mkdir(parents=True)
    token = f"smoke-{os.getpid()}-static"
    (work / "public" / "test.txt").write_text(token + "\n")
    (work / "public" / "sub" / "inner.txt").write_text("inner\n")
    port = free_port()
    (work / "valet.json").write_text(json.dumps({
        "server": {"port": port, "workers": 1},
        "static": {"prefix": "/static/", "root": "./public"},
    }))
    p = procs.start("valet", [str(valet), "-c", "valet.json", "-p", str(port)], work)
    try:
        wait_listening(p, port)
    except Broken as e:
        r.broken("valet.start", str(e))
        procs.stop(p)
        return

    def root():
        st, _, body, _ = http_req(port, "GET", "/")
        if st != 200 or b"Hello" not in body:
            raise CheckFailed(f"GET / -> {st} {short(body, 60)}")

    def static():
        st, _, body, _ = http_req(port, "GET", "/static/test.txt")
        if st != 200 or token.encode() not in body:
            raise CheckFailed(f"GET /static/test.txt -> {st} {short(body, 60)}")

    def dirindex():
        st, _, body, _ = http_req(port, "GET", "/static/")
        if st != 200 or b"test.txt" not in body:
            raise CheckFailed(f"GET /static/ -> {st} {short(body, 80)}")

    def traversal():
        st, _, body, _ = http_req(port, "GET", "/static/../valet.json")
        if st != 403 or b'"server"' in body:
            raise CheckFailed(f"GET /static/../valet.json -> {st} {short(body, 60)} (want 403)")

    r.run("valet.root", root)
    r.run("valet.static", static)
    r.run("valet.dirindex", dirindex)
    r.run("valet.traversal", traversal)
    procs.stop(p)

    # HTTPS with a freshly generated self-signed P-256 certificate.
    if not shutil.which("openssl"):
        r.broken("valet.https", "openssl not found (needed to generate a certificate)")
        return
    tport = free_port()
    gen = run_cmd(["openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
                   "-nodes", "-keyout", "key.pem", "-out", "cert.pem", "-days", "2",
                   "-subj", "/CN=localhost"], work, timeout=20)
    if gen.returncode != 0:
        r.broken("valet.https", f"openssl req failed: {short(gen.stdout)}")
        return
    (work / "tls.json").write_text(json.dumps({
        "server": {"port": tport, "workers": 1},
        "tls": {"enabled": True, "cert": str(work / "cert.pem"), "key": str(work / "key.pem")},
    }))
    p = procs.start("valet-tls", [str(valet), "-c", "tls.json", "-p", str(tport)], work)

    def https():
        wait_listening(p, tport)
        st, _, body, version = http_req(tport, "GET", "/", tls=True)
        if st != 200 or b"Hello" not in body or version != "TLSv1.3":
            raise CheckFailed(f"HTTPS GET / -> {st} {version} {short(body, 60)}")
        return version

    r.run("valet.https", https)
    procs.stop(p)


# --------------------------------------------------------------------------
# tome
# --------------------------------------------------------------------------

def resp_cmd(*args: str) -> bytes:
    out = f"*{len(args)}\r\n".encode()
    for a in args:
        b = a.encode()
        out += b"$%d\r\n%s\r\n" % (len(b), b)
    return out


def resp_exchange(port: int, payload: bytes, want: bytes, timeout: float = IO_TIMEOUT) -> bytes:
    """Send payload, read until `want` has arrived (or the server goes quiet).
    A reset or refusal from the server under test is its behaviour: CheckFailed."""
    got = b""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
            s.sendall(payload)
            deadline = time.monotonic() + timeout
            while want not in got and time.monotonic() < deadline:
                s.settimeout(max(0.05, deadline - time.monotonic()))
                try:
                    chunk = s.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    break
                got += chunk
    except OSError as e:
        raise CheckFailed(f"{type(e).__name__} after {short(got) or 'no reply'}: {e}") from None
    return got


def suite_tome(r: Reporter, procs: Procs, tmp: Path) -> None:
    try:
        server = binary("tome/build/debug/tome-server")
        cli = binary("tome/build/debug/tome-cli")
    except Broken as e:
        r.broken("tome.start", str(e))
        return
    for mode, flags in (("uring", []), ("blocking", ["-b"])):
        work = tmp / f"tome-{mode}"
        work.mkdir()
        port = free_port()
        p = procs.start(f"tome-{mode}", [str(server), "-p", str(port), *flags], work)
        try:
            wait_listening(p, port)
        except Broken as e:
            r.broken(f"tome.{mode}.start", str(e))
            procs.stop(p)
            continue
        pre = f"smoke-{mode}"

        def ping():
            got = resp_exchange(port, resp_cmd("PING"), b"+PONG\r\n")
            if got != b"+PONG\r\n":
                raise CheckFailed(f"PING -> {short(got) or 'no reply'}")

        def set_get():
            # One command per connection: pipelining has its own check.
            got = resp_exchange(port, resp_cmd("SET", f"{pre}:k", "world"), b"+OK\r\n")
            if got != b"+OK\r\n":
                raise CheckFailed(f"SET -> {short(got) or 'no reply'}")
            got = resp_exchange(port, resp_cmd("GET", f"{pre}:k"), b"$5\r\nworld\r\n")
            if got != b"$5\r\nworld\r\n":
                raise CheckFailed(f"GET -> {short(got) or 'no reply'}")

        def incr():
            a = resp_exchange(port, resp_cmd("INCR", f"{pre}:n"), b"\r\n")
            b = resp_exchange(port, resp_cmd("INCR", f"{pre}:n"), b"\r\n")
            if (a, b) != (b":1\r\n", b":2\r\n"):
                raise CheckFailed(f"INCR, INCR -> {short(a) or 'no reply'}, {short(b) or 'no reply'}")

        def pipeline():
            payload = resp_cmd("SET", f"{pre}:p", "piped") + resp_cmd("GET", f"{pre}:p")
            want = b"+OK\r\n$5\r\npiped\r\n"
            got = resp_exchange(port, payload, want)
            if got != want:
                raise CheckFailed(f"SET+GET in one write -> {short(got) or 'no reply'}")

        def cli_c():
            resp_exchange(port, resp_cmd("SET", f"{pre}:c", "from-cli"), b"+OK\r\n")
            res = run_cmd([str(cli), "-p", str(port), "-c", f"GET {pre}:c"], work, timeout=4)
            if res.returncode != 0 or b"from-cli" not in res.stdout:
                raise CheckFailed(f"tome-cli -c -> exit {res.returncode}: {short(res.stdout, 90)}")

        def cli_stdin():
            resp_exchange(port, resp_cmd("SET", f"{pre}:s", "via-stdin"), b"+OK\r\n")
            res = run_cmd([str(cli), "-p", str(port)], work,
                          stdin=f"GET {pre}:s\nquit\n".encode(), timeout=4)
            if res.returncode != 0 or b"via-stdin" not in res.stdout:
                raise CheckFailed(f"tome-cli <stdin -> exit {res.returncode}: {short(res.stdout, 90)}")

        for name, fn in (("ping", ping), ("set_get", set_get), ("incr", incr),
                         ("pipeline", pipeline), ("cli", cli_c), ("cli_stdin", cli_stdin)):
            r.run(f"tome.{mode}.{name}", fn)
        procs.stop(p)


# --------------------------------------------------------------------------
# mausoleum
# --------------------------------------------------------------------------

def suite_mausoleum(r: Reporter, procs: Procs, tmp: Path) -> None:
    try:
        m7m = binary("mausoleum/build/debug/mausoleum")
        seed = binary("mausoleum/build/debug/wiki-seed")
    except Broken as e:
        r.broken("mausoleum.start", str(e))
        return
    work = tmp / "mausoleum"
    work.mkdir()

    def serve(data: Path, port: int, encrypted: bool = False) -> subprocess.Popen:
        data.mkdir(exist_ok=True)
        argv = [str(m7m), "serve", "-p", str(port), "-d", str(data)]
        if not encrypted:
            argv.append("--no-encryption")
        p = procs.start(f"mausoleum-{port}", argv, work)
        wait_listening(p, port)
        return p

    def seed_cmd(port: int, *flags: str, encrypted: bool = False) -> subprocess.CompletedProcess:
        # wiki-seed speaks the encrypted protocol by default, like the server.
        mode = [] if encrypted else ["--no-encryption"]
        return run_cmd([str(seed), "-p", str(port), *mode, *flags], work)

    def verified(res: subprocess.CompletedProcess) -> bool:
        return res.returncode == 0 and b"[OK]" in res.stdout and b"[FAIL]" not in res.stdout

    # write -> read while up -> graceful restart -> read
    port = free_port()
    data = work / "data-term"
    try:
        p = serve(data, port)
    except Broken as e:
        r.broken("mausoleum.start", str(e))
        return

    def do_seed():
        res = seed_cmd(port, "--seed")
        if res.returncode != 0 or b"Created" not in res.stdout:
            raise CheckFailed(f"wiki-seed --seed -> exit {res.returncode}: {short(res.stdout, 120)}")

    def verify_live():
        res = seed_cmd(port, "--verify")
        if not verified(res):
            raise CheckFailed(f"wiki-seed --verify -> exit {res.returncode}: {short(res.stdout, 120)}")

    seeded = r.run("mausoleum.seed", do_seed) == PASS
    r.run("mausoleum.verify_live", verify_live)
    procs.stop(p, signal.SIGTERM)

    def restart_term():
        if not seeded:
            raise Broken("nothing was seeded")
        port2 = free_port()  # same --data-dir; a fresh port isolates persistence from bind/TIME_WAIT
        p2 = serve(data, port2)
        try:
            res = seed_cmd(port2, "--verify")
        finally:
            procs.stop(p2)
        if not verified(res):
            raise CheckFailed(f"after SIGTERM + restart, --verify -> {short(res.stdout, 120)}")

    r.run("mausoleum.restart_term", restart_term)

    def restart_kill9():
        port9 = free_port()
        data9 = work / "data-kill9"
        p9 = serve(data9, port9)
        res = seed_cmd(port9, "--seed")
        if res.returncode != 0:
            procs.stop(p9)
            raise Broken(f"seeding the kill -9 server failed: {short(res.stdout)}")
        procs.stop(p9, signal.SIGKILL)
        port9 = free_port()
        p9 = serve(data9, port9)
        try:
            res = seed_cmd(port9, "--verify")
        finally:
            procs.stop(p9)
        if not verified(res):
            raise CheckFailed(f"after kill -9 + restart, --verify -> {short(res.stdout, 120)}")

    r.run("mausoleum.restart_kill9", restart_kill9)

    def term_graceful():
        # #2463: SIGTERM to the default (io_uring) loop must drain and shut
        # down cleanly. At the signal one client sits idle on a keep-alive
        # connection and another is half-way through sending a PING. The
        # PING is still answered, a connection made after the signal is not
        # served, and the process exits 0 well inside the 5s drain deadline
        # (it must not wait on the idle client) with storage checkpointed.
        portg = free_port()
        datag = work / "data-graceful"
        pg = serve(datag, portg)
        try:
            res = seed_cmd(portg, "--seed")
            if res.returncode != 0:
                raise Broken(f"seeding failed: {short(res.stdout)}")
            if wal_bytes(datag) <= WAL_CHECKPOINT_ONLY_SIZE:
                raise Broken(f"seeding left no WAL records to checkpoint ({wal_bytes(datag)} bytes)")
            idle = socket.create_connection(("127.0.0.1", portg), timeout=IO_TIMEOUT)
            busy = socket.create_connection(("127.0.0.1", portg), timeout=IO_TIMEOUT)
            try:
                ping = m7sp_ping(0x2463)
                busy.sendall(ping[:6])
                time.sleep(0.2)  # let the server take both connections and the partial header
                os.killpg(pg.pid, signal.SIGTERM)
                time.sleep(0.2)
                late = m7sp_try_ping(portg)
                if late:
                    raise CheckFailed(f"a connection made after SIGTERM was served: {late.hex()}")
                busy.sendall(ping[6:])
                reply = recv_exact(busy, 16)
                if len(reply) != 16 or reply[9] != 0x81:
                    raise CheckFailed(f"PING in flight at SIGTERM -> {reply.hex() or 'no reply'} (want PONG)")
                code = pg.wait(timeout=3)
            except subprocess.TimeoutExpired:
                raise CheckFailed(f"still running 3s after its last request: {log_tail(pg, 3)}") from None
            finally:
                idle.close()
                busy.close()
        finally:
            procs.stop(pg)
        check_clean_exit(pg, code, datag)

    r.run("mausoleum.term_graceful", term_graceful)

    def verify_fail_exit():
        porte = free_port()
        pe = serve(work / "data-empty", porte)
        try:
            res = seed_cmd(porte, "--verify")
        finally:
            procs.stop(pe)
        if b"[FAIL]" not in res.stdout and b"not found" not in res.stdout.lower():
            raise Broken(f"--verify on an empty store did not report a miss: {short(res.stdout)}")
        if res.returncode == 0:
            raise CheckFailed(f"--verify reported a missing page and exited 0: {short(res.stdout, 90)}")

    r.run("mausoleum.seed_verify_fail_exit", verify_fail_exit)

    def unreachable_exit():
        res = seed_cmd(free_port(), "--verify")  # nothing listens there
        if res.returncode == 0:
            raise CheckFailed(f"no server, exit 0: {short(res.stdout, 90)}")

    r.run("mausoleum.seed_unreachable_exit", unreachable_exit)

    # The default (encrypted) protocol.
    porte = free_port()
    try:
        pe = serve(work / "data-enc", porte, encrypted=True)
    except Broken as e:
        r.broken("mausoleum.encrypted_start", str(e))
        return

    def seed_encrypted():
        a = seed_cmd(porte, "--seed", encrypted=True)
        b = seed_cmd(porte, "--verify", encrypted=True)
        if a.returncode != 0 or not verified(b):
            raise CheckFailed(f"--seed exit {a.returncode}: {short(a.stdout, 70)}; "
                              f"--verify exit {b.returncode}: {short(b.stdout, 70)}")

    def shell_handshake():
        res = run_cmd([str(m7m), "shell", "-p", str(porte)], work, stdin=b"quit\n")
        if res.returncode != 0 or b"Encrypted session established" not in res.stdout:
            raise CheckFailed(f"shell -> exit {res.returncode}: {short(res.stdout, 120)}")

    def shell_ping():
        res = run_cmd([str(m7m), "shell", "-p", str(porte)], work, stdin=b"ping\nquit\n")
        if res.returncode != 0 or b"pong" not in res.stdout.lower():
            raise CheckFailed(f"shell 'ping' -> exit {res.returncode}: {short(res.stdout[-90:], 90)}")

    def shell_commands():
        res = run_cmd([str(m7m), "shell", "-p", str(porte)], work, stdin=b"help\nquit\n")
        out = res.stdout.decode(errors="replace").lower()
        missing = [c for c in ("put", "get", "delete", "list") if not re.search(rf"\b{c}\b", out)]
        if missing:
            raise CheckFailed(f"shell lacks {', '.join(missing)}: {short(res.stdout, 100)}")

    def shell_crud():
        # put -> list -> get -> delete -> get, by id, over the encrypted protocol.
        res = run_cmd([str(m7m), "shell", "-p", str(porte)], work,
                      stdin=b'put slug=smoke title="Smoke test" n=7\nlist\nquit\n')
        out = res.stdout.decode(errors="replace")
        m = re.search(r"inserted (\d+)", out)
        if res.returncode != 0 or not m or not re.search(rf"^(m7m> )*{m.group(1)}\s.*slug=\"smoke\"", out, re.M):
            raise CheckFailed(f"shell put/list -> exit {res.returncode}: {short(res.stdout[-120:], 120)}")
        doc = m.group(1)
        res = run_cmd([str(m7m), "shell", "-p", str(porte)], work,
                      stdin=f"get {doc}\ndelete {doc}\nquit\n".encode())
        out = res.stdout.decode(errors="replace")
        if res.returncode != 0 or 'title = "Smoke test"' not in out or f"deleted {doc}" not in out:
            raise CheckFailed(f"shell get/delete -> exit {res.returncode}: {short(res.stdout[-120:], 120)}")
        res = run_cmd([str(m7m), "shell", "-p", str(porte)], work, stdin=f"get {doc}\nquit\n".encode())
        if res.returncode == 0 or b"not found" not in res.stdout:
            raise CheckFailed(f"shell get after delete -> exit {res.returncode}: {short(res.stdout[-90:], 90)}")

    r.run("mausoleum.seed_encrypted", seed_encrypted)
    r.run("mausoleum.shell_handshake", shell_handshake)
    r.run("mausoleum.shell_ping", shell_ping)
    r.run("mausoleum.shell_commands", shell_commands)
    r.run("mausoleum.shell_crud", shell_crud)

    def term_graceful_encrypted():
        if wal_bytes(work / "data-enc") <= WAL_CHECKPOINT_ONLY_SIZE:
            raise Broken("the encrypted server's writes left no WAL records to checkpoint")
        os.killpg(pe.pid, signal.SIGTERM)
        try:
            code = pe.wait(timeout=3)
        except subprocess.TimeoutExpired:
            raise CheckFailed(f"still running 3s after SIGTERM: {log_tail(pe, 3)}") from None
        check_clean_exit(pe, code, work / "data-enc")

    r.run("mausoleum.term_graceful_encrypted", term_graceful_encrypted)
    procs.stop(pe)


# A checkpointed WAL holds exactly one 32-byte record header of type
# WAL_REC_CHECKPOINT (7); the type byte sits at offset 28 (lib/wal.ritz).
WAL_CHECKPOINT_ONLY_SIZE = 32


def wal_bytes(data: Path) -> int:
    wal = data / "wal.wal.000000"
    return wal.stat().st_size if wal.exists() else 0


def m7sp_ping(request_id: int) -> bytes:
    # 16-byte M7SP header: magic "M7SP", length 16, version 1, MSG_PING, flags 0.
    return b"M7SP" + (16).to_bytes(4, "big") + bytes([1, 0x01, 0, 0]) + request_id.to_bytes(4, "big")


def m7sp_try_ping(port: int) -> bytes:
    """PING on a new connection; whatever comes back. Refused, reset or
    closed unanswered all read as b""."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5) as s:
            s.sendall(m7sp_ping(0x2464))
            return recv_exact(s, 16)
    except OSError:
        return b""


def recv_exact(s: socket.socket, n: int) -> bytes:
    got = b""
    while len(got) < n:
        try:
            chunk = s.recv(n - len(got))
        except OSError:
            break
        if not chunk:
            break
        got += chunk
    return got


def check_clean_exit(p: subprocess.Popen, code: int, data: Path) -> None:
    """After SIGTERM: exit 0, 'Server stopped.', and the WAL cut back to its checkpoint record."""
    log = p.log.read_text(errors="replace")  # type: ignore[attr-defined]
    if code != 0:
        raise CheckFailed(f"exit {code} after SIGTERM (want 0): {log_tail(p, 3)}")
    if "Server stopped." not in log:
        raise CheckFailed(f"exit 0 but no 'Server stopped.': {log_tail(p, 3)}")
    wal = (data / "wal.wal.000000").read_bytes()
    if len(wal) != WAL_CHECKPOINT_ONLY_SIZE or wal[28] != 7:
        raise CheckFailed(f"WAL is {len(wal)} bytes after shutdown, not one checkpoint record")


# --------------------------------------------------------------------------
# stack: valet -> zeus -> nexus (+ encrypted mausoleum of its own)
# --------------------------------------------------------------------------


def suite_stack(r: Reporter, procs: Procs, tmp: Path) -> None:
    try:
        m7m = binary("mausoleum/build/debug/mausoleum")
        zeus = binary("zeus/build/debug/zeus")
        valet = binary("valet/build/debug/valet")
        nexus = binary("nexus/build/debug/nexus")
    except Broken as e:
        r.broken("stack.start", str(e))
        return
    work = tmp / "stack"
    data = work / "m7m"
    data.mkdir(parents=True)
    sock = work / "zeus.sock"
    port = free_port()
    # nexus's store: zeus passes MAUSOLEUM_PORT on to its workers (#3065).
    # Every zeus here gets it, or its nexus dials 127.0.0.1:7777: some other
    # stack's mausoleum.
    store_port = free_port()
    store_env = {"MAUSOLEUM_HOST": "127.0.0.1", "MAUSOLEUM_PORT": str(store_port)}

    # A second mausoleum, --no-encryption, for MAUSOLEUM_PLAINTEXT (#2466).
    plain_port = free_port()
    plain_data = work / "m7m-plain"
    plain_data.mkdir()

    def up(with_store: bool = True, plaintext: bool = False,
           env: dict[str, str] | None = None) -> list[subprocess.Popen]:
        """valet -> zeus -> nexus, plus a mausoleum unless with_store is False.

        plaintext: that mausoleum runs --no-encryption on plain_port, and zeus
        is pointed there; env: extra variables for zeus (and so nexus).
        """
        if sock.exists():
            sock.unlink()
        m_port, m_data = (plain_port, plain_data) if plaintext else (store_port, data)
        m_argv = [str(m7m), "serve", "-p", str(m_port), "-d", str(m_data)]
        if plaintext:
            m_argv.append("--no-encryption")
        zeus_env = {**store_env, "MAUSOLEUM_PORT": str(m_port), **(env or {})}
        # A restart reuses the port, so it can race the old socket's
        # teardown; retry a bind failure briefly rather than flake.
        m = None
        for attempt in range(6 if with_store else 0):
            m = procs.start("stack-mausoleum", m_argv, work)
            try:
                wait_listening(m, m_port)
                break
            except Broken:
                procs.stop(m)
                if attempt == 5 or "Failed to bind" not in log_tail(m):
                    raise
                time.sleep(0.5)
        z = procs.start("stack-zeus", [str(zeus), "-f", "-w", "2", "-s", str(sock),
                                       "-p", str(work / "zeus.pid"), str(nexus)], work,
                             env=zeus_env)
        wait_path(z, sock)
        v = procs.start("stack-valet", [str(valet), "-p", str(port), "-z", str(sock)], work)
        wait_listening(v, port)
        # Both workers attached: /health answers through zeus.
        deadline = time.monotonic() + START_TIMEOUT
        while True:
            try:
                if http_req(port, "GET", "/health", timeout=1)[0] == 200:
                    break
            except OSError:
                pass
            if time.monotonic() > deadline:
                raise Broken(f"/health never answered 200 through zeus: {log_tail(z)}")
            time.sleep(0.1)
        time.sleep(0.3)
        return [v, z] + ([m] if m is not None else [])

    def down(ps: list[subprocess.Popen]) -> None:
        for p in ps:
            procs.stop(p, signal.SIGTERM)

    try:
        ps = up()
    except Broken as e:
        r.broken("stack.start", str(e))
        return
    zeus_proc = ps[1]
    slug = f"smoke-{os.getpid()}"
    first, second = f"first-{slug}-body", f"second-{slug}-body"
    form = {"Content-Type": "application/x-www-form-urlencoded"}

    def gets(want: str) -> list[str]:
        seen = []
        for _ in range(4):
            st, _, body, _ = http_req(port, "GET", f"/wiki/{slug}")
            seen.append(f"{st}{'' if want.encode() in body else '(stale)'}" if st == 200 else str(st))
        return seen

    def health():
        st = http_req(port, "GET", "/health")[0]
        if st != 200:
            raise CheckFailed(f"/health -> {st}")

    def index():
        st, _, body, _ = http_req(port, "GET", "/")
        if st != 200 or b"<" not in body:
            raise CheckFailed(f"GET / -> {st} {short(body, 60)}")

    def store_connected():
        time.sleep(0.2)
        log = Path(zeus_proc.log).read_text(errors="replace")  # type: ignore[attr-defined]
        n = log.count("Connected to mausoleum")
        if n < 2:
            raise CheckFailed(f"{n} of 2 workers logged 'Connected to mausoleum': {log_tail(zeus_proc, 4)}")

    def create():
        st, hdrs, body, _ = http_req(port, "POST", "/wiki", body=f"slug={slug}&content={first}".encode(), headers=form)
        if st != 303:
            raise CheckFailed(f"POST /wiki -> {st} {short(body, 60)} (want 303)")

    def read_4x():
        seen = gets(first)
        if seen != ["200"] * 4:
            raise CheckFailed(f"4 GETs -> {', '.join(seen)}")

    def edit_post():
        st, _, body, _ = http_req(port, "POST", f"/wiki/{slug}", body=f"content={second}".encode(), headers=form)
        if st not in (200, 303):
            raise CheckFailed(f"POST /wiki/{slug} -> {st} {short(body, 60)} (want 303)")

    def edit_4x():
        seen = gets(second)
        if seen != ["200"] * 4:
            raise CheckFailed(f"4 GETs after edit -> {', '.join(seen)}")

    r.run("stack.health", health)
    r.run("stack.index", index)
    r.run("stack.store_connected", store_connected)
    created = r.run("stack.create", create) == PASS
    r.run("stack.read_4x", read_4x)
    edited = r.run("stack.edit_post", edit_post) == PASS
    if edited:
        r.run("stack.edit_4x", edit_4x)
    else:
        r.broken("stack.edit_4x", "the edit POST failed, so there is no edit to read back")

    def keepalive_100():
        # valet closes a connection after 100 responses. Through zeus it used
        # to pass on the worker's "Connection: keep-alive" for the 100th too,
        # then close: the client's next request was a read error, ~1% of all
        # requests under wrk (#2459).
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            for i in range(1, 101):
                conn.request("GET", "/health")
                resp = conn.getresponse()
                resp.read()
                said = (resp.getheader("Connection") or "").lower()
                want = "close" if i == 100 else "keep-alive"
                if resp.status != 200 or said != want:
                    raise CheckFailed(f"response {i}: {resp.status}, Connection: {said or '(none)'} (want {want})")
        finally:
            conn.close()

    def log_lines():
        # Workers share stdout; a line written in pieces interleaved with the
        # other worker's ("...Spire at 7127.0.0.11:87777", #2459).
        log = Path(zeus_proc.log).read_text(errors="replace")  # type: ignore[attr-defined]
        lines = [ln for ln in log.splitlines() if "Connecting to mausoleum" in ln]
        want = re.compile(rf"\[nexus \d+\] \[STORE\] Connecting to mausoleum via Spire at 127\.0\.0\.1:{store_port}")
        bad = [ln for ln in lines if not want.fullmatch(ln)]
        if len(lines) < 2 or bad:
            raise CheckFailed(f"{len(lines)} connect lines, malformed: {short(' | '.join(bad), 160)}")

    def wrk_index():
        # 64 connections on / through zeus -w 2 (#2464). ResponseSlot was 56
        # bytes in a ring sized for 48, so response slots 220-255 overlapped
        # arena slot 0: nexus's page body clobbered response ids, the
        # response ring filled, nexus acked requests it never answered, and
        # every request after was a 504 until restart.
        out = run_cmd([WRK, "-t4", "-c64", "-d10s", "--timeout", "2s",
                       f"http://127.0.0.1:{port}/"], work, timeout=30).stdout.decode(errors="replace")
        n = re.search(r"(\d+) requests in", out)
        sock_err = re.search(r"Socket errors: connect (\d+), read (\d+), write (\d+), timeout (\d+)", out)
        timeouts = int(sock_err.group(4)) if sock_err else 0
        # wrk counts statuses outside 200-399; / answers 200, never 3xx.
        bad = re.search(r"Non-2xx or 3xx responses: (\d+)", out)
        non2xx = int(bad.group(1)) if bad else 0
        if not n or int(n.group(1)) == 0:
            raise Broken(f"wrk made no requests: {short(out, 200)}")
        if timeouts or non2xx:
            raise CheckFailed(f"{n.group(1)} requests: {timeouts} timeouts, {non2xx} non-2xx")
        # And the stack is still serving afterwards.
        after = [http_req(port, "GET", p)[0] for p in ("/health", "/")]
        if after != [200, 200]:
            raise CheckFailed(f"after wrk: /health, / -> {after} (want 200s)")
        return f"{n.group(1)} requests, 0 timeouts, 0 non-2xx"

    r.run("stack.keepalive_100", keepalive_100)
    r.run("stack.log_lines", log_lines)
    if WRK:
        r.run("stack.wrk_index", wrk_index)
    elif os.environ.get("GITHUB_ACTIONS"):
        r.broken("stack.wrk_index", "wrk is not on PATH; main.yml's 'Install test tools' step installs it")
    else:
        r.skip("stack.wrk_index", "wrk is not on PATH (apt install wrk)")
    down(ps)

    def restart():
        if not created:
            raise Broken("the page was never created")
        ps2 = up()
        try:
            seen = gets("")  # either revision: persistence, not editing
        finally:
            down(ps2)
        if seen != ["200"] * 4:
            raise CheckFailed(f"after restarting the stack, 4 GETs -> {', '.join(seen)}")

    r.run("stack.restart", restart)

    def no_store():
        # No mausoleum, 2 workers: each would serve a private in-memory wiki,
        # so a page created on one is a 404 on the next request (#2459).
        # Every page request must fail instead, with a 503.
        ps3 = up(with_store=False)
        try:
            seen = [http_req(port, "GET", "/wiki/welcome")[0] for _ in range(4)]
            post = http_req(port, "POST", "/wiki", body=f"slug={slug}-x&content=x".encode(), headers=form)[0]
            log = Path(ps3[1].log).read_text(errors="replace")  # type: ignore[attr-defined]
        finally:
            down(ps3)
        if seen != [503] * 4 or post != 503:
            raise CheckFailed(f"4 GETs -> {seen}, POST /wiki -> {post} (want 503s)")
        if log.count("REFUSING to serve pages") < 2:
            raise CheckFailed(f"workers did not log why they refuse: {short(log[-200:], 200)}")

    r.run("stack.no_store_503", no_store)

    def zeus_log(ps: list[subprocess.Popen]) -> str:
        return Path(ps[1].log).read_text(errors="replace")  # type: ignore[attr-defined]

    def plaintext_store():
        # MAUSOLEUM_PLAINTEXT=1: nexus speaks plaintext Spire to a mausoleum
        # running --no-encryption (#2466). Before, nothing could switch it.
        ps4 = up(plaintext=True, env={"MAUSOLEUM_PLAINTEXT": "1"})
        try:
            page = f"{slug}-plain"
            post = http_req(port, "POST", "/wiki", body=f"slug={page}&content=plain-{slug}".encode(),
                            headers=form)[0]
            seen = []
            for _ in range(4):
                st, _, body, _ = http_req(port, "GET", f"/wiki/{page}")
                seen.append(str(st) if st != 200 or f"plain-{slug}".encode() in body else "200(stale)")
            log = zeus_log(ps4)
        finally:
            down(ps4)
        want = f"Spire at 127.0.0.1:{plain_port} (plaintext)"
        if log.count(want) < 2 or log.count("Connected to mausoleum") < 2:
            raise CheckFailed(f"workers did not connect in plaintext ({want!r}): {short(log[-240:], 240)}")
        if post != 303 or seen != ["200"] * 4:
            raise CheckFailed(f"POST /wiki -> {post}, 4 GETs -> {', '.join(seen)} (want 303, 200s)")

    def encrypted_vs_plaintext_hint():
        # Without the switch, nexus's encrypted handshake gets no reply from a
        # --no-encryption mausoleum: every page request fails, and the log
        # says why (wiki_store_connect_hint), not just "error -6".
        ps5 = up(plaintext=True)
        try:
            st = http_req(port, "GET", "/wiki/welcome")[0]
            log = zeus_log(ps5)
        finally:
            down(ps5)
        if "is it running with --no-encryption?" not in log:
            raise CheckFailed(f"no handshake hint in the log: {short(log[-240:], 240)}")
        if st != 503:
            raise CheckFailed(f"GET /wiki/welcome -> {st} (want 503)")

    def plaintext_bad_value():
        # An unknown MAUSOLEUM_PLAINTEXT refuses to serve, never ignored: the
        # (encrypted) store is up and would otherwise be reached.
        ps6 = up(env={"MAUSOLEUM_PLAINTEXT": "yes"})
        try:
            st = http_req(port, "GET", "/wiki/welcome")[0]
            log = zeus_log(ps6)
        finally:
            down(ps6)
        if log.count("MAUSOLEUM_PLAINTEXT is not 1") < 2 or "Connected to mausoleum" in log:
            raise CheckFailed(f"workers did not refuse MAUSOLEUM_PLAINTEXT=yes: {short(log[-240:], 240)}")
        if st != 503:
            raise CheckFailed(f"GET /wiki/welcome -> {st} (want 503)")

    r.run("stack.plaintext_store", plaintext_store)
    r.run("stack.plaintext_hint", encrypted_vs_plaintext_hint)
    r.run("stack.plaintext_bad_value", plaintext_bad_value)

    def zeus_alone() -> tuple[subprocess.Popen, list[int]]:
        """zeus -f -w 2 nexus, no valet or store; returns zeus and its worker pids."""
        if sock.exists():
            sock.unlink()
        z = procs.start("stack-zeus-alone", [str(zeus), "-f", "-w", "2", "-s", str(sock),
                                             "-p", str(work / "zeus.pid"), str(nexus)], work, env=store_env)
        wait_path(z, sock)
        deadline = time.monotonic() + START_TIMEOUT
        while True:
            log = Path(z.log).read_text(errors="replace")  # type: ignore[attr-defined]
            pids = [int(m) for m in re.findall(r"zeus: spawned worker \d+ \(pid (\d+)\)", log)]
            if len(pids) == 2:
                return z, pids
            if time.monotonic() > deadline:
                procs.stop(z)
                # The tail alone hid the evidence in #3121: show every line
                # that mentions a spawn, torn or not.
                spawn = [ln for ln in log.splitlines() if "spawn" in ln]
                raise Broken(f"zeus never logged 2 spawned workers in {START_TIMEOUT:.0f} s; "
                             f"spawn lines: {spawn}; tail: {log_tail(z)}")
            time.sleep(0.1)

    def workers_gone_after(sig: int) -> None:
        # Signal zeus alone, not its process group: a supervisor stops its
        # own workers. Before #2465 both nexus workers outlived a SIGTERM to
        # zeus (reparented to init, shm and all); only killpg hid it.
        z, pids = zeus_alone()
        try:
            os.kill(z.pid, sig)
            deadline = time.monotonic() + 2.0
            while (alive := [p for p in pids if _pid_alive(p)]) and time.monotonic() < deadline:
                time.sleep(0.05)
            if alive:
                raise CheckFailed(f"{signal.Signals(sig).name} to zeus: worker(s) {alive} of {pids} "
                                  f"still running 2 s later")
            if sig != signal.SIGKILL:
                # The workers' PDEATHSIG kills them whenever zeus exits, so
                # "gone" alone can't tell zeus's shutdown from zeus dying
                # of the signal: zeus must say it reaped each one.
                try:
                    z.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    raise CheckFailed(f"{signal.Signals(sig).name}: zeus still running 2 s later")
                log = Path(z.log).read_text(errors="replace")  # type: ignore[attr-defined]
                reaped = {int(m) for m in re.findall(r"zeus: reaped worker \d+ \(pid (\d+)\)", log)}
                if z.returncode != 0 or reaped != set(pids):
                    raise CheckFailed(f"{signal.Signals(sig).name}: zeus exit {z.returncode}, reaped "
                                      f"{sorted(reaped)} of {pids} (want exit 0, all reaped)")
                # nexus dies of SIGTERM; needing SIGKILL means the worker
                # inherited zeus's blocked signal mask across exec.
                if "ignored SIGTERM" in log:
                    raise CheckFailed(f"{signal.Signals(sig).name}: a worker ignored zeus's SIGTERM: "
                                      f"{log_tail(z, 4)}")
        finally:
            procs.stop(z, signal.SIGKILL)

    r.run("stack.zeus_term_stops_workers", lambda: workers_gone_after(signal.SIGTERM))
    r.run("stack.zeus_int_stops_workers", lambda: workers_gone_after(signal.SIGINT))
    # SIGKILL can't be handled: the workers' PR_SET_PDEATHSIG must stop them.
    r.run("stack.zeus_kill9_stops_workers", lambda: workers_gone_after(signal.SIGKILL))

    def respawns_killed_worker() -> None:
        # #3075: check_workers tested liveness with kill(pid, 0), which
        # succeeds on an unreaped zombie, so a crashed worker was never
        # respawned and its slot silently served nothing.
        z, pids = zeus_alone()
        try:
            os.kill(pids[0], signal.SIGKILL)
            pat = r"zeus: respawned worker \d+ \(pid (\d+)\)"
            deadline = time.monotonic() + 2.0
            while True:
                log = Path(z.log).read_text(errors="replace")  # type: ignore[attr-defined]
                new = [int(m) for m in re.findall(pat, log)]
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
            procs.stop(z, signal.SIGKILL)

    r.run("stack.zeus_respawns_killed_worker", respawns_killed_worker)

    def reload_reaps_dead_worker() -> None:
        # #3075: SIGHUP's per-worker exit wait used kill(pid, 0) too, so a
        # worker that had died spun the full 500 ms, then its slot took a
        # new pid and the corpse stayed a zombie for zeus's lifetime. SIGHUP
        # straight after the kill, before check_workers' next tick.
        z, pids = zeus_alone()
        try:
            os.kill(pids[0], signal.SIGKILL)
            os.kill(z.pid, signal.SIGHUP)
            deadline = time.monotonic() + 3.0
            while True:
                log = Path(z.log).read_text(errors="replace")  # type: ignore[attr-defined]
                if "zeus: hot reload complete" in log:
                    break
                if time.monotonic() > deadline:
                    raise CheckFailed(f"SIGHUP: no 'hot reload complete' in 3 s: {log_tail(z, 4)}")
                time.sleep(0.05)
            if Path(f"/proc/{pids[0]}").exists():
                raise CheckFailed(f"SIGHUP after kill -9 of worker {pids[0]}: hot reload left it "
                                  f"unreaped (zombie)")
        finally:
            procs.stop(z, signal.SIGKILL)

    r.run("stack.zeus_reload_reaps_dead_worker", reload_reaps_dead_worker)

    def zeus_writes_and_lines(z: subprocess.Popen) -> tuple[int, int]:
        """(write syscalls zeus has made, lines zeus has logged), read consistently."""
        while True:
            before = Path(z.log).read_text(errors="replace")  # type: ignore[attr-defined]
            try:
                # The thread's own file: /proc/<pid>/io also folds in the
                # writes of every worker zeus has reaped.
                io = Path(f"/proc/{z.pid}/task/{z.pid}/io").read_text()
            except OSError as e:
                raise Broken(f"/proc/{z.pid}/task/{z.pid}/io unreadable (no task I/O accounting?): {e}")
            if Path(z.log).read_text(errors="replace") == before:  # type: ignore[attr-defined]
                syscw = int(re.search(r"^syscw: (\d+)$", io, re.M).group(1))  # type: ignore[union-attr]
                return syscw, sum(ln.startswith("zeus: ") for ln in before.splitlines())
            time.sleep(0.05)

    def log_one_write_per_line() -> None:
        # #3121: zeus printed a line in pieces, one write(2) per fragment and
        # per digit ("spawned worker " "0" " (pid " "5" "6" ... ")\n"). Its
        # workers share that stdout, so a worker's line landing between two
        # pieces tore it and the "spawned worker N (pid P)" regexes above
        # never matched: zeus_int_stops_workers waited out its 10 s. With no
        # client connected, zeus's only write(2)s are its log lines, so
        # syscw (/proc/<pid>/io) must equal its line count: at startup, and
        # after a kill -9 makes it log a respawn.
        z, pids = zeus_alone()
        try:
            deadline = time.monotonic() + START_TIMEOUT
            while "zeus: entering event loop" not in Path(z.log).read_text(errors="replace"):  # type: ignore[attr-defined]
                if time.monotonic() > deadline:
                    raise Broken(f"zeus never entered its event loop: {log_tail(z)}")
                time.sleep(0.05)
            writes, lines = zeus_writes_and_lines(z)
            if writes != lines:
                raise CheckFailed(f"startup: zeus made {writes} write(2)s for {lines} log lines "
                                  f"(want one write per line)")
            os.kill(pids[0], signal.SIGKILL)
            deadline = time.monotonic() + 2.0
            while "zeus: respawned worker" not in Path(z.log).read_text(errors="replace"):  # type: ignore[attr-defined]
                if time.monotonic() > deadline:
                    raise CheckFailed(f"kill -9 worker {pids[0]}: no respawn in 2 s: {log_tail(z, 4)}")
                time.sleep(0.05)
            writes, lines = zeus_writes_and_lines(z)
            if writes != lines:
                raise CheckFailed(f"respawn: zeus made {writes} write(2)s for {lines} log lines "
                                  f"(want one write per line)")
        finally:
            procs.stop(z, signal.SIGKILL)

    r.run("stack.zeus_log_one_write_per_line", log_one_write_per_line)


def _pid_alive(pid: int) -> bool:
    """True if pid exists and is not a zombie."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return stat.rsplit(")", 1)[1].split()[0] != "Z"


# --------------------------------------------------------------------------
# hollow entry points (#2460): no command reports success for work not done
# --------------------------------------------------------------------------

def lsp_session(lsp: Path, cwd: Path, src: str, uri: str, requests: list[tuple[str, dict]]) -> list[dict]:
    def frame(obj: dict) -> bytes:
        b = json.dumps(obj).encode()
        return b"Content-Length: %d\r\n\r\n%s" % (len(b), b)
    msgs = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"processId": None, "rootUri": cwd.as_uri(), "capabilities": {}}},
            {"jsonrpc": "2.0", "method": "initialized", "params": {}},
            {"jsonrpc": "2.0", "method": "textDocument/didOpen",
             "params": {"textDocument": {"uri": uri, "languageId": "ritz", "version": 1, "text": src}}}]
    for i, (method, params) in enumerate(requests, start=2):
        msgs.append({"jsonrpc": "2.0", "id": i, "method": method, "params": params})
    msgs += [{"jsonrpc": "2.0", "id": 99, "method": "shutdown"}, {"jsonrpc": "2.0", "method": "exit"}]
    res = run_cmd([str(lsp)], cwd, stdin=b"".join(frame(m) for m in msgs), timeout=6)
    out, replies = res.stdout, []
    for m in re.finditer(rb"Content-Length: (\d+)\r\n\r\n", out):
        n = int(m.group(1))
        try:
            replies.append(json.loads(out[m.end():m.end() + n]))
        except ValueError:
            pass
    return replies


def suite_hollow(r: Reporter, tmp: Path) -> None:
    work = tmp / "hollow"
    work.mkdir()

    def sage_runs_js():
        sage = binary("sage/build/debug/sage")
        (work / "t.js").write_text("console.log(6 * 7);\n")
        res = run_cmd([str(sage), "t.js"], work)
        if res.returncode != 0 or not re.search(rb"(?m)^42$", res.stdout):
            raise CheckFailed(f"sage t.js (console.log(6*7)) -> exit {res.returncode}: {short(res.stdout, 80)}")

    def goliath_unknown():
        goliath = binary("goliath/build/debug/goliath")
        res = run_cmd([str(goliath), "no-such-command-2456"], work)
        if res.returncode == 0:
            raise CheckFailed(f"unknown command, exit 0: {short(res.stdout, 80)}")

    def sage_no_false_success():
        # Whatever sage can do, exit 0 on a script means it ran it (#2460).
        sage = binary("sage/build/debug/sage")
        (work / "t.js").write_text("console.log(6 * 7);\n")
        res = run_cmd([str(sage), "t.js"], work)
        if res.returncode == 0 and not re.search(rb"(?m)^42$", res.stdout):
            raise CheckFailed(f"sage t.js -> exit 0 without running it: {short(res.stdout, 80)}")

    r.run("hollow.sage_runs_js", sage_runs_js)
    r.run("hollow.sage_no_false_success", sage_no_false_success)
    r.run("hollow.goliath_unknown_command", goliath_unknown)

    # rzrz: a subcommand on a project that does not exist did no work, so it
    # must not exit 0, whether it is implemented or honestly "not implemented".
    for sub in ("test", "run", "clean", "compare"):
        def rzrz_sub(sub=sub):
            rzrz = binary("rzrz/build/debug/rzrz")
            res = run_cmd([str(rzrz), sub, "no-such-project-2456"], REPO)
            if res.returncode == 0:
                raise CheckFailed(f"rzrz {sub} no-such-project -> exit 0: {short(res.stdout, 80)}")
        r.run(f"hollow.rzrz_{sub}", rzrz_sub)

    # ritz-lsp: a capability it advertises must answer for a symbol it can see.
    src = "fn helper() -> i32\n    42\n\nfn main() -> i32\n    helper()\n"
    path = work / "t.ritz"
    path.write_text(src)
    pos = {"textDocument": {"uri": path.as_uri()}, "position": {"line": 4, "character": 6}}
    cache: dict = {}

    def lsp_replies() -> dict[int, dict]:
        if not cache:
            lsp = binary("ritz-lsp/build/debug/ritz-lsp")
            replies = lsp_session(lsp, work, src, path.as_uri(),
                                  [("textDocument/hover", pos), ("textDocument/definition", pos)])
            cache.update({m["id"]: m for m in replies if "id" in m})
            if 1 not in cache:
                raise Broken(f"ritz-lsp never answered initialize ({len(replies)} replies)")
        return cache

    def lsp_cap(cap: str, rid: int, what: str):
        replies = lsp_replies()
        caps = replies[1].get("result", {}).get("capabilities", {})
        if not caps.get(cap):
            return f"{cap} not advertised"
        if rid not in replies:
            raise Broken(f"ritz-lsp sent no reply to {what} (the xfail is about a null answer)")
        if not replies[rid].get("result"):
            raise CheckFailed(f"advertises {cap}, {what} on helper() -> {json.dumps(replies[rid].get('result'))}")

    r.run("hollow.lsp_hover", lambda: lsp_cap("hoverProvider", 2, "hover"))
    r.run("hollow.lsp_definition", lambda: lsp_cap("definitionProvider", 3, "definition"))


# --------------------------------------------------------------------------
# rzsh (#2461): the Linux build, a scripted session per feature
# --------------------------------------------------------------------------

def suite_rzsh(r: Reporter, tmp: Path) -> None:
    work = tmp / "rzsh"
    (work / "sub").mkdir(parents=True)

    def session(script: str) -> tuple[subprocess.CompletedProcess, list[str]]:
        rzsh = binary("rzsh/build/debug/rzsh.linux")
        res = run_cmd([str(rzsh)], work, stdin=(script + "\nexit\n").encode(), timeout=5)
        return res, [ln.strip() for ln in res.stdout.decode(errors="replace").splitlines()]

    def expect_line(script: str, want: str):
        res, lines = session(script)
        # Exact lines only: rzsh echoes each input after its prompt
        # ("rzsh> echo X=$X"), so a suffix match would pass on the echo.
        if want not in lines:
            raise CheckFailed(f"{script!r} -> {short(res.stdout, 120)}")

    def redirect():
        out = work / "out.txt"
        out.unlink(missing_ok=True)
        res, _ = session(f"echo redirected > {out}")
        if not out.exists() or out.read_text().strip() != "redirected":
            raise CheckFailed(f"'echo redirected > out.txt' -> file {'missing' if not out.exists() else repr(out.read_text())}; "
                              f"stdout {short(res.stdout, 80)}")

    r.run("rzsh.echo", lambda: expect_line("echo hello world", "hello world"))
    r.run("rzsh.external", lambda: expect_line("/bin/echo external-ok", "external-ok"))
    r.run("rzsh.cd", lambda: expect_line(f"cd {work / 'sub'}\npwd", str(work / "sub")))
    r.run("rzsh.var", lambda: expect_line("export X=5\necho X=$X", "X=5"))
    r.run("rzsh.status", lambda: expect_line("false\necho status=$?", "status=1"))
    r.run("rzsh.redirect", redirect)
    r.run("rzsh.pipe", lambda: expect_line("echo piped | /usr/bin/tr p P", "PiPed"))

    def eof():
        # No trailing `exit`: end of stdin must end the shell (it used to spin).
        rzsh = binary("rzsh/build/debug/rzsh.linux")
        res = run_cmd([str(rzsh)], work, stdin=b"echo before-eof\n", timeout=5)
        if res.returncode != 0 or "before-eof" not in res.stdout.decode(errors="replace").split():
            raise CheckFailed(f"rc={res.returncode} stdout {short(res.stdout, 80)}")

    r.run("rzsh.eof", eof)


# --------------------------------------------------------------------------

SUITES = ["help", "valet", "tome", "mausoleum", "stack", "hollow", "rzsh"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("suites", nargs="*", metavar="SUITE",
                    help=f"subset of {', '.join(SUITES)} (default: all)")
    ap.add_argument("--list", action="store_true", help="print the xfail table and exit")
    ap.add_argument("--keep", action="store_true", help="keep the temp dir (logs) afterwards")
    args = ap.parse_args(argv)
    if args.list:
        for k, v in XFAILS.items():
            print(f"{k:40} {v}")
        return 0
    unknown = [s for s in args.suites if s not in SUITES]
    if unknown:  # not ap.error(): that exits 2, and this script exits 0 or 1
        print(f"smoke_stack: unknown suite(s) {unknown}; choose from {SUITES}", file=sys.stderr)
        return 1
    selected = args.suites or SUITES

    tmp = Path(tempfile.mkdtemp(prefix="smoke_stack_"))
    procs = Procs(tmp)
    r = Reporter(XFAILS)

    def on_signal(signum, _frame):
        raise SystemExit(f"smoke_stack: killed by signal {signum}")
    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(s, on_signal)
    atexit.register(procs.kill_all)

    t0 = time.monotonic()
    timings = []
    try:
        for suite in selected:
            ts = time.monotonic()
            print(f"--- {suite}", flush=True)
            try:
                if suite == "help":
                    suite_help(r, tmp)
                elif suite in ("hollow", "rzsh"):
                    {"hollow": suite_hollow, "rzsh": suite_rzsh}[suite](r, tmp)
                else:
                    {"valet": suite_valet, "tome": suite_tome, "mausoleum": suite_mausoleum,
                     "stack": suite_stack}[suite](r, procs, tmp)
            except Exception as e:  # noqa: BLE001 -- one crashed suite must not hide the rest
                r.broken(f"{suite}.harness", f"suite crashed: {type(e).__name__}: {e}")
            procs.kill_all()  # a suite that bailed early leaves nothing behind
            timings.append((suite, time.monotonic() - ts))
    finally:
        procs.kill_all()
        leaked = procs.survivors()
        if leaked:
            r.broken("harness.cleanup", f"process groups still alive after SIGKILL: {leaked}")
        if args.keep:
            print(f"logs kept in {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    for k in r.unused_xfails(set(selected)):
        r.broken(f"harness.xfail:{k}", "XFAILS entry matches no check that ran: rename or delete it")

    print("\n=== smoke-stack: per-suite seconds ===")
    for suite, secs in timings:
        print(f"  {suite:10} {secs:6.1f}s")
    print(f"  {'total':10} {time.monotonic() - t0:6.1f}s")
    print(f"=== {r.summary()}")
    failed = [x for x in r.results if x.outcome in (FAIL, XPASS)]
    for x in failed:
        print(f"  {x.outcome}: {x.check}  {x.detail if x.outcome == FAIL else XFAILS.get(x.check, '')}")
    code = r.exit_code()
    print("✓ smoke-stack passed" if code == 0 else "💥 smoke-stack FAILED")
    return code


if __name__ == "__main__":
    sys.exit(main())
