#!/usr/bin/env python3
"""CI must boot harland (AGAST #1845).

projects/harland/tools/test_tier1_boot.sh (#2132) boots the kernel under OVMF
twice -- harland's own BOOTX64.EFI, and GRUB-EFI via multiboot2 -- and needs
init's Tier-1 suite to report ALL TESTS PASSED with no KERNEL PANIC or
EXCEPTION. Until #1845 nothing ran it but a person, so nothing went red when
harland stopped booting.

It is a step in main.yml's build-all job, after `./rz build --all`. ci_local.py
parses main.yml, so every room's gate (`--job build-all --job bootstrap`) boots
harland too. These tests pin two things:

  * the wiring: the step exists, gates for real, has a timeout, and its serial
    logs are uploaded whether it passes or fails;
  * the verdicts: a missing tool is a SETUP ERROR (ci_local's exit 3 -- no
    verdict, so neither a pass nor a regression), and a panic, an exception
    or a boot that never reports a verdict is a FAIL (exit 1). The script
    runs here against a stub QEMU that writes a canned serial log, so these
    checks need no QEMU, OVMF or kernel build.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_harland_boot.py -q
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ci_local  # noqa: E402

REPO = ci_local.REPO_ROOT
BOOT_SCRIPT = "projects/harland/tools/test_tier1_boot.sh"
INSTALL_SCRIPT = ".github/scripts/install_boot_tools.sh"
# What test_tier1_boot.sh's setup checks need on ubuntu-latest:
# qemu-system-x86_64, qemu-img (qemu-utils), OVMF_CODE*.fd (ovmf),
# grub-mkstandalone + /usr/lib/grub/x86_64-efi (grub-efi-amd64-bin).
BOOT_PACKAGES = ("qemu-system-x86", "qemu-utils", "ovmf", "grub-efi-amd64-bin")


# --------------------------------------------------------------------------
# Wiring: main.yml
# --------------------------------------------------------------------------


def _raw_build_all() -> list[dict]:
    spec = yaml.safe_load(ci_local.WORKFLOW.read_text())
    return spec["jobs"]["build-all"]["steps"]


def _index(steps: list[dict], pred) -> list[int]:
    return [i for i, s in enumerate(steps) if pred(s)]


def _boot_index(steps: list[dict]) -> int:
    hits = _index(steps, lambda s: BOOT_SCRIPT in str(s.get("run", "")))
    assert len(hits) == 1, (
        f"want exactly one build-all step running {BOOT_SCRIPT}, got {len(hits)}"
    )
    return hits[0]


def test_boot_script_exists():
    assert (REPO / BOOT_SCRIPT).is_file()
    assert (REPO / INSTALL_SCRIPT).is_file()


def test_build_all_boots_harland_after_building_the_workspace():
    steps = _raw_build_all()
    boot = _boot_index(steps)
    builds = _index(steps, lambda s: "./rz build --all" in str(s.get("run", "")))
    assert builds and builds[0] < boot


def test_boot_step_is_a_real_gate():
    """No continue-on-error, no `|| true`, from the repo root, and the
    10-minute bound the ticket asks for (two boots take ~1 min locally)."""
    step = _raw_build_all()[_boot_index(_raw_build_all())]
    assert not step.get("continue-on-error", False)
    assert "|| true" not in step["run"]
    assert step.get("working-directory", ".") == "."
    assert 0 < int(step.get("timeout-minutes", 0)) <= 10
    # Both boots: native alone would let GRUB-EFI rot unseen.
    assert not re.search(r"test_tier1_boot\.sh\s+(native|grub)\b", step["run"])


def test_boot_step_is_not_a_setup_step():
    """ci_local skips setup steps by default; the boot must never be one."""
    boot = [
        s
        for s in ci_local.load_steps()
        if s.job == "build-all" and BOOT_SCRIPT in s.run
    ]
    assert len(boot) == 1 and not boot[0].is_setup


def test_boot_tools_are_installed_before_the_boot_as_a_setup_step():
    steps = _raw_build_all()
    boot = _boot_index(steps)
    installs = _index(steps, lambda s: INSTALL_SCRIPT in str(s.get("run", "")))
    assert len(installs) == 1 and installs[0] < boot
    # ci_local must classify it as setup: running it locally would apt-get
    # on the developer's machine.
    parsed = [
        s
        for s in ci_local.load_steps()
        if s.job == "build-all" and INSTALL_SCRIPT in s.run
    ]
    assert len(parsed) == 1 and parsed[0].is_setup
    src = (REPO / INSTALL_SCRIPT).read_text()
    for pkg in BOOT_PACKAGES:
        assert pkg in src, f"{INSTALL_SCRIPT} does not install {pkg}"


def test_serial_logs_are_uploaded_on_pass_and_fail():
    steps = _raw_build_all()
    boot = _boot_index(steps)
    run = steps[boot]["run"]
    assert "KEEP_WORK=" in run
    uploads = _index(
        steps, lambda s: "actions/upload-artifact" in str(s.get("uses", ""))
    )
    after = [i for i in uploads if i > boot]
    assert len(after) == 1, "want one upload-artifact step after the boot"
    up = steps[after[0]]
    assert up.get("if") == "always()", "logs matter most when the boot fails"
    assert "harland" in up["with"]["path"] and up["with"]["path"].rstrip("/").endswith(
        "boot-logs"
    )
    assert "boot-logs" in run


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------

# Writes $FAKE_SERIAL to the `-serial file:PATH` it was given, then idles
# until killed (the script kills QEMU once a verdict appears, and `timeout`
# kills it otherwise). Every argv goes to $STUB_LOG.
QEMU_STUB = r"""#!/usr/bin/env bash
echo "$@" >> "$STUB_LOG"
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$FAKE_SERIAL" > "${a#file:}"; fi
    prev="$a"
done
sleep 30
"""
QEMU_IMG_STUB = """#!/usr/bin/env bash
for a in "$@"; do last="$a"; done
: > "$last"
"""
MKINITRAMFS_STUB = """import sys
out = sys.argv[sys.argv.index("--output") + 1]
open(out, "wb").close()
"""

# A boot whose virtio-keyboard-pci came up and whose injected `sendkey a`
# reached the kernel input queue and init (AGAST #3438).
KEY_OK = (
    r"  [OK] VirtIO input device\n"
    r"[test] input ... [virtio-input] event type=1 code=30 value=1\n"
    r"key event code=30 value=1\n"
)
SUITE_PASSED = r"[test] hello ... PASS (exit=0)\n  Results: 10 passed, 0 failed\n  ALL TESTS PASSED\n"
# The native boot's virtio-blk is modern-only and offers 1024-entry queues;
# the driver must take the MMIO transport and cap the queue (AGAST #3576).
BLK_MODERN = r"[virtio-blk] Device 0 initialized (64 MB, modern, queue 256)\n"
PASSED = BLK_MODERN + KEY_OK + SUITE_PASSED


@pytest.fixture
def tree(tmp_path):
    """A copy of the script in a fake repo with fake build outputs."""
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / BOOT_SCRIPT, tools / "test_tier1_boot.sh")
    (tools / "mkinitramfs.py").write_text(MKINITRAMFS_STUB)
    for rel in (
        "projects/harland/build/debug/harland.elf",
        "projects/harland/build/debug/BOOTX64.EFI",
        "projects/indium/build/debug/init.elf",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF")
    # The script reads its package list from here (AGAST #2759).
    shutil.copy(
        REPO / "projects/indium/initramfs.pkgs", root / "projects/indium/initramfs.pkgs"
    )
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"")
    return {
        "root": root,
        "script": tools / "test_tier1_boot.sh",
        "stubs": stubs,
        "ovmf": ovmf,
        "tmp": tmp_path,
    }


def _stub(stubs: Path, name: str, body: str) -> None:
    p = stubs / name
    p.write_text(body)
    p.chmod(0o755)


def _run(
    tree,
    serial: str = "",
    *,
    qemu=True,
    qemu_img=True,
    full_path=True,
    env_extra=None,
    mode="native",
) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    if qemu:
        _stub(stubs, "qemu-system-x86_64", QEMU_STUB)
    if qemu_img:
        _stub(stubs, "qemu-img", QEMU_IMG_STUB)
    if full_path:
        path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    else:
        # Only what the script needs before its first tool check, so a real
        # qemu on this host can't satisfy it.
        os.symlink(shutil.which("dirname"), stubs / "dirname")
        path = str(stubs)
    env = {
        "PATH": path,
        "HOME": str(tree["tmp"]),
        "SKIP_BUILD": "1",
        "BOOT_TIMEOUT": "3",
        "OVMF_CODE": str(tree["ovmf"]),
        "STUB_LOG": str(tree["tmp"] / "stub.log"),
        "FAKE_SERIAL": serial,
        **(env_extra or {}),
    }
    return subprocess.run(
        ["/bin/bash", str(tree["script"]), mode],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_setup_exit_code_is_ci_locals():
    """The script's 'missing tool' code must be the one ci_local reads as
    SETUP ERROR, or a runner without QEMU reads as a regression (exit 2 was
    a plain failure to ci_local)."""
    assert ci_local.EXIT_SETUP == 3


def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False, qemu_img=False, full_path=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


def test_missing_qemu_img_is_a_setup_error(tree):
    """The boot needs qemu-img for its per-boot overlay. Unchecked, its
    absence surfaced as a boot that never reported a verdict: a FAIL."""
    r = _run(tree, qemu_img=False, full_path=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-img" in r.stderr


def test_missing_ovmf_is_a_setup_error(tree):
    r = _run(tree, PASSED, env_extra={"OVMF_CODE": str(tree["tmp"] / "nope.fd")})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "OVMF" in r.stderr


def test_all_tests_passed_passes_and_keeps_the_serial_log(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, PASSED, env_extra={"KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS (native)" in r.stdout
    assert "ALL TESTS PASSED" in (keep / "native.log").read_text()


def test_boot_attaches_a_keyboard_and_a_monitor_socket(tree):
    """The sendkey check needs a modern-only virtio-keyboard-pci and a
    monitor socket to inject the key through (AGAST #3438)."""
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "virtio-keyboard-pci" in argv
    assert "-monitor unix:" in argv


def test_native_boot_attaches_a_modern_only_blk_with_1024_entry_queues(tree):
    """Without disable-legacy=on QEMU's virtio-blk is transitional and the
    driver takes the legacy I/O-port path; queue-size=1024 is what makes the
    256-entry cap matter (AGAST #3576)."""
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "virtio-blk-pci,drive=initramfs,disable-legacy=on,queue-size=1024" in argv


@pytest.mark.parametrize(
    "blk_line",
    [
        r"[virtio-blk] Device 0 initialized (64 MB, legacy, queue 256)\n",
        r"[virtio-blk] Device 0 initialized (64 MB, modern, queue 1024)\n",
    ],
    ids=["legacy-transport", "queue-not-capped"],
)
def test_native_blk_not_modern_with_a_256_entry_queue_fails(tree, blk_line):
    r = _run(tree, blk_line + KEY_OK + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "virtio-blk did not come up over the modern transport" in r.stdout


def test_suite_passed_but_key_never_arrived_fails(tree):
    """ALL TESTS PASSED is not enough: init's input check skips without a
    key, so the script itself must see the key reach the kernel and init."""
    r = _run(tree, BLK_MODERN + r"  [OK] VirtIO input device\n" + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS (native): init Tier-1 suite" in r.stdout
    assert "injected key A never reached the kernel input queue" in r.stdout


def test_keyboard_that_never_came_up_fails(tree):
    r = _run(tree, BLK_MODERN + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "virtio-keyboard-pci did not come up" in r.stdout


def test_kernel_panic_fails(tree):
    r = _run(tree, r"[kmain] start\nKERNEL PANIC: planted\n")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native)" in r.stdout


def test_exception_fails_even_if_the_suite_passed(tree):
    r = _run(tree, r"EXCEPTION: #GP\nRIP=0x1\nCR2=0\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


def test_no_verdict_before_the_timeout_fails(tree):
    r = _run(tree, r"[kmain] start\n")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout


def test_failed_suite_fails(tree):
    r = _run(tree, r"  Results: 9 passed, 1 failed\n  TESTS FAILED\n")
    assert r.returncode == 1, r.stdout + r.stderr


def _stub_rz(tree, rc: int) -> None:
    _stub(tree["root"], "rz", f"#!/usr/bin/env bash\nexit {rc}\n")


def test_build_missing_a_toolchain_binary_is_a_setup_error(tree):
    """`rz build` exits EXIT_SETUP when e.g. lld-link is absent; the script
    used to turn that into a FAIL."""
    _stub_rz(tree, ci_local.EXIT_SETUP)
    r = _run(tree, PASSED, env_extra={"SKIP_BUILD": "0"})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr


def test_build_failure_is_a_failure(tree):
    _stub_rz(tree, 1)
    r = _run(tree, PASSED, env_extra={"SKIP_BUILD": "0"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: build of harland failed" in r.stdout


def test_missing_build_output_is_a_failure_not_a_setup_error(tree):
    (tree["root"] / "projects/harland/build/debug/harland.elf").unlink()
    r = _run(tree, PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
