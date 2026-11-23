"""virtio-blk and virtio-input signal through MSI-X; blk waits sleep on it (AGAST #3631).

#1852 put virtio-net on MSI-X, but virtio-blk and virtio-input stayed on
(polled) INTx, and a block request spun on the used ring until its TSC
deadline. Now:

  * both drivers give their device one MSI-X vector (drivers/virtio/vmsix.ritz):
    table entry 0, programmed with an allocated vector, named as the queue's
    vector (queue_msix_vector: legacy offset 22, modern common_cfg 0x1A) and
    the config-change vector (msix_config: legacy 20, modern 0x10). On the
    legacy transport that moves the device config to offset 24, so MSI-X goes
    on before blk reads its capacity;
  * a block request issued with IF=1 sleeps on that vector between checks of
    the used ring (drivers/irq_wait.ritz, NVMe's sleep made common); one
    issued with IF=0 (boot) still polls and must not hlt. It sleeps in
    sti;hlt and never parks the process, even where the wait queue could:
    another process would reuse the disk's one DMA page mid-request.

The test compiles the real blk.ritz / input.ritz, virtio/common.ritz,
virtio/vmsix.ritz and irq_wait.ritz against the stand-ins of
test_harland_virtio_blk_timeout.py: a legacy virtio device whose MSI-X table,
IF flag and sti;hlt are simulated. In "irq-only" mode the device completes a
request only while the CPU sleeps in sti_hlt, so a driver that spins instead
times out. Exit codes name the failed claim (CHECKS). The QEMU boot
(tools/test_msix_boot.sh) checks the same on the modern transport.
"""

import pytest

from test_harland_virtio_blk_timeout import REAL, _run

pytestmark = pytest.mark.integration

BLK_CHECKS = {
    1: "virtio_blk_init found no device",
    2: "the disk did not get an MSI-X vector",
    3: "capacity read from the pre-MSI-X config offset: MSI-X went on after "
       "the config read",
    4: "the request queue was not pointed at MSI-X table entry 0",
    5: "config changes were not routed to MSI-X table entry 0",
    6: "MSI-X table entry 0 was not programmed with the disk's vector",
    10: "with IF=1 a read whose completion arrives by interrupt failed: the "
        "wait spun on the used ring instead of sleeping on the vector",
    11: "the interrupt-driven read returned the wrong data",
    12: "the interrupt-driven read never slept in sti;hlt",
    13: "the interrupt-driven read was not counted as a vector wait",
    14: "the disk's vector delivered no interrupt",
    15: "the wait parked the process: another one could reuse the disk's DMA "
        "page mid-request",
    20: "with IF=0 the read slept in sti;hlt (boot code must poll)",
    21: "with IF=0 a read whose completion needs an interrupt did not time out",
    22: "after the IF=0 timeout, a read with IF=1 failed",
    23: "after the IF=0 timeout, a read with IF=1 returned the wrong data",
    30: "a disk without MSI-X has a vector",
    31: "a disk without MSI-X failed a read",
}

