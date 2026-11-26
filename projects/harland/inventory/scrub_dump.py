#!/usr/bin/env python3
"""Scrub a hardware-inventory dump for committing (AGAST #4300).

A dump from HWINV.EFI holds the machine's identifiers: SMBIOS serial numbers,
asset tags and the system UUID, PCIe Device Serial Numbers (which carry a MAC
address on some NICs), the monitor's EDID serial number, and the Windows
product key in an ACPI MSDM table. This copies a dump with those removed and
everything else byte-identical:

    SMBIOS   serial-number and asset-tag strings (types 1, 2, 3, 4, 17, 22,
             39) become 'X's of the same length, unless they are a vendor
             placeholder ("To Be Filled By O.E.M.", "00000000", ...); the
             type 1 UUID and the battery's SBDS serial word are zeroed; a
             Lenovo type 133 opaque ID is zeroed, with the string that holds
             it
    PCI      every Device Serial Number capability's 8 bytes are zeroed
    EDID     the serial number field and any serial-string descriptor (0xFF)
             are zeroed and the checksum fixed
    ACPI     MSDM's product key becomes 'X's and the checksum is fixed

Every edit keeps the file's size, so manifest.txt stays right, and
check_dump.py must still pass on the result.

Then it checks its own work: it searches every output file for every value
it removed (as text, UTF-16 and bytes, in both byte orders) and for each
--forbid word (a hostname, a username; any case). A hit means an identifier
sits somewhere no rule covers: the scrub fails, names the file, and writes
nothing. The report names each field it scrubbed, never the value.

Usage: scrub_dump.py RAW_DUMP OUT_DIR [--forbid WORD]...
Exit: 0 = OUT_DIR written; 1 = refused (nothing written); 2 = bad usage.
"""

import argparse
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_dump

# (SMBIOS type, offset of a string field): serial numbers and asset tags.
ID_STRINGS = {
    1: {0x07: "serial"},
    2: {0x07: "serial", 0x08: "asset tag"},
    3: {0x07: "serial", 0x08: "asset tag"},
    4: {0x20: "serial", 0x21: "asset tag"},
    17: {0x18: "serial", 0x19: "asset tag"},
    22: {0x07: "serial"},
    39: {0x08: "serial", 0x09: "asset tag"},
}
PLACEHOLDERS = {
    "to be filled by o.e.m.", "default string", "not specified", "not available", "not defined",
    "none", "unknown", "n/a", "na", "undefined", "empty", "no asset tag", "unknown asset tag",
    "0123456789", "123456789", "1234567890", "9876543210",
}
PLACEHOLDER_RES = [
    re.compile(r"(.)\1*"),                                  # 00000000, FFFF, all blanks
    re.compile(r".*\b(serial ?(number|num|no\.?)|asset ?tag)\b.*", re.IGNORECASE),   # "Chassis Serial Number"
    re.compile(r".*_AssetTag", re.IGNORECASE),                       # DIMM_A1_AssetTag
]
MIN_SEARCH = 4          # shorter removed values are too likely to occur by chance
EDID_HEADER = b"\0\xff\xff\xff\xff\xff\xff\0"


def is_placeholder(text):
    t = text.strip()
    return not t or t.lower() in PLACEHOLDERS or any(r.fullmatch(t) for r in PLACEHOLDER_RES)


def acpi_fix_checksum(t):
    t[9] = 0
    t[9] = (-sum(t)) & 0xFF


