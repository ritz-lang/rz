"""A timed-out virtio-blk request no longer poisons every later request (AGAST #4139).

drivers/virtio/blk.ritz runs one request at a time per device, in that
device's single DMA page (header, status byte, data). When the wait for the
used ring timed out, virtio_blk_read/virtio_blk_write returned -3 and left the
request's three descriptors on the ring. The device still owned that request.
The next call then:

  * rewrote the header, status byte and (for a write) the data in the page the
    device was about to read, so a late write could land on the wrong sector
    with the wrong data;
  * submitted its own request and, as soon as the old one completed, took the
    stale used entry for its own, read its own status byte (still 0xFF) and
    freed its own descriptors while the device still held them.

From then on every request was one behind: on skronk one "Read timeout" gave
~15 "Read error: 255" and the initramfs load panicked.

Now a timed-out request stays recorded as in flight. The next call on that
device first waits for it (same deadline) and frees its descriptors. Only then
does it touch the DMA page. If it still hasn't completed, the call returns -3
without submitting anything.

The test compiles the real blk.ritz and virtio/common.ritz into a host
program. The io stand-in is a legacy virtio-blk device behind port I/O: a
notify (outw to QUEUE_NOTIFY) completes the request at once, or, while the
test holds the device, leaves it until fake_dev_service(). Exit codes name the
failed claim (CHECKS). The QEMU boot (tools/test_tier1_boot.sh) is the runtime
check of the healthy path.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"

# --- stand-ins ----------------------------------------------------------------

# The real serial.ritz drives the UART through port I/O; only its StrView
# is needed here.
SERIAL_STUB = """\
pub struct StrView
    ptr: *u8
    len: i64
"""

# The kernel logs through klog (AGAST #1885); these have its signatures and
# do nothing.
KLOG_STUB = """\
import serial { StrView }

pub fn klog(s: StrView) -> i32
    return 0

pub fn klog_cstr(s: *u8) -> i32
    return 0

pub fn klog_dec(n: i64) -> i32
    return 0

pub fn klog_udec(n: u64) -> i32
    return 0

pub fn klog_hex(n: u64) -> i32
    return 0

pub fn klog_hex_width(n: u64, width: i32) -> i32
    return 0

pub fn klog_hex_prefix(n: u64) -> i32
    return 0
"""

# Block device 0 is a legacy virtio device with its I/O BAR at 0xC000.
PCI_STUB = """\
pub const VIRTIO_DEVICE_BLOCK: u16 = 0x1001
pub const VIRTIO_DEVICE_INPUT: u16 = 0x1052
pub const PCI_CAP_VENDOR: u8 = 0x09

pub struct PciDevice
    segment: u16
    bus: u8
    device: u8
    function: u8
    vendor_id: u16
    device_id: u16
    class_code: u8
    subclass: u8
    prog_if: u8
    revision: u8
    header_type: u8
    interrupt_line: u8
    interrupt_pin: u8
    bar: [6]u64
    bar_size: [6]u64
    bar_is_io: [6]u8
    bar_is_64bit: [6]u8

var g_dev: PciDevice

pub fn pci_find_virtio_nth(virtio_device_id: u16, n: i32) -> *PciDevice
    if n != 0
        return 0 as *PciDevice
    g_dev.bar[0] = 0xC000
    g_dev.bar_is_io[0] = 1
    @g_dev

pub fn pci_find_virtio(virtio_device_id: u16) -> *PciDevice
    pci_find_virtio_nth(virtio_device_id, 0)

pub fn pci_enable_bus_master(dev: *PciDevice)
    return

# vio_init_device_isolated (the NIC's, #4724) and the window record's
# requester: never reached on blk or input.
pub fn pci_disable_bus_master(dev: *PciDevice)
    return

pub fn pci_dev_sid(dev: *PciDevice) -> u32
    0

pub fn pci_enable_memory(dev: *PciDevice)
    return

pub fn pci_enable_io(dev: *PciDevice)
    return

pub fn pci_find_capability_nth(dev: *PciDevice, cap_id: u8, n: i32) -> u8
    0

pub fn pci_dev_read_config8(dev: *PciDevice, offset: u8) -> u8
    0

# vio_find_mmio_caps reads the MSI-X capability when it records a window
# (#4720); the fake device is legacy, so it is never reached.
pub fn pci_find_capability(dev: *PciDevice, cap_id: u8) -> u8
    0

pub fn pci_dev_read_config16(dev: *PciDevice, offset: u8) -> u16
    0

pub fn pci_dev_read_config32(dev: *PciDevice, offset: u8) -> u32
    0
