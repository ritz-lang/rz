#!/usr/bin/env python3
"""Build and read the hardware-inventory USB-stick image (AGAST #3406).

The image is what `dd` or Etcher writes to a stick: a protective MBR, a GPT
with one EFI System Partition (1 MiB aligned), and that partition formatted
FAT32 holding \\EFI\\BOOT\\BOOTX64.EFI (the removable-media default path, so
any UEFI machine boots it from its boot menu with no NVRAM entry) and a
README.TXT. HWINV.EFI writes its dump to \\INVENTORY\\<timestamp>\\ on the
same partition; `extract` copies everything back out on any host.

Pure Python on purpose: no mtools, dosfstools (/usr/sbin, off a room's
PATH), losetup or root. The writer only takes upper-case 8.3 names, which is
all the image needs; the reader also follows long-name (LFN) entries and the
NT lower-case flags, since the firmware's FAT driver writes both.

Usage:
    esp_image.py build OUT.img --efi HWINV.EFI [--size-mib N]
    esp_image.py extract IMG DESTDIR
"""

import argparse
import struct
import sys
import uuid
import zlib
from pathlib import Path

SECTOR = 512
PART_START = 2048                    # LBA: 1 MiB alignment
GPT_ENTRIES = 128
GPT_ENTRY_SIZE = 128
GPT_ENTRY_SECTORS = GPT_ENTRIES * GPT_ENTRY_SIZE // SECTOR   # 32
ESP_TYPE = uuid.UUID("C12A7328-F81F-11D2-BA4B-00A0C93EC93B")
# Fixed GUIDs and timestamps: the same inputs build the same image bytes.
DISK_GUID = uuid.UUID("52495a54-4857-494e-5600-000000003406")
PART_GUID = uuid.UUID("52495a54-4857-494e-5601-000000003406")
VOLUME_ID = 0x34060001
VOLUME_LABEL = b"HWINV      "
DOS_DATE = ((2026 - 1980) << 9) | (1 << 5) | 1     # 2026-01-01
DOS_TIME = 0
EOC = 0x0FFFFFFF

README = (b"Ritz hardware inventory stick (AGAST #3406)\r\n"
          b"\r\n"
          b"Boot this stick from the firmware boot menu (UEFI, Secure Boot off).\r\n"
          b"It writes ACPI, SMBIOS, the memory map, PCI config space, GOP/EDID\r\n"
          b"and firmware facts to \\INVENTORY\\<timestamp>\\ on this partition,\r\n"
          b"then powers off. Read the files on any machine.\r\n")


# --- writer -------------------------------------------------------------------

def _sectors_per_cluster(part_sectors):
    """Microsoft's FAT32 table: 512 B clusters to 260 MiB, then 4/8/16/32 KiB."""
    mib = part_sectors * SECTOR // (1024 * 1024)
    if mib < 260:
        return 1
    if mib < 8 * 1024:
        return 8
    if mib < 16 * 1024:
        return 16
    if mib < 32 * 1024:
        return 32
    return 64


