#!/usr/bin/env python3
"""Validate a hardware-inventory dump (AGAST #3406).

HWINV.EFI writes \\INVENTORY\\<timestamp>\\ with:

    acpi/RSDP, acpi/XSDT, acpi/<SIG>[n]   every table, raw; names as Linux's
                                          /sys/firmware/acpi/tables (SSDT1,
                                          SSDT2 when a signature repeats),
                                          except that a byte outside [0-9A-Za-z]
                                          is '_' (ASF! is ASF_); DSDT and FACS
                                          come from the FADT
    smbios/smbios_entry_point, smbios/DMI as /sys/firmware/dmi/tables
    memmap.bin, memmap.txt                GetMemoryMap's descriptors
    pci.bin, pci.txt                      config space of every function
    gop.txt, edid-<n>.bin                 GOP modes; EDID where firmware has it
    firmware.txt                          vendor, revision, Secure Boot state
    manifest.txt                          every file and its size; written
                                          last, so its "end" line means the
                                          dump finished

This checks each file's internal consistency (signatures, lengths,
checksums, counts), that the files agree with each other (the XSDT's table
count, the manifest), and any facts pinned with --expect-* (what QEMU was
told: -smp, -m, -smbios type=1, the PCI devices).

Usage: check_dump.py DUMP_DIR_OR_IMAGE_ROOT [--expect-...]
Exit: 0 = the dump is good; 1 = a check failed; 2 = bad usage.
"""

import argparse
import re
import struct
import sys
from pathlib import Path

RAM_TYPES = {1, 2, 3, 4, 5, 6, 7, 9, 10}   # loader, BS, RT code/data, conventional, ACPI
NO_CHECKSUM = {"FACS"}


class DumpError(Exception):
    pass


def file_sig(sig):
    """The file name HWINV gives a table's signature: bytes outside
    [0-9A-Za-z] become '_' (main.ritz table_name), so ASF! is ASF_."""
    return re.sub(r"[^0-9A-Za-z]", "_", sig)


class SmbiosStruct:
    """One SMBIOS structure: its offset in the table, type, handle, formatted
    length, and its strings with their offsets (string i is strings[i - 1])."""

    def __init__(self, dmi, off, ln, end):
        self.off, self.typ, self.ln = off, dmi[off], ln
        self.handle = struct.unpack_from("<H", dmi, off + 2)[0]
        self.strings, self.string_offs = [], []
        at = off + ln
        if end > at:
            for raw in dmi[at:end].split(b"\0"):
                self.strings.append(raw)
                self.string_offs.append(at)
                at += len(raw) + 1
        self.dmi = dmi

    def byte(self, i):
        return self.dmi[self.off + i] if i < self.ln else 0

    def word(self, i):
        return struct.unpack_from("<H", self.dmi, self.off + i)[0] if i + 2 <= self.ln else 0

    def string_index(self, i):
        idx = self.byte(i)
        return idx if 0 < idx <= len(self.strings) else 0

    def s(self, i):
        idx = self.string_index(i)
        return self.strings[idx - 1].decode("latin-1") if idx else ""


def smbios_structures(dmi):
    """Every structure in an SMBIOS structure table, through type 127.
    Raises DumpError on a bad length or a missing string-set terminator."""
    off = 0
    while off + 4 <= len(dmi):
        ln = dmi[off + 1]
        if ln < 4 or off + ln > len(dmi):
            raise DumpError(f"SMBIOS: structure at {off} has a bad length")
        end = dmi.find(b"\0\0", off + ln)
        if end < 0:
            raise DumpError(f"SMBIOS: structure at {off} has no string-set terminator")
        st = SmbiosStruct(dmi, off, ln, end)
        yield st
        if st.typ == 127:
            return
        off = end + 2


def find_dump_dir(root):
    """root itself if it is a dump, else the one INVENTORY/<timestamp> in it."""
    root = Path(root)
    if (root / "manifest.txt").exists() or (root / "acpi").is_dir():
        return root
    inv = root / "INVENTORY"
    dirs = sorted(p for p in inv.iterdir() if p.is_dir()) if inv.is_dir() else []
    if len(dirs) != 1:
        raise DumpError(f"want exactly one dump under {inv}, found {len(dirs)}: "
                        + ", ".join(p.name for p in dirs))
    return dirs[0]


