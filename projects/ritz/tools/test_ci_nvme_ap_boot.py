#!/usr/bin/env python3
"""CI must boot harland on two CPUs and drive an AP-issued NVMe command (AGAST #4220).

projects/harland/tools/test_nvme_ap_boot.sh boots the kernel under OVMF on
two CPUs with one NVMe controller. The BSP calls the AP through an IPI; the
AP reads the end of the disk, and its command must go through a per-CPU I/O
queue pair whose MSI-X entry targets that AP. It passes only if the read
returns the pattern the script wrote AND the command waited for its vector
and the vector fired on the AP (waited=W, interrupted=I, both > 0): a driver
that polls from APs, or aims every I/O vector at the BSP, fails.

Like test_ci_msix_boot.py this pins:

  * the wiring: the step exists, gates for real, has a timeout, runs before
    the boot-log upload, and keeps its serial log;
  * the verdicts: a missing tool is a SETUP ERROR (ci_local's exit 3), every
    failed check is exit 1. The script runs against a stub QEMU, so no QEMU,
    OVMF or kernel build is needed.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_nvme_ap_boot.py -q
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
AP_SCRIPT = "projects/harland/tools/test_nvme_ap_boot.sh"
TIER1_SCRIPT = "projects/harland/tools/test_tier1_boot.sh"

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
SUITE_PASSED = r"[test] hello ... PASS (exit=0)\n  Results: 10 passed, 0 failed\n  ALL TESTS PASSED\n"


def ap_fnv() -> int:
    """FNV-1a (32-bit) of sectors 32568-32767 of the 16 MiB image the script
    writes: sector N is ("LBA" + N as u32 LE + "!") * 64."""
    h = 0x811C9DC5
    for n in range(32568, 32768):
        for b in (b"LBA" + struct.pack("<I", n) + b"!") * 64:
            h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


FNV = ap_fnv()

AP_STARTED = r"    Booting AP 1...    AP 1 started!\n"
NVME_ON = r"[msix] nvme harland-ap: MSI-X on, vectors admin=64 io=80, CPUs=2\n"
AP_READ = rf"[msix] nvme AP 1: nsid 1: LBA 32568-32767 fnv1a={FNV}, waited=2, interrupted=2\n"

PASSED = AP_STARTED + NVME_ON + AP_READ + SUITE_PASSED


# --------------------------------------------------------------------------
# Wiring: main.yml
# --------------------------------------------------------------------------


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _step_index(steps: list[dict], script: str) -> int:
    hits = [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]
    assert len(hits) == 1, f"want exactly one build-all step running {script}, got {hits}"
    return hits[0]


def test_ap_boot_script_exists():
    assert (REPO / AP_SCRIPT).is_file()


def test_ap_boot_runs_after_the_tier1_boot_and_before_the_log_upload():
    steps = _build_all()
    ap = _step_index(steps, AP_SCRIPT)
    assert ap > _step_index(steps, TIER1_SCRIPT)
    uploads = [i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads and min(uploads) > ap, "nvme-ap.log must be uploaded too"


def test_ap_step_is_a_real_gate_with_a_timeout():
    step = _build_all()[_step_index(_build_all(), AP_SCRIPT)]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    assert "SKIP_BUILD" not in step["run"]
    [parsed] = [s for s in ci_local.load_steps() if AP_SCRIPT in s.run]
    assert not parsed.is_setup


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / AP_SCRIPT, tools / "test_nvme_ap_boot.sh")
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
    return {"root": root, "script": tools / "test_nvme_ap_boot.sh", "stubs": stubs,
            "ovmf": ovmf, "tmp": tmp_path}


def _stub(stubs: Path, name: str, body: str) -> None:
    p = stubs / name
    p.write_text(body)
    p.chmod(0o755)


def _run(tree, serial: str = "", *, qemu=True, qemu_img=True, full_path=True,
         env_extra=None) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    if qemu:
        _stub(stubs, "qemu-system-x86_64", QEMU_STUB)
    if qemu_img:
        _stub(stubs, "qemu-img", QEMU_IMG_STUB)
    if full_path:
        path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    else:
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
    return subprocess.run(["/bin/bash", str(tree["script"])], env=env,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.integration
def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False, qemu_img=False, full_path=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


@pytest.mark.integration
def test_build_failure_is_a_failure(tree):
    _stub(tree["root"], "rz", "#!/usr/bin/env bash\nexit 1\n")
    r = _run(tree, PASSED, env_extra={"SKIP_BUILD": "0"})
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_all_checks_pass_and_the_serial_log_is_kept(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, PASSED, env_extra={"KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: a second CPU started" in r.stdout
    assert "PASS: the AP-issued command waited for its vector" in r.stdout
    assert "AP 1 started" in (keep / "nvme-ap.log").read_text()


@pytest.mark.integration
def test_boot_is_two_cpus_with_an_nvme(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "-smp 2 " in argv
    assert "-device nvme," in argv


@pytest.mark.integration
@pytest.mark.parametrize(
    "serial, want",
    [
        (NVME_ON + AP_READ + SUITE_PASSED, "no AP started"),
        (AP_STARTED + AP_READ + SUITE_PASSED, "did not come up in MSI-X mode"),
        (AP_STARTED + NVME_ON + SUITE_PASSED, "no AP-issued NVMe read logged"),
        # The AP's command polled instead of waiting
        (AP_STARTED + NVME_ON + f"[msix] nvme AP 1: nsid 1: LBA 32568-32767 fnv1a={FNV}, waited=0, interrupted=2\n" + SUITE_PASSED,
         "did not wait for its MSI-X vector"),
        # It waited, but the vector never fired on the AP (aimed at the BSP)
        (AP_STARTED + NVME_ON + f"[msix] nvme AP 1: nsid 1: LBA 32568-32767 fnv1a={FNV}, waited=2, interrupted=0\n" + SUITE_PASSED,
         "never fired on the AP"),
        (AP_STARTED + NVME_ON + "[msix] nvme AP 1: nsid 1: LBA 32568-32767 fnv1a=12345, waited=2, interrupted=2\n" + SUITE_PASSED,
         f"want fnv1a={FNV}"),
    ],
    ids=["no-ap", "no-msix", "no-ap-read", "polled", "wrong-destination", "bad-data"],
)
def test_ap_check_fails(tree, serial, want):
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout


@pytest.mark.integration
def test_exception_fails_even_if_everything_else_passed(tree):
    r = _run(tree, r"EXCEPTION: #PF\nRIP=0x1\nCR2=0\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_no_verdict_before_the_timeout_fails(tree):
    r = _run(tree, AP_STARTED + NVME_ON + AP_READ)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout
