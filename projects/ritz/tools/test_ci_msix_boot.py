#!/usr/bin/env python3
"""CI must boot harland with PCI devices on MSI-X (AGAST #1852).

projects/harland/tools/test_msix_boot.sh boots the kernel under OVMF with a
virtio-net NIC and an NVMe controller. It passes only if the NVMe's MSI-X
table is found, virtio-net comes up in MSI-X mode, the NIC's interrupt
counter is > 0, and init's Tier-1 suite still reports ALL TESTS PASSED. The
NIC is modern-only with a 1024-entry RX queue (AGAST #3576), so it must also
come up over the MMIO transport, cap that queue at 256 and get a DHCP lease.

It is a build-all step after the Tier-1 boot, so every room's gate runs it.
Like that boot (test_ci_harland_boot.py), these tests pin:

  * the wiring: the step exists, gates for real, has a timeout, and keeps
    its serial log with the uploaded boot logs;
  * the verdicts: a missing tool is a SETUP ERROR (ci_local's exit 3, never
    anything else -- run-gate.sh relies on that, see
    test_ci_local.test_real_build_all_job_is_rz_build_all_then_the_e2e), and
    every failed check is exit 1. The script runs against a stub QEMU (the
    one test_ci_harland_boot.py uses), so no QEMU, OVMF or kernel build is
    needed.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_msix_boot.py -q
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
MSIX_SCRIPT = "projects/harland/tools/test_msix_boot.sh"
TIER1_SCRIPT = "projects/harland/tools/test_tier1_boot.sh"

# The same stubs as test_ci_harland_boot.py (kept local: tools/ test modules
# don't import each other). The QEMU stub writes $FAKE_SERIAL to the
# `-serial file:PATH` it was given and idles until killed; every argv goes
# to $STUB_LOG.
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

NVME_TABLE = r"[msix] 00:05.00 1B36:0010: 65 vectors, table BAR0+0x2000\n"
NIC_ON = r"[msix] virtio-net: MSI-X on, vectors config=64 rx=65 tx=66\n"


def interrupts(n: int) -> str:
    return rf"[msix] virtio-net interrupts: {n}\n"


NET_MODERN = r"[virtio-net] Transport: modern (MMIO)\n"
RX_CAPPED = r"[virtio-net] Queue 0: size=256 (device max 1024)\n"
DHCP_OK = r"[dhcp] Configured!\n"
MODERN_OK = NET_MODERN + RX_CAPPED + DHCP_OK


PASSED = NVME_TABLE + MODERN_OK + NIC_ON + interrupts(8) + SUITE_PASSED


# --------------------------------------------------------------------------
# Wiring: main.yml
# --------------------------------------------------------------------------


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _step_index(steps: list[dict], script: str) -> int:
    hits = [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]
    assert len(hits) == 1, f"want exactly one build-all step running {script}, got {hits}"
    return hits[0]


def test_msix_boot_script_exists():
    assert (REPO / MSIX_SCRIPT).is_file()


def test_msix_boot_runs_after_the_tier1_boot_and_before_the_log_upload():
    steps = _build_all()
    msix = _step_index(steps, MSIX_SCRIPT)
    assert msix > _step_index(steps, TIER1_SCRIPT)
    uploads = [i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))]
    assert uploads and min(uploads) > msix, "msix.log must be uploaded too"


def test_msix_step_is_a_real_gate_with_a_timeout():
    step = _build_all()[_step_index(_build_all(), MSIX_SCRIPT)]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    # A self-contained step: ci_local may one day run steps out of order.
    assert "SKIP_BUILD" not in step["run"]
    [parsed] = [s for s in ci_local.load_steps() if MSIX_SCRIPT in s.run]
    assert not parsed.is_setup


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / MSIX_SCRIPT, tools / "test_msix_boot.sh")
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
    return {"root": root, "script": tools / "test_msix_boot.sh", "stubs": stubs,
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


def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False, qemu_img=False, full_path=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


def test_missing_qemu_img_is_a_setup_error(tree):
    r = _run(tree, qemu_img=False, full_path=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-img" in r.stderr


def test_missing_ovmf_is_a_setup_error(tree):
    r = _run(tree, PASSED, env_extra={"OVMF_CODE": str(tree["tmp"] / "nope.fd")})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "OVMF" in r.stderr


def test_build_missing_a_toolchain_binary_is_a_setup_error(tree):
    _stub(tree["root"], "rz", f"#!/usr/bin/env bash\nexit {ci_local.EXIT_SETUP}\n")
    r = _run(tree, PASSED, env_extra={"SKIP_BUILD": "0"})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr


def test_build_failure_is_a_failure(tree):
    _stub(tree["root"], "rz", "#!/usr/bin/env bash\nexit 1\n")
    r = _run(tree, PASSED, env_extra={"SKIP_BUILD": "0"})
    assert r.returncode == 1, r.stdout + r.stderr


def test_all_checks_pass_and_the_serial_log_is_kept(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, PASSED, env_extra={"KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: virtio-net delivered 8 MSI-X interrupts" in r.stdout
    assert "interrupts: 8" in (keep / "msix.log").read_text()


def test_boot_attaches_a_nic_on_user_net_and_an_nvme(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert (
        "virtio-net-pci,netdev=net0,romfile=,disable-legacy=on,rx_queue_size=1024"
        in argv
    )
    assert "-netdev user,id=net0" in argv
    assert "-device nvme," in argv


@pytest.mark.parametrize(
    "drop, want",
    [
        (NET_MODERN, "was not driven over the modern (MMIO) transport"),
        (RX_CAPPED, "RX queue was not capped from 1024 to 256"),
        (DHCP_OK, "DHCP got no lease"),
    ],
    ids=["legacy-transport", "queue-not-capped", "no-dhcp-lease"],
)
def test_modern_nic_check_missing_fails(tree, drop, want):
    r = _run(tree, PASSED.replace(drop, ""))
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout


def test_zero_interrupts_fails(tree):
    """The NIC in MSI-X mode but nothing delivered: the mutation that drops
    msix_dispatch from irq_handler, or leaves the table entries masked."""
    r = _run(tree, NVME_TABLE + MODERN_OK + NIC_ON + interrupts(0) + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "counter is 0, want > 0" in r.stdout


def test_missing_counter_fails(tree):
    r = _run(tree, NVME_TABLE + MODERN_OK + NIC_ON + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "counter is missing" in r.stdout


def test_nic_not_in_msix_mode_fails(tree):
    r = _run(tree, NVME_TABLE + MODERN_OK + interrupts(3) + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not come up in MSI-X mode" in r.stdout


def test_no_nvme_msix_table_fails(tree):
    r = _run(tree, MODERN_OK + NIC_ON + interrupts(3) + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NVMe controller" in r.stdout


def test_exception_fails_even_if_everything_else_passed(tree):
    r = _run(tree, r"EXCEPTION: #GP\nRIP=0x1\nCR2=0\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


def test_no_verdict_before_the_timeout_fails(tree):
    r = _run(tree, NVME_TABLE + NIC_ON + interrupts(8))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout
