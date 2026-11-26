"""harland's test_tier1_boot.sh binds its QEMU monitor socket under /tmp (#4177).

A unix socket path must fit sun_path: 108 bytes with the NUL, so 107 usable.
The gate sets TMPDIR deep in its worktree, and the script made the monitor
socket `$(mktemp -d)/<name>-mon.sock`; past the limit QEMU fails to bind it
and never starts, which reads as a boot with no verdict.  #4100 and #4135
fixed the other harnesses the same way: the socket dir is `mktemp -d /tmp/...`.

The script runs from a copy in a scratch tree (it finds everything relative to
itself) with stand-in build outputs, a fake qemu-img, and a fake
qemu-system-x86_64 that really bind()s its -monitor path, accepts the
script's sendkey, and writes a passing serial log.  Native mode only: grub
adds nothing the socket path depends on.
"""

import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TIER1_SH = REPO / "projects" / "harland" / "tools" / "test_tier1_boot.sh"
SOCK_DIR_SH = REPO / "projects" / "ritz" / "tools" / "sock_dir.sh"
SUN_PATH_MAX = 107  # sizeof(sun_path) - 1 for the NUL

FAKE_QEMU = textwrap.dedent("""\
    #!/usr/bin/env python3
    # Bind -monitor the way QEMU does (failing past sun_path), take one
    # sendkey on it, then log a passing native boot and power off; or, with
    # FAKE_QEMU_HANG, go quiet and answer the script's vCPU dump instead.
    import os, socket, sys, time
    args = sys.argv[1:]
    mon = args[args.index("-monitor") + 1].removeprefix("unix:").split(",")[0]
    serial = args[args.index("-serial") + 1].removeprefix("file:")
    open(os.environ["FAKE_QEMU_MON"], "w").write(mon)
    s = socket.socket(socket.AF_UNIX)
    try:
        s.bind(mon)
    except OSError as e:
        sys.exit(f"qemu-system-x86_64: -monitor {mon}: {e}")
    s.listen(1)
    # the kernel's banner and boot-test self-tests (\\harland\\boot-test,
    # #1887), then its ring dump repeating both (\\harland\\klog-dump, #1885)
    names = ("vmm higher-half heap ipc channel-close channel-debug-print munmap "
             "mmap-failure pmm-above-4g mmap-overlap mmap-cursor mmap-driver-window elf-loader sysret nmi-gs ist-nest nmi-nest cap-device shm-map virtio-blk-read proc-create-init driver-enter driver-fault driver-preempt driver-reap drv-irq-wait console-poll").split()
    log = ("\\n========================================\\n    Hello from Harland!\\n========================================\\n"
           + "".join(f"[boot-test] PASS {n}\\n" for n in names)
           + f"[boot-test] {len(names)} passed, 0 failed\\n")
    with open(serial, "a") as f:
        f.write(log + "\\n=== RING BUFFER DUMP (kernel log) ===\\n" + log
                + "\\n=== END RING BUFFER ===\\n"
                "[OK] VirtIO input device\\n")
    s.settimeout(20)
    c, _ = s.accept()
    c.sendall(b"QEMU monitor\\n(qemu) ")
    if b"sendkey a" not in c.recv(4096):
        sys.exit("no sendkey")
    if os.environ.get("FAKE_QEMU_HANG"):
        c.close()
        c, _ = s.accept()
        if b"info registers -a" not in c.recv(4096):
            sys.exit("no vCPU dump")
        c.sendall(b"CPU#0\\nRIP=ffffffff80fa4e01 RFL=00000246\\n")
        c.close()
        time.sleep(600)  # hung guest: the script kills us
    with open(serial, "a") as f:
        f.write("[virtio-blk] Device 0 initialized (64 MB, modern, queue 256)\\n"
                "[virtio-input] event type=1 code=30 value=1\\n"
                "key event code=30 value=1\\n"
                "[OK] Persistent storage\\n"
                "[timer] LAPIC timer 62500000 Hz (bus/16, TSC-calibrated), periodic 100 Hz tick, initial count 625000\\n"
                "[busy A] 1/8\\n[busy B] 1/8\\n[busy A] 2/8\\n[busy B] 2/8\\n"
                "[busy A] 3/8\\n[busy B] 3/8\\n[busy A] 4/8\\n[busy B] 4/8\\n"
                "[busy A] 5/8\\n[busy B] 5/8\\n[busy A] 6/8\\n[busy B] 6/8\\n"
                "[busy A] 7/8\\n[busy B] 7/8\\n[busy A] 8/8\\n[busy B] 8/8\\n"
                "[sched] 350 ticks, 280 switches, 230 preemptions\\n"
                "[smp] syscall stacks OK: 4 CPUs in ring-3 SYSCALL at once, distinct per-CPU stacks and frames\\n"
                "[test] ping nodev ... ping: NetAttach: Errno.NoDev (no network service) (-19)\\nPASS (exit=19)\\n"
                "[test] udp-send nodev ... udp-send: NetAttach: Errno.NoDev (no network service) (-19)\\nPASS (exit=19)\\n"
                "[test] udp-recv nodev ... udp-recv: NetAttach: Errno.NoDev (no network service) (-19)\\nPASS (exit=19)\\n"
                "[test] write_empty_test ... [write_empty_test] PASS: /tmp and /var\\nPASS (exit=0)\\n"
                "ALL TESTS PASSED\\n"
                "[exit] init exited with code 0\\n")
    """)

