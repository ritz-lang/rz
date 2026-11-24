"""Harland's MMIO window PML4 entry exists before the first process (AGAST #3577).

vmm_map_mmio maps device registers in a bump window at PML4[257]
(MMIO_WINDOW_BASE). vmm_create_user_pml4 copies PML4[256..511] by value, so
before #3577 a process saw the window only if PML4[257] was present when the
process was created: a driver whose first vmm_map_mmio came after that (hotplug,
deferred init) created PML4[257] in the kernel PML4 alone, and polling it from a
syscall under the older process's CR3 faulted.

After: vmm_init_physmap calls vmm_init_mmio_window, which gives PML4[257] its
PDPT before any process exists. Every process copies that entry, so a later
mapping lands in the PDPT the process already shares.

vmm_map_page ends in `invlpg`, which faults in user mode, so the host check
pins the mechanism rather than calling vmm_map_mmio: the window's PML4 entry is
present before the process and the process points at the same PDPT.
"""

import re

import pytest

from test_harland_syscall_dispatch import KERNEL_SRC, _run


VMM_SRC = KERNEL_SRC / "mm" / "vmm.ritz"

# vmm imports klog (#1885) and io; klog imports serial. Their `asm x86_64:`
# blocks only ritz0 parses; klog imports ritzlib.fmt.digits (#1957) and ritzlib.str.
VMM_MODULES = ["mm.vmm", "mm.pmm", "klog", "serial", "io", "boot_abi.serial", "boot_abi.portio", "ritzlib.fmt.digits", "ritzlib.str"]

# A fake kernel PML4 in a page-aligned slice of .bss (below 1 GiB in a -no-pie
# binary, as vmm_alloc_low_table requires; phys == virt until the physmap is up).
# Exit code i names the i-th failing check.
WINDOW_PROGRAM = """\
import ritzlib.option
import mm.pmm { PAGE_SIZE, pmm_init, pmm_mark_region_free, pmm_alloc_page }
import mm.vmm { PTE_PRESENT, PTE_ADDR_MASK, MMIO_WINDOW_BASE, vmm_pml4_phys, vmm_init_mmio_window, vmm_create_user_pml4, vmm_read_pml4_entry }

var g_mem: [266240]u8
# Tracks the low 1 GiB, where g_mem is (#4183: the caller supplies the bitmap).
var g_bm: [32768]u8

fn zero_page(p: u64) -> i32
    var i: u64 = 0
    while i < 512
        *((p + i * 8) as *u64) = 0
        i = i + 1
    return 0

fn main() -> i32
    # The window is the slot this test pins.
    if ((MMIO_WINDOW_BASE >> 39) & 511) != 257
        return 1
    pmm_init(@g_bm[0], 262144)
    pmm_mark_region_free(@g_mem[0] as u64, 266240)
    let kpml4: u64 = pmm_alloc_page()
    if kpml4 == 0
        return 2
    zero_page(kpml4)
    vmm_pml4_phys = kpml4

    # Boot: the window's PML4 entry exists before any process.
    if vmm_init_mmio_window() != 0
        return 3
    let kentry: u64 = vmm_read_pml4_entry(kpml4, 257)
    if (kentry & PTE_PRESENT) == 0
        return 4

    # A process created now shares that PDPT, so whatever vmm_map_mmio puts
    # below it later is visible under the process's CR3.
    let proc: u64 = vmm_create_user_pml4()
    if proc == 0
        return 5
    let pentry: u64 = vmm_read_pml4_entry(proc, 257)
    if (pentry & PTE_PRESENT) == 0
        return 6
    if (pentry & PTE_ADDR_MASK) != (kentry & PTE_ADDR_MASK)
        return 7

    # A second call keeps the PDPT (and every mapping below it).
    if vmm_init_mmio_window() != 0
        return 8
    if vmm_read_pml4_entry(kpml4, 257) != kentry
        return 9
    0
"""


@pytest.mark.integration
def test_mmio_window_pdpt_exists_before_the_first_process_and_is_shared(tmp_path):
    rc = _run("ritz0", tmp_path, WINDOW_PROGRAM, VMM_MODULES)
    assert rc == 0, f"MMIO window check {rc} failed (see WINDOW_PROGRAM)"


def _fn_body(src: str, name: str) -> str:
    m = re.search(rf"^pub fn {name}\(.*?(?=^\S)", src, re.S | re.M)
    assert m, f"{name} not found in {VMM_SRC}"
    return m.group(0)


def test_physmap_init_creates_the_window_before_switching_to_the_physmap():
    """kernel_main runs vmm_init_physmap before the first process; the window's
    PDPT comes from vmm_alloc_low_table, written through the identity map, so
    it has to be made before g_physmap_offset moves."""
    body = _fn_body(VMM_SRC.read_text(), "vmm_init_physmap")
    call = body.find("vmm_init_mmio_window()")
    assert call != -1, "vmm_init_physmap does not create the MMIO window"
    assert call < body.find("g_physmap_offset = PHYSMAP_BASE")
