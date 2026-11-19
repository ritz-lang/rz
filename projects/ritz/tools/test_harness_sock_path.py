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
# /tmp ran out of inodes (`mktemp: No space left on device`).  Every harness
# now takes its socket dir from sock_dir(): $TMPDIR when the path fits
# sun_path, else $XDG_RUNTIME_DIR, else /tmp -- and the next candidate when a
# mktemp fails.  #4282: one copy, tools/sock_dir.sh, which each one sources.
TIER1_SH = REPO / "projects" / "harland" / "tools" / "test_tier1_boot.sh"
SOCK_DIR_SH = REPO / "projects" / "ritz" / "tools" / "sock_dir.sh"
SOCK_DIR_SCRIPTS = (RUN_SH, E2E_SH, TIER1_SH)


def _sock_dir(script: Path, env: dict, prefix: str = "rz_t", namelen: int = 9):
    # `script` names the harness the row was written for; all share sock_dir.sh.
    del script
    r = subprocess.run(
        ["bash", "-c", f'. "{SOCK_DIR_SH}" && sock_dir {prefix}. {"n" * namelen}'],
        capture_output=True, text=True, timeout=10, env=env, check=False,
    )
    return r.returncode, r.stdout.strip(), r.stderr


@pytest.mark.parametrize("script", SOCK_DIR_SCRIPTS, ids=lambda p: p.name)
def test_harness_sources_the_shared_sock_dir_not_its_own_copy(script):
    text = script.read_text()
    assert not re.search(r"^\s*sock_dir\s*\(\)", text, re.MULTILINE), f"{script.name} defines its own sock_dir()"
    assert re.search(r'^\. "\$\w+/projects/ritz/tools/sock_dir\.sh"$', text, re.MULTILINE), script.name


@pytest.mark.parametrize("script", SOCK_DIR_SCRIPTS, ids=lambda p: p.name)
def test_harness_takes_its_socket_dir_from_sock_dir_not_a_hardcoded_tmp(script):
    text = script.read_text()
    assert not re.search(r"mktemp\s+-d\s+/tmp/", text), f"{script.name} still hardcodes /tmp"
    assert re.search(r'^SOCK_DIR="?\$\(sock_dir [\w.]+ [\w."-]+\)"? \|\| ', text, re.MULTILINE), script.name


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


# --- sock_dir order: $TMPDIR, $XDG_RUNTIME_DIR, /tmp (#4274, #4282) ----------
#
# bench/run.sh (via tools/sock_dir.sh) and smoke_stack's short_sock_dir pick a
# socket dir the same way: the first candidate where <dir>/<name> fits
# sun_path AND mktemp succeeds. A full /tmp (bangerang 2026-11-19, ENOSPC on
# every gate) must not stop a run whose $TMPDIR or $XDG_RUNTIME_DIR is fine.
# Both implementations run the same rows.

SOCK_NAME = "zeus_bench_inmem.sock"  # bench's longest socket name


