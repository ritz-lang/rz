"""tome: PING, SET/GET, INCR, a pipelined SET+GET and tome-cli, in the
default io_uring mode AND in blocking mode (-b)."""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from .harness import (
    IO_TIMEOUT,
    Broken,
    CheckFailed,
    Procs,
    Reporter,
    binary,
    free_port,
    run_cmd,
    short,
    wait_listening,
)


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
                except TimeoutError:
                    break
                if not chunk:
                    break
                got += chunk
    except OSError as e:
        raise CheckFailed(f"{type(e).__name__} after {short(got) or 'no reply'}: {e}") from None
    return got


@dataclass
class TomeCtx:
    port: int
    pre: str    # key prefix, one per mode
    cli: Path   # tome-cli
    work: Path


def ping(ctx: TomeCtx) -> None:
    got = resp_exchange(ctx.port, resp_cmd("PING"), b"+PONG\r\n")
    if got != b"+PONG\r\n":
        raise CheckFailed(f"PING -> {short(got) or 'no reply'}")


def set_get(ctx: TomeCtx) -> None:
    # One command per connection: pipelining has its own check.
    got = resp_exchange(ctx.port, resp_cmd("SET", f"{ctx.pre}:k", "world"), b"+OK\r\n")
    if got != b"+OK\r\n":
        raise CheckFailed(f"SET -> {short(got) or 'no reply'}")
    got = resp_exchange(ctx.port, resp_cmd("GET", f"{ctx.pre}:k"), b"$5\r\nworld\r\n")
    if got != b"$5\r\nworld\r\n":
        raise CheckFailed(f"GET -> {short(got) or 'no reply'}")


def incr(ctx: TomeCtx) -> None:
    a = resp_exchange(ctx.port, resp_cmd("INCR", f"{ctx.pre}:n"), b"\r\n")
    b = resp_exchange(ctx.port, resp_cmd("INCR", f"{ctx.pre}:n"), b"\r\n")
    if (a, b) != (b":1\r\n", b":2\r\n"):
        raise CheckFailed(f"INCR, INCR -> {short(a) or 'no reply'}, {short(b) or 'no reply'}")


def pipeline(ctx: TomeCtx) -> None:
    payload = resp_cmd("SET", f"{ctx.pre}:p", "piped") + resp_cmd("GET", f"{ctx.pre}:p")
    want = b"+OK\r\n$5\r\npiped\r\n"
    got = resp_exchange(ctx.port, payload, want)
    if got != want:
        raise CheckFailed(f"SET+GET in one write -> {short(got) or 'no reply'}")


def cli_c(ctx: TomeCtx) -> None:
    resp_exchange(ctx.port, resp_cmd("SET", f"{ctx.pre}:c", "from-cli"), b"+OK\r\n")
    res = run_cmd([str(ctx.cli), "-p", str(ctx.port), "-c", f"GET {ctx.pre}:c"], ctx.work, timeout=4)
    if res.returncode != 0 or b"from-cli" not in res.stdout:
        raise CheckFailed(f"tome-cli -c -> exit {res.returncode}: {short(res.stdout, 90)}")


def cli_stdin(ctx: TomeCtx) -> None:
    resp_exchange(ctx.port, resp_cmd("SET", f"{ctx.pre}:s", "via-stdin"), b"+OK\r\n")
    res = run_cmd([str(ctx.cli), "-p", str(ctx.port)], ctx.work,
                  stdin=f"GET {ctx.pre}:s\nquit\n".encode(), timeout=4)
    if res.returncode != 0 or b"via-stdin" not in res.stdout:
        raise CheckFailed(f"tome-cli <stdin -> exit {res.returncode}: {short(res.stdout, 90)}")


CHECKS = (("ping", ping), ("set_get", set_get), ("incr", incr),
          ("pipeline", pipeline), ("cli", cli_c), ("cli_stdin", cli_stdin))


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
        ctx = TomeCtx(port, f"smoke-{mode}", cli, work)
        for name, fn in CHECKS:
            r.run(f"tome.{mode}.{name}", partial(fn, ctx))
        procs.stop(p)