"""

NVME_STUB = """\
pub struct NvmeNamespace
    nsid: u32

pub fn nvme_probe() -> i32
    0

pub fn nvme_get_namespace(n: i32) -> *NvmeNamespace
    0 as *NvmeNamespace

pub fn nvme_ns_sectors(ns: *NvmeNamespace) -> u64
    0

pub fn nvme_ns_read(ns: *NvmeNamespace, sector: u64, count: u32, buf: *u8) -> i32
    -1

pub fn nvme_ns_write(ns: *NvmeNamespace, sector: u64, count: u32, buf: *u8) -> i32
    -1
"""

# Physical == virtual, as in the kernel's identity map: pages come from a
# page-aligned slice of .bss, consecutive calls give contiguous pages (the
# ring allocator in common.ritz relies on that).
PMM_STUB = """\
pub const PAGE_SIZE: u64 = 4096

var g_mem: [65536]u8
var g_next: u64 = 0

pub fn pmm_alloc_page() -> u64
    let base: u64 = @g_mem[0] as u64
    if g_next == 0
        g_next = (base + 4095) & (0xFFFFFFFFFFFFFFFF ^ 4095)
    if g_next + 4096 > base + 65536
        return 0
    let p: u64 = g_next
    g_next = g_next + 4096
    p

pub fn pmm_free_page(addr: u64) -> i32
    0
"""

HEAP_STUB = """\
var g_arena: [8192]u8
var g_top: u64 = 0

pub fn kalloc(size: u64) -> *u8
    let n: u64 = (size + 15) & 18446744073709551600
    if g_top + n > 8192
        return 0 as *u8
    let p: *u8 = @g_arena[0] + g_top
    g_top = g_top + n
    p

pub fn kfree(ptr: *u8) -> i32
    0
"""

# The legacy transport keeps its registers as raw physical addresses; queue
# pages are reached through the physmap, the identity here (AGAST #1878).
VMM_STUB = """\
pub fn vmm_virt_to_phys(vaddr: u64) -> u64
    vaddr

pub fn vmm_map_mmio(paddr: u64, size: u64) -> u64
    0

pub fn phys_to_virt(paddr: u64) -> u64
    paddr
"""

# The device. Legacy registers at 0xC000 (virtio 1.1 §4.1.4.8): features 0,
# queues 0 and 1 have QNUM entries, capacity CAPACITY sectors. Reading sector
# S gives byte i = (S * 7 + i) & 255; a write is logged (count, last sector,
# its first byte). The rings are where common.ritz puts them for the PFN it
# wrote (the last queue set up).
#
# MSI-X (AGAST #3631), off unless fake_msix_present(true): once the driver
# enables it (the drivers/msix.ritz stand-in calls fake_msix_enable) the
# config vector and the selected queue's vector sit at 20 and 22 and the
# device config moves to 24. A completion then "interrupts": the queue's
# table entry's vector is counted. With fake_dev_irq_only(true) the device
# completes a request only while the CPU sleeps in sti_hlt, as a real one
# whose interrupt wakes a hlt: a driver that spins instead never sees it.
# The CPU's IF flag, sti_hlt and the LAPIC watchdog / wait queue that
# drivers/irq_wait.ritz calls (extern) are stand-ins here too; the watchdog
# expires on its WD_CHECKS-th check.
IO_STUB = """\
const BASE: u16 = 0xC000
const QNUM: u16 = 16
const CAPACITY: u32 = 64
const NO_VECTOR: u16 = 0xFFFF
const WD_CHECKS: i32 = 3

var g_msix_present: bool = false
var g_msix_on: bool = false
var g_entry_vec: [4]u8
var g_cfg_vec: u16 = 0xFFFF
var g_qvec: [2]u16
var g_irqs: [16]u64
var g_irq_only: bool = false
var g_if: bool = false
var g_hlts: u64 = 0
var g_wd_checks: i32 = 0

var g_status: u8 = 0
var g_qsel: u16 = 0
var g_pfn: u32 = 0
var g_hold: bool = false
var g_last_avail: u16 = 0
var g_writes: i32 = 0
var g_write_sector: u64 = 0
var g_write_byte: u8 = 0

fn ring() -> u64
    (g_pfn as u64) * 4096

fn avail_ring() -> u64
    ring() + (QNUM as u64) * 16

fn used_ring() -> u64
    (avail_ring() + 4 + (QNUM as u64) * 2 + 4095) & (0xFFFFFFFFFFFFFFFF ^ 4095)

fn desc(i: u16) -> u64
    ring() + (i as u64) * 16

