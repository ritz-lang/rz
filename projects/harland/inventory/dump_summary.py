#!/usr/bin/env python3
"""Summarize a hardware-inventory dump on the host (AGAST #4300).

HWINV.EFI writes raw bytes. This reads them back as the few facts a person
asks first: the machine, firmware, CPU, RAM, PCI device names, the display.
PCI names come from pci.ids (the database lspci uses), which the stick does
not carry, so they are looked up here.

    machine   SMBIOS type 1 and 2 (manufacturer, product, board)
    firmware  SMBIOS type 0 and firmware.txt (UEFI revision, Secure Boot)
    CPU       SMBIOS type 4 (name, cores, threads, speed) and the MADT's
              enabled local APICs
    RAM       every populated SMBIOS type 17 device, the total, and the RAM
              the UEFI memory map holds
    PCI       every function in pci.txt: address, IDs, class, vendor and
              device name
    display   the GOP's current mode and each EDID's name and size

Serial numbers and UUIDs are never printed, so the summary of a raw dump is
as safe to commit as one of a scrubbed dump.

Usage: dump_summary.py DUMP [--pci-ids FILE] [-o OUT]
"""

import argparse
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_dump

PCI_IDS_PATHS = ["/usr/share/misc/pci.ids", "/usr/share/hwdata/pci.ids", "/usr/share/pci.ids"]
MEM_TYPES = {0x01: "Other", 0x02: "Unknown", 0x12: "DDR", 0x13: "DDR2", 0x18: "DDR3", 0x1A: "DDR4", 0x1B: "LPDDR", 0x1C: "LPDDR2",
             0x1D: "LPDDR3", 0x1E: "LPDDR4", 0x22: "DDR5", 0x23: "LPDDR5"}
CPU_FAMILY_UNKNOWN = {"", "Unknown", "None", "To Be Filled By O.E.M."}


class PciIds:
    """pci.ids: vendors, devices, classes and subclasses."""

    def __init__(self, path):
        self.version, self.vendors, self.devices, self.classes = "", {}, {}, {}
        if path is None:
            return
        vendor = cls = None
        for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
            if m := re.fullmatch(r"#\s*Version:\s*(\S+)", line):
                self.version = m[1]
            if not line or line.startswith("#"):
                continue
            if m := re.fullmatch(r"C ([0-9a-f]{2})\s+(.*)", line):
                cls, vendor = int(m[1], 16), None
                self.classes[(cls, None)] = m[2]
            elif m := re.fullmatch(r"([0-9a-f]{4})\s+(.*)", line):
                vendor, cls = int(m[1], 16), None
                self.vendors[vendor] = m[2]
            elif vendor is not None and (m := re.fullmatch(r"\t([0-9a-f]{4})\s+(.*)", line)):
                self.devices[(vendor, int(m[1], 16))] = m[2]
            elif cls is not None and (m := re.fullmatch(r"\t([0-9a-f]{2})\s+(.*)", line)):
                self.classes[(cls, int(m[1], 16))] = m[2]

    def name(self, ven, did, cls):
        kind = self.classes.get((cls >> 16, (cls >> 8) & 0xFF)) or self.classes.get((cls >> 16, None))
        who = " ".join(x for x in (self.vendors.get(ven), self.devices.get((ven, did))) if x)
        return f"{kind}: {who}" if kind and who else (kind or who)


def find_pci_ids():
    return next((p for p in PCI_IDS_PATHS if Path(p).is_file()), None)


def _smbios(d):
    try:
        return list(check_dump.smbios_structures((d / "smbios" / "DMI").read_bytes()))
    except (OSError, check_dump.DumpError):
        return []


