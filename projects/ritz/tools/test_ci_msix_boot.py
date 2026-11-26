#!/usr/bin/env python3
"""CI must boot harland with PCI devices on MSI-X (AGAST #1852).

projects/harland/tools/test_msix_boot.sh boots the kernel under OVMF with a
virtio-net NIC and an NVMe controller. It passes only if the NVMe's MSI-X
table is found, virtio-net comes up in MSI-X mode, the NIC's interrupt
counter is > 0, and init's Tier-1 suite still reports ALL TESTS PASSED. The
NVMe controller must come up in MSI-X mode too (AGAST #3630): its admin and
I/O completion queues on vectors, a read of the disk's last 200 sectors with
interrupts on that returns the pattern the script wrote, an interrupt counter
> 0, commands that waited for their interrupt and none that completed without
it. The NIC is modern-only with a 1024-entry RX queue (AGAST #3576), so it
must also come up over the MMIO transport, cap that queue at 256 and get a
DHCP lease. It boots twice (AGAST #4723): pc, then q35 with intel-iommu and
the NIC behind it, where every check holds again with DMA translated
("[vtd] translation on") and the NIC on VIRTIO_F_ACCESS_PLATFORM.

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
MSIX_SCRIPT = "projects/harland/tools/test_msix_boot.sh"
TIER1_SCRIPT = "projects/harland/tools/test_tier1_boot.sh"

# The same stubs as test_ci_harland_boot.py (kept local: tools/ test modules
# don't import each other). The QEMU stub writes $FAKE_SERIAL to the
# `-serial file:PATH` it was given and idles until killed; every argv goes
# to $STUB_LOG. The translating boot (an intel-iommu on the command line,
# AGAST #4723) gets $FAKE_SERIAL_VTD instead: since the cutover (AGAST
# #4735) its NIC has another owner, so its log is its own.
QEMU_STUB = r"""#!/usr/bin/env bash
echo "$@" >> "$STUB_LOG"
log="$FAKE_SERIAL"
case " $* " in *" intel-iommu,"*) log="$FAKE_SERIAL_VTD" ;; esac
prev=""
for a in "$@"; do
    if [ "$prev" = "-serial" ]; then printf '%b' "$log" > "${a#file:}"; fi
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

# #4582: the pc machine has no MCFG, so PCI stays on port I/O. Logged before
# any driver's MSI-X set-up, so every fixture that reaches NVMe carries it.
PCI_PORT_IO = r"[pci] no MCFG: segment 0 only, port I/O\n"
NVME_TABLE = PCI_PORT_IO + r"[msix] 00:05.00 1B36:0010: 65 vectors, table BAR0+0x2000\n"
NIC_ON = r"[msix] virtio-net: MSI-X on, vectors config=64 rx=65 tx=66\n"


def interrupts(n: int) -> str:
    return rf"[msix] virtio-net interrupts: {n}\n"


NET_MODERN = r"[virtio-net] Transport: modern (MMIO)\n"
RX_CAPPED = r"[virtio-net] Queue 0: size=256 (device max 1024)\n"
DHCP_OK = r"[dhcp] Configured!\n"
TX_BURST_OK = r"[net] TX burst: sent=300/300 replies=300\n"
MODERN_OK = NET_MODERN + RX_CAPPED + DHCP_OK + TX_BURST_OK




def _nvme_pattern_fnv() -> int:
    """FNV-1a (32-bit) of the last 200 512-byte sectors (32568-32767) of the
    16 MiB NVMe image the script writes: sector N is ("LBA" + N as u32 LE +
    "!") * 64, as in test_nvme_boot.sh."""
    h = 0x811C9DC5
    for n in range(32568, 32768):
        for b in (b"LBA" + struct.pack("<I", n) + b"!") * 64:
            h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h


NVME_FNV = _nvme_pattern_fnv()
NVME_ON = r"[msix] nvme harland-msix: MSI-X on, vectors admin=67 io=68\n"
NVME_READ = rf"[msix] nvme harland-msix nsid 1: LBA 32568-32767 fnv1a={NVME_FNV}\n"


def nvme_interrupts(n: int, missed: int = 0, waited: int = 3) -> str:
    return (rf"[msix] nvme interrupts: {n}, commands waited: {waited}, "
            rf"completions without one: {missed}\n")