class Checker:
    def __init__(self, d):
        self.d = d
        self.errors = []
        self.facts = {}

    def err(self, msg):
        self.errors.append(msg)

    def read(self, rel):
        p = self.d / rel
        if not p.is_file():
            self.err(f"missing file {rel}")
            return None
        return p.read_bytes()

    # --- ACPI ---------------------------------------------------------------

    def acpi(self):
        rsdp = self.read("acpi/RSDP")
        if rsdp is not None:
            if rsdp[:8] != b"RSD PTR " or len(rsdp) < 20 or sum(rsdp[:20]) & 0xFF:
                self.err("RSDP: bad signature or ACPI 1.0 checksum")
            elif rsdp[15] >= 2:
                length = struct.unpack_from("<I", rsdp, 20)[0]
                if len(rsdp) != length or sum(rsdp) & 0xFF:
                    self.err(f"RSDP: extended length {length} / checksum wrong (file {len(rsdp)} bytes)")
                elif struct.unpack_from("<Q", rsdp, 24)[0] == 0:
                    self.err("RSDP: revision 2 with no XSDT address")
        tables, file_sigs = {}, {}
        for p in sorted((self.d / "acpi").glob("*")) if (self.d / "acpi").is_dir() else []:
            if p.name == "RSDP":
                continue
            t = p.read_bytes()
            tables[p.name] = t
            sig = t[:4].decode("latin-1")
            if not re.fullmatch(re.escape(file_sig(sig)) + r"\d*", p.name):
                self.err(f"acpi/{p.name}: signature is {sig!r}, not the file's name")
                continue
            file_sigs[p.name] = file_sig(sig)
            if len(t) < 8 or struct.unpack_from("<I", t, 4)[0] != len(t):
                self.err(f"acpi/{p.name}: header length != file size {len(t)}")
                continue
            if sig not in NO_CHECKSUM and sum(t) & 0xFF:
                self.err(f"acpi/{p.name}: checksum does not sum to zero")
        self.acpi_tables = tables
        xsdt = tables.get("XSDT")
        if xsdt is None:
            self.err("missing file acpi/XSDT")
            return
        listed = (len(xsdt) - 36) // 8
        via_xsdt = [n for n in tables if n not in ("XSDT", "DSDT", "FACS")]
        if listed != len(via_xsdt):
            self.err(f"XSDT lists {listed} tables but {len(via_xsdt)} were dumped: {sorted(via_xsdt)}")
        sigs = {}
        for n in via_xsdt:
            if n in file_sigs:   # by the table's own signature: DBG2 is not DBG + 2
                sigs.setdefault(file_sigs[n], []).append(n)
        for sig, names in sigs.items():
            want = [sig] if len(names) == 1 else [f"{sig}{i}" for i in range(1, len(names) + 1)]
            if sorted(names) != sorted(want):
                self.err(f"acpi: names for {sig} should be {want} (Linux sysfs style), got {sorted(names)}")
        if "FACP" in tables and "DSDT" not in tables:
            self.err("FADT present but its DSDT was not dumped")
        self.facts["acpi"] = sorted(tables)
        apic = tables.get("APIC")
        if apic is not None and len(apic) >= 44:
            cpus, off = 0, 44
            while off + 2 <= len(apic):
                typ, ln = apic[off], apic[off + 1]
                if ln < 2:
                    self.err("APIC: zero-length entry")
                    break
                if typ == 0 and struct.unpack_from("<I", apic, off + 4)[0] & 1:
                    cpus += 1
                if typ == 9 and struct.unpack_from("<I", apic, off + 8)[0] & 1:
                    cpus += 1
                off += ln
            self.facts["cpus"] = cpus

    # --- SMBIOS -------------------------------------------------------------

    def smbios(self):
        ep = self.read("smbios/smbios_entry_point")
        dmi = self.read("smbios/DMI")
        if ep is None or dmi is None:
            return
        if ep[:5] == b"_SM3_":
            ln = ep[6] if len(ep) > 6 else 0
            if ln < 24 or len(ep) < ln or sum(ep[:ln]) & 0xFF:
                self.err("SMBIOS3 entry point: bad length or checksum")
                return
            max_size = struct.unpack_from("<I", ep, 12)[0]
            if len(dmi) > max_size:
                self.err(f"SMBIOS: DMI is {len(dmi)} bytes, entry point allows {max_size}")
        elif ep[:4] == b"_SM_":
            ln = ep[5]
            if sum(ep[:ln]) & 0xFF or ep[16:21] != b"_DMI_":
                self.err("SMBIOS 2.x entry point: bad checksum or no _DMI_ anchor")
                return
            if struct.unpack_from("<H", ep, 22)[0] != len(dmi):
                self.err("SMBIOS 2.x: table length != DMI size")
        else:
            self.err("SMBIOS entry point: no _SM3_ or _SM_ anchor")
            return
        mem_mib, system, ended = 0, {}, False
        try:
            for st in smbios_structures(dmi):
                if st.typ == 1:
                    system = {"manufacturer": st.s(4), "product": st.s(5), "version": st.s(6),
                              "serial": st.s(7)}
                elif st.typ == 17 and st.ln >= 0x0E:
                    size = st.word(0x0C)
                    if size == 0x7FFF and st.ln >= 0x20:
                        mem_mib += struct.unpack_from("<I", dmi, st.off + 0x1C)[0]
                    elif size not in (0, 0xFFFF):
                        mem_mib += (size & 0x7FFF) // 1024 if size & 0x8000 else size
                ended = st.typ == 127
        except DumpError as e:
            self.err(str(e))
            return
        if not ended:
            self.err("SMBIOS: no end-of-table (type 127) structure")
        self.facts["smbios_system"] = system
        self.facts["smbios_mem_mib"] = mem_mib

    # --- memory map, PCI, GOP, firmware ---------------------------------------

    def memmap(self):
        raw = self.read("memmap.bin")
        txt = self.read("memmap.txt")
        if raw is None or txt is None:
            return
        lines = txt.decode().splitlines()
        m = re.fullmatch(r"desc_size=(\d+) desc_version=(\d+) count=(\d+)", lines[0] if lines else "")
        if not m:
            self.err("memory map: memmap.txt has no desc_size/count header")
            return
        dsz, count = int(m[1]), int(m[3])
        if dsz < 40 or len(raw) != dsz * count or len(lines) - 1 != count:
            self.err(f"memory map: {count} x {dsz}-byte descriptors, but memmap.bin is "
                     f"{len(raw)} bytes and memmap.txt has {len(lines) - 1} entries")
            return
        ram = 0
        for i in range(count):
            typ, _, start, _, pages, _ = struct.unpack_from("<IIQQQQ", raw, i * dsz)
            if typ in RAM_TYPES:
                ram += pages * 4096
        self.facts["memmap_ram_mib"] = ram // (1024 * 1024)

    def pci(self):
        raw = self.read("pci.bin")
        txt = self.read("pci.txt")
        if raw is None or txt is None:
            return
        devs, off = [], 0
        while off + 8 <= len(raw):
            seg, bus, dev, fn, _, ln = struct.unpack_from("<HBBBBH", raw, off)
            cfg = raw[off + 8:off + 8 + ln]
            if ln not in (256, 4096) or len(cfg) != ln:
                self.err(f"pci.bin: record at {off} has config length {ln}")
                return
            ven, did = struct.unpack_from("<HH", cfg, 0)
            devs.append(f"{seg:04x}:{bus:02x}:{dev:02x}.{fn} {ven:04x}:{did:04x}")
            off += 8 + ln
        if off != len(raw):
            self.err("pci.bin: trailing bytes")
        listed = [" ".join(line.split()[:2]) for line in txt.decode().splitlines() if line.strip()]
        if listed != devs:
            self.err(f"pci.txt lists {len(listed)} functions, pci.bin has {len(devs)} (or they differ)")
        if not devs:
            self.err("pci: no functions found")
        self.facts["pci"] = sorted({d.split()[1] for d in devs})

    def gop(self):
        txt = self.read("gop.txt")
        if txt is None:
            return
        lines = txt.decode().splitlines()
        m = re.match(r"modes (\d+) current (\d+)", lines[0] if lines else "")
        modes = [line for line in lines if re.match(r"mode \d+: \d+x\d+ ", line)]
        if lines and lines[0].startswith("absent"):
            self.facts["gop"] = "absent"
            return
        if not m or int(m[1]) == 0 or len(modes) != int(m[1]) or int(m[2]) >= int(m[1]):
            self.err("GOP: gop.txt mode count, mode lines or current mode inconsistent")
            return
        cur = next((line for line in modes if line.startswith(f"mode {m[2]}:")), "")
        self.facts["gop"] = cur.split()[2] if cur else "?"
        for line in lines:
            em = re.fullmatch(r"edid (\d+) (\d+)", line)
            if em:
                e = self.read(f"edid-{em[1]}.bin")
                if e is not None and (len(e) != int(em[2]) or e[:8] != b"\0\xff\xff\xff\xff\xff\xff\0"):
                    self.err(f"edid-{em[1]}.bin: bad size or EDID header")
                elif e is not None and any(sum(e[i:i + 128]) & 0xFF for i in range(0, len(e), 128)):
                    self.err(f"edid-{em[1]}.bin: a 128-byte block's checksum does not sum to zero")

    def firmware(self):
        txt = self.read("firmware.txt")
        if txt is None:
            return
        kv = dict(line.split("=", 1) for line in txt.decode("utf-8", "replace").splitlines() if "=" in line)
        if not kv.get("vendor"):
            self.err("firmware.txt: no vendor")
        for k in ("revision", "uefi", "secure_boot"):
            if k not in kv:
                self.err(f"firmware.txt: no {k}")
        self.facts["firmware"] = kv

    def manifest(self):
        txt = self.read("manifest.txt")
        if txt is None:
            return
        lines = txt.decode().splitlines()
        if not lines or lines[-1] != "end":
            self.err("manifest.txt: no final 'end' line (the dump did not finish)")
        listed = {}
        for line in lines[:-1]:
            name, _, size = line.rpartition(" ")
            listed[name] = int(size) if size.isdigit() else -1
        actual = {p.relative_to(self.d).as_posix(): p.stat().st_size
                  for p in self.d.rglob("*") if p.is_file() and p.name != "manifest.txt"}
        if listed != actual:
            diff = sorted(set(listed.items()) ^ set(actual.items()))
            self.err(f"manifest.txt does not match the files: {diff[:8]}")

    def run(self):
        self.acpi()
        self.smbios()
        self.memmap()
        self.pci()
        self.gop()
        self.firmware()
        self.manifest()


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a hardware-inventory dump.")
    ap.add_argument("dump", help="INVENTORY/<timestamp> dir, or a dir holding INVENTORY/")
    ap.add_argument("--expect-cpus", type=int)
    ap.add_argument("--expect-mem-mib", type=int)
    ap.add_argument("--expect-smbios", action="append", default=[], metavar="FIELD=VALUE",
                    help="SMBIOS type 1 field (manufacturer, product, version, serial)")
    ap.add_argument("--expect-acpi", default="", help="comma-separated table names that must exist")
    ap.add_argument("--expect-pci", action="append", default=[], metavar="VVVV:DDDD")
    args = ap.parse_args(argv)
    try:
        d = find_dump_dir(args.dump)
    except DumpError as e:
        print(f"FAIL: {e}")
        return 1
    c = Checker(d)
    c.run()
    f = c.facts
    if args.expect_cpus is not None and f.get("cpus") != args.expect_cpus:
        c.err(f"cpus: MADT has {f.get('cpus')} enabled local APICs, expected {args.expect_cpus}")
    if args.expect_mem_mib is not None:
        want = args.expect_mem_mib
        if f.get("smbios_mem_mib") != want:
            c.err(f"mem: SMBIOS type 17 devices total {f.get('smbios_mem_mib')} MiB, expected {want}")
        ram = f.get("memmap_ram_mib")
        if ram is not None and not (want * 0.75 <= ram <= want):
            c.err(f"mem: the memory map has {ram} MiB of RAM, expected 75-100% of {want}")
    for kv in args.expect_smbios:
        k, _, v = kv.partition("=")
        got = f.get("smbios_system", {}).get(k)
        if got != v:
            c.err(f"SMBIOS type 1 {k}: {got!r}, expected {v!r}")
    for t in filter(None, args.expect_acpi.split(",")):
        if t not in getattr(c, "acpi_tables", {}):
            c.err(f"acpi: expected table {t} not dumped")
    for dev in args.expect_pci:
        if dev.lower() not in f.get("pci", []):
            c.err(f"pci: expected device {dev} not found (have {f.get('pci')})")
    print(f"dump: {d}")
    for k, v in f.items():
        print(f"  {k}: {v}")
    for e in c.errors:
        print(f"FAIL: {e}")
    if c.errors:
        return 1
    print("PASS: inventory dump is complete and consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
