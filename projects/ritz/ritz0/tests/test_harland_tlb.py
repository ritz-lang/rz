"""Harland's owner-side unmap and lazy-CR3 drop (AGAST #4880, SMP_USER.md §3).

mm/tlb.ritz unmaps from a process's space on the CPU the process is on: an
UNMAP request to another CPU, or locally. The cross-CPU path needs real APs,
so its proof is the `[tlb] owner unmap OK` / `[tlb] kernel invlpg OK` boot
lines (arch/x86_64/apcall.ritz tlb_selftest_all, tools/test_tier1_boot.sh
tlb_owner_unmap). The host program below runs the local path, the one every
process takes until #4881. The source checks pin what the design relies on:
no PTE_GLOBAL, every CR3 load recorded in PC_ACTIVE_PML4, and vmm_free_pml4
refusing a PML4 that is still loaded.
"""

import re

import pytest

from test_harland_syscall_dispatch import KERNEL_SRC, _run
from test_harland_mmio_window import VMM_MODULES

VMM_SRC = KERNEL_SRC / "mm" / "vmm.ritz"
TLB_SRC = KERNEL_SRC / "mm" / "tlb.ritz"

TLB_MODULES = ["mm.tlb", "sync.mbox", "arch.x86_64.tsc", "arch.x86_64.tsc_calc", "arch.x86_64.cpu_map"] + VMM_MODULES

# A fake PML4 in .bss (phys == virt: no physmap on the host), not loaded on
# any CPU, so neither the map nor the unmap runs invlpg (which faults in
# ring 3). Exit code i names the i-th failing check.
LOCAL_PROGRAM = """\
import ritzlib.option
import mm.pmm { PAGE_SIZE, pmm_irqsave, pmm_init, pmm_mark_region_free, pmm_alloc_page }
import mm.vmm { PTE_PRESENT, PTE_WRITABLE, PTE_DEVICE, PTE_ADDR_MASK, vmm_map_page_in, vmm_pte_in, vmm_free_pml4, vmm_pml4_loaded_on }
import mm.tlb { TLB_CLEAR, TLB_QUARANTINE, tlb_unmap_on }

var g_mem: [266240]u8
var g_bm: [32768]u8

const VA: u64 = 0x10000000000

# sync/mbox.ritz's hooks (mm/tlb.ritz posts through it). The local path
# posts nothing, so the IPI must never be sent.
var g_ipis: i32 = 0
pub fn lapic_send_fixed_ipi(dest_apic: u32, vector: u8)
    g_ipis = g_ipis + 1

pub fn lapic_eoi()
    return

pub fn ap_call_run(kind: u32) -> i32
    -1

fn zero_page(p: u64)
    var i: u64 = 0
    while i < 512
        *((p + i * 8) as *u64) = 0
        i = i + 1

# The raw leaf at `va` (vmm_pte_in reports only present ones).
fn leaf(pml4: u64, va: u64) -> u64
    let l4: u64 = *((pml4 + ((va >> 39) & 511) * 8) as *u64) & PTE_ADDR_MASK
    let l3: u64 = *((l4 + ((va >> 30) & 511) * 8) as *u64) & PTE_ADDR_MASK
    let l2: u64 = *((l3 + ((va >> 21) & 511) * 8) as *u64) & PTE_ADDR_MASK
    *((l2 + ((va >> 12) & 511) * 8) as *u64)

fn main() -> i32
    pmm_irqsave(false)
    pmm_init(@g_bm[0], 262144)
    pmm_mark_region_free(@g_mem[0] as u64, 266240)
    let pml4: u64 = pmm_alloc_page()
    zero_page(pml4)
    var frames: [3]u64 = [pmm_alloc_page(), pmm_alloc_page(), pmm_alloc_page()]
    var p: u64 = 0
    while p < 3
        if vmm_map_page_in(pml4, VA + p * PAGE_SIZE, frames[p as i32], PTE_WRITABLE) != 0
            return 1
        p = p + 1
    # Loaded nowhere: the request is local, whatever CPU it names.
    if vmm_pml4_loaded_on(pml4, -1) != -1
        return 2

    # Clear two of three leaves on CPU 0, this CPU: two changed, the third
    # stays, nothing posted.
    if tlb_unmap_on(0, 7, pml4, VA, 2, TLB_CLEAR) != 2
        return 3
    if vmm_pte_in(pml4, VA) != 0 or vmm_pte_in(pml4, VA + PAGE_SIZE) != 0
        return 4
    if (vmm_pte_in(pml4, VA + 2 * PAGE_SIZE) & PTE_ADDR_MASK) != frames[2]
        return 5
    # Again: nothing left to clear.
    if tlb_unmap_on(0, 7, pml4, VA, 2, TLB_CLEAR) != 0
        return 6

    # Quarantine the third: not present, PTE_DEVICE and the frame kept.
    if tlb_unmap_on(0, 7, pml4, VA + 2 * PAGE_SIZE, 1, TLB_QUARANTINE) != 1
        return 7
    let q: u64 = leaf(pml4, VA + 2 * PAGE_SIZE)
    if (q & PTE_PRESENT) != 0 or (q & PTE_DEVICE) == 0 or (q & PTE_ADDR_MASK) != frames[2]
        return 8

    # A CPU that is not started (no AP on the host) is served locally too.
    if vmm_map_page_in(pml4, VA, frames[0], PTE_WRITABLE) != 0
        return 9
    if tlb_unmap_on(3, 7, pml4, VA, 1, TLB_CLEAR) != 1 or vmm_pte_in(pml4, VA) != 0
        return 10
    if g_ipis != 0
        return 11
    0
"""