# Carry out the chain at `head`: header -> data -> status.
fn serve(head: u16)
    let d0: u64 = desc(head)
    let hdr: u64 = *(d0 as *u64)
    let d1: u64 = desc(*((d0 + 14) as *u16))
    let data: u64 = *(d1 as *u64)
    let len: u32 = *((d1 + 8) as *u32)
    let d2: u64 = desc(*((d1 + 14) as *u16))
    let status: u64 = *(d2 as *u64)
    let req_type: u32 = *(hdr as *u32)
    let sector: u64 = *((hdr + 8) as *u64)
    if req_type == 0
        var i: u64 = 0
        while i < (len as u64)
            *((data + i) as *u8) = ((sector * 7 + i) & 255) as u8
            i = i + 1
    else
        g_writes = g_writes + 1
        g_write_sector = sector
        g_write_byte = *(data as *u8)
    *(status as *u8) = 0

# Interrupt for queue 0's completion: count its entry's vector, if any.
fn raise_queue_irq()
    if not g_msix_on or g_qvec[0] == NO_VECTOR or g_qvec[0] > 3
        return
    let v: u8 = g_entry_vec[g_qvec[0] as i32]
    if v >= 64 and v < 80
        g_irqs[(v - 64) as i32] = g_irqs[(v - 64) as i32] + 1

# Complete every request the driver has made available, in order.
pub fn fake_dev_service() -> i32
    let avail_idx: u16 = *((avail_ring() + 2) as *u16)
    while g_last_avail != avail_idx
        let head: u16 = *((avail_ring() + 4 + ((g_last_avail % QNUM) as u64) * 2) as *u16)
        serve(head)
        let uidx: u16 = *((used_ring() + 2) as *u16)
        let elem: u64 = used_ring() + 4 + ((uidx % QNUM) as u64) * 8
        *(elem as *u32) = head as u32
        *((elem + 4) as *u32) = 1
        *((used_ring() + 2) as *u16) = uidx + 1
        g_last_avail = g_last_avail + 1
        raise_queue_irq()
    0

# Requests made available and not yet completed.
pub fn fake_dev_pending() -> u16
    *((avail_ring() + 2) as *u16) - g_last_avail

pub fn fake_dev_hold(hold: bool) -> i32
    g_hold = hold
    0

pub fn fake_dev_irq_only(on: bool) -> i32
    g_irq_only = on
    0

pub fn fake_msix_present(on: bool) -> i32
    g_msix_present = on
    g_qvec[0] = NO_VECTOR
    g_qvec[1] = NO_VECTOR
    0

pub fn fake_msix_is_present() -> bool
    g_msix_present

pub fn fake_msix_enable() -> i32
    g_msix_on = true
    0

pub fn fake_msix_set_entry(entry: u16, vector: u8) -> i32
    if entry < 4
        g_entry_vec[entry as i32] = vector
    0

pub fn fake_msix_entry_vector(entry: u16) -> u8
    g_entry_vec[entry as i32]

pub fn fake_msix_count(vector: u8) -> u64
    if vector >= 64 and vector < 80
        return g_irqs[(vector - 64) as i32]
    0

pub fn fake_cfg_vector() -> u16
    g_cfg_vec

pub fn fake_queue_vector(q: u16) -> u16
    g_qvec[q as i32]

pub fn fake_cpu_halts() -> u64
    g_hlts

pub fn fake_cpu_set_if(on: bool) -> i32
    g_if = on
    0

pub fn interrupts_enabled() -> bool
    g_if

pub fn enable_interrupts() -> i32
    g_if = true
    0

pub fn disable_interrupts() -> i32
    g_if = false
    0

# sti;hlt: a device holding back its completion for an interrupt delivers
# it now (and the interrupt wakes the hlt).
pub fn sti_hlt() -> i32
    g_if = true
    g_hlts = g_hlts + 1
    if g_irq_only and not g_hold
        fake_dev_service()
    0

pub fn lapic_watchdog_arm(ticks: u32)
    g_wd_checks = 0

pub fn lapic_watchdog_expired() -> bool
    g_wd_checks = g_wd_checks + 1
    g_wd_checks >= WD_CHECKS

pub fn lapic_watchdog_stop()
    pass

# The wait queue: parking is possible only after fake_waitq_allow(true);
# a park counts and, like the woken process, sees the interrupt delivered.
var g_can_park: bool = false
var g_parks: u64 = 0

pub fn fake_waitq_allow(on: bool) -> i32
    g_can_park = on
    0

pub fn fake_waitq_parks() -> u64
    g_parks

pub fn waitq_can_park() -> bool
    g_can_park

