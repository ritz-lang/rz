#!/usr/bin/env python3
"""CI must boot harland with xHCI controllers and USB keyboards (AGAST #4887),
type into rzsh on one (AGAST #4888), and survive a controller error and a
hot-plug (AGAST #4889).

projects/harland/tools/test_usb_boot.sh boots harland under OVMF with two of
QEMU's qemu-xhci: the first with two usb-kbd keyboards, one forced to full
speed (usb_version=1), the second with one keyboard and the fault-usb boot
option, which fails that controller once its keyboard is ready.
drivers/usb brings each controller up on its own MSI-X vector aimed at the
BSP and enumerates each keyboard on events alone, then resets the failed
controller alone and enumerates its keyboard again. These pin:

  * the wiring: the step runs after the APIC ID 256 boot and before the log
    upload, gates for real, has a timeout and keeps usb.log; `make test-usb`
    runs the same script;
  * the verdicts, against a stub QEMU (no QEMU, OVMF or kernel build): the
    real boot's log passes, and each enumeration step's line missing fails,
    as do a port seen connected twice (an interrupt re-entering the
    boot-time port scan), no MSI-X vector, both controllers on one vector,
    the failed controller not reset or not back, the other one disturbed, a
    failed step, a panic and no Tier-1 verdict. A missing QEMU, or one without qemu-xhci, is a SETUP
    ERROR (exit 3).
  * the keyboard boot (`test_usb_boot.sh keyboard`, #4888): its own CI step
    after the enumeration boot, and `make test-usb-kbd`; against a stub
    fbcon_screen.py, it boots with the USB keyboard as the only input (q35,
    i8042=off, -serial none) on the second of two controllers, types each
    step the docs promise, then unplugs and replugs it over QMP and types
    again.
  * the fallback boots (`keyboard-msi`, `keyboard-poll`, #4891): their own
    CI steps after the keyboard boot, and `make test-usb-msi` /
    `test-usb-poll`; against the stub, each puts its boot option on the ESP
    (usb-no-msix, usb-poll), waits for hc1 running that way on screen, and
    types `echo hi` and Ctrl-C.

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

# The xHCI and USB lines of a real boot (2026-11-27, QEMU 10.2), in order.
def controller(hc: int, bdf: str) -> str:
    return (
        rf"[xhci] hc{hc} {bdf} 1B36:000D v1.00: 64 slots, 8 ports, 32-byte contexts,"
        r" 0 scratchpads, 64-bit DMA\n"
        rf"[xhci] hc{hc} ports 5-8: USB 2.0\n"
        rf"[xhci] hc{hc} ports 1-4: USB 3.0\n"
    )


def running(hc: int, vector: int) -> str:
    return rf"[xhci] hc{hc} running: MSI-X vector {vector} -> BSP\n"


CONTROLLER_0 = controller(0, "00:04.0")
CONTROLLER_1 = controller(1, "00:05.0")
RUNNING = running(0, 64)
RUNNING_1 = running(1, 65)
CONNECTED_5 = r"[usb] hc0 port 5: connected (USB 2)\n"
CONNECTED_6 = r"[usb] hc0 port 6: connected (USB 2)\n"
ENABLED_HIGH = r"[usb] hc0 port 5: enabled, high speed\n"
ENABLED_FULL = r"[usb] hc0 port 6: enabled, full speed\n"
ADDRESSED_1 = r"[usb] hc0 slot 1 addressed: port 5, address 1, EP0 64 bytes\n"
ADDRESSED_2 = r"[usb] hc0 slot 2 addressed: port 6, address 2, EP0 8 bytes\n"
DEVICE_1 = r"[usb] hc0 slot 1: device 0627:0001, USB 2.0, class 0, 1 configuration(s)\n"
MPS_2 = r"[usb] hc0 slot 2: EP0 max packet 8 (from the device descriptor)\n"
DEVICE_2 = r"[usb] hc0 slot 2: device 0627:0001, USB 2.0, class 0, 1 configuration(s)\n"


def config(slot: int, hc: int = 0) -> str:
    return (
        rf"[usb] hc{hc} slot {slot}: config 1, 34 bytes\n"
        rf"[usb] hc{hc} slot {slot}:   interface 0 class 3/1/1, 1 endpoint(s)\n"
        rf"[usb] hc{hc} slot {slot}:   endpoint 0x81, 8 bytes, interval 6\n"
    )


def configured(slot: int, hc: int = 0) -> str:
    return rf"[usb] hc{hc} slot {slot}: configured (configuration 1)\n"


def ready(slot: int, hc: int = 0) -> str:
    return rf"[usb] hc{hc} slot {slot}: keyboard ready (endpoint 0x81, interval 6, MSI-X)\n"


# hc1's one keyboard, enumerated at boot and again after its reset.
HC1_KEYBOARD = (
    r"[usb] hc1 port 5: connected (USB 2)\n"
    r"[usb] hc1 port 5: enabled, high speed\n"
    r"[usb] hc1 slot 1 addressed: port 5, address 1, EP0 64 bytes\n"
    + config(1, 1)
    + configured(1, 1)
)
HC1_READY = ready(1, 1)
HC1_READY_AGAIN = HC1_READY  # the same line, after the reset: `without` drops the last
FAULT = r"[xhci] hc1: fault-usb: forcing a controller error\n"
# The suite's output shares the line: the check must not need line start.
HC1_ERROR = r"[test] mmap_isolation ... [xhci] hc1: controller error (USBSTS 0x00001008): resetting it alone\n"
HC1_RESET = r"[xhci] hc1: reset done, ports re-enumerating\n"
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
    ready(1),
    ready(2),
]
RECOVERY = [HC1_KEYBOARD, HC1_READY, FAULT, HC1_ERROR, HC1_RESET, HC1_KEYBOARD, HC1_READY_AGAIN]
PASSED_LINES = [CONTROLLER_0, RUNNING, CONTROLLER_1, RUNNING_1, *ENUMERATION, OK_LINE, *RECOVERY, SUITE_PASSED]


def log(lines: list[str]) -> str:
    return "".join(lines)


def without(line: str) -> str:
    """The passing log with `line` taken out, once."""
    parts = list(PASSED_LINES)
    parts.reverse()
    parts.remove(line)
    parts.reverse()
    return log(parts)


# --------------------------------------------------------------------------
# Wiring: main.yml and the Makefile
# --------------------------------------------------------------------------


def _build_all() -> list[dict]:
    return yaml.safe_load(ci_local.WORKFLOW.read_text())["jobs"]["build-all"]["steps"]


def _indices(steps: list[dict], script: str, mode: str = "") -> list[int]:
    """Steps that run `script`; with `mode`, only those passing it, and
    without, only those passing none."""
    found = []
    for i, s in enumerate(steps):
        run = str(s.get("run", ""))
        if script not in run:
            continue
        args = run.split(script, 1)[1].split()
        if (args[:1] == [mode]) if mode else not args:
            found.append(i)
    return found


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
    parsed = [s for s in ci_local.load_steps() if s.run.rstrip().endswith(USB_SCRIPT)]
    assert len(parsed) == 1 and not parsed[0].is_setup


def test_keyboard_boot_is_its_own_gate_after_the_enumeration_boot():
    steps = _build_all()
    [usb] = _indices(steps, USB_SCRIPT)
    [kbd] = _indices(steps, USB_SCRIPT, "keyboard")
    uploads = [
        i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))
    ]
    assert usb < kbd < min(uploads)
    step = steps[kbd]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    text = (REPO / "projects/harland/Makefile").read_text()
    assert "\ntest-usb-kbd:\n\t./tools/test_usb_boot.sh keyboard\n" in text


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
    # ...and stages its packages through indium's stager (AGAST #4834).
    (root / "projects/indium/tools").mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "projects/indium/tools/stage_initramfs.sh",
                root / "projects/indium/tools/stage_initramfs.sh")
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
    assert "-device qemu-xhci,id=xhci0" in argv and "-device qemu-xhci,id=xhci1" in argv
    assert argv.count("-device usb-kbd,bus=xhci0.0") == 2
    assert "usb-kbd,bus=xhci0.0,usb_version=1" in argv
    assert argv.count("-device usb-kbd,bus=xhci1.0") == 1


@pytest.mark.integration
@pytest.mark.parametrize(
    "line,why",
    [
        pytest.param(RUNNING, "two distinct MSI-X vectors", id="not-running"),
        pytest.param(ENABLED_HIGH, "high-speed keyboard", id="no-high-speed"),
        pytest.param(ENABLED_FULL, "full-speed keyboard", id="no-full-speed"),
        pytest.param(MPS_2, "first 8 bytes", id="no-ep0-size-read"),
        pytest.param(ADDRESSED_2, "slot 2 is addressed", id="not-addressed"),
        pytest.param(DEVICE_1, "slot 1: the device descriptor", id="no-device-descriptor"),
        pytest.param(config(2), "slot 2: the configuration is read", id="no-config"),
        pytest.param(configured(1), "slot 1: SET_CONFIGURATION", id="not-configured"),
        pytest.param(HC1_ERROR, "only hc1 is reset", id="hc1-error-unseen"),
        pytest.param(HC1_RESET, "hc1 comes back", id="hc1-not-back"),
        pytest.param(HC1_READY_AGAIN, "keyboard ready twice", id="hc1-not-ready-again"),
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
    lines = [CONTROLLER_0, RUNNING, CONTROLLER_1, RUNNING_1, CONNECTED_5, *ENUMERATION, OK_LINE, *RECOVERY, SUITE_PASSED]
    r = _run(tree, log(lines))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "want 2 'hc0 ... connected' lines on 2 ports, got 3 on 2" in r.stdout


@pytest.mark.integration
def test_both_controllers_on_one_vector_fails(tree):
    lines = [running(1, 64) if part == RUNNING_1 else part for part in PASSED_LINES]
    r = _run(tree, log(lines))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "two distinct MSI-X vectors" in r.stdout


@pytest.mark.integration
def test_hc1_error_disturbing_hc0_fails(tree):
    """hc1's reset must leave hc0 alone: hc0 reset, or a keyboard of hc0's
    ready a second time (re-enumerated), fails."""
    for extra in (r"[xhci] hc0: controller error (USBSTS 0x00001008): resetting it alone\n", ready(1)):
        r = _run(tree, log(PASSED_LINES[:-1] + [extra, SUITE_PASSED]))
        assert r.returncode == 1, r.stdout + r.stderr
        assert "hc0 was disturbed by hc1's error" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "fallback",
    [
        pytest.param(r"[xhci] hc0 running: no vector, polled from the BSP tick\n", id="polled"),
        pytest.param(r"[xhci] hc0 running: MSI vector 64 -> BSP\n", id="plain-msi"),
    ],
)
def test_no_msix_vector_fails(tree, fallback):
    """With no boot option qemu-xhci must get MSI-X: plain MSI or the poll
    there is a broken MSI-X path, not a pass."""
    lines = [fallback if part == RUNNING else part for part in PASSED_LINES]
    r = _run(tree, log(lines))
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_a_failed_step_fails_even_if_the_rest_passed(tree):
    bad = r"[usb] hc0 port 7: command failed: no slots (9); device left unconfigured\n"
    r = _run(tree, log(PASSED_LINES[:-1] + [bad, SUITE_PASSED]))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "a device's enumeration failed" in r.stdout


@pytest.mark.integration
def test_panic_fails(tree):
    r = _run(tree, log([CONTROLLER_0, RUNNING, r"*** KERNEL PANIC ***\n"]))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "kernel panic or exception" in r.stdout


@pytest.mark.integration
def test_no_tier1_verdict_fails(tree):
    r = _run(tree, log(PASSED_LINES[:-1]))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout


# fbcon_screen.py's stand-in: its argv, one per line, then the exit code
# the test asks for.
FBCON_STUB = """import os, sys
open(os.environ["FBCON_ARGV"], "w").write("\\n".join(sys.argv[1:]))
esp = [a.split("fat:rw:", 1)[1] for a in sys.argv if "fat:rw:" in a][0]
open(os.environ["FBCON_ARGV"] + ".esp", "w").write("\\n".join(sorted(os.listdir(os.path.join(esp, "harland")))))
sys.exit(int(os.environ.get("FBCON_RC", "0")))
"""


def _keyboard_run(tree, rc: int = 0, mode: str = "keyboard") -> tuple[subprocess.CompletedProcess, list[str]]:
    tools = tree["script"].parent
    (tools / "fbcon_screen.py").write_text(FBCON_STUB)
    for rel in ("projects/indium/build/debug/init_interactive.elf", "projects/rzsh/build/debug/rzsh.elf"):
        p = tree["script"].parents[3] / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF")
    argv_file = tree["tmp"] / "fbcon.argv"
    stubs = tree["stubs"]
    q = stubs / "qemu-system-x86_64"
    q.write_text(QEMU_STUB)
    q.chmod(0o755)
    env = {
        "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
        "HOME": str(tree["tmp"]),
        "SKIP_BUILD": "1",
        "OVMF_CODE": str(tree["ovmf"]),
        "FBCON_ARGV": str(argv_file),
        "FBCON_RC": str(rc),
    }
    r = subprocess.run(
        ["/bin/bash", str(tree["script"]), mode],
        env=env, capture_output=True, text=True, timeout=60,
    )
    return r, argv_file.read_text().split("\n") if argv_file.exists() else []


def _sends(argv: list[str]) -> list[tuple[str, str]]:
    return [(argv[i + 1], argv[i + 2]) for i, a in enumerate(argv) if a == "--send"]


def _steps(argv: list[str]) -> list[str]:
    """The --send keys and --qmp-do commands, in the order they run."""
    return [argv[i + 2] for i, a in enumerate(argv) if a in ("--send", "--qmp-do")]


@pytest.mark.integration
def test_keyboard_boot_types_each_step_with_the_usb_keyboard_alone(tree):
    r, argv = _keyboard_run(tree)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: typed into rzsh on a USB keyboard" in r.stdout
    qemu = argv[argv.index("--") + 1 :]
    # The USB keyboard is the only input and the screen the only output.
    assert "q35,i8042=off" in qemu and qemu[qemu.index("-serial") + 1] == "none"
    # Two controllers, the keyboard on the second (#4889).
    assert qemu.count("qemu-xhci,id=xhci0") == 1 and qemu.count("qemu-xhci,id=xhci1") == 1
    assert qemu.count("usb-kbd,id=kbd,bus=xhci1.0") == 1
    assert _steps(argv) == [
        "e c h o spc h i ret",
        "s p i n ret",
        "ctrl-c",
        "e c h o spc shift-4 shift-slash ret",
        "e c h o spc caps_lock a b caps_lock c ret",
        "e c h o spc x@1200 ret",
        # Hot-plug: unplug, replug once the port is detached, type again.
        "device_del id=kbd",
        "device_add driver=usb-kbd id=kbd bus=xhci1.0",
        "e c h o spc b a c k ret",
    ]
    expects = [argv[i + 1] for i, a in enumerate(argv) if a == "--expect"]
    assert any("hc1 slot 1: keyboard ready" in e and e.endswith(", MSI-X\\)") for e in expects)
    assert any("back" in e for e in expects), "typing must work after the replug"
    assert any("130" in e for e in expects), "Ctrl-C's kill must show $? = 130"


@pytest.mark.integration
def test_keyboard_boot_failure_fails(tree):
    r, _ = _keyboard_run(tree, rc=1)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS" not in r.stdout


# --------------------------------------------------------------------------
# The fallbacks (#4891): plain MSI, and the BSP tick's poll
# --------------------------------------------------------------------------

FALLBACKS = {
    # mode: (boot option on the ESP, the source hc1's keyboard-ready line
    # names, make target)
    "keyboard-msi": ("usb-no-msix", "MSI", "test-usb-msi"),
    "keyboard-poll": ("usb-poll", "polled", "test-usb-poll"),
}


@pytest.mark.parametrize("mode", sorted(FALLBACKS))
def test_each_fallback_boot_is_its_own_gate_after_the_keyboard_boot(mode):
    steps = _build_all()
    [kbd] = _indices(steps, USB_SCRIPT, "keyboard")
    [fb] = _indices(steps, USB_SCRIPT, mode)
    uploads = [
        i for i, s in enumerate(steps) if "upload-artifact" in str(s.get("uses", ""))
    ]
    assert kbd < fb < min(uploads)
    step = steps[fb]
    assert "continue-on-error" not in step
    assert "|| true" not in step["run"]
    assert step.get("timeout-minutes")
    assert "boot-logs" in step["run"]
    target = FALLBACKS[mode][2]
    text = (REPO / "projects/harland/Makefile").read_text()
    assert f"\n{target}:\n\t./tools/test_usb_boot.sh {mode}\n" in text
    assert target in text.split("\n.PHONY:", 1)[1].split("\n", 1)[0]


@pytest.mark.integration
@pytest.mark.parametrize("mode", sorted(FALLBACKS))
def test_fallback_boot_sets_its_option_and_types_on_it(tree, mode):
    option, via, _ = FALLBACKS[mode]
    r, argv = _keyboard_run(tree, mode=mode)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: typed into rzsh on a USB keyboard" in r.stdout
    esp = (tree["tmp"] / "fbcon.argv.esp").read_text().split("\n")
    assert option in esp, esp
    others = {o for o, _, _ in FALLBACKS.values()} | {"fault-usb"}
    assert not (others - {option}) & set(esp), esp
    expects = [argv[i + 1] for i, a in enumerate(argv) if a == "--expect"]
    assert any("hc1 slot 1: keyboard ready" in e and e.endswith(f", {via}\\)") for e in expects), expects
    absents = [argv[i + 1] for i, a in enumerate(argv) if a == "--absent"]
    assert any("hc[01] running:" in a for a in absents), "another source must fail"
    assert any("130" in e for e in expects), "Ctrl-C's kill must show $? = 130"
    assert _steps(argv) == [
        "e c h o spc h i ret",
        "s p i n ret",
        "ctrl-c",
        "e c h o spc shift-4 shift-slash ret",
    ]
    qemu = argv[argv.index("--") + 1 :]
    assert qemu.count("usb-kbd,id=kbd,bus=xhci1.0") == 1
    # qemu-xhci has an MSI capability only with msi=on: the MSI boot needs
    # it on both controllers, or its "MSI" boot is the poll in disguise.
    opt = ",msi=on" if mode == "keyboard-msi" else ""
    assert qemu.count(f"qemu-xhci,id=xhci0{opt}") == 1
    assert qemu.count(f"qemu-xhci,id=xhci1{opt}") == 1


@pytest.mark.integration
def test_keyboard_boot_sets_no_fallback_option(tree):
    r, _ = _keyboard_run(tree)
    assert r.returncode == 0, r.stdout + r.stderr
    esp = (tree["tmp"] / "fbcon.argv.esp").read_text().split("\n")
    assert "usb-no-msix" not in esp and "usb-poll" not in esp


@pytest.mark.integration
def test_fallback_boot_failure_fails(tree):
    r, _ = _keyboard_run(tree, rc=1, mode="keyboard-poll")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS" not in r.stdout


@pytest.mark.integration
def test_a_keyboard_ready_off_msix_fails(tree):
    """The enumeration boot's keyboards must be serviced on MSI-X: a ready
    line naming plain MSI or the poll does not count."""
    lines = [part.replace("MSI-X)", "polled)") if part == ready(2) else part for part in PASSED_LINES]
    r = _run(tree, log(lines))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "hc0 was disturbed" in r.stdout
