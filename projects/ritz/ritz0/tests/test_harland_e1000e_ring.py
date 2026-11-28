"""The e1000e as netd's NIC: the kernel's probe, grant and quiesce, and
netd's one match on the kind (AGAST #4893; harland docs/E1000E.md "Shape:
one netd, chosen at boot", "Kernel side").

A translating boot hands /bin/netd one NIC: a virtio-net, else an e1000e
(8086:10d3, QEMU's 82574L; 8086:15a1, the X99's I218-V). The e1000e probe
turns bus master off, makes the NIC's private domain and only then sets bus
master, runs the fault probe, aims MSI-X entries 0-2 at one vector on the
BSP and records BAR0, whole, as the one CAP_TYPE_MMIO window: never BAR3,
the MSI-X table. DriverBoot.nic names the kind, and netd runs its generic
loop on VirtioNic or E1000eNic. netd's death resets the e1000e (IMC, GIO
master disable and GIO_MASTER_EN clear, CTRL.RST and its self-clear) and
counts the reset complete only when both waits succeeded.

The behaviour is tools/test_msix_boot.sh's e1000e and e1000e-shell boots
(their verdicts are host-tested in projects/ritz/tools/test_ci_msix_boot.py),
and netd's kind check is system/test/test_nicboot.ritz. These checks pin the
order and the guards the boots can't observe.
"""

import re
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).resolve().parents[1]
HARLAND = RITZ0_DIR.parent.parent / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
E1000E = KERNEL_SRC / "drivers" / "e1000e.ritz"
NIC = KERNEL_SRC / "drivers" / "nic.ritz"
PCI = KERNEL_SRC / "drivers" / "pci.ritz"
IR = KERNEL_SRC / "drivers" / "iommu" / "ir.ritz"
RING1 = KERNEL_SRC / "net" / "ring1.ritz"
DRIVER = KERNEL_SRC / "syscall" / "runtime" / "driver.ritz"
NETD = HARLAND / "system" / "src" / "netd.ritz"
NICBOOT = HARLAND / "system" / "src" / "nicboot.ritz"
BOOT_ABI = HARLAND / "driver_abi" / "src" / "boot.ritz"


def _code(path):
    return "\n".join(l.split("#", 1)[0].rstrip() for l in path.read_text().splitlines())


def _fn_body(src, name):
    m = re.search(rf"^(?:pub )?fn {name}(?:<[^>]*>)?\(.*?(?=^\S)", src + "\nEND", re.M | re.S)
    assert m, f"no fn {name}"
    return m.group(0)


def _in_order(body, *needles):
    at = -1
    for n in needles:
        i = body.find(n, at + 1)
        assert i > at, f"{n!r} missing or out of order"
        at = i


def _check_one_nic_a_boot_virtio_net_first():
    """The probe order, and the requesters TE holds out of the identity
    domain, are the same NIC's."""
    prepare = _fn_body(_code(RING1), "net_ring1_prepare")
    _in_order(prepare, "virtio_net_ring1_probe()", "None => e1000e_ring1_probe()", "process_create_init()")
    ring = _fn_body(_code(PCI), "pci_find_ring_nic")
    _in_order(ring, "pci_find_virtio(VIRTIO_DEVICE_NET)", "return Some(vnet)", "pci_find_e1000e()")
    e1k = _fn_body(_code(PCI), "pci_find_e1000e")
    assert "E1000E_DEVICE_82574L" in e1k and "E1000E_DEVICE_I218V" in e1k
    assert re.search(r"E1000E_DEVICE_82574L: u16 = 0x10D3\b", PCI.read_text())
    assert re.search(r"E1000E_DEVICE_I218V: u16 = 0x15A1\b", PCI.read_text())
    assert "pci_find_ring_nic()" in _fn_body(_code(IR), "nic_requesters")