def _bash_sock_dir(env: dict) -> str:
    r = subprocess.run(
        ["bash", "-c", f'. "{SOCK_DIR_SH}" && sock_dir rz_t_ {SOCK_NAME}'],
        capture_output=True, text=True, timeout=10, env=env, check=False,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def _py_sock_dir(env: dict) -> str:
    tools = REPO / "projects" / "ritz" / "tools"
    r = subprocess.run(
        ["python3", "-I", "-c",
         (f"import sys; sys.path.insert(0, {str(tools)!r}); "
          "from smoke_stack.harness import short_sock_dir; "
          f"print(short_sock_dir({SOCK_NAME!r}, prefix='rz_t_'))")],
        capture_output=True, text=True, timeout=10, env=env, check=False,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


IMPLS = pytest.mark.parametrize("pick", [_bash_sock_dir, _py_sock_dir], ids=["sh", "py"])


def _sd_env(tmpdir, xdg=None) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("TMPDIR", "XDG_RUNTIME_DIR")}
    if tmpdir is not None:
        env["TMPDIR"] = str(tmpdir)
    if xdg is not None:
        env["XDG_RUNTIME_DIR"] = str(xdg)
    return env


@pytest.fixture
def short_base(tmp_path):
    """A short path to tmp_path: a symlink /tmp/rz_tl_XXXXXXXX -> tmp_path.

    sun_path counts the path as written, so a socket under the link fits
    wherever pytest put tmp_path (a gate's basetemp is far past 60 bytes)."""
    for _ in range(10):
        link = Path("/tmp") / f"rz_tl_{os.urandom(4).hex()}"
        try:
            link.symlink_to(tmp_path)
            break
        except FileExistsError:
            continue
        except OSError as e:
            pytest.skip(f"cannot make a short link in /tmp: {e}")
    try:
        yield link
    finally:
        link.unlink()


def _short(tmp_path: Path, name: str) -> Path:
    d = tmp_path / name
    d.mkdir()
    return d


def _check(got: str, parent: Path):
    try:
        assert Path(got).parent == parent, f"{got} not under {parent}"
        assert Path(got).is_dir()
        assert Path(got).name.startswith("rz_t_")
        assert len(os.fsencode(f"{got}/{SOCK_NAME}")) <= SUN_PATH_MAX
    finally:
        if got and Path(got).is_dir() and Path(got).name.startswith("rz_t_"):
            Path(got).rmdir()


@IMPLS
def test_sock_dir_short_tmpdir_is_used(pick, tmp_path, short_base):
    tmpdir = _short(short_base, "t")
    _check(pick(_sd_env(tmpdir, xdg=_short(short_base, "x"))), tmpdir)


@IMPLS
def test_sock_dir_long_tmpdir_falls_to_xdg_runtime_dir(pick, tmp_path, short_base):
    xdg = _short(short_base, "x")
    _check(pick(_sd_env(_long_tmpdir(tmp_path), xdg=xdg)), xdg)


@IMPLS
def test_sock_dir_long_tmpdir_no_xdg_falls_to_tmp(pick, tmp_path):
    _check(pick(_sd_env(_long_tmpdir(tmp_path))), Path("/tmp"))


@IMPLS
def test_sock_dir_long_tmpdir_and_long_xdg_falls_to_tmp(pick, tmp_path):
    _check(pick(_sd_env(_long_tmpdir(tmp_path), xdg=_long_tmpdir(tmp_path / "x"))), Path("/tmp"))


@IMPLS
def test_sock_dir_unwritable_tmpdir_moves_on(pick, tmp_path, short_base):
    # mktemp fails in a dir it cannot write, as it does in a full one.
    if os.geteuid() == 0:
        pytest.skip("root writes anywhere")
    ro = _short(short_base, "ro")
    ro.chmod(0o555)
    xdg = _short(short_base, "x")
    try:
        _check(pick(_sd_env(ro, xdg=xdg)), xdg)
    finally:
        ro.chmod(0o755)


@IMPLS
def test_sock_dir_missing_candidates_move_on(pick, tmp_path):
    # A TMPDIR or XDG_RUNTIME_DIR that does not exist fails mktemp too.
    _check(pick(_sd_env(tmp_path / "gone", xdg=tmp_path / "also_gone")), Path("/tmp"))


@IMPLS
def test_sock_dir_relative_or_empty_candidates_are_skipped(pick, tmp_path):
    # A socket path must not depend on the cwd the server was started in.
    _check(pick(_sd_env("rel", xdg="")), Path("/tmp"))


def test_sock_dir_sh_fails_naming_candidates_when_none_works(tmp_path):
    # SOCK_DIR_LAST overrides /tmp only so this row can make every candidate fail.
    env = _sd_env(tmp_path / "gone", xdg=_long_tmpdir(tmp_path))
    env["SOCK_DIR_LAST"] = str(tmp_path / "no_tmp")
    r = subprocess.run(
        ["bash", "-c", f'. "{SOCK_DIR_SH}" && sock_dir rz_t_ {SOCK_NAME}; echo "rc=$?"'],
        capture_output=True, text=True, timeout=10, env=env, check=False,
    )
    assert "rc=1" in r.stdout, (r.stdout, r.stderr)
    assert "no socket dir" in r.stderr and "gone" in r.stderr and "no_tmp" in r.stderr, r.stderr


def test_short_sock_dir_py_raises_broken_naming_candidates_when_none_works(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(REPO / "projects" / "ritz" / "tools"))
    from smoke_stack import harness
    monkeypatch.setenv("TMPDIR", str(tmp_path / "gone"))
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(_long_tmpdir(tmp_path)))
    monkeypatch.setenv("SOCK_DIR_LAST", str(tmp_path / "no_tmp"))
    with pytest.raises(harness.Broken, match=r"no socket dir.*gone.*no_tmp"):
        harness.short_sock_dir(SOCK_NAME, prefix="rz_t_")


def test_bench_sockets_use_short_tmpdir(tmp_path, short_base):
    # bench/run.sh goes through sock_dir: a short TMPDIR is used, not /tmp.
    tmpdir = _short(short_base, "t")
    r = subprocess.run(
        ["bash", str(RUN_SH), "--dry-run"],
        capture_output=True, text=True, timeout=30, env=_env(tmpdir), check=False,
    )
    socks = dict(re.findall(r"dry-run: socket (\w+)=(\S+)", r.stderr))
    assert set(socks) == {"SOCK_PROXY", "SOCK_PROXY_DB"}, r.stderr
    for name, path in socks.items():
        assert Path(path).parent.parent == tmpdir, f"{name}={path}"


@IMPLS
def test_sock_dir_counts_bytes_not_characters(pick, tmp_path, short_base):
    # sun_path is bytes: a TMPDIR of multibyte characters that fits by
    # character count but not by byte count is skipped (sock_dir.sh runs
    # its arithmetic under LC_ALL=C, as #4274's inline copies did).
    room = SUN_PATH_MAX - len(f"/rz_t_XXXXXXXX/{SOCK_NAME}")
    head = os.fsencode(short_base)
    chars = room - len(head) - 1  # "/" + chars characters == room by character count
    wide = _short(short_base, "é" * chars)
    assert len(str(wide)) == room and len(os.fsencode(wide)) > room
    xdg = _short(short_base, "x")
    env = _sd_env(wide, xdg=xdg)
    env["LC_ALL"] = env["LANG"] = "C.UTF-8"
    _check(pick(env), xdg)
