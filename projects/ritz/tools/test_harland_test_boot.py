#!/usr/bin/env python3
"""`make -C projects/harland test-boot` must fail when the kernel panics (AGAST #3437).

tools/test_boot.sh boots harland's GRUB ISO under legacy BIOS (SeaBIOS ->
GRUB multiboot2), the one boot path test_tier1_boot.sh (OVMF only) does not
cover. Until #3437 it attached a blank `qemu-img create` disk as the
initramfs, so the kernel printed its banner, then

    [initramfs] Loaded 0 files from disk
    *** KERNEL PANIC: Failed to load initramfs ***

and the script still exited 0, because its last check was
`grep "Hello from Harland"`. Any boot that printed the banner passed.

These tests run the script against a stub QEMU that writes a canned serial
log, so they need no QEMU, kernel or ISO build. The verdicts they pin:

  * a panic or an exception after the banner is a FAIL (exit 1), even when
    the Tier-1 suite reported ALL TESTS PASSED;
  * the banner alone is not a pass: the boot must reach init's Tier-1 suite
    and see ALL TESTS PASSED;
  * the initramfs QEMU boots is the one mkinitramfs.py built from the
    userspace packages, never a blank disk, and nothing is left under build/
    for a later run to boot instead;
  * the TSC is calibrated: the log names a measured frequency, not the
    uncalibrated fallback guess (#4181);
  * a missing tool is a SETUP ERROR (exit 3, ci_local's EXIT_SETUP), not a
    regression.

Run with:
    python3 -m pytest projects/ritz/tools/test_harland_test_boot.py -q
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
SCRIPT = REPO / "projects" / "harland" / "tools" / "test_boot.sh"
EXIT_SETUP = 3  # ci_local.EXIT_SETUP; test_ci_harland_boot.py pins the value

pytestmark = pytest.mark.unit

# Logs its argv to $STUB_LOG, writes $FAKE_SERIAL to the `-serial file:PATH`
# it was given and exits: the boot is over as soon as the log is written.
# With $FAKE_HANG set it then idles until killed, as a hung guest does.
QEMU_STUB = r"""#!/usr/bin/env bash
echo "qemu $*" >> "$STUB_LOG"
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$FAKE_SERIAL" > "${a#file:}"; fi
    prev="$a"
done
[ -n "${FAKE_HANG:-}" ] && sleep 60
exit 0
"""
QEMU_IMG_STUB = r"""#!/usr/bin/env bash
echo "qemu-img $*" >> "$STUB_LOG"
# `create [-q] [-f F] [-F F] [-b B] FILE [SIZE]`: touch FILE.
pos=(); skip=0
for a in "${@:2}"; do
    if [ "$skip" = 1 ]; then skip=0; continue; fi
    case "$a" in -f|-F|-b|-o) skip=1 ;; -*) ;; *) pos+=("$a") ;; esac
done
: > "${pos[0]}"
"""
# Records the ELFs it was handed, so a test can check the initramfs holds the
# userspace and not nothing.
MKINITRAMFS_STUB = """import os, sys
a = sys.argv
bins = sorted(os.listdir(a[a.index("--bin-dir") + 1]))
out = a[a.index("--output") + 1]
open(out, "wb").write(b"INITRAMFS")
with open(os.environ["STUB_LOG"], "a") as f:
    f.write("mkinitramfs " + out + " " + " ".join(bins) + "\\n")
