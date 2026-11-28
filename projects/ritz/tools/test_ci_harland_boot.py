#!/usr/bin/env python3
"""CI must boot harland (AGAST #1845).

projects/harland/tools/test_tier1_boot.sh (#2132) boots the kernel under OVMF
twice -- harland's own BOOTX64.EFI, and GRUB-EFI via multiboot2 -- and needs
init's Tier-1 suite to report ALL TESTS PASSED with no KERNEL PANIC or
EXCEPTION. Until #1845 nothing ran it but a person, so nothing went red when
harland stopped booting.

It is a step in main.yml's build-all job, after `./rz build --all`. ci_local.py
parses main.yml, so every room's gate (`--job build-all --job bootstrap`) boots
harland too. These tests pin two things:

  * the wiring: the step exists, gates for real, has a timeout, and its serial
    logs are uploaded whether it passes or fails;
  * the verdicts: a missing tool is a SETUP ERROR (ci_local's exit 3 -- no
    verdict, so neither a pass nor a regression), and a panic, an exception
    or a boot that never reports a verdict is a FAIL (exit 1). The script
    runs here against a stub QEMU that writes a canned serial log, so these
    checks need no QEMU, OVMF or kernel build.

Run with:
    python3 -m pytest projects/ritz/tools/test_ci_harland_boot.py -q
"""

from __future__ import annotations

import json
import os
import re
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
BOOT_SCRIPT = "projects/harland/tools/test_tier1_boot.sh"
INSTALL_SCRIPT = ".github/scripts/install_boot_tools.sh"
# What test_tier1_boot.sh's setup checks need on ubuntu-latest:
# qemu-system-x86_64, qemu-img (qemu-utils), OVMF_CODE*.fd (ovmf),
# grub-mkstandalone + /usr/lib/grub/x86_64-efi (grub-efi-amd64-bin).
BOOT_PACKAGES = ("qemu-system-x86", "qemu-utils", "ovmf", "grub-efi-amd64-bin")


# --------------------------------------------------------------------------
# Wiring: main.yml
# --------------------------------------------------------------------------


def _raw_build_all() -> list[dict]:
    spec = yaml.safe_load(ci_local.WORKFLOW.read_text())
    return spec["jobs"]["build-all"]["steps"]


def _index(steps: list[dict], pred) -> list[int]:
    return [i for i, s in enumerate(steps) if pred(s)]


def _boot_index(steps: list[dict]) -> int:
    hits = _index(steps, lambda s: BOOT_SCRIPT in str(s.get("run", "")))
    assert len(hits) == 1, (
        f"want exactly one build-all step running {BOOT_SCRIPT}, got {len(hits)}"
    )
    return hits[0]


def test_boot_script_exists():
    assert (REPO / BOOT_SCRIPT).is_file()
    assert (REPO / INSTALL_SCRIPT).is_file()


def test_build_all_boots_harland_after_building_the_workspace():
    steps = _raw_build_all()
    boot = _boot_index(steps)
    builds = _index(steps, lambda s: "./rz build --all" in str(s.get("run", "")))
    assert builds and builds[0] < boot


def test_boot_step_is_a_real_gate():
    """No continue-on-error, no `|| true`, from the repo root, and the
    10-minute bound the ticket asks for (two boots take ~1 min locally)."""
    step = _raw_build_all()[_boot_index(_raw_build_all())]
    assert not step.get("continue-on-error", False)
    assert "|| true" not in step["run"]
    assert step.get("working-directory", ".") == "."
    assert 0 < int(step.get("timeout-minutes", 0)) <= 10
    # Both boots: native alone would let GRUB-EFI rot unseen.
    assert not re.search(r"test_tier1_boot\.sh\s+(native|grub)\b", step["run"])


def test_boot_step_is_not_a_setup_step():
    """ci_local skips setup steps by default; the boot must never be one."""
    boot = [
        s
        for s in ci_local.load_steps()
        if s.job == "build-all" and BOOT_SCRIPT in s.run
    ]
    assert len(boot) == 1 and not boot[0].is_setup


def test_boot_tools_are_installed_before_the_boot_as_a_setup_step():
    steps = _raw_build_all()
    boot = _boot_index(steps)
    installs = _index(steps, lambda s: INSTALL_SCRIPT in str(s.get("run", "")))
    assert len(installs) == 1 and installs[0] < boot
    # ci_local must classify it as setup: running it locally would apt-get
    # on the developer's machine.
    parsed = [
        s
        for s in ci_local.load_steps()
        if s.job == "build-all" and INSTALL_SCRIPT in s.run
    ]
    assert len(parsed) == 1 and parsed[0].is_setup
    src = (REPO / INSTALL_SCRIPT).read_text()
    for pkg in BOOT_PACKAGES:
        assert pkg in src, f"{INSTALL_SCRIPT} does not install {pkg}"


def test_serial_logs_are_uploaded_on_pass_and_fail():
    steps = _raw_build_all()
    boot = _boot_index(steps)
    run = steps[boot]["run"]
    assert "KEEP_WORK=" in run
    uploads = _index(
        steps, lambda s: "actions/upload-artifact" in str(s.get("uses", ""))
    )
    after = [i for i in uploads if i > boot]
    assert len(after) == 1, "want one upload-artifact step after the boot"
    up = steps[after[0]]
    assert up.get("if") == "always()", "logs matter most when the boot fails"
    assert "harland" in up["with"]["path"] and up["with"]["path"].rstrip("/").endswith(
        "boot-logs"
    )
    assert "boot-logs" in run


# --------------------------------------------------------------------------
# Verdicts: the script against a stub QEMU
# --------------------------------------------------------------------------

