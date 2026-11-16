"""valet: GET /, a static file, a directory index, traversal -> 403, HTTPS."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from .harness import (
    Broken,
    CheckFailed,
    Procs,
    Reporter,
    binary,
    free_port,
    http_req,
    run_cmd,
    short,
    wait_listening,
)


@dataclass
class ValetCtx:
    port: int
    token: str  # the static file's contents


def root(ctx: ValetCtx) -> None:
    st, _, body, _ = http_req(ctx.port, "GET", "/")
    if st != 200 or b"Hello" not in body:
        raise CheckFailed(f"GET / -> {st} {short(body, 60)}")


def static(ctx: ValetCtx) -> None:
    st, _, body, _ = http_req(ctx.port, "GET", "/static/test.txt")
    if st != 200 or ctx.token.encode() not in body:
        raise CheckFailed(f"GET /static/test.txt -> {st} {short(body, 60)}")


def dirindex(ctx: ValetCtx) -> None:
    st, _, body, _ = http_req(ctx.port, "GET", "/static/")
    if st != 200 or b"test.txt" not in body:
        raise CheckFailed(f"GET /static/ -> {st} {short(body, 80)}")


def traversal(ctx: ValetCtx) -> None:
    st, _, body, _ = http_req(ctx.port, "GET", "/static/../valet.json")
    if st != 403 or b'"server"' in body:
        raise CheckFailed(f"GET /static/../valet.json -> {st} {short(body, 60)} (want 403)")


def https(p: subprocess.Popen, port: int) -> str:
    wait_listening(p, port)
    st, _, body, version = http_req(port, "GET", "/", tls=True)
    if st != 200 or b"Hello" not in body or version != "TLSv1.3":
        raise CheckFailed(f"HTTPS GET / -> {st} {version} {short(body, 60)}")
    return version


CHECKS = (("root", root), ("static", static), ("dirindex", dirindex), ("traversal", traversal))


def _plain(r: Reporter, procs: Procs, valet: Path, work: Path) -> bool:
    """The plain-HTTP checks; False if valet never listened."""
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
        return False
    ctx = ValetCtx(port, token)
    for name, fn in CHECKS:
        r.run(f"valet.{name}", partial(fn, ctx))
    procs.stop(p)
    return True


def _tls(r: Reporter, procs: Procs, valet: Path, work: Path) -> None:
    """HTTPS with a freshly generated self-signed P-256 certificate."""
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
    r.run("valet.https", partial(https, p, tport))
    procs.stop(p)


def suite_valet(r: Reporter, procs: Procs, tmp: Path) -> None:
    try:
        valet = binary("valet/build/debug/valet")
    except Broken as e:
        r.broken("valet.start", str(e))
        return
    work = tmp / "valet"
    if _plain(r, procs, valet, work):
        _tls(r, procs, valet, work)