"""

BANNER = r"    Hello from Harland!\n  [..] Initial filesystem"
# The calibrated TSC frequency kernel_main logs before APs start (#4181).
TSC = r"[tsc] 2304.186 MHz (PIT), not invariant\n"
LOADED = TSC + r"[initramfs] Loaded 27 files from disk\n"
# The default -smp 4 starts 3 APs, and every one must come up (#4184).
APS = r"  [OK] Boot APs (3 APs started)\n"
# The kernel's per-CPU syscall stack self-test (#4192): all four CPUs were in
# a ring-3 SYSCALL at once on their own stacks.
SMP = r"[smp] syscall stacks OK: 4 CPUs in ring-3 SYSCALL at once, distinct per-CPU stacks and frames\n"
PASSED = APS + SMP + r"  Results: 15 passed, 0 failed\n  ALL TESTS PASSED\n"
SUITE_ONLY = r"  Results: 15 passed, 0 failed\n  ALL TESTS PASSED\n"
# What the blank disk produced (#3437): the banner, then a panic.
PANIC_AFTER_BANNER = (
    BANNER
    + r"[initramfs] Loading from VirtIO disk...\n"
    + r"[initramfs] Loaded 0 files from disk\n"
    + r"*** KERNEL PANIC: Failed to load initramfs ***\n"
)
USER_ELFS = {
    "indium": "init.elf",
    "rzsh": "rzsh.elf",
    "prism": "hello_gfx.elf",
}


@pytest.fixture
def tree(tmp_path):
    """A copy of the script in a fake repo with a fake ISO and userspace."""
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(SCRIPT, tools / "test_boot.sh")
    (tools / "mkinitramfs.py").write_text(MKINITRAMFS_STUB)
    iso = root / "projects" / "harland" / "build" / "harland.iso"
    iso.parent.mkdir(parents=True)
    iso.write_bytes(b"ISO")
    for pkg, elf in USER_ELFS.items():
        p = root / "projects" / pkg / "build" / "debug" / elf
        p.parent.mkdir(parents=True)
        p.write_bytes(b"\x7fELF")
    # The script reads its package list from here (AGAST #2759).
    shutil.copy(
        REPO / "projects/indium/initramfs.pkgs", root / "projects/indium/initramfs.pkgs"
    )
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    return {
        "root": root,
        "script": tools / "test_boot.sh",
        "stubs": stubs,
        "tmp": tmp_path,
    }


def _stub(stubs: Path, name: str, body: str) -> None:
    p = stubs / name
    p.write_text(body)
    p.chmod(0o755)


def _run(
    tree, serial: str = "", *, qemu=True, full_path=True, env_extra=None
) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    if qemu:
        _stub(stubs, "qemu-system-x86_64", QEMU_STUB)
    _stub(stubs, "qemu-img", QEMU_IMG_STUB)
    if full_path:
        path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    else:
        # Only the stubs and what the script needs before its tool checks,
        # so a real QEMU on this host can't satisfy it.
        for tool in ("dirname", "mktemp", "rm"):
            os.symlink(shutil.which(tool), stubs / tool)
        path = str(stubs)
    env = {
        "PATH": path,
        "HOME": str(tree["tmp"]),
        "SKIP_BUILD": "1",
        "BOOT_TIMEOUT": "5",
        "STUB_LOG": str(tree["tmp"] / "stub.log"),
        "FAKE_SERIAL": serial,
        **(env_extra or {}),
    }
    return subprocess.run(
        ["/bin/bash", str(tree["script"])],
        check=False,
        env=env,
        cwd=tree["tmp"],
        capture_output=True,
        text=True,
        timeout=120,
    )


def _stub_log(tree) -> str:
    p = tree["tmp"] / "stub.log"
    return p.read_text() if p.exists() else ""


# --- the #3437 bug: a panic after the banner ----------------------------------


@pytest.mark.integration
def test_panic_after_the_banner_fails(tree):
    r = _run(tree, PANIC_AFTER_BANNER)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "KERNEL PANIC" in r.stdout and "FAIL" in r.stdout


@pytest.mark.integration
def test_panic_fails_even_if_the_suite_passed(tree):
    r = _run(tree, BANNER + LOADED + PASSED + r"*** KERNEL PANIC: late ***\n")
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_exception_fails_even_if_the_suite_passed(tree):
    r = _run(tree, BANNER + LOADED + r"EXCEPTION: #GP\nRIP=0x1\nCR2=0\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "EXCEPTION" in r.stdout


@pytest.mark.integration
def test_the_banner_alone_is_not_a_pass(tree):
    """The old ladder's last rung: 'Boot successful (single core)'."""
    r = _run(tree, BANNER + LOADED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "ALL TESTS PASSED" in r.stdout  # the FAIL line names what was missing


@pytest.mark.integration
def test_a_hung_boot_fails_and_says_it_timed_out(tree):
    """A boot that never reaches a verdict is a FAIL that names the timeout,
    so a slow host reads differently from a suite that never ran."""
    r = _run(tree, BANNER + LOADED, env_extra={"FAKE_HANG": "1", "BOOT_TIMEOUT": "3"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "no verdict within 3s" in r.stdout


def test_the_default_timeout_allows_a_loaded_host():
    """TCG boots took 16-39s at load average 26 on huburght; 60s failed one."""
    src = SCRIPT.read_text()
    assert 'TIMEOUT="${BOOT_TIMEOUT:-120}"' in src


@pytest.mark.integration
def test_failed_suite_fails(tree):
    r = _run(
        tree, BANNER + LOADED + r"  Results: 14 passed, 1 failed\n  TESTS FAILED\n"
    )
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_good_boot_passes(tree):
    r = _run(tree, BANNER + LOADED + PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout


# --- every CPU -smp starts comes up (#4184) -----------------------------------


@pytest.mark.integration
def test_a_missing_ap_fails_even_if_the_suite_passed(tree):
    r = _run(tree, BANNER + LOADED + r"  [OK] Boot APs (2 APs started)\n" + SUITE_ONLY)
    assert r.returncode == 1, r.stdout + r.stderr
    assert '"(3 APs started)"' in r.stdout


@pytest.mark.integration
def test_no_ap_line_fails(tree):
    r = _run(tree, BANNER + LOADED + SUITE_ONLY)
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_the_ap_count_follows_smp_and_plug_cpu(tree):
    """SMP=20,... expects 19 APs; PLUG_CPU cold-plugs one more (APIC ID 256)."""
    smp20 = r"[smp] syscall stacks OK: 20 CPUs in ring-3 SYSCALL at once, distinct per-CPU stacks and frames\n"
    r = _run(tree, BANNER + LOADED + r"  [OK] Boot APs (19 APs started)\n" + smp20 + SUITE_ONLY,
             env_extra={"SMP": "20,sockets=2,cores=10", "CPU": "Haswell-v1,+x2apic"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "-smp 20,sockets=2,cores=10" in _stub_log(tree) and "-cpu Haswell-v1,+x2apic" in _stub_log(tree)
    r = _run(tree, BANNER + LOADED + r"  [OK] Boot APs (1 APs started)\n" + SUITE_ONLY,
             env_extra={"SMP": "1,sockets=2,cores=200,maxcpus=400", "MACHINE": "q35",
                        "PLUG_CPU": "socket-id=1,core-id=0,thread-id=0"})
    assert r.returncode == 0, r.stdout + r.stderr
    qemu = [line for line in _stub_log(tree).splitlines() if line.startswith("qemu ")][-1]
    assert "-machine q35" in qemu and "-device Haswell-v1-x86_64-cpu,socket-id=1,core-id=0,thread-id=0" in qemu, qemu


@pytest.mark.integration
def test_a_missing_per_cpu_syscall_verdict_fails(tree):
    """AGAST #4192: the boot must prove every CPU took SYSCALL on its own
    stack. A green suite and all APs up are not enough."""
    r = _run(tree, BANNER + LOADED + APS + SUITE_ONLY)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "CPUs in SYSCALL at once" in r.stdout


# --- the TSC is calibrated (#4181) ---------------------------------------------


@pytest.mark.integration
def test_good_boot_names_the_tsc_frequency(tree):
    r = _run(tree, BANNER + LOADED + PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "[tsc] 2304.186 MHz (PIT)" in r.stdout


@pytest.mark.integration
def test_no_tsc_line_fails(tree):
    r = _run(tree, BANNER + LOADED.replace(TSC, "") + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "no calibrated TSC frequency" in r.stdout


@pytest.mark.integration
def test_uncalibrated_tsc_fails(tree):
    guess = r"[tsc] 6000.000 MHz (uncalibrated guess), not invariant\n"
    r = _run(tree, BANNER + LOADED.replace(TSC, guess) + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


# --- the initramfs is the real one --------------------------------------------


@pytest.mark.integration
def test_boots_the_mkinitramfs_image_of_the_userspace(tree):
    r = _run(tree, BANNER + LOADED + PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    log = _stub_log(tree)
    mk = [line.split() for line in log.splitlines() if line.startswith("mkinitramfs ")]
    assert len(mk) == 1, log
    image, elfs = mk[0][1], mk[0][2:]
    assert sorted(elfs) == sorted(USER_ELFS.values())
    qemu = [line for line in log.splitlines() if line.startswith("qemu ")]
    assert len(qemu) == 1 and "-cdrom" in qemu[0], log
    # The disk QEMU attaches as `id=initramfs` is the mkinitramfs image, or a
    # qemu-img overlay backed by it -- never a blank `qemu-img create`.
    drive = next(a for a in qemu[0].split() if a.endswith(",id=initramfs"))
    disk = drive.split("file=", 1)[1].split(",", 1)[0]
    if disk != image:
        creates = [
            line
            for line in log.splitlines()
            if line.startswith("qemu-img create ") and line.split()[-1] == disk
        ]
        assert len(creates) == 1 and f"-b {image}" in creates[0], log


@pytest.mark.integration
def test_leaves_no_disk_under_build_for_a_later_run(tree):
    """The blank disk lived at build/initramfs.qcow2 and was reused forever."""
    build = tree["root"] / "projects" / "harland" / "build"
    _run(tree, BANNER + LOADED + PASSED)
    assert sorted(p.name for p in build.iterdir()) == ["harland.iso"]


@pytest.mark.integration
def test_missing_user_build_output_fails(tree):
    (tree["root"] / "projects/indium/build/debug/init.elf").unlink()
    r = _run(tree, BANNER + LOADED + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "init.elf" in r.stdout


# --- setup errors -------------------------------------------------------------


@pytest.mark.integration
def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False, full_path=False)
    assert r.returncode == EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


# --- docs and the Makefile name the real check --------------------------------


def test_make_test_runs_the_boot_check():
    mk = (REPO / "projects" / "harland" / "Makefile").read_text()
    assert "\ntest: test-boot" in mk


def test_readme_lists_what_make_help_lists():
    """README's target list is `make help`'s; test-tier1 was missing from it."""
    readme = (REPO / "projects" / "harland" / "README.md").read_text()
    mk = (REPO / "projects" / "harland" / "Makefile").read_text()
    help_targets = [
        line.split('"')[1].split()[0]
        for line in mk.splitlines()
        if line.strip().startswith('@echo "  ') and " - " in line
    ]
    assert "test-tier1" in help_targets
    for t in help_targets:
        assert f"\n{t} " in readme, f"README target list is missing {t}"