# Writes $FAKE_SERIAL to the `-serial file:PATH` it was given. With
# $FAKE_POWEROFF=1 it then exits 0, as QEMU does when the guest powers off
# through ACPI (init's exit, AGAST #2755); otherwise it idles until killed
# (the script stops QEMU once it has had POWEROFF_WAIT seconds after the
# verdict, and `timeout` kills it otherwise). Every argv goes to $STUB_LOG.
QEMU_STUB = r"""#!/usr/bin/env bash
echo "$@" >> "$STUB_LOG"
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$FAKE_SERIAL" > "${a#file:}"; fi
    # The ESP's files, relative to it (boot options are marker files there).
    case "$a" in *fat:rw:*) d="${a#*fat:rw:}"; (cd "$d" && find . -type f | sed 's|^|ESP |') >> "$STUB_LOG" ;; esac
    prev="$a"
done
if [ "${FAKE_POWEROFF:-0}" = 1 ]; then sleep 1; exit 0; fi
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

# A boot whose virtio-keyboard-pci came up and whose injected `sendkey a`
# reached the kernel input queue and init (AGAST #3438).
KEY_OK = (
    r"  [OK] VirtIO input device\n"
    r"[test] input ... [virtio-input] event type=1 code=30 value=1\n"
    r"key event code=30 value=1\n"
)
SUITE_PASSED = r"[test] hello ... PASS (exit=0)\n  Results: 10 passed, 0 failed\n  ALL TESTS PASSED\n"
# init runs indium's ping, udp-send and udp-recv with no ring-2 net service:
# each prints its NetAttach NoDev line between init's "[test] ..." and its
# verdict, and exits 19 (AGAST #4751).
NET_TOOLS = ("ping", "udp-send", "udp-recv")
NET_NODEV = "".join(
    rf"[test] {t} nodev ... {t}: NetAttach: Errno.NoDev (no network service) (-19)\nPASS (exit=19)\n"
    for t in NET_TOOLS
)
# indium's write_empty_test checked /var as well as /tmp (AGAST #4830).
WRITE_EMPTY_OK = r"[test] write_empty_test ... [write_empty_test] PASS: /tmp and /var\nPASS (exit=0)\n"
# indium's stat_test checked /var as well as /tmp (AGAST #4832).
STAT_OK = r"[test] stat_test ... [stat_test] PASS: /tmp and /var\nPASS (exit=0)\n"
# The native boot's virtio-blk is modern-only and offers 1024-entry queues;
# the driver must take the MMIO transport and cap the queue (AGAST #3576).
BLK_MODERN = r"[virtio-blk] Device 0 initialized (64 MB, modern, queue 256)\n"
# The native boot's persistent store sits on a disk that answers every
# request 100 ms late; it must still come up (AGAST #4078).
PERSIST_OK = r"\r  [OK] Persistent storage (0 blobs)\n"
# init exits after the suite, and the kernel powers off (AGAST #2755).
INIT_EXIT = r"[exit] init exited with code 0, powering off\n"
# The kernel calibrated its LAPIC tick, and init's two /bin/busy children
# (Tier-1 `preempt`) ran side by side: their lines interleave (AGAST #3629).
TIMER_OK = r"[timer] LAPIC timer 62500000 Hz (bus/16, TSC-calibrated), periodic 100 Hz tick, initial count 625000\n"
# A healthy pair alternates almost every step: eight steps each, 16 runs, and
# the scheduler preempts on most ticks (AGAST #4332 added the counter check).
# The run floor is 6, not 10 (AGAST #4438): a loaded host can pair the lines
# to 9 runs while preemption stays healthy, so the counter ratio is the real
# invariant and 6 only has to separate that from the 2..4-run failure shapes.
BUSY_OK = "".join(f"[busy A] {step}/8\n[busy B] {step}/8\n" for step in range(1, 9))
# The ratio is contended ticks (two or more runnable) to preemptions (#4832).
SCHED_OK = "[sched] 356 ticks, 285 switches, 233 preemptions, 250 contended ticks\n"
# The kernel's SMP syscall-stack self-test (AGAST #4192): all four CPUs were
# in a ring-3 SYSCALL at once, each on its own per-CPU stack.
SMP_OK = "[smp] syscall stacks OK: 4 CPUs in ring-3 SYSCALL at once, distinct per-CPU stacks and frames\n"
# The BSP pinged each of the three APs over its mailbox and every pong came
# back in order (AGAST #4879, SMP_USER.md §6).
MBOX_OK = "".join(f"[mbox] round trip OK: cpu {k} answered 64 pings\n" for k in (1, 2, 3))
# Each AP served the BSP's owner-side UNMAP and a KERNEL_INVLPG (AGAST #4880,
# SMP_USER.md §3, §6).
TLB_OK = "".join(f"[tlb] owner unmap OK: cpu {k} saw the unmap\n[tlb] kernel invlpg OK: cpu {k} saw the unmap\n"
                 for k in (1, 2, 3))
TLB_NONE = "[tlb] no APs for the owner unmap\n"
# A process on the BSP and one pinned to the last AP (cpu 3) made forwarded
# and local syscalls at once, every count exact (AGAST #4881, SMP_USER.md
# §6); at one CPU the pinned spawn fell back to the BSP.
SMP_USER_OK = "[smp-user] concurrent syscalls OK: cpu0 100000 cpu3 100000, forwarded 100002\n"
SMP_USER_NONE = "[smp-user] single CPU: pinned spawn ran on the BSP\n"
SMP_OK = SMP_OK + MBOX_OK + TLB_OK + SMP_USER_OK
PREEMPT_OK = TIMER_OK + BUSY_OK + SCHED_OK
# The native ESP carries \\harland\\klog-dump, so the kernel dumps its crash
# ring before init: the dump must be exactly the kernel's serial output up to
# it, from the banner on (AGAST #1885).
# The boot-test mode (AGAST #1887): the ESP's \\harland\\boot-test marker (GRUB:
# the `boot-test` cmdline word) makes the kernel run its self-tests, one
# "[boot-test] PASS|FAIL <name>" line each and a summary. The gate requires
# every name in BOOT_TESTS to pass, among them channel-close and
# channel-debug-print, which the kernel used to skip as page faults.
BOOT_TESTS = (
    "vmm", "higher-half", "heap", "ipc", "channel-close", "channel-debug-print",
    "munmap", "mmap-failure", "pmm-above-4g", "mmap-overlap", "mmap-cursor",
    "mmap-driver-window",
    "elf-loader", "sysret", "nmi-gs", "ist-nest", "nmi-nest", "cap-device", "shm-map", "virtio-blk-read",
    "proc-create-init", "driver-enter", "driver-fault", "driver-preempt", "driver-reap", "drv-irq-wait", "drv-mmio-map", "drv-dma-alloc", "drv-dma-free", "console-poll", "shm-wait", "net-attach", "net-info", "shm-retire", "net-addr", "frame-ring", "spawn-pages", "drv-quiesce", "smp-user",
)
BOOT_TEST_OK = "".join(f"[boot-test] PASS {t}\n" for t in BOOT_TESTS) + (
    f"[boot-test] {len(BOOT_TESTS)} passed, 0 failed\n"
)
KERNEL_BANNER = r"\n========================================\n    Hello from Harland!\n========================================\n"
RING_DUMP_START = r"\n=== RING BUFFER DUMP (kernel log) ===\n"
RING_DUMP_END = r"\n=== END RING BUFFER ===\n"
# The kernel's log up to the dump (its boot-test lines included), then the
# dump repeating it.
RING_OK = (KERNEL_BANNER + BOOT_TEST_OK + RING_DUMP_START
           + KERNEL_BANNER + BOOT_TEST_OK + RING_DUMP_END)
PASSED = RING_OK + BLK_MODERN + PERSIST_OK + KEY_OK + PREEMPT_OK + SMP_OK + NET_NODEV + WRITE_EMPTY_OK + STAT_OK + SUITE_PASSED + INIT_EXIT


@pytest.fixture
def tree(tmp_path):
    """A copy of the script in a fake repo with fake build outputs."""
    root = tmp_path / "repo"
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(REPO / BOOT_SCRIPT, tools / "test_tier1_boot.sh")
    # ...which sources the shared socket-dir picker (AGAST #4282).
    (root / "projects/ritz/tools").mkdir(parents=True)
    shutil.copy(REPO / "projects/ritz/tools/sock_dir.sh", root / "projects/ritz/tools/sock_dir.sh")
    (tools / "mkinitramfs.py").write_text(MKINITRAMFS_STUB)
    # The fake harland.elf is not a real binary: the red-zone check (AGAST
    # #4308) passes unless a test says otherwise.
    (tools / "check_no_red_zone.py").write_text("import sys\nsys.exit(0)\n")
    for rel in (
        "projects/harland/build/debug/harland.elf",
        "projects/harland/build/debug/BOOTX64.EFI",
        "projects/indium/build/debug/init.elf",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x7fELF")
    # The script reads its package list from here (AGAST #2759).
    shutil.copy(
        REPO / "projects/indium/initramfs.pkgs", root / "projects/indium/initramfs.pkgs"
    )
    # ...and stages its packages through indium's stager (AGAST #4834).
    (root / "projects/indium/tools").mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO / "projects/indium/tools/stage_initramfs.sh",
                root / "projects/indium/tools/stage_initramfs.sh")
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.write_bytes(b"")
    return {
        "root": root,
        "script": tools / "test_tier1_boot.sh",
        "stubs": stubs,
        "ovmf": ovmf,
        "tmp": tmp_path,
    }


def _stub(stubs: Path, name: str, body: str) -> None:
    p = stubs / name
    p.write_text(body)
    p.chmod(0o755)


def _run(
    tree,
    serial: str = "",
    *,
    qemu=True,
    qemu_img=True,
    full_path=True,
    env_extra=None,
    mode="native",
    poweroff=True,
) -> subprocess.CompletedProcess:
    stubs = tree["stubs"]
    if qemu:
        _stub(stubs, "qemu-system-x86_64", QEMU_STUB)
    if qemu_img:
        _stub(stubs, "qemu-img", QEMU_IMG_STUB)
    if full_path:
        path = f"{stubs}{os.pathsep}{os.environ['PATH']}"
    else:
        # Only what the script needs before its first tool check, so a real
        # qemu on this host can't satisfy it.
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
        "FAKE_POWEROFF": "1" if poweroff else "0",
        "POWEROFF_WAIT": "2",
        **(env_extra or {}),
    }
    return subprocess.run(
        ["/bin/bash", str(tree["script"]), mode],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_setup_exit_code_is_ci_locals():
    """The script's 'missing tool' code must be the one ci_local reads as
    SETUP ERROR, or a runner without QEMU reads as a regression (exit 2 was
    a plain failure to ci_local)."""
    assert ci_local.EXIT_SETUP == 3


@pytest.mark.integration
def test_missing_qemu_is_a_setup_error(tree):
    r = _run(tree, qemu=False, qemu_img=False, full_path=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-system-x86_64" in r.stderr


@pytest.mark.integration
def test_missing_qemu_img_is_a_setup_error(tree):
    """The boot needs qemu-img for its per-boot overlay. Unchecked, its
    absence surfaced as a boot that never reported a verdict: a FAIL."""
    r = _run(tree, qemu_img=False, full_path=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-img" in r.stderr


@pytest.mark.integration
def test_missing_ovmf_is_a_setup_error(tree):
    r = _run(tree, PASSED, env_extra={"OVMF_CODE": str(tree["tmp"] / "nope.fd")})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "OVMF" in r.stderr


@pytest.mark.integration
def test_all_tests_passed_passes_and_keeps_the_serial_log(tree):
    keep = tree["tmp"] / "logs"
    keep.mkdir()
    r = _run(tree, PASSED, env_extra={"KEEP_WORK": str(keep)})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS (native)" in r.stdout
    assert "ALL TESTS PASSED" in (keep / "native.log").read_text()


@pytest.mark.integration
def test_boot_attaches_a_keyboard_and_a_monitor_socket(tree):
    """The sendkey check needs a modern-only virtio-keyboard-pci and a
    monitor socket to inject the key through (AGAST #3438)."""
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "virtio-keyboard-pci" in argv
    assert "-monitor unix:" in argv


@pytest.mark.integration
def test_native_boot_attaches_a_modern_only_blk_with_1024_entry_queues(tree):
    """Without disable-legacy=on QEMU's virtio-blk is transitional and the
    driver takes the legacy I/O-port path; queue-size=1024 is what makes the
    256-entry cap matter (AGAST #3576)."""
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "virtio-blk-pci,drive=initramfs,disable-legacy=on,queue-size=1024" in argv


@pytest.mark.integration
@pytest.mark.parametrize(
    "blk_line",
    [
        r"[virtio-blk] Device 0 initialized (64 MB, legacy, queue 256)\n",
        r"[virtio-blk] Device 0 initialized (64 MB, modern, queue 1024)\n",
    ],
    ids=["legacy-transport", "queue-not-capped"],
)
def test_native_blk_not_modern_with_a_256_entry_queue_fails(tree, blk_line):
    r = _run(tree, blk_line + PERSIST_OK + KEY_OK + SUITE_PASSED + INIT_EXIT)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "virtio-blk did not come up over the modern transport" in r.stdout


@pytest.mark.integration
def test_all_tests_passed_reports_the_power_off(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS (native): init exited and QEMU powered off" in r.stdout


@pytest.mark.integration
def test_qemu_that_never_powers_off_fails(tree):
    """init exited, but the machine hung instead of powering off: QEMU had to
    be stopped (AGAST #2755)."""
    r = _run(tree, PASSED, poweroff=False)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS (native): init Tier-1 suite" in r.stdout
    assert "QEMU did not power off after init exited" in r.stdout


@pytest.mark.integration
def test_init_that_never_exits_fails(tree):
    """QEMU exiting is not enough: init itself must have exited."""
    r = _run(tree, BLK_MODERN + PERSIST_OK + KEY_OK + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native): init did not exit" in r.stdout


@pytest.mark.integration
def test_native_boot_attaches_a_slow_persist_disk(tree):
    """A spin-count poll in virtio-blk timed out under host load (AGAST
    #4078); a second disk 100 ms slow per request pins that it waits on time,
    not on polls."""
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = (tree["tmp"] / "stub.log").read_text()
    assert "latency-ns=100000000" in argv and "drive=persist" in argv


@pytest.mark.integration
def test_persistent_storage_that_never_came_up_fails(tree):
    r = _run(
        tree,
        BLK_MODERN
        + r"[virtio-blk] Read timeout\n  [!!] Persistent storage (persist_init failed)\n"
        + KEY_OK
        + SUITE_PASSED
        + INIT_EXIT,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS (native): init Tier-1 suite" in r.stdout
    assert "persistent storage did not come up" in r.stdout


@pytest.mark.integration
def test_busy_children_that_ran_one_after_the_other_fail(tree):
    """ALL TESTS PASSED is not enough: init only sees both children exit 0.
    Without preemption the first runs to its end before the second starts
    (AGAST #3629)."""
    serial = (BLK_MODERN + PERSIST_OK + KEY_OK + TIMER_OK
              + r"[busy A] 1/2\n[busy A] 2/2\n[busy B] 1/2\n[busy B] 2/2\n"
              + SUITE_PASSED + INIT_EXIT)
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS (native): init Tier-1 suite" in r.stdout
    assert "busy children barely interleaved, not preempted each step (AABB, 2 runs)" in r.stdout


def _busy(seq: str) -> str:
    """Serial lines for busy children that print one step each in seq order."""
    step = {"A": 0, "B": 0}
    out = []
    for tag in seq:
        step[tag] += 1
        out.append(f"[busy {tag}] {step[tag]}/8\n")
    return "".join(out)


# The Main Branch Validation failure of AGAST #4438: the two children were
# preempted (the [sched] counters are healthy) but each timeslice covered two
# steps, so the lines paired ABBAABBA... for 9 runs instead of alternating for
# 16. The interleave count is a relative-speed measure, not a preemption one.
BUSY_PAIRED_9 = _busy("ABBAABBAABBAABBA")
assert BUSY_PAIRED_9.count("[busy A]") == 8 and BUSY_PAIRED_9.count("[busy B]") == 8


@pytest.mark.integration
def test_busy_children_coarsely_paired_by_load_pass(tree):
    """The #4438 CI failure: healthy preemption, but the host gave each child
    two steps per timeslice, so the lines paired (ABBAABBA..., 9 runs). The
    run count must tolerate that; only the [sched] ratio proves the scheduler
    kept preempting."""
    serial = (RING_OK + BLK_MODERN + PERSIST_OK + KEY_OK + TIMER_OK
              + BUSY_PAIRED_9
              + SCHED_OK
              + SMP_OK + NET_NODEV + WRITE_EMPTY_OK + STAT_OK
              + SUITE_PASSED + INIT_EXIT)
    r = _run(tree, serial)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "two busy children preempted each other: ABBAABBAABBAABBA (9 runs" in r.stdout


@pytest.mark.integration
def test_busy_children_interleaved_but_one_ran_alone_fail(tree):
    """Interleave alone is timing-sensitive (AGAST #4332): the scheduler's own
    counters must also show it kept preempting. The #4332 regression gave one
    child 735 user ticks to the other's 98 (911 ticks, 195 preemptions), so the
    lines still interleaved in spurts but one child ploughed through alone:
    the other was runnable all along, so those ticks were contended."""
    serial = (BLK_MODERN + PERSIST_OK + KEY_OK + TIMER_OK
              + BUSY_OK
              + "[sched] 911 ticks, 246 switches, 195 preemptions, 840 contended ticks\n"
              + SUITE_PASSED + INIT_EXIT)
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS (native): init Tier-1 suite" in r.stdout
    assert "one child ran alone: 840 contended ticks but only 195 preemptions" in r.stdout


@pytest.mark.integration
def test_ticks_spent_alone_do_not_count_against_preemption(tree):
    """A boot's total ticks include every tick a Tier-1 program runs alone
    (waiting on the 100 ms storage disk, say), where no preemption is
    possible. Those don't fail the #4332 check: only contended ticks, with
    two or more processes runnable, are held against the preemptions
    (AGAST #4832; #4830's /var test took the all-ticks ratio to 2.96)."""
    serial = (BLK_MODERN + PERSIST_OK + KEY_OK + TIMER_OK
              + BUSY_OK
              + "[sched] 810 ticks, 300 switches, 237 preemptions, 255 contended ticks\n"
              + SUITE_PASSED + INIT_EXIT)
    r = _run(tree, serial)
    assert "two busy children preempted each other" in r.stdout, r.stdout + r.stderr
    assert "ran alone" not in r.stdout


@pytest.mark.integration
def test_sched_counters_without_contended_ticks_fail(tree):
    """The kernel reports contended ticks; a log without them (an older
    kernel) has nothing to hold the preemptions against."""
    serial = (BLK_MODERN + PERSIST_OK + KEY_OK + TIMER_OK
              + BUSY_OK
              + "[sched] 356 ticks, 285 switches, 233 preemptions\n"
              + SUITE_PASSED + INIT_EXIT)
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "no [sched] tick/preemption counters" in r.stdout


@pytest.mark.integration
def test_busy_child_that_never_finished_fails(tree):
    serial = (BLK_MODERN + PERSIST_OK + KEY_OK + TIMER_OK
              + r"[busy A] 1/2\n[busy B] 1/2\n[busy A] 2/2\n"
              + SUITE_PASSED + INIT_EXIT)
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "busy children did not both finish" in r.stdout


@pytest.mark.integration
def test_no_calibrated_timer_fails(tree):
    serial = (BLK_MODERN + PERSIST_OK + KEY_OK
              + r"[busy A] 1/2\n[busy B] 1/2\n[busy A] 2/2\n[busy B] 2/2\n"
              + SMP_OK + SUITE_PASSED + INIT_EXIT)
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "no calibrated LAPIC timer tick" in r.stdout


@pytest.mark.integration
def test_missing_per_cpu_syscall_stack_verdict_fails(tree):
    """A boot must prove the per-CPU syscall stacks (AGAST #4192): without the
    self-test's verdict the boot fails, so an AP that never entered ring 3
    cannot pass silently."""
    serial = BLK_MODERN + PERSIST_OK + KEY_OK + PREEMPT_OK + SUITE_PASSED + INIT_EXIT
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "no per-CPU syscall stack verdict" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "mbox, verdict",
    [
        (MBOX_OK.replace("[mbox] round trip OK: cpu 3 answered 64 pings\n", ""),
         "2 of 3 APs answered the mailbox round trip"),
        (MBOX_OK.replace("[mbox] round trip OK: cpu 3 answered 64 pings\n",
                         "[mbox] round trip FAIL: cpu 3 answered 17 of 64 pings\n"),
         "an AP did not answer the BSP's pings over its mailbox"),
        (MBOX_OK.replace("cpu 3", "cpu 2"), "2 of 3 APs answered the mailbox round trip"),
    ],
    ids=["missing-ap", "ap-failed", "same-ap-twice"],
)
def test_every_ap_must_answer_the_mailbox_round_trip(tree, mbox, verdict):
    """Every AP -smp starts must answer the BSP's pings over its mailbox
    (AGAST #4879): one OK line per distinct AP, and no FAIL line."""
    r = _run(tree, PASSED.replace(MBOX_OK, mbox))
    assert r.returncode == 1, r.stdout + r.stderr
    assert verdict in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "tlb, verdict",
    [
        (TLB_OK.replace("[tlb] owner unmap OK: cpu 3 saw the unmap\n", ""),
         "2 (owner) and 3 (kernel) of 3 APs saw the unmap"),
        (TLB_OK.replace("[tlb] owner unmap OK: cpu 2 saw the unmap\n",
                        "[tlb] owner unmap FAIL: cpu 2 read the stale frame\n"),
         "an AP missed an unmap"),
        (TLB_OK + "[vmm] vmm_free_pml4: PML4 0x7FE4F000 is still loaded on cpu 1: not freed\n",
         "a PML4 was freed while a CPU still had it loaded"),
    ],
    ids=["missing-ap", "stale-read", "freed-while-loaded"],
)
def test_every_ap_must_see_the_unmap(tree, tlb, verdict):
    """Every AP -smp starts must serve the owner-side unmap and the
    kernel-half one (AGAST #4880): one OK line each per distinct AP, no FAIL,
    and vmm_free_pml4's lazy-CR3 assert never fires."""
    r = _run(tree, PASSED.replace(TLB_OK, tlb))
    assert r.returncode == 1, r.stdout + r.stderr
    assert verdict in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("line, rc", [("[mbox] no APs to ping\n" + TLB_NONE + SMP_USER_NONE, 0),
                                      ("[mbox] no APs to ping\n" + SMP_USER_NONE, 1),
                                      ("[mbox] no APs to ping\n" + TLB_NONE, 1), ("", 1)],
                         ids=["said", "tlb-silent", "smp-user-silent", "silent"])
def test_one_cpu_must_say_it_has_no_ap_to_ping(tree, line, rc):
    """At -smp 1 there is no AP: the kernel says so, and silence fails. Nor
    does it run the SMP syscall-stack self-test (init_smp needs an AP)."""
    r = _run(tree, PASSED.replace(SMP_OK, line), env_extra={"QEMU_SMP": "1"})
    assert r.returncode == rc, r.stdout + r.stderr
    assert "PASS (native): one CPU, no SMP syscall-stack self-test to run" in r.stdout
    if rc == 0:
        assert "PASS (native): one CPU, no AP to ping over the mailbox" in r.stdout
        assert "PASS (native): one CPU, no AP for the owner unmap" in r.stdout
        assert "PASS (native): one CPU, the pinned spawn ran on the BSP" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "line, verdict",
    [
        ("", "no concurrent-syscalls verdict for a process on cpu 3 (got: none)"),
        (SMP_USER_OK.replace("cpu3", "cpu2"), "no concurrent-syscalls verdict for a process on cpu 3"),
        (SMP_USER_OK.replace("cpu0 100000", "cpu0 99999"), "no concurrent-syscalls verdict for a process on cpu 3"),
        (SMP_USER_OK + "[smp-user] FAIL: forwarded bumps were lost: two CPUs ran a BSP-owned row at once\n",
         "the smp-user boot test failed"),
    ],
    ids=["silent", "not-the-last-ap", "inexact", "failed"],
)
def test_a_process_pinned_to_the_last_ap_must_make_its_syscalls(tree, line, verdict):
    """The smp-user boot test (AGAST #4881): a process pinned to the last AP
    and one on the BSP each made 100000 forwarded and 100000 local syscalls
    at once, every count exact, and no FAIL line."""
    r = _run(tree, PASSED.replace(SMP_USER_OK, line))
    assert r.returncode == 1, r.stdout + r.stderr
    assert verdict in r.stdout


