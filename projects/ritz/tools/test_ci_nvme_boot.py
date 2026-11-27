#!/usr/bin/env python3
"""CI must boot harland from NVMe disks (AGAST #1850).

projects/harland/tools/test_nvme_boot.sh boots the kernel under OVMF with two
QEMU NVMe controllers and no virtio-blk: harland-root holds the initramfs,
harland-data a 4 MiB disk with a known sector pattern. It passes only if the
kernel's NVMe driver logs the right size and FNV-1a of LBAs 1-200 for
harland-data, the initramfs loads, persistent storage saves a goliath image to
harland-data (its header and image magic are on the disk afterwards, AGAST
#1881) and init's Tier-1 suite passes.

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

# The QEMU stub models the kernel's storage guard (AGAST #4883): an ESP
# without \harland\storage-format is the guard boot, which gets
# $FAKE_GUARD_SERIAL (default: kfs refusing harland-data) and writes nothing
# to the data drive unless FAKE_GUARD_WRITE=1. Otherwise it writes
# $FAKE_SERIAL to the `-serial file:PATH` it was given; with FAKE_PERSIST=1
# it also writes a goliath block-store header (sector 0:
# "GOLIATHB", version 2, 512-byte sectors, image at sector 2, 100 bytes) and
# the image magic ("GOLIATHS", sector 2) into the drive with id=data, as the
# kernel's NVMe writes would, and
# with FAKE_CLOBBER=1 zeroes sector 1 (a write that skipped read-modify-write).
# Then it idles until killed. Every argv goes to $STUB_LOG.
QEMU_STUB = r"""#!/usr/bin/env bash
echo "$@" >> "$STUB_LOG"
serial="$FAKE_SERIAL" persist="${FAKE_PERSIST:-0}" prev=""
for a in "$@"; do
    case "$prev $a" in "-drive format=raw,file=fat:rw:"*)
        if [ ! -e "${a#format=raw,file=fat:rw:}/harland/storage-format" ]; then
            serial="${FAKE_GUARD_SERIAL-$GUARD_SERIAL}" persist="${FAKE_GUARD_WRITE:-0}"
        fi ;;
    esac
    prev="$a"
done
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$serial" > "${a#file:}"; fi
    if [ "$prev" = "-drive" ] && [ "$persist" = 1 ]; then
        case "$a" in *id=data*)
            f="${a#file=}"; f="${f%%,*}"
            printf 'GOLIATHB' | dd of="$f" conv=notrunc status=none
            printf '\x02\0\0\0\x00\x02\0\0' | dd of="$f" bs=1 seek=8 conv=notrunc status=none
            printf '\x02\0\0\0\0\0\0\0\x64\0\0\0\0\0\0\0' | dd of="$f" bs=1 seek=24 conv=notrunc status=none
            printf 'GOLIATHS' | dd of="$f" bs=1 seek=1024 conv=notrunc status=none
            if [ "${FAKE_CLOBBER:-0}" = 1 ]; then
                dd if=/dev/zero of="$f" bs=512 seek=1 count=1 conv=notrunc status=none
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
PERSIST = r"  [OK] Persistent storage (goliath image: boot 1, 3 blobs)\n"
# No \harland\net-selftest on this ESP, so the kernel leaves the NIC alone
# before init (AGAST #4335); test_nvme_boot.sh requires this line.
NET_SKIPPED = r"[net] Network self-tests skipped: boot option off\n"
SUITE_PASSED = r"  Results: 10 passed, 0 failed\n  ALL TESTS PASSED\n"
PASSED = NET_SKIPPED + nvme_line() + INITRAMFS + PERSIST + SUITE_PASSED
# The guard boot (no \harland\storage-format): kfs leaves harland-data alone.
GUARD_SERIAL = (r"kfs: block device 1 holds data that is not a goliath image; not using it\n"
                r"  [!!] Persistent storage (disk holds other data; boot option storage-format formats it)\n")


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
        "GUARD_SERIAL": GUARD_SERIAL,
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
    # Two boots: the guard boot, then the one with storage-format.
    assert len(argv.splitlines()) == 2
    assert "PASS (guard): kfs refused harland-data" in r.stdout
    assert "PASS (guard): harland-data still holds the pattern" in r.stdout
    assert "not using it" in (keep / "nvme-guard.log").read_text()


# --------------------------------------------------------------------------
# AGAST #4883: without storage-format, kfs must not touch harland-data
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_guard_boot_without_the_refusal_line_fails(tree):
    """The mutation that drops the storage-claim guard: kfs treats the
    patterned disk as blank and says nothing."""
    r = _run(tree, PASSED, env_extra={"FAKE_GUARD_SERIAL": PERSIST})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (guard): kfs did not log" in r.stdout


@pytest.mark.integration
def test_guard_boot_that_writes_the_data_disk_fails(tree):
    """kfs logs the refusal but a save still reaches the disk."""
    r = _run(tree, PASSED, env_extra={"FAKE_GUARD_WRITE": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (guard): the boot without storage-format wrote" in r.stdout


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
    """The kernel says persistent storage came up, but nothing reached the
    disk: the mutation that drops the NVMe write command's doorbell."""
    r = _run(tree, PASSED, persist=False)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not save a goliath image" in r.stdout


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


PASSED_4K = NET_SKIPPED + nvme_line(lba=4096) + INITRAMFS + PERSIST + SUITE_PASSED


@pytest.mark.integration
def test_network_initialized_without_the_boot_option_fails(tree):
    """The mutation that runs the boot-path NIC tests unconditionally
    (AGAST #4335): this ESP has no \\harland\\net-selftest, so the kernel must
    not even initialize the stack (which probes ENA)."""
    r = _run(tree, NET_SKIPPED + nvme_line() + INITRAMFS + PERSIST + SUITE_PASSED
             + r"[ena] Initializing ENA driver...\n")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "network without the boot option" in r.stdout


@pytest.mark.integration
def test_missing_network_skip_line_fails(tree):
    """The boot must say the NIC tests are off, so a serial log without the
    line can't pass as a gated boot."""
    r = _run(tree, nvme_line() + INITRAMFS + PERSIST + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "skip the network self-tests" in r.stdout


@pytest.mark.integration
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


@pytest.mark.integration
def test_4k_variant_fails_if_the_driver_saw_512_byte_lbas(tree):
    """QEMU ignored the option, or the driver misreads LBADS: the pattern
    still hashes right, so only the logged LBA size catches it."""
    r = _run(tree, PASSED, env_extra={"NVME_LBA_SIZE": "4096"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: harland-data" in r.stdout


@pytest.mark.integration
def test_default_variant_keeps_512_byte_lbas(tree):
    r = _run(tree, PASSED_4K)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "logical_block_size" not in (tree["tmp"] / "stub.log").read_text()


@pytest.mark.integration
def test_unknown_lba_size_is_refused(tree):
    r = _run(tree, PASSED, env_extra={"NVME_LBA_SIZE": "1024"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NVME_LBA_SIZE" in r.stdout


@pytest.mark.integration
def test_sectors_beside_persists_writes_must_keep_the_pattern(tree):
    """goliath writes its header to sector 0 alone; on 4 KiB LBAs sector 1
    (the unused second header) shares LBA 0 with it, so a write without
    read-modify-write zeroes it."""
    r = _run(tree, PASSED_4K, env_extra={"NVME_LBA_SIZE": "4096", "FAKE_CLOBBER": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "clobbered: 1" in r.stdout
