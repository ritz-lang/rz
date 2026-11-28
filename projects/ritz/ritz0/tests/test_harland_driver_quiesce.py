"""driver_quiesce: a ring-1 driver's death quiesces its device before its
address space goes (AGAST #4733, RING1_DRIVER.md "Driver death").

When the exiting pid is the recorded owner of a device IRQ capability (or
drops its last IRQ handle for it), the kernel, after the switch to the
kernel PML4 and before vmm_free_pml4:

1. masks the device's MSI-X entries through its own mapping;
2. writes virtio status 0 and reads it back until 0, bounded by
   VIRTIO_RESET_TIMEOUT_US (100 ms);
3. takes each DMA run of that device out of its domain and waits for the
   IOTLB; a run whose reset or invalidation was not confirmed gets
   PTE_DEVICE on its leaves and goes on dma_quarantine, never dma_free_pages;
4. invalidates the link snapshot (NetInfo is NoDev), forgets the frame
   object's registration and, for the kernel seat's driver, clears the
   seat's (ring_driver_gone);
5. (cap_retire_held_shm, right after) retires the frame object and latches
   DRIVER_GONE on the consumer.

The behaviour is the drv-quiesce boot test (postinit.ritz, stub modes
40-42). These source checks pin the order it can't observe, and the run
table's per-device take is host-tested with the real mm/dma_runs.ritz in
test_harland_dma_free.py.
"""

import re
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parents[1]
HARLAND = RITZ0_DIR.parent.parent / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
PROCESS = KERNEL_SRC / "syscall" / "runtime" / "process.ritz"
DRIVER = KERNEL_SRC / "syscall" / "runtime" / "driver.ritz"
NET = KERNEL_SRC / "syscall" / "runtime" / "net.ritz"
RING = KERNEL_SRC / "net" / "ring.ritz"
COMMON = KERNEL_SRC / "drivers" / "virtio" / "common.ritz"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"
CAP_TABLE = KERNEL_SRC / "cap" / "table.ritz"
POSTINIT = KERNEL_SRC / "postinit.ritz"
STUB = HARLAND / "kernel" / "driver_stub.s"
BOOT_SH = HARLAND / "tools" / "test_tier1_boot.sh"


def _fn_body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
    assert m, f"no fn {name}"
    return m.group(0)


@pytest.mark.unit
def test_exit_quiesces_on_the_kernel_pml4_before_anything_is_freed():
    """After the switch to the kernel PML4; before the shm retire (step 5
    comes after the reset), the capability table (it names the IRQ owner)
    and vmm_free_pml4. Its own call, beside any other exit hook."""
    body = _fn_body(PROCESS.read_text(), "sys_exit_impl")
    q = body.index("driver_quiesce(me.pid as u32, my_pml4)")
    assert body.index("vmm_switch_pml4(g_kernel_pml4)") < q
    assert q < body.index("cap_retire_held_shm(")
    assert q < body.index("cap_table_free_pid(")
    assert q < body.index("vmm_free_pml4(my_pml4)")
    assert "proc_exit_current" not in body[:q]


@pytest.mark.unit
def test_quiesce_masks_resets_invalidates_then_unpublishes():
    """Per owned device: mask, reset with readback, then each run leaves the
    domain; then the snapshot. A run is kept for the PML4's free only when
    both the reset and the invalidation were confirmed."""
    src = DRIVER.read_text()
    dev = _fn_body(src, "quiesce_device")
    mask = dev.index("msix_mask_entries(")
    reset = dev.index("device_reset(dev.reset)")
    leave = dev.index("run_left_domain(")
    assert mask < reset < leave
    assert re.search(r"let reset_ok: bool = match reset\n\s+DeviceReset\.Done => true\n\s+_ => false", dev), dev
    assert 'DeviceReset.Done => klog("0")' in dev
    # The reset is the device's kind's (AGAST #4893): virtio's status
    # readback, or the e1000e's two waits, 0 only when both succeeded.
    kinds = _fn_body(src, "device_reset")
    assert "if status == 0 then DeviceReset.Done else DeviceReset.Status(status)" in kinds
    assert re.search(r"NicReset\.E1000e\(regs\) =>\n\s+let end: E1000eReset = e1000e_reset\(regs\)\n\s+match end\n\s+E1000eReset\.Done => DeviceReset\.Done\n\s+_ => DeviceReset\.Stuck\(", kinds), kinds
    assert re.search(r"if reset_ok and left\b", dev), dev
    assert "quarantine_leaves(" in dev and "dma_quarantine_iova(" in dev
    assert "dma_free_pages" not in dev
    assert "[quiesce] pid " in dev and " status " in dev
    body = _fn_body(src, "driver_quiesce")
    assert "cap_irq_owner(" in body
    assert body.index("quiesce_device(") < body.index("driver_gone(pid)")
    obj = _fn_body(src, "driver_quiesce_object")
    assert obj.index("quiesce_device(") < obj.index("driver_gone(pid)")


