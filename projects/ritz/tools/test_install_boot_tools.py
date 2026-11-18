#!/usr/bin/env python3
"""Self-tests for .github/scripts/install_boot_tools.sh -- AGAST #4222.

build-all's "Install test tools (QEMU, OVMF, GRUB-EFI for the harland boot)"
step timed out at 10 minutes twice on 2026-11-18 (runs 44398657610 and
44416492749): apt pulled 86 packages / 46.6 MB, mostly qemu-system-x86's
Recommends (gstreamer, pipewire, sdl2, spice, vte...), from a mirror serving
~75 kB/s. One attempt ate the whole step, so the script's retries never ran.

The script now
  * installs with --no-install-recommends (17 packages / ~26 MB on the
    ubuntu-26.04 runner; ipxe-qemu, the default NIC's option ROMs, is a hard
    Depends of qemu-system-x86, and the boot runs -display none),
  * fetches with --download-only under a per-attempt timeout -- safe to kill,
    and apt resumes the partial download on the next attempt -- and only
    then installs, so dpkg is never killed half way,
  * keeps the .debs in $BOOT_TOOLS_DEB_CACHE, which main.yml restores and
    saves with actions/cache, so a warm run never touches the mirror.

We can't run Actions here, so stub `sudo` and `apt-get` go on a sealed PATH.

Run with:
    python3 -m pytest projects/ritz/tools/test_install_boot_tools.py -q
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".github" / "scripts" / "install_boot_tools.sh"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "main.yml"
PACKAGES = ("qemu-system-x86", "qemu-utils", "ovmf", "grub-efi-amd64-bin")

# apt-get stub. Every call's argv goes to $STUB_DIR/<verb>-args, one line
# per call, where <verb> is fetch (install --download-only), install,
# update or autoclean. The first $HANG_FETCHES fetches hang (a mirror that
# stalls); FAIL_FETCHES=always makes every fetch fail. A fetch that works
# drops a .deb (and apt's partial/ dir) into Dir::Cache::Archives if one is
# given. install "installs" the tools the script checks for.
APT_STUB = r"""#!/usr/bin/env bash
set -u
d="$STUB_DIR"
archives=""
prev=""
for a in "$@"; do
  case "$prev:$a" in -o:Dir::Cache::Archives=*) archives="${a#*=}" ;; esac
  prev="$a"
done
n() { wc -l < "$d/$1-args"; }
case " $* " in
  *" update "*) echo "$*" >> "$d/update-args"; exit 0 ;;
  *" autoclean "*) echo "$*" >> "$d/autoclean-args"; exit 0 ;;
  *" --download-only "*)
    echo "$*" >> "$d/fetch-args"
    if [ "${FAIL_FETCHES:-0}" = always ]; then
      echo "E: Failed to fetch qemu-system-x86 (stub)" >&2; exit 100
    fi
    if [ "$(n fetch)" -le "${HANG_FETCHES:-0}" ]; then sleep 30; exit 0; fi
    if [ -n "$archives" ]; then
      mkdir -p "$archives/partial"
      : > "$archives/qemu-system-x86_stub_amd64.deb"
      : > "$archives/lock"
    fi
    exit 0 ;;
  *" install "*)
    echo "$*" >> "$d/install-args"
    for t in qemu-system-x86_64 qemu-img grub-mkstandalone; do
      printf '#!/bin/sh\necho "%s [stub]"\n' "$t" > "$d/bin/$t"
      chmod +x "$d/bin/$t"
    done
    mkdir -p "$d/grub/x86_64-efi" "$d/ovmf"
    : > "$d/ovmf/OVMF_CODE_4M.fd"
    exit 0 ;;