FAKE_MKINITRAMFS = textwrap.dedent("""\
    import sys
    open(sys.argv[sys.argv.index("--output") + 1], "w").close()
    """)


def _tree(root: Path) -> Path:
    """A projects/ tree the copied script takes for a built checkout."""
    tools = root / "projects" / "harland" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(TIER1_SH, tools / TIER1_SH.name)
    # ...which sources the shared socket-dir picker (AGAST #4282).
    sock_dir_sh = root / "projects" / "ritz" / "tools" / SOCK_DIR_SH.name
    sock_dir_sh.parent.mkdir(parents=True)
    shutil.copy(SOCK_DIR_SH, sock_dir_sh)
    (tools / "mkinitramfs.py").write_text(FAKE_MKINITRAMFS)
    # Its fake kernel passes the red-zone check (AGAST #4308).
    (tools / "check_no_red_zone.py").write_text("import sys\nsys.exit(0)\n")
    for elf in ("harland/build/debug/harland.elf", "harland/build/debug/BOOTX64.EFI",
                "indium/build/debug/init.elf"):
        p = root / "projects" / elf
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
    (root / "projects" / "indium" / "initramfs.pkgs").write_text("indium\n")
    return tools / TIER1_SH.name


# (FAKE_QEMU_HANG, exit status, stdout line): the monitor socket carries both
# the sendkey of a passing boot and the vCPU dump of a hung one (#4078).
CASES = [
    ("", 0, "PASS (native): sendkey a reached the kernel input queue"),
    ("1", 1, "CPU#0 RIP=ffffffff80fa4e01 RFL=00000246"),
]


@pytest.mark.integration
def test_tier1_monitor_socket_fits_sun_path_under_long_tmpdir(tmp_path):
    script = _tree(tmp_path / "repo")
    tmpdir = tmp_path / ("t" * 50) / ("m" * 50)
    tmpdir.mkdir(parents=True)
    assert len(os.fsencode(tmpdir)) > SUN_PATH_MAX  # any socket under it is over
    bins = tmp_path / "bin"
    bins.mkdir()
    (bins / "qemu-system-x86_64").write_text(FAKE_QEMU)
    (bins / "qemu-img").write_text('#!/bin/sh\nexec touch "$(eval echo \\${$#})"\n')
    for b in bins.iterdir():
        b.chmod(0o755)
    ovmf = tmp_path / "OVMF_CODE.fd"
    ovmf.touch()
    mon_file = tmp_path / "mon.path"
    for hang, rc, line in CASES:
        env = dict(os.environ, TMPDIR=str(tmpdir), PATH=f"{bins}:{os.environ['PATH']}",
                   SKIP_BUILD="1", OVMF_CODE=str(ovmf), BOOT_TIMEOUT="20",
                   BOOT_STALL="2", POWEROFF_WAIT="5", FAKE_QEMU_MON=str(mon_file),
                   FAKE_QEMU_HANG=hang)
        r = subprocess.run(["bash", str(script), "native"], capture_output=True,
                           text=True, timeout=60, env=env)
        mon = mon_file.read_text()
        assert len(os.fsencode(mon)) <= SUN_PATH_MAX, mon
        assert not mon.startswith(str(tmpdir)), mon
        assert r.returncode == rc, r.stdout + r.stderr
        assert line in r.stdout, r.stdout + r.stderr
        # The EXIT trap removed the socket dir too.
        assert not Path(mon).parent.exists(), f"{mon} left behind"