# hlts the commands' interrupt waits slept in: only logged, 0 is legal when
# QEMU raises the interrupt before the wait checks (AGAST #4246)
NVME_HALTED = r"[msix] nvme waits halted: 3\n"


def nvme_idle(p: int) -> str:
    """hlts of one watchdog round of the same wait with no command
    outstanding: it slept in hlt rather than spinning (AGAST #4212, #4246)"""
    return rf"[msix] nvme idle wait halted: {p}\n"


NVME_OK = NVME_ON + NVME_READ + nvme_interrupts(5) + NVME_HALTED + nvme_idle(1)

# virtio-blk and virtio-input on MSI-X over the modern transport; blk reads
# and the DHCP window sleep on their vectors (AGAST #3631)
BLK_MODERN = r"[virtio-blk] Device 0 initialized (16 MB, modern, queue 256)\n"
BLK_ON = r"[msix] virtio-blk: MSI-X on, vector 65\n"
INPUT_ON = r"[msix] virtio-input: MSI-X on, vector 64\n"


def blk_waits(n: int = 17, waited: int = 8, data: str = "same") -> str:
    return (rf"[msix] virtio-blk interrupts: {n}, requests waited: {waited}, "
            rf"halted: 8, data: {data}\n")


def net_rx_waits(waits: int = 880, halts: int = 880) -> str:
    return rf"[msix] virtio-net rx waits: {waits}, halted: {halts}\n"


WAITS_OK = BLK_MODERN + BLK_ON + INPUT_ON + blk_waits() + net_rx_waits()

# AGAST #4724: without an IOMMU the NIC stays on physical addresses and a
# ring-1 owner is refused (both boots log a verdict; the vtd fixture adds
# the allowed one).
NIC_REFUSED = r"[nic-dma] ring-1 owner refused: the NIC is not isolated on this boot; the owner stays in the kernel\n"

PASSED = NVME_TABLE + MODERN_OK + NIC_ON + interrupts(8) + NVME_OK + WAITS_OK + NIC_REFUSED + SUITE_PASSED

# The translating boot's own lines (AGAST #4723): interrupt remapping, TE
# with identity contexts, and the NIC's bit 33.
IR_ON = r"      Interrupt remapping: VT-d on, 1 unit(s), table at 0x7E000, 8-bit xAPIC destinations\n"
# AGAST #4724: the line also counts the requesters held for a private domain.
TE_ON = (r"      [vtd] translation on: identity domain for every requester on 1 PCI segment(s), RAM below 0x80000000, "
         r"0 RMRR(s), 1 requester(s) held for a private domain\n")
NET_PLATFORM = r"[virtio-net] VIRTIO_F_ACCESS_PLATFORM negotiated: DMA through the IOMMU\n"
# The NIC's private domain (AGAST #4724): held out of identity at TE, its
# own domain before bus master, the fault probe, a frame DMA'd into a
# granted IOVA, and net_ring1_allowed.
NIC_DOMAIN = r"[nic-dma] private domain 2 for 0000:00:04.0 and 0 alias(es), never in the identity map; bus master on\n"
NIC_FAULT_RECORD = r"[nic-dma] fault record: source 0000:00:04.0 IOVA 0x1000006000 reason 6 (read)\n"
NIC_FAULT = r"[nic-dma] fault probe: the NIC's DMA to unmapped IOVA 0x1000006000 faulted with its source ID 0000:00:04.0\n"
NIC_ALLOWED = (r"[nic-dma] ring-1 owner allowed: translation on, remapping on, compatibility format blocked (read from the unit), "
               r"NIC isolated; the owner is /bin/virtio-net\n")
# The cutover (AGAST #4735): on the translating boot /bin/virtio-net owns the
# NIC. Its rings and pools are DrvDmaAlloc runs in the NIC's domain (the
# kernel logs each), and the frame it received lands in one of them (the
# driver logs the IOVA in decimal: 0x1000007000 + 0x800).
DMA_RUN_RING = r"[nic-dma] DrvDmaAlloc: pid 2, 3 page(s) at IOVA 0x1000004000 in domain 2\n"
DMA_RUN_POOL = r"[nic-dma] DrvDmaAlloc: pid 2, 16 page(s) at IOVA 0x1000007000 in domain 2\n"
NIC_DMA = r"[virtio-net] device DMA: 602 bytes received into granted IOVA 68719507456\n"
NIC_DMA_OK = NIC_DOMAIN + NIC_FAULT_RECORD + NIC_FAULT + NIC_ALLOWED + DMA_RUN_RING + DMA_RUN_POOL + NIC_DMA
RING1_PARKED = r"[net-ring1] /bin/virtio-net pid 2 parked: generation 2 published\n"
DRIVER_UP = r"[virtio-net] up: MAC published, 32 RX buffers posted\n"


