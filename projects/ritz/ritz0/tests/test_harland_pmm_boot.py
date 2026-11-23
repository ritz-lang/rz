"""Harland's PMM keeps the UEFI boot regions and physical page 0 out of the
free pool; the UEFI boot test fails when the kernel panics (AGAST #2749,
feature #1844.3).

Before: under the Harland (UEFI) boot protocol `kernel_main` reserved only
the legacy 1-2 MB kernel window, so the PMM could hand out pages holding the
loaded kernel image, the bootloader's PML4, the boot info block or the memory
map that UEFI placed elsewhere.  Page tables were reserved only after
`heap_init`, which itself allocates through the PMM.  Physical page 0 was
allocatable, so `pmm_alloc_page()` returning 0 was ambiguous between "page 0"
and "out of memory".

After: the HARLAND branch reserves kernel/PML4/bootinfo/memmap right after
`pmm_init_from_bootinfo`; `vmm_reserve_page_tables()` runs before and after
`heap_init`; the PMM never frees or hands out page 0.
"""

import re

import pytest

from test_harland_syscall_dispatch import KERNEL_SRC, _run

pytestmark = pytest.mark.integration

MAIN_SRC = KERNEL_SRC / "main.ritz"

# mm/pmm logs through klog (#1885), which imports serial, whose `asm x86_64:`
# blocks only ritz0 parses (AGAST #1455/#1825), and ritz0 is what `rz build
# harland` uses. klog imports ritzlib.fmt.digits (#1957) and ritzlib.str.
PMM_MODULES = ["mm.pmm", "klog", "serial", "io", "boot_abi.serial", "boot_abi.portio", "ritzlib.fmt.digits", "ritzlib.str"]

# Exit code i names the i-th failing check.
PMM_PAGE_ZERO = """\
import ritzlib.option
import mm.pmm { PAGE_SIZE, pmm_init, pmm_mark_region_free, pmm_alloc_page, pmm_free_page, pmm_get_free_pages }

var bm: [8]u8

fn main() -> i32
    pmm_init(@bm[0], 64)
    # Pages 0..3 reported usable by firmware: page 0 must not enter the pool.
    pmm_mark_region_free(0, 4 * PAGE_SIZE)
    if pmm_get_free_pages() != 3
        return 1
    let a: u64 = pmm_alloc_page()
    let b: u64 = pmm_alloc_page()
    let c: u64 = pmm_alloc_page()
    if a == 0 or b == 0 or c == 0
        return 2
    # Pool exhausted: 0 is the failure sentinel, never a page.
    if pmm_alloc_page() != 0
        return 3
    # Freeing address 0 is refused and does not grow the pool.
    if pmm_free_page(0) != -1
        return 4
    if pmm_get_free_pages() != 0
        return 5
    if pmm_alloc_page() != 0
        return 6
    # A real page still round-trips.
    if pmm_free_page(b) != 0
        return 7
    if pmm_alloc_page() != b
        return 8
    0
"""


def test_pmm_never_hands_out_or_frees_page_zero(tmp_path):
    rc = _run("ritz0", tmp_path, PMM_PAGE_ZERO, PMM_MODULES)
    assert rc == 0, f"PMM page-0 check {rc} failed (see PMM_PAGE_ZERO)"


# --- contiguous runs (AGAST #4329: the AMD-Vi device table) ---------------------
PMM_CONTIG = """\
import ritzlib.option
import mm.pmm { PAGE_SIZE, pmm_init, pmm_mark_region_free, pmm_alloc_page, pmm_alloc_contig, pmm_free_page, pmm_get_free_pages }

var bm: [8]u8

fn main() -> i32
    pmm_init(@bm[0], 64)
    # Pages 1..9 free, then a hole at 10, then 11..15.
    pmm_mark_region_free(0, 10 * PAGE_SIZE)
    pmm_mark_region_free(11 * PAGE_SIZE, 5 * PAGE_SIZE)
    # Take pages 1..3, give back 2: the free run 2..2 is too short for 4,
    # so the run of 4 is 4..7.
    let a: u64 = pmm_alloc_page()
    let b: u64 = pmm_alloc_page()
    let c: u64 = pmm_alloc_page()
    if a != PAGE_SIZE or c != 3 * PAGE_SIZE
        return 1
    pmm_free_page(b)
    if pmm_alloc_contig(4) != 4 * PAGE_SIZE
        return 2
    # 14 free - 3 + 1 - 4: pages 2, 8, 9, 11..15
    if pmm_get_free_pages() != 8
        return 3
    # No run of 6 (the hole at 10 splits 8..15); the run of 5 is 11..15.
    if pmm_alloc_contig(6) != 0
        return 4
    if pmm_alloc_contig(5) != 11 * PAGE_SIZE
        return 5
    if pmm_alloc_contig(0) != 0 or pmm_alloc_contig(3) != 0
        return 6
    # The single pages left still allocate: 2, then 8.
    if pmm_alloc_page() != 2 * PAGE_SIZE or pmm_alloc_page() != 8 * PAGE_SIZE
        return 7
    0
"""


def test_pmm_alloc_contig_finds_a_free_run(tmp_path):
    rc = _run("ritz0", tmp_path, PMM_CONTIG, PMM_MODULES)
    assert rc == 0, f"PMM contig check {rc} failed (see PMM_CONTIG)"


# --- memory above 4 GiB (AGAST #4183) -------------------------------------------
#
# Before #4183 the bitmap was a fixed 128 KiB array (MAX_PAGES, 4 GiB): pages
# above 4 GiB were dropped from the pool and pmm_free_page refused them. Now
# the boot paths size the bitmap from the memory map's highest usable address
# and carve it out of the first usable region below 1 GiB that holds none of
# the boot structures. Host addresses stand in for physical ones: the "low"
# region is a static buffer (identity "mapped" in a -no-pie binary), the
# region above 4 GiB is only ever tracked, never touched.

GIB = 1 << 30
SIX_GIB_PAGES = 6 * GIB // 4096