def _check_the_probe_isolates_before_bus_master_and_routes_msix_at_the_bsp():
    probe = _fn_body(_code(E1000E), "e1000e_ring1_probe")
    assert "not dma_translation_on()" in probe
    _in_order(probe, "pci_disable_bus_master(dev)", "vmm_map_mmio(bar0, E1000E_BAR0_LEN as u64)",
              "wr(regs, E1K_REG_IMC, E1K_IMC_ALL)", "nic_private_domain(dev)",
              "e1000e_fault_probe(regs, dom, sid)", "nic_ring1_allowed(dev, dom)",
              'nic_msix_bsp(dev, @e1000e_msix, "e1000e",', "vio_window_add(")
    # A NIC whose fault probe failed is handed out only once it resets.
    assert re.search(r"if not e1000e_fault_probe\(regs, dom, sid\)\n\s+match e1000e_reset\(regs\)\n\s+E1000eReset\.Done => pass", probe)
    # The kernel never turns bus master on itself: nic_private_domain does,
    # after the domain.
    assert "pci_enable_bus_master(" not in _code(E1000E)


def _check_bar0_whole_is_the_one_window_and_never_the_msix_table():
    probe = _fn_body(_code(E1000E), "e1000e_ring1_probe")
    assert "(*dev).bar_is_io[0] != 0 or bar0 == 0 or (*dev).bar_size[0] < E1000E_BAR0_LEN as u64" in probe
    # BAR0's queue-address registers: DrvMmioMap grants the window only to
    # an isolated requester; the MSI-X table and PBA guard it.
    assert ("vio_window_add(bar0, E1000E_BAR0_LEN as u64, 0, guard.table, guard.pba, "
            "phys_range(bar0, E1000E_BAR0_LEN as u64), sid)") in probe
    assert "if vio_window_guarded(w)\n                return nic_ring1_refused(" in probe
    assert "window_count: 1" in probe
    assert "grant.window_ids[0] = window" in probe and "grant.window_types[0] = E1000E_WINDOW_BAR0" in probe
    assert "kind: NIC_KIND_E1000E" in probe and "reset: NicReset.E1000e(regs)" in probe
    # BAR3 is named nowhere: the table is msix.ritz's mapping.
    assert "bar[3]" not in _code(E1000E)


def _check_the_fault_probe_names_an_unmapped_iova_and_resets_after():
    body = _fn_body(_code(E1000E), "e1000e_fault_probe")
    _in_order(body, "dma_domain_hole(dom)", "dma_domain_enter(dom, phys, 1)", "addr: hole",
              "wr(regs, E1K_REG_TCTL, E1K_TCTL_EN | E1K_TCTL_PSP)", "nic_faults_drain()",
              "memory_barrier()", "wr(regs, E1K_REG_TDT, 1)", "nic_fault_seen(sid, hole)",
              "e1000e_reset(regs)")
    # The ring page is freed only once the NIC reset and the domain let go.
    assert re.search(r"if reset and dma_domain_leave\(dom, ring, 1\)\n\s+dma_free_pages\(phys, 1\)\n\s+else\n\s+dma_quarantine\(phys, 1\)", body)


def _check_the_reset_is_complete_only_when_both_waits_succeed():
    body = _fn_body(_code(E1000E), "e1000e_reset")
    _in_order(body, "wr(regs, E1K_REG_IMC, E1K_IMC_ALL)",
              "E1K_CTRL_GIO_MASTER_DISABLE",
              "wait_clear(regs, E1K_REG_STATUS, E1K_STATUS_GIO_MASTER_EN, E1K_MASTER_US)",
              "return E1000eReset.MasterStuck",
              "E1K_CTRL_RST",
              "wait_clear(regs, E1K_REG_CTRL, E1K_CTRL_RST, E1K_RESET_US)",
              "return E1000eReset.ResetStuck",
              "E1000eReset.Done")
    assert body.count("E1000eReset.Done") == 1
    # Each wait guards what follows it: its timeout returns before the next
    # step.
    assert ("if not wait_clear(regs, E1K_REG_STATUS, E1K_STATUS_GIO_MASTER_EN, E1K_MASTER_US)\n"
            "        return E1000eReset.MasterStuck") in body
    assert ("if not wait_clear(regs, E1K_REG_CTRL, E1K_CTRL_RST, E1K_RESET_US)\n"
            "        return E1000eReset.ResetStuck") in body
    wait = _fn_body(_code(E1000E), "wait_clear")
    assert "while (rd(regs, off) & bit) != 0" in wait and "if deadline_passed(deadline)\n            return false" in wait
    src = E1000E.read_text()
    # 80 ms, Linux's MASTER_DISABLE_TIMEOUT; 100 ms for the self-clear.
    assert re.search(r"^const E1K_MASTER_US: u64 = 80000\b", src, re.M)
    assert re.search(r"^const E1K_RESET_US: u64 = 100000\b", src, re.M)
    assert re.search(r"^const E1K_CTRL_GIO_MASTER_DISABLE: u32 = 1 << 2\b", src, re.M)
    assert re.search(r"^const E1K_STATUS_GIO_MASTER_EN: u32 = 1 << 19\b", src, re.M)
    assert re.search(r"^const E1K_CTRL_RST: u32 = 1 << 26\b", src, re.M)
    assert re.search(r"^const E1K_REG_IMC: u64 = 0x00D8\b", src, re.M)


