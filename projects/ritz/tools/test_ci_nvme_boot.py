#!/usr/bin/env python3
"""CI must boot harland from NVMe disks (AGAST #1850).

projects/harland/tools/test_nvme_boot.sh boots the kernel under OVMF with two
QEMU NVMe controllers and no virtio-blk: harland-root holds the initramfs,
harland-data a 4 MiB disk with a known sector pattern. It passes only if the
kernel's NVMe driver logs the right size and FNV-1a of LBAs 1-200 for
harland-data, the initramfs loads, persistent storage formats harland-data
(its magic is in the image afterwards) and init's Tier-1 suite passes.

AGAST #4088: a second CI step runs the same boot with NVME_LBA_SIZE=4096
(QEMU `logical_block_size=4096` on both controllers), so the driver must
translate 512-byte sectors to 4 KiB LBAs (read-modify-write for unaligned
writes) and describe multi-page transfers with PRP2 / PRP lists. The driver
logs the LBA size it found, so the 4 KiB step cannot pass on 512-byte LBAs.

These tests pin, as test_ci_msix_boot.py does for its boot:

  * the wiring: the step exists after the MSI-X boot and before the log
    upload, gates for real and has a timeout;
  * the verdicts: a missing tool is a SETUP ERROR (exit 3), every failed
    check is exit 1. The script runs against a stub QEMU, so no QEMU, OVMF
    or kernel build is needed.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_nvme_boot.py -q
"""

from __future__ import annotations

import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ci_local  # noqa: E402

REPO = ci_local.REPO_ROOT
NVME_SCRIPT = "projects/harland/tools/test_nvme_boot.sh"
MSIX_SCRIPT = "projects/harland/tools/test_msix_boot.sh"

# The QEMU stub writes $FAKE_SERIAL to the `-serial file:PATH` it was given;
# with FAKE_PERSIST=1 it also writes the persist superblock magic into the
# drive with id=data, as the kernel's NVMe writes would, and with
# FAKE_CLOBBER=1 zeroes sector 66 (a write that skipped read-modify-write).
# Then it idles until killed. Every argv goes to $STUB_LOG.
QEMU_STUB = r"""#!/usr/bin/env bash
echo "$@" >> "$STUB_LOG"
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$FAKE_SERIAL" > "${a#file:}"; fi
    if [ "$prev" = "-drive" ] && [ "${FAKE_PERSIST:-0}" = 1 ]; then
        case "$a" in *id=data*)
            f="${a#file=}"; f="${f%%,*}"
            printf '\0HARBLOB' | dd of="$f" conv=notrunc status=none
            if [ "${FAKE_CLOBBER:-0}" = 1 ]; then
                dd if=/dev/zero of="$f" bs=512 seek=66 count=1 conv=notrunc status=none
            fi ;;
        esac
    fi
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


def _pattern_fnv() -> int:
    """FNV-1a (32-bit) of LBAs 1-200 of the data disk, from the pattern's
    definition: sector N is ("LBA" + u32le(N) + "!") * 64."""
    h = 0x811C9DC5
    for n in range(1, 201):
        for b in (b"LBA" + struct.pack("<I", n) + b"!") * 64:
            h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


def nvme_line(sectors: int = 8192, fnv: int | None = None, lba: int = 512) -> str:
    fnv = _pattern_fnv() if fnv is None else fnv
    return (rf"[nvme] harland-data nsid 1: {sectors} sectors, LBA 1-200 fnv1a={fnv}"
            rf", {lba}-byte LBAs\n")


INITRAMFS = r"[initramfs] Loaded 42 entries\n"
PERSIST = r"  [OK] Persistent storage (0 blobs)\n"
SUITE_PASSED = r"  Results: 10 passed, 0 failed\n  ALL TESTS PASSED\n"
PASSED = nvme_line() + INITRAMFS + PERSIST + SUITE_PASSED


# --------------------------------------------------------------------------
# Wiring: main.yml
# --------------------------------------------------------------------------


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _step_indices(steps: list[dict], script: str) -> list[int]:
    return [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]


def _step_index(steps: list[dict], script: str) -> int:
    hits = _step_indices(steps, script)
    assert len(hits) == 1, f"want exactly one build-all step running {script}, got {hits}"
    return hits[0]


def _lba_size(step: dict) -> str:
    return str((step.get("env") or {}).get("NVME_LBA_SIZE", "512"))


def test_nvme_boot_runs_after_the_msix_boot_and_before_the_log_upload():
    assert (REPO / NVME_SCRIPT).is_file()
    steps = _build_all()
    nvme = _step_indices(steps, NVME_SCRIPT)
    assert nvme and min(nvme) > _step_index(steps, MSIX_SCRIPT)
    uploads = [i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads and min(uploads) > max(nvme), "nvme logs must be uploaded too"


def test_nvme_boots_once_with_512_and_once_with_4096_byte_lbas():
    steps = _build_all()
    sizes = sorted(_lba_size(steps[i]) for i in _step_indices(steps, NVME_SCRIPT))
    assert sizes == ["4096", "512"]


@pytest.mark.parametrize("lba", ["512", "4096"])
def test_nvme_step_is_a_real_gate_with_a_timeout(lba):
    steps = _build_all()
    [step] = [steps[i] for i in _step_indices(steps, NVME_SCRIPT) if _lba_size(steps[i]) == lba]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    assert "SKIP_BUILD" not in step["run"]
    parsed = [s for s in ci_local.load_steps() if NVME_SCRIPT in s.run]
    assert len(parsed) == 2 and not any(s.is_setup for s in parsed)


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / NVME_SCRIPT, tools / "test_nvme_boot.sh")
    (tools / "mkinitramfs.py").write_text(MKINITRAMFS_STUB)
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
    return {"root": root, "script": tools / "test_nvme_boot.sh", "stubs": stubs,
            "ovmf": ovmf, "tmp": tmp_path}


def _stub(stubs: Path, name: str, body: str) -> None:
    p = stubs / name
    p.write_text(body)
    p.chmod(0o755)


def _run(tree, serial: str = "", *, persist=True, qemu=True,
         env_extra=None) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    _stub(stubs, "qemu-img", QEMU_IMG_STUB)
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
        "FAKE_PERSIST": "1" if persist else "0",
        **(env_extra or {}),
    }
    return subprocess.run(["/bin/bash", str(tree["script"])], env=env,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


@pytest.mark.integration
def test_all_checks_pass_on_two_nvme_disks_and_no_virtio_blk(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, PASSED, env_extra={"KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"read back the pattern (fnv1a={_pattern_fnv()}, 512-byte LBAs)" in r.stdout
    assert "harland-data" in (keep / "nvme.log").read_text()
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "-device nvme,serial=harland-root,drive=root" in argv
    assert "-device nvme,serial=harland-data,drive=data" in argv
    # harland-root must come first: it is block device 0, the initramfs.
    assert argv.index("harland-root") < argv.index("harland-data")
    assert "virtio-blk" not in argv


@pytest.mark.integration
@pytest.mark.parametrize("line", [
    pytest.param(nvme_line(fnv=_pattern_fnv() ^ 1), id="wrong-data"),
    pytest.param(nvme_line(sectors=8191), id="wrong-size"),
    pytest.param("", id="no-namespace"),
])
def test_bad_or_missing_pattern_read_fails(tree, line):
    r = _run(tree, line + INITRAMFS + PERSIST + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: harland-data" in r.stdout


@pytest.mark.integration
def test_initramfs_not_loaded_fails(tree):
    r = _run(tree, nvme_line() + PERSIST + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "initramfs did not load" in r.stdout


@pytest.mark.integration
def test_persist_magic_missing_from_the_image_fails(tree):
    """The kernel says persist came up, but nothing reached the disk: the
    mutation that drops the NVMe write command's doorbell."""
    r = _run(tree, PASSED, persist=False)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "persistent storage did not come up" in r.stdout