PMM_ABOVE_4G = f"""\
import ritzlib.option
import boot_abi.handoff {{ HarlandBootInfo, HarlandMemEntry, HARLAND_BOOT_MAGIC, HARLAND_MEM_USABLE, HARLAND_MEM_RESERVED }}
import mm.pmm {{ PAGE_SIZE, Mb2BootInfo, pmm_init, pmm_mark_region_free, pmm_alloc_page, pmm_alloc_page_high, pmm_free_page, pmm_get_free_pages, pmm_get_total_pages, pmm_bitmap_phys, pmm_init_from_bootinfo, pmm_init_from_multiboot }}

const FOUR_GIB: u64 = 0x100000000
const SIX_GIB: u64 = 0x180000000
const SIX_GIB_PAGES: u64 = {SIX_GIB_PAGES}
# A 6 GiB bitmap: 196608 bytes, 48 pages.
const BITMAP_PAGES: u64 = 48

var bm: [196608]u8
var low: [1048576]u8
var info: HarlandBootInfo
var mmap: [3]HarlandMemEntry
var mb: [16]u64

fn page_up(a: u64) -> u64
    return (a + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)

# Allocate every page below 4 GiB; none may lie in [bm_lo, bm_hi). Returns
# how many were handed out, or 0 on an overlap.
fn drain_low(bm_lo: u64, bm_hi: u64) -> u64
    var n: u64 = 0
    while true
        let p: u64 = pmm_alloc_page()
        if p == 0 or p >= FOUR_GIB
            return n
        if p >= bm_lo and p < bm_hi
            return 0
        n = n + 1

fn put32(a: u64, v: u32)
    let p: *u32 = a as *u32
    *p = v

fn put64(a: u64, v: u64)
    let p: *u64 = a as *u64
    *p = v

fn main() -> i32
    # 1. The allocator itself: pages above 4 GiB enter the pool, come back
    #    from pmm_alloc_page_high, and free again.
    pmm_init(@bm[0], SIX_GIB_PAGES)
    pmm_mark_region_free(PAGE_SIZE, 2 * PAGE_SIZE)
    pmm_mark_region_free(FOUR_GIB, 8 * PAGE_SIZE)
    if pmm_get_free_pages() != 10
        return 1
    let hi: u64 = pmm_alloc_page_high()
    if hi != FOUR_GIB + 7 * PAGE_SIZE
        return 2
    if pmm_free_page(hi) != 0
        return 3
    # Low pages first, then the ones above 4 GiB.
    pmm_alloc_page()
    pmm_alloc_page()
    if pmm_alloc_page() != FOUR_GIB
        return 4
    # Past the bitmap: never the PMM's.
    if pmm_free_page(SIX_GIB) != -1
        return 5

    # 2. UEFI boot info: usable [low, low+1M) and [4G, 6G). The kernel image
    #    covers the first 64 KiB of low; the bitmap must go after it.
    let lo: u64 = page_up(@low[0] as u64)
    let lo_end: u64 = (@low[0] as u64 + 1048576) & ~(PAGE_SIZE - 1)
    mmap[0].base = lo
    mmap[0].length = lo_end - lo
    mmap[0].mem_type = HARLAND_MEM_USABLE
    mmap[1].base = FOUR_GIB
    mmap[1].length = 2 * 1073741824
    mmap[1].mem_type = HARLAND_MEM_USABLE
    mmap[2].base = SIX_GIB
    mmap[2].length = 1073741824
    mmap[2].mem_type = HARLAND_MEM_RESERVED
    info.magic = HARLAND_BOOT_MAGIC
    info.memory_map = @mmap[0]
    info.memory_map_entries = 3
    info.kernel_phys = lo
    info.kernel_size = 65536
    if pmm_init_from_bootinfo(@info, 0) != 0
        return 10
    # Sized from the highest usable address, not capped at 4 GiB.
    if pmm_get_total_pages() != SIX_GIB_PAGES
        return 11
    let b: u64 = pmm_bitmap_phys()
    if b < lo + 65536 or b + BITMAP_PAGES * PAGE_SIZE > lo_end
        return 12
    let low_pages: u64 = (lo_end - lo) / PAGE_SIZE
    # Every usable page but the bitmap's is free, 2 GiB of them above 4 GiB.
    if pmm_get_free_pages() != low_pages + 524288 - BITMAP_PAGES
        return 13
    if pmm_alloc_page_high() != SIX_GIB - PAGE_SIZE
        return 14
    if drain_low(b, b + BITMAP_PAGES * PAGE_SIZE) != low_pages - BITMAP_PAGES
        return 15

    # 3. Multiboot2: the info block sits at the start of the usable low
    #    region; the bitmap must not overwrite it.
    let mbi: u64 = lo
    put32(mbi, 8 + 16 + 3 * 24 + 8)
    put32(mbi + 4, 0)
    put32(mbi + 8, 6)
    put32(mbi + 12, 16 + 3 * 24)
    put32(mbi + 16, 24)
    put32(mbi + 20, 0)
    put64(mbi + 24, lo)
    put64(mbi + 32, lo_end - lo)
    put32(mbi + 40, 1)
    put32(mbi + 44, 0)
    put64(mbi + 48, FOUR_GIB)
    put64(mbi + 56, 2 * 1073741824)
    put32(mbi + 64, 1)
    put32(mbi + 68, 0)
    put64(mbi + 72, SIX_GIB)
    put64(mbi + 80, 1073741824)
    put32(mbi + 88, 2)
    put32(mbi + 92, 0)
    put32(mbi + 96, 0)
    put32(mbi + 100, 8)
    if pmm_init_from_multiboot(mbi as *Mb2BootInfo, 0) != 0
        return 20
    if pmm_get_total_pages() != SIX_GIB_PAGES
        return 21
    let mb_b: u64 = pmm_bitmap_phys()
    if mb_b < mbi + 104 or mb_b + BITMAP_PAGES * PAGE_SIZE > lo_end
        return 22
    # The info block itself is the caller's to reserve (main does): here only
    # the bitmap's pages are out of the pool.
    if pmm_get_free_pages() != low_pages + 524288 - BITMAP_PAGES
        return 23
    0
"""


