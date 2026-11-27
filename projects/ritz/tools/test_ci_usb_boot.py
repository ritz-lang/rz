#!/usr/bin/env python3
"""CI must boot harland with an xHCI controller and USB keyboards (AGAST #4887).

projects/harland/tools/test_usb_boot.sh boots harland under OVMF with QEMU's
qemu-xhci and two usb-kbd keyboards, one forced to full speed
(usb_version=1). drivers/usb brings the controller up on an MSI-X vector
aimed at the BSP and enumerates each keyboard on events alone. These pin:

  * the wiring: the step runs after the APIC ID 256 boot and before the log
    upload, gates for real, has a timeout and keeps usb.log; `make test-usb`
    runs the same script;
  * the verdicts, against a stub QEMU (no QEMU, OVMF or kernel build): the
    real boot's log passes, and each enumeration step's line missing fails,
    as do a port seen connected twice (an interrupt re-entering the
    boot-time port scan), no MSI-X vector, a failed step, a panic and no
    Tier-1 verdict. A missing QEMU, or one without qemu-xhci, is a SETUP
    ERROR (exit 3).

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_usb_boot.py -q
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
USB_SCRIPT = "projects/harland/tools/test_usb_boot.sh"
IRQ_DEST_SCRIPT = "projects/harland/tools/test_irq_dest_boot.sh"

# The QEMU stub answers `-device help` with $FAKE_DEVICES (qemu-xhci unless
# the test says otherwise), writes $FAKE_SERIAL to the `-serial file:PATH`
# it was given, then idles until killed. Every boot argv goes to $STUB_LOG.
QEMU_STUB = r"""#!/usr/bin/env bash
if [ "${1:-}" = "-device" ] && [ "${2:-}" = "help" ]; then
    printf '%b' "${FAKE_DEVICES-name \"qemu-xhci\", bus PCI\n}"
    exit 0
