"""mausoleum: wiki-seed writes, restart on the same --data-dir, read back;
wiki-seed exit codes; the encrypted protocol; the shell."""

from __future__ import annotations

import os
import re
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from .harness import (
    IO_TIMEOUT,
    PASS,
    Broken,
    CheckFailed,
    Procs,
    Reporter,
    binary,
    free_port,
    log_tail,
    run_cmd,
    short,
    wait_listening,
)

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
# The suite's shared state, and the servers and wiki-seed runs it drives
# --------------------------------------------------------------------------

@dataclass
class MausCtx:
    procs: Procs
    m7m: Path    # the mausoleum binary
    seed: Path   # wiki-seed
    work: Path
    port: int = 0           # the first (plaintext) server, seeded and then restarted
    data: Path | None = None
    seeded: bool = False
    porte: int = 0          # the encrypted server
    pe: subprocess.Popen | None = None


def serve(ctx: MausCtx, data: Path, port: int, encrypted: bool = False) -> subprocess.Popen:
    data.mkdir(exist_ok=True)
    argv = [str(ctx.m7m), "serve", "-p", str(port), "-d", str(data)]
    if not encrypted:
        argv.append("--no-encryption")
    p = ctx.procs.start(f"mausoleum-{port}", argv, ctx.work)
    wait_listening(p, port)
    return p


def seed_cmd(ctx: MausCtx, port: int, *flags: str, encrypted: bool = False) -> subprocess.CompletedProcess:
    # wiki-seed speaks the encrypted protocol by default, like the server.
    mode = [] if encrypted else ["--no-encryption"]
    return run_cmd([str(ctx.seed), "-p", str(port), *mode, *flags], ctx.work)


def verified(res: subprocess.CompletedProcess) -> bool:
    return res.returncode == 0 and b"[OK]" in res.stdout and b"[FAIL]" not in res.stdout


def shell(ctx: MausCtx, stdin: bytes, *flags: str) -> subprocess.CompletedProcess:
    """`mausoleum shell` against the encrypted server."""
    return run_cmd([str(ctx.m7m), "shell", "-p", str(ctx.porte), *flags], ctx.work, stdin=stdin)


# --------------------------------------------------------------------------
# Checks: write -> read while up -> restart -> read; exit codes
# --------------------------------------------------------------------------

def do_seed(ctx: MausCtx) -> None:
    res = seed_cmd(ctx, ctx.port, "--seed")
    if res.returncode != 0 or b"Created" not in res.stdout:
        raise CheckFailed(f"wiki-seed --seed -> exit {res.returncode}: {short(res.stdout, 120)}")


def verify_live(ctx: MausCtx) -> None:
    res = seed_cmd(ctx, ctx.port, "--verify")
    if not verified(res):
        raise CheckFailed(f"wiki-seed --verify -> exit {res.returncode}: {short(res.stdout, 120)}")


def restart_term(ctx: MausCtx) -> None:
    if not ctx.seeded:
        raise Broken("nothing was seeded")
    port2 = free_port()  # same --data-dir; a fresh port isolates persistence from bind/TIME_WAIT
    p2 = serve(ctx, ctx.data, port2)
    try:
        res = seed_cmd(ctx, port2, "--verify")
    finally:
        ctx.procs.stop(p2)
    if not verified(res):
        raise CheckFailed(f"after SIGTERM + restart, --verify -> {short(res.stdout, 120)}")


def restart_kill9(ctx: MausCtx) -> None:
    port9 = free_port()
    data9 = ctx.work / "data-kill9"
    p9 = serve(ctx, data9, port9)
    res = seed_cmd(ctx, port9, "--seed")
    if res.returncode != 0:
        ctx.procs.stop(p9)
        raise Broken(f"seeding the kill -9 server failed: {short(res.stdout)}")
    ctx.procs.stop(p9, signal.SIGKILL)
    port9 = free_port()
    p9 = serve(ctx, data9, port9)
    try:
        res = seed_cmd(ctx, port9, "--verify")
    finally:
        ctx.procs.stop(p9)
    if not verified(res):
        raise CheckFailed(f"after kill -9 + restart, --verify -> {short(res.stdout, 120)}")


def _sigterm_mid_request(pg: subprocess.Popen, portg: int) -> int:
    """One idle keep-alive client and one half-sent PING at the SIGTERM;
    returns the server's exit code."""
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
        return pg.wait(timeout=3)
    except subprocess.TimeoutExpired:
        raise CheckFailed(f"still running 3s after its last request: {log_tail(pg, 3)}") from None
    finally:
        idle.close()
        busy.close()