@pytest.mark.unit
def test_step_4_closes_the_kernel_seat_only_for_its_own_driver():
    """Step 4 (#4731's net/ring.ritz): the snapshot goes, and when the
    dying pid is the kernel seat's driver, ring_driver_gone clears its
    registration so a parked take_rx answers NoDriver. Another driver's
    death (a blk driver, say) leaves the net seat alone."""
    body = _fn_body(DRIVER.read_text(), "driver_gone")
    assert "net_driver_quiesced(pid)" in body
    assert re.search(r"if ring_seat_driver_is\(pid\)\n\s+ring_driver_gone\(\)", body), body
    seat = _fn_body(RING.read_text(), "ring_seat_driver_is")
    assert "seat_open and seat_driver == pid as u64" in seat


@pytest.mark.unit
def test_the_snapshot_goes_and_the_frame_registration_with_it():
    body = _fn_body(NET.read_text(), "net_driver_quiesced")
    assert "snapshot_invalidate()" in body
    assert "net_frame_register(0, 0)" in body


@pytest.mark.unit
def test_reset_reads_back_within_its_own_timeout():
    """VIRTIO_RESET_TIMEOUT_US lives with the virtio code (not vtd's
    private VTD_TIMEOUT_US) and is 100 ms; the write of 0 comes before the
    reads, which stop at 0 or the deadline."""
    src = COMMON.read_text()
    assert re.search(r"^pub const VIRTIO_RESET_TIMEOUT_US: u64 = 100000\b", src, re.M)
    body = _fn_body(src, "vio_status_reset")
    assert body.index("volatile_store(reg, 0)") < body.index("vio_status_read(reg)")
    assert "volatile_load(reg)" in _fn_body(src, "vio_status_read")
    assert "deadline_after_us(VIRTIO_RESET_TIMEOUT_US)" in body
    assert "deadline_passed(" in body


@pytest.mark.unit
def test_msix_mask_sets_every_entry_masked():
    body = _fn_body(MSIX.read_text(), "msix_mask_entries")
    assert "MSIX_ENTRY_CTRL_MASKED" in body and "volatile_store(" in body


@pytest.mark.unit
def test_dropping_the_last_irq_handle_quiesces_before_the_owner_goes():
    """CapRevoke of the last IRQ handle is the other way a pid stops owning
    the device: the quiesce runs while it is still the recorded owner."""
    body = _fn_body(CAP_TABLE.read_text(), "cap_last_handle_dropped")
    q = body.index("driver_quiesce_object(")
    assert q < body.index("irq_owner_release(")


@pytest.mark.unit
def test_boot_test_is_listed_and_its_stub_modes_are_40_to_42():
    src = POSTINIT.read_text()
    assert 'boot_test_result("drv-quiesce", drv_quiesce_self_test())' in src
    stub = STUB.read_text()
    for name, num in (("QUIESCE", 40), ("QUIESCE_DMA", 41), ("QUIESCE_REVOKE", 42)):
        assert re.search(rf"^\.equ DRIVER_STUB_{name},\s+{num}$", stub, re.M), name
        assert re.search(rf"^const DRIVER_STUB_{name}: u64 = {num}$", src, re.M), name
    assert " drv-quiesce" in BOOT_SH.read_text()
