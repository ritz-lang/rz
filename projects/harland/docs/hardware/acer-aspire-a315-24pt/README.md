# Acer Aspire 3 A315-24PT: hardware inventory

An AMD laptop that runs Windows, inventoried with the stick (#3406, #4300).

| | |
|---|---|
| Model | Acer Aspire A315-24PT ("Aspire 3 15"), board MDC Herbag_MDU V1.18 |
| Firmware | Insyde V1.18 (2024-06-18), UEFI 2.80. Secure Boot was off for the capture |
| CPU | AMD Ryzen 5 7520U (Mendocino, Zen 2): 4 cores, 8 threads |
| Memory | 16 GiB LPDDR5-5500, soldered (two 8 GiB channels) |
| Display | 1920x1080 internal panel, Innolux (CMN) N156HCN-EAA |
| Captured | 2026-11-26, by booting the inventory stick |

## Files

| File | Contents |
|---|---|
| `hwinv/` | The stick's dump, scrubbed: raw ACPI, raw SMBIOS, the UEFI memory map, PCI config space, GOP modes, EDID. Layout: `projects/harland/inventory/README.md` |
| `hwinv-summary.txt` | CPU, RAM, PCI names and display, generated from `hwinv/` by `inventory/dump_summary.py` |

## What matters for harland's first boot

- **Framebuffer: UEFI GOP.** Firmware boots in mode 0, 1920x1080. The
  framebuffer is at 0x7ee0000000, size 0x7e9000 (`hwinv/gop.txt`). The GPU is
  the integrated Radeon (Mendocino) [1002:1506] at 03:00.0.
- **NVMe:** Kingston OM8PGP4 (DRAM-less) [2646:501b] at 01:00.0.
- **USB:** three AMD xHCI functions, at 03:00.3, 03:00.4 and 04:00.0.
- **WiFi:** MediaTek MT7921 [14c3:7961] at 02:00.0. There is no wired
  Ethernet controller.
- **MCFG (PCIe ECAM):** base 0xe0000000, segment 0, buses 0-255.
- **MADT:** 16 Local APIC entries (8 enabled) and 2 IOAPICs: id 33 at
  0xfec00000 (GSI 0) and id 34 at 0xfec01000 (GSI 24).
- **FADT:** revision 5, not hardware-reduced, `LOW_POWER_S0_IDLE_CAPABLE`
  set. `IAPC_BOOT_ARCH` = 0x3 (legacy devices, 8042).
- **IOMMU:** AMD-Vi, `IVRS` present. `CRAT` and `CDIT` describe the APU
  topology for HSA.

## Scrubbing

`hwinv/` was scrubbed by `projects/harland/inventory/scrub_dump.py`. Its
report:

- SMBIOS: the system and baseboard serial numbers (overwritten with `X`s)
  and the system UUID (zeroed). The chassis serial and asset tags are vendor
  placeholders ("Chassis Serial Number", "Type2 - Board Asset Tag"), and the
  DIMM serials are `00000000`, so they were kept.
- `acpi/MSDM`: the embedded Windows product key is overwritten with `X`s and
  the table's checksum is fixed.
- No PCI function has a Device Serial Number, and the EDID has no serial
  number.

After the scrub, the script searched every file for each removed value, as
text, as UTF-16 and as bytes in both byte orders, and for the machine's
hostname and the owner's username. Nothing matched, and `check_dump.py`
passes on the result.
