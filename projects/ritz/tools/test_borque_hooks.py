"""The hooks .borque/profile.toml names, run the way Borque's hostd runs them (AGAST #3722).

hostd (borque #3711/#3716) creates a room's worktree itself, from its bare
mirror ``~/borque/mirrors/ritz.git`` at ``~/borque/worktrees/ritz-task-<id>``,
and runs each hook as argv with no shell, cwd = that worktree, and a clean
environment: no venv or LLVM on PATH, maybe no PATH, HOME or
XDG_RUNTIME_DIR at all. These tests hold the hooks to that:

  * .claude/provision-room.sh and .claude/host-budget.sh work from that path
    with that environment (each hook is copied into a worktree laid out as
    hostd lays it out and run as ``.claude/<hook>.sh`` from there);
  * provision-room.sh first checks what the host probe can't see (venv
    modules, pytest < 9.2, qemu, OVMF, lld-link, free disk, a scratch
    dir that can run a binary), and on a miss exits non-zero with ONE line naming each problem,
    before it writes anything;
  * .borque/test-borque.sh (the profile and the verify/train-gate wrappers)
    passes.

Nothing here touches the real ~/.claude.json, systemd or venv: HOME,
CLAUDE_CONFIG_DIR, the venvs and the tools are all under tmp_path.

Run with:
    python3 -m pytest projects/ritz/tools/test_borque_hooks.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration  # every test starts a process (AGAST #4092)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
HOOKS = ("provision-room.sh", "host-budget.sh", "host-env.sh")
ROOM = "ritz-task-4242"
# What the hooks run besides the tools under test: a PATH of just these keeps
# the host's own qemu and lld-link out of the refusal tests.
BASICS = (
    "bash",
    "sh",
    "env",
    "python3",
    "git",
    "grep",
    "awk",
    "df",
    "mktemp",
    "chmod",
    "rm",
    "mkdir",
    "cat",
    "id",
    "getent",
    "cut",
    "dirname",
    "basename",
    "mv",
)
GIT = [
    "git",
    "-c",
    "user.name=t",
    "-c",
    "user.email=t@t",
    "-c",
    "init.defaultBranch=main",
]


def _exe(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(0o755)
    return path


@pytest.fixture()
def host(tmp_path: Path) -> dict:
    """A host as Borque leaves it: mirror, room worktree, and the tools a gate needs."""
    home = tmp_path / "home"
    mirror = home / "borque" / "mirrors" / "ritz.git"
    wt = home / "borque" / "worktrees" / ROOM
    src = tmp_path / "src"
    subprocess.run([*GIT, "init", "-q", str(src)], check=True)
    subprocess.run(
        [*GIT, "-C", str(src), "commit", "-q", "--allow-empty", "-m", "x"], check=True
    )
    subprocess.run([*GIT, "clone", "-q", "--bare", str(src), str(mirror)], check=True)
    subprocess.run(
        [*GIT, "-C", str(mirror), "worktree", "add", "-q", "--detach", str(wt)],
        check=True,
    )
    # The hooks at the run's base_sha: what hostd execs, relative to cwd.
    (wt / ".claude").mkdir()
    for name in HOOKS:
        shutil.copy2(REPO / ".claude" / name, wt / ".claude" / name)

    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / ".claude.json").write_text(
        json.dumps({"oauthAccount": {"keep": "me"}, "projects": {}})
    )

    venv = _venv(home / "dev" / ".venv")
    pkgs = venv / "site"

    # Tools where a host keeps them: lld-link in ~/.local/bin (starbux,
    # chungus), qemu in the LLVM bin dir only so it is on no default PATH.
    llvm = tmp_path / "llvm-21" / "bin"
    _exe(home / ".local" / "bin" / "lld-link", "#!/bin/sh\nexit 0\n")
    _exe(llvm / "qemu-system-x86_64", "#!/bin/sh\nexit 0\n")
    ovmf = tmp_path / "OVMF_CODE_4M.fd"
    ovmf.write_text("")
    h = {
        "home": home,
        "wt": wt,
        "mirror": mirror,
        "cj": cfg / ".claude.json",
        "pkgs": pkgs,
        "venv": venv,
        "llvm": llvm,
        # hostd's clean environment, at its barest: no PATH, no XDG_RUNTIME_DIR.
        "env": {
            "HOME": str(home),
            "CLAUDE_CONFIG_DIR": str(cfg),
            "RZ_LLVM_BIN": str(llvm),
            "OVMF_CODE": str(ovmf),
            # tmp_path's filesystem may be a small tmpfs; the disk test sets it.
            "RZ_MIN_DISK_GB": "0",
        },
    }
    _pytest_version(h, "9.1.1")
    return h


def _venv(root: Path, mods: tuple[str, ...] = ("llvmlite", "yaml")) -> Path:
    """A venv whose modules the test controls, at ROOT, with bin/python3.

    -S keeps the real interpreter's site-packages (which may well have
    llvmlite) out of it; ROOT/site stands in for the venv's own."""
    site = root / "site"
    site.mkdir(parents=True)
    for mod in mods:
        (site / mod).mkdir()
        (site / mod / "__init__.py").write_text("")
    for name in ("python3", "python"):
        _exe(
            root / "bin" / name,
            f'#!/bin/sh\nPYTHONPATH="{site}" exec "{sys.executable}" -S "$@"\n',
        )
    _pytest_version(site, "9.1.1")
    return root


