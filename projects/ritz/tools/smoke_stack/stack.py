"""stack: valet -> zeus (2 workers) -> nexus + an encrypted mausoleum of its own.

Create a page, GET it 4 times, edit it, restart the whole stack, GET it
again; 100 keep-alive requests (the last says Connection: close); whole log
lines; no mausoleum with 2 workers -> 503, not 404; MAUSOLEUM_PLAINTEXT=1
against a --no-encryption mausoleum, the handshake hint without it, a bad
value -> refuse. zeus on its own (signals, respawn, reload, one write(2) per
log line) is stack_zeus.py.

Every check is a module-level function of a StackCtx: the binaries, ports,
paths and the page under test, shared without closures.
"""

from __future__ import annotations

import http.client
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

from . import stack_zeus
from .harness import (
    PASS,
    START_TIMEOUT,
    WRK,
    Broken,
    CheckFailed,
    Procs,
    Reporter,
    binary,
    free_port,
    http_req,
    log_tail,
    log_text,
    run_cmd,
    short,
    wait_listening,
    wait_path,
)

FORM = {"Content-Type": "application/x-www-form-urlencoded"}


@dataclass
class StackCtx:
    procs: Procs
    work: Path
    m7m: Path
    zeus: Path
    valet: Path
    nexus: Path
    port: int = field(default_factory=free_port)        # valet, the stack's front door
    # nexus's store: zeus passes MAUSOLEUM_PORT on to its workers (#3065).
    # Every zeus here gets it, or its nexus dials 127.0.0.1:7777: some other
    # stack's mausoleum.
    store_port: int = field(default_factory=free_port)
    # A second mausoleum, --no-encryption, for MAUSOLEUM_PLAINTEXT (#2466).
    plain_port: int = field(default_factory=free_port)
    slug: str = field(default_factory=lambda: f"smoke-{os.getpid()}")
    zeus_proc: subprocess.Popen | None = None  # the first stack's zeus
    created: bool = False

    @property
    def data(self) -> Path:
        return self.work / "m7m"

    @property
    def plain_data(self) -> Path:
        return self.work / "m7m-plain"

    @property
    def sock(self) -> Path:
        return self.work / "zeus.sock"

    @property
    def store_env(self) -> dict[str, str]:
        return {"MAUSOLEUM_HOST": "127.0.0.1", "MAUSOLEUM_PORT": str(self.store_port)}

    @property
    def first(self) -> str:
        return f"first-{self.slug}-body"

    @property
    def second(self) -> str:
        return f"second-{self.slug}-body"


# --------------------------------------------------------------------------
# Bringing the stack up and down
# --------------------------------------------------------------------------

def _start_store(ctx: StackCtx, plaintext: bool) -> subprocess.Popen:
    m_port, m_data = (ctx.plain_port, ctx.plain_data) if plaintext else (ctx.store_port, ctx.data)
    m_argv = [str(ctx.m7m), "serve", "-p", str(m_port), "-d", str(m_data)]
    if plaintext:
        m_argv.append("--no-encryption")
    # A restart reuses the port, so it can race the old socket's
    # teardown; retry a bind failure briefly rather than flake.
    for attempt in range(6):
        m = ctx.procs.start("stack-mausoleum", m_argv, ctx.work)
        try:
            wait_listening(m, m_port)
            return m
        except Broken:
            ctx.procs.stop(m)
            if attempt == 5 or "Failed to bind" not in log_tail(m):
                raise
            time.sleep(0.5)
    raise AssertionError("unreachable")


def _wait_health(ctx: StackCtx, z: subprocess.Popen) -> None:
    """Both workers attached: /health answers through zeus."""
    deadline = time.monotonic() + START_TIMEOUT
    while True:
        try:
            if http_req(ctx.port, "GET", "/health", timeout=1)[0] == 200:
                break
        except OSError:
            pass
        if time.monotonic() > deadline:
            raise Broken(f"/health never answered 200 through zeus: {log_tail(z)}")
        time.sleep(0.1)
    time.sleep(0.3)


