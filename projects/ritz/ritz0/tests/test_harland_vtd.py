"""Harland's VT-d interrupt remapping formats and DMAR parsing (AGAST #4316).

An MSI address and an I/O APIC redirection entry carry an 8-bit APIC ID; past
APIC ID 254 a device interrupt reaches its CPU on bare metal only through
interrupt remapping: the message carries a handle into the interrupt
remapping table, whose entry (IRTE) holds a 32-bit x2APIC destination when
extended interrupt mode (EIM) is on.

drivers/iommu/dmar.ritz holds the parts with no hardware: the DMAR table
parser, the IRTE / remappable MSI / remappable redirection-entry encodings,
the IRT handle each source uses, and the register values and queued-
invalidation descriptors drivers/iommu/vtd.ritz writes. The behaviour test
compiles it with a synthetic DMAR table (two remapping units, an I/O APIC
scope, a scope through a bridge, a junk structure) into a host program whose
exit code names the failed claim. Source-level tests pin how the kernel uses
it: MSI-X and the I/O APIC switch to the remappable formats when remapping
is on, and remapping comes up before the I/O APIC is programmed.
tools/test_irq_dest_boot.sh boots it on q35 with -device intel-iommu.

DMA remapping (AGAST #4722): the same host program checks the RMRR parse and
the translation formats (CAP, root and context entries, second-level entries,
context-cache and IOTLB descriptors, fault records); a second one runs the
real vtd.ritz against an emulated unit, mapping and unmapping IOVAs,
attaching and detaching a requester, reading a fault record, and checking
the invalidations each step queues and that a unit which stops answering
ends the wait with a reported timeout. TE is never set.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"
DMAR = KERNEL_SRC / "drivers" / "iommu" / "dmar.ritz"
VTD = KERNEL_SRC / "drivers" / "iommu" / "vtd.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"
IR = KERNEL_SRC / "drivers" / "iommu" / "ir.ritz"
VIRTIO_COMMON = KERNEL_SRC / "drivers" / "virtio" / "common.ritz"
VIRTIO_NET = KERNEL_SRC / "drivers" / "virtio" / "net.ritz"
NIC = KERNEL_SRC / "drivers" / "nic.ritz"
E1000E = KERNEL_SRC / "drivers" / "e1000e.ritz"

PROGRAM = """\
import drivers.iommu.dmar

var t: [192]u8

fn put8(off: i32, v: u32)
    t[off] = (v & 0xFF) as u8

fn put16(off: i32, v: u32)
    put8(off, v)
    put8(off + 1, v >> 8)

fn put32(off: i32, v: u32)
    put16(off, v)
    put16(off + 2, v >> 16)

fn put64(off: i32, v: u64)
    put32(off, (v & 0xFFFFFFFF) as u32)
    put32(off + 4, (v >> 32) as u32)

# DMAR: header (48) | DRHD A (16 + I/O APIC scope 8 + bridged scope 10 = 34)
#      | RMRR (type 1, 24 bytes, skipped) | DRHD B, INCLUDE_PCI_ALL (16)
fn build(len: u32)
    put32(0, 0x52414D44)
    put32(4, len)
    put8(36, 46)
    put8(37, 0x03)            # INTR_REMAP | X2APIC_OPT_OUT
    put16(48, 0)              # DRHD A
    put16(50, 34)
    put8(52, 0)
    put16(54, 0)
    put64(56, 0xFED90000)
    put8(64, 3)               # scope: I/O APIC, enumeration ID 2, bus 0xFF, 1e.7
    put8(65, 8)
    put8(68, 2)
    put8(69, 0xFF)
    put8(70, 0x1E)
    put8(71, 7)
    put8(72, 3)               # scope: I/O APIC 9 behind a bridge (two path steps)
    put8(73, 10)
    put8(76, 9)
    put8(77, 0)
    put8(78, 1)
    put8(79, 0)
    put8(80, 0)
    put8(81, 0)
    put16(82, 1)              # RMRR: skipped
    put16(84, 24)
    put16(106, 0)             # DRHD B
    put16(108, 16)
    put8(110, 1)
    put16(112, 1)
    put64(114, 0x1FED91000)

# DMAR with RMRRs (AGAST #4722): header (48) | DRHD (16) | RMRR 0x7F000000-
# 0x7F00FFFF with an endpoint 00:14.0, an endpoint behind a bridge and an
# I/O APIC scope (50) | RMRR ending before it starts (24) | RMRR 0x9000-
# 0x9FFF on segment 1 for 03:02.1 (32)
fn build_rmrr(len: u32)
    var i: i32 = 0
    while i < 192
        t[i] = 0
        i = i + 1
    put32(0, 0x52414D44)
    put32(4, len)
    put8(37, 1)
    put16(48, 0)              # DRHD, INCLUDE_PCI_ALL
    put16(50, 16)
    put8(52, 1)
    put64(56, 0xFED90000)
    put16(64, 1)              # RMRR
    put16(66, 50)
    put64(72, 0x7F000000)
    put64(80, 0x7F00FFFF)
    put8(88, 1)               # endpoint 00:14.0
    put8(89, 8)
    put8(94, 0x14)
    put8(96, 1)               # endpoint behind a bridge (two path steps)
    put8(97, 10)
    put8(102, 1)
    put8(106, 3)              # an I/O APIC scope: not a DMA requester
    put8(107, 8)
    put8(110, 2)
    put8(111, 0xFF)
    put8(112, 0x1E)
    put8(113, 7)
    put16(114, 1)             # RMRR: limit below base, dropped
    put16(116, 24)
    put64(122, 0x80000000)
    put64(130, 0x7FFFFFFF)
    put16(138, 1)             # RMRR on segment 1
    put16(140, 32)
    put16(144, 1)
    put64(146, 0x9000)
    put64(154, 0x9FFF)
    put8(162, 1)              # endpoint 03:02.1
    put8(163, 8)
    put8(167, 3)
    put8(168, 2)
    put8(169, 1)

