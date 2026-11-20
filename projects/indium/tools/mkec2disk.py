#!/usr/bin/env python3
"""Build the EC2 boot disk without root (AGAST #1849).

    mkec2disk.py OUT.img BOOTX64.EFI kernel.elf initramfs.tar [--size-mib N]

The layout is the one `make ec2-disk` built with sgdisk, losetup and
mkfs.vfat under sudo: a GPT with one EFI System Partition from 1 MiB to the
end, FAT32, holding

    /EFI/BOOT/BOOTX64.EFI     the removable-media default path EC2's UEFI boots
    /harland/kernel.elf
    /harland/initramfs.tar    BOOTX64.EFI hands it to the kernel (AGAST #4253)
    /startup.nsh              the UEFI shell fallback

Task rooms have no sudo (the "no new privileges" flag), no mtools and no
dosfstools (which lives in /usr/sbin, off a room's PATH). harland's
inventory/esp_image.py writes the GPT and the FAT32 in pure Python, long
names included, so the whole disk is built here without a helper binary.

The image is built under a temporary name and renamed into place only when
every step succeeded, so make never sees a half-written disk as up to date.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "harland" / "inventory"))

import esp_image  # noqa: E402

STARTUP_NSH = b"@echo -off\r\nFS0:\\EFI\\BOOT\\BOOTX64.EFI\r\n"


def build(out: Path, efi: Path, kernel: Path, initramfs: Path, size_mib: int = 128) -> None:
    out = Path(out)
    tmp = out.with_name(out.name + ".tmp")
    esp_image.build_image(tmp, {
        "EFI/BOOT/BOOTX64.EFI": Path(efi).read_bytes(),
        "STARTUP.NSH": STARTUP_NSH,
        "harland/kernel.elf": Path(kernel).read_bytes(),
        "harland/initramfs.tar": Path(initramfs).read_bytes(),
    }, size_mib=size_mib)
    tmp.replace(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the EC2 boot disk (GPT + FAT32 ESP), rootless")
    ap.add_argument("out", type=Path)
    ap.add_argument("efi", type=Path)
    ap.add_argument("kernel", type=Path)
    ap.add_argument("initramfs", type=Path)
    ap.add_argument("--size-mib", type=int, default=128)
    a = ap.parse_args(argv)
    build(a.out, a.efi, a.kernel, a.initramfs, a.size_mib)
    print(f"Created: {a.out} (GPT + ESP: BOOTX64.EFI, harland/kernel.elf, harland/initramfs.tar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