esac
echo "apt-get stub: unexpected args: $*" >&2
exit 2
"""

SUDO_STUB = '#!/bin/sh\nexec "$@"\n'

# The only real tools on the sealed PATH, so the host's own qemu can't
# satisfy the script's checks.
REAL_TOOLS = (
    "bash",
    "sh",
    "wc",
    "sleep",
    "head",
    "chmod",
    "mkdir",
    "rm",
    "ls",
    "timeout",
    "id",
    "chown",
)


def _calls(stub: Path, verb: str) -> list[str]:
    f = stub / f"{verb}-args"
    return f.read_text().splitlines() if f.exists() else []


@pytest.fixture
def stub(tmp_path):
    (tmp_path / "bin").mkdir()
    for name, body in (("apt-get", APT_STUB), ("sudo", SUDO_STUB)):
        p = tmp_path / "bin" / name
        p.write_text(body)
        p.chmod(0o755)
    (tmp_path / "sys").mkdir()
    for tool in REAL_TOOLS:
        real = shutil.which(tool)
        assert real, f"{tool} is needed to run the stubs"
        (tmp_path / "sys" / tool).symlink_to(real)
    return tmp_path


def _run(stub: Path, *, attempts=3, fetch_timeout=2, env_extra=None):
    env = {
        "PATH": f"{stub / 'bin'}:{stub / 'sys'}",
        "STUB_DIR": str(stub),
        "HOME": str(stub),
        "BOOT_TOOLS_INSTALL_ATTEMPTS": str(attempts),
        "BOOT_TOOLS_INSTALL_BACKOFF": "0",
        "BOOT_TOOLS_FETCH_TIMEOUT": str(fetch_timeout),
        # Test seams for have_tools()'s two absolute paths.
        "BOOT_TOOLS_GRUB_DIR": str(stub / "grub" / "x86_64-efi"),
        "BOOT_TOOLS_OVMF_DIR": str(stub / "ovmf"),
        **(env_extra or {}),
    }
    return subprocess.run(
        [str(stub / "sys" / "bash"), str(SCRIPT)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.integration
def test_installs_the_boot_packages_without_recommends(stub):
    r = _run(stub)
    assert r.returncode == 0, r.stdout + r.stderr
    for verb in ("fetch", "install"):
        (args,) = _calls(stub, verb)
        words = args.split()
        assert "--no-install-recommends" in words, f"{verb}: {args}"
        assert "-y" in words
        for pkg in PACKAGES:
            assert pkg in words, f"{verb} does not name {pkg}"


@pytest.mark.integration
def test_a_stalled_fetch_is_cut_off_and_retried(stub):
    """The 2026-11-18 failure: one slow fetch ate the step's 10 minutes and
    the retry loop never got a second go."""
    r = _run(stub, attempts=3, fetch_timeout=2, env_extra={"HANG_FETCHES": "1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(_calls(stub, "fetch")) == 2
    assert len(_calls(stub, "install")) == 1
    assert "timed out" in r.stdout


@pytest.mark.integration
def test_nothing_is_installed_until_a_fetch_completes(stub):
    """dpkg must never run under the fetch timeout or after a failed fetch:
    killing it half way leaves the runner's dpkg state broken."""
    r = _run(stub, attempts=2, env_extra={"FAIL_FETCHES": "always"})
    assert r.returncode != 0
    assert len(_calls(stub, "fetch")) == 2
    assert _calls(stub, "install") == []
    out = r.stdout + r.stderr
    assert "::error" in out and "2 attempts" in out
    assert "Failed to fetch" in out  # apt's own reason reaches the log


@pytest.mark.integration
def test_deb_cache_is_used_pruned_and_left_saveable(stub):
    cache = stub / "debs"
    r = _run(stub, env_extra={"BOOT_TOOLS_DEB_CACHE": str(cache)})
    assert r.returncode == 0, r.stdout + r.stderr
    opt = f"Dir::Cache::Archives={cache}"
    for verb in ("fetch", "install", "autoclean"):
        (args,) = _calls(stub, verb)
        assert opt in args.split(), f"{verb} ignores the cache: {args}"
    # The .debs stay for actions/cache to save; apt's root-only partial/
    # dir and lock file would make that save fail, so they go.
    assert (cache / "qemu-system-x86_stub_amd64.deb").exists()
    assert not (cache / "partial").exists()
    assert not (cache / "lock").exists()


