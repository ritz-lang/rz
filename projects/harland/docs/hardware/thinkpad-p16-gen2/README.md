# Lenovo ThinkPad P16 Gen 2: hardware inventory

The first target machine for M2.4, "Boots on a laptop" (#1842, #1853).

| | |
|---|---|
| Model | LENOVO 21FACTO1WW, "ThinkPad P16 Gen 2" (machine type 21FA) |
| Firmware | UEFI, 64-bit EFI. BIOS N3TET57W 1.57 (2024-10-21), EC 1.55 |
| CPU | Intel Core i7-13850HX (Raptor Lake-HX): 20 cores, 28 threads |
| Memory | 64 GB, 2 SO-DIMMs |
| Captured | 2026-11-15. Read-only, over ssh, with sudo, from the machine's running Ubuntu 26.04 (kernel 7.0.0-42) |

The machine left the LAN after this capture, so nothing in it can be
re-captured. The inventory stick (#3406) was booted on it on 2026-11-26:
`hwinv/` is that dump, and it fills most of "What's missing" below.

## Files

| File | Contents |
|---|---|
| `summary.txt` | `/sys/class/dmi/id` fields, UEFI and EFI bitness, and the kernel version |
| `lscpu.txt` | `lscpu` |
| `proc.txt` | `/proc/cpuinfo`, `/proc/meminfo`, and `/proc/iomem` read as a normal user (addresses are zeroed: use `root/iomem.txt`) |
| `lspci-nnk.txt`, `lspci-vv.txt` | `lspci` read as a normal user |
| `lsusb.txt` | `lsusb` and `lsusb -t` |
| `misc.txt` | `/sys/firmware/acpi/tables` listing, DRM connectors, `ip -br link`, input, NVMe and sound class devices |
| `root/dmidecode.txt` | `dmidecode` (full SMBIOS) |
| `root/acpi/` | Raw ACPI tables from `/sys/firmware/acpi/tables`. `dynamic/` holds the SSDTs that firmware loads at runtime |
| `root/lspci-vvv-root.txt` | `lspci -vvv` read as root (shows capabilities) |
| `root/lspci-config-space.txt` | `lspci -xxxx`: 4 KiB config space for every function |
| `root/iomem.txt`, `root/interrupts.txt` | `/proc/iomem` (real addresses), `/proc/interrupts` |
| `root/memmap/memmap.txt` | Firmware memory map from `/sys/firmware/memmap` (the e820 view) |
| `root/efivars-list.txt` | EFI variable names (names only, no contents) |
| `hwinv/` | The inventory stick's dump, scrubbed (#4300): raw ACPI, raw SMBIOS, the UEFI memory map, 4 KiB PCI config space, GOP modes, EDID. Layout: `projects/harland/inventory/README.md` |
| `hwinv-summary.txt` | CPU, RAM, PCI names and display, generated from `hwinv/` by `inventory/dump_summary.py` |

The DSDT and SSDTs are **not decompiled**: `iasl` (acpica-tools) is not
installed on the machine where this was committed. Run
`iasl -d root/acpi/DSDT` (add `-e root/acpi/SSDT*` to resolve externals) to
get `.dsl`.

## What matters for harland's first boot

- **Framebuffer: use UEFI GOP.** The iGPU is Intel Raptor Lake-S UHD
  Graphics [8086:a788] at 00:02.0, with a 256 MiB prefetchable BAR at
  0x4000000000 and graphics stolen memory at 0x9c800000-0xa07fffff. The
  laptop's internal panel is on `card1-eDP-1`. External DP and HDMI are on
  `card2`, which is probably the NVIDIA dGPU. That fits hybrid ("Optimus")
  graphics, where the iGPU drives the panel. The capture did not record which
  PCI device each DRM card belongs to, or the GOP mode.
- **dGPU:** NVIDIA RTX 3500 Ada Laptop (AD104GLM) [10de:27bb] at 01:00.0, with
  HDA audio [10de:22bc] at 01:00.1. Harland can ignore it at first.
- **xHCI:** Intel Raptor Lake USB 3.2 Gen 2x2 [8086:7a60] at 00:14.0. It
  carries the internal devices: Synaptics fingerprint reader [06cb:0126],
  camera [174f:1812] and AX211 Bluetooth [8087:0033]. The keyboard and
  trackpoint are on i8042 (IRQ 1) rather than USB. The Thunderbolt 4 (Maple
  Ridge) xHCI [8086:1138] at 48:00.0 sits behind the TB bridges at 20:00.0
  and 21:0x.0, with its NHI [8086:1137] at 22:00.0.
- **NVMe:** Samsung PM9A1 [144d:a80a] at 07:00.0. It appears as a plain NVMe
  function: no Intel VMD/RST remapping was seen in `lspci`.
- **MCFG (PCIe ECAM):** base 0xc0000000, segment 0, buses 0-255.
- **HPET:** 0xfed00000.
- **MADT:** LAPIC at 0xfee00000. 32 Local APIC entries (28 threads present),
  1 IOAPIC (id 2, 0xfec00000, GSI base 0), 2 interrupt source overrides and
  24 LAPIC NMI entries. There are no x2APIC entries.
- **DMAR** (VT-d) is present.
- **FADT:** revision 6, not hardware-reduced. The `LOW_POWER_S0_IDLE_CAPABLE`
  flag is set (S0ix, "modern standby"). `IAPC_BOOT_ARCH` = 0x1, so the 8042
  flag is clear even though the kernel drives an i8042 on IRQ 1.
- **Other devices:** CNVi WiFi (AX211) [8086:7a70] at 00:14.3, Realtek
  card reader (`rtsx_pci`) at 0a:00.0, Raptor Lake HDA [8086:7a50] at 00:1f.3.
  The machine has no wired Ethernet controller.

All ACPI table checksums are valid as committed (FACS has no checksum).

## What's missing

What Linux could not show, or what the Linux capture did not include. The
first three and the last are now in `hwinv/`:

- The **UEFI memory map** with EFI memory types: `hwinv/memmap.txt`, 90
  descriptors. (`root/memmap/memmap.txt` is the e820 view, and `iomem.txt` is
  Linux's merged view.)
- **GOP modes**, the mode firmware boots in, and the framebuffer base and
  stride: `hwinv/gop.txt`. Firmware boots in mode 0, 3840x2400, stride 3840
  pixels, framebuffer 0x4000000000 (size 0x2328000). That is the iGPU's
  prefetchable BAR, so the iGPU drives the panel at boot.
- **EDID:** `hwinv/edid-0.bin`, the AUO B160ZAN01.T panel (256 bytes, base
  block and one extension).
- **The boot log.** The kernel ring buffer had wrapped after about 3 days of
  uptime and held only AppArmor audit lines and Bluetooth `hci0` reset
  timeouts. It was dropped (see below), so there are no boot-time e820, EFI,
  ACPI or PCI messages.
- **The contents of EFI variables** (Setup, Secure Boot keys and so on), the
  TPM event log, and Option ROMs.
- **The SMBIOS entry point and raw table bytes:** `hwinv/smbios/`.

`hwinv/acpi/` is byte-identical to `root/acpi/` except `BGRT` and `PHAT`,
which firmware rebuilds on every boot. The stick names `ASF!` as `ASF_`: it
writes any signature byte outside `[0-9A-Za-z]` as `_`.

## Scrubbing

Before committing, the capture was searched for serial numbers, UUIDs, MAC
addresses, the machine's hostname, and the owner's username. The search
covered every text file and every raw ACPI table, as text, as UTF-16, and as
binary in both byte orders. Every match was handled as follows. Afterwards a
search of this directory for each original value finds nothing.

- **`dmidecode.txt`:** the serial numbers for the system, chassis and
  baseboard, both memory modules, and the battery (SBDS) are replaced with
  `<scrubbed>`, and so is the system UUID. A 16-byte opaque ID in the Lenovo
  OEM type-133 record (handle 0x0031) is zeroed, and the string that decodes
  from it is replaced with `<scrubbed>`. That ID may be per-machine, so it was
  scrubbed as a precaution.
- **`lspci-vvv-root.txt`:** every PCIe *Device Serial Number* capability
  value is replaced with `<scrubbed>` (the Thunderbolt bridges/controllers
  and the card reader).
- **`lspci-config-space.txt`:** the same values are zeroed in the hex dump.
  The scrub walked each function's extended-capability list and zeroed the 8
  serial bytes of each DSN capability (ID 0x0003). Everything else in the
  dump is unchanged.
- **`misc.txt`:** the WiFi MAC address is replaced with `<scrubbed>`. The
  lines for virtual interfaces (Docker bridges, veth, WireGuard) are removed:
  they are host configuration, not hardware.
- **`dmesg.txt` was not committed.** It held no hardware information (see
  above). It did hold process and file names from the host's software.
- **Not changed:** the ACPI tables are byte-identical to the capture. No
  table contained an identifier, so none was dropped or patched. The EFI
  variable list is also unchanged: its GUIDs are firmware vendor namespaces,
  and no variable name embeds a serial number. The hostname and username did
  not appear in any file. The SMBIOS asset tag `9876543210` is a factory
  default, so it was kept.
- The `ssh` post-quantum warning lines at the top of some files were also
  removed.

### `hwinv/`

`hwinv/` was scrubbed by `projects/harland/inventory/scrub_dump.py`, which
applies the rules above to the raw dump and keeps every file's size. Its
report:

- SMBIOS: the system, baseboard and chassis serial numbers, both DIMMs'
  serial numbers and the system UUID; the battery's SBDS serial number; the
  Lenovo type 133 opaque ID (handle 0x0031) and the string that repeats it.
  The serials are overwritten with `X`s, and the UUID and IDs are zeroed.
- `pci.bin`: the Device Serial Number of the card reader (0a:00.0) and of each
  Thunderbolt function (20:00.0, 21:0x.0, 22:00.0) is zeroed.
- The EDID has no serial number, and no ACPI table held an identifier.

After the scrub, the script searched every file for each removed value, as
text, as UTF-16 and as bytes in both byte orders, and for the machine's
hostname and the owner's username. Nothing matched, and `check_dump.py`
passes on the result.