@pytest.mark.integration
def test_local_unmap_clears_and_quarantines_without_a_message(tmp_path):
    rc = _run("ritz0", tmp_path, LOCAL_PROGRAM, TLB_MODULES)
    assert rc == 0, f"local unmap check {rc} failed (see LOCAL_PROGRAM)"


def _fn_body(src: str, name: str) -> str:
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S|\Z)", src, re.S | re.M)
    assert m, f"{name} not found"
    return m.group(0)


def _kernel_ritz():
    return sorted(KERNEL_SRC.rglob("*.ritz"))


def _pin_no_pte_global():
    """A global entry survives a CR3 load, and the lazy-CR3 drop (and every
    KERNEL_INVLPG full flush) rely on a CR3 load flushing everything."""
    users = []
    for path in _kernel_ritz():
        for n, line in enumerate(path.read_text().splitlines(), 1):
            code = line.split("#", 1)[0]
            if "PTE_GLOBAL" in code and not code.lstrip().startswith("pub const PTE_GLOBAL"):
                users.append(f"{path.relative_to(KERNEL_SRC)}:{n}: {line.strip()}")
    assert not users, "PTE_GLOBAL used:\n" + "\n".join(users)


def _pin_every_cr3_load_goes_through_vmm_switch_pml4():
    """PC_ACTIVE_PML4 is only right if it sees every CR3 load. Ritz code
    writes CR3 in vmm_switch_pml4 and in vmm_flush_tlb_all (which reloads the
    value already there), and nowhere else."""
    writers = []
    for path in _kernel_ritz():
        src = path.read_text()
        for m in re.finditer(r"movq %\w+, %cr3", src):
            fn = re.findall(r"^(?:pub )?fn (\w+)", src[: m.start()], re.M)[-1]
            writers.append(f"{path.relative_to(KERNEL_SRC)}:{fn}")
    assert sorted(writers) == ["mm/vmm.ritz:vmm_flush_tlb_all", "mm/vmm.ritz:vmm_switch_pml4"]
    body = _fn_body(VMM_SRC.read_text(), "vmm_switch_pml4")
    assert body.find("pc_active_pml4[c]") < body.find("%cr3"), "the slot must be written before the load"


def _pin_vmm_free_pml4_refuses_a_loaded_pml4():
    body = _fn_body(VMM_SRC.read_text(), "vmm_free_pml4")
    check = body.find("vmm_pml4_loaded_on(pml4, -1)")
    assert check != -1, "vmm_free_pml4 does not ask whether the PML4 is loaded"
    assert check < body.find("vmm_free_user_pages"), "the check must come before any free"
    assert "return" in body[check:body.find("vmm_free_user_pages")]


def _pin_owner_flushes_before_the_reply_and_only_where_loaded():
    """The UNMAP_DONE is posted after tlb_serve returns (sync/mbox.ritz), and
    the owner flushes only a space loaded on it."""
    here = _fn_body(TLB_SRC.read_text(), "tlb_unmap_here")
    assert "pml4 == vmm_get_current_pml4()" in here and "tlb_flush_here" in here
    handle = _fn_body((KERNEL_SRC / "sync" / "mbox.ritz").read_text(), "mbox_handle")
    serve = handle.find("tlb_serve(")
    assert serve != -1 and serve < handle.find("mbox_post(msg.from as i32, done)", serve)


# One case for the source pins (docs/TESTING.md, "What a ritz0 pytest case
# costs"): each row still runs and fails on its own, by name.
SOURCE_PINS = [
    _pin_no_pte_global,
    _pin_every_cr3_load_goes_through_vmm_switch_pml4,
    _pin_vmm_free_pml4_refuses_a_loaded_pml4,
    _pin_owner_flushes_before_the_reply_and_only_where_loaded,
]


@pytest.mark.unit
def test_source_pins():
    failed = []
    for pin in SOURCE_PINS:
        try:
            pin()
        except AssertionError as e:
            failed.append(f"{pin.__name__}: {e}")
    assert not failed, "\n".join(failed)
