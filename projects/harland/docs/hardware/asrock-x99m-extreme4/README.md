# ASRock X99M Extreme4 desktop: hardware inventory

A Haswell-E desktop on an ASRock X99M Extreme4 board, inventoried with the
stick (#3406, #4300). The board's SMBIOS system fields are all "To Be Filled
By O.E.M.".

| | |
|---|---|
| Board | ASRock X99M Extreme4 |
| Firmware | AMI P1.50 (2014-09-04), UEFI 2.31. Secure Boot off, in setup mode |
| CPU | Intel Core i7-5930K (Haswell-E) @ 3.50 GHz: 6 cores, 12 threads |
| Memory | 32 GiB, 4 x 8 GiB DDR4 at 2133 MT/s (SMBIOS reports the type as "Other") |
| GPU | NVIDIA GeForce GTX 1070 (GP104) [10de:1b81] at 02:00.0 |
| Display | Samsung U28E510 monitor, 3840x2160 |
| Captured | 2026-11-26, by booting the inventory stick |

## Files

| File | Contents |
|---|---|
| `hwinv/` | The stick's dump, scrubbed: raw ACPI, raw SMBIOS, the UEFI memory map, PCI config space, GOP modes, EDID. Layout: `projects/harland/inventory/README.md` |
| `hwinv-summary.txt` | CPU, RAM, PCI names and display, generated from `hwinv/` by `inventory/dump_summary.py` |

## What matters for harland's first boot

- **Framebuffer: UEFI GOP**, on the GTX 1070: firmware boots in mode 0,
  3840x2160, and the framebuffer at 0xe0000000 (size 0x21c0000,
  `hwinv/gop.txt`) is the card's BAR1.
- **Storage:** the X99 SATA controller is in RAID mode [8086:2822] at
  00:1f.2, not AHCI. A driver for it has to match this ID or the board has to
  be switched to AHCI.
- **USB:** X99 xHCI [8086:8d31] at 00:14.0, plus two EHCI controllers.
- **Ethernet:** Intel I218-V [8086:15a1] at 00:19.0 and Qualcomm Atheros
  QCA8171 [1969:10a1] at 04:00.0.
- **MCFG (PCIe ECAM):** base 0x80000000, segment 0, buses 0-255.
- **MADT:** 12 Local APIC entries, all enabled, and 2 IOAPICs: id 8 at
  0xfec00000 (GSI 0) and id 9 at 0xfec01000 (GSI 24).
- **FADT:** revision 5, not hardware-reduced, no S0 idle.
  `IAPC_BOOT_ARCH` = 0x11 (legacy devices, PCIe ASPM controls); the 8042
  flag is clear.
- **NUMA tables:** `SRAT`, `SLIT` and `MSCT` are present on this
  single-socket board. `DMAR` (VT-d) is present.

## Scrubbing

`hwinv/` was scrubbed by `projects/harland/inventory/scrub_dump.py`. Its
report:

- SMBIOS: the system UUID is zeroed. Every serial number and asset tag is a
  vendor placeholder ("To Be Filled By O.E.M.", blanks, `00000000`,
  `DIMM_A1_AssetTag`), so they were kept.
- `pci.bin`: the Device Serial Number of the Atheros NIC (04:00.0) is zeroed.
- `edid-0.bin`: the monitor's serial number and its serial-number string
  descriptor are zeroed, and the block's checksum is fixed.

After the scrub, the script searched every file for each removed value, as
text, as UTF-16 and as bytes in both byte orders, and for the machine's
hostname and the owner's username. Nothing matched, and `check_dump.py`
passes on the result.
