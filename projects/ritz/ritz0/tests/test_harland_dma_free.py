"""DrvDmaFree (223): the run table, the VA/IOVA free list and the quarantine
rule (AGAST #4725, RING1_DRIVER.md §5 "MMIO and DMA syscalls").

mm/dma_runs.ritz records each live DrvDmaAlloc run and the free list of VA
and IOVA ranges per process and device. It imports nothing but
ritzlib.option, so the behaviour test compiles the real module into a host
program:

* a free names an exact live run of that process and device (VA and page
  count); anything else takes nothing;
* a freed range is reused first fit from the front of a hole, by the same
  process and device only, and with an IOVA only when the device has one;
* holes that touch in VA and IOVA merge; the bump floor stays above every
  hole of the process;
* exit takes every run and drops every hole of the pid.

The syscall needs a page table, a process and (for the IOTLB) a unit, so its
proof is the drv-dma-free boot test (postinit.ritz, stub mode 23), the vtd
emulated-unit test of vtd_domain_enter_at, and indium's drv_refuse_test; the
source checks below pin the order the boot test can't see: the IOVA leaves
the domain and its invalidation finishes before the CPU leaves go and the
frames reach the PMM, and an unconfirmed one quarantines instead.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"
RUNS = KERNEL_SRC / "mm" / "dma_runs.ritz"
DRIVER = KERNEL_SRC / "syscall" / "runtime" / "driver.ritz"
VMM = KERNEL_SRC / "mm" / "vmm.ritz"
PROCESS = KERNEL_SRC / "syscall" / "runtime" / "process.ritz"


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(tmp_path, src):
    """Compile the real dma_runs.ritz with `src`, link, run: the exit status."""
    mod = tmp_path / "tree" / "mm" / "dma_runs.ritz"
    mod.parent.mkdir(parents=True)
    mod.write_text(RUNS.read_text())
    (tmp_path / "t.ritz").write_text(src)
    objs = [str(_compile(tmp_path, tmp_path / "t.ritz", "t")),
            str(_compile(tmp_path, mod, "dma_runs", ("--no-runtime",)))]
    exe = tmp_path / "t"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                            "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode


# Exit status: the number of the first claim that failed, 0 if all held.
RUNS_PROGRAM = """\
import ritzlib.option
import mm.dma_runs

const P: u64 = 4096
const BASE: u64 = 0x7E0000000000
const IOVA: u64 = 0x1000000000
const NIC: u64 = 7
const BLK: u64 = 8

fn run(pid: u32, obj: u64, vaddr: u64, iova: u64, pages: u64) -> DmaRun
    DmaRun { pid: pid, dom: if iova == 0 then 0 else 1, object_id: obj, vaddr: vaddr, iova: iova, phys: 0x100000, pages: pages }

fn range(vaddr: u64, iova: u64, pages: u64) -> DmaRange
    DmaRange { vaddr: vaddr, iova: iova, pages: pages }

fn took(r: Option<DmaRange>, vaddr: u64, iova: u64, pages: u64) -> bool
    match r
        Some(x) => x.vaddr == vaddr and x.iova == iova and x.pages == pages
        None => false

fn main() -> i32
    # 1: a live run is taken only by its exact pid, device, VA and length
    if not dma_run_room() or not dma_run_add(run(5, NIC, BASE, IOVA, 2))
        return 1
    if dma_run_take(6, NIC, BASE, 2).is_some() or dma_run_take(5, BLK, BASE, 2).is_some()
        return 1
    if dma_run_take(5, NIC, BASE + P, 1).is_some() or dma_run_take(5, NIC, BASE, 1).is_some()
        return 1
    let r: DmaRun = match dma_run_take(5, NIC, BASE, 2)
        Some(x) => x
        None => return 1
    if r.iova != IOVA or r.phys != 0x100000 or r.dom != 1
        return 1
    # 2: ... once: a second free of it finds nothing
    if dma_run_take(5, NIC, BASE, 2).is_some()
        return 2
    # 3: a freed range comes back first fit from the front, for that process
    # and device only, and with an IOVA only when the device has one
    dma_hole_put(5, NIC, range(BASE, IOVA, 4))
    if dma_hole_take(6, NIC, 1, true).is_some() or dma_hole_take(5, BLK, 1, true).is_some() or dma_hole_take(5, NIC, 1, false).is_some()
        return 3
    if not took(dma_hole_take(5, NIC, 1, true), BASE, IOVA, 1)
        return 3
    if not took(dma_hole_take(5, NIC, 2, true), BASE + P, IOVA + P, 2)
        return 4
    # 5: a run bigger than every hole takes nothing, and the rest stays
    if dma_hole_take(5, NIC, 2, true).is_some() or not took(dma_hole_take(5, NIC, 1, true), BASE + 3 * P, IOVA + 3 * P, 1)
        return 5
    # 6: holes that touch in VA and IOVA merge, on either side
    dma_hole_put(5, NIC, range(BASE + 2 * P, IOVA + 2 * P, 1))
    dma_hole_put(5, NIC, range(BASE, IOVA, 2))
    dma_hole_put(5, NIC, range(BASE + 3 * P, IOVA + 3 * P, 1))
    if not took(dma_hole_take(5, NIC, 4, true), BASE, IOVA, 4)
        return 6
    # 7: touching in VA but not in IOVA does not merge
    dma_hole_put(5, NIC, range(BASE, IOVA, 1))
    dma_hole_put(5, NIC, range(BASE + P, IOVA + 9 * P, 1))
    if dma_hole_take(5, NIC, 2, true).is_some()
        return 7
    # 8: the bump floor is past every hole of the process, any device
    dma_hole_put(5, BLK, range(BASE + 20 * P, 0, 3))
    if dma_hole_floor(5, BASE) != BASE + 23 * P or dma_hole_floor(6, BASE) != BASE
        return 8
    # 9: holes without an IOVA merge on VA alone and split without one
    dma_hole_put(5, BLK, range(BASE + 23 * P, 0, 1))
    if not took(dma_hole_take(5, BLK, 1, false), BASE + 20 * P, 0, 1) or not took(dma_hole_take(5, BLK, 3, false), BASE + 21 * P, 0, 3)
        return 9
    # 10: exit takes every live run of the pid and drops its holes; another
    # pid keeps its own
    if not dma_run_add(run(5, NIC, BASE + 40 * P, 0, 1)) or not dma_run_add(run(5, BLK, BASE + 41 * P, 0, 1)) or not dma_run_add(run(9, NIC, BASE, 0, 1))
        return 10
    var n: i32 = 0
    while dma_run_take_pid(5).is_some()
        n = n + 1
    dma_holes_drop_pid(5)
    if n != 2 or dma_runs_held(5) != 0 or dma_runs_held(9) != 1 or dma_hole_floor(5, BASE) != BASE
        return 10
    # 11: 64 live runs fill the table; the 65th is refused before anything
    var k: u64 = 1
    while k < 64
        if not dma_run_add(run(9, NIC, BASE + k * P, 0, 1))
            return 11
        k = k + 1
    if dma_run_room() or dma_run_add(run(9, NIC, BASE + 99 * P, 0, 1))
        return 11
    # 12: a full free list drops the range (never reused) and keeps the rest
    var h: u64 = 0
    while h < 33
        dma_hole_put(3, NIC, range(BASE + h * 2 * P, 0, 1))
        h = h + 1
    if dma_runs_held(3) != 32 or dma_hole_take(3, NIC, 1, false).is_none()
        return 12
    # 13: driver_quiesce takes the runs of one pid and device only (#4733)
    while dma_run_take_pid(9).is_some()
        n = n + 1
    if not dma_run_add(run(4, NIC, BASE, 0, 1)) or not dma_run_add(run(4, BLK, BASE + P, 0, 1)) or not dma_run_add(run(2, NIC, BASE, 0, 1))
        return 13
    let d: DmaRun = match dma_run_take_device(4, NIC)
        Some(x) => x
        None => return 13
    if d.object_id != NIC or d.pid != 4 or dma_run_take_device(4, NIC).is_some()
        return 13
    if dma_runs_held(4) != 1 or dma_runs_held(2) != 1
        return 13
    0
"""


@pytest.mark.integration
def test_dma_runs_and_free_list(tmp_path):
    assert _run(tmp_path, RUNS_PROGRAM) == 0


def _body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
    assert m, f"no fn {name}"
    return m.group(0)


@pytest.mark.unit
def test_free_waits_for_the_iotlb_before_the_pmm():
    """§5: the IOVA leaves the domain and the unit confirms it before the CPU
    leaves go and the frames reach the PMM; then both ranges go back on the
    free list. Unconfirmed: the leaves are quarantined (PTE_DEVICE), the
    frames and the IOVA recorded on dma_quarantine, nothing freed, nothing
    reused."""
    body = _body(DRIVER.read_text(), "drv_dma_free")
    assert "held_object(pid, irq_handle, CAP_TYPE_IRQ)" in body
    assert body.index("CAP_TYPE_IRQ") < body.index("dma_run_take(")
    leave = body.index("run_left_domain(")
    unmap = body.index("unmap_run(")
    assert leave < unmap < body.index("dma_free_pages(") < body.index("dma_hole_put(")
    assert "quarantine_leaves(" in body
    assert re.search(r"dma_quarantine_iova\(run\.phys, run\.pages, run\.iova\)", body)


@pytest.mark.unit
def test_alloc_reuses_a_hole_and_keeps_the_bump_above_holes():
    """DrvDmaAlloc takes a hole of this process and device first; a fresh run
    starts past every hole (dma_hole_floor); a failure after the domain
    confirmed gives the range back, an unconfirmed one quarantines it with
    its IOVA; a live run is recorded so DrvDmaFree can find it."""
    src = DRIVER.read_text()
    body = _body(src, "drv_dma_alloc")
    assert "dma_run_room()" in body and body.index("dma_run_room()") < body.index("dma_alloc_zeroed(")
    assert "dma_hole_take(pid, object_id, pages, dom != 0)" in body
    assert "dma_hole_floor(pid," in _body(src, "dma_window_room")
    assert "dma_domain_enter_at(dom, range.iova, phys, pages)" in body
    assert re.search(r"VtdEnter\.Stuck =>\s+dma_quarantine_iova\(phys, pages, range\.iova\)", body)
    assert "dma_run_add(" in body


@pytest.mark.unit
def test_quarantined_leaf_is_kept_and_counted():
    """A quarantined leaf is not present (a stale pointer faults) but keeps
    PTE_DEVICE and the frame: vmm_free_user_pt never frees it, and
    vmm_slot_end counts the page so the VA is not handed out again."""
    src = VMM.read_text()
    q = _body(src, "vmm_quarantine_leaf_in")
    assert "| PTE_DEVICE" in q and "PTE_PRESENT" not in q.split("vmm_set_entry", 1)[1].split("\n", 1)[0]
    assert "PTE_DEVICE" in _body(src, "vmm_slot_end")


@pytest.mark.unit
def test_exit_settles_every_live_run_before_the_pml4_goes():
    """A driver's exit takes each live run out of its domain (quarantining
    one the unit doesn't confirm) and forgets its holes, before
    vmm_free_pml4 frees the confirmed frames once."""
    body = _body(PROCESS.read_text(), "sys_exit_impl")
    assert body.index("drv_dma_process_end(") < body.index("vmm_free_pml4(my_pml4)")