def _short_name(name):
    base, _, ext = name.partition(".")
    if (not base or len(base) > 8 or len(ext) > 3 or "." in ext
            or name != name.upper()
            or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-~" for c in base + ext)):
        raise ValueError(f"not an upper-case 8.3 name: {name!r}")
    return base.ljust(8).encode() + ext.ljust(3).encode()


def _dirent(name11, attr, cluster, size):
    return struct.pack("<11sBBBHHHHHHHI", name11, attr, 0, 0, DOS_TIME, DOS_DATE, DOS_DATE,
                       cluster >> 16, DOS_TIME, DOS_DATE, cluster & 0xFFFF, size)


class _Fat32:
    def __init__(self, part_sectors):
        self.spc = _sectors_per_cluster(part_sectors)
        self.rsvd = 32
        self.total = part_sectors
        fatsz = 1
        while True:
            clusters = (self.total - self.rsvd - 2 * fatsz) // self.spc
            need = -(-((clusters + 2) * 4) // SECTOR)
            if need <= fatsz:
                break
            fatsz = need
        self.fatsz = fatsz
        self.clusters = clusters
        if clusters < 65525:
            raise ValueError("partition too small for FAT32: make the image at least 34 MiB")
        self.csize = self.spc * SECTOR
        self.fat = [0x0FFFFFF8, 0x0FFFFFFF] + [0] * clusters
        self.data = {}                # cluster -> bytes
        self.next = 2

    def alloc(self, nbytes):
        n = max(1, -(-nbytes // self.csize))
        first = self.next
        if first + n - 2 > self.clusters:
            raise ValueError("image full")
        for c in range(first, first + n):
            self.fat[c] = c + 1
        self.fat[first + n - 1] = EOC
        self.next += n
        return first, n

    def put(self, first, payload):
        for i in range(0, max(len(payload), 1), self.csize):
            self.data[first + i // self.csize] = payload[i:i + self.csize]

    def render(self):
        data_start = self.rsvd + 2 * self.fatsz
        out = bytearray(self.total * SECTOR)
        bpb = bytearray(SECTOR)
        bpb[0:3] = b"\xEB\x58\x90"
        bpb[3:11] = b"RITZINV "
        struct.pack_into("<HBHBHHBHHHII", bpb, 11, SECTOR, self.spc, self.rsvd, 2, 0, 0,
                         0xF8, 0, 63, 255, PART_START, self.total)
        struct.pack_into("<IHHIHH", bpb, 36, self.fatsz, 0, 0, 2, 1, 6)
        struct.pack_into("<BBBI11s8s", bpb, 64, 0x80, 0, 0x29, VOLUME_ID, VOLUME_LABEL, b"FAT32   ")
        bpb[510:512] = b"\x55\xAA"
        free = self.clusters - (self.next - 2)
        fsinfo = bytearray(SECTOR)
        struct.pack_into("<I", fsinfo, 0, 0x41615252)
        struct.pack_into("<III", fsinfo, 484, 0x61417272, free, self.next)
        struct.pack_into("<I", fsinfo, 508, 0xAA550000)
        for base in (0, 6):           # boot sector + FSInfo, and their backups
            out[base * SECTOR:(base + 1) * SECTOR] = bpb
            out[(base + 1) * SECTOR:(base + 2) * SECTOR] = fsinfo
            out[(base + 2) * SECTOR + 510:(base + 2) * SECTOR + 512] = b"\x55\xAA"
        fat = struct.pack(f"<{len(self.fat)}I", *self.fat)
        for i in range(2):
            at = (self.rsvd + i * self.fatsz) * SECTOR
            out[at:at + len(fat)] = fat
        for c, payload in self.data.items():
            at = (data_start + (c - 2) * self.spc) * SECTOR
            out[at:at + len(payload)] = payload
        return bytes(out)


def _tree(files):
    """{"A/B/C.EFI": data} -> nested dicts (dict = directory, bytes = file)."""
    root = {}
    for path, data in files.items():
        parts = path.strip("/").split("/")
        node = root
        for p in parts[:-1]:
            _short_name(p)
            node = node.setdefault(p, {})
            if not isinstance(node, dict):
                raise ValueError(f"{path}: a file is in the way")
        _short_name(parts[-1])
        node[parts[-1]] = bytes(data)
    return root


def _write_dir(fs, node, cluster, parent):
    """Lay out node's children and write node's directory at `cluster`."""
    entries = []
    if parent is None:
        entries.append(struct.pack("<11sB20s", VOLUME_LABEL, 0x08, bytes(20)))
    else:
        entries.append(_dirent(b".          ", 0x10, cluster, 0))
        entries.append(_dirent(b"..         ", 0x10, 0 if parent == 2 else parent, 0))
    for name in sorted(node):
        child = node[name]
        if isinstance(child, dict):
            nbytes = (len(child) + 2) * 32
            first, _ = fs.alloc(nbytes)
            entries.append(_dirent(_short_name(name), 0x10, first, 0))
            _write_dir(fs, child, first, cluster)
        else:
            first = fs.alloc(len(child))[0] if child else 0
            if child:
                fs.put(first, child)
            entries.append(_dirent(_short_name(name), 0x20, first, len(child)))
    fs.put(cluster, b"".join(entries))


def _fat_partition(part_sectors, files):
    fs = _Fat32(part_sectors)
    tree = _tree(files)
    fs.alloc((len(tree) + 1) * 32)        # the root directory: cluster 2
    _write_dir(fs, tree, 2, None)
    return fs.render()


def _gpt_header(my_lba, alt_lba, entries_lba, last_usable, entries_crc):
    hdr = bytearray(92)
    struct.pack_into("<8sIII", hdr, 0, b"EFI PART", 0x00010000, 92, 0)
    struct.pack_into("<QQQQ", hdr, 24, my_lba, alt_lba, 34, last_usable)
    hdr[56:72] = DISK_GUID.bytes_le
    struct.pack_into("<QIII", hdr, 72, entries_lba, GPT_ENTRIES, GPT_ENTRY_SIZE, entries_crc)
    struct.pack_into("<I", hdr, 16, zlib.crc32(bytes(hdr)))
    return bytes(hdr).ljust(SECTOR, b"\0")


def build_image(out, files, size_mib=64):
    """Write a GPT + FAT32 ESP image of size_mib MiB holding `files`
    ({"EFI/BOOT/BOOTX64.EFI": bytes, ...}; upper-case 8.3 names only)."""
    total = size_mib * 1024 * 1024 // SECTOR
    last_lba = total - 1
    last_usable = last_lba - 1 - GPT_ENTRY_SECTORS
    part_end = (last_usable + 1) // PART_START * PART_START - 1   # MiB aligned end
    part_sectors = part_end - PART_START + 1
    part = _fat_partition(part_sectors, files)

    entry = bytearray(GPT_ENTRY_SIZE)
    entry[0:16] = ESP_TYPE.bytes_le
    entry[16:32] = PART_GUID.bytes_le
    struct.pack_into("<QQQ", entry, 32, PART_START, part_end, 0)
    entry[56:56 + 2 * len("EFI System")] = "EFI System".encode("utf-16-le")
    table = bytes(entry).ljust(GPT_ENTRIES * GPT_ENTRY_SIZE, b"\0")
    crc = zlib.crc32(table)

    mbr = bytearray(SECTOR)
    struct.pack_into("<B3sB3sII", mbr, 446, 0, b"\x00\x02\x00", 0xEE, b"\xFF\xFF\xFF",
                     1, min(total - 1, 0xFFFFFFFF))
    mbr[510:512] = b"\x55\xAA"

    img = bytearray(total * SECTOR)
    img[0:SECTOR] = mbr
    img[SECTOR:2 * SECTOR] = _gpt_header(1, last_lba, 2, last_usable, crc)
    img[2 * SECTOR:2 * SECTOR + len(table)] = table
    back_entries = last_lba - GPT_ENTRY_SECTORS
    img[back_entries * SECTOR:back_entries * SECTOR + len(table)] = table
    img[last_lba * SECTOR:] = _gpt_header(last_lba, 1, back_entries, last_usable, crc)
    img[PART_START * SECTOR:PART_START * SECTOR + len(part)] = part
    Path(out).write_bytes(bytes(img))


# --- reader -------------------------------------------------------------------

def _esp_extent(data):
    if data[SECTOR:SECTOR + 8] != b"EFI PART":
        raise ValueError("no GPT header at LBA 1")
    entries_lba, count, size = struct.unpack_from("<QII", data, SECTOR + 72)
    for i in range(count):
        e = data[entries_lba * SECTOR + i * size:entries_lba * SECTOR + (i + 1) * size]
        if e[0:16] == ESP_TYPE.bytes_le:
            first, last = struct.unpack_from("<QQ", e, 32)
            return first, last
    raise ValueError("no EFI System Partition in the GPT")


def partition_bytes(img):
    """The ESP's bytes (the FAT32 file system) from a GPT image."""
    data = Path(img).read_bytes()
    first, last = _esp_extent(data)
    return data[first * SECTOR:(last + 1) * SECTOR]


class _FatReader:
    def __init__(self, part):
        self.p = part
        bps, self.spc, rsvd, nfats = struct.unpack_from("<HBHB", part, 11)
        if bps != SECTOR or part[82:87] != b"FAT32":
            raise ValueError("ESP is not FAT32 with 512-byte sectors")
        fatsz = struct.unpack_from("<I", part, 36)[0]
        self.root = struct.unpack_from("<I", part, 44)[0]
        self.fat_at = rsvd * SECTOR
        self.data_at = (rsvd + nfats * fatsz) * SECTOR
        self.csize = self.spc * SECTOR

    def chain(self, c):
        seen = set()
        while 2 <= c < 0x0FFFFFF8 and c not in seen:
            seen.add(c)
            yield c
            c = struct.unpack_from("<I", self.p, self.fat_at + 4 * c)[0] & 0x0FFFFFFF

    def read(self, c, size=None):
        buf = b"".join(self.p[self.data_at + (x - 2) * self.csize:
                              self.data_at + (x - 1) * self.csize] for x in self.chain(c))
        return buf if size is None else buf[:size]

    def entries(self, c):
        raw = self.read(c)
        lfn = {}
        for off in range(0, len(raw), 32):
            e = raw[off:off + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5:
                lfn = {}
                continue
            attr = e[11]
            if attr == 0x0F:
                seq = e[0] & 0x1F
                chars = e[1:11] + e[14:26] + e[28:32]
                lfn[seq] = chars.decode("utf-16-le")
                continue
            if attr & 0x08:
                lfn = {}
                continue
            if lfn:
                name = "".join(lfn[k] for k in sorted(lfn)).split("\0")[0]
            else:
                base = e[0:8].decode("latin-1").rstrip()
                ext = e[8:11].decode("latin-1").rstrip()
                if e[12] & 0x08:
                    base = base.lower()
                if e[12] & 0x10:
                    ext = ext.lower()
                name = base + ("." + ext if ext else "")
            lfn = {}
            if name in (".", ".."):
                continue
            first = (struct.unpack_from("<H", e, 20)[0] << 16) | struct.unpack_from("<H", e, 26)[0]
            yield name, bool(attr & 0x10), first, struct.unpack_from("<I", e, 28)[0]

    def walk(self, c=None, prefix=""):
        for name, is_dir, first, size in self.entries(self.root if c is None else c):
            path = prefix + name
            if is_dir:
                yield from self.walk(first, path + "/")
            else:
                yield path, (self.read(first, size) if first else b"")


def read_files(img):
    """Every file on the image's ESP: {"DIR/NAME": bytes}."""
    return dict(_FatReader(partition_bytes(img)).walk())


# --- CLI ----------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="build a raw .img for dd/Etcher")
    b.add_argument("out")
    b.add_argument("--efi", required=True, help="the UEFI app, installed as \\EFI\\BOOT\\BOOTX64.EFI")
    b.add_argument("--size-mib", type=int, default=64)
    x = sub.add_parser("extract", help="copy every file off an image's ESP")
    x.add_argument("img")
    x.add_argument("dest")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        build_image(args.out, {"EFI/BOOT/BOOTX64.EFI": Path(args.efi).read_bytes(),
                               "README.TXT": README}, size_mib=args.size_mib)
        print(f"{args.out}: {args.size_mib} MiB, GPT + FAT32 ESP with \\EFI\\BOOT\\BOOTX64.EFI")
        return 0
    dest = Path(args.dest)
    n = 0
    for path, data in read_files(args.img).items():
        out = dest / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        n += 1
    print(f"{args.img}: extracted {n} file(s) to {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