BLK_PROGRAM = """\
import drivers.virtio.blk { VirtioBlkDevice, virtio_blk_init, virtio_blk_read, virtio_blk_msix_vector, virtio_blk_irq_count, virtio_blk_irq_wait_count }
import io { fake_msix_present, fake_msix_entry_vector, fake_cfg_vector, fake_queue_vector, fake_cpu_halts, fake_cpu_set_if, fake_dev_irq_only, fake_waitq_allow, fake_waitq_parks }

var g_buf: [512]u8

fn holds_sector(sector: u64) -> bool
    var i: u64 = 0
    while i < 512
        if g_buf[i as i32] != ((sector * 7 + i) & 255) as u8
            return false
        i = i + 1
    true

fn main() -> i32
    fake_msix_present(true)
    let dev: *VirtioBlkDevice = virtio_blk_init()
    if dev == 0 as *VirtioBlkDevice
        return 1
    let vec: u8 = virtio_blk_msix_vector(0)
    if vec == 0
        return 2
    if (*dev).capacity != 64
        return 3
    if fake_queue_vector(0) != 0
        return 4
    if fake_cfg_vector() != 0
        return 5
    if fake_msix_entry_vector(0) != vec
        return 6

    let buf: *u8 = @g_buf[0]
    fake_dev_irq_only(true)
    fake_cpu_set_if(true)
    fake_waitq_allow(true)
    if virtio_blk_read(dev, 3, 1, buf) != 0
        return 10
    if not holds_sector(3)
        return 11
    if fake_cpu_halts() == 0
        return 12
    if virtio_blk_irq_wait_count() != 1
        return 13
    if virtio_blk_irq_count(0) == 0
        return 14
    if fake_waitq_parks() != 0
        return 15

    fake_cpu_set_if(false)
    let halts: u64 = fake_cpu_halts()
    let r: i32 = virtio_blk_read(dev, 4, 1, buf)
    if fake_cpu_halts() != halts
        return 20
    if r != -3
        return 21
    fake_cpu_set_if(true)
    if virtio_blk_read(dev, 5, 1, buf) != 0
        return 22
    if not holds_sector(5)
        return 23
    0
"""

POLLED_PROGRAM = """\
import drivers.virtio.blk { VirtioBlkDevice, virtio_blk_init, virtio_blk_read, virtio_blk_msix_vector }
import io { fake_cpu_set_if }

var g_buf: [512]u8

fn main() -> i32
    fake_cpu_set_if(true)
    let dev: *VirtioBlkDevice = virtio_blk_init()
    if dev == 0 as *VirtioBlkDevice
        return 1
    if virtio_blk_msix_vector(0) != 0
        return 30
    if virtio_blk_read(dev, 3, 1, @g_buf[0]) != 0
        return 31
    0
"""

INPUT_CHECKS = {
    1: "virtio_input_init failed",
    2: "the input device did not get an MSI-X vector",
    3: "the event queue was not pointed at MSI-X table entry 0",
    4: "config changes were not routed to MSI-X table entry 0",
    5: "MSI-X table entry 0 was not programmed with the device's vector",
    6: "the status queue was given a vector (only the event queue signals)",
}

INPUT_PROGRAM = """\
import drivers.virtio.input { virtio_input_init, virtio_input_msix_vector }
import io { fake_msix_present, fake_msix_entry_vector, fake_cfg_vector, fake_queue_vector }

fn main() -> i32
    fake_msix_present(true)
    if virtio_input_init() != 0
        return 1
    let vec: u8 = virtio_input_msix_vector()
    if vec == 0
        return 2
    if fake_queue_vector(0) != 0
        return 3
    if fake_cfg_vector() != 0
        return 4
    if fake_msix_entry_vector(0) != vec
        return 5
    if fake_queue_vector(1) != 0xFFFF
        return 6
    0
"""

INPUT_REAL = ["drivers/virtio/input.ritz"] + [r for r in REAL if r != "drivers/virtio/blk.ritz"]


def test_blk_request_sleeps_on_its_msix_vector(tmp_path):
    rc = _run(tmp_path, BLK_PROGRAM)
    assert rc == 0, f"check {rc}: {BLK_CHECKS.get(rc, 'crashed or unknown exit code')}"


def test_blk_without_msix_still_polls(tmp_path):
    rc = _run(tmp_path, POLLED_PROGRAM)
    assert rc == 0, f"check {rc}: {BLK_CHECKS.get(rc, 'crashed or unknown exit code')}"


def test_input_event_queue_signals_msix_entry_0(tmp_path):
    rc = _run(tmp_path, INPUT_PROGRAM, real=INPUT_REAL)
    assert rc == 0, f"check {rc}: {INPUT_CHECKS.get(rc, 'crashed or unknown exit code')}"