fn main() -> i32
    build(122)
    if dmar_parse(@t[0], 122) != 2 or dmar_num_units != 2
        return 1
    if (dmar_flags & DMAR_INTR_REMAP) == 0 or (dmar_flags & DMAR_X2APIC_OPT_OUT) == 0
        return 2
    if dmar_unit_base[0] != 0xFED90000 or dmar_unit_base[1] != 0x1FED91000
        return 3
    if dmar_unit_include_all[0] != 0 or dmar_unit_include_all[1] != 1 or dmar_unit_segment[1] != 1
        return 4
    # I/O APIC 2: bus 0xFF, device 0x1E, function 7; I/O APIC 9 can't be named
    if dmar_num_ioapics != 2 or dmar_ioapic_source_id(2) != 0xFFF7 or dmar_ioapic_unit[0] != 0
        return 5
    if dmar_ioapic_source_id(9) != DMAR_SID_NONE or dmar_ioapic_source_id(4) != DMAR_SID_NONE
        return 6
    # not a DMAR / too short / header longer than the bytes we have
    t[0] = 0x41
    if dmar_parse(@t[0], 122) != -1 or dmar_num_units != 0
        return 7
    build(122)
    if dmar_parse(@t[0], 40) != -1 or dmar_parse(@t[0], 200) != -1
        return 8
    # a zero-length structure ends the parse without looping
    put16(50, 0)
    if dmar_parse(@t[0], 122) != 0
        return 9
    build(122)
    # a structure running past the end is dropped
    put16(108, 40)
    if dmar_parse(@t[0], 122) != 1
        return 10

    # IRTE: present, vector 23:16, x2APIC destination 63:32 or xAPIC 47:40
    if irte_lo(0x41, 256, false, true) != 0x0000010000410001
        return 11
    if irte_lo(0x21, 3, true, false) != 0x0000030000210011
        return 12
    if irte_dest(irte_lo(0x41, 0x12345678, false, true), true) != 0x12345678 or irte_vector(irte_lo(0x41, 7, false, true)) != 0x41
        return 13
    if irte_dest(irte_lo(0x41, 0x1F7, false, false), false) != 0xF7
        return 14
    # source validation: SID in 15:0, SVT = 1 in 19:18; none without a SID
    if irte_hi(0x0108, IRTE_SVT_VERIFY_SID) != 0x40108 or irte_hi(DMAR_SID_NONE, IRTE_SVT_VERIFY_SID) != 0
        return 15
    if irte_hi(0x0108, IRTE_SVT_NONE) != 0
        return 16
    # remappable MSI address: handle 14:0 in 19:5, bit 15 in 2, format bit 4
    if msi_addr_remap(0) != 0xFEE00010 or msi_addr_remap(0xC0) != 0xFEE01810 or msi_addr_remap(0x8001) != 0xFEE00034
        return 17
    if msi_addr_handle(msi_addr_remap(0xC5)) != 0xC5 or msi_addr_handle(msi_addr_remap(0xFFFF)) != 0xFFFF
        return 18
    if not msi_addr_is_remap(msi_addr_remap(3)) or msi_addr_is_remap(0xFEE05000)
        return 19
    # remappable RTE: format bit 48, handle 63:49 and bit 11; vector kept
    if ioapic_rte_remap_hi(1) != 0x00030000 or ioapic_rte_remap_hi(0x7FFF) != 0xFFFF0000
        return 20
    if ioapic_rte_remap_lo(33, 1, false) != 33 or ioapic_rte_remap_lo(36, 0x8004, true) != 0x10824
        return 21
    if ioapic_rte_handle(ioapic_rte_remap_hi(0x8004), ioapic_rte_remap_lo(36, 0x8004, false)) != 0x8004
        return 22
    if not ioapic_rte_is_remap(ioapic_rte_remap_hi(4)) or ioapic_rte_is_remap(0x03000000)
        return 23
    # handles: pins and MSI vectors never share an entry
    if ir_handle_ioapic(1) != 1 or ir_handle_ioapic(23) != 23 or ir_handle_msi(64) != 192 or ir_handle_msi(79) != 207
        return 24
    # GCMD keeps persistent state, drops one-shot commands
    if vtd_gcmd_from_gsts(0xFF800000) != 0x96800000 or vtd_gcmd_from_gsts(GCMD_IRE | GCMD_SIRTP) != GCMD_IRE
        return 25
    # IRTA: page address, EIME bit 11, S = 7 (256 entries)
    if vtd_irta(0x12345000, true) != 0x12345807 or vtd_irta(0x12345678, false) != 0x12345007
        return 26
    # ECAP: IR and QI needed, EIM too for 32-bit destinations
    if not vtd_ecap_can_remap(0x1A, true) or vtd_ecap_can_remap(0x0A, true) or not vtd_ecap_can_remap(0x0A, false)
        return 27
    if vtd_ecap_can_remap(0x18, false) or vtd_ecap_can_remap(0x12, false)
        return 28
    # queued invalidation descriptors
    if qi_iec_global_lo() != 0x4 or qi_iec_index_lo(0xC1) != 0x000000C100000014
        return 29
    if qi_wait_lo(0xA5) != 0x000000A500000025 or qi_wait_hi(0x1003) != 0x1000
        return 30
    if qi_next_tail(0) != 1 or qi_next_tail(255) != 0
        return 31

    # PCI segments (AGAST #4598): DRHD A is on segment 0, B on segment 1;
    # each distinct segment gets one IRT, and each unit knows which.
    build(122)
    if dmar_parse(@t[0], 122) != 2 or dmar_num_segs != 2 or dmar_seg_id[0] != 0 or dmar_seg_id[1] != 1
        return 32
    if dmar_unit_seg_index[0] != 0 or dmar_unit_seg_index[1] != 1 or dmar_seg_index(1) != 1 or dmar_seg_index(5) != -1
        return 33
    # a requester ID (segment << 16 | bus:dev.fn) picks its segment's table;
    # one with no source ID goes to every table, one on a segment with no
    # unit to none
    if dmar_sid_seg_index(0x0108) != 0 or dmar_sid_seg_index(0x10108) != 1 or dmar_sid_seg_index(0x20108) != -1
        return 34
    if dmar_sid_seg_index(DMAR_SID_NONE) != DMAR_SEG_ALL
        return 35
    # the IRTE's SID field is the 16-bit bus:dev.fn; the segment chose the table
    if irte_hi(0x10108, IRTE_SVT_VERIFY_SID) != 0x40108
        return 36
    # an I/O APIC's source ID carries its unit's segment; both units on
    # segment 1 share one table
    put16(54, 1)
    if dmar_parse(@t[0], 122) != 2 or dmar_num_segs != 1 or dmar_seg_id[0] != 1 or dmar_unit_seg_index[0] != 0 or dmar_unit_seg_index[1] != 0
        return 37
    if dmar_ioapic_source_id(2) != 0x1FFF7 or dmar_ioapic_source_id(9) != DMAR_SID_NONE
        return 38

    # RMRRs (AGAST #4722): the regions, and each endpoint that uses one
    build(122)
    if dmar_parse(@t[0], 122) != 2 or dmar_num_rmrrs != 0 or dmar_num_rmrr_devs != 0
        return 39
    build_rmrr(170)
    if dmar_parse(@t[0], 170) != 1 or dmar_num_rmrrs != 2 or dmar_num_ioapics != 0
        return 40
    if dmar_rmrr_base[0] != 0x7F000000 or dmar_rmrr_limit[0] != 0x7F00FFFF or dmar_rmrr_segment[0] != 0
        return 41
    if dmar_rmrr_base[1] != 0x9000 or dmar_rmrr_limit[1] != 0x9FFF or dmar_rmrr_segment[1] != 1
        return 42
    if dmar_num_rmrr_devs != 3 or dmar_rmrr_dev_sid[0] != 0xA0 or dmar_rmrr_dev_region[0] != 0
        return 43
    if dmar_rmrr_dev_sid[1] != DMAR_SID_NONE or dmar_rmrr_dev_region[1] != 0
        return 44
    if dmar_rmrr_dev_sid[2] != 0x10311 or dmar_rmrr_dev_region[2] != 1
        return 45
    if dmar_rmrr_next(0xA0, 0) != 0 or dmar_rmrr_next(0xA0, 1) != -1 or dmar_rmrr_next(0x10311, 0) != 2 or dmar_rmrr_next(0x100A0, 0) != -1
        return 46
    put64(72, 0x7F000800)     # not page-aligned: dropped with its devices
    if dmar_parse(@t[0], 170) != 1 or dmar_num_rmrrs != 1 or dmar_num_rmrr_devs != 1 or dmar_rmrr_dev_region[0] != 0
        return 47

    # CAP
    if vtd_cap_domains(0) != 16 or vtd_cap_domains(2) != 256 or vtd_cap_domains(6) != 65536
        return 48
    if vtd_cap_sl_levels(CAP_SAGAW_48 | CAP_SAGAW_39) != 4 or vtd_cap_sl_levels(CAP_SAGAW_39) != 3 or vtd_cap_sl_levels(0x100) != 0
        return 49
    if vtd_cap_mgaw(0x2F0000) != 48 or vtd_iova_bits(0x2F0000, 4) != 48 or vtd_iova_bits(0x260000, 4) != 39 or vtd_iova_bits(0x2F0000, 3) != 39
        return 50
    if vtd_cap_fault_offset(0x22000000) != 0x220 or vtd_cap_fault_count(0x70000000000) != 8 or vtd_cap_fault_count(0) != 1
        return 51
    if not vtd_can_translate(CAP_SAGAW_48, ECAP_QI) or vtd_can_translate(CAP_SAGAW_48, 0) or vtd_can_translate(0x100, ECAP_QI)
        return 52
    if fsts_fri(0x0302) != 3
        return 53
    # root and context entries
    if vtd_rtaddr(0x12345678) != 0x12345000 or vtd_root_lo(0x5000) != 0x5001 or vtd_sid_bus(0x10311) != 3 or vtd_sid_devfn(0x10311) != 0x11
        return 54
    if vtd_ctx_lo(0x7000) != 0x7001 or vtd_ctx_hi(5, 4) != 0x502 or vtd_ctx_hi(0x1234, 3) != 0x123401 or vtd_ctx_did(vtd_ctx_hi(0x1234, 3)) != 0x1234
        return 55
    if not vtd_entry_present(0x7001) or vtd_entry_present(0x7000) or vtd_entry_addr(0xFFF0000000007001) != 0x7000
        return 56
    # second-level entries: 9 IOVA bits per level above the page offset
    let iova: u64 = (3 << 39) | (5 << 30) | (7 << 21) | (9 << 12) | 0x123
    if sl_index(iova, 4) != 3 or sl_index(iova, 3) != 5 or sl_index(iova, 2) != 7 or sl_index(iova, 1) != 9
        return 57
    if sl_table(0x8000) != 0x8003 or sl_leaf(0x9000, true) != 0x9003 or sl_leaf(0x9000, false) != 0x9001 or sl_leaf(0xFFF0000000001FFF, false) != 0x1001
        return 58
    if sl_present(0) or not sl_present(sl_leaf(0x9000, false))
        return 59
    # fault records
    if not frcd_pending(0xC000000600000008) or not frcd_is_read(0xC000000600000008) or frcd_reason(0xC000000600000008) != 6 or frcd_sid(0xC000000600000108) != 0x108
        return 60
    if frcd_pending(0x0000000500000108) or frcd_is_read(0x8000000500000108) or frcd_addr(0x20ABC) != 0x20000
        return 61
    # context-cache and IOTLB descriptors
    if qi_cc_global_lo() != 0x11 or qi_cc_device_lo(3, 0x10308) != 0x0000030800030031
        return 62
    if qi_iotlb_lo(QI_G_GLOBAL, 0, 0) != 0x12 or qi_iotlb_lo(QI_G_DOMAIN, 3, CAP_DRD | CAP_DWD) != 0x300E2
        return 63
    if qi_iotlb_unmap_lo(3, CAP_PSI) != 0x30032 or qi_iotlb_unmap_hi(0x10ABC, CAP_PSI) != 0x10000
        return 64
    if qi_iotlb_unmap_lo(3, 0) != 0x30022 or qi_iotlb_unmap_hi(0x10ABC, 0) != 0
        return 65
    # 2 MiB second-level leaves (AGAST #4723): PS (bit 7) on a level-2 entry,
    # the address 2 MiB aligned; CAP.SLLPS bit 34 says the unit walks them
    if sl_leaf_2m(0x40000000, true) != 0x40000083 or sl_leaf_2m(0x40012345, false) != 0x40000081
        return 66
    if not sl_is_large(sl_leaf_2m(0x200000, false)) or sl_is_large(sl_leaf(0x200000, true)) or sl_is_large(sl_table(0x8000))
        return 66
    if not vtd_cap_sl_2m(0x400000000) or vtd_cap_sl_2m(0x800000000) or vtd_cap_sl_2m(0)
        return 67
    0
"""

CLAIMS = {1: "two DRHD units", 2: "DMAR flags", 3: "unit register bases", 4: "INCLUDE_PCI_ALL/segment",
          5: "I/O APIC source ID", 6: "unnameable source ID", 7: "bad signature", 8: "bad length",
          9: "zero-length struct", 10: "struct past end", 11: "IRTE x2APIC dest", 12: "IRTE xAPIC dest + level",
          13: "IRTE dest/vector decode", 14: "IRTE xAPIC 8 bits", 15: "IRTE SID verify", 16: "IRTE no SVT",
          17: "remap MSI addr", 18: "MSI handle round trip", 19: "MSI format bit", 20: "remap RTE hi",
          21: "remap RTE lo", 22: "RTE handle round trip", 23: "RTE format bit", 24: "handles",
          25: "GCMD from GSTS", 26: "IRTA", 27: "ECAP EIM", 28: "ECAP IR/QI", 29: "IEC descriptors",
          30: "wait descriptor", 31: "queue tail", 32: "segment list", 33: "unit -> segment index",
          34: "requester ID -> segment table", 35: "no source ID -> every table", 36: "IRTE SID drops the segment",
          37: "shared segment, one table", 38: "I/O APIC source ID carries its segment",
          39: "no valid RMRR in the IR table", 40: "RMRR count", 41: "RMRR 0 region", 42: "RMRR on segment 1",
          43: "RMRR endpoint", 44: "RMRR endpoint behind a bridge", 45: "RMRR endpoint carries its segment",
          46: "dmar_rmrr_next", 47: "unaligned RMRR dropped", 48: "CAP.ND", 49: "CAP.SAGAW levels",
          50: "MGAW / IOVA bits", 51: "fault record offset/count", 52: "translation capable",
          53: "FSTS.FRI", 54: "RTADDR / root entry / SID split", 55: "context entry", 56: "entry present/addr",
          57: "second-level index", 58: "second-level entries", 59: "second-level present",
          60: "fault record decode", 61: "fault record not pending / write", 62: "context-cache descriptors",
          63: "IOTLB descriptors + drain", 64: "IOTLB page-selective unmap", 65: "IOTLB unmap without PSI",
          66: "2 MiB second-level leaf", 67: "CAP.SLLPS 2 MiB"}


@pytest.mark.integration
def test_dmar_parse_and_remapping_formats(tmp_path):
    tree = tmp_path / "tree" / "drivers" / "iommu"
    tree.mkdir(parents=True)
    (tree / "dmar.ritz").write_text(DMAR.read_text())
    (tmp_path / "t.ritz").write_text(PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "dmar.ritz", "dmar", ("--no-runtime",))]:
        ll = tmp_path / f"{name}.ll"
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
        assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
        objs.append(str(ll))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == 0, f"exit {rc}: {CLAIMS.get(rc, 'crash')}"


# --- source level: the kernel uses the remappable formats when IR is on -------

def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


@pytest.mark.unit
def test_dmar_module_is_import_free():
    assert not re.search(r"^import\b", _code(DMAR), re.M), "dmar.ritz must stay import-free (host-compiled)"


@pytest.mark.unit
def test_msix_entry_uses_an_irte_when_remapping_is_on():
    # through drivers/iommu/ir.ritz (#4329), which hands VT-d the remappable format.
    # msix_set_entry delegates to msix_set_entry_to, which takes the CPU the
    # entry is aimed at (AGAST #4220: per-CPU vectors).
    code = _code(MSIX)
    assert "msix_set_entry_to(" in _body(code, "msix_set_entry")
    body = _body(code, "msix_set_entry_to")
    assert "ir_enabled()" in body, body
    assert re.search(r"ir_set\(\s*\w+\s*,\s*vector\s*,\s*dest\s*,\s*\w+\s*,\s*msix_sid\(info\)", body), \
        "the IRTE must carry the vector, destination and requester ID"
    assert "ir_handle_msi(vector)" in body and "ir_msi_addr(" in body and "ir_msi_data(" in body, body
    assert "msi_addr_remap(" in _body(_code(IR), "ir_msi_addr")
    # the device's requester ID goes into the IRTE for source validation
    # the requester ID is the device's, segment included (AGAST #4582)
    assert "pci_dev_sid((*info).dev)" in _body(code, "msix_sid")


@pytest.mark.unit
def test_ioapic_entries_are_remappable_when_remapping_is_on():
    code = _code(APIC)
    set_irq = _body(code, "ioapic_set_irq_mode")   # edge and level pins (#4339)
    assert "ir_enabled()" in set_irq, set_irq
    assert "ir_handle_ioapic(" in set_irq and "ir_ioapic_rte_hi(" in set_irq and "ir_ioapic_rte_lo(" in set_irq
    assert "ir_set(" in set_irq and "ir_ioapic_sid(" in set_irq, set_irq
    ir = _code(IR)
    assert "ioapic_rte_remap_hi(" in _body(ir, "ir_ioapic_rte_hi") and "ioapic_rte_remap_lo(" in _body(ir, "ir_ioapic_rte_lo")
    # remapping is up before the I/O APIC is programmed, after the LAPIC mode is known
    select = _body(code, "apic_select_mode")
    assert "ir_init(" in select, select
    assert select.index("x2apic_mode = 1") < select.index("ir_init("), select
    assert "vtd_ir_init(" in _body(_code(IR), "ir_init")
    # Both boot paths share the post-ACPI bring-up (#1884)
    b = _body(code, "apic_bring_up")
    assert b.index("apic_select_mode()") < b.index("ioapic_init()"), b
    for init_fn in ("apic_init_with_mb", "apic_init_from_bootinfo"):
        assert "apic_bring_up()" in _body(code, init_fn), init_fn


@pytest.mark.unit
def test_irq_route_counts_remapping_as_reachable():
    code = _code(APIC)
    route = _body(code, "irq_route_dest")
    assert re.search(r"irq_dest_pick\(.*\bir_x2apic\(\)", route), "irq_route_dest ignores IR"
    # with IR on the table entry holds the destination: no extended-destination-ID bits
    assert re.search(r"irq_ext_dest and not ir_enabled\(\)", route), route


@pytest.mark.unit
def test_vtd_blocks_compatibility_format_and_invalidates_entries():
    code = _code(VTD)
    # an IRTE change reaches the hardware only after an IEC invalidation
    assert "vtd_irte_write(" in _body(code, "vtd_ir_set")
    assert "qi_iec_index_lo(" in _body(code, "vtd_irte_write"), "vtd_ir_set doesn't invalidate the entry"
    init = _code(VTD)
    assert "GCMD_IRE" in init and "GCMD_SIRTP" in init and "GCMD_QIE" in init
    # CFI stays clear: a compatibility-format interrupt would bypass the table
    assert re.search(r"GCMD_CFI", init), "vtd must clear CFI explicitly"


@pytest.mark.unit
def test_vtd_picks_the_ir_table_by_the_requesters_segment():
    # AGAST #4598: one IRT per PCI segment; a unit points at its segment's
    # table, and an IRTE is written to, read from and invalidated in the
    # table and units of the requester's segment only.
    code = _code(VTD)
    assert re.search(r"vtd_seg_irt_phys\s*:\s*\[8\]u64", code), "no per-segment IRT"
    assert not re.search(r"^var vtd_irt_phys\b", code, re.M), "a single shared IRT is left"
    enable = _body(code, "vtd_unit_enable")
    assert "vtd_seg_irt_phys[dmar_unit_seg_index[u]]" in enable, enable
    st = _body(code, "vtd_ir_set")
    assert "dmar_sid_seg_index(sid)" in st, st
    assert "vtd_irte_write(si," in st, st
    assert "dmar_unit_seg_index[u] == si" in _body(code, "vtd_irte_write"), "invalidates units of other segments"
    get = _body(code, "vtd_ir_get_lo")
    assert re.search(r"fn vtd_ir_get_lo\(handle: u32, sid: u32\)", get) and "dmar_sid_seg_index(sid)" in get, get
    assert "vtd_ir_get_lo(handle, sid)" in _body(_code(IR), "ir_get_dest")


# --- DMA remapping on an emulated unit (AGAST #4722) ---------------------------
#
# The real vtd.ritz and dmar.ritz, compiled for the host with stand-ins for
# the kernel modules they import. The fake unit is a register page and a
# clock (cpu_pause): GSTS follows GCMD, and the invalidation queue runs,
# writing each wait descriptor's status and logging every other descriptor
# in order, so the test reads back the invalidation sequence a call queued.
# With the unit "dead" the queue stops: every wait must end in a reported
# timeout, not a hang. Nothing turns translation on: GCMD.TE stays clear.

# As the kernel's serial.ritz: ritzlib's StrView (ritzlib.span, which
# vtd.ritz takes requester lists in, AGAST #4724, uses it too).
DMA_SERIAL_STUB = """\
pub import ritzlib.strview { StrView }
"""

DMA_KLOG_STUB = """\
import serial { StrView }

pub fn klog(s: StrView)
    return

pub fn klog_dec(n: i64)
    return

pub fn klog_hex(n: u64)
    return
"""

DMA_IO_STUB = """\
import fakevtd { fake_tick }

pub fn memory_barrier()
    return

pub fn cpu_pause()
    fake_tick()
"""

DMA_TSC_STUB = """\
var g_now: u64 = 0

pub fn deadline_after_us(us: u64) -> u64
    return g_now + 1000

pub fn deadline_passed(deadline: u64) -> bool
    g_now = g_now + 1
    return g_now >= deadline
"""

DMA_PMM_STUB = """\
var g_mem: [8388608]u8
var g_next: u64 = 0

pub fn pmm_alloc_page() -> u64
    let base: u64 = @g_mem[0] as u64
    if g_next == 0
        g_next = (base + 4095) & (0xFFFFFFFFFFFFFFFF ^ 4095)
    if g_next + 4096 > base + 8388608
        return 0
    let p: u64 = g_next
    g_next = g_next + 4096
    return p
"""

DMA_VMM_STUB = """\
import fakevtd { fake_regs }

pub fn vmm_map_mmio(paddr: u64, size: u64) -> u64
    return fake_regs()

pub fn vmm_ensure_mapped(paddr: u64, size: u64) -> i32
    return 0

pub fn phys_to_virt(paddr: u64) -> u64
    return paddr
"""

DMA_ACPI_STUB = """\
import fakevtd { fake_dmar }

pub fn acpi_find_table(sig: u32) -> u64
    return fake_dmar()
"""

FAKEVTD = """\
import drivers.iommu.dmar { VTD_REG_GCMD, VTD_REG_GSTS, VTD_REG_IQH, VTD_REG_IQT, VTD_REG_IQA, GCMD_WBF, QI_TYPE_WAIT, QI_WAIT_SW }

var g_regs: [4096]u8
var g_dmar: [96]u8
var g_dead: bool = false
var g_rmrr: bool = false
pub var fake_log_lo: [64]u64
pub var fake_log_hi: [64]u64
pub var fake_log_n: i32 = 0

pub fn fake_regs() -> u64
    return @g_regs[0] as u64

pub fn fake_reg32(off: u64) -> u32
    return volatile_load((fake_regs() + off) as *u32)

pub fn fake_set_reg32(off: u64, v: u32)
    volatile_store((fake_regs() + off) as *u32, v)

pub fn fake_reg64(off: u64) -> u64
    return (fake_reg32(off) as u64) | ((fake_reg32(off + 4) as u64) << 32)

pub fn fake_set_reg64(off: u64, v: u64)
    fake_set_reg32(off, (v & 0xFFFFFFFF) as u32)
    fake_set_reg32(off + 4, (v >> 32) as u32)

# A dead unit still answers GCMD but never runs its queue.
pub fn fake_set_dead(dead: bool)
    g_dead = dead

# One unit clock: GSTS shows GCMD (a write-buffer flush is done at once),
# and the queue runs from IQH to IQT.
pub fn fake_tick()
    fake_set_reg32(VTD_REG_GSTS, fake_reg32(VTD_REG_GCMD) & (0xFFFFFFFF ^ GCMD_WBF))
    if g_dead
        return
    let q: u64 = fake_reg64(VTD_REG_IQA) & 0xFFFFFFFFFFFFF000
    var head: u64 = fake_reg64(VTD_REG_IQH)
    let tail: u64 = fake_reg64(VTD_REG_IQT)
    while head != tail
        let lo: u64 = volatile_load((q + head) as *u64)
        let hi: u64 = volatile_load((q + head + 8) as *u64)
        if (lo & 0xF) == QI_TYPE_WAIT
            if (lo & QI_WAIT_SW) != 0
                volatile_store(hi as *u32, (lo >> 32) as u32)
        else if fake_log_n < 64
            fake_log_lo[fake_log_n] = lo
            fake_log_hi[fake_log_n] = hi
            fake_log_n = fake_log_n + 1
        head = (head + 16) & 0xFFF
    fake_set_reg64(VTD_REG_IQH, head)

fn put8(off: i32, v: u32)
    g_dmar[off] = (v & 0xFF) as u8

fn put16(off: i32, v: u32)
    put8(off, v)
    put8(off + 1, v >> 8)

fn put32(off: i32, v: u32)
    put16(off, v)
    put16(off + 2, v >> 16)

fn put64(off: i32, v: u64)
    put32(off, (v & 0xFFFFFFFF) as u32)
    put32(off + 4, (v >> 32) as u32)

# With an RMRR, the DMAR also reserves 0x7F000000-0x7F00FFFF on segment 0.
pub fn fake_set_rmrr(on: bool)
    g_rmrr = on

# DMAR: one unit, every device on segment 0, interrupt remapping supported.
pub fn fake_dmar() -> u64
    put32(0, 0x52414D44)
    put32(4, 64)
    put8(37, 1)
    put16(48, 0)
    put16(50, 16)
    put8(52, 1)
    put32(56, 0xFED90000)
    if g_rmrr
        put32(4, 88)
        put16(64, 1)
        put16(66, 24)
        put16(70, 0)
        put64(72, 0x7F000000)
        put64(80, 0x7F00FFFF)
    return @g_dmar[0] as u64
"""

DMA_STUBS = {
    "serial.ritz": DMA_SERIAL_STUB,
    "klog.ritz": DMA_KLOG_STUB,
    "io.ritz": DMA_IO_STUB,
    "arch/x86_64/tsc.ritz": DMA_TSC_STUB,
    "mm/pmm.ritz": DMA_PMM_STUB,
    "mm/vmm.ritz": DMA_VMM_STUB,
    "drivers/acpi/tables.ritz": DMA_ACPI_STUB,
    "fakevtd.ritz": FAKEVTD,
}

DMA_PROGRAM = """\
import drivers.iommu.dmar
import drivers.iommu.vtd
import fakevtd
import ritzlib.option

# SAGAW 4-level, 256 domain IDs, MGAW 48, fault records at 0x220 (4 of
# them), page-selective invalidation, read drain; no caching mode.
const CAP: u64 = 0x800380222F0402
const ECAP: u64 = 0x0A                       # IR, QI; tables not snooped
const NO_FAULT: VtdFault = VtdFault { sid: 0, iova: 0, reason: 0, read: false }

fn logged(k: i32, lo: u64, hi: u64) -> bool
    return k < fake_log_n and fake_log_lo[k] == lo and fake_log_hi[k] == hi

fn te_clear() -> bool
    return (fake_reg32(VTD_REG_GCMD) & GCMD_TE) == 0 and (fake_reg32(VTD_REG_GSTS) & GCMD_TE) == 0

fn main() -> i32
    fake_set_reg64(VTD_REG_CAP, CAP)
    fake_set_reg64(VTD_REG_ECAP, ECAP)
    if vtd_translation_capable(0x08) or vtd_domain_new(0x08).is_some()
        return 1
    if vtd_ir_init(false) != 0
        return 2
    if not vtd_translation_capable(0x08) or vtd_translation_capable(DMAR_SID_NONE) or vtd_translation_capable(0x10008)
        return 3
    let dom: u32 = vtd_domain_new(0x08).unwrap_or(0)
    if dom != 1 or vtd_domain_new(0x10008).is_some()
        return 4

    # map: a 4-level walk, tables made on the way; no caching mode, so
    # nothing is queued
    let n0: i32 = fake_log_n
    if vtd_domain_map(dom, 0x10000, 0x12345000, true) != VtdDma.Ok
        return 5
    if vtd_domain_entry(dom, 0x10000).unwrap_or(0) != sl_leaf(0x12345000, true) or vtd_domain_entry(dom, 0x11000).is_some()
        return 6
    if vtd_domain_map(dom, 0x10000, 0x5000, false) != VtdDma.Mapped
        return 7
    if vtd_domain_map(dom, 0x10800, 0x5000, false) != VtdDma.BadAddress or vtd_domain_map(dom, 0x20000, 0x5001, false) != VtdDma.BadAddress
        return 8
    if vtd_domain_map(dom, 0x1000000000000, 0x5000, false) != VtdDma.BadAddress or vtd_domain_map(9, 0x20000, 0x5000, false) != VtdDma.NoDomain
        return 9
    if vtd_domain_map(dom, 0xFFFFFFFFF000, 0x6000, false) != VtdDma.Ok or vtd_domain_entry(dom, 0xFFFFFFFFF000).unwrap_or(0) != sl_leaf(0x6000, false)
        return 10
    if fake_log_n != n0
        return 11

    # attach: the root table goes in (RTADDR, SRTP), then the context cache
    # and IOTLB are dropped globally, once; the context entry names the domain
    if vtd_context_attach(dom, 0x08) != VtdDma.Ok
        return 12
    let root: u64 = fake_reg64(VTD_REG_RTADDR)
    if root == 0 or (root & 0xFFF) != 0 or (fake_reg32(VTD_REG_GCMD) & GCMD_SRTP) == 0
        return 13
    if fake_log_n != n0 + 2 or not logged(n0, qi_cc_global_lo(), 0) or not logged(n0 + 1, qi_iotlb_lo(QI_G_GLOBAL, 0, CAP), 0)
        return 14
    let re: u64 = volatile_load(root as *u64)
    let ce: u64 = vtd_entry_addr(re) + 0x08 * 16
    if not vtd_entry_present(re) or not vtd_entry_present(volatile_load(ce as *u64)) or volatile_load((ce + 8) as *u64) != vtd_ctx_hi(dom, 4)
        return 15
    # the context's table, walked by hand: IOVA 0x10000 is entries 0, 0, 0, 16
    var t: u64 = vtd_entry_addr(volatile_load(ce as *u64))
    var lvl: i32 = 0
    while lvl < 3
        let e: u64 = volatile_load(t as *u64)
        if (e & 3) != 3
            return 33
        t = vtd_entry_addr(e)
        lvl = lvl + 1
    if volatile_load((t + 16 * 8) as *u64) != sl_leaf(0x12345000, true)
        return 33
    if vtd_context_domain(0x08).unwrap_or(0) != dom or vtd_context_domain(0x10).is_some()
        return 16
    # the interrupt remapping that was on stays on; translation stays off
    if not te_clear() or (fake_reg32(VTD_REG_GSTS) & GCMD_IRE) == 0
        return 17
    if vtd_context_attach(dom, 0x08) != VtdDma.Ok or fake_log_n != n0 + 2
        return 18
    let dom2: u32 = vtd_domain_new(0x08).unwrap_or(0)
    if dom2 != 2 or vtd_context_attach(dom2, 0x08) != VtdDma.Busy or vtd_context_attach(dom2, 0x10) != VtdDma.Ok
        return 19
    if vtd_context_attach(dom, DMAR_SID_NONE) != VtdDma.NoSegment or vtd_context_attach(dom, 0x10008) != VtdDma.NoSegment
        return 20

    # unmap: the entry goes, then a page-selective IOTLB invalidation, waited on
    let n1: i32 = fake_log_n
    if vtd_domain_unmap(dom, 0x10000) != VtdDma.Ok or vtd_domain_entry(dom, 0x10000).is_some()
        return 21
    if fake_log_n != n1 + 1 or not logged(n1, qi_iotlb_unmap_lo(dom, CAP), 0x10000)
        return 22
    if vtd_domain_unmap(dom, 0x10000) != VtdDma.NotMapped or vtd_domain_unmap(dom, 0x5000000) != VtdDma.NotMapped
        return 23

    # a fault record: requester, page, reason, read; F written back to clear it
    if vtd_fault_next().is_some()
        return 24
    fake_set_reg64(0x230, 0x20ABC)
    fake_set_reg64(0x238, 0xC000000600000010)
    fake_set_reg32(VTD_REG_FSTS, FSTS_PPF | 0x100)
    let f: VtdFault = vtd_fault_next().unwrap_or(NO_FAULT)
    if f.sid != 0x10 or f.iova != 0x20000 or f.reason != 6 or not f.read
        return 25
    if fake_reg32(0x23C) != 0x80000000
        return 26
    fake_set_reg32(0x23C, 0)
    fake_set_reg32(VTD_REG_FSTS, 0)

    # detach: the entry goes, then the requester's context-cache entry and
    # its domain's IOTLB entries, waited on
    let n2: i32 = fake_log_n
    if vtd_context_detach(0x08) != VtdDma.Ok or vtd_context_domain(0x08).is_some()
        return 27
    if fake_log_n != n2 + 2 or not logged(n2, qi_cc_device_lo(dom, 0x08), 0) or not logged(n2 + 1, qi_iotlb_lo(QI_G_DOMAIN, dom, CAP), 0)
        return 28
    if vtd_context_detach(0x08) != VtdDma.NotMapped
        return 29

    # a unit that stops answering: the bounded wait reports it
    fake_set_dead(true)
    if vtd_domain_map(dom, 0x30000, 0x7000, true) != VtdDma.Ok or vtd_domain_unmap(dom, 0x30000) != VtdDma.Timeout
        return 30
    if vtd_context_detach(0x10) != VtdDma.Timeout
        return 31
    if not te_clear()
        return 32
    # a unit with no second-level depth this driver builds: interrupt
    # remapping still comes up, translation is refused
    fake_set_dead(false)
    fake_set_reg64(VTD_REG_CAP, CAP & (0xFFFFFFFFFFFFFFFF ^ (CAP_SAGAW_48 | CAP_SAGAW_39)))
    if vtd_ir_init(false) != 0 or vtd_translation_capable(0x08) or vtd_domain_new(0x08).is_some()
        return 34
    0
"""

DMA_CLAIMS = {1: "nothing before remapping is on", 2: "IR init on the fake unit", 3: "translation capable query",
              4: "domain per segment", 5: "map", 6: "leaf entry", 7: "double map refused",
              8: "unaligned IOVA/page refused", 9: "IOVA past the width / bad domain", 10: "map at the top of 48 bits",
              11: "map queues nothing without caching mode", 12: "attach", 13: "root table installed",
              14: "root install invalidates context cache + IOTLB once", 15: "root/context entry contents",
              16: "context domain query", 17: "TE clear, IRE kept", 18: "attach twice is Ok, no re-install",
              19: "attach to another domain is Busy", 20: "attach without a segment", 21: "unmap",
              22: "unmap: page-selective IOTLB invalidation", 23: "unmap of a hole", 24: "no fault",
              25: "fault record decoded", 26: "fault record cleared", 27: "detach",
              28: "detach: context-cache device + IOTLB domain invalidation", 29: "detach twice",
              30: "unmap on a dead unit times out", 31: "detach on a dead unit times out", 32: "TE never set",
              33: "second-level table walked by hand", 34: "a unit that can't translate is refused"}


def _run_on_emulated_unit(tmp_path, program, claims):
    tree = tmp_path / "tree"
    sources = dict(DMA_STUBS)
    for rel in ("drivers/iommu/dmar.ritz", "drivers/iommu/vtd.ritz"):
        sources[rel] = (KERNEL_SRC / rel).read_text()
    for rel, text in sources.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
    (tmp_path / "t.ritz").write_text(program)
    env = dict(os.environ, RITZ_PATH=f"{tree}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, extra in [(tmp_path / "t.ritz", ()), *[(tree / rel, ("--no-runtime",)) for rel in sources]]:
        ll = tmp_path / (str(src.relative_to(tmp_path))[:-5].replace("/", "_") + ".ll")
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
        assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {src.name}:\n{proc.stdout}{proc.stderr}"
        objs.append(str(ll))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == 0, f"exit {rc}: {claims.get(rc, 'crash')}"


@pytest.mark.integration
def test_vtd_dma_remapping_on_an_emulated_unit(tmp_path):
    _run_on_emulated_unit(tmp_path, DMA_PROGRAM, DMA_CLAIMS)


# --- The translating boot (AGAST #4723) ------------------------------------------
#
# vtd_dma_init, on the same emulated unit: an identity domain per segment
# (RAM up to the top the caller gives, and the segment's RMRRs, in 2 MiB
# leaves where CAP.SLLPS has them), a context naming it for every requester
# (each bus:dev.fn), the context cache and IOTLB dropped, then TE. The test
# walks the tables the unit would walk.

TE_PROGRAM = """\
import drivers.iommu.dmar
import drivers.iommu.vtd
import fakevtd
import ritzlib.span

# SAGAW 4-level, 256 domain IDs, MGAW 48, fault records at 0x220, PSI, DRD,
# SLLPS 2 MiB (bit 34); no caching mode.
const CAP: u64 = 0x800384222F0402
const ECAP: u64 = 0x0A
const TOP: u64 = 0x40000000                  # 1 GiB of RAM

fn te_on() -> bool
    return (fake_reg32(VTD_REG_GSTS) & GCMD_TE) != 0

# The entry the unit's walk for requester `sid` ends on at `iova`: the
# leaf (or 0 if the walk stops at a missing entry), with `*level` the level
# it is at (2: a 2 MiB leaf). 0 with `*level` 9: no context.
fn walk(sid: u32, iova: u64, level: *u32) -> u64
    *level = 9
    let re: u64 = volatile_load((fake_reg64(VTD_REG_RTADDR) + vtd_sid_bus(sid) * 16) as *u64)
    if not vtd_entry_present(re)
        return 0
    let ce: u64 = vtd_entry_addr(re) + vtd_sid_devfn(sid) * 16
    let lo: u64 = volatile_load(ce as *u64)
    if not vtd_entry_present(lo)
        return 0
    var lvl: u32 = (volatile_load((ce + 8) as *u64) & 7) as u32 + 2
    var t: u64 = vtd_entry_addr(lo)
    while true
        *level = lvl
        let e: u64 = volatile_load((t + sl_index(iova, lvl) * 8) as *u64)
        if not sl_present(e) or lvl == 1 or sl_is_large(e)
            return e
        t = vtd_entry_addr(e)
        lvl = lvl - 1

# How many descriptors with low half `lo` were queued from entry `from` on.
fn queued(lo: u64, from: i32) -> i32
    var n: i32 = 0
    var k: i32 = from
    while k < fake_log_n
        if fake_log_lo[k] == lo
            n = n + 1
        k = k + 1
    return n

fn main() -> i32
    fake_set_reg64(VTD_REG_CAP, CAP)
    fake_set_reg64(VTD_REG_ECAP, ECAP)
    fake_set_rmrr(true)
    # nothing before interrupt remapping is on
    if vtd_dma_translation_on() or vtd_dma_init(TOP, span_empty<u32>())
        return 1
    if vtd_ir_init(false) != 0 or te_on()
        return 2
    let n0: i32 = fake_log_n
    if not vtd_dma_init(TOP, span_empty<u32>())
        return 3
    if not vtd_dma_translation_on() or not te_on() or (fake_reg32(VTD_REG_GCMD) & GCMD_TE) == 0
        return 4
    # interrupt remapping stays on, compatibility format still blocked
    if (fake_reg32(VTD_REG_GSTS) & GCMD_IRE) == 0 or (fake_reg32(VTD_REG_GCMD) & GCMD_CFI) != 0
        return 5
    # one identity domain, and every requester names it: the first, the
    # last, one on another bus, and the NIC-like 00:03.0
    let dom: u32 = vtd_context_domain(0x0000).unwrap_or(0)
    if dom == 0 or vtd_context_domain(0xFFFF).unwrap_or(0) != dom or vtd_context_domain(0x0318).unwrap_or(0) != dom or vtd_context_domain(0x18).unwrap_or(0) != dom
        return 6
    # RAM is identity-mapped read-write in 2 MiB leaves, up to TOP and no further
    var lvl: u32 = 0
    if walk(0x18, 0, @lvl) != sl_leaf_2m(0, true) or lvl != 2
        return 7
    if walk(0xFFFF, 0x3FFFF000, @lvl) != sl_leaf_2m(0x3FE00000, true) or lvl != 2
        return 8
    if sl_present(walk(0x18, TOP, @lvl)) or sl_present(walk(0x18, 0x7EE00000, @lvl))
        return 9
    # the RMRR (above TOP) is mapped for every requester on its segment
    if walk(0x0318, 0x7F00F000, @lvl) != sl_leaf_2m(0x7F000000, true) or lvl != 2
        return 10
    # the root table's install drops the caches once; once the contexts are
    # in, every unit's are dropped again, last, before TE
    if queued(qi_cc_global_lo(), n0) != 2 or queued(qi_iotlb_lo(QI_G_GLOBAL, 0, CAP), n0) != 2
        return 11
    if fake_log_lo[fake_log_n - 2] != qi_cc_global_lo() or fake_log_lo[fake_log_n - 1] != qi_iotlb_lo(QI_G_GLOBAL, 0, CAP)
        return 11
    # a second call leaves it as it is
    let root: u64 = fake_reg64(VTD_REG_RTADDR)
    if not vtd_dma_init(TOP, span_empty<u32>()) or fake_reg64(VTD_REG_RTADDR) != root or vtd_context_domain(0x18).unwrap_or(0) != dom
        return 12

    # a unit without 2 MiB leaves: 4 KiB leaves
    fake_set_reg32(VTD_REG_GCMD, 0)
    fake_set_reg32(VTD_REG_GSTS, 0)
    fake_set_rmrr(false)
    fake_set_reg64(VTD_REG_CAP, CAP & (0xFFFFFFFFFFFFFFFF ^ 0x400000000))
    if vtd_ir_init(false) != 0 or vtd_dma_translation_on() or te_on()
        return 13
    if not vtd_dma_init(0x400000, span_empty<u32>()) or not te_on()
        return 14
    if walk(0x18, 0x3FF000, @lvl) != sl_leaf(0x3FF000, true) or lvl != 1 or sl_present(walk(0x18, 0x400000, @lvl))
        return 15

    # a unit that can't translate: interrupt remapping only, TE stays clear
    fake_set_reg32(VTD_REG_GCMD, 0)
    fake_set_reg32(VTD_REG_GSTS, 0)
    fake_set_reg64(VTD_REG_CAP, CAP & (0xFFFFFFFFFFFFFFFF ^ (CAP_SAGAW_48 | CAP_SAGAW_39)))
    if vtd_ir_init(false) != 0 or vtd_dma_init(TOP, span_empty<u32>()) or vtd_dma_translation_on() or te_on()
        return 16
    # RAM past what the unit translates (MGAW 39): refused
    fake_set_reg64(VTD_REG_CAP, (CAP & (0xFFFFFFFFFFFFFFFF ^ 0x3F0000)) | 0x260000)
    if vtd_ir_init(false) != 0 or vtd_dma_init(0x10000000000, span_empty<u32>()) or vtd_dma_translation_on() or te_on()
        return 17
    # a unit that stops answering its queue: refused, TE stays clear
    fake_set_reg64(VTD_REG_CAP, CAP)
    if vtd_ir_init(false) != 0
        return 18
    fake_set_dead(true)
    if vtd_dma_init(TOP, span_empty<u32>()) or vtd_dma_translation_on() or te_on()
        return 19
    0
"""

TE_CLAIMS = {1: "nothing before interrupt remapping", 2: "IR init, TE clear", 3: "translation init",
             4: "TE set and reported", 5: "IR kept, CFI still blocked", 6: "identity context for every requester",
             7: "RAM identity 2 MiB leaf at 0", 8: "RAM identity up to the top", 9: "nothing past the top",
             10: "RMRR identity-mapped", 11: "context cache + IOTLB flushed before TE", 12: "second init is a no-op",
             13: "IR re-init on a 4 KiB unit", 14: "translation on with 4 KiB leaves", 15: "4 KiB identity leaves",
             16: "a unit that can't translate is refused", 17: "RAM past the IOVA width is refused",
             18: "IR on the live unit", 19: "a dead queue refuses TE"}


@pytest.mark.integration
def test_vtd_translating_boot_on_an_emulated_unit(tmp_path):
    _run_on_emulated_unit(tmp_path, TE_PROGRAM, TE_CLAIMS)


@pytest.mark.unit
def test_vtd_sets_translation_enable_only_in_the_translating_boot():
    # AGAST #4723: TE is set in one place, after the identity contexts and
    # the global flush, and only from ir_init once VT-d remapping is on
    code = _code(VTD)
    code = re.sub(r"^import [^{\n]*\{.*?\}", "", code, flags=re.M | re.S)
    # a GCMD write naming TE; vtd_isolation_live (AGAST #4724) only reads GSTS
    te = [m.start() for m in re.finditer(r"vtd_gcmd\([^)]*GCMD_TE", code)]
    init = _body(code, "vtd_dma_init").rstrip()
    assert te and all(code.find(init) <= i < code.find(init) + len(init) for i in te), \
        "TE set outside vtd_dma_init"
    live = _body(code, "vtd_isolation_live")
    assert "VTD_REG_GSTS" in live and "vtd_gcmd" not in live and "vtd_wreg" not in live, live
    assert init.index("vtd_seg_identity(") < init.index("qi_cc_global_lo()") < init.index("GCMD_TE"), init
    assert "vtd_seg_levels(si) == 0" in _body(code, "vtd_seg_identity"), "a segment that can't translate must be refused"
    assert "if not vtd_on" in init, init
    ir_init = _body(_code(IR), "ir_init")
    assert re.search(r"vtd_ir_init\(x2apic\) == 0", ir_init) and "vtd_dma_init(pmm_top_phys(), " in ir_init, ir_init
    # the boot's answer: VT-d's; AMD-Vi stays pass-through (decision D6)
    on = _body(_code(IR), "dma_translation_on")
    assert "vtd_dma_translation_on()" in on and "amdvi" not in on, on


@pytest.mark.unit
def test_virtio_net_asks_for_access_platform_on_a_translating_boot():
    # AGAST #4723: VIRTIO_F_ACCESS_PLATFORM (bit 33) puts the NIC's DMA
    # through the domain; asked for only when the boot translates
    common = _code(VIRTIO_COMMON)
    assert "(*dev).access_platform" in _body(common, "vio_set_features")
    # common.ritz is shared with blk and input and host-compiled with stubs:
    # the IOMMU question is virtio-net's
    assert "drivers.iommu" not in common
    init = _body(_code(VIRTIO_NET), "virtio_net_init")
    assert re.search(r"if dma_translation_on\(\)\s+wanted = wanted \| VIRTIO_F_ACCESS_PLATFORM\s+vio_set_features\(vdev, wanted\)", init), \
        "virtio-net must ask for bit 33 on a translating boot"
    assert "VIRTIO_F_ACCESS_PLATFORM negotiated" in VIRTIO_NET.read_text()


# --- The NIC's private domain (AGAST #4724) ---------------------------------------
#
# On the same emulated unit: vtd_dma_init holds the NIC and its alias out of
# the identity domain; vtd_private_domain gives them their own (and moves a
# requester already on identity off it, dropping its context-cache entry and
# the identity domain's IOTLB first); vtd_domain_enter maps a run at fresh
# IOVAs from VTD_IOVA_BASE (vtd_domain_enter_at at an IOVA the caller
# owns), and a failure part-way unmaps what it mapped or,
# when the unit doesn't confirm that, reports the run Stuck (DrvDmaAlloc
# then quarantines it); vtd_isolation_live reads TE, IRE and CFI from GSTS.

NIC_PROGRAM = """\
import drivers.iommu.dmar
import drivers.iommu.vtd
import fakevtd
import ritzlib.option
import ritzlib.span

const CAP: u64 = 0x800384222F0402
const ECAP: u64 = 0x0A
const TOP: u64 = 0x40000000
const NIC: u32 = 0x18                       # 00:03.0
const ALIAS: u32 = 0x100                    # 01:00.0, a PCIe-to-PCI bridge's alias
const PAGE: u64 = 4096

var held: [2]u32
var one: [1]u32
var mixed: [2]u32

fn logged(k: i32, lo: u64, hi: u64) -> bool
    return k < fake_log_n and fake_log_lo[k] == lo and fake_log_hi[k] == hi

fn ctx(sid: u32) -> u32
    return vtd_context_domain(sid).unwrap_or(0)

fn entered(r: VtdEnter) -> u64
    match r
        VtdEnter.Entered(iova) => iova
        VtdEnter.Refused => 1
        VtdEnter.Stuck => 2

# The 4 KiB leaf the unit's walk for requester `sid` ends on at `iova`, 0 if none.
fn walk(sid: u32, iova: u64) -> u64
    let re: u64 = volatile_load((fake_reg64(VTD_REG_RTADDR) + vtd_sid_bus(sid) * 16) as *u64)
    if not vtd_entry_present(re)
        return 0
    let ce: u64 = vtd_entry_addr(re) + vtd_sid_devfn(sid) * 16
    let lo: u64 = volatile_load(ce as *u64)
    if not vtd_entry_present(lo)
        return 0
    var lvl: u32 = (volatile_load((ce + 8) as *u64) & 7) as u32 + 2
    var t: u64 = vtd_entry_addr(lo)
    while true
        let e: u64 = volatile_load((t + sl_index(iova, lvl) * 8) as *u64)
        if not sl_present(e) or lvl == 1 or sl_is_large(e)
            return e
        t = vtd_entry_addr(e)
        lvl = lvl - 1

fn main() -> i32
    fake_set_reg64(VTD_REG_CAP, CAP)
    fake_set_reg64(VTD_REG_ECAP, ECAP)
    held[0] = NIC
    held[1] = ALIAS
    if vtd_ir_init(false) != 0
        return 1
    # no private domain, nothing isolated, before translation is on
    if vtd_private_domain(span_from_ptr<u32>(@held[0], 2)).is_some() or vtd_isolation_live() or vtd_requester_isolated(NIC)
        return 18
    if not vtd_dma_init(TOP, span_from_ptr<u32>(@held[0], 2))
        return 1
    # held: no context, so no identity map; their neighbours have one
    if vtd_context_domain(NIC).is_some() or vtd_context_domain(ALIAS).is_some() or walk(NIC, 0x1000) != 0
        return 2
    let ident: u32 = ctx(0x10)
    if ident == 0 or ctx(0x101) != ident or ctx(0x20) != ident
        return 3
    if not vtd_isolation_live() or vtd_requester_isolated(NIC)
        return 4
    # the private domain: both requesters name it, and only they are isolated
    let dom: u32 = vtd_private_domain(span_from_ptr<u32>(@held[0], 2)).unwrap_or(0)
    if dom == 0 or dom == ident or ctx(NIC) != dom or ctx(ALIAS) != dom
        return 6
    if not vtd_requester_isolated(NIC) or not vtd_requester_isolated(ALIAS) or vtd_requester_isolated(0x10)
        return 7
    # a requester on identity, moved: its context-cache entry and the identity
    # domain's IOTLB are dropped before it names the new domain
    one[0] = 0x20
    let n1: i32 = fake_log_n
    let dom2: u32 = vtd_private_domain(span_from_ptr<u32>(@one[0], 1)).unwrap_or(0)
    if dom2 == 0 or ctx(0x20) != dom2 or not logged(n1, qi_cc_device_lo(ident, 0x20), 0) or not logged(n1 + 1, qi_iotlb_lo(QI_G_DOMAIN, ident, CAP), 0)
        return 8
    if ctx(0x10) != ident
        return 8
    # requesters on two segments (the second has no unit): refused
    mixed[0] = 0x28
    mixed[1] = 0x10028
    if vtd_private_domain(span_from_ptr<u32>(@mixed[0], 2)).is_some() or ctx(0x28) != ident or vtd_requester_isolated(0x28)
        return 9
    # a run enters at fresh IOVAs from VTD_IOVA_BASE, read-write, contiguous,
    # and the NIC's walk reaches it
    let iova: u64 = entered(vtd_domain_enter(dom, 0x5000000, 3))
    if iova != VTD_IOVA_BASE
        return 10
    var k: u64 = 0
    while k < 3
        if vtd_domain_entry(dom, iova + k * PAGE).unwrap_or(0) != sl_leaf(0x5000000 + k * PAGE, true) or walk(NIC, iova + k * PAGE) != sl_leaf(0x5000000 + k * PAGE, true)
            return 10
        k = k + 1
    # the next follows it: an IOVA is never handed out twice
    let iova2: u64 = entered(vtd_domain_enter(dom, 0x6000000, 3))
    if iova2 != VTD_IOVA_BASE + 3 * PAGE
        return 11
    # the private domain holds nothing else: no RAM, no other run
    if vtd_domain_entry(dom, 0x5000000).is_some() or vtd_domain_entry(dom, 0).is_some() or walk(NIC, 0x5000000) != 0
        return 12
    if vtd_domain_entry(dom2, iova).is_some()
        return 12
    # leaving: every page unmapped with a page-selective invalidation
    let n2: i32 = fake_log_n
    if not vtd_domain_leave(dom, iova, 3) or vtd_domain_entry(dom, iova).is_some() or walk(NIC, iova + 2 * PAGE) != 0
        return 13
    if fake_log_n != n2 + 3 or not logged(n2, qi_iotlb_unmap_lo(dom, CAP), iova)
        return 13
    # a confirmed leave's IOVA enters again at the caller's choice (DrvDmaFree's
    # free list, AGAST #4725); one still mapped refuses and keeps its mapping
    if entered(vtd_domain_enter_at(dom, iova, 0x5800000, 3)) != iova or vtd_domain_entry(dom, iova + 2 * PAGE).unwrap_or(0) != sl_leaf(0x5800000 + 2 * PAGE, true)
        return 19
    if entered(vtd_domain_enter_at(dom, iova2, 0x5900000, 1)) != 1 or vtd_domain_entry(dom, iova2).unwrap_or(0) != sl_leaf(0x6000000, true)
        return 19
    if not vtd_domain_leave(dom, iova, 3)
        return 19
    # isolation as the unit reports it: CFI passing, IRE or TE off is not isolation
    let gsts: u32 = fake_reg32(VTD_REG_GSTS)
    fake_set_reg32(VTD_REG_GSTS, gsts | GCMD_CFI)
    if vtd_isolation_live()
        return 14
    fake_set_reg32(VTD_REG_GSTS, gsts & (0xFFFFFFFF ^ GCMD_IRE))
    if vtd_isolation_live()
        return 14
    fake_set_reg32(VTD_REG_GSTS, gsts & (0xFFFFFFFF ^ GCMD_TE))
    if vtd_isolation_live()
        return 14
    fake_set_reg32(VTD_REG_GSTS, gsts)
    # a run past the domain's width: refused, nothing taken
    if entered(vtd_domain_enter(dom, 0x7000000, 0x1000000000)) != 1
        return 15
    # a page that won't map part-way: the pages before it are unmapped again
    let next: u64 = VTD_IOVA_BASE + 6 * PAGE
    if vtd_domain_map(dom, next + PAGE, 0x9000, true) != VtdDma.Ok
        return 16
    if entered(vtd_domain_enter(dom, 0x7000000, 2)) != 1 or vtd_domain_entry(dom, next).is_some()
        return 16
    # ... and when the unit doesn't confirm that, the run is Stuck
    let after: u64 = VTD_IOVA_BASE + 8 * PAGE
    if vtd_domain_map(dom, after + PAGE, 0x9000, true) != VtdDma.Ok
        return 17
    fake_set_dead(true)
    if entered(vtd_domain_enter(dom, 0x7000000, 2)) != 2
        return 17
    fake_set_dead(false)
    0