def up(ctx: StackCtx, with_store: bool = True, plaintext: bool = False,
       env: dict[str, str] | None = None) -> list[subprocess.Popen]:
    """valet -> zeus -> nexus, plus a mausoleum unless with_store is False.

    plaintext: that mausoleum runs --no-encryption on plain_port, and zeus
    is pointed there; env: extra variables for zeus (and so nexus).
    """
    if ctx.sock.exists():
        ctx.sock.unlink()
    m_port = ctx.plain_port if plaintext else ctx.store_port
    zeus_env = {**ctx.store_env, "MAUSOLEUM_PORT": str(m_port), **(env or {})}
    m = _start_store(ctx, plaintext) if with_store else None
    z = ctx.procs.start("stack-zeus", [str(ctx.zeus), "-f", "-w", "2", "-s", str(ctx.sock),
                                       "-p", str(ctx.work / "zeus.pid"), str(ctx.nexus)], ctx.work,
                        env=zeus_env)
    wait_path(z, ctx.sock)
    v = ctx.procs.start("stack-valet", [str(ctx.valet), "-p", str(ctx.port), "-z", str(ctx.sock)], ctx.work)
    wait_listening(v, ctx.port)
    _wait_health(ctx, z)
    return [v, z] + ([m] if m is not None else [])


def down(ctx: StackCtx, ps: list[subprocess.Popen]) -> None:
    for p in ps:
        ctx.procs.stop(p, signal.SIGTERM)


def gets(ctx: StackCtx, want: str) -> list[str]:
    seen = []
    for _ in range(4):
        st, _, body, _ = http_req(ctx.port, "GET", f"/wiki/{ctx.slug}")
        seen.append(f"{st}{'' if want.encode() in body else '(stale)'}" if st == 200 else str(st))
    return seen


# --------------------------------------------------------------------------
# Checks against the first stack
# --------------------------------------------------------------------------

def health(ctx: StackCtx) -> None:
    st = http_req(ctx.port, "GET", "/health")[0]
    if st != 200:
        raise CheckFailed(f"/health -> {st}")


def index(ctx: StackCtx) -> None:
    st, _, body, _ = http_req(ctx.port, "GET", "/")
    if st != 200 or b"<" not in body:
        raise CheckFailed(f"GET / -> {st} {short(body, 60)}")


def store_connected(ctx: StackCtx) -> None:
    time.sleep(0.2)
    log = log_text(ctx.zeus_proc)
    n = log.count("Connected to mausoleum")
    if n < 2:
        raise CheckFailed(f"{n} of 2 workers logged 'Connected to mausoleum': {log_tail(ctx.zeus_proc, 4)}")


def create(ctx: StackCtx) -> None:
    st, _, body, _ = http_req(ctx.port, "POST", "/wiki",
                                 body=f"slug={ctx.slug}&content={ctx.first}".encode(), headers=FORM)
    if st != 303:
        raise CheckFailed(f"POST /wiki -> {st} {short(body, 60)} (want 303)")


def read_4x(ctx: StackCtx) -> None:
    seen = gets(ctx, ctx.first)
    if seen != ["200"] * 4:
        raise CheckFailed(f"4 GETs -> {', '.join(seen)}")


def edit_post(ctx: StackCtx) -> None:
    st, _, body, _ = http_req(ctx.port, "POST", f"/wiki/{ctx.slug}",
                              body=f"content={ctx.second}".encode(), headers=FORM)
    if st not in (200, 303):
        raise CheckFailed(f"POST /wiki/{ctx.slug} -> {st} {short(body, 60)} (want 303)")


def edit_4x(ctx: StackCtx) -> None:
    seen = gets(ctx, ctx.second)
    if seen != ["200"] * 4:
        raise CheckFailed(f"4 GETs after edit -> {', '.join(seen)}")


def keepalive_100(ctx: StackCtx) -> None:
    # valet closes a connection after 100 responses. Through zeus it used
    # to pass on the worker's "Connection: keep-alive" for the 100th too,
    # then close: the client's next request was a read error, ~1% of all
    # requests under wrk (#2459).
    conn = http.client.HTTPConnection("127.0.0.1", ctx.port, timeout=5)
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


