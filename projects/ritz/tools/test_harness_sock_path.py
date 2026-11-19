"""Shell harnesses must bind their unix sockets where the path fits (#4135).

AGAST #4274 (below): under $TMPDIR when it fits, else $XDG_RUNTIME_DIR,
else /tmp; never a hardcoded /tmp that a full tmpfs breaks.

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
import shutil
import signal
import subprocess
import tempfile
import textwrap
from pathlib import Path

import pytest

# Every test here runs bench/run.sh or e2e_large_page.sh (AGAST #4092: spawn_guard).
pytestmark = pytest.mark.integration

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


# AGAST #4274: a hardcoded /tmp socket dir broke every gate on bangerang when
# /tmp ran out of inodes (`mktemp: No space left on device`).  Both harnesses
# now take their socket dir from sock_dir(): $TMPDIR when the path fits
# sun_path, else $XDG_RUNTIME_DIR, else /tmp -- and the next candidate when a
# mktemp fails.  The function is the same text in both scripts.
TIER1_SH = REPO / "projects" / "harland" / "tools" / "test_tier1_boot.sh"
SOCK_DIR_SCRIPTS = (E2E_SH, TIER1_SH)


def _sock_dir_fn(script: Path) -> str:
    m = re.search(r"^sock_dir\(\) \{\n.*?^\}\n", script.read_text(), re.MULTILINE | re.DOTALL)
    assert m, f"{script.name} defines no sock_dir()"
    return m.group(0)


def _sock_dir(script: Path, env: dict, prefix: str = "rz_t", namelen: int = 9):
    r = subprocess.run(
        ["bash", "-c", _sock_dir_fn(script) + f'sock_dir {prefix} {namelen}'],
        capture_output=True, text=True, timeout=10, env=env, check=False,
    )
    return r.returncode, r.stdout.strip(), r.stderr


def test_sock_dir_is_one_function_shared_by_both_harnesses():
    assert _sock_dir_fn(E2E_SH) == _sock_dir_fn(TIER1_SH)


@pytest.mark.parametrize("script", SOCK_DIR_SCRIPTS, ids=lambda p: p.name)
def test_harness_takes_its_socket_dir_from_sock_dir_not_a_hardcoded_tmp(script):
    text = script.read_text()
    assert not re.search(r"mktemp\s+-d\s+/tmp/", text), f"{script.name} still hardcodes /tmp"
    assert re.search(r'^SOCK_DIR="\$\(sock_dir \w+ \d+\)" \|\| exit 1$', text, re.MULTILINE), script.name


def _clean_env(**kw) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("TMPDIR", "XDG_RUNTIME_DIR")}
    env.update({k: str(v) for k, v in kw.items() if v is not None})
    return env


def test_sock_dir_honours_a_short_tmpdir(tmp_path):
    short = Path(tempfile.mkdtemp(prefix="rzs", dir="/tmp"))
    try:
        rc, d, err = _sock_dir(E2E_SH, _clean_env(TMPDIR=short, XDG_RUNTIME_DIR=tmp_path))
        assert rc == 0, err
        assert Path(d).parent == short and Path(d).is_dir(), d
    finally:
        shutil.rmtree(short)


def test_sock_dir_skips_a_long_tmpdir_for_xdg_runtime_dir(tmp_path):
    runtime = Path(tempfile.mkdtemp(prefix="rzx", dir="/tmp"))
    try:
        rc, d, err = _sock_dir(E2E_SH, _clean_env(TMPDIR=_long_tmpdir(tmp_path), XDG_RUNTIME_DIR=runtime))
        assert rc == 0, err
        assert Path(d).parent == runtime, d
    finally:
        shutil.rmtree(runtime)


def test_sock_dir_falls_through_when_mktemp_fails(tmp_path):
    # A full /tmp is what #4274 saw; an unwritable TMPDIR fails mktemp the
    # same way, and the next candidate (here XDG_RUNTIME_DIR) is used.
    full = tmp_path / "full"
    full.mkdir()
    full.chmod(0o500)
    runtime = Path(tempfile.mkdtemp(prefix="rzx", dir="/tmp"))
    try:
        rc, d, err = _sock_dir(E2E_SH, _clean_env(TMPDIR=full, XDG_RUNTIME_DIR=runtime))
        assert rc == 0, err
        assert Path(d).parent == runtime, d
    finally:
        full.chmod(0o700)
        shutil.rmtree(runtime)


def test_sock_dir_ends_at_tmp(tmp_path):
    rc, d, err = _sock_dir(E2E_SH, _clean_env(TMPDIR=_long_tmpdir(tmp_path)))
    assert rc == 0, err
    try:
        assert Path(d).parent == Path("/tmp"), d
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_sock_dir_path_plus_name_always_fits_sun_path():
    # A TMPDIR exactly at the limit for prefix + name is used; one byte
    # longer is skipped.  Bases under /tmp: a gate's tmp_path is too deep.
    prefix, namelen = "rz_t", 30
    room = SUN_PATH_MAX - len("/" + prefix + ".XXXXXXXX/") - namelen
    top = Path(tempfile.mkdtemp(prefix="rze", dir="/tmp"))
    try:
        edge = top / ("e" * (room - len(os.fsencode(top)) - 1))
        over = Path(str(edge) + "x")
        edge.mkdir()
        over.mkdir()
        assert len(os.fsencode(edge)) == room
        rc, d, err = _sock_dir(E2E_SH, _clean_env(TMPDIR=edge), prefix, namelen)
        assert rc == 0 and Path(d).parent == edge, (d, err)
        assert len(os.fsencode(d)) + 1 + namelen == SUN_PATH_MAX, d
        rc, d, err = _sock_dir(E2E_SH, _clean_env(TMPDIR=over), prefix, namelen)
        assert rc == 0 and Path(d).parent != over, (d, err)
        if not str(d).startswith(str(top)):
            shutil.rmtree(d, ignore_errors=True)
    finally:
        shutil.rmtree(top)