"""

NIC_CLAIMS = {1: "IR and translation init with held requesters", 2: "held requesters get no context",
              3: "every other requester keeps identity", 4: "isolation read live from GSTS",
              6: "private domain named by the NIC and its alias", 7: "only the private domain's requesters are isolated",
              8: "a requester moved off identity: context cache + identity IOTLB dropped first",
              9: "requesters on two segments refused", 10: "a run enters at fresh IOVAs, walked by the NIC",
              11: "IOVAs are never reused", 12: "the private domain maps nothing but its runs",
              13: "leave unmaps with page-selective invalidation", 14: "CFI, IRE or TE off is not isolation",
              15: "a run past the width is refused", 16: "a partial enter unmaps what it mapped",
              17: "a partial enter on a dead unit is Stuck", 18: "nothing before translation is on",
              19: "enter_at reuses a left IOVA and refuses a mapped one"}


@pytest.mark.integration
def test_vtd_nic_private_domain_on_an_emulated_unit(tmp_path):
    _run_on_emulated_unit(tmp_path, NIC_PROGRAM, NIC_CLAIMS)


PCI = KERNEL_SRC / "drivers" / "pci.ritz"


@pytest.mark.unit
def test_nic_bus_master_waits_for_its_private_domain():
    """AGAST #4724: on a translating boot the virtio probe leaves the NIC's
    bus master off (and clears what firmware left), names every requester,
    refuses an unnamed alias before anything else, and sets bus master only
    once the private domain is live, then runs the fault probe."""
    common = _code(VIRTIO_COMMON)
    vinit = _body(common, "vio_init")
    assert vinit.index("if not bus_master\n        pci_disable_bus_master(pci_dev)") < vinit.index("vio_find_mmio_caps")
    assert vinit.count("pci_enable_bus_master(pci_dev)") == 2
    assert vinit.count("if bus_master\n            pci_enable_bus_master(pci_dev)") == 1
    assert vinit.count("if bus_master\n        pci_enable_bus_master(pci_dev)") == 1
    assert "vio_init(pci_dev, false)" in _body(common, "vio_init_device_isolated")
    net = _code(VIRTIO_NET)
    init = _body(net, "virtio_net_init")
    assert re.search(r"let isolate: bool = dma_translation_on\(\)\s+var vdev: \*VirtioDevice = 0 as \*VirtioDevice\s+"
                     r"if isolate\s+vdev = vio_init_device_isolated\(pci_dev\)", init), init
    assert init.index("virtio_net_isolate(pci_dev, vdev)") < init.index("virtio_net_setup_msix")
    iso = _body(net, "virtio_net_isolate")
    assert iso.index("nic_private_domain(pci_dev)") < iso.index("virtio_net_fault_probe(vdev, pci_dev_sid(pci_dev))")
    assert "None => return false" in iso
    # The domain before bus master is every ring NIC's (drivers/nic.ritz,
    # AGAST #4893).
    nicd = _body(_code(NIC), "nic_private_domain")
    named = nicd.index("if not req.named")
    dom = nicd.index("dma_private_domain(span_from_ptr<u32>(@req.sids[0], req.count as i64))")
    bm = nicd.index("pci_enable_bus_master(dev)")
    assert named < dom < bm, nicd
    assert nicd[named:dom].count("return None") == 1 and nicd[dom:bm].count("return None") == 1
    # bus master is set nowhere else in either NIC's kernel code
    assert "pci_enable_bus_master(" not in net
    assert "pci_enable_bus_master(" not in _code(E1000E)


@pytest.mark.unit
def test_nic_dma_goes_through_its_domain():
    """AGAST #4724: the rings and both buffer pools enter the NIC's domain
    (the path DrvDmaAlloc uses) and the device is given their IOVAs; a
    descriptor carries the device address as it is, no CPU translation."""
    net = _code(VIRTIO_NET)
    assert "dma_domain_enter(virtio_net_dom, (*vq).phys_addr, vio_queue_pages(vq))" in _body(net, "virtio_net_alloc_queue")
    assert "VtdEnter.Entered(iova) => (*vq).phys_addr = iova" in _body(net, "virtio_net_alloc_queue")
    pool = _body(net, "nic_pool_new")
    assert "dma_domain_enter(virtio_net_dom, phys, VIRTIO_NET_POOL_PAGES)" in pool and "dma_quarantine(" in pool
    add = _body(net, "virtq_add_buf")
    assert "(*desc_ptr).addr = dev_addr" in add and "virt_to_phys" not in add
    assert "virtio_rx_buffers" not in net and "virtio_tx_buffers" not in net
    poll = _body(net, "virtio_net_poll")
    assert "virtio_rx_pool.virt + (rx_addr - virtio_rx_pool.dev)" in poll and "phys_to_virt(rx_addr)" not in poll
    probe = _body(net, "virtio_net_fault_probe")
    assert "dma_domain_hole(virtio_net_dom)" in probe
    assert probe.index("nic_faults_drain()") < probe.index("virtq_kick(txq)") < probe.index("nic_fault_seen(sid, hole)")
    assert "virtio_net_reset_done(vdev)" in probe
    seen = _body(_code(NIC), "nic_fault_seen")
    assert "match dma_fault_next()" in seen and "f.sid == sid and f.iova == hole" in seen
    assert "nic_ring1_allowed(virtio_net.pci_dev, virtio_net_dom)" in _body(net, "net_ring1_allowed")
    allowed = _body(_code(NIC), "nic_ring1_allowed")
    assert "dma_isolation_live()" in allowed and "dma_requester_isolated(" in allowed


@pytest.mark.unit
def test_ir_init_holds_the_nic_out_of_the_identity_domain():
    ir = _code(IR)
    body = _body(ir, "ir_init")
    assert "var nic: DmaRequesters = nic_requesters()" in body
    assert "vtd_dma_init(pmm_top_phys(), span_from_ptr<u32>(@nic.sids[0], nic.count as i64))" in body
    assert "pci_dma_requesters(nic)" in _body(ir, "nic_requesters")
    # the private-domain calls are VT-d's alone
    for fn in ("dma_private_domain", "dma_requester_isolated", "dma_isolation_live"):
        assert "amdvi" not in _body(ir, fn), fn
    assert "if not vtd_dma_translation_on()\n        return None" in _body(ir, "dma_private_domain")


@pytest.mark.unit
def test_dma_requesters_name_aliases_or_refuse():
    """AGAST #4724: phantom functions are never named; a PCIe-to-PCI bridge
    adds (secondary bus, devfn 0), a conventional or PCI-to-PCIe bridge its
    own ID, and either only when the function is alone behind it; a PCIe
    switch or root port adds nothing."""
    pci = _code(PCI)
    body = _body(pci, "pci_dma_requesters")
    assert "requesters_add(@r, pci_dev_sid(dev))" in body
    assert re.search(r"PCIE_DEVCTL_PHANTOM\) != 0\s+r\.named = false", body)
    assert re.search(r"if cap == 0 or port == PCIE_TYPE_PCIE_TO_PCI or port == PCIE_TYPE_PCI_TO_PCIE\s+"
                     r"if not pci_alone_behind\(bridge, dev\)\s+r\.named = false\s+"
                     r"else if port == PCIE_TYPE_PCIE_TO_PCI\s+requesters_add\(@r, pci_sid\(\(\*bridge\)\.segment as u32, bus as u32, 0, 0\)\)\s+"
                     r"else\s+requesters_add\(@r, pci_dev_sid\(bridge\)\)", body), body
    assert "(*r).named = false" in _body(pci, "requesters_add")
    assert "PCIE_TYPE_PCIE_TO_PCI: u16 = 7" in pci and "PCIE_TYPE_PCI_TO_PCIE: u16 = 8" in pci

