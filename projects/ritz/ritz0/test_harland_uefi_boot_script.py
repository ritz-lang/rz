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
        # Keep the raw initramfs (a ustar archive, zero-padded) for the
        # staging tests to list.
        convert) : > "${@: -1}"
                 [ -n "$STUB_RAW" ] && cp "${@: -2:1}" "$STUB_RAW" ;;
    esac
    """)

# Stub ./rz: log each `rz build PKG`, fail the one named by STUB_RZ_FAIL.
STUB_RZ = textwrap.dedent("""\
    #!/bin/bash
    echo "$*" >> "$STUB_RZ_LOG"
    # A failure whose output test.sh filters out entirely.
    [ "$2" = "${STUB_RZ_FAIL:-}" ] && { echo "  Compiling $2"; exit 1; }
    exit 0
    """)

# The packages initramfs.pkgs lists, as the real tree has them.
REPO = HARLAND.parents[1]
PKGS_FILE = REPO / "projects" / "indium" / "initramfs.pkgs"


def _listed_pkgs():
    pkgs = []
    for line in PKGS_FILE.read_text().splitlines():
        pkgs.extend(line.split("#", 1)[0].split())
    return pkgs


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
    # The initramfs package list, a dummy ELF per listed package (indium
    # also builds init_interactive), and one in a package it does not list.
    projects = root / "projects"
    (projects / "indium").mkdir()
    shutil.copy2(PKGS_FILE, projects / "indium" / "initramfs.pkgs")
    elves = {pkg: [f"{pkg}_bin"] for pkg in _listed_pkgs()}
    elves["indium"] = ["init", "init_interactive"]
    elves["unlisted"] = ["stray"]
    for pkg, names in elves.items():
        out = projects / pkg / "build" / "debug"
        out.mkdir(parents=True, exist_ok=True)
        for name in names:
            (out / f"{name}.elf").write_bytes(f"\x7fELF {pkg}/{name}".encode())
    runtime = projects / "ritz" / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "Makefile").write_text("all:\n\t@:\n")
    (root / "rz").write_text(STUB_RZ)
    (root / "rz").chmod(0o755)

    stubs = tmp_path / "stubs"
    stubs.mkdir()
    for name, body in (("qemu-system-x86_64", STUB_QEMU), ("qemu-img", STUB_QEMU_IMG)):
        (stubs / name).write_text(body)
        (stubs / name).chmod(0o755)
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"\0")

    def run(log, extra_env=None, args=()):
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
            "STUB_RAW": str(tmp_path / "initramfs.raw"),
            "STUB_RZ_LOG": str(tmp_path / "rz.log"),
            **(extra_env or {}),
        }
        proc = subprocess.run(["bash", str(boot / "test.sh"), *args], capture_output=True,
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


# --- the initramfs: indium/initramfs.pkgs, built or a setup error (AGAST #3615) --
#
# test.sh hand-built indium, prism and rzsh with `rz build X | grep ... || true`
# (a failed build went on to boot stale binaries) and copied named binaries
# into the initramfs, a package set that could drift from initramfs.pkgs.


def _staged(tmp_path):
    """{path: contents} of the regular files in the initramfs tar QEMU got."""
    import tarfile
    with tarfile.open(tmp_path / "initramfs.raw") as tar:
        return {m.name.removeprefix("./"): tar.extractfile(m).read()
                for m in tar.getmembers() if m.isfile()}


def test_boot_script_builds_the_listed_packages(harness, tmp_path):
    proc, _ = harness(_log_up_to(12), {"SKIP_BUILD": "0"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    built = (tmp_path / "rz.log").read_text().split("\n")
    assert built[:-1] == [f"build {p}" for p in _listed_pkgs()], built


@pytest.mark.parametrize("pkg", _listed_pkgs())
def test_boot_script_build_failure_is_a_setup_error(harness, tmp_path, pkg):
    proc, _ = harness(_log_up_to(12), {"SKIP_BUILD": "0", "STUB_RZ_FAIL": pkg})
    out = proc.stdout + proc.stderr
    assert proc.returncode == 3, out
    assert f"SETUP ERROR: build of {pkg} failed" in proc.stderr, out
    assert not (tmp_path / "initramfs.raw").exists(), "booted after a failed build"


def test_boot_script_stages_exactly_the_listed_packages(harness, tmp_path):
    proc, _ = harness(_log_up_to(12))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    bins = {k for k in _staged(tmp_path) if k.startswith("bin/")}
    want = {f"bin/{p}_bin" for p in _listed_pkgs() if p != "indium"}
    want |= {"bin/init", "bin/init_interactive"}
    assert bins == want


def test_boot_script_interactive_mode_boots_init_interactive(harness, tmp_path):
    proc, _ = harness(_log_up_to(12), args=("--interactive",))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    staged = _staged(tmp_path)
    assert staged["bin/init"] == b"\x7fELF indium/init_interactive"
    assert staged["bin/init_interactive"] == b"\x7fELF indium/init_interactive"


def test_boot_script_default_mode_boots_init(harness, tmp_path):
    proc, _ = harness(_log_up_to(12))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _staged(tmp_path)["bin/init"] == b"\x7fELF indium/init"


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