def log_lines(ctx: StackCtx) -> None:
    # Workers share stdout; a line written in pieces interleaved with the
    # other worker's ("...Spire at 7127.0.0.11:87777", #2459).
    log = log_text(ctx.zeus_proc)
    lines = [ln for ln in log.splitlines() if "Connecting to mausoleum" in ln]
    want = re.compile(rf"\[nexus \d+\] \[STORE\] Connecting to mausoleum via Spire at 127\.0\.0\.1:{ctx.store_port}")
    bad = [ln for ln in lines if not want.fullmatch(ln)]
    if len(lines) < 2 or bad:
        raise CheckFailed(f"{len(lines)} connect lines, malformed: {short(' | '.join(bad), 160)}")


def wrk_index(ctx: StackCtx) -> str:
    # 64 connections on / through zeus -w 2 (#2464). ResponseSlot was 56
    # bytes in a ring sized for 48, so response slots 220-255 overlapped
    # arena slot 0: nexus's page body clobbered response ids, the
    # response ring filled, nexus acked requests it never answered, and
    # every request after was a 504 until restart.
    out = run_cmd([WRK, "-t4", "-c64", "-d10s", "--timeout", "2s",
                   f"http://127.0.0.1:{ctx.port}/"], ctx.work, timeout=30).stdout.decode(errors="replace")
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
    after = [http_req(ctx.port, "GET", p)[0] for p in ("/health", "/")]
    if after != [200, 200]:
        raise CheckFailed(f"after wrk: /health, / -> {after} (want 200s)")
    return f"{n.group(1)} requests, 0 timeouts, 0 non-2xx"


# --------------------------------------------------------------------------
# Checks that bring up a stack of their own
# --------------------------------------------------------------------------

def restart(ctx: StackCtx) -> None:
    if not ctx.created:
        raise Broken("the page was never created")
    ps2 = up(ctx)
    try:
        seen = gets(ctx, "")  # either revision: persistence, not editing
    finally:
        down(ctx, ps2)
    if seen != ["200"] * 4:
        raise CheckFailed(f"after restarting the stack, 4 GETs -> {', '.join(seen)}")


def no_store(ctx: StackCtx) -> None:
    # No mausoleum, 2 workers: each would serve a private in-memory wiki,
    # so a page created on one is a 404 on the next request (#2459).
    # Every page request must fail instead, with a 503.
    ps3 = up(ctx, with_store=False)
    try:
        seen = [http_req(ctx.port, "GET", "/wiki/welcome")[0] for _ in range(4)]
        post = http_req(ctx.port, "POST", "/wiki", body=f"slug={ctx.slug}-x&content=x".encode(), headers=FORM)[0]
        log = log_text(ps3[1])
    finally:
        down(ctx, ps3)
    if seen != [503] * 4 or post != 503:
        raise CheckFailed(f"4 GETs -> {seen}, POST /wiki -> {post} (want 503s)")
    if log.count("REFUSING to serve pages") < 2:
        raise CheckFailed(f"workers did not log why they refuse: {short(log[-200:], 200)}")


def plaintext_store(ctx: StackCtx) -> None:
    # MAUSOLEUM_PLAINTEXT=1: nexus speaks plaintext Spire to a mausoleum
    # running --no-encryption (#2466). Before, nothing could switch it.
    ps4 = up(ctx, plaintext=True, env={"MAUSOLEUM_PLAINTEXT": "1"})
    try:
        page = f"{ctx.slug}-plain"
        post = http_req(ctx.port, "POST", "/wiki", body=f"slug={page}&content=plain-{ctx.slug}".encode(),
                        headers=FORM)[0]
        seen = []
        for _ in range(4):
            st, _, body, _ = http_req(ctx.port, "GET", f"/wiki/{page}")
            seen.append(str(st) if st != 200 or f"plain-{ctx.slug}".encode() in body else "200(stale)")
        log = log_text(ps4[1])
    finally:
        down(ctx, ps4)
    want = f"Spire at 127.0.0.1:{ctx.plain_port} (plaintext)"
    if log.count(want) < 2 or log.count("Connected to mausoleum") < 2:
        raise CheckFailed(f"workers did not connect in plaintext ({want!r}): {short(log[-240:], 240)}")
    if post != 303 or seen != ["200"] * 4:
        raise CheckFailed(f"POST /wiki -> {post}, 4 GETs -> {', '.join(seen)} (want 303, 200s)")


