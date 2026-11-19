"""The hardware-inventory boot image's host tools (AGAST #3406).

projects/harland/inventory holds a UEFI app (HWINV.EFI) that dumps ACPI,
SMBIOS, the memory map, PCI config space, GOP/EDID and firmware facts to
\\INVENTORY\\<timestamp>\\ on the FAT32 ESP it booted from, and two host tools:

  esp_image.py   builds the raw USB-stick image (protective MBR + GPT + one
                 FAT32 ESP holding \\EFI\\BOOT\\BOOTX64.EFI) and reads files
                 back out of one, with no mtools, dosfstools or root;
  check_dump.py  validates a dump: every ACPI table's signature, length and
                 checksum, the XSDT's table count, the SMBIOS entry point and
                 structure table, the memory map, PCI, GOP and the manifest,
                 and any facts the test pinned on QEMU's command line.

These run both tools on synthetic inputs, so they need no QEMU, OVMF or
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

INVENTORY = Path(__file__).resolve().parents[2] / "harland" / "inventory"


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


def test_build_rejects_names_that_are_not_83(tmp_path):
    with pytest.raises(ValueError):
        esp_image.build_image(tmp_path / "x.img", {"EFI/BOOT/bootx64.efi.old": b""})


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
