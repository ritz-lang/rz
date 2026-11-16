"""harland's `boot/test.sh` (make test-uefi-boot) needs no mkfs.vfat and fails
below the top milestone (AGAST #2200).

Before: test.sh formatted its ESP with a bare `mkfs.vfat`, which dosfstools
installs to /usr/sbin; a room unit's PATH (and any non-login shell's here)
has no sbin, so under `set -e` the script died with exit 127.  And
`boot/uefi_verdict.sh` exited 0 at any milestone from "Hello from Harland"
up, so a boot that stopped at MILESTONE 9 (a timeout, a regression) passed.

After: the ESP is a QEMU vvfat directory (`fat:rw:DIR`, as
tools/test_tier1_boot.sh does), so neither dosfstools nor mtools is needed;
the verdict requires MILESTONE 12 (init's Tier-1 suite: ALL TESTS PASSED)
unless a lower one is asked for; a missing tool is exit 3 (SETUP ERROR).

These run test.sh end to end against a stub qemu-system-x86_64 that writes a
canned serial log, in a copy of the harland tree with dummy build outputs,
so they need no QEMU, OVMF or build.
"""

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

HARLAND = Path(__file__).resolve().parents[2] / "harland"
BOOT = HARLAND / "boot"
VERDICT = BOOT / "uefi_verdict.sh"

# One serial line per milestone, as the kernel and init print them.
MILESTONE_LINES = {
    1: "Hello from Harland",
    2: "exit(0)",
    6: "[smp] AP 1 started",
    7: "Task 2 done",
    9: "virtio-blk: Read sector 0 OK",
    10: "[userspace] exit",
    11: "[ACPI] Initiating S5 shutdown",
    12: "ALL TESTS PASSED",
}


def _log_up_to(milestone: int) -> str:
    """A serial log that reaches `milestone` and stops (a planted early stop)."""
    lines = ["Harland UEFI Bootloader"]
    lines += [line for m, line in sorted(MILESTONE_LINES.items()) if m <= milestone]
    return "\n".join(lines) + "\n"


def _verdict(tmp_path, log, *args):
    serial = tmp_path / "serial.log"
    serial.write_text(log)
    return subprocess.run(["bash", str(VERDICT), str(serial), *args],
                          capture_output=True, text=True, timeout=30)


# --- the verdict requires milestone 12 by default -------------------------------

@pytest.mark.parametrize("reached", [1, 2, 6, 7, 9, 10, 11])
def test_verdict_fails_below_milestone_12_by_default(tmp_path, reached):
    proc = _verdict(tmp_path, _log_up_to(reached))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "below the required milestone 12" in proc.stdout


def test_verdict_passes_at_milestone_12(tmp_path):
    proc = _verdict(tmp_path, _log_up_to(12))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "MILESTONE 12" in proc.stdout


@pytest.mark.parametrize("required, reached, want", [
    (9, 9, 0), (9, 10, 0), (9, 7, 1), (1, 1, 0), (12, 11, 1),
])
def test_verdict_honours_a_required_milestone(tmp_path, required, reached, want):
    proc = _verdict(tmp_path, _log_up_to(reached), str(required))
    assert proc.returncode == want, proc.stdout + proc.stderr


def test_verdict_panic_still_fails_when_milestone_lowered(tmp_path):
    proc = _verdict(tmp_path, _log_up_to(9) + "*** KERNEL PANIC ***\n", "1")
    assert proc.returncode == 1


def test_verdict_rejects_a_bad_milestone_argument(tmp_path):
    assert _verdict(tmp_path, _log_up_to(12), "twelve").returncode == 2


# --- test.sh end to end with a stub QEMU ----------------------------------------

STUB_QEMU = textwrap.dedent("""\
    #!/bin/bash
    # Stub qemu-system-x86_64: record the ESP, write the canned serial log.
    for a in "$@"; do
        case "$a" in
            file:*) serial="${a#file:}" ;;
            *file=fat:rw:*) esp="${a#*file=fat:rw:}" ;;
        esac
    done
    { echo "ESP=$esp"; (cd "$esp" && find . -type f | sort); } > "$STUB_RECORD"
    cat "$STUB_SERIAL" > "$serial"
    """)

STUB_QEMU_IMG = textwrap.dedent("""\
    #!/bin/bash
    case "$1" in
        create) : > "$4" ;;
        convert) : > "${@: -1}" ;;
    esac
    """)