def encrypted_vs_plaintext_hint(ctx: StackCtx) -> None:
    # Without the switch, nexus's encrypted handshake gets no reply from a
    # --no-encryption mausoleum: every page request fails, and the log
    # says why (wiki_store_connect_hint), not just "error -6".
    ps5 = up(ctx, plaintext=True)
    try:
        st = http_req(ctx.port, "GET", "/wiki/welcome")[0]
        log = log_text(ps5[1])
    finally:
        down(ctx, ps5)
    if "is it running with --no-encryption?" not in log:
        raise CheckFailed(f"no handshake hint in the log: {short(log[-240:], 240)}")
    if st != 503:
        raise CheckFailed(f"GET /wiki/welcome -> {st} (want 503)")


def plaintext_bad_value(ctx: StackCtx) -> None:
    # An unknown MAUSOLEUM_PLAINTEXT refuses to serve, never ignored: the
    # (encrypted) store is up and would otherwise be reached.
    ps6 = up(ctx, env={"MAUSOLEUM_PLAINTEXT": "yes"})
    try:
        st = http_req(ctx.port, "GET", "/wiki/welcome")[0]
        log = log_text(ps6[1])
    finally:
        down(ctx, ps6)
    if log.count("MAUSOLEUM_PLAINTEXT is not 1") < 2 or "Connected to mausoleum" in log:
        raise CheckFailed(f"workers did not refuse MAUSOLEUM_PLAINTEXT=yes: {short(log[-240:], 240)}")
    if st != 503:
        raise CheckFailed(f"GET /wiki/welcome -> {st} (want 503)")


OWN_STACK = (("restart", restart), ("no_store_503", no_store), ("plaintext_store", plaintext_store),
             ("plaintext_hint", encrypted_vs_plaintext_hint), ("plaintext_bad_value", plaintext_bad_value))


# --------------------------------------------------------------------------
# The suite
# --------------------------------------------------------------------------

def _run(r: Reporter, ctx: StackCtx, name: str, fn) -> str:
    return r.run(f"stack.{name}", partial(fn, ctx))


def _first_stack(r: Reporter, ctx: StackCtx) -> None:
    """The checks against the stack `up()` brought up first."""
    _run(r, ctx, "health", health)
    _run(r, ctx, "index", index)
    _run(r, ctx, "store_connected", store_connected)
    ctx.created = _run(r, ctx, "create", create) == PASS
    _run(r, ctx, "read_4x", read_4x)
    if _run(r, ctx, "edit_post", edit_post) == PASS:
        _run(r, ctx, "edit_4x", edit_4x)
    else:
        r.broken("stack.edit_4x", "the edit POST failed, so there is no edit to read back")
    _run(r, ctx, "keepalive_100", keepalive_100)
    _run(r, ctx, "log_lines", log_lines)
    if WRK:
        _run(r, ctx, "wrk_index", wrk_index)
    elif os.environ.get("GITHUB_ACTIONS"):
        r.broken("stack.wrk_index", "wrk is not on PATH; main.yml's 'Install test tools' step installs it")
    else:
        r.skip("stack.wrk_index", "wrk is not on PATH (apt install wrk)")


def suite_stack(r: Reporter, procs: Procs, tmp: Path) -> None:
    try:
        ctx = StackCtx(procs, tmp / "stack", binary("mausoleum/build/debug/mausoleum"),
                       binary("zeus/build/debug/zeus"), binary("valet/build/debug/valet"),
                       binary("nexus/build/debug/nexus"))
    except Broken as e:
        r.broken("stack.start", str(e))
        return
    ctx.data.mkdir(parents=True)
    ctx.plain_data.mkdir()
    try:
        ps = up(ctx)
    except Broken as e:
        r.broken("stack.start", str(e))
        return
    ctx.zeus_proc = ps[1]
    _first_stack(r, ctx)
    down(ctx, ps)
    for name, fn in OWN_STACK + stack_zeus.CHECKS:
        _run(r, ctx, name, fn)