def term_graceful(ctx: MausCtx) -> None:
    # #2463: SIGTERM to the default (io_uring) loop must drain and shut
    # down cleanly. At the signal one client sits idle on a keep-alive
    # connection and another is half-way through sending a PING. The
    # PING is still answered, a connection made after the signal is not
    # served, and the process exits 0 well inside the 5s drain deadline
    # (it must not wait on the idle client) with storage checkpointed.
    portg = free_port()
    datag = ctx.work / "data-graceful"
    pg = serve(ctx, datag, portg)
    try:
        res = seed_cmd(ctx, portg, "--seed")
        if res.returncode != 0:
            raise Broken(f"seeding failed: {short(res.stdout)}")
        if wal_bytes(datag) <= WAL_CHECKPOINT_ONLY_SIZE:
            raise Broken(f"seeding left no WAL records to checkpoint ({wal_bytes(datag)} bytes)")
        code = _sigterm_mid_request(pg, portg)
    finally:
        ctx.procs.stop(pg)
    check_clean_exit(pg, code, datag)


def verify_fail_exit(ctx: MausCtx) -> None:
    porte = free_port()
    pe = serve(ctx, ctx.work / "data-empty", porte)
    try:
        res = seed_cmd(ctx, porte, "--verify")
    finally:
        ctx.procs.stop(pe)
    if b"[FAIL]" not in res.stdout and b"not found" not in res.stdout.lower():
        raise Broken(f"--verify on an empty store did not report a miss: {short(res.stdout)}")
    if res.returncode == 0:
        raise CheckFailed(f"--verify reported a missing page and exited 0: {short(res.stdout, 90)}")


def unreachable_exit(ctx: MausCtx) -> None:
    res = seed_cmd(ctx, free_port(), "--verify")  # nothing listens there
    if res.returncode == 0:
        raise CheckFailed(f"no server, exit 0: {short(res.stdout, 90)}")


# --------------------------------------------------------------------------
# Checks: the default (encrypted) protocol and the shell
# --------------------------------------------------------------------------

def seed_encrypted(ctx: MausCtx) -> None:
    a = seed_cmd(ctx, ctx.porte, "--seed", encrypted=True)
    b = seed_cmd(ctx, ctx.porte, "--verify", encrypted=True)
    if a.returncode != 0 or not verified(b):
        raise CheckFailed(f"--seed exit {a.returncode}: {short(a.stdout, 70)}; "
                          f"--verify exit {b.returncode}: {short(b.stdout, 70)}")


def shell_handshake(ctx: MausCtx) -> None:
    res = shell(ctx, b"quit\n")
    if res.returncode != 0 or b"Encrypted session established" not in res.stdout:
        raise CheckFailed(f"shell -> exit {res.returncode}: {short(res.stdout, 120)}")


def shell_ping(ctx: MausCtx) -> None:
    res = shell(ctx, b"ping\nquit\n")
    if res.returncode != 0 or b"pong" not in res.stdout.lower():
        raise CheckFailed(f"shell 'ping' -> exit {res.returncode}: {short(res.stdout[-90:], 90)}")


def shell_commands(ctx: MausCtx) -> None:
    res = shell(ctx, b"help\nquit\n")
    out = res.stdout.decode(errors="replace").lower()
    missing = [c for c in ("put", "get", "delete", "list") if not re.search(rf"\b{c}\b", out)]
    if missing:
        raise CheckFailed(f"shell lacks {', '.join(missing)}: {short(res.stdout, 100)}")


def shell_crud(ctx: MausCtx) -> None:
    # put -> list -> get -> delete -> get, by id, over the encrypted protocol.
    res = shell(ctx, b'put slug=smoke title="Smoke test" n=7\nlist\nquit\n')
    out = res.stdout.decode(errors="replace")
    m = re.search(r"inserted (\d+)", out)
    if res.returncode != 0 or not m or not re.search(rf"^(m7m> )*{m.group(1)}\s.*slug=\"smoke\"", out, re.MULTILINE):
        raise CheckFailed(f"shell put/list -> exit {res.returncode}: {short(res.stdout[-120:], 120)}")
    doc = m.group(1)
    res = shell(ctx, f"get {doc}\ndelete {doc}\nquit\n".encode())
    out = res.stdout.decode(errors="replace")
    if res.returncode != 0 or 'title = "Smoke test"' not in out or f"deleted {doc}" not in out:
        raise CheckFailed(f"shell get/delete -> exit {res.returncode}: {short(res.stdout[-120:], 120)}")
    res = shell(ctx, f"get {doc}\nquit\n".encode())
    if res.returncode == 0 or b"not found" not in res.stdout:
        raise CheckFailed(f"shell get after delete -> exit {res.returncode}: {short(res.stdout[-90:], 90)}")


