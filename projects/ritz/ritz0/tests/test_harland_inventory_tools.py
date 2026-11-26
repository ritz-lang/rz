"""The hardware-inventory boot image's host tools (AGAST #3406).

projects/harland/inventory holds a UEFI app (HWINV.EFI) that dumps ACPI,
SMBIOS, the memory map, PCI config space, GOP/EDID and firmware facts to
\\INVENTORY\\<timestamp>\\ on the FAT32 ESP it booted from, and host tools:

  esp_image.py   builds the raw USB-stick image (protective MBR + GPT + one
                 FAT32 ESP holding \\EFI\\BOOT\\BOOTX64.EFI) and reads files
                 back out of one, with no mtools, dosfstools or root;
  check_dump.py  validates a dump: every ACPI table's signature, length and
                 checksum, the XSDT's table count, the SMBIOS entry point and
                 structure table, the memory map, PCI, GOP and the manifest,
                 and any facts the test pinned on QEMU's command line;
  scrub_dump.py  copies a real machine's dump without its serials, UUID,
                 PCIe DSNs, EDID serial and product key, and proves none is
                 left (#4300);
  dump_summary.py  CPU, RAM, PCI names and display, read from a dump.

These run the tools on synthetic inputs, so they need no QEMU, OVMF or
build. inventory/test.sh boots the real image (the CI boot step).
"""

import importlib.util
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

INVENTORY = Path(__file__).resolve().parents[3] / "harland" / "inventory"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, INVENTORY / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


esp_image = _load("esp_image")
check_dump = _load("check_dump")

ESP_TYPE_GUID = bytes.fromhex("28732ac11ff8d211ba4b00a0c93ec93b")  # C12A7328-F81F-11D2-BA4B-00A0C93EC93B


def _sbin_tool(name):
    for d in (None, "/usr/sbin", "/sbin"):
        p = shutil.which(name) if d is None else (Path(d) / name)
        if p and Path(p).exists():
            return str(p)
    return None


# --- esp_image: the GPT ------------------------------------------------------

@pytest.fixture
def stick(tmp_path):
    img = tmp_path / "hwinv.img"
    esp_image.build_image(img, {
        "EFI/BOOT/BOOTX64.EFI": b"MZ" + bytes(range(256)) * 40,
        "README.TXT": b"hello\r\n",
    }, size_mib=64)
    return img


def test_image_is_the_requested_size(stick):
    assert stick.stat().st_size == 64 * 1024 * 1024


def test_protective_mbr(stick):
    data = stick.read_bytes()
    assert data[510:512] == b"\x55\xaa"
    entry = data[446:462]
    assert entry[4] == 0xEE                       # GPT protective
    assert struct.unpack_from("<I", entry, 8)[0] == 1


def _gpt_header(data, lba):
    hdr = bytearray(data[lba * 512:lba * 512 + 92])
    assert hdr[:8] == b"EFI PART"
    crc = struct.unpack_from("<I", hdr, 16)[0]
    struct.pack_into("<I", hdr, 16, 0)
    assert zlib.crc32(bytes(hdr)) == crc, "header CRC32"
    return hdr


def test_primary_and_backup_gpt_headers_are_valid(stick):
    data = stick.read_bytes()
    last_lba = len(data) // 512 - 1
    primary = _gpt_header(data, 1)
    backup = _gpt_header(data, last_lba)
    assert struct.unpack_from("<Q", primary, 24)[0] == 1
    assert struct.unpack_from("<Q", primary, 32)[0] == last_lba
    assert struct.unpack_from("<Q", backup, 24)[0] == last_lba
    assert struct.unpack_from("<Q", backup, 32)[0] == 1
    for hdr in (primary, backup):
        entries_lba, count, size = struct.unpack_from("<QII", hdr, 72)
        table = data[entries_lba * 512:entries_lba * 512 + count * size]
        assert zlib.crc32(table) == struct.unpack_from("<I", hdr, 88)[0], "entries CRC32"


def test_one_esp_partition_aligned_to_1mib(stick):
    data = stick.read_bytes()
    entry = data[1024:1024 + 128]
    assert entry[:16] == ESP_TYPE_GUID
    first, last = struct.unpack_from("<QQ", entry, 32)
    assert first == 2048
    assert last < len(data) // 512 - 33
    assert data[1024 + 128:1024 + 256] == bytes(128), "only one partition"


