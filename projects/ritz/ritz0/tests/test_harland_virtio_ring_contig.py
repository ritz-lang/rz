"""A virtqueue's rings are one physically contiguous run of pages (AGAST #4880).

drivers/virtio/common.ritz vio_queue_alloc gives the device one physical
address for a queue's rings (descriptors, available, used: three pages for
a 256-entry queue), and the device reads them at that address plus their
offsets. It used to take the first page from pmm_alloc_page and then call
pmm_alloc_page once per further page, dropping their results on the
assumption that "PMM allocates pages in ascending order". The per-CPU frame
caches (#4879) broke that: a cache is a stack, so once it holds freed
frames, consecutive pmm_alloc_page calls are not adjacent. The pages after
the first then belong to someone else. On the vtd boot (test_msix_boot.sh)
the NIC's TX rings ran over VT-d's own second-level table, and
vio_queue_reset zeroed it: the NIC lost its domain's mappings and faulted
on a ring page instead of on the fault probe's hole.

Now the rings come from one pmm_alloc_contig run. The stub PMM here hands
single pages out from the top of its memory down, as a warm cache does, and
contiguous runs only through pmm_alloc_contig; it records which allocation
gave each page. The real blk.ritz and common.ritz (through the
test_harland_virtio_blk_timeout harness and its legacy device stand-in) set
up a queue, and every page of its rings must belong to the allocation that
gave the first. The vtd boot of tools/test_msix_boot.sh is the runtime check.
"""

import pytest

import test_harland_virtio_blk_timeout as blk

pytestmark = pytest.mark.integration

# Physical == virtual, as in blk's stand-in. Pages TAKEN.. are another
# allocation's from the start (as VT-d's table was on the vtd boot), single
# pages come from just below them downwards (a frame cache's order after
# frees), runs from the bottom up; g_owner names the allocation that gave
# each page (0: none).
PMM_STUB = """\
pub const PAGE_SIZE: u64 = 4096

const NPAGES: i32 = 31
const TAKEN: i32 = 24
var g_mem: [131072]u8
var g_base: u64 = 0
var g_owner: [32]u32
var g_low: i32 = 0
var g_high: i32 = 0
var g_ids: u32 = 0

fn setup()
    if g_base == 0
        g_base = ((@g_mem[0] as u64) + 4095) & (0xFFFFFFFFFFFFFFFF ^ 4095)
        g_ids = 1
        var i: i32 = TAKEN
        while i < NPAGES
            g_owner[i] = g_ids
            i = i + 1
        g_high = TAKEN

pub fn pmm_alloc_page() -> u64
    setup()
    if g_high <= g_low
        return 0
    g_high = g_high - 1
    g_ids = g_ids + 1
    g_owner[g_high] = g_ids
    g_base + (g_high as u64) * 4096

pub fn pmm_alloc_contig(n: u64) -> u64
    setup()
    if n == 0 or (g_low as u64) + n > (g_high as u64)
        return 0
    g_ids = g_ids + 1
    let first: i32 = g_low
    var i: i32 = 0
    while (i as u64) < n
        g_owner[first + i] = g_ids
        i = i + 1
    g_low = first + (n as i32)
    g_base + (first as u64) * 4096

pub fn pmm_owner_of(addr: u64) -> u32
    setup()
    if addr < g_base or addr >= g_base + (NPAGES as u64) * 4096
        return 0
    g_owner[((addr - g_base) / 4096) as i32]

pub fn pmm_free_page(addr: u64) -> i32
    0
"""

CHECKS = {
    1: "virtio_blk_init found no device",
    2: "the request queue's rings fit one page: the claim needs more",
    3: "the rings' first page is no page the PMM gave out",
    4: "a ring page after the first belongs to another allocation (or none): "
       "the rings are not one contiguous run",
}

PROGRAM = """\
import drivers.virtio.blk { VirtioBlkDevice, virtio_blk_init }
import drivers.virtio.common { vio_queue_pages }
import virtio_abi.virtq { Virtqueue }
import mm.pmm { pmm_owner_of }

fn main() -> i32
    let dev: *VirtioBlkDevice = virtio_blk_init()
    if dev == 0 as *VirtioBlkDevice
        return 1
    let vq: *Virtqueue = (*dev).request_queue
    let first: u64 = (*vq).phys_addr
    let pages: u64 = vio_queue_pages(vq)
    if pages < 2
        return 2
    let owner: u32 = pmm_owner_of(first)
    if owner == 0
        return 3
    var p: u64 = 1
    while p < pages
        if pmm_owner_of(first + p * 4096) != owner
            return 4
        p = p + 1
    0
"""


def test_a_queues_rings_are_one_contiguous_run(tmp_path, monkeypatch):
    monkeypatch.setitem(blk.STUBS, "mm/pmm.ritz", PMM_STUB)
    rc = blk._run(tmp_path, PROGRAM)
    assert rc == 0, f"check {rc}: {CHECKS.get(rc, 'crashed or unknown exit code')}"