class Scrubber:
    def __init__(self, files):
        self.files = {k: bytearray(v) for k, v in files.items()}
        self.removed = []       # (file, what, value bytes) for the search
        self.report = []        # what was scrubbed, without values

    def note(self, rel, what, value):
        self.report.append(f"{rel}: {what}")
        self.removed.append((rel, what, bytes(value)))

    # --- SMBIOS -------------------------------------------------------------

    def smbios(self):
        rel = "smbios/DMI"
        dmi = self.files.get(rel)
        if dmi is None:
            return
        for st in list(check_dump.smbios_structures(bytes(dmi))):
            where = f"type {st.typ} handle {st.handle:#06x}"
            for at, what in ID_STRINGS.get(st.typ, {}).items():
                idx = st.string_index(at)
                if not idx or is_placeholder(st.s(at)):
                    continue
                o, raw = st.string_offs[idx - 1], st.strings[idx - 1]
                dmi[o:o + len(raw)] = b"X" * len(raw)
                self.note(rel, f"SMBIOS {where} {what}", raw)
            if st.typ == 1 and st.ln >= 0x18:
                uuid = dmi[st.off + 8:st.off + 24]
                if uuid not in (bytes(16), b"\xff" * 16):
                    self.note(rel, f"SMBIOS {where} uuid", uuid)
                    # SMBIOS stores the first three fields little-endian;
                    # search for the RFC 4122 byte order and the text form too.
                    rfc = uuid[3::-1] + uuid[5:3:-1] + uuid[7:5:-1] + uuid[8:]
                    h = rfc.hex()
                    text = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
                    for v in (rfc, text.encode(), text.upper().encode()):
                        self.removed.append((rel, f"SMBIOS {where} uuid", v))
                    dmi[st.off + 8:st.off + 24] = bytes(16)
            if st.typ == 22 and st.ln >= 0x12 and st.word(0x10):
                struct.pack_into("<H", dmi, st.off + 0x10, 0)
                self.report.append(f"{rel}: SMBIOS {where} SBDS serial number")
            if st.typ == 133 and st.ln >= 0x14:
                # Lenovo: a 16-byte per-machine opaque ID, repeated inside the
                # first string. The ThinkPad's Linux-side scrub zeroed it too.
                oid = bytes(dmi[st.off + 4:st.off + 20])
                if oid != bytes(16):
                    dmi[st.off + 4:st.off + 20] = bytes(16)
                    self.note(rel, f"SMBIOS {where} OEM opaque ID", oid)
                    for o, raw in zip(st.string_offs, st.strings):
                        if oid in raw:
                            dmi[o:o + len(raw)] = b"X" * len(raw)
                            self.report.append(f"{rel}: SMBIOS {where} string holding that ID")

    # --- PCI ----------------------------------------------------------------

    def pci(self):
        rel = "pci.bin"
        raw = self.files.get(rel)
        if raw is None:
            return
        off = 0
        while off + 8 <= len(raw):
            seg, bus, dev, fn, _, ln = struct.unpack_from("<HBBBBH", raw, off)
            base = off + 8
            if ln == 4096:
                cap, seen = 0x100, set()
                while 0x100 <= cap <= 4096 - 12 and cap not in seen:
                    seen.add(cap)
                    hdr = struct.unpack_from("<I", raw, base + cap)[0]
                    if hdr in (0, 0xFFFFFFFF):
                        break
                    if hdr & 0xFFFF == 0x0003:
                        at = base + cap + 4
                        dsn = bytes(raw[at:at + 8])
                        if dsn != bytes(8):
                            raw[at:at + 8] = bytes(8)
                            self.note(rel, f"PCI {seg:04x}:{bus:02x}:{dev:02x}.{fn} "
                                      "Device Serial Number (DSN)", dsn)
                    cap = hdr >> 20
            off = base + ln

    # --- EDID ---------------------------------------------------------------

    def edid(self):
        for rel in sorted(k for k in self.files if re.fullmatch(r"edid-\d+\.bin", k)):
            e = self.files[rel]
            if len(e) < 128 or e[:8] != EDID_HEADER:
                continue
            if e[12:16] != bytes(4):
                self.note(rel, "EDID serial number", e[12:16])
                e[12:16] = bytes(4)
            for i in range(4):
                blk = 54 + 18 * i
                if e[blk:blk + 3] == b"\0\0\0" and e[blk + 3] == 0xFF:
                    text = bytes(e[blk + 5:blk + 18]).split(b"\n")[0].rstrip(b" ")
                    if text:
                        self.note(rel, "EDID serial-string descriptor", text)
                    e[blk + 5:blk + 18] = b"\n" + b" " * 12
            e[127] = (-sum(e[:127])) & 0xFF

    # --- ACPI ---------------------------------------------------------------

    def msdm(self):
        rel = "acpi/MSDM"
        t = self.files.get(rel)
        if t is None or len(t) < 56:
            return
        n = struct.unpack_from("<I", t, 52)[0]
        key = bytes(t[56:56 + n])
        if key.strip(b"\0 "):
            t[56:56 + n] = b"X" * len(key)
            acpi_fix_checksum(t)
            self.note(rel, "MSDM Windows product key", key)

    def run(self):
        self.smbios()
        self.pci()
        self.edid()
        self.msdm()

    # --- the check -------------------------------------------------------------

    def leaks(self, forbid=()):
        """(file, what) for every removed value or forbidden word still present."""
        needles = []
        for _, what, v in self.removed:
            if len(v) < MIN_SEARCH:
                continue
            needles += [(what, v), (what, v[::-1])]
            text = v.strip(b" ")
            if len(text) >= MIN_SEARCH and all(32 <= c < 127 for c in text):
                needles += [(what, text.decode().encode("utf-16-le"))]
        hits = []
        for rel, data in sorted(self.files.items()):
            low = bytes(data).lower()
            for what, v in needles:
                if v in data:
                    hits.append((rel, what))
            for word in forbid:
                for form in (word.lower().encode(), word.lower().encode("utf-16-le")):
                    if form in low:
                        hits.append((rel, f"forbidden word {word!r}"))
        return sorted(set(hits))


def read_dump(d):
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scrub a hardware-inventory dump for committing.")
    ap.add_argument("raw", help="INVENTORY/<timestamp> dir as the stick wrote it")
    ap.add_argument("out", help="where to write the scrubbed copy (must not exist)")
    ap.add_argument("--forbid", action="append", default=[], metavar="WORD",
                    help="a word that must not appear anywhere (hostname, username); any case")
    args = ap.parse_args(argv)
    raw, out = Path(args.raw), Path(args.out)
    if out.exists():
        print(f"FAIL: {out} exists; scrub into a new directory")
        return 2
    try:
        raw = check_dump.find_dump_dir(raw)
        s = Scrubber(read_dump(raw))
        s.run()
    except check_dump.DumpError as e:
        print(f"FAIL: {e}")
        return 1
    hits = s.leaks(args.forbid)
    if hits:
        for rel, what in hits:
            print(f"FAIL: {rel} still holds {what}: no rule covers it, so nothing was written")
        return 1
    out.mkdir(parents=True)
    for rel, data in s.files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_bytes(bytes(data))
    c = check_dump.Checker(out)
    c.run()
    print(f"scrubbed {raw.name} into {out}")
    for line in s.report:
        print(f"  {line}")
    if c.errors:
        for e in c.errors:
            print(f"FAIL: the scrubbed dump: {e}")
        return 1
    print(f"{len(s.report)} field(s) scrubbed; the rest is byte-identical; check_dump passes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
