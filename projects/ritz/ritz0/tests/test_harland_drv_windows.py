"""DrvMmioMap's window records and DrvDmaAlloc's leaves (AGAST #4720, #4721,
RING1_DRIVER.md §5 "MMIO and DMA syscalls").

drivers/virtio/window.ritz keeps one record per virtio capability window
(page base, byte offset, length, notify multiplier, and the device's MSI-X
table and PBA ranges); the record is the CAP_TYPE_MMIO object DrvMmioMap
(221) maps. It imports nothing but ritzlib.option, so the behaviour test
compiles the real module into a host program:

* a grant is the complete pages covering the window's bytes;
* a window any of whose pages holds a byte of the MSI-X table or PBA is
  guarded (DrvMmioMap returns Errno.Inval and maps nothing);
* ids start at 1, are never reused, and 0 names no window.

The syscalls themselves need a page table and a process, so their proof is
the drv-mmio-map and drv-dma-alloc boot tests (postinit.ritz) and indium's
drv_refuse_test; the source checks below pin what those can't see from
ring 3: the leaf flags, and that neither path goes through the region table.
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
WINDOW = KERNEL_SRC / "drivers" / "virtio" / "window.ritz"
COMMON = KERNEL_SRC / "drivers" / "virtio" / "common.ritz"
DRIVER = KERNEL_SRC / "syscall" / "runtime" / "driver.ritz"


def _compile(tmp_path, path, name, extra=()):
    ll = tmp_path / f"{name}.ll"
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    proc = run_ritz0([str(path), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
    assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
    return ll


def _run(tmp_path, src):
    """Compile the real window.ritz with `src`, link, run: the exit status."""
    mod = tmp_path / "tree" / "drivers" / "virtio" / "window.ritz"
    mod.parent.mkdir(parents=True)
    mod.write_text(WINDOW.read_text())
    (tmp_path / "t.ritz").write_text(src)
    objs = [str(_compile(tmp_path, tmp_path / "t.ritz", "t")),
            str(_compile(tmp_path, mod, "window", ("--no-runtime",)))]
    exe = tmp_path / "t"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                            "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60, check=False).returncode


# Exit status: the number of the first claim that failed, 0 if all held.
WINDOWS = """\
import ritzlib.option
import drivers.virtio.window

const BAR: u64 = 0xFEB00000
const TABLE: u64 = 0xFEB01000       # 3 entries: 48 bytes
const PBA: u64 = 0xFEB03800       # a page of its own

fn none_found(id: u64) -> bool
    vio_window_find(id).is_none()

fn pages(id: u64) -> u64
    match vio_window_find(id)
        Some(w) => vio_window_pages(w)
        None => 0

fn guarded(id: u64) -> bool
    match vio_window_find(id)
        Some(w) => vio_window_guarded(w)
        None => false

fn queue_regs(id: u64) -> bool
    match vio_window_find(id)
        Some(w) => vio_window_queue_regs(w)
        None => false

# The device's common configuration (queue addresses) is at BAR+0x20, 0x38
# bytes; its requester is 00:03.0.
fn add(phys: u64, len: u64) -> u64
    let t: PhysRange = phys_range(TABLE, 48)
    let p: PhysRange = phys_range(PBA, 8)
    match vio_window_add(phys, len, 4, t, p, phys_range(BAR + 0x20, 0x38), 0x18)
        Some(id) => id
        None => 0

fn main() -> i32
    # 1: a window inside one page, off its start: one page, offset kept
    let common: u64 = add(BAR + 0x20, 0x38)
    if common != 1 or pages(common) != 1
        return 1
    let w: VioWindow = match vio_window_find(common)
        Some(x) => x
        None => return 1
    if w.page_base != BAR or w.offset != 0x20 or w.length != 0x38 or w.notify_multiplier != 4 or w.sid != 0x18
        return 2
    # 3: bytes that straddle a page boundary take both pages
    let straddle: u64 = add(BAR + 0x4FF0, 0x20)
    if pages(straddle) != 2
        return 3
    # 4: neither touches the table's or the PBA's page
    if guarded(common) or guarded(straddle)
        return 4
    # 16: the common configuration's window holds queue-address registers,
    # and so does any window sharing its page; one past that page does not
    # (AGAST #4724)
    let isr: u64 = add(BAR + 0x800, 4)
    if not queue_regs(common) or not queue_regs(isr) or queue_regs(straddle)
        return 16
    # 5: a window sharing the table's page is guarded, though no byte of
    # the window itself is a table byte
    let beside_table: u64 = add(TABLE + 0x100, 0x10)
    if not guarded(beside_table)
        return 5
    # 6: so is one whose last page holds the PBA (and not the table)
    let into_pba: u64 = add(BAR + 0x2F00, 0x200)
    if pages(into_pba) != 2 or not guarded(into_pba)
        return 6
    # 7: a window ending right before the table's page is not
    let below: u64 = add(TABLE - 0x10, 0x10)
    if guarded(below)
        return 7
    # 8: no table and no PBA: nothing guards
    let bare: u64 = match vio_window_add(TABLE, 16, 0, phys_range_none(), phys_range_none(), phys_range_none(), 0)
        Some(id) => id
        None => 0
    if bare == 0 or guarded(bare) or queue_regs(bare)
        return 8
    # 9: length 0 records nothing; id 0 and unknown ids name nothing
    if vio_window_add(BAR, 0, 0, phys_range_none(), phys_range_none(), phys_range_none(), 0).is_some()
        return 9
    if not none_found(0) or not none_found(999)
        return 10
    # 15: a table ending exactly where the window's first page starts
    # does not guard it (checked before the table fills)
    let edge: u64 = match vio_window_add(BAR + 0x6000, 16, 0, phys_range(BAR + 0x5FF0, 0x10), phys_range_none(), phys_range_none(), 0)
        Some(id) => id
        None => 0
    if edge == 0 or guarded(edge) or not vio_window_remove(edge)
        return 15
    # 11: a removed id is gone and is not handed out again
    if not vio_window_remove(below) or not none_found(below) or vio_window_remove(below)
        return 11
    let again: u64 = add(BAR, 16)
    if again == below or again == 0
        return 12
    # 13: sixteen records fill the table; the seventeenth is refused
    var n: i32 = 7                  # live: common .. bare and isr, less below, plus again
    while n < 16
        if add(BAR, 16) == 0
            return 13
        n = n + 1
    if add(BAR, 16) != 0
        return 14
    0
"""


@pytest.mark.integration
def test_window_pages_guard_and_ids(tmp_path):
    assert _run(tmp_path, WINDOWS) == 0


def _body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
    assert m, f"no fn {name}"
    return m.group(0)


def test_probe_records_every_window():
    """vio_find_mmio_caps records each capability window it maps, with the
    device's MSI-X table and PBA, so a grant never needs the shared page."""
    src = COMMON.read_text()
    assert "vio_note_window(" in _body(src, "vio_find_mmio_caps")
    note = _body(src, "vio_note_window")
    assert "vio_window_add(" in note and "PCI_CAP_MSIX" in note
    # AGAST #4724: with the queue-address registers and the requester
    assert "vio_common_range(pci_dev)" in note and "pci_dev_sid(pci_dev)" in note
    assert "VIRTIO_PCI_CAP_COMMON_CFG" in _body(src, "vio_common_range")


def test_queue_register_grant_needs_an_isolated_device():
    """AGAST #4724: DrvMmioMap maps a page holding the queue-address
    registers only for a device whose requester is in a private DMA domain,
    and refuses it (Errno.Perm) before mapping anything."""
    body = _body(DRIVER.read_text(), "drv_mmio_map")
    m = re.search(r"if vio_window_queue_regs\(window\) and not dma_requester_isolated\(window\.sid\)\s+return Errno\.Perm", body)
    assert m, body
    assert body.index("vio_window_queue_regs") < body.index("map_run(")


def test_dma_alloc_enters_the_holders_domain():
    """AGAST #4724: DrvDmaAlloc maps its run into the IRQ object's device
    domain and copies out that IOVA; a refused entry frees the run, a stuck
    one (an unconfirmed invalidation) quarantines it, and a CPU mapping that
    fails after the entry takes the run out of the domain first."""
    body = _body(DRIVER.read_text(), "drv_dma_alloc")
    assert "irq_object_domain(object_id)" in body
    enter = body.index("dma_domain_enter(dom, phys, pages)")
    assert enter < body.index("map_run(")
    assert re.search(r"VtdEnter\.Entered\(v\) => iova = v", body)
    assert re.search(r"VtdEnter\.Refused =>\s+dma_free_pages\(phys", body)
    assert re.search(r"VtdEnter\.Stuck =>\s+dma_quarantine\(phys, pages\)", body)
    assert re.search(r"if dom != 0 and not dma_domain_leave\(dom, iova, pages\)\s+dma_quarantine\(phys, pages\)", body)
    assert "(*out).iova = iova" in body


def test_mmio_leaves_are_uncached_device_user_nx():
    """§5: PTE_WRITABLE | PTE_USER | PTE_WRITE_THROUGH | PTE_CACHE_DISABLE |
    PTE_DEVICE | nx, the kernel's UC MMIO type plus user and device."""
    body = _body(DRIVER.read_text(), "drv_mmio_leaf")
    for flag in ("PTE_WRITABLE", "PTE_USER", "PTE_WRITE_THROUGH", "PTE_CACHE_DISABLE", "PTE_DEVICE", "vmm_nx_flag()"):
        assert flag in body, flag


def test_dma_leaves_are_write_back_owned_ram():
    """§5: PTE_WRITABLE | PTE_USER | nx and nothing else: write-back, and no
    PTE_DEVICE, so a process's exit frees the run once (vmm_free_user_pt)."""
    body = _body(DRIVER.read_text(), "drv_dma_leaf")
    for flag in ("PTE_WRITABLE", "PTE_USER", "vmm_nx_flag()"):
        assert flag in body, flag
    for flag in ("PTE_WRITE_THROUGH", "PTE_CACHE_DISABLE", "PTE_DEVICE", "PTE_SHM"):
        assert flag not in body, flag


def test_dma_alloc_is_not_a_region():
    """The run is one dma_alloc_pages, zeroed, and not in dma_regions: the
    process's PML4 owns it, and exit frees it once."""
    src = DRIVER.read_text()
    body = _body(src, "drv_dma_alloc")
    assert "dma_alloc_zeroed(" in body
    assert not re.search(r"\bdma_alloc\(", src)