@pytest.mark.integration
def test_sfdisk_reads_the_partition_table(stick):
    sfdisk = _sbin_tool("sfdisk")
    if not sfdisk:
        pytest.skip("sfdisk not installed")
    out = subprocess.run([sfdisk, "--dump", str(stick)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "label: gpt" in out.stdout
    assert "C12A7328-F81F-11D2-BA4B-00A0C93EC93B" in out.stdout.upper()


# --- esp_image: the FAT32 ESP ------------------------------------------------

def test_files_round_trip(stick):
    files = esp_image.read_files(stick)
    assert files["EFI/BOOT/BOOTX64.EFI"] == b"MZ" + bytes(range(256)) * 40
    assert files["README.TXT"] == b"hello\r\n"


def test_partition_is_fat32_with_enough_clusters(stick):
    part = esp_image.partition_bytes(stick)
    assert part[82:90] == b"FAT32   "
    bps, spc, rsvd, nfats = struct.unpack_from("<HBHB", part, 11)
    total = struct.unpack_from("<I", part, 32)[0]
    fatsz = struct.unpack_from("<I", part, 36)[0]
    clusters = (total - rsvd - nfats * fatsz) // spc
    assert clusters >= 65525, "fewer clusters than FAT32 needs: firmware would read it as FAT16"


@pytest.mark.integration
def test_fsck_fat_accepts_the_esp(stick, tmp_path):
    fsck = _sbin_tool("fsck.fat")
    if not fsck:
        pytest.skip("fsck.fat not installed")
    part = tmp_path / "esp.part"
    part.write_bytes(esp_image.partition_bytes(stick))
    out = subprocess.run([fsck, "-n", str(part)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.integration
def test_reader_follows_long_names_and_lowercase_83_names(stick, tmp_path):
    """FatDxe writes LFN entries for long names (the timestamp directory)
    and plain 8.3 entries with the NT lowercase flags for short lowercase
    names ("acpi"); the reader must return both as written."""
    mcopy, mmd = shutil.which("mcopy"), shutil.which("mmd")
    if not (mcopy and mmd):
        pytest.skip("mtools not installed")
    off = f"@@{2048 * 512}"
    src = tmp_path / "x.bin"
    src.write_bytes(b"\x00\x01" * 3000)
    env = {"MTOOLS_SKIP_CHECK": "1", "MTOOLS_NO_VFAT": "0", "PATH": "/usr/bin:/bin"}
    for cmd in ([mmd, "-i", f"{stick}{off}", "::/INVENTORY"],
                [mmd, "-i", f"{stick}{off}", "::/INVENTORY/20261119-060203"],
                [mmd, "-i", f"{stick}{off}", "::/INVENTORY/20261119-060203/acpi"],
                [mcopy, "-i", f"{stick}{off}", str(src),
                 "::/INVENTORY/20261119-060203/acpi/smbios_entry_point"]):
        r = subprocess.run(cmd, capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stderr
    files = esp_image.read_files(stick)
    assert files["INVENTORY/20261119-060203/acpi/smbios_entry_point"] == src.read_bytes()


def test_writer_stores_long_names_as_lfn_entries(tmp_path):
    """AGAST #4359: the EC2 disk needs mixed-case names and `initramfs.tar`,
    none of which is upper-case 8.3. The writer emits LFN entries over
    generated aliases (the smbios path needs more than one), and the reader
    returns every name exactly as written."""
    img = tmp_path / "long.img"
    files = {
        "EFI/BOOT/BOOTX64.EFI": b"MZ",
        "harland/kernel.elf": b"\x7fELF" + b"k" * 5000,
        "harland/initramfs.tar": b"t" * 5000,
        "INVENTORY/20261119-060203/acpi/smbios_entry_point": b"long",
    }
    esp_image.build_image(img, files, size_mib=48)
    assert esp_image.read_files(img) == files


def test_a_directory_spanning_clusters_keeps_every_long_name(tmp_path):
    """512-byte clusters hold 16 entries; 20 names of three LFN entries each
    overrun the first cluster, so the writer must budget LFN entries, not
    just one entry per name, or the tail lands on another file's cluster."""
    img = tmp_path / "many.img"
    files = {f"logs/session-{i:03d}-diagnostics.txt": bytes([i]) for i in range(20)}
    esp_image.build_image(img, files, size_mib=48)
    assert esp_image.read_files(img) == files


def test_lfn_aliases_do_not_collide(tmp_path):
    img = tmp_path / "collide.img"
    files = {"initramfs-one.tar": b"one", "initramfs-two.tar": b"two",
             "KERNEL.ELF": b"upper", "boot/initrd.img": b"lower"}
    esp_image.build_image(img, files, size_mib=48)
    assert esp_image.read_files(img) == files


@pytest.mark.parametrize("bad", ["EFI/BOOT/bad*name.efi", "name.", "name ", "a/b:c", ""])
def test_build_rejects_invalid_names(tmp_path, bad):
    with pytest.raises(ValueError):
        esp_image.build_image(tmp_path / "x.img", {bad: b""})


def test_bigger_sticks_get_bigger_clusters(tmp_path):
    img = tmp_path / "big.img"
    esp_image.build_image(img, {"EFI/BOOT/BOOTX64.EFI": b"MZ"}, size_mib=270)
    part = esp_image.partition_bytes(img)
    assert part[13] == 8                           # 4 KiB clusters above 260 MiB
    assert esp_image.read_files(img)["EFI/BOOT/BOOTX64.EFI"] == b"MZ"


@pytest.mark.integration
def test_cli_build_and_extract(tmp_path):
    efi = tmp_path / "HWINV.EFI"
    efi.write_bytes(b"MZ-test-efi")
    img = tmp_path / "stick.img"
    tool = INVENTORY / "esp_image.py"
    r = subprocess.run([sys.executable, str(tool), "build", str(img), "--efi", str(efi),
                        "--size-mib", "48"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(tool), "extract", str(img), str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (out / "EFI" / "BOOT" / "BOOTX64.EFI").read_bytes() == b"MZ-test-efi"
    assert (out / "README.TXT").exists()


# --- check_dump: a synthetic dump that matches QEMU's shape ------------------

def _checksum_fix(buf, at):
    buf[at] = (-sum(buf) + buf[at]) & 0xFF
    return bytes(buf)


def _acpi_table(sig, body=b"", rev=1):
    hdr = bytearray(36)
    hdr[0:4] = sig.encode()
    struct.pack_into("<IB", hdr, 4, 36 + len(body), rev)
    hdr[10:16] = b"BOCHS "
    t = bytearray(hdr + body)
    return _checksum_fix(t, 9)


def _madt(cpus):
    body = bytearray(struct.pack("<II", 0xFEE00000, 1))
    for i in range(cpus):
        body += struct.pack("<BBBBI", 0, 8, i, i, 1)
    return _acpi_table("APIC", bytes(body))


def _rsdp():
    r = bytearray(36)
    r[0:8] = b"RSD PTR "
    r[9:15] = b"BOCHS "
    r[15] = 2
    struct.pack_into("<IQ", r, 20, 36, 0x7FFE0000)
    r[8] = 0
    r[8] = (-sum(r[:20])) & 0xFF
    r[32] = (-sum(r)) & 0xFF
    return bytes(r)


def _smbios_struct(typ, handle, formatted, strings):
    s = bytes([typ, 4 + len(formatted)]) + struct.pack("<H", handle) + formatted
    tail = b"".join(x.encode() + b"\0" for x in strings) + b"\0"
    if not strings:
        tail = b"\0\0"
    return s + tail


def _smbios(manufacturer, product, serial, mem_mib):
    t1 = _smbios_struct(1, 0x100, bytes([1, 2, 3, 4]) + bytes(16) + bytes([6, 0, 0]),
                        [manufacturer, product, "1.0", serial])
    t17 = _smbios_struct(17, 0x1100, struct.pack("<HHHHHH", 0x1000, 0xFFFE, 64, 64, mem_mib, 9)
                         + bytes(13), [])
    end = _smbios_struct(127, 0x7F00, b"", [])
    table = t1 + t17 + end
    ep = bytearray(24)
    ep[0:5] = b"_SM3_"
    ep[6] = 24
    ep[7], ep[8], ep[10] = 3, 0, 1
    struct.pack_into("<IQ", ep, 12, len(table), 0x7F000000)
    return _checksum_fix(ep, 5), table


def _write_dump(root, cpus=2, mem_mib=512, manufacturer="RitzInventoryTest",
                product="QEMU-HWINV", serial="HWINV-3406"):
    d = root / "INVENTORY" / "20261119-060203"
    (d / "acpi").mkdir(parents=True)
    (d / "smbios").mkdir()
    facp = _acpi_table("FACP", bytes(244 - 36), rev=6)
    tables = {"FACP": facp, "APIC": _madt(cpus), "HPET": _acpi_table("HPET", bytes(20)),
              "MCFG": _acpi_table("MCFG", bytes(8 + 16)), "WAET": _acpi_table("WAET", bytes(4))}
    xsdt = _acpi_table("XSDT", b"".join(struct.pack("<Q", 0x7FFE1000 + i) for i in range(len(tables))))
    (d / "acpi" / "RSDP").write_bytes(_rsdp())
    (d / "acpi" / "XSDT").write_bytes(xsdt)
    for name, t in tables.items():
        (d / "acpi" / name).write_bytes(t)
    (d / "acpi" / "DSDT").write_bytes(_acpi_table("DSDT", b"\x10" * 100, rev=2))
    facs = bytearray(64)
    facs[0:4] = b"FACS"
    struct.pack_into("<I", facs, 4, 64)
    (d / "acpi" / "FACS").write_bytes(bytes(facs))
    ep, table = _smbios(manufacturer, product, serial, mem_mib)
    (d / "smbios" / "smbios_entry_point").write_bytes(ep)
    (d / "smbios" / "DMI").write_bytes(table)
    # Memory map: desc_size 48, all of RAM conventional bar 1 MiB reserved.
    descs = struct.pack("<IIQQQQ8x", 7, 0, 0x100000, 0, (mem_mib - 1) * 256, 0xF)
    descs += struct.pack("<IIQQQQ8x", 0, 0, 0, 0, 256, 0)
    (d / "memmap.bin").write_bytes(descs)
    (d / "memmap.txt").write_text(
        "desc_size=48 desc_version=1 count=2\n"
        f"7 0x100000 {(mem_mib - 1) * 256} 0xf\n0 0x0 256 0x0\n")
    pci = [(0, 0, 0, 0x8086, 0x29C0, 0x060000), (0, 1, 0, 0x1234, 0x1111, 0x030000),
           (0, 2, 0, 0x1AF4, 0x1005, 0x00FF00)]
    pci_bin = b""
    lines = []
    for bus, dev, fn, ven, did, cls in pci:
        cfg = bytearray(256)
        struct.pack_into("<HH", cfg, 0, ven, did)
        cfg[9], cfg[10], cfg[11] = cls & 0xFF, (cls >> 8) & 0xFF, cls >> 16
        pci_bin += struct.pack("<HBBBBH", 0, bus, dev, fn, 0, 256) + bytes(cfg)
        lines.append(f"0000:{bus:02x}:{dev:02x}.{fn} {ven:04x}:{did:04x} class {cls:06x} cfg 256")
    (d / "pci.bin").write_bytes(pci_bin)
    (d / "pci.txt").write_text("\n".join(lines) + "\n")
    (d / "gop.txt").write_text("modes 2 current 0 fb 0x80000000 size 0x300000\n"
                               "mode 0: 1280x800 format 1 stride 1280\n"
                               "mode 1: 640x480 format 1 stride 640\n"
                               "edid none\n")
    (d / "firmware.txt").write_text("vendor=EDK II\nrevision=0x10000\nuefi=0x20046\n"
                                    "secure_boot=absent\nsetup_mode=absent\nconfig_tables=9\n")
    files = sorted(p for p in d.rglob("*") if p.is_file())
    (d / "manifest.txt").write_text(
        "".join(f"{p.relative_to(d).as_posix()} {p.stat().st_size}\n" for p in files) + "end\n")
    return d


EXPECT = ["--expect-cpus", "2", "--expect-mem-mib", "512",
          "--expect-smbios", "manufacturer=RitzInventoryTest",
          "--expect-smbios", "product=QEMU-HWINV", "--expect-smbios", "serial=HWINV-3406",
          "--expect-acpi", "FACP,APIC,HPET,MCFG,DSDT,FACS",
          "--expect-pci", "8086:29c0", "--expect-pci", "1af4:1005"]


def _check(d, *extra):
    return check_dump.main([str(d), *EXPECT, *extra])


def test_a_good_dump_passes(tmp_path):
    assert _check(_write_dump(tmp_path)) == 0


def test_find_dump_dir_takes_the_only_timestamp(tmp_path):
    d = _write_dump(tmp_path)
    assert check_dump.find_dump_dir(tmp_path) == d
    (tmp_path / "INVENTORY" / "20261119-070000").mkdir()
    with pytest.raises(check_dump.DumpError):
        check_dump.find_dump_dir(tmp_path)


@pytest.mark.parametrize("mutate, why", [
    (lambda d: (d / "acpi" / "APIC").write_bytes(
        (d / "acpi" / "APIC").read_bytes()[:-1] + b"\x99"), "checksum"),
    (lambda d: (d / "acpi" / "HPET").unlink(), "XSDT"),
    (lambda d: (d / "acpi" / "WAET").write_bytes((d / "acpi" / "HPET").read_bytes()), "signature"),
    (lambda d: (d / "acpi" / "RSDP").write_bytes(b"RSD PTR " + bytes(28)), "RSDP"),
    (lambda d: (d / "smbios" / "smbios_entry_point").write_bytes(b"_SM3_" + bytes(19)), "SMBIOS"),
    (lambda d: (d / "smbios" / "DMI").write_bytes(
        (d / "smbios" / "DMI").read_bytes().replace(b"HWINV-3406", b"HWINV-9999")), "serial"),
    (lambda d: (d / "memmap.bin").write_bytes(b"\0" * 47), "memory map"),
    (lambda d: (d / "pci.txt").write_text("0000:00:00.0 8086:29c0 class 060000 cfg 256\n"), "pci"),
    (lambda d: (d / "gop.txt").write_text("modes 0 current 0\n"), "GOP"),
    (lambda d: (d / "firmware.txt").write_text("vendor=\n"), "vendor"),
    (lambda d: (d / "manifest.txt").write_text("acpi/RSDP 36\n"), "manifest"),
])
def test_each_broken_part_fails(tmp_path, capsys, mutate, why):
    d = _write_dump(tmp_path)
    mutate(d)
    assert _check(d) == 1
    assert why.lower() in capsys.readouterr().out.lower()


def test_cpu_count_comes_from_the_madt(tmp_path, capsys):
    d = _write_dump(tmp_path, cpus=3)
    assert _check(d) == 1
    assert "cpus" in capsys.readouterr().out.lower()


def test_memory_size_comes_from_smbios_and_the_map(tmp_path, capsys):
    d = _write_dump(tmp_path, mem_mib=1024)
    assert _check(d) == 1
    assert "mem" in capsys.readouterr().out.lower()


def test_linux_style_names_for_repeated_signatures(tmp_path):
    """Two SSDTs are SSDT1 and SSDT2, as /sys/firmware/acpi/tables names them."""
    d = _write_dump(tmp_path)
    xsdt = bytearray((d / "acpi" / "XSDT").read_bytes())
    xsdt += struct.pack("<QQ", 1, 2)
    struct.pack_into("<I", xsdt, 4, len(xsdt))
    xsdt[9] = 0
    (d / "acpi" / "XSDT").write_bytes(_checksum_fix(xsdt, 9))
    for i in (1, 2):
        (d / "acpi" / f"SSDT{i}").write_bytes(_acpi_table("SSDT", bytes(8 * i)))
    files = sorted(p for p in d.rglob("*") if p.is_file() and p.name != "manifest.txt")
    (d / "manifest.txt").write_text(
        "".join(f"{p.relative_to(d).as_posix()} {p.stat().st_size}\n" for p in files) + "end\n")
    assert _check(d) == 0


def _rewrite_manifest(d):
    files = sorted(p for p in d.rglob("*") if p.is_file() and p.name != "manifest.txt")
    (d / "manifest.txt").write_text(
        "".join(f"{p.relative_to(d).as_posix()} {p.stat().st_size}\n" for p in files) + "end\n")


def _add_tables(d, tables):
    """Add (file name, table) pairs to the dump, list them in the XSDT."""
    xsdt = bytearray((d / "acpi" / "XSDT").read_bytes())
    for name, t in tables:
        xsdt += struct.pack("<Q", 0x7FFF0000 + len(xsdt))
        (d / "acpi" / name).write_bytes(t)
    struct.pack_into("<I", xsdt, 4, len(xsdt))
    xsdt[9] = 0
    (d / "acpi" / "XSDT").write_bytes(_checksum_fix(xsdt, 9))
    _rewrite_manifest(d)


@pytest.mark.parametrize("sig, names", [
    ("ASF!", ["ASF_"]),               # HWINV writes a FAT-unsafe byte as '_'
    ("DBG2", ["DBG2"]),               # a digit in the signature is not an instance number
    ("TPM2", ["TPM2"]),
    ("DBG2", ["DBG21", "DBG22"]),     # ...and a repeated one still gets 1, 2
])
def test_real_firmware_table_names(tmp_path, capsys, sig, names):
    d = _write_dump(tmp_path)
    _add_tables(d, [(n, _acpi_table(sig, bytes(4 * i))) for i, n in enumerate(names)])
    assert _check(d) == 0, capsys.readouterr().out


# --- scrub_dump: identifiers out, everything else byte-identical --------------

scrub_dump = _load("scrub_dump")
dump_summary = _load("dump_summary")

SYS_SERIAL, BOARD_SERIAL, CHASSIS_SERIAL, ASSET = "SYSSER0001", "BRDSER0002", "CHSSER0003", "ASSET-0077"
CPU_SERIAL, DIMM_SERIAL = "CPUSER0004", "DIMMSER05"
UUID = bytes(range(0x31, 0x41))
OEM_ID = bytes(range(0xA1, 0xB1))
DSN = bytes.fromhex("0011223344556677")
EDID_SERIAL32 = bytes.fromhex("51525354")
EDID_SERIAL_TEXT = "MONSER0006"
PRODUCT_KEY = "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE"
SECRETS = [SYS_SERIAL, BOARD_SERIAL, CHASSIS_SERIAL, ASSET, CPU_SERIAL, DIMM_SERIAL, UUID, OEM_ID,
           DSN, EDID_SERIAL32, EDID_SERIAL_TEXT, PRODUCT_KEY]


def _struct_at(typ, handle, ln, fields, strings):
    """An SMBIOS structure of formatted length ln with byte/word fields set."""
    f = bytearray(ln)
    f[0], f[1] = typ, ln
    struct.pack_into("<H", f, 2, handle)
    for at, v in fields.items():
        if isinstance(v, bytes):
            f[at:at + len(v)] = v
        elif at in WORD_FIELDS.get(typ, ()):
            struct.pack_into("<H", f, at, v)
        else:
            f[at] = v
    tail = b"\0".join(s if isinstance(s, bytes) else s.encode() for s in strings) + b"\0\0" \
        if strings else b"\0\0"
    return bytes(f) + tail


WORD_FIELDS = {4: (0x14, 0x16), 17: (0x0C, 0x15), 22: (0x10,)}


def _real_smbios():
    s = [
        _struct_at(0, 0, 0x1A, {4: 1, 5: 2, 8: 3}, ["Firmware Co", "1.57", "10/21/2024"]),
        _struct_at(1, 1, 0x1B, {4: 1, 5: 2, 6: 3, 7: 4, 8: UUID}, ["Box Co", "Box 9", "Rev A", SYS_SERIAL]),
        _struct_at(2, 2, 0x0F, {4: 1, 5: 2, 6: 3, 7: 4, 8: 5},
                   ["Board Co", "BRD-1", "1.0", BOARD_SERIAL, "Default string"]),
        _struct_at(3, 3, 0x16, {4: 1, 5: 0x0A, 6: 2, 7: 3, 8: 4}, ["Box Co", "1.0", CHASSIS_SERIAL, ASSET]),
        _struct_at(4, 4, 0x30, {0x10: 1, 0x14: 4000, 0x16: 3500, 0x18: 0x41, 0x20: 2, 0x21: 3, 0x23: 4, 0x25: 8},
                   ["Example CPU 9000 @ 3.50GHz", CPU_SERIAL, "To Be Filled By O.E.M."]),
        _struct_at(17, 5, 0x28, {0x0C: 8192, 0x10: 1, 0x12: 0x1A, 0x15: 3200, 0x17: 2, 0x18: 3, 0x1A: 4},
                   ["DIMM_A1", "Hynix", DIMM_SERIAL, "HMA81GS6 "]),
        _struct_at(17, 6, 0x28, {0x0C: 8192, 0x10: 1, 0x12: 0x1A, 0x15: 3200, 0x17: 2, 0x18: 3, 0x1A: 4},
                   ["DIMM_B1", "Hynix", "00000000", "HMA81GS6 "]),
        _struct_at(22, 7, 0x1A, {4: 1, 5: 2, 8: 3, 0x10: 0xBEEF}, ["Front", "SMP", "BATT-NAME1"]),
        _struct_at(133, 8, 0x2C, {4: OEM_ID}, [b"\x85," + OEM_ID, b"\x03OEMTEXT"]),
        _struct_at(127, 9, 4, {}, []),
    ]
    table = b"".join(s)
    ep = bytearray(24)
    ep[0:5] = b"_SM3_"
    ep[6], ep[7], ep[10] = 24, 3, 1
    struct.pack_into("<IQ", ep, 12, len(table), 0x7F000000)
    return _checksum_fix(ep, 5), table


def _edid():
    e = bytearray(128)
    e[0:8] = b"\0\xff\xff\xff\xff\xff\xff\0"
    e[8:10] = b"\x04\x43"
    e[12:16] = EDID_SERIAL32
    for i, (tag, text) in enumerate([(0xFF, EDID_SERIAL_TEXT), (0xFC, "PANEL-27")]):
        blk = 54 + 18 * i
        e[blk + 3] = tag
        e[blk + 5:blk + 18] = (text.encode() + b"\n").ljust(13, b" ")
    return _checksum_fix(e, 127)


def _write_real_dump(root):
    """A dump shaped like a real machine's: serials, a UUID, a PCIe DSN, an
    EDID serial and a Windows product key, beside the names that stay."""
    d = _write_dump(root)
    ep, dmi = _real_smbios()
    (d / "smbios" / "smbios_entry_point").write_bytes(ep)
    (d / "smbios" / "DMI").write_bytes(dmi)
    cfg = bytearray(4096)
    struct.pack_into("<HH", cfg, 0, 0x8086, 0x15A1)
    cfg[9], cfg[10], cfg[11] = 0, 0, 2
    struct.pack_into("<I", cfg, 0x100, 0x00000003 | (1 << 16) | (0x140 << 20))
    cfg[0x104:0x10C] = DSN
    struct.pack_into("<I", cfg, 0x140, 0x0000000B | (1 << 16))   # a vendor cap after it
    cfg[0x144:0x148] = b"KEEP"
    with (d / "pci.bin").open("ab") as f:
        f.write(struct.pack("<HBBBBH", 0, 4, 0, 0, 0, 4096) + bytes(cfg))
    with (d / "pci.txt").open("a") as f:
        f.write("0000:04:00.0 8086:15a1 class 020000 cfg 4096\n")
    (d / "edid-0.bin").write_bytes(_edid())
    (d / "gop.txt").write_text((d / "gop.txt").read_text().replace("edid none", "edid 0 128"))
    (d / "hwinv.log").write_text("HWINV: writing \\INVENTORY\\20261119-060203\n")
    msdm = struct.pack("<IIIII", 1, 0, 1, 0, len(PRODUCT_KEY)) + PRODUCT_KEY.encode()
    _add_tables(d, [("MSDM", _acpi_table("MSDM", msdm))])
    return d


def test_an_edid_with_a_bad_checksum_fails(tmp_path, capsys):
    d = _write_real_dump(tmp_path / "raw")
    e = bytearray((d / "edid-0.bin").read_bytes())
    e[20] ^= 1
    (d / "edid-0.bin").write_bytes(bytes(e))
    assert check_dump.main([str(d)]) == 1
    assert "edid-0.bin" in capsys.readouterr().out


def _scrub(raw, out, *extra):
    return scrub_dump.main([str(raw), str(out), *extra])


def _haystacks(d):
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in d.rglob("*") if p.is_file()}


def _forms(secret):
    if isinstance(secret, bytes):
        return [secret, secret[::-1]]
    return [secret.encode(), secret.encode("utf-16-le")]


def test_the_real_shaped_dump_is_valid_and_holds_every_secret(tmp_path, capsys):
    """The fixture itself: check_dump passes it, and each secret is in it."""
    d = _write_real_dump(tmp_path / "raw")
    assert check_dump.main([str(d)]) == 0, capsys.readouterr().out
    blob = b"".join(_haystacks(d).values())
    for s in SECRETS:
        assert _forms(s)[0] in blob, s


def test_scrub_removes_every_identifier(tmp_path, capsys):
    raw = _write_real_dump(tmp_path / "raw")
    out = tmp_path / "out"
    assert _scrub(raw, out) == 0, capsys.readouterr().out
    for name, data in _haystacks(out).items():
        for s in SECRETS:
            for form in _forms(s):
                assert form not in data, f"{s!r} left in {name}"


def test_scrubbed_dump_still_checks_and_keeps_its_shape(tmp_path, capsys):
    raw = _write_real_dump(tmp_path / "raw")
    out = tmp_path / "out"
    assert _scrub(raw, out) == 0
    assert check_dump.main([str(out)]) == 0, capsys.readouterr().out
    before, after = _haystacks(raw), _haystacks(out)
    assert {k: len(v) for k, v in before.items()} == {k: len(v) for k, v in after.items()}
    for unchanged in ("memmap.bin", "acpi/DSDT", "acpi/APIC", "gop.txt", "manifest.txt"):
        assert before[unchanged] == after[unchanged], unchanged


def test_scrub_keeps_names_placeholders_and_the_rest_of_config_space(tmp_path):
    raw = _write_real_dump(tmp_path / "raw")
    out = tmp_path / "out"
    assert _scrub(raw, out) == 0
    dmi = (out / "smbios" / "DMI").read_bytes()
    for kept in (b"Box Co", b"Box 9", b"Example CPU 9000", b"Default string", b"To Be Filled By O.E.M.",
                 b"00000000", b"HMA81GS6", b"BATT-NAME1", b"\x03OEMTEXT"):
        assert kept in dmi, kept
    assert b"KEEP" in (out / "pci.bin").read_bytes()
    assert b"PANEL-27" in (out / "edid-0.bin").read_bytes()
    assert b"\xef\xbe" not in dmi                           # the battery's SBDS serial word


@pytest.mark.parametrize("planted", [
    SYS_SERIAL.encode(),                    # a serial as text
    SYS_SERIAL.encode("utf-16-le"),         # ...as UTF-16, as in a _STR
    DSN[::-1],                              # an ID's bytes, the other byte order
], ids=["text", "utf16", "reversed"])
def test_scrub_refuses_an_identifier_it_cannot_place(tmp_path, capsys, planted):
    """A serial somewhere no rule covers (here: in the DSDT) fails the scrub
    and writes nothing, rather than committing it."""
    raw = _write_real_dump(tmp_path / "raw")
    (raw / "acpi" / "DSDT").write_bytes(_acpi_table("DSDT", b"\x0d" + planted + b"\0", rev=2))
    _rewrite_manifest(raw)
    out = tmp_path / "out"
    assert _scrub(raw, out) == 1
    assert "acpi/DSDT" in capsys.readouterr().out
    assert not out.exists()


def test_scrub_refuses_a_forbidden_word(tmp_path, capsys):
    raw = _write_real_dump(tmp_path / "raw")
    (raw / "hwinv.log").write_text("HWINV on myhost\n")
    _rewrite_manifest(raw)
    assert _scrub(raw, tmp_path / "out", "--forbid", "MyHost") == 1
    assert "hwinv.log" in capsys.readouterr().out
    assert not (tmp_path / "out").exists()


def test_scrub_report_names_fields_not_values(tmp_path, capsys):
    raw = _write_real_dump(tmp_path / "raw")
    assert _scrub(raw, tmp_path / "out") == 0
    report = capsys.readouterr().out
    for what in ("serial", "uuid", "dsn", "edid", "msdm"):
        assert what in report.lower(), what
    for s in SECRETS:
        assert (s if isinstance(s, str) else s.hex()) not in report


# --- dump_summary: CPU, RAM and PCI names, from the dump on the host -------------

PCI_IDS = """\
#\tVersion: 2026.11.01
1234  Technical Corp.
\t1111  QEMU Virtual Video Controller
8086  Intel Corporation
\t15a1  Ethernet Connection (2) I218-V
\t29c0  82G33/G31/P35/P31 Express DRAM Controller
C 02  Network controller
\t00  Ethernet controller
C 03  Display controller
\t00  VGA compatible controller
C 06  Bridge
\t00  Host bridge
"""


def test_summary_names_cpu_ram_pci_and_panel(tmp_path):
    d = _write_real_dump(tmp_path / "raw")
    ids = tmp_path / "pci.ids"
    ids.write_text(PCI_IDS)
    text = dump_summary.summarize(d, ids)
    assert "Example CPU 9000 @ 3.50GHz" in text
    assert "4 cores, 8 threads" in text
    assert "16384 MiB" in text and "DDR4" in text and "3200 MT/s" in text and "HMA81GS6" in text
    assert "0000:04:00.0 8086:15a1 Ethernet controller: Intel Corporation " \
           "Ethernet Connection (2) I218-V" in text
    assert "0000:00:02.0 1af4:1005 class 00ff00" in text     # not in pci.ids: ids only
    assert "pci.ids 2026.11.01" in text
    assert "PANEL-27" in text
    assert "Box Co Box 9" in text
    for s in SECRETS:
        assert (s if isinstance(s, str) else s.hex()) not in text