@pytest.mark.integration
def test_exception_fails_even_if_everything_else_passed(tree):
    r = _run(tree, r"EXCEPTION: #GP\nRIP=0x1\nCR2=0\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_no_verdict_before_the_timeout_fails(tree):
    r = _run(tree, nvme_line() + INITRAMFS + PERSIST)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout


# --------------------------------------------------------------------------
# AGAST #4088: the 4 KiB-LBA variant (NVME_LBA_SIZE=4096)
# --------------------------------------------------------------------------


PASSED_4K = nvme_line(lba=4096) + INITRAMFS + PERSIST + SUITE_PASSED


def test_4k_variant_passes_on_4096_byte_lbas_and_tells_qemu_so(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, PASSED_4K, env_extra={"NVME_LBA_SIZE": "4096", "KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    for disk in ("root", "data"):
        assert (f"-device nvme,serial=harland-{disk},drive={disk},"
                "logical_block_size=4096,physical_block_size=4096") in argv
    # Its own log name, so the 512-byte step's nvme.log is not overwritten.
    assert "4096-byte LBAs" in (keep / "nvme-4k.log").read_text()


def test_4k_variant_fails_if_the_driver_saw_512_byte_lbas(tree):
    """QEMU ignored the option, or the driver misreads LBADS: the pattern
    still hashes right, so only the logged LBA size catches it."""
    r = _run(tree, PASSED, env_extra={"NVME_LBA_SIZE": "4096"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: harland-data" in r.stdout


def test_default_variant_keeps_512_byte_lbas(tree):
    r = _run(tree, PASSED_4K)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "logical_block_size" not in (tree["tmp"] / "stub.log").read_text()


def test_unknown_lba_size_is_refused(tree):
    r = _run(tree, PASSED, env_extra={"NVME_LBA_SIZE": "1024"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NVME_LBA_SIZE" in r.stdout


def test_sectors_beside_persists_writes_must_keep_the_pattern(tree):
    """Persist writes sectors 0-64; on 4 KiB LBAs sector 64 shares LBA 8 with
    65-71, so a write without read-modify-write zeroes them."""
    r = _run(tree, PASSED_4K, env_extra={"NVME_LBA_SIZE": "4096", "FAKE_CLOBBER": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "clobbered: 66" in r.stdout