@pytest.mark.integration
def test_one_cpu_with_an_smp_verdict_fails(tree):
    """At one CPU the kernel runs no SMP self-test, so a verdict is news."""
    r = _run(tree, PASSED.replace(MBOX_OK, "[mbox] no APs to ping\n"), env_extra={"QEMU_SMP": "1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "one CPU, but the SMP self-test said something" in r.stdout


@pytest.mark.integration
def test_ring_ok_passes(tree):
    r = _run(tree, PASSED)
    assert "PASS (native): the crash ring holds all" in r.stdout, r.stdout + r.stderr


@pytest.mark.integration
def test_no_ring_dump_fails(tree):
    """Without the \\harland\\klog-dump ring dump the boot fails (AGAST #1885)."""
    r = _run(tree, PASSED.replace(RING_OK, KERNEL_BANNER))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "no ring buffer dump" in r.stdout + r.stderr


@pytest.mark.integration
def test_message_missing_from_the_ring_fails(tree):
    """A kernel line that reached serial but not the ring (the old prints())
    makes the dump disagree with the log before it."""
    serial = PASSED.replace(
        RING_OK,
        KERNEL_BANNER + r"Total pages: 523926\n" + RING_DUMP_START + KERNEL_BANNER + RING_DUMP_END,
    )
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "serial and ring disagree" in r.stdout + r.stderr


@pytest.mark.integration
def test_suite_passed_but_key_never_arrived_fails(tree):
    """ALL TESTS PASSED is not enough: init's input check skips without a
    key, so the script itself must see the key reach the kernel and init."""
    r = _run(tree, BLK_MODERN + r"  [OK] VirtIO input device\n" + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PASS (native): init Tier-1 suite" in r.stdout
    assert "injected key A never reached the kernel input queue" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("tool", NET_TOOLS)
def test_net_tool_that_did_not_answer_nodev_fails(tree, tool):
    """A net tool that exits 19 without NetAttach's NoDev line (or that
    reached the kernel undeclared) fails the gate, though the suite passed."""
    bad = rf"[test] {tool} nodev ... PASS (exit=19)\n"
    good = rf"[test] {tool} nodev ... {tool}: NetAttach: Errno.NoDev (no network service) (-19)\nPASS (exit=19)\n"
    r = _run(tree, PASSED.replace(good, bad))
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"FAIL (native): {tool} did not exit 19 (Errno.NoDev)" in r.stdout


@pytest.mark.integration
def test_write_empty_on_tmp_alone_fails(tree):
    """write_empty_test passes with only /tmp when /var/boots is missing; a
    boot whose storage disk came up must not pass that way (AGAST #4830)."""
    tmp_only = r"[test] write_empty_test ... [write_empty_test] PASS: /tmp (no storage disk, /var skipped)\nPASS (exit=0)\n"
    r = _run(tree, PASSED.replace(WRITE_EMPTY_OK, tmp_only))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native): write_empty_test did not pass on both /tmp and /var" in r.stdout


@pytest.mark.integration
def test_stat_on_tmp_alone_fails(tree):
    """stat_test passes with only /tmp when /var/boots is missing; a boot
    whose storage disk came up must not pass that way (AGAST #4832)."""
    tmp_only = r"[test] stat_test ... [stat_test] PASS: /tmp (no storage disk, /var skipped)\nPASS (exit=0)\n"
    r = _run(tree, PASSED.replace(STAT_OK, tmp_only))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native): stat_test did not pass on both /tmp and /var" in r.stdout


@pytest.mark.integration
def test_net_call_reaching_the_kernel_undeclared_fails(tree):
    r = _run(tree, r"[syscall] unknown: 228\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "a net call reached the kernel undeclared" in r.stdout


@pytest.mark.integration
def test_keyboard_that_never_came_up_fails(tree):
    r = _run(tree, BLK_MODERN + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "virtio-keyboard-pci did not come up" in r.stdout


@pytest.mark.integration
def test_kernel_panic_fails(tree):
    r = _run(tree, r"[kmain] start\nKERNEL PANIC: planted\n")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native)" in r.stdout


def _dump(stdout: str, verdict: str) -> str:
    """What no_exception printed: its header line through its verdict."""
    head = "around the first EXCEPTION or KERNEL PANIC -----\n"
    assert head in stdout and verdict in stdout, stdout
    return stdout.split(head, 1)[1].split(verdict, 1)[0]


@pytest.mark.integration
def test_kernel_panic_prints_the_panic_and_the_boot_lines_before_it(tree):
    """AGAST #4856: a grub-reboot boot panicked before init, and the step
    printed only "kernel exception during boot": the tail starts at init's
    suite and the dump at an EXCEPTION line, so a KERNEL PANIC showed
    neither its message nor the boot lines that led to it."""
    r = _run(
        tree,
        r"  [..] Physical memory[pmm] no room below 1 GiB for a 4 KiB bitmap\r\n"
        r"\r  [!!] Physical memory (no bitmap)\n"
        r"  [..] Kernel heap\r  [!!] Kernel heap (init failed)\n"
        r"\n*** KERNEL PANIC ***\nkernel heap corrupt after vfs_init\n",
        poweroff=False,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native): kernel panic during boot" in r.stdout
    out = _dump(r.stdout, "FAIL (native): kernel panic")
    for line in ("[pmm] no room below 1 GiB", "[!!] Kernel heap (init failed)",
                 "*** KERNEL PANIC ***", "kernel heap corrupt after vfs_init"):
        assert line in out, r.stdout


@pytest.mark.integration
def test_exception_prints_its_register_dump(tree):
    """An exception other than a page fault has no CR2 line: its dump runs
    to the registers, and so must what the step prints (AGAST #4856)."""
    r = _run(
        tree,
        r"[kmain] start\n\n!!! EXCEPTION !!!\nVector: 13 (General Protection)\n"
        r"RIP: 0xFFFFFFFF80101234\n\nRegisters:\nRAX: 0x0\n",
        poweroff=False,
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native): kernel exception during boot" in r.stdout
    out = _dump(r.stdout, "FAIL (native): kernel exception")
    for line in ("[kmain] start", "Vector: 13 (General Protection)",
                 "RIP: 0xFFFFFFFF80101234", "RAX: 0x0"):
        assert line in out, r.stdout


@pytest.mark.integration
def test_exception_fails_even_if_the_suite_passed(tree):
    r = _run(tree, r"EXCEPTION: #GP\nRIP=0x1\nCR2=0\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_no_verdict_before_the_timeout_fails(tree):
    r = _run(tree, r"[kmain] start\n", poweroff=False)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout
    assert "no verdict within 3s (BOOT_TIMEOUT)" in r.stdout


@pytest.mark.integration
def test_serial_log_that_stops_growing_is_a_hang(tree):
    """A hang is a log that stops growing for BOOT_STALL seconds, however
    long the cap: a fixed 60 s cap failed live boots on a loaded host (AGAST
    #4078), so the cap went up and this is what catches a real hang."""
    r = _run(
        tree,
        r"[kmain] start\n",
        poweroff=False,
        env_extra={"BOOT_STALL": "2", "BOOT_TIMEOUT": "20"},
    )
    assert r.returncode == 1, r.stdout + r.stderr
    assert "hung: serial output stopped for 2s (BOOT_STALL)" in r.stdout
    assert "serial tail: [kmain] start" in r.stdout


@pytest.mark.integration
def test_failed_suite_fails(tree):
    r = _run(tree, r"  Results: 9 passed, 1 failed\n  TESTS FAILED\n")
    assert r.returncode == 1, r.stdout + r.stderr


def _stub_rz(tree, rc: int) -> None:
    _stub(tree["root"], "rz", f"#!/usr/bin/env bash\nexit {rc}\n")


@pytest.mark.integration
def test_build_missing_a_toolchain_binary_is_a_setup_error(tree):
    """`rz build` exits EXIT_SETUP when e.g. lld-link is absent; the script
    used to turn that into a FAIL."""
    _stub_rz(tree, ci_local.EXIT_SETUP)
    r = _run(tree, PASSED, env_extra={"SKIP_BUILD": "0"})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr


@pytest.mark.integration
def test_build_failure_is_a_failure(tree):
    _stub_rz(tree, 1)
    r = _run(tree, PASSED, env_extra={"SKIP_BUILD": "0"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: build of harland failed" in r.stdout


@pytest.mark.integration
def test_red_zone_use_fails_before_booting(tree):
    """AGAST #4308: the kernel is checked for red-zone use, and a kernel
    that uses it fails the boot test."""
    (tree["root"] / "projects/harland/tools/check_no_red_zone.py").write_text(
        "import sys\nprint('FAIL: uses the red zone')\nsys.exit(1)\n")
    r = _run(tree, PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: uses the red zone" in r.stdout
    assert "ALL TESTS PASSED" not in r.stdout


@pytest.mark.integration
def test_missing_build_output_is_a_failure_not_a_setup_error(tree):
    (tree["root"] / "projects/harland/build/debug/harland.elf").unlink()
    r = _run(tree, PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


# --------------------------------------------------------------------------
# AGAST #1848 (M2.2): the boot again, on the image ritz1 builds
# --------------------------------------------------------------------------
#
# main.yml's bootstrap job builds ritz1 and ritz1_selfhosted, so it boots
# harland twice more, once per compiler, with COMPILER=<name>. COMPILER makes
# the script build with `./rz build <pkg> --compiler <name>` (unless
# SKIP_BUILD=1) and requires every binary the boot loads to have a build
# manifest whose "compiler" is <name>. Without that check, a stale ritz0 build
# left in build/debug would boot and pass as the "ritz1 image" while ritz1 had
# built nothing.

COMPILERS = ("ritz1", "ritz1_selfhosted")
BUILD_STEP = "Build ritz1 + ritz1_selfhosted"
KERNEL = "projects/harland/build/debug/harland.elf"
LOADER = "projects/harland/build/debug/BOOTX64.EFI"
INIT = "projects/indium/build/debug/init.elf"


# --------------------------------------------------------------------------
# Wiring: main.yml's bootstrap job
# --------------------------------------------------------------------------


def _bootstrap() -> list[dict]:
    spec = yaml.safe_load(ci_local.WORKFLOW.read_text())
    return spec["jobs"]["bootstrap"]["steps"]


def _boot_steps(steps: list[dict]) -> dict[str, int]:
    """{compiler: index} of the bootstrap steps that boot a ritz1-family image."""
    found: dict[str, int] = {}
    for i, s in enumerate(steps):
        run = str(s.get("run", ""))
        if BOOT_SCRIPT not in run:
            continue
        for c in COMPILERS:
            if f"COMPILER={c} " in run:
                assert c not in found, f"two bootstrap steps boot the {c} image"
                found[c] = i
    return found


def test_bootstrap_boots_each_self_hosted_image_once():
    found = _boot_steps(_bootstrap())
    assert sorted(found) == sorted(COMPILERS), found


def test_boots_come_after_the_compilers_are_built():
    steps = _bootstrap()
    build = [i for i, s in enumerate(steps) if s.get("name") == BUILD_STEP]
    assert len(build) == 1
    assert all(i > build[0] for i in _boot_steps(steps).values())


@pytest.mark.parametrize("compiler", COMPILERS)
def test_boot_step_is_a_real_gate(compiler):
    """Both boots (native and GRUB), no escape hatch, a bound, and not a step
    ci_local would skip as setup."""
    steps = _bootstrap()
    step = steps[_boot_steps(steps)[compiler]]
    assert not step.get("continue-on-error", False)
    assert "|| true" not in step["run"]
    assert "SKIP_BUILD" not in step["run"], "the step must build with the compiler"
    assert step.get("working-directory", ".") == "."
    assert 0 < int(step.get("timeout-minutes", 0)) <= 10
    assert "test_tier1_boot.sh native" not in step["run"]
    assert "test_tier1_boot.sh grub" not in step["run"]
    parsed = [
        s for s in ci_local.load_steps()
        if s.job == "bootstrap" and s.name == step["name"]
    ]
    assert len(parsed) == 1 and not parsed[0].is_setup


def test_boot_tools_installed_in_bootstrap_as_a_setup_step():
    steps = _bootstrap()
    installs = [i for i, s in enumerate(steps) if INSTALL_SCRIPT in str(s.get("run", ""))]
    assert len(installs) == 1
    assert installs[0] < min(_boot_steps(steps).values())
    parsed = [
        s for s in ci_local.load_steps()
        if s.job == "bootstrap" and INSTALL_SCRIPT in s.run
    ]
    assert len(parsed) == 1 and parsed[0].is_setup


def test_each_boot_keeps_its_own_serial_logs_and_they_are_uploaded():
    """native.log/grub.log per compiler: one shared KEEP_WORK would let the
    second boot overwrite the first's logs."""
    steps = _bootstrap()
    dirs = set()
    for c, i in _boot_steps(steps).items():
        run = steps[i]["run"]
        assert f"boot-logs/{c}" in run and "KEEP_WORK=" in run
        dirs.add(c)
    assert len(dirs) == len(COMPILERS)
    last = max(_boot_steps(steps).values())
    uploads = [
        s for s in steps[last + 1:]
        if "actions/upload-artifact" in str(s.get("uses", ""))
        and "boot-logs" in str(s.get("with", {}).get("path", ""))
    ]
    assert len(uploads) == 1 and uploads[0].get("if") == "always()"


# --------------------------------------------------------------------------
# Verdicts: COMPILER in the script, against the stub QEMU
# --------------------------------------------------------------------------


def _manifest(root: Path, rel: str, compiler: str) -> None:
    Path(f"{root / rel}.manifest.json").write_text(json.dumps({"compiler": compiler}))


def _all_built_by(tree, compiler: str) -> None:
    for rel in (KERNEL, LOADER, INIT):
        _manifest(tree["root"], rel, compiler)


@pytest.mark.integration
def test_image_built_by_the_compiler_passes(tree):
    _all_built_by(tree, "ritz1")
    r = _run(tree, PASSED, env_extra={"COMPILER": "ritz1"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: 3 boot binaries built by ritz1" in r.stdout


# One row per kind of binary the boot loads: the kernel ELF, the UEFI PE
# loader and an initramfs user binary are checked by separate paths.
@pytest.mark.integration
@pytest.mark.parametrize("rel", [KERNEL, LOADER, INIT], ids=["kernel", "loader", "user"])
def test_binary_built_by_another_compiler_fails(tree, rel):
    _all_built_by(tree, "ritz1")
    _manifest(tree["root"], rel, "ritz0")
    r = _run(tree, PASSED, env_extra={"COMPILER": "ritz1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"FAIL: {Path(rel).name} was built by ritz0, not ritz1" in r.stdout


@pytest.mark.integration
def test_binary_without_a_manifest_fails(tree):
    _all_built_by(tree, "ritz1")
    Path(f"{tree['root'] / LOADER}.manifest.json").unlink()
    r = _run(tree, PASSED, env_extra={"COMPILER": "ritz1"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: BOOTX64.EFI has no build manifest" in r.stdout


@pytest.mark.integration
def test_unknown_compiler_is_bad_usage(tree):
    r = _run(tree, PASSED, env_extra={"COMPILER": "gcc"})
    assert r.returncode == 2, r.stdout + r.stderr


@pytest.mark.integration
def test_build_passes_the_compiler_to_rz(tree):
    log = tree["tmp"] / "rz.log"
    _stub(tree["root"], "rz", f'#!/usr/bin/env bash\necho "$@" >> {log}\n')
    # initramfs.pkgs' compiler= entries (Buddhafinger, AGAST #4834) build in
    # the builder image instead: a stub run, logged apart from rz's.
    blog = tree["tmp"] / "builder.log"
    _stub(tree["stubs"], "fake-builder-run", f'#!/usr/bin/env bash\necho "$@" >> {blog}\n')
    _all_built_by(tree, "ritz1_selfhosted")
    r = _run(tree, PASSED, env_extra={
        "SKIP_BUILD": "0", "COMPILER": "ritz1_selfhosted",
        "RZ_BUILDER_IMAGE": "rz-builder:fake",
        "RZ_BUILDER_RUN": str(tree["stubs"] / "fake-builder-run"),
    })
    assert r.returncode == 0, r.stdout + r.stderr
    calls = log.read_text().splitlines()
    assert calls and calls[0] == "build harland --compiler ritz1_selfhosted"
    assert all(c.endswith("--compiler ritz1_selfhosted") for c in calls), calls
    assert not [c for c in calls if " buddhafinger" in c], calls
    runs = blog.read_text().splitlines()
    assert len(runs) == 1 and "rz-builder:fake projects/buddhafinger" in runs[0], runs


# --------------------------------------------------------------------------
# Boot-test mode (AGAST #1887): the kernel's self-tests are asserted
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_native_esp_carries_the_boot_test_marker(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ESP ./harland/boot-test" in (tree["tmp"] / "stub.log").read_text()
    # ...and \\harland\\smp-user, the boot test of processes on APs (#4881).
    assert "ESP ./harland/smp-user" in (tree["tmp"] / "stub.log").read_text()
    assert f"PASS (native): {len(BOOT_TESTS)} kernel boot self-tests passed" in r.stdout


def test_grub_boots_pass_boot_test_on_the_cmdline():
    """GRUB has no ESP marker for the kernel to see: the multiboot2 cmdline
    carries the same option."""
    text = (REPO / BOOT_SCRIPT).read_text()
    assert "multiboot2 /boot/harland.elf boot-test smp-user;" in text


@pytest.mark.integration
def test_no_boot_test_summary_fails(tree):
    """A kernel that ran no self-tests (or never reached the summary) fails."""
    r = _run(tree, PASSED.replace(BOOT_TEST_OK, ""))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native): no boot-test summary" in r.stdout


@pytest.mark.integration
def test_a_failed_boot_test_fails(tree):
    serial = PASSED.replace("PASS heap\n", "FAIL heap\n").replace(
        f"{len(BOOT_TESTS)} passed, 0 failed", f"{len(BOOT_TESTS) - 1} passed, 1 failed"
    )
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL (native): boot self-tests failed: heap" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("name", ["channel-close", "channel-debug-print"])
def test_a_skipped_boot_test_fails(tree, name):
    """The two IPC calls the kernel skipped as page faults must run: a boot
    that leaves one out fails even with a clean summary."""
    serial = PASSED.replace(f"[boot-test] PASS {name}\n", "").replace(
        f"{len(BOOT_TESTS)} passed", f"{len(BOOT_TESTS) - 1} passed"
    )
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"FAIL (native): boot self-tests missing: {name}" in r.stdout


@pytest.mark.integration
def test_boot_test_lines_repeated_by_the_ring_dump_count_once(tree):
    """The \\harland\\klog-dump ring dump repeats the kernel's log, its
    [boot-test] lines included: the gate reads them only before the dump."""
    assert PASSED.count("[boot-test] PASS heap") == 2
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"PASS (native): {len(BOOT_TESTS)} kernel boot self-tests passed" in r.stdout
