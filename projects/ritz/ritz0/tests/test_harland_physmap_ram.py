"""Harland's physmap maps only 2 MiB chunks that hold RAM (AGAST #4209).

Before: vmm_init_physmap mapped every 2 MiB chunk from 0 to pmm's top of RAM
write-back, the PCI hole below 4 GiB included (framebuffer at 0xC0000000,
LAPIC, IOAPIC, BARs). A WB alias of device memory lets the CPU access it
speculatively and cached, a memory-type conflict with vmm_map_mmio's UC
mappings.

After: vmm_physmap_fill maps a chunk only if pmm has a free page in it, or
the boot identity map maps it and it lies above the first GiB (the UEFI
loader identity-maps only RAM-typed chunks there, loader data such as
BootInfo and the boot page tables included) or below pmm's top (both boot
maps cover the first GiB whole). A GiB with no RAM chunk gets no PD.

vmm_init_physmap switches phys_to_virt to PHYSMAP_BASE, which a host process
can't follow, so the host check drives vmm_physmap_fill on fake tables and a
pmm bitmap that tracks RAM it never touches (phys == virt until the switch).
"""

import re

import pytest

from test_harland_syscall_dispatch import KERNEL_SRC, _run

pytestmark = pytest.mark.integration

VMM_SRC = KERNEL_SRC / "mm" / "vmm.ritz"

# vmm imports klog (#1885) and io; klog imports serial. Their `asm x86_64:`
# blocks only ritz0 parses; klog imports ritzlib.fmt.digits (#1957) and ritzlib.str.
VMM_MODULES = ["mm.vmm", "mm.pmm", "klog", "serial", "io", "boot_abi.serial", "boot_abi.portio", "ritzlib.fmt.digits", "ritzlib.str"]

GIB = 1 << 30
SIX_GIB_PAGES = 6 * GIB // 4096
HALF_GIB_PAGES = GIB // 2 // 4096

# Exit code i names the i-th failing check.
PHYSMAP_PROGRAM = f"""\
import ritzlib.option
import mm.pmm {{ PAGE_SIZE, pmm_init, pmm_mark_region_free, pmm_alloc_page }}
import mm.vmm {{ PTE_PRESENT, PTE_WRITABLE, PTE_HUGE, PTE_ADDR_MASK, vmm_pml4_phys, vmm_physmap_fill }}

const ONE_GIB: u64 = 0x40000000
const FOUR_GIB: u64 = 0x100000000
const TWO_MIB: u64 = 0x200000
const SIX_GIB_PAGES: u64 = {SIX_GIB_PAGES}
const HALF_GIB_PAGES: u64 = {HALF_GIB_PAGES}

# Page-table pages come from here (low .bss in a -no-pie binary).
var g_mem: [131072]u8
# A 6 GiB bitmap.
var g_bm: [196608]u8

fn get(t: u64, i: u64) -> u64
    return *((t + i * 8) as *u64)

fn put(t: u64, i: u64, v: u64)
    *((t + i * 8) as *u64) = v

fn table() -> u64
    let t: u64 = pmm_alloc_page()
    var i: u64 = 0
    while i < 512
        put(t, i, 0)
        i = i + 1
    return t

# A boot identity PD mapping chunks [lo, hi) of GiB g.
fn identity_pd(g: u64, lo: u64, hi: u64) -> u64
    let pd: u64 = table()
    var e: u64 = lo
    while e < hi
        put(pd, e, (g * ONE_GIB + e * TWO_MIB) | PTE_PRESENT | PTE_WRITABLE | PTE_HUGE)
        e = e + 1
    return pd

# The physmap PD of GiB g maps exactly chunks [lo, hi), write-back.
fn pd_maps(pdpt: u64, g: u64, lo: u64, hi: u64) -> bool
    let pde: u64 = get(pdpt, g)
    if (pde & PTE_PRESENT) == 0
        return false
    let pd: u64 = pde & PTE_ADDR_MASK
    var e: u64 = 0
    while e < 512
        let want: u64 = (g * ONE_GIB + e * TWO_MIB) | PTE_PRESENT | PTE_WRITABLE | PTE_HUGE
        if e >= lo and e < hi
            if get(pd, e) != want
                return false
        else if get(pd, e) != 0
            return false
        e = e + 1
    return true

fn main() -> i32
    # 1. -m 6G under OVMF: RAM at 0-2 GiB and 4-6 GiB, the PCI hole between.
    #    The loader identity-maps GiB 0 and two loader-data chunks with no
    #    usable page in them (BootInfo-like): one at 1 GiB, one at the top
    #    of RAM, above the last usable page (pmm's top).
    pmm_init(@g_bm[0], SIX_GIB_PAGES)
    pmm_mark_region_free(@g_mem[0] as u64, 131072)
    pmm_mark_region_free(FOUR_GIB, 2 * ONE_GIB - TWO_MIB)
    let pml4: u64 = table()
    let id_pdpt: u64 = table()
    put(pml4, 0, id_pdpt | PTE_PRESENT | PTE_WRITABLE)
    put(id_pdpt, 0, identity_pd(0, 0, 512) | PTE_PRESENT | PTE_WRITABLE)
    put(id_pdpt, 1, identity_pd(1, 0, 1) | PTE_PRESENT | PTE_WRITABLE)
    put(id_pdpt, 5, identity_pd(5, 511, 512) | PTE_PRESENT | PTE_WRITABLE)
    vmm_pml4_phys = pml4
    let pdpt: u64 = table()
    let n: i64 = vmm_physmap_fill(pdpt, 6)
    if not pd_maps(pdpt, 0, 0, 512)
        return 1
    if not pd_maps(pdpt, 1, 0, 1)
        return 2
    # The PCI hole: no PD at all.
    if get(pdpt, 2) != 0 or get(pdpt, 3) != 0
        return 3
    if not pd_maps(pdpt, 4, 0, 512) or not pd_maps(pdpt, 5, 0, 512)
        return 4
    if n != 1537
        return 5

    # 2. -m 512M multiboot: the boot map covers GiB 0 whole, RAM ends at
    #    511 MiB. Chunks from 512 MiB on hold no RAM.
    pmm_init(@g_bm[0], HALF_GIB_PAGES)
    pmm_mark_region_free(@g_mem[0] as u64, 131072)
    pmm_mark_region_free(0x10000000, 0x0FF00000)
    let pml4b: u64 = table()
    let id_pdptb: u64 = table()
    put(pml4b, 0, id_pdptb | PTE_PRESENT | PTE_WRITABLE)
    put(id_pdptb, 0, identity_pd(0, 0, 512) | PTE_PRESENT | PTE_WRITABLE)
    vmm_pml4_phys = pml4b
    let pdptb: u64 = table()
    let nb: i64 = vmm_physmap_fill(pdptb, 1)
    if not pd_maps(pdptb, 0, 0, 256)
        return 6
    if nb != 256
        return 7
    0
"""


def test_physmap_maps_only_ram_chunks(tmp_path):
    rc = _run("ritz0", tmp_path, PHYSMAP_PROGRAM, VMM_MODULES)
    assert rc == 0, f"physmap check {rc} failed (see PHYSMAP_PROGRAM)"


def test_physmap_init_builds_through_the_ram_filter():
    """vmm_init_physmap's PDs are vmm_physmap_fill's, not a fill of its own."""
    src = VMM_SRC.read_text()
    m = re.search(r"^pub fn vmm_init_physmap\(.*?(?=^\S)", src, re.S | re.M)
    assert m, "vmm_init_physmap not found"
    assert "vmm_physmap_fill(" in m.group(0)
