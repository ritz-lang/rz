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
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
KERNEL_SRC = RITZ_ROOT.parent / "harland" / "kernel" / "src"
DMAR = KERNEL_SRC / "drivers" / "iommu" / "dmar.ritz"
VTD = KERNEL_SRC / "drivers" / "iommu" / "vtd.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"

PROGRAM = """\
import drivers.iommu.dmar

var t: [160]u8

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
    0
"""

CLAIMS = {1: "two DRHD units", 2: "DMAR flags", 3: "unit register bases", 4: "INCLUDE_PCI_ALL/segment",
          5: "I/O APIC source ID", 6: "unnameable source ID", 7: "bad signature", 8: "bad length",
          9: "zero-length struct", 10: "struct past end", 11: "IRTE x2APIC dest", 12: "IRTE xAPIC dest + level",
          13: "IRTE dest/vector decode", 14: "IRTE xAPIC 8 bits", 15: "IRTE SID verify", 16: "IRTE no SVT",
          17: "remap MSI addr", 18: "MSI handle round trip", 19: "MSI format bit", 20: "remap RTE hi",
          21: "remap RTE lo", 22: "RTE handle round trip", 23: "RTE format bit", 24: "handles",
          25: "GCMD from GSTS", 26: "IRTA", 27: "ECAP EIM", 28: "ECAP IR/QI", 29: "IEC descriptors",
          30: "wait descriptor", 31: "queue tail"}


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
    body = _body(_code(MSIX), "msix_set_entry")
    assert "vtd_ir_enabled()" in body, body
    assert re.search(r"vtd_ir_set\(\s*\w+\s*,\s*vector\s*,\s*dest\b", body), "the IRTE must carry the vector and destination"
    assert "ir_handle_msi(vector)" in body and "msi_addr_remap(" in body, body
    # the device's requester ID goes into the IRTE for source validation
    assert re.search(r"\.bus\b", body) and re.search(r"\.device\b", body) and re.search(r"\.function\b", body), body


@pytest.mark.unit
def test_ioapic_entries_are_remappable_when_remapping_is_on():
    code = _code(APIC)
    set_irq = _body(code, "ioapic_set_irq")
    assert "vtd_ir_enabled()" in set_irq, set_irq
    assert "ir_handle_ioapic(" in set_irq and "ioapic_rte_remap_hi(" in set_irq and "ioapic_rte_remap_lo(" in set_irq
    assert "vtd_ir_set(" in set_irq, set_irq
    # remapping is up before the I/O APIC is programmed, after the LAPIC mode is known
    select = _body(code, "apic_select_mode")
    assert "vtd_ir_init(" in select, select
    assert select.index("x2apic_mode = 1") < select.index("vtd_ir_init("), select
    for init_fn in ("apic_init_with_mb", "apic_init_from_bootinfo"):
        b = _body(code, init_fn)
        assert b.index("apic_select_mode()") < b.index("ioapic_init()"), init_fn


@pytest.mark.unit
def test_irq_route_counts_remapping_as_reachable():
    code = _code(APIC)
    assert re.search(r"irq_dest_pick\(.*vtd_ir_x2apic\(\)", _body(code, "irq_route_dest")), "irq_route_dest ignores IR"


@pytest.mark.unit
def test_vtd_blocks_compatibility_format_and_invalidates_entries():
    code = _code(VTD)
    # an IRTE change reaches the hardware only after an IEC invalidation
    assert "qi_iec_index_lo(" in _body(code, "vtd_ir_set"), "vtd_ir_set doesn't invalidate the entry"
    init = _code(VTD)
    assert "GCMD_IRE" in init and "GCMD_SIRTP" in init and "GCMD_QIE" in init
    # CFI stays clear: a compatibility-format interrupt would bypass the table
    assert re.search(r"GCMD_CFI", init), "vtd must clear CFI explicitly"
