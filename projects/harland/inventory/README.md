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
| `acpi/<SIG>[n]` | every table the XSDT lists, raw, named as Linux's `/sys/firmware/acpi/tables` (`SSDT1`, `SSDT2` when a signature repeats) |
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
- that the XSDT's table count matches the files and the files use Linux's names;
- the SMBIOS entry point and structure table;
- the memory map, PCI, GOP and the manifest.

`--expect-cpus`, `--expect-mem-mib`, `--expect-smbios field=value`,
`--expect-acpi` and `--expect-pci` pin known facts. `test.sh` uses them with
what it told QEMU (`-smp`, `-m`, `-smbios type=1`, the PCI devices it added).
It boots twice, once with each SMBIOS entry point (64-bit and 32-bit), and
runs `fsck.fat` on the image after the firmware's writes when `fsck.fat` is
installed.

```bash
make -C projects/harland test-inventory      # ~12 s
```

Real hardware and a scrub/commit script for the dumps are Phase 2 (AGAST
#4300).
