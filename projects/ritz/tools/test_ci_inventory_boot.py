#!/usr/bin/env python3
"""CI must boot the hardware-inventory stick and check its dump (AGAST #3406).

projects/harland/inventory/test.sh builds the USB-stick image (esp_image.py:
GPT + FAT32 ESP with HWINV.EFI as \\EFI\\BOOT\\BOOTX64.EFI), boots it under
q35 + OVMF from a writable USB mass-storage device, reads back the
\\INVENTORY\\<timestamp>\\ dump the app wrote, and validates it with
check_dump.py against what it told QEMU (-smp, -m, -smbios type=1, the PCI
devices). It boots twice: SMBIOS entry point 64-bit and 32-bit.

These tests pin, as test_ci_esp_initramfs_boot.py does for its boot:

  * the wiring: the step exists after test-uefi-boot and before the log
    upload, gates for real, has a timeout and keeps its work for upload;
  * the verdicts: a missing tool is a SETUP ERROR (exit 3); no "HWINV: DONE"
    or no dump on the stick is exit 1; QEMU boots the image from USB
    storage, writable, never a vvfat directory. The script runs against a
    stub QEMU, so no QEMU, OVMF or build is needed. The real boot is the
    CI step itself (and test_harland_inventory_tools.py covers the tools).

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_inventory_boot.py -q
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
SCRIPT = "projects/harland/inventory/test.sh"
UEFI_BOOT = "projects/harland/boot/test.sh"

# Writes $FAKE_SERIAL to the `-serial file:PATH` it was given, logs its
# argv, then idles until killed (as QEMU does after the app's DONE).
QEMU_STUB = r"""#!/usr/bin/env bash
echo "$@" >> "$STUB_LOG"
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$FAKE_SERIAL" > "${a#file:}"; fi
    prev="$a"
done
sleep 30
"""

DONE = r"HWINV: writing \\INVENTORY\\20261119-060203\nHWINV: DONE. Remove the stick\n"


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _step_indices(steps: list[dict], script: str) -> list[int]:
    return [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]


def test_inventory_boot_runs_after_test_uefi_boot_and_before_the_log_upload():
    assert (REPO / SCRIPT).is_file()
    steps = _build_all()
    [inv] = _step_indices(steps, SCRIPT)
    [uefi] = _step_indices(steps, UEFI_BOOT)
    assert inv > uefi
    uploads = [i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads and min(uploads) > inv, "the inventory serial logs must be uploaded too"


def test_inventory_step_is_a_real_gate_with_a_timeout():
    steps = _build_all()
    [i] = _step_indices(steps, SCRIPT)
    step = steps[i]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"], "KEEP_WORK into boot-logs, for the upload"
    assert str(step.get("env", {}).get("SKIP_BUILD")) == "1", "build-all already built HWINV.EFI"
    parsed = [s for s in ci_local.load_steps() if SCRIPT in s.run]
    assert len(parsed) == 1 and not parsed[0].is_setup


def test_hwinv_is_a_harland_uefi_bin():
    toml = (REPO / "projects/harland/ritz.toml").read_text()
    block = toml[toml.index('name = "hwinv"'):]
    assert 'target = "x86_64-unknown-uefi"' in block.split("[[bin]]")[0]
    assert 'sources = ["inventory/src"]' in block.split("[[bin]]")[0]


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    inv = root / "projects" / "harland" / "inventory"
    inv.mkdir(parents=True)
    for f in ("test.sh", "esp_image.py", "check_dump.py"):
        shutil.copy(REPO / "projects/harland/inventory" / f, inv / f)
    efi = root / "projects/harland/build/debug/HWINV.EFI"
    efi.parent.mkdir(parents=True)
    efi.write_bytes(b"MZ-stub")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"")
    return {"script": inv / "test.sh", "stubs": stubs, "ovmf": ovmf, "tmp": tmp_path}


def _run(tree, serial: str = "", *, qemu=True, env_extra=None) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    if qemu:
        p = stubs / "qemu-system-x86_64"
        p.write_text(QEMU_STUB)
        p.chmod(0o755)
        path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    else:
        for tool in ("dirname", "python3"):
            os.symlink(shutil.which(tool), stubs / tool)
        path = str(stubs)
    env = {
        "PATH": path,
        "HOME": str(tree["tmp"]),
        "TMPDIR": str(tree["tmp"]),
        "SKIP_BUILD": "1",
        "BOOT_TIMEOUT": "2",
        "OVMF_CODE": str(tree["ovmf"]),
        "STUB_LOG": str(tree["tmp"] / "stub.log"),
        "FAKE_SERIAL": serial,
        **(env_extra or {}),
    }
    return subprocess.run(["/bin/bash", str(tree["script"])], env=env,
                          capture_output=True, text=True, timeout=90)


@pytest.mark.integration
def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


@pytest.mark.integration
def test_missing_ovmf_is_a_setup_error(tree):
    r = _run(tree, env_extra={"OVMF_CODE": str(tree["tmp"] / "nope.fd")})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "OVMF" in r.stderr


@pytest.mark.integration
def test_missing_efi_is_a_setup_error(tree):
    (tree["script"].parents[1] / "build/debug/HWINV.EFI").unlink()
    r = _run(tree, DONE)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr


@pytest.mark.integration
def test_no_done_before_the_timeout_fails(tree):
    r = _run(tree, r"HWINV: writing \\INVENTORY\\x\n  acpi: RSDP rev 2\n")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report HWINV: DONE" in r.stdout


@pytest.mark.integration
def test_done_with_no_dump_on_the_stick_fails(tree):
    """The serial line alone proves nothing: the files must be on the image."""
    r = _run(tree, DONE)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS: the inventory stick" not in r.stdout


@pytest.mark.integration
def test_boots_the_image_from_writable_usb_storage_twice(tree):
    _run(tree, DONE)
    boots = (tree["tmp"] / "stub.log").read_text().splitlines()
    assert len(boots) == 2, "one boot per SMBIOS entry point"
    assert "smbios-entry-point-type=64" in boots[0]
    assert "smbios-entry-point-type=32" in boots[1]
    for argv in boots:
        assert "usb-storage" in argv and "qemu-xhci" in argv
        assert "fat:rw:" not in argv, "the real image, not a vvfat directory"
        stick = [a for a in argv.split() if a.startswith("if=none,id=stick")]
        assert stick and "readonly" not in stick[0] and "snapshot" not in argv
        assert "type=1,manufacturer=RitzInventoryTest" in argv