fi
echo "$@" >> "$STUB_LOG"
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$FAKE_SERIAL" > "${a#file:}"; fi
    prev="$a"
done
sleep 30
"""
MKINITRAMFS_STUB = """import sys
out = sys.argv[sys.argv.index("--output") + 1]
open(out, "wb").write(bytes(512))
"""

# The xHCI and USB lines of a real boot (2026-11-27, QEMU 8.2), in order.
CONTROLLER = (
    r"[xhci] 00:04.0 1B36:000D v1.00: 64 slots, 8 ports, 32-byte contexts,"
    r" 0 scratchpads, 64-bit DMA\n"
    r"[xhci] ports 5-8: USB 2.0\n"
    r"[xhci] ports 1-4: USB 3.0\n"
)
RUNNING = r"[xhci] running: MSI-X vector 64 -> BSP\n"
CONNECTED_5 = r"[usb] port 5: connected (USB 2)\n"
CONNECTED_6 = r"[usb] port 6: connected (USB 2)\n"
ENABLED_HIGH = r"[usb] port 5: enabled, high speed\n"
ENABLED_FULL = r"[usb] port 6: enabled, full speed\n"
ADDRESSED_1 = r"[usb] slot 1 addressed: port 5, address 1, EP0 64 bytes\n"
ADDRESSED_2 = r"[usb] slot 2 addressed: port 6, address 2, EP0 8 bytes\n"
DEVICE_1 = r"[usb] slot 1: device 0627:0001, USB 2.0, class 0, 1 configuration(s)\n"
MPS_2 = r"[usb] slot 2: EP0 max packet 8 (from the device descriptor)\n"
DEVICE_2 = r"[usb] slot 2: device 0627:0001, USB 2.0, class 0, 1 configuration(s)\n"


def config(slot: int) -> str:
    return (
        rf"[usb] slot {slot}: config 1, 34 bytes\n"
        rf"[usb] slot {slot}:   interface 0 class 3/1/1, 1 endpoint(s)\n"
        rf"[usb] slot {slot}:   endpoint 0x81, 8 bytes, interval 6\n"
    )


def configured(slot: int) -> str:
    return rf"[usb] slot {slot}: configured (configuration 1)\n"


OK_LINE = r"  [OK] USB (xHCI)\n"
SUITE_PASSED = r"  Results: 10 passed, 0 failed\n  ALL TESTS PASSED\n"
ENUMERATION = [
    CONNECTED_5,
    CONNECTED_6,
    ENABLED_HIGH,
    ENABLED_FULL,
    ADDRESSED_1,
    ADDRESSED_2,
    DEVICE_1,
    MPS_2,
    DEVICE_2,
    config(1),
    configured(1),
    config(2),
    configured(2),
]
PASSED_LINES = [CONTROLLER, RUNNING, *ENUMERATION, OK_LINE, SUITE_PASSED]


def log(lines: list[str]) -> str:
    return "".join(lines)


def without(line: str) -> str:
    return log([part for part in PASSED_LINES if part != line])


# --------------------------------------------------------------------------
# Wiring: main.yml and the Makefile
# --------------------------------------------------------------------------


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _indices(steps: list[dict], script: str) -> list[int]:
    return [i for i, s in enumerate(steps) if script in str(s.get("run", ""))]


def test_usb_boot_runs_after_the_irq_dest_boot_and_before_the_log_upload():
    assert (REPO / USB_SCRIPT).is_file()
    steps = _build_all()
    [usb] = _indices(steps, USB_SCRIPT)
    assert usb > max(_indices(steps, IRQ_DEST_SCRIPT))
    uploads = [
        i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))
    ]
    assert uploads and min(uploads) > usb, "usb.log must be uploaded too"


def test_usb_step_is_a_real_gate_with_a_timeout():
    steps = _build_all()
    [step] = [steps[i] for i in _indices(steps, USB_SCRIPT)]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    parsed = [s for s in ci_local.load_steps() if USB_SCRIPT in s.run]
    assert len(parsed) == 1 and not parsed[0].is_setup


def test_make_test_usb_runs_the_script():
    text = (REPO / "projects/harland/Makefile").read_text()
    assert "\ntest-usb:\n\t./tools/test_usb_boot.sh\n" in text
    assert "test-usb" in text.split("\n.PHONY:", 1)[1].split("\n", 1)[0]


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / USB_SCRIPT, tools / "test_usb_boot.sh")
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
    return {"script": tools / "test_usb_boot.sh", "stubs": stubs, "ovmf": ovmf, "tmp": tmp_path}


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
def test_qemu_without_qemu_xhci_is_a_setup_error(tree):
    r = _run(tree, env_extra={"FAKE_DEVICES": r'name "e1000", bus PCI\n'})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "qemu-xhci" in r.stderr


@pytest.mark.integration
def test_passes_with_both_keyboards_configured(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, log(PASSED_LINES), env_extra={"KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "FAIL" not in r.stdout
    assert "configured (configuration 1)" in (keep / "usb.log").read_text()
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "-device qemu-xhci,id=xhci" in argv
    assert argv.count("-device usb-kbd,bus=xhci.0") == 2
    assert "usb-kbd,bus=xhci.0,usb_version=1" in argv


@pytest.mark.integration
@pytest.mark.parametrize(
    "line,why",
    [
        pytest.param(RUNNING, "running on an MSI-X vector", id="not-running"),
        pytest.param(ENABLED_HIGH, "high-speed keyboard", id="no-high-speed"),
        pytest.param(ENABLED_FULL, "full-speed keyboard", id="no-full-speed"),
        pytest.param(MPS_2, "first 8 bytes", id="no-ep0-size-read"),
        pytest.param(ADDRESSED_2, "slot 2 is addressed", id="not-addressed"),
        pytest.param(DEVICE_1, "slot 1: the device descriptor", id="no-device-descriptor"),
        pytest.param(config(2), "slot 2: the configuration is read", id="no-config"),
        pytest.param(configured(1), "slot 1: SET_CONFIGURATION", id="not-configured"),
    ],
)
def test_each_missing_step_fails(tree, line, why):
    r = _run(tree, without(line))
    assert r.returncode == 1, r.stdout + r.stderr
    assert any(why in l for l in r.stdout.splitlines() if l.startswith("FAIL")), r.stdout


@pytest.mark.integration
def test_a_port_connected_twice_fails(tree):
    """The boot-time port scan run with interrupts on: the controller's event
    re-entered it, and the port was seen connected (and reset) twice."""
    lines = [CONTROLLER, RUNNING, CONNECTED_5, *ENUMERATION, OK_LINE, SUITE_PASSED]
    r = _run(tree, log(lines))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "want 2 'connected' lines on 2 ports, got 3 on 2" in r.stdout


@pytest.mark.integration
def test_no_msix_vector_fails(tree):
    polled = r"[xhci] running: no MSI-X vector: events wait for the polled fallback\n"
    lines = [polled if part == RUNNING else part for part in PASSED_LINES]
    r = _run(tree, log(lines))
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_a_failed_step_fails_even_if_the_rest_passed(tree):
    bad = r"[usb] port 7: command failed: no slots (9); device left unconfigured\n"
    r = _run(tree, log(PASSED_LINES[:-1] + [bad, SUITE_PASSED]))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "a device's enumeration failed" in r.stdout


@pytest.mark.integration
def test_panic_fails(tree):
    r = _run(tree, log([CONTROLLER, RUNNING, r"*** KERNEL PANIC ***\n"]))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "kernel panic or exception" in r.stdout


@pytest.mark.integration
def test_no_tier1_verdict_fails(tree):
    r = _run(tree, log(PASSED_LINES[:-1]))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout
