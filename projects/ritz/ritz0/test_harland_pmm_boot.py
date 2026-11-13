"""Harland's PMM keeps the UEFI boot regions and physical page 0 out of the
free pool; the UEFI boot test fails when the kernel panics (AGAST #2749,
feature #1844.3).

Before: under the Harland (UEFI) boot protocol `kernel_main` reserved only
the legacy 1-2 MB kernel window, so the PMM could hand out pages holding the
loaded kernel image, the bootloader's PML4, the boot info block or the memory
map that UEFI placed elsewhere.  Page tables were reserved only after
`heap_init`, which itself allocates through the PMM.  Physical page 0 was
allocatable, so `pmm_alloc_page()` returning 0 was ambiguous between "page 0"
and "out of memory".  And `boot/test.sh` reported a milestone even when the
serial log showed a kernel panic or CPU exception.

After: the HARLAND branch reserves kernel/PML4/bootinfo/memmap right after
`pmm_init_from_bootinfo`; `vmm_reserve_page_tables()` runs before and after
`heap_init`; the PMM never frees or hands out page 0; and the UEFI verdict
(`boot/uefi_verdict.sh`, called by `boot/test.sh`) exits 1 on a panic line.
"""

import re
import subprocess

import pytest

from test_harland_syscall_dispatch import KERNEL_SRC, _run

pytestmark = pytest.mark.integration

HARLAND = KERNEL_SRC.parents[1]
MAIN_SRC = KERNEL_SRC / "main.ritz"
VERDICT = HARLAND / "boot" / "uefi_verdict.sh"

# mm/pmm imports serial, whose `asm x86_64:` blocks only ritz0 parses
# (AGAST #1455/#1825), and ritz0 is what `rz build harland` uses.
PMM_MODULES = ["mm.pmm", "serial", "io"]

# Exit code i names the i-th failing check.
PMM_PAGE_ZERO = """\
import ritzlib.option
import mm.pmm { PAGE_SIZE, pmm_init, pmm_mark_region_free, pmm_alloc_page, pmm_free_page, pmm_get_free_pages }

fn main() -> i32
    pmm_init()
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
    start = body.index("pmm_init_from_bootinfo(harland_boot_info)")
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


# --- the UEFI boot verdict fails on a panic -------------------------------------

@pytest.mark.parametrize("log, want", [
    ("Harland kernel starting...\nALL TESTS PASSED\n", 0),
    ("ALL TESTS PASSED\n\n*** KERNEL PANIC ***\nhalted\n", 1),
    ("Hello from Harland\n\n!!! EXCEPTION !!!\nRIP: 0x1000\n", 1),
    ("Hello from Harland\n\n*** KERNEL PANIC: Failed to load initramfs ***\n", 1),
], ids=["pass", "panic", "exception", "initramfs-panic"])
def test_uefi_verdict_fails_on_panic(tmp_path, log, want):
    serial = tmp_path / "serial.log"
    serial.write_text(log)
    proc = subprocess.run(["bash", str(VERDICT), str(serial)], capture_output=True, text=True, timeout=30)
    assert proc.returncode == want, proc.stdout + proc.stderr


def test_boot_test_uses_the_verdict():
    script = (HARLAND / "boot" / "test.sh").read_text()
    assert re.search(r'uefi_verdict\.sh" "\$SERIAL_LOG"', script), "boot/test.sh does not call uefi_verdict.sh"
