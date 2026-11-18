#!/usr/bin/env python3
"""valet shell tests pick free ports, never fixed ones (AGAST #3694).

valet sets SO_REUSEPORT on its listener, so a second valet on the same port
binds without error and the kernel splits connections between the two. A
room's by-hand run of a fixed-port test could then steal a gate's connections
and flake it (#3685, which fixed test_tls_socket.sh only). Every valet shell
test now takes its ports from projects/valet/test/lib_ports.sh: a random port
nobody listens on, below the ephemeral range, and a port given by hand that
already has a listener is refused, not shared.

test_tls_socket_ports.py covers test_tls_socket.sh's three servers and two
concurrent runs. This file covers the library and that every other script
uses it.

Run with:
    python3 -m pytest projects/ritz/tools/test_valet_test_ports.py -q
"""

from __future__ import annotations

import os
import random
import re
import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
LIB = REPO / "projects/valet/test/lib_ports.sh"

# Every shell test that starts a valet on a TCP port.
SCRIPTS = [
    # Gated (main.yml build-all).
    "projects/valet/test/test_split_request.sh",
    "projects/valet/test/test_framing.sh",
    "projects/valet/test/test_large_echo.sh",
    "projects/valet/test/test_static_conn.sh",
    "projects/valet/test/test_short_send.sh",
    "projects/valet/test/test_tls_socket.sh",
    "projects/nexus/test/e2e_large_page.sh",
    # By hand.
    "projects/valet/test/test_basic.sh",
    "projects/valet/test/test_multishot.sh",
    "projects/valet/test/test_workers.sh",
    "projects/valet/test/test_etag.sh",
    "projects/valet/test/test_range.sh",
    "projects/valet/test/test_dirlist.sh",
    "projects/valet/test/test_middleware.sh",
    "projects/valet/test/test_json_builder.sh",
]

# A stand-in for valet (and zeus/nexus): records that it was started.
STUB = """#!/bin/sh
echo started >> "$STUB_LOG"
exit 1
"""


def _unused_port() -> int:
    """A port below the ephemeral range with nothing bound on it."""
    while True:
        port = random.randrange(10000, 32000)
        with socket.socket() as s:
            try:
                s.bind(("0.0.0.0", port))
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


def _lib(snippet: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f'. "{LIB}"\n{snippet}'],
        capture_output=True,
        text=True,
        timeout=30,
    )


# --- lib_ports.sh -----------------------------------------------------------


def test_pick_port_skips_a_port_with_a_listener():
    """With RANDOM seeded, pick_port's first candidate is known; a listener
    there makes it move on to a free port. (pick_port runs directly, not in
    $(...): bash reseeds RANDOM in a subshell.)"""
    seed = random.randrange(1, 30000)
    first = int(_lib(f"RANDOM={seed}; pick_port").stdout)
    assert 10000 <= first < 32000
    decoy = _Decoy(first)
    try:
        r = _lib(f"RANDOM={seed}; pick_port")
        assert r.returncode == 0, r.stderr
        picked = int(r.stdout)
        assert picked != first
        assert _lib(f"port_taken {picked}").returncode != 0, "picked a taken port"
    finally:
        decoy.close()


def test_pick_port_avoids_the_ports_it_is_given():
    """pick_port A B never returns A or B, so one run's servers differ."""
    seed = random.randrange(1, 30000)
    first = int(_lib(f"RANDOM={seed}; pick_port").stdout)
    r = _lib(f"RANDOM={seed}; pick_port 1 {first}")
    assert r.returncode == 0, r.stderr
    assert int(r.stdout) != first


def test_require_free_port_refuses_a_shared_port():
    port = _unused_port()
    free = _unused_port()
    decoy = _Decoy(port)
    try:
        bad = _lib(f"require_free_port {free} {port}")
        good = _lib(f"require_free_port {free}")
    finally:
        decoy.close()
    assert bad.returncode == 1
    assert f"port {port} already has a listener" in bad.stdout
    assert good.returncode == 0, good.stdout


# --- every script ---------------------------------------------------------

# PORT=9180, PORT="${PORT:-9180}", "port": 9180 and the like.
FIXED = re.compile(r"""PORT=["']?(\$\{\w*PORT:-)?\d{2,5}|"port":\s*\d""")


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_has_no_fixed_port(script):
    text = (REPO / script).read_text()
    assert "lib_ports.sh" in text, f"{script} does not source lib_ports.sh"
    assert not FIXED.search(text), f"{script} fixes a port: {FIXED.search(text).group(0)}"


@pytest.mark.parametrize("script", SCRIPTS)
def test_script_refuses_a_given_port_with_a_listener(script, tmp_path):
    """PORT set by hand to a port a valet already listens on fails at once,
    naming the port, before any server starts."""
    stub = tmp_path / "stub"
    stub.write_text(STUB)
    stub.chmod(0o755)
    log = tmp_path / "stub.log"
    port = _unused_port()
    env = dict(
        os.environ,
        PORT=str(port),
        VALET=str(stub),
        ZEUS=str(stub),
        NEXUS=str(stub),
        STUB_LOG=str(log),
        CLIENT_TIMEOUT="1",
    )
    decoy = _Decoy(port)
    try:
        r = subprocess.run(
            ["bash", str(REPO / script)],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        decoy.close()
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert f"port {port} already has a listener" in out, out
    assert not log.exists(), "a server started on a shared port"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