pub fn waitq_park() -> i32
    g_parks = g_parks + 1
    if g_irq_only and not g_hold
        fake_dev_service()
    0

pub fn fake_dev_writes() -> i32
    g_writes

pub fn fake_dev_write_sector() -> u64
    g_write_sector

pub fn fake_dev_write_byte() -> u8
    g_write_byte

# blk.ritz waits on a TSC deadline (AGAST #4078). A held request must time out
# at once, so this clock jumps 1e9 cycles per read: a deadline of N cycles
# passes after about N / 1e9 polls, however fast the host runs.
var g_tsc: u64 = 0

pub fn rdtsc() -> u64
    g_tsc = g_tsc + 1000000000
    g_tsc

pub fn outb(port: u16, value: u8) -> i32
    if port == BASE + 18
        g_status = value
    0

pub fn inb(port: u16) -> u8
    if port == BASE + 18
        return g_status
    0

pub fn outw(port: u16, value: u16) -> i32
    if port == BASE + 14
        g_qsel = value
    if port == BASE + 16 and not g_hold and not g_irq_only
        fake_dev_service()
    if g_msix_on and port == BASE + 20
        g_cfg_vec = value
    if g_msix_on and port == BASE + 22 and g_qsel < 2
        g_qvec[g_qsel as i32] = value
    0

pub fn inw(port: u16) -> u16
    if port == BASE + 12 and g_qsel < 2
        return QNUM
    if g_msix_on and port == BASE + 20
        return g_cfg_vec
    if g_msix_on and port == BASE + 22 and g_qsel < 2
        return g_qvec[g_qsel as i32]
    0

pub fn outl(port: u16, value: u32) -> i32
    if port == BASE + 8
        g_pfn = value
    0

pub fn inl(port: u16) -> u32
    if not g_msix_on and port == BASE + 20
        return CAPACITY
    if g_msix_on and port == BASE + 24
        return CAPACITY
    0
"""

# drivers/msix.ritz: the device's table lives in the io stand-in.
MSIX_STUB = """\
import drivers.pci { PciDevice }
import io { fake_msix_is_present, fake_msix_enable, fake_msix_set_entry, fake_msix_count }

pub const PCI_CAP_MSIX: u8 = 0x11

pub struct MsixInfo
    dev: *PciDevice
    cap: u8
    table_bar: u8
    table_size: u16
    table_offset: u32
    table_virt: u64

var g_msix_next: u8 = 64

pub fn msix_probe(dev: *PciDevice, out: *MsixInfo) -> i32
    (*out).dev = dev
    if not fake_msix_is_present()
        return -1
    (*out).table_size = 4
    0

pub fn msix_enable(info: *MsixInfo) -> i32
    fake_msix_enable()
    (*info).table_virt = 1
    0

pub fn msix_vector_alloc() -> u8
    let v: u8 = g_msix_next
    g_msix_next = g_msix_next + 1
    v

pub fn msix_set_entry(info: *MsixInfo, entry: u16, vector: u8) -> i32
    fake_msix_set_entry(entry, vector)
    0

pub fn msix_vector_count(vector: u8) -> u64
    fake_msix_count(vector)
"""

STUBS = {
    "serial.ritz": SERIAL_STUB,
    "klog.ritz": KLOG_STUB,
    "io.ritz": IO_STUB,
    "drivers/pci.ritz": PCI_STUB,
    "drivers/nvme/nvme.ritz": NVME_STUB,
    "drivers/msix.ritz": MSIX_STUB,
    "mm/pmm.ritz": PMM_STUB,
    "mm/heap.ritz": HEAP_STUB,
    "mm/vmm.ritz": VMM_STUB,
}
REAL = ["drivers/virtio/blk.ritz", "drivers/virtio/common.ritz",
        "drivers/virtio/vmsix.ritz", "drivers/irq_wait.ritz",
        "drivers/virtio/window.ritz"]
# The virtqueue and feature negotiation the drivers call (AGAST #4732): the
# real virtio_abi package, at virtio_abi/<module>.ritz in the tree.
VIRTIO_ABI_SRC = KERNEL_SRC.parents[1] / "virtio_abi" / "src"
VIRTIO_ABI = {f"virtio_abi/{name}.ritz": VIRTIO_ABI_SRC / f"{name}.ritz"
              for name in ("virtq", "features")}

# Exit code -> the claim that failed.
CHECKS = {
    1: "virtio_blk_init found no device",
    2: "a healthy read failed",
    3: "a healthy read returned the wrong data",
    10: "a read the device holds did not time out (-3)",
    11: "after a timed-out read completed late, the next read did not wait for "
        "it: it took the stale completion as its own (status 255 -> -5)",
    12: "once the device answers again, a read failed: the driver is still "
        "out of step with the used ring",
    13: "once the device answers again, a read returned another request's data",
    14: "descriptors leaked across the timeouts",
    20: "a write the device holds did not time out (-3)",
    21: "a write while the previous one is in flight did not return -3",
    22: "a read while a write is in flight did not return -3",
    23: "a request was submitted while the previous one was still in flight",
    24: "the late write did not land as issued (sector 20, 0xAA): its DMA page "
        "was reused while the device still owned it",
    25: "a write after the late one completed failed",
    26: "the write after the late one did not land as issued (sector 21, 0xBB)",
    27: "descriptors leaked across the write timeouts",
}

PROGRAM = """\
import ritzlib.option
import drivers.virtio.blk { VirtioBlkDevice, virtio_blk_init, virtio_blk_read, virtio_blk_write }
import virtio_abi.virtq { Virtqueue }
import io { fake_dev_service, fake_dev_pending, fake_dev_hold, fake_dev_writes, fake_dev_write_sector, fake_dev_write_byte }