def _pytest_version(h: dict | Path, version: str) -> None:
    site = h["pkgs"] if isinstance(h, dict) else h
    for old in site.glob("pytest-*.dist-info"):
        shutil.rmtree(old)
    d = site / f"pytest-{version}.dist-info"
    d.mkdir()
    (d / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: pytest\nVersion: {version}\n"
    )


def _basics_dir(h: dict, without: tuple[str, ...] = ()) -> Path:
    """A dir with only BASICS in it (symlinks to this host's copies)."""
    d = h["home"] / ("basics" + "".join(f"-no-{w}" for w in without))
    if not d.is_dir():
        d.mkdir()
        for name in BASICS:
            if name not in without:
                (d / name).symlink_to(shutil.which(name))
    return d


def _basics(h: dict) -> str:
    """A host's own PATH, as run-gate.sh passes it on: the venv first, then BASICS."""
    return f"{h['venv']}/bin:{_basics_dir(h)}"


def _hook(h: dict, name: str, *args: str, **env: str) -> subprocess.CompletedProcess:
    """``.claude/<name> <args>`` as hostd runs it: argv, cwd = worktree, given env only."""
    e = {**h["env"], **env}
    return subprocess.run(
        [f".claude/{name}", *args],
        cwd=h["wt"],
        env={k: v for k, v in e.items() if v is not None},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _settings(h: dict) -> Path:
    return h["wt"] / ".claude" / "settings.json"


def _projects(h: dict) -> dict:
    return json.loads(h["cj"].read_text()).get("projects", {})


# --------------------------------------------------------------------------
# provision-room.sh
# --------------------------------------------------------------------------


def test_provision_works_from_a_borque_worktree_with_a_clean_env(host):
    # Basics only on PATH: the venv, LLVM and ~/.local/bin come from the hook.
    r = _hook(host, "provision-room.sh", str(host["wt"]), PATH=_basics(host))
    assert r.returncode == 0, r.stderr
    assert _settings(host).is_file()
    assert _projects(host)[str(host["wt"].resolve())]["hasTrustDialogAccepted"] is True
    assert json.loads(host["cj"].read_text())["oauthAccount"] == {"keep": "me"}


def test_provision_works_without_home(host):
    """No HOME: python3 comes from the given PATH, the rest falls back to the passwd entry."""
    llvm = host["llvm"]
    _exe(llvm / "lld-link", "#!/bin/sh\nexit 0\n")
    r = _hook(host, "provision-room.sh", str(host["wt"]), HOME=None, PATH=_basics(host))
    assert r.returncode == 0, r.stderr
    assert _settings(host).is_file()


@pytest.mark.parametrize(
    ("break_it", "reason"),
    [
        (
            lambda h: _exe(h["venv"] / "bin" / "python3", "#!/bin/sh\nexit 3\n"),
            "python3",
        ),
        (lambda h: shutil.rmtree(h["pkgs"] / "llvmlite"), "llvmlite"),
        (lambda h: shutil.rmtree(h["pkgs"] / "yaml"), "yaml"),
        (lambda h: _pytest_version(h, "9.2.0"), "pytest 9.2.0"),
        (lambda h: (h["llvm"] / "qemu-system-x86_64").unlink(), "qemu-system-x86_64"),
        (lambda h: (h["home"] / ".local" / "bin" / "lld-link").unlink(), "lld-link"),
        (lambda h: h["env"].update(OVMF_CODE=str(h["home"] / "nope.fd")), "OVMF"),
        (lambda h: h["env"].update(RZ_MIN_DISK_GB="999999999"), "disk"),
        (
            lambda h: h["env"].update(
                RZ_EXEC_DIRS=f"{h['home']}/no-such-tmp:/nonexistent"
            ),
            "no exec-able scratch dir",
        ),
    ],
    ids=[
        "broken-python3",
        "llvmlite",
        "yaml",
        "pytest-9.2",
        "qemu",
        "lld-link",
        "ovmf",
        "disk",
        "tmpdir",
    ],
)
def test_provision_refuses_a_host_without_what_a_gate_needs(host, break_it, reason):
    before = host["cj"].read_text()
    break_it(host)
    r = _hook(host, "provision-room.sh", str(host["wt"]), PATH=_basics(host))
    assert r.returncode != 0
    lines = r.stderr.strip().splitlines()
    assert len(lines) == 1, r.stderr
    assert reason in lines[0], lines[0]
    # Nothing written: a host that can't gate gets no half-provisioned room.
    assert not _settings(host).exists()
    assert host["cj"].read_text() == before


def test_provision_checks_the_first_python3_on_path(host):
    """omegalisk: the gate's python is ~/dev/nevelis/.venv's, first on PATH
    (run-gate.sh passes PATH on); there is no ~/dev/.venv to look at."""
    shutil.rmtree(host["venv"])
    nev = _venv(host["home"] / "dev" / "nevelis" / ".venv")
    path = f"{nev}/bin:{_basics_dir(host)}"
    r = _hook(host, "provision-room.sh", "--check-host", str(host["wt"]), PATH=path)
    assert r.returncode == 0, r.stderr
    # The python checked is PATH's first, not a good ~/dev/.venv beside it.
    _venv(host["home"] / "dev" / ".venv")
    shutil.rmtree(nev / "site" / "llvmlite")
    r = _hook(host, "provision-room.sh", "--check-host", str(host["wt"]), PATH=path)
    assert r.returncode == 1
    assert "llvmlite" in r.stderr and f"{nev}/bin/python3" in r.stderr, r.stderr


def test_provision_ignores_a_python3_the_hook_itself_puts_on_path(host):
    """~/.local/bin (a pip --user python3, say) and LLVM's bin dir go on PATH
    for lld-link and qemu only: the gate's python3 is looked up before them."""
    _exe(host["home"] / ".local" / "bin" / "python3", "#!/bin/sh\nexit 3\n")
    _exe(host["llvm"] / "python3", "#!/bin/sh\nexit 3\n")
    r = _hook(
        host, "provision-room.sh", "--check-host", str(host["wt"]), PATH=_basics(host)
    )
    assert r.returncode == 0, r.stderr


def test_provision_default_path_adds_the_venvs_in_order(host):
    """No PATH at all (hostd): ~/dev/.venv/bin, then ~/dev/nevelis/.venv/bin,
    whichever exist, go before the system dirs."""
    shutil.rmtree(host["venv"])
    nev = _venv(host["home"] / "dev" / "nevelis" / ".venv")
    r = _hook(host, "provision-room.sh", "--check-host", str(host["wt"]))
    assert r.returncode == 0, r.stderr
    dev = _venv(host["home"] / "dev" / ".venv", mods=("llvmlite",))
    r = _hook(host, "provision-room.sh", "--check-host", str(host["wt"]))
    assert r.returncode == 1
    assert "yaml" in r.stderr and f"{dev}/bin/python3" in r.stderr, r.stderr
    assert str(nev) not in r.stderr


def test_provision_refuses_without_python3_on_path(host):
    path = str(_basics_dir(host, without=("python3",)))
    r = _hook(host, "provision-room.sh", "--check-host", str(host["wt"]), PATH=path)
    assert r.returncode == 1
    assert "no python3 on PATH" in r.stderr, r.stderr


def _noexec_path(h: dict, *dirs: Path | str) -> str:
    """BASICS, but files under DIRS can't run, as on a noexec mount.

    A real noexec mount needs privileges (unshare is refused on starbux), so
    chmod is shimmed to leave files there non-executable: running one then
    fails with EACCES, as it does on noexec.  The file is still written."""
    shim = h["home"] / "noexec-basics"
    if not shim.is_dir():
        shutil.copytree(_basics_dir(h), shim, symlinks=True)
    (shim / "chmod").unlink(missing_ok=True)
    # The probe's own file only, directly in DIR: tmp_path (so HOME) is under /tmp.
    cases = " | ".join(f'"{d}"/rz-exec.*' for d in dirs)
    _exe(
        shim / "chmod",
        "#!/bin/sh\n"
        f'for a; do case "$a" in {cases}) exit 0 ;; esac; done\n'
        f'exec "{shutil.which("chmod")}" "$@"\n',
    )
    return f"{h['venv']}/bin:{shim}"


def test_provision_passes_when_only_a_later_scratch_dir_can_exec(host):
    """bangerang: /tmp is noexec for good, but ~/tmp or the gate dir can run a
    binary, and #3704 gives each gate its own TMPDIR there.  One usable dir
    is enough; an unusable $TMPDIR alone must not refuse the host."""
    noexec, ro, ok = (host["home"] / n for n in ("noexec", "ro-tmp", "tmp"))
    for d in (noexec, ro, ok):
        d.mkdir()
    ro.chmod(0o555)  # unwritable
    r = _hook(
        host,
        "provision-room.sh",
        str(host["wt"]),
        PATH=_noexec_path(host, noexec),
        TMPDIR=str(noexec),
        RZ_EXEC_DIRS=f"{noexec}:{host['home']}/no-such-tmp:{ro}:{ok}",
    )
    assert r.returncode == 0, r.stderr
    for d in (noexec, ok):
        assert not list(d.iterdir()), "the probe must clean up after itself"


def test_provision_refuses_when_every_scratch_dir_is_noexec(host):
    noexec = host["home"] / "noexec"
    noexec.mkdir()
    r = _hook(
        host,
        "provision-room.sh",
        str(host["wt"]),
        PATH=_noexec_path(host, noexec),
        RZ_EXEC_DIRS=str(noexec),
    )
    assert r.returncode != 0
    assert "no exec-able scratch dir" in r.stderr and str(noexec) in r.stderr
    assert not list(noexec.iterdir())


def test_provision_default_scratch_dirs_end_with_home(host):
    """No RZ_EXEC_DIRS, with $TMPDIR and /tmp noexec and no ~/tmp or gate dir:
    $HOME, last in the default list, still lets the room provision."""
    noexec = host["home"] / "noexec"
    noexec.mkdir()
    r = _hook(
        host,
        "provision-room.sh",
        str(host["wt"]),
        PATH=_noexec_path(host, noexec, "/tmp"),
        TMPDIR=str(noexec),
    )
    assert r.returncode == 0, r.stderr
    r = _hook(
        host,
        "provision-room.sh",
        str(host["wt"]),
        PATH=_noexec_path(host, noexec, "/tmp", host["home"]),
        TMPDIR=str(noexec),
    )
    assert r.returncode != 0
    assert f"{noexec}:/tmp:{host['home']}/tmp:" in r.stderr, r.stderr


def test_provision_check_host_runs_only_the_checks(host):
    """--check-host: ask a host whether it could gate a room, writing nothing."""
    before = host["cj"].read_text()
    r = _hook(
        host, "provision-room.sh", "--check-host", str(host["wt"]), PATH=_basics(host)
    )
    assert r.returncode == 0, r.stderr
    assert "host ok" in r.stdout
    (host["llvm"] / "qemu-system-x86_64").unlink()
    r = _hook(
        host,
        "provision-room.sh",
        "--check-host",
        str(host["wt"]),
        PATH=_basics(host),
        RZ_PROVISION_HOST_CHECKS="0",  # an explicit check is never skipped
    )
    assert r.returncode == 1 and "qemu-system-x86_64" in r.stderr
    assert not _settings(host).exists()
    assert host["cj"].read_text() == before


def test_provision_names_every_problem_on_its_one_line(host):
    (host["llvm"] / "qemu-system-x86_64").unlink()
    (host["home"] / ".local" / "bin" / "lld-link").unlink()
    r = _hook(host, "provision-room.sh", str(host["wt"]), PATH=_basics(host))
    assert r.returncode != 0
    assert len(r.stderr.strip().splitlines()) == 1
    assert "qemu-system-x86_64" in r.stderr and "lld-link" in r.stderr


def test_provision_host_checks_can_be_turned_off(host):
    (host["llvm"] / "qemu-system-x86_64").unlink()
    r = _hook(host, "provision-room.sh", str(host["wt"]), RZ_PROVISION_HOST_CHECKS="0")
    assert r.returncode == 0, r.stderr


def test_provision_remove_and_verify_skip_the_host_checks(host):
    """Teardown must work on a host that has since lost a tool."""
    assert _hook(host, "provision-room.sh", str(host["wt"])).returncode == 0
    (host["llvm"] / "qemu-system-x86_64").unlink()
    path = _basics(host)
    assert "qemu" in _hook(host, "provision-room.sh", str(host["wt"]), PATH=path).stderr
    r = _hook(host, "provision-room.sh", "--verify", str(host["wt"]), PATH=path)
    assert r.returncode == 0, r.stderr
    r = _hook(host, "provision-room.sh", "--remove", str(host["wt"]), PATH=path)
    assert r.returncode == 0, r.stderr
    assert str(host["wt"].resolve()) not in _projects(host)


# --------------------------------------------------------------------------
# host-budget.sh
# --------------------------------------------------------------------------


def _systemctl(h: dict) -> Path:
    """A systemctl fake on a minimal PATH, recording argv and XDG_RUNTIME_DIR."""
    bin_dir = h["home"] / "fakebin"
    _exe(
        bin_dir / "systemctl",
        f'#!/bin/sh\necho "$* XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR" >> "{h["home"]}/systemctl.log"\nexit 0\n',
    )
    return bin_dir


def test_host_budget_installs_and_removes_with_a_clean_env(host):
    path = f"{_systemctl(host)}:/usr/bin:/bin"
    r = _hook(host, "host-budget.sh", ROOM, PATH=path)
    assert r.returncode == 0, r.stderr
    units = host["home"] / ".config" / "systemd" / "user"
    dropin = units / f"adele-agent@{ROOM}.service.d" / "50-ritz-host-budget.conf"
    assert (units / "ritz-rooms.slice").is_file() and dropin.is_file()
    # systemctl --user needs the user manager's runtime dir, which a clean
    # env doesn't carry: the hook supplies the standard one.
    log = (host["home"] / "systemctl.log").read_text()
    assert f"daemon-reload XDG_RUNTIME_DIR=/run/user/{os.getuid()}" in log
    assert _hook(host, "host-budget.sh", "--verify", ROOM, PATH=path).returncode == 0
    r = _hook(host, "host-budget.sh", "--remove", ROOM, PATH=path)
    assert r.returncode == 0, r.stderr
    assert not dropin.exists()


def test_host_budget_keeps_a_given_runtime_dir(host):
    path = f"{_systemctl(host)}:/usr/bin:/bin"
    r = _hook(
        host, "host-budget.sh", ROOM, PATH=path, XDG_RUNTIME_DIR="/run/user/elsewhere"
    )
    assert r.returncode == 0, r.stderr
    assert (
        "XDG_RUNTIME_DIR=/run/user/elsewhere"
        in (host["home"] / "systemctl.log").read_text()
    )


def _verify_without_home(host: dict, env_file: Path) -> subprocess.CompletedProcess:
    """--verify as hostd runs it: no HOME, no PATH, config at ENV_FILE.

    RZ_HOST_ENV is host-env.sh's explicit path (AGAST #2998), so the test
    controls the whole host.env it reads.  Without it the hook would fall back
    to the passwd entry's ~/.config/rz/host.env: the operator's real file,
    whose contents (a key this base's host-env.sh predates, say) must not be
    able to red a gate about the hooks (AGAST #4424).
    """
    return _hook(
        host,
        "host-budget.sh",
        "--verify",
        ROOM,
        HOME=None,
        RZ_HOST_ENV=str(env_file),
        RZ_SYSTEMD_USER_DIR=str(host["home"] / "units"),
    )


def test_host_budget_runs_without_home_or_path(host):
    """(a) No host.env at all: --verify reads only and still gives a verdict."""
    cfg = host["home"] / "cfg" / "host.env"  # never written
    r = _verify_without_home(host, cfg)
    assert r.returncode == 1, r.stderr
    assert "MISSING OR STALE" in r.stderr
    assert "unbound" not in r.stderr
    # With HOME unset the hook must say which file it consulted.  This is the
    # file we chose, not the operator's: if the isolation is lost, the note
    # names the passwd home instead and this fails (AGAST #4424).
    assert f"note: HOME unset; host config is {cfg}" in r.stderr


def test_host_budget_accepts_a_host_env_with_only_known_keys(host):
    """(b) KNOWN keys load: install works and --verify reports them as in effect."""
    cfg = host["home"] / "cfg" / "host.env"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(
        "RZ_ROOMS_MEMORY_HIGH=2G\n"
        "RZ_ROOMS_MEMORY_MAX=3G\n"
        "RZ_GATE_SLOTS=2\n"
        "RZ_TEST_BUDGET_SCALE=1.5\n"
    )
    units = host["home"] / "units"
    path = f"{_systemctl(host)}:/usr/bin:/bin"
    install = _hook(
        host,
        "host-budget.sh",
        ROOM,
        PATH=path,
        RZ_HOST_ENV=str(cfg),
        RZ_SYSTEMD_USER_DIR=str(units),
    )
    assert install.returncode == 0, install.stderr
    r = _verify_without_home(host, cfg)
    assert r.returncode == 0, r.stderr
    assert "host budget OK" in r.stdout
    assert f"from {cfg}" in r.stdout


def test_host_budget_names_a_host_env_key_this_tree_does_not_know(host):
    """(c) An UNKNOWN key fails, naming the file: not an anonymous mystery."""
    cfg = host["home"] / "cfg" / "host.env"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("RZ_NOT_A_KEY=1\n")
    r = _verify_without_home(host, cfg)
    assert r.returncode == 2, r.stderr
    assert f"{cfg}:1: unknown key RZ_NOT_A_KEY" in r.stderr
    # The verdict is about OUR file; the operator's was never read.
    assert str(Path(os.path.expanduser("~")) / ".config" / "rz" / "host.env") not in (
        r.stderr
    )


# --------------------------------------------------------------------------
# .borque/: the profile and the verify / train-gate wrappers
# --------------------------------------------------------------------------


def test_borque_profile_and_wrappers():
    r = subprocess.run(
        ["bash", str(REPO / ".borque" / "test-borque.sh")],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
