"""Shell harnesses must bind their unix sockets under /tmp, not $TMPDIR (#4135).

A unix socket path fits in sun_path: 108 bytes with the NUL, so 107 usable.
The gate sets TMPDIR deep in its worktree (.trees/ritz-gate-<name>.tmp), and
a `mktemp -d` socket dir under it left the path ~30 bytes from the limit.
Past it zeus's bind() fails and the harness only says "zeus socket never
appeared".  #4100 fixed smoke_stack the same way (harness.short_sock_dir).

Both cases run with a TMPDIR long enough that any socket under it is over
the limit; neither needs a built server:

  * bench/run.sh --dry-run reports the socket paths it would use;
  * e2e_large_page.sh runs against a fake zeus that really bind()s its -s
    path (so an over-long path fails as it would for zeus) and a fake valet
    that records its argv and stops the script, which then has nothing left
    to test.
"""

import os
import re
import signal
import subprocess
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUN_SH = REPO / "bench" / "run.sh"
E2E_SH = REPO / "projects" / "nexus" / "test" / "e2e_large_page.sh"
SUN_PATH_MAX = 107  # sizeof(sun_path) - 1 for the NUL


def _long_tmpdir(tmp_path: Path) -> Path:
    """A TMPDIR where `mktemp -d`/x.sock is over SUN_PATH_MAX by itself."""
    d = tmp_path / ("t" * 50) / ("m" * 50)
    d.mkdir(parents=True)
    assert len(os.fsencode(d)) > SUN_PATH_MAX
    return d


def _env(tmpdir: Path, **extra) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("BENCH_PORT_")}
    env["TMPDIR"] = str(tmpdir)
    env.update(extra)
    return env


def test_bench_sockets_fit_sun_path_under_long_tmpdir(tmp_path):
    tmpdir = _long_tmpdir(tmp_path)
    r = subprocess.run(
        ["bash", str(RUN_SH), "--dry-run"],
        capture_output=True, text=True, timeout=30, env=_env(tmpdir),
    )
    socks = dict(re.findall(r"dry-run: socket (\w+)=(\S+)", r.stderr))
    assert set(socks) == {"SOCK_PROXY", "SOCK_PROXY_DB"}, r.stderr
    for name, path in socks.items():
        assert len(os.fsencode(path)) <= SUN_PATH_MAX, f"{name}={path}"
        assert not path.startswith(str(tmpdir)), f"{name}={path} under TMPDIR"
        # The EXIT trap removed the run's dir.
        assert not Path(path).parent.exists(), f"{name}: {path} left behind"


FAKE_ZEUS = textwrap.dedent("""\
    #!/usr/bin/env python3
    # bind() the -s path the way zeus does, then wait to be killed.
    import socket, sys, time
    path = sys.argv[sys.argv.index("-s") + 1]
    s = socket.socket(socket.AF_UNIX)
    s.bind(path)  # OSError past sun_path: no socket ever appears
    s.listen(1)
    time.sleep(60)
    """)

FAKE_VALET = textwrap.dedent("""\
    #!/bin/sh
    # The socket check passed: record our argv and stop the script.
    printf '%s\\n' "$@" >"$E2E_VALET_ARGV"
    kill -TERM "$PPID"
    """)


def test_e2e_large_page_socket_fits_sun_path_under_long_tmpdir(tmp_path):
    tmpdir = _long_tmpdir(tmp_path)
    bins = tmp_path / "bin"
    bins.mkdir()
    for name, text in (("zeus", FAKE_ZEUS), ("valet", FAKE_VALET), ("nexus", "#!/bin/sh\n")):
        (bins / name).write_text(text)
        (bins / name).chmod(0o755)
    argv_file = tmp_path / "valet.argv"
    r = subprocess.run(
        ["bash", str(E2E_SH)],
        capture_output=True, text=True, timeout=30,
        env=_env(tmpdir, ZEUS=str(bins / "zeus"), VALET=str(bins / "valet"),
                 NEXUS=str(bins / "nexus"), E2E_VALET_ARGV=str(argv_file)),
    )
    assert "zeus socket never appeared" not in r.stderr, r.stderr
    assert r.returncode == -signal.SIGTERM or r.returncode == 128 + signal.SIGTERM, (r.returncode, r.stderr)
    argv = argv_file.read_text().split("\n")
    sock = argv[argv.index("--zeus-socket") + 1]
    assert len(os.fsencode(sock)) <= SUN_PATH_MAX, sock
    assert not sock.startswith(str(tmpdir)), sock
    # The EXIT trap still removes the dir after a SIGTERM.
    assert not Path(sock).parent.exists(), f"{sock} left behind"