def summarize(d, pci_ids=None):
    d = check_dump.find_dump_dir(d)
    ids = PciIds(pci_ids)
    c = check_dump.Checker(d)
    c.run()
    structs = _smbios(d)
    by_type = {}
    for st in structs:
        by_type.setdefault(st.typ, []).append(st)
    out = []

    def first(typ):
        return by_type.get(typ, [None])[0]

    out.append("Hardware inventory summary (dump_summary.py, from the HWINV dump beside it)")
    out.append("")
    if st := first(1):
        out.append(f"Machine   {st.s(4)} {st.s(5)} ({st.s(6)})".rstrip())
    if st := first(2):
        out.append(f"Board     {st.s(4)} {st.s(5)} ({st.s(6).strip() or '-'})")
    fw = c.facts.get("firmware", {})
    if st := first(0):
        out.append(f"Firmware  {st.s(4)} {st.s(5)} ({st.s(8)})")
    if fw:
        uefi = int(fw.get("uefi", "0"), 16)
        out.append(f"UEFI      {uefi >> 16}.{uefi & 0xFFFF:02d}"
                   f" by {fw.get('vendor', '?')} {fw.get('revision', '')};"
                   f" Secure Boot {fw.get('secure_boot', '?')}, setup mode {fw.get('setup_mode', '?')}")
    out.append("")
    for st in by_type.get(4, []):
        if not st.byte(0x18) & 0x40:      # status: socket populated
            continue
        cores, threads = st.byte(0x23), st.byte(0x25)
        if cores == 0xFF and st.ln >= 0x2C:
            cores = st.word(0x2A)
        if threads == 0xFF and st.ln >= 0x30:
            threads = st.word(0x2E)
        name = st.s(0x10).strip() or st.s(0x07)
        out.append(f"CPU       {name}")
        out.append(f"          {cores} cores, {threads} threads; {st.word(0x16)} MHz now, "
                   f"{st.word(0x14)} MHz max ({st.s(0x04)})")
    if "cpus" in c.facts:
        out.append(f"          MADT: {c.facts['cpus']} enabled local APICs")
    out.append("")
    total = 0
    for st in by_type.get(17, []):
        size = st.word(0x0C)
        if size in (0, 0xFFFF):
            continue
        mib = struct.unpack_from("<I", st.dmi, st.off + 0x1C)[0] if size == 0x7FFF and st.ln >= 0x20 \
            else ((size & 0x7FFF) // 1024 if size & 0x8000 else size)
        total += mib
        kind = MEM_TYPES.get(st.byte(0x12), f"type {st.byte(0x12):#x}")
        speed = st.word(0x15) if st.ln >= 0x17 else 0
        part = st.s(0x1A).strip() if st.ln >= 0x1B else ""
        maker = st.s(0x17).strip() if st.ln >= 0x18 else ""
        out.append(f"RAM       {st.s(0x10)}: {mib} MiB {kind}"
                   + (f" {speed} MT/s" if speed else "")
                   + "".join(f", {x}" for x in (maker, part) if x))
    out.append(f"RAM total {total} MiB in SMBIOS; the UEFI memory map holds "
               f"{c.facts.get('memmap_ram_mib', '?')} MiB")
    out.append("")
    gop = (d / "gop.txt").read_text() if (d / "gop.txt").is_file() else ""
    out.append(f"Display   GOP mode {c.facts.get('gop', 'absent')}")
    for e in sorted(d.glob("edid-*.bin")):
        b = e.read_bytes()
        if len(b) < 128:
            continue
        maker = struct.unpack(">H", b[8:10])[0]
        pnp = "".join(chr(64 + ((maker >> s) & 0x1F)) for s in (10, 5, 0))
        names = []
        for i in range(4):
            blk = b[54 + 18 * i:72 + 18 * i]
            if blk[:3] == b"\0\0\0" and blk[3] in (0xFC, 0xFE):
                t = blk[5:].split(b"\n")[0].decode("latin-1").strip()
                if t and t not in names:
                    names.append(t)
        out.append(f"          {e.name}: {pnp} {struct.unpack('<H', b[10:12])[0]:04x}"
                   f" {', '.join(names)}; {b[21]} x {b[22]} cm".rstrip())
    if not gop:
        out.append("          (no gop.txt)")
    out.append("")
    out.append(f"PCI       names from pci.ids {ids.version or '(none found: ids only)'}")
    txt = (d / "pci.txt").read_text() if (d / "pci.txt").is_file() else ""
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        ven, did = (int(x, 16) for x in parts[1].split(":"))
        cls = int(parts[3], 16)
        name = ids.name(ven, did, cls)
        out.append(f"  {parts[0]} {parts[1]}" + (f" {name}" if name else f" class {cls:06x}"))
    out.append("")
    out.append("ACPI      " + " ".join(sorted(c.facts.get("acpi", []))))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Summarize a hardware-inventory dump.")
    ap.add_argument("dump")
    ap.add_argument("--pci-ids", help=f"pci.ids file (default: the first of {PCI_IDS_PATHS})")
    ap.add_argument("-o", "--out", help="write here instead of stdout")
    args = ap.parse_args(argv)
    text = summarize(Path(args.dump), args.pci_ids or find_pci_ids())
    if args.out:
        Path(args.out).write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