def _check_drv_device_records_the_kind_and_quiesce_resets_by_it():
    src = _code(DRIVER)
    assert "reset: NicReset" in src
    assert "pub fn drv_device_bind(object_id: u64, reset: NicReset, msix_table_va: u64, msix_entries: u32) -> bool" in src
    q = _fn_body(src, "quiesce_device")
    _in_order(q, "msix_mask_entries(dev.msix_table_va, dev.msix_entries)", "device_reset(dev.reset)",
              "run_left_domain(")
    # Only Done is a completed reset: a stuck wait is logged by name.
    reset = _fn_body(src, "device_reset")
    assert "E1000eReset.Done => DeviceReset.Done" in reset
    assert "_ => DeviceReset.Stuck(e1000e_reset_name(end))" in reset
    assert 'klog("stuck: ")' in q
    # netd's restart still asks only drv_device_fit: a stuck e1000e reset
    # leaves the device unfit, as a virtio status that never read 0 does.
    assert "if not drv_device_fit(ring1_obj)\n        return Respawn.Unfit" in _fn_body(_code(RING1), "net_netd_respawn")


def _check_driver_boot_carries_the_kind():
    abi = BOOT_ABI.read_text()
    assert re.search(r"^\s+nic: u16\s+# NIC_KIND_\*", abi, re.M)
    assert "_pad: u16" not in abi.split("pub struct DriverBoot", 1)[1].split("pub fn", 1)[0]
    grant = _fn_body(_code(RING1), "ring1_grant_to")
    assert "boot.nic = g.kind" in grant
    choice = _fn_body(_code(NICBOOT), "nic_choice")
    assert "match b.nic" in choice and "_ => Err(BootRefused.Kind)" in choice


def _check_netd_matches_the_kind_once_and_runs_one_generic_loop():
    netd = _code(NETD)
    main = _fn_body(netd, "main")
    assert main.count("match choice") == 1
    assert "Ok(_) => run<VirtioNic>(@&g_virtio)" in main and "Ok(_) => run<E1000eNic<MmioRegs>>(@&g_e1000e)" in main
    assert "fn run<N: Nic + FirstDma>(svc: @&NetSvc<N>) -> i32" in netd
    assert "var g_e1000e: NetSvc<E1000eNic<MmioRegs>>" in netd
    # No kind test past the match: every pass is the instance's own code.
    for fn in ("run", "serve", "seat_loop", "take_over"):
        body = _fn_body(netd, fn)
        assert "NicChoice" not in body and "NIC_KIND" not in body, fn
    up = _fn_body(netd, "e1000e_up")
    _in_order(up, "drv_mmio_map(w.handle)", "E1000eDma {", "g_e1000e.nic.up(MmioRegs { base: bar0 }, runs, e1000e_msix(g_boot))",
              "publish_up<E1000eNic<MmioRegs>>(@&g_e1000e)?")


# One case, a row per rule: the ritz0 suite's case count is capped
# (docs/TESTING.md, "What a ritz0 pytest case costs").
_RULES = [
    _check_one_nic_a_boot_virtio_net_first,
    _check_the_probe_isolates_before_bus_master_and_routes_msix_at_the_bsp,
    _check_bar0_whole_is_the_one_window_and_never_the_msix_table,
    _check_the_fault_probe_names_an_unmapped_iova_and_resets_after,
    _check_the_reset_is_complete_only_when_both_waits_succeed,
    _check_drv_device_records_the_kind_and_quiesce_resets_by_it,
    _check_driver_boot_carries_the_kind,
    _check_netd_matches_the_kind_once_and_runs_one_generic_loop,
]


@pytest.mark.unit
def test_e1000e_ring_rules():
    for rule in _RULES:
        rule()
