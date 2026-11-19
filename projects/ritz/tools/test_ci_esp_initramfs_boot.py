#!/usr/bin/env python3
"""CI must boot harland with the initramfs on the ESP and no block device (AGAST #4253).

projects/harland/tools/test_esp_initramfs_boot.sh boots the kernel under OVMF
with only a vvfat ESP: EFI/BOOT/BOOTX64.EFI, harland/kernel.elf and
harland/initramfs.tar. There is no virtio-blk or NVMe disk, as on EC2 Nitro or
a laptop. It passes only if BOOTX64.EFI logs that it read the TAR (its exact
size), the kernel loads the initramfs from boot memory (the BootInfo hand-off,
not a disk) and init's Tier-1 suite passes.

These tests pin, as test_ci_nvme_boot.py does for its boot:

  * the wiring: the step exists after the NVMe boots and before the log
    upload, gates for real and has a timeout;
  * the verdicts: a missing tool is a SETUP ERROR (exit 3), every failed
    check is exit 1, and QEMU gets no disk but the ESP. The script runs
    against a stub QEMU, so no QEMU, OVMF or kernel build is needed.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_esp_initramfs_boot.py -q
"""

from __future__ import annotations

import os
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
ESP_SCRIPT = "projects/harland/tools/test_esp_initramfs_boot.sh"
NVME_SCRIPT = "projects/harland/tools/test_nvme_boot.sh"

# The size of the TAR the mkinitramfs stub writes: the loader line must
# carry it exactly.
TAR_SIZE = 3072

# The QEMU stub writes $FAKE_SERIAL to the `-serial file:PATH` it was given,
# then idles until killed. Every argv goes to $STUB_LOG.
QEMU_STUB = r"""#!/usr/bin/env bash
echo "$@" >> "$STUB_LOG"
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$FAKE_SERIAL" > "${a#file:}"; fi
    prev="$a"
done
sleep 30
"""
MKINITRAMFS_STUB = f"""import sys
out = sys.argv[sys.argv.index("--output") + 1]
open(out, "wb").write(bytes({TAR_SIZE}))
"""

LOADER = rf"    Read initramfs: {TAR_SIZE} bytes at 0x7E000000\n"
FROM_MEMORY = (
    rf"[initramfs] Loading from boot memory ({TAR_SIZE} bytes)...\n"
    r"[initramfs] Loaded 32 files from boot memory\n"
)
FROM_DISK = (
    r"[initramfs] Loading from VirtIO disk...\n[initramfs] Loaded 32 files from disk\n"
)
SUITE_PASSED = r"  Results: 10 passed, 0 failed\n  ALL TESTS PASSED\n"
PASSED = LOADER + FROM_MEMORY + SUITE_PASSED


# --------------------------------------------------------------------------
# Wiring: main.yml
# --------------------------------------------------------------------------


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _step_indices(steps: list[dict], script: str) -> list[int]:
    return [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]


def test_esp_boot_runs_after_the_nvme_boots_and_before_the_log_upload():
    assert (REPO / ESP_SCRIPT).is_file()
    steps = _build_all()
    [esp] = _step_indices(steps, ESP_SCRIPT)
    nvme = _step_indices(steps, NVME_SCRIPT)
    assert nvme and esp > max(nvme)
    uploads = [
        i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))
    ]
    assert uploads and min(uploads) > esp, "esp-initramfs.log must be uploaded too"


def test_esp_step_is_a_real_gate_with_a_timeout():
    steps = _build_all()
    [i] = _step_indices(steps, ESP_SCRIPT)
    step = steps[i]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    parsed = [s for s in ci_local.load_steps() if ESP_SCRIPT in s.run]
    assert len(parsed) == 1 and not parsed[0].is_setup


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / ESP_SCRIPT, tools / "test_esp_initramfs_boot.sh")
    (tools / "mkinitramfs.py").write_text(MKINITRAMFS_STUB)
    (root / "projects" / "indium").mkdir(parents=True)
    (root / "projects" / "indium" / "initramfs.pkgs").write_text("indium  # init\n")
    for rel in (
        "projects/harland/build/debug/harland.elf",
        "projects/harland/build/debug/BOOTX64.EFI",
        "projects/indium/build/debug/init.elf",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"")
    return {
        "root": root,
        "script": tools / "test_esp_initramfs_boot.sh",
        "stubs": stubs,
        "ovmf": ovmf,
        "tmp": tmp_path,
    }


def _stub(stubs: Path, name: str, body: str) -> None:
    p = stubs / name
    p.write_text(body)
    p.chmod(0o755)


def _run(
    tree, serial: str = "", *, qemu=True, env_extra=None
) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    if qemu:
        _stub(stubs, "qemu-system-x86_64", QEMU_STUB)
        path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    else:
        for tool in ("dirname", "python3"):
            os.symlink(shutil.which(tool), stubs / tool)
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
        ["/bin/bash", str(tree["script"])],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.integration
def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


@pytest.mark.integration
def test_passes_with_the_initramfs_from_boot_memory_and_only_the_esp(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, PASSED, env_extra={"KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "from boot memory" in (keep / "esp-initramfs.log").read_text()
    argv = (tree["tmp"] / "stub.log").read_text()
    # The ESP is the only disk: a vvfat drive and the OVMF flash, nothing else.
    drives = [a for a in argv.split() if a.startswith(("format=", "file=", "if="))]
    assert len([d for d in drives if "fat:rw:" in d]) == 1
    assert not [d for d in drives if "fat:rw:" not in d and "pflash" not in d], drives
    for dev in ("virtio-blk", "nvme", "-hda", "-cdrom"):
        assert dev not in argv


@pytest.mark.integration
def test_initramfs_from_a_disk_fails(tree):
    """The kernel ignored the BootInfo hand-off (the mutation that drops it)."""
    r = _run(tree, LOADER + FROM_DISK + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not load the initramfs from boot memory" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "loader",
    [
        pytest.param("", id="no-loader-line"),
        pytest.param(r"    Read initramfs: 512 bytes at 0x1000\n", id="wrong-size"),
    ],
)
def test_loader_must_read_the_whole_tar(tree, loader):
    r = _run(tree, loader + FROM_MEMORY + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"did not log 'Read initramfs: {TAR_SIZE} bytes'" in r.stdout


@pytest.mark.integration
def test_panic_fails(tree):
    r = _run(tree, LOADER + r"*** KERNEL PANIC: Failed to load initramfs ***\n")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "kernel panic or exception" in r.stdout


@pytest.mark.integration
def test_exception_fails_even_if_everything_else_passed(tree):
    r = _run(tree, r"EXCEPTION: #GP\nRIP=0x1\nCR2=0\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_no_verdict_before_the_timeout_fails(tree):
    r = _run(tree, LOADER + FROM_MEMORY)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout
