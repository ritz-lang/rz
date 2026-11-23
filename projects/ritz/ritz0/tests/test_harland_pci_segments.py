"""Harland PCI on segments other than 0: MCFG / ECAM and segment-carrying requester IDs (AGAST #4582).

A multi-segment EPYC puts devices on PCI segments 1+, reachable only through
ECAM (the MCFG table's memory-mapped config space): port I/O 0xCF8/0xCFC
reaches segment 0 alone. AMD-Vi keeps a device table per segment (#4339) and
looks a requester up by segment << 16 | bus:dev.fn, so a device's MSI-X IRTE
must carry its segment too.

drivers/pci_ecam.ritz holds the hardware-free part: the MCFG parser, the ECAM
address of a (segment, bus, device, function, register) and the requester ID
packing. The behaviour test compiles it with a synthetic two-segment MCFG into
a host program whose exit code names the failed claim. QEMU gives no second
segment cheaply (pxb-pcie buses stay on segment 0), so segment 1+ enumeration
is pinned at source level; tools/test_irq_dest_boot.sh boots q35 (which has an
MCFG) and checks segment 0 through ECAM matches port I/O, and
tools/test_msix_boot.sh boots pc (no MCFG) on the port-I/O fallback.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
HARLAND = RITZ_ROOT.parent / "harland"
KERNEL_SRC = HARLAND / "kernel" / "src"
ECAM = KERNEL_SRC / "drivers" / "pci_ecam.ritz"
PCI = KERNEL_SRC / "drivers" / "pci.ritz"
MSIX = KERNEL_SRC / "drivers" / "msix.ritz"
MAIN = KERNEL_SRC / "main.ritz"
IRQ_DEST_BOOT = HARLAND / "tools" / "test_irq_dest_boot.sh"

PROGRAM = """\
import drivers.pci_ecam

var t: [100]u8

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

# MCFG entry i (16 bytes from offset 44): base, segment, start bus, end bus
fn entry(i: i32, base: u64, seg: u32, start: u32, end: u32)
    let o: i32 = 44 + i * 16
    put64(o, base)
    put16(o + 8, seg)
    put8(o + 10, start)
    put8(o + 11, end)

# MCFG: header (36) | reserved (8) | segment 0 buses 00-ff | segment 1
# buses 40-7f | a zero-base entry (skipped)
fn build(len: u32)
    var i: i32 = 0
    while i < 100
        t[i] = 0
        i = i + 1
    put32(0, 0x4746434D)
    put32(4, len)
    entry(0, 0xB0000000, 0, 0x00, 0xFF)
    entry(1, 0x3F000000000, 1, 0x40, 0x7F)
    entry(2, 0, 2, 0x00, 0xFF)

fn main() -> i32
    build(92)
    if mcfg_parse(@t[0], 92) != 2 or mcfg_count != 2
        return 1
    if mcfg_base[0] != 0xB0000000 or mcfg_seg[1] != 1 or mcfg_bus_start[1] != 0x40 or mcfg_bus_end[1] != 0x7F
        return 2
    # which entry covers (segment, bus): none past its bus range or segment
    if mcfg_find(0, 0) != 0 or mcfg_find(0, 0xFF) != 0 or mcfg_find(1, 0x40) != 1 or mcfg_find(1, 0x7F) != 1
        return 3
    if mcfg_find(1, 0x3F) != -1 or mcfg_find(1, 0x80) != -1 or mcfg_find(2, 0) != -1 or mcfg_find(3, 0) != -1
        return 4
    # ECAM: the base names bus 0, so bus N's 1 MiB sits at base + N << 20
    if ecam_addr(0, 0, 0, 0, 0) != 0xB0000000 or ecam_addr(0, 1, 2, 3, 0x10) != 0xB0113010
        return 5
    if ecam_addr(1, 0x41, 0x1F, 7, 0xFFC) != 0x3F000000000 + (0x41 << 20) + (0x1F << 15) + (7 << 12) + 0xFFC
        return 6
    if ecam_addr(1, 0x80, 0, 0, 0) != 0 or ecam_addr(5, 0, 0, 0, 0) != 0
        return 7
    # the bus's 1 MiB window, for mapping it
    if ecam_bus_phys(1, 0x41) != 0x3F000000000 + (0x41 << 20) or ecam_bus_phys(1, 0x3F) != 0
        return 8
    # requester IDs: segment << 16 | bus << 8 | device << 3 | function
    if pci_sid(0, 0, 3, 0) != 0x18 or pci_sid(0, 0x12, 0x1F, 7) != 0x12FF
        return 9
    if pci_sid(1, 0x41, 0, 0) != 0x14100 or pci_sid(0xABCD, 0xFF, 0x1F, 7) != 0xABCDFFFF
        return 10
    # MCFG segments other than 0
    if mcfg_has_other_segments() != true
        return 11
    entry(1, 0x3F000000000, 0, 0x80, 0xFF)
    if mcfg_parse(@t[0], 92) != 2 or mcfg_has_other_segments()
        return 11
    # not an MCFG / shorter than its header / header longer than the bytes
    build(92)
    t[0] = 0x41
    if mcfg_parse(@t[0], 92) != -1 or mcfg_count != 0
        return 12
    build(92)
    if mcfg_parse(@t[0], 40) != -1 or mcfg_count != 0
        return 13
    build(200)
    if mcfg_parse(@t[0], 92) != -1 or mcfg_count != 0
        return 14
    # a truncated last entry is dropped; end bus below start bus too
    build(70)
    if mcfg_parse(@t[0], 92) != 1 or mcfg_find(1, 0x40) != -1
        return 15
    build(92)
    entry(1, 0x3F000000000, 1, 0x7F, 0x40)
    if mcfg_parse(@t[0], 92) != 1
        return 16
    # no more than PCI_MCFG_MAX entries are kept
    if PCI_MCFG_MAX != 8
        return 17
    return 0
"""

CLAIMS = {1: "two usable entries", 2: "entry fields", 3: "find in range", 4: "find out of range",
          5: "ECAM address seg 0", 6: "ECAM address seg 1", 7: "ECAM address uncovered",
          8: "bus window", 9: "sid seg 0", 10: "sid seg 1+", 11: "other segments",
          12: "bad signature", 13: "too short", 14: "length past bytes", 15: "truncated entry",
          16: "end bus below start", 17: "max entries"}


def _run_program(tmp_path, program, claims):
    tree = tmp_path / "tree" / "drivers"
    tree.mkdir(parents=True)
    (tree / "pci_ecam.ritz").write_text(ECAM.read_text())
    (tmp_path / "t.ritz").write_text(program)
    env = dict(os.environ, RITZ_PATH=f"{tmp_path / 'tree'}:{RITZ_ROOT}:{tmp_path}")
    objs = []
    for src, name, extra in [(tmp_path / "t.ritz", "t", ()),
                             (tree / "pci_ecam.ritz", "pci_ecam", ("--no-runtime",))]:
        ll = tmp_path / f"{name}.ll"
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env, timeout=300)
        assert proc.returncode == 0 and ll.exists(), f"ritz0 rejected {name}:\n{proc.stdout}{proc.stderr}"
        objs.append(str(ll))
    exe = tmp_path / "t"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe), "-nostdlib", "-no-pie"],
                          capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-3000:]
    rc = subprocess.run([str(exe)], capture_output=True, timeout=60).returncode
    assert rc == 0, f"exit {rc}: {claims.get(rc, 'crash')}"


@pytest.mark.integration
def test_mcfg_parse_ecam_address_and_sid(tmp_path):
    _run_program(tmp_path, PROGRAM, CLAIMS)


# --- source level --------------------------------------------------------------

def _code(path):
    return "\n".join(line.split("#", 1)[0].rstrip() for line in path.read_text().splitlines())


def _body(code, name):
    m = re.search(rf"^(?:pub\s+)?fn {name}\(.*?(?=^\S)", code + "\nEND", re.M | re.S)
    assert m, f"fn {name} not found"
    return m.group(0)


@pytest.mark.unit
def test_pci_ecam_module_is_import_free():
    assert not re.search(r"^import\b", _code(ECAM), re.M), "pci_ecam.ritz must stay import-free (host-compiled)"


@pytest.mark.unit
def test_pci_device_carries_its_segment():
    code = _code(PCI)
    struct = re.search(r"^pub struct PciDevice\n(.*?)(?=^\S)", code, re.M | re.S).group(1)
    assert re.search(r"^\s+segment: u16$", struct, re.M), "PciDevice has no segment"
    probe = _body(code, "pci_probe_function")
    assert "dev.segment = seg" in probe, probe


@pytest.mark.unit
def test_config_access_goes_through_ecam_with_port_io_fallback():
    code = _code(PCI)
    rd = _body(code, "pci_seg_read_config32")
    wr = _body(code, "pci_seg_write_config32")
    for b in (rd, wr):
        # ECAM where MCFG covers the bus; port I/O only for segment 0
        assert "pci_ecam_virt(" in b and "volatile_" in b, b
        assert re.search(r"seg\s*==\s*0", b) and "PCI_CONFIG_ADDRESS" in b, b
    assert "0xFFFFFFFF" in rd, "an uncovered segment must read as no device"
    # the device-based accessors use the device's segment
    for fn in ("pci_dev_read_config8", "pci_dev_read_config16", "pci_dev_read_config32",
               "pci_dev_write_config16", "pci_dev_write_config32"):
        assert "(*dev).segment" in _body(code, fn), fn
    # ECAM buses are mapped 1 MiB at a time, as reached, not the whole 256 MiB
    assert "ecam_bus_phys(" in _body(code, "pci_ecam_virt") and "vmm_map_mmio(" in _body(code, "pci_ecam_virt")


@pytest.mark.unit
def test_segments_past_0_are_enumerated_from_mcfg():
    code = _code(PCI)
    seg = _body(code, "pci_init_segments")
    assert "mcfg_parse(" in seg, seg
    # segment 0 was scanned over port I/O by pci_init; ECAM is checked against it
    assert "pci_ecam_check(" in seg, seg
    # every MCFG bus nothing reached is probed for a root bus (#4599), which
    # covers segment 1+'s lowest bus too
    assert "pci_scan_roots(" in seg, seg
    roots = _body(code, "pci_scan_roots")
    assert "mcfg_seg[" in roots and "pci_scan_bus(" in roots, roots
    # bridges found there get their secondary buses scanned in their own segment
    assert "pci_scan_bridges(" in roots
    assert "(*dev).segment" in _body(code, "pci_scan_bridges")
    # main runs it once ACPI (in apic_init_*) has found the tables
    main = _code(MAIN)
    assert "pci_init_segments(" in main
    assert main.index("apic_init_from_bootinfo(") < main.index("pci_init_segments(")


@pytest.mark.unit
def test_drivers_use_segment_aware_config_access():
    # bus/device/function accessors reach segment 0 only: a driver must go
    # through its PciDevice so a segment-1 device gets its own config space
    for path in KERNEL_SRC.rglob("*.ritz"):
        if path.name in ("pci.ritz", "pci_ecam.ritz"):
            continue
        assert not re.search(r"\bpci_(read|write)_config(8|16|32)\(", _code(path)), path


@pytest.mark.unit
def test_msix_sid_carries_the_segment():
    body = _body(_code(MSIX), "msix_sid")
    assert "pci_dev_sid(" in body, body
    assert "pci_sid(" in _body(_code(PCI), "pci_dev_sid") and "(*dev).segment" in _body(_code(PCI), "pci_dev_sid")


@pytest.mark.unit
def test_q35_boot_checks_ecam():
    text = IRQ_DEST_BOOT.read_text()
    assert "[pci] ECAM matches port I/O" in text


# --- other host bridges' root buses (AGAST #4599) ------------------------------
#
# pci_init scans bus 0 and the bridges below it. An EPYC has a root complex
# per quadrant (root buses 0x00/0x40/0x80/0xC0 in one segment) and QEMU's
# pxb-pcie adds a root bus at bus_nr: neither sits behind a P2P bridge, so a
# bridge walk never reaches them. pci_init_segments marks every bus a device
# or a bridge's secondary..subordinate range accounts for, then probes the
# MCFG buses still unmarked for a root bus (the brute-force scan; harland
# parses no AML, so no _BBN). tools/test_irq_dest_boot.sh's plain boot puts a
# pxb-pcie at bus 0x40 with a root port and a device behind it.

ROOTS_PROGRAM = """\
import drivers.pci_ecam