def test_pmm_tracks_memory_above_4gib_on_both_boot_paths(tmp_path):
    rc = _run("ritz0", tmp_path, PMM_ABOVE_4G, PMM_MODULES)
    assert rc == 0, f"PMM above-4G check {rc} failed (see PMM_ABOVE_4G)"


# pmm_alloc_page keeps a next-free hint instead of scanning from page 0: a
# linear scan makes draining 8 GiB of pages quadratic (even skipping whole
# used bytes, ~2.7e11 byte tests: a 2 GiB drain took 33 s, this one ~16x
# that, far past _run's 60 s timeout); with the hint it takes milliseconds. The
# hint must also move back down when a lower page is freed.
PMM_HINT = """\
import ritzlib.option
import mm.pmm { PAGE_SIZE, pmm_init, pmm_mark_region_free, pmm_alloc_page, pmm_free_page }

const PAGES: u64 = 2097152

var bm: [262144]u8

fn main() -> i32
    pmm_init(@bm[0], PAGES)
    pmm_mark_region_free(0, PAGES * PAGE_SIZE)
    var want: u64 = PAGE_SIZE
    while want < PAGES * PAGE_SIZE
        if pmm_alloc_page() != want
            return 1
        want = want + PAGE_SIZE
    if pmm_alloc_page() != 0
        return 2
    # Free a high page, then a low one: the low one comes back first.
    pmm_free_page(400000 * PAGE_SIZE)
    pmm_free_page(5 * PAGE_SIZE)
    if pmm_alloc_page() != 5 * PAGE_SIZE
        return 3
    if pmm_alloc_page() != 400000 * PAGE_SIZE
        return 4
    if pmm_alloc_page() != 0
        return 5
    0
"""


def test_pmm_alloc_uses_a_next_free_hint(tmp_path):
    rc = _run("ritz0", tmp_path, PMM_HINT, PMM_MODULES)
    assert rc == 0, f"PMM hint check {rc} failed (see PMM_HINT)"


# --- kernel_main reserves the UEFI boot regions before anything allocates -------

def _kernel_main():
    src = MAIN_SRC.read_text()
    m = re.search(r"^pub fn kernel_main\(boot_info_addr: u64\) -> i32\n((?:[ \t]+.*\n|[ \t]*\n|#.*\n)+)",
                  src, re.M)
    assert m, "kernel/src/main.ritz has no kernel_main"
    # Comments say what the code should do; the test checks what it does.
    return "\n".join(line.split("#", 1)[0].rstrip() for line in m.group(1).splitlines())


def test_harland_branch_reserves_boot_regions_before_first_allocation():
    body = _kernel_main()
    start = body.index("pmm_init_from_bootinfo(harland_boot_info, ")
    end = body.index("else if boot_protocol == BOOT_PROTOCOL_MULTIBOOT2", start)
    branch = body[start:end]
    required = {
        "kernel image": r"pmm_mark_region_used\(\(\*harland_boot_info\)\.kernel_phys, \(\*harland_boot_info\)\.kernel_size\)",
        "PML4": r"pmm_mark_region_used\(\(\*harland_boot_info\)\.pml4_phys, PAGE_SIZE\)",
        "boot info": r"pmm_mark_region_used\(boot_info_addr, ",
        "memory map": r"pmm_mark_region_used\(\(\*harland_boot_info\)\.memory_map as u64, ",
    }
    missing = [name for name, pat in required.items() if not re.search(pat, branch)]
    assert not missing, f"HARLAND branch does not reserve: {', '.join(missing)}"
    # The PMM branch runs before vmm_init / heap_init, the first allocators.
    assert end < body.index("vmm_init()") < body.index("heap_init(")


def test_page_tables_reserved_before_and_after_heap_init():
    body = _kernel_main()
    heap = body.index("heap_init(")
    calls = [m.start() for m in re.finditer(r"vmm_reserve_page_tables\(\)", body)]
    assert any(c < heap for c in calls), "page tables not reserved before heap_init"
    assert any(c > heap for c in calls), "page tables not reserved after heap_init"