def shell_collection(ctx: MausCtx) -> None:
    # #3682: `--collection a` CONNECTs to "a"; without it the shell is on the
    # default collection, so a row put into "a" shows up only under "a".
    res = shell(ctx, b'put slug=only-in-a\nquit\n', "--collection", "a")
    m = re.search(r"inserted (\d+)", res.stdout.decode(errors="replace"))
    if res.returncode != 0 or not m:
        raise CheckFailed(f"shell --collection a put -> exit {res.returncode}: {short(res.stdout[-120:], 120)}")
    res = shell(ctx, b"list\nquit\n", "--collection", "a")
    if res.returncode != 0 or b'slug="only-in-a"' not in res.stdout:
        raise CheckFailed(f"shell --collection a list -> exit {res.returncode}: {short(res.stdout[-120:], 120)}")
    res = shell(ctx, b"list\nquit\n")
    if res.returncode != 0 or b"only-in-a" in res.stdout:
        raise CheckFailed(f"default shell sees collection a -> exit {res.returncode}: {short(res.stdout[-120:], 120)}")
    # The default is the store's default collection (not one named "shell"):
    # a row put with no flag is listed under `--collection default`.
    res = shell(ctx, b"put slug=in-default\nquit\n")
    if res.returncode != 0:
        raise CheckFailed(f"default shell put -> exit {res.returncode}: {short(res.stdout[-120:], 120)}")
    res = shell(ctx, b"list\nquit\n", "--collection", "default")
    if res.returncode != 0 or b'slug="in-default"' not in res.stdout:
        raise CheckFailed(f"shell --collection default misses the default shell's row -> exit {res.returncode}: "
                          f"{short(res.stdout[-120:], 120)}")


def term_graceful_encrypted(ctx: MausCtx) -> None:
    if wal_bytes(ctx.work / "data-enc") <= WAL_CHECKPOINT_ONLY_SIZE:
        raise Broken("the encrypted server's writes left no WAL records to checkpoint")
    os.killpg(ctx.pe.pid, signal.SIGTERM)
    try:
        code = ctx.pe.wait(timeout=3)
    except subprocess.TimeoutExpired:
        raise CheckFailed(f"still running 3s after SIGTERM: {log_tail(ctx.pe, 3)}") from None
    check_clean_exit(ctx.pe, code, ctx.work / "data-enc")


AFTER_RESTART = (("restart_term", restart_term), ("restart_kill9", restart_kill9),
                 ("term_graceful", term_graceful), ("seed_verify_fail_exit", verify_fail_exit),
                 ("seed_unreachable_exit", unreachable_exit))
ENCRYPTED = (("seed_encrypted", seed_encrypted), ("shell_handshake", shell_handshake),
             ("shell_ping", shell_ping), ("shell_commands", shell_commands),
             ("shell_crud", shell_crud), ("shell_collection", shell_collection),
             ("term_graceful_encrypted", term_graceful_encrypted))


def suite_mausoleum(r: Reporter, procs: Procs, tmp: Path) -> None:
    try:
        ctx = MausCtx(procs, binary("mausoleum/build/debug/mausoleum"),
                      binary("mausoleum/build/debug/wiki-seed"), tmp / "mausoleum")
    except Broken as e:
        r.broken("mausoleum.start", str(e))
        return
    ctx.work.mkdir()

    # write -> read while up -> graceful restart -> read
    ctx.port, ctx.data = free_port(), ctx.work / "data-term"
    try:
        p = serve(ctx, ctx.data, ctx.port)
    except Broken as e:
        r.broken("mausoleum.start", str(e))
        return
    ctx.seeded = r.run("mausoleum.seed", partial(do_seed, ctx)) == PASS
    r.run("mausoleum.verify_live", partial(verify_live, ctx))
    procs.stop(p, signal.SIGTERM)
    for name, fn in AFTER_RESTART:
        r.run(f"mausoleum.{name}", partial(fn, ctx))

    # The default (encrypted) protocol.
    ctx.porte = free_port()
    try:
        ctx.pe = serve(ctx, ctx.work / "data-enc", ctx.porte, encrypted=True)
    except Broken as e:
        r.broken("mausoleum.encrypted_start", str(e))
        return
    for name, fn in ENCRYPTED:
        r.run(f"mausoleum.{name}", partial(fn, ctx))
    procs.stop(ctx.pe)
