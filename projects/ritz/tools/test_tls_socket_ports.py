#!/usr/bin/env python3
"""test_tls_socket.sh must test its own valet, not another one (AGAST #3685).

valet sets SO_REUSEPORT on its listener, so a second valet on the same port
binds without error and the kernel splits incoming connections between the
two. test_tls_socket.sh used a fixed port 9143, and 9144 for its second
server. A huburght gate failed "X25519: no HTTP response" because a room was
running the same script with mutated valet builds on 9143 at the same time:
the gate's s_client finished a handshake with the mutant, and the gate's own
valet logged no connection at all. Two copies run with PORT a and a+1
collide the same way, through the second server.

These tests run the script with a stub valet. The stub binds its port the
way valet does and records whether anything was already listening there. A
listener that is already there is exactly the port sharing that broke the
gate.

Run with:
    python3 -m pytest projects/ritz/tools/test_tls_socket_ports.py -q
"""

from __future__ import annotations

import json
import os
import random
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration  # every test starts a process (AGAST #4092)

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "projects/valet/test/test_tls_socket.sh"
# Servers one run starts: the main one (PORT), the short-send one (SPORT) and
# the big-cert-chain one (HPORT, AGAST #3677).
SERVERS = 3

# A stand-in for valet: reads `-c <config>` (relative to its cwd, as valet
# does), records "<port> taken|free" for whether a listener was already on the
# port, then binds it with SO_REUSEPORT and hangs up on every connection.
STUB = r"""#!/usr/bin/env python3
import json, os, socket, sys
cfg = json.load(open(sys.argv[sys.argv.index("-c") + 1]))
port = cfg["server"]["port"]
probe = socket.socket()
probe.settimeout(1)
taken = probe.connect_ex(("127.0.0.1", port)) == 0
probe.close()
with open(os.environ["STUB_LOG"], "a") as f:
    f.write("%d %s\n" % (port, "taken" if taken else "free"))
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
s.bind(("0.0.0.0", port))
s.listen(64)
while True:
    c, _ = s.accept()
    c.close()
"""


def _free_port() -> int:
    """An unused port below the ephemeral range, as the script picks: a port
    the kernel hands out (bind to 0) can be a busy client's local port by the
    time the stub binds it, and then the bind fails."""
    while True:
        port = random.randrange(10000, 32000)
        with socket.socket() as s:
            try:
                s.bind(("0.0.0.0", port))
            except OSError:
                continue
        # The decoys sit on port + 1, so that must be free too.
        with socket.socket() as s:
            try:
                s.bind(("0.0.0.0", port + 1))
            except OSError:
                continue
        return port


class _Decoy:
    """A listener on `port` that shares it the way a second valet would."""

    def __init__(self, port: int):
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.bind(("0.0.0.0", port))
        self.sock.listen(64)
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            c.close()

    def close(self):
        self.sock.close()


@pytest.fixture
def stub(tmp_path):
    path = tmp_path / "valet"
    path.write_text(STUB.replace("/usr/bin/env python3", sys.executable, 1))
    path.chmod(0o755)
    return path


def _run(stub: Path, log: Path, **env) -> subprocess.CompletedProcess:
    full = dict(os.environ, VALET=str(stub), STUB_LOG=str(log), CLIENT_TIMEOUT="1")
    full.pop("PORT", None)
    full.pop("SPORT", None)
    full.pop("HPORT", None)
    full.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT)], env=full, capture_output=True, text=True, timeout=180
    )


def _starts(log: Path) -> list[tuple[int, str]]:
    if not log.exists():
        return []
    return [(int(p), state) for p, state in (ln.split() for ln in log.read_text().splitlines())]


def test_concurrent_runs_never_share_a_port(stub, tmp_path):
    """Two copies at once (two gate slots, or a gate and a room) must each get
    ports nobody else is listening on."""
    logs = [tmp_path / "a.log", tmp_path / "b.log"]
    threads = [threading.Thread(target=_run, args=(stub, log)) for log in logs]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    starts = [_starts(log) for log in logs]
    assert all(len(s) == SERVERS for s in starts), starts
    assert all(state == "free" for s in starts for _, state in s), starts
    ports = [p for s in starts for p, _ in s]
    assert len(set(ports)) == 2 * SERVERS, f"two servers shared a port: {starts}"


def test_second_server_port_is_not_port_plus_one(stub, tmp_path):
    """The short-send server used PORT+1, which is the next copy's PORT when
    copies run on adjacent ports."""
    port = _free_port()
    decoy = _Decoy(port + 1)
    try:
        log = tmp_path / "stub.log"
        _run(stub, log, PORT=str(port))
    finally:
        decoy.close()
    starts = _starts(log)
    assert len(starts) == SERVERS, starts
    assert all(state == "free" for _, state in starts), starts


def test_a_given_port_with_a_listener_is_refused(stub, tmp_path):
    """PORT set by hand to a port something already listens on fails at once,
    naming the port, rather than testing whichever server the kernel picks."""
    port = _free_port()
    decoy = _Decoy(port)
    try:
        log = tmp_path / "stub.log"
        r = _run(stub, log, PORT=str(port))
    finally:
        decoy.close()
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"port {port} already has a listener" in r.stdout + r.stderr
    assert _starts(log) == [], "valet started on a shared port"
    assert "=== Test 1" not in r.stdout


def test_given_ports_are_used(stub, tmp_path):
    """PORT, SPORT and HPORT from the environment are honoured, for a by-hand
    run."""
    ports = set()
    while len(ports) < SERVERS:
        ports.add(_free_port())
    port, sport, hport = sorted(ports)
    log = tmp_path / "stub.log"
    _run(stub, log, PORT=str(port), SPORT=str(sport), HPORT=str(hport))
    assert sorted(p for p, _ in _starts(log)) == [port, sport, hport]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