@pytest.mark.integration
def test_tilde_cache_path_from_main_yml_is_expanded(stub):
    """A step's env: value is not shell-expanded; main.yml passes the cache
    step's own `~/...` path."""
    r = _run(stub, env_extra={"BOOT_TOOLS_DEB_CACHE": "~/debs"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert (stub / "debs" / "qemu-system-x86_stub_amd64.deb").exists()
    assert not (stub / "~").exists()


@pytest.mark.integration
def test_without_a_cache_apt_uses_its_own_archives(stub):
    r = _run(stub)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Dir::Cache::Archives" not in "".join(_calls(stub, "fetch"))
    assert _calls(stub, "autoclean") == []


@pytest.mark.integration
def test_already_installed_tools_skip_apt(stub):
    assert _run(stub).returncode == 0
    (stub / "fetch-args").unlink()
    r = _run(stub)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "already installed" in r.stdout
    assert _calls(stub, "fetch") == []


def _default(name: str) -> int:
    m = re.search(rf"\${{{name}:-(\d+)}}", SCRIPT.read_text())
    assert m, f"{name} has no numeric default in {SCRIPT.name}"
    return int(m.group(1))


def _install_step() -> dict:
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["build-all"]["steps"]
    hits = [s for s in steps if "install_boot_tools.sh" in s.get("run", "")]
    assert len(hits) == 1
    return hits[0]


@pytest.mark.unit
def test_every_retry_fits_inside_the_step_timeout():
    """All fetch attempts plus their backoff must end before the step's
    timeout-minutes, with time left to install, or the retries are dead
    code again and the step dies without the script's ::error."""
    attempts = _default("BOOT_TOOLS_INSTALL_ATTEMPTS")
    fetch = _default("BOOT_TOOLS_FETCH_TIMEOUT")
    backoff = _default("BOOT_TOOLS_INSTALL_BACKOFF")
    assert attempts >= 2
    backoffs = sum(backoff * 2**i for i in range(attempts - 1))
    install_room = 90  # dpkg unpack of ~17 packages, measured ~20 s
    step = _install_step()["timeout-minutes"] * 60
    assert attempts * fetch + backoffs + install_room <= step, (
        attempts,
        fetch,
        backoffs,
        step,
    )


@pytest.mark.unit
def test_workflow_caches_the_debs_across_runs():
    steps = yaml.safe_load(WORKFLOW.read_text())["jobs"]["build-all"]["steps"]
    install = _install_step()
    i = steps.index(install)
    cache_dir = install.get("env", {}).get("BOOT_TOOLS_DEB_CACHE")
    assert cache_dir, "the install step must name its .deb cache"
    caches = [
        s
        for s in steps[:i]
        if "actions/cache" in str(s.get("uses", ""))
        and s.get("with", {}).get("path") == cache_dir
    ]
    assert len(caches) == 1, (
        "want one actions/cache step for the debs before the install"
    )
    w = caches[0]["with"]
    # Refreshed with each runner image and whenever the package list changes.
    # ImageOS/ImageVersion are runner env vars, not in `${{ env }}`: a step
    # must hand them over as an output, or the key silently never changes.
    assert "${{ env.Image" not in w["key"]
    m = re.search(r"steps\.([\w-]+)\.outputs\.(\w+)", w["key"])
    assert m, w["key"]
    (src,) = [s for s in steps[:i] if s.get("id") == m.group(1)]
    assert "$ImageOS" in src["run"] and "$ImageVersion" in src["run"]
    assert f"{m.group(2)}=" in src["run"] and "GITHUB_OUTPUT" in src["run"]
    assert "install test tools" in src["name"].lower(), "ci_local must skip it"
    assert "hashFiles('.github/scripts/install_boot_tools.sh')" in w["key"]
    assert w["key"].startswith(w["restore-keys"].strip())
    # Still a setup step by name (ci_local skips it), still a real gate.
    assert "install test tools" in install["name"].lower()
    assert not install.get("continue-on-error")
    assert "||" not in install["run"]