def driver_parks(p: int) -> str:
    return rf"[msix] virtio-net driver parks: {p}\n"


# What the in-kernel owner logs, and the ring-1 owner must not beside it
KERNEL_NETDEV = r"[netdev] Registered VirtIO-net device, MAC: 52:54:00:12:34:56\n"
KERNEL_NIC_UP = r"[virtio-net] Initialization complete!\n"
# The whole translating boot: the same storage, NVMe and NIC checks, the
# NIC brought up by the ring-1 driver (modern transport from the kernel
# probe, bit 33 and the capped RX queue from the driver), and its parks in
# place of the in-kernel RX waits.
VTD_OK = (NVME_TABLE.replace(PCI_PORT_IO, "") + IR_ON + TE_ON + NET_MODERN + NIC_DMA_OK + NIC_ON
          + RING1_PARKED + NET_PLATFORM + RX_CAPPED + DRIVER_UP + DHCP_OK + TX_BURST_OK + interrupts(8)
          + driver_parks(41) + NVME_OK + BLK_MODERN + BLK_ON + INPUT_ON + blk_waits() + SUITE_PASSED)


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
    shutil.copy(REPO / "projects/indium/initramfs.pkgs", root / "projects/indium/initramfs.pkgs")
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
        "FAKE_SERIAL_VTD": VTD_OK,
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
def test_missing_qemu_img_is_a_setup_error(tree):
    r = _run(tree, qemu_img=False, full_path=False)
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "qemu-img" in r.stderr


@pytest.mark.integration
def test_missing_ovmf_is_a_setup_error(tree):
    r = _run(tree, PASSED, env_extra={"OVMF_CODE": str(tree["tmp"] / "nope.fd")})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr
    assert "SETUP ERROR" in r.stderr and "OVMF" in r.stderr


@pytest.mark.integration
def test_build_missing_a_toolchain_binary_is_a_setup_error(tree):
    _stub(tree["root"], "rz", f"#!/usr/bin/env bash\nexit {ci_local.EXIT_SETUP}\n")
    r = _run(tree, PASSED, env_extra={"SKIP_BUILD": "0"})
    assert r.returncode == ci_local.EXIT_SETUP, r.stdout + r.stderr


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
    assert "PASS: virtio-net delivered 8 MSI-X interrupts" in r.stdout
    assert "interrupts: 8" in (keep / "msix.log").read_text()
    assert "[vtd] translation on" in (keep / "msix-vtd.log").read_text()
    assert "PASS: VT-d DMA translation is on" in r.stdout


@pytest.mark.integration
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
    # Modern-only disk and keyboard: their MSI-X goes through common_cfg
    assert "virtio-blk-pci,drive=initramfs,disable-legacy=on" in argv
    assert "-device virtio-keyboard-pci" in argv


@pytest.mark.integration
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


@pytest.mark.integration
@pytest.mark.parametrize(
    "burst, want",
    [
        ("", "no TX burst result"),
        # Every send past the 256 TX descriptors failed: none reclaimed
        (r"[net] TX burst: sent=256/300 replies=256\n", "sent 256 of 300"),
        # Too small a burst can't cross the ring
        (r"[net] TX burst: sent=200/200 replies=200\n", "sent 200 of 200"),
        # All sent, but frames overwritten in a shared TX buffer
        (r"[net] TX burst: sent=300/300 replies=75\n", "75 distinct replies"),
    ],
    ids=["missing", "tx-ring-exhausted", "burst-too-small", "tx-buffer-reused"],
)
def test_tx_burst_check_fails(tree, burst, want):
    r = _run(tree, PASSED.replace(TX_BURST_OK, burst))
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout


@pytest.mark.integration
def test_zero_interrupts_fails(tree):
    """The NIC in MSI-X mode but nothing delivered: the mutation that drops
    msix_dispatch from irq_handler, or leaves the table entries masked."""
    r = _run(tree, NVME_TABLE + MODERN_OK + NIC_ON + interrupts(0) + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "counter is 0, want > 0" in r.stdout


@pytest.mark.integration
def test_missing_counter_fails(tree):
    r = _run(tree, NVME_TABLE + MODERN_OK + NIC_ON + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "counter is missing" in r.stdout


@pytest.mark.integration
def test_nic_not_in_msix_mode_fails(tree):
    r = _run(tree, NVME_TABLE + MODERN_OK + interrupts(3) + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not come up in MSI-X mode" in r.stdout


@pytest.mark.integration
def test_no_nvme_msix_table_fails(tree):
    r = _run(tree, MODERN_OK + NIC_ON + interrupts(3) + SUITE_PASSED)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "NVMe controller" in r.stdout


@pytest.mark.integration
def test_exception_fails_even_if_everything_else_passed(tree):
    r = _run(tree, r"EXCEPTION: #GP\nRIP=0x1\nCR2=0\n" + PASSED)
    assert r.returncode == 1, r.stdout + r.stderr


@pytest.mark.integration
def test_boots_pc_then_q35_with_the_nic_behind_intel_iommu(tree):
    """AGAST #4723: the second boot is the translating one: q35 with the
    split irqchip, intel-iommu with interrupt remapping, the NIC created
    with iommu_platform=on. The first stays pc with no IOMMU."""
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    pc, vtd = (tree["tmp"] / "stub.log").read_text().splitlines()
    assert "-machine pc " in pc and "iommu" not in pc
    assert "-machine q35,kernel-irqchip=split " in vtd
    assert "-device intel-iommu,intremap=on,eim=on " in vtd
    # before the PCI devices it translates
    assert vtd.index("intel-iommu") < vtd.index("virtio-blk-pci")
    assert ("virtio-net-pci,netdev=net0,romfile=,disable-legacy=on,rx_queue_size=1024,iommu_platform=on"
            in vtd)
    # the same devices on both
    for dev in ("virtio-blk-pci,drive=initramfs,disable-legacy=on", "-device virtio-keyboard-pci",
                "-device nvme,serial=harland-msix", "-netdev user,id=net0"):
        assert dev in pc and dev in vtd, dev


@pytest.mark.integration
@pytest.mark.parametrize(
    "drop, want",
    [
        (IR_ON, "VT-d interrupt remapping did not come on"),
        (TE_ON, 'no "[vtd] translation on"'),
        (NET_PLATFORM, "did not negotiate VIRTIO_F_ACCESS_PLATFORM"),
    ],
    ids=["no-interrupt-remapping", "no-translation", "nic-without-bit-33"],
)
def test_translating_boot_check_missing_fails(tree, drop, want):
    r = _run(tree, PASSED, env_extra={"FAKE_SERIAL_VTD": VTD_OK.replace(drop, "")})
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout


@pytest.mark.integration
def test_translating_boot_keeps_every_device_check(tree):
    """A check that fails only on the translating boot fails the script: the
    storage, NVMe and NIC assertions run on both boots."""
    r = _run(tree, PASSED.replace(blk_waits(), ""),
             env_extra={"FAKE_SERIAL_VTD": VTD_OK.replace(blk_waits(), "")})
    assert r.returncode == 1
    # both boots report it, each under its own header
    assert r.stdout.count("no virtio-blk MSI-X read check logged") == 2
    assert "===== msix boot (pc) =====" in r.stdout and "===== msix boot (vtd) =====" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize("drop", [DHCP_OK, TX_BURST_OK, NIC_ON, interrupts(8), NET_MODERN, RX_CAPPED],
                         ids=["no-dhcp", "no-burst", "no-msix", "no-interrupts", "legacy", "queue-not-capped"])
def test_translating_boot_keeps_every_nic_check(tree, drop):
    """AGAST #4735: the NIC checks hold through the ring-1 driver: a lease,
    the burst, MSI-X on with interrupts delivered, modern, RX capped."""
    r = _run(tree, PASSED, env_extra={"FAKE_SERIAL_VTD": VTD_OK.replace(drop, "")})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "===== msix boot (vtd) =====" in r.stdout.split("FAIL:")[0]


@pytest.mark.integration
def test_translation_claimed_on_pc_fails(tree):
    r = _run(tree, PASSED + TE_ON)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "on the pc machine, which has no IOMMU" in r.stdout


@pytest.mark.integration
def test_pci_left_port_io_without_an_mcfg_fails(tree):
    r = _run(tree, PASSED.replace(PCI_PORT_IO, ""))
    assert r.returncode == 1, r.stdout + r.stderr
    assert 'FAIL: no "[pci] no MCFG: segment 0 only, port I/O" on the pc machine' in r.stdout


@pytest.mark.integration
def test_no_verdict_before_the_timeout_fails(tree):
    r = _run(tree, NVME_TABLE + NIC_ON + interrupts(8))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "did not report ALL TESTS PASSED" in r.stdout


# --------------------------------------------------------------------------
# NVMe in MSI-X mode (AGAST #3630)
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_nvme_interrupts_pass(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: NVMe is in MSI-X mode" in r.stdout
    assert "PASS: NVMe delivered 5 MSI-X interrupts, 3 commands waited for theirs, none missed" in r.stdout
    assert "PASS: NVMe idle interrupt wait slept: halted 1 times in one watchdog round" in r.stdout
    # The script computed the pattern's fingerprint itself and it matched
    assert f"PASS: NVMe read LBAs 32568-32767 under MSI-X (fnv1a={NVME_FNV})" in r.stdout


@pytest.mark.integration
def test_nvme_commands_that_never_halted_still_pass(tree):
    """Every command's interrupt beat its wait's first check (H = 0): legal,
    the idle wait still proves the wait sleeps (AGAST #4246)"""
    serial = (NVME_TABLE + MODERN_OK + NIC_ON + interrupts(8) + NVME_ON + NVME_READ
              + nvme_interrupts(5) + r"[msix] nvme waits halted: 0\n" + nvme_idle(1) + WAITS_OK
              + NIC_REFUSED + SUITE_PASSED)
    r = _run(tree, serial)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: NVMe idle interrupt wait slept" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "nvme, want",
    [
        # Still polled: no table programmed
        (NVME_READ + nvme_interrupts(5), "NVMe did not come up in MSI-X mode"),
        # Entries programmed but nothing delivered (masked, or no IEN on the CQ)
        (NVME_ON + NVME_READ + nvme_interrupts(0), "NVMe MSI-X interrupt counter is 0, want > 0"),
        (NVME_ON + NVME_READ, "NVMe MSI-X interrupt counter is missing"),
        # Some completions only seen by polling: e.g. the I/O CQ without IEN
        (NVME_ON + NVME_READ + nvme_interrupts(2, 3), "3 NVMe completions arrived without an interrupt"),
        # Interrupts delivered but the driver never waited for one: still polled
        (NVME_ON + NVME_READ + nvme_interrupts(5, 0, 0), "no NVMe command waited for its MSI-X interrupt"),
        # The idle wait was not run or logged
        (NVME_ON + NVME_READ + nvme_interrupts(5) + NVME_HALTED, "no NVMe idle interrupt wait logged"),
        # The idle wait spun on the counter instead of sleeping in hlt...
        (NVME_ON + NVME_READ + nvme_interrupts(5) + nvme_idle(0), "NVMe idle interrupt wait never halted"),
        # ...or spun while still counting its rounds as hlts
        (NVME_ON + NVME_READ + nvme_interrupts(5) + nvme_idle(550028),
         "NVMe idle interrupt wait halted 550028 times (> 64)"),
        # The read under MSI-X failed or returned the wrong data
        (NVME_ON + nvme_interrupts(5), "no NVMe read under MSI-X"),
        (NVME_ON + r"[msix] nvme harland-msix nsid 1: LBA 32568-32767 read failed\n" + nvme_interrupts(5),
         "no NVMe read under MSI-X"),
        (NVME_ON + r"[msix] nvme harland-msix nsid 1: LBA 32568-32767 fnv1a=12345\n" + nvme_interrupts(5),
         f"want fnv1a={NVME_FNV}"),
    ],
    ids=["polled", "zero-interrupts", "no-counter", "completions-without-interrupt", "never-waited",
         "no-idle-wait", "idle-never-halted", "idle-spun-counting", "no-read", "read-failed", "wrong-data"],
)
def test_nvme_msix_check_fails(tree, nvme, want):
    serial = NVME_TABLE + MODERN_OK + NIC_ON + interrupts(8) + nvme + SUITE_PASSED
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout, r.stdout


# --------------------------------------------------------------------------
# virtio-blk / virtio-input on MSI-X, waits that sleep (AGAST #3631)
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_virtio_waits_pass(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS: virtio-blk delivered 17 MSI-X interrupts, 8 requests waited for theirs" in r.stdout
    assert "PASS: virtio-input is in MSI-X mode" in r.stdout
    assert "PASS: virtio-net RX waited on its vector 880 times, halted 880" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "waits, want",
    [
        (BLK_ON + INPUT_ON + blk_waits() + net_rx_waits(),
         "virtio-blk was not driven over the modern (MMIO) transport"),
        (BLK_MODERN + INPUT_ON + blk_waits() + net_rx_waits(),
         "virtio-blk did not come up in MSI-X mode"),
        # Requests polled although the vector fired
        (BLK_MODERN + BLK_ON + INPUT_ON + blk_waits(waited=0) + net_rx_waits(),
         "no virtio-blk request waited"),
        (BLK_MODERN + BLK_ON + INPUT_ON + blk_waits(data="DIFFERENT") + net_rx_waits(),
         "returned data: DIFFERENT"),
        (BLK_MODERN + BLK_ON + blk_waits() + net_rx_waits(),
         "virtio-input did not come up in MSI-X mode"),
        # The DHCP window back on a fixed delay
        (BLK_MODERN + BLK_ON + INPUT_ON + blk_waits() + net_rx_waits(0, 0),
         "never waited on the RX vector"),
        # Waits that spin on the counter instead of hlt
        (BLK_MODERN + BLK_ON + INPUT_ON + blk_waits() + net_rx_waits(880, 0),
         "never halted: they spin"),
    ],
    ids=["blk-legacy", "blk-polled", "blk-never-waited", "blk-wrong-data", "input-polled",
         "net-no-rx-wait", "net-rx-spins"],
)
def test_virtio_wait_check_fails(tree, waits, want):
    serial = NVME_TABLE + MODERN_OK + NIC_ON + interrupts(8) + NVME_OK + waits + SUITE_PASSED
    r = _run(tree, serial)
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout, r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "vtd, want",
    [
        (VTD_OK.replace(NIC_DOMAIN, ""), "the NIC got no private DMA domain before its bus master"),
        (VTD_OK.replace(TE_ON, TE_ON.replace("1 requester(s) held", "0 requester(s) held")),
         "was not held out of the identity domain"),
        (VTD_OK.replace(NIC_FAULT, ""), "no fault record with the NIC's source ID (0000:00:04.0)"),
        (VTD_OK.replace(NIC_FAULT, NIC_FAULT.replace("ID 0000:00:04.0", "ID 0000:00:05.0")),
         "no fault record with the NIC's source ID (0000:00:04.0)"),
        (VTD_OK.replace(NIC_FAULT_RECORD, ""), "was not logged from the unit"),
        (VTD_OK.replace(NIC_DMA, ""), "no device DMA into a granted page"),
        (VTD_OK.replace(DMA_RUN_POOL, DMA_RUN_POOL.replace("in domain 2", "in domain 1")), "not its private domain 2"),
        (VTD_OK.replace(NIC_DMA, NIC_DMA.replace("IOVA 68719507456", "IOVA 29048832")), "below the private IOVA base"),
        (VTD_OK.replace(DMA_RUN_POOL, ""), "is in no run DrvDmaAlloc granted the driver"),
        (VTD_OK.replace(NIC_ALLOWED, ""), "net_ring1_allowed is false on the translating boot"),
        # the pre-cutover verdict: the owner stayed in the kernel
        (VTD_OK.replace(NIC_ALLOWED, NIC_ALLOWED.replace("the owner is /bin/virtio-net", "the owner stays in the kernel")),
         "net_ring1_allowed is false on the translating boot"),
    ],
    ids=["no-domain", "not-held", "no-fault", "fault-from-another-source", "no-unit-record",
         "no-device-dma", "dma-in-another-domain", "dma-at-a-ram-address", "dma-outside-the-runs",
         "ring1-not-allowed", "owner-in-the-kernel"],
)
def test_nic_private_domain_check_fails(tree, vtd, want):
    """AGAST #4724: each claim of the NIC's private domain is checked on the
    translating boot."""
    r = _run(tree, PASSED, env_extra={"FAKE_SERIAL_VTD": vtd})
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout


@pytest.mark.integration
def test_nic_private_domain_passes_on_the_translating_boot(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ("PASS: the NIC DMA'd a frame into granted IOVA 0x1000007800 (domain 2, the driver's DrvDmaAlloc run "
            "at 0x1000007000)") in r.stdout
    assert "PASS: no IOMMU: the NIC stays on physical addresses" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "pc, want",
    [
        (PASSED + NIC_DOMAIN, "a private NIC DMA domain on the pc machine"),
        (PASSED.replace(NIC_REFUSED, ""), 'no "[nic-dma] ring-1 owner refused" on the pc machine'),
    ],
    ids=["domain-on-pc", "no-refusal-on-pc"],
)
def test_nic_private_domain_on_pc_fails(tree, pc, want):
    r = _run(tree, pc)
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout


# --------------------------------------------------------------------------
# The cutover: the ring-1 driver owns the NIC on the translating boot
# (AGAST #4735, RING1_DRIVER.md sections 8-9)
# --------------------------------------------------------------------------


@pytest.mark.integration
def test_ring1_owner_passes_on_the_translating_boot(tree):
    r = _run(tree, PASSED)
    assert r.returncode == 0, r.stdout + r.stderr
    vtd = r.stdout.split("===== msix boot (vtd) =====")[1]
    assert "PASS: the kernel spawned /bin/virtio-net and it parked with generation 2 published" in vtd
    assert "PASS: the ring-1 driver brought the NIC up" in vtd
    assert "PASS: virtio_net_init did not run: the ring-1 driver is the NIC's only owner" in vtd
    assert "PASS: the ring-1 driver parked 41 times in DrvIrqWait" in vtd
    # the in-kernel owner's RX-wait check is the pc run's alone
    assert "RX waited on its vector" not in vtd
    assert "PASS: virtio-net RX waited on its vector 880 times, halted 880" in r.stdout


@pytest.mark.integration
@pytest.mark.parametrize(
    "vtd, want",
    [
        (VTD_OK.replace(RING1_PARKED, ""), "/bin/virtio-net was not spawned, or did not park"),
        (VTD_OK.replace(RING1_PARKED, RING1_PARKED.replace("generation 2", "generation 0")),
         "/bin/virtio-net was not spawned, or did not park"),
        (VTD_OK.replace(DRIVER_UP, ""), 'no "[virtio-net] up: MAC published"'),
        # both owners on one boot
        (VTD_OK.replace(DRIVER_UP, DRIVER_UP + KERNEL_NETDEV), "ran beside the ring-1 driver"),
        (VTD_OK.replace(DRIVER_UP, DRIVER_UP + KERNEL_NIC_UP), "ran beside the ring-1 driver"),
        # the park counter replaces halted > 0
        (VTD_OK.replace(driver_parks(41), ""), "no ring-1 driver park count logged"),
        (VTD_OK.replace(driver_parks(41), driver_parks(0)), "never parked in DrvIrqWait"),
        (VTD_OK.replace(driver_parks(41), net_rx_waits()), "no ring-1 driver park count logged"),
    ],
    ids=["not-spawned", "unpublished", "no-driver-banner", "netdev-banner-too", "kernel-banner-too",
         "no-park-count", "never-parked", "halts-instead-of-parks"],
)
def test_ring1_owner_check_fails(tree, vtd, want):
    r = _run(tree, PASSED, env_extra={"FAKE_SERIAL_VTD": vtd})
    assert r.returncode == 1, r.stdout + r.stderr
    assert want in r.stdout


@pytest.mark.integration
def test_ring1_checks_are_the_translating_boots_alone(tree):
    """The pc run keeps the in-kernel owner: its banners are not a failure
    there, and it needs no park count."""
    r = _run(tree, PASSED + KERNEL_NETDEV + KERNEL_NIC_UP)
    assert r.returncode == 0, r.stdout + r.stderr
    pc = r.stdout.split("===== msix boot (vtd) =====")[0]
    assert "PASS: the ring-1 driver" not in pc and "ring-1 driver park" not in pc


@pytest.mark.unit
def test_the_boot_images_carry_the_driver():
    """/bin/virtio-net comes from harland/system, which the shared package
    list names: the script reads that list instead of its own."""
    script = (REPO / MSIX_SCRIPT).read_text()
    assert "initramfs.pkgs" in script
    assert 'USER_PKGS="indium rzsh prism"' not in script