@pytest.fixture
def harness(tmp_path):
    """A copy of harland/boot with dummy build outputs and stub QEMU tools."""
    root = tmp_path / "tree"
    boot = root / "projects" / "harland" / "boot"
    boot.mkdir(parents=True)
    for name in ("test.sh", "uefi_verdict.sh"):
        shutil.copy2(BOOT / name, boot / name)
    debug = root / "projects" / "harland" / "build" / "debug"
    debug.mkdir(parents=True)
    (debug / "harland.elf").write_bytes(b"\x7fELF kernel")
    (debug / "BOOTX64.EFI").write_bytes(b"MZ bootloader")

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name, body in (("qemu-system-x86_64", STUB_QEMU), ("qemu-img", STUB_QEMU_IMG)):
        (stubs / name).write_text(body)
        (stubs / name).chmod(0o755)
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"\0")

    def run(log, extra_env=None):
        (tmp_path / "serial.canned").write_text(log)
        env = {
            "HOME": os.environ.get("HOME", str(tmp_path)),
            # A room unit's PATH: no /usr/sbin or /sbin, so no mkfs.vfat.
            "PATH": f"{stubs}:/usr/bin:/bin",
            "SKIP_BUILD": "1",
            "OVMF_CODE": str(ovmf),
            "BOOT_TIMEOUT": "20",
            "STUB_SERIAL": str(tmp_path / "serial.canned"),
            "STUB_RECORD": str(tmp_path / "esp.record"),
            **(extra_env or {}),
        }
        proc = subprocess.run(["bash", str(boot / "test.sh")], capture_output=True,
                              text=True, env=env, timeout=120)
        record = tmp_path / "esp.record"
        return proc, record.read_text() if record.exists() else ""

    return run


def test_boot_script_passes_without_sbin_on_path(harness):
    proc, record = harness(_log_up_to(12))
    out = proc.stdout + proc.stderr
    assert "command not found" not in out, out
    assert proc.returncode == 0, out
    # The ESP handed to QEMU holds the bootloader, kernel and startup.nsh.
    for f in ("./EFI/BOOT/BOOTX64.EFI", "./harland/kernel.elf", "./startup.nsh"):
        assert f in record.splitlines(), record


def test_boot_script_fails_on_a_planted_early_stop(harness):
    proc, _ = harness(_log_up_to(9))
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "below the required milestone 12" in proc.stdout


def test_boot_script_required_milestone_knob(harness):
    proc, _ = harness(_log_up_to(9), {"UEFI_MIN_MILESTONE": "9"})
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_boot_script_missing_ovmf_is_a_setup_error(harness, tmp_path):
    proc, _ = harness(_log_up_to(12), {"OVMF_CODE": str(tmp_path / "missing.fd")})
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "SETUP ERROR" in proc.stdout + proc.stderr


def test_boot_script_needs_no_fat_formatting_tools():
    src = (BOOT / "test.sh").read_text()
    code = "\n".join(line.split("#", 1)[0] for line in src.splitlines())
    for tool in ("mkfs.vfat", "mkfs.fat", "mformat", "mcopy", "mmd"):
        assert tool not in code, f"boot/test.sh still runs {tool}"


def test_boot_script_missing_qemu_img_is_a_setup_error(harness, tmp_path):
    # A PATH holding only a qemu-system-x86_64 stub (and coreutils via a
    # private dir): qemu-img is missing.
    only = tmp_path / "only-qemu"
    only.mkdir()
    for tool in ("bash", "dirname", "env"):
        (only / tool).symlink_to(shutil.which(tool))
    (only / "qemu-system-x86_64").write_text("#!/bin/sh\nexit 0\n")
    (only / "qemu-system-x86_64").chmod(0o755)
    proc, _ = harness(_log_up_to(12), {"PATH": str(only)})
    assert proc.returncode == 3, proc.stdout + proc.stderr
    assert "qemu-img" in proc.stderr


# --- CI wiring: main.yml's build-all runs it (AGAST #2200) -----------------------

def _build_all_steps():
    import yaml
    spec = yaml.safe_load((HARLAND.parents[1] / ".github" / "workflows" / "main.yml").read_text())
    return spec["jobs"]["build-all"]["steps"]


def test_ci_runs_test_uefi_boot_after_the_boot_tools_install():
    steps = _build_all_steps()
    runs = [str(s.get("run", "")) for s in steps]
    boot = [i for i, r in enumerate(runs) if "projects/harland/boot/test.sh" in r]
    assert len(boot) == 1, "want exactly one build-all step running boot/test.sh"
    step = steps[boot[0]]
    install = [i for i, r in enumerate(runs) if "install_boot_tools.sh" in r]
    tier1 = [i for i, r in enumerate(runs) if "test_tier1_boot.sh" in r]
    assert install and install[0] < boot[0]
    assert tier1 and tier1[0] < boot[0], "SKIP_BUILD needs the earlier builds"
    # A real gate: no lowered milestone, no swallowed failure, bounded.
    assert not step.get("continue-on-error", False)
    assert "|| true" not in step["run"]
    env = step.get("env", {})
    assert "UEFI_MIN_MILESTONE" not in env and "UEFI_MIN_MILESTONE" not in step["run"]
    assert env.get("SKIP_BUILD") == "1"
    assert 0 < int(step.get("timeout-minutes", 0)) <= 10
    # ci_local skips setup steps; the boot must not read as one.
    assert "install" not in step["name"].lower()
