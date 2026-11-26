# Hardware-inventory USB stick

A USB stick image that inventories a machine that doesn't run Linux (AGAST
#3406, for M2.4). Boot it from the firmware's boot menu. It writes what the
firmware knows about the machine to the stick and powers off. Pull the stick
and read the files on any computer.

## What it is

- **`src/main.ritz`** builds `HWINV.EFI`, a UEFI application written in Ritz
  (the `hwinv` bin in `../ritz.toml`, linked with `lld-link`). It runs
  before ExitBootServices and uses only Boot and Runtime Services, so it
  needs no drivers of its own.
- **`esp_image.py`** builds the raw image (`build`) and reads files back out
  of one (`extract`). The image has a protective MBR, a GPT and one FAT32
  EFI System Partition. `HWINV.EFI` sits at `\EFI\BOOT\BOOTX64.EFI`, the
  removable-media default path, so firmware boots it with no NVRAM entry.
  The script is pure Python: it needs no mtools, dosfstools or root.
- **`check_dump.py`** validates a dump (see below).
- **`scrub_dump.py`** and **`dump_summary.py`** prepare a real machine's dump
  for committing (see "Commit a real machine's dump").
- **`test.sh`** boots the image headless (q35 + OVMF, writable USB storage)
  and checks the dump. CI runs it in the build-all job.

## Build and write a stick

```bash
make -C projects/harland inventory-img          # build/hwinv.img, 64 MiB
make -C projects/harland inventory-img INVENTORY_MIB=256
sudo dd if=projects/harland/build/hwinv.img of=/dev/sdX bs=4M conv=fsync
```

On real hardware, turn Secure Boot off first, because `HWINV.EFI` is
unsigned.

## What it writes

Everything goes to `\INVENTORY\<YYYYMMDD-HHMMSS>\` on the stick. If that
directory already exists, the app adds `-2`, `-3` and so on, so several
machines can share one stick.

| File | Contents |
|---|---|
| `acpi/RSDP`, `acpi/XSDT` (or `RSDT`) | raw |
| `acpi/<SIG>[n]` | every table the XSDT lists, raw, named as Linux's `/sys/firmware/acpi/tables` (`SSDT1`, `SSDT2` when a signature repeats), except that a signature byte outside `[0-9A-Za-z]` is written as `_` (`ASF!` is `ASF_`) |
| `acpi/DSDT`, `acpi/FACS` | from the FADT |
| `smbios/smbios_entry_point`, `smbios/DMI` | SMBIOS3 when the firmware has it, else 2.x; same layout as `/sys/firmware/dmi/tables` |
| `memmap.bin`, `memmap.txt` | GetMemoryMap's descriptors, raw and one line each (`type start pages attr`) |
| `pci.bin`, `pci.txt` | config space of every function on every root bridge (PCI Root Bridge I/O). 4 KiB where extended config space answers, else 256 B. `pci.bin` records are `seg u16, bus, dev, func, 0, len u16`, then the bytes |
| `gop.txt`, `edid-<n>.bin` | GOP modes and the current mode; EDID (active, else discovered) per GOP handle |
| `firmware.txt` | vendor, firmware revision, UEFI revision, `SecureBoot`, `SetupMode`, every configuration-table GUID |
| `hwinv.log` | what each step did |
| `manifest.txt` | every file and its size, then `end`. Written last, so a complete manifest means a complete dump |

A failing step is logged and skipped; the rest still run.

## Check a dump

```bash
python3 projects/harland/inventory/esp_image.py extract hwinv.img out/   # or mount the stick
python3 projects/harland/inventory/check_dump.py out/
```

`check_dump.py` checks:

- every ACPI table's signature, length and checksum;
- that the XSDT's table count matches the files and the files use Linux's
  names, telling an instance number from a digit in the signature (`DBG2`,
  `TPM2`);
- the SMBIOS entry point and structure table;
- the memory map, PCI, GOP, each EDID block's checksum, and the manifest.

`--expect-cpus`, `--expect-mem-mib`, `--expect-smbios field=value`,
`--expect-acpi` and `--expect-pci` pin known facts. `test.sh` uses them with
what it told QEMU (`-smp`, `-m`, `-smbios type=1`, the PCI devices it added).
It boots twice, once with each SMBIOS entry point (64-bit and 32-bit), and
runs `fsck.fat` on the image after the firmware's writes when `fsck.fat` is
installed.

```bash
make -C projects/harland test-inventory      # ~12 s
```

## Commit a real machine's dump

A real dump holds the machine's identifiers, so it is never committed raw
(#4300). The dumps live in `projects/harland/docs/hardware/<model>/hwinv/`,
next to the machine's README and `hwinv-summary.txt`.

```bash
I=projects/harland/inventory
H=projects/harland/docs/hardware/<model>
python3 $I/check_dump.py /media/stick/INVENTORY/<stamp>
python3 $I/scrub_dump.py /media/stick/INVENTORY/<stamp> $H/hwinv \
    --forbid <hostname> --forbid <username>
python3 $I/dump_summary.py $H/hwinv -o $H/hwinv-summary.txt
```

`scrub_dump.py` copies the dump with these removed, and everything else
byte-identical:

- SMBIOS serial numbers and asset tags (types 1, 2, 3, 4, 17, 22, 39), unless
  they are a vendor placeholder; the system UUID; the battery's SBDS serial;
  Lenovo's type 133 opaque ID;
- every PCIe Device Serial Number (some NICs put their MAC address in it);
- the EDID serial number and serial-string descriptor;
- the Windows product key in `MSDM`.

Edits keep each file's size and fix the checksums they break, so
`manifest.txt` stays right and `check_dump.py` still passes. Afterwards the
script searches every file for every value it removed (text, UTF-16, bytes in
both byte orders) and for each `--forbid` word. If one still turns up
somewhere no rule covers, it writes nothing and names the file. It prints
which fields it scrubbed, never their values: copy that into the machine's
README.

`dump_summary.py` prints the machine, firmware, CPU, RAM, display and every
PCI function with its name from `pci.ids` (lspci's database, found on the
host; `--pci-ids` picks another). It never prints a serial number.
