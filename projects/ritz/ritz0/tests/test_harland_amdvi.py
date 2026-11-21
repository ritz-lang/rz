"""Harland's AMD-Vi interrupt remapping formats and IVRS parsing (AGAST #4329).

On AMD machines with APIC IDs past 254 (EPYC), a device interrupt reaches its
CPU only through AMD-Vi interrupt remapping: the IOMMU looks the requester's
device ID up in the device table, whose entry (DTE) points at the device's
interrupt remapping table; the MSI data / redirection-entry vector indexes it,
and in GA mode with XT the 128-bit entry holds a 32-bit x2APIC destination.

drivers/iommu/ivrs.ritz holds the parts with no hardware: the IVRS parser
(IVHD 10h/11h/40h, the highest type wins; select/range/alias/special/ACPI HID
entries), the DTE / IRTE / message encodings and the command-buffer commands
and register values drivers/iommu/amdvi.ritz writes. The behaviour test
compiles it with a synthetic IVRS (an IVHD 10h and two 11h blocks describing
the same platform, an IVMD block to skip) into a host program whose exit code
names the failed claim. Source-level tests pin how the kernel uses it, through
the vendor-neutral drivers/iommu/ir.ritz. tools/test_irq_dest_boot.sh boots it
on q35 with -device amd-iommu,intremap=on,xtsup=on.
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
IVRS = KERNEL_SRC / "drivers" / "iommu" / "ivrs.ritz"
AMDVI = KERNEL_SRC / "drivers" / "iommu" / "amdvi.ritz"
IR = KERNEL_SRC / "drivers" / "iommu" / "ir.ritz"
APIC = KERNEL_SRC / "arch" / "x86_64" / "apic.ritz"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"

PROGRAM = """\
import drivers.iommu.ivrs

var t: [300]u8

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

# IVHD header at `o`: type, length, IOMMU device ID, MMIO base
fn ivhd(o: i32, ty: u32, len: u32, devid: u32, base: u64)
    put8(o, ty)
    put16(o + 2, len)
    put16(o + 4, devid)
    put64(o + 8, base)

# IVRS: header (48) | IVHD 10h (24 + 8 = 32) | IVMD 21h (32, skipped)
#      | IVHD 11h A (40 + 72 = 112) | IVHD 11h B (40 + 4 = 44)
fn build(len: u32)
    var i: i32 = 0
    while i < 300
        t[i] = 0
        i = i + 1
    put32(0, 0x53525649)
    put32(4, len)
    put32(36, 0x00203041)
    ivhd(48, 0x10, 32, 0x0002, 0xFEB00000)
    put32(68, 0x41)               # 10h features: XTSup, GASup
    put32(72, 0x00001002)         # select 00:02.0
    put8(80, 0x21)                # IVMD: skipped
    put16(82, 32)
    ivhd(112, 0x11, 112, 0x0002, 0xFEB00000)
    put64(136, 0xC4)              # EFR image: GA, IA, XT
    put32(152, 0x00000802)        # select 00:01.0
    put32(156, 0x00010003)        # range 01:00.0 ..
    put32(160, 0x0001FF04)        #   .. 01:1f.7
    put32(164, 0x00030043)        # alias range 03:00.0 ..
    put16(169, 0x0028)            #   arriving as 00:05.0
    put32(172, 0x0003FF04)        #   .. 03:1f.7
    put32(176, 0x00041042)        # alias select 04:02.0
    put16(181, 0x0400)            #   arriving as 04:00.0
    put8(184, 0x48)               # special: I/O APIC 9 is 00:14.0
    put8(188, 9)
    put16(189, 0x00A0)
    put8(191, 1)
    put8(192, 0x48)               # special: HPET 0 is 00:14.5
    put8(196, 0)
    put16(197, 0x00A5)
    put8(199, 2)
    put8(200, 0xF0)               # ACPI HID device 00:1e.0, UID length 2: 24 bytes
    put16(201, 0x00F0)
    put8(221, 2)
    ivhd(224, 0x11, 44, 0x0600, 0x1FEB80000)
    put64(248, 0x80)              # EFR image: GA only
    put32(264, 0x00050002)        # select 05:00.0

fn main() -> i32
    build(268)
    if ivrs_parse(@t[0], 268) != 2 or ivrs_num_units != 2 or ivrs_ivhd_type != 0x11
        return 1
    if ivrs_ivinfo != 0x00203041
        return 2
    if ivrs_unit_base[0] != 0xFEB00000 or ivrs_unit_base[1] != 0x1FEB80000 or ivrs_unit_devid[1] != 0x0600
        return 3
    if ivrs_unit_efr[0] != 0xC4 or ivrs_unit_efr[1] != 0x80
        return 4
    # the last device ID: the second IOMMU's own (0x600), past every entry
    if ivrs_last_devid != 0x0600
        return 5
    if ivrs_num_special != 2 or ivrs_ioapic_devid(9) != 0x00A0 or ivrs_ioapic_devid(0) != IVRS_DEVID_NONE
        return 6
    if ivrs_alias(0x0350) != 0x0028 or ivrs_alias(0x0300) != 0x0028 or ivrs_alias(0x03FF) != 0x0028
        return 7
    if ivrs_alias(0x0410) != 0x0400 or ivrs_alias(0x0411) != 0x0411 or ivrs_alias(0x01FF) != 0x01FF
        return 8
    # only 10h known (the 11h blocks retyped): its features become EFR bits
    put8(112, 0x12)
    put8(224, 0x12)
    if ivrs_parse(@t[0], 268) != 1 or ivrs_ivhd_type != 0x10 or ivrs_unit_efr[0] != (EFR_XT_SUP | EFR_GA_SUP)
        return 9
    if ivrs_last_devid != 0x0010 or ivrs_num_special != 0 or ivrs_num_aliases != 0
        return 10
    # not an IVRS / too short / header longer than the bytes we have
    build(268)
    t[0] = 0x41
    if ivrs_parse(@t[0], 268) != -1 or ivrs_num_units != 0
        return 11
    build(268)
    if ivrs_parse(@t[0], 40) != -1 or ivrs_parse(@t[0], 280) != -1
        return 12
    # a zero-length block ends the parse without looping
    put16(50, 0)
    if ivrs_parse(@t[0], 268) != 0
        return 13
    # an unknown variable-length entry ends that block's entries
    build(268)
    put8(184, 0x85)
    if ivrs_parse(@t[0], 268) != 2 or ivrs_num_special != 0 or ivrs_num_aliases != 2
        return 14
    # a block running past the end is dropped
    build(268)
    put16(226, 60)
    if ivrs_parse(@t[0], 268) != 1
        return 15

    # DTE: DMA pass-through (V, TV, Mode 0, IR, IW); IV + IntTabLen 8 +
    # root + IntCtl 10b; blocked = IV with IntCtl 00b
    if dte_q0_passthrough() != 0x6000000000000003
        return 16
    if dte_q2_remap(0x12345000) != 0x2000000012345011 or dte_q2_irt(dte_q2_remap(0x12345000)) != 0x12345000
        return 17
    if not dte_q2_is_remap(dte_q2_remap(0x1000)) or dte_q2_is_remap(dte_q2_blocked()) or dte_q2_blocked() != 1
        return 18
    if amdvi_devtab_reg(0x3DB000, 2) != 0x3DB001 or amdvi_devtab_pages(0xFB) != 2 or amdvi_devtab_pages(0x7F) != 1 or amdvi_devtab_pages(0x80) != 2
        return 19
    if amdvi_devtab_pages(0x0600) != 13 or amdvi_devtab_pages(0xFFFF) != 512 or amdvi_devtab_reg(0x200000, 512) != 0x2001FF
        return 20
    # IRTEs: 32-bit legacy (dest 15:8, vector 23:16), 128-bit GA (dest 31:8 + 63:56 of hi)
    if irte32(0x41, 0x105) != 0x00410501 or irte32_dest(irte32(0x41, 0x17)) != 0x17
        return 21
    if irte_ga_lo(0x12345678) != 0x34567801 or irte_ga_hi(0x41, 0x12345678) != 0x1200000000000041
        return 22
    if irte_ga_dest(irte_ga_lo(256), irte_ga_hi(0x40, 256)) != 256 or irte_ga_dest(irte_ga_lo(0xFFFFFFFE), irte_ga_hi(0x40, 0xFFFFFFFE)) != 0xFFFFFFFE
        return 23
    if irte_ga_vector(irte_ga_hi(0x41, 0x12345678)) != 0x41
        return 24
    # messages: the handle in MSI data / the RTE vector, fixed delivery
    if amdvi_msi_data(192) != 192 or amdvi_msi_handle(0xC0) != 0xC0 or amdvi_msi_handle(0x87C0) != 0x7C0
        return 25
    if amdvi_rte_lo(4, true) != 0x10004 or amdvi_rte_lo(1, false) != 1 or amdvi_rte_handle(amdvi_rte_lo(23, true)) != 23
        return 26
    # control: on with the command buffer, GA bit 17, XT bit 50; event log
    # and guest APIC mode cleared, other firmware bits kept
    if amdvi_control(0, true, true) != 0x0004000000021001 or amdvi_control(0xE000404, false, false) != 0x1401
        return 27
    if amdvi_control(0x0004000000020000, true, false) != 0x21001
        return 28
    # modes: GA if EFR has it, XT on top only in x2APIC mode with XTSup
    if amdvi_pick_modes(0xC4, true) != 3 or amdvi_pick_modes(0x80, true) != 1 or amdvi_pick_modes(0x84, false) != 1
        return 29
    if amdvi_pick_modes(0x04, true) != 0
        return 30
    # commands: opcode in 63:60
    if amdvi_cmdbuf_reg(0x5000) != 0x0800000000005000
        return 31
    if cmd_wait_lo(0x3DC000) != 0x10000000003DC001 or cmd_wait_lo(0x3DC007) != 0x10000000003DC001
        return 32
    if cmd_inv_irt_lo(0xA0) != 0x50000000000000A0 or cmd_inv_dte_lo(0x10020) != 0x2000000000000020 or cmd_inv_all_lo() != 0x8000000000000000
        return 33
    if cmd_next_tail(0) != 1 or cmd_next_tail(255) != 0
        return 34
    0
"""

CLAIMS = {1: "highest IVHD type, two units", 2: "IVinfo", 3: "unit bases/devids", 4: "EFR images",
          5: "last device ID", 6: "I/O APIC special entry", 7: "alias range", 8: "alias select",
          9: "10h-only features", 10: "10h-only entries", 11: "bad signature", 12: "bad length",
          13: "zero-length block", 14: "unknown entry stops", 15: "block past end",
          16: "DTE q0 pass-through", 17: "DTE q2 remap", 18: "DTE q2 blocked", 19: "devtab reg/pages",
          20: "devtab pages large", 21: "IRTE 32-bit", 22: "IRTE GA encode", 23: "IRTE GA dest round trip",
          24: "IRTE GA vector", 25: "MSI data handle", 26: "RTE handle", 27: "control bits",
          28: "control drops XT", 29: "pick GA/XT", 30: "no GA", 31: "cmdbuf reg",
          32: "COMPLETION_WAIT", 33: "invalidation commands", 34: "command tail"}


@pytest.mark.integration
def test_ivrs_parse_and_amdvi_formats(tmp_path):
    tree = tmp_path / "tree" / "drivers" / "iommu"
    tree.mkdir(parents=True)
    (tree / "ivrs.ritz").write_text(IVRS.read_text())
    (tmp_path / "t.ritz").write_text(PROGRAM)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "ivrs.ritz", "ivrs", ("--no-runtime",))]:
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


# --- source level --------------------------------------------------------------

def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


@pytest.mark.unit
def test_ivrs_module_is_import_free():
    assert not re.search(r"^import\b", _code(IVRS), re.M), "ivrs.ritz must stay import-free (host-compiled)"


@pytest.mark.unit
def test_msix_and_ioapic_call_only_the_vendor_neutral_layer():
    for path in (MSIX, APIC):
        code = _code(path)
        assert not re.search(r"\b(vtd|amdvi)_\w+\(", code), f"{path.name} calls a vendor driver directly"
        assert "import drivers.iommu.ir " in code, path.name


@pytest.mark.unit
def test_ir_init_tries_vtd_then_amdvi():
    body = _body(_code(IR), "ir_init")
    assert "ACPI_SIG_DMAR" in body and "vtd_ir_init(" in body and "amdvi_ir_init(" in body, body
    assert body.index("vtd_ir_init(") < body.index("amdvi_ir_init("), body
    # every per-vendor entry point dispatches to both
    code = _code(IR)
    for fn in ("ir_enabled", "ir_x2apic", "ir_set"):
        b = _body(code, fn)
        assert "vtd_" in b and "amdvi_" in b, fn


@pytest.mark.unit
def test_amdvi_invalidates_after_every_table_change():
    code = _code(AMDVI)
    # an IRTE change reaches the IOMMU only after INVALIDATE_INTERRUPT_TABLE + COMPLETION_WAIT
    assert "cmd_inv_irt_lo(" in _body(code, "amdvi_ir_set"), "amdvi_ir_set doesn't invalidate the table"
    assert "amdvi_cmd_sync(" in _body(code, "amdvi_cmd_all") and "cmd_wait_lo(" in _body(code, "amdvi_cmd_sync")
    # a new DTE (the device's first IRT) is invalidated too
    assert "cmd_inv_dte_lo(" in _body(code, "amdvi_irt")


@pytest.mark.unit
def test_amdvi_blocks_unremapped_interrupts_and_passes_dma():
    init = _body(_code(AMDVI), "amdvi_ir_init")
    # every DTE: DMA untranslated, interrupts aborted until the device gets a table
    assert "dte_q0_passthrough()" in init and "dte_q2_blocked()" in init, init
    # the whole table is one physically contiguous run the IOMMU reads by length
    assert "pmm_alloc_contig(" in init and "amdvi_devtab_pages(" in init, init
    # GA / XT come from the EFR (MMIO and IVHD image) and the LAPIC mode
    assert "AMDVI_REG_EFR" in init and "amdvi_pick_modes(" in init, init