var t: [100]u8

fn put8(off: i32, v: u32)
    t[off] = (v & 0xFF) as u8

fn put16(off: i32, v: u32)
    put8(off, v)
    put8(off + 1, v >> 8)

fn put32(off: i32, v: u32)
    put16(off, v)
    put16(off + 2, v >> 16)

fn entry(i: i32, base: u64, seg: u32, start: u32, end: u32)
    let o: i32 = 44 + i * 16
    put32(o, (base & 0xFFFFFFFF) as u32)
    put32(o + 4, (base >> 32) as u32)
    put16(o + 8, seg)
    put8(o + 10, start)
    put8(o + 11, end)

# segment 0 buses 00-7f and 80-ff (two entries), segment 1 buses 40-7f
fn build()
    var i: i32 = 0
    while i < 100
        t[i] = 0
        i = i + 1
    put32(0, 0x4746434D)
    put32(4, 92)
    entry(0, 0xB0000000, 0, 0x00, 0x7F)
    entry(1, 0xB0000000, 0, 0x80, 0xFF)
    entry(2, 0x3F000000000, 1, 0x40, 0x7F)

fn main() -> i32
    build()
    if mcfg_parse(@t[0], 92) != 3
        return 1
    # nothing reached yet: each entry's first bus, clamped up to its start
    if pci_bus_unreached(0, 0) != 0 or pci_bus_unreached(2, 0) != 0x40 or pci_bus_unreached(1, 0) != 0x80
        return 2
    # bus 0 and a bridge range 01-3f reached: the next root candidate is 0x40
    pci_bus_mark(0, 0, 0)
    pci_bus_mark(0, 1, 0x3F)
    if pci_bus_unreached(0, 0) != 0x40 or pci_bus_unreached(0, 0x41) != 0x41
        return 3
    # marks stay in their segment
    if pci_bus_unreached(2, 0) != 0x40
        return 4
    # a range spanning two entries of one segment marks both
    pci_bus_mark(0, 0x40, 0x85)
    if pci_bus_unreached(0, 0) != -1 or pci_bus_unreached(1, 0) != 0x86
        return 5
    # bus 0xff: the mark loop ends, the last bus is found, past it is none
    pci_bus_mark(0, 0x86, 0xFE)
    if pci_bus_unreached(1, 0) != 0xFF or pci_bus_unreached(1, 0x100) != -1
        return 6
    pci_bus_mark(0, 0xFF, 0xFF)
    if pci_bus_unreached(1, 0) != -1
        return 6
    # buses no entry covers are ignored; hi < lo marks nothing
    pci_bus_mark(1, 0x80, 0xFF)
    pci_bus_mark(1, 0x50, 0x4F)
    if pci_bus_unreached(2, 0) != 0x40
        return 7
    # no such entry
    if pci_bus_unreached(3, 0) != -1 or pci_bus_unreached(-1, 0) != -1
        return 8
    # a new MCFG starts with nothing reached
    if mcfg_parse(@t[0], 92) != 3 or pci_bus_unreached(0, 0) != 0
        return 9
    # an entry overlapping an earlier one of its segment: the earlier owns
    # the shared buses, so they are never a root candidate twice
    entry(1, 0xC0000000, 0, 0x70, 0x8F)
    if mcfg_parse(@t[0], 92) != 3 or pci_bus_unreached(1, 0) != 0x80
        return 10
    return 0
"""

ROOTS_CLAIMS = {1: "parse", 2: "nothing reached", 3: "next candidate after bridges", 4: "per segment",
                5: "range over two entries", 6: "bus 0xff", 7: "uncovered / empty ranges",
                8: "no such entry", 9: "parse resets", 10: "overlapping entries"}


@pytest.mark.integration
def test_unreached_buses_are_root_candidates(tmp_path):
    _run_program(tmp_path, ROOTS_PROGRAM, ROOTS_CLAIMS)


@pytest.mark.unit
def test_root_scan_marks_devices_and_bridge_ranges():
    code = _code(PCI)
    mark = _body(code, "pci_mark_reached")
    # each device's own bus, and a bridge's secondary (0x19)..subordinate (0x1A)
    assert "pci_bus_mark((*dev).segment as u32, (*dev).bus as u32, (*dev).bus as u32)" in mark, mark
    assert "pci_dev_read_config8(dev, 0x19)" in mark and "pci_dev_read_config8(dev, 0x1A)" in mark, mark
    assert "pci_bus_mark((*dev).segment as u32, secondary as u32, subordinate as u32)" in mark, mark
    roots = _body(code, "pci_scan_roots")
    # walk each entry's unreached buses; mark what a new root brings in
    assert "pci_bus_unreached(" in roots and "pci_mark_reached(" in roots and "pci_bus_has_device(" in roots
    assert "klog(" in roots and "print" not in roots
    # the scan starts from what pci_init found on segment 0
    seg = _body(code, "pci_init_segments")
    assert seg.index("pci_mark_reached(0)") < seg.index("pci_scan_roots(")


@pytest.mark.unit
def test_probing_a_bus_maps_one_page_per_device_not_the_bus():
    # mapping each candidate bus's whole 1 MiB would fill page tables for
    # buses that are mostly empty: probe function 0's 4 KiB only
    body = _body(_code(PCI), "pci_bus_has_device")
    assert "vmm_map_mmio(" in body and "0x1000" in body, body
    assert "pci_seg_read_config" not in body, body


@pytest.mark.unit
def test_device_table_fits_a_large_epyc_and_logs_overflow():
    code = _code(PCI)
    assert re.search(r"^const PCI_MAX_DEVICES: i32 = 256$", code, re.M)
    assert re.search(r"^var pci_devices: \[256\]PciDevice$", code, re.M)
    probe = _body(code, "pci_probe_function")
    assert "pci_devices_dropped = pci_devices_dropped + 1" in probe, probe
    assert "pci_log_dropped()" in _body(code, "pci_init_segments") and "pci_log_dropped()" in _body(code, "pci_init")
    assert "klog(" in _body(code, "pci_log_dropped")


@pytest.mark.unit
def test_q35_boot_has_a_pxb_root_bus():
    text = IRQ_DEST_BOOT.read_text()
    assert "pxb-pcie" in text and "bus_nr=0x40" in text
    assert "[pci] root bus 0000:40" in text
