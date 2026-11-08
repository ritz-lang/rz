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
            GET it 4 times, edit it, restart the whole stack, GET it again
  hollow    sage, goliath, rzrz and ritz-lsp must not report success for
            work they did not do
  rzsh      the Linux shell: echo, cd, $X, $?, >, |, external commands

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
the kernel (bind to 0) except mausoleum's 7777, which nexus's store dials
unconditionally (#2459); if 7777 is taken the stack suite is SKIPPED, loudly.

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
    # tome (#2457)
    "tome.uring.ping": "#2457 the default io_uring server accepts, then never replies (silence or reset)",
    "tome.uring.set_get": "#2457 the default io_uring server never replies",
    "tome.uring.incr": "#2457 the default io_uring server never replies",
    "tome.uring.pipeline": "#2457 the default io_uring server never replies",
    "tome.uring.cli": "#2457 io_uring server never replies, and tome-cli -c hangs",
    "tome.uring.cli_stdin": "#2457 io_uring server never replies, and tome-cli ignores stdin",
    "tome.blocking.incr": "#2457 INCR is '-ERR unknown command'",
    "tome.blocking.pipeline": "#2457 -b answers only the first of two pipelined commands",
    "tome.blocking.cli": "#2457 tome-cli -c hangs after 'Connecting to ...'",
    "tome.blocking.cli_stdin": "#2457 tome-cli prints 'Connecting to ...' and nothing else",
    # nexus (#2459)
    "stack.read_4x": "#2459 each worker has its own page index: 404, 200, 404, 200",
    "stack.edit_4x": "#2459 an edit shows on alternate GETs only",
    # hollow entry points (#2460)
    "hollow.sage_runs_js": "#2460 sage prints its version and exits 0 without reading the file",
    "hollow.goliath_unknown_command": "#2460 goliath's main prints 'Run tests with: make test' and exits 0",
    "hollow.rzrz_test": "#2460 rzrz test prints 'Testing project' and returns 0",
    "hollow.rzrz_run": "#2460 rzrz run is a TODO that returns 0",
    "hollow.rzrz_clean": "#2460 rzrz clean prints and returns 0",
    "hollow.rzrz_compare": "#2460 rzrz compare is a TODO that returns 0",
    "hollow.lsp_hover": "#2460 ritz-lsp advertises hoverProvider and answers null",
    "hollow.lsp_definition": "#2460 ritz-lsp advertises definitionProvider and answers null",
    # rzsh (#2461)
    "rzsh.cd": "#2461 cd does not change directory",
    "rzsh.var": "#2461 $X is not expanded",
    "rzsh.status": "#2461 $? is not expanded",
    "rzsh.redirect": "#2461 > is passed to echo as an argument",
    "rzsh.pipe": "#2461 | is ignored",
}

IO_TIMEOUT = 1.5      # a server that has not answered in this long is not going to
START_TIMEOUT = 10.0  # a server that is not listening after this long is broken
CMD_TIMEOUT = 8.0     # bound on any one CLI invocation


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

    def start(self, name: str, argv: list[str], cwd: Path, stdin=subprocess.DEVNULL) -> subprocess.Popen:
        self._n += 1
        log = self.logdir / f"{self._n:02d}-{name}.log"
        fh = open(log, "wb")
        p = subprocess.Popen(argv, cwd=cwd, stdin=stdin, stdout=fh, stderr=subprocess.STDOUT,
                             start_new_session=True)
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
    procs.stop(pe)


# --------------------------------------------------------------------------
# stack: valet -> zeus -> nexus (+ encrypted mausoleum on 7777)
# --------------------------------------------------------------------------

NEXUS_STORE_PORT = 7777  # hardcoded in nexus src/store.ritz (#2459)


def suite_stack(r: Reporter, procs: Procs, tmp: Path) -> None:
    try:
        m7m = binary("mausoleum/build/debug/mausoleum")
        zeus = binary("zeus/build/debug/zeus")
        valet = binary("valet/build/debug/valet")
        nexus = binary("nexus/build/debug/nexus")
    except Broken as e:
        r.broken("stack.start", str(e))
        return
    if port_in_use(NEXUS_STORE_PORT):
        r.skip("stack.*", f"127.0.0.1:{NEXUS_STORE_PORT} is taken; nexus can only dial mausoleum "
                          f"there (#2459), so the stack cannot run on this host now")
        return
    work = tmp / "stack"
    data = work / "m7m"
    data.mkdir(parents=True)
    sock = work / "zeus.sock"
    port = free_port()

    def up() -> list[subprocess.Popen]:
        if sock.exists():
            sock.unlink()
        # 7777 is fixed, so a restart can race the old socket's teardown;
        # retry a bind failure briefly rather than flake.
        for attempt in range(6):
            m = procs.start("stack-mausoleum", [str(m7m), "serve", "-p", str(NEXUS_STORE_PORT), "-d", str(data)], work)
            try:
                wait_listening(m, NEXUS_STORE_PORT)
                break
            except Broken:
                procs.stop(m)
                if attempt == 5 or "Failed to bind" not in log_tail(m):
                    raise
                time.sleep(0.5)
        z = procs.start("stack-zeus", [str(zeus), "-f", "-w", "2", "-s", str(sock),
                                       "-p", str(work / "zeus.pid"), str(nexus)], work)
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
        return [v, z, m]

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

    r.run("hollow.sage_runs_js", sage_runs_js)
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
    r.run("rzsh.pipe", lambda: expect_line("echo piped | /usr/bin/tr p P", "Piped"))


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