var g_buf: [512]u8

fn holds_sector(sector: u64) -> bool
    var i: u64 = 0
    while i < 512
        if g_buf[i as i32] != ((sector * 7 + i) & 255) as u8
            return false
        i = i + 1
    true

fn fill(b: u8)
    var i: i32 = 0
    while i < 512
        g_buf[i] = b
        i = i + 1

fn main() -> i32
    let dev: *VirtioBlkDevice = virtio_blk_init()
    if dev == 0 as *VirtioBlkDevice
        return 1
    let vq: *Virtqueue = (*dev).request_queue
    let num: u16 = (*vq).num
    let buf: *u8 = @g_buf[0]
    if virtio_blk_read(dev, 3, 1, buf) != 0
        return 2
    if not holds_sector(3)
        return 3

    # A read the device answers only after the driver gave up.
    fake_dev_hold(true)
    if virtio_blk_read(dev, 5, 1, buf) != -3
        return 10
    fake_dev_service()
    # The device is still slow: this one times out too, but on its own.
    if virtio_blk_read(dev, 6, 1, buf) != -3
        return 11
    fake_dev_service()
    fake_dev_hold(false)
    var s: u64 = 7
    while s < 12
        if virtio_blk_read(dev, s, 1, buf) != 0
            return 12
        if not holds_sector(s)
            return 13
        s = s + 1
    if (*vq).free_count != num
        return 14

    # A write the device holds: its page must stay as issued until it's done.
    fake_dev_hold(true)
    fill(0xAA)
    if virtio_blk_write(dev, 20, 1, buf) != -3
        return 20
    fill(0xBB)
    if virtio_blk_write(dev, 21, 1, buf) != -3
        return 21
    if virtio_blk_read(dev, 22, 1, buf) != -3
        return 22
    if fake_dev_pending() != 1
        return 23
    fake_dev_service()
    if fake_dev_writes() != 1 or fake_dev_write_sector() != 20 or fake_dev_write_byte() != 0xAA
        return 24
    fake_dev_hold(false)
    fill(0xBB)
    if virtio_blk_write(dev, 21, 1, buf) != 0
        return 25
    if fake_dev_writes() != 2 or fake_dev_write_sector() != 21 or fake_dev_write_byte() != 0xBB
        return 26
    if (*vq).free_count != num
        return 27
    0
"""


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(tmp_path, src, real=REAL):
    """Compile `src` and each module of the stub tree (own object each), link, run."""
    tree = tmp_path / "tree"
    sources = dict(STUBS)
    for rel in real:
        sources[rel] = (KERNEL_SRC / rel).read_text()
    for rel, path in VIRTIO_ABI.items():
        sources[rel] = path.read_text()
    for rel, text in sources.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
    # The kernel is built by ritz0 (build.py --no-runtime), so only ritz0 runs.
    objs = [str(_compile(tmp_path, tree / rel, rel[:-5].replace("/", "_"), ("--no-runtime",)))
            for rel in sources]
    (tmp_path / "t.ritz").write_text(src)
    objs.insert(0, str(_compile(tmp_path, tmp_path / "t.ritz", "t")))
    exe = tmp_path / "t"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                            "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def test_a_timed_out_request_is_drained_before_its_dma_page_is_reused(tmp_path):
    rc = _run(tmp_path, PROGRAM)
    assert rc == 0, f"check {rc}: {CHECKS.get(rc, 'crashed or unknown exit code')}"
